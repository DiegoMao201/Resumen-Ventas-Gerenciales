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
# 1. CONFIGURACIÓN PROFESIONAL DE LA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Master Brain Ultra - Intelligence & Growth", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS para interfaz ejecutiva
st.markdown("""
<style>
    .metric-container {
        background-color: #f8f9fa;
        border-left: 5px solid #003865;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    h1, h2, h3 { color: #003865; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #eef;
        border-radius: 5px 5px 0px 0px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #003865;
        color: white;
    }
    div[data-testid="stMetricValue"] { color: #0058A7; font-size: 26px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MOTORES DE INTELIGENCIA (LIMPIEZA Y CLASIFICACIÓN)
# ==============================================================================

def normalizar_texto(texto):
    """Estandariza texto a mayúsculas sin tildes."""
    if not isinstance(texto, str): 
        return str(texto) if pd.notnull(texto) else "SIN INFO"
    texto = str(texto)
    texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sin_tildes.upper().strip()

def limpiar_nit(nit):
    """Limpia NIT/NIF para asegurar cruces perfectos (solo números)."""
    if pd.isna(nit): return "0"
    s_nit = str(nit).split('-')[0] # Quitar dígito verificación
    s_limpio = re.sub(r'[^0-9]', '', s_nit)
    s_limpio = s_limpio.lstrip('0') # Quitar ceros a la izquierda
    return s_limpio if s_limpio else "0"

def obtener_nombre_marca_por_codigo(codigo):
    """
    Diccionario Maestro basado en la IMAGEN del árbol de decisión.
    Entrada: Código numérico (str). Salida: Nombre de Marca limpio.
    """
    # Mapeo exacto de tu imagen
    mapa = {
        '33': 'OCEANIC PAINTS',
        '34': 'PROTECTO',
        '35': 'OTROS',
        '37': 'INTERNATIONAL PAINT',
        '40': 'ICO',
        '41': 'TERINSA',
        '50': 'PINTUCO (MEGA)',       # P8-ASC-MEGA
        '54': 'INTERNATIONAL PAINT',  # MPY-International
        '55': 'COLORANTS LATAM',      # DPP-AN COLORANTS...
        '56': 'PINTUCO PROFESIONAL',  # DPP-Pintuco Profesional
        '57': 'PINTUCO (MEGA)',       # ASC-Mega
        '58': 'PINTUCO',              # DPP-Pintuco (La marca madre)
        '59': 'MADETEC',              # DPP-Madetec
        '60': 'INTERPON',             # POW-Interpon
        '61': 'VARIOUS',
        '62': 'ICO',                  # DPP-ICO
        '63': 'TERINSA',              # DPP-Terinsa
        '64': 'PINTUCO',              # MPY-Pintuco
        '65': 'TERCEROS (NON-AN)',
        '66': 'ICO PACKAGING',
        '67': 'AUTOMOTIVE OEM',
        '68': 'RESICOAT',
        '73': 'CORAL',                # DPP-Coral
        '87': 'SIKKENS',
        '89': 'WANDA',
        '90': 'SIKKENS AUTOCOAT',
        '91': 'SIKKENS',
        '94': 'PROTECTO PROFESIONAL'
    }
    return mapa.get(codigo, None)

def clasificar_estrategia_master(row):
    """
    ALGORITMO DE CLASIFICACIÓN DE 3 NIVELES:
    1. Lista Blanca (Aliados Estratégicos) -> Prioridad Máxima.
    2. Código de Marca (Columna N) -> Prioridad Media.
    3. OTROS -> Todo lo demás.
    """
    # 1. Preparar datos
    # Mapeo de columnas basado en índices renombrados previamente
    prod_name = normalizar_texto(row.get('NOMBRE_PRODUCTO_K', ''))
    cat_name = normalizar_texto(row.get('CATEGORIA_L', ''))
    
    # Obtener código de marca (Columna N), limpiando decimales (.0)
    raw_code = str(row.get('CODIGO_MARCA_N', '0'))
    code_clean = raw_code.split('.')[0].strip()
    
    texto_busqueda = f"{prod_name} {cat_name}"

    # --- NIVEL 1: LISTA BLANCA (ALIADOS) ---
    # Si el producto contiene alguno de estos nombres, se clasifica aquí ignorando el código N.
    aliados = [
        'ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', 
        'SAINT GOBAIN', 'ALLEGION', 'SEGUREX', 'POLVOS', 'DELTA', 
        'MASTERD', 'GLOBAL', 'SANTENO', 'BELLOTA', '3M', 'SISTA', 'SINTESOLDA'
    ]
    for aliado in aliados:
        if aliado in texto_busqueda:
            return aliado

    # --- NIVEL 2: LÓGICA DE CÓDIGO (COLUMNA N) ---
    nombre_marca = obtener_nombre_marca_por_codigo(code_clean)
    if nombre_marca:
        return nombre_marca

    # --- NIVEL 3: FALLBACK ---
    # Si no es aliado y el código N no está en el mapa o es 0
    return 'OTROS'

# ==============================================================================
# 3. CONEXIÓN DROPBOX (ROBUSTA)
# ==============================================================================
@st.cache_data(ttl=3600)
def cargar_poblaciones_dropbox():
    """
    Intenta cargar 'clientes_detalle.csv' desde la raíz de la App de Dropbox.
    Maneja errores para no romper la app si el archivo falta.
    """
    try:
        # 1. Obtener credenciales
        try:
            APP_KEY = st.secrets["dropbox"]["app_key"]
            APP_SECRET = st.secrets["dropbox"]["app_secret"]
            REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]
        except:
            st.error("⚠️ No se encontraron las credenciales de Dropbox en st.secrets.")
            return pd.DataFrame()

        # 2. Conectar y Descargar
        with dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN) as dbx:
            # Intentamos en la raíz, que es lo más común
            ruta = '/clientes_detalle.csv' 
            try:
                metadata, res = dbx.files_download(path=ruta)
            except dropbox.exceptions.ApiError as e:
                # Si falla, intentamos con /data/ por si acaso, o retornamos error claro
                try:
                    ruta = '/data/clientes_detalle.csv'
                    metadata, res = dbx.files_download(path=ruta)
                except:
                    st.warning(f"⚠️ **Archivo no encontrado en Dropbox.**\nBusqué: `/clientes_detalle.csv`.\nPor favor verifica que el archivo esté en la carpeta de la App.")
                    return pd.DataFrame()

            # 3. Leer contenido
            contenido = res.content.decode('latin-1', errors='ignore')
            
            # Detectar separador (comas, punto y coma o pipes)
            separador = None 
            if '|' in contenido.split('\n')[0]: separador = '|'
            elif ';' in contenido.split('\n')[0]: separador = ';'
            else: separador = ','
            
            df_drop = pd.read_csv(io.StringIO(contenido), sep=separador, engine='python')
            
            # 4. Limpieza y Estandarización
            df_drop.columns = [c.strip().upper() for c in df_drop.columns]
            
            # Buscar columna NIT y CIUDAD
            col_nit = next((c for c in df_drop.columns if 'NIF' in c or 'NIT' in c), None)
            col_ciudad = next((c for c in df_drop.columns if 'CIUDAD' in c or 'POBLACION' in c), None)
            
            if not col_nit:
                st.warning("El archivo de Dropbox no tiene una columna NIT o NIF20 identificable.")
                return pd.DataFrame()
                
            df_drop['Key_Nit'] = df_drop[col_nit].apply(limpiar_nit)
            
            if col_ciudad:
                df_drop['Poblacion_Real'] = df_drop[col_ciudad].apply(normalizar_texto)
            else:
                df_drop['Poblacion_Real'] = 'SIN ASIGNAR'

            # Eliminar duplicados (tomar el primero)
            return df_drop.drop_duplicates(subset=['Key_Nit'])[['Key_Nit', 'Poblacion_Real']]

    except Exception as e:
        st.error(f"Error de conexión con Dropbox: {str(e)}")
        return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO CENTRAL (EL CEREBRO)
# ==============================================================================

# Validar si hay datos cargados
if 'df_ventas' not in st.session_state:
    st.info("👋 **Bienvenido a Master Brain Ultra.** Por favor carga tu archivo de ventas en la pantalla de inicio.")
    st.stop()

df_raw = st.session_state.df_ventas.copy()

# --- 4.1. MAPEO DE COLUMNAS POR POSICIÓN (H, K, L, N, O) ---
# Esto asegura que leamos las columnas correctas sin importar el nombre del encabezado
if df_raw.shape[1] > 14:
    col_map = {
        df_raw.columns[0]: 'anio',
        df_raw.columns[1]: 'mes',
        df_raw.columns[7]: 'CODIGO_CLIENTE_H', # NIT/Cliente
        df_raw.columns[10]: 'NOMBRE_PRODUCTO_K',
        df_raw.columns[11]: 'CATEGORIA_L',
        df_raw.columns[13]: 'CODIGO_MARCA_N',  # El código numérico clave
        df_raw.columns[14]: 'VALOR_VENTA_O'
    }
    # Renombrar solo las existentes
    final_map = {k: v for k, v in col_map.items() if k in df_raw.columns}
    df_raw = df_raw.rename(columns=final_map)
    
    # Convertir numéricos
    df_raw['VALOR_VENTA_O'] = pd.to_numeric(df_raw['VALOR_VENTA_O'], errors='coerce').fillna(0)
    
    # Crear Fecha para análisis temporal
    try:
        df_raw['anio_num'] = pd.to_numeric(df_raw['anio'], errors='coerce').fillna(2024).astype(int)
        # Mapeo simple de meses si vienen en texto
        meses = {'enero':1, 'febrero':2, 'marzo':3, 'abril':4, 'mayo':5, 'junio':6, 'julio':7, 'agosto':8, 'septiembre':9, 'octubre':10, 'noviembre':11, 'diciembre':12}
        
        if df_raw['mes'].dtype == object:
            df_raw['mes_lower'] = df_raw['mes'].astype(str).str.lower().str.strip()
            df_raw['mes_num'] = df_raw['mes_lower'].map(meses).fillna(1).astype(int)
        else:
            df_raw['mes_num'] = pd.to_numeric(df_raw['mes'], errors='coerce').fillna(1).astype(int)
            
        df_raw['Fecha_Dt'] = pd.to_datetime(dict(year=df_raw['anio_num'], month=df_raw['mes_num'], day=1))
    except:
        df_raw['Fecha_Dt'] = pd.to_datetime('today')

else:
    st.error("❌ El archivo cargado no tiene la estructura esperada (Mínimo columna O). Revisa el formato.")
    st.stop()

# --- 4.2. APLICAR LA CLASIFICACIÓN MAESTRA ---
with st.spinner("🧠 Ejecutando algoritmo de clasificación de marcas..."):
    df_raw['Marca_Master'] = df_raw.apply(clasificar_estrategia_master, axis=1)

# --- 4.3. CRUCE CON DROPBOX (POBLACIONES) ---
df_raw['Key_Nit'] = df_raw['CODIGO_CLIENTE_H'].apply(limpiar_nit)

with st.spinner("🌍 Georeferenciando clientes desde la nube..."):
    df_clientes = cargar_poblaciones_dropbox()

if not df_clientes.empty:
    # Left Join para no perder ventas aunque no tengan ciudad
    df_full = pd.merge(df_raw, df_clientes, on='Key_Nit', how='left')
    df_full['Poblacion_Real'] = df_full['Poblacion_Real'].fillna('SIN ASIGNAR')
else:
    # Si falla Dropbox, usamos fallback
    df_full = df_raw.copy()
    df_full['Poblacion_Real'] = 'SIN CONEXIÓN DB'

# ==============================================================================
# 5. DASHBOARD ANALÍTICO (UI)
# ==============================================================================

st.title("🧠 Master Brain Ultra: Estrategia Comercial 360º")
st.markdown("### Análisis de Crecimiento, Rentabilidad y Logística")

# --- SIDEBAR & FILTROS ---
with st.sidebar:
    st.header("🎛️ Panel de Control")
    
    # Filtro Año
    lista_anios = sorted(df_full['anio'].unique(), reverse=True)
    anio_act = st.selectbox("Año Objetivo", lista_anios, index=0)
    anio_ant = st.selectbox("Año Base (Comparar)", [a for a in lista_anios if a != anio_act] + ["Ninguno"], index=0)
    
    st.markdown("---")
    
    # Filtro Marca
    lista_marcas = sorted(df_full['Marca_Master'].unique())
    # Mover OTROS al final
    if 'OTROS' in lista_marcas: 
        lista_marcas.remove('OTROS')
        lista_marcas.append('OTROS')
        
    sel_marcas = st.multiselect("Filtrar Marcas", lista_marcas, default=lista_marcas)
    
    # Filtro Población
    lista_pobs = ["TODAS"] + sorted(df_full['Poblacion_Real'].unique())
    sel_pob = st.selectbox("Filtrar Población", lista_pobs)

# --- APLICACIÓN DE FILTROS ---
df_filtered = df_full[df_full['Marca_Master'].isin(sel_marcas)].copy()
if sel_pob != "TODAS":
    df_filtered = df_filtered[df_filtered['Poblacion_Real'] == sel_pob]

# Dataframes por periodo
df_now = df_filtered[df_filtered['anio'] == anio_act]
df_prev = df_filtered[df_filtered['anio'] == anio_ant] if anio_ant != "Ninguno" else pd.DataFrame()

# --- KPIs PRINCIPALES ---
tot_venta_act = df_now['VALOR_VENTA_O'].sum()
tot_venta_ant = df_prev['VALOR_VENTA_O'].sum() if not df_prev.empty else 0

diff = tot_venta_act - tot_venta_ant
crec_pct = (diff / tot_venta_ant * 100) if tot_venta_ant > 0 else 0

# Ticket Promedio (Venta Total / Registros o Clientes Únicos)
# Usaremos registros como proxy de líneas facturadas
ticket_prom = tot_venta_act / len(df_now) if len(df_now) > 0 else 0
clientes_unicos = df_now['Key_Nit'].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Venta Total", f"${tot_venta_act/1e6:,.1f} M", f"{crec_pct:+.1f}%")
col2.metric("Crecimiento Neto", f"${diff/1e6:+.1f} M", "Vs Año Base")
col3.metric("Clientes Activos", f"{clientes_unicos}", "En periodo")
col4.metric("Ticket Promedio (Línea)", f"${ticket_prom:,.0f}", "Eficiencia")

st.divider()

# --- TABS DE ANÁLISIS PROFUNDO ---
tab_growth, tab_logistics, tab_share = st.tabs([
    "🚀 Drivers de Crecimiento", 
    "📦 Costo por Servir (Logística)", 
    "🎯 Estructura de Portafolio"
])

# --- TAB 1: CRECIMIENTO (WATERFALL) ---
with tab_growth:
    st.subheader(f"¿Qué marcas movieron la aguja entre {anio_ant} y {anio_act}?")
    
    if not df_prev.empty:
        # Agrupar datos
        g_act = df_now.groupby('Marca_Master')['VALOR_VENTA_O'].sum()
        g_ant = df_prev.groupby('Marca_Master')['VALOR_VENTA_O'].sum()
        
        df_var = pd.DataFrame({'Actual': g_act, 'Base': g_ant}).fillna(0)
        df_var['Variacion'] = df_var['Actual'] - df_var['Base']
        df_var['Tipo'] = df_var['Variacion'].apply(lambda x: 'Crecimiento' if x >=0 else 'Decrecimiento')
        
        # Ordenar para el gráfico
        df_var = df_var.sort_values('Variacion', ascending=False)
        
        col_g1, col_g2 = st.columns([2, 1])
        
        with col_g1:
            # Waterfall Chart
            fig_water = go.Figure(go.Waterfall(
                name="Variación", orientation="v",
                measure=["relative"] * len(df_var),
                x=df_var.index,
                y=df_var['Variacion'],
                connector={"line":{"color":"rgb(63, 63, 63)"}},
                decreasing={"marker":{"color":"#D32F2F"}}, # Rojo
                increasing={"marker":{"color":"#388E3C"}}, # Verde
            ))
            fig_water.update_layout(title="Cascada de Crecimiento por Marca ($)", height=500)
            st.plotly_chart(fig_water, use_container_width=True)
            
        with col_g2:
            st.markdown("#### 🏆 Top Impulsores vs Frenos")
            st.dataframe(
                df_var[['Actual', 'Base', 'Variacion']]
                .style.format("${:,.0f}")
                .background_gradient(subset=['Variacion'], cmap='RdYlGn')
            )
    else:
        st.info("⚠️ Selecciona un 'Año Base' en el menú lateral para ver el análisis comparativo.")

# --- TAB 2: LOGÍSTICA (MATRIZ DE COSTO) ---
with tab_logistics:
    st.subheader("Matriz de Costo por Servir (Poblaciones)")
    st.markdown("""
    **Análisis de Rentabilidad Logística:**
    * **Eje Y (Drop Size):** Valor promedio por pedido/línea. Queremos estar arriba (pedidos grandes).
    * **Eje X (Frecuencia):** Cantidad de meses con compra. Queremos estar a la derecha (compra constante).
    * **Burbujas Rojas:** Zonas de alerta (Alta visita, bajo pedido).
    """)
    
    # Calcular métricas por Población
    df_log = df_now.groupby('Poblacion_Real').agg(
        Venta=('VALOR_VENTA_O', 'sum'),
        Lineas=('VALOR_VENTA_O', 'count'),
        Frecuencia_Meses=('Fecha_Dt', 'nunique')
    ).reset_index()
    
    df_log = df_log[df_log['Venta'] > 0]
    df_log['Drop_Size'] = df_log['Venta'] / df_log['Lineas']
    
    # Scatter Plot
    avg_drop = df_log['Drop_Size'].median()
    avg_freq = df_log['Frecuencia_Meses'].median()
    
    fig_scat = px.scatter(
        df_log,
        x="Frecuencia_Meses",
        y="Drop_Size",
        size="Venta",
        color="Drop_Size",
        hover_name="Poblacion_Real",
        title="Eficiencia Logística por Población",
        color_continuous_scale="RdYlGn",
        height=550
    )
    
    # Cuadrantes
    fig_scat.add_hline(y=avg_drop, line_dash="dash", annotation_text="Drop Medio")
    fig_scat.add_vline(x=avg_freq, line_dash="dash", annotation_text="Frec. Media")
    
    st.plotly_chart(fig_scat, use_container_width=True)
    
    st.markdown("#### 🚨 Alerta: Poblaciones Ineficientes (Mucha visita, poca venta)")
    df_inef = df_log[
        (df_log['Frecuencia_Meses'] > avg_freq) & 
        (df_log['Drop_Size'] < avg_drop)
    ].sort_values('Venta', ascending=False).head(10)
    
    st.dataframe(df_inef.style.format({'Venta': '${:,.0f}', 'Drop_Size': '${:,.0f}'}))

# --- TAB 3: SHARE & ESTRUCTURA ---
with tab_share:
    st.subheader("Distribución del Portafolio (Sunburst)")
    st.markdown("Explora la jerarquía: **Marca -> Categoría -> Producto**")
    
    # Limpiar datos para el gráfico
    df_sun = df_now.groupby(['Marca_Master', 'CATEGORIA_L'])['VALOR_VENTA_O'].sum().reset_index()
    df_sun = df_sun[df_sun['VALOR_VENTA_O'] > 0] # Quitar ceros
    
    col_s1, col_s2 = st.columns([2, 1])
    
    with col_s1:
        fig_sun = px.sunburst(
            df_sun,
            path=['Marca_Master', 'CATEGORIA_L'],
            values='VALOR_VENTA_O',
            color='VALOR_VENTA_O',
            color_continuous_scale='Blues',
            title="Peso Visual de Marcas y Categorías"
        )
        st.plotly_chart(fig_sun, use_container_width=True)
        
    with col_s2:
        st.markdown("#### Top Categorías Globales")
        df_top = df_now.groupby('CATEGORIA_L')['VALOR_VENTA_O'].sum().reset_index().sort_values('VALOR_VENTA_O', ascending=False).head(10)
        df_top['Share'] = (df_top['VALOR_VENTA_O'] / tot_venta_act) * 100
        
        st.dataframe(df_top.style.format({'VALOR_VENTA_O': '${:,.0f}', 'Share': '{:.2f}%'}))

st.success(f"✅ Análisis completado. {len(df_now):,.0f} registros procesados. {df_now['Poblacion_Real'].nunique()} poblaciones identificadas.")
