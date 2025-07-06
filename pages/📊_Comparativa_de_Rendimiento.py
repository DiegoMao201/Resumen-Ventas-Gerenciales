# ==============================================================================
# SCRIPT PARA: 📊 Comparativa de Rendimiento.py
# VERSIÓN: FINAL - 07 de Julio, 2025
# DESCRIPCIÓN: Versión final y completa que integra el análisis de descuentos
#              FIFO con las comparativas de KPIs de vendedores existentes.
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN DE DATOS ---
st.set_page_config(page_title="Comparativa de Rendimiento", page_icon="📊", layout="wide")

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
def calcular_vinculos_fifo(_df_ventas, nombre_exacto_descuento):
    """
    Aplica el modelo FIFO para vincular notas de descuento con la factura
    original más antigua y pendiente de cada cliente.
    """
    df_ventas = _df_ventas.copy()
    df_ventas['fecha_venta'] = pd.to_datetime(df_ventas['fecha_venta'])

    filtro_facturas = (df_ventas['valor_venta'] > 0) & (df_ventas['TipoDocumento'].str.contains('FACTURA', na=False, case=False))
    filtro_descuentos = (df_ventas['valor_venta'] < 0) & (df_ventas['nombre_articulo'] == nombre_exacto_descuento)

    facturas = df_ventas[filtro_facturas].sort_values(by=['cliente_id', 'fecha_venta']).reset_index()
    descuentos = df_ventas[filtro_descuentos].sort_values(by=['cliente_id', 'fecha_venta'])

    if descuentos.empty:
        return pd.DataFrame()
        
    facturas['atendida'] = False
    vinculos = []

    for _, descuento in descuentos.iterrows():
        facturas_candidatas = facturas[
            (facturas['cliente_id'] == descuento['cliente_id']) &
            (facturas['fecha_venta'] <= descuento['fecha_venta']) &
            (facturas['atendida'] == False)
        ]

        if not facturas_candidatas.empty:
            factura_a_vincular = facturas_candidatas.iloc[0]
            indice_factura = factura_a_vincular['index']
            dias_pago = (descuento['fecha_venta'] - factura_a_vincular['fecha_venta']).days
            
            vinculos.append({
                'nomvendedor': factura_a_vincular['nomvendedor'],
                'nombre_cliente': factura_a_vincular['nombre_cliente'],
                'valor_compra': factura_a_vincular['valor_venta'],
                'valor_descuento': abs(descuento['valor_venta']),
                'dias_pago': dias_pago,
            })
            
            facturas.loc[facturas['index'] == indice_factura, 'atendida'] = True
            
    if not vinculos:
        return pd.DataFrame()

    df_resultado = pd.DataFrame(vinculos)
    df_resultado['cumple_politica'] = df_resultado['dias_pago'] <= 15
    df_resultado['porcentaje_descuento'] = (df_resultado['valor_descuento'] / df_resultado['valor_compra']) * 100
    return df_resultado

@st.cache_data
def calcular_kpis_globales(df_ventas):
    """
    Calcula KPIs de rendimiento general para cada vendedor.
    """
    kpis_list = []
    vendedores = df_ventas['nomvendedor'].unique()

    for vendedor in vendedores:
        df_vendedor = df_ventas[df_ventas['nomvendedor'] == vendedor]
        df_productos = df_vendedor[df_vendedor['valor_venta'] > 0]
        df_descuentos = df_vendedor[df_vendedor['valor_venta'] < 0]

        if df_productos.empty: continue

        venta_bruta = df_productos['valor_venta'].sum()
        total_descuentos = abs(df_descuentos['valor_venta'].sum())
        clientes_unicos = df_vendedor['cliente_id'].nunique()
        
        kpis_list.append({
            'Vendedor': vendedor,
            'Ventas Brutas': venta_bruta,
            'Descuento Concedido (%)': (total_descuentos / venta_bruta * 100) if venta_bruta > 0 else 0,
            'Clientes Únicos': clientes_unicos,
            'Ticket Promedio': venta_bruta / clientes_unicos if clientes_unicos > 0 else 0
        })

    if not kpis_list: return pd.DataFrame(), pd.Series()
    df_kpis = pd.DataFrame(kpis_list)
    promedios = df_kpis.select_dtypes(include=np.number).mean()
    return df_kpis, promedios

