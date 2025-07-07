# ==============================================================================
# SCRIPT PARA: 📊 Comparativa de Rendimiento.py
# VERSIÓN: RESTAURADA ORIGINAL - 07 de Julio, 2025
# DESCRIPCIÓN: Se restaura el código a la funcionalidad original solicitada,
#              con todos sus análisis de KPIs y gráficos comparativos.
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN ---
st.set_page_config(page_title="Comparativa de Rendimiento", page_icon="📊", layout="wide")

if st.session_state.get('usuario') != "GERENTE":
    st.header("🔒 Acceso Exclusivo para Gerencia")
    st.warning("Esta sección solo está disponible para el perfil de 'GERENTE'.")
    st.stop()

df_ventas_historico = st.session_state.get('df_ventas')
if df_ventas_historico is None or df_ventas_historico.empty:
    st.error("No se pudieron cargar los datos maestros. Vuelva a la página principal.")
    st.stop()

# --- LÓGICA DE ANÁLISIS (EL CEREBRO ORIGINAL) ---

@st.cache_data
def calcular_kpis_globales(_df_ventas):
    df_ventas = _df_ventas.dropna(subset=['nomvendedor', 'nombre_articulo'])
    
    filtro_descuento = (df_ventas['nombre_articulo'].str.contains('descuento', case=False, na=False)) & \
                       (df_ventas['nombre_articulo'].str.contains('comercial', case=False, na=False))
    
    df_descuentos_global = df_ventas[filtro_descuento]
    df_productos_global = df_ventas[~filtro_descuento].copy()

    kpis_list = []
    vendedores = df_productos_global['nomvendedor'].unique()

    for vendedor in vendedores:
        df_vendedor_prods = df_productos_global[df_productos_global['nomvendedor'] == vendedor]
        df_vendedor_dctos = df_descuentos_global[df_descuentos_global['nomvendedor'] == vendedor]
        
        if df_vendedor_prods.empty: continue

        venta_bruta = df_vendedor_prods['valor_venta'].sum()
        margen_bruto = (df_vendedor_prods['valor_venta'] - (df_vendedor_prods['costo_unitario'].fillna(0) * df_vendedor_prods['unidades_vendidas'].fillna(0))).sum()
        total_descuentos = abs(df_vendedor_dctos['valor_venta'].sum())
        margen_operativo = margen_bruto - total_descuentos
        clientes_unicos = df_vendedor_prods['cliente_id'].nunique()
        
        kpis_list.append({
            'Vendedor': vendedor,
            'Ventas Brutas': venta_bruta,
            'Margen Operativo (%)': (margen_operativo / venta_bruta * 100) if venta_bruta > 0 else 0,
            'Descuento Concedido (%)': (total_descuentos / venta_bruta * 100) if venta_bruta > 0 else 0,
            'Clientes Únicos': clientes_unicos,
            'Ticket Promedio': venta_bruta / clientes_unicos if clientes_unicos > 0 else 0
        })

    if not kpis_list: return pd.DataFrame(), pd.Series(dtype='float64')

    df_kpis = pd.DataFrame(kpis_list)
    promedios = df_kpis.select_dtypes(include=np.number).mean()
    return df_kpis, promedios

# --- COMPONENTES DE LA INTERFAZ DE USUARIO (UI) ---

def render_radar_chart(df_kpis, promedios, vendedor_seleccionado):
    st.subheader(f"Radar de Competencias: {vendedor_seleccionado} vs. Promedio")
    kpis_radar = {'Ventas Brutas': True, 'Margen Operativo (%)': True, 'Clientes Únicos': True, 'Ticket Promedio': True, 'Descuento Concedido (%)': False}
    df_percentiles = df_kpis.copy()
    for kpi, higher_is_better in kpis_radar.items():
        if kpi not in df_percentiles.columns: continue
        rank_series = df_percentiles[kpi].rank(pct=True)
        df_percentiles[kpi] = rank_series if higher_is_better else 1 - rank_series
    
    datos_vendedor = df_percentiles[df_percentiles['Vendedor'] == vendedor_seleccionado].iloc[0]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[0.5] * len(kpis_radar), theta=list(kpis_radar.keys()), fill='toself', name='Promedio Equipo'))
    fig.add_trace(go.Scatterpolar(r=datos_vendedor[list(kpis_radar.keys())].values, theta=list(kpis_radar.keys()), fill='toself', name=vendedor_seleccionado))
    st.plotly_chart(fig, use_container_width=True)

def render_ranking_chart(df_kpis, kpi_seleccionado):
    st.subheader(f"Ranking de Vendedores por: {kpi_seleccionado}")
    ascending_order = True if kpi_seleccionado == 'Descuento Concedido (%)' else False
    df_sorted = df_kpis.sort_values(by=kpi_seleccionado, ascending=ascending_order)
    fig = px.bar(df_sorted, x=kpi_seleccionado, y='Vendedor', orientation='h', text_auto=True)
    st.plotly_chart(fig, use_container_width=True)

def render_matriz_equipo(df_kpis, promedios, vendedor_seleccionado):
    st.subheader("Matriz Estratégica del Equipo (Ventas vs. Margen)")
    avg_ventas = promedios['Ventas Brutas']
    avg_margen = promedios['Margen Operativo (%)']
    fig = px.scatter(df_kpis, x='Ventas Brutas', y='Margen Operativo (%)', size='Clientes Únicos', color='Vendedor', hover_name='Vendedor')
    fig.add_vline(x=avg_ventas, line_width=1.5, line_dash="dash", line_color="grey", annotation_text="Promedio Ventas")
    fig.add_hline(y=avg_margen, line_width=1.5, line_dash="dash", line_color="grey", annotation_text="Promedio Margen")
    st.plotly_chart(fig, use_container_width=True)

# --- EJECUCIÓN PRINCIPAL ---
st.title("📊 Comparativa de Rendimiento de Vendedores")
st.markdown("Analiza y compara el desempeño del equipo para identificar líderes y oportunidades de coaching. Todos los datos corresponden al histórico completo.")
st.markdown("---")

df_kpis, promedios = calcular_kpis_globales(df_ventas_historico)

if df_kpis.empty:
    st.warning("No hay suficientes datos de vendedores con ventas para generar una comparativa.")
    st.stop()

col1, col2 = st.columns(2)
vendedor_seleccionado = col1.selectbox("Seleccione un Vendedor para analizar:", options=sorted(df_kpis['Vendedor'].unique()))
kpi_ranking = col2.selectbox("Seleccione una Métrica para el Ranking:", options=sorted(promedios.index))

if vendedor_seleccionado:
    render_radar_chart(df_kpis, promedios, vendedor_seleccionado)
    st.markdown("---")
    render_matriz_equipo(df_kpis, promedios, vendedor_seleccionado)
    st.markdown("---")
    render_ranking_chart(df_kpis, kpi_ranking)
