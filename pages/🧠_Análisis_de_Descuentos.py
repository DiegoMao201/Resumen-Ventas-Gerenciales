# ==============================================================================
# SCRIPT UNIFICADO PARA: 🧠 Centro de Control Estratégico v12.0
# VERSIÓN: INTEGRACIÓN TOTAL (VENTAS + CARTERA DETALLADA) - 12 de Julio, 2025
# DESCRIPCIÓN: Fusiona el análisis de descuentos con el estado de cuenta
#              detallado del cliente para un análisis de riesgo/recompensa 360°.
#              Incluye botón para forzar la actualización de todos los datos.
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import dropbox
import io
import unicodedata

# --- 1. CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN DE ACCESO ---
st.set_page_config(page_title="Control Estratégico 360°", page_icon="🧠", layout="wide")

st.title("🧠 Control Estratégico 360°: Descuentos vs. Cartera v12.0")

if st.session_state.get('usuario') != "GERENTE":
    st.error("🔒 Acceso Exclusivo para Gerencia.")
    st.info("Por favor, inicie sesión desde la página principal para acceder a esta herramienta.")
    st.stop()

def normalizar_texto(texto):
    if not isinstance(texto, str):
        return texto
    try:
        # Normaliza para quitar tildes, convierte a mayúsculas y limpia espacios
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').strip().replace('  ', ' ')
    except (TypeError, AttributeError):
        return texto

# --- 2. LÓGICA DE CARGA DE DATOS (AHORA CON CARTERA DETALLE) ---
@st.cache_data(ttl=600)
def cargar_ventas_y_cobros():
    """Carga los datos de ventas y el archivo de cobros para el análisis de pagos."""
    df_ventas = st.session_state.get('df_ventas')
    if df_ventas is None or df_ventas.empty:
        st.error("Los datos de ventas no se encontraron. Vuelva a la página principal y cargue el archivo maestro.")
        return None, None
    
    # Carga de Cobros (usado para saber qué facturas se pagaron)
    try:
        with st.spinner("Cargando archivo de Cobros (pagos)..."):
            dbx = dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, app_secret=st.secrets.dropbox.app_secret, oauth2_refresh_token=st.secrets.dropbox.refresh_token)
            _, res = dbx.files_download(path="/data/Cobros.xlsx")
            df_cobros_granular = pd.read_excel(io.BytesIO(res.content))
    except Exception as e:
        st.error(f"Error crítico al cargar el archivo de Cobros desde Dropbox: {e}")
        return None, None
    
    # Procesamiento de Cobros
    df_cobros_granular.rename(columns={'Fecha Documento': 'fecha_documento', 'Fecha Saldado': 'fecha_saldado'}, inplace=True)
    df_ventas['fecha_venta_norm'] = pd.to_datetime(df_ventas['fecha_venta'], errors='coerce').dt.normalize()
    df_cobros_granular['fecha_documento_norm'] = pd.to_datetime(df_cobros_granular['fecha_documento'], errors='coerce').dt.normalize()
    df_cobros_granular['fecha_saldado'] = pd.to_datetime(df_cobros_granular['fecha_saldado'], errors='coerce').dt.normalize()
    df_ventas['llave_factura'] = df_ventas['Serie'].astype(str) + "_" + df_ventas['fecha_venta_norm'].astype(str)
    df_cobros_granular['llave_factura'] = df_cobros_granular['Serie'].astype(str) + "_" + df_cobros_granular['fecha_documento_norm'].astype(str)
    df_cobros_esencial = df_cobros_granular[['llave_factura', 'fecha_saldado']].dropna().drop_duplicates(subset=['llave_factura'])
    
    return df_ventas, df_cobros_esencial

