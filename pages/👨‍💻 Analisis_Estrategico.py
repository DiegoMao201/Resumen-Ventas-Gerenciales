# ==============================================================================
# 🧠 MASTER BRAIN V.ULTRA - CENTRO DE ESTRATEGIA & LOGÍSTICA
# Archivo: pages/Analisis_Estrategico.py
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import unicodedata
import io
import dropbox
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
st.set_page_config(page_title="Master Brain Estratégico", page_icon="♟️", layout="wide")

# ==============================================================================
# 🎨 ESTILOS DE ALTO NIVEL (CSS)
# ==============================================================================
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(to right, #f8f9fa, #e9ecef);
        border-left: 6px solid #2E86C1;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    div[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; color: #1B4F72; }
    h1, h2, h3 { color: #154360; font-family: 'Helvetica', sans-serif; }
    .stDataFrame { border: 1px solid #ddd; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔧 MOTOR DE INTELIGENCIA DE DATOS (FUNCIONES)
# ==============================================================================
def normalizar_texto(texto):
    if not isinstance(texto, str): return str(texto) if texto is not None else ""
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').replace('_', ' ').replace('.', ' ').strip()
    except: return str(texto)

def clasificar_marca_avanzado(fila):
    """
    Clasificación jerárquica estricta.
    Busca primero en MARCA, luego en CATEGORIA, luego en DESCRIPCION.
    Prioriza las marcas estratégicas definidas.
    """
    # Unimos todo el texto disponible del producto para buscar palabras clave
    texto_busqueda = f"{normalizar_texto(fila.get('marca_producto', ''))} {normalizar_texto(fila.get('categoria_producto', ''))} {normalizar_texto(fila.get('nombre_articulo', ''))}"
    
    # LISTA BLANCA ESTRATÉGICA (Prioridad Alta)
    marcas_vip = [
        'ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', 
        'SAINT GOBAIN', 'ALLEGION', 'SEGUREX', 'POLVOS', 'DELTA', 'MASTERD'
    ]
    
    for vip in marcas_vip:
        if vip in texto_busqueda:
            return vip # Retorna el nombre limpio de la marca VIP
            
    # Si no es ninguna de las anteriores, verificamos si es Pintuco
    if 'PINTUCO' in texto_busqueda or 'VINILTEX' in texto_busqueda or 'KORAZA' in texto_busqueda:
        return 'PINTUCO'
        
    # Si no, retornamos la categoría original o "OTROS"
    cat_orig = normalizar_texto(fila.get('categoria_producto', 'OTRAS'))
    return cat_orig if cat_orig else "OTROS"

@st.cache_data(ttl=3600)
def cargar_datos_cartera_inteligente():
    """
    Carga 'cartera_detalle' detectando automáticamente la columna de ID y separadores.
    """
    try:
        ruta_cartera = "/data/cartera_detalle.csv" 
        
        # Recuperar credenciales (manejo seguro de errores)
        if 'APP_CONFIG' not in st.session_state:
            # Intento de fallback si no se ha pasado por el login
            return pd.DataFrame()

        with dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, 
                             app_secret=st.secrets.dropbox.app_secret, 
                             oauth2_refresh_token=st.secrets.dropbox.refresh_token) as dbx:
            _, res = dbx.files_download(path=ruta_cartera)
            contenido = res.content.decode('latin-1')
            
            # 1. Detección de Separador
            separador = '|' if contenido.count('|') > contenido.count(',') else ','
            df = pd.read_csv(io.StringIO(contenido), sep=separador, engine='python', on_bad_lines='warn')
            
            # 2. Normalización de Columnas
            df.columns = [normalizar_texto(c) for c in df.columns]
            
            # 3. Detección Inteligente de ID Cliente
            # Palabras clave para buscar la columna ID
            posibles_ids = ['NIT', 'IDENTIFICACION', 'CEDULA', 'CODIGO', 'CLIENTEID', 'IDCLIENTE', 'TERCERO']
            col_id_encontrada = None
            
            for col in df.columns:
                for key in posibles_ids:
                    if key in col:
                        col_id_encontrada = col
                        break
                if col_id_encontrada: break
            
            # Si no encuentra nombre conocido, usa la PRIMERA columna (usualmente es el ID)
            if not col_id_encontrada and not df.empty:
                col_id_encontrada = df.columns[0]
                
            # 4. Detección de Población y Días
            col_pob = next((c for c in df.columns if 'POBLACION' in c or 'CIUDAD' in c), None)
            col_dias = next((c for c in df.columns if 'DIA' in c or 'VENCIM' in c), None)
            col_saldo = next((c for c in df.columns if 'SALDO' in c or 'VALOR' in c), None)
            
            if not col_id_encontrada: return pd.DataFrame() # Fallo crítico

            # Renombrar
            mapeo = {col_id_encontrada: 'cliente_id'}
            if col_pob: mapeo[col_pob] = 'Poblacion'
            if col_dias: mapeo[col_dias] = 'Dias_Cartera'
            if col_saldo: mapeo[col_saldo] = 'Saldo_Cartera'
            
            df = df.rename(columns=mapeo)
            
            # Estandarizar ID
            df['cliente_id'] = df['cliente_id'].astype(str).str.strip()
            
            # Agrupar para tener 1 registro por cliente
            # Priorizamos: Población (Moda), Días (Máximo riesgo), Saldo (Suma)
            agg_dict = {}
            if 'Poblacion' in df.columns: 
                agg_dict['Poblacion'] = lambda x: x.mode()[0] if not x.mode().empty else 'SIN DATA'
            if 'Dias_Cartera' in df.columns:
                df['Dias_Cartera'] = pd.to_numeric(df['Dias_Cartera'], errors='coerce').fillna(0)
                agg_dict['Dias_Cartera'] = 'max'
            if 'Saldo_Cartera' in df.columns:
                df['Saldo_Cartera'] = pd.to_numeric(df['Saldo_Cartera'], errors='coerce').fillna(0)
                agg_dict['Saldo_Cartera'] = 'sum'
                
            if agg_dict:
                df_maestro = df.groupby('cliente_id').agg(agg_dict).reset_index()
                return df_maestro
            else:
                return df[['cliente_id']].drop_duplicates()

    except Exception as e:
        st.error(f"Error interno cargando cartera: {str(e)}")
        return pd.DataFrame()

# ==============================================================================
# 1. PROCESAMIENTO Y FUSIÓN DE DATOS
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.warning("⚠️ Por favor inicia sesión en el 'Resumen Mensual' primero.")
    st.stop()

# --- PREPARACIÓN VENTAS ---
df_raw = st.session_state.df_ventas.copy()
filtro_neto = 'FACTURA|NOTA.*CREDITO'
df_raw['TipoDocumento'] = df_raw['TipoDocumento'].astype(str)
df = df_raw[df_raw['TipoDocumento'].str.contains(filtro_neto, na=False, case=False, regex=True)].copy()

# Conversiones Numéricas
for col in ['valor_venta', 'unidades_vendidas', 'costo_unitario']:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

df['Margen_Pesos'] = df['valor_venta'] - (df['unidades_vendidas'] * df['costo_unitario'])

# --- CLASIFICACIÓN DE MARCAS (CORREGIDA) ---
# Aplicamos la función fila por fila para mayor precisión
df['Marca_Analisis'] = df.apply(clasificar_marca_avanzado, axis=1)

# --- CRUCE CON CARTERA (CORREGIDO) ---
with st.spinner("Conectando con base de datos de Cartera y Población..."):
    df_cartera = cargar_datos_cartera_inteligente()

df['cliente_id'] = df['cliente_id'].astype(str).str.strip()

if not df_cartera.empty:
    df_full = pd.merge(df, df_cartera, on='cliente_id', how='left')
    # Rellenar nulos post-cruce
    if 'Poblacion' in df_full.columns: df_full['Poblacion'] = df_full['Poblacion'].fillna('SIN REGISTRO LOGISTICO')
    else: df_full['Poblacion'] = 'NO DATA'
    
    if 'Dias_Cartera' in df_full.columns: df_full['Dias_Cartera'] = df_full['Dias_Cartera'].fillna(0)
    else: df_full['Dias_Cartera'] = 0
else:
    df_full = df.copy()
    df_full['Poblacion'] = 'ERROR CARGA CARTERA'
    df_full['Dias_Cartera'] = 0

# ==============================================================================
# 2. DASHBOARD INTERACTIVO
# ==============================================================================
st.sidebar.header("🎛️ Panel de Control Ejecutivo")
st.sidebar.markdown("---")

# Filtros
anio_actual = st.sidebar.selectbox("Año Análisis", sorted(df_full['anio'].unique(), reverse=True))
anio_comp = st.sidebar.selectbox("Comparar contra", sorted(df_full['anio'].unique(), reverse=True)[1:] + ["Ninguno"], index=0)

# Filtro Multicategoría
categorias_disp = sorted(df_full['Marca_Analisis'].unique())
cats_sel = st.sidebar.multiselect("Filtro de Marcas/Categorías", options=categorias_disp, default=categorias_disp)

# Aplicar Filtros
df_act = df_full[(df_full['anio'] == anio_actual) & (df_full['Marca_Analisis'].isin(cats_sel))].copy()
df_ant = df_full[(df_full['anio'] == anio_comp) & (df_full['Marca_Analisis'].isin(cats_sel))].copy() if anio_comp != "Ninguno" else pd.DataFrame()

# ==============================================================================
# 3. RESUMEN KPI (HEADLINES)
# ==============================================================================
st.title("🚀 Inteligencia de Negocios 360°")
st.markdown(f"**Periodo:** {anio_actual} vs {anio_comp if anio_comp != 'Ninguno' else 'N/A'} | **Alcance:** {len(cats_sel)} Marcas seleccionadas")

col1, col2, col3, col4 = st.columns(4)

v_act = df_act['valor_venta'].sum()
v_ant = df_ant['valor_venta'].sum() if not df_ant.empty else 0
var_v = ((v_act - v_ant) / v_ant * 100) if v_ant else 0

m_act = df_act['Margen_Pesos'].sum()
m_ant = df_ant['Margen_Pesos'].sum() if not df_ant.empty else 0
var_m = ((m_act - m_ant) / m_ant * 100) if m_ant else 0

rent_act = (m_act / v_act * 100) if v_act else 0
rent_ant = (m_ant / v_ant * 100) if v_ant else 0

dias_cartera_prom = df_act[df_act['valor_venta'] > 0]['Dias_Cartera'].mean() # Promedio simple de clientes activos

with col1: st.metric("Ventas Totales", f"${v_act:,.0f}", f"{var_v:+.1f}%")
with col2: st.metric("Margen Bruto", f"${m_act:,.0f}", f"{var_m:+.1f}%")
with col3: st.metric("Rentabilidad %", f"{rent_act:.2f}%", f"{(rent_act - rent_ant):+.2f} pp")
with col4: st.metric("Días Cartera (Prom)", f"{dias_cartera_prom:.0f}", delta="Días promedio", delta_color="off")

# ==============================================================================
# 4. ANÁLISIS PROFUNDO (TABS)
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "💎 Share & Posicionamiento", 
    "📈 Crecimiento (YoY)", 
    "🚚 Logística & Costo Servir",
    "💰 Riesgo de Cartera"
])

