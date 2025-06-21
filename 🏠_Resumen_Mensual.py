import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import dropbox
import io

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Resumen Mensual | Tablero de Ventas",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DICCIONARIOS GLOBALES Y CONSTANTES ---
MAPEO_MARCAS = {
    50: "P8-ASC-MEGA", 54: "MPY-International", 55: "DPP-AN COLORANTS LATAM",
    56: "DPP-Pintuco Profesional", 57: "ASC-Mega", 58: "DPP-Pintuco",
    59: "DPP-Madetec", 60: "POW-Interpon", 61: "various", 62: "DPP-ICO",
    63: "DPP-Terinsa", 64: "MPY-Pintuco", 65: "non-AN Third Party",
    66: "ICO-AN Packaging", 67: "ASC-Automotive OEM", 68: "POW-Resicoat",
    73: "DPP-Coral", 91: "DPP-Sikkens"
}
GRUPOS_VENDEDORES = {
    "MOSTRADOR PEREIRA": ["ALEJANDRO CARBALLO MARQUEZ", "GEORGINA A. GALVIS HERRERA"],
    "MOSTRADOR ARMENIA": ["CRISTIAN CAMILO RENDON MONTES", "FANDRY JOHANA ABRIL PENHA", "JAVIER ORLANDO PATINO HURTADO"],
    "MOSTRADOR MANIZALES": ["DAVID FELIPE MARTINEZ RIOS", "JHON JAIRO CASTAÑO MONTES"],
    "MOSTRADOR LAURELES": ["MAURICIO RIOS MORALES"]
}
MAPEO_MESES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
PRESUPUESTOS = {
    '154033': {'presupuesto': 123873239.00, 'presupuestocartera': 105287598.00}, '154044': {'presupuesto': 80000000.00, 'presupuestocartera': 300000000.00},
    '154034': {'presupuesto': 82753045.00, 'presupuestocartera': 44854727.00}, '154014': {'presupuesto': 268214737.00, 'presupuestocartera': 307628243.00},
    '154046': {'presupuesto': 85469798.00, 'presupuestocartera': 7129065.00}, '154012': {'presupuesto': 246616193.00, 'presupuestocartera': 295198667.00},
    '154043': {'presupuesto': 124885413.00, 'presupuestocartera': 99488960.00}, '154035': {'presupuesto': 80000000.00, 'presupuestocartera': 300000000.00},
    '154006': {'presupuesto': 81250000.00, 'presupuestocartera': 103945133.00}, '154049': {'presupuesto': 56500000.00, 'presupuestocartera': 70421127.00},
    '154013': {'presupuesto': 303422639.00, 'presupuestocartera': 260017920.00}, '154011': {'presupuesto': 447060250.00, 'presupuestocartera': 428815923.00},
    '154029': {'presupuesto': 32500000.00, 'presupuestocartera': 40000000.00}
}
NOMBRES_COLUMNAS_VENTAS = ['anio', 'mes', 'fecha_venta', 'codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_cliente', 'codigo_articulo', 'nombre_articulo','linea_producto', 'marca_producto', 'valor_venta']
NOMBRES_COLUMNAS_COBROS = ['anio', 'mes', 'fecha_cobro', 'codigo_vendedor', 'valor_cobro']
RUTA_VENTAS = "/data/ventas_detalle.csv"
RUTA_COBROS = "/data/cobros_detalle.csv"

# --- FUNCIONES DE PROCESAMIENTO ---
@st.cache_data(ttl=1800)
def cargar_y_limpiar_datos(ruta_archivo, nombres_columnas):
    try:
        dbx = dropbox.Dropbox(st.secrets.dropbox.access_token)
        metadata, res = dbx.files_download(path=ruta_archivo)
        contenido_csv = res.content.decode('latin-1')
        df = pd.read_csv(io.StringIO(contenido_csv), header=None, sep=',', on_bad_lines='skip')
        if df.shape[1] != len(nombres_columnas): return pd.DataFrame(columns=nombres_columnas)
        df.columns = nombres_columnas
        df['anio'] = pd.to_numeric(df['anio'], errors='coerce')
        df['mes'] = pd.to_numeric(df['mes'], errors='coerce')
        df.dropna(subset=['anio', 'mes', 'codigo_vendedor'], inplace=True)
        for col in ['anio', 'mes']: df[col] = df[col].astype(int)
        return df
    except Exception as e:
        st.error(f"Error al cargar {ruta_archivo}: {e}")
        return pd.DataFrame(columns=nombres_columnas)

