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
    /* Colores Corporativos: Azul Profundo y Gris Acero */
    :root { --primary: #0f172a; --accent: #3b82f6; --bg-light: #f1f5f9; }
    
    .main { background-color: #ffffff; }
    h1, h2, h3 { color: var(--primary); font-family: 'Segoe UI', sans-serif; font-weight: 700; }
    
    /* Tarjetas de Métricas */
    .metric-card {
        background: white;
        border-left: 4px solid var(--accent);
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 10px;
    }
    .metric-val { font-size: 2rem; font-weight: 800; color: var(--primary); }
    .metric-lbl { font-size: 0.9rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px; }
    .metric-delta { font-size: 1rem; font-weight: 600; }
    .pos { color: #10b981; }
    .neg { color: #ef4444; }

    /* Tabs Personalizados */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        padding: 10px 20px;
        border: 1px solid #e2e8f0;
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
    """Normalización estricta para cruces de bases de datos."""
    if not isinstance(texto, str): 
        return str(texto) if pd.notnull(texto) else "SIN INFO"
    texto = str(texto)
    texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sin_tildes.upper().strip()

def limpiar_nit(nit):
    """Limpia NIT manejando errores de Excel (floats, notación científica)."""
    if pd.isna(nit): return "0"
    s_nit = str(nit)
    if '.' in s_nit: # Manejo de 900123.0
        s_nit = s_nit.split('.')[0]
    s_nit = s_nit.split('-')[0] # Quitar DV
    s_limpio = re.sub(r'[^0-9]', '', s_nit)
    return s_limpio.lstrip('0') if s_limpio else "0"

def obtener_nombre_marca_por_codigo(codigo):
    # Mapa extendido basado en tu lógica
    mapa = {
        '33': 'OCEANIC PAINTS', '34': 'PROTECTO', '35': 'OTROS',
        '37': 'INTERNATIONAL PAINT', '40': 'ICO', '41': 'TERINSA',
        '50': 'PINTUCO (MEGA)', '54': 'INTERNATIONAL PAINT', '55': 'COLORANTS LATAM',
        '56': 'PINTUCO PROFESIONAL', '57': 'PINTUCO (MEGA)', '58': 'PINTUCO',
        '59': 'MADETEC', '60': 'INTERPON', '61': 'VARIOUS', '62': 'ICO',
        '63': 'TERINSA', '64': 'PINTUCO', '65': 'TERCEROS (NON-AN)',
        '66': 'ICO PACKAGING', '67': 'AUTOMOTIVE OEM', '68': 'RESICOAT',
        '73': 'CORAL', '87': 'SIKKENS', '89': 'WANDA', '90': 'SIKKENS AUTOCOAT',
        '91': 'SIKKENS', '94': 'PROTECTO PROFESIONAL'
    }
    return mapa.get(codigo, None)

def clasificar_estrategia_master(row):
    # 1. Lista Blanca (Aliados)
    prod_name = normalizar_texto(row.get('NOMBRE_PRODUCTO_K', ''))
    cat_name = normalizar_texto(row.get('CATEGORIA_L', ''))
    aliados = ['ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', '3M', 'SISTA', 'SINTESOLDA']
    texto_busqueda = f"{prod_name} {cat_name}"
    
    for aliado in aliados:
        if aliado in texto_busqueda: return aliado

    # 2. Código Marca
    raw_code = str(row.get('CODIGO_MARCA_N', '0')).split('.')[0].strip()
    nombre_marca = obtener_nombre_marca_por_codigo(raw_code)
    if nombre_marca: return nombre_marca

    return 'OTROS'

# ==============================================================================
# 3. CONEXIÓN DROPBOX (SOPORTE EXCEL .XLSX)
# ==============================================================================
@st.cache_data(ttl=3600)
def cargar_poblaciones_dropbox_excel():
    """Lee Excel (.xlsx) desde Dropbox usando openpyxl."""
    try:
        try:
            APP_KEY = st.secrets["dropbox"]["app_key"]
            APP_SECRET = st.secrets["dropbox"]["app_secret"]
            REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]
        except:
            st.warning("⚠️ Configura st.secrets para Dropbox.")
            return pd.DataFrame()

        with dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN) as dbx:
            # Intentar ruta raíz
            ruta = '/clientes_detalle.xlsx' 
            try:
                metadata, res = dbx.files_download(path=ruta)
            except:
                try:
                    ruta = '/data/clientes_detalle.xlsx'
                    metadata, res = dbx.files_download(path=ruta)
                except:
                    st.error("❌ No encontré 'clientes_detalle.xlsx' en Dropbox.")
                    return pd.DataFrame()

            # LEER EXCEL BINARIO
            with io.BytesIO(res.content) as stream:
                df_drop = pd.read_excel(stream, engine='openpyxl')
            
            # Limpieza
            df_drop.columns = [c.strip().upper() for c in df_drop.columns]
            
            # Buscar columnas clave
            col_nit = next((c for c in df_drop.columns if 'NIF' in c or 'NIT' in c), None)
            col_ciudad = next((c for c in df_drop.columns if 'CIUDAD' in c or 'POBLACION' in c), None)
            col_canal = next((c for c in df_drop.columns if 'CANAL' in c or 'SECTOR' in c), None) # Opcional: Canal

            if not col_nit: return pd.DataFrame()
            
            df_drop['Key_Nit'] = df_drop[col_nit].apply(limpiar_nit)
            
            cols_to_keep = ['Key_Nit']
            
            if col_ciudad:
                df_drop['Poblacion_Real'] = df_drop[col_ciudad].apply(normalizar_texto)
                cols_to_keep.append('Poblacion_Real')
            else:
                df_drop['Poblacion_Real'] = 'SIN ASIGNAR'
                cols_to_keep.append('Poblacion_Real')

            # Si quieres añadir el Canal/Sector para análisis de margen (proxy)
            if col_canal:
                df_drop['Canal_Cliente'] = df_drop[col_canal].apply(normalizar_texto)
                cols_to_keep.append('Canal_Cliente')

            return df_drop.drop_duplicates(subset=['Key_Nit'])[cols_to_keep]

    except Exception as e:
        st.error(f"Error Dropbox: {str(e)}")
        return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO Y DATOS
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.info("👋 Por favor carga el archivo maestro de ventas en el Home.")
    st.stop()

df_raw = st.session_state.df_ventas.copy()

# Mapeo Inteligente
col_map = {
    df_raw.columns[0]: 'anio',
    df_raw.columns[1]: 'mes',
    df_raw.columns[7]: 'CODIGO_CLIENTE_H', 
    df_raw.columns[8]: 'NOMBRE_CLIENTE_I', # Agregamos Nombre Cliente
    df_raw.columns[10]: 'NOMBRE_PRODUCTO_K',
    df_raw.columns[11]: 'CATEGORIA_L',
    df_raw.columns[13]: 'CODIGO_MARCA_N',
    df_raw.columns[14]: 'VALOR_VENTA_O'
}
final_map = {k: v for k, v in col_map.items() if k in df_raw.columns}
df_raw = df_raw.rename(columns=final_map)

# Conversiones
df_raw['VALOR_VENTA_O'] = pd.to_numeric(df_raw['VALOR_VENTA_O'], errors='coerce').fillna(0)
df_raw['anio'] = pd.to_numeric(df_raw['anio'], errors='coerce').fillna(2024).astype(int)
df_raw['Key_Nit'] = df_raw['CODIGO_CLIENTE_H'].apply(limpiar_nit)

# Clasificación
with st.spinner("⚙️ Procesando lógica de negocio..."):
    df_raw['Marca_Master'] = df_raw.apply(clasificar_estrategia_master, axis=1)
    
    # Cargar Geo
    df_clientes = cargar_poblaciones_dropbox_excel()
    
    if not df_clientes.empty:
        df_full = pd.merge(df_raw, df_clientes, on='Key_Nit', how='left')
        df_full['Poblacion_Real'] = df_full['Poblacion_Real'].fillna('OTROS')
        if 'Canal_Cliente' not in df_full.columns: df_full['Canal_Cliente'] = 'GENERAL'
    else:
        df_full = df_raw.copy()
        df_full['Poblacion_Real'] = 'SIN DATA'
        df_full['Canal_Cliente'] = 'GENERAL'

# ==============================================================================
# 5. DASHBOARD "ULTRA"
# ==============================================================================

st.title("🧠 Master Brain Ultra")
st.markdown("Sistema Avanzado de Análisis de Crecimiento y Rentabilidad")
st.divider()

# --- SIDEBAR GLOBAL ---
with st.sidebar:
    st.header("🎛️ Filtros Maestros")
    anios = sorted(df_full['anio'].unique(), reverse=True)
    anio_obj = st.selectbox("Año Objetivo (Actual)", anios, index=0)
    anio_base = st.selectbox("Año Base (Comparativo)", [a for a in anios if a != anio_obj], index=0)
    
    st.markdown("---")
    # Multiselect inteligente
    all_brands = sorted(df_full['Marca_Master'].unique())
    sel_brands = st.multiselect("Marcas", all_brands, default=all_brands)
    
    all_cities = sorted(df_full['Poblacion_Real'].unique())
    sel_city = st.multiselect("Poblaciones", all_cities) # Ahora multiselect para comparar varias

# --- FILTRADO DE DATOS ---
df_f = df_full[df_full['Marca_Master'].isin(sel_brands)]
if sel_city:
    df_f = df_f[df_f['Poblacion_Real'].isin(sel_city)]

# Separar periodos para cálculos Delta
df_act = df_f[df_f['anio'] == anio_obj]
df_ant = df_f[df_f['anio'] == anio_base]

# --- KPI HEADER (Diseño Personalizado) ---
vta_act = df_act['VALOR_VENTA_O'].sum()
vta_ant = df_ant['VALOR_VENTA_O'].sum()
diff_abs = vta_act - vta_ant
diff_pct = (diff_abs / vta_ant * 100) if vta_ant > 0 else 100

# Clientes con compra > 0
cli_act = df_act[df_act['VALOR_VENTA_O']>0]['Key_Nit'].nunique()
cli_ant = df_ant[df_ant['VALOR_VENTA_O']>0]['Key_Nit'].nunique()
diff_cli = cli_act - cli_ant

c1, c2, c3, c4 = st.columns(4)

def kpi_card(col, title, val, delta, prefix="$"):
    color = "pos" if delta >= 0 else "neg"
    delta_str = f"{delta:,.1f}%" if prefix=="$" else f"{delta:,.0f}"
    symbol = "▲" if delta >= 0 else "▼"
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">{title}</div>
        <div class="metric-val">{prefix}{val:,.0f}</div>
        <div class="metric-delta {color}">{symbol} {delta_str} vs AA</div>
    </div>
    """, unsafe_allow_html=True)

kpi_card(c1, "Venta Total", vta_act/1e6, diff_pct, "$") # En Millones
kpi_card(c2, "Gap de Crecimiento", diff_abs/1e6, diff_pct, "$")
kpi_card(c3, "Clientes Activos", cli_act, diff_cli, "#")
# Ticket Promedio Anual
ticket = vta_act / cli_act if cli_act > 0 else 0
kpi_card(c4, "Ticket Promedio/Cliente", ticket, 0, "$")

# --- TABS ANALÍTICOS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Drivers de Crecimiento (Waterfall)", 
    "🌍 Geo-Rentabilidad", 
    "📦 Mix & Pareto (80/20)",
    "🔎 Explorador de Datos"
])

# --- TAB 1: WATERFALL DE CRECIMIENTO (EL ANÁLISIS REAL) ---
with tab1:
    st.subheader(f"Desglose de la Variación: {anio_base} vs {anio_obj}")
    st.markdown("Este gráfico muestra **exactamente** qué Marcas o Categorías construyeron (o destruyeron) valor.")

    dim_view = st.radio("Ver crecimiento por:", ["Marca_Master", "CATEGORIA_L", "Canal_Cliente"], horizontal=True)

    # Preparar datos para Waterfall
    g_act = df_act.groupby(dim_view)['VALOR_VENTA_O'].sum()
    g_ant = df_ant.groupby(dim_view)['VALOR_VENTA_O'].sum()
    
    df_w = pd.DataFrame({'Actual': g_act, 'Anterior': g_ant}).fillna(0)
    df_w['Variacion'] = df_w['Actual'] - df_w['Anterior']
    df_w['Contribucion_Pct'] = (df_w['Variacion'] / vta_ant) * 100 # KPI CLAVE
    
    # Filtrar ruidito (variaciones muy pequeñas)
    df_w = df_w.sort_values('Variacion', ascending=False)
    
    # Top 15 movers para el gráfico
    df_chart = df_w.head(15)
    
    fig_water = go.Figure(go.Waterfall(
        name="20", orientation="v",
        measure=["relative"] * len(df_chart),
        x=df_chart.index,
        y=df_chart['Variacion'],
        text=df_chart['Variacion'].apply(lambda x: f'{x/1e6:+.1f}M'),
        textposition="outside",
        connector={"line":{"color":"rgb(63, 63, 63)"}},
        decreasing={"marker":{"color":"#ef4444"}},
        increasing={"marker":{"color":"#10b981"}}
    ))
    fig_water.update_layout(title=f"Puente de Ventas por {dim_view}", height=500)
    st.plotly_chart(fig_water, use_container_width=True)

    st.markdown("#### 📊 Tabla de Impacto al Crecimiento")
    st.markdown("La columna **Contribución** indica cuántos puntos porcentuales de crecimiento total aportó esa línea.")
    
    # Formato condicional
    st.dataframe(
        df_w.style.format({
            'Actual': '${:,.0f}', 
            'Anterior': '${:,.0f}', 
            'Variacion': '${:,.0f}',
            'Contribucion_Pct': '{:+.2f}%'
        }).background_gradient(subset=['Variacion'], cmap='RdYlGn'),
        use_container_width=True
    )

# --- TAB 2: GEO-RENTABILIDAD ---
with tab2:
    st.subheader("Matriz de Eficiencia Geográfica")
    
    col_geo1, col_geo2 = st.columns([3, 1])
    
    with col_geo1:
        # Agrupar por Población
        df_geo = df_act.groupby('Poblacion_Real').agg(
            Venta=('VALOR_VENTA_O', 'sum'),
            Clientes=('Key_Nit', 'nunique'),
            Transacciones=('VALOR_VENTA_O', 'count')
        ).reset_index()
        
        df_geo = df_geo[df_geo['Venta'] > 0]
        df_geo['Venta_por_Cliente'] = df_geo['Venta'] / df_geo['Clientes']
        
        # Scatter Plot Mejorado
        fig_geo = px.scatter(
            df_geo,
            x="Clientes", y="Venta_por_Cliente",
            size="Venta", color="Venta_por_Cliente",
            hover_name="Poblacion_Real",
            title="Potencial por Población (Tamaño burbuja = Venta Total)",
            labels={"Venta_por_Cliente": "Venta Promedio x Cliente ($)", "Clientes": "# Clientes Activos"},
            color_continuous_scale="Viridis",
            log_x=True, log_y=True # Logarítmico para ver mejor los datos dispersos
        )
        st.plotly_chart(fig_geo, use_container_width=True)

    with col_geo2:
        st.markdown("**Top Poblaciones (Crecimiento)**")
        # Calcular crecimiento por ciudad
        g_geo_act = df_act.groupby('Poblacion_Real')['VALOR_VENTA_O'].sum()
        g_geo_ant = df_ant.groupby('Poblacion_Real')['VALOR_VENTA_O'].sum()
        df_ggeo = pd.DataFrame({'Act': g_geo_act, 'Ant': g_geo_ant}).fillna(0)
        df_ggeo['Var'] = df_ggeo['Act'] - df_ggeo['Ant']
        
        st.dataframe(
            df_ggeo.sort_values('Var', ascending=False).head(10)[['Var']]
            .style.format("${:,.0f}").background_gradient(cmap="Greens"),
            height=400
        )

# --- TAB 3: PARETO Y MIX ---
with tab3:
    c_p1, c_p2 = st.columns(2)
    
    with c_p1:
        st.subheader("Ley de Pareto (80/20) - Productos")
        # Calcular Pareto de Productos
        df_prod = df_act.groupby('NOMBRE_PRODUCTO_K')['VALOR_VENTA_O'].sum().sort_values(ascending=False).reset_index()
        df_prod['Acumulado'] = df_prod['VALOR_VENTA_O'].cumsum()
        df_prod['Porcentaje_Acum'] = (df_prod['Acumulado'] / df_prod['VALOR_VENTA_O'].sum()) * 100
        
        # Cortar donde sea < 80%
        top_80 = df_prod[df_prod['Porcentaje_Acum'] <= 80]
        count_80 = len(top_80)
        total_skus = len(df_prod)
        
        st.metric("SKUs que hacen el 80% de la venta", f"{count_80} / {total_skus}", 
                  f"Son el {(count_80/total_skus*100):.1f}% del portafolio")
        
        fig_pareto = px.area(df_prod, x=df_prod.index, y='Porcentaje_Acum', title="Curva de Concentración de Venta")
        fig_pareto.add_hline(y=80, line_dash="dash", line_color="red")
        st.plotly_chart(fig_pareto, use_container_width=True)

    with c_p2:
        st.subheader("Mix de Categorías (Treemap)")
        fig_tree = px.treemap(
            df_act, 
            path=['Marca_Master', 'CATEGORIA_L'], 
            values='VALOR_VENTA_O',
            color='VALOR_VENTA_O',
            color_continuous_scale='Blues',
            title="Distribución Jerárquica del Portafolio"
        )
        st.plotly_chart(fig_tree, use_container_width=True)

# --- TAB 4: EXPLORADOR DE DATOS (DETALLE) ---
with tab4:
    st.subheader("🔎 Data Drill-Down")
    
    # Filtros locales
    txt_search = st.text_input("Buscar Cliente o Producto Específico:", "")
    
    df_show = df_act[['Fecha_Dt', 'Key_Nit', 'NOMBRE_CLIENTE_I', 'Poblacion_Real', 'Marca_Master', 'NOMBRE_PRODUCTO_K', 'VALOR_VENTA_O']].copy()
    
    if txt_search:
        mask = df_show.astype(str).apply(lambda x: x.str.contains(txt_search, case=False)).any(axis=1)
        df_show = df_show[mask]
        
    st.dataframe(
        df_show.sort_values('VALOR_VENTA_O', ascending=False).head(1000).style.format({'VALOR_VENTA_O': '${:,.2f}'}), 
        use_container_width=True
    )