# --- TAB 1: SHARE DE MERCADO INTERNO (SOLUCIÓN AL ERROR DE CATEGORÍAS) ---
with tab1:
    st.subheader("📊 Peso y Participación por Marca Estratégica")
    
    # Agrupación Maestra
    df_share = df_act.groupby('Marca_Analisis').agg(
        Venta=('valor_venta', 'sum'),
        Margen=('Margen_Pesos', 'sum')
    ).reset_index()
    
    # Calcular Participación
    total_v = df_share['Venta'].sum()
    df_share['Share_Venta'] = (df_share['Venta'] / total_v) * 100
    df_share['Rentabilidad'] = (df_share['Margen'] / df_share['Venta']) * 100
    
    # Si hay comparativo, traer crecimiento
    if not df_ant.empty:
        df_share_ant = df_ant.groupby('Marca_Analisis')['valor_venta'].sum().reset_index().rename(columns={'valor_venta': 'Venta_Ant'})
        df_share = pd.merge(df_share, df_share_ant, on='Marca_Analisis', how='left').fillna(0)
        df_share['Crecimiento_Dinero'] = df_share['Venta'] - df_share['Venta_Ant']
        df_share['Crecimiento_Pct'] = np.where(df_share['Venta_Ant']!=0, (df_share['Crecimiento_Dinero']/df_share['Venta_Ant'])*100, 0)
    else:
        df_share['Crecimiento_Dinero'] = 0
        df_share['Crecimiento_Pct'] = 0

    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.markdown("##### 🍰 Distribución de Ventas (Share of Wallet)")
        fig_treemap = px.treemap(
            df_share, 
            path=[px.Constant("FERREINOX"), 'Marca_Analisis'], 
            values='Venta',
            color='Rentabilidad',
            color_continuous_scale='RdYlGn',
            hover_data=['Share_Venta', 'Crecimiento_Pct'],
            title="Tamaño = Venta Total | Color = Rentabilidad %"
        )
        st.plotly_chart(fig_treemap, use_container_width=True)
        
    with c2:
        st.markdown("##### 🏆 Ranking de Aporte")
        # Tabla sofisticada
        df_display = df_share[['Marca_Analisis', 'Venta', 'Share_Venta', 'Crecimiento_Pct', 'Rentabilidad']].sort_values('Venta', ascending=False)
        
        st.dataframe(
            df_display,
            column_config={
                "Venta": st.column_config.NumberColumn(format="$ %d"),
                "Share_Venta": st.column_config.ProgressColumn("Part. %", format="%.1f%%", min_value=0, max_value=100),
                "Crecimiento_Pct": st.column_config.NumberColumn("Crec. %", format="%.1f%%"),
                "Rentabilidad": st.column_config.NumberColumn("Mg %", format="%.1f%%")
            },
            hide_index=True,
            use_container_width=True
        )

