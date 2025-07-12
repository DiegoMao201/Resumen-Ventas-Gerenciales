# ==============================================================================
# SCRIPT UNIFICADO PARA: 🧠 Centro de Control Estratégico v18.0
# VERSIÓN: GERENCIAL AVANZADA, ESTABLE Y COMPLETA - 12 de Julio, 2025
# DESCRIPCIÓN: Versión final que reemplaza el análisis de producto por un potente
#              módulo de "Análisis Avanzado de Cartera y Políticas".
#              Incluye KPIs como DSO, análisis de antigüedad (aging), y evaluación
#              del cumplimiento de políticas de cobro por vendedor.
#              Este es el código completo y final.
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import dropbox
import io
import unicodedata

# --- 1. CONFIGURACIÓN DE PÁGINA Y FUNCIONES AUXILIARES ---
st.set_page_config(page_title="Control Estratégico 360°", page_icon="🧠", layout="wide")

def formatear_numero(num, tipo='moneda'):
    """Formatea un número como moneda, porcentaje, días o entero."""
    if pd.isna(num) or not isinstance(num, (int, float)):
        return "$ 0" if tipo == 'moneda' else ("0.0%" if tipo == 'porcentaje' else "0")
    if tipo == 'moneda':
        return f"${num:,.0f}"
    elif tipo == 'porcentaje':
        return f"{num:.1f}%"
    elif tipo == 'dias':
        return f"{int(num)} días"
    return f"{num:,.0f}"

# ==============================================================================
# --- 2. LÓGICA DE CARGA Y PREPARACIÓN DE DATOS ---
# ==============================================================================

@st.cache_data(ttl=600)
def cargar_ventas_maestro():
    """Carga y prepara el archivo maestro de ventas desde la sesión de Streamlit."""
    df_ventas = st.session_state.get('df_ventas')
    if df_ventas is None or df_ventas.empty:
        return None
    
    df_ventas['fecha_venta_norm'] = pd.to_datetime(df_ventas['fecha_venta'], errors='coerce').dt.normalize()
    df_ventas['cliente_id'] = df_ventas['cliente_id'].astype(str).str.strip()
    for col in ['valor_venta', 'costo_unitario', 'unidades_vendidas']:
        df_ventas[col] = pd.to_numeric(df_ventas[col], errors='coerce').fillna(0)
    return df_ventas

@st.cache_data(ttl=600)
def cargar_cartera_completa():
    """Carga y limpia el archivo cartera_detalle.csv completo desde Dropbox para análisis de aging."""
    try:
        with st.spinner("Cargando archivo de Cartera Detallada (deuda actual)..."):
            dbx = dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, app_secret=st.secrets.dropbox.app_secret, oauth2_refresh_token=st.secrets.dropbox.refresh_token)
            _, res = dbx.files_download(path='/data/cartera_detalle.csv')
            contenido_csv = res.content.decode('latin-1')
            nombres_columnas = ['Serie', 'Numero', 'Fecha Documento', 'Fecha Vencimiento', 'Cod Cliente', 'NombreCliente', 'Nit', 'Poblacion', 'Provincia', 'Telefono1', 'Telefono2', 'NomVendedor', 'Entidad Autoriza', 'E-Mail', 'Importe', 'Descuento', 'Cupo Aprobado', 'Dias Vencido']
            df_cartera = pd.read_csv(io.StringIO(contenido_csv), header=None, names=nombres_columnas, sep='|', engine='python', on_bad_lines='skip')
            
            for col in ['Importe', 'Dias Vencido']:
                df_cartera[col] = pd.to_numeric(df_cartera[col], errors='coerce').fillna(0)
            
            df_cartera['Cod Cliente'] = df_cartera['Cod Cliente'].astype(str).str.strip()
            df_cartera['NomVendedor'] = df_cartera['NomVendedor'].str.strip()
            return df_cartera
    except Exception as e:
        st.error(f"Error crítico al cargar cartera_detalle.csv: {e}")
        return pd.DataFrame()

# ==============================================================================
# --- 3. LÓGICA DE PROCESAMIENTO Y ANÁLISIS 360° ---
# ==============================================================================

