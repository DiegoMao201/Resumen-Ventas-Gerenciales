# Contenido completo de 🏠_Resumen_Mensual.py
# El único cambio está en la función cargar_y_limpiar_datos para usar el refresh_token
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import dropbox
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURACIÓN DE LA PÁGINA ---
URL_LOGO = "https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png"
st.set_page_config(page_title="Resumen Mensual | Tablero de Ventas", page_icon=URL_LOGO, layout="wide", initial_sidebar_state="expanded")

# --- DICCIONARIOS Y CONSTANTES ---
PRESUPUESTOS = {'154033':{'presupuesto':123873239, 'presupuestocartera':105287598}, '154044':{'presupuesto':80000000, 'presupuestocartera':300000000}, '154034':{'presupuesto':82753045, 'presupuestocartera':44854727}, '154014':{'presupuesto':268214737, 'presupuestocartera':307628243}, '154046':{'presupuesto':85469798, 'presupuestocartera':7129065}, '154012':{'presupuesto':246616193, 'presupuestocartera':295198667}, '154043':{'presupuesto':124885413, 'presupuestocartera':99488960}, '154035':{'presupuesto':80000000, 'presupuestocartera':300000000}, '154006':{'presupuesto':81250000, 'presupuestocartera':103945133}, '154049':{'presupuesto':56500000, 'presupuestocartera':70421127}, '154013':{'presupuesto':303422639, 'presupuestocartera':260017920}, '154011':{'presupuesto':447060250, 'presupuestocartera':428815923}, '154029':{'presupuesto':32500000, 'presupuestocartera':40000000}, '154040':{'presupuesto':0, 'presupuestocartera':0},'154053':{'presupuesto':0, 'presupuestocartera':0},'154048':{'presupuesto':0, 'presupuestocartera':0},'154042':{'presupuesto':0, 'presupuestocartera':0},'154031':{'presupuesto':0, 'presupuestocartera':0},'154039':{'presupuesto':0, 'presupuestocartera':0},'154051':{'presupuesto':0, 'presupuestocartera':0},'154008':{'presupuesto':0, 'presupuestocartera':0},'154052':{'presupuesto':0, 'presupuestocartera':0},'154050':{'presupuesto':0, 'presupuestocartera':0}}
GRUPOS_VENDEDORES = {"MOSTRADOR PEREIRA": ["ALEJANDRO CARBALLO MARQUEZ", "GEORGINA A. GALVIS HERRERA"], "MOSTRADOR ARMENIA": ["CRISTIAN CAMILO RENDON MONTES", "FANDRY JOHANA ABRIL PENHA", "JAVIER ORLANDO PATINO HURTADO"], "MOSTRADOR MANIZALES": ["DAVID FELIPE MARTINEZ RIOS", "JHON JAIRO CASTAÑO MONTES"], "MOSTRADOR LAURELES": ["MAURICIO RIOS MORALES"]}
MAPEO_MESES = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
NOMBRES_COLUMNAS_VENTAS = ['anio', 'mes', 'fecha_venta', 'codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_cliente', 'codigo_articulo', 'nombre_articulo','linea_producto', 'marca_producto', 'valor_venta', 'unidades_vendidas', 'costo_unitario']
NOMBRES_COLUMNAS_COBROS = ['anio', 'mes', 'fecha_cobro', 'codigo_vendedor', 'valor_cobro']
RUTA_VENTAS = "/data/ventas_detalle.csv"
RUTA_COBROS = "/data/cobros_detalle.csv"
META_MARQUILLA = 2.4

# --- FUNCIÓN DE CARGA DE DATOS ACTUALIZADA ---
@st.cache_data(ttl=1800)
def cargar_y_limpiar_datos(ruta_archivo, nombres_columnas):
    try:
        # LÓGICA DE CONEXIÓN DEFINITIVA USANDO EL REFRESH TOKEN
        with dropbox.Dropbox(
            app_key=st.secrets.dropbox.app_key,
            app_secret=st.secrets.dropbox.app_secret,
            oauth2_refresh_token=st.secrets.dropbox.refresh_token
        ) as dbx:
            metadata, res = dbx.files_download(path=ruta_archivo)
            contenido_csv = res.content.decode('latin-1')
            df = pd.read_csv(io.StringIO(contenido_csv), header=None, sep=',', on_bad_lines='skip', dtype=str)
            if df.shape[1] != len(nombres_columnas): return pd.DataFrame(columns=nombres_columnas)
            df.columns = nombres_columnas
            numeric_cols = ['anio', 'mes', 'valor_venta', 'valor_cobro', 'unidades_vendidas', 'costo_unitario']
            for col in numeric_cols:
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
            df.dropna(subset=['anio', 'mes', 'codigo_vendedor'], inplace=True)
            for col in ['anio', 'mes']: df[col] = df[col].astype(int)
            df['codigo_vendedor'] = df['codigo_vendedor'].astype(str)
            if 'fecha_venta' in df.columns:
                df['fecha_venta'] = pd.to_datetime(df['fecha_venta'], errors='coerce')
            return df
    except Exception as e:
        st.error(f"Error crítico al cargar {ruta_archivo}: {e}")
        return pd.DataFrame(columns=nombres_columnas)

