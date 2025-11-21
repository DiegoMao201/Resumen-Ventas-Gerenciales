import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import unicodedata
import io
import dropbox
import re

# ==============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==============================================================================
st.set_page_config(page_title="Master Brain Ultra - Estrategia & Logística", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-left: 5px solid #003865;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    h1, h2, h3 { color: #003865; font-family: 'Helvetica', sans-serif; font-weight: 800; }
    div[data-testid="stMetricValue"] { color: #0058A7; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #eef; border-radius: 5px; }
    .stTabs [aria-selected="true"] { background-color: #003865; color: white; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MOTORES DE LIMPIEZA Y CLASIFICACIÓN
# ==============================================================================

def normalizar_texto(texto):
    """Estandariza texto: Mayúsculas, sin tildes, sin espacios extra."""
    if not isinstance(texto, str): 
        return str(texto) if pd.notnull(texto) else "SIN INFO"
    texto = str(texto)
    texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sin_tildes.upper().strip()

def limpiar_nit(nit):
    """Limpia NIT/NIF para cruces (solo números)."""
    if pd.isna(nit): return "0"
    s_nit = str(nit).split('-')[0] # Quitar dígito verificación si viene separado por guion
    s_limpio = re.sub(r'[^0-9]', '', s_nit)
    s_limpio = s_limpio.lstrip('0')
    return s_limpio if s_limpio else "0"

def clasificar_marca_ultra(row):
    """
    Lógica Maestra de Clasificación (Prioridad: Lista Blanca -> Código N -> Texto)
    """
    # Mapeo de columnas por nombre interno (ya renombradas)
    nom_art = normalizar_texto(row.get('NOMBRE_PRODUCTO_K', ''))
    cat_prod = normalizar_texto(row.get('CATEGORIA_L', ''))
    
    # Limpieza del código de marca (Columna N)
    raw_cod = str(row.get('CODIGO_MARCA_N', '0')).strip()
    cod_marca_N = raw_cod.split('.')[0] if '.' in raw_cod else raw_cod
    
    texto_busqueda = f"{cat_prod} {nom_art} {normalizar_texto(row.get('Marca_Original',''))}"

    # 1. LISTA BLANCA (ALIADOS ESTRATÉGICOS) - Prioridad Alta
    aliados = [
        'ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', 
        'SAINT GOBAIN', 'ALLEGION', 'SEGUREX', 'POLVOS', 'DELTA', 
        'MASTERD', 'GLOBAL', 'SANTENO', 'BELLOTA', '3M', 'SISTA'
    ]
    for aliado in aliados:
        if aliado in texto_busqueda: return aliado

    # 2. MAPEO EXACTO DE CÓDIGOS (TU ÁRBOL DE DECISIÓN)
    mapa_arbol = {
        '33': 'OCEANIC PAINTS',
        '34': 'PROTECTO',
        '37': 'INTERNATIONAL PAINT',
        '40': 'ICO',
        '41': 'TERINSA',
        '50': 'PINTUCO (ASC)',
        '54': 'INTERNATIONAL PAINT',
        '55': 'COLORANTS',
        '56': 'PINTUCO PROFESIONAL',
        '58': 'PINTUCO',       
        '59': 'MADETEC',
        '60': 'INTERPON',
        '61': 'VARIOUS',
        '62': 'ICO',
        '63': 'TERINSA',
        '64': 'PINTUCO CONST',
        '66': 'ICO PACKAGING',
        '67': 'AUTOMOTIVE',
        '68': 'RESICOAT',
        '73': 'CORAL',
        '87': 'SIKKENS',
        '89': 'WANDA',
        '90': 'SIKKENS AUTOCOAT',
        '91': 'SIKKENS',
        '94': 'PROTECTO PROF'
    }
    
    if cod_marca_N in mapa_arbol:
        return mapa_arbol[cod_marca_N]

    # 3. BÚSQUEDA GENÉRICA DE PINTUCO (Si falló el código)
    claves_pintuco = ['PINTUCO', 'VINILTEX', 'KORAZA']
    for k in claves_pintuco:
        if k in texto_busqueda: return 'PINTUCO ARQUITECTONICO'

    return 'OTROS'

# ==============================================================================
# 3. CONEXIÓN DROPBOX (CLIENTES DETALLE)
# ==============================================================================
@st.cache_data(ttl=3600)
def cargar_clientes_dropbox():
    """Carga clientes_detalle.csv con NIF20 y CIUDAD."""
    try:
        try:
            APP_KEY = st.secrets["dropbox"]["app_key"]
            APP_SECRET = st.secrets["dropbox"]["app_secret"]
            REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]
        except:
            return pd.DataFrame()

        with dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN) as dbx:
            # RUTA ACTUALIZADA
            ruta = '/data/clientes_detalle.csv'
            metadata, res = dbx.files_download(path=ruta)
            contenido = res.content.decode('latin-1', errors='ignore')
            
            # Detección automática de separador
            df_drop = pd.read_csv(io.StringIO(contenido), sep=None, engine='python')
            
            # Normalizar nombres de columnas (Upper y strip)
            df_drop.columns = [c.strip().upper() for c in df_drop.columns]
            
            # Verificar columnas críticas
            col_nit = 'NIF20' if 'NIF20' in df_drop.columns else 'NIT'
            col_ciudad = 'CIUDAD' if 'CIUDAD' in df_drop.columns else 'POBLACION'
            
            if col_nit not in df_drop.columns:
                st.error(f"Columna {col_nit} no encontrada en Dropbox.")
                return pd.DataFrame()

            # Procesar
            df_drop['Key_Nit'] = df_drop[col_nit].apply(limpiar_nit)
            
            if col_ciudad in df_drop.columns:
                df_drop['Poblacion_Real'] = df_drop[col_ciudad].apply(normalizar_texto)
            else:
                df_drop['Poblacion_Real'] = "SIN CIUDAD"

            # Extraer Riesgo si existe
            if 'RIESGO' in df_drop.columns:
                df_drop['Riesgo_Cliente'] = df_drop['RIESGO']
            else:
                df_drop['Riesgo_Cliente'] = 'NO INFO'

            # Eliminar duplicados por NIT, priorizando el primero
            df_maestro = df_drop.drop_duplicates(subset=['Key_Nit'])
            
            return df_maestro[['Key_Nit', 'Poblacion_Real', 'Riesgo_Cliente']]

    except Exception as e:
        st.error(f"Error Dropbox: {e}")
        return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO DE DATOS (MASTER BRAIN)
# ==============================================================================

if 'df_ventas' not in st.session_state:
    st.info("⚠️ Carga el archivo de ventas en el inicio.")
    st.stop()

df_raw = st.session_state.df_ventas.copy()

# --- 4.1. MAPEO DE COLUMNAS (POSICIONAL) ---
# Aseguramos que tenemos suficientes columnas
if df_raw.shape[1] > 14:
    # Mapa basado en: H=Cliente, K=Producto, L=Categoria, N=MarcaCodigo, O=Venta
    col_mapping = {
        df_raw.columns[0]: 'anio',
        df_raw.columns[1]: 'mes', # Asumiendo col 1 es mes
        df_raw.columns[2]: 'dia', # Asumiendo col 2 es dia
        df_raw.columns[7]: 'CODIGO_CLIENTE_H',
        df_raw.columns[10]: 'NOMBRE_PRODUCTO_K',
        df_raw.columns[11]: 'CATEGORIA_L',
        df_raw.columns[13]: 'CODIGO_MARCA_N',
        df_raw.columns[14]: 'VALOR_VENTA_O'
    }
    # Renombrar solo las que existen
    new_cols = {k: v for k, v in col_mapping.items() if k in df_raw.columns}
    df_raw = df_raw.rename(columns=new_cols)
    
    # Limpieza Numérica
    df_raw['VALOR_VENTA_O'] = pd.to_numeric(df_raw['VALOR_VENTA_O'], errors='coerce').fillna(0)
    
    # Crear fecha ficticia si no existe para análisis de tiempo
    # Intento construir fecha si existen anio y mes
    try:
        meses_map = {'Enero':1, 'Febrero':2, 'Marzo':3, 'Abril':4, 'Mayo':5, 'Junio':6, 
                     'Julio':7, 'Agosto':8, 'Septiembre':9, 'Octubre':10, 'Noviembre':11, 'Diciembre':12}
        
        # Si mes es texto
        if df_raw['mes'].dtype == object:
             df_raw['mes_num'] = df_raw['mes'].map(meses_map).fillna(1).astype(int)
        else:
             df_raw['mes_num'] = pd.to_numeric(df_raw['mes'], errors='coerce').fillna(1).astype(int)
             
        df_raw['anio_num'] = pd.to_numeric(df_raw['anio'], errors='coerce').fillna(2024).astype(int)
        
        # Creamos columna fecha (primer dia del mes)
        df_raw['Fecha_Dt'] = pd.to_datetime(dict(year=df_raw['anio_num'], month=df_raw['mes_num'], day=1))
    except:
        df_raw['Fecha_Dt'] = pd.to_datetime('today') # Fallback

else:
    st.error("El archivo de ventas no tiene la estructura de columnas correcta (mínimo hasta columna O).")
    st.stop()

# --- 4.2. APLICAR INTELIGENCIA DE MARCA ---
df_raw['Marca_Master'] = df_raw.apply(clasificar_marca_ultra, axis=1)

# --- 4.3. FUSIÓN CON POBLACIONES (DROPBOX) ---
# Usamos CODIGO_CLIENTE_H como NIT (NIF20)
df_raw['Key_Nit'] = df_raw['CODIGO_CLIENTE_H'].apply(limpiar_nit)

with st.spinner("🌍 Georeferenciando clientes con base maestra..."):
    df_clientes = cargar_clientes_dropbox()

if not df_clientes.empty:
    df_full = pd.merge(df_raw, df_clientes, on='Key_Nit', how='left')
    df_full['Poblacion_Real'] = df_full['Poblacion_Real'].fillna('SIN ASIGNAR')
    df_full['Riesgo_Cliente'] = df_full['Riesgo_Cliente'].fillna('DESCONOCIDO')
else:
    df_full = df_raw.copy()
    df_full['Poblacion_Real'] = 'SIN CONEXION'
    df_full['Riesgo_Cliente'] = 'DESCONOCIDO'

# ==============================================================================
# 5. DASHBOARD ESTRATÉGICO
# ==============================================================================

st.title("🧠 Master Brain Ultra: Crecimiento & Logística")
st.markdown("### ¿Dónde ganamos dinero y dónde lo perdemos logísticamente?")

# --- FILTROS ---
st.sidebar.header("🎛️ Panel de Control")
anios = sorted(df_full['anio'].unique(), reverse=True)
anio_act = st.sidebar.selectbox("Año Actual", anios, index=0)
anio_base = st.sidebar.selectbox("Año Base", [a for a in anios if a != anio_act] + ["Ninguno"], index=0)

st.sidebar.markdown("---")
marcas = sorted(df_full['Marca_Master'].unique())
sel_marcas = st.sidebar.multiselect("Filtrar Marcas", marcas, default=marcas)

zonas = ["TODAS"] + sorted(df_full['Poblacion_Real'].unique())
sel_zona = st.sidebar.selectbox("Filtrar Población", zonas)

# --- DATA FILTRADA ---
df_f = df_full[df_full['Marca_Master'].isin(sel_marcas)].copy()
if sel_zona != "TODAS":
    df_f = df_f[df_f['Poblacion_Real'] == sel_zona]

df_now = df_f[df_f['anio'] == anio_act]
df_prev = df_f[df_f['anio'] == anio_base] if anio_base != "Ninguno" else pd.DataFrame()

# --- KPIs SUPERIORES ---
venta_hoy = df_now['VALOR_VENTA_O'].sum()
venta_ayer = df_prev['VALOR_VENTA_O'].sum() if not df_prev.empty else 0
dif_dinero = venta_hoy - venta_ayer
var_pct = (dif_dinero / venta_ayer * 100) if venta_ayer > 0 else 0
# Drop Size (Venta Total / Cantidad Facturas o Clientes Unicos en su defecto)
# Si no hay numero de factura, usamos filas como proxy de items o clientes unicos por fecha
transacciones = len(df_now) 
ticket_prom = venta_hoy / transacciones if transacciones > 0 else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Venta Total", f"${venta_hoy/1e6:,.1f} M", f"{var_pct:+.1f}%")
k2.metric("Crecimiento Neto ($)", f"${dif_dinero/1e6:+.1f} M", "vs Año Base")
k3.metric("Clientes Activos", df_now['Key_Nit'].nunique())
k4.metric("Ticket Promedio (Línea)", f"${ticket_prom:,.0f}", "Eficiencia Venta")

st.divider()

# --- TABS DE ANÁLISIS ---
t_grow, t_log, t_share = st.tabs(["🚀 Drivers de Crecimiento", "📦 Costo x Servir & Logística", "🎯 Peso Marcas/Categorías"])

# --- TAB 1: DRIVERS DE CRECIMIENTO (WATERFALL & BARRAS) ---
with t_grow:
    st.subheader(f"¿Qué Marcas Impulsan o Frenan el Crecimiento ({anio_base} vs {anio_act})?")
    
    if not df_prev.empty:
        # Agrupar
        g_now = df_now.groupby('Marca_Master')['VALOR_VENTA_O'].sum()
        g_old = df_prev.groupby('Marca_Master')['VALOR_VENTA_O'].sum()
        
        df_bridge = pd.DataFrame({'Actual': g_now, 'Base': g_old}).fillna(0)
        df_bridge['Variacion'] = df_bridge['Actual'] - df_bridge['Base']
        df_bridge['Tipo'] = df_bridge['Variacion'].apply(lambda x: 'Impulsor 🟢' if x >=0 else 'Freno 🔴')
        df_bridge = df_bridge.sort_values('Variacion', ascending=True)
        
        c_chart, c_table = st.columns([2, 1])
        
        with c_chart:
            # Gráfico de Barras Divergentes (Mejor que waterfall para muchas categorías)
            fig_div = px.bar(
                df_bridge, 
                y=df_bridge.index, 
                x='Variacion',
                color='Tipo',
                orientation='h',
                text_auto='.2s',
                color_discrete_map={'Impulsor 🟢': '#2E7D32', 'Freno 🔴': '#C62828'},
                title="Variación en Dinero por Marca (Neto)"
            )
            fig_div.add_vline(x=0, line_width=1, line_color="black")
            st.plotly_chart(fig_div, use_container_width=True)
            
        with c_table:
            st.markdown("#### Detalle de Variación")
            df_show = df_bridge[['Actual', 'Base', 'Variacion']].sort_values('Variacion', ascending=False)
            st.dataframe(df_show.style.format("${:,.0f}").background_gradient(subset=['Variacion'], cmap='RdYlGn'))
    else:
        st.info("Selecciona un Año Base para ver los Drivers de Crecimiento.")

# --- TAB 2: LOGÍSTICA (COSTO POR SERVIR) ---
with t_log:
    st.subheader("Matriz de Eficiencia: ¿Dónde es costoso entregar?")
    st.markdown("""
    * **Eje Y (Drop Size):** Cuánto nos compran en promedio por línea/pedido. (Arriba = Bueno).
    * **Eje X (Frecuencia):** Cantidad de meses distintos con compra. (Derecha = Visita constante).
    * **Burbuja:** Venta Total.
    """)
    
    # Calculamos métricas por Población
    # Frecuencia = Conteo de meses distintos con venta
    df_log_kpi = df_now.groupby('Poblacion_Real').agg(
        Venta_Total=('VALOR_VENTA_O', 'sum'),
        Frecuencia_Meses=('Fecha_Dt', 'nunique'), # Cuantos meses/fechas distintas hubo venta
        Num_Lineas=('VALOR_VENTA_O', 'count')
    ).reset_index()
    
    df_log_kpi = df_log_kpi[df_log_kpi['Venta_Total'] > 0]
    df_log_kpi['Drop_Size'] = df_log_kpi['Venta_Total'] / df_log_kpi['Num_Lineas']
    
    # Scatter Plot
    fig_log = px.scatter(
        df_log_kpi,
        x="Frecuencia_Meses",
        y="Drop_Size",
        size="Venta_Total",
        color="Drop_Size",
        hover_name="Poblacion_Real",
        title="Poblaciones: Tamaño de Pedido vs Frecuencia",
        color_continuous_scale="RdYlGn",
        height=500
    )
    # Lineas promedio
    avg_drop = df_log_kpi['Drop_Size'].median()
    avg_freq = df_log_kpi['Frecuencia_Meses'].median()
    
    fig_log.add_hline(y=avg_drop, line_dash="dash", annotation_text="Drop Medio")
    fig_log.add_vline(x=avg_freq, line_dash="dash", annotation_text="Frec Media")
    
    col_l1, col_l2 = st.columns([3, 1])
    with col_l1:
        st.plotly_chart(fig_log, use_container_width=True)
        
    with col_l2:
        st.warning("⚠️ **Ojo con estas:** Alta Frecuencia pero Bajo Drop Size (Logística cara)")
        df_alert = df_log_kpi[
            (df_log_kpi['Frecuencia_Meses'] >= avg_freq) & 
            (df_log_kpi['Drop_Size'] < avg_drop)
        ].sort_values('Venta_Total', ascending=False).head(10)
        st.dataframe(df_alert[['Poblacion_Real', 'Drop_Size']].style.format({'Drop_Size': '${:,.0f}'}))

# --- TAB 3: SHARE (PESO CATEGORÍAS) ---
with t_share:
    st.subheader("Profundidad de Portafolio")
    
    # Sunburst: Marca -> Categoria -> Producto (Top)
    # Limpiamos categoria para el grafico
    df_now['Cat_Clean'] = df_now['CATEGORIA_L'].apply(normalizar_texto)
    
    # Agrupamos
    df_sun = df_now.groupby(['Marca_Master', 'Cat_Clean'])['VALOR_VENTA_O'].sum().reset_index()
    df_sun = df_sun[df_sun['VALOR_VENTA_O'] > 0]
    
    col_s1, col_s2 = st.columns(2)
    
    with col_s1:
        fig_sun = px.sunburst(
            df_sun,
            path=['Marca_Master', 'Cat_Clean'],
            values='VALOR_VENTA_O',
            title="Peso Jerárquico (Click para expandir)",
            color='VALOR_VENTA_O',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_sun, use_container_width=True)
        
    with col_s2:
        st.markdown("#### Top 10 Categorías que más pesan")
        df_top_cat = df_now.groupby('Cat_Clean')['VALOR_VENTA_O'].sum().reset_index().sort_values('VALOR_VENTA_O', ascending=False).head(10)
        df_top_cat['% Share'] = (df_top_cat['VALOR_VENTA_O'] / venta_hoy) * 100
        
        fig_bar_cat = px.bar(df_top_cat, x='% Share', y='Cat_Clean', orientation='h', title="Pareto Categorías", text_auto='.1f')
        st.plotly_chart(fig_bar_cat, use_container_width=True)

st.success("✅ Análisis finalizado. Datos de clientes (NIF/Ciudad) integrados desde Dropbox.")
