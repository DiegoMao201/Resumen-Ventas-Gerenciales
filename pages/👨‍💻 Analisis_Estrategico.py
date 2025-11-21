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
