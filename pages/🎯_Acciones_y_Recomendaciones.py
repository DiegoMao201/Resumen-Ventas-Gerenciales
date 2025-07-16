# ==============================================================================
# SCRIPT DE INTELIGENCIA COMERCIAL PARA: 🎯 Acciones y Recomendaciones.py
# VERSIÓN: 3.0 (Expansión Estratégica)
#
# DESCRIPCIÓN:
# Esta versión transforma la página en una herramienta de inteligencia activa para el vendedor.
# Las mejoras clave incluyen:
#
# 1.  CUADRANTES DE RENDIMIENTO: Se reemplaza la Matriz BCG por un análisis más intuitivo de
#     "Rentabilidad vs. Popularidad" (Nº de Clientes), creando cuadrantes accionables:
#     Líderes, Potenciales, De Nicho y Problemáticos.
#
# 2.  ANÁLISIS DE CESTA DE MERCADO (CROSS-SELLING): Se integra un motor de reglas de
#     asociación para identificar qué productos se compran juntos frecuentemente. Esto genera
#     oportunidades de venta cruzada directas y basadas en datos.
#
# 3.  ANÁLISIS DE PENETRACIÓN DE PORTAFOLIO: Se cruzan los productos más importantes con
#     los clientes clave para visualizar "espacios en blanco", es decir, oportunidades
#     de venta de productos estrella a clientes que aún no los compran.
#
# 4.  DIAGNÓSTICO PROFUNDO DE PRODUCTO: Una nueva pestaña que permite al vendedor
#     seleccionar cualquier producto y obtener un análisis 360° de su rendimiento individual,
#     incluyendo tendencias, márgenes y sus principales compradores.
#
# 5.  PLAN DE ACCIÓN MEJORADO: El plan de acción ahora es dinámico y se nutre de
#     todos los análisis anteriores, ofreciendo recomendaciones específicas y contextuales
#     en lugar de consejos genéricos.
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import unicodedata
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Inteligencia de Portafolio",
    page_icon="💡",
    layout="wide"
)

# ==============================================================================
# SECCIÓN 1: LÓGICA DE ANÁLISIS AVANZADO
# ==============================================================================

def normalizar_texto(texto):
    """Normaliza texto a mayúsculas, sin tildes ni caracteres especiales."""
    if not isinstance(texto, str): return texto
    try:
        return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper().strip()
    except (TypeError, AttributeError): return texto

@st.cache_data(ttl=3600)
def calcular_metricas_portafolio(_df):
    """Calcula un set completo de métricas por producto: Ventas, Márgenes, Popularidad."""
    if _df.empty: return pd.DataFrame()

    df_ventas = _df[_df['valor_venta'] > 0].copy()
    numeric_cols = ['valor_venta', 'costo_unitario', 'unidades_vendidas']
    for col in numeric_cols:
        df_ventas[col] = pd.to_numeric(df_ventas[col], errors='coerce')
    df_ventas.dropna(subset=numeric_cols, inplace=True)
    df_ventas['costo_total_linea'] = df_ventas['costo_unitario'] * df_ventas['unidades_vendidas']

    df_productos = df_ventas.groupby(['codigo_articulo', 'nombre_articulo']).agg(
        Volumen_Venta=('valor_venta', 'sum'),
        Costo_Total=('costo_total_linea', 'sum'),
        Unidades_Vendidas=('unidades_vendidas', 'sum'),
        Popularidad=('cliente_id', 'nunique') # Nº de clientes únicos que compraron el producto
    ).reset_index()

    df_productos['Margen_Absoluto'] = df_productos['Volumen_Venta'] - df_productos['Costo_Total']
    df_productos['Rentabilidad_Pct'] = np.where(df_productos['Volumen_Venta'] > 0, (df_productos['Margen_Absoluto'] / df_productos['Volumen_Venta']) * 100, 0)
    df_productos = df_productos[df_productos['Volumen_Venta'] > 0].sort_values(by="Volumen_Venta", ascending=False)
    
    return df_productos

