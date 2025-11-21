import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import unicodedata
import io
import dropbox
import re
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
    """Normalización robusta."""
    if pd.isna(texto) or texto == "": return "SIN DEFINIR"
    texto = str(texto)
    texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sin_tildes.upper().strip()

def limpiar_nit(nit):
    """
    Limpia NIT manejando errores de Excel de forma agresiva.
    Ejemplo: 900.123.0 -> 900123, 900123-1 -> 900123
    """
    if pd.isna(nit): return "0"
    s_nit = str(nit).strip()
    
    # Manejar notación científica o flotantes (e.g. 900123.0)
    if '.' in s_nit:
        try:
            s_nit = str(int(float(s_nit)))
        except:
            s_nit = s_nit.split('.')[0]
            
    # Quitar guiones y DV
    if '-' in s_nit:
        s_nit = s_nit.split('-')[0]
        
    # Dejar solo números
    s_limpio = re.sub(r'[^0-9]', '', s_nit)
    
    # Quitar ceros a la izquierda
    s_limpio = s_limpio.lstrip('0')
    
    return s_limpio if s_limpio else "0"

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
# 3. CONEXIÓN DROPBOX (DEBUGGING MEJORADO)
# ==============================================================================
@st.cache_data(ttl=3600)
def cargar_poblaciones_dropbox_excel():
    """Lee Excel desde Dropbox con búsqueda flexible de columnas."""
    try:
        APP_KEY = st.secrets["dropbox"]["app_key"]
        APP_SECRET = st.secrets["dropbox"]["app_secret"]
        REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]

        with dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN) as dbx:
            # Intentar rutas comunes
            rutas = ['/clientes_detalle.xlsx', '/data/clientes_detalle.xlsx', '/Master/clientes_detalle.xlsx']
            res = None
            for r in rutas:
                try:
                    _, res = dbx.files_download(path=r)
                    break
                except: continue
            
            if not res:
                st.warning("⚠️ Archivo 'clientes_detalle.xlsx' no encontrado en Dropbox.")
                return pd.DataFrame()

            with io.BytesIO(res.content) as stream:
                df_drop = pd.read_excel(stream, engine='openpyxl')
            
            # --- NORMALIZACIÓN DE COLUMNAS ---
            df_drop.columns = [str(c).strip().upper() for c in df_drop.columns]
            
            # Búsqueda flexible de columnas
            col_nit = next((c for c in df_drop.columns if any(x in c for x in ['NIT', 'NIF', 'CEDULA', 'CODIGO'])), None)
            col_ciudad = next((c for c in df_drop.columns if any(x in c for x in ['CIUDAD', 'POBLACION', 'MUNICIPIO', 'CITY'])), None)
            col_canal = next((c for c in df_drop.columns if any(x in c for x in ['CANAL', 'SECTOR', 'NEGOCIO'])), None)

            if not col_nit:
                return pd.DataFrame()

            # Limpieza y selección
            df_drop['Key_Nit'] = df_drop[col_nit].apply(limpiar_nit)
            
            cols_final = ['Key_Nit']
            
            if col_ciudad:
                df_drop['Poblacion_Real'] = df_drop[col_ciudad].apply(normalizar_texto)
                cols_final.append('Poblacion_Real')
            else:
                df_drop['Poblacion_Real'] = 'SIN ASIGNAR'
                cols_final.append('Poblacion_Real')

            if col_canal:
                df_drop['Canal_Cliente'] = df_drop[col_canal].apply(normalizar_texto)
                cols_final.append('Canal_Cliente')

            # Eliminar duplicados de NIT para evitar explosión en el merge
            return df_drop.drop_duplicates(subset=['Key_Nit'])[cols_final]

    except Exception as e:
        st.error(f"Error conexión Dropbox: {str(e)}")
        return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO Y DATOS
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.info("👋 Por favor carga el archivo maestro de ventas en el Home.")
    st.stop()

df_raw = st.session_state.df_ventas.copy()

# Mapeo y Limpieza Inicial
col_map = {
    df_raw.columns[0]: 'anio',
    df_raw.columns[1]: 'mes',
    df_raw.columns[7]: 'CODIGO_CLIENTE_H', 
    df_raw.columns[8]: 'NOMBRE_CLIENTE_I',
    df_raw.columns[10]: 'NOMBRE_PRODUCTO_K',
    df_raw.columns[11]: 'CATEGORIA_L',
    df_raw.columns[13]: 'CODIGO_MARCA_N',
    df_raw.columns[14]: 'VALOR_VENTA_O'
}
final_map = {k: v for k, v in col_map.items() if k in df_raw.columns}
df_raw = df_raw.rename(columns=final_map)

