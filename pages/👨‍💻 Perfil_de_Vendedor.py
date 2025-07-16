# ==============================================================================
# SCRIPT REESTRUCTURADO Y MEJORADO PARA: pages/2_Perfil_del_Vendedor.py
# VERSIÓN: 16 de Julio, 2025
#
# DESCRIPCIÓN:
# Esta versión transforma el "Perfil del Vendedor" en un centro de análisis
# estratégico integral. Se han incorporado las siguientes mejoras:
#
# 1.  **Análisis RFM Avanzado:** Segmentación de clientes en categorías
#     estratégicas (Campeones, Leales, En Riesgo, etc.) para acciones de
#     marketing y retención dirigidas.
# 2.  **Análisis de Pareto (80/20):** Identificación precisa del porcentaje
#     de clientes que generan el 80% de los ingresos, con visualizaciones claras.
# 3.  **Inteligencia de Producto y Rentabilidad:** Análisis profundo del mix
#     de ventas por categoría y marca, y un desglose detallado de la
#     rentabilidad por producto y cliente.
# 4.  **Diagnóstico de Salud de Cartera:** Métricas mejoradas sobre clientes
#     nuevos, recurrentes, y en riesgo, con listas detalladas para acción inmediata.
# 5.  **Interfaz de Usuario Mejorada (UI/UX):**
#     -   Uso de pestañas más descriptivas para una navegación intuitiva.
#     -   Resumen ejecutivo (KPIs) al frente para una visión rápida.
#     -   Visualizaciones enriquecidas con Plotly para una mejor comprensión.
#     -   Contenedores y métricas para destacar la información más relevante.
# 6.  **Optimización y Escalabilidad:** El código está organizado en secciones
#     lógicas (Configuración, Lógica de Análisis, Componentes UI, Orquestador Principal),
#     utilizando caching de Streamlit (`@st.cache_data`) para un rendimiento óptimo.
#
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import unicodedata

# ==============================================================================
# SECCIÓN 1: CONFIGURACIÓN INICIAL Y FUNCIONES DE SOPORTE
# ==============================================================================

st.set_page_config(page_title="Análisis Estratégico de Vendedor", page_icon="🚀", layout="wide")

def normalizar_texto(texto):
    """
    Normaliza un texto a mayúsculas, sin tildes ni caracteres especiales.
    Idéntica a la del script principal para mantener consistencia.
    """
    if not isinstance(texto, str):
        return texto
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').strip().replace('  ', ' ')
    except (TypeError, AttributeError):
        return texto

def mostrar_acceso_restringido():
    """Muestra un mensaje de advertencia si el usuario no ha iniciado sesión."""
    st.header("🔒 Acceso Restringido")
    st.warning("Por favor, inicie sesión desde la página principal `🏠 Resumen Mensual` para continuar.")
    st.image("https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", width=300)
    st.stop()

# --- Verificación de estado de la sesión ---
if not st.session_state.get('autenticado'):
    mostrar_acceso_restringido()

# --- Carga de datos PRE-PROCESADOS desde la sesión principal ---
df_ventas_historico = st.session_state.get('df_ventas')
APP_CONFIG = st.session_state.get('APP_CONFIG')
DATA_CONFIG = st.session_state.get('DATA_CONFIG')

# --- Validación de datos ---
if df_ventas_historico is None or df_ventas_historico.empty or not APP_CONFIG or not DATA_CONFIG:
    st.error("Error Crítico: No se pudieron cargar los datos desde la sesión. Por favor, regrese a la página '🏠 Resumen Mensual' y vuelva a cargar los datos.")
    st.stop()


# ==============================================================================
# SECCIÓN 2: LÓGICA DE ANÁLISIS AVANZADO (El "Cerebro")
# ==============================================================================

