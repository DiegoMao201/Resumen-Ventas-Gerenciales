# ==============================================================================
# SCRIPT UNIFICADO PARA: 🧠 Centro de Control de Descuentos y Cartera v11.0
# VERSIÓN: CORREGIDA Y ESTRATÉGICA (VERSIÓN COMPLETA) - 12 de Julio, 2025
# DESCRIPCIÓN: Se corrige el error conceptual en el cálculo de descuentos,
#              separando el total otorgado del análisis de cartera pagada.
#              Ahora los KPIs reflejan la realidad del negocio.
#              Esta es la versión completa, línea por línea.
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import dropbox
import io

# --- 1. CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN DE ACCESO ---
st.set_page_config(page_title="Control Estratégico de Cartera", page_icon="🧠", layout="wide")

st.title("🧠 Control Estratégico de Cartera y Descuentos v11.0")

if st.session_state.get('usuario') != "GERENTE":
    st.error("🔒 Acceso Exclusivo para Gerencia.")
    st.info("Por favor, inicie sesión desde la página principal para acceder a esta herramienta.")
    st.stop()

# --- 2. LÓGICA DE CARGA DE DATOS ---
@st.cache_data(ttl=3600)
def cargar_datos_combinados(dropbox_path_cobros):
    df_ventas = st.session_state.get('df_ventas')
    if df_ventas is None or df_ventas.empty:
        st.error("Los datos de ventas no se encontraron en la sesión. Por favor, cargue los datos en la página principal.")
        return None, None

    df_ventas_copy = df_ventas.copy()

    try:
        with st.spinner("Cargando y validando archivo de cobros desde Dropbox..."):
            dbx = dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, app_secret=st.secrets.dropbox.app_secret, oauth2_refresh_token=st.secrets.dropbox.refresh_token)
            _, res = dbx.files_download(path=dropbox_path_cobros)
            df_cobros_granular = pd.read_excel(io.BytesIO(res.content))
    except Exception as e:
        st.error(f"Error crítico al cargar el archivo de cobros desde Dropbox: {e}")
        return None, None

    columnas_requeridas_cobros = ['Serie', 'Fecha Documento', 'Fecha Saldado', 'IMPORTE']
    if not all(col in df_cobros_granular.columns for col in columnas_requeridas_cobros):
        st.error(f"El archivo de cobros de Dropbox DEBE contener las columnas: {columnas_requeridas_cobros}. Columnas encontradas: {df_cobros_granular.columns.to_list()}")
        return None, None

    df_cobros_granular.rename(columns={'Fecha Documento': 'fecha_documento', 'Fecha Saldado': 'fecha_saldado', 'IMPORTE': 'importe'}, inplace=True)
    df_ventas_copy['fecha_venta_norm'] = pd.to_datetime(df_ventas_copy['fecha_venta'], errors='coerce').dt.normalize()
    df_cobros_granular['fecha_documento_norm'] = pd.to_datetime(df_cobros_granular['fecha_documento'], errors='coerce').dt.normalize()
    df_cobros_granular['fecha_saldado'] = pd.to_datetime(df_cobros_granular['fecha_saldado'], errors='coerce').dt.normalize()
    df_ventas_copy['llave_factura'] = df_ventas_copy['Serie'].astype(str) + "_" + df_ventas_copy['fecha_venta_norm'].astype(str)
    df_cobros_granular['llave_factura'] = df_cobros_granular['Serie'].astype(str) + "_" + df_cobros_granular['fecha_documento_norm'].astype(str)
    df_cobros_esencial = df_cobros_granular[['llave_factura', 'fecha_saldado']].dropna().drop_duplicates(subset=['llave_factura'])
    numeric_cols = ['valor_venta', 'costo_unitario', 'unidades_vendidas']
    for col in numeric_cols:
        df_ventas_copy[col] = pd.to_numeric(df_ventas_copy[col], errors='coerce').fillna(0)
    df_ventas_copy.dropna(subset=['fecha_venta_norm', 'Serie', 'llave_factura'], inplace=True)
    return df_ventas_copy, df_cobros_esencial

