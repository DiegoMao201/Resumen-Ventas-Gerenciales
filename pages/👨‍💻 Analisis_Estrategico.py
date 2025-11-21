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
    page_title="Master Brain Ultra | Growth Intelligence",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    :root { --primary: #0f172a; --accent: #6366f1; --success: #10b981; --danger: #ef4444; --bg-light: #f8fafc; }
    .main { background-color: #ffffff; }
    
    /* KPI Cards */
    .metric-card {
        background: white; border-left: 4px solid var(--accent);
        padding: 15px; border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04); margin-bottom: 15px;
    }
    .metric-val { font-size: 1.8rem; font-weight: 800; color: var(--primary); }
    .metric-lbl { font-size: 0.75rem; text-transform: uppercase; font-weight: 700; color: #64748b; letter-spacing: 1px; }
    .metric-delta { font-size: 0.85rem; font-weight: 600; margin-top: 5px; }
    .pos { color: var(--success); }
    .neg { color: var(--danger); }
    
    /* AI Insight Box */
    .ai-box {
        background-color: #fdf4ff; border: 1px solid #f0abfc;
        border-left: 5px solid #d946ef;
        padding: 20px; border-radius: 8px;
        margin: 15px 0;
        color: #701a75; font-size: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .ai-title { font-weight: 800; display: block; margin-bottom: 8px; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 1px;}
    
    /* Tables */
    .stDataFrame { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. FUNCIONES DE LÓGICA DE NEGOCIO (MODIFICADAS)
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
tabs = st.tabs(["📊 DNA Crecimiento", "📍 Geo-Oportunidad", "👥 Clientes Top", "📦 Producto Estrella", "📉 Riesgo/Fugas", "📝 AI Conclusiones"])

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
    st.subheader("🎯 Cazador de Oportunidades: Clientes")
    
    # Análisis Cliente x Cliente
    cl_act = df_act.groupby(['Key_Nit', 'CLIENTE', 'Vendedor'])['VALOR'].sum()
    cl_ant = df_ant.groupby(['Key_Nit', 'CLIENTE', 'Vendedor'])['VALOR'].sum()
    df_cl = pd.DataFrame({'Venta_Actual': cl_act, 'Venta_Anterior': cl_ant}).fillna(0)
    df_cl['Var_Pesos'] = df_cl['Venta_Actual'] - df_cl['Venta_Anterior']
    df_cl = df_cl.reset_index()
    
    # Oportunidad 1: Clientes que DECRECEN (Riesgo)
    df_risk = df_cl[df_cl['Var_Pesos'] < -500000].sort_values('Var_Pesos', ascending=True).head(15)
    
    # Oportunidad 2: Clientes con CRECIMIENTO MASIVO (Fidelizar)
    df_star = df_cl.sort_values('Var_Pesos', ascending=False).head(15)
    
    c_cli1, c_cli2 = st.columns(2)
    
    with c_cli1:
        st.markdown("### 📉 ALERTA: Clientes cayendo (Recuperación)")
        st.markdown("Estos clientes compran menos que el año pasado. **Acción: Llamada de servicio.**")
        st.dataframe(df_risk[['CLIENTE', 'Venta_Actual', 'Venta_Anterior', 'Var_Pesos', 'Vendedor']]
                     .style.format({'Venta_Actual': '${:,.0f}', 'Venta_Anterior': '${:,.0f}', 'Var_Pesos': '${:,.0f}'})
                     .background_gradient(cmap='Reds_r', subset=['Var_Pesos']), use_container_width=True)
        
    with c_cli2:
        st.markdown("### 🚀 ESTRELLAS: Mayor Crecimiento")
        st.markdown("Clientes desarrollando el portafolio. **Acción: Ofrecer nuevos productos.**")
        st.dataframe(df_star[['CLIENTE', 'Venta_Actual', 'Venta_Anterior', 'Var_Pesos', 'Vendedor']]
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
    
    best_sku = df_prod.sort_values('Var_Pesos', ascending=False).head(10)
    worst_sku = df_prod.sort_values('Var_Pesos', ascending=True).head(10)
    
    st.markdown(f"""
    <div class="ai-box">
    <span class="ai-title">📦 MIX INTEL</span>
    El producto que más dinero nuevo trajo a la compañía es: **{best_sku.iloc[0]['NOMBRE_PRODUCTO_K']}** (+${best_sku.iloc[0]['Var_Pesos']/1e6:,.1f}M).
    <br>Asegura inventario de este item.
    </div>
    """, unsafe_allow_html=True)
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("**Top 10: Productos Ganadores**")
        st.dataframe(best_sku.style.format({'Venta_Actual':'${:,.0f}','Var_Pesos':'${:,.0f}'}).background_gradient(cmap='Greens'), use_container_width=True)
    with col_p2:
        st.markdown("**Bottom 10: Productos Perdiendo Terreno**")
        st.dataframe(worst_sku.style.format({'Venta_Actual':'${:,.0f}','Var_Pesos':'${:,.0f}'}).background_gradient(cmap='Reds_r'), use_container_width=True)

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