@st.cache_data(ttl=600)
def cargar_cartera_detallada():
    """Carga el archivo cartera_detalle.csv con el estado de deuda actual."""
    try:
        with st.spinner("Cargando archivo de Cartera Detallada (deuda actual)..."):
            dbx = dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, app_secret=st.secrets.dropbox.app_secret, oauth2_refresh_token=st.secrets.dropbox.refresh_token)
            _, res = dbx.files_download(path='/data/cartera_detalle.csv')
            contenido_csv = res.content.decode('latin-1')
            
            nombres_columnas = ['Serie', 'Numero', 'Fecha Documento', 'Fecha Vencimiento', 'Cod Cliente', 'NombreCliente', 'Nit', 'Poblacion', 'Provincia', 'Telefono1', 'Telefono2', 'NomVendedor', 'Entidad Autoriza', 'E-Mail', 'Importe', 'Descuento', 'Cupo Aprobado', 'Dias Vencido']
            
            df_cartera = pd.read_csv(io.StringIO(contenido_csv), header=None, names=nombres_columnas, sep='|', engine='python', on_bad_lines='skip')
            
            # Limpieza y preparación de cartera
            df_cartera['Importe'] = pd.to_numeric(df_cartera['Importe'], errors='coerce').fillna(0)
            df_cartera['Dias Vencido'] = pd.to_numeric(df_cartera['Dias Vencido'], errors='coerce').fillna(0)
            df_cartera['Cod Cliente'] = df_cartera['Cod Cliente'].astype(str)
            df_cartera['Nit'] = df_cartera['Nit'].astype(str)
            
            # Agrupar por cliente para tener su estado de deuda total
            resumen_cartera_cliente = df_cartera.groupby('Cod Cliente').agg(
                deuda_total_actual=('Importe', 'sum'),
                deuda_vencida_actual=('Importe', lambda x: x[df_cartera.loc[x.index, 'Dias Vencido'] > 0].sum()),
                max_dias_vencido=('Dias Vencido', 'max')
            ).reset_index()
            return resumen_cartera_cliente
            
    except Exception as e:
        st.error(f"Error al cargar cartera_detalle.csv desde Dropbox: {e}")
        return pd.DataFrame()

# --- 3. LÓGICA DE PROCESAMIENTO ESTRATÉGICO 360° ---
@st.cache_data(ttl=600)
def procesar_analisis_360(_df_ventas_periodo, _df_cobros_esencial, _df_resumen_cartera, dias_politica_pago):
    if _df_ventas_periodo is None or _df_ventas_periodo.empty:
        return pd.DataFrame(), 0, 0, 0

    df_ventas = _df_ventas_periodo.copy()
    
    filtro_descuento = (df_ventas['nombre_articulo'].str.upper().str.contains('DESCUENTO', na=False)) & \
                       (df_ventas['nombre_articulo'].str.upper().str.contains('COMERCIAL', na=False))
    
    df_productos_raw = df_ventas[~filtro_descuento]
    df_descuentos_raw = df_ventas[filtro_descuento]

    # Cálculos globales del período
    venta_bruta_total = df_productos_raw['valor_venta'].sum()
    margen_bruto_total = (df_productos_raw['valor_venta'] - (df_productos_raw['costo_unitario'].fillna(0) * df_productos_raw['unidades_vendidas'].fillna(0))).sum()
    total_descuentos_periodo_completo = abs(df_descuentos_raw['valor_venta'].sum())

    # Agregación por cliente para el análisis de descuentos
    analisis_descuentos_cliente = df_descuentos_raw.groupby(['cliente_id', 'nombre_cliente']).agg(
        total_descontado_periodo=('valor_venta', lambda x: abs(x.sum()))
    ).reset_index()
    
    # Agregación de margen por cliente
    df_productos_raw['margen_bruto'] = df_productos_raw['valor_venta'] - (df_productos_raw['costo_unitario'].fillna(0) * df_productos_raw['unidades_vendidas'].fillna(0))
    margen_cliente = df_productos_raw.groupby('cliente_id').agg(margen_generado_periodo=('margen_bruto', 'sum')).reset_index()

    # --- CRUCE DE ORO: ANÁLISIS DE DESCUENTOS + ESTADO DE CARTERA ACTUAL ---
    df_final = pd.merge(analisis_descuentos_cliente, margen_cliente, on='cliente_id', how='left')
    df_final['cliente_id'] = df_final['cliente_id'].astype(str)
    
    if _df_resumen_cartera is not None and not _df_resumen_cartera.empty:
        df_final = pd.merge(df_final, _df_resumen_cartera, left_on='cliente_id', right_on='Cod Cliente', how='left')
        df_final.drop(columns=['Cod Cliente'], inplace=True)
        # Llenar con 0 para clientes que recibieron descuento pero no tienen deuda actual
        df_final.fillna({'deuda_total_actual': 0, 'deuda_vencida_actual': 0, 'max_dias_vencido': 0}, inplace=True)
    else:
        # Si no se carga la cartera, se crean columnas vacías
        df_final['deuda_total_actual'] = 0
        df_final['deuda_vencida_actual'] = 0
        df_final['max_dias_vencido'] = 0

    df_final['margen_neto_cliente'] = df_final['margen_generado_periodo'].fillna(0) - df_final['total_descontado_periodo'].fillna(0)
    
    # Clasificación Gerencial 360°
    def clasificar_cliente_360(row):
        descuento_alto = row['total_descontado_periodo'] > 0
        deuda_vencida_alta = row['deuda_vencida_actual'] > 100000  # Umbral de ejemplo
        margen_positivo = row['margen_neto_cliente'] > 0
        
        if margen_positivo and not deuda_vencida_alta:
            return "✅ Campeón Estratégico"
        elif margen_positivo and deuda_vencida_alta:
            return "⚠️ Rentable pero Riesgoso"
        elif not margen_positivo and not deuda_vencida_alta:
            return "💡 Fuga de Margen"
        elif not margen_positivo and deuda_vencida_alta:
            return "🔥 Crítico (Doble Problema)"
        return "Otros"
        
    df_final['Clasificacion_360'] = df_final.apply(clasificar_cliente_360, axis=1)
    
    return df_final, venta_bruta_total, margen_bruto_total, total_descuentos_periodo_completo

