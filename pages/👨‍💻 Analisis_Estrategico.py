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
st.set_page_config(page_title="Master Brain Ultra 2.0 - Logistics & Growth", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-left: 5px solid #003865;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    h1, h2, h3 { color: #003865; font-family: 'Helvetica', sans-serif; font-weight: 800; }
    div[data-testid="stMetricValue"] { color: #0058A7; font-weight: bold; font-size: 24px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #003865;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MOTORES DE LIMPIEZA Y CLASIFICACIÓN
# ==============================================================================

def normalizar_texto(texto):
    """Estandariza nombres de ciudades, clientes y marcas."""
    if not isinstance(texto, str): return str(texto) if texto is not None else "SIN INFO"
    texto = str(texto)
    texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sin_tildes.upper().strip()

def limpiar_nit_maestro(nit):
    """Limpia el NIT (NIF20) eliminando puntos, guiones y dígitos de verificación comunes."""
    if pd.isna(nit): return "0"
    s_nit = str(nit).split('-')[0] # Intenta quitar digito verificacion si viene con guion
    s_limpio = re.sub(r'[^0-9]', '', s_nit) # Solo deja números
    return s_limpio if s_limpio else "0"

def clasificar_marca_ultra(fila):
    """Clasificación Maestra de Marcas e Identificación de Familia Pintuco."""
    texto_completo = (
        normalizar_texto(fila.get('marca_producto', '')) + " " +
        normalizar_texto(fila.get('categoria_producto', '')) + " " +
        normalizar_texto(fila.get('nombre_articulo', ''))
    )
    
    # 1. ESTRATÉGICAS (LISTA BLANCA)
    estrategicas = [
        'ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', 
        'SAINT GOBAIN', 'ALLEGION', 'SEGUREX', 'POLVOS', 'DELTA', 
        'MASTERD', 'GLOBAL', 'SANTENO', 'BELLOTA', '3M', 'SISTA'
    ]
    for m in estrategicas:
        if m in texto_completo: return m

    # 2. FAMILIA PINTUCO DETALLADA
    familia_pintuco = {
        'TERINSA': 'TERINSA',
        'ICO': 'ICO',
        'INTERNATIONAL': 'INTERNATIONAL',
        'INTERPON': 'INTERPON',
        'RESICOAT': 'RESICOAT',
        'PROTECTO': 'PROTECTO',
        'OCEANIC': 'OCEANIC',
        'CORAL': 'CORAL',
        'SIKKEN': 'SIKKENS', 
        'WANDA': 'WANDA'
    }
    for clave, valor in familia_pintuco.items():
        if clave in texto_completo: return valor

    # 3. PINTUCO GENÉRICO
    claves_pintuco_gen = ['PINTUCO', 'VINILTEX', 'KORAZA', 'DOMESTICO', 'CONSTRUCCION', 'PIN']
    for k in claves_pintuco_gen:
        if k in texto_completo: return 'PINTUCO ARQUITECTONICO'

    return 'OTROS'

# ==============================================================================
# 3. CONEXIÓN DROPBOX (CLIENTES DETALLE)
# ==============================================================================
@st.cache_data(ttl=3600)
def cargar_maestro_clientes_dropbox():
    """
    Carga 'clientes_detalle' desde Dropbox.
    Columnas esperadas: NIF20 (Nit), CIUDAD (Población), NOMBRECLIENTE, etc.
    """
    try:
        try:
            APP_KEY = st.secrets["dropbox"]["app_key"]
            APP_SECRET = st.secrets["dropbox"]["app_secret"]
            REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]
        except:
            st.error("⚠️ Faltan credenciales de Dropbox en st.secrets")
            return pd.DataFrame()

        with dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN) as dbx:
            # NOTA: Asegúrate de que el nombre del archivo en Dropbox sea correcto
            ruta = '/data/clientes_detalle.csv' 
            metadata, res = dbx.files_download(path=ruta)
            contenido = res.content.decode('latin-1', errors='ignore')
            
            # Leemos intentando detectar separador, asumiendo pipe '|' o punto y coma ';' comúnmente
            # Si tu archivo es CSV estándar (coma), cambia sep=','
            df_drop = pd.read_csv(io.StringIO(contenido), sep=None, engine='python') 

            # Normalización de columnas para evitar errores por mayúsculas/minúsculas
            df_drop.columns = [c.strip().upper() for c in df_drop.columns]
            
            # Verificamos si existen las columnas clave; si no, tratamos de inferirlas
            col_nit = 'NIF20' if 'NIF20' in df_drop.columns else 'NIT'
            col_ciudad = 'CIUDAD' if 'CIUDAD' in df_drop.columns else 'POBLACION'
            
            if col_nit not in df_drop.columns:
                st.warning(f"Columna {col_nit} no encontrada en Dropbox. Columnas: {df_drop.columns}")
                return pd.DataFrame()

            # Procesamiento
            df_drop['Key_Nit'] = df_drop[col_nit].apply(limpiar_nit_maestro)
            
            if col_ciudad in df_drop.columns:
                df_drop['Poblacion_Real'] = df_drop[col_ciudad].apply(normalizar_texto)
            else:
                df_drop['Poblacion_Real'] = "SIN CIUDAD"

            # Extraemos RIESGO y CUPO si existen
            if 'RIESGO' in df_drop.columns:
                df_drop['Nivel_Riesgo'] = df_drop['RIESGO'].fillna('Bajo')
            else:
                df_drop['Nivel_Riesgo'] = 'No Info'

            # Dejar solo una fila por NIT (la más completa)
            df_maestro = df_drop.drop_duplicates(subset=['Key_Nit'], keep='first')
            
            return df_maestro[['Key_Nit', 'Poblacion_Real', 'Nivel_Riesgo', 'NOMBRECLIENTE']]

    except Exception as e:
        st.error(f"Error conectando a Dropbox: {e}")
        return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO INTELIGENTE (FUSIÓN VENTAS + LOGÍSTICA)