# --- TAB 2: CRECIMIENTO Y EVOLUCIÓN ---
with tab2:
    col_ev1, col_ev2 = st.columns([2, 1])
    
    with col_ev1:
        st.subheader("Comparativa Mensual de Ventas")
        monthly_act = df_act.groupby('mes')['valor_venta'].sum().reset_index()
        
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=monthly_act['mes'], y=monthly_act['valor_venta'], mode='lines+markers', name=f'{anio_actual}', line=dict(color='#2E86C1', width=3)))
        
        if not df_ant.empty:
            monthly_ant = df_ant.groupby('mes')['valor_venta'].sum().reset_index()
            fig_line.add_trace(go.Scatter(x=monthly_ant['mes'], y=monthly_ant['valor_venta'], mode='lines+markers', name=f'{anio_comp}', line=dict(color='#AED6F1', dash='dash')))
            
        fig_line.update_layout(xaxis_title="Mes", yaxis_title="Ventas ($)", hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)
        
    with col_ev2:
        st.subheader("Puente de Crecimiento (Waterfall)")
        if not df_ant.empty:
            df_waterfall = df_share.sort_values('Crecimiento_Dinero', ascending=False)
            
            fig_water = go.Figure(go.Waterfall(
                name="Crecimiento", orientation="v",
                measure=["relative"] * len(df_waterfall),
                x=df_waterfall['Marca_Analisis'],
                y=df_waterfall['Crecimiento_Dinero'],
                text=[f"${x/1e6:.1f}M" for x in df_waterfall['Crecimiento_Dinero']],
                connector={"line":{"color":"rgb(63, 63, 63)"}},
            ))
            fig_water.update_layout(title="¿Qué marcas aportaron más dinero este año?")
            st.plotly_chart(fig_water, use_container_width=True)
        else:
            st.info("Selecciona un año comparativo para ver el puente de crecimiento.")