# ==============================================================================
# 4. EJECUCIÓN PRINCIPAL Y RENDERIZADO DE LA UI
# ==============================================================================

# --- Botón de actualización en la barra lateral ---
st.sidebar.title("Control de Datos")
if st.sidebar.button("🔄 Forzar Actualización de Datos"):
    st.cache_data.clear()
    st.success("Caché limpiado. Los datos se recargarán desde Dropbox en el próximo re-run.")
    st.rerun()

# --- Carga y procesamiento inicial ---
df_ventas, df_cobros_esencial = cargar_ventas_y_cobros()
df_resumen_cartera = cargar_cartera_detallada()

if df_ventas is None:
    st.stop()

# --- Filtros (sin cambios) ---
st.sidebar.title("Filtros del Análisis")
min_date, max_date = df_ventas['fecha_venta_norm'].min().date(), df_ventas['fecha_venta_norm'].max().date()
fecha_inicio = st.sidebar.date_input("Fecha de Inicio (Ventas)", value=max_date.replace(day=1), min_value=min_date, max_value=max_date)
fecha_fin = st.sidebar.date_input("Fecha de Fin (Ventas)", value=max_date, min_value=min_date, max_value=max_date)
if fecha_inicio > fecha_fin: st.sidebar.error("Fechas inválidas."); st.stop()

df_ventas_periodo = df_ventas[(df_ventas['fecha_venta_norm'].dt.date >= fecha_inicio) & (df_ventas['fecha_venta_norm'].dt.date <= fecha_fin)]
vendedores_unicos = ['Visión Gerencial (Todos)'] + sorted(df_ventas_periodo['nomvendedor'].dropna().unique().tolist())
vendedor_seleccionado = st.sidebar.selectbox("Seleccionar Vendedor", options=vendedores_unicos)
df_ventas_filtrado = df_ventas_periodo[df_ventas_periodo['nomvendedor'] == vendedor_seleccionado] if vendedor_seleccionado != "Visión Gerencial (Todos)" else df_ventas_periodo

# --- Procesamiento 360 ---
with st.spinner(f"Ejecutando análisis 360° para {vendedor_seleccionado}..."):
    df_analisis_final, venta_bruta, margen_bruto, descuentos_totales = procesar_analisis_360(
        df_ventas_filtrado, df_cobros_esencial, df_resumen_cartera, 30
    )

# --- Pestañas y Visualización ---
tab1, tab2 = st.tabs(["📊 **Dashboard de Riesgo vs. Recompensa**", "🎯 **Plan de Acción por Cliente**"])

