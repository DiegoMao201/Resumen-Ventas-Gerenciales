# ==============================================================================
# SCRIPT PARA: 🧠 Análisis de Descuentos
# VERSIÓN: 3.0 DEFINITIVA - 07 de Julio, 2025
# DESCRIPCIÓN: Versión final con lógica FIFO correcta y motor de cálculo de alto
#              rendimiento. Se elimina el filtro de fecha de inicio para garantizar
#              la integridad del análisis y se añade manejo de errores de datos.
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN DE DATOS ---
st.set_page_config(page_title="Análisis de Descuentos", page_icon="🧠", layout="wide")

st.title("🧠 Análisis Estratégico de Descuentos")

if st.session_state.get('usuario') != "GERENTE":
    st.error("🔒 Acceso Exclusivo para Gerencia.")
    st.stop()

df_ventas_historico = st.session_state.get('df_ventas')
if df_ventas_historico is None or df_ventas_historico.empty:
    st.error("No se pudieron cargar los datos maestros. Vuelva a la página principal y recargue.")
    st.stop()

# ==============================================================================
# LÓGICA DE ANÁLISIS (MOTOR FIFO FINAL Y OPTIMIZADO)
# ==============================================================================

@st.cache_data
def calcular_vinculos_fifo_optimizado(_df_ventas, nombre_exacto_descuento, fecha_inicio_politica, fecha_fin_rango):
    """
    Versión Definitiva: El cálculo SIEMPRE comienza desde el inicio de la política
    para garantizar la lógica FIFO correcta. El usuario solo elige la fecha de fin.
    """
    df_ventas = _df_ventas.copy()
    df_ventas['fecha_venta'] = pd.to_datetime(df_ventas['fecha_venta'])
    
    fecha_politica = pd.to_datetime(fecha_inicio_politica)
    fecha_fin = pd.to_datetime(fecha_fin_rango)

    # 1. PREPARAR EL UNIVERSO COMPLETO DE TRANSACCIONES VÁLIDAS
    # El análisis corre desde el inicio de la política hasta la fecha fin seleccionada.
    mask_periodo_completo = (df_ventas['fecha_venta'] >= fecha_politica) & (df_ventas['fecha_venta'] <= fecha_fin)
    df_analisis = df_ventas[mask_periodo_completo]

    # 2. SEPARAR FACTURAS Y DESCUENTOS DENTRO DE ESE PERIODO COMPLETO
    filtro_facturas = (df_analisis['valor_venta'] > 0) & (df_analisis['TipoDocumento'].str.contains('FACTURA', na=False, case=False))
    filtro_descuentos = (df_analisis['valor_venta'] < 0) & (df_analisis['nombre_articulo'] == nombre_exacto_descuento)

    facturas = df_analisis[filtro_facturas].sort_values(by=['cliente_id', 'fecha_venta'])
    descuentos = df_analisis[filtro_descuentos].sort_values(by=['cliente_id', 'fecha_venta'])

    if descuentos.empty or facturas.empty:
        return pd.DataFrame()

    # 3. CREAR RANKING POR CLIENTE (La optimización de velocidad)
    facturas['rank'] = facturas.groupby('cliente_id').cumcount()
    descuentos['rank'] = descuentos.groupby('cliente_id').cumcount()

    # 4. UNIR (MERGE) POR CLIENTE Y RANK
    df_vinculado = pd.merge(
        descuentos,
        facturas,
        on=['cliente_id', 'rank'],
        suffixes=('_dcto', '_factura')
    )

    if df_vinculado.empty:
        return pd.DataFrame()

    # 5. CÁLCULOS FINALES
    df_vinculado['dias_pago'] = (df_vinculado['fecha_venta_dcto'] - df_vinculado['fecha_venta_factura']).dt.days
    df_vinculado = df_vinculado[df_vinculado['dias_pago'] >= 0] 

    df_resultado = df_vinculado.rename(columns={
        'nomvendedor_factura': 'nomvendedor', 'nombre_cliente_factura': 'nombre_cliente',
        'valor_venta_factura': 'valor_compra'
    })
    df_resultado['valor_descuento'] = abs(df_resultado['valor_venta_dcto'])
    df_resultado['cumple_politica'] = df_resultado['dias_pago'] <= 15
    df_resultado['porcentaje_descuento'] = (df_resultado['valor_descuento'] / df_resultado['valor_compra']) * 100
    
    columnas_finales = ['nomvendedor', 'nombre_cliente', 'cliente_id', 'valor_compra', 'valor_descuento', 'dias_pago', 'cumple_politica', 'porcentaje_descuento']
    return df_resultado[columnas_finales]