def calcular_metricas_base(df):
    """Añade columnas de margen y costo total. Confía en datos de entrada pre-procesados."""
    df_copy = df.copy()
    df_copy['costo_total_linea'] = df_copy['costo_unitario'].fillna(0) * df_copy['unidades_vendidas'].fillna(0)
    df_copy['margen_bruto'] = df_copy['valor_venta'] - df_copy['costo_total_linea']
    df_copy['porcentaje_margen'] = np.where(df_copy['valor_venta'] > 0, (df_copy['margen_bruto'] / df_copy['valor_venta']) * 100, 0)
    return df_copy

@st.cache_data
def analizar_tendencias_evolutivas(_df_vendedor):
    """Analiza la evolución mensual de Ventas, Margen y KPIs clave."""
    df = _df_vendedor.copy()
    df['mes_anio'] = df['fecha_venta'].dt.to_period('M')

    df_evolucion = df.groupby('mes_anio').agg(
        valor_venta=('valor_venta', 'sum'),
        margen_bruto=('margen_bruto', 'sum'),
        clientes_unicos=('cliente_id', 'nunique')
    ).reset_index()

    df_evolucion['mes_anio'] = df_evolucion['mes_anio'].dt.to_timestamp()
    df_evolucion['porcentaje_margen'] = np.where(df_evolucion['valor_venta'] > 0, (df_evolucion['margen_bruto'] / df_evolucion['valor_venta']) * 100, 0)

    return df_evolucion.fillna(0)

@st.cache_data
def realizar_analisis_rfm(_df_vendedor):
    """
    Realiza un análisis de Recencia, Frecuencia y Monetario (RFM) para segmentar clientes.
    """
    if _df_vendedor.empty: return pd.DataFrame(), {}

    df = _df_vendedor.copy()
    fecha_max_analisis = df['fecha_venta'].max() + pd.Timedelta(days=1)

    rfm_df = df.groupby(['cliente_id', 'nombre_cliente']).agg(
        Recencia=('fecha_venta', lambda date: (fecha_max_analisis - date.max()).days),
        Frecuencia=('fecha_venta', 'count'),
        Monetario=('valor_venta', 'sum')
    ).reset_index()

    # Creación de quintiles para puntajes
    rfm_df['R_Score'] = pd.qcut(rfm_df['Recencia'], 5, labels=[5, 4, 3, 2, 1], duplicates='drop')
    rfm_df['F_Score'] = pd.qcut(rfm_df['Frecuencia'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5], duplicates='drop')
    rfm_df['M_Score'] = pd.qcut(rfm_df['Monetario'], 5, labels=[1, 2, 3, 4, 5], duplicates='drop')
    
    rfm_df['R_Score'] = rfm_df['R_Score'].astype(int)
    rfm_df['F_Score'] = rfm_df['F_Score'].astype(int)
    rfm_df['M_Score'] = rfm_df['M_Score'].astype(int)

    rfm_df['RFM_Score'] = rfm_df['R_Score'].astype(str) + rfm_df['F_Score'].astype(str) + rfm_df['M_Score'].astype(str)

    # Segmentación basada en puntajes de Recencia y Frecuencia
    segt_map = {
        r'[1-2][1-2]': 'Hibernando',
        r'[1-2][3-4]': 'En Riesgo',
        r'[1-2]5': 'No se pueden perder',
        r'3[1-2]': 'Necesitan Atención',
        r'33': 'Leales Promedio',
        r'[3-4][4-5]': 'Clientes Leales',
        r'41': 'Prometedores',
        r'51': 'Nuevos Clientes',
        r'[4-5][2-3]': 'Potenciales Leales',
        r'5[4-5]': 'Campeones'
    }
    rfm_df['Segmento'] = rfm_df['R_Score'].astype(str) + rfm_df['F_Score'].astype(str)
    rfm_df['Segmento'] = rfm_df['Segmento'].replace(segt_map, regex=True)

    # Conteo de clientes por segmento
    resumen_segmentos = rfm_df['Segmento'].value_counts().reset_index()
    resumen_segmentos.columns = ['Segmento', 'Numero_Clientes']

    return rfm_df, resumen_segmentos

