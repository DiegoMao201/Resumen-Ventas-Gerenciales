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
    page_title="Master Brain Ultra | Operations & Growth Hub", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Ejecutivo, Limpio y con Nuevos Estilos para Insights
st.markdown("""
<style>
    /* Paleta de Colores Corporativa Premium */
    :root { --primary: #0f172a; --accent: #3b82f6; --success: #10b981; --danger: #ef4444; --bg-light: #f8fafc; --warning: #f59e0b; }
    
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

    /* Cajas de Insights de IA */
    .insight-box {
        background-color: #eff6ff; border: 1px solid #bfdbfe;
        padding: 20px; border-radius: 10px; color: #1e40af;
        font-size: 1rem; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .insight-title { font-weight: 800; display: block; margin-bottom: 8px; text-transform: uppercase; font-size: 0.8rem;}
    
    /* Tabs Personalizados */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9; border-radius: 8px; padding: 10px 24px; border: none; font-weight: 600;
    }
    .stTabs [aria-selected="true"] { background-color: var(--primary); color: white; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MOTORES DE LIMPIEZA, LÓGICA E INTELIGENCIA OPERATIVA
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
    texto_busqueda = f"{prod_name} {cat_name}"
    for aliado in aliados:
        if aliado in texto_busqueda: return aliado
    raw_code = str(row.get('CODIGO_MARCA_N', '0')).split('.')[0].strip()
    nombre_marca = obtener_nombre_marca_por_codigo(raw_code)
    if nombre_marca: return nombre_marca
    return 'OTROS'

# --- NUEVO MOTOR LOGÍSTICO ---
def asignar_hub_logistico(ciudad):
    """Clasifica la ciudad en uno de tus Hubs operativos"""
    c = normalizar_texto(ciudad)
    if c in ['PEREIRA', 'DOSQUEBRADAS', 'SANTA ROSA DE CABAL', 'LA VIRGINIA']: return 'HUB PEREIRA/DOSQ (LOCAL)'
    if c in ['MANIZALES', 'VILLAMARIA', 'CHINCHINA', 'NEIRA']: return 'HUB MANIZALES'
    if c in ['ARMENIA', 'CALARCA', 'CIRCASIA', 'TEBAIDA', 'MONTENEGRO', 'QUIMBAYA']: return 'HUB ARMENIA'
    if c in ['CARTAGO', 'ANSERMA', 'RIOSUCIO', 'VITERBO']: return 'ZONA CERCANA'
    return 'NACIONAL / FORANEO'

# ==============================================================================
# 3. CONEXIÓN DROPBOX
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
            key_col_match = next((val for key, val in cols_actuales.items() if key.lower() == 'cod. cliente'), None)
            city_col_match = next((val for key, val in cols_actuales.items() if key.lower() == 'ciudad'), None)
            vendedor_match = next((val for key, val in cols_actuales.items() if key.lower() == 'nomvendedor'), None)

            if not key_col_match: return pd.DataFrame()

            df_final = df_drop.copy()
            df_final['Key_Nit'] = df_final[key_col_match].apply(limpiar_codigo_master)
            
            if city_col_match:
                df_final['Poblacion_Real'] = df_final[city_col_match].apply(normalizar_texto)
            else:
                df_final['Poblacion_Real'] = 'SIN ASIGNAR'

            # --- AQUI ASIGNAMOS EL HUB EN LA BASE DE CLIENTES ---
            df_final['Hub_Logistico'] = df_final['Poblacion_Real'].apply(asignar_hub_logistico)

            if vendedor_match:
                df_final['Vendedor'] = df_final[vendedor_match].apply(normalizar_texto)
            else:
                df_final['Vendedor'] = 'GENERAL'
                
            return df_final.drop_duplicates(subset=['Key_Nit'])[['Key_Nit', 'Poblacion_Real', 'Hub_Logistico', 'Vendedor']]

    except Exception as e:
        st.error(f"Error Dropbox: {str(e)}")
        return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO DE VENTAS & LÓGICA YTD (YEAR TO DATE)
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.info("👋 Por favor carga el archivo maestro de ventas (CSV separado por |) en el Home.")
    st.stop()

df_raw = st.session_state.df_ventas.copy()

# Mapeo
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
    # INTENTO DE DETECTAR COLUMNA DÍA (Si existe en pos 2, usualmente)
    if len(df_raw.columns) > 2:
        # Verificamos si la columna 2 parece ser un día (1-31)
        if df_raw.iloc[:, 2].apply(lambda x: str(x).isnumeric()).all():
             df_raw['dia'] = df_raw.iloc[:, 2].astype(int)
        else:
             df_raw['dia'] = 15 # Dummy si no hay día
    else:
        df_raw['dia'] = 15
except Exception as e:
    st.error(f"Error columnas: {e}")
    st.stop()

df_raw['VALOR_VENTA_O'] = pd.to_numeric(df_raw['VALOR_VENTA_O'], errors='coerce').fillna(0)
df_raw['anio'] = pd.to_numeric(df_raw['anio'], errors='coerce').fillna(datetime.now().year).astype(int)
df_raw['mes'] = pd.to_numeric(df_raw['mes'], errors='coerce').fillna(1).astype(int)
df_raw['Key_Nit'] = df_raw['CODIGO_CLIENTE_H'].apply(limpiar_codigo_master)

# CRUCE
with st.spinner("⚙️ Ejecutando Data Fusion Engine (Ventas + Geo + Logística)..."):
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
        df_full['Hub_Logistico'] = 'SIN DATA'
        df_full['Vendedor'] = 'GENERAL'

# --- FILTRO YTD ESTRICTO (LO MEJOR DE LO MEJOR) ---
# Esto asegura que compares Peras con Peras a la fecha de HOY
today = date.today()
current_month = today.month
current_day = today.day

def es_ytd_valido(row):
    # Si el mes es menor al actual, entra seguro.
    if row['mes'] < current_month: return True
    # Si el mes es el actual, revisamos el día.
    if row['mes'] == current_month:
        # Si tenemos columna dia real, filtramos. Si es dummy (15), dejamos pasar todo el mes si hoy > 15.
        return row['dia'] <= current_day
    return False

df_full['Is_YTD'] = df_full.apply(es_ytd_valido, axis=1)
# Dataset Maestro Filtrado para Comparación Justa
df_master = df_full[df_full['Is_YTD'] == True].copy()

# ==============================================================================
# 5. DASHBOARD
# ==============================================================================

st.title("🧠 Master Brain Ultra | Strategic Operations Center")
st.markdown(f"**Informe de Inteligencia Operacional y Crecimiento** | Corte de Datos: **{today.strftime('%d de %B')}** (Comparativo YTD Real)")
st.divider()

# --- SIDEBAR RECARGADO ---
with st.sidebar:
    st.header("🎛️ Centro de Control")
    
    # Fechas
    anios = sorted(df_master['anio'].unique(), reverse=True)
    c_s1, c_s2 = st.columns(2)
    if len(anios) > 0:
        anio_obj = c_s1.selectbox("Año Objetivo", anios, index=0)
        list_base = [a for a in anios if a != anio_obj]
        anio_base = c_s2.selectbox("Año Base", list_base if list_base else anios, index=0)
    
    st.markdown("---")
    st.subheader("🧪 Simulador Operativo")
    st.caption("Ajusta parámetros para ver tu Rentabilidad Real")
    
    margen_bruto_pct = st.slider("Margen Bruto Promedio (%)", 10, 60, 25, 1, help="¿Cuánto ganas bruto por producto antes de gastos?") / 100
    costo_pedido_local = st.number_input("Costo Logístico Local ($)", value=12000, step=1000, help="Costo estimado de entregar un pedido en Pereira/Manizales/Armenia")
    costo_pedido_nal = st.number_input("Costo Logístico Nacional ($)", value=45000, step=5000, help="Costo flota/flete para foráneos")
    
    st.markdown("---")
    st.caption("SEGMENTACIÓN")
    hubs_sel = st.multiselect("Filtrar Hubs", df_master['Hub_Logistico'].unique(), default=df_master['Hub_Logistico'].unique())
    sel_city = st.multiselect("Filtrar Ciudades", sorted(df_master['Poblacion_Real'].unique()))

# --- FILTRADO GLOBAL ---
df_f = df_master[df_master['Hub_Logistico'].isin(hubs_sel)].copy()
if sel_city: df_f = df_f[df_f['Poblacion_Real'].isin(sel_city)]

df_act = df_f[df_f['anio'] == anio_obj]
df_ant = df_f[df_f['anio'] == anio_base]

# --- CÁLCULOS FINANCIEROS Y OPERATIVOS AVANZADOS ---
# 1. Ventas
vta_act = df_act['VALOR_VENTA_O'].sum()
vta_ant = df_ant['VALOR_VENTA_O'].sum()
diff_pct = ((vta_act - vta_ant) / vta_ant * 100) if vta_ant > 0 else 0

# 2. Operaciones (Proxy de Pedidos: Combinación Clave-Mes-Día única)
# Asumimos que un cliente comprando en una fecha es UN despacho/factura
df_act['Pedido_ID'] = df_act['Key_Nit'].astype(str) + '-' + df_act['mes'].astype(str) + '-' + df_act['dia'].astype(str)
num_pedidos = df_act['Pedido_ID'].nunique()
freq_compra = num_pedidos / df_act['Key_Nit'].nunique() if df_act['Key_Nit'].nunique() > 0 else 0

# 3. Costo de Servir (Cost-to-Serve)
def calcular_costo_fila(row):
    if 'HUB' in row['Hub_Logistico'] or 'CERCANA' in row['Hub_Logistico']:
        return costo_pedido_local
    return costo_pedido_nal

# Estimamos costo total multiplicando costo unitario por número de pedidos únicos
# Para hacerlo rápido, lo hacemos agrupado
df_pedidos_unicos = df_act[['Pedido_ID', 'Hub_Logistico']].drop_duplicates()
df_pedidos_unicos['Costo_Envio'] = df_pedidos_unicos.apply(calcular_costo_fila, axis=1)
costo_servir_total = df_pedidos_unicos['Costo_Envio'].sum()

# 4. Rentabilidad
utilidad_bruta = vta_act * margen_bruto_pct
utilidad_neta_operativa = utilidad_bruta - costo_servir_total
margen_neto_real_pct = (utilidad_neta_operativa / vta_act * 100) if vta_act > 0 else 0

# --- TARJETAS KPI PRINCIPALES ---
c1, c2, c3, c4, c5 = st.columns(5)

def kpi_card_ultra(col, title, val, delta_txt, sub_txt, color_delta="pos"):
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">{title}</div>
        <div class="metric-val">{val}</div>
        <div class="metric-delta"><span class="{color_delta}">{delta_txt}</span> <span style="color:#64748b; font-size:0.8rem;">{sub_txt}</span></div>
    </div>
    """, unsafe_allow_html=True)

