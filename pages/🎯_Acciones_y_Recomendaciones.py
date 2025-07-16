# ==============================================================================
# SCRIPT COMPLETO Y RECONSTRUIDO PARA: pages/1_Acciones_y_Recomendaciones.py
# VERSIÓN: 16 de Julio, 2025
# DESCRIPCIÓN: Script reconstruido desde cero para solucionar errores y mejorar
#              el análisis. La lógica de descuentos ahora se basa en el tipo de
#              documento 'NOTA_CREDITO'. Se solucionó el error de ValueError
#              en Plotly y se añadieron nuevos análisis y visualizaciones.
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io
import unicodedata
from datetime import datetime

# ==============================================================================
# SECCIÓN 1: CONFIGURACIÓN INICIAL Y CARGA DE DATOS
# ==============================================================================

st.set_page_config(page_title="Plan de Acción Estratégico", page_icon="🎯", layout="wide")

# Función de normalización (idéntica a la del script principal para consistencia)
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return texto
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').strip().replace('  ', ' ')
    except (TypeError, AttributeError):
        return texto

def mostrar_acceso_restringido():
    """Muestra un mensaje si el usuario no ha iniciado sesión."""
    st.header("🔒 Acceso Restringido")
    st.warning("Por favor, inicie sesión desde la página principal `🏠 Resumen Mensual` para continuar.")
    logo_url = st.session_state.get('APP_CONFIG', {}).get('url_logo', "https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png")
    st.image(logo_url, width=300)
    st.stop()

# --- Verificación del estado de la sesión ---
if not st.session_state.get('autenticado'):
    mostrar_acceso_restringido()

# --- Carga de datos y configuraciones desde la sesión principal ---
df_ventas_historico = st.session_state.get('df_ventas')
APP_CONFIG = st.session_state.get('APP_CONFIG')
DATA_CONFIG = st.session_state.get('DATA_CONFIG')

# --- Validación de datos cargados ---
if df_ventas_historico is None or df_ventas_historico.empty or not APP_CONFIG or not DATA_CONFIG:
    st.error("Error Crítico: No se pudieron cargar los datos desde la sesión.")
    st.warning("Por favor, regrese a la página '🏠 Resumen Mensual', asegúrese de que los datos se carguen y luego vuelva a esta página.")
    st.stop()


# ==============================================================================
# SECCIÓN 2: FUNCIONES DE ANÁLISIS DE NEGOCIO (EL "CEREBRO")
# ==============================================================================

@st.cache_data
def preparar_datos_analisis(df_bruto):
    """
    Filtra y procesa los datos del período.
    - Separa Facturas de Notas de Crédito.
    - Calcula el margen bruto solo sobre las facturas.
    """
    df = df_bruto.copy()
    
    # Normalizar TipoDocumento para una comparación robusta
    df['TipoDocumento_norm'] = df['TipoDocumento'].apply(normalizar_texto)
    
    # 1. Separar Facturas (ventas positivas)
    filtro_facturas = df['TipoDocumento_norm'].str.startswith('FACTURA', na=False)
    df_facturas = df[filtro_facturas].copy()
    
    # 2. Separar Notas de Crédito (devoluciones/descuentos, valores negativos)
    filtro_notas = df['TipoDocumento_norm'].str.contains('NOTA.*CREDITO', na=False, regex=True)
    df_notas_credito = df[filtro_notas].copy()

    # 3. Calcular el margen bruto a nivel de línea de producto (SOLO SOBRE FACTURAS)
    if not df_facturas.empty:
        df_facturas['costo_unitario'] = pd.to_numeric(df_facturas['costo_unitario'], errors='coerce').fillna(0)
        df_facturas['unidades_vendidas'] = pd.to_numeric(df_facturas['unidades_vendidas'], errors='coerce').fillna(0)
        df_facturas['valor_venta'] = pd.to_numeric(df_facturas['valor_venta'], errors='coerce').fillna(0)
        
        df_facturas['costo_total_linea'] = df_facturas['costo_unitario'] * df_facturas['unidades_vendidas']
        df_facturas['margen_bruto_linea'] = df_facturas['valor_venta'] - df_facturas['costo_total_linea']
        
        # Evitar división por cero
        df_facturas['rentabilidad_linea'] = np.where(df_facturas['valor_venta'] != 0, 
                                                     (df_facturas['margen_bruto_linea'] / df_facturas['valor_venta']) * 100, 
                                                     0)

    # df_productos ahora se refiere solo a las ventas facturadas
    return df_facturas, df_notas_credito