def generar_consejos_vendedor(kpis):
    # (Esta función no cambia)
    consejos = []
    if kpis['tasa_cumplimiento'] < 0.8:
        consejos.append(f"**Punto de Atención:** Tu tasa de cumplimiento de la política es del {kpis['tasa_cumplimiento']:.1%}. Un número importante de descuentos se otorga a pagos fuera de plazo. **Sugerencia:** Refuerza los términos de pago con los clientes antes de ofrecer el descuento.")
    else:
        consejos.append(f"**Fortaleza:** ¡Excelente gestión de la política con una tasa de cumplimiento del {kpis['tasa_cumplimiento']:.1%}! Tus clientes entienden y respetan los plazos.")
    if kpis['dias_pago_promedio'] > 15:
        consejos.append(f"**Oportunidad de Mejora:** El promedio de pago de tus clientes con descuento es de **{kpis['dias_pago_promedio']:.1f} días**. **Sugerencia:** Inicia el recordatorio de pago unos días antes del vencimiento del plazo de 15 días para asegurar el cumplimiento.")
    else:
        consejos.append(f"**Fortaleza:** Logras que tus clientes paguen en un promedio de **{kpis['dias_pago_promedio']:.1f} días** para acceder al descuento, ¡manteniendo la cartera sana!")
    return consejos

# ==============================================================================
# EJECUCIÓN PRINCIPAL Y RENDERIZADO DE UI
# ==============================================================================

# --- Constantes de la lógica de negocio ---
NOMBRE_ARTICULO_DESCUENTO = "DESCUENTOS COMERCIALES"
FECHA_INICIO_POLITICA = "2024-06-01"

# --- FILTROS INTERACTIVOS EN LA BARRA LATERAL (UI CORREGIDA) ---
st.sidebar.header("Filtros del Análisis")
st.sidebar.info("El análisis siempre empieza el 1 de Junio de 2024. Seleccione solo hasta qué fecha desea analizar.")
fecha_max_datos = df_ventas_historico['fecha_venta'].max()
fecha_min_seleccion = pd.to_datetime(FECHA_INICIO_POLITICA).date()

# El usuario solo elige la fecha de fin
fecha_fin = st.sidebar.date_input("Analizar hasta la fecha:", value=fecha_max_datos.date(), min_value=fecha_min_seleccion, max_value=fecha_max_datos.date())