# --- 3. LÓGICA DE PROCESAMIENTO PROFUNDO (CORREGIDA) ---
@st.cache_data
def procesar_y_analizar_profundo(_df_ventas_periodo, _df_cobros_global, dias_politica_pago):
    if _df_ventas_periodo is None or _df_ventas_periodo.empty:
        return pd.DataFrame(), pd.DataFrame(), 0, 0, 0

    df_ventas = _df_ventas_periodo.copy()

    filtro_descuento = (df_ventas['nombre_articulo'].str.upper().str.contains('DESCUENTO', na=False)) & \
                       (df_ventas['nombre_articulo'].str.upper().str.contains('COMERCIAL', na=False))

    df_productos_raw = df_ventas[~filtro_descuento]
    df_descuentos_raw = df_ventas[filtro_descuento]

    # --- CÁLCULOS GLOBALES SOBRE TODO EL PERÍODO ---
    venta_bruta_total = df_productos_raw['valor_venta'].sum()
    margen_bruto_total = (df_productos_raw['valor_venta'] - (df_productos_raw['costo_unitario'] * df_productos_raw['unidades_vendidas'])).sum()
    total_descuentos_periodo_completo = abs(df_descuentos_raw['valor_venta'].sum())

    # --- ANÁLISIS A NIVEL FACTURA PARA CRUCE CON CARTERA ---
    df_productos_raw['costo_total_linea'] = df_productos_raw['costo_unitario'] * df_productos_raw['unidades_vendidas']
    df_productos_raw['margen_bruto'] = df_productos_raw['valor_venta'] - df_productos_raw['costo_total_linea']

    ventas_por_factura = df_productos_raw.groupby('llave_factura').agg(
        valor_total_factura=('valor_venta', 'sum'),
        margen_total_factura=('margen_bruto', 'sum'),
        fecha_venta=('fecha_venta_norm', 'first'),
        nombre_cliente=('nombre_cliente', 'first'),
    ).reset_index()

    descuentos_por_factura = df_descuentos_raw.groupby('llave_factura').agg(monto_descontado=('valor_venta', 'sum')).reset_index()
    descuentos_por_factura['monto_descontado'] = abs(descuentos_por_factura['monto_descontado'])
    ventas_consolidadas = pd.merge(ventas_por_factura, descuentos_por_factura, on='llave_factura', how='left').fillna(0)

    # --- ANÁLISIS DEL SUBCONJUNTO PAGADO ---
    df_pagadas = pd.merge(ventas_consolidadas, _df_cobros_global, on='llave_factura', how='inner')
    if not df_pagadas.empty:
        df_pagadas['dias_pago'] = (df_pagadas['fecha_saldado'] - df_pagadas['fecha_venta']).dt.days
        df_pagadas.fillna({'dias_pago': 0}, inplace=True)

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

    df_clientes_pagados = pd.DataFrame()
    if not df_pagadas.empty:
        df_clientes_pagados = df_pagadas.groupby('nombre_cliente').agg(
            dias_pago_promedio=('dias_pago', 'mean'),
            total_comprado_pagado=('valor_total_factura', 'sum'),
            total_descontado=('monto_descontado', 'sum'),
            margen_total_generado=('margen_total_factura', 'sum'),
        ).reset_index()

        df_clientes_pagados['pct_descuento'] = (df_clientes_pagados['total_descontado'] / df_clientes_pagados['total_comprado_pagado']).replace([np.inf, -np.inf], 0).fillna(0) * 100
        df_clientes_pagados['pct_margen'] = (df_clientes_pagados['margen_total_generado'] / df_clientes_pagados['total_comprado_pagado']).replace([np.inf, -np.inf], 0).fillna(0) * 100
        
        def clasificar_cliente_pagado(row):
            paga_a_tiempo = row['dias_pago_promedio'] <= dias_politica_pago
            recibe_descuento = row['total_descontado'] > 0
            if paga_a_tiempo and recibe_descuento: return "✅ Justificado"
            elif paga_a_tiempo and not recibe_descuento: return "💡 Oportunidad"
            elif not paga_a_tiempo and recibe_descuento: return "❌ Crítico"
            else: return "⚠️ Alerta"
        df_clientes_pagados['Clasificacion'] = df_clientes_pagados.apply(clasificar_cliente_pagado, axis=1)

    return df_clientes_pagados, df_pendientes, venta_bruta_total, margen_bruto_total, total_descuentos_periodo_completo

