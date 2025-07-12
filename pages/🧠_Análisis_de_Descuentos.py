# ==============================================================================
# SCRIPT UNIFICADO PARA: 🧠 Centro de Control Estratégico v15.0
# VERSIÓN: DEFINITIVA, COMPLETA Y ESTABLE - 12 de Julio, 2025
# DESCRIPCIÓN: Versión final que corrige todos los errores de raíz, incluyendo
#              el ValueError de Plotly. Estructura profesional con funciones
#              modulares para garantizar la funcionalidad de los filtros en
#              toda la aplicación. Contiene todos los análisis solicitados.
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
    """Formatea un número como moneda, porcentaje o entero."""
    if pd.isna(num) or not isinstance(num, (int, float)):
        return "$ 0" if tipo == 'moneda' else ("0.0%" if tipo == 'porcentaje' else "0")
    if tipo == 'moneda':
        return f"${num:,.0f}"
    elif tipo == 'porcentaje':
        return f"{num:.1f}%"
    elif tipo == 'dias':
         return f"{num:,.0f} días"
    return str(num)

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
def cargar_cartera_detallada():
    """Carga, limpia y resume el archivo cartera_detalle.csv desde Dropbox."""
    try:
        with st.spinner("Cargando archivo de Cartera Detallada (deuda actual)..."):
            dbx = dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, app_secret=st.secrets.dropbox.app_secret, oauth2_refresh_token=st.secrets.dropbox.refresh_token)
            _, res = dbx.files_download(path='/data/cartera_detalle.csv')
            contenido_csv = res.content.decode('latin-1')
            nombres_columnas = ['Serie', 'Numero', 'Fecha Documento', 'Fecha Vencimiento', 'Cod Cliente', 'NombreCliente', 'Nit', 'Poblacion', 'Provincia', 'Telefono1', 'Telefono2', 'NomVendedor', 'Entidad Autoriza', 'E-Mail', 'Importe', 'Descuento', 'Cupo Aprobado', 'Dias Vencido']
            df_cartera = pd.read_csv(io.StringIO(contenido_csv), header=None, names=nombres_columnas, sep='|', engine='python', on_bad_lines='skip')
            
            df_cartera['Importe'] = pd.to_numeric(df_cartera['Importe'], errors='coerce').fillna(0)
            df_cartera['Dias Vencido'] = pd.to_numeric(df_cartera['Dias Vencido'], errors='coerce').fillna(0)
            df_cartera['Cod Cliente'] = df_cartera['Cod Cliente'].astype(str).str.strip()
            
            resumen_cartera_cliente = df_cartera.groupby('Cod Cliente').agg(
                deuda_total_actual=('Importe', 'sum'),
                deuda_vencida_actual=('Importe', lambda x: x[df_cartera.loc[x.index, 'Dias Vencido'] > 0].sum()),
                max_dias_vencido=('Dias Vencido', 'max')
            ).reset_index()
            return resumen_cartera_cliente
    except Exception as e:
        st.error(f"Error crítico al cargar cartera_detalle.csv: {e}")
        return pd.DataFrame()

# ==============================================================================
# --- 3. LÓGICA DE PROCESAMIENTO Y ANÁLISIS 360° ---
# ==============================================================================

