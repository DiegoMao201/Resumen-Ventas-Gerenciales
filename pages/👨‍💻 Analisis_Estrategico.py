# ==============================================================================
# 🧠 MASTER BRAIN - ANÁLISIS ESTRATÉGICO & LOGÍSTICO 360°
# Archivo: pages/Analisis_Estrategico.py
# Versión: ULTRA (Integración Ventas + Cartera + Población)
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import unicodedata
import io
import dropbox

st.set_page_config(page_title="Master Brain: Estrategia & Logística", page_icon="♟️", layout="wide")

# ==============================================================================
# 🎨 ESTILOS EJECUTIVOS
# ==============================================================================
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-left: 5px solid #2E86C1;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    h1, h2, h3 { color: #154360; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #EBF5FB; border-radius: 5px;
        font-weight: 600; color: #154360;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #2E86C1; color: white;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔧 FUNCIONES MAESTRAS DE LIMPIEZA Y CARGA
# ==============================================================================
def normalizar_texto(texto):
    if not isinstance(texto, str): return str(texto) if texto is not None else ""
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').replace('_', ' ').strip()
    except: return str(texto)

def clasificar_marca_estrategica(marca_original):
    """Agrupa marcas pequeñas en PINTUCO vs el resto de marcas estratégicas."""
    marca = normalizar_texto(marca_original)
    vip = ['ABRACOL', 'ARTECOLA', 'INDUMA', 'SAINT GOBAIN', 'YALE', 'ALLEGION', 'SEGUREX', 'ATLAS', 'POLVOS', 'DELTA', 'GOYA', 'MASTERD']
    for v in vip:
        if v in marca: return v
    return "PINTUCO (AGRUPADO)"

# --- CARGADOR ESPECÍFICO PARA CARTERA (POBLACIÓN) ---
@st.cache_data(ttl=3600)
def cargar_datos_poblacion_dropbox():
    """Descarga cartera_detalle para obtener la Población y Días de Cartera."""
    # Intentamos recuperar credenciales de la sesión principal
    if 'APP_CONFIG' in st.session_state:
        pass # Ya tenemos acceso
    else:
        # Fallback si no se cargó el config, usamos secrets directamente
        pass
    
    try:
        # Ruta hardcodeada según tu indicación
        ruta_cartera = "/data/cartera_detalle.csv" 
        
        with dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, 
                             app_secret=st.secrets.dropbox.app_secret, 
                             oauth2_refresh_token=st.secrets.dropbox.refresh_token) as dbx:
            _, res = dbx.files_download(path=ruta_cartera)
            contenido = res.content.decode('latin-1')
            
            # Lectura asumiendo estructura estándar pipe '|' o coma ',' (Ajuste automático)
            try:
                df = pd.read_csv(io.StringIO(contenido), sep='|', engine='python', on_bad_lines='warn')
                if df.shape[1] < 3: # Si falló el separador pipe
                    df = pd.read_csv(io.StringIO(contenido), sep=',', engine='python', on_bad_lines='warn')
            except:
                return pd.DataFrame()

            # LIMPIEZA CRÍTICA DE CARTERA
            # Buscamos columnas clave: NIT/ID, POBLACION, DIAS, SALDO
            # Normalizamos columnas
            df.columns = [normalizar_texto(c) for c in df.columns]
            
            # Mapeo de columnas (Ajusta si tus nombres son muy diferentes)
            col_id = next((c for c in df.columns if 'NIT' in c or 'CLIENTE' in c or 'ID' in c), 'NIT')
            col_pob = next((c for c in df.columns if 'POBLACION' in c or 'CIUDAD' in c), 'POBLACION')
            col_dias = next((c for c in df.columns if 'DIA' in c), 'DIAS')
            col_saldo = next((c for c in df.columns if 'SALDO' in c or 'VALOR' in c), 'SALDO')

            # Renombrar para estandarizar
            df = df.rename(columns={col_id: 'cliente_id', col_pob: 'Poblacion', col_dias: 'Dias_Cartera', col_saldo: 'Saldo_Cartera'})
            
            # Asegurar tipos
            df['cliente_id'] = df['cliente_id'].astype(str).str.strip()
            df['Poblacion'] = df['Poblacion'].apply(normalizar_texto)
            df['Dias_Cartera'] = pd.to_numeric(df['Dias_Cartera'], errors='coerce').fillna(0)
            df['Saldo_Cartera'] = pd.to_numeric(df['Saldo_Cartera'], errors='coerce').fillna(0)
            
            # Agrupar por cliente para tener un maestro único (Promedio ponderado de días sería ideal, pero usaremos max o promedio simple por ahora)
            # Priorizamos la Población más frecuente si el cliente tiene varias sedes
            df_maestro = df.groupby('cliente_id').agg({
                'Poblacion': lambda x: x.mode()[0] if not x.mode().empty else 'SIN POBLACION',
                'Dias_Cartera': 'max', # Tomamos el peor escenario de días
                'Saldo_Cartera': 'sum'
            }).reset_index()
            
            return df_maestro

    except Exception as e:
        st.error(f"Error conectando a cartera_detalle: {e}")
        return pd.DataFrame()

