# ==============================================================================
# 🧠 MASTER BRAIN V.ULTRA - CENTRO DE ESTRATEGIA & LOGÍSTICA
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import unicodedata
import io
import dropbox
import toml

st.set_page_config(page_title="Master Brain Estratégico", page_icon="♟️", layout="wide")

# ==============================================================================
# 🎨 ESTILOS DE ALTO NIVEL (CSS)
# ==============================================================================
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(to bottom right, #ffffff, #f8f9fa);
        border-left: 6px solid #003865;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }
    h1, h2, h3 { color: #003865; font-family: 'Helvetica', sans-serif; font-weight: 700; }
    .stDataFrame { border: 1px solid #ddd; border-radius: 5px; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #0058A7; }
    div[data-testid="stMetricDelta"] { font-size: 16px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔧 MOTOR DE INTELIGENCIA (FUNCIONES DE LIMPIEZA Y LÓGICA)
# ==============================================================================
def normalizar_texto(texto):
    if not isinstance(texto, str): return str(texto) if texto is not None else ""
    try:
        texto = str(texto)
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').replace('_', ' ').replace('.', '').strip()
    except: return str(texto)

def clasificar_marca_estricta(fila):
    """
    LÓGICA MAESTRA DE CATEGORIZACIÓN:
    1. Busca en una 'Lista Blanca' (ABRACOL, INDUMA, etc.)
    2. Si encuentra alguna, asigna esa marca.
    3. Si NO encuentra ninguna, asigna automáticamente 'PINTUCO'.
    """
    # Concatenamos todo para buscar (Marca + Categoria + Articulo)
    texto_busqueda = f"{normalizar_texto(fila.get('marca_producto', ''))} {normalizar_texto(fila.get('categoria_producto', ''))} {normalizar_texto(fila.get('nombre_articulo', ''))}"
    
    # TU LISTA BLANCA (Lo que NO es Pintuco)
    lista_blanca = [
        'ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', 
        'SAINT GOBAIN', 'ALLEGION', 'SEGUREX', 'POLVOS', 'DELTA', 'MASTERD'
    ]
    
    for marca in lista_blanca:
        if marca in texto_busqueda:
            return marca # ¡Encontrado! Es una marca estratégica separada
            
    return 'PINTUCO' # Si no está en la lista blanca, ES PINTUCO (Por defecto)

# ==============================================================================
# 📥 CARGADOR DE CARTERA (LÓGICA EXACTA DE TU EJEMPLO)
# ==============================================================================
@st.cache_data(ttl=600)
def cargar_cartera_dropbox_exacta():
    """
    Usa TU lógica probada para leer cartera_detalle.csv desde Dropbox.
    """
    try:
        # Recuperar credenciales (Manejo de errores si no están en secrets)
        try:
            APP_KEY = st.secrets["dropbox"]["app_key"]
            APP_SECRET = st.secrets["dropbox"]["app_secret"]
            REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]
        except:
            # Fallback para entornos locales sin secrets configurados igual
            return pd.DataFrame()

        with dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN) as dbx:
            path_archivo_dropbox = '/data/cartera_detalle.csv'
            metadata, res = dbx.files_download(path=path_archivo_dropbox)
            contenido_csv = res.content.decode('latin-1')

            nombres_columnas_originales = [
                'Serie', 'Numero', 'Fecha Documento', 'Fecha Vencimiento', 'Cod Cliente',
                'NombreCliente', 'Nit', 'Poblacion', 'Provincia', 'Telefono1', 'Telefono2',
                'NomVendedor', 'Entidad Autoriza', 'E-Mail', 'Importe', 'Descuento',
                'Cupo Aprobado', 'Dias Vencido'
            ]

            df = pd.read_csv(io.StringIO(contenido_csv), header=None, names=nombres_columnas_originales, sep='|', engine='python')
            
            # --- LIMPIEZA BÁSICA ---
            # Normalizar NIT para cruce (Quitar puntos, espacios)
            df['cliente_id'] = df['Nit'].apply(normalizar_texto)
            
            # Convertir numéricos clave
            df['Importe'] = pd.to_numeric(df['Importe'], errors='coerce').fillna(0)
            df['Dias Vencido'] = pd.to_numeric(df['Dias Vencido'], errors='coerce').fillna(0)
            
            # Agrupar por Cliente para el cruce (Necesitamos 1 registro por cliente con sus datos logísticos)
            # Lógica: Tomamos la Población más frecuente y el Máximo de Días Vencidos
            df_maestro = df.groupby('cliente_id').agg({
                'Poblacion': lambda x: x.mode()[0] if not x.mode().empty else 'SIN POBLACION',
                'Dias Vencido': 'max', # El peor día de vencimiento define el riesgo
                'Importe': 'sum'       # Deuda Total
            }).reset_index()
            
            df_maestro.rename(columns={'Dias Vencido': 'Max_Dias_Mora', 'Importe': 'Deuda_Total'}, inplace=True)
            df_maestro['Poblacion'] = df_maestro['Poblacion'].apply(normalizar_texto)
            
            return df_maestro

    except Exception as e:
        st.error(f"Error leyendo Dropbox con la lógica exacta: {e}")
        return pd.DataFrame()

# ==============================================================================
# 1. PROCESAMIENTO Y FUSIÓN DE DATOS
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.warning("⚠️ Por favor inicia sesión en el 'Resumen Mensual' primero para cargar las ventas.")
    st.stop()

# --- A. PREPARACIÓN VENTAS ---
df_raw = st.session_state.df_ventas.copy()
filtro_neto = 'FACTURA|NOTA.*CREDITO'
df_raw['TipoDocumento'] = df_raw['TipoDocumento'].astype(str)
df = df_raw[df_raw['TipoDocumento'].str.contains(filtro_neto, na=False, case=False, regex=True)].copy()

# Conversiones
for col in ['valor_venta', 'unidades_vendidas', 'costo_unitario']:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

df['Margen_Pesos'] = df['valor_venta'] - (df['unidades_vendidas'] * df['costo_unitario'])

# --- B. APLICAR CATEGORIZACIÓN "LISTA BLANCA O PINTUCO" ---
df['Marca_Master'] = df.apply(clasificar_marca_estricta, axis=1)

# --- C. CRUCE CON CARTERA (USANDO TU LÓGICA) ---
with st.spinner("🔄 Conectando con Dropbox y cruzando datos..."):
    df_cartera = cargar_cartera_dropbox_exacta()

# Normalizar llave en ventas
df['cliente_id'] = df['cliente_id'].apply(normalizar_texto)

# Left Join: Ventas es la base, traemos datos de cartera si existen
if not df_cartera.empty:
    df_full = pd.merge(df, df_cartera, on='cliente_id', how='left')
    df_full['Poblacion'] = df_full['Poblacion'].fillna('SIN INFO LOGISTICA')
    df_full['Max_Dias_Mora'] = df_full['Max_Dias_Mora'].fillna(0)
    df_full['Deuda_Total'] = df_full['Deuda_Total'].fillna(0)
else:
    df_full = df.copy()
    df_full['Poblacion'] = 'ERROR CARGA'
    df_full['Max_Dias_Mora'] = 0

# ==============================================================================
# 2. CONTROL DE MANDO (SIDEBAR)
# ==============================================================================
st.sidebar.header("🎛️ Filtros Maestros")
st.sidebar.markdown("---")

anios = sorted(df_full['anio'].unique(), reverse=True)
anio_act = st.sidebar.selectbox("Año Análisis (Actual)", anios, index=0)
anio_ant = st.sidebar.selectbox("Año Comparativo (Base)", [a for a in anios if a != anio_act] + ["Ninguno"], index=0)

# Filtro Categorías
cats = sorted(df_full['Marca_Master'].unique())
sel_cats = st.sidebar.multiselect("Seleccionar Marcas/Categorías", cats, default=cats)

# Filtro Zonas
zonas = ["TODAS"] + sorted(df_full['Poblacion'].unique())
sel_zona = st.sidebar.selectbox("Filtrar por Población", zonas)

# --- APLICAR FILTROS ---
df_fil = df_full[df_full['Marca_Master'].isin(sel_cats)].copy()
if sel_zona != "TODAS":
    df_fil = df_fil[df_fil['Poblacion'] == sel_zona]

df_act = df_fil[df_fil['anio'] == anio_act].copy()
df_prev = df_fil[df_fil['anio'] == anio_ant].copy() if anio_ant != "Ninguno" else pd.DataFrame()

# ==============================================================================
# 3. TABLERO EJECUTIVO (KPIs)
# ==============================================================================
st.title("♟️ Master Brain: Análisis de Crecimiento Real")
st.markdown(f"**Diagnóstico Estratégico:** {anio_act} vs {anio_ant if anio_ant != 'Ninguno' else 'N/A'}")

col1, col2, col3, col4 = st.columns(4)

v_act = df_act['valor_venta'].sum()
v_prev = df_prev['valor_venta'].sum() if not df_prev.empty else 0
crecimiento_abs = v_act - v_prev
crecimiento_pct = (crecimiento_abs / v_prev * 100) if v_prev else 0

m_act = df_act['Margen_Pesos'].sum()
m_prev = df_prev['Margen_Pesos'].sum() if not df_prev.empty else 0
margen_pct_act = (m_act / v_act * 100) if v_act else 0

# Días Mora Ponderado (Solo de clientes con venta actual)
dias_mora_prom = df_act[df_act['valor_venta']>0]['Max_Dias_Mora'].mean()

with col1: 
    st.metric("Ventas Totales", f"${v_act:,.0f}", f"{crecimiento_pct:+.1f}% ({crecimiento_abs/1e6:+.1f}M)")
with col2: 
    st.metric("Margen Bruto", f"${m_act:,.0f}", f"{(m_act - m_prev)/1e6:+.1f}M vs Año Ant")
with col3: 
    st.metric("Rentabilidad %", f"{margen_pct_act:.1f}%", f"{(margen_pct_act - (m_prev/v_prev*100 if v_prev else 0)):+.1f} pp")
with col4: 
    delta_color = "inverse" if dias_mora_prom > 30 else "normal"
    st.metric("Días Mora Promedio", f"{dias_mora_prom:.0f} días", "Riesgo Cartera", delta_color=delta_color)

# ==============================================================================
# 4. ANÁLISIS PROFUNDO (PESTAÑAS)
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Anatomía del Crecimiento", 
    "🗺️ Logística & Costo x Servir",
    "💎 Share & Rentabilidad",
    "🩸 Salud Financiera (Riesgo)"
])

