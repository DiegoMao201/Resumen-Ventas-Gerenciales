# ==============================================================================
# SCRIPT PARA: 🧠 Centro de Control de Descuentos y Cartera
# VERSIÓN: 7.5 GERENCIAL (MERGE CORREGIDO) - 07 de Julio, 2025
# DESCRIPCIÓN: Versión final con corrección de KeyError en `groupby` al eliminar
#              la columna duplicada 'nomvendedor' antes de la unión de datos.
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import io
import numpy as np
from datetime import datetime, timedelta
import dropbox

# --- CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN DE ACCESO ---
st.set_page_config(page_title="Control de Descuentos y Cartera", page_icon="🧠", layout="wide")

st.title("🧠 Centro de Control de Descuentos y Cartera v7.5")
st.markdown("Herramienta de análisis profundo para la efectividad de descuentos, salud de cartera y gestión de vencimientos.")

if st.session_state.get('usuario') != "GERENTE":
    st.error("🔒 Acceso Exclusivo para Gerencia.")
    st.info("Por favor, inicie sesión desde la página principal para acceder a esta herramienta.")
    st.stop()

# --- LÓGICA DE CARGA DE DATOS (CACHEADA PARA EFICIENCIA) ---
@st.cache_data(ttl=3600)
def cargar_datos_fuente(dropbox_path_cobros):
    """
    Carga los datos de ventas y cobros. Renombra y estandariza las columnas
    de cobros inmediatamente después de la carga para evitar KeyErrors.
    """
    try:
        df_ventas = st.session_state.get('df_ventas')
        if df_ventas is None:
            st.error("Los datos de ventas no se encontraron en la sesión. Por favor, vuelva a la página principal y cargue los datos primero.")
            return None, None
        
        with st.spinner("Cargando y validando archivo de cobros desde Dropbox..."):
            try:
                dbx = dropbox.Dropbox(
                    app_key=st.secrets.dropbox.app_key,
                    app_secret=st.secrets.dropbox.app_secret,
                    oauth2_refresh_token=st.secrets.dropbox.refresh_token
                )
                _, res = dbx.files_download(path=dropbox_path_cobros)
                df_cobros = pd.read_excel(io.BytesIO(res.content))
                st.success("Archivo de cobros cargado exitosamente desde Dropbox.", icon="✅")

            except Exception as e:
                st.error(f"Error al conectar con Dropbox: {e}")
                st.warning("La conexión a Dropbox falló. Se usarán datos de ejemplo para continuar.")
                data_cobros = {'Serie': ['F-001'], 'Fecha Documento': ['2025-05-01'], 'Fecha Saldado': ['2025-05-20'], 'NOMBRECLIENTE': ['CLIENTE EJEMPLO'], 'NOMVENDEDOR': ['VENDEDOR EJEMPLO']}
                df_cobros = pd.DataFrame(data_cobros)
        
        column_mapping = {
            'Fecha Documento': 'fecha_emision',
            'Fecha Saldado': 'fecha_saldado',
            'NOMBRECLIENTE': 'nombre_cliente',
            'NOMVENDEDOR': 'nomvendedor'
        }
        df_cobros.rename(columns=column_mapping, inplace=True)
        
        df_cobros['fecha_emision'] = pd.to_datetime(df_cobros['fecha_emision'], errors='coerce')
        df_cobros['fecha_saldado'] = pd.to_datetime(df_cobros['fecha_saldado'], errors='coerce')
        
        return df_ventas, df_cobros
    except KeyError as e:
        st.error(f"Error de columna al cargar datos: La columna {e} no se encontró en tu archivo de cobros. Por favor, verifica que el nombre de la columna sea exactamente el esperado.")
        return None, None
    except Exception as e:
        st.error(f"Error crítico al cargar los archivos: {e}")
        return None, None