# --- TAB 3: LOGÍSTICA Y POBLACIÓN ---
with tab3:
    st.subheader("🗺️ Análisis de Cobertura y Costo por Servir")
    
    df_pob = df_act.groupby('Poblacion').agg(
        Ventas=('valor_venta', 'sum'),
        Pedidos=('Serie', 'nunique'),
        Margen_Pesos=('Margen_Pesos', 'sum')
    ).reset_index()
    
    df_pob['Ticket_Promedio'] = df_pob['Ventas'] / df_pob['Pedidos']
    df_pob['Margen_Pct'] = (df_pob['Margen_Pesos'] / df_pob['Ventas']) * 100
    
    # Filtrar poblaciones muy pequeñas para limpiar el gráfico
    df_pob_viz = df_pob[df_pob['Ventas'] > df_pob['Ventas'].quantile(0.2)].copy()
    
    col_log1, col_log2 = st.columns([3, 1])
    
    with col_log1:
        fig_bubble = px.scatter(
            df_pob_viz,
            x="Ticket_Promedio",
            y="Margen_Pct",
            size="Ventas",
            color="Poblacion", # Podrías agrupar por región si tuvieras ese dato
            hover_name="Poblacion",
            text="Poblacion",
            title="Eficiencia Logística: Ticket Promedio vs Rentabilidad",
            labels={"Ticket_Promedio": "Ticket Promedio ($)", "Margen_Pct": "Rentabilidad %"}
        )
        fig_bubble.update_traces(textposition='top center')
        # Línea de referencia
        avg_ticket = df_pob['Ticket_Promedio'].mean()
        fig_bubble.add_vline(x=avg_ticket, line_dash="dash", annotation_text=f"Prom: ${avg_ticket:,.0f}")
        st.plotly_chart(fig_bubble, use_container_width=True)
        
    with col_log2:
        st.markdown("##### 🚨 Ojo con estas Poblaciones")
        st.caption("Bajo Ticket = Alto Costo Logístico Relativo")
        ineficientes = df_pob_viz.sort_values('Ticket_Promedio').head(10)
        st.dataframe(
            ineficientes[['Poblacion', 'Ticket_Promedio', 'Margen_Pct']],
            column_config={"Ticket_Promedio": st.column_config.NumberColumn(format="$ %d"), "Margen_Pct": st.column_config.NumberColumn(format="%.1f%%")},
            hide_index=True
        )

