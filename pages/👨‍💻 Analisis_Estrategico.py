import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import unicodedata
import io
import dropbox
from datetime import datetime, date
import calendar
from functools import reduce
import warnings
warnings.filterwarnings('ignore')

# ===== IMPORTACIONES PARA IA Y ANÁLISIS AVANZADO =====
from sklearn.linear_model import LinearRegression
import json
import requests

# ==============================================================================
# 1. CONFIGURACIÓN DE CACHÉ OPTIMIZADA
# ==============================================================================
@st.cache_resource(show_spinner=False)
def get_dropbox_client():
    """Cliente Dropbox singleton"""
    return dropbox.Dropbox(
        app_key=st.secrets.dropbox.app_key,
        app_secret=st.secrets.dropbox.app_secret,
        oauth2_refresh_token=st.secrets.dropbox.refresh_token
    )

@st.cache_data(ttl=7200, show_spinner=False)
def cargar_poblaciones_dropbox_excel_optimizado():
    """Versión optimizada con mejor manejo de errores"""
    try:
        dbx = get_dropbox_client()
        rutas = ['/clientes_detalle.xlsx', '/data/clientes_detalle.xlsx', '/Master/clientes_detalle.xlsx']
        res = None
        for r in rutas:
            try:
                _, res = dbx.files_download(path=r)
                break
            except: 
                continue
        
        if not res: 
            return pd.DataFrame()
        
        with io.BytesIO(res.content) as stream:
            df = pd.read_excel(stream, engine='openpyxl')
        
        cols = {c.strip().lower(): c for c in df.columns}
        
        if 'nit' in cols and 'poblacion' in cols:
            df_clean = df[[cols['nit'], cols['poblacion']]].copy()
            df_clean.columns = ['Key_Nit', 'Poblacion_Real']
            df_clean['Key_Nit'] = df_clean['Key_Nit'].apply(lambda x: str(x).strip() if pd.notna(x) else "0")
            return df_clean
        
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"No se pudo cargar datos geográficos: {e}")
        return pd.DataFrame()

