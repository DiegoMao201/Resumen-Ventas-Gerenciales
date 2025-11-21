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
    h1, h2, h3 { color: #003865; font-family: 'Helvetica', sans-serif; font-weight: 800; }
    div[data-testid="stMetricValue"] { color: #0058A7; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. MOTORES DE INTELIGENCIA (CLASIFICACIÓN Y LIMPIEZA)
# ==============================================================================

def normalizar_texto(texto):
    """Estandariza texto: Mayúsculas, sin tildes, sin espacios extra."""
    if not isinstance(texto, str): 
        return str(texto) if pd.notnull(texto) else "SIN INFO"
    texto = str(texto)
    # Quitar tildes
    texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sin_tildes.upper().strip()

def limpiar_nit_maestro(nit):
    """
    Limpia el NIT para asegurar el cruce perfecto.
    Elimina puntos, comas, guiones y espacios.
    """
    if pd.isna(nit): return "0"
    s_nit = str(nit)
    # Solo dejamos números
    s_limpio = re.sub(r'[^0-9]', '', s_nit)
    # Eliminamos ceros a la izquierda si existen (opcional, pero ayuda)
    s_limpio = s_limpio.lstrip('0')
    return s_limpio if s_limpio else "0"

def clasificar_marca_ultra(fila):
    """
    LÓGICA EXACTA SOLICITADA:
    1. Busca en CATEGORIA/ARTICULO la 'Lista Blanca' (Abracol, Induma...).
    2. Si no está, busca en MARCA los códigos de la imagen (33, 40, 58...).
    3. Si no, OTROS.
    """
    # Obtenemos los campos normalizados
    cat_prod = normalizar_texto(fila.get('categoria_producto', ''))
    nom_art = normalizar_texto(fila.get('nombre_articulo', ''))
    marca_orig = normalizar_texto(fila.get('marca_producto', '')) # Aquí debe venir el "58-DPP..."
    
    texto_busqueda_aliados = cat_prod + " " + nom_art

    # --- PASO 1: LISTA BLANCA (ALIADOS ESTRATÉGICOS) ---
    # Si aparece aquí, SE RESPETA SU NOMBRE y no se mira la marca numérica.
    aliados = [
        'ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', 
        'SAINT GOBAIN', 'ALLEGION', 'SEGUREX', 'POLVOS', 'DELTA', 
        'MASTERD', 'GLOBAL', 'SANTENO', 'BELLOTA'
    ]
    
    for aliado in aliados:
        if aliado in texto_busqueda_aliados:
            return aliado

    # --- PASO 2: LÓGICA NUMÉRICA (IMAGEN DEL ÁRBOL) ---
    # Buscamos patrones específicos en la columna 'marca_producto'
    
    # Diccionario basado en tu imagen
    mapa_codigos = {
        '33-': 'OCEANIC PAINTS',
        '34-': 'PROTECTO',
        '37-': 'INTERNATIONAL PAINT',
        '40-': 'ICO',
        '41-': 'TERINSA',
        '50-': 'PINTUCO (ASC)',
        '54-': 'INTERNATIONAL PAINT',
        '56-': 'PINTUCO PROFESIONAL',
        '58-': 'PINTUCO', # Decorativo principal
        '59-': 'MADETEC',
        '60-': 'INTERPON',
        '62-': 'ICO',
        '63-': 'TERINSA',
        '64-': 'PINTUCO', # Construcción/MPY
        '66-': 'ICO PACKAGING',
        '68-': 'RESICOAT',
        '73-': 'CORAL',
        '87-': 'SIKKENS',
        '89-': 'WANDA',
        '90-': 'SIKKENS AUTOCOAT',
        '91-': 'SIKKENS',
        '94-': 'PROTECTO PROFESIONAL'
    }

    # Verificamos si la marca empieza o contiene el código
    for codigo, nombre_salida in mapa_codigos.items():
        if codigo in marca_orig: # Ej: Si "58-" está en "58-DPP-Pintuco"
            return nombre_salida

    # Casos especiales de Pintuco sin número claro
    if 'PINTUCO' in marca_orig or 'VINILTEX' in marca_orig or 'KORAZA' in marca_orig:
        return 'PINTUCO'

    # --- PASO 3: RESTO ---
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
            return pd.DataFrame() 

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
            
            # LIMPIEZA CLAVE PARA CRUCE
            df_drop['Key_Nit'] = df_drop['Nit'].apply(limpiar_nit_maestro)
            df_drop['Poblacion'] = df_drop['Poblacion'].apply(normalizar_texto)
            df_drop['Importe'] = pd.to_numeric(df_drop['Importe'], errors='coerce').fillna(0)
            df_drop['DiasVencido'] = pd.to_numeric(df_drop['DiasVencido'], errors='coerce').fillna(0)

            # Agrupar por NIT para tener registro único
            def moda_poblacion(series):
                if series.empty: return None # Retorna None para manejarlo luego
                m = series.mode()
                return m[0] if not m.empty else series.iloc[0]

            df_maestro = df_drop.groupby('Key_Nit').agg({
                'Poblacion': moda_poblacion,
                'DiasVencido': 'max',        
                'Importe': 'sum'            
            }).reset_index()
            
            df_maestro.rename(columns={
                'DiasVencido': 'Max_Dias_Mora_Cartera', 
                'Importe': 'Deuda_Total_Cartera',
                'Poblacion': 'Poblacion_Dropbox' # Renombramos para distinguir
            }, inplace=True)
            
            return df_maestro

    except Exception as e:
        st.error(f"Error conectando a Dropbox: {e}")
        return pd.DataFrame()

# ==============================================================================
# 4. PROCESAMIENTO Y FUSIÓN DE DATOS (EL CEREBRO)
# ==============================================================================

if 'df_ventas' not in st.session_state:
    st.warning("⚠️ Por favor carga el archivo de ventas en la pantalla de inicio.")
    st.stop()

df_raw = st.session_state.df_ventas.copy()

# --- Filtrado de Documentos (Facturas y Notas Crédito) ---
filtro_docs = 'FACTURA|NOTA.*CREDITO'
if 'TipoDocumento' in df_raw.columns:
    df_raw['TipoDocumento'] = df_raw['TipoDocumento'].astype(str)
    df = df_raw[df_raw['TipoDocumento'].str.contains(filtro_docs, case=False, regex=True)].copy()
else:
    df = df_raw.copy()

# --- Conversión Numérica ---
cols_num = ['valor_venta', 'unidades_vendidas', 'costo_unitario', 'rentabilidad']
for col in cols_num:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    else:
        df[col] = 0.0

# Calcular Margen ($)
if 'Margen_Pesos' not in df.columns:
    df['Margen_Pesos'] = df['valor_venta'] - (df['unidades_vendidas'] * df['costo_unitario'])

# --- APLICAR LA NUEVA CLASIFICACIÓN ---
df['Marca_Master'] = df.apply(clasificar_marca_ultra, axis=1)

# --- INTELIGENCIA DE POBLACIONES (CRUCE ROBUSTO) ---
# 1. Crear llave de cruce limpia en Ventas
if 'cliente_id' in df.columns:
    df['Key_Nit'] = df['cliente_id'].apply(limpiar_nit_maestro)
elif 'nit_cliente' in df.columns:
    df['Key_Nit'] = df['nit_cliente'].apply(limpiar_nit_maestro)
else:
    df['Key_Nit'] = "0"

# 2. Traer datos de Dropbox
with st.spinner("🧠 Sincronizando datos logísticos y de cartera..."):
    df_logistica = cargar_datos_dropbox()

# 3. Fusión (Merge)
if not df_logistica.empty:
    df_full = pd.merge(df, df_logistica, on='Key_Nit', how='left')
else:
    df_full = df.copy()
    df_full['Poblacion_Dropbox'] = None
    df_full['Max_Dias_Mora_Cartera'] = 0
    df_full['Deuda_Total_Cartera'] = 0

# 4. Lógica Definitiva de Población (El Arreglo Final)
def determinar_poblacion_final(row):
    # Prioridad 1: Dropbox (Suele ser más limpio)
    if pd.notnull(row.get('Poblacion_Dropbox')) and str(row.get('Poblacion_Dropbox')).strip() != '':
        return str(row.get('Poblacion_Dropbox')).upper()
    
    # Prioridad 2: Archivo de Ventas (ciudad_cliente)
    ciudad_ventas = row.get('ciudad_cliente')
    if pd.notnull(ciudad_ventas) and str(ciudad_ventas).strip() != '':
        return normalizar_texto(ciudad_ventas)
    
    # Prioridad 3: Fallback
    return "POBLACION NO IDENTIFICADA"

df_full['Poblacion'] = df_full.apply(determinar_poblacion_final, axis=1)
df_full['Max_Dias_Mora_Cartera'] = df_full['Max_Dias_Mora_Cartera'].fillna(0)
df_full['Deuda_Total_Cartera'] = df_full['Deuda_Total_Cartera'].fillna(0)

# ==============================================================================
# 5. INTERFAZ DE ANÁLISIS
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

# Filtro Marcas (Ordenadas)
marcas_ordenadas = sorted(df_full['Marca_Master'].unique())
# Mover 'OTROS' al final visualmente
if 'OTROS' in marcas_ordenadas:
    marcas_ordenadas.remove('OTROS')
    marcas_ordenadas.append('OTROS')

sel_marcas = st.sidebar.multiselect("Filtrar Marcas", marcas_ordenadas, default=marcas_ordenadas)

# Filtro Poblaciones
pobs_disponibles = sorted(df_full['Poblacion'].unique())
sel_zona = st.sidebar.selectbox("Filtrar Población", ["TODAS"] + pobs_disponibles)

# --- APLICACIÓN DE FILTROS ---
df_fil = df_full[df_full['Marca_Master'].isin(sel_marcas)].copy()
if sel_zona != "TODAS":
    df_fil = df_fil[df_fil['Poblacion'] == sel_zona]

df_now = df_fil[df_fil['anio'] == anio_act]
df_prev = df_fil[df_fil['anio'] == anio_base] if anio_base != "Ninguno" else pd.DataFrame()

# ==============================================================================
# 6. DASHBOARD KPI
# ==============================================================================

venta_act = df_now['valor_venta'].sum()
venta_prev = df_prev['valor_venta'].sum() if not df_prev.empty else 0
dif_dinero = venta_act - venta_prev
crecimiento_pct = (dif_dinero / venta_prev * 100) if venta_prev > 0 else 0
margen_act = df_now['Margen_Pesos'].sum()
rentabilidad_pct = (margen_act / venta_act * 100) if venta_act > 0 else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Venta Total", f"${venta_act:,.0f}", f"{crecimiento_pct:+.1f}% vs AA")
k2.metric("Utilidad Bruta", f"${margen_act:,.0f}", f"{rentabilidad_pct:.1f}% Rentabilidad")
k3.metric("Clientes Únicos", f"{df_now['Key_Nit'].nunique()}", "Con compra en periodo")
k4.metric("Pedidos/Facturas", f"{df_now.shape[0]:,.0f}", "Total Líneas")

st.divider()

# ==============================================================================
# 7. PESTAÑAS
# ==============================================================================

tab1, tab2, tab3, tab4 = st.tabs(["🚀 Crecimiento", "📦 Logística (Poblaciones)", "🌍 Share", "🩸 Riesgo Cartera"])

# --- TAB 1: CRECIMIENTO ---
with tab1:
    st.subheader("Contribución al Crecimiento por Marca")
    if not df_prev.empty:
        grp_act = df_now.groupby('Marca_Master')['valor_venta'].sum().reset_index().rename(columns={'valor_venta':'Venta_Actual'})
        grp_prev = df_prev.groupby('Marca_Master')['valor_venta'].sum().reset_index().rename(columns={'valor_venta':'Venta_Anterior'})
        
        df_var = pd.merge(grp_act, grp_prev, on='Marca_Master', how='outer').fillna(0)
        df_var['Variacion'] = df_var['Venta_Actual'] - df_var['Venta_Anterior']
        df_var = df_var.sort_values('Variacion', ascending=False)

        fig_water = go.Figure(go.Waterfall(
            name="Variación", orientation="v",
            measure=["relative"] * len(df_var),
            x=df_var['Marca_Master'],
            y=df_var['Variacion'],
            connector={"line":{"color":"rgb(63, 63, 63)"}},
            decreasing={"marker":{"color":"#D32F2F"}},
            increasing={"marker":{"color":"#2E7D32"}}
        ))
        fig_water.update_layout(title="Cascada de Crecimiento ($)", height=500)
        st.plotly_chart(fig_water, use_container_width=True)
    else:
        st.info("Selecciona un Año Base para ver la comparativa.")

# --- TAB 2: LOGÍSTICA (POBLACIONES) ---
with tab2:
    st.subheader("Análisis de Poblaciones")
    
    if 'Poblacion' in df_now.columns:
        # Agrupar por la columna Población corregida
        df_pob = df_now.groupby('Poblacion').agg(
            Venta=('valor_venta', 'sum'),
            Margen=('Margen_Pesos', 'sum'),
            Clientes=('Key_Nit', 'nunique')
        ).reset_index()
        
        df_pob['Rentabilidad'] = (df_pob['Margen'] / df_pob['Venta']) * 100
        df_pob = df_pob.sort_values('Venta', ascending=False)

        # Top 20 Poblaciones Gráfico
        fig_bar = px.bar(
            df_pob.head(20), 
            x='Poblacion', y='Venta', color='Rentabilidad',
            title="Top 20 Poblaciones por Venta y Rentabilidad",
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
        st.markdown("#### Detalle Completo por Población")
        st.dataframe(df_pob.style.format({'Venta':'${:,.0f}', 'Margen':'${:,.0f}', 'Rentabilidad':'{:.1f}%'}))
    else:
        st.error("No se pudo calcular la columna de Población.")

# --- TAB 3: SHARE ---
with tab3:
    st.subheader("Participación de Portafolio")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        # Treemap
        fig_tree = px.treemap(
            df_now, path=[px.Constant("Total"), 'Marca_Master', 'categoria_producto'], 
            values='valor_venta',
            color='Marca_Master',
            title="Árbol de Ventas (Click para expandir)"
        )
        st.plotly_chart(fig_tree, use_container_width=True)
    with col_s2:
        # Pie
        df_pie = df_now.groupby('Marca_Master')['valor_venta'].sum().reset_index()
        fig_pie = px.pie(df_pie, values='valor_venta', names='Marca_Master', title="Share % por Marca")
        st.plotly_chart(fig_pie, use_container_width=True)

# --- TAB 4: RIESGO ---
with tab4:
    st.subheader("Cartera vs Ventas")
    # Scatter de Riesgo
    df_risk = df_now.groupby(['nombre_cliente', 'Key_Nit', 'Poblacion']).agg(
        Compra=('valor_venta', 'sum'),
        Dias_Mora=('Max_Dias_Mora_Cartera', 'max'),
        Deuda=('Deuda_Total_Cartera', 'max')
    ).reset_index()
    
    df_risk = df_risk[df_risk['Compra'] > 0]
    
    fig_sc = px.scatter(
        df_risk, x='Dias_Mora', y='Compra', size='Deuda', color='Poblacion',
        title="Mapa de Riesgo (Tamaño = Deuda Total)",
        hover_name='nombre_cliente'
    )
    fig_sc.add_vline(x=60, line_dash="dash", line_color="red", annotation_text="Critico >60 días")
    st.plotly_chart(fig_sc, use_container_width=True)

# --- DEBUG FINAL (Para que verifiques que todo sale bien) ---
with st.expander("🕵️‍♂️ Debug Técnico (Verificar Cruces)"):
    st.write(f"Total Registros Ventas: {len(df)}")
    st.write(f"Total Registros Cartera (Dropbox): {len(df_logistica)}")
    
    sin_pob = df_full[df_full['Poblacion'] == "POBLACION NO IDENTIFICADA"].shape[0]
    st.write(f"Registros sin Población identificada: {sin_pob}")
    
    st.write("Muestra de Clasificación de Marcas:")
    st.dataframe(df_full[['marca_producto', 'categoria_producto', 'Marca_Master']].head(10))
