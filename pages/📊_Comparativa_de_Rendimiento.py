import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ==============================================================================
# 1. CONFIGURACIÓN Y ESTADO INICIAL
# ==============================================================================
st.set_page_config(page_title="Comparativa de Rendimiento", page_icon="📊", layout="wide")

# Esta página es exclusiva para el perfil de Gerente
if st.session_state.get('usuario') != "GERENTE":
    st.header("🔒 Acceso Exclusivo para Gerencia")
    st.warning("Esta sección solo está disponible para el perfil de 'GERENTE'.")
    st.stop()

# Carga segura de datos desde el estado de la sesión
df_ventas_historico = st.session_state.get('df_ventas')
APP_CONFIG = st.session_state.get('APP_CONFIG')
DATA_CONFIG = st.session_state.get('DATA_CONFIG')

if df_ventas_historico is None or df_ventas_historico.empty or not APP_CONFIG or not DATA_CONFIG:
    st.error("No se pudieron cargar los datos maestros. Por favor, vuelva a la página principal y asegúrese de haber iniciado sesión.")
    st.stop()

# ==============================================================================
# 2. LÓGICA DE ANÁLISIS COMPARATIVO (El "Cerebro" de la Página)
# ==============================================================================

@st.cache_data
def calcular_kpis_globales(df_ventas):
    """
    Calcula un set de KPIs para cada vendedor y el promedio general.
    Esta es la función más pesada y se cachea para un rendimiento óptimo.
    """
    # Helper function para reutilizar la lógica de margen
    def preparar_datos_y_margen(df):
        filtro_descuento = (df['nombre_articulo'].str.contains('descuento', case=False, na=False)) & \
                           (df['nombre_articulo'].str.contains('comercial', case=False, na=False))
        df_descuentos = df[filtro_descuento]
        df_productos = df[~filtro_descuento].copy()
        if not df_productos.empty:
            df_productos['costo_total_linea'] = df_productos['costo_unitario'].fillna(0) * df_productos['unidades_vendidas'].fillna(0)
            df_productos['margen_bruto'] = df_productos['valor_venta'] - df_productos['costo_total_linea']
        return df_productos, df_descuentos

    kpis_list = []
    vendedores = df_ventas['nomvendedor'].unique()

    for vendedor in vendedores:
        df_vendedor = df_ventas[df_ventas['nomvendedor'] == vendedor]
        df_productos, df_descuentos = preparar_datos_y_margen(df_vendedor)
        
        # Calcular KPIs
        venta_bruta = df_productos['valor_venta'].sum()
        margen_bruto_productos = df_productos['margen_bruto'].sum()
        total_descuentos = abs(df_descuentos['valor_venta'].sum())
        margen_operativo = margen_bruto_productos - total_descuentos
        margen_operativo_pct = (margen_operativo / venta_bruta * 100) if venta_bruta > 0 else 0
        descuento_pct = (total_descuentos / venta_bruta * 100) if venta_bruta > 0 else 0
        clientes_unicos = df_vendedor['cliente_id'].nunique()
        ticket_promedio = venta_bruta / clientes_unicos if clientes_unicos > 0 else 0

        kpis_list.append({
            'Vendedor': vendedor,
            'Ventas Brutas': venta_bruta,
            'Margen Operativo (%)': margen_operativo_pct,
            'Descuento Concedido (%)': descuento_pct,
            'Clientes Únicos': clientes_unicos,
            'Ticket Promedio': ticket_promedio
        })

    df_kpis = pd.DataFrame(kpis_list)
    df_kpis = df_kpis[df_kpis['Ventas Brutas'] > 0] # Excluir vendedores sin ventas
    promedios = df_kpis.select_dtypes(include=np.number).mean()
    
    return df_kpis, promedios