# ==============================================================================

if 'df_ventas' not in st.session_state:
    st.info("📂 Esperando carga de archivo de ventas en el menú principal...")
    st.stop()

# Recuperar datos crudos
df = st.session_state.df_ventas.copy()

# --- 1. Limpieza Numérica y Fechas ---
cols_num = ['valor_venta', 'unidades_vendidas', 'costo_unitario', 'rentabilidad']
for col in cols_num:
    if col not in df.columns: df[col] = 0.0
    else: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Margen en Pesos
df['Margen_Pesos'] = df['valor_venta'] - (df['unidades_vendidas'] * df['costo_unitario'])

# Fechas (CRUCIAL PARA LOGÍSTICA)
col_fecha = 'fecha_documento' if 'fecha_documento' in df.columns else 'fecha'
if col_fecha in df.columns:
    df['Fecha_Dt'] = pd.to_datetime(df[col_fecha], errors='coerce')
    df['Mes'] = df['Fecha_Dt'].dt.month_name()
    df['Dia_Semana'] = df['Fecha_Dt'].dt.day_name()
else:
    df['Fecha_Dt'] = pd.to_datetime('today')
    df['Mes'] = 'Desconocido'

# --- 2. Clasificación de Marca ---
df['Marca_Master'] = df.apply(clasificar_marca_ultra, axis=1)

# --- 3. Fusión con Dropbox (Poblaciones Reales) ---
df['Key_Nit'] = df['cliente_id'].apply(limpiar_nit_maestro)

with st.spinner("🧠 Master Brain cruzando geo-referenciación con NIF20..."):
    df_clientes = cargar_maestro_clientes_dropbox()

if not df_clientes.empty:
    # Left Join para mantener todas las ventas
    df_full = pd.merge(df, df_clientes, on='Key_Nit', how='left')
    
    # Rellenar huecos: Si no cruza, usamos la ciudad del archivo de ventas si existe
    if 'ciudad_cliente' in df_full.columns:
        df_full['Poblacion_Real'] = df_full['Poblacion_Real'].fillna(df_full['ciudad_cliente'].apply(normalizar_texto))
    else:
        df_full['Poblacion_Real'] = df_full['Poblacion_Real'].fillna('SIN ASIGNAR')
        
    df_full['Nivel_Riesgo'] = df_full['Nivel_Riesgo'].fillna('Desconocido')
else:
    df_full = df.copy()
    df_full['Poblacion_Real'] = df_full.get('ciudad_cliente', 'SIN INFO').astype(str).apply(normalizar_texto)
    df_full['Nivel_Riesgo'] = 'Desconocido'

