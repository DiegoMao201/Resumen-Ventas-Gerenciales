import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import io
from dateutil.relativedelta import relativedelta
from datetime import datetime

# ==============================================================================
# 1. CONFIGURACIÓN Y ESTADO INICIAL
# ==============================================================================
st.set_page_config(page_title="Acciones y Recomendaciones", page_icon="🎯", layout="wide")

if not st.session_state.get('autenticado'):
    st.header("🔒 Acceso Restringido")
    st.warning("Por favor, inicie sesión desde la página principal `🏠 Resumen Mensual`.")
    st.stop()

df_ventas_historico = st.session_state.get('df_ventas')
APP_CONFIG = st.session_state.get('APP_CONFIG')
DATA_CONFIG = st.session_state.get('DATA_CONFIG')

if df_ventas_historico is None or df_ventas_historico.empty or not APP_CONFIG or not DATA_CONFIG:
    st.error("No se pudieron cargar los datos maestros. Vuelva a la página principal.")
    st.stop()

# ==============================================================================
# 2. LÓGICA DE ANÁLISIS Y RECOMENDACIONES (El "Cerebro")
# ==============================================================================

def preparar_datos_y_margen(df):
    filtro_descuento = (df['nombre_articulo'].str.contains('descuento', case=False, na=False)) & \
                       (df['nombre_articulo'].str.contains('comercial', case=False, na=False))
    df_descuentos = df[filtro_descuento]
    df_productos = df[~filtro_descuento].copy()
    df_productos['costo_total_linea'] = df_productos['costo_unitario'].fillna(0) * df_productos['unidades_vendidas'].fillna(0)
    df_productos['margen_bruto'] = df_productos['valor_venta'] - df_productos['costo_total_linea']
    return df_productos, df_descuentos

def analizar_rentabilidad(df_productos, df_descuentos):
    venta_bruta = df_productos['valor_venta'].sum()
    margen_bruto_productos = df_productos['margen_bruto'].sum()
    total_descuentos = abs(df_descuentos['valor_venta'].sum())
    margen_operativo = margen_bruto_productos - total_descuentos
    porcentaje_descuento = (total_descuentos / venta_bruta * 100) if venta_bruta > 0 else 0
    df_productos.loc[:, 'mes_anio'] = df_productos['fecha_venta'].dt.to_period('M')
    df_descuentos.loc[:, 'mes_anio'] = df_descuentos['fecha_venta'].dt.to_period('M')
    margen_bruto_mensual = df_productos.groupby('mes_anio')['margen_bruto'].sum()
    descuentos_mensual = abs(df_descuentos.groupby('mes_anio')['valor_venta'].sum())
    df_evolucion = pd.DataFrame(margen_bruto_mensual).reset_index()
    df_evolucion = pd.merge(df_evolucion, pd.DataFrame(descuentos_mensual).reset_index(), on='mes_anio', how='outer').fillna(0)
    df_evolucion['margen_operativo'] = df_evolucion['margen_bruto'] - df_evolucion['valor_venta']
    df_evolucion['mes_anio'] = df_evolucion['mes_anio'].dt.to_timestamp()
    top_clientes_descuento = abs(df_descuentos.groupby('nombre_cliente')['valor_venta'].sum()).nlargest(5).reset_index()
    return {
        "venta_bruta": venta_bruta, "margen_bruto_productos": margen_bruto_productos,
        "total_descuentos": total_descuentos, "margen_operativo": margen_operativo,
        "porcentaje_descuento": porcentaje_descuento, "df_evolucion": df_evolucion,
        "top_clientes_descuento": top_clientes_descuento
    }

