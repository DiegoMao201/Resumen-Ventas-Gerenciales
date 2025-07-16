# ==============================================================================
# SCRIPT DE INTELIGENCIA COMERCIAL PARA: 🎯 Acciones y Recomendaciones.py
# VERSIÓN: 4.0 (Motor Analítico Optimizado y UI Mejorada)
#
# DESCRIPCIÓN:
# Esta versión es una reconstrucción completa que soluciona el bug de los filtros
# y eleva la herramienta a un nivel superior de rendimiento y usabilidad.
#
# 1.  BUG CORREGIDO: El problema de caché que impedía la actualización con los
#     filtros ha sido solucionado implementando una estrategia de caching robusta.
#
# 2.  MOTOR ANALÍTICO CENTRALIZADO: Una única función cacheada (`run_full_analysis`)
#     ejecuta todos los cálculos pesados una sola vez por selección de filtros,
#     haciendo que la navegación entre pestañas sea instantánea.
#
# 3.  KPIs GLOBALES DINÁMICOS: Se añade un resumen ejecutivo en la parte superior
#     con los indicadores clave del periodo y enfoque seleccionados.
#
# 4.  DIAGNÓSTICO DE PRODUCTO 360°: El análisis de producto ahora incluye una
#     tendencia histórica de ventas para entender su estacionalidad y ciclo de vida.
#
# 5.  PLAN DE ACCIÓN HIPER-ACCIONABLE: Las recomendaciones ahora son específicas,
#     mencionando clientes y productos reales para que el vendedor sepa
#     exactamente qué hacer. (Ej: "Ofrece el Producto X al Cliente Y").
#
# 6.  FLEXIBILIDAD DE ANÁLISIS: Se añade la opción de ver el consolidado de
#     "Todo el año" además de la vista mensual.
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import unicodedata
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from typing import List, Dict, Any, Tuple

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Inteligencia de Portafolio v4.0",
    page_icon="🚀",
    layout="wide"
)

# ==============================================================================
# SECCIÓN 1: LÓGICA DE ANÁLISIS AVANZADO Y GESTIÓN DE DATOS
# ==============================================================================

def normalizar_texto(texto: Any) -> str:
    """Normaliza texto a mayúsculas, sin tildes ni caracteres especiales."""
    if not isinstance(texto, str):
        return texto
    try:
        # Normaliza, convierte a ASCII y luego a mayúsculas.
        return unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8').upper().strip()
    except (TypeError, AttributeError):
        return texto

