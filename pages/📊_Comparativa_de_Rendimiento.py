# ==============================================================================
# SCRIPT PARA: 📊 Comparativa de Rendimiento
# VERSIÓN: 2.0 RESTAURADA - 07 de Julio, 2025
# DESCRIPCIÓN: Versión final y completa que restaura toda la funcionalidad
#              original de KPIs y gráficos, e integra correctamente el análisis
#              de descuentos FIFO bajo un único selector de vendedor.
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN DE DATOS ---
st.set_page_config(page_title="Comparativa de Rendimiento", page_icon="📊", layout="wide")

st.title("📊 Comparativa de Rendimiento de Vendedores")
st.markdown("Análisis comparativo del equipo de ventas, KPIs de rendimiento y gestión de descuentos.")

if st.session_state.get('usuario') != "GERENTE":
    st.error("🔒 Acceso Exclusivo para Gerencia.")
    st.stop()

df_ventas_historico = st.session_state.get('df_ventas')
if df_ventas_historico is None or df_ventas_historico.empty:
    st.error("No se pudieron cargar los datos maestros. Vuelva a la página principal y recargue.")
    st.stop()

# ==============================================================================
# LÓGICA DE ANÁLISIS (EL CEREBRO DE LA PÁGINA)
# ==============================================================================

@st.cache_data
def calcular_kpis_globales(_df_ventas):
    """
    Calcula KPIs de rendimiento general (Ventas, Ticket, etc.) para cada vendedor.
    """
    # Se eliminan filas con nomvendedor nulo para evitar errores
    df_ventas = _df_ventas.dropna(subset=['nomvendedor'])
    kpis_list = []
    vendedores = df_ventas['nomvendedor'].unique()

    for vendedor in vendedores:
        df_vendedor = df_ventas[df_ventas['nomvendedor'] == vendedor]
        df_productos = df_vendedor[df_vendedor['valor_venta'] > 0]
        
        if df_productos.empty: continue

        venta_bruta = df_productos['valor_venta'].sum()
        clientes_unicos = df_vendedor['cliente_id'].nunique()
        
        kpis_list.append({
            'Vendedor': vendedor,
            'Ventas Brutas': venta_bruta,
            'Clientes Únicos': clientes_unicos,
            'Ticket Promedio': venta_bruta / clientes_unicos if clientes_unicos > 0 else 0
        })

    if not kpis_list: return pd.DataFrame(), pd.Series(dtype='float64')
    
    df_kpis = pd.DataFrame(kpis_list)
    promedios = df_kpis.select_dtypes(include=np.number).mean()
    return df_kpis, promedios

@st.cache_data
def calcular_vinculos_fifo_optimizado(_df_ventas, nombre_exacto_descuento, fecha_inicio_politica):
    """
    Versión optimizada que calcula los vínculos de descuento.
    """
    df_ventas = _df_ventas.copy()
    df_ventas['fecha_venta'] = pd.to_datetime(df_ventas['fecha_venta'])
    fecha_politica = pd.to_datetime(fecha_inicio_politica)

    df_analisis = df_ventas[df_ventas['fecha_venta'] >= fecha_politica]

    filtro_facturas = (df_analisis['valor_venta'] > 0) & (df_analisis['TipoDocumento'].str.contains('FACTURA', na=False, case=False))
    filtro_descuentos = (df_analisis['valor_venta'] < 0) & (df_analisis['nombre_articulo'] == nombre_exacto_descuento)

    facturas = df_analisis[filtro_facturas].sort_values(by=['cliente_id', 'fecha_venta'])
    descuentos = df_analisis[filtro_descuentos].sort_values(by=['cliente_id', 'fecha_venta'])

    if descuentos.empty or facturas.empty: return pd.DataFrame()

    facturas['rank'] = facturas.groupby('cliente_id').cumcount()
    descuentos['rank'] = descuentos.groupby('cliente_id').cumcount()

    df_vinculado = pd.merge(descuentos, facturas, on=['cliente_id', 'rank'], suffixes=('_dcto', '_factura'))

    if df_vinculado.empty: return pd.DataFrame()

    df_vinculado['dias_pago'] = (df_vinculado['fecha_venta_dcto'] - df_vinculado['fecha_venta_factura']).dt.days
    df_vinculado = df_vinculado[df_vinculado['dias_pago'] >= 0] 

    df_resultado = df_vinculado.rename(columns={'nomvendedor_factura': 'nomvendedor', 'nombre_cliente_factura': 'nombre_cliente', 'valor_venta_factura': 'valor_compra'})
    df_resultado['valor_descuento'] = abs(df_resultado['valor_venta_dcto'])
    
    return df_resultado[['nomvendedor', 'nombre_cliente', 'valor_compra', 'valor_descuento', 'dias_pago']]

