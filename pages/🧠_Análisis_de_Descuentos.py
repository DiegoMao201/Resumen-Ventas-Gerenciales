# ==============================================================================
# SCRIPT PARA: 🧠 Centro de Análisis de Cartera y Descuentos
# VERSIÓN: 4.1 FINAL CORREGIDA - 07 de Julio, 2025
# DESCRIPCIÓN: Versión definitiva que utiliza el nuevo archivo 'Cobros.xlsx'
#              con la ruta de Dropbox corregida para un análisis preciso.
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN ---
st.set_page_config(page_title="Análisis de Cartera y Dctos", page_icon="🧠", layout="wide")

st.title("🧠 Centro de Análisis de Cartera y Descuentos")

if st.session_state.get('usuario') != "GERENTE":
    st.error("🔒 Acceso Exclusivo para Gerencia.")
    st.stop()

# --- LÓGICA DE CARGA DE DATOS (INCLUYE EL NUEVO EXCEL DE COBROS) ---

@st.cache_data
def cargar_datos_completos(dropbox_path_ventas, dropbox_path_cobros):
    """
    Carga tanto el CSV de ventas como el nuevo Excel de cobros desde Dropbox.
    """
    try:
        # Carga de Ventas (usando los datos ya en sesión para eficiencia)
        df_ventas = st.session_state.get('df_ventas')
        if df_ventas is None:
            st.error("Los datos de ventas no se encontraron. Vuelva a la página principal.")
            return None, None

        # Carga del nuevo archivo de Cobros (Excel)
        with st.spinner("Cargando archivo de cobros desde Dropbox..."):
            import dropbox
            import io
            # Se asume que las credenciales están en st.secrets como en la app principal
            dbx = dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, app_secret=st.secrets.dropbox.app_secret, oauth2_refresh_token=st.secrets.dropbox.refresh_token)
            _, res = dbx.files_download(path=dropbox_path_cobros)
            df_cobros = pd.read_excel(io.BytesIO(res.content))
        
        return df_ventas, df_cobros
    except Exception as e:
        st.error(f"Error crítico al cargar los archivos desde Dropbox: {e}")
        st.info("Asegúrese de que el archivo 'Cobros.xlsx' exista en la carpeta '/data/' de su Dropbox.")
        return None, None

@st.cache_data
def procesar_y_unir_datos(_df_ventas, _df_cobros, nombre_articulo_descuento):
    """
    Une los datos de ventas y cobros para un análisis preciso y rápido.
    """
    # 1. Preparar Ventas y Descuentos
    df_ventas = _df_ventas.copy()
    df_ventas['fecha_venta'] = pd.to_datetime(df_ventas['fecha_venta'])
    
    df_productos = df_ventas[df_ventas['valor_venta'] > 0]
    df_descuentos = df_ventas[df_ventas['nombre_articulo'] == nombre_articulo_descuento]

    # Agrupar ventas por factura para tener el valor total de la compra
    ventas_agrupadas = df_productos.groupby('Serie').agg(
        valor_compra=('valor_venta', 'sum'),
        fecha_venta=('fecha_venta', 'first'),
        nomvendedor=('nomvendedor', 'first'),
        nombre_cliente=('nombre_cliente', 'first')
    ).reset_index()

    # 2. Preparar Cobros
    df_cobros = _df_cobros.copy()
    # Renombrar columnas para facilitar el manejo
    df_cobros = df_cobros.rename(columns={
        'Fecha Documento': 'fecha_documento',
        'Fecha Saldado': 'fecha_saldado',
        'NOMBRECLIENTE': 'nombre_cliente_cobro',
        'NOMVENDEDOR': 'nomvendedor_cobro'
    })
    df_cobros['fecha_documento'] = pd.to_datetime(df_cobros['fecha_documento'])
    df_cobros['fecha_saldado'] = pd.to_datetime(df_cobros['fecha_saldado'])

    # 3. UNIÓN DE DATOS (MERGE)
    # Unimos las ventas con su información de cobro correspondiente usando la Serie
    df_completo = pd.merge(ventas_agrupadas, df_cobros[['Serie', 'fecha_saldado']], on='Serie', how='left')

    # 4. CÁLCULOS
    # Calcular días de pago reales solo para las facturas que han sido saldadas
    df_completo['dias_pago'] = (df_completo['fecha_saldado'] - df_completo['fecha_venta']).dt.days

    # Agrupar descuentos por cliente para el análisis cruzado
    descuentos_por_cliente = df_descuentos.groupby('nombre_cliente').agg(
        total_descontado=('valor_venta', 'sum')
    ).reset_index()
    descuentos_por_cliente['total_descontado'] = abs(descuentos_por_cliente['total_descontado'])

    # 5. ANÁLISIS CRUZADO FINAL
    # Agrupar los datos completos por cliente para obtener días de pago promedio
    analisis_cliente = df_completo.dropna(subset=['dias_pago']).groupby('nombre_cliente').agg(
        dias_pago_promedio=('dias_pago', 'mean'),
        total_comprado=('valor_compra', 'sum')
    ).reset_index()

    # Unir los promedios de pago con los totales descontados
    analisis_final = pd.merge(analisis_cliente, descuentos_por_cliente, on='nombre_cliente', how='left').fillna(0)
    
    return df_completo, df_descuentos, analisis_final