with tab1:
    st.header(f"Dashboard Estratégico para: {vendedor_seleccionado}")
    st.info(f"Análisis de ventas del **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**, cruzado con la **deuda total actual** de los clientes.")

    # KPIs 360°
    margen_neto_total = margen_bruto - descuentos_totales
    rentabilidad_efectiva = (margen_neto_total / venta_bruta * 100) if venta_bruta > 0 else 0
    total_deuda_vencida_analizada = df_analisis_final['deuda_vencida_actual'].sum() if not df_analisis_final.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💸 Total Descuentos Otorgados", f"${descuentos_totales:,.0f}", help="Suma de todos los descuentos en el período de ventas seleccionado.")
    col2.metric("💰 Margen Neto del Período", f"${margen_neto_total:,.0f}", help="Margen Bruto menos los descuentos otorgados.")
    col3.metric("📈 Rentabilidad Efectiva", f"{rentabilidad_efectiva:.1f}%", help="Porcentaje del margen neto sobre la venta bruta.")
    col4.metric("🔥 Deuda Vencida (Clientes con Dcto)", f"${total_deuda_vencida_analizada:,.0f}", help="Suma de la deuda vencida actual de los clientes que recibieron descuentos en este período.")

    st.markdown("---")
    st.subheader("Matriz de Riesgo (Deuda Vencida) vs. Recompensa (Descuento Otorgado)")

    if not df_analisis_final.empty:
        # Asegurar que no hay nulos para el tamaño o color
        df_plot = df_analisis_final.copy()
        df_plot['total_descontado_periodo'] = df_plot['total_descontado_periodo'].fillna(0)
        df_plot['deuda_vencida_actual'] = df_plot['deuda_vencida_actual'].fillna(0)
        
        fig = px.scatter(
            df_plot,
            x="total_descontado_periodo",
            y="deuda_vencida_actual",
            size="margen_neto_cliente",
            color="Clasificacion_360",
            hover_name="nombre_cliente",
            log_x=True, log_y=True,
            title="Posicionamiento de Clientes: ¿Justifica el Margen el Riesgo?",
            labels={
                "total_descontado_periodo": "Recompensa (Total Descontado en Período) - Log",
                "deuda_vencida_actual": "Riesgo (Deuda Vencida Actual) - Log",
                "Clasificacion_360": "Clasificación 360"
            },
            color_discrete_map={
                "✅ Campeón Estratégico": "#28a745", 
                "⚠️ Rentable pero Riesgoso": "#ffc107", 
                "💡 Fuga de Margen": "#007bff", 
                "🔥 Crítico (Doble Problema)": "#dc3545"
            }
        )
        fig.update_layout(legend_title="Clasificación 360")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos suficientes para generar la matriz de riesgo vs recompensa.")

with tab2:
    st.header("Plan de Acción y Detalle por Cliente")
    st.markdown("Utiliza esta tabla para tomar decisiones informadas. Ordena por cualquier columna para identificar tus mayores riesgos y oportunidades.")
    
    if not df_analisis_final.empty:
        st.dataframe(
            df_analisis_final.sort_values(by="total_descontado_periodo", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "nombre_cliente": st.column_config.TextColumn("Cliente", width="large"),
                "Clasificacion_360": st.column_config.TextColumn("Clasificación"),
                "total_descontado_periodo": st.column_config.NumberColumn("Descuento Otorgado", format="$ {:,.0f}"),
                "margen_neto_cliente": st.column_config.NumberColumn("Margen Neto Cliente", format="$ {:,.0f}"),
                "deuda_vencida_actual": st.column_config.NumberColumn("Deuda Vencida Hoy", format="$ {:,.0f}"),
                "max_dias_vencido": st.column_config.NumberColumn("Max Días Vencido", format="%d días"),
                "deuda_total_actual": st.column_config.NumberColumn("Deuda Total Hoy", format="$ {:,.0f}"),
            },
            column_order=("nombre_cliente", "Clasificacion_360", "total_descontado_periodo", "margen_neto_cliente", "deuda_vencida_actual", "max_dias_vencido", "deuda_total_actual")
        )

        st.markdown("---")
        st.subheader("📋 Recomendaciones por Segmento")
        st.markdown("""
        - **✅ Campeón Estratégico:** Clientes rentables y con cartera sana. **Acción:** ¡Fidelizar! Son tus mejores aliados. Considera planes de lealtad y beneficios exclusivos.
        - **⚠️ Rentable pero Riesgoso:** Generan buen margen, pero su deuda vencida es un foco de riesgo. **Acción:** Gestión de cobro proactiva. Condicionar futuros descuentos a la mejora de su cartera. No cortar la relación, pero gestionarla de cerca.
        - **💡 Fuga de Margen:** No son rentables (el descuento supera al margen), pero al menos tienen su cartera al día. **Acción:** Revisar la política de precios y descuentos para este cliente. ¿Se puede reducir el descuento o venderle productos de mayor margen?
        - **🔥 Crítico (Doble Problema):** No son rentables y además tienen una alta deuda vencida. **Acción:** ¡Máxima alerta! Requieren una acción de cobro inmediata y una reevaluación completa de las condiciones comerciales. Suspender descuentos y posiblemente líneas de crédito.
        """)
    else:
        st.warning("No hay datos de clientes para analizar en el período y con los filtros seleccionados.")