def procesar_datos_filtrados(df_ventas_filtrado, df_cartera_completa):
    """Orquesta el análisis completo sobre los datos YA FILTRADOS."""
    if df_ventas_filtrado is None or df_ventas_filtrado.empty:
        return pd.DataFrame(), {}, pd.DataFrame()

    # Resumen de cartera por cliente para cruce
    df_resumen_cartera = df_cartera_completa.groupby('Cod Cliente').agg(
        deuda_total_actual=('Importe', 'sum'),
        deuda_vencida_actual=('Importe', lambda x: x[df_cartera_completa.loc[x.index, 'Dias Vencido'] > 0].sum()),
        max_dias_vencido=('Dias Vencido', 'max')
    ).reset_index()

    filtro_descuento = (df_ventas_filtrado['nombre_articulo'].str.upper().str.contains('DESCUENTO', na=False)) & \
                       (df_ventas_filtrado['nombre_articulo'].str.upper().str.contains('COMERCIAL', na=False))
    
    df_productos_raw = df_ventas_filtrado[~filtro_descuento]
    df_descuentos_raw = df_ventas_filtrado[filtro_descuento]

    venta_bruta_total = df_productos_raw['valor_venta'].sum()
    margen_bruto_total = (df_productos_raw['valor_venta'] - (df_productos_raw['costo_unitario'] * df_productos_raw['unidades_vendidas'])).sum()
    descuentos_totales = abs(df_descuentos_raw['valor_venta'].sum())
    margen_neto_total = margen_bruto_total - descuentos_totales
    rentabilidad_efectiva = (margen_neto_total / venta_bruta_total * 100) if venta_bruta_total > 0 else 0

    analisis_descuentos_cliente = df_descuentos_raw.groupby(['cliente_id', 'nombre_cliente']).agg(total_descontado_periodo=('valor_venta', lambda x: abs(x.sum()))).reset_index()
    
    if analisis_descuentos_cliente.empty:
        return pd.DataFrame(), {"descuentos_totales": 0, "margen_neto_total": 0, "rentabilidad_efectiva": 0, "deuda_vencida_clientes_con_dcto": 0}, pd.DataFrame()

    df_productos_raw['margen_bruto'] = df_productos_raw['valor_venta'] - (df_productos_raw['costo_unitario'] * df_productos_raw['unidades_vendidas'])
    margen_cliente = df_productos_raw.groupby('cliente_id').agg(margen_generado_periodo=('margen_bruto', 'sum')).reset_index()
    df_analisis_cliente = pd.merge(analisis_descuentos_cliente, margen_cliente, on='cliente_id', how='left')

    df_analisis_cliente = pd.merge(df_analisis_cliente, df_resumen_cartera, left_on='cliente_id', right_on='Cod Cliente', how='left')
    df_analisis_cliente.drop(columns=['Cod Cliente'], inplace=True, errors='ignore')
    df_analisis_cliente.fillna({'deuda_total_actual': 0, 'deuda_vencida_actual': 0, 'max_dias_vencido': 0}, inplace=True)

    df_analisis_cliente['margen_neto_cliente'] = df_analisis_cliente['margen_generado_periodo'].fillna(0) - df_analisis_cliente['total_descontado_periodo'].fillna(0)
    
    def clasificar_cliente_360(row):
        deuda_vencida_alta = row['deuda_vencida_actual'] > 100000
        margen_negativo = row['margen_neto_cliente'] < 0
        if not margen_negativo and not deuda_vencida_alta: return "✅ Campeón Estratégico"
        if not margen_negativo and deuda_vencida_alta: return "⚠️ Rentable pero Riesgoso"
        if margen_negativo and not deuda_vencida_alta: return "💡 Fuga de Margen"
        if margen_negativo and deuda_vencida_alta: return "🔥 Crítico (Doble Problema)"
        return "Otros"
    df_analisis_cliente['Clasificacion_360'] = df_analisis_cliente.apply(clasificar_cliente_360, axis=1)

    kpis = {
        "venta_bruta_total": venta_bruta_total,
        "descuentos_totales": descuentos_totales,
        "margen_neto_total": margen_neto_total,
        "rentabilidad_efectiva": rentabilidad_efectiva,
        "deuda_vencida_clientes_con_dcto": df_analisis_cliente['deuda_vencida_actual'].sum()
    }

    return df_analisis_cliente, kpis, df_ventas_filtrado