# Normalizar Población Final
df_full['Poblacion_Real'] = df_full['Poblacion_Real'].replace(['NAN', 'NONE', '0'], 'SIN ASIGNAR')

# ==============================================================================
# 5. INTERFAZ DE CONTROL (FILTROS)
# ==============================================================================

st.title("🧠 Master Brain Ultra 2.0: Análisis 360º")
st.markdown("**Estrategia Comercial + Eficiencia Logística + Estructura de Mercado**")

with st.sidebar:
    st.header("🎛️ Filtros Maestros")
    
    # Años
    anios = sorted(df_full['anio'].unique(), reverse=True) if 'anio' in df_full.columns else [2024]
    anio_act = st.selectbox("Año Objetivo (Actual)", anios, index=0)
    anio_ant = st.selectbox("Año Comparativo (Base)", [a for a in anios if a != anio_act] + ["Ninguno"], index=0)
    
    st.divider()
    
    # Marcas
    marcas = sorted(df_full['Marca_Master'].unique())
    sel_marcas = st.multiselect("Marcas", marcas, default=marcas)
    
    # Poblaciones
    zonas = ["TODAS"] + sorted(df_full['Poblacion_Real'].unique())
    sel_zona = st.selectbox("Población / Zona", zonas)
    
    st.info(f"Total Registros: {len(df_full):,.0f}")

# Aplicar filtros
df_f = df_full[df_full['Marca_Master'].isin(sel_marcas)].copy()
if sel_zona != "TODAS":
    df_f = df_f[df_f['Poblacion_Real'] == sel_zona]

df_now = df_f[df_f['anio'] == anio_act]
df_prev = df_f[df_f['anio'] == anio_ant] if anio_ant != "Ninguno" else pd.DataFrame()

# ==============================================================================
# 6. DASHBOARD SUPERIOR (KPIs VIVOS)
# ==============================================================================

vta_act = df_now['valor_venta'].sum()
vta_pre = df_prev['valor_venta'].sum() if not df_prev.empty else 0
dif_abs = vta_act - vta_pre
var_pct = (dif_abs / vta_pre * 100) if vta_pre > 0 else 0

mgn_act = df_now['Margen_Pesos'].sum()
rent_pct = (mgn_act / vta_act * 100) if vta_act > 0 else 0

# Frecuencia Global (Días de facturación totales en el año)
dias_facturacion = df_now['Fecha_Dt'].nunique()
ticket_medio = vta_act / len(df_now) if len(df_now) > 0 else 0 # Promedio por línea (no por factura aun)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Venta Total", f"${vta_act/1e6:,.1f} M", f"{var_pct:+.1f}%")
c2.metric("Utilidad Bruta", f"${mgn_act/1e6:,.1f} M", f"{rent_pct:.1f}% Margen")
c3.metric("Crecimiento Neto", f"${dif_abs/1e6:+.1f} M", "vs Año Base")
c4.metric("Días Operación", f"{dias_facturacion}", "Días con Ventas")
c5.metric("Total Clientes", f"{df_now['Key_Nit'].nunique()}", "Con Compra")

st.divider()

# ==============================================================================
# 7. PESTAÑAS DE ANÁLISIS PROFUNDO
# ==============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Drivers & Frenos (Crecimiento)", 
    "📦 Costo por Servir (Logística)", 
    "🎯 Peso & Estructura (Share)",
    "🔮 Tendencias Temporales"
])