# ==============================================================================
# 1. FUSIÓN DE DATOS (DATA BLENDING)
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.error("⚠️ Datos núcleo no cargados. Ve a 'Resumen Mensual' primero.")
    st.stop()

# 1.1 Carga Ventas
df_ventas = st.session_state.df_ventas.copy()
# Filtro neto
df_ventas['TipoDocumento'] = df_ventas['TipoDocumento'].astype(str)
df = df_ventas[df_ventas['TipoDocumento'].str.contains('FACTURA|NOTA.*CREDITO', na=False, case=False, regex=True)].copy()
df['valor_venta'] = pd.to_numeric(df['valor_venta'], errors='coerce').fillna(0)
df['unidades_vendidas'] = pd.to_numeric(df['unidades_vendidas'], errors='coerce').fillna(0)
df['costo_unitario'] = pd.to_numeric(df['costo_unitario'], errors='coerce').fillna(0)
df['Margen_Pesos'] = df['valor_venta'] - (df['unidades_vendidas'] * df['costo_unitario'])
df['Marca_Estrategica'] = df['marca_producto'].apply(clasificar_marca_estrategica) if 'marca_producto' in df.columns else df['categoria_producto'].apply(clasificar_marca_estrategica)

# 1.2 Carga Población (Cartera)
with st.spinner("🔄 Cruzando información logística con cartera_detalle..."):
    df_poblacion = cargar_datos_poblacion_dropbox()

# 1.3 Cruce Maestro (Left Join)
if not df_poblacion.empty:
    # Asegurar llave de cruce
    df['cliente_id'] = df['cliente_id'].astype(str).str.strip()
    # Cruce
    df_full = pd.merge(df, df_poblacion, on='cliente_id', how='left')
    df_full['Poblacion'] = df_full['Poblacion'].fillna('SIN INFORMACION LOGISTICA')
else:
    df_full = df.copy()
    df_full['Poblacion'] = "SIN DATA CARTERA"
    df_full['Dias_Cartera'] = 0

# ==============================================================================
# 2. PANEL DE CONTROL LATERAL
# ==============================================================================
st.sidebar.title("🎛️ Centro de Comando")
st.sidebar.markdown("---")

# Filtros Temporales
anios = sorted(df_full['anio'].unique(), reverse=True)
anio_sel = st.sidebar.selectbox("Año Principal", anios, index=0)
anio_comp = st.sidebar.selectbox("Año Comparativo", [a for a in anios if a != anio_sel] + ["Ninguno"], index=0)

# Filtros Dimensionales
marcas = ["TODAS"] + sorted(df_full['Marca_Estrategica'].unique())
marca_sel = st.sidebar.selectbox("Marca / Agrupación", marcas)

# Filtro Geográfico (Nuevo)
regiones = ["TODAS"] + sorted(df_full['Poblacion'].unique())
region_sel = st.sidebar.selectbox("Población / Ciudad", regiones)

# Aplicación de Filtros
df_filtrado = df_full[df_full['anio'] == anio_sel].copy()
df_previo = df_full[df_full['anio'] == anio_comp].copy() if anio_comp != "Ninguno" else pd.DataFrame()

if marca_sel != "TODAS":
    df_filtrado = df_filtrado[df_filtrado['Marca_Estrategica'] == marca_sel]
    if not df_previo.empty: df_previo = df_previo[df_previo['Marca_Estrategica'] == marca_sel]

if region_sel != "TODAS":
    df_filtrado = df_filtrado[df_filtrado['Poblacion'] == region_sel]
    if not df_previo.empty: df_previo = df_previo[df_previo['Poblacion'] == region_sel]

# ==============================================================================
# 3. KPI SUMMARY (HEADLINE METRICS)
# ==============================================================================
st.markdown(f"### 🚀 Desempeño Estratégico: {anio_sel} {'vs ' + str(anio_comp) if anio_comp != 'Ninguno' else ''}")

venta_act = df_filtrado['valor_venta'].sum()
margen_act = df_filtrado['Margen_Pesos'].sum()
margen_pct_act = (margen_act / venta_act * 100) if venta_act else 0
dias_cart_ponderado = df_filtrado['Dias_Cartera'].mean() # Aproximación

venta_ant = df_previo['valor_venta'].sum() if not df_previo.empty else 0
margen_ant = df_previo['Margen_Pesos'].sum() if not df_previo.empty else 0

