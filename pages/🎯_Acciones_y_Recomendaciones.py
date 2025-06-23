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
# (Las funciones de análisis se mantienen igual, solo cambiaremos la de la matriz)

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

    quintiles = df_rfm[['Recencia', 'Frecuencia', 'Monetario']].quantile([.25, .5, .75]).to_dict()
    def r_score(x): return 1 if x <= quintiles['Recencia'][.25] else 2 if x <= quintiles['Recencia'][.5] else 3 if x <= quintiles['Recencia'][.75] else 4
    def fm_score(x, c): return 4 if x > quintiles[c][.75] else 3 if x > quintiles[c][.5] else 2 if x > quintiles[c][.25] else 1
    df_rfm['R'] = df_rfm['Recencia'].apply(lambda x: r_score(x))
    df_rfm['F'] = df_rfm['Frecuencia'].apply(lambda x: fm_score(x, 'Frecuencia'))
    df_rfm['M'] = df_rfm['Monetario'].apply(lambda x: fm_score(x, 'Monetario'))
    
    mapa_segmentos = {
        r'^[1-2][3-4]$': '🏆 Campeones', r'^[1-2]2$': '💖 Clientes Leales',
        r'^[3-4][3-4]$': '😬 En Riesgo', r'^[3-4][1-2]$': '😥 Hibernando',
        r'^[1-2]1$': '🌱 Clientes Nuevos'
    }
    df_rfm['Clasificacion'] = (df_rfm['R'].astype(str) + df_rfm['F'].astype(str)).replace(mapa_segmentos, regex=True)
    df_rfm.loc[df_rfm['Clasificacion'].str.match(r'^\d{2}$'), 'Clasificacion'] = 'Otros'
    return df_rfm[['nombre_cliente', 'Recencia', 'Frecuencia', 'Monetario', 'Clasificacion']].sort_values('Monetario', ascending=False)


def analizar_matriz_productos(df_productos):
    if df_productos.empty: return pd.DataFrame()
    # Agrupar y calcular métricas, asegurando que el valor_venta no sea cero para evitar divisiones inválidas
    df_ventas = df_productos.groupby('nombre_articulo').agg(
        Volumen=('valor_venta', 'sum'),
        Margen_Total=('margen_bruto', 'sum')
    ).reset_index()
    df_ventas = df_ventas[df_ventas['Volumen'] > 0] # Solo productos con ventas positivas
    df_ventas['Rentabilidad'] = (df_ventas['Margen_Total'] / df_ventas['Volumen']) * 100

    vol_medio = df_ventas['Volumen'].median()
    rent_media = df_ventas['Rentabilidad'].median()

    def clasificar(row):
        if row['Volumen'] > vol_medio and row['Rentabilidad'] > rent_media: return '⭐ Estrella'
        if row['Volumen'] > vol_medio and row['Rentabilidad'] <= rent_media: return '🐄 Vaca Lechera'
        if row['Volumen'] <= vol_medio and row['Rentabilidad'] > rent_media: return '❓ Interrogante'
        return '🐕 Perro'
    df_ventas['Segmento'] = df_ventas.apply(clasificar, axis=1)
    return df_ventas

def generar_excel_descargable(datos_para_exportar):
    # ... (código sin cambios)
    pass
# ... (Otras funciones de análisis sin cambios)

