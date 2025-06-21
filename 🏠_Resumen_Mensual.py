import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import dropbox
import io

# --- CONFIGURACIÓN DE LA PÁGINA ---

# URL ANTERIOR (la que da problemas): 
# URL_LOGO = "https://github.com/DiegoMao201/Resumen-Ventas-Gerenciales/blob/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png?raw=true"

# URL NUEVA Y CORRECTA (la que funcionará):
URL_LOGO = "https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png"

st.set_page_config(
    page_title="Resumen Mensual | Tablero de Ventas",
    page_icon=URL_LOGO, # <--- Ahora usará la URL correcta
    layout="wide",
    initial_sidebar_state="expanded"
)
# El resto del código continúa igual...

# --- DICCIONARIOS GLOBALES Y CONSTANTES ---
PRESUPUESTOS = {'154033':{'presupuesto':123873239, 'presupuestocartera':105287598}, '154044':{'presupuesto':80000000, 'presupuestocartera':300000000}, '154034':{'presupuesto':82753045, 'presupuestocartera':44854727}, '154014':{'presupuesto':268214737, 'presupuestocartera':307628243}, '154046':{'presupuesto':85469798, 'presupuestocartera':7129065}, '154012':{'presupuesto':246616193, 'presupuestocartera':295198667}, '154043':{'presupuesto':124885413, 'presupuestocartera':99488960}, '154035':{'presupuesto':80000000, 'presupuestocartera':300000000}, '154006':{'presupuesto':81250000, 'presupuestocartera':103945133}, '154049':{'presupuesto':56500000, 'presupuestocartera':70421127}, '154013':{'presupuesto':303422639, 'presupuestocartera':260017920}, '154011':{'presupuesto':447060250, 'presupuestocartera':428815923}, '154029':{'presupuesto':32500000, 'presupuestocartera':40000000}}
GRUPOS_VENDEDORES = {"MOSTRADOR PEREIRA": ["ALEJANDRO CARBALLO MARQUEZ", "GEORGINA A. GALVIS HERRERA"], "MOSTRADOR ARMENIA": ["CRISTIAN CAMILO RENDON MONTES", "FANDRY JOHANA ABRIL PENHA", "JAVIER ORLANDO PATINO HURTADO"], "MOSTRADOR MANIZALES": ["DAVID FELIPE MARTINEZ RIOS", "JHON JAIRO CASTAÑO MONTES"], "MOSTRADOR LAURELES": ["MAURICIO RIOS MORALES"]}
MAPEO_MESES = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
NOMBRES_COLUMNAS_VENTAS = ['anio', 'mes', 'fecha_venta', 'codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_cliente', 'codigo_articulo', 'nombre_articulo','linea_producto', 'marca_producto', 'valor_venta']
NOMBRES_COLUMNAS_COBROS = ['anio', 'mes', 'fecha_cobro', 'codigo_vendedor', 'valor_cobro']
RUTA_VENTAS = "/data/ventas_detalle.csv"
RUTA_COBROS = "/data/cobros_detalle.csv"
META_MARQUILLA = 2.4

# --- FUNCIONES DE PROCESAMIENTO ---
@st.cache_data(ttl=1800)
def cargar_y_limpiar_datos(ruta_archivo, nombres_columnas):
    try:
        dbx = dropbox.Dropbox(st.secrets.dropbox.access_token)
        metadata, res = dbx.files_download(path=ruta_archivo)
        contenido_csv = res.content.decode('latin-1')
        df = pd.read_csv(io.StringIO(contenido_csv), header=None, sep=',', on_bad_lines='skip', dtype=str)
        if df.shape[1] != len(nombres_columnas): return pd.DataFrame(columns=nombres_columnas)
        df.columns = nombres_columnas
        for col in ['anio', 'mes', 'valor_venta', 'valor_cobro']:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=['anio', 'mes', 'codigo_vendedor'], inplace=True)
        for col in ['anio', 'mes']: df[col] = df[col].astype(int)
        df['codigo_vendedor'] = df['codigo_vendedor'].astype(str)
        return df
    except Exception: return pd.DataFrame(columns=nombres_columnas)