@st.cache_data
def analizar_cartera_y_concentracion(_df_vendedor):
    """Analiza la salud de la cartera (nuevos, recurrentes) y la concentración de ventas."""
    if _df_vendedor.empty: return {}

    fecha_max = _df_vendedor['fecha_venta'].max()
    mes_actual_inicio = fecha_max.replace(day=1)

    # Identificación de clientes
    clientes_mes_actual = set(_df_vendedor[_df_vendedor['fecha_venta'] >= mes_actual_inicio]['cliente_id'].unique())
    clientes_historicos = set(_df_vendedor[_df_vendedor['fecha_venta'] < mes_actual_inicio]['cliente_id'].unique())

    clientes_nuevos = clientes_mes_actual - clientes_historicos
    clientes_recurrentes = clientes_mes_actual.intersection(clientes_historicos)

    # Pareto Analysis (80/20)
    ventas_por_cliente = _df_vendedor.groupby('nombre_cliente')['valor_venta'].sum().sort_values(ascending=False)
    df_pareto = ventas_por_cliente.to_frame()
    df_pareto['Porcentaje_Acumulado'] = (df_pareto['valor_venta'].cumsum() / df_pareto['valor_venta'].sum()) * 100
    
    # Encontrar el punto del 80%
    try:
        clientes_80_pct = df_pareto[df_pareto['Porcentaje_Acumulado'] <= 80].shape[0] + 1
    except:
        clientes_80_pct = 0
    total_clientes = df_pareto.shape[0]
    porcentaje_clientes_80_20 = (clientes_80_pct / total_clientes * 100) if total_clientes > 0 else 0


    return {
        "nuevos": len(clientes_nuevos),
        "recurrentes": len(clientes_recurrentes),
        "top_clientes_volumen": ventas_por_cliente.head(15).reset_index(),
        "pareto_data": df_pareto.reset_index(),
        "pareto_summary": {
            "clientes_top_80": clientes_80_pct,
            "total_clientes": total_clientes,
            "porcentaje_clientes_top_80": porcentaje_clientes_80_20
        }
    }

@st.cache_data
def analizar_productos_y_rentabilidad(_df_vendedor):
    """Analiza el mix de productos, marcas y la rentabilidad detallada."""
    if 'super_categoria' not in _df_vendedor.columns or 'nombre_marca' not in _df_vendedor.columns:
        return {"error": "Faltan columnas 'super_categoria' o 'nombre_marca'."}

    # Rentabilidad por Producto
    top_productos_margen = _df_vendedor.groupby('nombre_articulo')['margen_bruto'].sum().nlargest(10).reset_index()
    bottom_productos_margen = _df_vendedor.groupby('nombre_articulo')['margen_bruto'].sum().nsmallest(10).reset_index()

    # Rentabilidad por Cliente
    top_clientes_margen = _df_vendedor.groupby(['cliente_id', 'nombre_cliente'])['margen_bruto'].sum().nlargest(10).reset_index()

    # Mix de Ventas
    mix_super_categoria = _df_vendedor.groupby('super_categoria')['valor_venta'].sum().reset_index()
    mix_marcas = _df_vendedor.groupby('nombre_marca')['valor_venta'].sum().nlargest(15).reset_index()

    return {
        "top_productos_margen": top_productos_margen,
        "bottom_productos_margen": bottom_productos_margen,
        "top_clientes_margen": top_clientes_margen,
        "distribucion_margen": _df_vendedor['porcentaje_margen'],
        "mix_super_categoria": mix_super_categoria,
        "mix_marcas": mix_marcas
    }