@st.cache_data(ttl=3600)
def asignar_cuadrantes_rendimiento(_df_productos):
    """Asigna productos a cuadrantes de rendimiento basados en Rentabilidad y Popularidad."""
    if _df_productos.empty: return _df_productos

    df = _df_productos.copy()
    rentabilidad_media = df['Rentabilidad_Pct'].mean()
    popularidad_media = df['Popularidad'].mean()

    def get_cuadrante(row):
        alta_rentabilidad = row['Rentabilidad_Pct'] >= rentabilidad_media
        alta_popularidad = row['Popularidad'] >= popularidad_media
        if alta_rentabilidad and alta_popularidad: return '⭐ Líderes'
        if not alta_rentabilidad and alta_popularidad: return '🤔 Potenciales (Bajo Margen)'
        if alta_rentabilidad and not alta_popularidad: return '💎 De Nicho (Gemas Ocultas)'
        return '📉 Problemáticos'

    df['Cuadrante'] = df.apply(get_cuadrante, axis=1)
    return df

@st.cache_data(ttl=3600)
def analisis_cesta_mercado(_df):
    """Realiza un Market Basket Analysis para encontrar oportunidades de cross-selling."""
    if _df.empty or 'cliente_id' not in _df.columns: return pd.DataFrame()
    
    # Agrupar por "transacción" (cliente + fecha)
    transactions = _df.groupby(['cliente_id', 'fecha_venta'])['nombre_articulo'].apply(list).values.tolist()
    
    te = TransactionEncoder()
    te_ary = te.fit(transactions).transform(transactions)
    df_onehot = pd.DataFrame(te_ary, columns=te.columns_)
    
    # Apriori para encontrar itemsets frecuentes
    frequent_itemsets = apriori(df_onehot, min_support=0.01, use_colnames=True)
    if frequent_itemsets.empty: return pd.DataFrame()
    
    # Generar reglas de asociación
    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1)
    rules = rules.sort_values(['lift', 'confidence'], ascending=[False, False])
    rules = rules[['antecedents', 'consequents', 'confidence', 'lift']]
    rules['antecedents'] = rules['antecedents'].apply(lambda x: ', '.join(list(x)))
    rules['consequents'] = rules['consequents'].apply(lambda x: ', '.join(list(x)))
    rules.rename(columns={'antecedents': 'Si el cliente compra...', 'consequents': 'Recomendar también...', 'confidence': 'Confianza', 'lift': 'Potencial'}, inplace=True)
    return rules

# ==============================================================================
# SECCIÓN 2: COMPONENTES DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def render_tab_fotografia(df_analisis, enfoque, periodo):
    """Renderiza la pestaña principal con los cuadrantes de rendimiento."""
    st.header("📸 Fotografía del Portafolio")
    st.markdown(f"Análisis para: **{enfoque}** | Periodo: **{periodo}**")

    if df_analisis.empty:
        st.warning("No hay datos suficientes para generar la matriz de portafolio.")
        return

    df_plot = df_analisis.copy()
    df_plot['Tamaño_Grafico'] = df_plot['Volumen_Venta']
    
    fig = px.scatter(
        df_plot,
        x="Popularidad", y="Rentabilidad_Pct",
        size="Tamaño_Grafico", color="Cuadrante",
        hover_name="nombre_articulo",
        hover_data={'Popularidad': True, 'Rentabilidad_Pct': ':.2f', 'Volumen_Venta': ':,.0f'},
        size_max=70, title="Matriz de Rendimiento (Rentabilidad vs. Popularidad)",
        labels={"Popularidad": "Popularidad (Nº de Clientes que lo Compran)", "Rentabilidad_Pct": "Rentabilidad (%)"},
        color_discrete_map={
            '⭐ Líderes': 'green', 
            '💎 De Nicho (Gemas Ocultas)': 'gold', 
            '🤔 Potenciales (Bajo Margen)': 'dodgerblue', 
            '📉 Problemáticos': 'tomato'
        }
    )
    fig.add_vline(x=df_plot['Popularidad'].mean(), line_dash="dash", line_color="gray", annotation_text="Popularidad Media")
    fig.add_hline(y=df_plot['Rentabilidad_Pct'].mean(), line_dash="dash", line_color="gray", annotation_text="Rentabilidad Media")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Ver detalle de productos por cuadrante", expanded=False):
        st.dataframe(df_analisis[['nombre_articulo', 'Cuadrante', 'Volumen_Venta', 'Rentabilidad_Pct', 'Popularidad', 'Margen_Absoluto']], use_container_width=True, hide_index=True)