def calcular_marquilla(df_periodo):
    if df_periodo.empty or 'nombre_articulo' not in df_periodo.columns: return pd.DataFrame(columns=['codigo_vendedor', 'promedio_marquilla'])
    df_periodo['nombre_articulo'] = df_periodo['nombre_articulo'].astype(str)
    df_marquilla_cliente = df_periodo.groupby(['codigo_vendedor', 'nomvendedor', 'cliente_id']).agg(
        compro_viniltex=('nombre_articulo', lambda x: x.str.contains('VINILTEX', case=False).any()),
        compro_koraza=('nombre_articulo', lambda x: x.str.contains('KORAZA', case=False).any()),
        compro_estucomastic=('nombre_articulo', lambda x: x.str.contains('ESTUCOMASTIC', case=False).any()),
        compro_vinilico=('nombre_articulo', lambda x: x.str.contains('VINILICO', case=False).any())
    ).reset_index()
    df_marquilla_cliente['puntaje_marquilla'] = df_marquilla_cliente[['compro_viniltex', 'compro_koraza', 'compro_estucomastic', 'compro_vinilico']].sum(axis=1)
    return df_marquilla_cliente.groupby(['codigo_vendedor', 'nomvendedor'])['puntaje_marquilla'].mean().reset_index().rename(columns={'puntaje_marquilla': 'promedio_marquilla'})

# --- AUTENTICACIÓN ---
st.sidebar.image("https://ferreinoxtools.com/wp-content/uploads/2023/06/logo-ferreinoxtools-2.svg", use_container_width=True)
st.sidebar.header("Control de Acceso")

@st.cache_data
def obtener_lista_usuarios():
    df = cargar_y_limpiar_datos(RUTA_VENTAS, NOMBRES_COLUMNAS_VENTAS)
    if not df.empty:
        return sorted(list(df['nomvendedor'].dropna().unique()))
    return []

vendedores_individuales = obtener_lista_usuarios()
usuarios_fijos = {"GERENTE": "1234", **{grupo: "2345" for grupo in GRUPOS_VENDEDORES}} # Simplificado
vendedores_en_grupos = [v for lista in GRUPOS_VENDEDORES.values() for v in lista]
vendedores_solos = [v for v in vendedores_individuales if v not in vendedores_en_grupos]
todos_usuarios = ["GERENTE"] + list(GRUPOS_VENDEDORES.keys()) + vendedores_solos
usuarios = usuarios_fijos.copy()
codigo = 1001
for vendedor in vendedores_solos:
    if vendedor not in usuarios:
        usuarios[vendedor] = str(codigo)
        codigo += 1

usuario_seleccionado = st.sidebar.selectbox("Seleccione su usuario", options=todos_usuarios, help="Elija su nombre de usuario o grupo.")
clave = st.sidebar.text_input("Contraseña", type="password")

if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if st.sidebar.button("Ingresar"):
    if usuario_seleccionado in usuarios and clave == usuarios[usuario_seleccionado]:
        st.session_state.autenticado = True
        st.session_state.usuario = usuario_seleccionado
    else:
        st.sidebar.error("Usuario o contraseña incorrectos"); st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.info("Por favor, ingrese sus credenciales para ver el tablero."); st.stop()

st.sidebar.success(f"Bienvenido, {st.session_state.usuario}!")
st.sidebar.markdown("---")

# --- LÓGICA PRINCIPAL DE LA APP ---
df_ventas = cargar_y_limpiar_datos(RUTA_VENTAS, NOMBRES_COLUMNAS_VENTAS)
df_cobros = cargar_y_limpiar_datos(RUTA_COBROS, NOMBRES_COLUMNAS_COBROS)

st.sidebar.header("Filtros de Periodo")
lista_anios = sorted(df_ventas['anio'].unique(), reverse=True)
anio_sel = st.sidebar.selectbox("Seleccione el Año", lista_anios)
lista_meses_num = sorted(df_ventas[df_ventas['anio'] == anio_sel]['mes'].unique())
mes_sel_num = st.sidebar.selectbox("Seleccione el Mes", options=lista_meses_num, format_func=lambda x: MAPEO_MESES.get(x))

# --- FILTRADO Y PROCESAMIENTO DEL PERIODO ---
df_ventas_periodo = df_ventas[(df_ventas['anio'] == anio_sel) & (df_ventas['mes'] == mes_sel_num)]
if df_ventas_periodo.empty: st.warning("No hay datos de ventas para el periodo seleccionado."); st.stop()

df_cobros_periodo = df_cobros[(df_cobros['anio'] == anio_sel) & (df_cobros['mes'] == mes_sel_num)]