def procesar_datos_filtrados(df_ventas_filtrado, df_resumen_cartera):
    """Orquesta el análisis completo sobre los datos YA FILTRADOS."""
    if df_ventas_filtrado is None or df_ventas_filtrado.empty:
        return pd.DataFrame(), {}, pd.DataFrame()

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
    df_productos_raw['margen_bruto'] = df_productos_raw['valor_venta'] - (df_productos_raw['costo_unitario'] * df_productos_raw['unidades_vendidas'])
    margen_cliente = df_productos_raw.groupby('cliente_id').agg(margen_generado_periodo=('margen_bruto', 'sum')).reset_index()
    df_analisis_cliente = pd.merge(analisis_descuentos_cliente, margen_cliente, on='cliente_id', how='left')

    if df_resumen_cartera is not None and not df_resumen_cartera.empty:
        df_analisis_cliente = pd.merge(df_analisis_cliente, df_resumen_cartera, left_on='cliente_id', right_on='Cod Cliente', how='left')
        df_analisis_cliente.drop(columns=['Cod Cliente'], inplace=True, errors='ignore')
        df_analisis_cliente.fillna({'deuda_total_actual': 0, 'deuda_vencida_actual': 0, 'max_dias_vencido': 0}, inplace=True)
    else:
        df_analisis_cliente['deuda_total_actual'], df_analisis_cliente['deuda_vencida_actual'], df_analisis_cliente['max_dias_vencido'] = 0, 0, 0

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

    df_analisis_producto = df_descuentos_raw.groupby('nombre_articulo').agg(total_descuento_producto=('valor_venta', lambda x: abs(x.sum()))).reset_index()
    
    kpis = {
        "descuentos_totales": descuentos_totales,
        "margen_neto_total": margen_neto_total,
        "rentabilidad_efectiva": rentabilidad_efectiva,
        "deuda_vencida_clientes_con_dcto": df_analisis_cliente['deuda_vencida_actual'].sum()
    }

    return df_analisis_cliente, kpis, df_analisis_producto

def generar_diagnostico_gerencial(kpis, df_analisis_cliente, vendedor):
    """Genera un análisis en texto basado en los KPIs y datos."""
    nombre_actor = "la Gerencia" if vendedor == "Visión Gerencial (Todos)" else f"el vendedor {vendedor}"
    diagnostico = f"### Diagnóstico para {nombre_actor}:\n"
    
    if kpis['rentabilidad_efectiva'] < 5:
        diagnostico += f"<li>🔴 **Rentabilidad Crítica ({formatear_numero(kpis['rentabilidad_efectiva'], 'porcentaje')}):** El margen neto es muy bajo o negativo. La política de descuentos actual está erosionando severamente las ganancias. Es urgente revisar precios y descuentos.</li>"
    elif kpis['rentabilidad_efectiva'] < 15:
        diagnostico += f"<li>🟡 **Rentabilidad Baja ({formatear_numero(kpis['rentabilidad_efectiva'], 'porcentaje')}):** La rentabilidad está por debajo de un nivel saludable. Hay que optimizar la asignación de descuentos.</li>"
    else:
        diagnostico += f"<li>🟢 **Rentabilidad Saludable ({formatear_numero(kpis['rentabilidad_efectiva'], 'porcentaje')}):** El margen se mantiene en un nivel adecuado después de los descuentos.</li>"

    if kpis['deuda_vencida_clientes_con_dcto'] > kpis['margen_neto_total'] and kpis['margen_neto_total'] > 0:
        diagnostico += f"<li>🔥 **Riesgo Mayor que Recompensa:** La deuda vencida actual de los clientes con descuento ({formatear_numero(kpis['deuda_vencida_clientes_con_dcto'])}) **supera el margen neto total** ({formatear_numero(kpis['margen_neto_total'])}) que generan.</li>"

    if not df_analisis_cliente.empty:
        clientes_criticos = df_analisis_cliente[df_analisis_cliente['Clasificacion_360'] == '🔥 Crítico (Doble Problema)']
        if not clientes_criticos.empty:
            diagnostico += f"<li>🚨 **Focos de Alerta Máxima:** Se han identificado **{len(clientes_criticos)}** clientes 'Críticos', que no son rentables y además presentan una alta deuda vencida. Requieren acción inmediata.</li>"
    
    return f"<ul>{diagnostico}</ul>"