# ==============================================================================
# COMPONENTES DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def render_radar_chart(df_kpis, promedios, vendedor_seleccionado):
    st.subheader(f"Radar de Competencias: {vendedor_seleccionado} vs. Promedio")
    kpis_radar = {'Ventas Brutas': True, 'Clientes Únicos': True, 'Ticket Promedio': True, 'Descuento Concedido (%)': False}
    df_percentiles = df_kpis.copy()
    for kpi, higher_is_better in kpis_radar.items():
        if kpi not in df_percentiles.columns: continue
        rank_series = df_percentiles[kpi].rank(pct=True)
        df_percentiles[kpi] = rank_series if higher_is_better else 1 - rank_series
    
    datos_vendedor = df_percentiles[df_percentiles['Vendedor'] == vendedor_seleccionado]
    if datos_vendedor.empty: return

    datos_vendedor = datos_vendedor.iloc[0]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[0.5] * len(kpis_radar), theta=list(kpis_radar.keys()), fill='toself', name='Promedio Equipo'))
    fig.add_trace(go.Scatterpolar(r=datos_vendedor[list(kpis_radar.keys())].values, theta=list(kpis_radar.keys()), fill='toself', name=vendedor_seleccionado))
    st.plotly_chart(fig, use_container_width=True)

def render_ranking_chart(df_kpis, kpi_seleccionado):
    st.subheader(f"Ranking de Vendedores por: {kpi_seleccionado}")
    if kpi_seleccionado not in df_kpis.columns: 
        st.warning(f"No se pudo generar el ranking para la métrica '{kpi_seleccionado}'.")
        return
    ascending_order = True if kpi_seleccionado == 'Descuento Concedido (%)' else False
    df_sorted = df_kpis.sort_values(by=kpi_seleccionado, ascending=ascending_order)
    fig = px.bar(df_sorted, x=kpi_seleccionado, y='Vendedor', orientation='h', text_auto=True)
    st.plotly_chart(fig, use_container_width=True)

def render_tabla_descuentos(df_vinculado, vendedor):
    st.subheader(f"🔍 Análisis de Descuentos Otorgados por: {vendedor}")
    df_vista = df_vinculado[df_vinculado['nomvendedor'] == vendedor]

    if df_vista.empty:
        st.info(f"No se encontraron descuentos comerciales otorgados por {vendedor}.")
        return
    
    st.dataframe(
        df_vista[['nombre_cliente', 'valor_compra', 'valor_descuento', 'dias_pago', 'cumple_politica', 'porcentaje_descuento']],
        column_config={
            "nombre_cliente": "Cliente",
            "valor_compra": st.column_config.NumberColumn("Valor Compra", format="$ {:,.0f}"),
            "valor_descuento": st.column_config.NumberColumn("Valor Descuento", format="$ {:,.0f}"),
            "dias_pago": st.column_config.NumberColumn("Días de Pago"),
            "cumple_politica": "Cumple (≤15d)",
            "porcentaje_descuento": st.column_config.ProgressColumn("% Descuento", format="%.2f%%", min_value=0, max_value=max(5, df_vista['porcentaje_descuento'].max() if not df_vista.empty else 5))
        },
        use_container_width=True, hide_index=True
    )

# ==============================================================================
# EJECUCIÓN PRINCIPAL DE LA PÁGINA
# ==============================================================================

st.title("📊 Comparativa de Rendimiento de Vendedores")
st.markdown("Análisis comparativo del equipo de ventas y su gestión de descuentos.")
st.markdown("---")

# --- Nombre del artículo de descuento ---
NOMBRE_ARTICULO_DESCUENTO = "DESCUENTOS COMERCIALES" 

# --- Cálculos Principales ---
df_vinculado_fifo = calcular_vinculos_fifo(df_ventas_historico, NOMBRE_ARTICULO_DESCUENTO)
df_kpis, promedios = calcular_kpis_globales(df_ventas_historico)

# --- Contenido Principal ---
if df_kpis.empty:
    st.warning("No hay suficientes datos de ventas para generar una comparativa de KPIs.")
else:
    col1, col2 = st.columns(2)
    vendedor_sel_kpi = col1.selectbox("Seleccione un Vendedor para analizar sus KPIs:", options=sorted(df_kpis['Vendedor'].unique()))
    kpi_ranking = col2.selectbox("Seleccione una Métrica para el Ranking:", options=sorted(promedios.index))

    if vendedor_sel_kpi:
        render_radar_chart(df_kpis, promedios, vendedor_sel_kpi)
        st.markdown("---")
        render_ranking_chart(df_kpis, kpi_ranking)

# --- Sección de Descuentos ---
st.markdown("---")
if df_vinculado_fifo.empty:
    st.warning("No se encontraron datos de descuentos para analizar en el histórico.")
else:
    vendedores_con_descuento = sorted(df_vinculado_fifo['nomvendedor'].unique())
    vendedor_sel_dcto = st.selectbox("Seleccione un Vendedor para analizar sus descuentos:", options=vendedores_con_descuento)
    if vendedor_sel_dcto:
        render_tabla_descuentos(df_vinculado_fifo, vendedor_sel_dcto)