df_raw['VALOR_VENTA_O'] = pd.to_numeric(df_raw['VALOR_VENTA_O'], errors='coerce').fillna(0)
df_raw['anio'] = pd.to_numeric(df_raw['anio'], errors='coerce').fillna(2024).astype(int)
df_raw['mes'] = pd.to_numeric(df_raw['mes'], errors='coerce').fillna(1).astype(int)
df_raw['Key_Nit'] = df_raw['CODIGO_CLIENTE_H'].apply(limpiar_nit)

# Clasificación Maestra
with st.spinner("⚙️ Ejecutando algoritmos de clasificación y geolocalización..."):
    df_raw['Marca_Master'] = df_raw.apply(clasificar_estrategia_master, axis=1)
    
    # Carga Geo y Merge
    df_clientes = cargar_poblaciones_dropbox_excel()
    
    if not df_clientes.empty:
        # Merge Left para no perder ventas si no hay dato geo
        df_full = pd.merge(df_raw, df_clientes, on='Key_Nit', how='left')
        
        # Relleno inteligente de nulos
        df_full['Poblacion_Real'] = df_full['Poblacion_Real'].fillna('NO IDENTIFICADO')
        if 'Canal_Cliente' not in df_full.columns:
            df_full['Canal_Cliente'] = 'GENERAL'
        else:
            df_full['Canal_Cliente'] = df_full['Canal_Cliente'].fillna('GENERAL')
    else:
        df_full = df_raw.copy()
        df_full['Poblacion_Real'] = 'SIN DATA'
        df_full['Canal_Cliente'] = 'GENERAL'

    # Crear columna de Fecha real para series de tiempo
    df_full['Fecha_Dt'] = pd.to_datetime(df_full['anio'].astype(str) + '-' + df_full['mes'].astype(str) + '-01')

# ==============================================================================
# 5. DASHBOARD "ULTRA"
# ==============================================================================

st.title("🧠 Master Brain Ultra")
st.markdown("**Sistema Avanzado de Inteligencia Comercial** | _v2.0 Enhanced Engine_")
st.divider()

# --- SIDEBAR GLOBAL ---
with st.sidebar:
    st.header("🎛️ Centro de Control")
    
    # Filtro Fechas
    anios = sorted(df_full['anio'].unique(), reverse=True)
    c_s1, c_s2 = st.columns(2)
    anio_obj = c_s1.selectbox("Año Objetivo", anios, index=0)
    anio_base = c_s2.selectbox("Año Base", [a for a in anios if a != anio_obj], index=0)
    
    st.markdown("---")
    st.caption("FILTROS DE SEGMENTACIÓN")
    
    # Filtros con conteo
    all_brands = sorted(df_full['Marca_Master'].unique())
    sel_brands = st.multiselect("Marcas", all_brands, default=all_brands, placeholder="Todas las marcas")
    
    all_cats = sorted(df_full[df_full['Marca_Master'].isin(sel_brands)]['CATEGORIA_L'].dropna().unique())
    sel_cats = st.multiselect("Categorías", all_cats, placeholder="Todas las categorías")
    
    all_cities = sorted(df_full['Poblacion_Real'].unique())
    sel_city = st.multiselect("Poblaciones", all_cities, placeholder="Todas las zonas")

    # Debugger Expander (Para revisar problemas de datos)
    with st.expander("🛠️ Debugger de Datos"):
        st.write(f"Total Registros: {len(df_full):,}")
        st.write(f"Clientes con Geo: {df_full[df_full['Poblacion_Real'] != 'NO IDENTIFICADO']['Key_Nit'].nunique()}")
        st.write(f"Merge Rate: {100 - (df_full['Poblacion_Real'] == 'NO IDENTIFICADO').mean()*100:.1f}%")

# --- FILTRADO MAESTRO ---
df_f = df_full[df_full['Marca_Master'].isin(sel_brands)]
if sel_cats: df_f = df_f[df_f['CATEGORIA_L'].isin(sel_cats)]
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

# Cálculo CAGR mensual simple (Tendencia del año actual)
try:
    last_month_sale = df_act.groupby('mes')['VALOR_VENTA_O'].sum().iloc[-1]
    first_month_sale = df_act.groupby('mes')['VALOR_VENTA_O'].sum().iloc[0]
    trend_signal = "Positiva" if last_month_sale > first_month_sale else "Negativa"