def analizar_segmentacion_rfm(df_productos, fecha_fin_analisis):
    if df_productos.empty: return pd.DataFrame()
    df_rfm = df_productos.groupby(['cliente_id', 'nombre_cliente']).agg(
        Recencia=('fecha_venta', lambda date: (fecha_fin_analisis - date.max()).days),
        Frecuencia=('fecha_venta', 'nunique'),
        Monetario=('valor_venta', 'sum')
    ).reset_index()

    quintiles = df_rfm[['Recencia', 'Frecuencia', 'Monetario']].quantile([.2, .4, .6, .8]).to_dict()
    def r_score(x): return 1 if x <= quintiles['Recencia'][.2] else 2 if x <= quintiles['Recencia'][.4] else 3 if x <= quintiles['Recencia'][.6] else 4 if x <= quintiles['Recencia'][.8] else 5
    def fm_score(x, c): return 5 if x > quintiles[c][.8] else 4 if x > quintiles[c][.6] else 3 if x > quintiles[c][.4] else 2 if x > quintiles[c][.2] else 1
    df_rfm['R'] = df_rfm['Recencia'].apply(lambda x: r_score(x))
    df_rfm['F'] = df_rfm['Frecuencia'].apply(lambda x: fm_score(x, 'Frecuencia'))
    df_rfm['M'] = df_rfm['Monetario'].apply(lambda x: fm_score(x, 'Monetario'))
    df_rfm['Segmento'] = df_rfm['R'].astype(str) + df_rfm['F'].astype(str) + df_rfm['M'].astype(str)
    
    mapa_segmentos = {
        r'^[1-2][4-5][4-5]$': '🏆 Campeones', r'^[1-2][3-5][3-5]$': '💖 Clientes Leales',
        r'^[1-2][1-3][1-3]$': '🌱 Nuevos Clientes Prometedores', r'^[3-4][4-5][4-5]$': '😬 En Riesgo (Necesitan Atención)',
        r'^[3-5][1-3].*$': '😴 Hibernando / Baja Frecuencia', r'^[3-4][1-3].*$': '😥 Clientes en Peligro',
    }
    df_rfm['Clasificacion'] = df_rfm['Segmento'].replace(mapa_segmentos, regex=True)
    df_rfm.loc[df_rfm['Clasificacion'].str.match(r'^\d{3}$'), 'Clasificacion'] = 'Otros'
    return df_rfm[['nombre_cliente', 'Recencia', 'Frecuencia', 'Monetario', 'Clasificacion']].sort_values('Monetario', ascending=False)

def analizar_matriz_productos(df_productos):
    if df_productos.empty: return pd.DataFrame()
    df_matriz = df_productos.groupby('nombre_articulo').agg(
        Volumen=('valor_venta', 'sum'),
        Rentabilidad=('margen_bruto', lambda x: x.sum() / df_productos.loc[x.index, 'valor_venta'].sum() * 100)
    ).reset_index()
    df_matriz = df_matriz[df_matriz['Volumen'] > 0]
    
    vol_medio = df_matriz['Volumen'].median()
    rent_media = df_matriz['Rentabilidad'].median()

    def clasificar(row):
        if row['Volumen'] > vol_medio and row['Rentabilidad'] > rent_media: return '⭐ Estrella'
        if row['Volumen'] > vol_medio and row['Rentabilidad'] <= rent_media: return '🐄 Vaca Lechera'
        if row['Volumen'] <= vol_medio and row['Rentabilidad'] > rent_media: return '❓ Interrogante'
        return '🐕 Perro'
    df_matriz['Segmento'] = df_matriz.apply(clasificar, axis=1)
    return df_matriz

def generar_excel_descargable(datos_para_exportar):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in datos_para_exportar.items():
            if not df.empty:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()