var_venta = ((venta_act - venta_ant) / venta_ant * 100) if venta_ant else 0
var_margen = ((margen_act - margen_ant) / margen_ant * 100) if margen_ant else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Ventas Totales", f"${venta_act:,.0f}", f"{var_venta:+.1f}%", delta_color="normal")
k2.metric("Margen Bruto ($)", f"${margen_act:,.0f}", f"{var_margen:+.1f}%", delta_color="normal")
k3.metric("Rentabilidad %", f"{margen_pct_act:.2f}%", f"{(margen_pct_act - ((margen_ant/venta_ant*100) if venta_ant else 0)):+.2f} pp")
k4.metric("Días Cartera (Prom)", f"{dias_cart_ponderado:.0f} días", help="Promedio de días de cartera de los clientes filtrados")

# ==============================================================================
# 4. PESTAÑAS DE ANÁLISIS AVANZADO
# ==============================================================================
tab_growth, tab_geo, tab_profit, tab_portfolio = st.tabs([
    "📈 Crecimiento & Tendencias", 
    "🗺️ Logística & Costo por Servir",
    "💎 Matriz de Rentabilidad",
    "💰 Salud de Cartera"
])

# --- TAB 1: CRECIMIENTO & COMPARATIVAS ---
with tab_growth:
    col_g1, col_g2 = st.columns([2, 1])
    
    with col_g1:
        st.subheader("Comparativa Mensual (YoY)")
        
        df_month_curr = df_filtrado.groupby('mes')['valor_venta'].sum().reset_index().rename(columns={'valor_venta': 'Actual'})
        
        if not df_previo.empty:
            df_month_prev = df_previo.groupby('mes')['valor_venta'].sum().reset_index().rename(columns={'valor_venta': 'Anterior'})
            df_chart = pd.merge(df_month_curr, df_month_prev, on='mes', how='outer').fillna(0)
            df_chart['Variacion'] = df_chart['Actual'] - df_chart['Anterior']
        else:
            df_chart = df_month_curr
            df_chart['Anterior'] = 0
            df_chart['Variacion'] = 0
            
        fig_combo = go.Figure()
        fig_combo.add_trace(go.Bar(x=df_chart['mes'], y=df_chart['Actual'], name=f'Ventas {anio_sel}', marker_color='#2E86C1'))
        fig_combo.add_trace(go.Scatter(x=df_chart['mes'], y=df_chart['Anterior'], name=f'Ventas {anio_comp}', line=dict(color='gray', dash='dot')))
        
        st.plotly_chart(fig_combo, use_container_width=True)
        
    with col_g2:
        st.subheader("Motores de Crecimiento")
        # Waterfall por Marca
        if not df_previo.empty:
            df_marca_curr = df_filtrado.groupby('Marca_Estrategica')['valor_venta'].sum()
            df_marca_prev = df_previo.groupby('Marca_Estrategica')['valor_venta'].sum()
            df_var = (df_marca_curr - df_marca_prev).dropna().sort_values(ascending=False)
            
            fig_water = go.Figure(go.Waterfall(
                orientation="v", measure=["relative"] * len(df_var),
                x=df_var.index, y=df_var.values,
                text=[f"${v/1e6:.1f}M" for v in df_var.values],
                connector={"line": {"color": "rgb(63, 63, 63)"}},
            ))
            fig_water.update_layout(title="Contribución al Crecimiento ($)", showlegend=False)
            st.plotly_chart(fig_water, use_container_width=True)
        else:
            st.info("Selecciona un año comparativo para ver el análisis de motores de crecimiento.")