def calcular_marquilla(df_periodo):
    if df_periodo.empty: return pd.DataFrame(columns=['codigo_vendedor', 'nomvendedor', 'promedio_marquilla'])
    df_periodo['nombre_articulo'] = df_periodo['nombre_articulo'].astype(str)
    df_marquilla_cliente = df_periodo.groupby(['codigo_vendedor', 'nomvendedor', 'cliente_id']).agg(
        compro_viniltex=('nombre_articulo', lambda x: x.str.contains('VINILTEX', case=False).any()),
        compro_koraza=('nombre_articulo', lambda x: x.str.contains('KORAZA', case=False).any()),
        compro_estucomastic=('nombre_articulo', lambda x: x.str.contains('ESTUCOMASTIC', case=False).any()),
        compro_vinilico=('nombre_articulo', lambda x: x.str.contains('VINILICO', case=False).any())
    ).reset_index()
    df_marquilla_cliente['puntaje_marquilla'] = df_marquilla_cliente[['compro_viniltex', 'compro_koraza', 'compro_estucomastic', 'compro_vinilico']].sum(axis=1)
    return df_marquilla_cliente.groupby(['codigo_vendedor', 'nomvendedor'])['puntaje_marquilla'].mean().reset_index().rename(columns={'promedio_marquilla': 'promedio_marquilla'})

def generar_comentario_asesor(avance_v, avance_c, marquilla_p):
    comentarios = []
    if avance_v >= 100: comentarios.append("📈 **Ventas:** ¡Felicitaciones! Has superado la meta de ventas. ¡Excelente trabajo!")
    elif avance_v >= 80: comentarios.append("📈 **Ventas:** ¡Estás muy cerca de la meta! Un último esfuerzo para lograrlo.")
    else: comentarios.append("📈 **Ventas:** Planifica tus visitas y aprovecha cada oportunidad.")
    if avance_c >= 100: comentarios.append("💰 **Cartera:** Objetivo de recaudo cumplido. Una gestión impecable.")
    else: comentarios.append("💰 **Cartera:** Recuerda hacer seguimiento a la cartera pendiente. Una buena gestión de cobro es clave.")
    if marquilla_p >= META_MARQUILLA: comentarios.append(f"🎨 **Marquilla:** Tu promedio de {marquilla_p:.2f} es excelente.")
    elif marquilla_p > 0: comentarios.append(f"🎨 **Marquilla:** Tu promedio es {marquilla_p:.2f}. Recuerda ofrecer todo el portafolio de marcas clave.")
    else: comentarios.append("🎨 **Marquilla:** Aún no registras ventas en las marcas clave. ¡Son una gran oportunidad de crecimiento!")
    return comentarios

def render_dashboard():
    st.sidebar.markdown("---")
    st.sidebar.header("Filtros de Periodo")
    
    df_ventas = st.session_state.df_ventas
    df_cobros = st.session_state.df_cobros
    
    lista_anios = sorted(df_ventas['anio'].unique(), reverse=True)
    anio_sel = st.sidebar.selectbox("Elija el Año", lista_anios)
    lista_meses_num = sorted(df_ventas[df_ventas['anio'] == anio_sel]['mes'].unique())
    mes_sel_num = st.sidebar.selectbox("Elija el Mes", options=lista_meses_num, format_func=lambda x: MAPEO_MESES.get(x))
    
    df_ventas_periodo = df_ventas[(df_ventas['anio'] == anio_sel) & (df_ventas['mes'] == mes_sel_num)]
    if df_ventas_periodo.empty: st.warning("No hay datos de ventas para el periodo seleccionado."); st.stop()
    df_cobros_periodo = df_cobros[(df_cobros['anio'] == anio_sel) & (df_cobros['mes'] == mes_sel_num)]

    resumen_ind = df_ventas_periodo.groupby(['codigo_vendedor', 'nomvendedor']).agg(ventas_totales=('valor_venta', 'sum'), impactos=('cliente_id', 'nunique')).reset_index()
    resumen_cobros = df_cobros_periodo.groupby('codigo_vendedor').agg(cobros_totales=('valor_cobro', 'sum')).reset_index()
    resumen_marquilla = calcular_marquilla(df_ventas_periodo)
    
    df_resumen_completo = pd.merge(resumen_ind, resumen_cobros, on='codigo_vendedor', how='left')
    df_resumen_completo = pd.merge(df_resumen_completo, resumen_marquilla, on=['codigo_vendedor', 'nomvendedor'], how='left')
    df_resumen_completo['presupuesto'] = df_resumen_completo['codigo_vendedor'].map(lambda x: PRESUPUESTOS.get(x, {}).get('presupuesto', 0))
    df_resumen_completo['presupuestocartera'] = df_resumen_completo['codigo_vendedor'].map(lambda x: PRESUPUESTOS.get(x, {}).get('presupuestocartera', 0))
    df_resumen_completo.fillna(0, inplace=True)
    
