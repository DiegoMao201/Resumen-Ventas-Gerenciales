# ==============================================================================
# SCRIPT UNIFICADO PARA: 🧠 Centro de Control Estratégico v13.0
# VERSIÓN: DEFINITIVA, PROFESIONAL Y COMPLETA - 12 de Julio, 2025
# DESCRIPCIÓN: Versión final que corrige todos los errores previos, restaura
#              todas las pestañas de análisis y reestructura el código para
#              un rendimiento robusto y una lógica clara. Fusiona el análisis
#              de descuentos con el estado de cuenta detallado del cliente.
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

st.title("🧠 Control Estratégico 360°: Descuentos vs. Cartera v13.0")

# Validación de acceso de usuario
if st.session_state.get('usuario') != "GERENTE":
    st.error("🔒 Acceso Exclusivo para Gerencia.")
    st.info("Por favor, inicie sesión desde la página principal para acceder a esta herramienta.")
    st.stop()

# Función de utilidad para normalizar texto (vendedores, clientes, etc.)
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return texto
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').strip().replace('  ', ' ')
    except (TypeError, AttributeError):
        return texto

# ==============================================================================
# --- 2. LÓGICA DE CARGA Y PREPARACIÓN DE DATOS ---
# ==============================================================================

@st.cache_data(ttl=600)
def cargar_ventas_maestro():
    """Carga y prepara el archivo maestro de ventas desde la sesión de Streamlit."""
    st.write("Cargando datos de ventas...") # Mensaje para depuración
    df_ventas = st.session_state.get('df_ventas')
    if df_ventas is None or df_ventas.empty:
        st.error("Los datos de ventas no se encontraron. Vuelva a la página principal y cargue el archivo maestro.")
        return None
    
    df_ventas['fecha_venta_norm'] = pd.to_datetime(df_ventas['fecha_venta'], errors='coerce').dt.normalize()
    df_ventas['cliente_id'] = df_ventas['cliente_id'].astype(str).str.strip()
    for col in ['valor_venta', 'costo_unitario', 'unidades_vendidas']:
        df_ventas[col] = pd.to_numeric(df_ventas[col], errors='coerce').fillna(0)
        
    return df_ventas

@st.cache_data(ttl=600)
def cargar_cartera_detallada():
    """Carga, limpia y resume el archivo cartera_detalle.csv desde Dropbox."""
    st.write("Cargando datos de cartera detallada...") # Mensaje para depuración
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
        st.error(f"Error al cargar cartera_detalle.csv desde Dropbox: {e}")
        return pd.DataFrame()

# ==============================================================================
# --- 3. LÓGICA DE PROCESAMIENTO Y ANÁLISIS 360° ---
# ==============================================================================

@st.cache_data(ttl=600)
def procesar_analisis_360(_df_ventas_periodo, _df_resumen_cartera):
    """Orquesta el análisis completo, uniendo ventas con cartera para una visión 360°."""
    if _df_ventas_periodo is None or _df_ventas_periodo.empty:
        return pd.DataFrame(), 0, 0, 0

    df_ventas = _df_ventas_periodo.copy()
    
    filtro_descuento = (df_ventas['nombre_articulo'].str.upper().str.contains('DESCUENTO', na=False)) & \
                       (df_ventas['nombre_articulo'].str.upper().str.contains('COMERCIAL', na=False))
    
    df_productos_raw = df_ventas[~filtro_descuento]
    df_descuentos_raw = df_ventas[filtro_descuento]

    # KPIs globales del período de ventas seleccionado
    venta_bruta_total = df_productos_raw['valor_venta'].sum()
    margen_bruto_total = (df_productos_raw['valor_venta'] - (df_productos_raw['costo_unitario'] * df_productos_raw['unidades_vendidas'])).sum()
    total_descuentos_periodo_completo = abs(df_descuentos_raw['valor_venta'].sum())

    # Agregar datos del período por cliente
    analisis_descuentos_cliente = df_descuentos_raw.groupby(['cliente_id', 'nombre_cliente']).agg(
        total_descontado_periodo=('valor_venta', lambda x: abs(x.sum()))
    ).reset_index()
    
    df_productos_raw['margen_bruto'] = df_productos_raw['valor_venta'] - (df_productos_raw['costo_unitario'] * df_productos_raw['unidades_vendidas'])
    margen_cliente = df_productos_raw.groupby('cliente_id').agg(margen_generado_periodo=('margen_bruto', 'sum')).reset_index()

    # Unir análisis del período (descuentos y margen)
    df_final = pd.merge(analisis_descuentos_cliente, margen_cliente, on='cliente_id', how='left')
    
    # Enriquecer con la información de la cartera de deuda actual
    if _df_resumen_cartera is not None and not _df_resumen_cartera.empty:
        df_final = pd.merge(df_final, _df_resumen_cartera, left_on='cliente_id', right_on='Cod Cliente', how='left')
        df_final.drop(columns=['Cod Cliente'], inplace=True, errors='ignore')
        df_final.fillna({'deuda_total_actual': 0, 'deuda_vencida_actual': 0, 'max_dias_vencido': 0}, inplace=True)
    else:
        df_final['deuda_total_actual'] = 0
        df_final['deuda_vencida_actual'] = 0
        df_final['max_dias_vencido'] = 0

    df_final['margen_neto_cliente'] = df_final['margen_generado_periodo'].fillna(0) - df_final['total_descontado_periodo'].fillna(0)
    
    # Clasificación Gerencial 360°
    def clasificar_cliente_360(row):
        deuda_vencida_alta = row['deuda_vencida_actual'] > 100000
        margen_negativo = row['margen_neto_cliente'] < 0
        
        if not margen_negativo and not deuda_vencida_alta: return "✅ Campeón Estratégico"
        if not margen_negativo and deuda_vencida_alta: return "⚠️ Rentable pero Riesgoso"
        if margen_negativo and not deuda_vencida_alta: return "💡 Fuga de Margen"
        if margen_negativo and deuda_vencida_alta: return "🔥 Crítico (Doble Problema)"
        return "Otros"
        
    df_final['Clasificacion_360'] = df_final.apply(clasificar_cliente_360, axis=1)
    
    return df_final, venta_bruta_total, margen_bruto_total, total_descuentos_periodo_completo