# ==============================================================================
# 3. LÓGICA DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def render_radar_chart(df_kpis, promedios, vendedor_seleccionado):
    st.subheader(f"Radar de Competencias: {vendedor_seleccionado} vs. Promedio del Equipo")
    
    # Normalizar datos para que sean comparables en el mismo gráfico
    kpis_a_comparar = ['Ventas Brutas', 'Margen Operativo (%)', 'Clientes Únicos', 'Ticket Promedio']
    df_normalizado = df_kpis.copy()
    for kpi in kpis_a_comparar:
        min_val, max_val = df_kpis[kpi].min(), df_kpis[kpi].max()
        if (max_val - min_val) > 0:
            df_normalizado[kpi] = (df_kpis[kpi] - min_val) / (max_val - min_val)
        else:
            df_normalizado[kpi] = 0.5 # Si todos tienen el mismo valor, ponerlo en el medio
    
    promedios_normalizados = (promedios - df_kpis.min()) / (df_kpis.max() - df_kpis.min())

    datos_vendedor = df_normalizado[df_normalizado['Vendedor'] == vendedor_seleccionado].iloc[0]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=promedios_normalizados[kpis_a_comparar].values,
        theta=kpis_a_comparar,
        fill='toself', name='Promedio del Equipo', line=dict(color='lightgrey')
    ))
    fig.add_trace(go.Scatterpolar(
        r=datos_vendedor[kpis_a_comparar].values,
        theta=kpis_a_comparar,
        fill='toself', name=vendedor_seleccionado, line=dict(color='dodgerblue')
    ))
    st.plotly_chart(fig, use_container_width=True)

def render_ranking_chart(df_kpis, kpi_seleccionado):
    st.subheader(f"Ranking de Vendedores por: {kpi_seleccionado}")
    df_sorted = df_kpis.sort_values(by=kpi_seleccionado, ascending=True)
    fig = px.bar(df_sorted, x=kpi_seleccionado, y='Vendedor', orientation='h', text_auto=True)
    fig.update_traces(texttemplate='%{x:,.2f}')
    st.plotly_chart(fig, use_container_width=True)

def render_matriz_equipo(df_kpis):
    st.subheader("Matriz Estratégica del Equipo (Ventas vs. Margen)")
    
    avg_ventas = df_kpis['Ventas Brutas'].mean()
    avg_margen = df_kpis['Margen Operativo (%)'].mean()
    
    fig = px.scatter(
        df_kpis, x='Ventas Brutas', y='Margen Operativo (%)',
        text='Vendedor', size='Clientes Únicos', color_discrete_sequence=['#1f77b4'],
        hover_name='Vendedor', hover_data={'Vendedor':False}
    )
    fig.update_traces(textposition='top center', textfont_size=10)
    fig.add_vline(x=avg_ventas, line_width=1, line_dash="dash", line_color="grey")
    fig.add_hline(y=avg_margen, line_width=1, line_dash="dash", line_color="grey")
    
    # Anotaciones de los cuadrantes
    fig.add_annotation(x=df_kpis['Ventas Brutas'].max(), y=df_kpis['Margen Operativo (%)'].max(), text="<b>Líderes</b>", showarrow=False, font_size=14, xanchor='right', yanchor='top', opacity=0.5)
    fig.add_annotation(x=df_kpis['Ventas Brutas'].min(), y=df_kpis['Margen Operativo (%)'].max(), text="<b>Especialistas de Nicho</b>", showarrow=False, font_size=14, xanchor='left', yanchor='top', opacity=0.5)
    fig.add_annotation(x=df_kpis['Ventas Brutas'].max(), y=df_kpis['Margen Operativo (%)'].min(), text="<b>Constructores de Volumen</b>", showarrow=False, font_size=14, xanchor='right', yanchor='bottom', opacity=0.5)
    fig.add_annotation(x=df_kpis['Ventas Brutas'].min(), y=df_kpis['Margen Operativo (%)'].min(), text="<b>En Desarrollo</b>", showarrow=False, font_size=14, xanchor='left', yanchor='bottom', opacity=0.5)

    st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# 4. EJECUCIÓN PRINCIPAL
# ==============================================================================
st.title("📊 Comparativa de Rendimiento de Vendedores")
st.markdown("Analiza y compara el desempeño del equipo para identificar líderes y oportunidades de coaching. Todos los datos corresponden al histórico completo.")
st.markdown("---")

# Calcular los datos una sola vez
df_kpis, promedios = calcular_kpis_globales(df_ventas_historico)

if df_kpis.empty:
    st.warning("No hay suficientes datos para generar una comparativa.")
    st.stop()

# --- INTERFAZ DE USUARIO ---
col1, col2 = st.columns(2)
with col1:
    vendedor_seleccionado = st.selectbox("Seleccione un Vendedor para destacar en el Radar:", options=sorted(df_kpis['Vendedor'].unique()))
with col2:
    kpi_ranking = st.selectbox("Seleccione una Métrica para el Ranking:", options=sorted(df_kpis.columns.drop('Vendedor')))

# --- Módulos de Visualización ---
render_radar_chart(df_kpis, promedios, vendedor_seleccionado)
st.markdown("---")
render_ranking_chart(df_kpis, kpi_ranking)
st.markdown("---")
render_matriz_equipo(df_kpis)