except:
    trend_signal = "Plana"

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

# --- TABS DE ANÁLISIS PROFUNDO ---
tabs = st.tabs([
    "📈 Drivers & Waterfall", 
    "👥 Inteligencia de Clientes (Churn)", 
    "🗓️ Tendencias & Seasonality",
    "🧩 Portfolio & BCG",
    "🌍 Geo-Analytics",
    "🔎 Data Explorer"
])

# --- TAB 1: WATERFALL (CRECIMIENTO) ---
with tabs[0]:
    c_w1, c_w2 = st.columns([3, 1])
    
    with c_w1:
        st.subheader(f"Análisis de Variación: ¿Por qué crecimos (o caímos)?")
        dim_view = st.radio("Dimensionar por:", ["Marca_Master", "CATEGORIA_L", "Canal_Cliente"], horizontal=True, key="w_radio")
        
        g_act = df_act.groupby(dim_view)['VALOR_VENTA_O'].sum()
        g_ant = df_ant.groupby(dim_view)['VALOR_VENTA_O'].sum()
        df_w = pd.DataFrame({'Actual': g_act, 'Anterior': g_ant}).fillna(0)
        df_w['Variacion'] = df_w['Actual'] - df_w['Anterior']
        df_w = df_w.sort_values('Variacion', ascending=False)
        
        # Gráfico Waterfall
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
        fig_water.update_layout(title=f"Puente de Ventas por {dim_view} (Top Movers)", height=450, plot_bgcolor="white")
        st.plotly_chart(fig_water, use_container_width=True)

    with c_w2:
        st.subheader("Insights Rápidos")
        best_performer = df_w.index[0]
        worst_performer = df_w.index[-1]
        st.info(f"🏆 **Mejor Desempeño:** {best_performer}\n\nAportó ${df_w.loc[best_performer, 'Variacion']/1e6:.1f}M al crecimiento.")
        st.warning(f"⚠️ **Mayor Reto:** {worst_performer}\n\nRestó ${abs(df_w.loc[worst_performer, 'Variacion'])/1e6:.1f}M.")
        
        st.markdown("### Tabla de Detalle")
        st.dataframe(df_w[['Actual', 'Variacion']].style.format("${:,.0f}").background_gradient(subset=['Variacion'], cmap='RdYlGn'), use_container_width=True)

# --- TAB 2: CLIENT INTELLIGENCE (CHURN & RETENTION) ---
with tabs[1]:
    st.subheader("Análisis de Salud de Cartera (Churn Analysis)")
    
    # Lógica de Churn
    cli_set_act = set(df_act[df_act['VALOR_VENTA_O']>0]['Key_Nit'])
    cli_set_ant = set(df_ant[df_ant['VALOR_VENTA_O']>0]['Key_Nit'])
    
    retained = cli_set_act.intersection(cli_set_ant)
    lost = cli_set_ant - cli_set_act
    new = cli_set_act - cli_set_ant
    
    c_ch1, c_ch2, c_ch3 = st.columns(3)
    c_ch1.metric("Clientes Retenidos", len(retained), help="Compraron este año y el anterior")
    c_ch2.metric("Clientes Nuevos (Captación)", len(new), f"+{len(new)}", delta_color="normal")
    c_ch3.metric("Clientes Perdidos (Churn)", len(lost), f"-{len(lost)}", delta_color="inverse")
    
    col_churn_main, col_churn_detail = st.columns([2, 1])
    
    with col_churn_main:
        # Calcular valor del Churn (Cuánto vendían los que se fueron)
        val_lost = df_ant[df_ant['Key_Nit'].isin(lost)]['VALOR_VENTA_O'].sum()
        val_new = df_act[df_act['Key_Nit'].isin(new)]['VALOR_VENTA_O'].sum()
        
        fig_sankey = go.Figure(data=[go.Pie(
            labels=['Retenidos', 'Nuevos', 'Perdidos (Churn)'],
            values=[len(retained), len(new), len(lost)],
            hole=.5,
            marker_colors=['#3b82f6', '#10b981', '#ef4444']
        )])
        fig_sankey.update_layout(title="Composición de Cartera (Base Clientes)")
        st.plotly_chart(fig_sankey, use_container_width=True)

    with col_churn_detail:
        st.markdown("**Impacto Económico**")
        st.write(f"💸 **Venta en Riesgo (Perdida):** ${val_lost/1e6:,.1f}M")
        st.write(f"💰 **Venta Nueva (Ganada):** ${val_new/1e6:,.1f}M")
        
        st.markdown("---")
        st.markdown("**Top 5 Clientes Perdidos (Prioridad Recuperación)**")
        lost_detail = df_ant[df_ant['Key_Nit'].isin(lost)].groupby('NOMBRE_CLIENTE_I')['VALOR_VENTA_O'].sum().sort_values(ascending=False).head(5)
        st.dataframe(lost_detail.to_frame().style.format("${:,.0f}"), use_container_width=True)