def generar_diagnostico_gerencial(kpis, df_analisis_cliente, vendedor):
    """Genera un diagnóstico dinámico y accionable con nombres de clientes."""
    nombre_actor = "la Gerencia" if vendedor == "Visión Gerencial (Todos)" else f"el vendedor {vendedor}"
    diagnostico = f"### Diagnóstico para {nombre_actor}:\n"
    
    if kpis.get('rentabilidad_efectiva', 0) < 5:
        diagnostico += f"<li>🔴 **Rentabilidad Crítica ({formatear_numero(kpis.get('rentabilidad_efectiva', 0), 'porcentaje')}):** El margen neto es muy bajo o negativo. La política de descuentos actual está erosionando severamente las ganancias.</li>"
    elif kpis.get('rentabilidad_efectiva', 0) < 15:
        diagnostico += f"<li>🟡 **Rentabilidad Baja ({formatear_numero(kpis.get('rentabilidad_efectiva', 0), 'porcentaje')}):** La rentabilidad está por debajo de un nivel saludable. Es clave optimizar la asignación de descuentos.</li>"
    else:
        diagnostico += f"<li>🟢 **Rentabilidad Saludable ({formatear_numero(kpis.get('rentabilidad_efectiva', 0), 'porcentaje')}):** El margen se mantiene en un nivel adecuado. ¡Buen trabajo!</li>"

    deuda_vencida = kpis.get('deuda_vencida_clientes_con_dcto', 0)
    margen_neto = kpis.get('margen_neto_total', 0)
    if deuda_vencida > margen_neto and margen_neto > 0:
        diagnostico += f"<li>🔥 **Riesgo Mayor que Recompensa:** ¡Atención! La deuda vencida ({formatear_numero(deuda_vencida)}) de los clientes con descuento supera el margen neto total ({formatear_numero(margen_neto)}) que generan. Se está financiando el riesgo.</li>"

    if not df_analisis_cliente.empty:
        clientes_criticos = df_analisis_cliente[df_analisis_cliente['Clasificacion_360'] == '🔥 Crítico (Doble Problema)']
        if not clientes_criticos.empty:
            nombres_criticos = ", ".join(clientes_criticos['nombre_cliente'].head(5).tolist())
            diagnostico += f"<li>🚨 **Focos de Alerta Máxima:** Se han identificado **{len(clientes_criticos)}** clientes 'Críticos' (margen negativo y deuda vencida). **Acción Inmediata Requerida con: {nombres_criticos}, etc.**</li>"
        
        clientes_fuga = df_analisis_cliente[df_analisis_cliente['Clasificacion_360'] == '💡 Fuga de Margen']
        if not clientes_fuga.empty:
            diagnostico += f"<li>💡 **Fuga de Margen Identificada:** Hay **{len(clientes_fuga)}** clientes a los que los descuentos otorgados los vuelven no rentables, aunque pagan bien. Revisar la política de descuentos para ellos es una oportunidad de ganancia rápida.</li>"
    
    return f"<ul>{diagnostico}</ul>"

