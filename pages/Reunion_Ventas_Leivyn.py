import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Tablero Gerencial Ferreinox SAS BIC",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    .stMetric { text-align: center; }
    h1, h2, h3 { color: #2c3e50; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_excel("analisis_2025.xlsx")
    df.columns = df.columns.str.strip()
    rename_dict = {
        'Vendedores': 'Vendedor',
        'Importe 2025': 'Importe 2025',
        'Importe 2024': 'Importe 2024',
        '%Crec': '%Crec',
        'CLIENTES_DESCODIFICADO': 'Clientes Descodificado',
        'VALOR_DESCODIFICADOS': 'Valor Descodificado',
        'CLIENTES_NUEVO': 'Clientes Nuevo',
        'VALOR_NUEVOS': 'Valor Nuevo',
        'CLIENTES_REACTIVADO': 'Clientes Reactivado',
        'VALOR_REACTIVADO': 'Valor Reactivado',
        'VARIACION_CLIENTES_#CREC': 'Clientes Crecimiento',
        'VALOR_CLIENTES_CRECEN': 'Valor Crecimiento',
        'CLIENTE_#DECREC': 'Clientes Decrecimiento',
        'VALOR_CLIENTE_DECRECE': 'Valor Decrecimiento',
        'TOTAL CLIENTE': 'Total Clientes'
    }
    df = df.rename(columns={k: v for k, v in rename_dict.items() if k in df.columns})
    cols_to_numeric = [
        'Importe 2025', 'Importe 2024', 'Valor Descodificado', 'Valor Nuevo', 'Valor Reactivado',
        'Valor Crecimiento', 'Valor Decrecimiento'
    ]
    for col in cols_to_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df = df.dropna(subset=['Vendedor'])
    df = df[df['Vendedor'].str.upper() != 'TOTAL']
    df['Crecimiento Neto'] = df['Importe 2025'] - df['Importe 2024']
    df['% Crecimiento Real'] = (df['Crecimiento Neto'] / df['Importe 2024']) * 100
    cols_gains = ['Valor Nuevo', 'Valor Reactivado', 'Valor Crecimiento']
    cols_losses = ['Valor Descodificado', 'Valor Decrecimiento']
    df['Ganancia Total'] = df[cols_gains].sum(axis=1)
    df['Pérdida Total'] = df[cols_losses].sum(axis=1)
    return df

st.sidebar.image("https://raw.githubusercontent.com/DiegoMao2021/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", use_column_width=True)
st.sidebar.title("Menú de Control")

df = load_data()

selected_sellers = st.sidebar.multiselect("Filtrar por Vendedor", df['Vendedor'].unique(), default=df['Vendedor'].unique())
df_filtered = df[df['Vendedor'].isin(selected_sellers)]

st.title("🚀 Tablero de Control Gerencial - Ferreinox SAS BIC")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
total_sales_2025 = df_filtered['Importe 2025'].sum()
total_sales_2024 = df_filtered['Importe 2024'].sum()
total_growth = total_sales_2025 - total_sales_2024
pct_growth = (total_growth / total_sales_2024) * 100 if total_sales_2024 > 0 else 0
top_performer = df_filtered.loc[df_filtered['Importe 2025'].idxmax()]['Vendedor']
top_grower = df_filtered.loc[df_filtered['Crecimiento Neto'].idxmax()]['Vendedor']

col1.metric("Ventas Totales 2025", f"${total_sales_2025:,.0f}", f"{pct_growth:.1f}% vs 2024")
col2.metric("Crecimiento Neto ($)", f"${total_growth:,.0f}", "Variación Absoluta")
col3.metric("Top Vendedor (Volumen)", top_performer, "Líder en Facturación")
col4.metric("Top Crecimiento (Valor)", top_grower, "Mayor Aporte Neto")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📈 Visión General", "🔍 Análisis de Impacto", "👤 Ficha por Vendedor"])

with tab1:
    st.subheader("Ranking de Ventas y Crecimiento")
    c1, c2 = st.columns(2)
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=df_filtered['Vendedor'],
        y=df_filtered['Importe 2024'],
        name='2024',
        marker_color='#95a5a6'
    ))
    fig_bar.add_trace(go.Bar(
        x=df_filtered['Vendedor'],
        y=df_filtered['Importe 2025'],
        name='2025',
        marker_color='#2ecc71'
    ))
    fig_bar.update_layout(title="Comparativo de Ventas 2024 vs 2025", barmode='group', xaxis_tickangle=-45)
    c1.plotly_chart(fig_bar, use_container_width=True)

    fig_scat = px.scatter(
        df_filtered,
        x='Importe 2025',
        y='% Crecimiento Real',
        size='Ganancia Total',
        color='Vendedor',
        hover_name='Vendedor',
        title="Matriz de Potencial (Tamaño = Ganancia Bruta)",
        labels={'Importe 2025': 'Volumen de Ventas 2025', '% Crecimiento Real': '% Crecimiento YoY'}
    )
    fig_scat.add_hline(y=df_filtered['% Crecimiento Real'].mean(), line_dash="dash", line_color="red", annotation_text="Promedio Crecimiento")
    fig_scat.add_vline(x=df_filtered['Importe 2025'].mean(), line_dash="dash", line_color="blue", annotation_text="Promedio Ventas")
    c2.plotly_chart(fig_scat, use_container_width=True)