kpi_card_ultra(c1, "Venta YTD", f"${vta_act/1e6:,.1f}M", f"{diff_pct:+.1f}%", "vs Año Ant")
kpi_card_ultra(c2, "Utilidad Neta (Est)", f"${utilidad_neta_operativa/1e6:,.1f}M", f"{margen_neto_real_pct:.1f}%", "Margen Real", "pos" if margen_neto_real_pct > 10 else "neg")
kpi_card_ultra(c3, "Costo Logístico", f"${costo_servir_total/1e6:,.1f}M", f"{(costo_servir_total/vta_act)*100:.1f}%", "s/Venta", "neg")
kpi_card_ultra(c4, "Despachos Total", f"{num_pedidos:,}", f"{freq_compra:.1f}", "Freq. Promedio")
ticket_prom = vta_act / num_pedidos if num_pedidos > 0 else 0
kpi_card_ultra(c5, "Ticket / Despacho", f"${ticket_prom:,.0f}", "---", "Valor Medio")

# --- TABS PROFUNDOS ---
tabs = st.tabs([
    "🚚 Rentabilidad & Cost-to-Serve", 
    "🧪 Optimización & Batching",
    "📈 Drivers de Crecimiento", 
    "👥 Retención de Clientes", 
    "🌍 Geo-Expansión",
    "📝 AI Insights (Resumen)"
])