# --- TAB 1: ANATOMÍA DEL CRECIMIENTO (LO MÁS IMPORTANTE) ---
with tab1:
    st.subheader("¿Qué impulsó (o frenó) realmente el crecimiento?")
    st.markdown("Este gráfico desglosa el cambio en ventas. Muestra exactamente cuánto dinero aportó cada marca al resultado final.")
    
    if not df_prev.empty:
        # 1. Calcular ventas por marca ambos años
        g_act = df_act.groupby('Marca_Master')['valor_venta'].sum().reset_index().rename(columns={'valor_venta':'Venta_Actual'})
        g_prev = df_prev.groupby('Marca_Master')['valor_venta'].sum().reset_index().rename(columns={'valor_venta':'Venta_Anterior'})
        
        # 2. Merge y Calculo de Variación Absoluta
        df_waterfall = pd.merge(g_act, g_prev, on='Marca_Master', how='outer').fillna(0)
        df_waterfall['Variacion'] = df_waterfall['Venta_Actual'] - df_waterfall['Venta_Anterior']
        df_waterfall['Contribucion_Pts'] = (df_waterfall['Variacion'] / v_prev) * 100 # Puntos porcentuales de crecimiento
        
        # Ordenar por impacto absoluto
        df_waterfall = df_waterfall.sort_values('Variacion', ascending=False)
        
        col_w1, col_w2 = st.columns([2, 1])
        
        with col_w1:
            # Gráfico Waterfall
            fig_water = go.Figure(go.Waterfall(
                name="Variación", orientation="v",
                measure=["relative"] * len(df_waterfall),
                x=df_waterfall['Marca_Master'],
                textposition="outside",
                text=[f"${v/1e6:+.0f}M" for v in df_waterfall['Variacion']],
                y=df_waterfall['Variacion'],
                connector={"line":{"color":"rgb(63, 63, 63)"}},
                decreasing={"marker":{"color":"#E74C3C"}},
                increasing={"marker":{"color":"#2ECC71"}},
                totals={"marker":{"color":"#3498DB"}}
            ))
            fig_water.update_layout(
                title="Puente de Variación de Ventas (Millones $)",
                showlegend=False,
                yaxis_title="Impacto en Dinero ($)"
            )
            st.plotly_chart(fig_water, use_container_width=True)
            
        with col_w2:
            st.markdown("##### 🧠 Insights de Crecimiento")
            
            top_driver = df_waterfall.iloc[0]
            top_detractor = df_waterfall.iloc[-1]
            
            st.info(f"🏆 **Motor Principal:** **{top_driver['Marca_Master']}** aportó **${top_driver['Variacion']/1e6:,.1f}M** al crecimiento.")
            if top_detractor['Variacion'] < 0:
                st.error(f"📉 **Freno Principal:** **{top_detractor['Marca_Master']}** cayó **${abs(top_detractor['Variacion'])/1e6:,.1f}M**. Requiere revisión estratégica.")
            else:
                st.success("✅ Todas las categorías crecieron.")

            st.dataframe(
                df_waterfall[['Marca_Master', 'Variacion', 'Contribucion_Pts']],
                column_config={
                    "Variacion": st.column_config.NumberColumn("Var $", format="$%d"),
                    "Contribucion_Pts": st.column_config.NumberColumn("Impacto Crecimiento", format="%+.2f pp")
                },
                hide_index=True
            )
    else:
        st.warning("Selecciona un Año Comparativo en el menú lateral para ver el análisis de crecimiento.")

