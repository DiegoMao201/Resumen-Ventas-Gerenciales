# ==============================================================================
# SCRIPT UNIFICADO PARA: 🧠 Centro de Control de Descuentos y Cartera v9.0
# VERSIÓN: FINAL INTEGRADA - 12 de Julio, 2025
# DESCRIPCIÓN: Fusiona el análisis por vendedor con el cruce de cartera
#              para un análisis exhaustivo de la justificación de descuentos.
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import dropbox
import io

# --- 1. CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN DE ACCESO ---
st.set_page_config(page_title="Control de Descuentos y Cartera", page_icon="🧠", layout="wide")

st.title("🧠 Centro de Control de Descuentos y Cartera v9.0")
st.markdown("Análisis profundo de la justificación de descuentos comerciales y salud de la cartera por vendedor.")

if st.session_state.get('usuario') != "GERENTE":
    st.error("🔒 Acceso Exclusivo para Gerencia.")
    st.info("Por favor, inicie sesión desde la página principal para acceder a esta herramienta.")
    st.stop()

# --- 2. LÓGICA DE CARGA DE DATOS (ROBUSTA Y CENTRALIZADA) ---
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
            st.success("Archivo de cobros granular cargado.", icon="✅")
    except Exception as e:
        st.error(f"Error crítico al cargar el archivo de cobros desde Dropbox: {e}")
        return None, None

    columnas_requeridas_cobros = ['Serie', 'Fecha Documento', 'Fecha Saldado', 'IMPORTE']
    if not all(col in df_cobros_granular.columns for col in columnas_requeridas_cobros):
        st.error(f"El archivo de cobros de Dropbox DEBE contener las columnas: {columnas_requeridas_cobros}. Columnas encontradas: {df_cobros_granular.columns.to_list()}")
        return None, None

    df_cobros_granular.rename(columns={'Fecha Documento': 'fecha_documento', 'Fecha Saldado': 'fecha_saldado', 'IMPORTE': 'importe'}, inplace=True)

    # Normalización y creación de llaves
    df_ventas_copy['fecha_venta_norm'] = pd.to_datetime(df_ventas_copy['fecha_venta'], errors='coerce').dt.normalize()
    df_cobros_granular['fecha_documento_norm'] = pd.to_datetime(df_cobros_granular['fecha_documento'], errors='coerce').dt.normalize()
    df_cobros_granular['fecha_saldado'] = pd.to_datetime(df_cobros_granular['fecha_saldado'], errors='coerce').dt.normalize()

    df_ventas_copy['llave_factura'] = df_ventas_copy['Serie'].astype(str) + "_" + df_ventas_copy['fecha_venta_norm'].astype(str)
    df_cobros_granular['llave_factura'] = df_cobros_granular['Serie'].astype(str) + "_" + df_cobros_granular['fecha_documento_norm'].astype(str)

    df_cobros_esencial = df_cobros_granular[['llave_factura', 'fecha_saldado']].dropna().drop_duplicates(subset=['llave_factura'])

    numeric_cols = ['valor_venta', 'costo_unitario', 'unidades_vendidas']
    for col in numeric_cols:
        df_ventas_copy[col] = pd.to_numeric(df_ventas_copy[col], errors='coerce')

    df_ventas_copy.dropna(subset=['fecha_venta_norm', 'Serie', 'llave_factura'], inplace=True)
    return df_ventas_copy, df_cobros_esencial

# --- 3. LÓGICA DE PROCESAMIENTO PROFUNDO (EL "CEREBRO") ---
@st.cache_data
def procesar_y_analizar_profundo(_df_ventas_periodo, _df_cobros_global, dias_politica_pago):
    if _df_ventas_periodo is None or _df_cobros_global is None or _df_ventas_periodo.empty:
        return pd.DataFrame(), pd.DataFrame()

    df_ventas = _df_ventas_periodo.copy()
    
    # Identificar descuentos con mayor precisión
    filtro_descuento = (df_ventas['nombre_articulo'].str.upper().str.contains('DESCUENTO', na=False)) & \
                       (df_ventas['nombre_articulo'].str.upper().str.contains('COMERCIAL', na=False))
    
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

    # Cruce con cartera para saber qué se ha pagado
    df_pagadas = pd.merge(ventas_consolidadas, _df_cobros_global, on='llave_factura', how='inner')
    
    if not df_pagadas.empty:
        df_pagadas['dias_pago'] = (df_pagadas['fecha_saldado'] - df_pagadas['fecha_venta']).dt.days

    series_pagadas = df_pagadas['llave_factura'].unique()
    df_pendientes = ventas_consolidadas[~ventas_consolidadas['llave_factura'].isin(series_pagadas)].copy()
    
    # Análisis de cartera pendiente (Aging)
    if not df_pendientes.empty:
        hoy = pd.to_datetime(datetime.now())
        df_pendientes['dias_antiguedad'] = (hoy - df_pendientes['fecha_venta']).dt.days
        def clasificar_vencimiento(dias):
            if dias <= 30: return "Corriente (0-30 días)"
            elif dias <= 60: return "Vencida (31-60 días)"
            elif dias <= 90: return "Vencida (61-90 días)"
            else: return "Vencida (+90 días)"
        df_pendientes['Rango_Vencimiento'] = df_pendientes['dias_antiguedad'].apply(clasificar_vencimiento)

    # Análisis de clientes con facturas pagadas
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

        # ### LÓGICA DE CLASIFICACIÓN MEJORADA ###
        def clasificar_cliente_pagado(row):
            paga_a_tiempo = row['dias_pago_promedio'] <= dias_politica_pago
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

