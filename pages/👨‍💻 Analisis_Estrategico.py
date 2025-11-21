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
# 1. CONFIGURACIÓN ULTRA (UI/UX & ESTILO)
# ==============================================================================
st.set_page_config(
    page_title="Master Brain Ultra | Ops & Growth Intelligence", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Profesional para Dashboards Ejecutivos
st.markdown("""
<style>
    :root { --primary: #0f172a; --accent: #3b82f6; --success: #10b981; --warning: #f59e0b; --danger: #ef4444; --bg-card: #ffffff; }
    .main { background-color: #f1f5f9; }
    h1, h2, h3 { color: var(--primary); font-family: 'Segoe UI', sans-serif; font-weight: 800; }
    
    /* Tarjetas KPIs */
    .metric-card {
        background: var(--bg-card);
        border-left: 4px solid var(--accent);
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 15px;
    }
    .metric-val { font-size: 2rem; font-weight: 800; color: var(--primary); }
    .metric-lbl { font-size: 0.8rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; }
    .metric-delta { font-size: 0.9rem; font-weight: 600; margin-top: 5px; }
    .pos { color: var(--success); } .neg { color: var(--danger); }

    /* Insights Box */
    .insight-box {
        background-color: #eff6ff; border: 1px solid #bfdbfe;
        padding: 15px; border-radius: 8px; color: #1e40af;
        font-size: 0.95rem; margin-bottom: 20px;
    }
    .warning-box {
        background-color: #fef2f2; border: 1px solid #fecaca;
        padding: 15px; border-radius: 8px; color: #991b1b;
        font-size: 0.95rem; margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MOTORES DE LIMPIEZA Y LÓGICA DE NEGOCIO
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
    # Mapa reducido para optimización
    mapa = {'33': 'OCEANIC', '34': 'PROTECTO', '40': 'ICO', '41': 'TERINSA', '58': 'PINTUCO', '60': 'INTERPON', '73': 'CORAL', '87': 'SIKKENS', '91': 'SIKKENS', '50': 'PINTUCO MEGA'}
    return mapa.get(codigo, None)

def clasificar_estrategia_master(row):
    prod = normalizar_texto(row.get('NOMBRE_PRODUCTO_K', ''))
    aliados = ['ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', '3M', 'SISTA', 'SINTESOLDA']
    for a in aliados: 
        if a in prod: return a
    raw_code = str(row.get('CODIGO_MARCA_N', '0')).split('.')[0].strip()
    marca = obtener_nombre_marca_por_codigo(raw_code)
    return marca if marca else 'OTROS'

def asignar_hub_logistico(ciudad):
    """Asigna la ciudad a uno de los Hubs propios o a Foráneo"""
    c = normalizar_texto(ciudad)
    if c in ['PEREIRA', 'DOSQUEBRADAS', 'SANTA ROSA DE CABAL', 'LA VIRGINIA']: return 'HUB PEREIRA/DOSQ'
    if c in ['MANIZALES', 'VILLAMARIA', 'CHINCHINA', 'NEIRA']: return 'HUB MANIZALES'
    if c in ['ARMENIA', 'CALARCA', 'CIRCASIA', 'TEBAIDA', 'MONTENEGRO', 'QUIMBAYA']: return 'HUB ARMENIA'
    if c in ['CARTAGO', 'ANSERMA', 'RIOSUCIO']: return 'ZONA CERCANA'
    return 'NACIONAL / FORANEO'

# ==============================================================================
# 3. CARGA DE DATOS (DROPBOX + CSV)
# ==============================================================================
@st.cache_data(ttl=3600)
def cargar_datos_maestros():
    try:
        APP_KEY = st.secrets["dropbox"]["app_key"]
        APP_SECRET = st.secrets["dropbox"]["app_secret"]
        REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]
        with dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN) as dbx:
            _, res = dbx.files_download(path='/clientes_detalle.xlsx') # Ajusta ruta si es necesario
            with io.BytesIO(res.content) as stream:
                df = pd.read_excel(stream)
                # Busca columnas dinámicamente
                col_k = next((c for c in df.columns if 'cod' in c.lower() and 'cli' in c.lower()), None)
                col_c = next((c for c in df.columns if 'ciudad' in c.lower()), None)
                if col_k and col_c:
                    df['Key_Nit'] = df[col_k].apply(limpiar_codigo_master)
                    df['Poblacion_Real'] = df[col_c].apply(normalizar_texto)
                    df['Hub_Logistico'] = df['Poblacion_Real'].apply(asignar_hub_logistico)
                    return df[['Key_Nit', 'Poblacion_Real', 'Hub_Logistico']].drop_duplicates(subset=['Key_Nit'])
    except Exception as e:
        st.error(f"Error Dropbox: {e}")
    return pd.DataFrame(columns=['Key_Nit', 'Poblacion_Real', 'Hub_Logistico'])

# ==============================================================================
# 4. PROCESAMIENTO DE VENTAS E INTEGRACIÓN
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.warning("⚠️ Esperando carga de archivo maestro en Home...")
    st.stop()

# Carga base cruda y renombra columnas por índice para seguridad
df_raw = st.session_state.df_ventas.copy()
try:
    # Asumimos estructura estándar | separada
    cols_map = {0: 'anio', 1: 'mes', 2: 'dia', 7: 'COD_CLIENTE', 8: 'NOM_CLIENTE', 10: 'PRODUCTO', 11: 'CATEGORIA', 13: 'COD_MARCA', 14: 'VALOR'}
    # Verifica si existe col dia (índice 2), si no, crea dummy
    if df_raw.shape[1] > 14:
        df_raw = df_raw.rename(columns={df_raw.columns[i]: name for i, name in cols_map.items() if i < len(df_raw.columns)})
    else:
        # Fallback si faltan columnas
        st.error("El CSV no tiene suficientes columnas.")
        st.stop()
except:
    st.error("Error mapeando columnas.")
    st.stop()

# Limpieza Tipos
df_raw['VALOR'] = pd.to_numeric(df_raw['VALOR'], errors='coerce').fillna(0)
df_raw['anio'] = pd.to_numeric(df_raw['anio'], errors='coerce').fillna(0).astype(int)
df_raw['mes'] = pd.to_numeric(df_raw['mes'], errors='coerce').fillna(1).astype(int)
# Manejo de días: si no existe columna día real, asumimos 15 para YTD, o tratamos de leerla
if 'dia' not in df_raw.columns: 
    df_raw['dia'] = 15 
else:
    df_raw['dia'] = pd.to_numeric(df_raw['dia'], errors='coerce').fillna(28).astype(int)

df_raw['Key_Nit'] = df_raw['COD_CLIENTE'].apply(limpiar_codigo_master)

# Cruce con Geo-Data
with st.spinner("🔄 Integrando Logística y Finanzas..."):
    df_raw['Marca_Master'] = df_raw.apply(clasificar_estrategia_master, axis=1)
    df_clientes = cargar_datos_maestros()
    
    if not df_clientes.empty:
        df_full = pd.merge(df_raw, df_clientes, on='Key_Nit', how='left')
        df_full['Poblacion_Real'] = df_full['Poblacion_Real'].fillna('SIN ASIGNAR')
        df_full['Hub_Logistico'] = df_full['Hub_Logistico'].fillna('NACIONAL / FORANEO')
    else:
        df_full = df_raw.copy()
        df_full['Poblacion_Real'] = 'SIN DATA'
        df_full['Hub_Logistico'] = 'SIN DATA'

# ==============================================================================
# 5. LÓGICA YTD (YEAR TO DATE) ESTRICTA
# ==============================================================================
today = date.today()
current_year = today.year
current_month = today.month
current_day = today.day

# Filtro Maestro de Fechas para Comparabilidad Real
# Solo tomamos registros cuya fecha (Mes/Día) sea <= a la fecha actual, para cualquier año
df_full['Fecha_Simulada'] = pd.to_datetime(dict(year=df_full['anio'], month=df_full['mes'], day=df_full['dia'].clip(1, 28)))
limit_date_tuple = (current_month, current_day)

def es_ytd_valido(row):
    # Retorna True si el mes/dia del registro es anterior o igual a hoy
    if row['mes'] < current_month: return True
    if row['mes'] == current_month and row['dia'] <= current_day: return True
    return False

df_full['Is_YTD'] = df_full.apply(es_ytd_valido, axis=1)
df_ytd = df_full[df_full['Is_YTD'] == True].copy() # Solo data comparable a la fecha

# ==============================================================================
# 6. INTERFAZ DE SIMULACIÓN (SIDEBAR)
# ==============================================================================
st.title("🧠 Master Brain Ultra | Strategic Operations Center")
st.markdown(f"**Análisis YTD al {today.strftime('%d-%b')}:** Comparando periodos equivalentes.")

with st.sidebar:
    st.header("🎛️ Simulador Operativo")
    
    st.subheader("1. Estructura de Costos")
    margen_bruto_pct = st.slider("Margen Bruto Promedio (%)", 10, 50, 25, 1) / 100
    costo_pedido_local = st.number_input("Costo Logístico Local (Por Pedido)", value=15000, step=1000, help="Costo de entregar en Pereira/Dosq/Manizales/Armenia")
    costo_pedido_nal = st.number_input("Costo Logístico Nacional (Por Pedido)", value=45000, step=5000)
    
    st.subheader("2. Filtros Globales")
    anios_disp = sorted(df_ytd['anio'].unique(), reverse=True)
    anio_obj = st.selectbox("Año Objetivo", anios_disp, index=0)
    anio_base = st.selectbox("Año Base (Comparativo)", [a for a in anios_disp if a != anio_obj], index=0)
    
    hubs_sel = st.multiselect("Hubs Logísticos", df_ytd['Hub_Logistico'].unique(), default=df_ytd['Hub_Logistico'].unique())

# Filtrado Principal
df_obj = df_ytd[(df_ytd['anio'] == anio_obj) & (df_ytd['Hub_Logistico'].isin(hubs_sel))]
df_base = df_ytd[(df_ytd['anio'] == anio_base) & (df_ytd['Hub_Logistico'].isin(hubs_sel))]

# ==============================================================================
# 7. CÁLCULOS AVANZADOS (KPIs & MODELADO)
# ==============================================================================

# Métricas Cabecera
vta_act = df_obj['VALOR'].sum()
vta_ant = df_base['VALOR'].sum()
delta_vta = ((vta_act - vta_ant) / vta_ant) * 100 if vta_ant > 0 else 100

# Utilidad Bruta Simulada
utilidad_bruta = vta_act * margen_bruto_pct

# Costo de Servir (Simulación basada en # Facturas y Ubicación)
# Asumimos que cada registro único de Mes/Dia/Cliente es un "Pedido/Despacho"
pedidos_obj = df_obj.groupby(['Hub_Logistico', 'Key_Nit', 'mes', 'dia']).size().reset_index().rename(columns={0:'items'})
num_pedidos_totales = len(pedidos_obj)

def calcular_costo_logistico(row):
    if 'HUB' in row['Hub_Logistico'] or 'CERCANA' in row['Hub_Logistico']:
        return costo_pedido_local
    return costo_pedido_nal

pedidos_obj['Costo_Logistico'] = pedidos_obj.apply(calcular_costo_logistico, axis=1)
costo_servir_total = pedidos_obj['Costo_Logistico'].sum()

# Utilidad Neta Operacional (Simulada)
utilidad_neta = utilidad_bruta - costo_servir_total
margen_neto_real = (utilidad_neta / vta_act * 100) if vta_act > 0 else 0

# Layout KPIs
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Venta YTD (Corte Hoy)", f"${vta_act/1e6:,.1f}M", f"{delta_vta:+.1f}%")
c2.metric("Utilidad Bruta Est.", f"${utilidad_bruta/1e6:,.1f}M", f"{margen_bruto_pct*100:.0f}% Margen")
c3.metric("Costo de Servir", f"${costo_servir_total/1e6:,.1f}M", f"-{(costo_servir_total/vta_act)*100:.1f}% s/Venta", delta_color="inverse")
c4.metric("Utilidad Neta Oper.", f"${utilidad_neta/1e6:,.1f}M", f"{margen_neto_real:.1f}% Real")
c5.metric("# Pedidos/Despachos", f"{num_pedidos_totales:,}", f"Freq: {num_pedidos_totales/df_obj['Key_Nit'].nunique():.1f} ped/clie")

st.divider()

# ==============================================================================
# 8. TABS DE ANÁLISIS PROFUNDO
# ==============================================================================
tabs = st.tabs(["🚚 Costo de Servir & Rentabilidad", "🔄 Optimización Logística (Batching)", "📈 Crecimiento & Fuga", "🗺️ Geo-Expansión", "📝 AI Insights"])

# --- TAB 1: RENTABILIDAD POR HUB Y CIUDAD ---
with tabs[0]:
    col_r1, col_r2 = st.columns([2, 1])
    
    # Preparar datos por Ciudad
    df_city = df_obj.groupby(['Poblacion_Real', 'Hub_Logistico']).agg(
        Venta=('VALOR', 'sum'),
        Clientes=('Key_Nit', 'nunique'),
        Items=('PRODUCTO', 'count') # Proxy de complejidad
    ).reset_index()
    
    # Calcular Pedidos por ciudad
    pedidos_city = pedidos_obj.groupby('Poblacion_Real')['Costo_Logistico'].sum().reset_index()
    df_city = pd.merge(df_city, pedidos_city, on='Poblacion_Real', how='left')
    
    df_city['Margen_Contribucion'] = (df_city['Venta'] * margen_bruto_pct) - df_city['Costo_Logistico']
    df_city['ROI_Logistico'] = df_city['Margen_Contribucion'] / df_city['Costo_Logistico']
    
    with col_r1:
        st.subheader("Matriz de Eficiencia: ¿Dónde ganamos dinero real?")
        fig_bubble = px.scatter(
            df_city, 
            x="Costo_Logistico", 
            y="Margen_Contribucion",
            size="Venta", 
            color="Hub_Logistico",
            hover_name="Poblacion_Real",
            title="Costo de Servir vs. Contribución Neta (Tamaño = Venta)",
            labels={"Costo_Logistico": "Gasto Logístico Total ($)", "Margen_Contribucion": "Ganancia Neta ($)"},
            height=500
        )
        # Línea de equilibrio
        fig_bubble.add_shape(type="line", x0=0, y0=0, x1=df_city['Costo_Logistico'].max(), y1=0, line=dict(color="Red", width=2, dash="dash"))
        st.plotly_chart(fig_bubble, use_container_width=True)

    with col_r2:
        st.subheader("Top Ciudades 'Destructoras de Valor'")
        st.caption("Ciudades donde el costo logístico (frecuencia x distancia) se come el margen.")
        df_neg = df_city[df_city['Margen_Contribucion'] < 0].sort_values('Margen_Contribucion')
        if df_neg.empty:
            st.success("✅ ¡Increíble! Ninguna ciudad está dando pérdidas operativas con los parámetros actuales.")
        else:
            st.dataframe(df_neg[['Poblacion_Real', 'Venta', 'Costo_Logistico', 'Margen_Contribucion']].style.format("${:,.0f}"), use_container_width=True)
            
        st.subheader("Rentabilidad por Hub")
        df_hub_roi = df_city.groupby('Hub_Logistico')[['Margen_Contribucion', 'Costo_Logistico']].sum().reset_index()
        df_hub_roi['Ratio'] = df_hub_roi['Margen_Contribucion'] / df_hub_roi['Costo_Logistico']
        st.dataframe(df_hub_roi.sort_values('Ratio', ascending=False).style.format({'Margen_Contribucion':'${:,.0f}', 'Costo_Logistico':'${:,.0f}', 'Ratio':'{:.2f}x'}), use_container_width=True)

# --- TAB 2: SIMULACIÓN DE BATCHING (AGRUPACIÓN) ---
with tabs[1]:
    st.subheader("🧪 Laboratorio de Optimización Operativa")
    st.markdown("""
    **Hipótesis:** Si agrupamos los pedidos de clientes en días específicos (ej. Martes y Viernes), reducimos la frecuencia de despachos 
    sin perder venta, aumentando el margen neto.
    """)
    
    col_b1, col_b2 = st.columns(2)
    
    with col_b1:
        # Datos actuales
        freq_actual = num_pedidos_totales
        costo_actual = costo_servir_total
        
        # Simulación: Reducir frecuencia en un % (Estimado por consolidación)
        factor_consolidacion = st.slider("Nivel de Consolidación Esperado (Batching)", 0, 50, 20, format="%d%% Savings") / 100
        
        freq_simulada = int(freq_actual * (1 - factor_consolidacion))
        costo_simulado = costo_actual * (1 - factor_consolidacion)
        ahorro = costo_actual - costo_simulado
        
        st.markdown(f"#### 📉 Ahorro Potencial: :green[${ahorro/1e6:,.1f} Millones]")
        st.markdown(f"Pasarías de **{freq_actual:,}** despachos a **{freq_simulada:,}** despachos en el periodo.")
        
        fig_waterfall = go.Figure(go.Waterfall(
            orientation = "v",
            measure = ["relative", "relative", "total"],
            x = ["Utilidad Actual", "Ahorro Logístico", "Utilidad Optimizada"],
            y = [utilidad_neta, ahorro, utilidad_neta + ahorro],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
            decreasing = {"marker":{"color":"Maroon"}},
            increasing = {"marker":{"color":"Teal"}},
            totals = {"marker":{"color":"#0f172a"}}
        ))
        fig_waterfall.update_layout(title="Impacto en P&L por Optimización", height=400)
        st.plotly_chart(fig_waterfall, use_container_width=True)
        
    with col_b2:
        st.markdown("#### 📅 Frecuencia de Compra por Cliente (Días promedio entre pedidos)")
        # Calcular días entre pedidos por cliente
        df_fechas = df_obj[['Key_Nit', 'Fecha_Simulada']].drop_duplicates().sort_values(['Key_Nit', 'Fecha_Simulada'])
        df_fechas['Prev_Fecha'] = df_fechas.groupby('Key_Nit')['Fecha_Simulada'].shift(1)
        df_fechas['Dias_Diff'] = (df_fechas['Fecha_Simulada'] - df_fechas['Prev_Fecha']).dt.days
        
        avg_freq = df_fechas.groupby('Key_Nit')['Dias_Diff'].mean().fillna(0)
        
        fig_hist = px.histogram(avg_freq, x="Dias_Diff", nbins=20, title="Distribución de Frecuencia de Compra", labels={'Dias_Diff': 'Días entre pedidos'})
        fig_hist.add_vline(x=7, line_dash="dash", line_color="green", annotation_text="Ciclo Semanal")
        st.plotly_chart(fig_hist, use_container_width=True)
        st.caption("Clientes a la izquierda (0-5 días) son candidatos ideales para 'Batching' (agrupar pedidos).")

# --- TAB 3: CRECIMIENTO Y FUGA ---
with tabs[2]:
    c_g1, c_g2 = st.columns(2)
    
    with c_g1:
        st.subheader("Análisis de Fuga (Churn Rate)")
        cli_act = set(df_obj['Key_Nit'])
        cli_ant = set(df_base['Key_Nit'])
        
        perdidos = cli_ant - cli_act
        nuevos = cli_act - cli_ant
        retenidos = cli_act.intersection(cli_ant)
        
        fig_sankey = go.Figure(data=[go.Sankey(
            node = dict(
              pad = 15, thickness = 20, line = dict(color = "black", width = 0.5),
              label = [f"Cartera {anio_base} ({len(cli_ant)})", f"Cartera {anio_obj} ({len(cli_act)})", "Perdidos", "Retenidos", "Nuevos"],
              color = ["blue", "blue", "red", "green", "green"]
            ),
            link = dict(
              source = [0, 0, 4, 3], # Indices correspondientes a labels
              target = [2, 3, 1, 1],
              value = [len(perdidos), len(retenidos), len(nuevos), len(retenidos)]
          ))])
        fig_sankey.update_layout(title="Flujo de Clientes (Retention Flow)", font_size=10)
        st.plotly_chart(fig_sankey, use_container_width=True)
        
    with c_g2:
        st.subheader("Impacto Económico del Churn")
        venta_perdida = df_base[df_base['Key_Nit'].isin(perdidos)]['VALOR'].sum()
        venta_nueva = df_obj[df_obj['Key_Nit'].isin(nuevos)]['VALOR'].sum()
        
        st.metric("Venta en Riesgo (Perdida)", f"${venta_perdida/1e6:,.1f}M", delta_color="inverse")
        st.metric("Venta Nueva (Captación)", f"${venta_nueva/1e6:,.1f}M")
        
        st.markdown("##### Top Clientes Perdidos")
        top_lost = df_base[df_base['Key_Nit'].isin(perdidos)].groupby('NOM_CLIENTE')['VALOR'].sum().nlargest(5)
        st.table(top_lost.apply(lambda x: f"${x:,.0f}"))

# --- TAB 4: GEO EXPANSIÓN ---
with tabs[3]:
    st.subheader("🗺️ Estrategia Territorial")
    col_geo1, col_geo2 = st.columns([3, 1])
    
    with col_geo1:
        # Treemap de Geografía
        fig_tree = px.treemap(
            df_city, 
            path=[px.Constant("Colombia"), 'Hub_Logistico', 'Poblacion_Real'], 
            values='Venta',
            color='Margen_Contribucion',
            color_continuous_scale='RdYlGn',
            midpoint=0,
            title="Mapa de Calor: Venta (Tamaño) vs Rentabilidad (Color)"
        )
        st.plotly_chart(fig_tree, use_container_width=True)
        
    with col_geo2:
        st.markdown("**Oportunidades de Expansión**")
        st.info("""
        **Lógica de Expansión:**
        Busca ciudades en el mapa con color **Verde Intenso** pero tamaño **Pequeño**.
        Significa que es rentable ir, pero vendemos poco. ¡Ahí hay que atacar!
        """)
        
        st.markdown("**Alerta de Retracción**")
        st.error("""
        **Lógica de Cierre:**
        Busca ciudades **Rojas** de cualquier tamaño.
        Si es grande y roja, renegocia precios o fletes urgente.
        """)

# --- TAB 5: AI INSIGHTS (GENERACIÓN DE TEXTO) ---
with tabs[4]:
    st.subheader("📝 Informe Ejecutivo Automático")
    
    # 1. Insight General
    trend = "CRECIMIENTO" if delta_vta > 0 else "CONTRACCIÓN"
    color_trend = "blue" if delta_vta > 0 else "red"
    
    st.markdown(f"""
    <div class="insight-box">
    <strong>ANÁLISIS DE TENDENCIA:</strong> A la fecha ({today.strftime('%d-%b')}), la compañía muestra una tendencia de <span style='color:{color_trend}; font-weight:bold'>{trend}</span> 
    del <strong>{delta_vta:+.1f}%</strong> respecto al mismo periodo del año anterior. 
    Se han facturado <strong>${vta_act/1e6:,.1f}M</strong>. El costo de servir estimado es del <strong>{(costo_servir_total/vta_act)*100:.1f}%</strong> sobre la venta.
    </div>
    """, unsafe_allow_html=True)
    
    # 2. Insight Operativo (Hubs)
    best_hub = df_hub_roi.sort_values('Margen_Contribucion', ascending=False).iloc[0]
    worst_hub = df_hub_roi.sort_values('Margen_Contribucion', ascending=True).iloc[0]
    
    st.markdown(f"""
    <div class="insight-box">
    <strong>INTELIGENCIA OPERATIVA:</strong> El hub más rentable es <strong>{best_hub['Hub_Logistico']}</strong>, generando una contribución neta de 
    <strong>${best_hub['Margen_Contribucion']/1e6:,.1f}M</strong> (Ratio {best_hub['Ratio']:.1f}x). 
    <br><br>
    ⚠️ <strong>ATENCIÓN:</strong> El hub/zona con menor desempeño es <strong>{worst_hub['Hub_Logistico']}</strong>. 
    Se recomienda revisar rutas o incrementar ticket promedio para diluir el costo logístico.
    </div>
    """, unsafe_allow_html=True)
    
    # 3. Recomendación de Batching
    if ahorro > 0:
        st.markdown(f"""
        <div class="insight-box" style="background-color:#f0fdf4; border-color:#bbf7d0; color:#166534;">
        <strong>OPORTUNIDAD DE EFICIENCIA:</strong> Según la simulación, implementar una política de agrupación de pedidos (Batching) 
        para reducir frecuencias en un {factor_consolidacion*100:.0f}%, liberaría <strong>${ahorro/1e6:,.1f} Millones</strong> 
        directamente a la utilidad neta sin vender un peso más.
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Master Brain Ultra v2.0 | Desarrollado para Toma de Decisiones de Alto Nivel | Datos Confidenciales")