# --- AGRUPACIÓN (VERSIÓN CORREGIDA Y ROBUSTA) ---
registros_agrupados = []
for grupo, lista_vendedores in GRUPOS_VENDEDORES.items():
    df_grupo = df_resumen_completo[df_resumen_completo['nomvendedor'].isin(lista_vendedores)]
    
    if not df_grupo.empty:
        # 1. Suma segura de las columnas numéricas que siempre existen
        suma_grupo = df_grupo[['ventas_totales', 'cobros_totales', 'impactos', 'presupuesto', 'presupuestocartera']].sum().to_dict()
        
        # 2. Cálculo seguro de la marquilla, verificando que la columna exista
        if 'promedio_marquilla' in df_grupo.columns and df_grupo['impactos'].sum() > 0:
            promedio_marquilla_grupo = np.average(df_grupo['promedio_marquilla'], weights=df_grupo['impactos'])
        else:
            promedio_marquilla_grupo = 0
        
        # 3. Construir el registro del grupo
        registro_grupo = {
            'nomvendedor': grupo,
            'codigo_vendedor': grupo,
            **suma_grupo,
            'promedio_marquilla': promedio_marquilla_grupo
        }
        registros_agrupados.append(registro_grupo)

df_agrupado = pd.DataFrame(registros_agrupados)

# Unir con los vendedores individuales que no están en grupos
vendedores_en_grupos_lista = [v for lista in GRUPOS_VENDEDORES.values() for v in lista]
df_individuales = df_resumen_completo[~df_resumen_completo['nomvendedor'].isin(vendedores_en_grupos_lista)]

# Concatenar para obtener la tabla final
df_final = pd.concat([df_agrupado, df_individuales], ignore_index=True)
# ----------------------------------------------------

    usuario_actual = st.session_state.usuario
    if usuario_actual == "GERENTE":
        lista_filtro = sorted(df_final['nomvendedor'].unique())
        vendedores_sel = st.sidebar.multiselect("Filtrar Vendedores/Grupos", options=lista_filtro, default=lista_filtro)
        dff = df_final[df_final['nomvendedor'].isin(vendedores_sel)]
    else: dff = df_final[df_final['nomvendedor'] == usuario_actual]
    if dff.empty: st.warning("No hay datos para mostrar para tu selección."); st.stop()
    
    def asignar_estatus(row):
        avance_v = (row['ventas_totales'] / row['presupuesto'] * 100) if row['presupuesto'] > 0 else 0
        if avance_v >= 95: return "🟢 En Objetivo"
        if avance_v >= 70: return "🟡 Cerca del Objetivo"
        return "🔴 Necesita Atención"
    dff['Estatus'] = dff.apply(asignar_estatus, axis=1)
    
    st.title(f"🏠 Resumen de Rendimiento")
    st.header(f"{MAPEO_MESES.get(mes_sel_num)} {anio_sel}")
    st.markdown("---")
    with st.container(border=True):
        ventas_total = dff['ventas_totales'].sum(); meta_ventas = dff['presupuesto'].sum()
        cobros_total = dff['cobros_totales'].sum(); meta_cobros = dff['presupuestocartera'].sum()
        marquilla_prom = np.average(dff['promedio_marquilla'], weights=dff['impactos']) if dff['impactos'].sum() > 0 else 0
        avance_ventas = (ventas_total / meta_ventas * 100) if meta_ventas > 0 else 0
        avance_cobros = (cobros_total / meta_cobros * 100) if meta_cobros > 0 else 0
        st.subheader(f"👨‍💼 Asesor Virtual para: {st.session_state.usuario}")
        comentarios = generar_comentario_asesor(avance_ventas, avance_cobros, marquilla_prom)
        for comentario in comentarios: st.markdown(f"- {comentario}")
    st.subheader("Métricas Clave del Periodo")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ventas Totales", f"${ventas_total:,.0f}", f"{ventas_total - meta_ventas:,.0f} vs Meta")
        st.progress(min(avance_ventas / 100, 1.0), text=f"Avance Ventas: {avance_ventas:.1f}%")
    with col2:
        st.metric("Recaudo de Cartera", f"${cobros_total:,.0f}", f"{cobros_total - meta_cobros:,.0f} vs Meta")
        st.progress(min(avance_cobros / 100, 1.0), text=f"Avance Cartera: {avance_cobros:.1f}%")
    with col3:
        st.metric("Promedio Marquilla", f"{marquilla_prom:.2f}", f"{marquilla_prom - META_MARQUILLA:,.2f} vs Meta")
        st.progress(min((marquilla_prom / META_MARQUILLA), 1.0) if marquilla_prom > 0 else 0, text=f"Meta: {META_MARQUILLA}")
    
    st.subheader("Desglose por Vendedor / Grupo")
    st.dataframe(
        dff[['Estatus', 'nomvendedor', 'ventas_totales', 'presupuesto', 'cobros_totales', 'presupuestocartera', 'impactos', 'promedio_marquilla']],
        column_config={ "Estatus": st.column_config.TextColumn("🚦", width="small"), "nomvendedor": st.column_config.TextColumn("Vendedor/Grupo", width="medium"), "ventas_totales": st.column_config.NumberColumn("Ventas", format="$ %d"), "presupuesto": st.column_config.NumberColumn("Meta Ventas", format="$ %d"), "cobros_totales": st.column_config.NumberColumn("Recaudo", format="$ %d"), "presupuestocartera": st.column_config.NumberColumn("Meta Recaudo", format="$ %d"), "impactos": st.column_config.NumberColumn("Clientes Únicos", format="%d"), "promedio_marquilla": st.column_config.ProgressColumn("Promedio Marquilla", format="%.2f", min_value=0, max_value=4) },
        use_container_width=True, hide_index=True
    )