# Unificar selección de vendedor con la lógica del primer script
vendedores_unicos = ['Visión Gerencial (Todos)'] + sorted(df_ventas_periodo['nomvendedor'].dropna().unique().tolist())
vendedor_seleccionado = st.sidebar.selectbox("Seleccionar Vendedor o Visión General", options=vendedores_unicos)

# Se fija la política de pago a 30 días como base del análisis
DIAS_POLITICA_PAGO = 30
st.sidebar.info(f"Política de Pronto Pago fijada en **{DIAS_POLITICA_PAGO} días** para el análisis.")

if vendedor_seleccionado != "Visión Gerencial (Todos)":
    df_ventas_filtrado = df_ventas_periodo[df_ventas_periodo['nomvendedor'] == vendedor_seleccionado]
else:
    df_ventas_filtrado = df_ventas_periodo

with st.spinner(f"Ejecutando análisis profundo para {vendedor_seleccionado}..."):
    df_analisis_pagado, df_cartera_pendiente = procesar_y_analizar_profundo(
        df_ventas_filtrado, df_cobros_granular_raw, DIAS_POLITICA_PAGO
    )

# --- KPIs y Visualización ---
total_cartera_pendiente = df_cartera_pendiente['valor_total_factura'].sum() if not df_cartera_pendiente.empty else 0
total_descuentos_periodo = df_analisis_pagado['total_descontado'].sum() if not df_analisis_pagado.empty else 0

st.header(f"Análisis para: {vendedor_seleccionado}")
st.info(f"Período analizado: del **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**.")

tab1, tab2, tab3 = st.tabs([
    "📊 **Análisis de Efectividad de Descuentos**", 
    "⏳ **Análisis de Cartera Pendiente (Aging)**",
    "🗣️ **Plan de Acción y Conclusiones**"
])

with tab1:
    st.header("Matriz de Efectividad de Descuentos (Cartera Pagada)")
    if df_analisis_pagado.empty:
        st.warning("No hay datos de facturas pagadas para los filtros seleccionados.")
    else:
        st.subheader("Comportamiento de Pago vs. % Descuento Otorgado")
        st.markdown("""
        Esta matriz visualiza la efectividad de tu política de descuentos. Cada burbuja es un cliente.
        - **Eje X (Días Promedio de Pago):** Más a la derecha, más tardan en pagar.
        - **Eje Y (% Descuento):** Más arriba, mayor es el descuento que se les otorga.
        - **Color (Clasificación):** Muestra si el descuento está justificado.
        - **Tamaño (Total Comprado):** Clientes más grandes tienen burbujas más grandes.
        """
        )

        fig_scatter = px.scatter(
            df_analisis_pagado, x='dias_pago_promedio', y='pct_descuento',
            size='total_comprado_pagado', color='Clasificacion', hover_name='nombre_cliente',
            title=f"Matriz de Clientes: Eficiencia de Descuentos para {vendedor_seleccionado}",
            labels={'dias_pago_promedio': 'Días Promedio de Pago', 'pct_descuento': '% Descuento sobre Compra', 'pct_margen': 'Margen (%)'},
            color_discrete_map={"✅ Justificado": "#28a745", "💡 Oportunidad": "#007bff", "❌ Crítico": "#dc3545", "⚠️ Alerta": "#ffc107"},
            hover_data=['total_comprado_pagado', 'total_descontado', 'pct_margen'],
            size_max=60)
        fig_scatter.add_vline(x=DIAS_POLITICA_PAGO, line_width=3, line_dash="dash", line_color="black", annotation_text=f"Meta {DIAS_POLITICA_PAGO} días")
        st.plotly_chart(fig_scatter, use_container_width=True)
    
        with st.expander("Ver detalle completo de clientes analizados (Cartera Pagada)"):
            st.dataframe(df_analisis_pagado.sort_values(by="total_descontado", ascending=False), use_container_width=True, hide_index=True)