# ==============================================================================
# 4. EJECUCIÓN PRINCIPAL Y RENDERIZADO DE LA UI
# ==============================================================================

# --- Carga de datos ---
df_ventas_raw, df_cobros_granular_raw = cargar_datos_combinados("/data/Cobros.xlsx")

if df_ventas_raw is None:
    st.stop()

# --- Filtros en la barra lateral ---
st.sidebar.header("Filtros del Análisis ⚙️")
min_date, max_date = df_ventas_raw['fecha_venta_norm'].min().date(), df_ventas_raw['fecha_venta_norm'].max().date()

fecha_inicio = st.sidebar.date_input("Fecha de Inicio", value=max_date.replace(day=1), min_value=min_date, max_value=max_date)
fecha_fin = st.sidebar.date_input("Fecha de Fin", value=max_date, min_value=min_date, max_value=max_date)

if fecha_inicio > fecha_fin:
    st.sidebar.error("La fecha de inicio no puede ser posterior a la fecha de fin.")
    st.stop()

df_ventas_periodo = df_ventas_raw[(df_ventas_raw['fecha_venta_norm'].dt.date >= fecha_inicio) & (df_ventas_raw['fecha_venta_norm'].dt.date <= fecha_fin)]
vendedores_unicos = ['Visión Gerencial (Todos)'] + sorted(df_ventas_periodo['nomvendedor'].dropna().unique().tolist())
vendedor_seleccionado = st.sidebar.selectbox("Seleccionar Vendedor o Visión General", options=vendedores_unicos)
DIAS_POLITICA_PAGO = 30
st.sidebar.info(f"Política de Pronto Pago fijada en **{DIAS_POLITICA_PAGO} días**.")

if vendedor_seleccionado != "Visión Gerencial (Todos)":
    df_ventas_filtrado = df_ventas_periodo[df_ventas_periodo['nomvendedor'] == vendedor_seleccionado]
else:
    df_ventas_filtrado = df_ventas_periodo

# --- Procesamiento principal ---
with st.spinner(f"Ejecutando análisis estratégico para {vendedor_seleccionado}..."):
    df_clientes_pagados, df_cartera_pendiente, venta_bruta_total, margen_bruto_total, total_descuentos_otorgados_kpi = procesar_y_analizar_profundo(
        df_ventas_filtrado, df_cobros_granular_raw, DIAS_POLITICA_PAGO
    )

# --- Definición de Pestañas ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 **Resumen Gerencial**", 
    "✅ **Cartera Pagada (Detalle)**",
    "⏳ **Cartera Pendiente (Aging)**",
    "🎯 **Plan de Acción**"
])

