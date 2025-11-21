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
st.set_page_config(page_title="Master Brain Ultra - Estrategia Real", page_icon="♟️", layout="wide")

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(to bottom right, #ffffff, #f0f2f6);
        border-left: 5px solid #003865;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    h1, h2, h3 { color: #003865; font-family: 'Arial', sans-serif; font-weight: 700; }
    div[data-testid="stMetricValue"] { font-size: 26px; color: #0058A7; font-weight: bold; }
    .stDataFrame { border: 1px solid #e0e0e0; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MOTORES DE LIMPIEZA (EL CEREBRO LÓGICO)
# ==============================================================================

def normalizar_texto(texto):
    """Limpia nombres de ciudades y marcas (quita tildes, espacios dobles)."""
    if not isinstance(texto, str): return str(texto) if texto is not None else "SIN INFO"
    try:
        texto = str(texto)
        # Quitar tildes y caracteres raros
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        # Mayúsculas y quitar espacios extra
        return texto_sin_tildes.upper().strip()
    except: return "ERROR TEXTO"

def limpiar_nit_maestro(nit):
    """
    🔧 FUNCIÓN CRÍTICA: Convierte cualquier NIT (con puntos, guiones, espacios, texto)
    en una cadena limpia de SOLO NÚMEROS para poder cruzar Ventas con Población.
    """
    if pd.isna(nit): return "0"
    s_nit = str(nit)
    # Eliminar todo lo que NO sea un número (0-9)
    s_limpio = re.sub(r'[^0-9]', '', s_nit)
    # Si queda vacío (ej: era todo letras), retornar '0'
    return s_limpio if s_limpio else "0"

def clasificar_marca_estrategica(fila):
    """
    LÓGICA MAESTRA DE CATEGORÍAS:
    1. ¿Es Marca Estratégica (Lista Blanca)? -> Se queda con su nombre (ABRACOL, etc).
    2. Si NO es estratégica:
       ¿Es PINTUCO? (Buscamos 'Pintuco' en Marca, Categoria o Nombre).
    3. Si no es nada de lo anterior -> 'OTROS' (Accesorios, genéricos, etc).
    """
    # Unimos todo el texto del producto para buscar palabras clave
    marca = normalizar_texto(fila.get('marca_producto', ''))
    categoria = normalizar_texto(fila.get('categoria_producto', ''))
    articulo = normalizar_texto(fila.get('nombre_articulo', ''))
    
    texto_completo = f"{marca} {categoria} {articulo}"
    
    # LISTA BLANCA (Marcas que queremos ver separadas SÍ o SÍ)
    lista_estrategica = [
        'ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', 
        'SAINT GOBAIN', 'ALLEGION', 'SEGUREX', 'POLVOS', 'DELTA', 'MASTERD', 'GLOBAL'
    ]
    
    for m in lista_estrategica:
        if m in texto_completo:
            return m # Es estratégica, la devolvemos tal cual

    # Si llegamos aquí, NO es estratégica. Verificamos si es PINTUCO.
    # Buscamos Pintuco o sus marcas hijas obvias
    claves_pintuco = ['PINTUCO', 'TERINSA', 'ICO', 'VINILTEX', 'KORAZA']
    
    if 'PINTUCO' in marca: return 'PINTUCO' # Si la marca ya dice Pintuco
    
    for k in claves_pintuco:
        if k in texto_completo:
            return 'PINTUCO'

    # Si no es estratégica ni Pintuco, es OTROS
    return 'OTROS'

# ==============================================================================
# 3. CONEXIÓN CON DROPBOX (DATOS POBLACIÓN Y CARTERA)
# ==============================================================================
@st.cache_data(ttl=3600)
def cargar_datos_dropbox():
    try:
        # Intentar leer credenciales
        try:
            APP_KEY = st.secrets["dropbox"]["app_key"]
            APP_SECRET = st.secrets["dropbox"]["app_secret"]
            REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]
        except:
            # Si no hay secrets, retornamos vacío sin romper
            return pd.DataFrame()

        with dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN) as dbx:
            # Ruta del archivo en Dropbox
            ruta = '/data/cartera_detalle.csv'
            metadata, res = dbx.files_download(path=ruta)
            
            # Leer CSV sin cabeceras (asumiendo formato del pantallazo)
            contenido = res.content.decode('latin-1')
            
            cols = [
                'Serie', 'Numero', 'FechaDoc', 'FechaVenc', 'CodCliente',
                'NombreCliente', 'Nit', 'Poblacion', 'Provincia', 'Tel1', 'Tel2',
                'Vendedor', 'Entidad', 'Email', 'Importe', 'Descuento',
                'Cupo', 'DiasVencido'
            ]
            
            df_drop = pd.read_csv(io.StringIO(contenido), header=None, names=cols, sep='|', engine='python')
            
            # --- LIMPIEZA CRÍTICA PARA INTEGRACIÓN DE POBLACIONES ---
            # 1. Limpiar la llave (NIT) para que sea idéntica a Ventas
            df_drop['Key_Nit'] = df_drop['Nit'].apply(limpiar_nit_maestro)
            
            # 2. Limpiar Población
            df_drop['Poblacion'] = df_drop['Poblacion'].apply(normalizar_texto)
            
            # 3. Numéricos
            df_drop['Importe'] = pd.to_numeric(df_drop['Importe'], errors='coerce').fillna(0)
            df_drop['DiasVencido'] = pd.to_numeric(df_drop['DiasVencido'], errors='coerce').fillna(0)

            # --- AGRUPAR PARA OBTENER UN MAESTRO DE CLIENTES ---
            # Un cliente puede tener muchas facturas. Necesitamos 1 registro por cliente con su Población.
            # Usamos la moda (la población que más se repite para ese cliente)
            def obtener_moda(series):
                val = series.mode()
                return val[0] if not val.empty else "SIN POBLACION"

            df_maestro = df_drop.groupby('Key_Nit').agg({
                'Poblacion': obtener_moda,
                'DiasVencido': 'max',  # El peor retraso define el riesgo
                'Importe': 'sum'       # Deuda Total
            }).reset_index()
            
            df_maestro.rename(columns={'DiasVencido': 'Max_Dias_Mora', 'Importe': 'Deuda_Total'}, inplace=True)
            
            return df_maestro

    except Exception as e:
        st.error(f"Error conectando a Dropbox: {e}")
        return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO DE DATOS (VENTAS + DROPBOX)
# ==============================================================================

# Verificación de seguridad
if 'df_ventas' not in st.session_state:
    st.warning("⚠️ No hay datos de ventas cargados. Por favor ve al inicio y carga el archivo.")
    st.stop()

# Cargar Ventas desde Memoria
df_raw = st.session_state.df_ventas.copy()

# Filtros básicos de ventas (Facturas y Notas)
filtro_neto = 'FACTURA|NOTA.*CREDITO'
df_raw['TipoDocumento'] = df_raw['TipoDocumento'].astype(str)
df = df_raw[df_raw['TipoDocumento'].str.contains(filtro_neto, case=False, regex=True)].copy()

# Convertir numéricos de Ventas
for col in ['valor_venta', 'unidades_vendidas', 'costo_unitario']:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

df['Margen_Pesos'] = df['valor_venta'] - (df['unidades_vendidas'] * df['costo_unitario'])

# --- APLICAR NUEVA LÓGICA DE MARCAS ---
df['Marca_Master'] = df.apply(clasificar_marca_estrategica, axis=1)

# --- CREAR LLAVE DE CRUCE EN VENTAS ---
# Usamos la misma función 'limpiar_nit_maestro' que usamos en Dropbox
df['Key_Nit'] = df['cliente_id'].apply(limpiar_nit_maestro)

# --- CARGAR DROPBOX Y CRUZAR ---
with st.spinner("🔄 Integrando Poblaciones y Cartera..."):
    df_logistica = cargar_datos_dropbox()

if not df_logistica.empty:
    # LEFT JOIN: Ventas es la base, traemos Población de df_logistica
    df_full = pd.merge(df, df_logistica, on='Key_Nit', how='left')
    
    # Rellenar vacíos si el cliente compró pero no está en el archivo de cartera
    df_full['Poblacion'] = df_full['Poblacion'].fillna('SIN INFO LOGISTICA')
    df_full['Max_Dias_Mora'] = df_full['Max_Dias_Mora'].fillna(0)
else:
    st.warning("⚠️ No se pudo cargar la información logística. Mostrando solo datos de ventas.")
    df_full = df.copy()
    df_full['Poblacion'] = 'ERROR CARGA'
    df_full['Max_Dias_Mora'] = 0

# ==============================================================================
# 5. INTERFAZ Y FILTROS
# ==============================================================================
st.sidebar.header("🎛️ Filtros Maestros")

# Años
anios = sorted(df_full['anio'].unique(), reverse=True)
anio_act = st.sidebar.selectbox("Año Actual", anios, index=0)
anio_base = st.sidebar.selectbox("Año Base (Comparativo)", [a for a in anios if a != anio_act] + ["Ninguno"], index=0)

st.sidebar.markdown("---")

# Marcas (Usando la nueva columna Marca_Master)
marcas_disp = sorted(df_full['Marca_Master'].unique())
sel_marcas = st.sidebar.multiselect("Marcas", marcas_disp, default=marcas_disp)

# Poblaciones (Ahora sí integradas)
zonas_disp = ["TODAS"] + sorted(df_full['Poblacion'].unique())
sel_zona = st.sidebar.selectbox("Población / Zona", zonas_disp)

# --- APLICAR FILTROS AL DATAFRAME ---
df_fil = df_full[df_full['Marca_Master'].isin(sel_marcas)].copy()

if sel_zona != "TODAS":
    df_fil = df_fil[df_fil['Poblacion'] == sel_zona]

# Separar DataFrames
df_now = df_fil[df_fil['anio'] == anio_act]
df_prev = df_fil[df_fil['anio'] == anio_base] if anio_base != "Ninguno" else pd.DataFrame()

# ==============================================================================
# 6. VISUALIZACIÓN (KPIS Y GRÁFICOS)
# ==============================================================================
st.title("♟️ Master Brain: Crecimiento Real & Logística")
st.markdown(f"**Viendo:** {sel_zona} | **Comparando:** {anio_act} vs {anio_base}")

# KPIs Generales
v_act = df_now['valor_venta'].sum()
v_prev = df_prev['valor_venta'].sum() if not df_prev.empty else 0
crec_pct = ((v_act - v_prev) / v_prev * 100) if v_prev else 0

m_act = df_now['Margen_Pesos'].sum()
rent_act = (m_act / v_act * 100) if v_act else 0

# Mora Promedio (Ponderada por clientes activos)
mora_prom = df_now[df_now['valor_venta']>0]['Max_Dias_Mora'].mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Venta Total", f"${v_act:,.0f}", f"{crec_pct:+.1f}%")
k2.metric("Margen $", f"${m_act:,.0f}", "Utilidad Bruta")
k3.metric("Rentabilidad %", f"{rent_act:.1f}%", "Margen / Venta")
k4.metric("Días Mora Promedio", f"{mora_prom:.0f} días", "Riesgo Cartera", delta_color="inverse")

# TABS
tab1, tab2, tab3, tab4 = st.tabs(["🚀 Crecimiento Real", "🗺️ Logística (Poblaciones)", "💎 Share", "🩸 Riesgo"])

# --- TAB 1: CRECIMIENTO REAL ---
with tab1:
    st.subheader("Anatomía del Crecimiento (Sin 'Otros' ensuciando)")
    if not df_prev.empty:
        # Agrupar
        g_act = df_now.groupby('Marca_Master')['valor_venta'].sum().reset_index().rename(columns={'valor_venta':'Venta_Actual'})
        g_prev = df_prev.groupby('Marca_Master')['valor_venta'].sum().reset_index().rename(columns={'valor_venta':'Venta_Anterior'})
        
        df_w = pd.merge(g_act, g_prev, on='Marca_Master', how='outer').fillna(0)
        df_w['Variacion'] = df_w['Venta_Actual'] - df_w['Venta_Anterior']
        df_w = df_w.sort_values('Variacion', ascending=False)
        
        col_w1, col_w2 = st.columns([2, 1])
        with col_w1:
            fig = go.Figure(go.Waterfall(
                name="Variación", orientation="v",
                measure=["relative"] * len(df_w),
                x=df_w['Marca_Master'],
                y=df_w['Variacion'],
                text=[f"${x/1e6:.1f}M" for x in df_w['Variacion']],
                textposition="outside",
                decreasing={"marker":{"color":"#E74C3C"}},
                increasing={"marker":{"color":"#2ECC71"}}
            ))
            fig.update_layout(title="Impacto en Dinero por Marca ($)", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with col_w2:
            st.dataframe(df_w[['Marca_Master', 'Variacion']], hide_index=True)
    else:
        st.info("Selecciona un año base para ver el waterfall.")

# --- TAB 2: LOGÍSTICA (SOLUCIÓN DEL ERROR) ---
with tab2:
    st.subheader("Mapa de Eficiencia Logística")
    st.markdown("**Eje X:** Ticket Promedio (Eficiencia) | **Eje Y:** Rentabilidad | **Puntos:** Poblaciones")
    
    # Agrupar por Población (Ahora limpias)
    df_log = df_now.groupby('Poblacion').agg(
        Venta=('valor_venta', 'sum'),
        Margen=('Margen_Pesos', 'sum'),
        Pedidos=('Serie', 'nunique') # Asumiendo Serie como ID pedido
    ).reset_index()
    
    df_log['Ticket'] = df_log['Venta'] / df_log['Pedidos']
    df_log['Rentabilidad'] = (df_log['Margen'] / df_log['Venta']) * 100
    
    # Filtrar poblaciones muy pequeñas para no ensuciar gráfico
    df_log = df_log[df_log['Venta'] > 100000] 
    
    fig_map = px.scatter(
        df_log,
        x="Ticket",
        y="Rentabilidad",
        size="Venta",
        color="Rentabilidad",
        text="Poblacion",
        color_continuous_scale="RdYlGn",
        title="¿Dónde cuesta más servir?"
    )
    fig_map.add_vline(x=df_log['Ticket'].mean(), line_dash="dash", annotation_text="Promedio")
    st.plotly_chart(fig_map, use_container_width=True)

# --- TAB 3: SHARE ---
with tab3:
    st.subheader("Distribución de Venta")
    df_share = df_now.groupby('Marca_Master')['valor_venta'].sum().reset_index()
    fig_pie = px.pie(df_share, values='valor_venta', names='Marca_Master', title="Share de Mercado Real")
    st.plotly_chart(fig_pie, use_container_width=True)

# --- TAB 4: RIESGO ---
with tab4:
    st.subheader("Clientes Críticos")
    st.markdown("Clientes con alta compra pero alta mora.")
    
    # Agrupar por Cliente
    df_risk = df_now.groupby(['nombre_cliente', 'Poblacion']).agg(
        Compra=('valor_venta', 'sum'),
        Mora_Max=('Max_Dias_Mora', 'max')
    ).reset_index()
    
    # Filtro Top Clientes
    df_risk = df_risk[df_risk['Compra'] > 1000000]
    
    fig_risk = px.scatter(
        df_risk,
        x="Mora_Max", y="Compra",
        color="Poblacion",
        size="Compra",
        hover_name="nombre_cliente",
        title="Matriz Riesgo vs Venta"
    )
    fig_risk.add_vline(x=60, line_color="red", line_dash="dash")
    st.plotly_chart(fig_risk, use_container_width=True)