# ==============================================================================
# --- 4. CUERPO PRINCIPAL DE LA APLICACIÓN ---
# ==============================================================================

def main():
    # --- Barra Lateral: Controles y Filtros ---
    st.sidebar.title("Control de Datos")
    if st.sidebar.button("🔄 Forzar Actualización de Datos"):
        st.cache_data.clear()
        st.success("Caché limpiado. Los datos se recargarán desde Dropbox.")
        st.rerun()

    st.sidebar.title("Filtros del Análisis")

    # --- Carga de datos inicial ---
    df_ventas_maestro = cargar_ventas_maestro()
    df_resumen_cartera = cargar_cartera_detallada()

    if df_ventas_maestro is None:
        st.warning("No se pueden continuar los análisis sin los datos de ventas.")
        st.stop()

    # --- Aplicación de Filtros ---
    min_date, max_date = df_ventas_maestro['fecha_venta_norm'].min().date(), df_ventas_maestro['fecha_venta_norm'].max().date()
    fecha_inicio = st.sidebar.date_input("Fecha de Inicio (Ventas)", value=max_date.replace(day=1), min_value=min_date, max_value=max_date)
    fecha_fin = st.sidebar.date_input("Fecha de Fin (Ventas)", value=max_date, min_value=min_date, max_value=max_date)
    if fecha_inicio > fecha_fin: 
        st.sidebar.error("Rango de fechas inválido.")
        st.stop()

    # Filtrado por fecha y luego por vendedor
    df_ventas_periodo = df_ventas_maestro[(df_ventas_maestro['fecha_venta_norm'].dt.date >= fecha_inicio) & (df_ventas_maestro['fecha_venta_norm'].dt.date <= fecha_fin)]
    
    vendedores_unicos = ['Visión Gerencial (Todos)'] + sorted(df_ventas_periodo['nomvendedor'].dropna().unique().tolist())
    vendedor_seleccionado = st.sidebar.selectbox("Seleccionar Vendedor", options=vendedores_unicos)
    
    if vendedor_seleccionado != "Visión Gerencial (Todos)":
        df_ventas_filtrado = df_ventas_periodo[df_ventas_periodo['nomvendedor'] == vendedor_seleccionado]
    else:
        df_ventas_filtrado = df_ventas_periodo

    # --- Ejecución del Procesamiento 360 ---
    with st.spinner(f"Ejecutando análisis 360° para {vendedor_seleccionado}..."):
        df_analisis_final, venta_bruta, margen_bruto, descuentos_totales = procesar_analisis_360(
            df_ventas_filtrado, df_resumen_cartera
        )

    # --- Visualización en Pestañas ---
    tab1, tab2, tab3 = st.tabs([
        "📊 **Dashboard Estratégico 360°**", 
        "🎯 **Plan de Acción y Detalle de Clientes**",
        "📂 **Análisis de Cartera Vencida (Pareto)**"
    ])

    # --- Pestaña 1: Dashboard Estratégico 360° ---
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
            # SOLUCIÓN AL ERROR: Filtrar datos para escala logarítmica y manejar tamaño
            df_plot = df_analisis_final.copy().fillna(0)
            df_plot = df_plot[(df_plot['total_descontado_periodo'] > 0) & (df_plot['deuda_vencida_actual'] > 0)]
            
            # Manejar el tamaño para que no sea negativo
            df_plot['size_plot'] = df_plot['margen_neto_cliente'].apply(lambda x: max(x, 1))


            if not df_plot.empty:
                fig = px.scatter(
                    df_plot,
                    x="total_descontado_periodo",
                    y="deuda_vencida_actual",
                    size="size_plot",
                    color="Clasificacion_360",
                    hover_name="nombre_cliente",
                    log_x=True, log_y=True,
                    title="Posicionamiento de Clientes: ¿Justifica el Margen el Riesgo?",
                    labels={
                        "total_descontado_periodo": "Recompensa (Total Descontado) - Escala Log",
                        "deuda_vencida_actual": "Riesgo (Deuda Vencida Actual) - Escala Log",
                        "Clasificacion_360": "Clasificación 360",
                        "size_plot": "Impacto (Margen Neto)"
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
                st.info("No hay clientes con descuentos y deuda vencida simultáneamente para mostrar en el gráfico logarítmico.")
        else:
            st.info("No hay datos suficientes para generar la matriz de riesgo vs recompensa.")

    # --- Pestaña 2: Plan de Acción y Detalle de Clientes ---
    with tab2:
        st.header("Plan de Acción y Detalle por Cliente")
        st.markdown("Utiliza esta tabla para tomar decisiones. Ordena por cualquier columna para identificar tus mayores riesgos y oportunidades.")
        
        if not df_analisis_final.empty:
            df_display = df_analisis_final.copy()
            columnas_ordenadas = [
                "nombre_cliente", "Clasificacion_360", "total_descontado_periodo", 
                "margen_neto_cliente", "deuda_vencida_actual", "max_dias_vencido", "deuda_total_actual"
            ]
            df_display = df_display[columnas_ordenadas]

            st.dataframe(
                df_display.sort_values(by="total_descontado_periodo", ascending=False),
                use_container_width=True, hide_index=True,
                column_config={
                    "nombre_cliente": st.column_config.TextColumn("Cliente", width="large"),
                    "Clasificacion_360": st.column_config.TextColumn("Clasificación"),
                    "total_descontado_periodo": st.column_config.NumberColumn("Descuento Otorgado", format="$ {:,.0f}"),
                    "margen_neto_cliente": st.column_config.NumberColumn("Margen Neto Cliente", format="$ {:,.0f}"),
                    "deuda_vencida_actual": st.column_config.NumberColumn("Deuda Vencida Hoy", format="$ {:,.0f}"),
                    "max_dias_vencido": st.column_config.NumberColumn("Max Días Vencido", format="%d días"),
                    "deuda_total_actual": st.column_config.NumberColumn("Deuda Total Hoy", format="$ {:,.0f}"),
                }
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

    # --- Pestaña 3: Análisis de Cartera Vencida (Pareto) ---
    with tab3:
        st.header("Análisis de Concentración de Deuda Vencida")
        st.markdown("Esta pestaña se enfoca en los clientes que tienen la mayor parte de la deuda vencida, según el archivo de cartera actual.")

        if df_resumen_cartera is not None and not df_resumen_cartera.empty:
            df_cartera_vencida = df_resumen_cartera[df_resumen_cartera['deuda_vencida_actual'] > 0].copy()
            
            if not df_cartera_vencida.empty:
                # Necesitamos el nombre del cliente, que no está en el resumen. Lo traemos del maestro de ventas.
                nombres_clientes = df_ventas_maestro[['cliente_id', 'nombre_cliente']].drop_duplicates()
                df_cartera_vencida = pd.merge(df_cartera_vencida, nombres_clientes, left_on='Cod Cliente', right_on='cliente_id', how='left')
                df_cartera_vencida['nombre_cliente'] = df_cartera_vencida['nombre_cliente'].fillna('Nombre no encontrado')

                client_debt = df_cartera_vencida.set_index('nombre_cliente')['deuda_vencida_actual'].sort_values(ascending=False)
                
                total_debt_vencida = client_debt.sum()
                client_debt_cumsum = client_debt.cumsum()
                pareto_limit = total_debt_vencida * 0.80
                pareto_clients_df = client_debt.to_frame().iloc[0:len(client_debt_cumsum[client_debt_cumsum <= pareto_limit]) + 1]
                
                num_total_clientes_deuda = len(client_debt)
                num_clientes_pareto = len(pareto_clients_df)
                porcentaje_clientes_pareto = (num_clientes_pareto / num_total_clientes_deuda) * 100 if num_total_clientes_deuda > 0 else 0
                
                st.info(f"El **{porcentaje_clientes_pareto:.0f}%** de los clientes con deuda ({num_clientes_pareto} de {num_total_clientes_deuda}) representan aproximadamente el **80%** del total de la cartera vencida.")
                
                df_pareto_display = pareto_clients_df.reset_index()
                df_pareto_display.columns = ['Cliente', 'Monto Vencido']
                st.dataframe(df_pareto_display, hide_index=True, use_container_width=True,
                    column_config={"Monto Vencido": st.column_config.NumberColumn(format="$ {:,.0f}")}
                )
            else:
                st.success("¡Felicidades! No se encontró cartera vencida en el archivo de detalle de cartera.")
        else:
            st.warning("No se pudo cargar el archivo de detalle de cartera para realizar el análisis de Pareto.")

# --- Punto de entrada para ejecutar la aplicación ---
if __name__ == '__main__':
    main()
