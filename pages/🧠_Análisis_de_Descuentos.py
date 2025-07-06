# ==============================================================================
# SCRIPT PARA: 🧠 Análisis de Descuentos
# VERSIÓN: 1.0 - 07 de Julio, 2025
# DESCRIPCIÓN: Dashboard avanzado para el análisis estratégico de la política
#              de descuentos comerciales por pronto pago.
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN DE DATOS ---
st.set_page_config(page_title="Análisis de Descuentos", page_icon="🧠", layout="wide")

st.title("🧠 Análisis Estratégico de Descuentos")
st.markdown("Evaluación profunda de la política de descuentos por pronto pago, su impacto y la gestión del equipo.")

if st.session_state.get('usuario') != "GERENTE":
    st.error("🔒 Acceso Exclusivo para Gerencia.")
    st.stop()

df_ventas_historico = st.session_state.get('df_ventas')
if df_ventas_historico is None or df_ventas_historico.empty:
    st.error("No se pudieron cargar los datos maestros. Vuelva a la página principal y recargue.")
    st.stop()

# --- LÓGICA DE ANÁLISIS (CEREBRO) ---

@st.cache_data
def calcular_vinculos_fifo(_df_ventas):
    """
    Aplica el modelo FIFO para vincular notas de descuento con la factura
    original más antigua y pendiente de cada cliente.
    Esta función es el corazón del análisis.
    """
    df_ventas = _df_ventas.copy()
    df_ventas['fecha_venta'] = pd.to_datetime(df_ventas['fecha_venta'])

    filtro_facturas = (df_ventas['valor_venta'] > 0) & (df_ventas['TipoDocumento'].str.contains('FACTURA', na=False, case=False))
    filtro_descuentos = (df_ventas['valor_venta'] < 0) & (df_ventas['nombre_articulo'].str.contains('DESCUENTO COMERCIAL', na=False, case=False))

    facturas = df_ventas[filtro_facturas].sort_values(by=['cliente_id', 'fecha_venta']).reset_index()
    descuentos = df_ventas[filtro_descuentos].sort_values(by=['cliente_id', 'fecha_venta'])

    if descuentos.empty or facturas.empty:
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
                'cliente_id': factura_a_vincular['cliente_id'],
                'valor_compra': factura_a_vincular['valor_venta'],
                'valor_descuento': abs(descuento['valor_venta']),
                'dias_pago': dias_pago
            })
            
            facturas.loc[facturas['index'] == indice_factura, 'atendida'] = True
            
    if not vinculos:
        return pd.DataFrame()

    df_resultado = pd.DataFrame(vinculos)
    df_resultado['cumple_politica'] = df_resultado['dias_pago'] <= 15
    return df_resultado

def generar_consejos_vendedor(kpis):
    consejos = []
    if kpis['tasa_cumplimiento'] < 0.8:
        consejos.append(f"**Punto de Atención:** Tu tasa de cumplimiento de la política es del {kpis['tasa_cumplimiento']:.1%}. Esto indica que una porción significativa de los descuentos se otorga a pagos fuera de los 15 días. **Sugerencia:** Refuerza los términos de pago con los clientes antes de ofrecer el descuento.")
    else:
        consejos.append(f"**Fortaleza:** ¡Excelente gestión de la política con una tasa de cumplimiento del {kpis['tasa_cumplimiento']:.1%}! Tus clientes entienden y respetan los plazos.")

    if kpis['dias_pago_promedio'] > 15:
        consejos.append(f"**Oportunidad de Mejora:** El promedio de pago de tus clientes con descuento es de **{kpis['dias_pago_promedio']:.1f} días**. **Sugerencia:** Inicia el recordatorio de pago unos días antes del vencimiento del plazo de 15 días para asegurar el cumplimiento.")
    else:
        consejos.append(f"**Fortaleza:** Logras que tus clientes paguen en un promedio de **{kpis['dias_pago_promedio']:.1f} días** para acceder al descuento, ¡manteniendo la cartera sana!")
        
    return consejos

# --- EJECUCIÓN PRINCIPAL Y RENDERIZADO DE UI ---

df_vinculado = calcular_vinculos_fifo(df_ventas_historico)

if df_vinculado.empty:
    st.warning("No se encontraron datos suficientes para realizar el análisis de descuentos.")
    st.stop()

# --- Pestañas de Análisis ---
tab1, tab2, tab3 = st.tabs(["📊 Visión General", "👨‍💼 Análisis por Vendedor", "👥 Análisis por Cliente"])

