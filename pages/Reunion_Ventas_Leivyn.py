import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTILOS CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Tablero Gerencial Ferreinox SAS BIC - Master Edition",
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
    'gold': '#DAA520',      # Goldenrod para Estrellas
    'background': '#F0F2F6'
}

st.markdown("""
<style>
    /* Estilo General */
    .main { background-color: #FAFAFA; }
    h1 { color: #1f2c39; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    h2, h3, h4 { color: #2c3e50; font-family: 'Helvetica Neue', sans-serif; }
    
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
        background-color: #1f2c39;
        color: white;
    }
    
    /* Alertas personalizadas */
    .insight-box {
        padding: 15px;
        border-left: 5px solid #4682B4;
        background-color: #eef4f9;
        margin-bottom: 10px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. PROCESAMIENTO DE DATOS AVANZADO
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    try:
        # Intentar cargar, si no existe crea un dummy para que el usuario vea el ejemplo
        df = pd.read_excel("analisis_2025.xlsx")
    except FileNotFoundError:
        st.error("⚠️ No se encontró 'analisis_2025.xlsx'. Usando datos simulados para demostración.")
        # DATOS SIMULADOS PARA QUE EL CÓDIGO NO FALLE SI NO TIENES EL EXCEL
        data = {
            'Vendedor': [f'Vendedor {i}' for i in range(1, 21)],
            'Importe 2025': np.random.randint(50000000, 500000000, 20),
            'Importe 2024': np.random.randint(40000000, 450000000, 20),
            'CLIENTES_NUEVO': np.random.randint(0, 15, 20),
            'VALOR_NUEVOS': np.random.randint(1000000, 50000000, 20),
            'VALOR_DESCODIFICADOS': np.random.randint(0, 30000000, 20),
            'TOTAL CLIENTE': np.random.randint(20, 150, 20)
        }
        data['CLIENTES_REACTIVADO'] = np.random.randint(0, 5, 20)
        data['VALOR_REACTIVADO'] = np.random.randint(0, 10000000, 20)
        data['VALOR_CLIENTES_CRECEN'] = np.random.randint(10000000, 100000000, 20)
        data['VALOR_CLIENTE_DECRECE'] = np.random.randint(0, 50000000, 20)
        data['CLIENTES_DESCODIFICADO'] = np.random.randint(0, 10, 20)
        
        df = pd.DataFrame(data)

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
        'Clientes_Nuevos', 'Clientes_Perdidos', 'Clientes_Reactivados', 'Total_Clientes'
    ]
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0 # Crear columna en 0 si no existe para evitar errores
            
    # Filtrado Básico
    df = df.dropna(subset=['Vendedor'])
    df = df[~df['Vendedor'].astype(str).str.upper().isin(['TOTAL', 'NAN', 'NONE'])]
    
    # --- CÁLCULOS DE BI BÁSICOS ---
    df['Variacion_Neta'] = df['Venta_2025'] - df['Venta_2024']
    df['Variacion_Pct'] = (df['Variacion_Neta'] / df['Venta_2024']).replace([float('inf'), -float('inf')], 0).fillna(0) * 100
    
    df['Ganancia_Bruta'] = df['Valor_Nuevos'] + df['Valor_Reactivados'] + df['Valor_Crecimiento']
    df['Perdida_Bruta'] = df['Valor_Perdidos'] + df['Valor_Decrecimiento']
    
    # Pareto
    df = df.sort_values('Venta_2025', ascending=False)
    df['Acumulado_Venta'] = df['Venta_2025'].cumsum()
    df['Pct_Acumulado'] = (df['Acumulado_Venta'] / df['Venta_2025'].sum()) * 100
    df['Categoria_Pareto'] = df['Pct_Acumulado'].apply(lambda x: 'A (Top 80%)' if x <= 80 else 'B (Cola 20%)')
    
    # --- CÁLCULOS AVANZADOS PARA LA SUPER PESTAÑA ---
    
    # 1. Ticket Promedio (Aproximación)
    # Evitar división por cero
    df['Ticket_Promedio_2025'] = np.where(df['Total_Clientes'] > 0, df['Venta_2025'] / df['Total_Clientes'], 0)
    
    # Para 2024 estimamos clientes anteriores (Total Actual - Nuevos + Perdidos) - Aprox
    df['Clientes_2024_Est'] = df['Total_Clientes'] - df['Clientes_Nuevos'] + df['Clientes_Perdidos']
    df['Clientes_2024_Est'] = df['Clientes_2024_Est'].replace(0, 1) # Evitar div/0
    df['Ticket_Promedio_2024'] = df['Venta_2024'] / df['Clientes_2024_Est']

    return df

df = load_data()

if df.empty:
    st.stop()

# -----------------------------------------------------------------------------
# 3. BARRA LATERAL (CONTROLES)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Ferreinox SAS BIC")
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
    
    st.caption("v3.0 - Mastermind Analytic Engine")

# -----------------------------------------------------------------------------
# 4. ENCABEZADO Y KPIs PRINCIPALES
# -----------------------------------------------------------------------------
st.title("🚀 Tablero de Dirección Estratégica")
st.markdown(f"**Periodo de Análisis:** 2024 vs 2025 | **Data Points:** {len(df_filtered)}")

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
    avg_sale = df_filtered['Venta_2025'].mean()
    st.metric("Promedio/Vendedor", f"${avg_sale:,.0f}", "KPI Eficiencia")
with kpi5:
    total_new_clients = df_filtered['Clientes_Nuevos'].sum()
    st.metric("Clientes Captados", int(total_new_clients), "Nuevos + Reactivados")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. PESTAÑAS DE ANÁLISIS
# -----------------------------------------------------------------------------
tab_exec, tab_comm, tab_deep, tab_master = st.tabs([
    "📊 Visión Ejecutiva (Waterfall)", 
    "🏆 Desempeño Comercial", 
    "🔍 Dinámica de Clientes", 
    "💎 Mastermind Estratégico (AVANZADO)"
])

# --- TAB 1: VISIÓN EJECUTIVA (EL PUENTE DE VENTAS) ---
with tab_exec:
    st.subheader("Puente de Resultados: ¿Cómo llegamos a la cifra de 2025?")
    
    sum_2024 = df_filtered['Venta_2024'].sum()
    sum_nuevos = df_filtered['Valor_Nuevos'].sum()
    sum_react = df_filtered['Valor_Reactivados'].sum()
    sum_crec = df_filtered['Valor_Crecimiento'].sum()
    sum_decrec = -abs(df_filtered['Valor_Decrecimiento'].sum()) 
    sum_perds = -abs(df_filtered['Valor_Perdidos'].sum())
    
    calculated_2025 = sum_2024 + sum_nuevos + sum_react + sum_crec + sum_decrec + sum_perds
    
    fig_waterfall = go.Figure(go.Waterfall(
        name = "20", orientation = "v",
        measure = ["relative", "relative", "relative", "relative", "relative", "relative", "total"],
        x = ["Ventas 2024", "Nuevos", "Reactivados", "Crecimiento Clientes", "Decrecimiento Clientes", "Clientes Perdidos", "Ventas 2025"],
        textposition = "outside",
        text = [f"${x/1e6:,.1f}M" for x in [sum_2024, sum_nuevos, sum_react, sum_crec, sum_decrec, sum_perds, calculated_2025]],
        y = [sum_2024, sum_nuevos, sum_react, sum_crec, sum_decrec, sum_perds, 0],
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
        decreasing = {"marker":{"color":COLOR_PALETTE['negative']}},
        increasing = {"marker":{"color":COLOR_PALETTE['positive']}},
        totals = {"marker":{"color":COLOR_PALETTE['highlight']}}
    ))
    
    fig_waterfall.update_layout(title="Bridge de Variación de Ventas (YoY)", showlegend = False, height=500)
    st.plotly_chart(fig_waterfall, use_container_width=True)

# --- TAB 2: DESEMPEÑO COMERCIAL ---
with tab_comm:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Ranking de Facturación 2025")
        df_sorted = df_filtered.sort_values('Venta_2025', ascending=True)
        fig_bar = go.Figure(go.Bar(
            y=df_sorted['Vendedor'], x=df_sorted['Venta_2025'], orientation='h',
            marker=dict(color=df_sorted['Venta_2025'], colorscale='Blues', showscale=False),
            text=df_sorted['Venta_2025'].apply(lambda x: f"${x/1e6:,.1f}M"), textposition='auto'
        ))
        fig_bar.update_layout(height=600, xaxis_title="Volumen de Ventas ($)")
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with c2:
        st.subheader("Top Performers (Pareto)")
        pareto_df = df_filtered[df_filtered['Categoria_Pareto'].str.contains('A')]
        st.write(f"**{len(pareto_df)} Vendedores** generan el **80%** de la venta.")
        st.dataframe(
            pareto_df[['Vendedor', 'Venta_2025']].sort_values('Venta_2025', ascending=False),
            hide_index=True, use_container_width=True
        )

# --- TAB 3: DINÁMICA DE CLIENTES ---
with tab_deep:
    st.subheader("Matriz de Oportunidad")
    fig_scatter = px.scatter(
        df_filtered, x="Venta_2025", y="Variacion_Pct", size="Ganancia_Bruta",
        color="Vendedor", hover_name="Vendedor",
        labels={"Venta_2025": "Volumen ($)", "Variacion_Pct": "% Crecimiento"}, height=550
    )
    avg_growth = df_filtered['Variacion_Pct'].mean()
    avg_vol = df_filtered['Venta_2025'].mean()
    fig_scatter.add_hline(y=avg_growth, line_dash="dot", line_color="red")
    fig_scatter.add_vline(x=avg_vol, line_dash="dot", line_color="blue")
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    st.markdown("### 🚦 Desglose por Vendedor")
    sel = st.selectbox("Seleccione Vendedor:", df_filtered['Vendedor'].unique())
    s_data = df_filtered[df_filtered['Vendedor'] == sel].iloc[0]
    
    col_d1, col_d2, col_d3 = st.columns(3)
    base_ret = max(0, s_data['Venta_2024'] - abs(s_data['Valor_Perdidos']) - abs(s_data['Valor_Decrecimiento']))
    fig_donut = go.Figure(data=[go.Pie(labels=['Nuevos', 'Crecimiento', 'Retención'], values=[s_data['Valor_Nuevos']+s_data['Valor_Reactivados'], s_data['Valor_Crecimiento'], base_ret], hole=.5)])
    fig_donut.update_layout(height=250, margin=dict(t=0,b=0))
    col_d1.plotly_chart(fig_donut, use_container_width=True)
    col_d2.metric("Captación ($)", f"${s_data['Valor_Nuevos']+s_data['Valor_Reactivados']:,.0f}")
    col_d3.metric("Fuga ($)", f"${s_data['Valor_Perdidos']:,.0f}")

# --- TAB 4: MASTERMIND ESTRATÉGICO (LA SUPER PESTAÑA) ---
with tab_master:
    st.markdown("## 🧠 Centro de Inteligencia Comercial Avanzada")
    st.markdown("Analítica profunda para toma de decisiones de alto nivel. Modelos teóricos aplicados a datos reales.")
    
    # --- SECCIÓN 1: MATRIZ ESTRATÉGICA (CUADRANTES BCG ADAPTADOS) ---
    st.markdown("### 1. Matriz de Posicionamiento Estratégico (Cuota vs. Crecimiento)")
    st.write("Clasificación teórica de la fuerza de ventas basada en su cuota de mercado relativa (dentro de la empresa) y su dinamismo.")
    
    # Preparación de datos BCG
    max_venta = df_filtered['Venta_2025'].max()
    df_filtered['Cuota_Relativa'] = df_filtered['Venta_2025'] / max_venta # Ratio respecto al líder
    
    # Definir Cuadrantes
    median_share = df_filtered['Cuota_Relativa'].median()
    median_growth = df_filtered['Variacion_Pct'].median()
    
    fig_bcg = px.scatter(
        df_filtered,
        x="Cuota_Relativa",
        y="Variacion_Pct",
        size="Venta_2025",
        color="Categoria_Pareto", # Color por importancia Pareto
        hover_name="Vendedor",
        text="Vendedor",
        color_discrete_map={'A (Top 80%)': '#FFD700', 'B (Cola 20%)': '#A9A9A9'},
        labels={"Cuota_Relativa": "Participación Relativa (vs Líder)", "Variacion_Pct": "Tasa de Crecimiento Anual"},
        title="Matriz de Desempeño"
    )
    
    # Dibujar Cuadrantes
    fig_bcg.add_hline(y=median_growth, line_color="gray", line_dash="dash")
    fig_bcg.add_vline(x=median_share, line_color="gray", line_dash="dash")
    
    # Anotaciones de Cuadrantes
    fig_bcg.add_annotation(x=max(df_filtered['Cuota_Relativa']), y=max(df_filtered['Variacion_Pct']), text="⭐ ESTRELLAS (Alto Vol/Alto Crec)", showarrow=False, font=dict(color="green"))
    fig_bcg.add_annotation(x=0.1, y=max(df_filtered['Variacion_Pct']), text="❓ INTERROGANTES (Bajo Vol/Alto Crec)", showarrow=False, font=dict(color="orange"))
    fig_bcg.add_annotation(x=max(df_filtered['Cuota_Relativa']), y=min(df_filtered['Variacion_Pct']), text="🐮 VACAS (Alto Vol/Bajo Crec)", showarrow=False, font=dict(color="blue"))
    fig_bcg.add_annotation(x=0.1, y=min(df_filtered['Variacion_Pct']), text="🐕 PERROS (Bajo Vol/Bajo Crec)", showarrow=False, font=dict(color="red"))
    
    fig_bcg.update_traces(textposition='top center')
    fig_bcg.update_layout(height=600, plot_bgcolor='#f9f9f9')
    st.plotly_chart(fig_bcg, use_container_width=True)
    
    # --- SECCIÓN 2: DESCOMPOSICIÓN DEL CRECIMIENTO (VECTORIAL) ---
    st.markdown("---")
    st.markdown("### 2. Descomposición Vectorial del Crecimiento (Price vs. Volume Effect)")
    st.write("¿El crecimiento se debe a que vendemos más caro (Efecto Ticket) o a que traemos más clientes (Efecto Tráfico)?")
    
    # Lógica Matemática:
    # Var Venta = (Var Clientes * Ticket Anterior) + (Var Ticket * Clientes Actuales)
    
    decomp_data = []
    for index, row in df_filtered.iterrows():
        delta_clientes = row['Total_Clientes'] - row['Clientes_2024_Est']
        delta_ticket = row['Ticket_Promedio_2025'] - row['Ticket_Promedio_2024']
        
        # Efecto Cantidad (Volumen)
        efecto_volumen = delta_clientes * row['Ticket_Promedio_2024']
        
        # Efecto Precio (Mix/Ticket)
        efecto_precio = delta_ticket * row['Total_Clientes'] # Simplificación matemática del residuo cruzado
        
        decomp_data.append({
            'Vendedor': row['Vendedor'],
            'Efecto_Volumen': efecto_volumen,
            'Efecto_Ticket': efecto_precio,
            'Venta_Total_2025': row['Venta_2025']
        })
    
    df_decomp = pd.DataFrame(decomp_data).sort_values('Venta_Total_2025', ascending=False).head(10) # Top 10 para legibilidad
    
    fig_vec = go.Figure()
    fig_vec.add_trace(go.Bar(name='Impulso por Clientes (Tráfico)', x=df_decomp['Vendedor'], y=df_decomp['Efecto_Volumen'], marker_color='#2ca02c'))
    fig_vec.add_trace(go.Bar(name='Impulso por Valor (Ticket)', x=df_decomp['Vendedor'], y=df_decomp['Efecto_Ticket'], marker_color='#1f77b4'))
    
    fig_vec.update_layout(barmode='relative', title="Factores de Crecimiento (Top 10 Vendedores)", height=450)
    st.plotly_chart(fig_vec, use_container_width=True)
    st.info("💡 **Interpretación:** Barras azules indican crecimiento por mejora en la venta promedio por cliente. Barras verdes indican crecimiento por captación de nuevos clientes.")

    # --- SECCIÓN 3: ESTADÍSTICA Y RIESGO (DISTRIBUCIÓN Y GINI) ---
    st.markdown("---")
    col_master1, col_master2 = st.columns(2)
    
    with col_master1:
        st.markdown("### 3. Distribución de Gauss (Histograma)")
        st.write("Análisis de la normalidad de las ventas. ¿Tenemos un equipo balanceado o dependemos de anomalías?")
        
        fig_hist = px.histogram(df_filtered, x="Venta_2025", nbins=10, title="Distribución de Frecuencia de Ventas", marginal="box", opacity=0.7, color_discrete_sequence=['#4682B4'])
        # Añadir linea de promedio
        fig_hist.add_vline(x=df_filtered['Venta_2025'].mean(), line_dash="dash", line_color="red", annotation_text="Promedio")
        st.plotly_chart(fig_hist, use_container_width=True)
        
    with col_master2:
        st.markdown("### 4. Curva de Lorenz y Coeficiente de Gini")
        st.write("Medición de la desigualdad en la fuerza de ventas. Cuanto más curva, más dependemos de pocos.")
        
        # Calculo Lorenz
        lorenz_v = np.sort(df_filtered['Venta_2025'])
        lorenz_v = lorenz_v.cumsum() / lorenz_v.sum()
        lorenz_v = np.insert(lorenz_v, 0, 0)
        
        xaxis = np.linspace(0, 1, len(lorenz_v))
        
        fig_lorenz = go.Figure()
        fig_lorenz.add_trace(go.Scatter(x=xaxis, y=lorenz_v, mode='lines', name='Curva Real', fill='tozeroy'))
        fig_lorenz.add_trace(go.Scatter(x=[0,1], y=[0,1], mode='lines', name='Igualdad Perfecta', line=dict(dash='dash', color='gray')))
        
        # Calculo Gini aproximado
        B = np.sum((lorenz_v[1:] + lorenz_v[:-1]) * (xaxis[1:] - xaxis[:-1]) / 2)
        gini = 1 - 2*B
        
        fig_lorenz.update_layout(title=f"Concentración de Ventas (Gini: {gini:.2f})", xaxis_title="% Acumulado Vendedores", yaxis_title="% Acumulado Ventas")
        st.plotly_chart(fig_lorenz, use_container_width=True)
        
        if gini > 0.5:
            st.warning(f"⚠️ **Alerta de Riesgo:** Gini de {gini:.2f} indica alta dependencia en pocos vendedores estrella.")
        else:
            st.success(f"✅ **Equipo Balanceado:** Gini de {gini:.2f} sugiere una distribución de ventas saludable.")

    # --- SECCIÓN 4: MATRIZ DE CORRELACIÓN ---
    st.markdown("---")
    st.markdown("### 5. Factores de Correlación (Mapa de Calor)")
    st.write("¿Qué variables están realmente conectadas? Un valor cercano a 1 indica correlación positiva fuerte.")
    
    # Selección de variables numéricas relevantes para correlación
    corr_cols = ['Venta_2025', 'Variacion_Pct', 'Clientes_Nuevos', 'Valor_Perdidos', 'Total_Clientes', 'Ticket_Promedio_2025']
    corr_matrix = df_filtered[corr_cols].corr()
    
    fig_corr = px.imshow(corr_matrix, text_auto=True, aspect="auto", color_continuous_scale='RdBu_r', title="Mapa de Calor de Correlaciones")
    st.plotly_chart(fig_corr, use_container_width=True)

    # --- SECCIÓN 5: CONCLUSIONES AUTOMÁTICAS (IA GENERATIVA SIMULADA) ---
    st.markdown("---")
    st.markdown("### 🤖 Insights Generados Automáticamente")
    
    # Lógica simple de reglas para generar texto
    top_grower = df_filtered.loc[df_filtered['Variacion_Pct'].idxmax()]
    top_loser = df_filtered.loc[df_filtered['Valor_Perdidos'].idxmax()]
    
    st.markdown(f"""
    <div class="insight-box">
        <h4>Resumen Estratégico:</h4>
        <ul>
            <li><strong>Motor de Crecimiento:</strong> El vendedor <b>{top_grower['Vendedor']}</b> tiene la mayor aceleración ({top_grower['Variacion_Pct']:.1f}%), impulsado principalmente por una estrategia de {'captación' if top_grower['Valor_Nuevos'] > top_grower['Valor_Crecimiento'] else 'desarrollo de cartera'}.</li>
            <li><strong>Punto de Dolor:</strong> Se debe auditar la cartera de <b>{top_loser['Vendedor']}</b>, quien presenta la mayor fuga de capital (${top_loser['Valor_Perdidos']:,.0f}).</li>
            <li><strong>Salud del Ticket:</strong> El ticket promedio global es de <b>${df_filtered['Ticket_Promedio_2025'].mean():,.0f}</b>. {(df_filtered['Ticket_Promedio_2025'].mean() > df_filtered['Ticket_Promedio_2024'].mean()) and 'Ha mejorado respecto al año anterior.' or 'Ha disminuido, posible presión en precios.'}</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. PIE DE PÁGINA
# -----------------------------------------------------------------------------
st.markdown("---")
col_footer1, col_footer2 = st.columns([3, 1])
with col_footer1:
    st.markdown("**Ferreinox SAS BIC** | Sistema de Inteligencia de Negocios v3.0 | Confidencial")
with col_footer2:
    if st.button("🔄 Recalcular Modelos"):
        st.cache_data.clear()
        st.rerun()