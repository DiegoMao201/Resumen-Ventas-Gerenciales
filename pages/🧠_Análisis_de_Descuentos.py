# ==============================================================================
# SCRIPT PARA: 🧠 Centro de Control de Descuentos y Cartera
# VERSIÓN: 7.0 GERENCIAL (ANÁLISIS PROFUNDO) - 07 de Julio, 2025
# DESCRIPCIÓN: Versión reconstruida desde cero con una lógica de cruce de datos
#              meticulosa, análisis de vencimiento (aging), KPIs avanzados y
#              comentarios detallados para máxima precisión y confianza.
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import io
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN DE ACCESO ---
st.set_page_config(page_title="Control de Descuentos y Cartera", page_icon="🧠", layout="wide")

st.title("🧠 Centro de Control de Descuentos y Cartera v7.0")
st.markdown("Herramienta de análisis profundo para la efectividad de descuentos, salud de cartera y gestión de vencimientos.")

if st.session_state.get('usuario') != "GERENTE":
    st.error("🔒 Acceso Exclusivo para Gerencia.")
    st.info("Por favor, inicie sesión desde la página principal para acceder a esta herramienta.")
    st.stop()

# --- LÓGICA DE CARGA DE DATOS (CACHEADA PARA EFICIENCIA) ---
@st.cache_data(ttl=3600)
def cargar_datos_fuente(dropbox_path_cobros):
    """
    Carga los datos de ventas (desde session_state) y el archivo de cobros desde Dropbox.
    """
    try:
        df_ventas = st.session_state.get('df_ventas')
        if df_ventas is None:
            st.error("Los datos de ventas no se encontraron en la sesión. Por favor, vuelva a la página principal y cargue los datos primero.")
            return None, None
        
        with st.spinner("Cargando y validando archivo de cobros desde Dropbox..."):
            try:
                import dropbox
                dbx = dropbox.Dropbox(
                    app_key=st.secrets.dropbox.app_key,
                    app_secret=st.secrets.dropbox.app_secret,
                    oauth2_refresh_token=st.secrets.dropbox.refresh_token
                )
                _, res = dbx.files_download(path=dropbox_path_cobros)
                df_cobros = pd.read_excel(io.BytesIO(res.content))
            except Exception as e:
                st.error(f"Error real al conectar con Dropbox: {e}")
                st.warning("Usando datos de ejemplo para cobros debido al error de conexión.")
                data_cobros = {'Serie': [], 'Fecha Saldado': []} # Simular vacío para no fallar
                df_cobros = pd.DataFrame(data_cobros)
        return df_ventas, df_cobros
    except Exception as e:
        st.error(f"Error crítico al cargar los archivos: {e}")
        return None, None