# TAB 1: RENTABILIDAD
with tabs[0]:
    st.subheader("Análisis de Costo de Servir por Población")
    col_r1, col_r2 = st.columns([2,1])
    
    # Preparar Data
    df_city_ops = df_act.groupby(['Poblacion_Real', 'Hub_Logistico']).agg(
        Venta=('VALOR_VENTA_O', 'sum'),
        Clientes=('Key_Nit', 'nunique'),
        Pedidos_Unicos=('Pedido_ID', 'nunique')
    ).reset_index()
    
    # Costo por fila de ciudad
    df_city_ops['Costo_Unitario'] = df_city_ops.apply(calcular_costo_fila, axis=1)
    df_city_ops['Costo_Total_Logistica'] = df_city_ops['Pedidos_Unicos'] * df_city_ops['Costo_Unitario']
    df_city_ops['Utilidad_Neta'] = (df_city_ops['Venta'] * margen_bruto_pct) - df_city_ops['Costo_Total_Logistica']
    df_city_ops['ROI_Logistico'] = df_city_ops['Utilidad_Neta'] / df_city_ops['Costo_Total_Logistica']
    
    with col_r1:
        fig_bubble = px.scatter(
            df_city_ops, 
            x="Costo_Total_Logistica", y="Utilidad_Neta",
            size="Venta", color="Hub_Logistico",
            hover_name="Poblacion_Real",
            title="Matriz de Eficiencia: Gasto Logístico vs. Utilidad Real",
            labels={"Costo_Total_Logistica": "Costo Operativo ($)", "Utilidad_Neta": "Ganancia Neta ($)"},
            height=500
        )
        # Linea de perdida
        fig_bubble.add_shape(type="line", x0=0, y0=0, x1=df_city_ops['Costo_Total_Logistica'].max(), y1=0, line=dict(color="Red", dash="dot"))
        st.plotly_chart(fig_bubble, use_container_width=True)
    
    with col_r2:
        st.markdown("**Top Ciudades: Menor Margen**")
        st.caption("Ciudades donde el flete se come la ganancia. Revisar precios o frecuencias.")
        st.dataframe(
            df_city_ops.sort_values('Utilidad_Neta').head(10)[['Poblacion_Real', 'Venta', 'Costo_Total_Logistica', 'Utilidad_Neta']]
            .style.format("${:,.0f}").background_gradient(cmap='RdYlGn', subset=['Utilidad_Neta']),
            use_container_width=True
        )

