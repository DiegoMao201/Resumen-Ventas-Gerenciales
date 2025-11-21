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
st.set_page_config(page_title="Master Brain Ultra - Estrategia 360", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .metric-card {
        background-color: #ffffff;
        border-left: 5px solid #003865;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    h1, h2, h3 { color: #003865; font-family: 'Helvetica', sans-serif; font-weight: 800; }
    div[data-testid="stMetricValue"] { color: #0058A7; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. FUNCIONES DE LIMPIEZA E INTELIGENCIA
# ==============================================================================

def normalizar_texto(texto):
    """Estandariza texto: Mayúsculas, sin tildes, sin espacios extra."""
    if not isinstance(texto, str): 
        return str(texto) if pd.notnull(texto) else "SIN INFO"
    texto = str(texto)
    texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sin_tildes.upper().strip()

def limpiar_codigo_cliente(codigo):
    """
    Limpia el código de la Columna H para asegurar el cruce con Dropbox.
    """
    if pd.isna(codigo): return "0"
    s_cod = str(codigo)
    # Solo dejamos números
    s_limpio = re.sub(r'[^0-9]', '', s_cod)
    # Quitamos ceros a la izquierda si es necesario (normalmente los ERP los quitan)
    s_limpio = s_limpio.lstrip('0')
    return s_limpio if s_limpio else "0"

def clasificar_marca_ultra(row):
    """
    LÓGICA MAESTRA:
    1. Prioridad: Lista Blanca (Abracol, Induma...) en Nombre/Categoria.
    2. Secundaria: Código numérico en Columna N (Imagen del Árbol).
    3. Resto: OTROS.
    """
    # --- EXTRACCIÓN DE DATOS POR POSICIÓN (Mapeo Excel) ---
    # Usamos los nombres normalizados que definiremos al cargar el DF
    nom_art = normalizar_texto(row.get('NOMBRE_PRODUCTO_K', ''))
    cat_prod = normalizar_texto(row.get('CATEGORIA_L', ''))
    cod_marca_N = str(row.get('CODIGO_MARCA_N', '0')).strip().split('.')[0] # Quitamos decimales si hay (58.0 -> 58)
    
    texto_busqueda = cat_prod + " " + nom_art

    # --- 1. LISTA BLANCA (ALIADOS) ---
    aliados = [
        'ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', 
        'SAINT GOBAIN', 'ALLEGION', 'SEGUREX', 'POLVOS', 'DELTA', 
        'MASTERD', 'GLOBAL', 'SANTENO', 'BELLOTA'
    ]
    
    for aliado in aliados:
        if aliado in texto_busqueda:
            return aliado

    # --- 2. LÓGICA NUMÉRICA (COLUMNA N -> IMAGEN DEL ÁRBOL) ---
    # Mapeo exacto de los códigos de tu imagen a nombres reales
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
        '58': 'PINTUCO',       # La marca principal
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

    # Buscamos el código exacto o si empieza por él
    if cod_marca_N in mapa_arbol:
        return mapa_arbol[cod_marca_N]
    
    # Si el código en N es complejo (ej: "58-PINTUCO"), intentamos buscar el prefijo
    for key, valor in mapa_arbol.items():
        if cod_marca_N.startswith(key):
            return valor
            
    # Casos de rescate si la columna N está vacía pero dice Pintuco en otro lado
    if cod_marca_N in ['0', '', 'NAN']:
        if 'PINTUCO' in texto_busqueda or 'VINILTEX' in texto_busqueda:
            return 'PINTUCO'

    return 'OTROS'

# ==============================================================================
# 3. CONEXIÓN DROPBOX (CARGA DE POBLACIONES)
# ==============================================================================
@st.cache_data(ttl=3600)
def cargar_datos_dropbox():
    """Trae la info logística desde Dropbox."""
    try:
        try:
            APP_KEY = st.secrets["dropbox"]["app_key"]
            APP_SECRET = st.secrets["dropbox"]["app_secret"]
            REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]
        except:
            return pd.DataFrame() 

        with dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN) as dbx:
            ruta = '/data/cartera_detalle.csv'
            metadata, res = dbx.files_download(path=ruta)
            contenido = res.content.decode('latin-1')
            
            cols = [
                'Serie', 'Numero', 'FechaDoc', 'FechaVenc', 'CodCliente',
                'NombreCliente', 'Nit', 'Poblacion', 'Provincia', 'Tel1', 'Tel2',
                'Vendedor', 'Entidad', 'Email', 'Importe', 'Descuento',
                'Cupo', 'DiasVencido'
            ]
            df_drop = pd.read_csv(io.StringIO(contenido), header=None, names=cols, sep='|', engine='python')
            
            # LIMPIEZA CLAVE PARA CRUCE (Usamos CodCliente o Nit)
            # Asumiremos que Columna H del Excel es el Codigo Cliente Interno o el Nit. 
            # Limpiamos ambos para asegurar cruce.
            df_drop['Key_Cliente'] = df_drop['CodCliente'].apply(limpiar_codigo_cliente)
            df_drop['Key_Nit'] = df_drop['Nit'].apply(limpiar_codigo_cliente)
            
            df_drop['Poblacion'] = df_drop['Poblacion'].apply(normalizar_texto)
            df_drop['Importe'] = pd.to_numeric(df_drop['Importe'], errors='coerce').fillna(0)
            df_drop['DiasVencido'] = pd.to_numeric(df_drop['DiasVencido'], errors='coerce').fillna(0)

            # Agrupar para tener registro único por Cliente
            def moda_poblacion(series):
                if series.empty: return None
                m = series.mode()
                return m[0] if not m.empty else series.iloc[0]

            # Agrupamos por Key_Cliente (que debe coincidir con Columna H)
            df_maestro = df_drop.groupby('Key_Cliente').agg({
                'Poblacion': moda_poblacion,
                'DiasVencido': 'max',        
                'Importe': 'sum',
                'NombreCliente': 'first'
            }).reset_index()
            
            df_maestro.rename(columns={
                'DiasVencido': 'Max_Dias_Mora_Cartera', 
                'Importe': 'Deuda_Total_Cartera',
                'Poblacion': 'Poblacion_Dropbox',
                'NombreCliente': 'Cliente_Dropbox'
            }, inplace=True)
            
            return df_maestro

    except Exception as e:
        st.error(f"Error conectando a Dropbox: {e}")
        return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO Y FUSIÓN (EL CEREBRO)
# ==============================================================================

if 'df_ventas' not in st.session_state:
    st.warning("⚠️ Por favor carga el archivo de ventas (CSV separado por |) en el inicio.")
    st.stop()

df_raw = st.session_state.df_ventas.copy()

# --- 4.1. MAPEO DE COLUMNAS POR POSICIÓN (CRUCIAL) ---
# Como el archivo no tiene headers confiables o pueden variar,
# vamos a renombrar las columnas basándonos en sus posiciones (A=0, B=1...).
# H = 7 (Código Cliente)
# K = 10 (Nombre Producto)
# L = 11 (Categoría/Ref)
# N = 13 (Código Marca)
# O = 14 (Valor Venta)
# A = 0 (Año)

# Verificamos que tenga suficientes columnas
if df_raw.shape[1] > 14:
    # Creamos un mapeo manual de las columnas críticas
    col_mapping = {
        df_raw.columns[0]: 'anio',
        df_raw.columns[7]: 'CODIGO_CLIENTE_H',    # Columna H
        df_raw.columns[10]: 'NOMBRE_PRODUCTO_K', # Columna K
        df_raw.columns[11]: 'CATEGORIA_L',       # Columna L
        df_raw.columns[13]: 'CODIGO_MARCA_N',    # Columna N
        df_raw.columns[14]: 'VALOR_VENTA_O'      # Columna O
    }
    df_raw = df_raw.rename(columns=col_mapping)
    
    # Limpieza de datos numéricos
    df_raw['VALOR_VENTA_O'] = pd.to_numeric(df_raw['VALOR_VENTA_O'], errors='coerce').fillna(0)
    # Si hay columna Margen (Q o similar), calcularla o estimarla
    # Asumiremos Margen = Venta por ahora si no hay datos de costo claros en la imagen
    df_raw['Margen_Pesos'] = df_raw['VALOR_VENTA_O'] * 0.25 # Estimado por seguridad, o restar costo si existe
    
else:
    st.error("El archivo cargado no tiene la estructura de columnas esperada (mínimo hasta columna O).")
    st.stop()

# --- 4.2. APLICAR CLASIFICACIÓN ---
df_raw['Marca_Master'] = df_raw.apply(clasificar_marca_ultra, axis=1)

# --- 4.3. FUSIÓN CON DROPBOX (POBLACIÓN) ---
# Limpiar la llave de cruce (Columna H)
df_raw['Key_Cliente'] = df_raw['CODIGO_CLIENTE_H'].apply(limpiar_codigo_cliente)

with st.spinner("🧠 Buscando poblaciones en Dropbox..."):
    df_logistica = cargar_datos_dropbox()

if not df_logistica.empty:
    # Left Join usando la Columna H limpia
    df_full = pd.merge(df_raw, df_logistica, on='Key_Cliente', how='left')
else:
    df_full = df_raw.copy()
    df_full['Poblacion_Dropbox'] = None
    df_full['Max_Dias_Mora_Cartera'] = 0
    df_full['Deuda_Total_Cartera'] = 0

# --- 4.4. DETERMINAR POBLACIÓN FINAL ---
def get_pob_final(row):
    # 1. Si Dropbox trajo población, usamos esa
    if pd.notnull(row.get('Poblacion_Dropbox')) and str(row.get('Poblacion_Dropbox')) != 'nan':
        return str(row.get('Poblacion_Dropbox'))
    # 2. Si no, intentar buscar en alguna columna de texto del archivo original (Fallback)
    # (Opcional, si hubiera columna ciudad en ventas, pero priorizamos Dropbox)
    return "SIN POBLACION (REVISAR COD H)"

df_full['Poblacion'] = df_full.apply(get_pob_final, axis=1)
df_full['Max_Dias_Mora_Cartera'] = df_full['Max_Dias_Mora_Cartera'].fillna(0)
df_full['Deuda_Total_Cartera'] = df_full['Deuda_Total_Cartera'].fillna(0)

# ==============================================================================
# 5. DASHBOARD VISUAL
# ==============================================================================

st.title("🧠 Master Brain Ultra: Análisis de Ventas")

# --- FILTROS ---
st.sidebar.header("Filtros")
anios = sorted(df_full['anio'].unique(), reverse=True)
anio_act = st.sidebar.selectbox("Año Actual", anios)
anio_base = st.sidebar.selectbox("Año Base (Comparativo)", [a for a in anios if a != anio_act] + ["Ninguno"])

marcas = sorted(df_full['Marca_Master'].unique())
if 'OTROS' in marcas: marcas.remove('OTROS'); marcas.append('OTROS')
sel_marcas = st.sidebar.multiselect("Marcas", marcas, default=marcas)

pobs = ["TODAS"] + sorted(df_full['Poblacion'].astype(str).unique())
sel_pob = st.sidebar.selectbox("Población", pobs)

# --- APLICAR FILTROS ---
df_fil = df_full[df_full['Marca_Master'].isin(sel_marcas)]
if sel_pob != "TODAS":
    df_fil = df_fil[df_fil['Poblacion'] == sel_pob]

df_now = df_fil[df_fil['anio'] == anio_act]
df_prev = df_fil[df_fil['anio'] == anio_base] if anio_base != "Ninguno" else pd.DataFrame()

# --- KPIs ---
vta_act = df_now['VALOR_VENTA_O'].sum()
vta_prev = df_prev['VALOR_VENTA_O'].sum() if not df_prev.empty else 0
crec = ((vta_act - vta_prev) / vta_prev * 100) if vta_prev > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("Venta Total", f"${vta_act:,.0f}", f"{crec:+.1f}%")
c2.metric("Clientes", df_now['Key_Cliente'].nunique())
c3.metric("Pedidos/Lineas", df_now.shape[0])

st.divider()

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 Crecimiento", "📍 Poblaciones", "🥧 Share", "⚠️ Riesgo"])

with tab1:
    if not df_prev.empty:
        # Waterfall
        g_act = df_now.groupby('Marca_Master')['VALOR_VENTA_O'].sum().reset_index(name='Venta_Act')
        g_prev = df_prev.groupby('Marca_Master')['VALOR_VENTA_O'].sum().reset_index(name='Venta_Prev')
        merged = pd.merge(g_act, g_prev, on='Marca_Master', how='outer').fillna(0)
        merged['Var'] = merged['Venta_Act'] - merged['Venta_Prev']
        merged = merged.sort_values('Var', ascending=False)
        
        fig = go.Figure(go.Waterfall(
            x=merged['Marca_Master'], y=merged['Var'],
            measure=["relative"]*len(merged),
            decreasing={"marker":{"color":"red"}},
            increasing={"marker":{"color":"green"}}
        ))
        fig.update_layout(title="Variación de Ventas por Marca ($)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Selecciona Año Base para ver comparativo.")

with tab2:
    # Logística
    df_log = df_now.groupby('Poblacion')['VALOR_VENTA_O'].sum().reset_index().sort_values('VALOR_VENTA_O', ascending=False)
    fig_bar = px.bar(df_log.head(20), x='Poblacion', y='VALOR_VENTA_O', color='VALOR_VENTA_O', title="Top Poblaciones")
    st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    # Share
    fig_tree = px.treemap(df_now, path=['Marca_Master', 'NOMBRE_PRODUCTO_K'], values='VALOR_VENTA_O', title="Portafolio")
    st.plotly_chart(fig_tree, use_container_width=True)

with tab4:
    # Riesgo
    df_risk = df_now.groupby(['Key_Cliente', 'Poblacion']).agg({
        'VALOR_VENTA_O': 'sum',
        'Max_Dias_Mora_Cartera': 'max',
        'Deuda_Total_Cartera': 'max'
    }).reset_index()
    df_risk = df_risk[df_risk['VALOR_VENTA_O'] > 0]
    
    fig_sc = px.scatter(
        df_risk, x='Max_Dias_Mora_Cartera', y='VALOR_VENTA_O', size='Deuda_Total_Cartera', color='Poblacion',
        title="Ventas vs Mora (Tamaño = Deuda Total)"
    )
    fig_sc.add_vline(x=60, line_dash="dash", line_color="red")
    st.plotly_chart(fig_sc, use_container_width=True)

# --- DEBUG ---
with st.expander("Verificar Datos Crudos (Primeras filas)"):
    st.write("Vista de columnas renombradas y clasificadas:")
    st.dataframe(df_full[['CODIGO_CLIENTE_H', 'NOMBRE_PRODUCTO_K', 'CODIGO_MARCA_N', 'Marca_Master', 'Poblacion']].head(10))
