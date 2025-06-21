import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import dropbox
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Perfil de Vendedor | Tablero de Ventas",
    page_icon="👨‍💻",
    layout="wide"
)

# --- DICCIONARIOS Y CONSTANTES (Copiados de la página principal) ---
URL_LOGO = "https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png"
GRUPOS_VENDEDORES = {"MOSTRADOR PEREIRA": ["ALEJANDRO CARBALLO MARQUEZ", "GEORGINA A. GALVIS HERRERA"], "MOSTRADOR ARMENIA": ["CRISTIAN CAMILO RENDON MONTES", "FANDRY JOHANA ABRIL PENHA", "JAVIER ORLANDO PATINO HURTADO"], "MOSTRADOR MANIZALES": ["DAVID FELIPE MARTINEZ RIOS", "JHON JAIRO CASTAÑO MONTES"], "MOSTRADOR LAURELES": ["MAURICIO RIOS MORALES"]}
MAPEO_MESES = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
NOMBRES_COLUMNAS_VENTAS = ['anio', 'mes', 'fecha_venta', 'codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_cliente', 'codigo_articulo', 'nombre_articulo','linea_producto', 'marca_producto', 'valor_venta']
RUTA_VENTAS = "/data/ventas_detalle.csv"
MARQUILLAS_CLAVE = ['VINILTEX', 'KORAZA', 'ESTUCOMASTIC', 'VINILICO']

# --- FUNCIONES (Copiadas y adaptadas de la página principal) ---
@st.cache_data(ttl=1800)
def cargar_y_limpiar_datos(ruta_archivo, nombres_columnas):
    try:
        dbx = dropbox.Dropbox(st.secrets.dropbox.access_token)
        metadata, res = dbx.files_download(path=ruta_archivo)
        contenido_csv = res.content.decode('latin-1')
        df = pd.read_csv(io.StringIO(contenido_csv), header=None, sep=',', on_bad_lines='skip', dtype=str)
        if df.shape[1] != len(nombres_columnas): return pd.DataFrame(columns=nombres_columnas)
        df.columns = nombres_columnas
        numeric_cols = ['anio', 'mes', 'valor_venta', 'valor_cobro']
        for col in numeric_cols:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=['anio', 'mes', 'codigo_vendedor', 'fecha_venta'], inplace=True, how='any')
        for col in ['anio', 'mes']: df[col] = df[col].astype(int)
        df['codigo_vendedor'] = df['codigo_vendedor'].astype(str)
        df['fecha_venta'] = pd.to_datetime(df['fecha_venta'], errors='coerce')
        return df
    except Exception: return pd.DataFrame(columns=nombres_columnas)

# --- NUEVA FUNCIÓN: ANÁLISIS DE CLIENTES ---
def analizar_cartera_clientes(df_ventas_vendedor, anio_actual, mes_actual):
    if df_ventas_vendedor.empty:
        return 0, 0, 0, pd.DataFrame()

    fecha_actual_fin = pd.to_datetime(f"{anio_actual}-{mes_actual}-01") + pd.offsets.MonthEnd(0)
    fecha_anterior_fin = fecha_actual_fin - pd.offsets.MonthBegin(1)
    fecha_riesgo = fecha_actual_fin - pd.DateOffset(months=3)

    df_ventas_vendedor['fecha_primera_compra'] = df_ventas_vendedor.groupby('cliente_id')['fecha_venta'].transform('min')
    
    clientes_mes_actual = set(df_ventas_vendedor[(df_ventas_vendedor['anio'] == anio_actual) & (df_ventas_vendedor['mes'] == mes_actual)]['cliente_id'].unique())
    clientes_mes_anterior = set(df_ventas_vendedor[df_ventas_vendedor['fecha_venta'] <= fecha_anterior_fin]['cliente_id'].unique())

    # Cálculos
    clientes_nuevos = {c for c in clientes_mes_actual if df_ventas_vendedor[df_ventas_vendedor['cliente_id'] == c]['fecha_primera_compra'].min().month == mes_actual and df_ventas_vendedor[df_ventas_vendedor['cliente_id'] == c]['fecha_primera_compra'].min().year == anio_actual}
    clientes_recurrentes = clientes_mes_actual.intersection(clientes_mes_anterior)
    
    df_ultima_compra = df_ventas_vendedor.groupby('cliente_id')['fecha_venta'].max().reset_index()
    clientes_en_riesgo = set(df_ultima_compra[df_ultima_compra['fecha_venta'] < fecha_riesgo]['cliente_id'].unique())
    clientes_top_riesgo = df_ventas_vendedor[df_ventas_vendedor['cliente_id'].isin(clientes_en_riesgo)].groupby(['cliente_id', 'nombre_cliente'])['valor_venta'].sum().nlargest(5).reset_index()

    return len(clientes_nuevos), len(clientes_recurrentes), len(clientes_en_riesgo), clientes_top_riesgo

# --- CONTROLADOR PRINCIPAL Y AUTENTICACIÓN ---
# Este bloque es esencial en CADA PÁGINA para mantener la seguridad
if 'autenticado' not in st.session_state or not st.session_state.autenticado:
    st.image(URL_LOGO, width=300)
    st.header("Acceso Restringido")
    st.warning("Por favor, inicie sesión desde la página principal para acceder a esta sección.")
    st.stop()

# --- LÓGICA DE LA PÁGINA ---
st.title("👨‍💻 Perfil de Vendedor y Análisis Detallado")
st.markdown("---")