# --- TAB 2: LOGÍSTICA Y COSTO POR SERVIR ---
with tab2:
    st.subheader("📍 Mapa de Eficiencia Logística")
    st.markdown("**Eje X: Ticket Promedio** (Eficiencia) | **Eje Y: Población** | **Color: Rentabilidad**")
    st.caption("Un Ticket Promedio bajo en una población lejana implica un alto costo logístico oculto (fletes, tiempo).")
    
    # Agrupar por Población
    df_log = df_act.groupby('Poblacion').agg(
        Ventas=('valor_venta', 'sum'),
        Pedidos=('Serie', 'nunique'),
        Margen=('Margen_Pesos', 'sum')
    ).reset_index()
    
    df_log['Ticket_Promedio'] = df_log['Ventas'] / df_log['Pedidos']
    df_log['Rentabilidad_Pct'] = (df_log['Margen'] / df_log['Ventas']) * 100
    
    # Filtrar ruido (Poblaciones con ventas insignificantes)
    df_log_viz = df_log[df_log['Ventas'] > df_log['Ventas'].quantile(0.2)]
    
    fig_scatter = px.scatter(
        df_log_viz,
        x="Ticket_Promedio",
        y="Rentabilidad_Pct",
        size="Ventas",
        color="Rentabilidad_Pct",
        hover_name="Poblacion",
        text="Poblacion",
        color_continuous_scale="RdYlGn",
        title="Matriz de Eficiencia: Ticket vs Rentabilidad"
    )
    
    # Líneas de referencia
    avg_ticket = df_log['Ticket_Promedio'].mean()
    fig_scatter.add_vline(x=avg_ticket, line_dash="dash", annotation_text="Ticket Promedio General")
    fig_scatter.update_traces(textposition='top center')
    
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    st.markdown("##### 🚨 Top Poblaciones Ineficientes (Bajo Ticket = Alto Costo x Servir)")
    st.dataframe(
        df_log_viz.nsmallest(10, 'Ticket_Promedio')[['Poblacion', 'Ticket_Promedio', 'Rentabilidad_Pct', 'Ventas']],
        column_config={"Ticket_Promedio": st.column_config.NumberColumn(format="$%d"), "Rentabilidad_Pct": st.column_config.NumberColumn(format="%.1f%%")},
        hide_index=True,
        use_container_width=True
    )