# --- TAB 3: TENDENCIAS TEMPORALES ---
with tabs[2]:
    st.subheader("Evolución Mensual Comparativa")
    
    g_time = df_f.groupby(['anio', 'mes'])['VALOR_VENTA_O'].sum().reset_index()
    
    # Pivot para gráfico de líneas comparativo
    df_pivot = g_time.pivot(index='mes', columns='anio', values='VALOR_VENTA_O').fillna(0)
    
    fig_line = go.Figure()
    colors = ['#94a3b8', '#3b82f6', '#10b981'] # Gris para años viejos, Azul actual
    
    for i, col in enumerate(df_pivot.columns):
        color = '#0f172a' if col == anio_obj else '#cbd5e1'
        width = 4 if col == anio_obj else 2
        fig_line.add_trace(go.Scatter(x=df_pivot.index, y=df_pivot[col], mode='lines+markers', name=str(col), line=dict(color=color, width=width)))

    fig_line.update_layout(
        title="Tendencia de Venta Mensual", 
        xaxis_title="Mes", 
        yaxis_title="Venta ($)",
        hovermode="x unified",
        plot_bgcolor="white",
        height=500
    )
    st.plotly_chart(fig_line, use_container_width=True)
    
    # Heatmap de Estacionalidad
    st.markdown("#### 🌡️ Mapa de Calor de Ventas (Estacionalidad)")
    df_heat = df_f.groupby(['anio', 'mes'])['VALOR_VENTA_O'].sum().reset_index()
    fig_heat = px.density_heatmap(df_heat, x="mes", y="anio", z="VALOR_VENTA_O", color_continuous_scale="Blues", labels={"VALOR_VENTA_O":"Venta"})
    fig_heat.update_layout(height=350)
    st.plotly_chart(fig_heat, use_container_width=True)

# --- TAB 4: PORTFOLIO (TREEMAP FIXED + BCG) ---
with tabs[3]:
    c_p1, c_p2 = st.columns(2)
    
    with c_p1:
        st.subheader("Jerarquía de Portafolio (Treemap)")
        # --- FIX TREEMAP ERROR ---
        # Limpieza estricta para evitar el ValueError de Plotly
        df_tree = df_act.copy()
        df_tree['Marca_Master'] = df_tree['Marca_Master'].fillna('SIN MARCA').astype(str)
        df_tree['CATEGORIA_L'] = df_tree['CATEGORIA_L'].fillna('SIN CAT').astype(str)
        # Agrupar para reducir granularidad y evitar duplicados a nivel hoja
        df_tree_g = df_tree.groupby(['Marca_Master', 'CATEGORIA_L'])['VALOR_VENTA_O'].sum().reset_index()
        df_tree_g = df_tree_g[df_tree_g['VALOR_VENTA_O'] > 0] # Eliminar ceros
        
        if not df_tree_g.empty:
            fig_tree = px.treemap(
                df_tree_g, 
                path=[px.Constant("Total"), 'Marca_Master', 'CATEGORIA_L'], 
                values='VALOR_VENTA_O',
                color='VALOR_VENTA_O',
                color_continuous_scale='Blues',
                title="Distribución de Venta por Marca > Categoría"
            )
            fig_tree.update_traces(root_color="lightgrey")
            fig_tree.update_layout(margin=dict(t=50, l=25, r=25, b=25))
            st.plotly_chart(fig_tree, use_container_width=True)
        else:
            st.warning("No hay datos suficientes para el Treemap.")

    with c_p2:
        st.subheader("Ley de Pareto (80/20) - Productos")
        df_pareto = df_act.groupby('NOMBRE_PRODUCTO_K')['VALOR_VENTA_O'].sum().sort_values(ascending=False).reset_index()
        df_pareto['Acumulado'] = df_pareto['VALOR_VENTA_O'].cumsum()
        df_pareto['Pct_Acum'] = 100 * df_pareto['Acumulado'] / df_pareto['VALOR_VENTA_O'].sum()
        
        # Gráfico Pareto
        fig_par = go.Figure()
        fig_par.add_trace(go.Bar(x=df_pareto.index, y=df_pareto['VALOR_VENTA_O'], name='Venta', marker_color='#3b82f6'))
        fig_par.add_trace(go.Scatter(x=df_pareto.index, y=df_pareto['Pct_Acum'], name='% Acumulado', yaxis='y2', line=dict(color='#ef4444', width=2)))
        
        fig_par.update_layout(
            title="Concentración de Venta por SKU",
            yaxis=dict(title="Venta $"),
            yaxis2=dict(title="% Acumulado", overlaying='y', side='right', range=[0, 110]),
            showlegend=False
        )
        # Linea de corte 80%
        fig_par.add_hline(y=80, line_dash="dot", annotation_text="Corte 80%", annotation_position="bottom right", yref="y2")
        st.plotly_chart(fig_par, use_container_width=True)
        
        top_skus = df_pareto[df_pareto['Pct_Acum'] <= 80].shape[0]
        total_skus = df_pareto.shape[0]
        st.success(f"💡 **Insight:** {top_skus} productos ({top_skus/total_skus:.1%}) generan el 80% de la venta.")