# ==============================================================================
# EJECUCIÓN PRINCIPAL Y RENDERIZADO DE LA INTERFAZ
# ==============================================================================

# --- Carga de Datos ---
df_ventas, df_cobros = cargar_datos_completos(
    dropbox_path_ventas="/data/ventas_detalle.csv",
    dropbox_path_cobros="/data/Cobros.xlsx" # Ruta corregida
)

# Si la carga falla, la aplicación se detiene aquí.
if df_ventas is None or df_cobros is None:
    st.stop()

# --- Procesamiento de Datos ---
with st.spinner("Procesando y uniendo datos de ventas y cobros..."):
    df_cartera, df_descuentos, df_analisis_cruzado = procesar_y_unir_datos(
        df_ventas,
        df_cobros,
        nombre_articulo_descuento="DESCUENTOS COMERCIALES"
    )

# --- Pestañas de Análisis ---
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📊 Análisis de Cartera (Cobros)", "💸 Análisis de Descuentos Otorgados", "🎯 Visión Cruzada: Descuentos vs. Pago"])

with tab1:
    st.header("Salud de la Cartera de Clientes")
    df_cartera_pagada = df_cartera.dropna(subset=['dias_pago'])
    
    if df_cartera_pagada.empty:
        st.warning("No hay suficientes datos de facturas saldadas para analizar la cartera.")
    else:
        dias_pago_promedio = df_cartera_pagada['dias_pago'].mean()
        total_facturas_pagadas = len(df_cartera_pagada)
        facturas_fuera_plazo = len(df_cartera_pagada[df_cartera_pagada['dias_pago'] > 15])

        col1, col2, col3 = st.columns(3)
        col1.metric("Días Promedio de Pago (DSO Real)", f"{dias_pago_promedio:.1f} días")
        col2.metric("Total Facturas Pagadas en Periodo", f"{total_facturas_pagadas:,}")
        col3.metric("% Facturas Pagadas > 15 días", f"{(facturas_fuera_plazo/total_facturas_pagadas)*100:.1f}%")
        
        st.subheader("Distribución de los Días de Pago Reales")
        fig_hist = px.histogram(df_cartera_pagada, x='dias_pago', nbins=50, title="Frecuencia de Pagos por Días")
        fig_hist.add_vline(x=15, line_width=2, line_dash="dash", line_color="green", annotation_text="Meta 15 días")
        st.plotly_chart(fig_hist, use_container_width=True)

with tab2:
    st.header("Análisis de los Descuentos Otorgados")
    if df_descuentos.empty:
        st.warning("No se encontraron descuentos comerciales en el periodo analizado.")
    else:
        total_descuentos_monto = abs(df_descuentos['valor_venta'].sum())
        num_descuentos = len(df_descuentos)
        
        col1, col2 = st.columns(2)
        col1.metric("Monto Total en Descuentos", f"${total_descuentos_monto:,.0f}")
        col2.metric("Número de Descuentos Aplicados", f"{num_descuentos:,}")
        
        st.subheader("Descuentos por Vendedor")
        dctos_vendedor = df_descuentos.groupby('nomvendedor')['valor_venta'].sum().abs().sort_values(ascending=False)
        st.bar_chart(dctos_vendedor)

with tab3:
    st.header("¿Quién aprovecha realmente los descuentos?")
    
    if df_analisis_cruzado.empty:
        st.warning("No hay suficientes datos para generar el análisis cruzado de pagos y descuentos.")
    else:
        st.info("Esta tabla cruza los días promedio que un cliente tarda en pagar con el total de descuentos que ha recibido. Idealmente, los clientes con más descuentos deberían tener menos días de pago.")
        
        df_analisis_cruzado['pct_descuento'] = (df_analisis_cruzado['total_descontado'] / df_analisis_cruzado['total_comprado']).fillna(0) * 100
        
        st.dataframe(df_analisis_cruzado.sort_values(by='total_descontado', ascending=False),
                     column_config={
                         "nombre_cliente": "Cliente",
                         "dias_pago_promedio": st.column_config.NumberColumn("Días Prom. Pago", format="%.1f"),
                         "total_comprado": st.column_config.NumberColumn("Total Comprado", format="$ {:,.0f}"),
                         "total_descontado": st.column_config.NumberColumn("Total Descontado", format="$ {:,.0f}"),
                         "pct_descuento": st.column_config.ProgressColumn("% Descuento s/Compra", format="%.2f%%", min_value=0, max_value=max(5, df_analisis_cruzado['pct_descuento'].max() if not df_analisis_cruzado.empty else 5))
                     }, use_container_width=True, hide_index=True)
        
        st.subheader("Visualización Estratégica: Días de Pago vs. Descuento Recibido")
        fig_scatter = px.scatter(df_analisis_cruzado[df_analisis_cruzado['total_descontado'] > 0], # Solo mostrar clientes que recibieron descuentos
                                 x='dias_pago_promedio',
                                 y='total_descontado',
                                 size='total_comprado',
                                 hover_name='nombre_cliente',
                                 color='pct_descuento',
                                 title="Comportamiento de Pago vs. Descuentos")
        fig_scatter.add_vline(x=15, line_width=2, line_dash="dash", line_color="green", annotation_text="Meta 15 Días")
        st.plotly_chart(fig_scatter, use_container_width=True)