# ==============================================================================
# COMPONENTES DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def render_radar_chart(df_kpis, promedios, vendedor_seleccionado):
    st.header(f"Radar de Competencias: {vendedor_seleccionado}")
    kpis_radar = {'Ventas Brutas': True, 'Clientes Únicos': True, 'Ticket Promedio': True}
    df_percentiles = df_kpis.copy()
    
    for kpi, higher_is_better in kpis_radar.items():
        if kpi not in df_percentiles.columns: continue
        rank_series = df_percentiles[kpi].rank(pct=True)
        df_percentiles[kpi] = rank_series if higher_is_better else 1 - rank_series
    
    datos_vendedor = df_percentiles[df_percentiles['Vendedor'] == vendedor_seleccionado]
    if datos_vendedor.empty: return

    datos_vendedor = datos_vendedor.iloc[0]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[0.5] * len(kpis_radar), theta=list(kpis_radar.keys()), fill='toself', name='Promedio Equipo', line_color='lightgrey'))
    fig.add_trace(go.Scatterpolar(r=datos_vendedor[list(kpis_radar.keys())].values, theta=list(kpis_radar.keys()), fill='toself', name=vendedor_seleccionado))
    st.plotly_chart(fig, use_container_width=True)

def render_ranking_chart(df_kpis, kpi_seleccionado):
    st.header(f"Ranking General por: {kpi_seleccionado}")
    if kpi_seleccionado not in df_kpis.columns: 
        st.warning(f"No se pudo generar el ranking para la métrica '{kpi_seleccionado}'.")
        return
    df_sorted = df_kpis.sort_values(by=kpi_seleccionado, ascending=False)
    fig = px.bar(df_sorted, x=kpi_seleccionado, y='Vendedor', orientation='h', text_auto=True, title=f"Top Vendedores por {kpi_seleccionado}")
    st.plotly_chart(fig, use_container_width=True)

def render_tabla_descuentos(df_vinculado, vendedor):
    st.header(f"🔍 Detalle de Descuentos Otorgados por {vendedor}")
    df_vista = df_vinculado[df_vinculado['nomvendedor'] == vendedor]

    if df_vista.empty:
        st.info(f"Este vendedor no ha otorgado descuentos comerciales desde el inicio de la política.")
        return
    
    st.dataframe(
        df_vista[['nombre_cliente', 'valor_compra', 'valor_descuento', 'dias_pago']],
        column_config={
            "nombre_cliente": "Cliente",
            "valor_compra": st.column_config.NumberColumn("Valor Compra Original", format="$ {:,.0f}"),
            "valor_descuento": st.column_config.NumberColumn("Valor Descuento", format="$ {:,.0f}"),
            "dias_pago": st.column_config.NumberColumn("Días de Pago"),
        },
        use_container_width=True, hide_index=True
    )

# ==============================================================================
# ORQUESTACIÓN Y EJECUCIÓN DE LA PÁGINA
# ==============================================================================

# --- CÁLCULOS PRINCIPALES ---
df_kpis, promedios = calcular_kpis_globales(df_ventas_historico)

# Constantes de la lógica de negocio
NOMBRE_ARTICULO_DESCUENTO = "DESCUENTOS COMERCIALES"
FECHA_INICIO_POLITICA = "2024-06-01"
df_vinculado_fifo = calcular_vinculos_fifo_optimizado(df_ventas_historico, NOMBRE_ARTICULO_DESCUENTO, FECHA_INICIO_POLITICA)


# --- RENDERIZADO PRINCIPAL ---
if df_kpis.empty:
    st.warning("No hay suficientes datos de ventas para generar una comparativa de KPIs.")
    st.stop()

st.markdown("---")
st.header("Análisis de Vendedor Individual")
col1, col2 = st.columns([1, 2])

with col1:
    # Selector único y principal para toda la página
    vendedores_lista = sorted(df_kpis['Vendedor'].unique())
    vendedor_seleccionado = st.selectbox(
        "**Seleccione un Vendedor:**", 
        options=vendedores_lista,
        help="La selección de este vendedor actualizará todos los módulos de esta página."
    )
    
    # Selector para el gráfico de ranking
    kpi_para_ranking = st.selectbox(
        "**Seleccione Métrica para el Ranking:**",
        options=sorted(promedios.index)
    )

with col2:
    if vendedor_seleccionado:
        render_radar_chart(df_kpis, promedios, vendedor_seleccionado)

st.markdown("---")

# Renderizar el ranking y la tabla de descuentos
if vendedor_seleccionado:
    render_ranking_chart(df_kpis, kpi_para_ranking)
    st.markdown("---")
    render_tabla_descuentos(df_vinculado_fifo, vendedor_seleccionado)
