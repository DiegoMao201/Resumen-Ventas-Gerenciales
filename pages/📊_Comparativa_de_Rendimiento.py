# ==============================================================================
# SCRIPT PARA: 📊 Comparativa de Rendimiento.py
# VERSIÓN: 07 de Julio, 2025
# DESCRIPCIÓN: Versión final que implementa el modelo FIFO para asignar
#              descuentos a la factura pendiente más antigua del cliente.
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
    st.error("No se pudieron cargar los datos maestros. Vuelva a la página principal.")
    st.stop()

# --- LÓGICA DE ANÁLISIS (CEREBRO) ---

@st.cache_data
def calcular_vinculos_fifo(_df_ventas):
    """
    Aplica el modelo FIFO para vincular notas de descuento con la factura
    original más antigua y pendiente de cada cliente.
    """
    df_ventas = _df_ventas.copy()
    df_ventas['fecha_venta'] = pd.to_datetime(df_ventas['fecha_venta'])

    filtro_facturas = (df_ventas['valor_venta'] > 0) & (df_ventas['TipoDocumento'].str.contains('FACTURA', na=False, case=False))
    filtro_descuentos = (df_ventas['valor_venta'] < 0) & (df_ventas['nombre_articulo'].str.contains('DESCUENTO COMERCIAL', na=False, case=False))

    facturas = df_ventas[filtro_facturas].sort_values(by=['cliente_id', 'fecha_venta']).reset_index()
    descuentos = df_ventas[filtro_descuentos].sort_values(by=['cliente_id', 'fecha_venta'])

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
                'cumplimiento': '✅ Sí' if dias_pago <= 15 else '❌ No'
            })
            
            facturas.loc[facturas['index'] == indice_factura, 'atendida'] = True
            
    if not vinculos:
        return pd.DataFrame()

    df_resultado = pd.DataFrame(vinculos)
    df_resultado['porcentaje_descuento'] = (df_resultado['valor_descuento'] / df_resultado['valor_compra']) * 100
    return df_resultado

# --- INTERFAZ DE USUARIO (UI) ---

def render_tabla_descuentos(df_vinculado, vendedor):
    st.subheader(f"🔍 Análisis de Descuentos Otorgados por: {vendedor}")
    df_vista = df_vinculado[df_vinculado['nomvendedor'] == vendedor]

    if df_vista.empty:
        st.info(f"No se encontraron descuentos comerciales otorgados por {vendedor}.")
        return

    st.dataframe(
        df_vista,
        column_config={
            "nombre_cliente": "Cliente",
            "valor_compra": st.column_config.NumberColumn("Valor Compra", format="$ {:,.0f}"),
            "valor_descuento": st.column_config.NumberColumn("Valor Descuento", format="$ {:,.0f}"),
            "dias_pago": st.column_config.NumberColumn("Días de Pago"),
            "cumplimiento": "Cumple Política (≤15d)",
            "porcentaje_descuento": st.column_config.ProgressColumn("% Descuento", format="%.2f%%", min_value=0, max_value=max(5, df_vista['porcentaje_descuento'].max()))
        },
        use_container_width=True, hide_index=True
    )

# --- EJECUCIÓN PRINCIPAL ---

st.title("📊 Comparativa de Rendimiento de Vendedores")
st.markdown("Análisis comparativo del equipo de ventas y su gestión de descuentos.")
st.markdown("---")

# Se calcula el DF vinculado una sola vez
df_vinculado_fifo = calcular_vinculos_fifo(df_ventas_historico)

# El resto del código de esta página para los otros gráficos permanece igual
# (Se omite por brevedad, pero debe estar en tu archivo)
# ... aquí iría el código para `calcular_kpis_globales`, `render_radar_chart`, etc.
# Lo importante es la nueva función `calcular_vinculos_fifo` y la UI actualizada.

vendedores_con_descuento = sorted(df_vinculado_fifo['nomvendedor'].unique())
if not vendedores_con_descuento:
    st.warning("No se encontraron datos de descuentos para analizar en el histórico.")
    st.stop()

vendedor_seleccionado = st.selectbox(
    "Seleccione un Vendedor para analizar sus descuentos:", 
    options=vendedores_con_descuento
)

if vendedor_seleccionado:
    render_tabla_descuentos(df_vinculado_fifo, vendedor_seleccionado)
