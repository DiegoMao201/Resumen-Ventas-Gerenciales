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
# 1. CONFIGURACIÓN VISUAL (UI/UX PREMIUM)
# ==============================================================================
st.set_page_config(
    page_title="Master Brain Ultra | Operations Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Estilos Corporativos */
    :root { --primary: #0f172a; --accent: #3b82f6; --success: #10b981; --danger: #ef4444; --bg-light: #f8fafc; }
    .main { background-color: #ffffff; }
    
    /* Tarjetas KPI */
    .metric-card {
        background: white; border-left: 5px solid var(--accent);
        padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px;
    }
    .metric-val { font-size: 2rem; font-weight: 800; color: var(--primary); }
    .metric-lbl { font-size: 0.8rem; text-transform: uppercase; font-weight: 700; color: #64748b; }
    .metric-delta { font-size: 0.9rem; font-weight: 600; margin-top: 5px; }
    .pos { color: var(--success); }
    .neg { color: var(--danger); }
    
    /* Cajas de Análisis */
    .analysis-box {
        background-color: #f0f9ff; border: 1px solid #bae6fd;
        border-left: 5px solid #0284c7;
        padding: 20px; border-radius: 8px;
        margin-top: 15px; margin-bottom: 15px;
        color: #0c4a6e; font-size: 0.95rem;
    }
    .analysis-title { font-weight: 800; display: block; margin-bottom: 5px; text-transform: uppercase; }
    .action-item { font-weight: 600; color: #b91c1c; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f5f9; border-radius: 5px; border: none; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: var(--primary); color: white; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. FUNCIONES DE LÓGICA DE NEGOCIO
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

def clasificar_estrategia_master(row):
    prod_name = normalizar_texto(row.get('NOMBRE_PRODUCTO_K', ''))
    cat_name = normalizar_texto(row.get('CATEGORIA_L', ''))
    aliados = ['ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', '3M', 'SISTA', 'SINTESOLDA']
    
    texto = f"{prod_name} {cat_name}"
    for aliado in aliados:
        if aliado in texto: return aliado
        
    raw_code = str(row.get('CODIGO_MARCA_N', '0')).split('.')[0].strip()
    mapa = {'33': 'OCEANIC', '34': 'PROTECTO', '58': 'PINTUCO', '60': 'INTERPON', '40': 'ICO', '41': 'TERINSA', '50':'PINTUCO MEGA'}
    return mapa.get(raw_code, 'OTRAS MARCAS')

def asignar_hub_logistico(ciudad):
    c = normalizar_texto(ciudad)
    
    # --- DEFINICIÓN ZONA LOGÍSTICA (TIENEN COSTO) ---
    # 1. RISARALDA (Hub Local)
    risaralda = ['PEREIRA', 'DOSQUEBRADAS', 'SANTA ROSA DE CABAL', 'LA VIRGINIA', 'MARSELLA', 'BELEN DE UMBRIA', 'APIA', 'SANTUARIO']
    if c in risaralda: return 'HUB RISARALDA'

    # 2. CALDAS (Hub Manizales)
    caldas = ['MANIZALES', 'VILLAMARIA', 'CHINCHINA', 'NEIRA', 'RIOSUCIO', 'ANSERMA', 'VITERBO', 'SUPIA', 'FILADELFIA', 'PALESTINA']
    if c in caldas: return 'HUB CALDAS'

    # 3. QUINDIO (Hub Armenia)
    quindio = ['ARMENIA', 'CALARCA', 'CIRCASIA', 'TEBAIDA', 'MONTENEGRO', 'QUIMBAYA', 'FILANDIA', 'SALENTO', 'PIJAO', 'GENOVA']
    if c in quindio: return 'HUB QUINDIO'

    # 4. VALLE DEL CAUCA Y NORTE DEL VALLE
    valle = ['CARTAGO', 'OBANDO', 'ZARZAL', 'ROLDANILLO', 'LA UNION', 'SEVILLA', 'CAICEDONIA', 
             'CALI', 'PALMIRA', 'BUGA', 'TULUA', 'YUMBO', 'JAMUNDI', 'CANDELARIA', 'BUENAVENTURA', 
             'ANSERMANUEVO', 'ALCALA', 'ULLOA', 'EL AGUILA', 'EL CAIRO', 'ARGELIA', 'VERSALLES', 'EL DOVIO']
    if c in valle: return 'HUB VALLE'

    # --- ZONA MOSTRADOR (SIN COSTO LOGÍSTICO) ---
    # Todo lo que no sea Risaralda, Caldas, Quindío o Valle
    return 'MOSTRADOR / SIN LOGISTICA'

# ==============================================================================
# 3. CARGA DE DATOS (DROPBOX + VENTAS)
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
                df['Hub_Logistico'] = df['Poblacion_Real'].apply(asignar_hub_logistico)
                return df[['Key_Nit', 'Poblacion_Real', 'Hub_Logistico', 'Vendedor']].drop_duplicates(subset=['Key_Nit'])
    except Exception: pass
    return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO Y FILTRADO YTD
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.warning("⚠️ Carga el archivo en el Home primero.")
    st.stop()

df_raw = st.session_state.df_ventas.copy()

try:
    cols_map = {0: 'anio', 1: 'mes', 7: 'COD', 8: 'CLIENTE', 10: 'PROD', 11: 'CATEGORIA', 13: 'MARCA', 14: 'VALOR'}
    df_raw = df_raw.rename(columns={df_raw.columns[i]: n for i,n in cols_map.items() if i < len(df_raw.columns)})
    if len(df_raw.columns) > 2 and str(df_raw.iloc[0,2]).isnumeric():
        df_raw['dia'] = df_raw.iloc[:, 2].astype(int)
    else: df_raw['dia'] = 15
except: st.stop()

df_raw['VALOR'] = pd.to_numeric(df_raw['VALOR'], errors='coerce').fillna(0)
df_raw['anio'] = pd.to_numeric(df_raw['anio'], errors='coerce').fillna(date.today().year).astype(int)
df_raw['mes'] = pd.to_numeric(df_raw['mes'], errors='coerce').fillna(1).astype(int)
df_raw['Key_Nit'] = df_raw['COD'].apply(limpiar_codigo_master)

with st.spinner("🧠 Analizando Operación..."):
    df_raw['Marca_Master'] = df_raw.apply(clasificar_estrategia_master, axis=1)
    df_cli = cargar_poblaciones_dropbox_excel()
    if not df_cli.empty:
        df_full = pd.merge(df_raw, df_cli, on='Key_Nit', how='left')
        df_full['Poblacion_Real'] = df_full['Poblacion_Real'].fillna('NO IDENTIFICADO')
        # Si no cruzó, recalcular Hub basado en poblacion (aunque sea None, irá a Mostrador si no se sabe)
        mask_null = df_full['Hub_Logistico'].isna()
        df_full.loc[mask_null, 'Hub_Logistico'] = df_full.loc[mask_null, 'Poblacion_Real'].apply(asignar_hub_logistico)
        df_full['Vendedor'] = df_full['Vendedor'].fillna('GENERAL')
    else:
        df_full = df_raw.copy()
        df_full['Poblacion_Real'] = 'SIN DATA'
        df_full['Hub_Logistico'] = 'MOSTRADOR / SIN LOGISTICA'
        df_full['Vendedor'] = 'GENERAL'

hoy = date.today()
def ytd(row):
    if row['mes'] < hoy.month: return True
    if row['mes'] == hoy.month: return row['dia'] <= hoy.day
    return False
df_master = df_full[df_full.apply(ytd, axis=1)].copy()

# ==============================================================================
# 5. DASHBOARD & LÓGICA DE NEGOCIO AVANZADA
# ==============================================================================
st.title("🧠 Master Brain Ultra | Ops Intelligence Center")
st.markdown(f"**Fecha Corte:** {hoy.strftime('%d-%b-%Y')} | Comparación exacta de periodos.")
st.divider()

# --- SIDEBAR: PARÁMETROS Y FILTROS ---
with st.sidebar:
    st.header("🎛️ Panel de Control")
    
    st.subheader("1. Estructura de Costos")
    margen_pct = st.slider("Margen Bruto (%)", 10, 60, 25) / 100
    st.info("ℹ️ Costos aplican solo a: Eje Cafetero y Valle.")
    costo_local = st.number_input("Costo Envío Local/Cercano ($)", 10000, 50000, 12000)
    costo_nal = st.number_input("Costo Envío Regional ($)", 20000, 100000, 45000)
    
    st.subheader("2. Segmentación")
    anios = sorted(df_master['anio'].unique(), reverse=True)
    anio_obj = st.selectbox("Año Objetivo", anios, 0)
    anio_base = st.selectbox("Año Base", [a for a in anios if a!=anio_obj], 0)
    
    sel_hubs = st.multiselect("Hubs Logísticos", sorted(df_master['Hub_Logistico'].unique()), default=sorted(df_master['Hub_Logistico'].unique()))
    sel_city = st.multiselect("Poblaciones", sorted(df_master['Poblacion_Real'].unique()))
    sel_brand = st.multiselect("Marcas", sorted(df_master['Marca_Master'].unique()))
    sel_cat = st.multiselect("Categorías", sorted(df_master['CATEGORIA'].astype(str).unique()))

# --- FILTRADO DINÁMICO ---
df_f = df_master[df_master['Hub_Logistico'].isin(sel_hubs)].copy()
if sel_city: df_f = df_f[df_f['Poblacion_Real'].isin(sel_city)]
if sel_brand: df_f = df_f[df_f['Marca_Master'].isin(sel_brand)]
if sel_cat: df_f = df_f[df_f['CATEGORIA'].isin(sel_cat)]

df_act = df_f[df_f['anio'] == anio_obj].copy()
df_ant = df_f[df_f['anio'] == anio_base].copy()

# --- CÁLCULOS "COST-TO-SERVE" (LOGICA CORREGIDA) ---
df_act['Pedido_ID'] = df_act['Key_Nit'].astype(str)+'-'+df_act['mes'].astype(str)+'-'+df_act['dia'].astype(str)
n_pedidos = df_act['Pedido_ID'].nunique()
venta = df_act['VALOR'].sum()

def calc_costo(row):
    hub = row['Hub_Logistico']
    # REGLA DE ORO: Si es MOSTRADOR (fuera de cobertura logística), costo es CERO.
    if 'MOSTRADOR' in hub:
        return 0
    
    # Si está dentro de la cobertura (Risaralda, Caldas, Quindio, Valle)
    # Asumimos Pereira/Dosq como 'Local' y el resto como 'Regional' (Nacional en contexto variable)
    # O si prefieres: Risaralda = Local, Resto = Nacional.
    if 'RISARALDA' in hub: # Pereira, Dosquebradas, etc.
        return costo_local
    else: # Caldas, Quindio, Valle
        return costo_nal

df_pedidos_unicos = df_act[['Pedido_ID', 'Hub_Logistico']].drop_duplicates()
df_pedidos_unicos['Costo'] = df_pedidos_unicos.apply(calc_costo, axis=1)
costo_total = df_pedidos_unicos['Costo'].sum()

ut_bruta = venta * margen_pct
ut_neta = ut_bruta - costo_total
margen_real = (ut_neta/venta*100) if venta > 0 else 0

# --- HEADER METRICS ---
c1,c2,c3,c4,c5 = st.columns(5)
delta_v = ((venta - df_ant['VALOR'].sum())/df_ant['VALOR'].sum()*100) if df_ant['VALOR'].sum()>0 else 100

def card(col, tit, val, d, sub, color="pos"):
    col.markdown(f"""<div class="metric-card"><div class="metric-lbl">{tit}</div>
    <div class="metric-val">{val}</div><div class="metric-delta"><span class="{color}">{d}</span> {sub}</div></div>""", unsafe_allow_html=True)

card(c1, "Venta Total", f"${venta/1e6:,.1f}M", f"{delta_v:+.1f}%", "Crecimiento")
card(c2, "Utilidad Real", f"${ut_neta/1e6:,.1f}M", f"{margen_real:.1f}%", "Margen Neto Oper.")
card(c3, "Costo Logístico", f"${costo_total/1e6:,.1f}M", f"{(costo_total/venta)*100:.1f}%", "del Venta Total", "neg")
card(c4, "# Despachos", f"{n_pedidos:,}", f"{n_pedidos/df_act['Key_Nit'].nunique():.1f}", "Freq. Promedio")
card(c5, "Ticket Promedio", f"${(venta/n_pedidos if n_pedidos else 0):,.0f}", "---", "Por Despacho")

# ==============================================================================
# 6. TABS CON ANÁLISIS
# ==============================================================================
tabs = st.tabs(["🚚 Rentabilidad", "⚖️ Peso Categorías", "🔄 Batching (Ahorro)", "📈 Drivers", "👥 Retención", "🌍 Geo-Estrategia", "🤖 Conclusión"])

# --- TAB 1: RENTABILIDAD ---
with tabs[0]:
    df_city = df_act.groupby(['Poblacion_Real', 'Hub_Logistico']).agg(
        Venta=('VALOR', 'sum'), Pedidos=('Pedido_ID', 'nunique')
    ).reset_index()
    
    df_city['Costo_Unit'] = df_city.apply(calc_costo, axis=1)
    df_city['Costo_Total'] = df_city['Pedidos'] * df_city['Costo_Unit']
    df_city['Utilidad'] = (df_city['Venta'] * margen_pct) - df_city['Costo_Total']
    
    ciudades_perdida = df_city[df_city['Utilidad'] < 0]
    txt_rentabilidad = ""
    if ciudades_perdida.empty:
        txt_rentabilidad = "✅ **EXCELENTE NOTICIA:** Todas las poblaciones son rentables con los filtros actuales."
    else:
        top_loser = ciudades_perdida.sort_values('Utilidad').iloc[0]
        txt_rentabilidad = f"""
        ⚠️ **ALERTA:** Pierdes dinero en **{len(ciudades_perdida)} poblaciones**.
        <br>Crítico: **{top_loser['Poblacion_Real']}** (Pérdida: ${abs(top_loser['Utilidad']):,.0f}).
        """

    st.markdown(f"""<div class="analysis-box"><span class="analysis-title">ANÁLISIS DE RENTABILIDAD</span>{txt_rentabilidad}</div>""", unsafe_allow_html=True)
    
    col_r1, col_r2 = st.columns([2,1])
    with col_r1:
        if not df_city.empty:
            fig = px.scatter(df_city, x="Costo_Total", y="Utilidad", size="Venta", color="Hub_Logistico", 
                             hover_name="Poblacion_Real", title="Matriz Eficiencia", height=450)
            fig.add_hline(y=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos para graficar.")
    with col_r2:
        st.markdown("**Detalle Financiero**")
        format_dict = {"Venta": "${:,.0f}", "Costo_Total": "${:,.0f}", "Utilidad": "${:,.0f}"}
        st.dataframe(df_city[['Poblacion_Real', 'Venta', 'Costo_Total', 'Utilidad']]
                     .sort_values('Utilidad')
                     .style.format(format_dict).background_gradient(cmap='RdYlGn', subset=['Utilidad']), 
                     use_container_width=True)

# --- TAB 2: PESO CATEGORÍAS ---
with tabs[1]:
    st.markdown("""
    <div class="analysis-box">
    <span class="analysis-title">ANÁLISIS DE IMPACTO POR CATEGORÍA</span>
    Aquí analizamos minuciosamente si una categoría está "poniendo" o "quitando" valor al crecimiento global.
    </div>
    """, unsafe_allow_html=True)

    cat_act = df_act.groupby('CATEGORIA')['VALOR'].sum()
    cat_ant = df_ant.groupby('CATEGORIA')['VALOR'].sum()
    
    df_cat_analysis = pd.DataFrame({'Venta_Actual': cat_act, 'Venta_Anterior': cat_ant}).fillna(0)
    df_cat_analysis['Var_Pesos'] = df_cat_analysis['Venta_Actual'] - df_cat_analysis['Venta_Anterior']
    df_cat_analysis['Var_Pct'] = (df_cat_analysis['Var_Pesos'] / df_cat_analysis['Venta_Anterior']).replace([np.inf, -np.inf], 0)
    
    total_growth_abs = df_cat_analysis['Var_Pesos'].sum()
    df_cat_analysis['Incidencia_Peso'] = df_cat_analysis.apply(
        lambda row: (row['Var_Pesos'] / abs(total_growth_abs)) if total_growth_abs != 0 else 0, axis=1
    )
    
    df_cat_analysis = df_cat_analysis.sort_values('Var_Pesos', ascending=False)

    fig_cat = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative"] * len(df_cat_analysis),
        x=df_cat_analysis.index,
        y=df_cat_analysis['Var_Pesos'],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "#ef4444"}}, 
        increasing={"marker": {"color": "#10b981"}}, 
    ))
    fig_cat.update_layout(title="Contribution Chart: ¿Quién aporta y quién resta al crecimiento?", height=450)
    st.plotly_chart(fig_cat, use_container_width=True)

    st.markdown("### 📋 Detalle Minucioso de Aporte")
    format_cat = {
        "Venta_Actual": "${:,.0f}", "Venta_Anterior": "${:,.0f}",
        "Var_Pesos": "${:,.0f}", "Var_Pct": "{:+.1%}", "Incidencia_Peso": "{:+.2%}"
    }
    df_show = df_cat_analysis[['Venta_Actual', 'Venta_Anterior', 'Var_Pesos', 'Var_Pct', 'Incidencia_Peso']].copy()
    st.dataframe(
        df_show.style.format(format_cat)
        .background_gradient(cmap='RdYlGn', subset=['Var_Pesos', 'Incidencia_Peso'])
        .bar(subset=['Var_Pct'], align='mid', color=['#ef4444', '#10b981']),
        use_container_width=True
    )

# --- TAB 3: BATCHING ---
with tabs[2]:
    st.markdown(f"""<div class="analysis-box"><span class="analysis-title">SIMULADOR DE EFICIENCIA</span>
    Promedio actual: **{n_pedidos/df_act['Key_Nit'].nunique():.1f} despachos por cliente**.
    <br>Agrupar pedidos reduce costos y aumenta utilidad directa.
    </div>""", unsafe_allow_html=True)
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        ahorro_pct = st.slider("Meta reducción de viajes (%)", 0, 50, 20) / 100
        ahorro = costo_total * ahorro_pct
        
        fig_w = go.Figure(go.Waterfall(
            measure=["relative", "relative", "total"],
            x=["Utilidad Actual", "Ahorro Logístico", "Utilidad Potencial"],
            y=[ut_neta, ahorro, ut_neta+ahorro],
            text=[f"${ut_neta/1e6:.1f}M", f"+${ahorro/1e6:.1f}M", f"${(ut_neta+ahorro)/1e6:.1f}M"],
            decreasing={"marker":{"color":"#ef4444"}}, increasing={"marker":{"color":"#10b981"}}, totals={"marker":{"color":"#0f172a"}}
        ))
        st.plotly_chart(fig_w, use_container_width=True)
        
    with col_b2:
        top_freq = df_act.groupby(['Key_Nit', 'CLIENTE'])['Pedido_ID'].nunique().reset_index().sort_values('Pedido_ID', ascending=False).head(5)
        st.markdown("**Top Clientes Candidatos a Batching**")
        st.table(top_freq.rename(columns={'Pedido_ID':'# Despachos'}))

# --- TAB 4: DRIVERS ---
with tabs[3]:
    col_d1, col_d2 = st.columns([3,1])
    with col_d1:
        dim = st.radio("Ver impacto por:", ["Marca_Master", "Hub_Logistico"], horizontal=True)
        g_act = df_act.groupby(dim)['VALOR'].sum()
        g_ant = df_ant.groupby(dim)['VALOR'].sum()
        df_diff = pd.DataFrame({'Act': g_act, 'Ant': g_ant}).fillna(0)
        df_diff['Diff'] = df_diff['Act'] - df_diff['Ant']
        df_diff = df_diff.sort_values('Diff', ascending=False)
        
        best = df_diff.index[0] if not df_diff.empty else "N/A"
        val_best = df_diff['Diff'].iloc[0] if not df_diff.empty else 0
        st.markdown(f"<div class='analysis-box'>Mayor impulsor: **{best}** (+${val_best/1e6:,.1f}M).</div>", unsafe_allow_html=True)

        fig_d = go.Figure(go.Waterfall(orientation="v", measure=["relative"]*len(df_diff), x=df_diff.index, y=df_diff['Diff'],
                                      decreasing={"marker":{"color":"#ef4444"}}, increasing={"marker":{"color":"#10b981"}}))
        st.plotly_chart(fig_d, use_container_width=True)
    
    with col_d2:
        st.dataframe(df_diff[['Diff']].style.format({"Diff": "${:,.0f}"}).background_gradient(cmap='RdYlGn'), use_container_width=True)

# --- TAB 5: RETENCIÓN ---
with tabs[4]:
    c_act = set(df_act['Key_Nit']); c_ant = set(df_ant['Key_Nit'])
    lost = c_ant - c_act; new = c_act - c_ant
    
    val_lost = df_ant[df_ant['Key_Nit'].isin(lost)]['VALOR'].sum() if lost else 0
    txt_churn = f"⚠️ Se han fugado **{len(lost)} clientes**. Venta perdida: **${val_lost/1e6:,.1f}M**." if lost else "✅ Cero fugas."
        
    st.markdown(f"<div class='analysis-box'>{txt_churn}</div>", unsafe_allow_html=True)
    
    c1,c2,c3 = st.columns(3)
    c1.metric("Retenidos", len(c_act.intersection(c_ant))); c2.metric("Nuevos", len(new)); c3.metric("Perdidos", len(lost))
    
    if lost:
        st.markdown("**Clientes Perdidos (Top 10)**")
        df_lost = df_ant[df_ant['Key_Nit'].isin(lost)].groupby(['CLIENTE','Poblacion_Real'])['VALOR'].sum().sort_values(ascending=False).head(10).to_frame()
        st.dataframe(df_lost.style.format({"VALOR": "${:,.0f}"}), use_container_width=True)

# --- TAB 6: GEO ESTRATEGIA (CORREGIDO TYPEERROR) ---
with tabs[5]:
    st.markdown(f"""<div class="analysis-box">
    <strong>Volumen (Tamaño)</strong> vs <strong>Rentabilidad (Color)</strong>.
    <br>• <strong style='color:green'>VERDE:</strong> Ganancia. <strong style='color:red'>ROJO:</strong> Pérdida operativa.
    <br>ℹ️ Nota: Las zonas en <strong>'MOSTRADOR'</strong> tendrán $0 costo y alta utilidad (verde intenso).
    </div>""", unsafe_allow_html=True)
    
    # Preparación de datos segura para evitar TypeError
    df_tree = df_city.copy()
    df_tree = df_tree[df_tree['Venta'] > 0]
    
    # Asegurar tipos de datos y eliminar NaNs críticos
    df_tree['Hub_Logistico'] = df_tree['Hub_Logistico'].fillna('SIN DEFINIR').astype(str)
    df_tree['Poblacion_Real'] = df_tree['Poblacion_Real'].fillna('SIN DEFINIR').astype(str)
    df_tree['Utilidad'] = pd.to_numeric(df_tree['Utilidad'], errors='coerce').fillna(0)
    
    if not df_tree.empty:
        # Solo graficar si hay datos
        fig_t = px.treemap(df_tree, path=[px.Constant("Colombia"), 'Hub_Logistico', 'Poblacion_Real'], 
                           values='Venta', color='Utilidad', color_continuous_scale='RdYlGn', midpoint=0)
        st.plotly_chart(fig_t, use_container_width=True)
    else:
        st.warning("No hay datos suficientes para generar el mapa geográfico.")

# --- TAB 7: CONCLUSIÓN ---
with tabs[6]:
    st.subheader("🤖 Master Brain Diagnosis")
    status = "CRECIMIENTO" if delta_v > 0 else "CONTRACCIÓN"
    color_st = "green" if delta_v > 0 else "red"
    
    st.markdown(f"""
    ### 1. Resumen Ejecutivo
    Operación en **<span style='color:{color_st}'>{status} ({delta_v:+.1f}%)</span>**.
    
    ### 2. Situación Financiera
    Costo logístico: **{(costo_total/venta)*100:.1f}%** de la venta.
    Margen Neto Real: **{margen_real:.1f}%**.
    
    ### 3. Recomendaciones:
    1.  **Análisis de Categorías:** Revisa la pestaña "Peso Categorías" para ver qué líneas están destruyendo valor (barras rojas en el Waterfall).
    2.  **Optimización:** Implementar *Batching* en **{top_freq.iloc[0]['CLIENTE'] if not top_freq.empty else 'Top Clientes'}**.
    3.  **Geografía:** Atención urgente a **{top_loser['Poblacion_Real'] if not ciudades_perdida.empty else 'N/A'}**.
    """, unsafe_allow_html=True)
