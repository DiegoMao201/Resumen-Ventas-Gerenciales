import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import unicodedata
import io
import dropbox
from datetime import datetime

# ==============================================================================
# 1. CONFIGURACIÓN ULTRA (UI/UX)
# ==============================================================================
st.set_page_config(
    page_title="Master Brain Ultra | Strategic Intelligence", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Ejecutivo y Limpio
st.markdown("""
<style>
    /* Paleta de Colores Corporativa Premium */
    :root { --primary: #0f172a; --accent: #3b82f6; --success: #10b981; --danger: #ef4444; --bg-light: #f8fafc; }
    
    .main { background-color: #ffffff; }
    h1, h2, h3 { color: var(--primary); font-family: 'Segoe UI', sans-serif; font-weight: 700; }
    
    /* Tarjetas de Métricas Mejoradas */
    .metric-card {
        background: white;
        border-left: 4px solid var(--accent);
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        margin-bottom: 16px;
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(0,0,0,0.1); }
    .metric-val { font-size: 2.2rem; font-weight: 800; color: var(--primary); margin: 8px 0; }
    .metric-lbl { font-size: 0.85rem; color: #64748b; text-transform: uppercase; letter-spacing: 1.2px; font-weight: 600; }
    .metric-delta { font-size: 0.95rem; font-weight: 600; display: flex; align-items: center; gap: 4px; }
    .pos { color: var(--success); background-color: #ecfdf5; padding: 2px 8px; border-radius: 4px; }
    .neg { color: var(--danger); background-color: #fef2f2; padding: 2px 8px; border-radius: 4px; }

    /* Tabs Personalizados */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9;
        border-radius: 8px;
        padding: 10px 24px;
        border: none;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--primary);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MOTORES DE LIMPIEZA E INTELIGENCIA
# ==============================================================================

def normalizar_texto(texto):
    """Normalización robusta para ciudades y nombres."""
    if pd.isna(texto) or str(texto).strip() == "": return "SIN DEFINIR"
    texto = str(texto)
    # Eliminar tildes
    texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sin_tildes.upper().strip()

def limpiar_codigo_master(codigo):
    """
    FUNCIÓN CRÍTICA: Asegura que el código de cliente sea idéntico en ambas bases.
    Elimina decimales (.0) que Excel agrega automáticamente.
    """
    if pd.isna(codigo): return "0"
    s_cod = str(codigo).strip()
    
    if s_cod == "": return "0"
    
    # Si Excel lo leyó como float (ej: 900123.0), quitamos el .0
    try:
        if '.' in s_cod:
            # Convertir a float y luego int para quitar decimales
            s_cod = str(int(float(s_cod)))
    except:
        pass # Si falla, dejar como string original
    
    return s_cod

def obtener_nombre_marca_por_codigo(codigo):
    mapa = {
        '33': 'OCEANIC PAINTS', '34': 'PROTECTO', '35': 'OTROS', '37': 'INTERNATIONAL PAINT', 
        '40': 'ICO', '41': 'TERINSA', '50': 'PINTUCO (MEGA)', '54': 'INTERNATIONAL PAINT', 
        '55': 'COLORANTS LATAM', '56': 'PINTUCO PROFESIONAL', '57': 'PINTUCO (MEGA)', 
        '58': 'PINTUCO', '59': 'MADETEC', '60': 'INTERPON', '61': 'VARIOUS', '62': 'ICO', 
        '63': 'TERINSA', '64': 'PINTUCO', '65': 'TERCEROS', '66': 'ICO PACKAGING', 
        '67': 'AUTOMOTIVE OEM', '68': 'RESICOAT', '73': 'CORAL', '87': 'SIKKENS', 
        '89': 'WANDA', '90': 'SIKKENS AUTOCOAT', '91': 'SIKKENS', '94': 'PROTECTO PROFESIONAL'
    }
    return mapa.get(codigo, None)

def clasificar_estrategia_master(row):
    prod_name = normalizar_texto(row.get('NOMBRE_PRODUCTO_K', ''))
    cat_name = normalizar_texto(row.get('CATEGORIA_L', ''))
    aliados = ['ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', '3M', 'SISTA', 'SINTESOLDA']
    
    # Prioridad 1: Aliados en el nombre
    texto_busqueda = f"{prod_name} {cat_name}"
    for aliado in aliados:
        if aliado in texto_busqueda: return aliado

    # Prioridad 2: Código Marca
    raw_code = str(row.get('CODIGO_MARCA_N', '0')).split('.')[0].strip()
    nombre_marca = obtener_nombre_marca_por_codigo(raw_code)
    if nombre_marca: return nombre_marca

    return 'OTROS'

# ==============================================================================
# 3. CONEXIÓN DROPBOX (LECTURA EXACTA DE COLUMNAS)
# ==============================================================================
@st.cache_data(ttl=3600)
def cargar_poblaciones_dropbox_excel():
    """
    Lee clientes_detalle.xlsx desde Dropbox.
    Busca específicamente: 'Cod. Cliente' y 'CIUDAD'.
    """
    try:
        APP_KEY = st.secrets["dropbox"]["app_key"]
        APP_SECRET = st.secrets["dropbox"]["app_secret"]
        REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]

        with dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN) as dbx:
            # Rutas posibles
            rutas = ['/clientes_detalle.xlsx', '/data/clientes_detalle.xlsx', '/Master/clientes_detalle.xlsx']
            res = None
            for r in rutas:
                try:
                    _, res = dbx.files_download(path=r)
                    break
                except: continue
            
            if not res:
                st.error("❌ Archivo 'clientes_detalle.xlsx' no encontrado en Dropbox.")
                return pd.DataFrame()

            with io.BytesIO(res.content) as stream:
                df_drop = pd.read_excel(stream, engine='openpyxl')
            
            # --- VALIDACIÓN EXACTA DE COLUMNAS ---
            # Buscamos nombres exactos según tu indicación
            col_codigo = 'Cod. Cliente'
            col_ciudad = 'CIUDAD'
            col_vendedor = 'NOMVENDEDOR' # Opcional, pero útil

            # Verificar si existen (ignorando mayúsculas/minúsculas por seguridad)
            cols_actuales = {c.strip(): c for c in df_drop.columns}
            
            key_col_match = None
            city_col_match = None
            
            # Buscar Match para Código
            for c in cols_actuales:
                if c.lower() == col_codigo.lower():
                    key_col_match = cols_actuales[c]
                    break
            
            # Buscar Match para Ciudad
            for c in cols_actuales:
                if c.lower() == col_ciudad.lower():
                    city_col_match = cols_actuales[c]
                    break

            if not key_col_match:
                st.error(f"⚠️ No encontré la columna '{col_codigo}' en el Excel. Columnas disponibles: {list(cols_actuales.keys())}")
                return pd.DataFrame()

            # Selección y Limpieza
            df_final = df_drop.copy()
            
            # LIMPIEZA DE LA LLAVE MAESTRA (Excel suele traer floats)
            df_final['Key_Nit'] = df_final[key_col_match].apply(limpiar_codigo_master)
            
            # Seleccionar datos a exportar
            export_cols = ['Key_Nit']
            
            if city_col_match:
                df_final['Poblacion_Real'] = df_final[city_col_match].apply(normalizar_texto)
                export_cols.append('Poblacion_Real')
            else:
                df_final['Poblacion_Real'] = 'SIN ASIGNAR'
                export_cols.append('Poblacion_Real')

            # Si existe vendedor, lo traemos también
            vendedor_match = next((val for key, val in cols_actuales.items() if key.lower() == 'nomvendedor'), None)
            if vendedor_match:
                df_final['Vendedor'] = df_final[vendedor_match].apply(normalizar_texto)
                export_cols.append('Vendedor')

            # Eliminar duplicados de la llave para evitar error de multiplicidad
            return df_final.drop_duplicates(subset=['Key_Nit'])[export_cols]

    except Exception as e:
        st.error(f"Error crítico conexión Dropbox: {str(e)}")
        return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO DE VENTAS (CSV SIN CABECERA)
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.info("👋 Por favor carga el archivo maestro de ventas (CSV separado por |) en el Home.")
    st.stop()

# Copia fresca
df_raw = st.session_state.df_ventas.copy()

# --- MAPEO POR POSICIÓN (INDICES) ---
# Como el CSV no tiene cabeceras o son raras, usamos iloc para asegurar.
# Columna 0 = Año, 1 = Mes, 7 (H) = Cod Cliente, etc.
try:
    # Aseguramos nombres internos consistentes
    df_raw = df_raw.rename(columns={
        df_raw.columns[0]: 'anio',
        df_raw.columns[1]: 'mes',
        df_raw.columns[7]: 'CODIGO_CLIENTE_H', # La clave H
        df_raw.columns[8]: 'NOMBRE_CLIENTE_I',
        df_raw.columns[10]: 'NOMBRE_PRODUCTO_K',
        df_raw.columns[11]: 'CATEGORIA_L',
        df_raw.columns[13]: 'CODIGO_MARCA_N',
        df_raw.columns[14]: 'VALOR_VENTA_O'
    })
except Exception as e:
    st.error(f"Error mapeando columnas del CSV. Verifica que tenga al menos 15 columnas separadas por |. Detalle: {e}")
    st.stop()

# Conversiones de tipos básicas
df_raw['VALOR_VENTA_O'] = pd.to_numeric(df_raw['VALOR_VENTA_O'], errors='coerce').fillna(0)
df_raw['anio'] = pd.to_numeric(df_raw['anio'], errors='coerce').fillna(datetime.now().year).astype(int)
df_raw['mes'] = pd.to_numeric(df_raw['mes'], errors='coerce').fillna(1).astype(int)

# --- LIMPIEZA CLAVE PARA EL CRUCE ---
# Aplicamos la MISMA limpieza que al Excel
df_raw['Key_Nit'] = df_raw['CODIGO_CLIENTE_H'].apply(limpiar_codigo_master)

# Clasificación Estratégica
with st.spinner("⚙️ Cruzando bases de datos y geolocalizando..."):
    df_raw['Marca_Master'] = df_raw.apply(clasificar_estrategia_master, axis=1)
    
    # Cargar Datos Dropbox
    df_clientes = cargar_poblaciones_dropbox_excel()
    
    if not df_clientes.empty:
        # MERGE LEFT: Unimos Ventas (Izquierda) con Clientes (Derecha) usando Key_Nit
        df_full = pd.merge(df_raw, df_clientes, on='Key_Nit', how='left')
        
        # Relleno de nulos post-cruce
        df_full['Poblacion_Real'] = df_full['Poblacion_Real'].fillna('NO IDENTIFICADO')
        if 'Vendedor' not in df_full.columns:
            df_full['Vendedor'] = 'GENERAL'
        else:
            df_full['Vendedor'] = df_full['Vendedor'].fillna('GENERAL')
            
    else:
        st.warning("⚠️ No se pudo cruzar con Dropbox. Usando datos crudos.")
        df_full = df_raw.copy()
        df_full['Poblacion_Real'] = 'SIN DATA'
        df_full['Vendedor'] = 'GENERAL'

# ==============================================================================
# 5. DASHBOARD "ULTRA"
# ==============================================================================

st.title("🧠 Master Brain Ultra")
st.markdown("**Sistema Avanzado de Inteligencia Comercial** | _Data Fusion Engine_")
st.divider()

# --- SIDEBAR GLOBAL ---
with st.sidebar:
    st.header("🎛️ Centro de Control")
    
    # Filtro Fechas
    anios = sorted(df_full['anio'].unique(), reverse=True)
    c_s1, c_s2 = st.columns(2)
    if len(anios) > 0:
        anio_obj = c_s1.selectbox("Año Objetivo", anios, index=0)
        list_base = [a for a in anios if a != anio_obj]
        anio_base = c_s2.selectbox("Año Base", list_base if list_base else anios, index=0)
    else:
        st.error("No hay datos de años.")
        st.stop()
    
    st.markdown("---")
    st.caption("FILTROS DE SEGMENTACIÓN")
    
    # Filtros dinámicos
    all_brands = sorted(df_full['Marca_Master'].astype(str).unique())
    sel_brands = st.multiselect("Marcas", all_brands, default=all_brands, placeholder="Todas las marcas")
    
    # Filtro Ciudad (Ahora sí debería funcionar)
    all_cities = sorted(df_full['Poblacion_Real'].astype(str).unique())
    sel_city = st.multiselect("Poblaciones (Geo)", all_cities, placeholder="Todas las zonas")
    
    # Debugger (Para que verifiques que funcionó)
    with st.expander("🛠️ Verificación de Cruce"):
        st.write(f"Registros Ventas: {len(df_raw):,}")
        st.write(f"Registros Clientes (Dropbox): {len(df_clientes):,}")
        n_match = df_full[df_full['Poblacion_Real'] != 'NO IDENTIFICADO'].shape[0]
        st.write(f"Registros Cruzados OK: {n_match:,} ({n_match/len(df_full):.1%})")
        st.write("Muestra de Keys en Ventas:", df_raw['Key_Nit'].head(3).values)
        if not df_clientes.empty:
            st.write("Muestra de Keys en Clientes:", df_clientes['Key_Nit'].head(3).values)

# --- FILTRADO MAESTRO ---
df_f = df_full.copy()
if sel_brands: df_f = df_f[df_f['Marca_Master'].isin(sel_brands)]
if sel_city: df_f = df_f[df_f['Poblacion_Real'].isin(sel_city)]

# Dataframes Año Actual vs Anterior
df_act = df_f[df_f['anio'] == anio_obj]
df_ant = df_f[df_f['anio'] == anio_base]

# --- KPI HEADER ---
vta_act = df_act['VALOR_VENTA_O'].sum()
vta_ant = df_ant['VALOR_VENTA_O'].sum()
diff_abs = vta_act - vta_ant
diff_pct = (diff_abs / vta_ant * 100) if vta_ant > 0 else 100

cli_act = df_act[df_act['VALOR_VENTA_O']>0]['Key_Nit'].nunique()
cli_ant = df_ant[df_ant['VALOR_VENTA_O']>0]['Key_Nit'].nunique()
diff_cli = cli_act - cli_ant

c1, c2, c3, c4 = st.columns(4)

def kpi_card(col, title, val, delta, prefix="$", is_currency=True):
    color = "pos" if delta >= 0 else "neg"
    delta_str = f"{delta:+.1f}%" if is_currency else f"{delta:+.0f}"
    symbol = "▲" if delta >= 0 else "▼"
    val_fmt = f"{prefix}{val/1e6:,.1f}M" if is_currency and val > 1e6 else f"{prefix}{val:,.0f}"
    
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">{title}</div>
        <div class="metric-val">{val_fmt}</div>
        <div class="metric-delta"><span class="{color}">{symbol} {delta_str}</span> <span style="color:#94a3b8; font-size:0.8rem; margin-left:5px;">vs AA</span></div>
    </div>
    """, unsafe_allow_html=True)

kpi_card(c1, "Venta Total", vta_act, diff_pct, "$", True)
kpi_card(c2, "Variación Neta", diff_abs, diff_pct, "$", True)
kpi_card(c3, "Clientes Activos", cli_act, diff_cli, "", False)
ticket = vta_act / cli_act if cli_act > 0 else 0
kpi_card(c4, "Ticket Promedio", ticket, (ticket/(vta_ant/cli_ant if cli_ant else 1)-1)*100, "$", False)

# --- TABS DE ANÁLISIS ---
tabs = st.tabs([
    "📈 Drivers & Waterfall", 
    "👥 Inteligencia de Clientes", 
    "🌍 Geo-Analytics",
    "🔎 Data Explorer"
])

# --- TAB 1: WATERFALL ---
with tabs[0]:
    c_w1, c_w2 = st.columns([3, 1])
    with c_w1:
        st.subheader(f"Análisis de Variación")
        dim_view = st.radio("Dimensionar por:", ["Marca_Master", "CATEGORIA_L", "Vendedor"], horizontal=True, key="w_radio")
        
        g_act = df_act.groupby(dim_view)['VALOR_VENTA_O'].sum()
        g_ant = df_ant.groupby(dim_view)['VALOR_VENTA_O'].sum()
        df_w = pd.DataFrame({'Actual': g_act, 'Anterior': g_ant}).fillna(0)
        df_w['Variacion'] = df_w['Actual'] - df_w['Anterior']
        df_w = df_w.sort_values('Variacion', ascending=False)
        
        top_positive = df_w[df_w['Variacion'] > 0].head(7)
        top_negative = df_w[df_w['Variacion'] < 0].tail(7)
        df_chart = pd.concat([top_positive, top_negative]).sort_values('Variacion', ascending=False)
        
        fig_water = go.Figure(go.Waterfall(
            orientation="v", measure=["relative"] * len(df_chart),
            x=df_chart.index, y=df_chart['Variacion'],
            text=df_chart['Variacion'].apply(lambda x: f'{x/1e6:+.1f}M'),
            textposition="outside",
            decreasing={"marker":{"color":"#ef4444"}}, increasing={"marker":{"color":"#10b981"}}
        ))
        fig_water.update_layout(title=f"Puente de Ventas por {dim_view}", height=450, plot_bgcolor="white")
        st.plotly_chart(fig_water, use_container_width=True)
    
    with c_w2:
        st.markdown("### Detalle Top Movers")
        st.dataframe(df_w[['Variacion']].style.format("${:,.0f}").background_gradient(cmap='RdYlGn'), use_container_width=True)

# --- TAB 2: CLIENTES (CHURN) ---
with tabs[1]:
    st.subheader("Salud de Cartera (Retención vs Fuga)")
    cli_set_act = set(df_act[df_act['VALOR_VENTA_O']>0]['Key_Nit'])
    cli_set_ant = set(df_ant[df_ant['VALOR_VENTA_O']>0]['Key_Nit'])
    
    retained = cli_set_act.intersection(cli_set_ant)
    lost = cli_set_ant - cli_set_act
    new = cli_set_act - cli_set_ant
    
    c_ch1, c_ch2, c_ch3 = st.columns(3)
    c_ch1.metric("Retenidos", len(retained))
    c_ch2.metric("Nuevos", len(new), f"+{len(new)}")
    c_ch3.metric("Perdidos", len(lost), f"-{len(lost)}", delta_color="inverse")
    
    st.markdown("---")
    col_lost_1, col_lost_2 = st.columns(2)
    with col_lost_1:
        st.markdown("**Top Clientes Perdidos (Mayor Impacto)**")
        lost_detail = df_ant[df_ant['Key_Nit'].isin(lost)].groupby(['NOMBRE_CLIENTE_I', 'Poblacion_Real'])['VALOR_VENTA_O'].sum().sort_values(ascending=False).head(10)
        st.dataframe(lost_detail.to_frame().style.format("${:,.0f}"), use_container_width=True)

# --- TAB 3: GEO ANALYTICS ---
with tabs[2]:
    st.subheader("📍 Distribución Geográfica (Por Ciudad Real)")
    
    if df_full['Poblacion_Real'].nunique() <= 1:
        st.warning("⚠️ No se detectaron múltiples poblaciones. Verifica la pestaña 'Data Explorer' o el Debugger en el Sidebar.")
    
    col_g1, col_g2 = st.columns([2, 1])
    
    # Agrupación Geo
    df_geo = df_act.groupby('Poblacion_Real').agg(
        Venta=('VALOR_VENTA_O', 'sum'),
        Clientes=('Key_Nit', 'nunique')
    ).reset_index()
    df_geo['Ticket'] = df_geo['Venta'] / df_geo['Clientes']
    df_geo = df_geo[df_geo['Venta'] > 0].sort_values('Venta', ascending=False)
    
    with col_g1:
        fig_geo = px.scatter(
            df_geo, x="Clientes", y="Ticket",
            size="Venta", color="Venta",
            hover_name="Poblacion_Real",
            title="Matriz Ciudad: Volumen vs Ticket",
            color_continuous_scale="Viridis",
            size_max=60
        )
        st.plotly_chart(fig_geo, use_container_width=True)
        
    with col_g2:
        st.markdown("**Ranking Ciudades**")
        st.dataframe(df_geo[['Poblacion_Real', 'Venta']].style.format({'Venta': '${:,.0f}'}).background_gradient(cmap="Blues"), use_container_width=True, hide_index=True)

# --- TAB 4: EXPLORER ---
with tabs[3]:
    st.subheader("🔎 Datos Maestros Integrados")
    search_txt = st.text_input("Buscar (Cliente, NIT, Ciudad):")
    
    cols_view = ['anio', 'mes', 'Key_Nit', 'NOMBRE_CLIENTE_I', 'Poblacion_Real', 'Vendedor', 'Marca_Master', 'VALOR_VENTA_O']
    df_view = df_act[cols_view].copy()
    
    if search_txt:
        mask = df_view.astype(str).apply(lambda x: x.str.contains(search_txt, case=False)).any(axis=1)
        df_view = df_view[mask]
        
    st.dataframe(
        df_view.sort_values('VALOR_VENTA_O', ascending=False).head(500)
        .style.format({'VALOR_VENTA_O': '${:,.2f}'}),
        use_container_width=True
    )