# (El resto del código de esta página se mantiene exactamente igual, se omite por brevedad)
# ...

def analizar_cartera_clientes(df_ventas_vendedor):
    if df_ventas_vendedor.empty: return 0, 0, 0, pd.DataFrame()
    
    fecha_hoy = datetime.now()
    anio_actual, mes_actual = fecha_hoy.year, fecha_hoy.month
    
    fecha_actual_inicio = fecha_hoy.replace(day=1)
    fecha_mes_anterior_fin = fecha_actual_inicio - pd.DateOffset(days=1)
    fecha_riesgo = fecha_actual_inicio - pd.DateOffset(months=3)

    df_ventas_vendedor['fecha_primera_compra'] = df_ventas_vendedor.groupby('cliente_id')['fecha_venta'].transform('min')
    
    clientes_mes_actual = set(df_ventas_vendedor[(df_ventas_vendedor['fecha_venta'].dt.year == anio_actual) & (df_ventas_vendedor['fecha_venta'].dt.month == mes_actual)]['cliente_id'].unique())
    clientes_historicos = set(df_ventas_vendedor[df_ventas_vendedor['fecha_venta'] <= fecha_mes_anterior_fin]['cliente_id'].unique())

    clientes_nuevos = clientes_mes_actual - clientes_historicos
    clientes_recurrentes = clientes_mes_actual.intersection(clientes_historicos)
    
    df_ultima_compra = df_ventas_vendedor.groupby('cliente_id')['fecha_venta'].max().reset_index()
    clientes_en_riesgo_ids = set(df_ultima_compra[df_ultima_compra['fecha_venta'] < fecha_riesgo]['cliente_id'].unique())
    clientes_en_riesgo_final_ids = clientes_en_riesgo_ids - clientes_mes_actual

    df_clientes_en_riesgo = df_ventas_vendedor[df_ventas_vendedor['cliente_id'].isin(clientes_en_riesgo_final_ids)]
    top_riesgo = df_clientes_en_riesgo.groupby(['cliente_id', 'nombre_cliente'])['valor_venta'].sum().nlargest(5).reset_index()

    return len(clientes_nuevos), len(clientes_recurrentes), len(clientes_en_riesgo_final_ids), top_riesgo

# --- CONTROLADOR PRINCIPAL Y AUTENTICACIÓN ---
if 'autenticado' not in st.session_state or not st.session_state.autenticado:
    st.image(URL_LOGO, width=300)
    st.header("Acceso Restringido")
    st.warning("Por favor, inicie sesión desde la página principal `🏠 Resumen Mensual` para acceder a esta sección.")
    st.stop()

# --- LÓGICA DE LA PÁGINA ---
st.title("👨‍💻 Perfil de Vendedor y Análisis Detallado")
st.markdown("---")

# Recuperar los datos de la sesión
df_ventas_historico = st.session_state.get('df_ventas')
if df_ventas_historico is None or df_ventas_historico.empty:
    st.error("No se pudieron cargar los datos. Por favor, vuelva a la página principal e inicie sesión de nuevo.")
    st.stop()

# --- BLOQUE DE CORRECCIÓN ---
# Nos aseguramos de que la columna de fecha tenga el formato correcto
df_ventas_historico['fecha_venta'] = pd.to_datetime(df_ventas_historico['fecha_venta'], errors='coerce')
df_ventas_historico.dropna(subset=['fecha_venta'], inplace=True)
# -----------------------------

# Selector de Vendedor/Grupo
lista_vendedores = sorted(list(df_ventas_historico['nomvendedor'].dropna().unique()))
vendedores_en_grupos = [v for lista in GRUPOS_VENDEDORES.values() for v in lista]
vendedores_solos = [v for v in lista_vendedores if v not in vendedores_en_grupos]
opciones_analisis = ["Seleccione un Vendedor o Grupo"] + list(GRUPOS_VENDEDORES.keys()) + vendedores_solos

usuario_actual = st.session_state.usuario
if usuario_actual != "GERENTE":
    # Si no es gerente, la única opción es él mismo o su grupo
    opcion_default = usuario_actual
    opciones_analisis = [opcion_default]
else:
    # Si es gerente, puede elegir de la lista completa
    opcion_default = "Seleccione un Vendedor o Grupo"

seleccion = st.selectbox("Seleccione el Vendedor o Grupo a analizar:", opciones_analisis, index=0 if opcion_default not in opciones_analisis else opciones_analisis.index(opcion_default))


if seleccion == "Seleccione un Vendedor o Grupo":
    st.info("Por favor, elija un vendedor o grupo para comenzar el análisis.")
    st.stop()

# Filtrar todos los datos históricos para la selección
if seleccion in GRUPOS_VENDEDORES:
    nombres_vendedores = GRUPOS_VENDEDORES[seleccion]
    df_vendedor_historico = df_ventas_historico[df_ventas_historico['nomvendedor'].isin(nombres_vendedores)]