# Cargar los datos una vez
df_ventas_historico = st.session_state.get('df_ventas', pd.DataFrame())
if df_ventas_historico.empty:
    df_ventas_historico = cargar_y_limpiar_datos(RUTA_VENTAS, NOMBRES_COLUMNAS_VENTAS)
    st.session_state.df_ventas = df_ventas_historico

# Selector de Vendedor/Grupo
lista_vendedores = sorted(list(df_ventas_historico['nomvendedor'].dropna().unique()))
opciones_analisis = ["Seleccione un Vendedor o Grupo"] + list(GRUPOS_VENDEDORES.keys()) + lista_vendedores
seleccion = st.selectbox("Seleccione el Vendedor o Grupo a analizar:", opciones_opciones_analisis)

if seleccion == "Seleccione un Vendedor o Grupo":
    st.info("Por favor, elija un vendedor o grupo para comenzar el análisis.")
    st.stop()

# Filtrar todos los datos históricos para la selección
if seleccion in GRUPOS_VENDEDORES:
    nombres_vendedores = GRUPOS_VENDEDORES[seleccion]
    df_vendedor_historico = df_ventas_historico[df_ventas_historico['nomvendedor'].isin(nombres_vendedores)]
else:
    nombres_vendedores = [seleccion]
    df_vendedor_historico = df_ventas_historico[df_vendedor_historico['nomvendedor'] == seleccion]

if df_vendedor_historico.empty:
    st.warning(f"No se encontraron datos históricos para {seleccion}.")
    st.stop()

st.header(f"Análisis para: {seleccion}")

# --- ANÁLISIS DE EVOLUCIÓN ---
st.subheader("Evolución de Ventas Mensuales")
df_evolucion = df_vendedor_historico.groupby(pd.Grouper(key='fecha_venta', freq='MS'))['valor_venta'].sum().reset_index()
df_evolucion['tendencia'] = df_evolucion['valor_venta'].rolling(window=3, center=True, min_periods=1).mean()

fig_evolucion = px.line(df_evolucion, x='fecha_venta', y='valor_venta', title=f"Ventas Mensuales de {seleccion}", markers=True, labels={"fecha_venta": "Mes", "valor_venta": "Ventas Totales"})
fig_evolucion.add_scatter(x=df_evolucion['fecha_venta'], y=df_evolucion['tendencia'], mode='lines', name='Tendencia (3 meses)')
st.plotly_chart(fig_evolucion, use_container_width=True)

# --- ANÁLISIS DE CARTERA Y PRODUCTOS (EN PESTAÑAS) ---
tab1, tab2 = st.tabs(["⭐ Análisis de Cartera de Clientes", "🎨 Análisis de Productos y Marquillas"])

with tab1:
    st.subheader("Salud de la Cartera de Clientes")
    anio_actual = df_vendedor_historico['anio'].max()
    mes_actual = df_vendedor_historico[df_vendedor_historico['anio'] == anio_actual]['mes'].max()
    
    nuevos, recurrentes, en_riesgo, top_riesgo = analizar_cartera_clientes(df_vendedor_historico, anio_actual, mes_actual)

    col1, col2, col3 = st.columns(3)
    col1.metric("Clientes Nuevos este Mes", f"{nuevos} 👤")
    col2.metric("Clientes Recurrentes", f"{recurrentes} 👥")
    col3.metric("Clientes en Riesgo (sin compra >3 meses)", f"{en_riesgo} ⚠️")

    if not top_riesgo.empty:
        with st.expander("Ver Top 5 Clientes en Riesgo (Mayor valor de compra histórica)"):
            st.dataframe(top_riesgo, column_config={"nombre_cliente": "Cliente", "valor_venta": st.column_config.NumberColumn("Valor Histórico", format="$ %d")}, use_container_width=True, hide_index=True)
            st.warning("¡Acción requerida! Es crucial contactar a estos clientes de alto valor para reactivarlos.")

with tab2:
    st.subheader("Superpoderes de Venta: Marcas y Marquillas")
    df_periodo_actual = df_vendedor_historico[(df_vendedor_historico['anio'] == anio_actual) & (df_vendedor_historico['mes'] == mes_actual)]
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Top Marcas Vendidas (últimos 12 meses)")
        doce_meses_atras = pd.to_datetime(f"{anio_actual}-{mes_actual}-01") - pd.DateOffset(months=12)
        df_ultimos_12m = df_vendedor_historico[df_vendedor_historico['fecha_venta'] > doce_meses_atras]
        top_marcas = df_ultimos_12m.groupby('nombre_marca')['valor_venta'].sum().nlargest(10).reset_index()
        fig_marcas = px.bar(top_marcas, x='valor_venta', y='nombre_marca', orientation='h', title="Marcas más vendidas")
        fig_marcas.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_marcas, use_container_width=True)
    
    with col2:
        st.markdown("##### Venta de Marquillas Clave (Mes Actual)")
        if not df_periodo_actual.empty:
            ventas_marquillas = {palabra: df_periodo_actual[df_periodo_actual['nombre_articulo'].str.contains(palabra, case=False)]['valor_venta'].sum() for palabra in MARQUILLAS_CLAVE}
            df_ventas_marquillas = pd.DataFrame(list(ventas_marquillas.items()), columns=['Marquilla', 'Ventas'])
            fig_marquillas = px.pie(df_ventas_marquillas, names='Marquilla', values='Ventas', title="Distribución Venta Marquillas", hole=0.4)
            st.plotly_chart(fig_marquillas, use_container_width=True)
        else:
            st.info("No hay datos de marquillas para el mes actual.")