# --- Pestaña 1: Resumen Gerencial ---
with tab1:
    st.header(f"Resumen Estratégico para: {vendedor_seleccionado}")
    st.info(f"Período analizado: del **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**.")
    
    st.subheader("Indicadores Clave de Rentabilidad y Riesgo")

    # --- Cálculo de KPIs Gerenciales ---
    margen_real = margen_bruto_total - total_descuentos_otorgados_kpi
    rentabilidad_efectiva = (margen_real / venta_bruta_total * 100) if venta_bruta_total > 0 else 0
    
    clientes_criticos_df = df_clientes_pagados[df_clientes_pagados['Clasificacion'] == '❌ Crítico'] if not df_clientes_pagados.empty else pd.DataFrame()
    fuga_de_rentabilidad = clientes_criticos_df['total_descontado'].sum() if not clientes_criticos_df.empty else 0
    
    descuentos_en_pagadas = df_clientes_pagados['total_descontado'].sum() if not df_clientes_pagados.empty else 0
    pct_descuentos_analizados = (descuentos_en_pagadas / total_descuentos_otorgados_kpi * 100) if total_descuentos_otorgados_kpi > 0 else 0
    
    total_cartera_pendiente = df_cartera_pendiente['valor_total_factura'].sum() if not df_cartera_pendiente.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💸 Total Descuentos Otorgados", f"${total_descuentos_otorgados_kpi:,.0f}", help="Suma de descuentos en TODAS las facturas del período, pagadas o no. ¡Esta es la cifra real!")
    col2.metric("💰 Rentabilidad Efectiva", f"{rentabilidad_efectiva:.1f}%", help="(Margen Bruto - Total Descuentos) / Venta Bruta. Es el margen real del negocio.")
    col3.metric("🔥 Fuga de Rentabilidad", f"${fuga_de_rentabilidad:,.0f}", help="Suma de descuentos a clientes que YA PAGARON, pero lo hicieron tarde. Este monto podría aumentar a medida que se cobre más cartera.")
    col4.metric("📊 % Dctos. bajo Análisis", f"{pct_descuentos_analizados:.1f}%", help="Porcentaje de los descuentos totales que ya podemos analizar porque sus facturas fueron pagadas. Si es bajo, es pronto para sacar conclusiones definitivas.")
    
    st.markdown("---")
    st.subheader("Matriz de Efectividad de Descuentos (Sobre Cartera Pagada)")
    if not df_clientes_pagados.empty and df_clientes_pagados['total_comprado_pagado'].sum() > 0:
        df_plot = df_clientes_pagados[df_clientes_pagados['total_comprado_pagado'] > 0].copy().fillna(0)
        
        fig_scatter = px.scatter(
            df_plot, x='dias_pago_promedio', y='pct_descuento',
            size='total_comprado_pagado', color='Clasificacion', hover_name='nombre_cliente',
            title=f"Eficiencia de Descuentos para {vendedor_seleccionado}",
            labels={'dias_pago_promedio': 'Días Promedio de Pago', 'pct_descuento': '% Descuento sobre Compra'},
            color_discrete_map={"✅ Justificado": "#28a745", "💡 Oportunidad": "#007bff", "❌ Crítico": "#dc3545", "⚠️ Alerta": "#ffc107"},
            hover_data=['total_comprado_pagado', 'total_descontado', 'margen_total_generado'],
            size_max=60)
        fig_scatter.add_vline(x=DIAS_POLITICA_PAGO, line_width=3, line_dash="dash", line_color="black", annotation_text=f"Meta {DIAS_POLITICA_PAGO} días")
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("No hay suficientes datos de clientes pagados en este período para generar la matriz de efectividad.")

# --- Pestaña 2: Cartera Pagada (Detalle) ---
with tab2:
    st.header("Análisis Detallado de Cartera Pagada")
    if not df_clientes_pagados.empty:
        st.write("A continuación se listan todos los clientes que realizaron pagos en el período, ordenados desde el que más tarda en pagar en promedio.")
        df_clientes_pagados_sorted = df_clientes_pagados.sort_values(by="dias_pago_promedio", ascending=False)
        st.dataframe(
            df_clientes_pagados_sorted,
            use_container_width=True, hide_index=True,
            column_config={
                "nombre_cliente": st.column_config.TextColumn("Cliente"),
                "dias_pago_promedio": st.column_config.NumberColumn("Días Pago Prom.", format="%d días"),
                "total_comprado_pagado": st.column_config.NumberColumn("Total Comprado", format="$ {:,.0f}"),
                "total_descontado": st.column_config.NumberColumn("Total Dcto.", format="$ {:,.0f}"),
                "pct_descuento": st.column_config.ProgressColumn("% Dcto.", format="%.1f%%", min_value=0, max_value=max(10, df_clientes_pagados.pct_descuento.max())),
                "pct_margen": st.column_config.ProgressColumn("% Margen", format="%.1f%%", min_value=min(0, df_clientes_pagados.pct_margen.min()), max_value=max(10, df_clientes_pagados.pct_margen.max()))
            }
        )
    else:
        st.warning("No se encontraron clientes con facturas pagadas en el período seleccionado.")