# ==============================================================================
# SECCIÓN 3: COMPONENTES DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def render_kpis_resumen(df, nombre_vendedor):
    """Muestra los KPIs principales del vendedor en el periodo seleccionado."""
    st.header(f"KPIs Clave para: {nombre_vendedor}")
    with st.container(border=True):
        venta_total = df['valor_venta'].sum()
        margen_total = df['margen_bruto'].sum()
        porcentaje_margen_promedio = (margen_total / venta_total * 100) if venta_total > 0 else 0
        clientes_unicos = df['cliente_id'].nunique()
        ticket_promedio = venta_total / clientes_unicos if clientes_unicos > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Ventas Totales", f"${venta_total:,.0f}")
        col2.metric("📈 Margen Bruto Total", f"${margen_total:,.0f}")
        col3.metric("📊 Margen Promedio", f"{porcentaje_margen_promedio:.2f}%")
        col4.metric("🧑‍🤝‍🧑 Clientes Únicos", f"{clientes_unicos}")

def render_tab_tendencias(analisis):
    """Renderiza la pestaña de análisis de tendencias."""
    st.subheader("Evolución Mensual del Rendimiento")
    df_evolucion = analisis['analisis_tendencias']

    if df_evolucion.empty:
        st.info("No hay suficientes datos históricos para mostrar una tendencia.")
        return

    # Gráfico de Ventas vs Margen
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_evolucion['mes_anio'], y=df_evolucion['valor_venta'], name='Ventas', marker_color='royalblue'))
    fig.add_trace(go.Scatter(x=df_evolucion['mes_anio'], y=df_evolucion['margen_bruto'], name='Margen Bruto', mode='lines+markers', yaxis='y2', line=dict(color='orange', width=3)))

    fig.update_layout(
        title='Ventas y Margen Bruto Mensual',
        xaxis_title='Mes',
        yaxis_title='Ventas ($)',
        yaxis2=dict(title='Margen Bruto ($)', overlaying='y', side='right'),
        legend=dict(x=0.01, y=0.99)
    )
    st.plotly_chart(fig, use_container_width=True)

def render_tab_analisis_cartera(analisis):
    """Renderiza la pestaña de análisis de cartera y concentración."""
    st.subheader("Diagnóstico de la Cartera de Clientes")
    analisis_cartera = analisis['analisis_cartera']

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("##### 🧑‍🤝‍🧑 Composición de Clientes (Último Mes)")
            st.metric("Clientes Nuevos", f"{analisis_cartera.get('nuevos', 0)} 🆕")
            st.metric("Clientes Recurrentes", f"{analisis_cartera.get('recurrentes', 0)} 🔄")

    with col2:
        with st.container(border=True):
            st.markdown("##### 🎯 Principio de Pareto (80/20)")
            pareto_summary = analisis_cartera.get('pareto_summary', {})
            st.metric(
                label=f"Clientes que generan el 80% de las ventas:",
                value=f"{pareto_summary.get('clientes_top_80', 0)} de {pareto_summary.get('total_clientes', 0)}"
            )
            st.progress(
                value=pareto_summary.get('porcentaje_clientes_top_80', 0) / 100,
                text=f"{pareto_summary.get('porcentaje_clientes_top_80', 0):.1f}% de la base de clientes"
            )

    st.markdown("---")
    st.subheader("Top 15 Clientes por Volumen de Venta")
    st.dataframe(
        analisis_cartera.get('top_clientes_volumen', pd.DataFrame()),
        use_container_width=True, hide_index=True,
        column_config={"valor_venta": st.column_config.NumberColumn("Venta Total", format="$ %d")}
    )