# ==============================================================================
# 3. LÓGICA DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================
def render_pagina_acciones():
    st.title("🎯 Acciones y Recomendaciones Estratégicas")
    st.markdown("Planes de acción inteligentes basados en tus datos para impulsar los resultados.")
    
    # ... (Selectores de vendedor y mes sin cambios)
    
    # --- Ejecutar Análisis ---
    with st.spinner(f"Generando plan de acción para {seleccion}..."):
        df_productos, df_descuentos = preparar_datos_y_margen(df_vendedor.copy())
        analisis_rentabilidad = analizar_rentabilidad(df_productos, df_descuentos)
        df_rfm = analizar_segmentacion_rfm(df_productos, fecha_fin)
        df_matriz_productos = analizar_matriz_productos(df_productos)
        
    # ... (Botón de descarga sin cambios)
    
    # ... (Módulos Foco de la Semana y Rentabilidad sin cambios)

    st.header("👥 Segmentación Estratégica de Clientes (RFM)")
    # ... (código del módulo RFM sin cambios)

    # =============================================================
    # INICIO DE LA MEJORA VISUAL - Matriz de Productos
    # =============================================================
    st.header("📦 Estrategia de Portafolio de Productos")
    with st.container(border=True):
        st.info("""
        Clasifica tus productos para saber dónde invertir tu tiempo. **Pasa el mouse sobre las burbujas para ver el detalle de cada producto.**
        - **⭐ Estrellas:** Alta Venta y Alta Rentabilidad. ¡Tus productos clave!
        - **❓ Interrogantes:** Baja Venta, Alta Rentabilidad. ¡Tus mayores oportunidades de crecimiento! Impúlsalos.
        - **🐄 Vacas Lecheras:** Alta Venta, Baja Rentabilidad. Generan flujo de caja, gestiona su eficiencia.
        - **🐕 Perros:** Baja Venta, Baja Rentabilidad. Considera reducir su foco.
        """)
        
        if not df_matriz_productos.empty:
            # --- Gráfico Limpio con Escala Logarítmica ---
            fig_matriz = px.scatter(
                df_matriz_productos,
                x="Volumen",
                y="Rentabilidad",
                color="Segmento",
                size='Volumen',
                hover_name="nombre_articulo",
                log_x=True, # Escala logarítmica para mejor visualización
                color_discrete_map={
                    '⭐ Estrella': 'gold',
                    '🐄 Vaca Lechera': 'dodgerblue',
                    '❓ Interrogante': 'limegreen',
                    '🐕 Perro': 'tomato'
                },
                title="Matriz de Rendimiento de Productos"
            )

            # --- Anotaciones para Productos Clave ---
            # Identificar el mejor 'Estrella' e 'Interrogante'
            top_estrella = df_matriz_productos[df_matriz_productos['Segmento'] == '⭐ Estrella'].nlargest(1, 'Volumen')
            top_interrogante = df_matriz_productos[df_matriz_productos['Segmento'] == '❓ Interrogante'].nlargest(1, 'Rentabilidad')
            
            for _, row in top_estrella.iterrows():
                fig_matriz.add_annotation(x=np.log10(row['Volumen']), y=row['Rentabilidad'], text=f"⭐ {row['nombre_articulo']}", showarrow=True, arrowhead=1, bgcolor="#ffecb3", bordercolor="black")
            for _, row in top_interrogante.iterrows():
                fig_matriz.add_annotation(x=np.log10(row['Volumen']), y=row['Rentabilidad'], text=f"❓ {row['nombre_articulo']}", showarrow=True, arrowhead=1, bgcolor="#c8e6c9", bordercolor="black")

            fig_matriz.update_layout(xaxis_title="Volumen de Ventas (Escala Logarítmica)", yaxis_title="Rentabilidad (%)")
            st.plotly_chart(fig_matriz, use_container_width=True)

            # --- Tabla Interactiva para Explorar ---
            st.subheader("Explorar Datos de Productos")
            segmentos_seleccionados = st.multiselect(
                "Filtrar por segmento:",
                options=df_matriz_productos['Segmento'].unique(),
                default=df_matriz_productos['Segmento'].unique()
            )
            df_filtrada = df_matriz_productos[df_matriz_productos['Segmento'].isin(segmentos_seleccionados)]
            st.dataframe(
                df_filtrada,
                column_config={
                    "Volumen": st.column_config.NumberColumn(format="$ %d"),
                    "Rentabilidad": st.column_config.ProgressColumn(format="%.1f%%", min_value=df_filtrada['Rentabilidad'].min()-1, max_value=df_filtrada['Rentabilidad'].max()+1)
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hay suficientes datos de productos para generar la matriz en este periodo.")
    # =============================================================
    # FIN DE LA MEJORA VISUAL
    # =============================================================

# ==============================================================================
# 4. EJECUCIÓN PRINCIPAL
# ==============================================================================
render_pagina_acciones()
