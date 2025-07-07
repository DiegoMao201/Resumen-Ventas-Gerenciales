# ==============================================================================
# SCRIPT PARA: 🧠 Centro de Control de Descuentos y Cartera
# VERSIÓN: 8.3 GERENCIAL (CORRECCIÓN DE CASE-SENSITIVE) - 07 de Julio, 2025
# DESCRIPCIÓN: Versión final con ajuste en el nombre de las columnas para
#              coincidir exactamente con el archivo de Excel ('IMPORTE' en vez
#              de 'Importe'), solucionando el error de validación.
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime
import dropbox
import io

# --- 1. CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN DE ACCESO ---
st.set_page_config(page_title="Control de Descuentos y Cartera", page_icon="🧠", layout="wide")

st.title("🧠 Centro de Control de Descuentos y Cartera v8.3")
st.markdown("Herramienta de análisis profundo con cruce de datos de alta precisión para un análisis confiable.")

if st.session_state.get('usuario') != "GERENTE":
    st.error("🔒 Acceso Exclusivo para Gerencia.")
    st.info("Por favor, inicie sesión desde la página principal para acceder a esta herramienta.")
    st.stop()

# --- 2. LÓGICA DE CARGA DE DATOS (CON NOMBRES DE COLUMNA CORREGIDOS) ---
@st.cache_data(ttl=3600)
def cargar_datos_combinados(dropbox_path_cobros):
    # Carga de ventas desde la sesión
    df_ventas = st.session_state.get('df_ventas')
    if df_ventas is None:
        st.error("Los datos de ventas no se encontraron en la sesión.")
        return None, None
    
    df_ventas_copy = df_ventas.copy()
    
    # Carga de cobros granulares desde Dropbox
    try:
        with st.spinner("Cargando archivo de cobros granular desde Dropbox..."):
            dbx = dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, app_secret=st.secrets.dropbox.app_secret, oauth2_refresh_token=st.secrets.dropbox.refresh_token)
            _, res = dbx.files_download(path=dropbox_path_cobros)
            df_cobros_granular = pd.read_excel(io.BytesIO(res.content))
            st.success("Archivo de cobros granular cargado.", icon="✅")
    except Exception as e:
        st.error(f"Error crítico al cargar el archivo de cobros desde Dropbox: {e}")
        return None, None
        
    # ### CAMBIO CLAVE ### - Se ajusta la lista de columnas requeridas a los nombres exactos del archivo Excel.
    columnas_requeridas_cobros = ['Serie', 'Fecha Documento', 'Fecha Saldado', 'IMPORTE']
    if not all(col in df_cobros_granular.columns for col in columnas_requeridas_cobros):
        st.error(f"Tu archivo de cobros de Dropbox DEBE contener las columnas: {columnas_requeridas_cobros}. Columnas encontradas: {df_cobros_granular.columns.to_list()}")
        return None, None

    # ### CAMBIO CLAVE ### - Se ajusta el mapeo para usar 'IMPORTE' como origen.
    df_cobros_granular.rename(columns={'Fecha Documento': 'fecha_documento', 'Fecha Saldado': 'fecha_saldado', 'IMPORTE': 'importe'}, inplace=True)
    
    # Normalización de fechas a solo YYYY-MM-DD
    df_ventas_copy['fecha_venta_norm'] = pd.to_datetime(df_ventas_copy['fecha_venta'], errors='coerce').dt.normalize()
    df_cobros_granular['fecha_documento_norm'] = pd.to_datetime(df_cobros_granular['fecha_documento'], errors='coerce').dt.normalize()
    df_cobros_granular['fecha_saldado'] = pd.to_datetime(df_cobros_granular['fecha_saldado'], errors='coerce').dt.normalize()
    
    # Creación de la llave compuesta para un cruce perfecto
    df_ventas_copy['llave_factura'] = df_ventas_copy['Serie'].astype(str) + "_" + df_ventas_copy['fecha_venta_norm'].astype(str)
    df_cobros_granular['llave_factura'] = df_cobros_granular['Serie'].astype(str) + "_" + df_cobros_granular['fecha_documento_norm'].astype(str)
    
    df_cobros_esencial = df_cobros_granular[['llave_factura', 'fecha_saldado']].dropna().drop_duplicates(subset=['llave_factura'])

    # Limpieza de columnas numéricas en ventas
    numeric_cols_ventas = ['valor_venta', 'costo_unitario', 'unidades_vendidas']
    for col in numeric_cols_ventas:
        df_ventas_copy[col] = pd.to_numeric(df_ventas_copy[col], errors='coerce')

    df_ventas_copy.dropna(subset=['fecha_venta_norm', 'Serie', 'llave_factura'], inplace=True)
    
    return df_ventas_copy, df_cobros_esencial