# --- CONTROLADOR PRINCIPAL ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False

# Renderizar el formulario de login siempre en la barra lateral
st.sidebar.image(URL_LOGO, use_container_width=True)
st.sidebar.header("Control de Acceso")
@st.cache_data
def obtener_lista_usuarios():
    #...
    df = cargar_y_limpiar_datos(RUTA_VENTAS, NOMBRES_COLUMNAS_VENTAS)
    if not df.empty:
        vendedores_individuales = sorted(list(df['nomvendedor'].dropna().unique()))
        vendedores_en_grupos = [v for lista in GRUPOS_VENDEDORES.values() for v in lista]
        vendedores_solos = [v for v in vendedores_individuales if v not in vendedores_en_grupos]
        return ["GERENTE"] + list(GRUPOS_VENDEDORES.keys()) + vendedores_solos
    return ["GERENTE"] + list(GRUPOS_VENDEDORES.keys())
todos_usuarios = obtener_lista_usuarios()
usuarios_fijos = {"GERENTE": "1234", "MOSTRADOR PEREIRA": "2345", "MOSTRADOR ARMENIA": "3456", "MOSTRADOR MANIZALES": "4567", "MOSTRADOR LAURELES": "5678"}
usuarios = usuarios_fijos.copy()
codigo = 1001
for u in todos_usuarios:
    if u not in usuarios: usuarios[u] = str(codigo); codigo += 1
usuario_seleccionado = st.sidebar.selectbox("Seleccione su usuario", options=todos_usuarios)
clave = st.sidebar.text_input("Contraseña", type="password")
if st.sidebar.button("Ingresar"):
    if usuario_seleccionado in usuarios and clave == usuarios[usuario_seleccionado]:
        st.session_state.autenticado = True
        st.session_state.usuario = usuario_seleccionado
        st.rerun()
    else:
        st.sidebar.error("Usuario o contraseña incorrectos")

if st.session_state.autenticado:
    # Cachear los dataframes después de un login exitoso para mejorar rendimiento entre páginas
    if 'df_ventas' not in st.session_state:
        st.session_state.df_ventas = cargar_y_limpiar_datos(RUTA_VENTAS, NOMBRES_COLUMNAS_VENTAS)
        st.session_state.df_cobros = cargar_y_limpiar_datos(RUTA_COBROS, NOMBRES_COLUMNAS_COBROS)
    render_dashboard()
else:
    st.title("Plataforma de Inteligencia de Negocios")
    st.image(URL_LOGO, width=300)
    st.header("Bienvenido")
    st.info("Por favor, utilice el panel de la izquierda para ingresar sus credenciales de acceso.")