# --- TAB 3: SHARE Y RENTABILIDAD ---
with tab3:
    st.subheader("Posicionamiento de Marcas")
    
    col_s1, col_s2 = st.columns([2, 1])
    
    # Datos agrupados
    df_share = df_act.groupby('Marca_Master').agg(
        Venta=('valor_venta', 'sum'),
        Margen=('Margen_Pesos', 'sum')
    ).reset_index()
    df_share['Rentabilidad'] = (df_share['Margen'] / df_share['Venta']) * 100
    
    with col_s1:
        st.markdown("##### 📦 Distribución de la Venta (Treemap)")
        fig_tree = px.treemap(
            df_share,
            path=[px.Constant("FERREINOX"), 'Marca_Master'],
            values='Venta',
            color='Rentabilidad',
            color_continuous_scale='RdYlGn',
            title="Tamaño = Venta | Color = Rentabilidad %"
        )
        st.plotly_chart(fig_tree, use_container_width=True)
        
    with col_s2:
        st.markdown("##### 💎 Matriz Estratégica")
        fig_bubble = px.scatter(
            df_share,
            x="Venta",
            y="Rentabilidad",
            size="Venta",
            color="Rentabilidad",
            text="Marca_Master",
            title="Volumen vs Margen"
        )
        st.plotly_chart(fig_bubble, use_container_width=True)