# TAB 2: BATCHING
with tabs[1]:
    st.subheader("Simulador de Agrupación de Pedidos (Batching)")
    st.markdown("""
    **Hipótesis:** Si en lugar de despachar todos los días a Pereira/Manizales/Armenia, agrupamos pedidos y despachamos 2 o 3 veces por semana, 
    reducimos el número de viajes sin perder venta, aumentando directamente la utilidad.
    """)
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        ahorro_pct = st.slider("Objetivo de Reducción de Viajes (%)", 0, 50, 20) / 100
        ahorro_dinero = costo_servir_total * ahorro_pct
        nueva_utilidad = utilidad_neta_operativa + ahorro_dinero
        
        st.metric("Dinero Recuperado (Ahorro)", f"${ahorro_dinero/1e6:,.1f} Millones", "Directo al Ebitda")
        
        fig_w = go.Figure(go.Waterfall(
            measure = ["relative", "relative", "total"],
            x = ["Utilidad Actual", "Ahorro Logístico", "Utilidad Potencial"],
            y = [utilidad_neta_operativa, ahorro_dinero, nueva_utilidad],
            text = [f"${utilidad_neta_operativa/1e6:.1f}M", f"+${ahorro_dinero/1e6:.1f}M", f"${nueva_utilidad/1e6:.1f}M"],
            decreasing = {"marker":{"color":"#ef4444"}}, increasing = {"marker":{"color":"#10b981"}}, totals = {"marker":{"color":"#0f172a"}}
        ))
        fig_w.update_layout(title="Impacto Financiero del Batching", height=350)
        st.plotly_chart(fig_w, use_container_width=True)

    with col_b2:
        st.markdown("**Análisis de Frecuencia Actual**")
        # Histograma de días entre pedidos
        df_dates = df_act[['Key_Nit', 'mes', 'dia']].drop_duplicates().sort_values(['Key_Nit', 'mes', 'dia'])
        # Simplificación: Contar pedidos por cliente
        counts = df_act.groupby('Key_Nit')['Pedido_ID'].nunique().reset_index()
        fig_h = px.histogram(counts, x="Pedido_ID", nbins=20, title="Distribución: # Pedidos por Cliente en el Periodo", labels={'Pedido_ID': 'Cantidad de Pedidos'})
        st.plotly_chart(fig_h, use_container_width=True)
        st.info("Clientes en la cola derecha (muchos pedidos) son candidatos ideales para reducir frecuencia.")

# TAB 3: DRIVERS (WATERFALL)
with tabs[2]:
    col_d1, col_d2 = st.columns([3,1])
    with col_d1:
        dim = st.radio("Analizar variación por:", ["Hub_Logistico", "Marca_Master", "CATEGORIA_L"], horizontal=True)
        g_act = df_act.groupby(dim)['VALOR_VENTA_O'].sum()
        g_ant = df_ant.groupby(dim)['VALOR_VENTA_O'].sum()
        df_diff = pd.DataFrame({'Act': g_act, 'Ant': g_ant}).fillna(0)
        df_diff['Diff'] = df_diff['Act'] - df_diff['Ant']
        df_diff = df_diff.sort_values('Diff', ascending=False)
        
        fig_water = go.Figure(go.Waterfall(
            orientation="v", measure=["relative"] * len(df_diff),
            x=df_diff.index, y=df_diff['Diff'],
            decreasing={"marker":{"color":"#ef4444"}}, increasing={"marker":{"color":"#10b981"}}
        ))
        fig_water.update_layout(title=f"Explicación del Crecimiento por {dim}")
        st.plotly_chart(fig_water, use_container_width=True)
    with col_d2:
        st.dataframe(df_diff[['Diff']].style.format("${:,.0f}").background_gradient(cmap='RdYlGn'), use_container_width=True)