# --- 3. LÓGICA DE PROCESAMIENTO PROFUNDO (CON LLAVE COMPUESTA) ---
@st.cache_data
def procesar_y_analizar_profundo(_df_ventas_periodo, _df_cobros_global, dias_pronto_pago):
    if _df_ventas_periodo is None or _df_cobros_global is None or _df_ventas_periodo.empty:
        return pd.DataFrame(), pd.DataFrame()

    df_ventas = _df_ventas_periodo.copy()
    
    filtro_descuento = (df_ventas['nombre_articulo'].str.contains('DESCUENTO', na=False, case=False)) & \
                       (df_ventas['nombre_articulo'].str.contains('COMERCIAL', na=False, case=False))
    
    df_productos_raw = df_ventas[~filtro_descuento]
    df_descuentos_raw = df_ventas[filtro_descuento]

    df_productos_raw['costo_total_linea'] = df_productos_raw['costo_unitario'].fillna(0) * df_productos_raw['unidades_vendidas'].fillna(0)
    df_productos_raw['margen_bruto'] = df_productos_raw['valor_venta'] - df_productos_raw['costo_total_linea']
    
    ventas_por_factura = df_productos_raw.groupby('llave_factura').agg(
        Serie=('Serie', 'first'),
        valor_total_factura=('valor_venta', 'sum'),
        margen_total_factura=('margen_bruto', 'sum'),
        fecha_venta=('fecha_venta_norm', 'first'),
        nombre_cliente=('nombre_cliente', 'first'),
        nomvendedor=('nomvendedor', 'first')
    ).reset_index()

    descuentos_por_factura = df_descuentos_raw.groupby('llave_factura').agg(
        monto_descontado=('valor_venta', 'sum')
    ).reset_index()
    descuentos_por_factura['monto_descontado'] = abs(descuentos_por_factura['monto_descontado'])

    ventas_consolidadas = pd.merge(ventas_por_factura, descuentos_por_factura, on='llave_factura', how='left')
    ventas_consolidadas['monto_descontado'].fillna(0, inplace=True)

    df_pagadas = pd.merge(ventas_consolidadas, _df_cobros_global, on='llave_factura', how='inner')
    
    if not df_pagadas.empty:
        df_pagadas['dias_pago'] = (df_pagadas['fecha_saldado'] - df_pagadas['fecha_venta']).dt.days
    
    series_pagadas = df_pagadas['llave_factura'].unique()
    df_pendientes = ventas_consolidadas[~ventas_consolidadas['llave_factura'].isin(series_pagadas)].copy()
    
    if not df_pendientes.empty:
        hoy = pd.to_datetime(datetime.now())
        df_pendientes['dias_antiguedad'] = (hoy - df_pendientes['fecha_venta']).dt.days
        def clasificar_vencimiento(dias):
            if dias <= 30: return "Corriente (0-30 días)"
            elif dias <= 60: return "Vencida (31-60 días)"
            elif dias <= 90: return "Vencida (61-90 días)"
            else: return "Vencida (+90 días)"
        df_pendientes['Rango_Vencimiento'] = df_pendientes['dias_antiguedad'].apply(clasificar_vencimiento)

    if not df_pagadas.empty:
        analisis_pagado_por_cliente = df_pagadas.groupby(['nombre_cliente', 'nomvendedor']).agg(
            dias_pago_promedio=('dias_pago', 'mean'),
            total_comprado_pagado=('valor_total_factura', 'sum'),
            total_descontado=('monto_descontado', 'sum'),
            margen_total_generado=('margen_total_factura', 'sum'),
            numero_facturas_pagadas=('llave_factura', 'nunique')
        ).reset_index()
        
        analisis_pagado_por_cliente['pct_descuento'] = (analisis_pagado_por_cliente['total_descontado'] / analisis_pagado_por_cliente['total_comprado_pagado']).replace([np.inf, -np.inf], 0).fillna(0) * 100
        analisis_pagado_por_cliente['pct_margen'] = (analisis_pagado_por_cliente['margen_total_generado'] / analisis_pagado_por_cliente['total_comprado_pagado']).replace([np.inf, -np.inf], 0).fillna(0) * 100

        def clasificar_cliente_pagado(row):
            paga_a_tiempo = row['dias_pago_promedio'] <= dias_pronto_pago
            recibe_descuento = row['total_descontado'] > 0
            if paga_a_tiempo and recibe_descuento: return "✅ Justificado"
            elif paga_a_tiempo and not recibe_descuento: return "💡 Oportunidad"
            elif not paga_a_tiempo and recibe_descuento: return "❌ Crítico"
            else: return "⚠️ Alerta"
            
        analisis_pagado_por_cliente['Clasificacion'] = analisis_pagado_por_cliente.apply(clasificar_cliente_pagado, axis=1)
        
        return analisis_pagado_por_cliente, df_pendientes
    else:
        return pd.DataFrame(), df_pendientes