def render_tab_rfm(analisis):
    """Renderiza la pestaña de análisis RFM."""
    st.subheader("Segmentación Estratégica de Clientes (RFM)")
    rfm_df, resumen_segmentos = analisis.get('analisis_rfm', (pd.DataFrame(), pd.DataFrame()))

    if rfm_df.empty:
        st.warning("No hay suficientes datos para realizar el análisis RFM.")
        return

    col1, col2 = st.columns([0.4, 0.6])
    with col1:
        st.markdown("##### Distribución de Clientes por Segmento")
        st.dataframe(resumen_segmentos, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("##### Visualización de Segmentos")
        fig = px.treemap(resumen_segmentos, path=['Segmento'], values='Numero_Clientes',
                         title='Proporción de Clientes por Segmento Estratégico',
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(margin = dict(t=50, l=25, r=25, b=25))
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Ver detalle completo de la segmentación RFM"):
        st.dataframe(rfm_df, use_container_width=True, hide_index=True)


def render_tab_productos_rentabilidad(analisis):
    """Renderiza la pestaña de análisis de productos y rentabilidad."""
    st.subheader("Análisis de Rentabilidad y Mix de Productos")
    analisis_prod = analisis.get('analisis_productos', {})

    if "error" in analisis_prod:
        st.error(f"Error en el análisis de productos: {analisis_prod['error']}")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 📈 Ventas por Super Categoría")
        if not analisis_prod['mix_super_categoria'].empty:
            fig = px.pie(analisis_prod['mix_super_categoria'], names='super_categoria', values='valor_venta', hole=0.4, title="Mix de Ventas por Super Categoría")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de 'Super Categoría' para mostrar.")

    with col2:
        st.markdown("##### 🏷️ Top 15 Marcas por Venta")
        if not analisis_prod['mix_marcas'].empty:
            fig = px.bar(analisis_prod['mix_marcas'], x='valor_venta', y='nombre_marca', orientation='h', title="Top Marcas")
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de 'Marca' para mostrar.")

    st.markdown("---")
    st.subheader("Análisis de Rentabilidad por Producto")
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("##### ✅ Top 10 Productos MÁS Rentables (Margen Bruto)")
        st.dataframe(analisis_prod['top_productos_margen'], use_container_width=True, hide_index=True, column_config={"margen_bruto": st.column_config.NumberColumn("Margen", format="$ %d")})
    with col4:
        st.markdown("##### ❌ Top 10 Productos MENOS Rentables (Margen Bruto)")
        st.dataframe(analisis_prod['bottom_productos_margen'], use_container_width=True, hide_index=True, column_config={"margen_bruto": st.column_config.NumberColumn("Margen", format="$ %d")})

# ==============================================================================
# SECCIÓN 4: ORQUESTADOR PRINCIPAL DE LA PÁGINA
# ==============================================================================

def render_pagina_perfil():
    """Función principal que orquesta el renderizado completo de la página."""
    st.title("🚀 Perfil Estratégico de Vendedor")
    st.markdown("Análisis 360° del rendimiento histórico, cartera de clientes, rentabilidad y mix de productos.")
    st.markdown("---")

    # --- Filtros de Selección ---
    col1, col2 = st.columns([0.4, 0.6])
    with col1:
        vendedores_unicos_norm = sorted(list(df_ventas_historico['nomvendedor'].dropna().unique()))
        grupos = DATA_CONFIG.get('grupos_vendedores', {})
        vendedores_en_grupos_norm = [normalizar_texto(v) for lista in grupos.values() for v in lista]
        mapa_norm_a_orig = {normalizar_texto(v): v for v in df_ventas_historico['nomvendedor'].dropna().unique()}
        vendedores_solos_norm = [v_norm for v_norm in vendedores_unicos_norm if v_norm not in vendedores_en_grupos_norm]
        vendedores_solos_orig = sorted([mapa_norm_a_orig.get(v_norm) for v_norm in vendedores_solos_norm if mapa_norm_a_orig.get(v_norm)])
        nombres_grupos = sorted(grupos.keys())
        opciones_analisis = nombres_grupos + vendedores_solos_orig
        
        usuario_actual = st.session_state.usuario
        default_index = 0
        if normalizar_texto(usuario_actual) != "GERENTE":
            opciones_analisis = [usuario_actual] if usuario_actual in opciones_analisis else []
        else:
            opciones_analisis.insert(0, "Seleccione un Vendedor o Grupo")

        if not opciones_analisis:
            st.warning(f"No se encontraron datos asociados al usuario '{usuario_actual}'.")
            st.stop()
        
        seleccion = st.selectbox("Seleccione el Vendedor o Grupo a analizar:", opciones_analisis, index=default_index, help="Elija un perfil individual o un grupo consolidado.")

    if seleccion == "Seleccione un Vendedor o Grupo":
        st.info("Por favor, elija un vendedor o grupo para comenzar el análisis.")
        st.stop()

    with col2:
        df_vendedor_base_copy = df_ventas_historico.copy()
        df_vendedor_base_copy['periodo'] = df_vendedor_base_copy['fecha_venta'].dt.to_period('M')
        meses_disponibles = sorted(df_vendedor_base_copy['periodo'].unique())
        mapa_meses = {f"{DATA_CONFIG['mapeo_meses'].get(p.month, p.month)} {p.year}": p for p in meses_disponibles}
        opciones_slider = list(mapa_meses.keys())
        
        start_index = max(0, len(opciones_slider) - 12)
        end_index = len(opciones_slider) - 1
        if start_index > end_index: start_index = end_index

        mes_inicio_str, mes_fin_str = st.select_slider(
            "Seleccione el Rango de Meses para el Análisis Histórico:",
            options=opciones_slider,
            value=(opciones_slider[start_index], opciones_slider[end_index])
        )
        periodo_inicio, periodo_fin = mapa_meses[mes_inicio_str], mapa_meses[mes_fin_str]
        fecha_inicio, fecha_fin = periodo_inicio.start_time, periodo_fin.end_time.normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)


    # --- Filtrado final de datos ---
    lista_vendedores_a_filtrar = grupos.get(seleccion, [seleccion])
    lista_vendedores_a_filtrar_norm = [normalizar_texto(v) for v in lista_vendedores_a_filtrar]
    df_base = df_ventas_historico[df_ventas_historico['nomvendedor'].isin(lista_vendedores_a_filtrar_norm)]
    df_vendedor = df_base[(df_base['fecha_venta'] >= fecha_inicio) & (df_base['fecha_venta'] <= fecha_fin)]

    if df_vendedor.empty:
        st.warning(f"No se encontraron datos para '{seleccion}' en el rango de meses seleccionado ({mes_inicio_str} a {mes_fin_str}).")
        st.stop()

    # --- Ejecución de análisis y renderizado de resultados ---
    with st.spinner(f"Realizando análisis estratégico para {seleccion}..."):
        df_vendedor_procesado = calcular_metricas_base(df_vendedor)

        analisis_completo = {
            "analisis_tendencias": analizar_tendencias_evolutivas(df_vendedor_procesado),
            "analisis_rfm": realizar_analisis_rfm(df_vendedor_procesado),
            "analisis_cartera": analizar_cartera_y_concentracion(df_vendedor_procesado),
            "analisis_productos": analizar_productos_y_rentabilidad(df_vendedor_procesado)
        }

    st.markdown("---")
    render_kpis_resumen(df_vendedor_procesado, seleccion)
    st.markdown("---")

    # --- Pestañas de Análisis Detallado ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 **Tendencias y Evolución**",
        "👥 **Salud de la Cartera**",
        "🏆 **Segmentación RFM**",
        "📦 **Rentabilidad y Productos**"
    ])

    with tab1:
        render_tab_tendencias(analisis_completo)
    with tab2:
        render_tab_analisis_cartera(analisis_completo)
    with tab3:
        render_tab_rfm(analisis_completo)
    with tab4:
        render_tab_productos_rentabilidad(analisis_completo)


# ==============================================================================
# PUNTO DE ENTRADA DEL SCRIPT
# ==============================================================================
if __name__ == "__main__":
    render_pagina_perfil()