with tab1:
    st.header("Indicadores Globales de la Política de Descuentos")
    
    total_descuentos = df_vinculado['valor_descuento'].sum()
    dias_pago_promedio_global = df_vinculado['dias_pago'].mean()
    tasa_cumplimiento_global = df_vinculado['cumple_politica'].mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Monto Total en Descuentos", f"${total_descuentos:,.0f}", help="Suma de todos los descuentos comerciales otorgados.")
    col2.metric("Días Promedio de Pago", f"{dias_pago_promedio_global:.1f} días", help="Promedio de días que tardan los clientes en pagar para recibir el descuento.")
    col3.metric("Tasa de Cumplimiento (≤15d)", f"{tasa_cumplimiento_global:.1%}", help="Porcentaje de descuentos que se otorgaron cumpliendo la política.")

    st.markdown("---")
    st.subheader("Distribución de los Días de Pago")
    st.info("Este gráfico muestra cuántos descuentos se dan en cada rango de días. Idealmente, la mayoría de las barras deberían estar a la izquierda de la línea roja (15 días).")
    
    fig = px.histogram(df_vinculado, x='dias_pago', nbins=30, title="Frecuencia de Pagos por Días Transcurridos")
    fig.add_vline(x=15, line_width=3, line_dash="dash", line_color="red", annotation_text="Límite 15 Días")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Rendimiento Individual por Vendedor")
    
    vendedores = sorted(df_vinculado['nomvendedor'].unique())
    vendedor_sel = st.selectbox("Seleccione un Vendedor", options=vendedores)
    
    df_vendedor = df_vinculado[df_vinculado['nomvendedor'] == vendedor_sel]
    
    if not df_vendedor.empty:
        kpis_vendedor = {
            'total_descuento': df_vendedor['valor_descuento'].sum(),
            'dias_pago_promedio': df_vendedor['dias_pago'].mean(),
            'tasa_cumplimiento': df_vendedor['cumple_politica'].mean()
        }

        col1, col2, col3 = st.columns(3)
        col1.metric(f"Monto Descuentos ({vendedor_sel})", f"${kpis_vendedor['total_descuento']:,.0f}")
        col2.metric(f"Días Promedio Pago ({vendedor_sel})", f"{kpis_vendedor['dias_pago_promedio']:.1f} días")
        col3.metric(f"Tasa Cumplimiento ({vendedor_sel})", f"{kpis_vendedor['tasa_cumplimiento']:.1%}")

        st.markdown("---")
        st.subheader("🤖 Coach Virtual: Consejos para " + vendedor_sel)
        with st.container(border=True):
            consejos = generar_consejos_vendedor(kpis_vendedor)
            for consejo in consejos:
                st.markdown(f"- {consejo}")

        st.subheader("Detalle de Descuentos Otorgados")
        st.dataframe(df_vendedor[['nombre_cliente', 'valor_compra', 'valor_descuento', 'dias_pago']], use_container_width=True, hide_index=True)

with tab3:
    st.header("Comportamiento de Clientes Frente al Descuento")
    st.info("Identifica a tus mejores clientes y aquellos cuya gestión de pagos podría mejorar.")

    kpis_cliente = df_vinculado.groupby('nombre_cliente').agg(
        total_descontado=('valor_descuento', 'sum'),
        frecuencia=('cliente_id', 'count'),
        dias_pago_promedio=('dias_pago', 'mean'),
        tasa_cumplimiento=('cumple_politica', 'mean')
    ).sort_values(by='total_descontado', ascending=False)
    
    # Segmentación de clientes
    clientes_estrella = kpis_cliente[(kpis_cliente['tasa_cumplimiento'] >= 0.9) & (kpis_cliente['dias_pago_promedio'] <= 15)].sort_values('total_descontado', ascending=False)
    clientes_a_revisar = kpis_cliente[(kpis_cliente['tasa_cumplimiento'] < 0.5) | (kpis_cliente['dias_pago_promedio'] > 20)].sort_values('dias_pago_promedio', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("⭐ Clientes Estrella")
        st.caption("Pagan a tiempo consistentemente y aprovechan la política correctamente.")
        st.dataframe(clientes_estrella.head(10), use_container_width=True)

    with col2:
        st.subheader("⚠️ Clientes a Revisar")
        st.caption("Reciben descuentos pero tienden a pagar fuera de plazo.")
        st.dataframe(clientes_a_revisar.head(10), use_container_width=True)