# --- TAB 4: SALUD FINANCIERA (RIESGO) ---
with tab4:
    st.subheader("💳 Ventas vs Riesgo de Cobro")
    st.markdown("Analiza a quién le estamos vendiendo y qué tan rápido pagan (Datos de Cartera Actual).")
    
    # Agrupamos por Cliente
    df_risk = df_act.groupby(['nombre_cliente', 'Poblacion']).agg(
        Venta_Anual=('valor_venta', 'sum'),
        Dias_Mora_Max=('Max_Dias_Mora', 'max') # Dato traído del cruce exacto
    ).reset_index()
    
    # Filtro para ver clientes relevantes
    df_risk = df_risk[df_risk['Venta_Anual'] > 2000000] # Solo clientes > 2M
    
    col_r1, col_r2 = st.columns([3, 1])
    
    with col_r1:
        fig_risk = px.scatter(
            df_risk,
            x="Dias_Mora_Max",
            y="Venta_Anual",
            color="Poblacion",
            size="Venta_Anual",
            hover_name="nombre_cliente",
            title="Matriz de Riesgo: Exposición ($) vs Días Mora Real",
            labels={"Dias_Mora_Max": "Días de Mora (Cartera Actual)", "Venta_Anual": "Venta Acumulada Periodo"}
        )
        # Zona Peligrosa
        fig_risk.add_vline(x=60, line_dash="dash", line_color="red", annotation_text="Límite 60 Días")
        fig_risk.add_hrect(y0=0, y1=df_risk['Venta_Anual'].max(), x0=60, fillcolor="red", opacity=0.1)
        
        st.plotly_chart(fig_risk, use_container_width=True)
        
    with col_r2:
        st.error("🚨 Clientes Críticos")
        st.caption("Ventas altas + Mora > 60 días")
        
        criticos = df_risk[df_risk['Dias_Mora_Max'] > 60].sort_values('Venta_Anual', ascending=False)
        st.dataframe(
            criticos[['nombre_cliente', 'Dias_Mora_Max']],
            column_config={"Dias_Mora_Max": st.column_config.NumberColumn("Días Mora", format="%d")},
            hide_index=True
        )