# --- TAB 2: LOGÍSTICA Y COSTO POR SERVIR (FUSIÓN CON POBLACIÓN) ---
with tab_geo:
    st.subheader("📍 Análisis de Eficiencia Logística por Población")
    st.markdown("""
    **Costo por Servir Relativo:** Relaciona el Ticket Promedio con la Ubicación. 
    *Poblaciones con Ticket Promedio bajo y altas transacciones pueden representar un sobrecosto logístico oculto.*
    """)
    
    # Agrupación por Población
    df_geo_data = df_filtrado.groupby('Poblacion').agg(
        Venta_Total=('valor_venta', 'sum'),
        Margen_Total=('Margen_Pesos', 'sum'),
        Transacciones=('Serie', 'nunique'),
        Dias_Cartera_Avg=('Dias_Cartera', 'mean')
    ).reset_index()
    
    df_geo_data['Ticket_Promedio'] = df_geo_data['Venta_Total'] / df_geo_data['Transacciones']
    df_geo_data['Rentabilidad_Pct'] = (df_geo_data['Margen_Total'] / df_geo_data['Venta_Total']) * 100
    
    # Filtro de visualización (Top 40 poblaciones para no saturar)
    df_viz = df_geo_data.sort_values('Venta_Total', ascending=False).head(40)
    
    fig_bubble = px.scatter(
        df_viz,
        x="Ticket_Promedio",
        y="Rentabilidad_Pct",
        size="Venta_Total",
        color="Dias_Cartera_Avg", # ¡NUEVO! Color por riesgo de cartera
        color_continuous_scale="RdYlGn_r", # Rojo = Muchos días (Malo), Verde = Pocos días (Bueno)
        hover_name="Poblacion",
        text="Poblacion",
        title="Matriz Logística: Eficiencia (Eje X) vs Rentabilidad (Eje Y) vs Cartera (Color)",
        labels={"Dias_Cartera_Avg": "Días Cartera Promedio"}
    )
    fig_bubble.update_traces(textposition='top center')
    fig_bubble.add_vline(x=df_viz['Ticket_Promedio'].mean(), line_dash="dash", annotation_text="Ticket Prom.")
    st.plotly_chart(fig_bubble, use_container_width=True)
    
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.markdown("##### ⚠️ Alerta: Ciudades Ineficientes (Bajo Ticket)")
        st.dataframe(df_viz.nsmallest(10, 'Ticket_Promedio')[['Poblacion', 'Ticket_Promedio', 'Rentabilidad_Pct', 'Transacciones']], use_container_width=True)
        
    with col_l2:
        st.markdown("##### 🏆 Ciudades Estrella (Alto Ticket + Rentabilidad)")
        st.dataframe(df_viz.nlargest(10, 'Ticket_Promedio')[['Poblacion', 'Ticket_Promedio', 'Rentabilidad_Pct', 'Transacciones']], use_container_width=True)

# --- TAB 3: RENTABILIDAD ---
with tab_profit:
    st.subheader("Matriz de Rentabilidad por Marca / Agrupación")
    
    df_profit = df_filtrado.groupby('Marca_Estrategica').agg(
        Venta=('valor_venta', 'sum'),
        Margen=('Margen_Pesos', 'sum')
    ).reset_index()
    
    df_profit['Margen_Pct'] = (df_profit['Margen'] / df_profit['Venta']) * 100
    df_profit['Size'] = df_profit['Margen'].abs() # Fix para burbujas
    
    fig_prof = px.scatter(
        df_profit, x="Venta", y="Margen_Pct", size="Size", color="Margen_Pct",
        color_continuous_scale="RdYlGn", text="Marca_Estrategica",
        title="Rentabilidad vs Volumen"
    )
    st.plotly_chart(fig_prof, use_container_width=True)

# --- TAB 4: SALUD DE CARTERA (NUEVO MODULO) ---
with tab_portfolio:
    st.subheader("💸 Impacto Financiero: Ventas vs Comportamiento de Pago")
    
    if df_poblacion.empty:
        st.warning("No se cargó el archivo de cartera. Este módulo muestra datos limitados.")
    
    # Agrupar por Cliente para ver relación Venta vs Días
    df_risk = df_filtrado.groupby(['nombre_cliente', 'cliente_id']).agg(
        Venta_Anual=('valor_venta', 'sum'),
        Dias_Cartera=('Dias_Cartera', 'max'), # Tomamos el dato del maestro
        Poblacion=('Poblacion', 'first')
    ).reset_index()
    
    # Filtrar clientes pequeños para limpiar gráfica
    df_risk = df_risk[df_risk['Venta_Anual'] > 1000000]
    
    fig_risk = px.scatter(
        df_risk, x="Dias_Cartera", y="Venta_Anual",
        color="Poblacion",
        hover_name="nombre_cliente",
        title="Riesgo de Cartera: ¿A quién le vendemos más y paga más lento?",
        labels={"Dias_Cartera": "Días de Cartera (Reporte)", "Venta_Anual": "Venta Acumulada ($)"}
    )
    # Linea de riesgo (ej. 60 días)
    fig_risk.add_vline(x=60, line_dash="dash", line_color="red", annotation_text="Límite Riesgo (60 días)")
    
    st.plotly_chart(fig_risk, use_container_width=True)
    
    st.markdown("### 🚨 Top Clientes con Alto Riesgo (Venta Alta + Mora Alta)")
    # Clientes con venta significativa y dias altos
    df_high_risk = df_risk[df_risk['Dias_Cartera'] > 60].sort_values('Venta_Anual', ascending=False).head(15)
    
    st.dataframe(
        df_high_risk,
        column_config={
            "Venta_Anual": st.column_config.NumberColumn(format="$ %d"),
            "Dias_Cartera": st.column_config.NumberColumn(format="%d días")
        },
        use_container_width=True
    )