# --- TAB 5: GEO ANALYTICS (SOLUCIONADO) ---
with tabs[4]:
    st.subheader("📍 Análisis Geográfico y Rentabilidad Regional")
    
    col_g1, col_g2 = st.columns([2, 1])
    
    # Agrupación Geográfica
    df_geo = df_act.groupby('Poblacion_Real').agg(
        Venta=('VALOR_VENTA_O', 'sum'),
        Clientes=('Key_Nit', 'nunique')
    ).reset_index()
    df_geo['Ticket_Promedio'] = df_geo['Venta'] / df_geo['Clientes']
    df_geo = df_geo[df_geo['Venta'] > 0].sort_values('Venta', ascending=False)
    
    with col_g1:
        # Scatter Plot Avanzado
        fig_geo = px.scatter(
            df_geo, x="Clientes", y="Ticket_Promedio",
            size="Venta", color="Venta",
            hover_name="Poblacion_Real",
            title="Matriz de Oportunidad Regional",
            labels={"Ticket_Promedio": "Venta Promedio por Cliente ($)", "Clientes": "# Clientes Activos"},
            color_continuous_scale="Viridis",
            size_max=60,
            log_x=True # Escala logarítmica para visualizar mejor pequeñas vs grandes ciudades
        )
        st.plotly_chart(fig_geo, use_container_width=True)
        
    with col_g2:
        st.markdown("**Top Poblaciones por Venta**")
        st.dataframe(
            df_geo[['Poblacion_Real', 'Venta', 'Ticket_Promedio']].head(10)
            .style.format({'Venta': '${:,.0f}', 'Ticket_Promedio': '${:,.0f}'})
            .background_gradient(subset=['Venta'], cmap="Blues"),
            use_container_width=True,
            hide_index=True
        )
        
        if 'NO IDENTIFICADO' in df_geo['Poblacion_Real'].values:
            st.warning("⚠️ Hay ventas en 'NO IDENTIFICADO'. Revisa la pestaña de Debugger en el Sidebar.")

# --- TAB 6: DATA EXPLORER ---
with tabs[5]:
    st.subheader("🔎 Explorador Granular")
    
    with st.expander("Filtros Avanzados de Búsqueda"):
        search_txt = st.text_input("Buscar (Cliente, Producto o NIT):")
    
    df_view = df_act[['anio', 'mes', 'Key_Nit', 'NOMBRE_CLIENTE_I', 'Poblacion_Real', 'Marca_Master', 'NOMBRE_PRODUCTO_K', 'VALOR_VENTA_O']].copy()
    
    if search_txt:
        mask = df_view.astype(str).apply(lambda x: x.str.contains(search_txt, case=False)).any(axis=1)
        df_view = df_view[mask]
        
    st.dataframe(
        df_view.sort_values('VALOR_VENTA_O', ascending=False).head(500)
        .style.format({'VALOR_VENTA_O': '${:,.2f}'}),
        use_container_width=True
    )
    
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')

    csv = convert_df(df_view)
    st.download_button("📥 Descargar Data Filtrada (CSV)", data=csv, file_name="data_master_ultra.csv", mime="text/csv")