# TAB 4: RETENCIÓN
with tabs[3]:
    cli_act_set = set(df_act['Key_Nit'])
    cli_ant_set = set(df_ant['Key_Nit'])
    lost = cli_ant_set - cli_act_set
    new = cli_act_set - cli_ant_set
    retained = cli_act_set.intersection(cli_ant_set)
    
    c_ch1, c_ch2, c_ch3 = st.columns(3)
    c_ch1.metric("Clientes Retenidos", len(retained))
    c_ch2.metric("Nuevos Clientes", len(new), f"+{len(new)}")
    c_ch3.metric("Clientes Perdidos", len(lost), f"-{len(lost)}", delta_color="inverse")
    
    st.markdown("##### ¿Quiénes nos dejaron? (Y cuánto compraban)")
    if len(lost) > 0:
        lost_data = df_ant[df_ant['Key_Nit'].isin(lost)].groupby(['NOMBRE_CLIENTE_I', 'Poblacion_Real'])['VALOR_VENTA_O'].sum().reset_index().sort_values('VALOR_VENTA_O', ascending=False).head(10)
        st.dataframe(lost_data.style.format({'VALOR_VENTA_O': '${:,.0f}'}), use_container_width=True)
    else:
        st.success("¡Cero fugas de clientes en este periodo!")

# TAB 5: GEO MAPA
with tabs[4]:
    st.subheader("Estrategia Territorial")
    # Treemap para ver Jerarquia: Hub -> Ciudad -> Venta
    fig_tree = px.treemap(
        df_city_ops, 
        path=[px.Constant("Territorio"), 'Hub_Logistico', 'Poblacion_Real'], 
        values='Venta',
        color='Utilidad_Neta',
        color_continuous_scale='RdYlGn',
        midpoint=0,
        title="Mapa de Calor: Tamaño (Ventas) vs. Color (Utilidad Real)"
    )
    st.plotly_chart(fig_tree, use_container_width=True)

# TAB 6: AI INSIGHTS
with tabs[5]:
    st.subheader("📝 Informe Ejecutivo Automático (AI Generated)")
    
    # Lógica de Texto
    trend_txt = "CRECIMIENTO SÓLIDO" if diff_pct > 5 else "ESTABILIDAD" if diff_pct > -5 else "CONTRACCIÓN"
    color_trend = "green" if diff_pct > 0 else "red"
    
    top_hub = df_city_ops.groupby('Hub_Logistico')['Utilidad_Neta'].sum().idxmax()
    low_hub = df_city_ops.groupby('Hub_Logistico')['Utilidad_Neta'].sum().idxmin()
    
    st.markdown(f"""
    <div class="insight-box">
        <span class="insight-title">1. DIAGNÓSTICO GLOBAL</span>
        La operación muestra una tendencia de <strong style="color:{color_trend}">{trend_txt}</strong> con una variación del 
        <strong>{diff_pct:+.1f}%</strong> YTD. La utilidad neta operativa estimada es del <strong>{margen_neto_real_pct:.1f}%</strong>, 
        después de descontar un gasto logístico aproximado de <strong>${costo_servir_total/1e6:,.1f} Millones</strong>.
    </div>
    
    <div class="insight-box">
        <span class="insight-title">2. FOCO REGIONAL</span>
        El Hub Logístico más eficiente es <strong>{top_hub}</strong>, aportando la mayor masa de utilidad. 
        Por el contrario, se detectan oportunidades de mejora en <strong>{low_hub}</strong>, donde el costo de servir 
        está presionando los márgenes.
    </div>
    
    <div class="insight-box">
        <span class="insight-title">3. OPORTUNIDAD DE OPTIMIZACIÓN (BATCHING)</span>
        Con una frecuencia de compra promedio de <strong>{freq_compra:.1f} pedidos/cliente</strong>, existe una oportunidad clara. 
        Si se implementa una política de agrupación de pedidos para reducir viajes en un 20%, la compañía podría liberar 
        caja por valor de <strong>${(costo_servir_total*0.2)/1e6:,.1f} Millones</strong> adicionales.
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Master Brain Ultra v3.0 | Strategic Intelligence | Datos Confidenciales")