@st.cache_data
def analizar_rentabilidad_total(df_productos, df_devoluciones):
    """Calcula las métricas de rentabilidad clave para el período seleccionado."""
    venta_facturada = df_productos['valor_venta'].sum()
    total_devoluciones = abs(df_devoluciones['valor_venta'].sum()) # El valor es negativo, lo necesitamos positivo
    venta_neta_final = venta_facturada - total_devoluciones
    
    margen_bruto_total = df_productos['margen_bruto_linea'].sum()
    margen_operativo_real = margen_bruto_total - total_devoluciones
    
    rentabilidad_bruta_pct = (margen_bruto_total / venta_facturada * 100) if venta_facturada > 0 else 0
    rentabilidad_operativa_pct = (margen_operativo_real / venta_facturada * 100) if venta_facturada > 0 else 0
    
    return {
        "venta_facturada": venta_facturada,
        "total_devoluciones": total_devoluciones,
        "venta_neta_final": venta_neta_final,
        "margen_bruto": margen_bruto_total,
        "margen_operativo": margen_operativo_real,
        "rentabilidad_bruta_pct": rentabilidad_bruta_pct,
        "rentabilidad_operativa_pct": rentabilidad_operativa_pct
    }

@st.cache_data
def analizar_segmentacion_rfm(df_productos, fecha_fin_analisis):
    """Realiza un análisis RFM (Recencia, Frecuencia, Monetario) para segmentar clientes."""
    if df_productos.empty:
        return pd.DataFrame()
        
    df_rfm = df_productos.groupby('nombre_cliente').agg(
        Recencia=('fecha_venta', lambda date: (fecha_fin_analisis - date.max()).days),
        Frecuencia=('Serie', 'nunique'),
        Monetario=('valor_venta', 'sum')
    ).reset_index()

    if len(df_rfm) < 4: return df_rfm

    df_rfm['R_Score'] = pd.qcut(df_rfm['Recencia'], 4, labels=[4, 3, 2, 1], duplicates='drop')
    df_rfm['F_Score'] = pd.qcut(df_rfm['Frecuencia'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop')
    
    mapa_segmentos = {
        r'^[3-4][3-4]$': '🏆 Campeones',
        r'^[3-4][1-2]$': '🌱 Potenciales Leales',
        r'^[1-2][3-4]$': '😬 En Riesgo',
        r'^[1-2][1-2]$': '😥 Hibernando'
    }
    df_rfm['Segmento_RFM'] = (df_rfm['R_Score'].astype(str) + df_rfm['F_Score'].astype(str)).replace(mapa_segmentos, regex=True)
    df_rfm.loc[df_rfm['Segmento_RFM'].str.match(r'^\d{2}$'), 'Segmento_RFM'] = 'Otros'
    
    return df_rfm[['nombre_cliente', 'Recencia', 'Frecuencia', 'Monetario', 'Segmento_RFM']].sort_values('Monetario', ascending=False)

@st.cache_data
def analizar_matriz_bcg(df_productos):
    """Crea una Matriz BCG para clasificar el portafolio de productos."""
    if df_productos.empty:
        return pd.DataFrame()
        
    df_matriz = df_productos.groupby('nombre_articulo').agg(
        Volumen_Venta=('valor_venta', 'sum'),
        Margen_Absoluto=('margen_bruto_linea', 'sum')
    ).reset_index()
    
    df_matriz = df_matriz[df_matriz['Volumen_Venta'] > 0]
    if df_matriz.empty: return pd.DataFrame()

    df_matriz['Rentabilidad_Pct'] = np.where(df_matriz['Volumen_Venta'] != 0, (df_matriz['Margen_Absoluto'] / df_matriz['Volumen_Venta']) * 100, 0)
    
    vol_medio = df_matriz['Volumen_Venta'].median()
    rent_media = df_matriz['Rentabilidad_Pct'].median()

    def clasificar_bcg(row):
        if row['Volumen_Venta'] >= vol_medio and row['Rentabilidad_Pct'] >= rent_media: return '⭐ Estrella'
        if row['Volumen_Venta'] >= vol_medio and row['Rentabilidad_Pct'] < rent_media: return '🐄 Vaca Lechera'
        if row['Volumen_Venta'] < vol_medio and row['Rentabilidad_Pct'] >= rent_media: return '❓ Interrogante'
        return '🐕 Perro'

    df_matriz['Segmento_BCG'] = df_matriz.apply(clasificar_bcg, axis=1)
    return df_matriz

def generar_excel_completo(datos_exportar):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for nombre_hoja, df in datos_exportar.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                df.to_excel(writer, sheet_name=nombre_hoja, index=False)
    return output.getvalue()

# ==============================================================================
# SECCIÓN 3: INTERFAZ DE USUARIO Y VISUALIZACIONES
# ==============================================================================
def render_pagina_acciones():
    st.title("🎯 Plan de Acción Estratégico")
    st.markdown("Análisis profundo para la toma de decisiones. Explore la rentabilidad, clientes y productos para descubrir oportunidades de crecimiento.")

    st.sidebar.title("Filtros del Análisis")
    
    # Lógica de selección de Vendedor/Grupo
    vendedores_unicos_norm = sorted(list(df_ventas_historico['nomvendedor'].dropna().unique()))
    grupos = DATA_CONFIG.get('grupos_vendedores', {})
    mapa_norm_a_orig = {normalizar_texto(v): v for v in df_ventas_historico['nomvendedor'].dropna().unique()}
    vendedores_en_grupos_norm = {normalizar_texto(v) for lista in grupos.values() for v in lista}
    vendedores_solos_norm = [v_norm for v_norm in vendedores_unicos_norm if v_norm not in vendedores_en_grupos_norm]
    vendedores_solos_orig = sorted([mapa_norm_a_orig.get(v_norm) for v_norm in vendedores_solos_norm if mapa_norm_a_orig.get(v_norm)])
    opciones_analisis = ["TODOS (VISIÓN GERENCIAL)"] + sorted(grupos.keys()) + vendedores_solos_orig
    
    usuario_actual = st.session_state.usuario
    default_index = 0
    if normalizar_texto(usuario_actual) != "GERENTE":
        try:
            default_index = opciones_analisis.index(usuario_actual)
        except ValueError:
            opciones_analisis.insert(1, usuario_actual)
            default_index = 1

    seleccion = st.sidebar.selectbox("Seleccione Vendedor o Grupo a analizar:", opciones_analisis, index=default_index)

    fecha_min = df_ventas_historico['fecha_venta'].min().date()
    fecha_max = df_ventas_historico['fecha_venta'].max().date()
    
    fecha_inicio, fecha_fin = st.sidebar.date_input("Seleccione el rango de fechas:", value=(fecha_max.replace(day=1), fecha_max), min_value=fecha_min, max_value=fecha_max)

    if not fecha_inicio or not fecha_fin or fecha_inicio > fecha_fin:
        st.sidebar.error("Rango de fechas inválido.")
        st.stop()
    
    with st.spinner(f"Analizando datos para '{seleccion}'..."):
        if seleccion == "TODOS (VISIÓN GERENCIAL)":
            df_filtrado_vendedor = df_ventas_historico
        else:
            lista_vendedores_filtrar = grupos.get(seleccion, [seleccion])
            df_filtrado_vendedor = df_ventas_historico[df_ventas_historico['nomvendedor'].isin([normalizar_texto(v) for v in lista_vendedores_filtrar])]

        fecha_inicio_dt, fecha_fin_dt = pd.to_datetime(fecha_inicio), pd.to_datetime(fecha_fin)
        df_periodo = df_filtrado_vendedor[(df_filtrado_vendedor['fecha_venta'] >= fecha_inicio_dt) & (df_filtrado_vendedor['fecha_venta'] <= fecha_fin_dt)]

        if df_periodo.empty:
            st.warning(f"No se encontraron datos de ventas para '{seleccion}' en el período seleccionado.")
            st.stop()

        df_productos, df_devoluciones = preparar_datos_analisis(df_periodo)
        
        if df_productos.empty:
            st.warning(f"No se encontraron facturas para '{seleccion}' en el período seleccionado. No se puede continuar el análisis.")
            st.stop()
            
        analisis_rentabilidad = analizar_rentabilidad_total(df_productos, df_devoluciones)
        df_rfm = analizar_segmentacion_rfm(df_productos, fecha_fin_dt)
        df_bcg = analizar_matriz_bcg(df_productos)
        
        df_dispersion_clientes = df_productos.groupby('nombre_cliente').agg(
            Frecuencia=('Serie', 'nunique'),
            Ticket_Promedio=('valor_venta', 'mean'),
            Venta_Total=('valor_venta', 'sum')
        ).reset_index()

    st.download_button(label="📥 Descargar Análisis Completo en Excel", data=generar_excel_completo({"Rentabilidad": pd.DataFrame([analisis_rentabilidad]), "Clientes_RFM": df_rfm, "Productos_BCG": df_bcg, "Detalle_Facturas": df_productos, "Detalle_Notas_Credito": df_devoluciones}), file_name=f"Analisis_{seleccion.replace(' ', '_')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["💰 Resumen de Rentabilidad", "📉 Análisis de Devoluciones", "👥 Análisis de Clientes", "📦 Análisis de Productos", "💡 Plan de Acción"])

    with tab1:
        st.header("Análisis de Rentabilidad")
        st.info(f"Análisis para **{seleccion}** desde el **{fecha_inicio.strftime('%d/%m/%Y')}** hasta el **{fecha_fin.strftime('%d/%m/%Y')}**.")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Facturado", f"${analisis_rentabilidad['venta_facturada']:,.0f}")
        col2.metric("Total Devoluciones (NC)", f"-${analisis_rentabilidad['total_devoluciones']:,.0f}", help="Valor total de las Notas de Crédito.")
        col3.metric("Venta Neta Real", f"${analisis_rentabilidad['venta_neta_final']:,.0f}")
        
        col4, col5, col6 = st.columns(3)
        col4.metric("Margen Bruto (sobre facturado)", f"${analisis_rentabilidad['margen_bruto']:,.0f}", f"{analisis_rentabilidad['rentabilidad_bruta_pct']:.1f}% Rent.")
        col5.metric("Margen Operativo (Post-NC)", f"${analisis_rentabilidad['margen_operativo']:,.0f}", f"{analisis_rentabilidad['rentabilidad_operativa_pct']:.1f}% Rent.")
        
        fig_waterfall = go.Figure(go.Waterfall(
            name = "20", orientation = "v",
            measure = ["absolute", "relative", "total", "relative", "total"],
            x = ["Total Facturado", "Devoluciones (NC)", "Venta Neta", "Costo de Venta", "Margen Bruto"],
            textposition = "outside",
            text = [f"${v:,.0f}" for v in [analisis_rentabilidad['venta_facturada'], -analisis_rentabilidad['total_devoluciones'], analisis_rentabilidad['venta_neta_final'], -(analisis_rentabilidad['venta_facturada'] - analisis_rentabilidad['margen_bruto']), analisis_rentabilidad['margen_bruto']]],
            y = [analisis_rentabilidad['venta_facturada'], -analisis_rentabilidad['total_devoluciones'], 0, -(analisis_rentabilidad['venta_facturada'] - analisis_rentabilidad['margen_bruto']), 0],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        fig_waterfall.update_layout(title_text="Descomposición del Margen Bruto", showlegend=False)
        st.plotly_chart(fig_waterfall, use_container_width=True)

    with tab2:
        st.header("Análisis de Notas de Crédito (Devoluciones y Ajustes)")
        if df_devoluciones.empty:
            st.success("¡Excelente! No se registraron Notas de Crédito en este período para la selección actual.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Clientes con más Devoluciones")
                top_clientes_nc = df_devoluciones.groupby('nombre_cliente')['valor_venta'].sum().abs().nlargest(10).reset_index()
                fig_clientes_nc = px.bar(top_clientes_nc, y='nombre_cliente', x='valor_venta', orientation='h', title="Top 10 Clientes por Valor en NC", labels={'valor_venta': 'Monto en NC ($)', 'nombre_cliente': ''}, text='valor_venta')
                fig_clientes_nc.update_traces(texttemplate='$%{text:,.0f}', textposition='outside').update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_clientes_nc, use_container_width=True)
            with col2:
                st.subheader("Productos más Devueltos")
                top_prods_nc = df_devoluciones.groupby('nombre_articulo')['valor_venta'].sum().abs().nlargest(10).reset_index()
                fig_prods_nc = px.bar(top_prods_nc, y='nombre_articulo', x='valor_venta', orientation='h', title="Top 10 Productos por Valor en NC", labels={'valor_venta': 'Monto en NC ($)', 'nombre_articulo': ''}, text='valor_venta')
                fig_prods_nc.update_traces(texttemplate='$%{text:,.0f}', textposition='outside').update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_prods_nc, use_container_width=True)

    with tab3:
        st.header("Segmentación Estratégica de Clientes (RFM)")
        if not df_rfm.empty:
            col1, col2 = st.columns([0.4, 0.6])
            with col1:
                st.markdown("- **🏆 Campeones:** Clientes más valiosos. ¡Fidelízalos!")
                st.markdown("- **🌱 Potenciales Leales:** Compran bien pero poco frecuente. ¡Aumenta su frecuencia!")
                st.markdown("- **😬 En Riesgo:** Frecuentes, pero hace tiempo no vuelven. ¡Re actívalos!")
                st.markdown("- **😥 Hibernando:** Clientes perdidos.")
                fig_rfm = px.pie(df_rfm, names='Segmento_RFM', title="Distribución de Clientes por Segmento", hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig_rfm, use_container_width=True)
            with col2:
                st.dataframe(df_rfm.style.format({'Monetario': '${:,.0f}'}), use_container_width=True, height=500)
            
            st.subheader("Mapa de Valor de Clientes")
            # SOLUCIÓN AL ERROR: Asegurarse de que 'size' no sea negativo.
            df_dispersion_plot = df_dispersion_clientes[df_dispersion_clientes['Venta_Total'] > 0].copy()
            if not df_dispersion_plot.empty:
                fig_disp = px.scatter(df_dispersion_plot, x="Ticket_Promedio", y="Frecuencia", size="Venta_Total", color="Venta_Total", hover_name="nombre_cliente", log_x=True, size_max=60, title="Frecuencia vs. Ticket Promedio", labels={"Ticket_Promedio": "Ticket Promedio ($)", "Frecuencia": "N° de Compras"})
                st.plotly_chart(fig_disp, use_container_width=True)
            else:
                st.info("No hay clientes con ventas positivas netas para mostrar en el mapa de dispersión.")
        else:
            st.warning("No hay suficientes datos de clientes para realizar el análisis RFM.")

    with tab4:
        st.header("Estrategia de Portafolio de Productos (Matriz BCG)")
        if not df_bcg.empty:
            fig_bcg = px.scatter(df_bcg, x="Volumen_Venta", y="Rentabilidad_Pct", size="Margen_Absoluto", color="Segmento_BCG", hover_name="nombre_articulo", log_x=True, size_max=60, title="Matriz de Rendimiento de Productos", labels={"Volumen_Venta": "Volumen de Venta ($)", "Rentabilidad_Pct": "Rentabilidad (%)"}, color_discrete_map={'⭐ Estrella': 'gold', '🐄 Vaca Lechera': 'dodgerblue', '❓ Interrogante': 'limegreen', '🐕 Perro': 'tomato'})
            st.plotly_chart(fig_bcg, use_container_width=True)
            
            st.subheader("Explorar Datos por Segmento BCG")
            segmento_sel = st.selectbox("Selecciona un segmento:", sorted(df_bcg['Segmento_BCG'].unique()))
            df_bcg_filtrado = df_bcg[df_bcg['Segmento_BCG'] == segmento_sel].sort_values('Volumen_Venta', ascending=False)
            st.dataframe(df_bcg_filtrado.style.format({'Volumen_Venta': '${:,.0f}', 'Margen_Absoluto': '${:,.0f}', 'Rentabilidad_Pct': '{:.1f}%'}), height=400, use_container_width=True)
        else:
            st.warning("No hay suficientes datos de productos para generar la matriz BCG.")

    with tab5:
        st.header("💡 Plan de Acción Sugerido")
        st.info("Recomendaciones generadas a partir de los datos analizados.")

        with st.container(border=True):
            st.subheader("🎯 Rentabilidad y Devoluciones")
            pct_devoluciones = (analisis_rentabilidad['total_devoluciones'] / analisis_rentabilidad['venta_facturada']) if analisis_rentabilidad['venta_facturada'] > 0 else 0
            if pct_devoluciones > 0.05:
                 st.warning(f"**Atención:** Las devoluciones representan un **{pct_devoluciones:.1%}** del total facturado. Es crucial investigar las causas, especialmente de los productos y clientes top en devoluciones, para proteger el margen.")
            else:
                 st.success("**Control de Devoluciones:** El nivel de Notas de Crédito es bajo. ¡Buen trabajo! Mantén el monitoreo.")
            st.info("**Acción:** Revisa los productos 'Vaca Lechera' (alta venta, baja rentabilidad). ¿Es posible mejorar su margen negociando con proveedores o ajustando ligeramente el precio? Para los 'Perro', considera si es estratégico mantenerlos en portafolio.")

        with st.container(border=True):
            st.subheader("👥 Clientes")
            if not df_rfm.empty:
                st.success(f"**Fidelizar Campeones:** Tienes **{len(df_rfm[df_rfm['Segmento_RFM'] == '🏆 Campeones'])} clientes Campeones**. Crea un programa de beneficios exclusivos para ellos. Son tu activo más valioso.")
                if not df_rfm[df_rfm['Segmento_RFM'] == '😬 En Riesgo'].empty:
                    st.warning(f"**Reactivar Clientes en Riesgo:** Hay **{len(df_rfm[df_rfm['Segmento_RFM'] == '😬 En Riesgo'])} clientes importantes que no han comprado recientemente**. Lanza una campaña de reactivación con una oferta personalizada.")
            st.info("**Acción (Mapa de Valor):** Identifica clientes con alta frecuencia pero bajo ticket promedio. Son candidatos ideales para venta cruzada (cross-selling). Ofréceles productos de mayor valor o complementarios a sus compras habituales.")

        with st.container(border=True):
            st.subheader("📦 Productos")
            if not df_bcg.empty:
                st.success(f"**Impulsar Interrogantes:** Tienes **{len(df_bcg[df_bcg['Segmento_BCG'] == '❓ Interrogante'])} productos con alta rentabilidad pero baja venta**. Son tus joyas ocultas. Dales mayor visibilidad, capacita al equipo sobre sus ventajas y considera una campaña de marketing específica para ellos.")
                if not df_bcg[df_bcg['Segmento_BCG'] == '🐕 Perro'].empty:
                    st.warning(f"**Evaluar Productos Perro:** Hay **{len(df_bcg[df_bcg['Segmento_BCG'] == '🐕 Perro'])} productos de bajo rendimiento**. Analiza si cumplen un rol estratégico (ej. atraer clientes). Si no, considera reducir su inventario o deslistarlos para simplificar la operación.")
            st.info("**Acción (Estrellas):** Asegura siempre la disponibilidad de tus productos 'Estrella'. Un quiebre de stock en estos productos significa una gran pérdida de oportunidad.")

# --- Ejecución Principal de la Página ---
if __name__ == "__main__":
    render_pagina_acciones()
