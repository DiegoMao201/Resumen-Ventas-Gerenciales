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
# 🧠 CONFIGURACIÓN MAESTRA Y ESTILOS
# ==============================================================================
st.set_page_config(page_title="Master Brain Ultra - Estrategia Real", page_icon="♟️", layout="wide")

st.markdown("""
<style>
    /* Estilo de Tarjetas Métricas */
    .metric-card {
        background: linear-gradient(to bottom right, #ffffff, #f0f2f6);
        border-left: 5px solid #003865;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    h1, h2, h3 { color: #003865; font-family: 'Arial', sans-serif; font-weight: 700; }
    
    /* Ajustes de Tablas */
    .stDataFrame { border: 1px solid #e0e0e0; border-radius: 5px; }
    
    /* Métricas Grandes */
    div[data-testid="stMetricValue"] { font-size: 26px; color: #0058A7; font-weight: bold; }
    div[data-testid="stMetricDelta"] { font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔧 MOTOR DE INTELIGENCIA 1: LIMPIEZA DE TEXTO
# ==============================================================================
def normalizar_texto(texto):
    """Limpia textos para comparaciones (quita tildes, mayúsculas, espacios extra)."""
    if not isinstance(texto, str): return str(texto) if texto is not None else ""
    try:
        texto = str(texto)
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        # Mantenemos solo letras y números para nombres, eliminamos caracteres raros
        return texto_sin_tildes.upper().strip()
    except: return ""

def limpiar_nit(nit):
    """Limpia el NIT/ID para asegurar el cruce (solo deja números)."""
    if pd.isna(nit): return "0"
    s_nit = str(nit)
    # Elimina puntos, comas, guiones y espacios, dejando solo dígitos
    s_limpio = re.sub(r'[^0-9]', '', s_nit)
    return s_limpio if s_limpio else "0"

# ==============================================================================
# 🔧 MOTOR DE INTELIGENCIA 2: LÓGICA DE MARCAS (LA SOLICITUD CLAVE)
# ==============================================================================
def clasificar_marca_ultra(fila):
    """
    LÓGICA DE SEGREGACIÓN REAL:
    1. Busca Marcas Estratégicas (Independientes).
    2. Busca explícitamente PINTUCO (o sus submarcas clave).
    3. Todo lo demás se va a 'OTROS' (Accesorios, genéricos, etc).
    """
    # Unimos Marca + Categoria + Nombre para buscar palabras clave
    marca_original = normalizar_texto(fila.get('marca_producto', ''))
    categoria = normalizar_texto(fila.get('categoria_producto', ''))
    articulo = normalizar_texto(fila.get('nombre_articulo', ''))
    
    texto_busqueda = f"{marca_original} {categoria} {articulo}"
    
    # --- NIVEL 1: MARCAS ESTRATÉGICAS (LISTA BLANCA) ---
    # Estas se separan SIEMPRE.
    lista_estrategica = [
        'ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', 
        'SAINT GOBAIN', 'ALLEGION', 'SEGUREX', 'POLVOS', 'DELTA', 'MASTERD'
    ]
    
    for marca in lista_estrategica:
        if marca in texto_busqueda:
            return marca # ¡Es una marca estratégica!

    # --- NIVEL 2: PINTUCO PURO ---
    # Si no es estratégica, verificamos si es realmente Pintuco.
    # Agregamos palabras clave que identifican productos Pintuco.
    lista_pintuco_keywords = ['PINTUCO', 'TERINSA', 'ICO', 'VINILTEX', 'KORAZA', 'DOMESTICO', 'CONSTRUCCION']
    
    # Primero miramos si la marca original dice explícitamente PINTUCO
    if 'PINTUCO' in marca_original:
        return 'PINTUCO'
    
    # Si no, buscamos en el texto completo
    for kw in lista_pintuco_keywords:
        if kw in texto_busqueda:
            return 'PINTUCO'

    # --- NIVEL 3: BOLSA DE "OTROS" ---
    # Si no es estratégica y no dice Pintuco por ningún lado, es OTROS.
    return 'OTROS'

# ==============================================================================
# 📥 MOTOR DE CONEXIÓN DROPBOX (CARTERA & LOGÍSTICA)
# ==============================================================================
@st.cache_data(ttl=900)
def cargar_cartera_logistica():
    """Descarga cartera_detalle.csv para obtener UBICACIÓN y RIESGO."""
    try:
        # Intentar obtener secretos
        try:
            APP_KEY = st.secrets["dropbox"]["app_key"]
            APP_SECRET = st.secrets["dropbox"]["app_secret"]
            REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]
        except:
            st.warning("⚠️ No se detectaron credenciales de Dropbox en secrets.toml.")
            return pd.DataFrame()

        with dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN) as dbx:
            # Ruta exacta
            metadata, res = dbx.files_download(path='/data/cartera_detalle.csv')
            contenido_csv = res.content.decode('latin-1')

            # Nombres de columnas según tu imagen/estructura previa
            cols = [
                'Serie', 'Numero', 'FechaDoc', 'FechaVenc', 'CodCliente',
                'NombreCliente', 'Nit', 'Poblacion', 'Provincia', 'Tel1', 'Tel2',
                'Vendedor', 'Entidad', 'Email', 'Importe', 'Descuento',
                'Cupo', 'DiasVencido'
            ]
            
            df = pd.read_csv(io.StringIO(contenido_csv), header=None, names=cols, sep='|', engine='python')
            
            # LIMPIEZA CRÍTICA PARA EL CRUCE
            # Usamos limpiar_nit para dejar solo números puros (ej: 890900123)
            df['Key_Nit'] = df['Nit'].apply(limpiar_nit)
            
            # Convertir numéricos
            df['Importe'] = pd.to_numeric(df['Importe'], errors='coerce').fillna(0)
            df['DiasVencido'] = pd.to_numeric(df['DiasVencido'], errors='coerce').fillna(0)
            
            # --- AGRUPACIÓN POR CLIENTE ---
            # Un cliente tiene muchas facturas. Necesitamos SU UBICACIÓN ÚNICA.
            # Lógica: Tomamos la población más frecuente (Moda) y el riesgo máximo.
            
            def obtener_moda(x):
                m = pd.Series.mode(x)
                return m.values[0] if not m.empty else "SIN_INFO"

            df_agrupado = df.groupby('Key_Nit').agg({
                'Poblacion': obtener_moda,     # Ubicación logística
                'DiasVencido': 'max',          # Peor día de mora (Riesgo)
                'Importe': 'sum',              # Deuda total actual
                'Cupo': 'max'                  # Cupo asignado
            }).reset_index()
            
            # Normalizar población para filtros
            df_agrupado['Poblacion'] = df_agrupado['Poblacion'].apply(normalizar_texto)
            df_agrupado.rename(columns={'DiasVencido': 'Dias_Mora_Real', 'Importe': 'Deuda_Total'}, inplace=True)
            
            return df_agrupado

    except Exception as e:
        st.error(f"❌ Error conectando con Dropbox: {e}")
        return pd.DataFrame()

# ==============================================================================
# 🚀 LOGICA PRINCIPAL DE DATOS
# ==============================================================================

# Verificar si hay datos de ventas previos
if 'df_ventas' not in st.session_state:
    st.warning("⚠️ Por favor carga el archivo de ventas en la página de inicio primero.")
    st.stop()

# 1. PREPARAR VENTAS
df_raw = st.session_state.df_ventas.copy()

# Filtro solo Facturas y Notas Crédito (Venta Neta)
filtro_docs = 'FACTURA|NOTA.*CREDITO'
df_raw['TipoDocumento'] = df_raw['TipoDocumento'].astype(str)
df = df_raw[df_raw['TipoDocumento'].str.contains(filtro_docs, case=False, regex=True)].copy()

# Conversiones numéricas
cols_num = ['valor_venta', 'unidades_vendidas', 'costo_unitario']
for c in cols_num:
    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

# Calcular Margen
df['Margen_Pesos'] = df['valor_venta'] - (df['unidades_vendidas'] * df['costo_unitario'])

# Crear llave de cruce limpia en Ventas
df['Key_Nit'] = df['cliente_id'].apply(limpiar_nit)

# 2. APLICAR NUEVA CLASIFICACIÓN DE MARCAS (ULTRA)
df['Marca_Analisis'] = df.apply(clasificar_marca_ultra, axis=1)

# 3. TRAER DATOS DE DROPBOX Y CRUZAR
with st.spinner("🔄 Sincronizando con Dropbox (Logística y Riesgo)..."):
    df_cartera = cargar_cartera_logistica()

if not df_cartera.empty:
    # LEFT JOIN: Mantenemos todas las ventas, pegamos info de cartera donde coincida el NIT
    df_full = pd.merge(df, df_cartera, on='Key_Nit', how='left')
    
    # Llenar huecos de clientes que compraron pero no tienen deuda actual (o no están en cartera)
    df_full['Poblacion'] = df_full['Poblacion'].fillna('MOSTRADOR / SIN INFO')
    df_full['Dias_Mora_Real'] = df_full['Dias_Mora_Real'].fillna(0)
else:
    st.warning("⚠️ No se pudo cargar Cartera. Usando datos solo de ventas (Sin población/riesgo).")
    df_full = df.copy()
    df_full['Poblacion'] = 'SIN CONEXION'
    df_full['Dias_Mora_Real'] = 0

# ==============================================================================
# 🎛️ SIDEBAR DE CONTROL
# ==============================================================================
st.sidebar.header("🎛️ Panel de Control Master")
st.sidebar.markdown("---")

# Filtro de Años
lista_anios = sorted(df_full['anio'].unique(), reverse=True)
anio_actual = st.sidebar.selectbox("Año Principal (Análisis)", lista_anios, index=0)
anio_base = st.sidebar.selectbox("Año Base (Comparativo)", [a for a in lista_anios if a != anio_actual] + ["Ninguno"], index=0)

st.sidebar.markdown("---")

# Filtro de Marcas (Usando la nueva clasificación)
opciones_marcas = sorted(df_full['Marca_Analisis'].unique())
sel_marcas = st.sidebar.multiselect("Filtrar Marcas", opciones_marcas, default=opciones_marcas)

# Filtro de Población (Logística)
opciones_zonas = ["TODAS"] + sorted(df_full['Poblacion'].unique())
sel_zona = st.sidebar.selectbox("Filtrar por Población (Logística)", opciones_zonas)

# Filtro Vendedor
opciones_vend = ["TODOS"] + sorted(df_full['nombre_vendedor'].astype(str).unique())
sel_vend = st.sidebar.selectbox("Filtrar por Vendedor", opciones_vend)

# APLICAR FILTROS
df_filtrado = df_full[df_full['Marca_Analisis'].isin(sel_marcas)].copy()

if sel_zona != "TODAS":
    df_filtrado = df_filtrado[df_filtrado['Poblacion'] == sel_zona]
if sel_vend != "TODOS":
    df_filtrado = df_filtrado[df_filtrado['nombre_vendedor'] == sel_vend]

# Separar DataFrames por año
df_now = df_filtrado[df_filtrado['anio'] == anio_actual]
df_hist = df_filtrado[df_filtrado['anio'] == anio_base] if anio_base != "Ninguno" else pd.DataFrame()

# ==============================================================================
# 📊 TABLERO KPI EJECUTIVO
# ==============================================================================
st.title("♟️ Master Brain: Crecimiento & Estrategia Real")
st.markdown(f"**Diagnóstico:** {anio_actual} vs {anio_base if anio_base != 'Ninguno' else 'N/A'} | **Foco:** {sel_zona}")

# Cálculos KPI
venta_now = df_now['valor_venta'].sum()
venta_hist = df_hist['valor_venta'].sum() if not df_hist.empty else 0
diff_venta = venta_now - venta_hist
perc_venta = (diff_venta / venta_hist * 100) if venta_hist else 0

margen_now = df_now['Margen_Pesos'].sum()
margen_hist = df_hist['Margen_Pesos'].sum() if not df_hist.empty else 0
rent_now = (margen_now / venta_now * 100) if venta_now else 0
rent_hist = (margen_hist / venta_hist * 100) if venta_hist else 0

# Riesgo (Promedio ponderado de días mora de los clientes que compraron este año)
riesgo_pond = df_now[df_now['valor_venta'] > 0]['Dias_Mora_Real'].mean()

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Ventas Totales", f"${venta_now:,.0f}", f"{perc_venta:+.1f}% ({diff_venta/1e6:+.1f}M)")
with c2: st.metric("Margen Bruto", f"${margen_now:,.0f}", f"{(margen_now - margen_hist)/1e6:+.1f}M vs Base")
with c3: st.metric("Rentabilidad Real", f"{rent_now:.1f}%", f"{(rent_now - rent_hist):+.1f} pp")
with c4: 
    color_riesgo = "inverse" if riesgo_pond > 45 else "normal"
    st.metric("Riesgo Cartera (Días)", f"{riesgo_pond:.0f} días", "Promedio Clientes Activos", delta_color=color_riesgo)

# ==============================================================================
# 📑 ANÁLISIS PROFUNDO (TABS)
# ==============================================================================
tab_growth, tab_log, tab_mix, tab_risk = st.tabs([
    "🚀 Crecimiento Real (Sin Ruido)", 
    "🗺️ Logística & Costo x Servir", 
    "💎 Mix & Share", 
    "🩸 Salud Financiera"
])

# --- TAB 1: CRECIMIENTO REAL (WATERFALL) ---
with tab_growth:
    st.subheader("¿Quién está poniendo el dinero realmente?")
    st.markdown("Este gráfico aísla **Pintuco Real** de las marcas **Estratégicas** y la bolsa de **Otros**.")
    
    if not df_hist.empty:
        # Agrupar
        g_now = df_now.groupby('Marca_Analisis')['valor_venta'].sum().reset_index().rename(columns={'valor_venta':'Venta_Act'})
        g_hist = df_hist.groupby('Marca_Analisis')['valor_venta'].sum().reset_index().rename(columns={'valor_venta':'Venta_Ant'})
        
        df_w = pd.merge(g_now, g_hist, on='Marca_Analisis', how='outer').fillna(0)
        df_w['Variacion'] = df_w['Venta_Act'] - df_w['Venta_Ant']
        df_w = df_w.sort_values('Variacion', ascending=False)
        
        col_g1, col_g2 = st.columns([2, 1])
        
        with col_g1:
            fig_water = go.Figure(go.Waterfall(
                name="Variación", orientation="v",
                measure=["relative"] * len(df_w),
                x=df_w['Marca_Analisis'],
                textposition="outside",
                text=[f"${v/1e6:+.0f}M" for v in df_w['Variacion']],
                y=df_w['Variacion'],
                connector={"line":{"color":"rgb(63, 63, 63)"}},
                decreasing={"marker":{"color":"#E74C3C"}},
                increasing={"marker":{"color":"#2ECC71"}}
            ))
            fig_water.update_layout(title="Impacto en Dinero por Marca Real ($)", showlegend=False)
            st.plotly_chart(fig_water, use_container_width=True)
            
        with col_g2:
            st.markdown("#### 📝 Detalles")
            st.dataframe(
                df_w[['Marca_Analisis', 'Variacion']],
                column_config={"Variacion": st.column_config.NumberColumn("Crecimiento $", format="$%d")},
                hide_index=True,
                use_container_width=True
            )
            # Insight automático
            mejor = df_w.iloc[0]
            st.info(f"🌟 **{mejor['Marca_Analisis']}** es el motor principal (creció ${mejor['Variacion']/1e6:,.1f}M).")
    else:
        st.info("Selecciona un año base para ver el análisis de crecimiento.")

# --- TAB 2: LOGÍSTICA & COSTO ---
with tab_log:
    st.subheader("📍 Eficiencia Logística por Población")
    st.markdown("""
    **Análisis de Costo por Servir:** - **Eje X:** Ticket Promedio (¿Cuánto compran por pedido?). Tickets bajos en zonas lejanas = Pérdida.
    - **Eje Y:** Rentabilidad %.
    - **Tamaño:** Volumen de Ventas.
    """)
    
    # Agrupar por Población
    # Nota: 'Serie' suele ser el número de factura para contar pedidos únicos
    df_mapa = df_now.groupby('Poblacion').agg(
        Venta=('valor_venta', 'sum'),
        Margen=('Margen_Pesos', 'sum'),
        Pedidos=('Serie', 'nunique')
    ).reset_index()
    
    df_mapa['Ticket_Promedio'] = df_mapa['Venta'] / df_mapa['Pedidos']
    df_mapa['Rentabilidad'] = (df_mapa['Margen'] / df_mapa['Venta']) * 100
    
    # Filtro visual para quitar ruido (poblaciones con ventas < 0.1% del total)
    umbral_min = df_mapa['Venta'].sum() * 0.001
    df_mapa_viz = df_mapa[df_mapa['Venta'] > umbral_min]
    
    fig_sc = px.scatter(
        df_mapa_viz,
        x="Ticket_Promedio",
        y="Rentabilidad",
        size="Venta",
        color="Rentabilidad",
        hover_name="Poblacion",
        text="Poblacion",
        color_continuous_scale="RdYlGn",
        title="Mapa de Eficiencia Logística"
    )
    fig_sc.add_vline(x=df_mapa['Ticket_Promedio'].mean(), line_dash="dash", annotation_text="Ticket Promedio Global")
    st.plotly_chart(fig_sc, use_container_width=True)

# --- TAB 3: MIX & SHARE ---
with tab_mix:
    col_m1, col_m2 = st.columns(2)
    
    # Agrupación
    df_share = df_now.groupby('Marca_Analisis').agg(Venta=('valor_venta', 'sum'), Margen=('Margen_Pesos', 'sum')).reset_index()
    df_share['Rentabilidad'] = (df_share['Margen'] / df_share['Venta']) * 100
    
    with col_m1:
        st.subheader("📦 Participación (Treemap)")
        fig_tree = px.treemap(
            df_share, 
            path=[px.Constant("TOTAL"), 'Marca_Analisis'], 
            values='Venta',
            color='Rentabilidad',
            color_continuous_scale='RdYlGn',
            title="Tamaño = Venta | Color = Rentabilidad"
        )
        st.plotly_chart(fig_tree, use_container_width=True)
        
    with col_m2:
        st.subheader("💎 Matriz Rentabilidad vs Volumen")
        fig_bub = px.scatter(
            df_share,
            x="Venta", y="Rentabilidad",
            size="Venta", color="Rentabilidad",
            text="Marca_Analisis",
            title="Posicionamiento Estratégico"
        )
        st.plotly_chart(fig_bub, use_container_width=True)

# --- TAB 4: RIESGO & CARTERA ---
with tab_risk:
    st.subheader("💳 Ventas vs Riesgo de Cobro")
    st.markdown("Este módulo cruza lo que vendemos HOY con cómo nos están pagando (Dato Máximo de Días de Mora).")
    
    # Agrupar por Cliente
    df_cli = df_now.groupby(['nombre_cliente', 'Poblacion']).agg(
        Compra_Anual=('valor_venta', 'sum'),
        Dias_Mora=('Dias_Mora_Real', 'max') # Dato que viene del Dropbox
    ).reset_index()
    
    # Top Clientes (> 1M ventas) para no saturar el gráfico
    df_cli_top = df_cli[df_cli['Compra_Anual'] > 1000000]
    
    col_r1, col_r2 = st.columns([3, 1])
    
    with col_r1:
        fig_risk = px.scatter(
            df_cli_top,
            x="Dias_Mora",
            y="Compra_Anual",
            color="Poblacion",
            size="Compra_Anual",
            hover_name="nombre_cliente",
            title="Clientes: Volumen de Compra vs Días de Atraso"
        )
        # Línea de peligro (60 días)
        fig_risk.add_vline(x=60, line_dash="dash", line_color="red", annotation_text="Zona Crítica (>60 días)")
        st.plotly_chart(fig_risk, use_container_width=True)
        
    with col_r2:
        st.error("🚨 Top Morosos Activos")
        criticos = df_cli_top[df_cli_top['Dias_Mora'] > 60].sort_values('Dias_Mora', ascending=False).head(10)
        st.dataframe(
            criticos[['nombre_cliente', 'Dias_Mora']],
            column_config={"Dias_Mora": st.column_config.NumberColumn("Días", format="%d")},
            hide_index=True
        )
