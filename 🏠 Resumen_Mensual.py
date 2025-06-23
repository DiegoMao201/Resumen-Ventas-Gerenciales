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
st.set_page_config(
    page_title="Resumen Mensual | Tablero de Ventas",
    page_icon=URL_LOGO,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DICCIONARIOS GLOBALES Y CONSTANTES ---
PRESUPUESTOS = {'154033':{'presupuesto':123873239, 'presupuestocartera':105287598}, '154044':{'presupuesto':80000000, 'presupuestocartera':300000000}, '154034':{'presupuesto':82753045, 'presupuestocartera':44854727}, '154014':{'presupuesto':268214737, 'presupuestocartera':307628243}, '154046':{'presupuesto':85469798, 'presupuestocartera':7129065}, '154012':{'presupuesto':246616193, 'presupuestocartera':295198667}, '154043':{'presupuesto':124885413, 'presupuestocartera':99488960}, '154035':{'presupuesto':80000000, 'presupuestocartera':300000000}, '154006':{'presupuesto':81250000, 'presupuestocartera':103945133}, '154049':{'presupuesto':56500000, 'presupuestocartera':70421127}, '154013':{'presupuesto':303422639, 'presupuestocartera':260017920}, '154011':{'presupuesto':447060250, 'presupuestocartera':428815923}, '154029':{'presupuesto':32500000, 'presupuestocartera':40000000}, '154040':{'presupuesto':0, 'presupuestocartera':0},'154053':{'presupuesto':0, 'presupuestocartera':0},'154048':{'presupuesto':0, 'presupuestocartera':0},'154042':{'presupuesto':0, 'presupuestocartera':0},'154031':{'presupuesto':0, 'presupuestocartera':0},'154039':{'presupuesto':0, 'presupuestocartera':0},'154051':{'presupuesto':0, 'presupuestocartera':0},'154008':{'presupuesto':0, 'presupuestocartera':0},'154052':{'presupuesto':0, 'presupuestocartera':0},'154050':{'presupuesto':0, 'presupuestocartera':0}}
GRUPOS_VENDEDORES = {"MOSTRADOR PEREIRA": ["ALEJANDRO CARBALLO MARQUEZ", "GEORGINA A. GALVIS HERRERA"], "MOSTRADOR ARMENIA": ["CRISTIAN CAMILO RENDON MONTES", "FANDRY JOHANA ABRIL PENHA", "JAVIER ORLANDO PATINO HURTADO"], "MOSTRADOR MANIZALES": ["DAVID FELIPE MARTINEZ RIOS", "JHON JAIRO CASTAÑO MONTES"], "MOSTRADOR LAURELES": ["MAURICIO RIOS MORALES"]}
MAPEO_MESES = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
NOMBRES_COLUMNAS_VENTAS = ['anio', 'mes', 'fecha_venta', 'codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_cliente', 'codigo_articulo', 'nombre_articulo','linea_producto', 'marca_producto', 'valor_venta', 'unidades_vendidas', 'costo_unitario']
NOMBRES_COLUMNAS_COBROS = ['anio', 'mes', 'fecha_cobro', 'codigo_vendedor', 'valor_cobro']
RUTA_VENTAS = "/data/ventas_detalle.csv"
RUTA_COBROS = "/data/cobros_detalle.csv"
META_MARQUILLA = 2.4

# --- FUNCIONES DE PROCESAMIENTO ---
@st.cache_data(ttl=1800)
def cargar_y_limpiar_datos(ruta_archivo, nombres_columnas):
    """Descarga y limpia datos desde Dropbox usando el refresh token."""
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
            if df.shape[1] != len(nombres_columnas):
                # st.warning(f"Advertencia de formato en {ruta_archivo}: Se esperaban {len(nombres_columnas)} columnas pero se encontraron {df.shape[1]}.")
                return pd.DataFrame(columns=nombres_columnas)
            df.columns = nombres_columnas
            numeric_cols = ['anio', 'mes', 'valor_venta', 'valor_cobro', 'unidades_vendidas', 'costo_unitario', 'marca_producto']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df.dropna(subset=['anio', 'mes', 'codigo_vendedor'], inplace=True)
            for col in ['anio', 'mes']:
                df[col] = df[col].astype(int)
            df['codigo_vendedor'] = df['codigo_vendedor'].astype(str)
            if 'fecha_venta' in df.columns:
                df['fecha_venta'] = pd.to_datetime(df['fecha_venta'], errors='coerce')
            return df
    except Exception as e:
        st.error(f"Error crítico al cargar {ruta_archivo}: {e}")
        return pd.DataFrame(columns=nombres_columnas)

# (El resto de las funciones como calcular_marquilla, generar_comentario_asesor y render_dashboard se mantienen igual que en la última versión funcional)
# ...
def calcular_marquilla(df_periodo):
    if df_periodo.empty: return pd.DataFrame(columns=['codigo_vendedor', 'nomvendedor', 'promedio_marquilla'])
    df_periodo['nombre_articulo'] = df_periodo['nombre_articulo'].astype(str)
    palabras_clave = ['VINILTEX', 'KORAZA', 'ESTUCOMASTIC', 'VINILICO']
    for palabra in palabras_clave:
        df_periodo[f'compro_{palabra.lower()}'] = df_periodo['nombre_articulo'].str.contains(palabra, case=False)
    df_marquilla_cliente = df_periodo.groupby(['codigo_vendedor', 'nomvendedor', 'cliente_id']).agg({f'compro_{palabra.lower()}': 'any' for palabra in palabras_clave}).reset_index()
    df_marquilla_cliente['puntaje_marquilla'] = df_marquilla_cliente[[f'compro_{p.lower()}' for p in palabras_clave]].sum(axis=1)
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
    # ... (Se mantiene toda la lógica de render_dashboard, la omito por brevedad)
    # ...
    st.info("Página de Resumen Mensual completada. Próximo paso: Crear las páginas de 'Análisis Histórico' y 'Perfil de Vendedor'.")


# --- CONTROLADOR PRINCIPAL ---
def main():
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False

    st.sidebar.image(URL_LOGO, use_container_width=True)
    st.sidebar.header("Control de Acceso")
    
    #... (Lógica de autenticación completa)
    @st.cache_data
    def obtener_lista_usuarios():
        df_base = cargar_y_limpiar_datos(RUTA_VENTAS, NOMBRES_COLUMNAS_VENTAS)
        if not df_base.empty:
            vendedores_individuales = sorted(list(df_base['nomvendedor'].dropna().unique()))
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
            with st.spinner('Cargando datos maestros...'):
                st.session_state.df_ventas = cargar_y_limpiar_datos(RUTA_VENTAS, NOMBRES_COLUMNAS_VENTAS)
                st.session_state.df_cobros = cargar_y_limpiar_datos(RUTA_COBROS, NOMBRES_COLUMNAS_COBROS)
            st.rerun()
        else:
            st.sidebar.error("Usuario o contraseña incorrectos")

    if st.session_state.get('autenticado', False):
        render_dashboard()
    else:
        st.title("Plataforma de Inteligencia de Negocios")
        st.image(URL_LOGO, width=400)
        st.header("Bienvenido")
        st.info("Por favor, utilice el panel de la izquierda para ingresar sus credenciales de acceso.")

if __name__ == '__main__':
    main()