# --- TAB 1: DRIVERS & FRENOS (CRECIMIENTO) ---
with tab1:
    st.subheader(f"Desglose de Crecimiento: {anio_ant} vs {anio_act}")
    
    col_g1, col_g2 = st.columns([2, 1])
    
    with col_g1:
        if not df_prev.empty:
            # Data para Waterfall
            grp_now = df_now.groupby('Marca_Master')['valor_venta'].sum()
            grp_old = df_prev.groupby('Marca_Master')['valor_venta'].sum()
            
            df_bridge = pd.DataFrame({'Actual': grp_now, 'Anterior': grp_old}).fillna(0)
            df_bridge['Variacion'] = df_bridge['Actual'] - df_bridge['Anterior']
            df_bridge = df_bridge.sort_values('Variacion', ascending=True) # Ordenar para waterfall
            
            fig_water = go.Figure(go.Waterfall(
                orientation="h",
                measure=["relative"] * len(df_bridge),
                y=df_bridge.index,
                x=df_bridge['Variacion'],
                text=[f"${v/1e6:.1f}M" for v in df_bridge['Variacion']],
                textposition="auto",
                decreasing={"marker":{"color":"#E53935"}}, # Rojo freno
                increasing={"marker":{"color":"#43A047"}}, # Verde impulso
                connector={"line":{"color":"rgb(63, 63, 63)"}}
            ))
            fig_water.update_layout(
                title="Puente de Crecimiento por Marca (Impacto Real)",
                xaxis_title="Variación en Dinero",
                height=600
            )
            st.plotly_chart(fig_water, use_container_width=True)
        else:
            st.warning("Selecciona un año base para ver el puente de crecimiento.")

    with col_g2:
        st.markdown("#### Top Impulsores vs Frenos")
        if not df_prev.empty:
            df_bridge['Estado'] = df_bridge['Variacion'].apply(lambda x: '🚀 Impulsa' if x > 0 else '⚓ Frena')
            df_bridge['Var %'] = (df_bridge['Variacion'] / df_bridge['Anterior']) * 100
            
            st.dataframe(
                df_bridge.sort_values('Variacion', ascending=False)
                .style.format({'Actual': '${:,.0f}', 'Anterior': '${:,.0f}', 'Variacion': '${:,.0f}', 'Var %': '{:+.1f}%'})
                .background_gradient(subset=['Variacion'], cmap='RdYlGn')
            )