with tab2:
    st.subheader("Desglose de Movimientos (Waterfall Analysis)")
    st.write("Entendiendo de dónde viene el dinero: Nuevos, Reactivados, Crecimiento vs Fugas.")
    impact_cols = ['Valor Nuevo', 'Valor Reactivado', 'Valor Crecimiento', 'Valor Decrecimiento', 'Valor Descodificado']
    df_impact = df_filtered[['Vendedor'] + impact_cols].set_index('Vendedor')
    df_impact['Valor Decrecimiento'] = -df_impact['Valor Decrecimiento'].abs()
    df_impact['Valor Descodificado'] = -df_impact['Valor Descodificado'].abs()
    fig_stack = go.Figure()
    colors = {'Valor Nuevo': '#3498db', 'Valor Reactivado': '#9b59b6', 'Valor Crecimiento': '#2ecc71',
              'Valor Decrecimiento': '#f1c40f', 'Valor Descodificado': '#e74c3c'}
    for col in impact_cols:
        fig_stack.add_trace(go.Bar(
            x=df_impact.index,
            y=df_impact[col],
            name=col,
            marker_color=colors.get(col, '#333')
        ))
    fig_stack.update_layout(
        title="Balance de Captación vs Fuga por Vendedor",
        barmode='relative',
        xaxis_tickangle=-45,
        yaxis_title="Valor Monetario"
    )
    st.plotly_chart(fig_stack, use_container_width=True)

with tab3:
    st.subheader("Análisis Individual Profundo")
    seller = st.selectbox("Seleccione un Vendedor para ver su ficha técnica:", df['Vendedor'].unique())
    seller_data = df[df['Vendedor'] == seller].iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ventas 2025", f"${seller_data['Importe 2025']:,.0f}")
    c2.metric("Crecimiento vs 2024", f"{seller_data['% Crecimiento Real']:.2f}%")
    valor_clientes_nuevo = seller_data['Clientes Nuevo'] if 'Clientes Nuevo' in seller_data.index else 0
    valor_clientes_nuevo = 0 if pd.isna(valor_clientes_nuevo) else int(valor_clientes_nuevo)
    c3.metric("Clientes Nuevos", valor_clientes_nuevo)
    valor_clientes_perdidos = seller_data['Clientes Descodificado'] if 'Clientes Descodificado' in seller_data.index else 0
    valor_clientes_perdidos = 0 if pd.isna(valor_clientes_perdidos) else int(valor_clientes_perdidos)
    c4.metric("Clientes Perdidos", valor_clientes_perdidos)
    labels = ['Nuevos', 'Reactivados', 'Crecimiento Clientes', 'Decrecimiento Clientes', 'Descodificados']
    values = [
        seller_data.get('Valor Nuevo', 0), 
        seller_data.get('Valor Reactivado', 0), 
        seller_data.get('Valor Crecimiento', 0), 
        abs(seller_data.get('Valor Decrecimiento', 0)),
        abs(seller_data.get('Valor Descodificado', 0))
    ]
    fig_pie = px.pie(
        names=labels, 
        values=values, 
        title=f"Distribución del Impacto: {seller}",
        hole=0.4
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    st.info(f"Análisis Técnico: {seller} generó ${seller_data['Ganancia Total']:,.0f} en nuevas oportunidades, pero enfrentó una resistencia (pérdida) de ${seller_data['Pérdida Total']:,.0f}. Su saldo neto operativo es {'positivo' if seller_data['Ganancia Total'] > seller_data['Pérdida Total'] else 'negativo'} según el balance mostrado.")

st.markdown("---")
st.caption("Sistema de Análisis Desarrollado para Ferreinox SAS BIC. v1.0")