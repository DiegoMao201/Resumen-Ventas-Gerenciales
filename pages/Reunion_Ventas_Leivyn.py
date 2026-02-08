import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTILOS CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Tablero Gerencial Ferreinox SAS BIC",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Paleta de Colores Corporativa (Sobria y Profesional)
COLOR_PALETTE = {
    'primary': '#0e1117',
    'positive': '#2E8B57',  # Sea Green
    'negative': '#CD5C5C',  # Indian Red
    'neutral': '#708090',   # Slate Gray
    'highlight': '#4682B4', # Steel Blue
    'background': '#F0F2F6'
}

st.markdown("""
<style>
    /* Estilo General */
    .main { background-color: #FAFAFA; }
    h1 { color: #1f2c39; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    h2, h3 { color: #2c3e50; font-family: 'Helvetica Neue', sans-serif; }
    
    /* Tarjetas de Métricas (KPIs) */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    div[data-testid="stMetricLabel"] { font-size: 14px; color: #666; }
    div[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; color: #0e1117; }
    
    /* Contenedores */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4682B4;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. PROCESAMIENTO DE DATOS AVANZADO
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("analisis_2025.xlsx")
    except FileNotFoundError:
        st.error("⚠️ No se encontró el archivo 'analisis_2025.xlsx'. Por favor cárguelo en el directorio.")
        return pd.DataFrame()

    df.columns = df.columns.str.strip()
    
    # Mapeo y Normalización
    rename_dict = {
        'Vendedores': 'Vendedor',
        'Importe 2025': 'Venta_2025',
        'Importe 2024': 'Venta_2024',
        'CLIENTES_DESCODIFICADO': 'Clientes_Perdidos',
        'VALOR_DESCODIFICADOS': 'Valor_Perdidos',
        'CLIENTES_NUEVO': 'Clientes_Nuevos',
        'VALOR_NUEVOS': 'Valor_Nuevos',
        'CLIENTES_REACTIVADO': 'Clientes_Reactivados',
        'VALOR_REACTIVADO': 'Valor_Reactivados',
        'VARIACION_CLIENTES_#CREC': 'Clientes_Crecen',
        'VALOR_CLIENTES_CRECEN': 'Valor_Crecimiento',
        'CLIENTE_#DECREC': 'Clientes_Decrecen',
        'VALOR_CLIENTE_DECRECE': 'Valor_Decrecimiento',
        'TOTAL CLIENTE': 'Total_Clientes'
    }
    
    df = df.rename(columns={k: v for k, v in rename_dict.items() if k in df.columns})
    
    # Limpieza Numérica
    numeric_cols = [
        'Venta_2025', 'Venta_2024', 'Valor_Perdidos', 'Valor_Nuevos', 
        'Valor_Reactivados', 'Valor_Crecimiento', 'Valor_Decrecimiento',
        'Clientes_Nuevos', 'Clientes_Perdidos', 'Clientes_Reactivados'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # Filtrado Básico
    df = df.dropna(subset=['Vendedor'])
    df = df[~df['Vendedor'].astype(str).str.upper().isin(['TOTAL', 'NAN', 'NONE'])]
    
    # --- CÁLCULOS DE BI AVANZADOS ---
    
    # 1. Variación Neta
    df['Variacion_Neta'] = df['Venta_2025'] - df['Venta_2024']
    df['Variacion_Pct'] = (df['Variacion_Neta'] / df['Venta_2024']).replace([float('inf'), -float('inf')], 0).fillna(0) * 100
    
    # 2. Clasificación de Impacto (Churn vs Growth)
    df['Ganancia_Bruta'] = df['Valor_Nuevos'] + df['Valor_Reactivados'] + df['Valor_Crecimiento']
    df['Perdida_Bruta'] = df['Valor_Perdidos'] + df['Valor_Decrecimiento'] # Normalmente son positivos en la celda, los trataremos como resta visualmente
    
    # 3. Categorización de Vendedor (Pareto)
    df = df.sort_values('Venta_2025', ascending=False)
    df['Acumulado_Venta'] = df['Venta_2025'].cumsum()
    df['Pct_Acumulado'] = (df['Acumulado_Venta'] / df['Venta_2025'].sum()) * 100
    df['Categoria_Pareto'] = df['Pct_Acumulado'].apply(lambda x: 'A (Top 80%)' if x <= 80 else 'B (Cola 20%)')

    return df

df = load_data()

if df.empty:
    st.stop()

# -----------------------------------------------------------------------------
# 3. BARRA LATERAL (CONTROLES)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://raw.githubusercontent.com/DiegoMao2021/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", use_container_width=True)
    st.header("⚙️ Configuración")
    
    # Filtros
    vendedores = sorted(df['Vendedor'].unique())
    selected_sellers = st.multiselect("Filtrar Vendedores:", vendedores, default=vendedores)
    
    if not selected_sellers:
        st.warning("Seleccione al menos un vendedor.")
        st.stop()
        
    df_filtered = df[df['Vendedor'].isin(selected_sellers)]
    
    st.markdown("---")
    st.markdown("### 📥 Exportar Datos")
    csv = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar Reporte CSV", data=csv, file_name="reporte_gerencial_2025.csv", mime="text/csv")
    
    st.info(f"Mostrando {len(df_filtered)} registros.")
    st.caption("Desarrollado para Ferreinox SAS BIC v2.0")

# -----------------------------------------------------------------------------
# 4. ENCABEZADO Y KPIs PRINCIPALES
# -----------------------------------------------------------------------------
st.title("🚀 Tablero de Dirección Estratégica")
st.markdown(f"**Periodo de Análisis:** 2024 vs 2025 | **Última Actualización:** {pd.Timestamp.now().strftime('%Y-%m-%d')}")

# Cálculos Totales
total_2025 = df_filtered['Venta_2025'].sum()
total_2024 = df_filtered['Venta_2024'].sum()
diff_abs = total_2025 - total_2024
diff_pct = (diff_abs / total_2024) * 100 if total_2024 != 0 else 0

# KPIs Layout
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.metric("Facturación 2025", f"${total_2025:,.0f}", f"{diff_pct:+.1f}%", delta_color="normal")
with kpi2:
    st.metric("Facturación 2024", f"${total_2024:,.0f}", "Base Comparativa", delta_color="off")
with kpi3:
    net_color = "normal" if diff_abs >= 0 else "inverse"
    st.metric("Variación Neta", f"${diff_abs:,.0f}", "Impacto en Caja", delta_color=net_color)
with kpi4:
    # Eficiencia: Promedio por vendedor
    avg_sale = df_filtered['Venta_2025'].mean()
    st.metric("Promedio/Vendedor", f"${avg_sale:,.0f}", "KPI Eficiencia")
with kpi5:
    # Clientes Nuevos Totales
    total_new_clients = df_filtered['Clientes_Nuevos'].sum()
    st.metric("Clientes Captados", int(total_new_clients), "Nuevos + Reactivados")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. PESTAÑAS DE ANÁLISIS
# -----------------------------------------------------------------------------
tab_exec, tab_comm, tab_deep, tab_data = st.tabs([
    "📊 Visión Ejecutiva (Waterfall)", 
    "🏆 Desempeño Comercial", 
    "🔍 Dinámica de Clientes", 
    "📑 Base de Datos"
])

# --- TAB 1: VISIÓN EJECUTIVA (EL PUENTE DE VENTAS) ---
with tab_exec:
    st.subheader("Puente de Resultados: ¿Cómo llegamos a la cifra de 2025?")
    st.write("Este gráfico desglosa los componentes positivos y negativos que construyen el resultado final.")
    
    # Preparar datos para Waterfall
    sum_2024 = df_filtered['Venta_2024'].sum()
    sum_nuevos = df_filtered['Valor_Nuevos'].sum()
    sum_react = df_filtered['Valor_Reactivados'].sum()
    sum_crec = df_filtered['Valor_Crecimiento'].sum()
    sum_decrec = -abs(df_filtered['Valor_Decrecimiento'].sum()) # Negativo
    sum_perds = -abs(df_filtered['Valor_Perdidos'].sum()) # Negativo
    
    # Ajuste matemático (por si hay decimales sueltos, el final debe cuadrar)
    calculated_2025 = sum_2024 + sum_nuevos + sum_react + sum_crec + sum_decrec + sum_perds
    
    fig_waterfall = go.Figure(go.Waterfall(
        name = "20", orientation = "v",
        measure = ["relative", "relative", "relative", "relative", "relative", "relative", "total"],
        x = ["Ventas 2024", "Nuevos", "Reactivados", "Crecimiento Clientes", "Decrecimiento Clientes", "Clientes Perdidos", "Ventas 2025"],
        textposition = "outside",
        text = [f"${x/1e6:,.1f}M" for x in [sum_2024, sum_nuevos, sum_react, sum_crec, sum_decrec, sum_perds, calculated_2025]],
        y = [sum_2024, sum_nuevos, sum_react, sum_crec, sum_decrec, sum_perds, 0], # El último es calculado automático por Plotly si es 'total' pero a veces falla, mejor dejar que plotly calcule
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
        decreasing = {"marker":{"color":COLOR_PALETTE['negative']}},
        increasing = {"marker":{"color":COLOR_PALETTE['positive']}},
        totals = {"marker":{"color":COLOR_PALETTE['highlight']}}
    ))
    
    fig_waterfall.update_layout(
        title="Bridge de Variación de Ventas (YoY)",
        showlegend = False,
        height=500,
        yaxis=dict(title="Valor Monetario", showgrid=True, gridcolor='#eee'),
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_waterfall, use_container_width=True)
    
    # Análisis de Texto Automático
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.info(f"""
        **Análisis de Captación:**
        La empresa generó **${sum_nuevos+sum_react:,.0f}** a través de Nuevos y Reactivados. 
        Esto representa un **{((sum_nuevos+sum_react)/sum_2024)*100:.1f}%** sobre la base del 2024.
        """)
    with col_t2:
        st.warning(f"""
        **Análisis de Fuga:**
        Se perdieron **${abs(sum_perds+sum_decrec):,.0f}** por descodificaciones y decrecimiento.
        Es vital revisar la retención en los clientes top.
        """)

# --- TAB 2: DESEMPEÑO COMERCIAL ---
with tab_comm:
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Ranking de Facturación 2025")
        # Gráfico de Barras con Colores Condicionales
        df_sorted = df_filtered.sort_values('Venta_2025', ascending=True) # Ascendente para gráfico horizontal
        
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=df_sorted['Vendedor'],
            x=df_sorted['Venta_2025'],
            orientation='h',
            marker=dict(
                color=df_sorted['Venta_2025'],
                colorscale='Blues',
                showscale=False
            ),
            text=df_sorted['Venta_2025'].apply(lambda x: f"${x/1e6:,.1f}M"),
            textposition='auto'
        ))
        fig_bar.update_layout(
            height=600,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_title="Volumen de Ventas ($)",
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with c2:
        st.subheader("Top Performers (Pareto)")
        pareto_df = df_filtered[df_filtered['Categoria_Pareto'].str.contains('A')]
        st.write(f"**{len(pareto_df)} Vendedores** generan el **80%** de la venta.")
        st.dataframe(
            pareto_df[['Vendedor', 'Venta_2025', 'Variacion_Pct']].sort_values('Venta_2025', ascending=False),
            column_config={
                "Venta_2025": st.column_config.ProgressColumn(
                    "Ventas",
                    format="$%d",
                    min_value=0,
                    max_value=df_filtered['Venta_2025'].max(),
                ),
                "Variacion_Pct": st.column_config.NumberColumn(
                    "% Var",
                    format="%.1f%%"
                )
            },
            hide_index=True
        )

# --- TAB 3: DINÁMICA DE CLIENTES ---
with tab_deep:
    st.subheader("Matriz de Oportunidad: Crecimiento vs. Volumen")
    st.markdown("Identificación de vendedores con **Alto Potencial** (Crecen mucho, venden poco) vs **Vacas Lecheras** (Venden mucho, crecen poco).")
    
    fig_scatter = px.scatter(
        df_filtered,
        x="Venta_2025",
        y="Variacion_Pct",
        size="Ganancia_Bruta",
        color="Vendedor",
        hover_name="Vendedor",
        text="Vendedor",
        labels={"Venta_2025": "Volumen de Ventas ($)", "Variacion_Pct": "% Crecimiento Real"},
        height=550
    )
    
    # Líneas Promedio
    avg_growth = df_filtered['Variacion_Pct'].mean()
    avg_vol = df_filtered['Venta_2025'].mean()
    
    fig_scatter.add_hline(y=avg_growth, line_dash="dot", line_color="red", annotation_text="Promedio Crecimiento")
    fig_scatter.add_vline(x=avg_vol, line_dash="dot", line_color="blue", annotation_text="Promedio Ventas")
    
    fig_scatter.update_traces(textposition='top center')
    fig_scatter.update_layout(showlegend=False, plot_bgcolor='#f4f4f4')
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    st.markdown("### 🚦 Desglose Detallado por Vendedor")
    
    # Heatmap style table logic via Pandas Styler es dificil en streamlit, usamos métricas visuales
    selected_drilldown = st.selectbox("Seleccione Vendedor para Rayos X:", df_filtered['Vendedor'].unique())
    seller_data = df_filtered[df_filtered['Vendedor'] == selected_drilldown].iloc[0]
    
    col_d1, col_d2, col_d3 = st.columns(3)
    
    # Gráfico de Torta para composición
    labels = ['Nuevos/Reactivados', 'Crecimiento Cartera', 'Retención (Base)']
    # Aproximación: Lo que vendió en 2024 menos lo que perdió, es la base retenida
    base_retenida = max(0, seller_data['Venta_2024'] - abs(seller_data['Valor_Perdidos']) - abs(seller_data['Valor_Decrecimiento']))
    ganancia_nueva = seller_data['Valor_Nuevos'] + seller_data['Valor_Reactivados']
    crecimiento_existente = seller_data['Valor_Crecimiento']
    
    values = [ganancia_nueva, crecimiento_existente, base_retenida]
    
    fig_donut = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.5)])
    fig_donut.update_layout(title=f"Mix de Venta: {selected_drilldown}", height=300, margin=dict(t=30, b=0, l=0, r=0))
    
    col_d1.plotly_chart(fig_donut, use_container_width=True)
    
    with col_d2:
        st.write("#### 📈 Captación")
        st.write(f"**Clientes Nuevos:** {int(seller_data['Clientes_Nuevos'])}")
        st.write(f"**Valor Nuevos:** ${seller_data['Valor_Nuevos']:,.0f}")
        st.progress(min(1.0, seller_data['Valor_Nuevos'] / (seller_data['Venta_2025']+1)))
        
        st.write(f"**Clientes Reactivados:** {int(seller_data['Clientes_Reactivados'])}")
        st.write(f"**Valor Reactivados:** ${seller_data['Valor_Reactivados']:,.0f}")
        
    with col_d3:
        st.write("#### 📉 Fugas")
        st.write(f"**Clientes Perdidos:** {int(seller_data['Clientes_Perdidos'])}")
        st.write(f"**Valor Perdido:** ${seller_data['Valor_Perdidos']:,.0f}")
        val_loss_norm = abs(seller_data['Valor_Perdidos']) / (seller_data['Venta_2024'] + 1)
        st.progress(min(1.0, val_loss_norm))
        st.caption("Barra indica % de pérdida respecto al año anterior")

# --- TAB 4: DATA COMPLETA ---
with tab_data:
    st.subheader("Base de Datos Maestra")
    st.markdown("Utilice esta tabla para auditoría y revisión granular.")
    
    # Configuración de columnas para visualización pro
    st.dataframe(
        df_filtered,
        column_order=("Vendedor", "Venta_2024", "Venta_2025", "Variacion_Pct", "Clientes_Nuevos", "Valor_Perdidos"),
        column_config={
            "Vendedor": st.column_config.TextColumn("Ejecutivo"),
            "Venta_2024": st.column_config.NumberColumn("2024", format="$%d"),
            "Venta_2025": st.column_config.NumberColumn("2025", format="$%d"),
            "Variacion_Pct": st.column_config.NumberColumn("Var %", format="%.1f%%"),
            "Valor_Perdidos": st.column_config.NumberColumn("Fuga ($)", format="$%d"),
            "Clientes_Nuevos": st.column_config.NumberColumn("# New", help="Cantidad de clientes nuevos")
        },
        use_container_width=True,
        height=600
    )

# -----------------------------------------------------------------------------
# 6. PIE DE PÁGINA
# -----------------------------------------------------------------------------
st.markdown("---")
col_footer1, col_footer2 = st.columns([3, 1])
with col_footer1:
    st.markdown("**Ferreinox SAS BIC** | Tablero de Inteligencia Comercial | Confidencial")
with col_footer2:
    if st.button("🔄 Actualizar Datos"):
        st.cache_data.clear()
        st.rerun()