@st.cache_data(ttl=3600)
def run_full_analysis(_df: pd.DataFrame, anio: int, mes: int or str, vendedor: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Función central que filtra los datos y ejecuta todos los análisis necesarios.
    Cacheada para un rendimiento óptimo. Los filtros son argumentos explícitos
    para que el caché funcione correctamente.
    """
    # 1. Filtrar el DataFrame según la selección del usuario
    df_filtrado = _df[(_df['anio'] == anio)]
    if mes != "Todo el año":
        df_filtrado = df_filtrado[df_filtrado['mes'] == mes]
    if vendedor != "Visión General":
        df_filtrado = df_filtrado[df_filtrado['nomvendedor'] == vendedor]

    if df_filtrado.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # 2. Calcular Métricas del Portafolio
    df_ventas = df_filtrado[df_filtrado['valor_venta'] > 0].copy()
    numeric_cols = ['valor_venta', 'costo_unitario', 'unidades_vendidas']
    for col in numeric_cols:
        df_ventas[col] = pd.to_numeric(df_ventas[col], errors='coerce')
    df_ventas.dropna(subset=numeric_cols, inplace=True)
    df_ventas['costo_total_linea'] = df_ventas['costo_unitario'] * df_ventas['unidades_vendidas']

    df_productos = df_ventas.groupby(['codigo_articulo', 'nombre_articulo']).agg(
        Volumen_Venta=('valor_venta', 'sum'),
        Costo_Total=('costo_total_linea', 'sum'),
        Popularidad=('cliente_id', 'nunique')
    ).reset_index()

    df_productos['Margen_Absoluto'] = df_productos['Volumen_Venta'] - df_productos['Costo_Total']
    df_productos['Rentabilidad_Pct'] = np.where(df_productos['Volumen_Venta'] > 0, (df_productos['Margen_Absoluto'] / df_productos['Volumen_Venta']) * 100, 0)
    df_productos = df_productos[df_productos['Volumen_Venta'] > 0]

    # 3. Asignar Cuadrantes de Rendimiento
    if not df_productos.empty:
        rentabilidad_media = df_productos['Rentabilidad_Pct'].median() # Usar mediana es más robusto a outliers
        popularidad_media = df_productos['Popularidad'].median()

        def get_cuadrante(row):
            alta_rentabilidad = row['Rentabilidad_Pct'] >= rentabilidad_media
            alta_popularidad = row['Popularidad'] >= popularidad_media
            if alta_rentabilidad and alta_popularidad: return '⭐ Líderes'
            if not alta_rentabilidad and alta_popularidad: return '🤔 Potenciales (Bajo Margen)'
            if alta_rentabilidad and not alta_popularidad: return '💎 De Nicho (Gemas Ocultas)'
            return '📉 Problemáticos'
        df_productos['Cuadrante'] = df_productos.apply(get_cuadrante, axis=1)

    # 4. Análisis de Cesta de Mercado (Cross-Selling)
    df_reglas = pd.DataFrame()
    if not df_ventas.empty and df_ventas['cliente_id'].nunique() > 1:
        transactions = df_ventas.groupby(['cliente_id', 'fecha_venta'])['nombre_articulo'].apply(list).values.tolist()
        if transactions:
            te = TransactionEncoder()
            te_ary = te.fit(transactions).transform(transactions)
            df_onehot = pd.DataFrame(te_ary, columns=te.columns_)
            
            # Ajustar min_support dinámicamente para evitar errores
            min_support_val = max(0.01, 10 / len(transactions)) if len(transactions) > 0 else 0.01
            
            frequent_itemsets = apriori(df_onehot, min_support=min_support_val, use_colnames=True)
            if not frequent_itemsets.empty:
                rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.0)
                if not rules.empty:
                    rules = rules.sort_values(['lift', 'confidence'], ascending=[False, False])
                    rules = rules[['antecedents', 'consequents', 'confidence', 'lift']]
                    rules['antecedents'] = rules['antecedents'].apply(lambda x: ', '.join(list(x)))
                    rules['consequents'] = rules['consequents'].apply(lambda x: ', '.join(list(x)))
                    rules.rename(columns={'antecedents': 'Si el cliente compra...', 'consequents': 'Recomendar también...', 'confidence': 'Confianza', 'lift': 'Potencial'}, inplace=True)
                    df_reglas = rules
    
    return df_filtrado, df_productos.sort_values(by="Volumen_Venta", ascending=False), df_reglas

# ==============================================================================
# SECCIÓN 2: COMPONENTES DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def render_tab_fotografia(df_analisis: pd.DataFrame, enfoque: str, periodo: str):
    st.header("📸 Fotografía del Portafolio")
    st.markdown(f"Análisis para: **{enfoque}** | Periodo: **{periodo}**")

    if df_analisis.empty:
        st.warning("No hay datos suficientes para generar la matriz de portafolio.")
        return

    c1, c2 = st.columns([2, 1])
    with c1:
        fig = px.scatter(
            df_analisis, x="Popularidad", y="Rentabilidad_Pct",
            size="Volumen_Venta", color="Cuadrante",
            hover_name="nombre_articulo",
            hover_data={'Popularidad': True, 'Rentabilidad_Pct': ':.2f%', 'Volumen_Venta': ':,.0f'},
            size_max=70, title="Matriz de Rendimiento (Rentabilidad vs. Popularidad)",
            labels={"Popularidad": "Popularidad (Nº de Clientes)", "Rentabilidad_Pct": "Rentabilidad (%)"},
            color_discrete_map={
                '⭐ Líderes': '#2ca02c', '💎 De Nicho (Gemas Ocultas)': '#ff7f0e',
                '🤔 Potenciales (Bajo Margen)': '#1f77b4', '📉 Problemáticos': '#d62728'
            }
        )
        fig.add_vline(x=df_analisis['Popularidad'].median(), line_dash="dash", line_color="gray", annotation_text="Mediana Popularidad")
        fig.add_hline(y=df_analisis['Rentabilidad_Pct'].median(), line_dash="dash", line_color="gray", annotation_text="Mediana Rentabilidad")
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.subheader("Resumen por Cuadrante")
        summary = df_analisis.groupby('Cuadrante')['Volumen_Venta'].agg(['count', 'sum']).reset_index()
        summary.columns = ['Cuadrante', 'Nº Productos', 'Ventas Totales']
        summary['% Ventas'] = (summary['Ventas Totales'] / summary['Ventas Totales'].sum()) * 100
        st.dataframe(summary, hide_index=True, use_container_width=True,
            column_config={
                "Ventas Totales": st.column_config.NumberColumn(format="$ {:,.0f}"),
                "% Ventas": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)
            })
        st.info("La 'Popularidad' se mide por el número de clientes únicos y la 'Rentabilidad' por el margen porcentual. El tamaño de la burbuja representa el volumen de ventas.")

    with st.expander("Ver detalle de todos los productos", expanded=False):
        st.dataframe(df_analisis[['nombre_articulo', 'Cuadrante', 'Volumen_Venta', 'Rentabilidad_Pct', 'Popularidad', 'Margen_Absoluto']], use_container_width=True, hide_index=True)

def render_tab_cross_selling(df_reglas: pd.DataFrame):
    st.header("💡 Oportunidades de Venta Cruzada (Cross-Selling)")
    st.info("""
        **¿Cómo leer esta tabla?** Si un cliente compra el producto de la primera columna, existe una alta probabilidad de que también esté interesado en el producto de la segunda.
        - **Confianza:** Porcentaje de veces que la recomendación fue acertada en el pasado.
        - **Potencial (Lift):** Cuántas veces más probable es que se compren juntos que por separado. Un valor > 1.5 indica una fuerte asociación.
    """)
    if df_reglas.empty:
        st.warning("No se encontraron suficientes patrones de compra conjunta para generar recomendaciones de venta cruzada en este periodo.")
        return
    
    conf_min = st.slider("Filtrar por Confianza mínima:", 0.0, 1.0, 0.1, 0.05)
    df_filtrada = df_reglas[df_reglas['Confianza'] >= conf_min].head(20) # Mostrar top 20
    
    st.dataframe(df_filtrada, use_container_width=True, hide_index=True,
        column_config={
            "Confianza": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=1),
            "Potencial": st.column_config.NumberColumn(format="%.2f x")
        })

def render_tab_penetracion(df_ventas: pd.DataFrame, df_analisis_productos: pd.DataFrame):
    st.header("🎯 Penetración en Clientes Clave")
    st.info("Esta sección muestra qué productos estrella **aún no han sido comprados** por tus clientes más importantes, revelando oportunidades directas (espacios en blanco).")

    if df_analisis_productos.empty or df_ventas.empty:
        st.warning("No hay datos suficientes para analizar la penetración.")
        return

    c1, c2 = st.columns(2)
    top_n_clientes = c1.slider("Seleccionar el Top N de clientes (por ventas):", 5, 25, 10)
    top_n_productos = c2.slider("Seleccionar el Top N de productos (por ventas):", 5, 25, 10)

    clientes_top = df_ventas.groupby('nombre_cliente')['valor_venta'].sum().nlargest(top_n_clientes).index
    productos_top = df_analisis_productos.nlargest(top_n_productos, 'Volumen_Venta')['nombre_articulo'].unique()

    matriz_penetracion = pd.crosstab(
        index=df_ventas['nombre_cliente'],
        columns=df_ventas['nombre_articulo'],
        values=df_ventas['valor_venta'],
        aggfunc='sum'
    ).reindex(index=clientes_top, columns=productos_top).fillna(0)
    
    # Identificar oportunidades (celdas en cero) ANTES de formatear
    oportunidades = matriz_penetracion[matriz_penetracion == 0].stack().reset_index()
    oportunidades.columns = ['Cliente', 'Producto', '_']

    fig = go.Figure(data=go.Heatmap(
        z=matriz_penetracion.values, x=matriz_penetracion.columns, y=matriz_penetracion.index,
        colorscale='Greens',
        hovertemplate='Cliente: %{y}<br>Producto: %{x}<br>Ventas: $%{z:,.0f}<extra></extra>'
    ))
    fig.update_layout(title=f'Mapa de Calor: Ventas de Top {top_n_productos} Productos a Top {top_n_clientes} Clientes',
                      xaxis_title="Productos Clave", yaxis_title="Clientes Clave")
    st.plotly_chart(fig, use_container_width=True)
    
    if not oportunidades.empty:
        with st.expander("🎯 **Ver lista de oportunidades directas (espacios en blanco)**", expanded=True):
            st.dataframe(oportunidades[['Cliente', 'Producto']], use_container_width=True, hide_index=True)

def render_tab_diagnostico(_df_ventas_full_periodo: pd.DataFrame, df_analisis_productos: pd.DataFrame):
    st.header("🔬 Diagnóstico Profundo de Producto")
    if df_analisis_productos.empty:
        st.warning("No hay productos para analizar.")
        return

    lista_productos = [""] + sorted(df_analisis_productos['nombre_articulo'].unique().tolist())
    producto_sel = st.selectbox("Seleccione un producto para su diagnóstico:", lista_productos, key="sel_prod_diag")

    if not producto_sel:
        st.info("Seleccione un producto de la lista para ver su análisis detallado.")
        return

    info_producto = df_analisis_productos[df_analisis_productos['nombre_articulo'] == producto_sel].iloc[0]
    df_producto_ventas = _df_ventas_full_periodo[_df_ventas_full_periodo['nombre_articulo'] == producto_sel]

    st.subheader(f"Informe 360° para: {producto_sel}")
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Ventas Totales (Periodo)", f"${info_producto['Volumen_Venta']:,.0f}", help="Ventas totales en el periodo y enfoque seleccionados.")
    kpi2.metric("Margen Bruto (Periodo)", f"${info_producto['Margen_Absoluto']:,.0f}")
    kpi3.metric("Rentabilidad Media", f"{info_producto['Rentabilidad_Pct']:.1f}%")
    kpi4.metric("Nº Clientes Únicos", f"{info_producto['Popularidad']}")

    c1, c2 = st.columns(2)
    with c1:
        compradores = df_producto_ventas.groupby('nombre_cliente')['valor_venta'].sum().nlargest(10).sort_values()
        if not compradores.empty:
            fig_compradores = px.bar(compradores, x=compradores.values, y=compradores.index, orientation='h',
                                     title=f"Top 10 Compradores de {producto_sel}",
                                     labels={'x': 'Ventas ($)', 'y': 'Cliente'})
            fig_compradores.update_layout(yaxis_title="")
            st.plotly_chart(fig_compradores, use_container_width=True)
        else:
            st.info("No hay datos de compradores para este producto en el periodo.")

    with c2:
        df_producto_ventas['fecha_venta'] = pd.to_datetime(df_producto_ventas['fecha_venta'])
        tendencia = df_producto_ventas.set_index('fecha_venta').resample('ME')['valor_venta'].sum()
        if not tendencia.empty:
            fig_tendencia = px.line(tendencia, x=tendencia.index, y='valor_venta',
                                    title=f"Tendencia de Ventas Mensuales", markers=True,
                                    labels={'valor_venta': 'Ventas ($)', 'fecha_venta': 'Mes'})
            fig_tendencia.update_layout(yaxis_title="Ventas ($)", xaxis_title="Mes")
            st.plotly_chart(fig_tendencia, use_container_width=True)
        else:
            st.info("No hay datos de tendencia para este producto en el periodo.")

def render_tab_plan_accion(df_analisis: pd.DataFrame, df_reglas: pd.DataFrame, df_ventas: pd.DataFrame):
    st.header("✍️ Plan de Acción Personalizado")
    st.info("Recomendaciones automáticas y específicas generadas a partir de tus datos. ¡Úsalas para preparar tus próximas visitas!")
    
    recomendaciones = []

    # 1. Explotar Gemas Ocultas
    df_gemas = df_analisis[df_analisis['Cuadrante'] == '💎 De Nicho (Gemas Ocultas)'].nlargest(2, 'Rentabilidad_Pct')
    if not df_gemas.empty:
        recomendaciones.append("### 💎 Explotar Gemas Ocultas (Alta Rentabilidad, Baja Popularidad)")
        for _, row in df_gemas.iterrows():
            recomendaciones.append(f"- **Oportunidad de Nicho:** **{row['nombre_articulo']}** es muy rentable ({row['Rentabilidad_Pct']:.1f}%) pero pocos lo compran. **Acción:** Identifica el perfil de los {row['Popularidad']} clientes que ya lo compran y ofrécelo a clientes similares.")

    # 2. Impulsar Venta Cruzada
    if not df_reglas.empty:
        recomendaciones.append("### 🔗 Impulsar Venta Cruzada (Cross-Selling)")
        for _, top_regla in df_reglas.head(2).iterrows():
            recomendaciones.append(f"- **Recomendación Directa:** Cuando un cliente compre **{top_regla['Si el cliente compra...']}**, ofrécele **{top_regla['Recomendar también...']}**. Esta combinación tiene una confianza del **{top_regla['Confianza']:.0%}** y un potencial de **{top_regla['Potencial']:.1f}x**.")

    # 3. Cerrar Brechas en Clientes Clave
    clientes_top = df_ventas.groupby('nombre_cliente')['valor_venta'].sum().nlargest(5).index
    productos_lideres = df_analisis[df_analisis['Cuadrante'] == '⭐ Líderes']['nombre_articulo'].unique()
    if len(productos_lideres) > 0 and not clientes_top.empty:
        matriz_penetracion = pd.crosstab(
            df_ventas['nombre_cliente'], df_ventas['nombre_articulo']
        ).reindex(index=clientes_top, columns=productos_lideres, fill_value=0)
        
        oportunidades = matriz_penetracion[matriz_penetracion == 0].stack().reset_index()
        if not oportunidades.empty:
            recomendaciones.append("### 🎯 Cerrar Brechas en Clientes Clave")
            oportunidades.columns = ['nombre_cliente', 'nombre_articulo', '_']
            oportunidad_top = oportunidades.iloc[np.random.randint(0, len(oportunidades))] # Tomar una al azar
            recomendaciones.append(f"- **Oportunidad Inmediata:** Tu cliente clave **{oportunidad_top['nombre_cliente']}** aún no compra tu producto líder **'{oportunidad_top['nombre_articulo']}'**. ¡Prepárale una oferta!")

    # 4. Gestionar Productos con Bajo Margen
    df_potenciales = df_analisis[df_analisis['Cuadrante'] == '🤔 Potenciales (Bajo Margen)'].nsmallest(2, 'Rentabilidad_Pct')
    if not df_potenciales.empty:
        recomendaciones.append("### 🤔 Mejorar Margen de Productos Populares")
        for _, row in df_potenciales.iterrows():
            recomendaciones.append(f"- **Revisión de Precio/Costo:** El producto **{row['nombre_articulo']}** es popular (comprado por {row['Popularidad']} clientes) pero su rentabilidad es baja ({row['Rentabilidad_Pct']:.1f}%). **Acción:** Analiza si es posible ajustar el precio o negociar un mejor costo.")

    if not recomendaciones:
        st.success("✅ ¡Excelente rendimiento! No se han identificado acciones críticas inmediatas. Explora las pestañas para encontrar oportunidades de optimización.")
    else:
        for i, punto in enumerate(recomendaciones):
            st.markdown(punto)
            if i < len(recomendaciones) - 1:
                st.markdown("---")

# ==============================================================================
# SECCIÓN 3: ORQUESTADOR PRINCIPAL DE LA PÁGINA
# ==============================================================================

def main():
    st.title("🚀 Inteligencia de Portafolio y Acciones Comerciales v4.0")

    if 'df_ventas' not in st.session_state or st.session_state.df_ventas.empty:
        st.error("❌ No se han cargado los datos de ventas. Por favor, ve a la página principal y carga los datos primero.")
        st.stop()
        
    df_ventas_historicas = st.session_state.df_ventas
    mapeo_meses = st.session_state.get('DATA_CONFIG', {}).get('mapeo_meses', {i: str(i) for i in range(1, 13)})

    # --- FILTROS EN EL SIDEBAR ---
    st.sidebar.header("🗓️ Filtros de Análisis")
    lista_anios = sorted(df_ventas_historicas['anio'].unique(), reverse=True)
    anio_sel = st.sidebar.selectbox("Año", lista_anios, key="sel_anio_acc")
    
    meses_disponibles = ["Todo el año"] + sorted(df_ventas_historicas[df_ventas_historicas['anio'] == anio_sel]['mes'].unique())
    mes_sel = st.sidebar.selectbox("Mes", meses_disponibles, 
        format_func=lambda x: "Todo el año" if x == "Todo el año" else mapeo_meses.get(x, "N/A"), 
        key="sel_mes_acc")
    
    vendedores_unicos = ["Visión General"] + sorted(df_ventas_historicas['nomvendedor'].dropna().unique())
    enfoque_sel = st.sidebar.selectbox("Enfoque (Vendedor)", vendedores_unicos, key="sel_enfoque_acc")

    # --- EJECUCIÓN DEL ANÁLISIS (USANDO CACHÉ) ---
    with st.spinner("🧠 Ejecutando análisis avanzados... Esto puede tardar un momento la primera vez."):
        df_filtrado, df_analisis_productos, df_reglas_asociacion = run_full_analysis(
            df_ventas_historicas, anio_sel, mes_sel, enfoque_sel
        )

    if df_filtrado.empty:
        periodo_str = f'{"Todo el año" if mes_sel == "Todo el año" else mapeo_meses.get(mes_sel)} {anio_sel}'
        st.warning(f"No se encontraron datos para la selección: **{enfoque_sel}** en **{periodo_str}**.")
        st.stop()
    
    # --- KPIs GLOBALES ---
    st.markdown("---")
    st.subheader("📊 Resumen del Periodo Seleccionado")
    total_ventas = df_filtrado['valor_venta'].sum()
    total_margen = df_analisis_productos['Margen_Absoluto'].sum()
    num_clientes = df_filtrado['cliente_id'].nunique()
    num_productos = df_filtrado['codigo_articulo'].nunique()

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Ventas Totales", f"${total_ventas:,.0f}")
    kpi2.metric("Margen Bruto Total", f"${total_margen:,.0f}")
    kpi3.metric("Clientes Activos", f"{num_clientes}")
    kpi4.metric("Productos Vendidos", f"{num_productos}")
    st.markdown("---")
    
    # --- PESTAÑAS DE NAVEGACIÓN ---
    periodo_str = f'{"Todo el año" if mes_sel == "Todo el año" else mapeo_meses.get(mes_sel)} {anio_sel}'
    
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
    main()