# --- CÁLCULOS PRINCIPALES ---
resumen = df_ventas_periodo.groupby(['codigo_vendedor', 'nomvendedor']).agg(ventas_totales=('valor_venta', 'sum'), impactos=('cliente_id', 'nunique')).reset_index()
resumen_cobros = df_cobros_periodo.groupby('codigo_vendedor').agg(cobros_totales=('valor_cobro', 'sum')).reset_index()
resumen_marquilla = calcular_marquilla(df_ventas_periodo)

# Unir todo
df_resumen = pd.merge(resumen, resumen_cobros, on='codigo_vendedor', how='left')
df_resumen = pd.merge(df_resumen, resumen_marquilla[['codigo_vendedor', 'promedio_marquilla']], on='codigo_vendedor', how='left')
df_resumen.fillna(0, inplace=True)

# --- AGRUPACIÓN ---
registros_agrupados = []
for grupo, lista_vendedores in GRUPOS_VENDEDORES.items():
    df_grupo = df_resumen[df_resumen['nomvendedor'].isin(lista_vendedores)]
    if not df_grupo.empty:
        suma_grupo = df_grupo[['ventas_totales', 'cobros_totales', 'impactos']].sum().to_dict()
        # El promedio de marquilla del grupo es el promedio de los promedios de sus miembros
        promedio_marquilla_grupo = df_grupo['promedio_marquilla'].mean()
        registro_grupo = {'nomvendedor': grupo, **suma_grupo, 'promedio_marquilla': promedio_marquilla_grupo, 'codigo_vendedor': 'GRUPO'}
        registros_agrupados.append(registro_grupo)
df_agrupado = pd.DataFrame(registros_agrupados)

df_individuales = df_resumen[~df_resumen['nomvendedor'].isin(vendedores_en_grupos)]
df_final = pd.concat([df_agrupado, df_individuales], ignore_index=True)

# Asignar presupuestos
df_final['presupuesto'] = df_final['codigo_vendedor'].astype(str).map(lambda x: PRESUPUESTOS.get(x, {}).get('presupuesto', 0))
df_final['presupuestocartera'] = df_final['codigo_vendedor'].astype(str).map(lambda x: PRESUPUESTOS.get(x, {}).get('presupuestocartera', 0))

# --- FILTRADO FINAL POR USUARIO LOGUEADO ---
usuario_actual = st.session_state.usuario
dff = pd.DataFrame() 
if usuario_actual == "GERENTE":
    lista_filtro = sorted(df_final['nomvendedor'].unique())
    vendedores_sel = st.sidebar.multiselect("Filtrar Vendedores/Grupos", options=lista_filtro, default=lista_filtro)
    dff = df_final[df_final['nomvendedor'].isin(vendedores_sel)]
else:
    dff = df_final[df_final['nomvendedor'] == usuario_actual]

if dff.empty: st.warning("No hay datos para mostrar para tu selección."); st.stop()

# --- VISUALIZACIÓN DE LA PÁGINA ---
st.header(f"Resumen de Rendimiento | {MAPEO_MESES.get(mes_sel_num)} {anio_sel}")
st.markdown(f"**Usuario:** `{usuario_actual}`")

# Métricas Globales
ventas_total = dff['ventas_totales'].sum()
meta_ventas = dff['presupuesto'].sum()
avance_ventas = (ventas_total / meta_ventas) * 100 if meta_ventas > 0 else 0
cobros_total = dff['cobros_totales'].sum()
meta_cobros = dff['presupuestocartera'].sum()
avance_cobros = (cobros_total / meta_cobros) * 100 if meta_cobros > 0 else 0
marquilla_prom = dff['promedio_marquilla'].mean()

col1, col2, col3 = st.columns(3)
col1.metric("Ventas Totales", f"${ventas_total:,.0f}", f"{avance_ventas:.1f}% de Meta (${meta_ventas:,.0f})")
col2.metric("Cobros Totales", f"${cobros_total:,.0f}", f"{avance_cobros:.1f}% de Meta (${meta_cobros:,.0f})")
col3.metric("Promedio Marquilla", f"{marquilla_prom:.2f}", "Meta: 2.4")

# Tabla de Resumen
st.subheader("Desglose por Vendedor / Grupo")
st.dataframe(dff[['nomvendedor', 'ventas_totales', 'presupuesto', 'cobros_totales', 'presupuestocartera', 'impactos', 'promedio_marquilla']].round(2))

st.info("Página de Resumen Mensual completada. Próximo paso: Crear las páginas de 'Análisis Histórico' y 'Perfil de Vendedor'.")