def render_tab_cross_selling(df_reglas):
    """Renderiza las oportunidades de venta cruzada."""
    st.header("💡 Oportunidades de Venta Cruzada (Cross-Selling)")
    st.info("""
        **¿Cómo leer esta tabla?** Si un cliente compra el producto de la primera columna, existe una alta probabilidad de que también esté interesado en el producto de la segunda.
        - **Confianza:** Porcentaje de veces que la recomendación fue acertada en el pasado.
        - **Potencial (Lift):** Cuántas veces más probable es que se compren juntos que por separado. Un valor > 1 indica una buena asociación.
    """)
    if df_reglas.empty:
        st.warning("No se encontraron suficientes patrones de compra conjunta para generar recomendaciones de venta cruzada en este periodo.")
        return
    
    conf_min = st.slider("Filtrar por Confianza mínima:", 0.0, 1.0, 0.2, 0.05)
    df_filtrada = df_reglas[df_reglas['Confianza'] >= conf_min]
    
    st.dataframe(df_filtrada, use_container_width=True, hide_index=True,
                 column_config={"Confianza": st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1),
                                "Potencial": st.column_config.NumberColumn(format="%.2f x")})

def render_tab_penetracion(df_ventas, df_analisis_productos):
    """Renderiza el análisis de penetración de productos en clientes clave."""
    st.header("🎯 Penetración en Clientes Clave")
    st.info("Esta sección muestra qué productos estrella **aún no han sido comprados** por tus clientes más importantes, revelando oportunidades directas.")

    if df_analisis_productos.empty:
        st.warning("No hay datos de productos para analizar la penetración.")
        return

    top_n_clientes = st.slider("Seleccionar el Top N de clientes a analizar:", 5, 20, 10)
    top_n_productos = st.slider("Seleccionar el Top N de productos a analizar:", 5, 20, 10)

    clientes_top = df_ventas.groupby('nombre_cliente')['valor_venta'].sum().nlargest(top_n_clientes).index
    productos_top = df_analisis_productos.nlargest(top_n_productos, 'Volumen_Venta')['nombre_articulo'].unique()

    df_cruce = df_ventas[df_ventas['nombre_cliente'].isin(clientes_top) & df_ventas['nombre_articulo'].isin(productos_top)]
    matriz_penetracion = pd.crosstab(df_cruce['nombre_cliente'], df_cruce['nombre_articulo'], values=df_cruce['valor_venta'], aggfunc='sum').fillna(0)
    
    # Reindexar para asegurar que todos los clientes y productos top estén presentes
    matriz_penetracion = matriz_penetracion.reindex(index=clientes_top, columns=productos_top, fill_value=0)

    fig = go.Figure(data=go.Heatmap(
        z=matriz_penetracion.values,
        x=matriz_penetracion.columns,
        y=matriz_penetracion.index,
        colorscale='Greens',
        hovertemplate='Cliente: %{y}<br>Producto: %{x}<br>Ventas: $%{z:,.0f}<extra></extra>'
    ))
    fig.update_layout(title=f'Mapa de Calor: Ventas de Top {top_n_productos} Productos a Top {top_n_clientes} Clientes',
                      xaxis_title="Productos Clave", yaxis_title="Clientes Clave")
    st.plotly_chart(fig, use_container_width=True)

    # Identificar oportunidades (celdas en cero)
    oportunidades = matriz_penetracion[matriz_penetracion == 0].stack().reset_index()
    oportunidades.columns = ['Cliente', 'Producto', '_']
    if not oportunidades.empty:
        with st.expander("Ver lista de oportunidades directas (espacios en blanco)", expanded=True):
            st.dataframe(oportunidades[['Cliente', 'Producto']], use_container_width=True, hide_index=True)