# ==============================================================================
# 4. EJECUCIÓN PRINCIPAL Y RENDERIZADO DE LA UI
# ==============================================================================

df_ventas_raw, df_cobros_granular_raw = cargar_datos_combinados("/data/Cobros.xlsx")

if df_ventas_raw is None or df_cobros_granular_raw is None:
    st.stop()

st.sidebar.header("Filtros del Análisis ⚙️")

min_date = df_ventas_raw['fecha_venta_norm'].min().date()
max_date = df_ventas_raw['fecha_venta_norm'].max().date()

fecha_inicio = st.sidebar.date_input("Fecha de Inicio", value=max_date.replace(day=1), min_value=min_date, max_value=max_date)
fecha_fin = st.sidebar.date_input("Fecha de Fin", value=max_date, min_value=min_date, max_value=max_date)

if fecha_inicio > fecha_fin:
    st.sidebar.error("La fecha de inicio no puede ser posterior a la fecha de fin.")
    st.stop()

df_ventas_periodo = df_ventas_raw[
    (df_ventas_raw['fecha_venta_norm'].dt.date >= fecha_inicio) & 
    (df_ventas_raw['fecha_venta_norm'].dt.date <= fecha_fin)
]

vendedores_unicos = ['Visión Gerencial (Todos)'] + sorted(df_ventas_periodo['nomvendedor'].dropna().unique().tolist())
vendedor_seleccionado = st.sidebar.selectbox("Seleccionar Vendedor", options=vendedores_unicos)

DIAS_PRONTO_PAGO = st.sidebar.slider("Definir 'Pronto Pago' (días)", min_value=5, max_value=90, value=30, help="Días máximos para considerar un pago como 'pronto pago'.")

if vendedor_seleccionado != "Visión Gerencial (Todos)":
    df_ventas_filtrado = df_ventas_periodo[df_ventas_periodo['nomvendedor'] == vendedor_seleccionado]
else:
    df_ventas_filtrado = df_ventas_periodo