else:
    nombres_vendedores = [seleccion]
    df_vendedor_historico = df_ventas_historico[df_ventas_historico['nomvendedor'] == seleccion]

if df_vendedor_historico.empty:
    st.warning(f"No se encontraron datos históricos para {seleccion}.")
    st.stop()

st.header(f"Análisis para: {seleccion}")

# --- ANÁLISIS DE EVOLUCIÓN ---
st.subheader("Evolución de Ventas Mensuales")
df_evolucion = df_vendedor_historico.groupby(pd.Grouper(key='fecha_venta', freq='M'))['valor_venta'].sum().reset_index()
df_evolucion['tendencia'] = df_evolucion['valor_venta'].rolling(window=3, center=True, min_periods=1).mean()

fig_evolucion = px.line(df_evolucion, x='fecha_venta', y='valor_venta', title=f"Ventas Mensuales de {seleccion}", markers=True, labels={"fecha_venta": "Mes", "valor_venta": "Ventas Totales"})
fig_evolucion.add_scatter(x=df_evolucion['fecha_venta'], y=df_evolucion['tendencia'], mode='lines', name='Tendencia (3 meses)')
st.plotly_chart(fig_evolucion, use_container_width=True)

# --- ANÁLISIS DE CARTERA Y PRODUCTOS (EN PESTAÑAS) ---
tab1, tab2 = st.tabs(["⭐ Análisis de Cartera de Clientes", "🎨 Análisis de Productos y Marquillas"])

with tab1:
    st.subheader("Salud de la Cartera de Clientes")
    nuevos, recurrentes, en_riesgo, top_riesgo = analizar_cartera_clientes(df_vendedor_historico)

    col1, col2, col3 = st.columns(3)
    col1.metric("Clientes Nuevos (Últ. 30 días)", f"{nuevos} 👤")
    col2.metric("Clientes Recurrentes (Últ. 30 días)", f"{recurrentes} 👥")
    col3.metric("Clientes en Riesgo (sin compra >3 meses)", f"{en_riesgo} ⚠️")

    if not top_riesgo.empty:
        with st.expander("Ver Top 5 Clientes en Riesgo (Mayor valor de compra histórica)"):
            st.dataframe(top_riesgo, column_config={"nombre_cliente": "Cliente", "valor_venta": st.column_config.NumberColumn("Valor Histórico", format="$ %d")}, use_container_width=True, hide_index=True)
            st.warning("¡Acción requerida! Es crucial contactar a estos clientes de alto valor para reactivarlos.")
    else:
        st.success("¡Excelente! No hay clientes de alto valor en riesgo actualmente.")

with tab2:
    st.subheader("Superpoderes de Venta: Marcas y Marquillas")
    anio_actual = df_vendedor_historico['anio'].max()
    mes_actual = df_vendedor_historico[df_vendedor_historico['anio'] == anio_actual]['mes'].max()
    df_periodo_actual = df_vendedor_historico[(df_vendedor_historico['anio'] == anio_actual) & (df_vendedor_historico['mes'] == mes_actual)]
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Top Marcas Vendidas (últimos 12 meses)")
        doce_meses_atras = pd.to_datetime(f"{anio_actual}-{mes_actual}-01") - pd.DateOffset(months=12)
        df_ultimos_12m = df_vendedor_historico[df_vendedor_historico['fecha_venta'] > doce_meses_atras]
        
        if not df_ultimos_12m.empty:
            top_marcas = df_ultimos_12m.groupby('nombre_marca')['valor_venta'].sum().nlargest(10).reset_index().sort_values('valor_venta', ascending=True)
            fig_marcas = px.bar(top_marcas, x='valor_venta', y='nombre_marca', orientation='h', title="Marcas más vendidas", text_auto='.2s')
            fig_marcas.update_layout(yaxis_title=None, xaxis_title="Venta Total")
            st.plotly_chart(fig_marcas, use_container_width=True)
        else:
            st.info("No hay datos de los últimos 12 meses.")
    
    with col2:
        st.markdown("##### Venta de Marquillas Clave (Mes Actual)")
        if not df_periodo_actual.empty:
            df_periodo_actual['nombre_articulo'] = df_periodo_actual['nombre_articulo'].astype(str)
            ventas_marquillas = {palabra: df_periodo_actual[df_periodo_actual['nombre_articulo'].str.contains(palabra, case=False)]['valor_venta'].sum() for palabra in MARQUILLAS_CLAVE}
            df_ventas_marquillas = pd.DataFrame(list(ventas_marquillas.items()), columns=['Marquilla', 'Ventas'])
            
            fig_marquillas = px.pie(df_ventas_marquillas, names='Marquilla', values='Ventas', title="Distribución Venta Marquillas", hole=0.4)
            st.plotly_chart(fig_marquillas, use_container_width=True)
        else:
            st.info("No hay datos de marquillas para el mes actual.")