# ==============================================================================
# 3. LÓGICA DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================
def render_pagina_acciones():
    st.title("🎯 Acciones y Recomendaciones Estratégicas")
    st.markdown("Planes de acción inteligentes basados en tus datos para impulsar los resultados.")
    
    # --- SELECTORES ---
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        # (código del selector de vendedor sin cambios)
        lista_vendedores = sorted(list(df_ventas_historico['nomvendedor'].dropna().unique()))
        vendedores_en_grupos = [v for lista in DATA_CONFIG['grupos_vendedores'].values() for v in lista]
        vendedores_solos = [v for v in lista_vendedores if v not in vendedores_en_grupos]
        opciones_analisis = list(DATA_CONFIG['grupos_vendedores'].keys()) + vendedores_solos
        usuario_actual = st.session_state.usuario
        if usuario_actual == "GERENTE":
            opciones_analisis.insert(0, "Seleccione un Vendedor o Grupo")
            default_index = 0
        else:
            opciones_analisis = [usuario_actual] if usuario_actual in opciones_analisis else []
            default_index = 0
        if not opciones_analisis: st.warning(f"No se encontraron datos para '{usuario_actual}'."); st.stop()
        seleccion = st.selectbox("Seleccione el Vendedor o Grupo a analizar:", opciones_analisis, index=default_index, key="seller_selector")
    
    if seleccion == "Seleccione un Vendedor o Grupo": st.info("Por favor, elija un vendedor para comenzar."); st.stop()

    df_vendedor_base = df_ventas_historico[df_ventas_historico['nomvendedor'].isin(DATA_CONFIG['grupos_vendedores'].get(seleccion, [seleccion]))]
    if df_vendedor_base.empty: st.warning(f"No hay datos para {seleccion}."); st.stop()
    
    df_vendedor_base.loc[:, 'periodo'] = df_vendedor_base['fecha_venta'].dt.to_period('M')
    meses_disponibles = sorted(df_vendedor_base['periodo'].unique())
    mapa_meses = {f"{DATA_CONFIG['mapeo_meses'][p.month]} {p.year}": p for p in meses_disponibles}
    opciones_slider = list(mapa_meses.keys())
    
    with col2:
        if len(opciones_slider) > 1:
            mes_inicio_str, mes_fin_str = st.select_slider("Seleccione rango de meses:", options=opciones_slider, value=(opciones_slider[0], opciones_slider[-1]))
        elif len(opciones_slider) == 1:
            mes_inicio_str = mes_fin_str = opciones_slider[0]
            st.text(f"Periodo: {mes_inicio_str}")
        else:
            st.warning("No hay periodos para analizar."); st.stop()
            
    periodo_inicio, periodo_fin = mapa_meses[mes_inicio_str], mapa_meses[mes_fin_str]
    fecha_inicio, fecha_fin = periodo_inicio.start_time, periodo_fin.end_time
    df_vendedor = df_vendedor_base[(df_vendedor_base['fecha_venta'] >= fecha_inicio) & (df_vendedor_base['fecha_venta'] <= fecha_fin)]
    if df_vendedor.empty: st.warning(f"No se encontraron datos para '{seleccion}' en el rango seleccionado."); st.stop()
        
    # --- Ejecutar Análisis ---
    with st.spinner(f"Generando plan de acción para {seleccion}..."):
        df_productos, df_descuentos = preparar_datos_y_margen(df_vendedor.copy())
        analisis_rentabilidad = analizar_rentabilidad(df_productos, df_descuentos)
        df_rfm = analizar_segmentacion_rfm(df_productos, fecha_fin)
        df_matriz_productos = analizar_matriz_productos(df_productos)
        
    # --- BOTÓN DE DESCARGA ---
    datos_para_exportar = {"Rentabilidad_y_Dcto": analisis_rentabilidad['df_evolucion'], "Top_Clientes_con_Dcto": analisis_rentabilidad['top_clientes_descuento'], "Segmentacion_RFM": df_rfm, "Matriz_de_Productos": df_matriz_productos}
    excel_file = generar_excel_descargable(datos_para_exportar)
    st.download_button(label="📥 Descargar Análisis en Excel", data=excel_file, file_name=f"Plan_Accion_{seleccion.replace(' ', '_')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.markdown("---")

    # --- RENDERIZADO DE MÓDULOS ---
    st.header("💰 Optimización de Rentabilidad y Descuentos")
    col1, col2, col3, col4 = st.columns(4)
    # ... (código de métricas sin cambios)

    st.header("👥 Segmentación Estratégica de Clientes (RFM)")
    with st.container(border=True):
        st.info("Clasifica a tus clientes para enfocar tus esfuerzos: **Campeones** (tus mejores clientes), **Leales** (compran consistentemente), **En Riesgo** (necesitan atención para no perderlos) e **Hibernando** (necesitan reactivación).")
        st.dataframe(df_rfm, use_container_width=True, hide_index=True)

    st.header("📦 Estrategia de Portafolio de Productos")
    with st.container(border=True):
        st.info("Clasifica tus productos para saber dónde invertir tu tiempo: **Estrellas** (alto volumen, alta rentabilidad), **Interrogantes** (potenciales estrellas, necesitan un impulso), **Vacas** (generan flujo de caja) y **Perros** (baja prioridad).")
        fig_matriz = px.scatter(df_matriz_productos, x="Volumen", y="Rentabilidad", color="Segmento", text="nombre_articulo", size='Volumen', hover_name="nombre_articulo", size_max=60)
        fig_matriz.update_traces(textposition='top center')
        st.plotly_chart(fig_matriz, use_container_width=True)

# ==============================================================================
# 4. EJECUCIÓN PRINCIPAL
# ==============================================================================
render_pagina_acciones()