# --- TAB 4: RIESGO Y CARTERA ---
with tab4:
    st.subheader("💳 Salud Financiera de la Venta")
    
    # Agrupamos por cliente para cruzar venta con días de cartera real
    df_risk = df_act.groupby(['nombre_cliente', 'Poblacion']).agg(
        Venta_Anual=('valor_venta', 'sum'),
        Dias_Cartera=('Dias_Cartera', 'max') # Tomamos el peor día registrado
    ).reset_index()
    
    # Filtrar clientes relevantes
    df_risk = df_risk[df_risk['Venta_Anual'] > 1000000]
    
    fig_scatter_risk = px.scatter(
        df_risk,
        x="Dias_Cartera",
        y="Venta_Anual",
        color="Poblacion",
        size="Venta_Anual",
        hover_name="nombre_cliente",
        title="Matriz de Riesgo: Exposición ($) vs Días de Mora",
        labels={"Dias_Cartera": "Días Mora / Cartera", "Venta_Anual": "Venta Acumulada"}
    )
    # Zona de Riesgo
    fig_scatter_risk.add_vrect(x0=60, x1=df_risk['Dias_Cartera'].max()*1.1, fillcolor="red", opacity=0.1, annotation_text="RIESGO > 60 DÍAS")
    
    st.plotly_chart(fig_scatter_risk, use_container_width=True)