def render_tab_diagnostico(_df_ventas, df_analisis_productos):
    """Renderiza la pestaña para un análisis profundo de un producto individual."""
    st.header("🔬 Diagnóstico Profundo de Producto")
    if df_analisis_productos.empty:
        st.warning("No hay productos para analizar.")
        return

    lista_productos = df_analisis_productos['nombre_articulo'].tolist()
    producto_sel = st.selectbox("Seleccione un producto para su diagnóstico:", [""] + lista_productos, key="sel_prod_diag")

    if not producto_sel:
        st.info("Seleccione un producto de la lista para ver su análisis detallado.")
        return

    # Filtrar datos para el producto seleccionado
    info_producto = df_analisis_productos[df_analisis_productos['nombre_articulo'] == producto_sel].iloc[0]
    df_producto_ventas = _df_ventas[_df_ventas['nombre_articulo'] == producto_sel]

    st.subheader(f"Informe Médico para: {producto_sel}")
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Ventas Totales", f"${info_producto['Volumen_Venta']:,.0f}")
    kpi2.metric("Margen Bruto", f"${info_producto['Margen_Absoluto']:,.0f}")
    kpi3.metric("Rentabilidad Media", f"{info_producto['Rentabilidad_Pct']:.2f}%")
    kpi4.metric("Nº Clientes", f"{info_producto['Popularidad']}")

    # Análisis de compradores
    compradores = df_producto_ventas.groupby('nombre_cliente')['valor_venta'].sum().nlargest(10).reset_index()
    fig_compradores = px.bar(compradores, x='valor_venta', y='nombre_cliente', orientation='h',
                             title=f"Top 10 Compradores de {producto_sel}",
                             labels={'valor_venta': 'Ventas ($)', 'nombre_cliente': 'Cliente'})
    fig_compradores.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_compradores, use_container_width=True)


def render_tab_plan_accion(df_analisis, df_reglas, df_ventas):
    """Genera y renderiza el plan de acción dinámico y mejorado."""
    st.header("✍️ Plan de Acción Personalizado")
    st.info("Estas son recomendaciones automáticas generadas a partir de tus datos. Úsalas como punto de partida para tu estrategia comercial.")
    
    recomendaciones = []

    # 1. Acción sobre productos problemáticos
    df_problematicos = df_analisis[df_analisis['Cuadrante'] == '📉 Problemáticos'].sort_values(by='Margen_Absoluto').head(3)
    if not df_problematicos.empty:
        recomendaciones.append("### 📉 **Gestionar Productos Problemáticos**")
        for _, row in df_problematicos.iterrows():
            recomendaciones.append(f"- **Acción Crítica:** El producto **{row['nombre_articulo']}** tiene baja rentabilidad y pocos compradores. Aporta un margen de solo **${row['Margen_Absoluto']:,.0f}**. Considera descontinuarlo o no ofrecerlo activamente.")

    # 2. Acción sobre gemas ocultas
    df_gemas = df_analisis[df_analisis['Cuadrante'] == '💎 De Nicho (Gemas Ocultas)'].sort_values(by='Rentabilidad_Pct', ascending=False).head(3)
    if not df_gemas.empty:
        recomendaciones.append("### 💎 **Explotar Gemas Ocultas**")
        for _, row in df_gemas.iterrows():
            compradores_gema = df_ventas[df_ventas['nombre_articulo'] == row['nombre_articulo']]['cliente_id'].nunique()
            recomendaciones.append(f"- **Oportunidad de Nicho:** **{row['nombre_articulo']}** es altamente rentable ({row['Rentabilidad_Pct']:.1f}%) pero solo lo compran {compradores_gema} clientes. Identifica el perfil de estos compradores y busca clientes similares para ofrecérselo.")

    # 3. Acción sobre venta cruzada
    if not df_reglas.empty:
        recomendaciones.append("### 🔗 **Impulsar Venta Cruzada (Cross-Selling)**")
        top_regla = df_reglas.iloc[0]
        recomendaciones.append(f"- **Recomendación Directa:** Tu oportunidad de cross-selling más fuerte es: cuando un cliente compre **{top_regla['Si el cliente compra...']}**, ofrécele **{top_regla['Recomendar también...']}**. Esta combinación tiene una confianza del **{top_regla['Confianza']:.0%}**.")

    # 4. Acción sobre penetración
    clientes_top = df_ventas.groupby('nombre_cliente')['valor_venta'].sum().nlargest(10).index
    productos_top = df_analisis[df_analisis['Cuadrante'] == '⭐ Líderes']['nombre_articulo'].unique()
    if len(productos_top) > 0:
        df_cruce = df_ventas[df_ventas['nombre_cliente'].isin(clientes_top) & df_ventas['nombre_articulo'].isin(productos_top)]
        matriz_penetracion = pd.crosstab(df_cruce['nombre_cliente'], df_cruce['nombre_articulo']).reindex(index=clientes_top, columns=productos_top, fill_value=0)
        oportunidades = matriz_penetracion[matriz_penetracion == 0].stack().reset_index()
        if not oportunidades.empty:
            recomendaciones.append("### 🎯 **Cerrar Brechas en Clientes Clave**")
            oportunidad_top = oportunidades.iloc[0]
            recomendaciones.append(f"- **Oportunidad Directa:** Tu cliente clave **{oportunidad_top['nombre_cliente']}** aún no ha comprado tu producto líder **{oportunidad_top['nombre_articulo']}**. Prepara una oferta específica para tu próxima visita.")
            
    if not recomendaciones:
        st.success("¡Excelente rendimiento! No se han identificado acciones críticas inmediatas. Revisa las pestañas para encontrar oportunidades de optimización.")
    else:
        for punto in recomendaciones:
            st.markdown(punto)

