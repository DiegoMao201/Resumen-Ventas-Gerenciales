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
st.set_page_config(page_title="Master Brain Ultra - Estrategia 360", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .metric-card {
        background-color: #ffffff;
        border-left: 5px solid #003865;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .big-font { font-size: 20px !important; font-weight: bold; color: #003865; }
    .sub-font { font-size: 14px !important; color: #666; }
    h1, h2, h3 { color: #003865; font-family: 'Helvetica', sans-serif; font-weight: 800; }
    div[data-testid="stMetricValue"] { color: #0058A7; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MOTORES DE INTELIGENCIA (CLASIFICACIÓN Y LIMPIEZA)
# ==============================================================================

def normalizar_texto(texto):
    """Estandariza nombres de ciudades y clientes."""
    if not isinstance(texto, str): return str(texto) if texto is not None else "SIN INFO"
    texto = str(texto)
    texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sin_tildes.upper().strip()

def limpiar_nit_maestro(nit):
    """Limpia el NIT para asegurar el cruce perfecto entre Ventas y Cartera."""
    if pd.isna(nit): return "0"
    s_nit = str(nit)
    s_limpio = re.sub(r'[^0-9]', '', s_nit) # Solo números
    return s_limpio if s_limpio else "0"

def clasificar_marca_ultra(fila):
    """
    LÓGICA MAESTRA DE CLASIFICACIÓN:
    1. Marcas Estratégicas (Lista Blanca).
    2. Desglose de Familia Pintuco (Terinsa, Ico, International, etc).
    3. Si es Pintuco genérico -> PINTUCO.
    4. Todo lo demás -> OTROS.
    """
    # Concatenamos todo para buscar palabras clave
    texto_completo = (
        normalizar_texto(fila.get('marca_producto', '')) + " " +
        normalizar_texto(fila.get('categoria_producto', '')) + " " +
        normalizar_texto(fila.get('nombre_articulo', ''))
    )
    
    # 1. LISTA BLANCA (ESTRATÉGICAS) - Prioridad Alta
    estrategicas = [
        'ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', 
        'SAINT GOBAIN', 'ALLEGION', 'SEGUREX', 'POLVOS', 'DELTA', 
        'MASTERD', 'GLOBAL', 'SANTENO', 'BELLOTA'
    ]
    for m in estrategicas:
        if m in texto_completo: return m

    # 2. FAMILIA PINTUCO (DESGLOSE SEGÚN TU FOTO DE ÁRBOL)
    familia_pintuco = {
        'TERINSA': 'TERINSA',
        'ICO': 'ICO',
        'INTERNATIONAL': 'INTERNATIONAL PAINT',
        'INTERPON': 'INTERPON',
        'RESICOAT': 'RESICOAT',
        'PROTECTO': 'PROTECTO',
        'OCEANIC': 'OCEANIC PAINTS',
        'CORAL': 'CORAL',
        'SIKKEN': 'SIKKENS', 
        'WANDA': 'WANDA'
    }
    
    for clave, valor in familia_pintuco.items():
        if clave in texto_completo: return valor

    # 3. PINTUCO GENERAL
    claves_pintuco_gen = ['PINTUCO', 'VINILTEX', 'KORAZA', 'DOMESTICO', 'CONSTRUCCION']
    for k in claves_pintuco_gen:
        if k in texto_completo: return 'PINTUCO ARQUITECTONICO'

    # 4. BASURERO (OTROS)
    return 'OTROS'

# ==============================================================================
# 3. CONEXIÓN DROPBOX (CARGA DE POBLACIONES Y CARTERA)
# ==============================================================================
@st.cache_data(ttl=3600)
def cargar_datos_dropbox():
    """Trae la info logística real desde Dropbox."""
    try:
        try:
            APP_KEY = st.secrets["dropbox"]["app_key"]
            APP_SECRET = st.secrets["dropbox"]["app_secret"]
            REFRESH_TOKEN = st.secrets["dropbox"]["refresh_token"]
        except:
            return pd.DataFrame() # Si no hay secrets, retorno vacío

        with dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN) as dbx:
            ruta = '/data/cartera_detalle.csv'
            metadata, res = dbx.files_download(path=ruta)
            contenido = res.content.decode('latin-1')
            
            cols = [
                'Serie', 'Numero', 'FechaDoc', 'FechaVenc', 'CodCliente',
                'NombreCliente', 'Nit', 'Poblacion', 'Provincia', 'Tel1', 'Tel2',
                'Vendedor', 'Entidad', 'Email', 'Importe', 'Descuento',
                'Cupo', 'DiasVencido'
            ]
            df_drop = pd.read_csv(io.StringIO(contenido), header=None, names=cols, sep='|', engine='python')
            
            # Limpieza Clave
            df_drop['Key_Nit'] = df_drop['Nit'].apply(limpiar_nit_maestro)
            df_drop['Poblacion'] = df_drop['Poblacion'].apply(normalizar_texto)
            df_drop['Importe'] = pd.to_numeric(df_drop['Importe'], errors='coerce').fillna(0)
            df_drop['DiasVencido'] = pd.to_numeric(df_drop['DiasVencido'], errors='coerce').fillna(0)

            # Agrupación Inteligente
            def moda_poblacion(series):
                if series.empty: return "SIN POBLACION"
                m = series.mode()
                return m[0] if not m.empty else "SIN POBLACION"

            df_maestro = df_drop.groupby('Key_Nit').agg({
                'Poblacion': moda_poblacion,
                'DiasVencido': 'max',       
                'Importe': 'sum',           
                'NombreCliente': 'first'    
            }).reset_index()
            
            df_maestro.rename(columns={
                'DiasVencido': 'Max_Dias_Mora_Cartera', 
                'Importe': 'Deuda_Total_Cartera',
                'NombreCliente': 'Cliente_Cartera'
            }, inplace=True)
            
            return df_maestro

    except Exception as e:
        st.error(f"Error Dropbox: {e}")
        return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO Y FUSIÓN DE DATOS
# ==============================================================================

# Verificación de carga inicial
if 'df_ventas' not in st.session_state:
    st.warning("⚠️ Por favor carga el archivo de ventas en la pantalla de inicio.")
    st.stop()

df_raw = st.session_state.df_ventas.copy()

# --- 1. Pre-procesamiento de Ventas ---
filtro_docs = 'FACTURA|NOTA.*CREDITO'
# Aseguramos que TipoDocumento sea string
if 'TipoDocumento' in df_raw.columns:
    df_raw['TipoDocumento'] = df_raw['TipoDocumento'].astype(str)
    df = df_raw[df_raw['TipoDocumento'].str.contains(filtro_docs, case=False, regex=True)].copy()
else:
    df = df_raw.copy()

# --- CORRECCIÓN DEL ERROR NUMÉRICO AQUÍ ---
cols_num = ['valor_venta', 'unidades_vendidas', 'costo_unitario', 'rentabilidad']
for col in cols_num:
    if col in df.columns:
        # Si la columna existe, convertimos y rellenamos
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    else:
        # Si no existe, creamos la columna con ceros
        df[col] = 0.0

# Calcular Margen en Pesos ($)
if 'Margen_Pesos' not in df.columns:
    df['Margen_Pesos'] = df['valor_venta'] - (df['unidades_vendidas'] * df['costo_unitario'])

# --- 2. APLICAR CLASIFICACIÓN DE MARCAS ULTRA ---
df['Marca_Master'] = df.apply(clasificar_marca_ultra, axis=1)

# --- 3. FUSIÓN CON DROPBOX (POBLACIONES) ---
df['Key_Nit'] = df['cliente_id'].apply(limpiar_nit_maestro)

with st.spinner("🧠 Master Brain analizando poblaciones y cartera..."):
    df_logistica = cargar_datos_dropbox()

if not df_logistica.empty:
    # Left Join: Prioridad a Ventas, traemos info logística
    df_full = pd.merge(df, df_logistica, on='Key_Nit', how='left')
    
    # Relleno inteligente
    df_full['Poblacion'] = df_full['Poblacion'].fillna('SIN INFO LOGISTICA')
    df_full['Max_Dias_Mora_Cartera'] = df_full['Max_Dias_Mora_Cartera'].fillna(0)
    df_full['Deuda_Total_Cartera'] = df_full['Deuda_Total_Cartera'].fillna(0)
else:
    df_full = df.copy()
    if 'ciudad_cliente' in df_full.columns:
        df_full['Poblacion'] = df_full['ciudad_cliente'].apply(normalizar_texto)
    else:
        df_full['Poblacion'] = 'SIN INFO'
    
    df_full['Max_Dias_Mora_Cartera'] = 0
    df_full['Deuda_Total_Cartera'] = 0

# ==============================================================================
# 5. INTERFAZ DE ANÁLISIS SUPERIOR
# ==============================================================================

st.title("🧠 Master Brain Ultra: Análisis Estratégico")
st.markdown("### Visión de Crecimiento, Rentabilidad y Logística")

# --- FILTROS SIDEBAR ---
st.sidebar.header("🎛️ Panel de Control")

# Años
if 'anio' in df_full.columns:
    anios = sorted(df_full['anio'].unique(), reverse=True)
else:
    anios = [2024]

col_a1, col_a2 = st.sidebar.columns(2)
anio_act = col_a1.selectbox("Año Actual", anios, index=0)
anio_base = col_a2.selectbox("Año Base", [a for a in anios if a != anio_act] + ["Ninguno"], index=0)

st.sidebar.markdown("---")

# Marcas (Usando la nueva clasificación)
marcas_ordenadas = sorted(df_full['Marca_Master'].unique())
if 'OTROS' in marcas_ordenadas:
    marcas_ordenadas.remove('OTROS')
    marcas_ordenadas.append('OTROS')

sel_marcas = st.sidebar.multiselect("Filtrar Marcas", marcas_ordenadas, default=marcas_ordenadas)

# Poblaciones
zonas_ordenadas = ["TODAS"] + sorted(df_full['Poblacion'].astype(str).unique())
sel_zona = st.sidebar.selectbox("Filtrar Población", zonas_ordenadas)

# --- APLICACIÓN DE FILTROS ---
df_fil = df_full[df_full['Marca_Master'].isin(sel_marcas)].copy()
if sel_zona != "TODAS":
    df_fil = df_fil[df_fil['Poblacion'] == sel_zona]

# Dataframes por año
df_now = df_fil[df_fil['anio'] == anio_act]
df_prev = df_fil[df_fil['anio'] == anio_base] if anio_base != "Ninguno" else pd.DataFrame()

# ==============================================================================
# 6. DASHBOARD DE ALTO NIVEL (KPIs)
# ==============================================================================

# Cálculos Globales
venta_act = df_now['valor_venta'].sum()
venta_prev = df_prev['valor_venta'].sum() if not df_prev.empty else 0
dif_dinero = venta_act - venta_prev
crecimiento_pct = (dif_dinero / venta_prev * 100) if venta_prev > 0 else 0

margen_act = df_now['Margen_Pesos'].sum()
rentabilidad_pct = (margen_act / venta_act * 100) if venta_act > 0 else 0

# Conteo de Clientes Activos (con compra)
clientes_activos = df_now['Key_Nit'].nunique()

# Layout KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Venta Total", f"${venta_act:,.0f}", f"{crecimiento_pct:+.1f}% ({dif_dinero:,.0f})")
k2.metric("Utilidad Bruta", f"${margen_act:,.0f}", f"{rentabilidad_pct:.1f}% Rentabilidad")
k3.metric("Clientes Activos", f"{clientes_activos}", "En periodo seleccionado")
k4.metric("Ticket Promedio", f"${(venta_act/len(df_now)):,.0f}" if len(df_now)>0 else "$0", "Por Factura/Item")

st.divider()

# ==============================================================================
# 7. PESTAÑAS DE ANÁLISIS PROFUNDO
# ==============================================================================

tab1, tab2, tab3, tab4 = st.tabs(["🚀 Crecimiento Real", "📦 Logística & Costo Servir", "🌍 Share de Mercado", "🩸 Riesgo & Cartera"])

# --- TAB 1: ANÁLISIS DE CRECIMIENTO (WATERFALL & CONTRIBUCIÓN) ---
with tab1:
    st.subheader(f"¿Qué movió la aguja entre {anio_base} y {anio_act}?")
    
    if not df_prev.empty:
        # Agrupación por Marca Master
        grp_act = df_now.groupby('Marca_Master')['valor_venta'].sum().reset_index().rename(columns={'valor_venta':'Venta_Actual'})
        grp_prev = df_prev.groupby('Marca_Master')['valor_venta'].sum().reset_index().rename(columns={'valor_venta':'Venta_Anterior'})
        
        df_var = pd.merge(grp_act, grp_prev, on='Marca_Master', how='outer').fillna(0)
        df_var['Variacion_Dinero'] = df_var['Venta_Actual'] - df_var['Venta_Anterior']
        df_var['Crecimiento_Pct'] = (df_var['Variacion_Dinero'] / df_var['Venta_Anterior']).replace([np.inf, -np.inf], 0) * 100
        
        # Cálculo de CONTRIBUCIÓN AL CRECIMIENTO TOTAL
        total_venta_anterior = df_prev['valor_venta'].sum()
        df_var['Contribucion_Puntos'] = (df_var['Variacion_Dinero'] / total_venta_anterior) * 100
        
        df_var = df_var.sort_values('Variacion_Dinero', ascending=False)
        
        col_water, col_data = st.columns([2, 1])
        
        with col_water:
            # Gráfico de Cascada (Waterfall)
            fig_water = go.Figure(go.Waterfall(
                name="Variación", orientation="v",
                measure=["relative"] * len(df_var),
                x=df_var['Marca_Master'],
                y=df_var['Variacion_Dinero'],
                text=[f"${v/1e6:.1f}M" for v in df_var['Variacion_Dinero']],
                textposition="outside",
                connector={"line":{"color":"rgb(63, 63, 63)"}},
                decreasing={"marker":{"color":"#D32F2F"}}, # Rojo
                increasing={"marker":{"color":"#2E7D32"}}, # Verde
                totals={"marker":{"color":"#003865"}}
            ))
            fig_water.update_layout(title="Explicación del Crecimiento (Impacto en Dinero)", showlegend=False, height=500)
            st.plotly_chart(fig_water, use_container_width=True)
            
        with col_data:
            st.markdown("#### Detalle de Contribución")
            st.markdown("La columna **'Puntos Growth'** indica cuánto aportó esa marca al crecimiento total de la empresa.")
            
            df_show = df_var[['Marca_Master', 'Venta_Actual', 'Variacion_Dinero', 'Contribucion_Puntos']].copy()
            df_show['Venta_Actual'] = df_show['Venta_Actual'].map('${:,.0f}'.format)
            df_show['Variacion_Dinero'] = df_show['Variacion_Dinero'].map('${:,.0f}'.format)
            df_show['Contribucion_Puntos'] = df_show['Contribucion_Puntos'].map('{:+.2f} pts'.format)
            
            st.dataframe(df_show, hide_index=True, use_container_width=True, height=500)

    else:
        st.info("Selecciona un Año Base en el menú lateral para ver el análisis comparativo de crecimiento.")

# --- TAB 2: LOGÍSTICA Y COSTO POR SERVIR ---
with tab2:
    st.subheader("Mapa de Eficiencia Logística por Población")
    st.markdown("""
    **¿Cómo leer esto?**
    * **Eje X (Eficiencia):** Ticket Promedio. Más a la derecha = Pedidos más grandes (mejor logística).
    * **Eje Y (Rentabilidad):** % de Margen. Más arriba = Más ganancia.
    * **Tamaño:** Volumen de venta de la población.
    * **Color:** Rojo (Bajo margen) a Verde (Alto margen).
    """)
    
    # Agrupamos por Población (Limpiada con Dropbox)
    if 'numero_documento' in df_now.columns:
        col_pedido = 'numero_documento'
    else:
        col_pedido = 'cliente_id' # Fallback si no hay numero documento

    df_log_kpi = df_now.groupby('Poblacion').agg(
        Venta_Total=('valor_venta', 'sum'),
        Margen_Total=('Margen_Pesos', 'sum'),
        Cant_Facturas=(col_pedido, 'nunique') 
    ).reset_index()
    
    # Filtramos poblaciones muy pequeñas
    df_log_kpi = df_log_kpi[df_log_kpi['Venta_Total'] > 0]
    
    df_log_kpi['Ticket_Promedio'] = df_log_kpi['Venta_Total'] / df_log_kpi['Cant_Facturas']
    df_log_kpi['Rentabilidad_Pct'] = (df_log_kpi['Margen_Total'] / df_log_kpi['Venta_Total']) * 100
    
    # Promedios para líneas de referencia
    prom_ticket = df_log_kpi['Ticket_Promedio'].median()
    prom_renta = df_log_kpi['Rentabilidad_Pct'].median()
    
    fig_scat = px.scatter(
        df_log_kpi,
        x="Ticket_Promedio",
        y="Rentabilidad_Pct",
        size="Venta_Total",
        color="Rentabilidad_Pct",
        hover_name="Poblacion",
        text="Poblacion",
        color_continuous_scale="RdYlGn",
        title=f"Costo por Servir: Eficiencia vs Rentabilidad ({anio_act})",
        height=600
    )
    
    # Cuadrantes
    fig_scat.add_vline(x=prom_ticket, line_dash="dash", line_color="gray", annotation_text="Ticket Medio")
    fig_scat.add_hline(y=prom_renta, line_dash="dash", line_color="gray", annotation_text="Rentabilidad Media")
    fig_scat.update_traces(textposition='top center')
    st.plotly_chart(fig_scat, use_container_width=True)
    
    # Tabla de "Destructores de Valor"
    st.markdown("#### ⚠️ Zonas de Atención (Bajo Ticket o Baja Rentabilidad)")
    df_alerta = df_log_kpi[
        (df_log_kpi['Ticket_Promedio'] < prom_ticket) | 
        (df_log_kpi['Rentabilidad_Pct'] < prom_renta)
    ].sort_values('Venta_Total', ascending=False).head(10)
    
    st.dataframe(df_alerta.style.format({
        'Venta_Total': '${:,.0f}', 
        'Ticket_Promedio': '${:,.0f}', 
        'Rentabilidad_Pct': '{:.1f}%'
    }))

# --- TAB 3: SHARE DE MERCADO ---
with tab3:
    st.subheader("Participación de Mercado Real (Share)")
    
    col_share1, col_share2 = st.columns(2)
    
    with col_share1:
        # Verificamos si existe columna categoria
        cat_col = 'categoria_producto' if 'categoria_producto' in df_now.columns else 'Marca_Master'
        
        df_tree = df_now.groupby(['Marca_Master', cat_col])['valor_venta'].sum().reset_index()
        df_tree = df_tree[df_tree['valor_venta'] > 0]
        
        fig_tree = px.treemap(
            df_tree,
            path=[px.Constant("Mercado Total"), 'Marca_Master', cat_col],
            values='valor_venta',
            color='Marca_Master',
            title="Composición del Mercado (Click para profundizar)"
        )
        st.plotly_chart(fig_tree, use_container_width=True)
        
    with col_share2:
        # Tabla resumen de Share
        total_mkt = df_now['valor_venta'].sum()
        df_share_tbl = df_now.groupby('Marca_Master')['valor_venta'].sum().reset_index().sort_values('valor_venta', ascending=False)
        df_share_tbl['Share %'] = (df_share_tbl['valor_venta'] / total_mkt * 100)
        
        fig_pie = px.pie(df_share_tbl, values='valor_venta', names='Marca_Master', hole=0.4, title="Share por Marca")
        st.plotly_chart(fig_pie, use_container_width=True)

# --- TAB 4: RIESGO & CARTERA ---
with tab4:
    st.subheader("Matriz de Riesgo: Venta vs Cartera Vencida")
    st.markdown("Cruzamos lo que te compran hoy vs qué tan mal pagan (Info actualizada de Dropbox).")
    
    # Agrupamos por Cliente
    df_risk = df_now.groupby(['nombre_cliente', 'Key_Nit', 'Poblacion']).agg(
        Compra_Anio=('valor_venta', 'sum'),
        Dias_Mora_Max=('Max_Dias_Mora_Cartera', 'max'),
        Deuda_Total=('Deuda_Total_Cartera', 'max')
    ).reset_index()
    
    # Filtramos clientes relevantes
    df_risk = df_risk[(df_risk['Compra_Anio'] > 1000000) | (df_risk['Deuda_Total'] > 0)]
    
    fig_risk = px.scatter(
        df_risk,
        x="Dias_Mora_Max",
        y="Compra_Anio",
        size="Deuda_Total", 
        color="Poblacion", 
        hover_name="nombre_cliente",
        title="Clientes Críticos: Alta Compra pero Alta Mora",
        labels={"Dias_Mora_Max": "Días Máximos de Mora", "Compra_Anio": f"Ventas {anio_act}"}
    )
    
    fig_risk.add_vline(x=60, line_color="red", line_dash="dash", annotation_text="Zona Crítica (>60 días)")
    st.plotly_chart(fig_risk, use_container_width=True)
    
    st.markdown("#### Top 10 Clientes Riesgosos (Alta Compra + Mora > 60 días)")
    df_top_risk = df_risk[df_risk['Dias_Mora_Max'] > 60].sort_values('Compra_Anio', ascending=False).head(10)
    
    st.dataframe(df_top_risk[['nombre_cliente', 'Poblacion', 'Dias_Mora_Max', 'Deuda_Total', 'Compra_Anio']].style.format({
        'Deuda_Total': '${:,.0f}',
        'Compra_Anio': '${:,.0f}',
        'Dias_Mora_Max': '{:.0f} días'
    }))

# ==============================================================================
# 8. FINALIZACIÓN
# ==============================================================================
st.success("✅ Análisis completado. Datos integrados de Ventas en memoria y Cartera en Dropbox.")