# --- Pestaña 3: Cartera Pendiente (Aging) ---
with tab3:
    st.header("Análisis de Vencimiento de Cartera (Aging)")
    if not df_cartera_pendiente.empty:
        st.subheader("Resumen de Cartera por Antigüedad")
        aging_summary = df_cartera_pendiente.groupby('Rango_Vencimiento')['valor_total_factura'].sum().reset_index()
        fig_pie = px.pie(
            aging_summary, names='Rango_Vencimiento', values='valor_total_factura',
            title='Distribución de la Cartera Pendiente',
            color_discrete_sequence=px.colors.sequential.Reds_r,
            category_orders={'Rango_Vencimiento': ["Corriente (0-30 días)", "Vencida (31-60 días)", "Vencida (61-90 días)", "Vencida (+90 días)"]}
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
        st.subheader("Detalle de Facturas Pendientes de Cobro")
        st.dataframe(
            df_cartera_pendiente[['nombre_cliente', 'fecha_venta', 'dias_antiguedad', 'valor_total_factura', 'Rango_Vencimiento']].sort_values(by="dias_antiguedad", ascending=False),
            use_container_width=True, hide_index=True,
            column_config={
                "valor_total_factura": st.column_config.NumberColumn(format="$ {:,.0f}"),
                "dias_antiguedad": st.column_config.NumberColumn("Días de Antigüedad")
            }
        )
    else:
        st.success("🎉 ¡Felicidades! No hay cartera pendiente de cobro para los filtros seleccionados.")

# --- Pestaña 4: Plan de Acción ---
with tab4:
    st.header("Plan de Acción Estratégico")

    st.subheader("🔥 Foco #1: Contener Fugas de Rentabilidad")
    st.markdown("Estos son los clientes **críticos** que recibieron descuentos pero **no cumplieron** con la política de pago. La acción aquí es **revisar y potencialmente suspender** sus descuentos.")
    if not clientes_criticos_df.empty:
        st.dataframe(
            clientes_criticos_df.sort_values("total_descontado", ascending=False),
            use_container_width=True, hide_index=True,
            column_config={
                "nombre_cliente": st.column_config.TextColumn("Cliente Crítico"),
                "total_descontado": st.column_config.NumberColumn("Monto Dcto. Perdido", format="$ {:,.0f}"),
                "dias_pago_promedio": st.column_config.NumberColumn("Paga en Prom. (días)", format="%d"),
                "pct_margen": st.column_config.NumberColumn("Margen Real (%)", format="%.1f%%")
            }
        )
    else:
        st.success("✅ ¡Excelente! No hay clientes críticos identificados en la cartera que ya ha sido pagada.")

    st.markdown("---")

    st.subheader("💡 Foco #2: Capitalizar Oportunidades de Crecimiento")
    st.markdown("Estos son los clientes **leales** que pagan a tiempo pero **no reciben descuentos**. Son una oportunidad para **fidelizar y aumentar ventas** con un descuento justificado.")
    clientes_oportunidad_df = df_clientes_pagados[df_clientes_pagados['Clasificacion'] == '💡 Oportunidad'] if not df_clientes_pagados.empty else pd.DataFrame()
    if not clientes_oportunidad_df.empty:
        st.dataframe(
            clientes_oportunidad_df.sort_values("total_comprado_pagado", ascending=False),
            use_container_width=True, hide_index=True,
            column_config={
                "nombre_cliente": st.column_config.TextColumn("Cliente Leal"),
                "total_comprado_pagado": st.column_config.NumberColumn("Total Comprado", format="$ {:,.0f}"),
                "dias_pago_promedio": st.column_config.NumberColumn("Paga en Prom. (días)", format="%d")
            }
        )
    else:
        st.info("No se identificaron clientes leales sin descuentos en la porción de cartera pagada.")