with tab2:
    st.header("Análisis de Vencimiento de Cartera (Aging)")
    if df_cartera_pendiente.empty:
        st.success("¡Felicidades! No hay cartera pendiente de cobro para los filtros seleccionados.")
    else:
        aging_summary = df_cartera_pendiente.groupby('Rango_Vencimiento')['valor_total_factura'].sum().reset_index()
        st.subheader("Resumen de Cartera por Antigüedad")
        col1, col2 = st.columns(2)
        col1.metric("Monto Total Pendiente", f"${total_cartera_pendiente:,.0f}")
        
        fig_pie = px.pie(
            aging_summary, names='Rango_Vencimiento', values='valor_total_factura',
            title='Distribución de la Cartera Pendiente',
            color_discrete_sequence=px.colors.sequential.Reds_r,
            category_orders={'Rango_Vencimiento': ["Corriente (0-30 días)", "Vencida (31-60 días)", "Vencida (61-90 días)", "Vencida (+90 días)"]}
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
        with st.expander("Ver detalle de todas las facturas pendientes de cobro"):
            st.dataframe(df_cartera_pendiente[['Serie', 'nombre_cliente', 'fecha_venta', 'dias_antiguedad', 'valor_total_factura', 'Rango_Vencimiento']].sort_values(by="dias_antiguedad", ascending=False), use_container_width=True, hide_index=True)

with tab3:
    st.header("Conclusiones Automáticas y Plan de Acción")
    st.info(f"Diagnóstico generado para **{vendedor_seleccionado}** en el período seleccionado.")

    st.subheader("Diagnóstico de la Política de Descuentos")
    if not df_analisis_pagado.empty:
        clientes_criticos_df = df_analisis_pagado[df_analisis_pagado['Clasificacion'] == '❌ Crítico']
        if not clientes_criticos_df.empty:
            monto_critico = clientes_criticos_df['total_descontado'].sum()
            st.error(f"""
            **🔥 Fuga de Rentabilidad Detectada:** Se han otorgado **${monto_critico:,.0f}** en descuentos a **{len(clientes_criticos_df)}** clientes
            que **NO CUMPLEN** la política de pronto pago (pagan en promedio después de {DIAS_POLITICA_PAGO} días).
            
            **Plan de Acción Inmediato:**
            1.  **Revisar y Suspender Descuentos:** Analizar la lista de clientes 'Críticos' (disponible en la primera pestaña) y considerar suspender futuros descuentos hasta que mejoren su comportamiento de pago.
            2.  **Comunicación Clara:** El vendedor debe comunicar al cliente que el 'Descuento Comercial' está condicionado al pago dentro de los 30 días.
            3.  **Evaluar Rentabilidad Neta:** Verificar si el `pct_margen` de estos clientes justifica mantener la relación comercial a pesar del mal comportamiento de pago.
            """)
            st.dataframe(clientes_criticos_df[['nombre_cliente', 'dias_pago_promedio', 'total_descontado', 'pct_margen']].sort_values('total_descontado', ascending=False), hide_index=True)
        else:
            st.success("✅ ¡Política de Descuentos Efectiva! No se encontraron descuentos otorgados a clientes que pagan tarde.", icon="🎉")

        clientes_oportunidad_df = df_analisis_pagado[df_analisis_pagado['Clasificacion'] == '💡 Oportunidad']
        if not clientes_oportunidad_df.empty:
            st.info(f"""
            **💡 Oportunidad de Fidelización:** Se han identificado **{len(clientes_oportunidad_df)}** clientes que pagan puntualmente pero no reciben descuentos.
            
            **Plan de Acción:**
            1.  **Recompensar Lealtad:** Considerar ofrecerles un descuento comercial en su próxima compra como premio por su buen comportamiento de pago.
            2.  **Aumentar Volumen de Compra:** Utilizar el descuento como un incentivo para incrementar su frecuencia o volumen de compra.
            """)

    else:
        st.info("No hay datos de cartera pagada para generar un diagnóstico sobre descuentos en este período.")

    st.subheader("Diagnóstico de la Salud de la Cartera")
    if not df_cartera_pendiente.empty:
        cartera_vencida = df_cartera_pendiente[df_cartera_pendiente['dias_antiguedad'] > 30]['valor_total_factura'].sum()
        if total_cartera_pendiente > 0 and cartera_vencida > 0:
            porcentaje_vencido = (cartera_vencida / total_cartera_pendiente) * 100
            st.warning(f"""
            **💰 Riesgo de Liquidez Identificado:** El **{porcentaje_vencido:.1f}%** de la cartera pendiente (**${cartera_vencida:,.0f}**) está vencida.
            
            **Plan de Acción:**
            1.  **Priorizar Cobro:** Enfocar la gestión de cobro en los clientes con mayor antigüedad (ver detalle en la pestaña 'Aging').
            2.  **Revisar Límites de Crédito:** Evaluar las condiciones de crédito para clientes con deudas vencidas recurrentes.
            """)
        else:
            st.success("👍 ¡Cartera Corriente! Toda la cartera pendiente originada en este periodo está al día.", icon="✅")
    else:
        st.success("👍 ¡Cartera Sana! No se registra cartera pendiente de cobro para los filtros seleccionados.", icon="✨")