# ==============================================================================
# --- 4. CUERPO PRINCIPAL DE LA APLICACIÓN Y RENDERIZADO ---
# ==============================================================================
def main():
    st.title("🧠 Control Estratégico 360°: Descuentos vs. Cartera v15.0")
    
    # --- Barra Lateral: Controles y Filtros ---
    st.sidebar.title("Control de Datos")
    if st.sidebar.button("🔄 Forzar Actualización de Datos"):
        st.cache_data.clear()
        st.success("Caché limpiado. Los datos se recargarán desde Dropbox.")
        st.rerun()

    st.sidebar.title("Filtros del Análisis")

    # --- Carga de datos ---
    df_ventas_maestro = cargar_ventas_maestro()
    df_resumen_cartera = cargar_cartera_detallada()

    if df_ventas_maestro is None:
        st.warning("No se pueden continuar los análisis sin los datos de ventas.")
        st.stop()

    # --- Lógica Central de Filtrado ---
    min_date = df_ventas_maestro['fecha_venta_norm'].min().date()
    max_date = df_ventas_maestro['fecha_venta_norm'].max().date()
    
    fecha_inicio = st.sidebar.date_input("Fecha de Inicio (Ventas)", value=max_date.replace(day=1), min_value=min_date, max_value=max_date, key="fecha_inicio_filtro")
    fecha_fin = st.sidebar.date_input("Fecha de Fin (Ventas)", value=max_date, min_value=min_date, max_value=max_date, key="fecha_fin_filtro")
    
    if fecha_inicio > fecha_fin: 
        st.sidebar.error("Rango de fechas inválido.")
        st.stop()

    df_ventas_periodo = df_ventas_maestro[(df_ventas_maestro['fecha_venta_norm'].dt.date >= fecha_inicio) & (df_ventas_maestro['fecha_venta_norm'].dt.date <= fecha_fin)]
    
    vendedores_unicos = ['Visión Gerencial (Todos)'] + sorted(df_ventas_periodo['nomvendedor'].dropna().unique().tolist())
    vendedor_seleccionado = st.sidebar.selectbox("Seleccionar Vendedor", options=vendedores_unicos, key="vendedor_filtro")
    
    if vendedor_seleccionado != "Visión Gerencial (Todos)":
        df_ventas_filtrado = df_ventas_periodo[df_ventas_periodo['nomvendedor'] == vendedor_seleccionado]
    else:
        df_ventas_filtrado = df_ventas_periodo

    # --- Ejecución del Procesamiento con datos ya filtrados ---
    df_analisis_cliente, kpis, df_analisis_producto = procesar_datos_filtrados(df_ventas_filtrado, df_resumen_cartera)

    # --- Renderizado de Pestañas ---
    tab1, tab2, tab3 = st.tabs(["📊 **Dashboard Estratégico**", "🎯 **Plan de Acción por Cliente**", "📦 **Análisis por Producto**"])

    with tab1:
        st.header(f"Dashboard Estratégico para: {vendedor_seleccionado}")
        st.info(f"Análisis de ventas del **{fecha_inicio.strftime('%d/%m/%Y')}** al **{fecha_fin.strftime('%d/%m/%Y')}**, cruzado con la **deuda total actual** de los clientes.")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💸 Total Descuentos Otorgados", formatear_numero(kpis.get('descuentos_totales', 0)), help="Suma de todos los descuentos en el período y vendedor seleccionados.")
        col2.metric("💰 Margen Neto del Período", formatear_numero(kpis.get('margen_neto_total', 0)), help="Margen Bruto menos los descuentos otorgados.")
        col3.metric("📈 Rentabilidad Efectiva", formatear_numero(kpis.get('rentabilidad_efectiva', 0), 'porcentaje'), help="Porcentaje del margen neto sobre la venta bruta.")
        col4.metric("🔥 Deuda Vencida (Clientes con Dcto)", formatear_numero(kpis.get('deuda_vencida_clientes_con_dcto', 0)), help="Suma de la deuda vencida actual de los clientes que recibieron descuentos en este período.")
        
        with st.expander("🤖 **Diagnóstico Automático del Asistente IA**", expanded=True):
            diagnostico_html = generar_diagnostico_gerencial(kpis, df_analisis_cliente, vendedor_seleccionado)
            st.markdown(diagnostico_html, unsafe_allow_html=True)
            
        st.markdown("---")
        st.subheader("Matriz de Riesgo (Deuda Vencida) vs. Recompensa (Descuento Otorgado)")

        if not df_analisis_cliente.empty:
            df_plot = df_analisis_cliente.copy().fillna(0)
            df_plot_log = df_plot[(df_plot['total_descontado_periodo'] > 0) & (df_plot['deuda_vencida_actual'] > 0)]
            
            # SOLUCIÓN AL VALUEERROR: Resetear el índice antes de graficar asegura que Plotly no se confunda.
            df_plot_log = df_plot_log.reset_index(drop=True)
            
            df_plot_log['size_plot'] = df_plot_log['margen_neto_cliente'].apply(lambda x: max(x, 1))

            if not df_plot_log.empty:
                fig = px.scatter(df_plot_log, x="total_descontado_periodo", y="deuda_vencida_actual", size="size_plot", color="Clasificacion_360", hover_name="nombre_cliente", log_x=True, log_y=True,
                                 title="Posicionamiento de Clientes (Escala Logarítmica)",
                                 labels={"total_descontado_periodo": "Recompensa (Total Descontado)", "deuda_vencida_actual": "Riesgo (Deuda Vencida Actual)"},
                                 color_discrete_map={"✅ Campeón Estratégico": "#28a745", "⚠️ Rentable pero Riesgoso": "#ffc107", "💡 Fuga de Margen": "#007bff", "🔥 Crítico (Doble Problema)": "#dc3545"})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay clientes con descuentos y deuda vencida simultáneamente para mostrar en el gráfico de riesgo logarítmico.")
        else:
            st.info("No hay datos de clientes con descuentos para analizar en el período seleccionado.")

    with tab2:
        st.header("Plan de Acción y Detalle por Cliente")
        if not df_analisis_cliente.empty:
            df_display = df_analisis_cliente.sort_values(by="total_descontado_periodo", ascending=False)
            st.dataframe(df_display, use_container_width=True, hide_index=True,
                         column_config={
                            "nombre_cliente": st.column_config.TextColumn("Cliente", width="large"), "Clasificacion_360": st.column_config.TextColumn("Clasificación"),
                            "total_descontado_periodo": st.column_config.NumberColumn("Descuento Otorgado", format="$ {:,.0f}"),
                            "margen_neto_cliente": st.column_config.NumberColumn("Margen Neto Cliente", format="$ {:,.0f}"),
                            "deuda_vencida_actual": st.column_config.NumberColumn("Deuda Vencida Hoy", format="$ {:,.0f}"),
                            "max_dias_vencido": st.column_config.NumberColumn("Max Días Vencido", format="%d días"),
                            "deuda_total_actual": st.column_config.NumberColumn("Deuda Total Hoy", format="$ {:,.0f}"),
                            "cliente_id": None, "margen_generado_periodo": None, 
                         })
        else:
            st.warning("No hay clientes con descuentos para analizar en el período y filtros seleccionados.")

    with tab3:
        st.header("Análisis de Descuentos por Producto")
        if not df_analisis_producto.empty:
            df_display_producto = df_analisis_producto.sort_values(by="total_descuento_producto", ascending=False)
            st.markdown(f"Se otorgaron descuentos a **{len(df_display_producto)}** productos únicos en este período.")
            
            fig_prod = px.bar(df_display_producto.head(20), x='nombre_articulo', y='total_descuento_producto',
                              title="Top 20 Productos con Mayor Monto de Descuento Otorgado",
                              labels={'nombre_articulo': 'Producto', 'total_descuento_producto': 'Monto Total Descontado'},
                              text='total_descuento_producto')
            fig_prod.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            fig_prod.update_layout(xaxis_tickangle=-45, yaxis_title="Monto Descontado")
            st.plotly_chart(fig_prod, use_container_width=True)
            
            with st.expander("Ver tabla completa de descuentos por producto"):
                st.dataframe(df_display_producto, use_container_width=True, hide_index=True,
                             column_config={"total_descuento_producto": st.column_config.NumberColumn(format="$ {:,.0f}")})
        else:
            st.info("No se otorgaron descuentos a productos específicos en el período y filtros seleccionados.")

if __name__ == '__main__':
    # Validar que se ha iniciado sesión antes de correr la app principal
    if 'authentication_status' not in st.session_state or not st.session_state['authentication_status']:
        st.title("🔒 Acceso Restringido")
        st.error("Por favor, inicie sesión desde la página principal `🏠 Resumen Mensual`.")
        st.image("https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", width=300)
    else:
        main()