# --- LÓGICA DE PROCESAMIENTO PROFUNDO ---
@st.cache_data
def procesar_y_analizar_profundo(_df_ventas, _df_cobros, nombre_articulo_descuento, dias_pronto_pago):
    """
    Función central reconstruida para un análisis preciso y profundo.
    El proceso es:
    1. Limpiar y preparar ambos dataframes.
    2. Procesar el df_ventas para agregar por factura (Serie), separando productos y descuentos.
    3. Unir los datos de ventas con los de cobros usando la 'Serie' como llave.
    4. Calcular métricas clave: estado, días de pago, días de antigüedad.
    5. Crear dos dataframes finales para análisis: uno para cartera pagada y otro para pendiente.
    6. Enriquecer ambos dataframes con cálculos y clasificaciones adicionales.
    """
    if _df_ventas is None or _df_cobros is None:
        return None, None, None

    # PASO 1: PREPARACIÓN Y LIMPIEZA DE DATOS
    df_ventas = _df_ventas.copy()
    df_ventas['fecha_venta'] = pd.to_datetime(df_ventas['fecha_venta'])
    df_ventas['valor_venta'] = pd.to_numeric(df_ventas['valor_venta'], errors='coerce')
    df_ventas.dropna(subset=['valor_venta', 'Serie', 'nombre_cliente', 'nomvendedor'], inplace=True)

    df_cobros = _df_cobros.copy()
    df_cobros.rename(columns={'Fecha Saldado': 'fecha_saldado'}, inplace=True)
    df_cobros['fecha_saldado'] = pd.to_datetime(df_cobros['fecha_saldado'], errors='coerce')
    df_cobros.dropna(subset=['Serie', 'fecha_saldado'], inplace=True)

    # PASO 2: AGREGACIÓN POR FACTURA DESDE EL ARCHIVO DE VENTAS
    # Separamos lo que es venta de producto (positivo) de lo que es descuento (negativo)
    df_productos = df_ventas[df_ventas['valor_venta'] > 0].copy()
    df_descuentos_raw = df_ventas[
        (df_ventas['nombre_articulo'] == nombre_articulo_descuento) & (df_ventas['valor_venta'] < 0)
    ].copy()

    # Agrupamos por 'Serie' para tener una línea por factura
    ventas_por_factura = df_productos.groupby('Serie').agg(
        valor_total_productos=('valor_venta', 'sum'),
        fecha_venta=('fecha_venta', 'first'),
        nombre_cliente=('nombre_cliente', 'first'),
        nomvendedor=('nomvendedor', 'first')
    ).reset_index()

    descuentos_por_factura = df_descuentos_raw.groupby('Serie').agg(
        monto_descontado=('valor_venta', 'sum')
    ).reset_index()
    descuentos_por_factura['monto_descontado'] = abs(descuentos_por_factura['monto_descontado'])

    # PASO 3: UNIÓN DE DATOS (CRUCE MAESTRO)
    # Usamos un LEFT JOIN desde las ventas para no perder ninguna factura, aunque no tenga descuento.
    df_facturas = pd.merge(ventas_por_factura, descuentos_por_factura, on='Serie', how='left')
    df_facturas['monto_descontado'].fillna(0, inplace=True)
    
    # Ahora cruzamos con el archivo de cobros. Las facturas que no crucen quedarán con 'fecha_saldado' en NaT (Not a Time).
    df_completo = pd.merge(df_facturas, df_cobros[['Serie', 'fecha_saldado']], on='Serie', how='left')

    # PASO 4: CÁLCULOS DE ESTADO Y MÉTRICAS DE TIEMPO
    hoy = pd.to_datetime(datetime.now())
    df_completo['estado'] = np.where(df_completo['fecha_saldado'].notna(), 'Pagada', 'Pendiente')
    df_completo['dias_pago'] = (df_completo['fecha_saldado'] - df_completo['fecha_venta']).dt.days
    df_completo['dias_antiguedad'] = (hoy - df_completo['fecha_venta']).dt.days

    # PASO 5: SEPARACIÓN DE CARTERAS PARA ANÁLISIS INDIVIDUAL
    df_pagadas = df_completo[df_completo['estado'] == 'Pagada'].copy()
    df_pendientes = df_completo[df_completo['estado'] == 'Pendiente'].copy()

    # PASO 6.1: ENRIQUECIMIENTO DE CARTERA PAGADA
    analisis_pagado = df_pagadas.groupby(['nombre_cliente', 'nomvendedor']).agg(
        dias_pago_promedio=('dias_pago', 'mean'),
        total_comprado_pagado=('valor_total_productos', 'sum'),
        total_descontado=('monto_descontado', 'sum'),
        numero_facturas_pagadas=('Serie', 'nunique')
    ).reset_index()
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

    # PASO 6.2: ENRIQUECIMIENTO DE CARTERA PENDIENTE (AGING)
    def clasificar_vencimiento(dias):
        if dias <= 30: return "Corriente (0-30 días)"
        elif dias <= 60: return "Vencida (31-60 días)"
        elif dias <= 90: return "Vencida (61-90 días)"
        else: return "Vencida (+90 días)"
    if not df_pendientes.empty:
        df_pendientes['Rango_Vencimiento'] = df_pendientes['dias_antiguedad'].apply(clasificar_vencimiento)
    
    analisis_pendiente_agg = df_pendientes.groupby(['nombre_cliente', 'nomvendedor']).agg(
        monto_pendiente=('valor_total_productos', 'sum'),
        antiguedad_prom_pendiente=('dias_antiguedad', 'mean'),
        numero_facturas_pendientes=('Serie', 'nunique')
    ).reset_index()

    # PASO 7: CÁLCULO DE KPIs GLOBALES
    total_ventas = ventas_por_factura['valor_total_productos'].sum()
    total_descuentos_otorgados = descuentos_por_factura['monto_descontado'].sum()
    total_cartera_pendiente = df_pendientes['valor_total_productos'].sum()
    # DSO (Days Sales Outstanding) - Una aproximación simple
    dso = (total_cartera_pendiente / total_ventas) * 90 if total_ventas > 0 else 0 # Asumiendo un periodo de 90 días

    kpis = {
        "DSO": dso,
        "Total Cartera Pendiente": total_cartera_pendiente,
        "Total Descuentos": total_descuentos_otorgados,
        "Porcentaje Descuento": (total_descuentos_otorgados / total_ventas) * 100 if total_ventas > 0 else 0
    }

    return analisis_pagado, df_pendientes, kpis