with st.spinner("Ejecutando análisis profundo de cartera..."):
    df_analisis_pagado, df_cartera_pendiente = procesar_y_analizar_profundo(
        df_ventas_filtrado, df_cobros_granular_raw, DIAS_PRONTO_PAGO
    )

total_cartera_pendiente = df_cartera_pendiente['valor_total_factura'].sum() if not df_cartera_pendiente.empty else 0
total_descuentos_periodo = df_analisis_pagado['total_descontado'].sum() if not df_analisis_pagado.empty else 0
total_ventas_pagadas_periodo = df_analisis_pagado['total_comprado_pagado'].sum() if not df_analisis_pagado.empty else 0
porcentaje_descuento_general = (total_descuentos_periodo / total_ventas_pagadas_periodo) * 100 if total_ventas_pagadas_periodo > 0 else 0
ventas_del_periodo_kpi = df_ventas_filtrado[~df_ventas_filtrado['nombre_articulo'].str.contains('DESCUENTO', na=False, case=False)]['valor_venta'].sum()
dias_periodo = (fecha_fin - fecha_inicio).days + 1
dso = (total_cartera_pendiente / ventas_del_periodo_kpi) * dias_periodo if ventas_del_periodo_kpi > 0 else 0

st.header("Indicadores Clave de Rendimiento (KPIs)")
st.info(f"Análisis para el período del **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}** para **{vendedor_seleccionado}**.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Días Venta en Calle (DSO)", f"{dso:.1f} días")
col2.metric("Cartera Pendiente Total", f"${total_cartera_pendiente:,.0f}")
col3.metric("Total Dctos. (Fact. Pagadas)", f"${total_descuentos_periodo:,.0f}")
col4.metric("% Dcto. s/ Venta Pagada", f"{porcentaje_descuento_general:.2f}%")

st.markdown("---")
tab1, tab2, tab3 = st.tabs([
    "📊 **Análisis de Cartera Pagada (Efectividad Dctos.)**", 
    "⏳ **Análisis de Cartera Pendiente (Aging)**",
    "🗣️ **Conclusiones y Plan de Acción**"
])

with tab1:
    st.header(f"Análisis de Descuentos en Cartera Pagada")
    if df_analisis_pagado.empty:
        st.warning(f"No hay datos de facturas pagadas para los filtros seleccionados.")
    else:
        df_scatter_data = df_analisis_pagado[df_analisis_pagado['total_comprado_pagado'] > 0].copy()
        if df_scatter_data.empty:
            st.warning("No hay clientes con un valor de compra positivo para mostrar en el gráfico.")
        else:
            st.subheader("Comportamiento de Pago vs. % Descuento Otorgado")
            fig_scatter = px.scatter(
                df_scatter_data, x='dias_pago_promedio', y='pct_descuento',
                size='total_comprado_pagado', color='Clasificacion', hover_name='nombre_cliente',
                title="Matriz de Clientes: Eficiencia de Descuentos",
                labels={'dias_pago_promedio': 'Días Promedio de Pago', 'pct_descuento': '% Descuento sobre Compra', 'pct_margen': 'Margen (%)'},
                color_discrete_map={"✅ Justificado": "#28a745", "💡 Oportunidad": "#007bff", "❌ Crítico": "#dc3545", "⚠️ Alerta": "#ffc107"},
                hover_data=['pct_margen', 'total_descontado'],
                size_max=60)
            fig_scatter.add_vline(x=DIAS_PRONTO_PAGO, line_width=3, line_dash="dash", line_color="black", annotation_text=f"Meta {DIAS_PRONTO_PAGO} días")
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        with st.expander("Ver detalle completo de clientes (Cartera Pagada)"):
            st.dataframe(df_analisis_pagado.sort_values(by="total_descontado", ascending=False), use_container_width=True, hide_index=True)