if st.sidebar.button("🚀 Generar Análisis", type="primary", use_container_width=True):
    
    with st.spinner('Realizando cálculo FIFO optimizado... ¡El nuevo motor es muy rápido!'):
        df_vinculado = calcular_vinculos_fifo_optimizado(df_ventas_historico, NOMBRE_ARTICULO_DESCUENTO, FECHA_INICIO_POLITICA, fecha_fin)

    st.success(f"Análisis generado desde el **{FECHA_INICIO_POLITICA}** hasta el **{fecha_fin.strftime('%d-%b-%Y')}**.")

    if df_vinculado.empty:
        st.warning(f"No se encontraron '{NOMBRE_ARTICULO_DESCUENTO}' para el periodo seleccionado.")
        st.stop()
    
    # --- CORRECCIÓN DEL TypeError ---
    # Se eliminan filas donde 'nomvendedor' pueda ser nulo antes de usarlo en el selectbox
    df_vinculado.dropna(subset=['nomvendedor'], inplace=True)
    if df_vinculado.empty:
        st.warning("Se encontraron descuentos, pero no tienen un vendedor asociado.")
        st.stop()

    # --- Pestañas de Análisis ---
    tab1, tab2, tab3 = st.tabs(["📊 Visión General", "👨‍💼 Análisis por Vendedor", "👥 Análisis por Cliente"])

    with tab1:
        # (El código de esta pestaña no cambia)
        st.header("Indicadores Globales de la Política de Descuentos")
        total_descuentos = df_vinculado['valor_descuento'].sum()
        dias_pago_promedio_global = df_vinculado['dias_pago'].mean()
        tasa_cumplimiento_global = df_vinculado['cumple_politica'].mean()
        col1, col2, col3 = st.columns(3)
        col1.metric("Monto Total en Descuentos", f"${total_descuentos:,.0f}")
        col2.metric("Días Promedio de Pago", f"{dias_pago_promedio_global:.1f} días")
        col3.metric("Tasa de Cumplimiento (≤15d)", f"{tasa_cumplimiento_global:.1%}")
        st.markdown("---")
        st.subheader("Distribución de los Días de Pago")
        fig_hist = px.histogram(df_vinculado, x='dias_pago', nbins=30, title="Frecuencia de Pagos por Días Transcurridos")
        fig_hist.add_vline(x=15, line_width=3, line_dash="dash", line_color="red", annotation_text="Límite 15 Días")
        st.plotly_chart(fig_hist, use_container_width=True)

    with tab2:
        # (El código de esta pestaña no cambia)
        st.header("Rendimiento Individual por Vendedor")
        vendedores = sorted(df_vinculado['nomvendedor'].unique())
        vendedor_sel = st.selectbox("Seleccione un Vendedor", options=vendedores, key="sb_vendedor_dcto")
        df_vendedor = df_vinculado[df_vinculado['nomvendedor'] == vendedor_sel]
        if not df_vendedor.empty:
            kpis_vendedor = {'total_descuento': df_vendedor['valor_descuento'].sum(), 'dias_pago_promedio': df_vendedor['dias_pago'].mean(), 'tasa_cumplimiento': df_vendedor['cumple_politica'].mean()}
            col1, col2, col3 = st.columns(3)
            col1.metric(f"Monto Descuentos ({vendedor_sel})", f"${kpis_vendedor['total_descuento']:,.0f}")
            col2.metric(f"Días Promedio Pago ({vendedor_sel})", f"{kpis_vendedor['dias_pago_promedio']:.1f} días")
            col3.metric(f"Tasa Cumplimiento ({vendedor_sel})", f"{kpis_vendedor['tasa_cumplimiento']:.1%}")
            st.markdown("---")
            st.subheader("🤖 Coach Virtual: Consejos para " + vendedor_sel)
            with st.container(border=True):
                consejos = generar_consejos_vendedor(kpis_vendedor)
                for consejo in consejos: st.markdown(f"- {consejo}")
            st.subheader("Detalle de Descuentos Otorgados")
            st.dataframe(df_vendedor[['nombre_cliente', 'valor_compra', 'valor_descuento', 'dias_pago', 'cumple_politica']], use_container_width=True, hide_index=True)

    with tab3:
        # (El código de esta pestaña no cambia)
        st.header("Comportamiento de Clientes Frente al Descuento")
        kpis_cliente = df_vinculado.groupby('nombre_cliente').agg(total_descontado=('valor_descuento', 'sum'), frecuencia=('cliente_id', 'count'), dias_pago_promedio=('dias_pago', 'mean'), tasa_cumplimiento=('cumple_politica', 'mean')).reset_index()
        clientes_estrella = kpis_cliente[(kpis_cliente['tasa_cumplimiento'] >= 0.9) & (kpis_cliente['dias_pago_promedio'] <= 15)].sort_values('total_descontado', ascending=False)
        clientes_a_revisar = kpis_cliente[(kpis_cliente['tasa_cumplimiento'] < 0.5) | (kpis_cliente['dias_pago_promedio'] > 20)].sort_values('dias_pago_promedio', ascending=False)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("⭐ Clientes Estrella")
            st.caption("Pagan a tiempo consistentemente.")
            st.dataframe(clientes_estrella.head(10), use_container_width=True, hide_index=True)
        with col2:
            st.subheader("⚠️ Clientes a Revisar (Oportunistas)")
            st.caption("Reciben descuentos pero tienden a pagar fuera de plazo.")
            st.dataframe(clientes_a_revisar.head(10), use_container_width=True, hide_index=True)
else:
    st.info("⬅️ Para comenzar, seleccione hasta qué fecha desea analizar en la barra lateral y haga clic en 'Generar Análisis'.")
