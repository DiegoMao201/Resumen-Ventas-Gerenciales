import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import unicodedata
import io
import dropbox
from datetime import datetime, date
import calendar
from functools import reduce
import warnings
warnings.filterwarnings('ignore')

# ===== NUEVAS IMPORTACIONES PARA IA Y ANÁLISIS AVANZADO =====
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import json
import requests  # Para API de GPT

# ===== CONFIGURACIÓN DE CACHÉ MEJORADA =====
@st.cache_resource(show_spinner=False)
def get_dropbox_client():
    """Cliente Dropbox singleton"""
    return dropbox.Dropbox(
        app_key=st.secrets.dropbox.app_key,
        app_secret=st.secrets.dropbox.app_secret,
        oauth2_refresh_token=st.secrets.dropbox.refresh_token
    )

@st.cache_data(ttl=7200, show_spinner=False)
def cargar_poblaciones_dropbox_excel_optimizado():
    """Versión optimizada con mejor manejo de errores"""
    try:
        dbx = get_dropbox_client()
        rutas = ['/clientes_detalle.xlsx', '/data/clientes_detalle.xlsx', '/Master/clientes_detalle.xlsx']
        res = None
        for r in rutas:
            try:
                _, res = dbx.files_download(path=r)
                break
            except: 
                continue
        
        if not res: 
            return pd.DataFrame()
        
        with io.BytesIO(res.content) as stream:
            df = pd.read_excel(stream, engine='openpyxl')
        
        cols = {c.strip().lower(): c for c in df.columns}
        
        if 'nit' in cols and 'poblacion' in cols:
            df_clean = df[[cols['nit'], cols['poblacion']]].copy()
            df_clean.columns = ['Key_Nit', 'Poblacion_Real']
            df_clean['Key_Nit'] = df_clean['Key_Nit'].apply(limpiar_codigo_master)
            return df_clean
        
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"No se pudo cargar datos geográficos: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=7200, show_spinner=False)
def procesar_datos_maestros(_df_raw):
    """Procesamiento optimizado de datos maestros con tipos eficientes"""
    df = _df_raw.copy()
    
    # Optimización de tipos de datos
    df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce').fillna(0).astype('float32')
    df['anio'] = pd.to_numeric(df['anio'], errors='coerce').fillna(date.today().year).astype('int16')
    df['mes'] = pd.to_numeric(df['mes'], errors='coerce').fillna(1).astype('int8')
    
    if 'dia' not in df.columns:
        df['dia'] = 15
    else:
        df['dia'] = pd.to_numeric(df['dia'], errors='coerce').fillna(15).astype('int8')
    
    df['Key_Nit'] = df['COD'].apply(limpiar_codigo_master)
    
    # Clasificación vectorizada
    df[['Marca_Master', 'Categoria_Master']] = df.apply(
        lambda x: pd.Series(clasificar_marca_unificada(x)), axis=1
    )
    
    return df