# ==============================================================================
# EJECUCIÓN PRINCIPAL Y RENDERIZADO
# ==============================================================================

# --- Carga de Datos ---
df_ventas, df_cobros = cargar_datos_fuente("/data/Cobros.xlsx")

if df_ventas is None or df_cobros is None:
    st.error("La carga de datos falló. No se puede continuar.")
    st.stop()

# --- Barra Lateral de Filtros ---
st.sidebar.header("Filtros del Análisis")
DIAS_PRONTO_PAGO = st.sidebar.slider("Definir 'Pronto Pago' (días)", min_value=5, max_value=90, value=30)
vendedores_unicos = df_ventas['nomvendedor'].dropna().unique().tolist()
lista_vendedores = ['Todos'] + sorted(vendedores_unicos)
vendedor_seleccionado = st.sidebar.selectbox("Seleccionar Vendedor", options=lista_vendedores)

# --- Procesamiento de Datos ---
with st.spinner("Ejecutando análisis profundo de cartera..."):
    df_analisis_pagado, df_cartera_pendiente, kpis = procesar_y_analizar_profundo(
        df_ventas, df_cobros, "DESCUENTOS COMERCIALES", DIAS_PRONTO_PAGO)

# --- Filtrado por Vendedor ---
if vendedor_seleccionado != "Todos":
    df_pagado_filtrado = df_analisis_pagado[df_analisis_pagado['nomvendedor'] == vendedor_seleccionado].copy()
    df_pendiente_filtrado = df_cartera_pendiente[df_cartera_pendiente['nomvendedor'] == vendedor_seleccionado].copy()
else:
    df_pagado_filtrado = df_analisis_pagado.copy()
    df_pendiente_filtrado = df_cartera_pendiente.copy()

# --- KPIs Gerenciales ---
st.header("Indicadores Clave de Rendimiento (KPIs)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Días de Venta en la Calle (DSO)", f"{kpis.get('DSO', 0):.1f} días", help="Promedio de días que se tarda en cobrar tras una venta.")
col2.metric("Cartera Pendiente Total", f"${kpis.get('Total Cartera Pendiente', 0):,.0f}", help="Monto total que los clientes deben a la fecha.")
col3.metric("Total en Descuentos", f"${kpis.get('Total Descuentos', 0):,.0f}", help="Suma de todos los descuentos comerciales otorgados.")
col4.metric("% Descuento s/ Venta", f"{kpis.get('Porcentaje Descuento', 0):.2f}%", help="Qué porcentaje de la venta total se está yendo en descuentos.")

# --- PESTAÑAS DE ANÁLISIS ---
st.markdown("---")
tab1, tab2, tab3 = st.tabs([
    "📊 **Análisis de Cartera Pagada (Efectividad Dctos.)**", 
    "⏳ **Análisis de Cartera Pendiente (Aging)**",
    "🗣️ **Conclusiones y Recomendaciones**"
])

# --- PESTAÑA 1: CARTERA PAGADA ---
with tab1:
    st.header(f"Análisis de Descuentos en Cartera Pagada")
    st.info("Este análisis se enfoca **únicamente en las facturas que ya han sido pagadas** para evaluar si los descuentos se justifican con un pronto pago.")
    if df_pagado_filtrado.empty:
        st.warning(f"No hay datos de facturas pagadas para '{vendedor_seleccionado}'.")
    else:
        st.subheader("Visualización Estratégica de Clientes (Pagados)")
        fig_scatter = px.scatter(
            df_pagado_filtrado, x='dias_pago_promedio', y='pct_descuento',
            size='total_comprado_pagado', color='Clasificacion', hover_name='nombre_cliente',
            title="Comportamiento de Pago vs. % Descuento Otorgado",
            labels={'dias_pago_promedio': 'Días Promedio de Pago', 'pct_descuento': '% Descuento s/Compra'},
            color_discrete_map={"✅ Justificado": "#28a745", "💡 Oportunidad": "#007bff", "❌ Crítico": "#dc3545", "⚠️ Alerta": "#ffc107"},
            size_max=60)
        fig_scatter.add_vline(x=DIAS_PRONTO_PAGO, line_width=2, line_dash="dash", annotation_text=f"Meta {DIAS_PRONTO_PAGO} días")
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        with st.expander("Ver detalle de clientes (Cartera Pagada)"):
            st.dataframe(df_pagado_filtrado.sort_values(by="total_descontado", ascending=False), use_container_width=True, hide_index=True)