# ==============================================================================
# SECCIÓN 3: ORQUESTADOR PRINCIPAL DE LA PÁGINA
# ==============================================================================

def render_pagina():
    """Orquesta la renderización de toda la página, incluyendo filtros y contenido en pestañas."""
    st.title("💡 Inteligencia de Portafolio y Acciones Comerciales")
    st.markdown("---")

    if 'df_ventas' not in st.session_state or st.session_state.df_ventas.empty:
        st.error("No se han cargado los datos de ventas. Por favor, ve a la página principal y carga los datos primero.")
        st.stop()
        
    df_ventas_historicas = st.session_state.df_ventas
    mapeo_meses = st.session_state.get('DATA_CONFIG', {}).get('mapeo_meses', {})

    st.sidebar.header("🗓️ Filtros de Análisis")
    lista_anios = sorted(df_ventas_historicas['anio'].unique(), reverse=True)
    anio_sel = st.sidebar.selectbox("Año", lista_anios, key="sel_anio_acc")
    meses_disponibles = sorted(df_ventas_historicas[df_ventas_historicas['anio'] == anio_sel]['mes'].unique())
    if not meses_disponibles:
        st.warning(f"No hay datos para el año {anio_sel}.")
        st.stop()
    mes_sel = st.sidebar.selectbox("Mes", meses_disponibles, format_func=lambda x: mapeo_meses.get(x, "N/A"), key="sel_mes_acc")
    
    vendedores_unicos = ["Visión General"] + sorted(df_ventas_historicas['nomvendedor'].dropna().unique())
    enfoque_sel = st.sidebar.selectbox("Enfoque", vendedores_unicos, key="sel_enfoque_acc")

    df_filtrado = df_ventas_historicas[(df_ventas_historicas['anio'] == anio_sel) & (df_ventas_historicas['mes'] == mes_sel)]
    if enfoque_sel != "Visión General":
        df_filtrado = df_filtrado[df_filtrado['nomvendedor'] == enfoque_sel]

    if df_filtrado.empty:
        st.info(f"No se encontraron datos para la selección: {enfoque_sel} en {mapeo_meses.get(mes_sel)} {anio_sel}.")
        st.stop()
    
    with st.spinner("Ejecutando análisis avanzados..."):
        df_analisis_productos = calcular_metricas_portafolio(df_filtrado)
        df_analisis_productos = asignar_cuadrantes_rendimiento(df_analisis_productos)
        df_reglas_asociacion = analisis_cesta_mercado(df_filtrado)

    periodo_str = f"{mapeo_meses.get(mes_sel)} {anio_sel}"
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📸 **Fotografía del Portafolio**",
        "🔗 **Venta Cruzada (Cross-Sell)**",
        "🎯 **Penetración de Clientes**",
        "🔬 **Diagnóstico por Producto**",
        "✍️ **Plan de Acción**"
    ])

    with tab1:
        render_tab_fotografia(df_analisis_productos, enfoque_sel, periodo_str)
    with tab2:
        render_tab_cross_selling(df_reglas_asociacion)
    with tab3:
        render_tab_penetracion(df_filtrado, df_analisis_productos)
    with tab4:
        render_tab_diagnostico(df_filtrado, df_analisis_productos)
    with tab5:
        render_tab_plan_accion(df_analisis_productos, df_reglas_asociacion, df_filtrado)


# --- Punto de Entrada del Script ---
if __name__ == "__main__":
    render_pagina()