# ==============================================================================
# 1. CONFIGURACIÓN VISUAL (UI/UX PREMIUM)
# ==============================================================================
st.set_page_config(
    page_title="Análisis Estratégico | Ferreinox",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === HEADER EMPRESARIAL ===
st.markdown("""
<div class="strategic-header">
    <h1>🚀 Análisis Estratégico de Crecimiento</h1>
    <p>Ferreinox S.A.S. BIC | Inteligencia de Negocios con IA | <a href="https://www.ferreinox.co" target="_blank" style="color: white; text-decoration: underline;">www.ferreinox.co</a></p>
</div>
""", unsafe_allow_html=True)

# Logo en sidebar
st.sidebar.image("https://raw.githubusercontent.com/DiegoMao2021/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", use_container_width=True)
st.sidebar.markdown("---")

st.markdown("""
<style>
    /* === PALETA FERREINOX === */
    :root {
        --ferreinox-primary: #1e3a8a;
        --ferreinox-secondary: #3b82f6;
        --ferreinox-accent: #f59e0b;
        --ferreinox-success: #10b981;
        --ferreinox-danger: #ef4444;
        --ferreinox-dark: #1f2937;
    }
    
    /* === HEADER EMPRESARIAL === */
    .strategic-header {
        background: linear-gradient(135deg, var(--ferreinox-primary) 0%, var(--ferreinox-secondary) 100%);
        padding: 2.5rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(30, 58, 138, 0.3);
        text-align: center;
    }
    
    .strategic-header h1 {
        color: white;
        font-size: 2.8rem;
        font-weight: 900;
        margin: 0 0 0.5rem 0;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        letter-spacing: -1px;
    }
    
    .strategic-header p {
        color: rgba(255, 255, 255, 0.95);
        font-size: 1.2rem;
        margin: 0;
        font-weight: 500;
    }
    
    /* === KPI CARDS PREMIUM === */
    .metric-card {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
        border-left: 5px solid var(--ferreinox-secondary);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
        margin-bottom: 1rem;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        border-left-color: var(--ferreinox-accent);
    }
    
    .ai-box {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-left: 4px solid var(--ferreinox-accent);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.1);
        margin: 1rem 0;
    }
    
    .ai-title {
        font-weight: 800;
        display: block;
        margin-bottom: 0.75rem;
        text-transform: uppercase;
        font-size: 0.9rem;
        letter-spacing: 1.2px;
        color: var(--ferreinox-accent);
    }
    
    /* === TABS MODERNOS === */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8fafc;
        padding: 0.5rem;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: white;
        border-radius: 8px;
        color: var(--ferreinox-dark);
        font-weight: 600;
        font-size: 1rem;
        border: 2px solid transparent;
        transition: all 0.3s;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e0f2fe;
        border-color: var(--ferreinox-secondary);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--ferreinox-primary) 0%, var(--ferreinox-secondary) 100%) !important;
        color: white !important;
        border-color: var(--ferreinox-primary) !important;
    }
    
    /* === ALERTAS === */
    div[data-testid="stAlert"] {
        border-radius: 10px;
        border-left: 5px solid;
        padding: 1rem 1.5rem;
    }
    
    /* === DATAFRAMES === */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
    }
    
    /* === PROGRESS BARS === */
    .stProgress > div > div {
        background: linear-gradient(90deg, var(--ferreinox-secondary) 0%, var(--ferreinox-accent) 100%);
        border-radius: 10px;
    }
    
    /* === SIDEBAR === */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
        border-right: 2px solid #e5e7eb;
    }
    
    section[data-testid="stSidebar"] .stSelectbox label {
        color: var(--ferreinox-primary);
        font-weight: 700;
    }
    
    /* === FOOTER === */
    .strategic-footer {
        text-align: center;
        padding: 2rem;
        margin-top: 3rem;
        border-top: 2px solid #e5e7eb;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    }
    
    .strategic-footer a {
        color: var(--ferreinox-primary);
        text-decoration: none;
        font-weight: 700;
    }
    
    /* === ANIMACIONES === */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .animated-section {
        animation: fadeIn 0.6s ease-out;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. FUNCIONES DE LÓGICA DE NEGOCIO Y UTILIDADES
# ==============================================================================

def normalizar_texto(texto):
    if pd.isna(texto) or str(texto).strip() == "": return "SIN DEFINIR"
    texto = str(texto)
    texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sin_tildes.upper().strip()

def limpiar_codigo_master(codigo):
    if pd.isna(codigo): return "0"
    s_cod = str(codigo).strip()
    if s_cod == "": return "0"
    try:
        if '.' in s_cod: s_cod = str(int(float(s_cod)))
    except: pass
    return s_cod

def clasificar_marca_unificada(row):
    """
    Lógica Central de Unificación de Marcas y Categorías.
    """
    prod_name = normalizar_texto(row.get('NOMBRE_PRODUCTO_K', ''))
    cat_raw = normalizar_texto(row.get('CATEGORIA_L', ''))
    raw_code = str(row.get('CODIGO_MARCA_N', '0')).split('.')[0].strip()
    
    texto_analisis = f"{prod_name} {cat_raw}"

    # 1. EXCLUSIÓN 3M
    if '3M' in texto_analisis:
        return 'OTROS', 'OTROS'

    # 2. ALIADOS (Marca = Categoria)
    aliados = ['ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', 'SISTA', 'SINTESOLDA']
    for aliado in aliados:
        if aliado in texto_analisis:
            return aliado, aliado

    # 3. MAPEO POR CÓDIGOS
    mapa_codigos = {
        '33': 'OCEANIC', '34': 'PROTECTO', '37': 'INTERNATIONAL', '40': 'ICO',
        '41': 'TERINSA', '50': 'PINTUCO MEGA', '54': 'INTERNATIONAL', '55': 'COLORANTS',
        '56': 'PINTUCO PROFESIONAL', '57': 'PINTUCO MEGA', '58': 'PINTUCO', '59': 'MADETEC',
        '60': 'INTERPON', '62': 'ICO', '63': 'TERINSA', '64': 'PINTUCO',
        '68': 'RESICOAT', '73': 'CORAL', '87': 'SIKKENS', '89': 'WANDA',
        '90': 'SIKKENS', '91': 'SIKKENS', '94': 'PROTECTO'
    }

    if raw_code in mapa_codigos:
        nombre_marca = mapa_codigos[raw_code]
        return nombre_marca, nombre_marca

    # 4. DEFAULT
    return 'OTRAS MARCAS', 'OTROS'

def generar_excel_profesional(df, sheet_name="Data"):
    """
    Genera un archivo Excel con formato profesional:
    - Encabezados en negrita y color.
    - Columnas autoajustadas.
    - Formato de moneda para columnas numéricas.
    """
    output = io.BytesIO()
    # Usamos xlsxwriter como motor para formateo avanzado
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        
        # Definir formatos
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#4F46E5', # Color Indigo profesional
            'font_color': '#FFFFFF',
            'border': 1
        })
        
        currency_format = workbook.add_format({'num_format': '$ #,##0'})
        text_format = workbook.add_format({'text_wrap': False})
        
        # Aplicar formato a los encabezados y columnas
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
            # Ajustar ancho basado en contenido o tipo
            col_width = 20
            # Detectar si es columna numérica para aplicar formato moneda
            is_numeric = pd.api.types.is_numeric_dtype(df[value])
            
            if is_numeric:
                worksheet.set_column(col_num, col_num, 15, currency_format)
            else:
                max_len = df[value].astype(str).map(len).max()
                col_width = min(max_len + 2, 40) if pd.notna(max_len) else 20
                worksheet.set_column(col_num, col_num, col_width, text_format)
                
    return output.getvalue()

# ==============================================================================
# 3. CARGA DE DATOS
# ==============================================================================
@st.cache_data(ttl=3600)
def cargar_poblaciones_dropbox_excel():
    try:
        APP_KEY = st.secrets["dropbox"]["app_key"]
        APP_SECRET = st.secrets["dropbox"]["app_secret"]
        REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]
        with dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN) as dbx:
            rutas = ['/clientes_detalle.xlsx', '/data/clientes_detalle.xlsx', '/Master/clientes_detalle.xlsx']
            res = None
            for r in rutas:
                try:
                    _, res = dbx.files_download(path=r)
                    break
                except: continue
            if not res: return pd.DataFrame()
            with io.BytesIO(res.content) as stream:
                df = pd.read_excel(stream, engine='openpyxl')
            
            cols = {c.strip().lower(): c for c in df.columns}
            col_k = next((v for k,v in cols.items() if 'cod' in k and 'cli' in k), None)
            col_c = next((v for k,v in cols.items() if 'ciudad' in k), None)
            col_v = next((v for k,v in cols.items() if 'vendedor' in k), None)
            
            if col_k:
                df['Key_Nit'] = df[col_k].apply(limpiar_codigo_master)
                df['Poblacion_Real'] = df[col_c].apply(normalizar_texto) if col_c else 'SIN ASIGNAR'
                df['Vendedor'] = df[col_v].apply(normalizar_texto) if col_v else 'GENERAL'
                return df[['Key_Nit', 'Poblacion_Real', 'Vendedor']].drop_duplicates(subset=['Key_Nit'])
    except Exception: pass
    return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.warning("⚠️ Por favor, carga el archivo maestro en el Home.")
    st.stop()

df_raw = st.session_state.df_ventas.copy()

# Mapeo y limpieza
try:
    cols_map = {
        0: 'anio', 1: 'mes', 2: 'dia', 7: 'COD', 8: 'CLIENTE', 
        10: 'NOMBRE_PRODUCTO_K', 11: 'CATEGORIA_L', 13: 'CODIGO_MARCA_N', 14: 'VALOR'
    }
    current_cols = df_raw.columns
    rename_dict = {current_cols[idx]: new_name for idx, new_name in cols_map.items() if idx < len(current_cols)}
    df_raw = df_raw.rename(columns=rename_dict)
    
    if 'dia' not in df_raw.columns: df_raw['dia'] = 15
    else: df_raw['dia'] = pd.to_numeric(df_raw['dia'], errors='coerce').fillna(15).astype(int)
except Exception:
    st.error("Error en estructura de columnas.")
    st.stop()

df_raw['VALOR'] = pd.to_numeric(df_raw['VALOR'], errors='coerce').fillna(0)
df_raw['anio'] = pd.to_numeric(df_raw['anio'], errors='coerce').fillna(date.today().year).astype(int)
df_raw['mes'] = pd.to_numeric(df_raw['mes'], errors='coerce').fillna(1).astype(int)
df_raw['Key_Nit'] = df_raw['COD'].apply(limpiar_codigo_master)

# Lógica Unificada
df_raw[['Marca_Master', 'Categoria_Master']] = df_raw.apply(
    lambda x: pd.Series(clasificar_marca_unificada(x)), axis=1
)

# Cruce Geo
df_cli = cargar_poblaciones_dropbox_excel()
if not df_cli.empty:
    df_full = pd.merge(df_raw, df_cli, on='Key_Nit', how='left')
    df_full['Poblacion_Real'] = df_full['Poblacion_Real'].fillna('SIN GEO')
    df_full['Vendedor'] = df_full['Vendedor'].fillna('GENERAL')
else:
    df_full = df_raw.copy()
    df_full['Poblacion_Real'] = 'SIN GEO'
    df_full['Vendedor'] = 'GENERAL'

# Filtro YTD
hoy = date.today()
def ytd(row):
    if row['mes'] < hoy.month: return True
    if row['mes'] == hoy.month: return row['dia'] <= hoy.day
    return False

df_master = df_full[df_full.apply(ytd, axis=1)].copy()

# ==============================================================================
# 5. DASHBOARD - GROWTH FOCUS
# ==============================================================================
st.title("🚀 Master Brain | Growth Intelligence Center")
st.markdown(f"**Modo:** Análisis de Crecimiento Comercial | **Corte:** {hoy.strftime('%d-%b')}")
st.divider()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔍 Filtros Estratégicos")
    
    anios = sorted(df_master['anio'].unique(), reverse=True)
    anio_obj = st.selectbox("Año Objetivo", anios, 0)
    anio_base = st.selectbox("Año Base (Comparativo)", [a for a in anios if a!=anio_obj], 0)
    
    sel_city = st.multiselect("Poblaciones", sorted(df_master['Poblacion_Real'].unique()))
    
    # Filtro Marca
    marcas_disp = sorted(df_master['Marca_Master'].unique())
    sel_brand = st.multiselect("Marcas (Unificadas)", marcas_disp)
    
    # Filtro Categoria (Dependiente de marca)
    if sel_brand:
        cats_disp = sorted(df_master[df_master['Marca_Master'].isin(sel_brand)]['Categoria_Master'].unique())
    else:
        cats_disp = sorted(df_master['Categoria_Master'].unique())
    sel_cat = st.multiselect("Categorías", cats_disp)

# --- FILTRADO DATA ---
df_f = df_master.copy()
if sel_city: df_f = df_f[df_f['Poblacion_Real'].isin(sel_city)]
if sel_brand: df_f = df_f[df_f['Marca_Master'].isin(sel_brand)]
if sel_cat: df_f = df_f[df_f['Categoria_Master'].isin(sel_cat)]

df_act = df_f[df_f['anio'] == anio_obj].copy()
df_ant = df_f[df_f['anio'] == anio_base].copy()

# --- KPIs MACRO ---
v_act = df_act['VALOR'].sum()
v_ant = df_ant['VALOR'].sum()
diff_v = v_act - v_ant
pct_v = (diff_v / v_ant * 100) if v_ant > 0 else 100

cli_act = df_act['Key_Nit'].nunique()
cli_ant = df_ant['Key_Nit'].nunique()
diff_cli = cli_act - cli_ant

tx_act = df_act['COD'].count() # Transacciones aprox
tik_act = v_act / tx_act if tx_act > 0 else 0
tik_ant = v_ant / df_ant['COD'].count() if not df_ant.empty else 0
diff_tik = ((tik_act - tik_ant)/tik_ant * 100) if tik_ant > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
def card(col, lbl, val, d_val, d_lbl, color="pos"):
    col.markdown(f"""<div class="metric-card"><div class="metric-lbl">{lbl}</div>
    <div class="metric-val">{val}</div><div class="metric-delta"><span class="{color}">{d_val}</span> {d_lbl}</div></div>""", unsafe_allow_html=True)

col_st = "pos" if diff_v >= 0 else "neg"
card(c1, "Ventas Totales", f"${v_act/1e6:,.1f}M", f"{pct_v:+.1f}%", "vs Año Anterior", col_st)
card(c2, "Variación Neta", f"${abs(diff_v)/1e6:,.1f}M", "Dinero", "Crecimiento Real", col_st)
card(c3, "Clientes Activos", f"{cli_act}", f"{diff_cli:+}", "Clientes vs AA", "pos" if diff_cli>=0 else "neg")
card(c4, "Ticket Promedio", f"${tik_act:,.0f}", f"{diff_tik:+.1f}%", "Valor por Línea", "pos" if diff_tik>=0 else "neg")
card(c5, "Mix de Marcas", f"{df_act['Marca_Master'].nunique()}", "Activas", "Portafolio Movido", "pos")

# ==============================================================================
# 6. TABS DE ANÁLISIS PROFUNDO (GROWTH & OPPORTUNITY)
# ==============================================================================
tabs = st.tabs([
    "📊 DNA Crecimiento", 
    "📍 Geo-Oportunidad", 
    "👥 Clientes Top 50", 
    "📦 Producto Estrella", 
    "📉 Riesgo/Fugas", 
    "🤖 AI Análisis", 
    "📈 Proyección Ventas"  # NUEVO TAB
])

# --- TAB 1: DNA DE CRECIMIENTO (Marca/Categoria) ---
with tabs[0]:
    col_dna1, col_dna2 = st.columns([3, 1])
    
    # Preparar datos Waterfall
    g_act = df_act.groupby('Marca_Master')['VALOR'].sum()
    g_ant = df_ant.groupby('Marca_Master')['VALOR'].sum()
    df_g = pd.DataFrame({'Actual': g_act, 'Anterior': g_ant}).fillna(0)
    df_g['Variacion'] = df_g['Actual'] - df_g['Anterior']
    df_g = df_g.sort_values('Variacion', ascending=False)
    
    top_grower = df_g.index[0] if not df_g.empty else "N/A"
    top_dragger = df_g.index[-1] if not df_g.empty and df_g['Variacion'].iloc[-1] < 0 else "Ninguno"
    
    with col_dna1:
        st.subheader("Contribution Chart: ¿Qué Marcas explican el resultado?")
        fig_w = go.Figure(go.Waterfall(
            orientation="v", measure=["relative"] * len(df_g),
            x=df_g.index, y=df_g['Variacion'],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#ef4444"}},
            increasing={"marker": {"color": "#10b981"}}
        ))
        fig_w.update_layout(height=450, title="Variación en Pesos ($) por Marca Unificada")
        st.plotly_chart(fig_w, use_container_width=True)
        
    with col_dna2:
        st.markdown(f"""
        <div class="ai-box">
        <span class="ai-title">🤖 AI GROWTH INSIGHTS</span>
        El crecimiento neto de <b>${diff_v/1e6:,.1f}M</b> se explica así:
        <br><br>
        🚀 <b>El Motor:</b> La marca <b>{top_grower}</b> es la campeona, aportando +${df_g['Variacion'].max()/1e6:,.1f}M al resultado.
        <br><br>
        ⚓ <b>El Freno:</b> {f"La marca <b>{top_dragger}</b> está restando crecimiento (${abs(df_g['Variacion'].min())/1e6:,.1f}M)." if top_dragger != "Ninguno" else "No hay marcas con decrecimiento significativo."}
        </div>
        """, unsafe_allow_html=True)
        
        st.dataframe(df_g[['Actual', 'Variacion']].style.format("${:,.0f}").background_gradient(cmap='RdYlGn', subset=['Variacion']), use_container_width=True)

# --- TAB 2: GEO OPORTUNIDAD ---
with tabs[1]:
    # Análisis de Poblaciones: Matriz BCG (Volumen vs Crecimiento)
    city_act = df_act.groupby('Poblacion_Real')['VALOR'].sum()
    city_ant = df_ant.groupby('Poblacion_Real')['VALOR'].sum()
    df_city = pd.DataFrame({'Venta': city_act, 'Anterior': city_ant}).fillna(0)
    df_city['Crecimiento_Pesos'] = df_city['Venta'] - df_city['Anterior']
    df_city['Crecimiento_Pct'] = (df_city['Crecimiento_Pesos'] / df_city['Anterior']).replace([np.inf, -np.inf], 0) * 100
    
    # Filtro visual para quitar ruido (ciudades muy pequeñas con crecimientos % absurdos)
    df_city = df_city[df_city['Venta'] > 100000] 
    
    col_geo1, col_geo2 = st.columns([3, 1])
    
    with col_geo1:
        st.subheader("Mapa de Calor: Volumen vs. Aceleración")
        fig_sc = px.scatter(df_city.reset_index(), x="Venta", y="Crecimiento_Pct", 
                            size="Venta", color="Crecimiento_Pesos",
                            hover_name="Poblacion_Real",
                            color_continuous_scale="RdYlGn",
                            title="Matriz Geo-Estratégica (Bubble Size = Volumen de Venta)",
                            labels={"Venta": "Venta Actual ($)", "Crecimiento_Pct": "Crecimiento (%)"})
        fig_sc.add_hline(y=0, line_dash="dash", line_color="grey")
        st.plotly_chart(fig_sc, use_container_width=True)
        
    with col_geo2:
        top_city = df_city.sort_values('Crecimiento_Pesos', ascending=False).index[0] if not df_city.empty else "N/A"
        flop_city = df_city.sort_values('Crecimiento_Pesos', ascending=True).index[0] if not df_city.empty else "N/A"
        
        st.markdown(f"""
        <div class="ai-box">
        <span class="ai-title">🌍 ANÁLISIS TERRITORIAL</span>
        <b>¿Dónde poner la lupa?</b>
        <br><br>
        🥇 <b>Zona Estrella:</b> {top_city} está liderando la expansión.
        <br><br>
        🚑 <b>Zona Crítica:</b> {flop_city} muestra la mayor contracción en dinero. Revisar competencia o vendedor asignado.
        </div>
        """, unsafe_allow_html=True)

# --- TAB 3: CLIENTES TOP OPORTUNIDAD ---
with tabs[2]:
    st.subheader("🎯 Cazador de Oportunidades: Top 50 Clientes")
    
    # Análisis Cliente x Cliente x Vendedor
    cl_act = df_act.groupby(['Key_Nit', 'CLIENTE', 'Vendedor'])['VALOR'].sum()
    cl_ant = df_ant.groupby(['Key_Nit', 'CLIENTE', 'Vendedor'])['VALOR'].sum()
    df_cl = pd.DataFrame({'Venta_Actual': cl_act, 'Venta_Anterior': cl_ant}).fillna(0)
    df_cl['Var_Pesos'] = df_cl['Venta_Actual'] - df_cl['Venta_Anterior']
    df_cl = df_cl.reset_index()
    
    # Oportunidad 1: Clientes que DECRECEN (Riesgo) - TOP 50
    df_risk = df_cl[df_cl['Var_Pesos'] < 0].sort_values('Var_Pesos', ascending=True).head(50)
    
    # Oportunidad 2: Clientes con CRECIMIENTO MASIVO (Fidelizar) - TOP 50
    df_star = df_cl.sort_values('Var_Pesos', ascending=False).head(50)
    
    c_cli1, c_cli2 = st.columns(2)
    
    with c_cli1:
        st.markdown("### 📉 TOP 50 Caídas (Recuperación)")
        st.markdown("Prioridad máxima: Clientes con mayor pérdida de valor respecto al año anterior.")
        
        # Botón de Descarga
        excel_risk = generar_excel_profesional(df_risk, "Top_50_Caidas")
        st.download_button(
            label="📥 Descargar Top 50 Caídas (Excel)",
            data=excel_risk,
            file_name=f"Top_50_Clientes_Caida_{hoy}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_risk"
        )
        
        st.dataframe(df_risk[['CLIENTE', 'Vendedor', 'Venta_Actual', 'Venta_Anterior', 'Var_Pesos']]
                     .style.format({'Venta_Actual': '${:,.0f}', 'Venta_Anterior': '${:,.0f}', 'Var_Pesos': '${:,.0f}'})
                     .background_gradient(cmap='Reds_r', subset=['Var_Pesos']), use_container_width=True)
        
    with c_cli2:
        st.markdown("### 🚀 TOP 50 Crecimiento")
        st.markdown("Clientes desarrollando el portafolio agresivamente.")
        
        # Botón de Descarga
        excel_star = generar_excel_profesional(df_star, "Top_50_Crecimiento")
        st.download_button(
            label="📥 Descargar Top 50 Crecimiento (Excel)",
            data=excel_star,
            file_name=f"Top_50_Clientes_Crecimiento_{hoy}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_star"
        )
        
        st.dataframe(df_star[['CLIENTE', 'Vendedor', 'Venta_Actual', 'Venta_Anterior', 'Var_Pesos']]
                     .style.format({'Venta_Actual': '${:,.0f}', 'Venta_Anterior': '${:,.0f}', 'Var_Pesos': '${:,.0f}'})
                     .background_gradient(cmap='Greens', subset=['Var_Pesos']), use_container_width=True)

# --- TAB 4: PRODUCTO ESTRELLA ---
with tabs[3]:
    st.subheader("📦 Rendimiento de Portafolio (SKUs)")
    
    prod_act = df_act.groupby(['NOMBRE_PRODUCTO_K', 'Marca_Master'])['VALOR'].sum()
    prod_ant = df_ant.groupby(['NOMBRE_PRODUCTO_K', 'Marca_Master'])['VALOR'].sum()
    df_prod = pd.DataFrame({'Venta_Actual': prod_act, 'Venta_Anterior': prod_ant}).fillna(0)
    df_prod['Var_Pesos'] = df_prod['Venta_Actual'] - df_prod['Venta_Anterior']
    df_prod = df_prod.reset_index()
    
    best_sku = df_prod.sort_values('Var_Pesos', ascending=False).head(50)
    worst_sku = df_prod.sort_values('Var_Pesos', ascending=True).head(50)
    
    st.markdown(f"""
    <div class="ai-box">
    <span class="ai-title">📦 MIX INTEL</span>
    El producto que más dinero nuevo trajo a la compañía es: **{best_sku.iloc[0]['NOMBRE_PRODUCTO_K']}** (+${best_sku.iloc[0]['Var_Pesos']/1e6:,.1f}M).
    <br>Asegura inventario de este item.
    </div>
    """, unsafe_allow_html=True)
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("**Top 50: Productos Ganadores**")
        excel_best_sku = generar_excel_profesional(best_sku, "Top_Prod_Ganadores")
        st.download_button(
            label="📥 Descargar Productos Ganadores",
            data=excel_best_sku,
            file_name=f"Top_Productos_Ganadores_{hoy}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_best_sku"
        )
        st.dataframe(best_sku.head(20).style.format({'Venta_Actual':'${:,.0f}','Var_Pesos':'${:,.0f}'}).background_gradient(cmap='Greens'), use_container_width=True)
    with col_p2:
        st.markdown("**Top 50: Productos Perdiendo Terreno**")
        excel_worst_sku = generar_excel_profesional(worst_sku, "Top_Prod_Perdidas")
        st.download_button(
            label="📥 Descargar Productos en Baja",
            data=excel_worst_sku,
            file_name=f"Top_Productos_Baja_{hoy}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_worst_sku"
        )
        st.dataframe(worst_sku.head(20).style.format({'Venta_Actual':'${:,.0f}','Var_Pesos':'${:,.0f}'}).background_gradient(cmap='Reds_r'), use_container_width=True)

# --- TAB 5: RIESGO / FUGAS ---
with tabs[4]:
    ids_act = set(df_act['Key_Nit'])
    ids_ant = set(df_ant['Key_Nit'])
    
    lost_ids = ids_ant - ids_act
    new_ids = ids_act - ids_ant
    
    # Calcular valor perdido (cuánto compraban el año pasado los que se fueron)
    val_lost = df_ant[df_ant['Key_Nit'].isin(lost_ids)]['VALOR'].sum()
    val_new = df_act[df_act['Key_Nit'].isin(new_ids)]['VALOR'].sum()
    
    col_f1, col_f2, col_f3 = st.columns(3)
    col_f1.metric("Clientes Perdidos (Churn)", len(lost_ids), f"-${val_lost/1e6:,.1f}M impact", delta_color="inverse")
    col_f2.metric("Clientes Nuevos (Acq)", len(new_ids), f"+${val_new/1e6:,.1f}M new sales")
    col_f3.metric("Retención Neta", f"{len(ids_act.intersection(ids_ant))}", "Clientes recurrentes")
    
    st.divider()
    
    if lost_ids:
        st.markdown("### 🚨 LISTA NEGRA: Clientes Fugados (Venta = 0 este año)")
        st.markdown("Estos clientes compraban el año pasado y este año no han comprado nada.")
        df_fugados = df_ant[df_ant['Key_Nit'].isin(lost_ids)].groupby(['CLIENTE', 'Poblacion_Real', 'Vendedor'])['VALOR'].sum().reset_index()
        df_fugados = df_fugados.rename(columns={'VALOR': 'Venta_Perdida_Total'}).sort_values('Venta_Perdida_Total', ascending=False)
        
        excel_churn = generar_excel_profesional(df_fugados, "Clientes_Fugados")
        st.download_button(
            label="📥 Descargar Lista de Fugados (Excel)",
            data=excel_churn,
            file_name=f"Clientes_Fugados_{hoy}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_churn"
        )
        
        st.dataframe(df_fugados.style.format({'Venta_Perdida_Total': '${:,.0f}'}), use_container_width=True)
    else:
        st.success("¡Increíble! No hay clientes perdidos con los filtros actuales.")

# --- TAB 6: AI CONCLUSIONES ---
with tabs[5]:
    st.header("🧠 Master Brain: Diagnóstico Final")
    
    # Generación de Texto Dinámico
    trend = "POSITIVA" if diff_v > 0 else "NEGATIVA"
    action_verb = "potenciar" if diff_v > 0 else "corregir"
    
    txt_geo = f"La zona de <b>{top_city}</b> es tu fortaleza actual."
    txt_risk = f"Hay <b>{len(lost_ids)} clientes</b> que dejaron de comprar, costando ${val_lost/1e6:,.1f}M."
    
    st.markdown(f"""
    ### Resumen Ejecutivo Generado por IA
    
    1.  **Salud General:** La operación muestra una tendencia **{trend}** ({pct_v:+.1f}%) comparada con el periodo anterior.
    
    2.  **Drivers de Crecimiento:**
        * El crecimiento viene principalmente de la marca **{top_grower}**.
        * {txt_geo}
        * El producto estrella es **{best_sku.iloc[0]['NOMBRE_PRODUCTO_K']}**.
        
    3.  **Focos de Atención (Action Items):**
        * **Recuperación:** {txt_risk} Revisa la pestaña 'Riesgo/Fugas' para descargar la lista y llamar.
        * **Clientes en Caída:** Hay clientes activos comprando menos (ver pestaña 'Clientes Top'). Priorizar a **{df_risk.iloc[0]['CLIENTE'] if not df_risk.empty else 'N/A'}**.
        
    4.  **Conclusión:**
        La estrategia para lo que resta del periodo debe ser {action_verb} la venta en **{top_grower}** y ejecutar un plan de recuperación inmediato en la zona de **{flop_city}**.
    """)
    
    st.info("💡 Tip: Usa los filtros de la izquierda para generar este mismo diagnóstico para una Ciudad o Marca específica.")

# --- TAB 7: PROYECCIÓN Y FORECASTING ---
with tabs[6]:
    st.header("📈 Proyección de Ventas y Tendencias")
    
    col_proj1, col_proj2 = st.columns([2, 1])
    
    with col_proj1:
        st.subheader("Forecast de Ventas (Regresión Lineal)")
        
        # Calcular proyección
        meses_a_proyectar = st.slider("Meses a proyectar:", 1, 6, 3)
        
        resultado_proyeccion = calcular_proyeccion_ventas(df_full, meses_proyectar=meses_a_proyectar)
        
        if resultado_proyeccion[0] is not None:
            df_proyeccion, confianza, r2 = resultado_proyeccion
            
            # Gráfico de proyección
            fig_proj = go.Figure()
            
            # Histórico
            df_historico = df_proyeccion[df_proyeccion['tipo'] == 'Histórico']
            fig_proj.add_trace(go.Scatter(
                x=df_historico['periodo'],
                y=df_historico['venta_proyectada'],
                mode='lines+markers',
                name='Histórico',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=8)
            ))
            
            # Proyección
            df_futuro = df_proyeccion[df_proyeccion['tipo'] == 'Proyección']
            fig_proj.add_trace(go.Scatter(
                x=df_futuro['periodo'],
                y=df_futuro['venta_proyectada'],
                mode='lines+markers',
                name='Proyección',
                line=dict(color='#f59e0b', width=3, dash='dash'),
                marker=dict(size=10, symbol='diamond')
            ))
            
            fig_proj.update_layout(
                title=f"Proyección de Ventas - Próximos {meses_a_proyectar} Meses",
                xaxis_title="Periodo",
                yaxis_title="Ventas ($)",
                hovermode='x unified',
                height=450
            )
            
            st.plotly_chart(fig_proj, use_container_width=True)
            
        else:
            st.warning("⚠️ No hay suficientes datos históricos para generar proyección confiable (mínimo 6 meses)")
    
    with col_proj2:
        st.subheader("Nivel de Confianza")
        
        if resultado_proyeccion[0] is not None:
            # Gauge de confianza
            color_confianza = "#10b981" if confianza == "Alta" else "#f59e0b" if confianza == "Media" else "#ef4444"
            
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, {color_confianza}15 0%, {color_confianza}30 100%);
                border-left: 5px solid {color_confianza};
                padding: 1.5rem;
                border-radius: 12px;
                text-align: center;
                margin-bottom: 1rem;
            ">
                <h2 style="color: {color_confianza}; margin: 0;">{confianza}</h2>
                <p style="margin: 0.5rem 0 0 0; color: #64748b;">R² = {r2:.3f}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.info(f"""
            **Interpretación:**
            - R² = {r2:.1%} de la variación está explicada por el modelo
            - Confianza **{confianza}** en la proyección
            - {"Proyección muy confiable para planificación" if confianza == "Alta" else "Usar con precaución, considerar factores externos" if confianza == "Media" else "Baja confiabilidad, alta variabilidad histórica"}
            """)
            
            # Proyección en tabla
            st.subheader("Valores Proyectados")
            if not df_futuro.empty:
                df_futuro_display = df_futuro[['anio', 'mes', 'venta_proyectada']].copy()
                df_futuro_display['venta_proyectada'] = df_futuro_display['venta_proyectada'].apply(lambda x: f"${x:,.0f}")
                df_futuro_display.columns = ['Año', 'Mes', 'Venta Estimada']
                
                st.dataframe(df_futuro_display, use_container_width=True, hide_index=True)
    
    # Análisis de Estacionalidad
    st.markdown("---")
    st.subheader("📅 Análisis de Estacionalidad")
    
    df_estacional = analisis_estacionalidad(df_full)
    
    if not df_estacional.empty:
        col_est1, col_est2 = st.columns([3, 1])
        
        with col_est1:
            # Gráfico de índice estacional
            fig_estacional = go.Figure()
            
            colores = []
            for idx in df_estacional['indice_estacional']:
                if idx >= 110:
                    colores.append('#10b981')
                elif idx >= 95:
                    colores.append('#3b82f6')
                else:
                    colores.append('#ef4444')
            
            fig_estacional.add_trace(go.Bar(
                x=df_estacional['mes'],
                y=df_estacional['indice_estacional'],
                marker_color=colores,
                text=df_estacional['indice_estacional'].apply(lambda x: f"{x:.1f}"),
                textposition='outside'
            ))
            
            fig_estacional.add_hline(
                y=100, 
                line_dash="dash", 
                line_color="gray",
                annotation_text="Línea Base (100)"
            )
            
            fig_estacional.update_layout(
                title="Índice Estacional por Mes (Base 100 = Promedio)",
                xaxis_title="Mes",
                yaxis_title="Índice Estacional",
                height=400
            )
            
            st.plotly_chart(fig_estacional, use_container_width=True)
        
        with col_est2:
            st.subheader("Clasificación")
            
            for _, row in df_estacional.iterrows():
                mes_nombre = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 
                             7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
                
                st.markdown(f"""
                **{mes_nombre.get(row['mes'], row['mes'])}:** {row['clasificacion']}  
                Índice: {row['indice_estacional']:.1f}
                """)
def generar_reporte_ejecutivo_pdf(
    df_act, df_ant, metricas, analisis_ia, 
    top_marca, top_ciudad, producto_estrella
):
    """
    Genera un reporte ejecutivo completo en formato Markdown para exportar
    """
    from datetime import datetime
    fecha_reporte = datetime.now().strftime("%d de %B de %Y, %H:%M")
    
    val_act = df_act['VALOR'].sum()
    val_ant = df_ant['VALOR'].sum()
    variacion = ((val_act - val_ant) / val_ant * 100) if val_ant > 0 else 0
    
    reporte = f"""
# 📊 REPORTE EJECUTIVO DE VENTAS
## Ferreinox S.A.S. BIC | www.ferreinox.co

**Generado:** {fecha_reporte}

---

## 🎯 RESUMEN EJECUTIVO

| Métrica | Valor Actual | Valor Anterior | Variación |
|---------|--------------|----------------|-----------|
| **Ventas Totales** | ${val_act:,.0f} | ${val_ant:,.0f} | {variacion:+.1f}% |
| **Marca Líder** | {top_marca} | - | - |
| **Ciudad Estrella** | {top_ciudad} | - | - |
| **Producto Estrella** | {producto_estrella} | - | - |

---

## 💎 MÉTRICAS PREMIUM

- **Tasa de Retención de Clientes:** {metricas['tasa_retencion']:.1f}%
- **Customer Lifetime Value (CLV):** ${metricas['clv_estimado']:,.0f}
- **Ticket Promedio:** ${metricas['ticket_promedio']:,.0f}
- **Frecuencia de Compra:** {metricas['frecuencia_compra']:.1f} transacciones/cliente
- **Growth Rate:** {metricas['growth_rate']:+.1f}%
- **Concentración de Ventas:** {metricas['concentracion_ventas']} (HHI: {metricas['indice_herfindahl']:.0f})
- **Penetración de Marcas:** {metricas['marcas_promedio_cliente']:.2f} marcas/cliente

---

## 🤖 ANÁLISIS ESTRATÉGICO CON IA

{analisis_ia}

---

## 📈 TOP 10 CLIENTES EN CRECIMIENTO

"""
    
    # Agregar top clientes
    if not df_act.empty and not df_ant.empty:
        cl_act = df_act.groupby(['Key_Nit', 'CLIENTE'])['VALOR'].sum()
        cl_ant = df_ant.groupby(['Key_Nit', 'CLIENTE'])['VALOR'].sum()
        df_cl = pd.DataFrame({'Actual': cl_act, 'Anterior': cl_ant}).fillna(0)
        df_cl['Variacion'] = df_cl['Actual'] - df_cl['Anterior']
        
        top_10 = df_cl.nlargest(10, 'Variacion').reset_index()
        
        reporte += "| # | Cliente | Venta Actual | Venta Anterior | Crecimiento |\n"
        reporte += "|---|---------|--------------|----------------|-------------|\n"
        
        for idx, row in top_10.iterrows():
            reporte += f"| {idx+1} | {row['CLIENTE']} | ${row['Actual']:,.0f} | ${row['Anterior']:,.0f} | ${row['Variacion']:,.0f} |\n"
    
    reporte += f"""

---

**Reporte generado automáticamente por el Sistema de Inteligencia de Negocios Ferreinox**  
**Confidencial - Solo para uso interno**
"""
    
    return reporte


# AGREGAR botón de descarga en el TAB principal o al final del dashboard
st.markdown("---")
st.subheader("📥 Exportar Reporte Completo")

col_export1, col_export2 = st.columns(2)

with col_export1:
    if st.button("📄 Generar Reporte Ejecutivo", type="primary", use_container_width=True):
        with st.spinner("Generando reporte completo..."):
            metricas_calc = calcular_metricas_avanzadas(df_act, df_ant)
            
            analisis_ia_export = ""
            if 'analisis_ia_generado' in st.session_state:
                analisis_ia_export = st.session_state.analisis_ia_generado
            else:
                analisis_ia_export = "Análisis IA no generado en esta sesión"
            
            top_marca_exp = df_act.groupby('Marca_Master')['VALOR'].sum().idxmax() if not df_act.empty else "N/A"
            top_ciudad_exp = df_act.groupby('Poblacion_Real')['VALOR'].sum().idxmax() if not df_act.empty else "N/A"
            producto_exp = df_act.groupby('NOMBRE_PRODUCTO_K')['VALOR'].sum().idxmax() if not df_act.empty else "N/A"
            
            reporte_completo = generar_reporte_ejecutivo_pdf(
                df_act, df_ant, metricas_calc, analisis_ia_export,
                top_marca_exp, top_ciudad_exp, producto_exp
            )
            
            st.session_state.reporte_completo_generado = reporte_completo

with col_export2:
    if 'reporte_completo_generado' in st.session_state:
        st.download_button(
            label="⬇️ Descargar Reporte (Markdown)",
            data=st.session_state.reporte_completo_generado,
            file_name=f"Reporte_Ejecutivo_Ferreinox_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
            use_container_width=True
        )
        st.success("✅ Reporte generado con éxito")