# --- PESTAÑA 2: CARTERA PENDIENTE ---
with tab2:
    st.header(f"Análisis de Vencimiento de Cartera (Aging)")
    st.info("Este análisis muestra las deudas vigentes, clasificadas por su antigüedad.")
    if df_pendiente_filtrado.empty:
        st.success(f"¡Felicidades! No hay cartera pendiente de cobro para '{vendedor_seleccionado}'.")
    else:
        # Gráfico de Aging
        aging_summary = df_pendiente_filtrado.groupby('Rango_Vencimiento')['valor_total_productos'].sum().reset_index()
        aging_summary.rename(columns={'valor_total_productos': 'Monto Pendiente'}, inplace=True)
        
        st.subheader("Resumen de Cartera por Antigüedad (Aging)")
        fig_pie = px.pie(
            aging_summary, names='Rango_Vencimiento', values='Monto Pendiente',
            title='Distribución de la Cartera Pendiente por Vencimiento',
            color_discrete_sequence=px.colors.sequential.Reds_r
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        with st.expander("Ver detalle de facturas pendientes de cobro"):
            st.dataframe(df_pendiente_filtrado.sort_values(by="dias_antiguedad", ascending=False), use_container_width=True, hide_index=True)

# --- PESTAÑA 3: CONCLUSIONES ---
with tab3:
    st.header("Conclusiones Automáticas y Plan de Acción")
    
    # Conclusiones sobre Cartera Pagada
    st.subheader("Diagnóstico de la Política de Descuentos")
    if not df_pagado_filtrado.empty:
        clientes_criticos_df = df_pagado_filtrado[df_pagado_filtrado['Clasificacion'] == '❌ Crítico']
        if not clientes_criticos_df.empty:
            monto_critico = clientes_criticos_df['total_descontado'].sum()
            st.error(f"""
            **Fuga de Rentabilidad Detectada:** Se han otorgado **${monto_critico:,.0f}** en descuentos a **{len(clientes_criticos_df)}** clientes
            que incumplen la política de pronto pago (pagan en promedio después de {DIAS_PRONTO_PAGO} días).
            **Plan de Acción:**
            1.  **Revisar** la asignación de descuentos para los clientes en la categoría 'Crítico'.
            2.  **Comunicar** a la fuerza de ventas la importancia de alinear los descuentos con el comportamiento de pago.
            """, icon="🔥")
        else:
            st.success("¡Política de Descuentos Efectiva! No se encontraron clientes críticos en la cartera pagada. Los descuentos se están asignando correctamente a buenos pagadores.", icon="🎉")
    else:
        st.info("No hay datos de cartera pagada para generar un diagnóstico sobre descuentos.")

    # Conclusiones sobre Cartera Pendiente
    st.subheader("Diagnóstico de la Salud de la Cartera")
    if not df_pendiente_filtrado.empty:
        cartera_vencida = df_pendiente_filtrado[df_pendiente_filtrado['dias_antiguedad'] > 30]['valor_total_productos'].sum()
        porcentaje_vencido = (cartera_vencida / kpis['Total Cartera Pendiente']) * 100 if kpis['Total Cartera Pendiente'] > 0 else 0
        st.warning(f"""
        **Riesgo de Liquidez Identificado:** El **{porcentaje_vencido:.1f}%** de la cartera pendiente (**${cartera_vencida:,.0f}**) está vencida (más de 30 días).
        **Plan de Acción:**
        1.  **Enfocar** la gestión de cobro en el segmento de '+90 días', que representa el mayor riesgo.
        2.  **Analizar** los clientes con los mayores montos pendientes en la pestaña de 'Aging' para una acción de cobro directa.
        """, icon="💰")
    else:
        st.success("¡Cartera Sana! No se registra cartera pendiente de cobro. Excelente gestión de liquidez.", icon="👍")