# ==============================================================================
# 2. CONFIGURACIÓN VISUAL EMPRESARIAL FERREINOX
# ==============================================================================
st.set_page_config(
    page_title="Análisis Estratégico de Crecimiento | Ferreinox",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === CSS EMPRESARIAL PROFESIONAL ===
st.markdown("""
<style>
    /* PALETA CORPORATIVA FERREINOX */
    :root {
        --ferreinox-azul-principal: #1e3a8a;
        --ferreinox-azul-secundario: #3b82f6;
        --ferreinox-dorado: #f59e0b;
        --ferreinox-verde: #10b981;
        --ferreinox-rojo: #ef4444;
        --ferreinox-gris-oscuro: #1f2937;
    }
    
    /* ENCABEZADO EMPRESARIAL */
    .encabezado-estrategico {
        background: linear-gradient(135deg, var(--ferreinox-azul-principal) 0%, var(--ferreinox-azul-secundario) 100%);
        padding: 2.5rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(30, 58, 138, 0.3);
        text-align: center;
    }
    
    .encabezado-estrategico h1 {
        color: white;
        font-size: 2.8rem;
        font-weight: 900;
        margin: 0 0 0.5rem 0;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    .encabezado-estrategico p {
        color: rgba(255, 255, 255, 0.95);
        font-size: 1.2rem;
        margin: 0;
        font-weight: 500;
    }
    
    /* TARJETAS DE MÉTRICAS */
    .tarjeta-metrica {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
        border-left: 5px solid var(--ferreinox-azul-secundario);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
        margin-bottom: 1rem;
    }
    
    .tarjeta-metrica:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        border-left-color: var(--ferreinox-dorado);
    }
    
    .etiqueta-metrica {
        font-size: 0.85rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .valor-metrica {
        font-size: 2rem;
        font-weight: 800;
        color: var(--ferreinox-azul-principal);
        margin: 0.25rem 0;
    }
    
    .delta-metrica {
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 0.25rem;
    }
    
    .delta-metrica.positivo { color: var(--ferreinox-verde); }
    .delta-metrica.negativo { color: var(--ferreinox-rojo); }
    
    /* CAJA DE ANÁLISIS IA */
    .caja-ia {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-left: 5px solid var(--ferreinox-dorado);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.15);
        margin: 1rem 0;
    }
    
    .titulo-ia {
        font-weight: 800;
        display: block;
        margin-bottom: 0.75rem;
        text-transform: uppercase;
        font-size: 0.9rem;
        letter-spacing: 1.2px;
        color: var(--ferreinox-dorado);
    }
    
    /* PESTAÑAS MODERNAS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8fafc;
        padding: 0.5rem;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: white;
        border-radius: 8px;
        color: var(--ferreinox-gris-oscuro);
        font-weight: 600;
        font-size: 1rem;
        border: 2px solid transparent;
        transition: all 0.3s;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e0f2fe;
        border-color: var(--ferreinox-azul-secundario);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--ferreinox-azul-principal) 0%, var(--ferreinox-azul-secundario) 100%) !important;
        color: white !important;
        border-color: var(--ferreinox-azul-principal) !important;
    }
    
    /* BARRA LATERAL */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
        border-right: 2px solid #e5e7eb;
    }
    
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: var(--ferreinox-azul-principal);
        font-weight: 700;
    }
    
    /* PIE DE PÁGINA */
    .pie-estrategico {
        text-align: center;
        padding: 2rem;
        margin-top: 3rem;
        border-top: 2px solid #e5e7eb;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    }
</style>
""", unsafe_allow_html=True)

# === ENCABEZADO EMPRESARIAL ===
st.markdown("""
<div class="encabezado-estrategico">
    <h1>📊 Análisis Estratégico de Crecimiento</h1>
    <p>Ferreinox S.A.S. BIC | Inteligencia Empresarial Avanzada | <a href="https://www.ferreinox.co" target="_blank" style="color: white; text-decoration: underline;">www.ferreinox.co</a></p>
</div>
""", unsafe_allow_html=True)

# Logo en sidebar
st.sidebar.image("https://raw.githubusercontent.com/DiegoMao2021/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", use_container_width=True)
st.sidebar.markdown("---")

# ==============================================================================
# 3. FUNCIONES DE UTILIDAD
# ==============================================================================
def normalizar_texto(texto):
    """Normaliza texto eliminando tildes y caracteres especiales"""
    if pd.isna(texto) or str(texto).strip() == "": 
        return "SIN DEFINIR"
    texto = str(texto)
    texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sin_tildes.upper().strip()

def limpiar_codigo_master(codigo):
    """Limpia códigos de cliente"""
    if pd.isna(codigo): 
        return "0"
    s_cod = str(codigo).strip()
    if s_cod == "": 
        return "0"
    try:
        if '.' in s_cod: 
            s_cod = str(int(float(s_cod)))
    except: 
        pass
    return s_cod

def clasificar_marca_unificada(row):
    """Clasificación de marcas según código"""
    codigo_marca = int(row.get('CODIGO_MARCA_N', 0)) if pd.notna(row.get('CODIGO_MARCA_N')) else 0
    
    mapeo_marcas = {
        50: "P8-ASC-MEGA", 54: "MPY-International", 55: "DPP-AN Colorantes Latam",
        56: "DPP-Pintuco Profesional", 57: "ASC-Mega", 58: "DPP-Pintuco",
        59: "DPP-Madetec", 60: "POW-Interpon", 61: "Varios", 62: "DPP-ICO",
        63: "DPP-Terinsa", 64: "MPY-Pintuco", 65: "Terceros No-AN",
        66: "ICO-AN Empaques", 67: "ASC-Automotriz", 68: "POW-Resicoat",
        73: "DPP-Coral", 91: "DPP-Sikkens"
    }
    
    marca = mapeo_marcas.get(codigo_marca, f"Código {codigo_marca}")
    
    if marca.startswith("DPP"):
        categoria = "Pinturas Decorativas"
    elif marca.startswith("POW"):
        categoria = "Recubrimientos en Polvo"
    elif marca.startswith("ASC"):
        categoria = "Automotriz"
    elif marca.startswith("MPY"):
        categoria = "Empaques Marítimos"
    else:
        categoria = "Otros"
    
    return marca, categoria

def tarjeta_metrica(col, etiqueta, valor, delta_valor, delta_etiqueta, color="positivo"):
    """Renderiza una tarjeta de métrica profesional"""
    color_clase = color
    col.markdown(f"""
    <div class="tarjeta-metrica">
        <div class="etiqueta-metrica">{etiqueta}</div>
        <div class="valor-metrica">{valor}</div>
        <div class="delta-metrica {color_clase}">
            <span>{delta_valor}</span> {delta_etiqueta}
        </div>
    </div>
    """, unsafe_allow_html=True)

def generar_excel_profesional(df, nombre_hoja="Datos"):
    """Genera Excel con formato empresarial"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=nombre_hoja)
        workbook = writer.book
        worksheet = writer.sheets[nombre_hoja]
        
        formato_encabezado = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#1e3a8a',
            'font_color': '#FFFFFF',
            'border': 1
        })
        
        formato_moneda = workbook.add_format({'num_format': '$ #,##0'})
        formato_texto = workbook.add_format({'text_wrap': False})
        
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, formato_encabezado)
            
            es_numerico = pd.api.types.is_numeric_dtype(df[value])
            
            if es_numerico:
                worksheet.set_column(col_num, col_num, 15, formato_moneda)
            else:
                max_len = df[value].astype(str).map(len).max()
                col_width = min(max_len + 2, 40) if pd.notna(max_len) else 20
                worksheet.set_column(col_num, col_num, col_width, formato_texto)
                
    return output.getvalue()

# ==============================================================================
# 4. VERIFICACIÓN Y CARGA DE DATOS
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.warning("⚠️ **Por favor, carga el archivo maestro en la página principal.**")
    st.info("👉 Ve a **🏠 Resumen Mensual** para cargar los datos")
    st.stop()

df_raw = st.session_state.df_ventas.copy()

# Mapeo de columnas
try:
    cols_map = {
        0: 'anio', 1: 'mes', 2: 'dia', 7: 'COD', 8: 'CLIENTE', 
        10: 'NOMBRE_PRODUCTO_K', 11: 'CATEGORIA_L', 13: 'CODIGO_MARCA_N', 14: 'VALOR'
    }
    current_cols = df_raw.columns
    rename_dict = {current_cols[idx]: new_name for idx, new_name in cols_map.items() if idx < len(current_cols)}
    df_raw = df_raw.rename(columns=rename_dict)
    
    if 'dia' not in df_raw.columns: 
        df_raw['dia'] = 15
    else: 
        df_raw['dia'] = pd.to_numeric(df_raw['dia'], errors='coerce').fillna(15).astype(int)
except Exception as e:
    st.error(f"❌ Error en estructura de columnas: {e}")
    st.stop()

# Limpieza de datos
df_raw['VALOR'] = pd.to_numeric(df_raw['VALOR'], errors='coerce').fillna(0)
df_raw['anio'] = pd.to_numeric(df_raw['anio'], errors='coerce').fillna(date.today().year).astype(int)
df_raw['mes'] = pd.to_numeric(df_raw['mes'], errors='coerce').fillna(1).astype(int)
df_raw['Key_Nit'] = df_raw['COD'].apply(limpiar_codigo_master)

# Clasificación de marcas
df_raw[['Marca_Master', 'Categoria_Master']] = df_raw.apply(
    lambda x: pd.Series(clasificar_marca_unificada(x)), axis=1
)

# Cruce geográfico
df_cli = cargar_poblaciones_dropbox_excel_optimizado()
if not df_cli.empty:
    df_full = pd.merge(df_raw, df_cli, on='Key_Nit', how='left')
    df_full['Poblacion_Real'] = df_full['Poblacion_Real'].fillna('Sin Geo')
    df_full['Vendedor'] = df_full.get('Vendedor', 'GENERAL').fillna('GENERAL')
else:
    df_full = df_raw.copy()
    df_full['Poblacion_Real'] = 'Sin Geo'
    df_full['Vendedor'] = 'GENERAL'

# Filtro YTD (Year To Date)
hoy = date.today()
def es_ytd(row):
    if row['mes'] < hoy.month: 
        return True
    if row['mes'] == hoy.month: 
        return row['dia'] <= hoy.day
    return False

df_master = df_full[df_full.apply(es_ytd, axis=1)].copy()

# ==============================================================================
# 5. FILTROS EN SIDEBAR
# ==============================================================================
st.title("📊 Centro de Inteligencia de Crecimiento")
st.markdown(f"**Modo:** Análisis Comparativo de Crecimiento | **Corte:** {hoy.strftime('%d-%b-%Y')}")
st.divider()

with st.sidebar:
    st.header("🔍 Configuración de Análisis")
    
    anios = sorted(df_master['anio'].unique(), reverse=True)
    if len(anios) < 2:
        st.error("⚠️ Se necesitan al menos 2 años de datos para análisis comparativo")
        st.stop()
    
    anio_objetivo = st.selectbox("Año Objetivo", anios, 0, key="anio_obj")
    anios_comparacion = [a for a in anios if a != anio_objetivo]
    anio_base = st.selectbox("Año Base (Comparación)", anios_comparacion, 0, key="anio_base")
    
    st.markdown("---")
    st.subheader("Filtros Adicionales")
    
    ciudades_disponibles = sorted(df_master['Poblacion_Real'].unique())
    sel_ciudades = st.multiselect("Ciudades", ciudades_disponibles, key="filtro_ciudad")
    
    marcas_disponibles = sorted(df_master['Marca_Master'].unique())
    sel_marcas = st.multiselect("Marcas", marcas_disponibles, key="filtro_marca")
    
    if sel_marcas:
        cats_disponibles = sorted(df_master[df_master['Marca_Master'].isin(sel_marcas)]['Categoria_Master'].unique())
    else:
        cats_disponibles = sorted(df_master['Categoria_Master'].unique())
    sel_categorias = st.multiselect("Categorías", cats_disponibles, key="filtro_cat")

# Aplicar filtros
df_filtrado = df_master.copy()
if sel_ciudades: 
    df_filtrado = df_filtrado[df_filtrado['Poblacion_Real'].isin(sel_ciudades)]
if sel_marcas: 
    df_filtrado = df_filtrado[df_filtrado['Marca_Master'].isin(sel_marcas)]
if sel_categorias: 
    df_filtrado = df_filtrado[df_filtrado['Categoria_Master'].isin(sel_categorias)]

df_actual = df_filtrado[df_filtrado['anio'] == anio_objetivo].copy()
df_anterior = df_filtrado[df_filtrado['anio'] == anio_base].copy()

# Validación de datos
if df_actual.empty or df_anterior.empty:
    st.warning("⚠️ **No hay datos suficientes para el análisis comparativo con los filtros seleccionados.**")
    st.info("💡 Intenta ajustar los filtros o seleccionar diferentes años")
    st.stop()

# ==============================================================================
# 6. CÁLCULO DE KPIS PRINCIPALES
# ==============================================================================
venta_actual = df_actual['VALOR'].sum()
venta_anterior = df_anterior['VALOR'].sum()
diferencia_ventas = venta_actual - venta_anterior
pct_variacion = (diferencia_ventas / venta_anterior * 100) if venta_anterior > 0 else 100

clientes_actual = df_actual['Key_Nit'].nunique()
clientes_anterior = df_anterior['Key_Nit'].nunique()
diferencia_clientes = clientes_actual - clientes_anterior

transacciones_actual = df_actual['COD'].count()
ticket_actual = venta_actual / transacciones_actual if transacciones_actual > 0 else 0
ticket_anterior = venta_anterior / df_anterior['COD'].count() if not df_anterior.empty else 0
diferencia_ticket_pct = ((ticket_actual - ticket_anterior) / ticket_anterior * 100) if ticket_anterior > 0 else 0

# ==============================================================================
# 7. DASHBOARD PRINCIPAL - KPIS
# ==============================================================================
st.subheader("📈 Indicadores Clave de Desempeño")

col1, col2, col3, col4, col5 = st.columns(5)

color_ventas = "positivo" if diferencia_ventas >= 0 else "negativo"
tarjeta_metrica(
    col1, 
    "Ventas Totales", 
    f"${venta_actual/1e6:,.1f}M",
    f"{pct_variacion:+.1f}%",
    "vs Año Anterior",
    color_ventas
)

tarjeta_metrica(
    col2,
    "Variación Neta",
    f"${abs(diferencia_ventas)/1e6:,.1f}M",
    "Dinero",
    "Crecimiento Real",
    color_ventas
)

color_clientes = "positivo" if diferencia_clientes >= 0 else "negativo"
tarjeta_metrica(
    col3,
    "Clientes Activos",
    f"{clientes_actual}",
    f"{diferencia_clientes:+}",
    "Clientes vs AA",
    color_clientes
)

color_ticket = "positivo" if diferencia_ticket_pct >= 0 else "negativo"
tarjeta_metrica(
    col4,
    "Ticket Promedio",
    f"${ticket_actual:,.0f}",
    f"{diferencia_ticket_pct:+.1f}%",
    "Valor por Línea",
    color_ticket
)

marcas_activas = df_actual['Marca_Master'].nunique()
tarjeta_metrica(
    col5,
    "Mix de Marcas",
    f"{marcas_activas}",
    "Activas",
    "Portafolio Movido",
    "positivo"
)

# ==============================================================================
# 8. PESTAÑAS DE ANÁLISIS PROFUNDO
# ==============================================================================
st.markdown("---")

tabs = st.tabs([
    "📊 ADN de Crecimiento", 
    "📍 Oportunidad Geográfica", 
    "👥 Top 50 Clientes", 
    "📦 Productos Estrella", 
    "⚠️ Gestión de Riesgo",
    "🤖 Análisis con IA"
])

# --- PESTAÑA 1: ADN DE CRECIMIENTO ---
with tabs[0]:
    st.header("📊 ADN del Crecimiento por Marca")
    
    col_adn1, col_adn2 = st.columns([3, 1])
    
    # Preparar datos Waterfall
    marcas_actual = df_actual.groupby('Marca_Master')['VALOR'].sum()
    marcas_anterior = df_anterior.groupby('Marca_Master')['VALOR'].sum()
    df_marcas = pd.DataFrame({'Actual': marcas_actual, 'Anterior': marcas_anterior}).fillna(0)
    df_marcas['Variacion'] = df_marcas['Actual'] - df_marcas['Anterior']
    df_marcas = df_marcas.sort_values('Variacion', ascending=False)
    
    if not df_marcas.empty:
        mejor_marca = df_marcas.index[0]
        peor_marca = df_marcas.index[-1] if df_marcas['Variacion'].iloc[-1] < 0 else "Ninguna"
        
        with col_adn1:
            st.subheader("Gráfico de Contribución: ¿Qué Marcas Explican el Resultado?")
            fig_waterfall = go.Figure(go.Waterfall(
                orientation="v",
                measure=["relative"] * len(df_marcas),
                x=df_marcas.index,
                y=df_marcas['Variacion'],
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                decreasing={"marker": {"color": "#ef4444"}},
                increasing={"marker": {"color": "#10b981"}}
            ))
            fig_waterfall.update_layout(
                height=450,
                title="Variación en Pesos ($) por Marca",
                showlegend=False
            )
            st.plotly_chart(fig_waterfall, use_container_width=True)
        
        with col_adn2:
            st.markdown(f"""
            <div class="caja-ia">
                <span class="titulo-ia">🤖 ANÁLISIS INTELIGENTE</span>
                El crecimiento neto de <b>${diferencia_ventas/1e6:,.1f}M</b> se explica así:
                <br><br>
                🚀 <b>Motor de Crecimiento:</b> La marca <b>{mejor_marca}</b> es la campeona, aportando 
                +${df_marcas['Variacion'].max()/1e6:,.1f}M al resultado.
                <br><br>
                {f"⚓ <b>Freno:</b> La marca <b>{peor_marca}</b> está restando crecimiento (${abs(df_marcas['Variacion'].min())/1e6:,.1f}M)." if peor_marca != "Ninguna" else "✅ No hay marcas con decrecimiento significativo."}
            </div>
            """, unsafe_allow_html=True)
        
        st.dataframe(
            df_marcas[['Actual', 'Variacion']].style.format("${:,.0f}").background_gradient(cmap='RdYlGn', subset=['Variacion']),
            use_container_width=True
        )
    else:
        st.info("📊 No hay datos suficientes para análisis de marcas")

# --- PESTAÑA 2: OPORTUNIDAD GEOGRÁFICA ---
with tabs[1]:
    st.header("📍 Análisis Territorial de Oportunidades")
    
    ciudad_actual = df_actual.groupby('Poblacion_Real')['VALOR'].sum()
    ciudad_anterior = df_anterior.groupby('Poblacion_Real')['VALOR'].sum()
    df_ciudad = pd.DataFrame({'Venta': ciudad_actual, 'Anterior': ciudad_anterior}).fillna(0)
    df_ciudad['Crecimiento_Pesos'] = df_ciudad['Venta'] - df_ciudad['Anterior']
    df_ciudad['Crecimiento_Pct'] = (df_ciudad['Crecimiento_Pesos'] / df_ciudad['Anterior']).replace([np.inf, -np.inf], 0) * 100
    
    # Filtrar ruido (ciudades muy pequeñas)
    df_ciudad = df_ciudad[df_ciudad['Venta'] > 100000]
    
    if not df_ciudad.empty:
        col_geo1, col_geo2 = st.columns([3, 1])
        
        with col_geo1:
            st.subheader("Matriz Estratégica: Volumen vs Aceleración")
            fig_scatter = px.scatter(
                df_ciudad.reset_index(),
                x="Venta",
                y="Crecimiento_Pct",
                size="Venta",
                color="Crecimiento_Pesos",
                hover_name="Poblacion_Real",
                color_continuous_scale="RdYlGn",
                title="Análisis Geo-Estratégico (Tamaño = Volumen de Venta)",
                labels={"Venta": "Venta Actual ($)", "Crecimiento_Pct": "Crecimiento (%)"}
            )
            fig_scatter.add_hline(y=0, line_dash="dash", line_color="grey")
            fig_scatter.update_layout(height=450)
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        with col_geo2:
            mejor_ciudad = df_ciudad.sort_values('Crecimiento_Pesos', ascending=False).index[0]
            peor_ciudad = df_ciudad.sort_values('Crecimiento_Pesos', ascending=True).index[0]
            
            st.markdown(f"""
            <div class="caja-ia">
                <span class="titulo-ia">🌍 ANÁLISIS TERRITORIAL</span>
                <b>¿Dónde enfocar esfuerzos?</b>
                <br><br>
                🥇 <b>Zona Estrella:</b> {mejor_ciudad} lidera la expansión.
                <br><br>
                🚑 <b>Zona Crítica:</b> {peor_ciudad} muestra la mayor contracción. 
                Revisar competencia o asignación de vendedor.
            </div>
            """, unsafe_allow_html=True)
        
        st.dataframe(
            df_ciudad.sort_values('Crecimiento_Pesos', ascending=False).head(15).style.format({
                'Venta': '${:,.0f}',
                'Anterior': '${:,.0f}',
                'Crecimiento_Pesos': '${:,.0f}',
                'Crecimiento_Pct': '{:+.1f}%'
            }).background_gradient(cmap='RdYlGn', subset=['Crecimiento_Pesos']),
            use_container_width=True
        )
    else:
        st.info("📍 No hay datos geográficos suficientes")

# --- PESTAÑA 3: TOP 50 CLIENTES ---
with tabs[2]:
    st.header("🎯 Cazador de Oportunidades: Top 50 Clientes")
    
    cliente_actual = df_actual.groupby(['Key_Nit', 'CLIENTE', 'Vendedor'])['VALOR'].sum()
    cliente_anterior = df_anterior.groupby(['Key_Nit', 'CLIENTE', 'Vendedor'])['VALOR'].sum()
    df_cliente = pd.DataFrame({'Venta_Actual': cliente_actual, 'Venta_Anterior': cliente_anterior}).fillna(0)
    df_cliente['Var_Pesos'] = df_cliente['Venta_Actual'] - df_cliente['Venta_Anterior']
    df_cliente = df_cliente.reset_index()
    
    # CORRECCIÓN DEL ERROR: Validar que hay datos antes de acceder con iloc
    df_riesgo = df_cliente[df_cliente['Var_Pesos'] < 0].sort_values('Var_Pesos', ascending=True).head(50)
    df_estrellas = df_cliente.sort_values('Var_Pesos', ascending=False).head(50)
    
    col_cli1, col_cli2 = st.columns(2)
    
    with col_cli1:
        st.markdown("### 📉 Top 50 Caídas (Recuperación)")
        st.markdown("**Prioridad máxima:** Clientes con mayor pérdida de valor vs año anterior")
        
        if not df_riesgo.empty:
            excel_riesgo = generar_excel_profesional(df_riesgo, "Top_50_Caidas")
            st.download_button(
                label="📥 Descargar Top 50 Caídas (Excel)",
                data=excel_riesgo,
                file_name=f"Top_50_Clientes_Caida_{hoy}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_riesgo"
            )
            
            st.dataframe(
                df_riesgo[['CLIENTE', 'Vendedor', 'Venta_Actual', 'Venta_Anterior', 'Var_Pesos']].style.format({
                    'Venta_Actual': '${:,.0f}',
                    'Venta_Anterior': '${:,.0f}',
                    'Var_Pesos': '${:,.0f}'
                }).background_gradient(cmap='Reds_r', subset=['Var_Pesos']),
                use_container_width=True
            )
        else:
            st.success("✅ ¡Excelente! No hay clientes con caídas significativas")
    
    with col_cli2:
        st.markdown("### 🚀 Top 50 Crecimiento")
        st.markdown("**Clientes desarrollando el portafolio agresivamente**")
        
        if not df_estrellas.empty:
            excel_estrellas = generar_excel_profesional(df_estrellas, "Top_50_Crecimiento")
            st.download_button(
                label="📥 Descargar Top 50 Crecimiento (Excel)",
                data=excel_estrellas,
                file_name=f"Top_50_Clientes_Crecimiento_{hoy}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_estrellas"
            )
            
            st.dataframe(
                df_estrellas[['CLIENTE', 'Vendedor', 'Venta_Actual', 'Venta_Anterior', 'Var_Pesos']].style.format({
                    'Venta_Actual': '${:,.0f}',
                    'Venta_Anterior': '${:,.0f}',
                    'Var_Pesos': '${:,.0f}'
                }).background_gradient(cmap='Greens', subset=['Var_Pesos']),
                use_container_width=True
            )
        else:
            st.warning("⚠️ No hay datos de clientes en crecimiento")

# --- PESTAÑA 4: PRODUCTOS ESTRELLA ---
with tabs[3]:
    st.header("📦 Rendimiento de Portafolio (SKUs)")
    
    prod_actual = df_actual.groupby(['NOMBRE_PRODUCTO_K', 'Marca_Master'])['VALOR'].sum()
    prod_anterior = df_anterior.groupby(['NOMBRE_PRODUCTO_K', 'Marca_Master'])['VALOR'].sum()
    df_prod = pd.DataFrame({'Venta_Actual': prod_actual, 'Venta_Anterior': prod_anterior}).fillna(0)
    df_prod['Var_Pesos'] = df_prod['Venta_Actual'] - df_prod['Venta_Anterior']
    df_prod = df_prod.reset_index()
    
    mejores_skus = df_prod.sort_values('Var_Pesos', ascending=False).head(50)
    peores_skus = df_prod.sort_values('Var_Pesos', ascending=True).head(50)
    
    # CORRECCIÓN DEL ERROR: Validar antes de acceder con iloc
    if not mejores_skus.empty:
        mejor_producto = mejores_skus.iloc[0]['NOMBRE_PRODUCTO_K']
        mejor_producto_valor = mejores_skus.iloc[0]['Var_Pesos']
        
        st.markdown(f"""
        <div class="caja-ia">
            <span class="titulo-ia">📦 INTELIGENCIA DE MIX</span>
            El producto que más dinero nuevo trajo es: <b>{mejor_producto}</b> 
            (+${mejor_producto_valor/1e6:,.1f}M).
            <br>✅ Asegurar inventario de este ítem.
        </div>
        """, unsafe_allow_html=True)
    
    col_prod1, col_prod2 = st.columns(2)
    
    with col_prod1:
        st.markdown("**Top 50: Productos Ganadores**")
        
        if not mejores_skus.empty:
            excel_mejor_sku = generar_excel_profesional(mejores_skus, "Top_Prod_Ganadores")
            st.download_button(
                label="📥 Descargar Productos Ganadores",
                data=excel_mejor_sku,
                file_name=f"Top_Productos_Ganadores_{hoy}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_mejor_sku"
            )
            
            st.dataframe(
                mejores_skus.head(20).style.format({
                    'Venta_Actual': '${:,.0f}',
                    'Var_Pesos': '${:,.0f}'
                }).background_gradient(cmap='Greens'),
                use_container_width=True
            )
        else:
            st.info("📊 No hay productos con crecimiento")
    
    with col_prod2:
        st.markdown("**Top 50: Productos Perdiendo Terreno**")
        
        if not peores_skus.empty and peores_skus.iloc[0]['Var_Pesos'] < 0:
            excel_peor_sku = generar_excel_profesional(peores_skus, "Top_Prod_Perdidas")
            st.download_button(
                label="📥 Descargar Productos en Baja",
                data=excel_peor_sku,
                file_name=f"Top_Productos_Baja_{hoy}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_peor_sku"
            )
            
            st.dataframe(
                peores_skus.head(20).style.format({
                    'Venta_Actual': '${:,.0f}',
                    'Var_Pesos': '${:,.0f}'
                }).background_gradient(cmap='Reds_r'),
                use_container_width=True
            )
        else:
            st.success("✅ No hay productos con pérdidas significativas")

# --- PESTAÑA 5: GESTIÓN DE RIESGO ---
with tabs[4]:
    st.header("⚠️ Gestión de Riesgo / Control de Fugas")
    
    ids_actual = set(df_actual['Key_Nit'])
    ids_anterior = set(df_anterior['Key_Nit'])
    
    ids_perdidos = ids_anterior - ids_actual
    ids_nuevos = ids_actual - ids_anterior
    
    valor_perdido = df_anterior[df_anterior['Key_Nit'].isin(ids_perdidos)]['VALOR'].sum()
    valor_nuevo = df_actual[df_actual['Key_Nit'].isin(ids_nuevos)]['VALOR'].sum()
    
    col_fuga1, col_fuga2, col_fuga3 = st.columns(3)
    
    col_fuga1.metric(
        "Clientes Perdidos (Churn)",
        len(ids_perdidos),
        f"-${valor_perdido/1e6:,.1f}M impacto",
        delta_color="inverse"
    )
    col_fuga2.metric(
        "Clientes Nuevos (Adquisición)",
        len(ids_nuevos),
        f"+${valor_nuevo/1e6:,.1f}M nuevas ventas"
    )
    col_fuga3.metric(
        "Retención Neta",
        f"{len(ids_actual.intersection(ids_anterior))}",
        "Clientes recurrentes"
    )
    
    st.divider()
    
    if ids_perdidos:
        st.markdown("### 🚨 LISTA CRÍTICA: Clientes Fugados (Venta = 0 este año)")
        st.markdown("**Estos clientes compraban el año pasado y este año no han comprado nada**")
        
        df_fugados = df_anterior[df_anterior['Key_Nit'].isin(ids_perdidos)].groupby([
            'CLIENTE', 'Poblacion_Real', 'Vendedor'
        ])['VALOR'].sum().reset_index()
        df_fugados = df_fugados.rename(columns={'VALOR': 'Venta_Perdida_Total'}).sort_values(
            'Venta_Perdida_Total', ascending=False
        )
        
        excel_fugados = generar_excel_profesional(df_fugados, "Clientes_Fugados")
        st.download_button(
            label="📥 Descargar Lista de Fugados (Excel)",
            data=excel_fugados,
            file_name=f"Clientes_Fugados_{hoy}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_fugados"
        )
        
        st.dataframe(
            df_fugados.style.format({'Venta_Perdida_Total': '${:,.0f}'}),
            use_container_width=True
        )
    else:
        st.success("🎉 ¡Increíble! No hay clientes perdidos con los filtros actuales")

# --- PESTAÑA 6: ANÁLISIS CON IA ---
with tabs[5]:
    st.header("🤖 Análisis Estratégico con Inteligencia Artificial")
    
    tendencia = "POSITIVA" if diferencia_ventas > 0 else "NEGATIVA"
    accion_requerida = "potenciar" if diferencia_ventas > 0 else "corregir"
    
    # CORRECCIÓN: Validar antes de acceder con iloc
    mejor_marca_texto = mejor_marca if not df_marcas.empty else "N/A"
    mejor_ciudad_texto = mejor_ciudad if not df_ciudad.empty else "N/A"
    mejor_producto_texto = mejor_producto if not mejores_skus.empty else "N/A"
    
    texto_geo = f"La zona de **{mejor_ciudad_texto}** es tu fortaleza actual."
    texto_riesgo = f"Hay **{len(ids_perdidos)} clientes** que dejaron de comprar, costando ${valor_perdido/1e6:,.1f}M."
    
    st.markdown(f"""
    ### 📋 Resumen Ejecutivo Generado por IA
    
    #### 1. **Diagnóstico General**
    La operación muestra una tendencia **{tendencia}** ({pct_variacion:+.1f}%) comparada con el periodo anterior.
    
    #### 2. **Motores de Crecimiento**
    - El crecimiento viene principalmente de la marca **{mejor_marca_texto}**
    - {texto_geo}
    - El producto estrella es **{mejor_producto_texto}**
    
    #### 3. **Focos de Atención (Plan de Acción)**
    - **Recuperación:** {texto_riesgo} Ver pestaña 'Gestión de Riesgo' para lista y contactar
    - **Clientes en Caída:** Revisar pestaña 'Top 50 Clientes' para priorizar acciones
    
    #### 4. **Conclusión Estratégica**
    La estrategia para lo que resta del periodo debe ser **{accion_requerida}** la venta en 
    **{mejor_marca_texto}** y ejecutar un plan de recuperación inmediato.
    """)
    
    st.info("💡 **Tip:** Usa los filtros de la izquierda para generar este mismo diagnóstico para una Ciudad o Marca específica")

# ==============================================================================
# 9. PIE DE PÁGINA
# ==============================================================================
st.markdown("---")
st.markdown(f"""
<div class="pie-estrategico">
    <p style="font-size: 1.1rem; margin-bottom: 1rem;">
        <strong>Ferreinox S.A.S. BIC</strong> | 
        <a href="https://www.ferreinox.co" target="_blank" style="color: #1e3a8a; text-decoration: none; font-weight: 700;">www.ferreinox.co</a>
    </p>
    <p style="color: #64748b; font-size: 0.9rem; margin: 0.5rem 0;">
        Sistema de Inteligencia Empresarial | Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}
    </p>
    <p style="color: #9ca3af; font-size: 0.85rem; margin-top: 0.5rem;">
        © {datetime.now().year} Ferreinox. Todos los derechos reservados.
    </p>
</div>
""", unsafe_allow_html=True)