# --- LÓGICA DE PROCESAMIENTO PROFUNDO ---
@st.cache_data
def procesar_y_analizar_profundo(_df_ventas, _df_cobros, nombre_articulo_descuento, dias_pronto_pago):
    if _df_ventas is None or _df_cobros is None:
        return pd.DataFrame(), pd.DataFrame(), {}

    df_ventas = _df_ventas.copy()
    df_cobros = _df_cobros.copy()

    if 'valor_venta' in df_ventas.columns and df_ventas['valor_venta'].dtype == 'object':
         df_ventas['valor_venta'] = df_ventas['valor_venta'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    
    df_ventas['valor_venta'] = pd.to_numeric(df_ventas['valor_venta'], errors='coerce')
    df_ventas['fecha_venta'] = pd.to_datetime(df_ventas['fecha_venta'], errors='coerce')
    df_ventas.dropna(subset=['valor_venta', 'Serie', 'nombre_cliente', 'nomvendedor', 'fecha_venta'], inplace=True)
    df_cobros.dropna(subset=['Serie', 'fecha_saldado', 'fecha_emision', 'nombre_cliente'], inplace=True)

    df_facturas_raw = df_ventas[df_ventas['valor_venta'] > 0].copy()
    df_descuentos_raw = df_ventas[
        (df_ventas['nombre_articulo'] == nombre_articulo_descuento) & (df_ventas['valor_venta'] < 0)
    ].copy()
    df_descuentos_raw['monto_descontado'] = abs(df_descuentos_raw['valor_venta'])

    ventas_por_factura = df_facturas_raw.groupby('Serie').agg(
        valor_total_factura=('valor_venta', 'sum'),
        fecha_venta=('fecha_venta', 'first'),
        nombre_cliente=('nombre_cliente', 'first'),
        nomvendedor=('nomvendedor', 'first')
    ).reset_index()

    df_cobros['dias_pago'] = (df_cobros['fecha_saldado'] - df_cobros['fecha_emision']).dt.days

    # --- FIX APLICADO AQUÍ ---
    # Se elimina la columna 'nomvendedor' de df_cobros antes del merge para evitar el conflicto
    # de columnas duplicadas. Se confía en el 'nomvendedor' del archivo de ventas.
    df_cobros_sin_vendedor = df_cobros.drop(columns=['nomvendedor'], errors='ignore')
    df_pagadas_detalle = pd.merge(df_cobros_sin_vendedor, ventas_por_factura, on='Serie', how='inner')
    
    # El resto del código funciona porque 'df_pagadas_detalle' ahora tiene una sola columna 'nomvendedor'
    analisis_pagado_por_cliente = df_pagadas_detalle.groupby(['nombre_cliente', 'nomvendedor']).agg(
        dias_pago_promedio=('dias_pago', 'mean'),
        total_comprado_pagado=('valor_total_factura', 'sum'),
        numero_facturas_pagadas=('Serie', 'nunique')
    ).reset_index()

    descuentos_por_cliente = df_descuentos_raw.groupby('nombre_cliente').agg(
        total_descontado=('monto_descontado', 'sum')
    ).reset_index()
    
    analisis_pagado = pd.merge(analisis_pagado_por_cliente, descuentos_por_cliente, on='nombre_cliente', how='left')
    analisis_pagado['total_descontado'].fillna(0, inplace=True)
    
    analisis_pagado['pct_descuento'] = (analisis_pagado['total_descontado'] / analisis_pagado['total_comprado_pagado']).replace([np.inf, -np.inf], 0).fillna(0) * 100

    def clasificar_cliente_pagado(row):
        paga_a_tiempo = row['dias_pago_promedio'] <= dias_pronto_pago
        recibe_descuento = row['total_descontado'] > 0
        if paga_a_tiempo and recibe_descuento: return "✅ Justificado"
        elif paga_a_tiempo and not recibe_descuento: return "💡 Oportunidad"
        elif not paga_a_tiempo and recibe_descuento: return "❌ Crítico"
        else: return "⚠️ Alerta"

    if not analisis_pagado.empty:
        analisis_pagado['Clasificacion'] = analisis_pagado.apply(clasificar_cliente_pagado, axis=1)

    series_pagadas = df_cobros['Serie'].unique()
    df_pendientes = ventas_por_factura[~ventas_por_factura['Serie'].isin(series_pagadas)].copy()
    
    if not df_pendientes.empty:
        hoy = pd.to_datetime(datetime.now())
        df_pendientes['dias_antiguedad'] = (hoy - df_pendientes['fecha_venta']).dt.days
        def clasificar_vencimiento(dias):
            if dias <= 30: return "Corriente (0-30 días)"
            elif dias <= 60: return "Vencida (31-60 días)"
            elif dias <= 90: return "Vencida (61-90 días)"
            else: return "Vencida (+90 días)"
        df_pendientes['Rango_Vencimiento'] = df_pendientes['dias_antiguedad'].apply(clasificar_vencimiento)
        df_pendientes.rename(columns={'valor_total_factura': 'valor_total_productos'}, inplace=True)

    return analisis_pagado, df_pendientes

# ==============================================================================
# EJECUCIÓN PRINCIPAL Y RENDERIZADO
# ==============================================================================

df_ventas_raw, df_cobros_raw = cargar_datos_fuente("/data/Cobros.xlsx")

if df_ventas_raw is None or df_cobros_raw is None:
    st.error("La carga de datos falló. No se puede continuar.")
    st.stop()

st.sidebar.header("Filtros del Análisis ⚙️")

st.sidebar.subheader("Filtrar por Período")
min_date_ventas = df_ventas_raw['fecha_venta'].min().date() if not df_ventas_raw.empty else datetime.now().date()
max_date_ventas = df_ventas_raw['fecha_venta'].max().date() if not df_ventas_raw.empty else datetime.now().date()

fecha_inicio = st.sidebar.date_input("Fecha de Inicio", value=(max_date_ventas - timedelta(days=90)), min_value=min_date_ventas, max_value=max_date_ventas)
fecha_fin = st.sidebar.date_input("Fecha de Fin", value=max_date_ventas, min_value=min_date_ventas, max_value=max_date_ventas)

if fecha_inicio > fecha_fin:
    st.sidebar.error("La fecha de inicio no puede ser posterior a la fecha de fin.")
    st.stop()

fecha_inicio_ts = pd.to_datetime(fecha_inicio)
fecha_fin_ts = pd.to_datetime(fecha_fin)

df_ventas_periodo = df_ventas_raw[(df_ventas_raw['fecha_venta'] >= fecha_inicio_ts) & (df_ventas_raw['fecha_venta'] <= fecha_fin_ts)]
df_cobros_periodo = df_cobros_raw[(df_cobros_raw['fecha_saldado'] >= fecha_inicio_ts) & (df_cobros_raw['fecha_saldado'] <= fecha_fin_ts)]

st.sidebar.subheader("Filtrar por Responsable")
DIAS_PRONTO_PAGO = st.sidebar.slider("Definir 'Pronto Pago' (días)", min_value=5, max_value=90, value=30, help="Días máximos para considerar un pago como 'pronto pago'.")
vendedores_unicos = df_ventas_periodo['nomvendedor'].dropna().unique().tolist()
lista_vendedores = ['Visión Gerencial (Todos)'] + sorted(vendedores_unicos)
vendedor_seleccionado = st.sidebar.selectbox("Seleccionar Vendedor", options=lista_vendedores)

with st.spinner("Ejecutando análisis profundo de cartera..."):
    df_analisis_pagado_full, df_cartera_pendiente_full = procesar_y_analizar_profundo(
        df_ventas_raw, df_cobros_raw, "DESCUENTOS COMERCIALES", DIAS_PRONTO_PAGO
    )
    
    clientes_en_periodo = df_cobros_periodo['nombre_cliente'].unique()
    df_analisis_pagado = df_analisis_pagado_full[df_analisis_pagado_full['nombre_cliente'].isin(clientes_en_periodo)]

if vendedor_seleccionado != "Visión Gerencial (Todos)":
    df_pagado_filtrado = df_analisis_pagado[df_analisis_pagado['nomvendedor'] == vendedor_seleccionado].copy()
    df_pendiente_filtrado = df_cartera_pendiente_full[df_cartera_pendiente_full['nomvendedor'] == vendedor_seleccionado].copy()
else:
    df_pagado_filtrado = df_analisis_pagado.copy()
    df_pendiente_filtrado = df_cartera_pendiente_full.copy()

total_cartera_pendiente = df_pendiente_filtrado['valor_total_productos'].sum() if not df_pendiente_filtrado.empty else 0
total_descuentos = df_pagado_filtrado['total_descontado'].sum()
total_ventas_pagadas_periodo = df_pagado_filtrado['total_comprado_pagado'].sum()
porcentaje_descuento = (total_descuentos / total_ventas_pagadas_periodo) * 100 if total_ventas_pagadas_periodo > 0 else 0
ventas_periodo = df_ventas_periodo[df_ventas_periodo['valor_venta'] > 0]['valor_venta'].sum()
dias_periodo = (fecha_fin - fecha_inicio).days + 1 if fecha_fin >= fecha_inicio else 1
dso = (total_cartera_pendiente / ventas_periodo) * dias_periodo if ventas_periodo > 0 else 0

st.header("Indicadores Clave de Rendimiento (KPIs)")
st.info(f"Análisis para el período del **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}** para **{vendedor_seleccionado}**.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Días Venta en Calle (DSO)", f"{dso:.1f} días", help="Promedio de días que se tarda en cobrar, calculado sobre las ventas del período seleccionado vs. la cartera pendiente total.")
col2.metric("Cartera Pendiente Total", f"${total_cartera_pendiente:,.0f}", help="Monto total que los clientes del vendedor seleccionado deben a la fecha.")
col3.metric("Total Dctos. (Período)", f"${total_descuentos:,.0f}", help="Suma de descuentos a clientes cuyas facturas se pagaron en el período seleccionado.")
col4.metric("% Dcto. s/ Venta Pagada (Período)", f"{porcentaje_descuento:.2f}%", help="Porcentaje de la venta (pagada en el período) que se destinó a descuentos.")

st.markdown("---")
tab1, tab2, tab3 = st.tabs([
    "📊 **Análisis de Cartera Pagada (Efectividad Dctos.)**", 
    "⏳ **Análisis de Cartera Pendiente (Aging)**",
    "🗣️ **Conclusiones y Plan de Acción**"
])

with tab1:
    st.header(f"Análisis de Descuentos en Cartera Pagada")
    st.info("Este análisis se enfoca en las facturas **pagadas dentro del período seleccionado** para evaluar si los descuentos se justifican con un pronto pago.")
    if df_pagado_filtrado.empty:
        st.warning(f"No hay datos de facturas pagadas para los filtros seleccionados.")
    else:
        st.subheader("Comportamiento de Pago vs. % Descuento Otorgado")
        fig_scatter = px.scatter(
            df_pagado_filtrado, x='dias_pago_promedio', y='pct_descuento',
            size='total_comprado_pagado', color='Clasificacion', hover_name='nombre_cliente',
            title="Matriz de Clientes: Eficiencia de Descuentos",
            labels={'dias_pago_promedio': 'Días Promedio de Pago', 'pct_descuento': '% Descuento sobre Compra'},
            color_discrete_map={"✅ Justificado": "#28a745", "💡 Oportunidad": "#007bff", "❌ Crítico": "#dc3545", "⚠️ Alerta": "#ffc107"},
            size_max=60)
        fig_scatter.add_vline(x=DIAS_PRONTO_PAGO, line_width=3, line_dash="dash", line_color="black", annotation_text=f"Meta {DIAS_PRONTO_PAGO} días")
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        with st.expander("Ver detalle de clientes (Cartera Pagada en el Período)"):
            st.dataframe(df_pagado_filtrado.sort_values(by="total_descontado", ascending=False), use_container_width=True, hide_index=True)

with tab2:
    st.header(f"Análisis de Vencimiento de Cartera (Aging)")
    st.info("Este análisis muestra **todas** las deudas vigentes para el vendedor seleccionado, clasificadas por su antigüedad.")
    if df_pendiente_filtrado.empty:
        st.success(f"¡Felicidades! No hay cartera pendiente de cobro para '{vendedor_seleccionado}'.")
    else:
        aging_summary = df_pendiente_filtrado.groupby('Rango_Vencimiento')['valor_total_productos'].sum().reset_index()
        aging_summary.rename(columns={'valor_total_productos': 'Monto Pendiente'}, inplace=True)
        
        st.subheader("Resumen de Cartera por Antigüedad (Aging)")
        fig_pie = px.pie(
            aging_summary, names='Rango_Vencimiento', values='Monto Pendiente',
            title='Distribución de la Cartera Pendiente por Vencimiento',
            color_discrete_sequence=px.colors.sequential.Reds_r,
            category_orders={'Rango_Vencimiento': ["Corriente (0-30 días)", "Vencida (31-60 días)", "Vencida (61-90 días)", "Vencida (+90 días)"]}
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        with st.expander("Ver detalle de todas las facturas pendientes de cobro"):
            st.dataframe(df_pendiente_filtrado[['Serie', 'nombre_cliente', 'nomvendedor', 'fecha_venta', 'dias_antiguedad', 'valor_total_productos', 'Rango_Vencimiento']].sort_values(by="dias_antiguedad", ascending=False), use_container_width=True, hide_index=True)

with tab3:
    st.header("Conclusiones Automáticas y Plan de Acción")
    st.info(f"Diagnóstico generado para el período del **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}** para **{vendedor_seleccionado}**.")

    st.subheader("Diagnóstico de la Política de Descuentos (en el período)")
    if not df_pagado_filtrado.empty:
        clientes_criticos_df = df_pagado_filtrado[df_pagado_filtrado['Clasificacion'] == '❌ Crítico']
        if not clientes_criticos_df.empty:
            monto_critico = clientes_criticos_df['total_descontado'].sum()
            st.error(f"""
            **🔥 Fuga de Rentabilidad Detectada:** Se han otorgado **${monto_critico:,.0f}** en descuentos a **{len(clientes_criticos_df)}** clientes
            que pagaron en este período pero que, históricamente, incumplen la política de pronto pago (pagan en promedio después de {DIAS_PRONTO_PAGO} días).
            **Plan de Acción:**
            1.  **Revisar Inmediatamente** la asignación de descuentos para los clientes en la categoría 'Crítico'.
            2.  **Capacitar** a la fuerza de ventas sobre la importancia de alinear descuentos con el comportamiento de pago real.
            3.  **Considerar** políticas de descuento condicionales.
            """)
        else:
            st.success("✅ ¡Política de Descuentos Efectiva! No se encontraron clientes críticos en la cartera pagada para este período.", icon="🎉")
    else:
        st.info("No hay datos de cartera pagada para generar un diagnóstico sobre descuentos en este período.")

    st.subheader("Diagnóstico de la Salud de la Cartera (Total)")
    if not df_pendiente_filtrado.empty:
        cartera_vencida = df_pendiente_filtrado[df_pendiente_filtrado['dias_antiguedad'] > 30]['valor_total_productos'].sum()
        if total_cartera_pendiente > 0:
            porcentaje_vencido = (cartera_vencida / total_cartera_pendiente) * 100
            if porcentaje_vencido > 0:
                st.warning(f"""
                **💰 Riesgo de Liquidez Identificado:** El **{porcentaje_vencido:.1f}%** de la cartera pendiente (**${cartera_vencida:,.0f}**) está vencida (más de 30 días).
                **Plan de Acción:**
                1.  **Priorizar Cobro:** Enfocar la gestión de cobro en el segmento de '+90 días', que representa el mayor riesgo.
                2.  **Contacto Proactivo:** Analizar los clientes con los mayores montos pendientes en la pestaña de 'Aging' para una acción de cobro directa.
                3.  **Revisar Límites de Crédito:** Evaluar si los clientes con deudas vencidas recurrentes deben tener una revisión de sus condiciones de crédito.
                """)
            else:
                st.success("👍 ¡Cartera Corriente! Toda la cartera pendiente está al día (menos de 30 días).", icon="✅")
    else:
        st.success("👍 ¡Cartera Sana! No se registra cartera pendiente de cobro para los filtros seleccionados.", icon="✨")