with tab2:
    st.header(f"Análisis de Vencimiento de Cartera (Aging)")
    if df_cartera_pendiente.empty:
        st.success(f"¡Felicidades! No hay cartera pendiente de cobro para los filtros seleccionados.")
    else:
        aging_summary = df_cartera_pendiente.groupby('Rango_Vencimiento')['valor_total_factura'].sum().reset_index()
        st.subheader("Resumen de Cartera por Antigüedad (Aging)")
        fig_pie = px.pie(
            aging_summary, names='Rango_Vencimiento', values='valor_total_factura',
            title='Distribución de la Cartera Pendiente por Vencimiento',
            color_discrete_sequence=px.colors.sequential.Reds_r,
            category_orders={'Rango_Vencimiento': ["Corriente (0-30 días)", "Vencida (31-60 días)", "Vencida (61-90 días)", "Vencida (+90 días)"]}
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        with st.expander("Ver detalle de todas las facturas pendientes de cobro"):
            st.dataframe(df_cartera_pendiente[['Serie', 'nombre_cliente', 'nomvendedor', 'fecha_venta', 'dias_antiguedad', 'valor_total_factura', 'Rango_Vencimiento']].sort_values(by="dias_antiguedad", ascending=False), use_container_width=True, hide_index=True)

with tab3:
    st.header("Conclusiones Automáticas y Plan de Acción")
    st.info(f"Diagnóstico generado para el período y vendedor seleccionados.")
    st.subheader("Diagnóstico de la Política de Descuentos")
    if not df_analisis_pagado.empty:
        clientes_criticos_df = df_analisis_pagado[df_analisis_pagado['Clasificacion'] == '❌ Crítico']
        if not clientes_criticos_df.empty:
            monto_critico = clientes_criticos_df['total_descontado'].sum()
            st.error(f"""
            **🔥 Fuga de Rentabilidad Detectada:** Se han otorgado **${monto_critico:,.0f}** en descuentos a **{len(clientes_criticos_df)}** clientes
            que, aunque pagaron, incumplen la política de pronto pago (pagan en promedio después de {DIAS_PRONTO_PAGO} días).
            **Plan de Acción:**
            1.  **Revisar Inmediatamente** la asignación de descuentos para los clientes en la categoría 'Crítico'.
            2.  **Alinear Descuentos con Rentabilidad:** Verificar si estos clientes críticos son al menos rentables (ver columna `pct_margen`).
            3.  **Implementar Descuentos Condicionales:** Proponer descuentos por pronto pago que se apliquen *después* de verificar el pago a tiempo.
            """)
        else:
            st.success("✅ ¡Política de Descuentos Efectiva! No se encontraron clientes críticos.", icon="🎉")
    else:
        st.info("No hay datos de cartera pagada para generar un diagnóstico sobre descuentos en este período.")

    st.subheader("Diagnóstico de la Salud de la Cartera")
    if not df_cartera_pendiente.empty:
        cartera_vencida = df_cartera_pendiente[df_cartera_pendiente['dias_antiguedad'] > 30]['valor_total_factura'].sum()
        if total_cartera_pendiente > 0:
            porcentaje_vencido = (cartera_vencida / total_cartera_pendiente) * 100
            if porcentaje_vencido > 0:
                st.warning(f"""
                **💰 Riesgo de Liquidez Identificado:** El **{porcentaje_vencido:.1f}%** de la cartera pendiente (**${cartera_vencida:,.0f}**) está vencida.
                **Plan de Acción:**
                1.  **Priorizar Cobro:** Enfocar la gestión de cobro en los segmentos más antiguos.
                2.  **Contacto Proactivo:** Analizar los clientes con los mayores montos pendientes en la pestaña de 'Aging' para una acción directa.
                3.  **Revisar Límites de Crédito:** Evaluar las condiciones de crédito para clientes con deudas vencidas recurrentes.
                """)
            else:
                st.success("👍 ¡Cartera Corriente! Toda la cartera pendiente originada en este periodo está al día.", icon="✅")
    else:
        st.success("👍 ¡Cartera Sana! No se registra cartera pendiente de cobro.", icon="✨")