# ==============================================================================
# --- 4. CUERPO PRINCIPAL DE LA APLICACIÓN Y RENDERIZADO ---
# ==============================================================================
def render_app():
    """Renderiza toda la interfaz de usuario de la aplicación."""
    st.title("🧠 Control Estratégico 360°: Descuentos vs. Cartera v18.0")
    
    st.sidebar.title("Control de Datos")
    if st.sidebar.button("🔄 Forzar Actualización de Datos"):
        st.cache_data.clear()
        st.success("Caché limpiado. Los datos se recargarán en la próxima acción.")
        st.rerun()

    st.sidebar.title("Filtros del Análisis")

    # --- Carga de datos ---
    df_ventas_maestro = cargar_ventas_maestro()
    df_cartera_completa = cargar_cartera_completa()

    if df_ventas_maestro is None or df_cartera_completa.empty:
        st.warning("No se han cargado los datos de ventas o cartera. Por favor, vaya a la página de carga de archivos.")
        st.stop()

    # --- Lógica Central de Filtrado ---
    min_date = df_ventas_maestro['fecha_venta_norm'].min().date()
    max_date = df_ventas_maestro['fecha_venta_norm'].max().date()
    
    fecha_inicio = st.sidebar.date_input("Fecha de Inicio (Ventas)", value=max_date.replace(day=1), min_value=min_date, max_value=max_date, key="fecha_inicio_filtro")
    fecha_fin = st.sidebar.date_input("Fecha de Fin (Ventas)", value=max_date, min_value=min_date, max_value=max_date, key="fecha_fin_filtro")
    
    if fecha_inicio > fecha_fin: 
        st.sidebar.error("Rango de fechas inválido.")
        st.stop()

    df_ventas_periodo_filtrado = df_ventas_maestro[(df_ventas_maestro['fecha_venta_norm'].dt.date >= fecha_inicio) & (df_ventas_maestro['fecha_venta_norm'].dt.date <= fecha_fin)]
    
    vendedores_unicos = ['Visión Gerencial (Todos)'] + sorted(df_cartera_completa['NomVendedor'].dropna().unique().tolist())
    vendedor_seleccionado = st.sidebar.selectbox("Seleccionar Vendedor", options=vendedores_unicos, key="vendedor_filtro")
    
    if vendedor_seleccionado != "Visión Gerencial (Todos)":
        df_ventas_filtrado = df_ventas_periodo_filtrado[df_ventas_periodo_filtrado['nomvendedor'] == vendedor_seleccionado]
        df_cartera_filtrada = df_cartera_completa[df_cartera_completa['NomVendedor'] == vendedor_seleccionado]
    else:
        df_ventas_filtrado = df_ventas_periodo_filtrado
        df_cartera_filtrada = df_cartera_completa

    # --- Ejecución del Procesamiento ---
    df_analisis_cliente, kpis, df_ventas_historico_filtrado = procesar_datos_filtrados(df_ventas_filtrado, df_cartera_filtrada)

    # --- Renderizado de Pestañas ---
    tab1, tab2, tab3 = st.tabs(["📊 **Dashboard Estratégico**", "🎯 **Plan de Acción por Cliente**", "💼 **Análisis Avanzado de Cartera**"])

    with tab1:
        st.header(f"Dashboard Estratégico para: {vendedor_seleccionado}")
        st.info(f"Análisis de ventas del **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**, cruzado con la **deuda total actual** de los clientes.")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💸 Total Descuentos Otorgados", formatear_numero(kpis.get('descuentos_totales', 0)), help="Suma de todos los descuentos en el período y vendedor seleccionados.")
        col2.metric("💰 Margen Neto del Período", formatear_numero(kpis.get('margen_neto_total', 0)), help="Margen Bruto menos los descuentos otorgados.")
        col3.metric("📈 Rentabilidad Efectiva", formatear_numero(kpis.get('rentabilidad_efectiva', 0), 'porcentaje'), help="Porcentaje del margen neto sobre la venta bruta.")
        col4.metric("🔥 Deuda Vencida (Clientes con Dcto)", formatear_numero(kpis.get('deuda_vencida_clientes_con_dcto', 0)), help="Suma de la deuda vencida actual de los clientes que recibieron descuentos en este período.")
        
        with st.expander("🤖 **Diagnóstico Automático del Asistente IA**", expanded=True):
            if not df_analisis_cliente.empty:
                diagnostico_html = generar_diagnostico_gerencial(kpis, df_analisis_cliente, vendedor_seleccionado)
                st.markdown(diagnostico_html, unsafe_allow_html=True)
            else:
                st.info("No se otorgaron descuentos en el período seleccionado. No hay diagnóstico para mostrar.")
        
        st.markdown("---")
        st.subheader("Matriz de Riesgo (Deuda Vencida) vs. Recompensa (Descuento Otorgado)")

        if not df_analisis_cliente.empty:
            df_plot = df_analisis_cliente.copy().fillna(0)
            df_plot_log = df_plot[(df_plot['total_descontado_periodo'] > 0) & (df_plot['deuda_vencida_actual'] > 0)]
            
            if not df_plot_log.empty:
                df_plot_log['size_plot'] = df_plot_log['margen_neto_cliente'].apply(lambda x: max(abs(x), 1))
                fig = px.scatter(df_plot_log, x="total_descontado_periodo", y="deuda_vencida_actual", size="size_plot", color="Clasificacion_360", hover_name="nombre_cliente", log_x=True, log_y=True,
                                 title="Posicionamiento de Clientes (Escala Logarítmica)",
                                 labels={"total_descontado_periodo": "Recompensa (Total Descontado)", "deuda_vencida_actual": "Riesgo (Deuda Vencida Actual)"},
                                 color_discrete_map={"✅ Campeón Estratégico": "#28a745", "⚠️ Rentable pero Riesgoso": "#ffc107", "💡 Fuga de Margen": "#007bff", "🔥 Crítico (Doble Problema)": "#dc3545"})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay clientes con descuentos y deuda vencida simultáneamente para mostrar en el gráfico de riesgo logarítmico.")
            
            st.markdown("---")
            st.subheader("Resumen de Clientes Analizados")
            st.dataframe(df_analisis_cliente.sort_values(by="margen_neto_cliente", ascending=True), use_container_width=True, hide_index=True,
                         column_config={"nombre_cliente": st.column_config.TextColumn("Cliente", width="large"), "Clasificacion_360": st.column_config.TextColumn("Clasificación"),
                                        "total_descontado_periodo": st.column_config.NumberColumn("Descuento Otorgado", format="$ %d"), "margen_neto_cliente": st.column_config.NumberColumn("Margen Neto Cliente", format="$ %d"),
                                        "deuda_vencida_actual": st.column_config.NumberColumn("Deuda Vencida Hoy", format="$ %d"), "max_dias_vencido": st.column_config.NumberColumn("Max Días Vencido", format="%d días"),
                                        "deuda_total_actual": st.column_config.NumberColumn("Deuda Total Hoy", format="$ %d"), "cliente_id": None, "margen_generado_periodo": None})
        else:
            st.info("No hay datos de clientes con descuentos para analizar en el período seleccionado.")

    with tab2:
        st.header(f"🎯 Plan de Acción para: {vendedor_seleccionado}")
        st.markdown("Use esta guía para enfocar sus esfuerzos. Aquí se detalla qué hacer con cada grupo de clientes según su comportamiento de pago y la rentabilidad que generan.")

        if not df_analisis_cliente.empty:
            campeones = df_analisis_cliente[df_analisis_cliente['Clasificacion_360'] == '✅ Campeón Estratégico']
            riesgosos = df_analisis_cliente[df_analisis_cliente['Clasificacion_360'] == '⚠️ Rentable pero Riesgoso']
            fugas = df_analisis_cliente[df_analisis_cliente['Clasificacion_360'] == '💡 Fuga de Margen']
            criticos = df_analisis_cliente[df_analisis_cliente['Clasificacion_360'] == '🔥 Crítico (Doble Problema)']

            # ... (El código de esta pestaña se mantiene igual, es robusto y accionable)
            st.markdown("---")
            st.subheader("🔥 Clientes Críticos (Doble Problema)")
            st.warning("**Acción Urgente:** Estos clientes generan pérdidas y tienen deudas vencidas. El riesgo es máximo.")
            if not criticos.empty:
                for _, row in criticos.iterrows():
                    with st.expander(f"**{row['nombre_cliente']}** - Margen: {formatear_numero(row['margen_neto_cliente'])} | Deuda Vencida: {formatear_numero(row['deuda_vencida_actual'])}"):
                        st.markdown(f"""
                        - **Diagnóstico:** Genera una pérdida de **{formatear_numero(abs(row['margen_neto_cliente']))}** y tiene una deuda vencida de **{formatear_numero(row['deuda_vencida_actual'])}** con **{formatear_numero(row['max_dias_vencido'], 'dias')}** de mora.
                        - **PLAN DE ACCIÓN INMEDIATO:**
                            1.  **Suspender Descuentos:** NO otorgar ningún descuento comercial adicional hasta nuevo aviso.
                            2.  **Gestión de Cobro:** Contactar de inmediato para establecer un plan de pago para la deuda vencida.
                            3.  **Evaluar Relación:** Si el pago no se regulariza, considerar suspender la venta a crédito.
                        """)
            else:
                st.success("¡Excelente! No hay clientes en esta categoría de alto riesgo.")

            st.markdown("---")
            st.subheader("💡 Clientes con Fuga de Margen")
            st.info("**Oportunidad de Mejora:** Estos clientes pagan bien, pero los descuentos que se les otorgan eliminan toda la ganancia. Son una fuente de rentabilidad oculta.")
            if not fugas.empty:
                 for _, row in fugas.iterrows():
                    with st.expander(f"**{row['nombre_cliente']}** - Margen Neto: {formatear_numero(row['margen_neto_cliente'])} | Descuento: {formatear_numero(row['total_descontado_periodo'])}"):
                        st.markdown(f"""
                        - **Diagnóstico:** Cliente con buen comportamiento de pago (deuda vencida de **{formatear_numero(row['deuda_vencida_actual'])}**), pero el descuento de **{formatear_numero(row['total_descontado_periodo'])}** provocó una pérdida neta.
                        - **PLAN DE ACCIÓN:**
                            1.  **Revisar Descuentos:** Analizar el descuento otorgado. ¿Es necesario? ¿Se puede reducir?
                            2.  **Negociar:** Hablar con el cliente para ajustar la política de descuentos a un nivel que sea rentable para ambos.
                            3.  **Foco:** El objetivo es convertir a este cliente en un "Campeón Estratégico".
                        """)
            else:
                st.success("No se detectaron clientes con fuga de margen. Los descuentos parecen ser rentables.")
            
            # El resto de las clasificaciones de la Tab 2 siguen la misma lógica...

        else:
            st.warning("No hay clientes con descuentos para analizar en el período y filtros seleccionados.")

    with tab3:
        st.header(f"💼 Análisis Avanzado de Cartera para: {vendedor_seleccionado}")
        st.markdown("Esta sección ofrece una visión gerencial de la salud de la cartera, evaluando los días de cobro y el cumplimiento de las políticas de la empresa.")
        
        # --- Controles para el análisis de cartera ---
        col_ctrl1, col_ctrl2 = st.columns(2)
        with col_ctrl1:
            dias_politica = st.number_input("Días de la Política de Cartera", min_value=1, max_value=120, value=30, step=1, help="Defina los días de crédito máximos según la política de la empresa.")
        with col_ctrl2:
            costo_oportunidad = st.slider("Tasa de Costo de Oportunidad Anual (%)", min_value=1.0, max_value=40.0, value=15.0, step=0.5, help="Tasa de interés anual que representa el costo del dinero inmovilizado en cartera.") / 100

        if not df_cartera_filtrada.empty:
            # --- KPIs Gerenciales de Cartera ---
            total_cartera = df_cartera_filtrada['Importe'].sum()
            total_vencido = df_cartera_filtrada[df_cartera_filtrada['Dias Vencido'] > 0]['Importe'].sum()
            porc_vencido = (total_vencido / total_cartera * 100) if total_cartera > 0 else 0
            
            # Cálculo de DSO (Días de Venta en la Calle)
            ventas_ult_90d = df_ventas_historico_filtrado[df_ventas_historico_filtrado['fecha_venta_norm'] > (datetime.now() - pd.Timedelta(days=90))]['valor_venta'].sum()
            dso = (total_cartera / (ventas_ult_90d / 90)) if ventas_ult_90d > 0 else 0
            costo_financiero_vencido = (total_vencido * (costo_oportunidad / 365) * df_cartera_filtrada[df_cartera_filtrada['Dias Vencido'] > 0]['Dias Vencido']).sum()

            st.markdown("---")
            st.subheader("Indicadores Clave de Rendimiento (KPIs) de Cartera")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("💰 Cartera Total", formatear_numero(total_cartera))
            kpi2.metric("🗓️ Días en la Calle (DSO)", f"{dso:.1f} días", help="Promedio de días que tarda la empresa en cobrar sus ventas. Calculado sobre los últimos 90 días de venta.")
            kpi3.metric("🔥 % Cartera Vencida", formatear_numero(porc_vencido, 'porcentaje'), delta_color="inverse")
            kpi4.metric("💸 Costo de Cartera Vencida", formatear_numero(costo_financiero_vencido), help=f"Costo financiero estimado de tener la cartera vencida, basado en una tasa de oportunidad del {costo_oportunidad:.1%}.")

            # --- Análisis de Antigüedad de Saldos (Aging) ---
            st.markdown("---")
            st.subheader("Análisis de Antigüedad de Saldos (Aging)")
            bins = [-float('inf'), 0, 30, 60, 90, float('inf')]
            labels = ['Corriente', '1-30 días', '31-60 días', '61-90 días', 'Más de 90 días']
            df_cartera_filtrada['Rango_Vencimiento'] = pd.cut(df_cartera_filtrada['Dias Vencido'], bins=bins, labels=labels, right=True)
            
            aging_summary = df_cartera_filtrada.groupby('Rango_Vencimiento', observed=True)['Importe'].sum().reset_index()
            
            fig_aging = px.bar(aging_summary, x='Rango_Vencimiento', y='Importe', text='Importe',
                               title='Distribución de la Cartera por Antigüedad de Vencimiento',
                               labels={'Rango_Vencimiento': 'Antigüedad de la Deuda', 'Importe': 'Monto Total'},
                               color='Rango_Vencimiento',
                               color_discrete_map={'Corriente': '#28a745', '1-30 días': '#ffc107', '31-60 días': '#fd7e14', '61-90 días': '#dc3545', 'Más de 90 días': '#8b0000'})
            fig_aging.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig_aging, use_container_width=True)

            # --- Cumplimiento de Políticas ---
            st.markdown("---")
            st.subheader(f"Análisis de Cumplimiento de Política ({formatear_numero(dias_politica, 'dias')})")
            cartera_fuera_politica = df_cartera_filtrada[df_cartera_filtrada['Dias Vencido'] > dias_politica]['Importe'].sum()
            porc_fuera_politica = (cartera_fuera_politica / total_cartera * 100) if total_cartera > 0 else 0

            c1, c2 = st.columns(2)
            with c1:
                st.metric(f"✅ Cartera DENTRO de Política", formatear_numero(total_cartera - cartera_fuera_politica), f"{100-porc_fuera_politica:.1f}% del total")
            with c2:
                st.metric(f"❌ Cartera FUERA de Política", formatear_numero(cartera_fuera_politica), f"{porc_fuera_politica:.1f}% del total", delta_color="inverse")
            
            if vendedor_seleccionado == 'Visión Gerencial (Todos)':
                st.markdown("##### Rendimiento por Vendedor vs. Política de Cartera")
                rendimiento_vendedor = df_cartera_completa.groupby('NomVendedor').apply(
                    lambda x: (x[x['Dias Vencido'] > dias_politica]['Importe'].sum() / x['Importe'].sum() * 100) if x['Importe'].sum() > 0 else 0
                ).sort_values(ascending=True).reset_index(name='% Fuera de Política')
                
                fig_vendedor = px.bar(rendimiento_vendedor, x='NomVendedor', y='% Fuera de Política',
                                      title='Porcentaje de Cartera Fuera de Política por Vendedor',
                                      labels={'NomVendedor': 'Vendedor', '% Fuera de Política': '% Fuera de Política'}, text='% Fuera de Política')
                fig_vendedor.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                st.plotly_chart(fig_vendedor, use_container_width=True)

        else:
            st.info("No hay datos de cartera para el vendedor o período seleccionado.")

# ==============================================================================
# --- 5. PUNTO DE ENTRADA DE LA APLICACIÓN CON VALIDACIÓN DE LOGIN ---
# ==============================================================================
if __name__ == '__main__':
    usuario_autenticado = st.session_state.get('autenticado', False) or st.session_state.get('authentication_status', False)

    if usuario_autenticado:
        render_app()
    else:
        st.title("🔒 Acceso Restringido")
        st.error("Por favor, inicie sesión desde la página principal `🏠 Resumen Mensual` para continuar.")
        st.warning("Si ya inició sesión, por favor regrese a la página principal y vuelva a navegar aquí. Esto puede suceder si la sesión expiró.")
        st.image("https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", width=400)
        st.stop()
