import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import unicodedata
import io
import dropbox
from datetime import datetime, date

# ==============================================================================
# 1. CONFIGURACIÓN ULTRA (UI/UX)
# ==============================================================================
st.set_page_config(
    page_title="Master Brain Ultra | Growth Engine", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Ejecutivo y Limpio
st.markdown("""
<style>
    :root { --primary: #0f172a; --accent: #3b82f6; --success: #10b981; --danger: #ef4444; --bg-light: #f8fafc; }
    .main { background-color: #ffffff; }
    h1, h2, h3 { color: var(--primary); font-family: 'Segoe UI', sans-serif; font-weight: 700; }
    
    /* Tarjetas KPI */
    .metric-card {
        background: white; border-left: 4px solid var(--accent);
        padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); margin-bottom: 16px;
    }
    .metric-val { font-size: 1.8rem; font-weight: 800; color: var(--primary); margin: 8px 0; }
    .metric-lbl { font-size: 0.8rem; color: #64748b; text-transform: uppercase; font-weight: 700; letter-spacing: 1px;}
    .metric-delta { font-size: 0.9rem; font-weight: 600; }
    .pos { color: var(--success); background-color: #ecfdf5; padding: 2px 6px; border-radius: 4px;}
    .neg { color: var(--danger); background-color: #fef2f2; padding: 2px 6px; border-radius: 4px;}

    /* Cajas de Análisis */
    .insight-box {
        background-color: #eff6ff; border: 1px solid #bfdbfe;
        padding: 20px; border-radius: 10px; color: #1e40af; margin-bottom: 20px;
    }
    .insight-title { font-weight: 800; display: block; margin-bottom: 5px; text-transform: uppercase; font-size: 0.85rem;}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 8px; padding: 10px 20px; border: none; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: var(--primary); color: white; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. LÓGICA DE NEGOCIO Y LIMPIEZA
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

def obtener_nombre_marca_por_codigo(codigo):
    # --- TU DICCIONARIO PERSONALIZADO ---
    mapa = {
        '33': 'OCEANIC PAINTS', '34': 'PROTECTO', '35': 'OTROS', '37': 'INTERNATIONAL PAINT', 
        '40': 'ICO', '41': 'TERINSA', '50': 'PINTUCO (MEGA)', '54': 'INTERNATIONAL PAINT', 
        '55': 'COLORANTS LATAM', '56': 'PINTUCO PROFESIONAL', '57': 'PINTUCO (MEGA)', 
        '58': 'PINTUCO', '59': 'MADETEC', '60': 'INTERPON', '61': 'VARIOUS', '62': 'ICO', 
        '63': 'TERINSA', '64': 'PINTUCO', '65': 'TERCEROS', '66': 'ICO PACKAGING', 
        '67': 'AUTOMOTIVE OEM', '68': 'RESICOAT', '73': 'CORAL', '87': 'SIKKENS', 
        '89': 'WANDA', '90': 'SIKKENS AUTOCOAT', '91': 'SIKKENS', '94': 'PROTECTO PROFESIONAL'
    }
    return mapa.get(str(codigo), None)

def clasificar_estrategia_master(row):
    prod_name = normalizar_texto(row.get('NOMBRE_PRODUCTO_K', ''))
    cat_name = normalizar_texto(row.get('CATEGORIA_L', ''))
    
    # 1. Busqueda por Aliados en el texto
    aliados = ['ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', '3M', 'SISTA', 'SINTESOLDA']
    texto_busqueda = f"{prod_name} {cat_name}"
    for aliado in aliados:
        if aliado in texto_busqueda: return aliado
    
    # 2. Busqueda por Codigo de Marca
    raw_code = str(row.get('CODIGO_MARCA_N', '0')).split('.')[0].strip()
    nombre_marca = obtener_nombre_marca_por_codigo(raw_code)
    if nombre_marca: return nombre_marca
    
    return 'OTROS / GENERICO'

def asignar_hub_logistico(ciudad):
    c = normalizar_texto(ciudad)
    # Risaralda
    if c in ['PEREIRA', 'DOSQUEBRADAS', 'SANTA ROSA DE CABAL', 'LA VIRGINIA']: return 'HUB RISARALDA'
    # Caldas
    if c in ['MANIZALES', 'VILLAMARIA', 'CHINCHINA', 'NEIRA']: return 'HUB CALDAS'
    # Quindio
    if c in ['ARMENIA', 'CALARCA', 'CIRCASIA', 'TEBAIDA', 'MONTENEGRO', 'QUIMBAYA']: return 'HUB QUINDIO'
    # Valle Norte y Otros
    if c in ['CARTAGO', 'ANSERMA', 'RIOSUCIO', 'VITERBO']: return 'ZONA CERCANA'
    # Resto
    return 'NACIONAL / FORANEO'

# ==============================================================================
# 3. DATA LOADING (DROPBOX)
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
                df_drop = pd.read_excel(stream, engine='openpyxl')
            
            cols_actuales = {c.strip(): c for c in df_drop.columns}
            key_col_match = next((val for key, val in cols_actuales.items() if 'cod' in key.lower() and 'cli' in key.lower()), None)
            city_col_match = next((val for key, val in cols_actuales.items() if 'ciudad' in key.lower()), None)
            vendedor_match = next((val for key, val in cols_actuales.items() if 'vendedor' in key.lower()), None)

            if not key_col_match: return pd.DataFrame()

            df_final = df_drop.copy()
            df_final['Key_Nit'] = df_final[key_col_match].apply(limpiar_codigo_master)
            
            if city_col_match:
                df_final['Poblacion_Real'] = df_final[city_col_match].apply(normalizar_texto)
            else:
                df_final['Poblacion_Real'] = 'SIN ASIGNAR'

            df_final['Hub_Logistico'] = df_final['Poblacion_Real'].apply(asignar_hub_logistico)
            
            if vendedor_match:
                df_final['Vendedor'] = df_final[vendedor_match].apply(normalizar_texto)
            else:
                df_final['Vendedor'] = 'GENERAL'
                
            return df_final.drop_duplicates(subset=['Key_Nit'])[['Key_Nit', 'Poblacion_Real', 'Hub_Logistico', 'Vendedor']]

    except Exception as e:
        # st.error(f"Dropbox Error: {e}") # Ocultar en producción si se desea
        return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO MAESTRO (YTD)
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.info("👋 Carga tu archivo maestro en el Home.")
    st.stop()

df_raw = st.session_state.df_ventas.copy()

# Mapeo de Columnas
try:
    df_raw = df_raw.rename(columns={
        df_raw.columns[0]: 'anio',
        df_raw.columns[1]: 'mes',
        df_raw.columns[7]: 'CODIGO_CLIENTE_H',
        df_raw.columns[8]: 'NOMBRE_CLIENTE_I',
        df_raw.columns[10]: 'NOMBRE_PRODUCTO_K',
        df_raw.columns[11]: 'CATEGORIA_L',
        df_raw.columns[13]: 'CODIGO_MARCA_N',
        df_raw.columns[14]: 'VALOR_VENTA_O'
    })
    # Verificar si hay columna día
    if len(df_raw.columns) > 2:
        if df_raw.iloc[:, 2].apply(lambda x: str(x).isnumeric()).all():
             df_raw['dia'] = df_raw.iloc[:, 2].astype(int)
        else: df_raw['dia'] = 15
    else: df_raw['dia'] = 15
except:
    st.error("Error en estructura de archivo.")
    st.stop()

df_raw['VALOR_VENTA_O'] = pd.to_numeric(df_raw['VALOR_VENTA_O'], errors='coerce').fillna(0)
df_raw['anio'] = pd.to_numeric(df_raw['anio'], errors='coerce').fillna(datetime.now().year).astype(int)
df_raw['mes'] = pd.to_numeric(df_raw['mes'], errors='coerce').fillna(1).astype(int)
df_raw['Key_Nit'] = df_raw['CODIGO_CLIENTE_H'].apply(limpiar_codigo_master)

# Fusión de Datos
with st.spinner("⚙️ Master Brain procesando datos..."):
    df_raw['Marca_Master'] = df_raw.apply(clasificar_estrategia_master, axis=1)
    df_clientes = cargar_poblaciones_dropbox_excel()
    
    if not df_clientes.empty:
        df_full = pd.merge(df_raw, df_clientes, on='Key_Nit', how='left')
        df_full['Poblacion_Real'] = df_full['Poblacion_Real'].fillna('NO IDENTIFICADO')
        df_full['Hub_Logistico'] = df_full['Hub_Logistico'].fillna('NACIONAL / FORANEO')
        df_full['Vendedor'] = df_full['Vendedor'].fillna('GENERAL')
    else:
        df_full = df_raw.copy()
        df_full['Poblacion_Real'] = 'SIN DATA'
        df_full['Hub_Logistico'] = 'NACIONAL / FORANEO'
        df_full['Vendedor'] = 'GENERAL'

# Filtro YTD Estricto
today = date.today()
def es_ytd_valido(row):
    if row['mes'] < today.month: return True
    if row['mes'] == today.month: return row['dia'] <= today.day
    return False

df_full['Is_YTD'] = df_full.apply(es_ytd_valido, axis=1)
df_master = df_full[df_full['Is_YTD'] == True].copy()

# ==============================================================================
# 5. INTERFAZ Y DASHBOARD
# ==============================================================================

st.title("🧠 Master Brain | Análisis de Crecimiento & Rentabilidad")
st.markdown(f"Comparativo YTD Estricto al **{today.strftime('%d de %B')}**.")
st.divider()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Filtros Globales")
    
    # Fechas
    anios = sorted(df_master['anio'].unique(), reverse=True)
    anio_obj = st.selectbox("Año Objetivo (Actual)", anios, index=0)
    list_base = [a for a in anios if a != anio_obj]
    anio_base = st.selectbox("Año Base (Anterior)", list_base if list_base else anios, index=0)
    
    st.markdown("---")
    st.subheader("Segmentación")
    
    # Filtros Anidados
    hubs = sorted(df_master['Hub_Logistico'].unique())
    sel_hubs = st.multiselect("Hubs Logísticos", hubs, default=hubs)
    
    # Filtrar df para obtener opciones dependientes
    df_temp = df_master[df_master['Hub_Logistico'].isin(sel_hubs)]
    
    ciudades = sorted(df_temp['Poblacion_Real'].unique())
    sel_city = st.multiselect("Ciudades", ciudades)
    
    categorias = sorted(df_temp['CATEGORIA_L'].astype(str).unique())
    sel_cat = st.multiselect("Categorías", categorias)
    
    marcas = sorted(df_temp['Marca_Master'].unique())
    sel_brand = st.multiselect("Marcas", marcas)
    
    st.markdown("---")
    st.caption("PARAMETROS FINANCIEROS")
    margen_bruto = st.slider("Margen Bruto (%)", 10, 60, 25) / 100
    costo_local = st.number_input("Costo Local ($)", 12000)
    costo_nal = st.number_input("Costo Nacional ($)", 45000)

# --- APLICACIÓN DE FILTROS ---
df_f = df_master[df_master['Hub_Logistico'].isin(sel_hubs)].copy()
if sel_city: df_f = df_f[df_f['Poblacion_Real'].isin(sel_city)]
if sel_cat: df_f = df_f[df_f['CATEGORIA_L'].isin(sel_cat)]
if sel_brand: df_f = df_f[df_f['Marca_Master'].isin(sel_brand)]

df_act = df_f[df_f['anio'] == anio_obj].copy()
df_ant = df_f[df_f['anio'] == anio_base].copy()

# --- CÁLCULOS GLOBALES ---
vta_act = df_act['VALOR_VENTA_O'].sum()
vta_ant = df_ant['VALOR_VENTA_O'].sum()
diff_vta = vta_act - vta_ant
diff_pct = (diff_vta / vta_ant * 100) if vta_ant > 0 else 100

# Cálculo de Costo Logístico Estimado (Para rentabilidad)
df_act['Pedido_ID'] = df_act['Key_Nit'].astype(str) + '-' + df_act['mes'].astype(str) + '-' + df_act['dia'].astype(str)
df_pedidos = df_act[['Pedido_ID', 'Hub_Logistico']].drop_duplicates()

def calcular_costo_row(h):
    if 'RISARALDA' in h or 'CALDAS' in h or 'QUINDIO' in h or 'CERCANA' in h: return costo_local
    return costo_nal

df_pedidos['Costo'] = df_pedidos['Hub_Logistico'].apply(calcular_costo_row)
costo_total = df_pedidos['Costo'].sum()
utilidad = (vta_act * margen_bruto) - costo_total
margen_neto = (utilidad / vta_act * 100) if vta_act > 0 else 0

# --- KPI CARDS ---
c1, c2, c3, c4, c5 = st.columns(5)

def kpi(col, title, val, delta, sub, color="pos"):
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">{title}</div>
        <div class="metric-val">{val}</div>
        <div class="metric-delta"><span class="{color}">{delta}</span> {sub}</div>
    </div>""", unsafe_allow_html=True)

kpi(c1, "Venta Actual", f"${vta_act/1e6:,.1f}M", f"{diff_pct:+.1f}%", "vs Año Ant")
kpi(c2, "Variación $", f"${diff_vta/1e6:,.1f}M", "Crecimiento", "Neto")
kpi(c3, "Utilidad Real", f"${utilidad/1e6:,.1f}M", f"{margen_neto:.1f}%", "Margen Operativo")
kpi(c4, "Gasto Logístico", f"${costo_total/1e6:,.1f}M", f"{(costo_total/vta_act)*100:.1f}%", "del Ingreso", "neg")
kpi(c5, "Clientes Activos", f"{df_act['Key_Nit'].nunique()}", f"{df_act['Key_Nit'].nunique() - df_ant['Key_Nit'].nunique():+}", "vs Año Ant")

# --- ESTRUCTURA DE PESTAÑAS ---
tabs = st.tabs([
    "🚀 Drivers de Crecimiento", 
    "⚖️ Mix & Categorías",
    "🚚 Rentabilidad & Costos", 
    "🌍 Mapa de Expansión",
    "👥 Retención de Clientes",
    "🧪 Simulador Batching"
])

# ==============================================================================
# TAB 1: DRIVERS DE CRECIMIENTO (WATERFALL & INCIDENCIA)
# ==============================================================================
with tabs[0]:
    st.subheader("¿Quién está aportando el crecimiento?")
    st.markdown("Este análisis desglosa la variación de ventas para identificar exactamente qué Marcas o Categorías son responsables del resultado.")

    col_d1, col_d2 = st.columns([3, 1])
    
    with col_d1:
        dimension = st.radio("Analizar Crecimiento por:", ["Marca_Master", "CATEGORIA_L"], horizontal=True)
        
        # Agrupación
        g_act = df_act.groupby(dimension)['VALOR_VENTA_O'].sum()
        g_ant = df_ant.groupby(dimension)['VALOR_VENTA_O'].sum()
        
        df_growth = pd.DataFrame({'Actual': g_act, 'Anterior': g_ant}).fillna(0)
        df_growth['Variacion'] = df_growth['Actual'] - df_growth['Anterior']
        df_growth['Crecimiento_Pct'] = (df_growth['Variacion'] / df_growth['Anterior']).replace([np.inf, -np.inf], 0)
        
        # Incidencia: Cuánto pesa esta variación sobre la variación TOTAL absoluta
        total_var_abs = abs(df_growth['Variacion'].sum())
        df_growth['Incidencia'] = df_growth['Variacion'] / total_var_abs if total_var_abs > 0 else 0
        
        df_growth = df_growth.sort_values('Variacion', ascending=False)
        
        # Gráfico Waterfall
        fig_water = go.Figure(go.Waterfall(
            orientation="v",
            measure=["relative"] * len(df_growth),
            x=df_growth.index,
            y=df_growth['Variacion'],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#ef4444"}},
            increasing={"marker": {"color": "#10b981"}},
        ))
        fig_water.update_layout(title=f"Cascada de Crecimiento por {dimension}", height=500)
        st.plotly_chart(fig_water, use_container_width=True)

    with col_d2:
        st.markdown(f"**Top Drivers ({dimension})**")
        st.caption("Ordenado por aporte en Dinero ($)")
        
        display_cols = df_growth[['Actual', 'Variacion', 'Crecimiento_Pct']]
        st.dataframe(
            display_cols.style.format({
                'Actual': '${:,.0f}', 
                'Variacion': '${:,.0f}', 
                'Crecimiento_Pct': '{:+.1%}'
            }).background_gradient(cmap='RdYlGn', subset=['Variacion']),
            use_container_width=True,
            height=500
        )

# ==============================================================================
# TAB 2: MIX & CATEGORIAS
# ==============================================================================
with tabs[1]:
    st.subheader("Evolución del Mix de Venta")
    
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        fig_sun = px.sunburst(
            df_act, 
            path=['Marca_Master', 'CATEGORIA_L'], 
            values='VALOR_VENTA_O',
            title=f"Distribución de Venta {anio_obj}",
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        st.plotly_chart(fig_sun, use_container_width=True)
        
    with col_m2:
        # Comparativo de Share
        share_act = df_act.groupby('CATEGORIA_L')['VALOR_VENTA_O'].sum() / vta_act
        share_ant = df_ant.groupby('CATEGORIA_L')['VALOR_VENTA_O'].sum() / vta_ant
        
        df_share = pd.DataFrame({'Share_Act': share_act, 'Share_Ant': share_ant}).fillna(0)
        df_share['Cambio_Puntos'] = (df_share['Share_Act'] - df_share['Share_Ant']) * 100
        df_share = df_share.sort_values('Share_Act', ascending=False)
        
        st.markdown("**Cambio en la Participación (Share of Pocket)**")
        st.dataframe(
            df_share.style.format("{:.2f}%").background_gradient(cmap='RdYlGn', subset=['Cambio_Puntos']),
            use_container_width=True
        )

# ==============================================================================
# TAB 3: RENTABILIDAD (COST TO SERVE)
# ==============================================================================
with tabs[2]:
    st.subheader("Matriz de Eficiencia Operativa")
    st.markdown("Relación entre el Costo Logístico Total y la Utilidad Generada por población.")
    
    # Preparar datos por Ciudad
    df_city_ops = df_act.groupby(['Poblacion_Real', 'Hub_Logistico']).agg(
        Venta=('VALOR_VENTA_O', 'sum'),
        Pedidos=('Pedido_ID', 'nunique')
    ).reset_index()
    
    # Aplicar costos
    df_city_ops['Costo_Unit'] = df_city_ops['Hub_Logistico'].apply(calcular_costo_row)
    df_city_ops['Costo_Total'] = df_city_ops['Pedidos'] * df_city_ops['Costo_Unit']
    df_city_ops['Utilidad'] = (df_city_ops['Venta'] * margen_bruto) - df_city_ops['Costo_Total']
    
    col_r1, col_r2 = st.columns([2,1])
    
    with col_r1:
        fig_scatter = px.scatter(
            df_city_ops,
            x="Costo_Total", y="Utilidad",
            size="Venta", color="Hub_Logistico",
            hover_name="Poblacion_Real",
            title="Utilidad vs. Costo Logístico (Tamaño burbuja = Venta)",
            height=500
        )
        # Linea de equilibrio
        fig_scatter.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Punto de Equilibrio")
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    with col_r2:
        st.markdown("**🚨 Ciudades Críticas (Menor Utilidad)**")
        st.dataframe(
            df_city_ops.sort_values('Utilidad').head(10)[['Poblacion_Real', 'Venta', 'Utilidad']]
            .style.format("${:,.0f}").background_gradient(cmap='RdYlGn', subset=['Utilidad']),
            use_container_width=True
        )

# ==============================================================================
# TAB 4: MAPA DE EXPANSION (CORREGIDO)
# ==============================================================================
with tabs[3]:
    st.subheader("Mapa Territorial de Crecimiento")
    st.markdown("El tamaño representa la Venta Actual. El color representa el **Crecimiento %** (Verde = Creciendo, Rojo = Cayendo).")
    
    # Preparar Datos para Treemap con la corrección del TypeError
    df_map = df_city_ops.copy()
    
    # Traer venta anterior para calcular crecimiento por ciudad
    df_map_ant = df_ant.groupby('Poblacion_Real')['VALOR_VENTA_O'].sum().reset_index().rename(columns={'VALOR_VENTA_O': 'Venta_Ant'})
    df_map = pd.merge(df_map, df_map_ant, on='Poblacion_Real', how='left').fillna(0)
    df_map['Crecimiento'] = df_map['Venta'] - df_map['Venta_Ant']
    df_map['Crecimiento_Pct'] = (df_map['Crecimiento'] / df_map['Venta_Ant']).replace([np.inf, -np.inf], 0)
    
    # --- CORRECCIÓN CLAVE PARA TYPEERROR ---
    # En lugar de px.Constant en el path, creamos una columna real
    df_map['Pais'] = 'COLOMBIA' 
    
    # Filtramos ventas cero para limpiar el gráfico
    df_map = df_map[df_map['Venta'] > 0]
    
    fig_tree = px.treemap(
        df_map,
        path=['Pais', 'Hub_Logistico', 'Poblacion_Real'], # Usamos la columna 'Pais'
        values='Venta',
        color='Crecimiento_Pct',
        color_continuous_scale='RdYlGn',
        midpoint=0,
        custom_data=['Crecimiento', 'Utilidad']
    )
    
    fig_tree.update_traces(hovertemplate='<b>%{label}</b><br>Venta: %{value:$,.0f}<br>Crecimiento: %{color:.1%}<br>Utilidad: %{customdata[1]:$,.0f}')
    st.plotly_chart(fig_tree, use_container_width=True, height=600)

# ==============================================================================
# TAB 5: RETENCIÓN
# ==============================================================================
with tabs[4]:
    st.subheader("Análisis de Fuga (Churn) y Nuevos Clientes")
    
    cli_act = set(df_act['Key_Nit'])
    cli_ant = set(df_ant['Key_Nit'])
    
    lost = cli_ant - cli_act
    new = cli_act - cli_ant
    retained = cli_act.intersection(cli_ant)
    
    col_ch1, col_ch2 = st.columns([1, 2])
    
    with col_ch1:
        st.metric("Retenidos", len(retained))
        st.metric("Nuevos", len(new), delta=len(new), delta_color="normal")
        st.metric("Perdidos", len(lost), delta=-len(lost), delta_color="inverse")
        
    with col_ch2:
        if len(lost) > 0:
            st.markdown("##### ⚠️ Top Clientes Perdidos (Mayor Venta Año Anterior)")
            df_lost_val = df_ant[df_ant['Key_Nit'].isin(lost)].groupby(['NOMBRE_CLIENTE_I', 'Poblacion_Real'])['VALOR_VENTA_O'].sum().reset_index()
            df_lost_val = df_lost_val.sort_values('VALOR_VENTA_O', ascending=False).head(10)
            st.dataframe(df_lost_val.style.format({'VALOR_VENTA_O': '${:,.0f}'}), use_container_width=True)
        else:
            st.success("¡Excelente! No hay clientes perdidos en este periodo.")

# ==============================================================================
# TAB 6: SIMULADOR BATCHING
# ==============================================================================
with tabs[5]:
    st.subheader("Simulador de Ahorro Operativo")
    
    col_sim1, col_sim2 = st.columns(2)
    with col_sim1:
        ahorro_pct = st.slider("Meta de reducción de viajes (Batching)", 0, 50, 20, format="%d%%") / 100
        ahorro_dinero = costo_total * ahorro_pct
        nueva_utilidad = utilidad + ahorro_dinero
        
        st.metric("Dinero Liberado (Ahorro)", f"${ahorro_dinero/1e6:,.1f}M")
        
        fig_b = go.Figure(go.Waterfall(
            measure=["relative", "relative", "total"],
            x=["Utilidad Actual", "Ahorro Logístico", "Nueva Utilidad"],
            y=[utilidad, ahorro_dinero, nueva_utilidad],
            decreasing={"marker":{"color":"#ef4444"}}, increasing={"marker":{"color":"#10b981"}}, totals={"marker":{"color":"#0f172a"}}
        ))
        st.plotly_chart(fig_b, use_container_width=True)
        
    with col_sim2:
        st.info("💡 **Insight:** Agrupar pedidos de clientes frecuentes reduce el costo de servir sin afectar la venta.")
        # Top clientes por frecuencia
        freq = df_act.groupby('NOMBRE_CLIENTE_I')['Pedido_ID'].nunique().reset_index().sort_values('Pedido_ID', ascending=False).head(5)
        st.markdown("**Clientes con más despachos (Candidatos):**")
        st.table(freq.rename(columns={'Pedido_ID': '# Envíos'}))

st.markdown("---")
st.caption("Master Brain Ultra v4.0 | Growth Focus | Powered by Python & Streamlit")