# --- TAB 2: COSTO POR SERVIR & LOGÍSTICA ---
with tab2:
    st.subheader("Análisis de Eficiencia Logística y Costo por Servir")
    st.markdown("""
    **Metodología Master Brain:**
    1. **Drop Size (Tamaño de Entrega):** Promedio de venta por factura. Si es bajo, el flete se come la utilidad.
    2. **Frecuencia de Visita:** Días únicos que facturamos a esa población.
    3. **Eficiencia:** Cruzamos Frecuencia vs Tamaño para detectar rutas ineficientes.
    """)
    
    # Definir columna de documento para contar facturas
    col_doc = 'numero_documento' if 'numero_documento' in df_now.columns else 'cliente_id'
    
    # Agrupación Maestra por Población
    df_log = df_now.groupby('Poblacion_Real').agg(
        Venta_Total=('valor_venta', 'sum'),
        Margen_Total=('Margen_Pesos', 'sum'),
        Num_Facturas=(col_doc, 'nunique'),
        Dias_Visita=('Fecha_Dt', 'nunique'), # Días únicos con facturación
        Num_Clientes=('Key_Nit', 'nunique')
    ).reset_index()
    
    # Cálculos Derivados
    df_log = df_log[df_log['Venta_Total'] > 0]
    df_log['Ticket_Promedio'] = df_log['Venta_Total'] / df_log['Num_Facturas'] # Drop Size
    df_log['Venta_Por_Dia_Visita'] = df_log['Venta_Total'] / df_log['Dias_Visita']
    df_log['Rentabilidad_%'] = (df_log['Margen_Total'] / df_log['Venta_Total']) * 100
    
    # Scatter Plot Avanzado: Costo vs Volumen
    # Eje X: Días de Visita (Costo logístico temporal)
    # Eje Y: Ticket Promedio (Eficiencia de entrega)
    
    mediana_ticket = df_log['Ticket_Promedio'].median()
    mediana_freq = df_log['Dias_Visita'].median()
    
    col_log1, col_log2 = st.columns([3, 1])
    
    with col_log1:
        fig_log = px.scatter(
            df_log,
            x="Dias_Visita",
            y="Ticket_Promedio",
            size="Venta_Total",
            color="Rentabilidad_%",
            hover_name="Poblacion_Real",
            hover_data=["Num_Clientes", "Num_Facturas"],
            color_continuous_scale="RdYlGn",
            title=f"Matriz Costo por Servir ({anio_act})",
            labels={"Dias_Visita": "Frecuencia de Atención (Días/Año)", "Ticket_Promedio": "Drop Size Promedio ($/Factura)"}
        )
        
        # Cuadrantes
        fig_log.add_hline(y=mediana_ticket, line_dash="dash", annotation_text="Ticket Medio")
        fig_log.add_vline(x=mediana_freq, line_dash="dash", annotation_text="Frec. Media")
        
        st.plotly_chart(fig_log, use_container_width=True)
        
    with col_log2:
        st.markdown("#### 🚨 Alerta Logística")
        st.markdown("Poblaciones con **Alta Frecuencia** pero **Bajo Ticket**. (Costosas de atender).")
        
        df_ineficiente = df_log[
            (df_log['Dias_Visita'] > mediana_freq) & 
            (df_log['Ticket_Promedio'] < mediana_ticket)
        ].sort_values('Dias_Visita', ascending=False).head(10)
        
        st.dataframe(df_ineficiente[['Poblacion_Real', 'Dias_Visita', 'Ticket_Promedio']].style.format({
            'Ticket_Promedio': '${:,.0f}',
            'Dias_Visita': '{:.0f}'
        }))

    # Detalle de Ineficiencia Diaria
    st.markdown("### 📅 Intensidad Diaria (Heatmap)")
    # Agrupar por Día de Semana y Población (Top 10 Poblaciones)
    top_pobs = df_now.groupby('Poblacion_Real')['valor_venta'].sum().nlargest(10).index
    df_heat = df_now[df_now['Poblacion_Real'].isin(top_pobs)].groupby(['Poblacion_Real', 'Dia_Semana'])['valor_venta'].count().reset_index()
    
    fig_heat = px.density_heatmap(
        df_heat, x="Dia_Semana", y="Poblacion_Real", z="valor_venta", 
        title="Concentración de Pedidos por Día de la Semana",
        color_continuous_scale="Blues",
        category_orders={"Dia_Semana": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# --- TAB 3: PESO & ESTRUCTURA (SHARE) ---
with tab3:
    st.subheader("Composición Jerárquica del Mercado")
    
    # Sunburst Chart: Marca -> Categoría -> Producto (Top)
    # Limitamos a top productos para no saturar
    df_sun = df_now.groupby(['Marca_Master', 'categoria_producto'])['valor_venta'].sum().reset_index()
    df_sun = df_sun[df_sun['valor_venta'] > 0]
    
    col_s1, col_s2 = st.columns([2, 1])
    
    with col_s1:
        fig_sun = px.sunburst(
            df_sun,
            path=['Marca_Master', 'categoria_producto'],
            values='valor_venta',
            color='valor_venta',
            color_continuous_scale='Viridis',
            title="Peso Visual de Marcas y Categorías"
        )
        st.plotly_chart(fig_sun, use_container_width=True)
        
    with col_s2:
        st.markdown("#### Tabla de Participación (Pareto)")
        total_val = df_sun['valor_venta'].sum()
        df_pareto = df_now.groupby('Marca_Master')['valor_venta'].sum().reset_index().sort_values('valor_venta', ascending=False)
        df_pareto['Share %'] = (df_pareto['valor_venta'] / total_val) * 100
        df_pareto['Acumulado %'] = df_pareto['Share %'].cumsum()
        
        st.dataframe(df_pareto.style.format({
            'valor_venta': '${:,.0f}',
            'Share %': '{:.2f}%',
            'Acumulado %': '{:.2f}%'
        }))

# --- TAB 4: TENDENCIAS TEMPORALES ---
with tab4:
    st.subheader("Evolución Mensual de la Venta")
    
    # Agrupar por Mes y Marca (Top 5 Marcas)
    top_marcas = df_now.groupby('Marca_Master')['valor_venta'].sum().nlargest(5).index
    df_trend = df_now[df_now['Marca_Master'].isin(top_marcas)].groupby(['Fecha_Dt', 'Marca_Master'])['valor_venta'].sum().reset_index()
    
    # Agrupar por mes para suavizar
    df_trend['Mes_Año'] = df_trend['Fecha_Dt'].dt.to_period('M').astype(str)
    df_trend_monthly = df_trend.groupby(['Mes_Año', 'Marca_Master'])['valor_venta'].sum().reset_index()
    
    fig_line = px.line(
        df_trend_monthly, 
        x="Mes_Año", 
        y="valor_venta", 
        color="Marca_Master",
        markers=True,
        title="Tendencia de Ventas Mensual (Top 5 Marcas)"
    )
    st.plotly_chart(fig_line, use_container_width=True)

st.success(f"✅ Análisis completo generado con éxito. NIFs cruzados: {df_full['Poblacion_Real'].nunique()} zonas logísticas identificadas.")
