# ==============================================================================
# ANÁLISIS ESTRATÉGICO POTENTE - FERREINOX (V2.0 EXECUTIVE EDITION)
# Guarda este archivo en la carpeta: pages/Analisis_Estrategico.py
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import unicodedata

st.set_page_config(page_title="Centro de Comando Estratégico", page_icon="🧠", layout="wide")

# ==============================================================================
# 🎨 ESTILOS CSS PERSONALIZADOS PARA VISTA EJECUTIVA
# ==============================================================================
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-left: 5px solid #4B4BFF;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .big-font { font-size: 18px !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔧 FUNCIONES AUXILIARES Y DE LIMPIEZA
# ==============================================================================
def normalizar_texto(texto):
    if not isinstance(texto, str): return str(texto) if texto is not None else ""
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').replace('_', ' ').strip()
    except: return str(texto)

def categorizar_marcas_estrategicas(marca_original):
    """
    Agrupa todas las marcas que NO están en la lista VIP como 'PINTUCO'.
    """
    marca = normalizar_texto(marca_original)
    
    # Lista de marcas a MANTENER individualmente
    marcas_vip = [
        'ABRACOL', 'ARTECOLA', 'INDUMA', 'SAINT GOBAIN', 'YALE', 
        'ALLEGION', 'SEGUREX', 'ATLAS', 'POLVOS', 'DELTA', 
        'GOYA', 'MASTERD'
    ]
    
    # Verificamos si la marca normalizada contiene alguna de las VIP
    # Usamos coincidencia parcial para mayor robustez
    for vip in marcas_vip:
        if vip in marca:
            return vip # Retorna el nombre limpio
            
    return "PINTUCO (AGRUPADO)"

# ==============================================================================
# 1. CARGA, LIMPIEZA Y ENRIQUECIMIENTO DE DATOS
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.warning("⚠️ Acceso Restringido: Por favor inicia sesión en el 'Resumen Mensual' para cargar el núcleo de datos.")
    st.stop()

# Copia de seguridad
df_raw = st.session_state.df_ventas.copy()

# --- FILTRADO NETO (Facturas - Notas) ---
filtro_neto = 'FACTURA|NOTA.*CREDITO'
df_raw['TipoDocumento'] = df_raw['TipoDocumento'].astype(str)
df = df_raw[df_raw['TipoDocumento'].str.contains(filtro_neto, na=False, case=False, regex=True)].copy()

# --- CONVERSIÓN NUMÉRICA ROBUSTA ---
cols_num = ['unidades_vendidas', 'costo_unitario', 'valor_venta']
for col in cols_num:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# --- CÁLCULOS FINANCIEROS BASE ---
df['Costo_Total'] = df['unidades_vendidas'] * df['costo_unitario']
df['Margen_Pesos'] = df['valor_venta'] - df['Costo_Total']

# --- APLICACIÓN DE LA LÓGICA DE NEGOCIO (PINTUCO VS OTROS) ---
# Asumimos que la columna de marca es 'marca_producto' o 'grupo'. Ajustar según tu dataset real.
col_marca = 'marca_producto' if 'marca_producto' in df.columns else 'categoria_producto'
df['Marca_Analisis'] = df[col_marca].apply(categorizar_marcas_estrategicas)

# Intentamos inferir ciudad si no existe explícitamente
if 'ciudad_cliente' not in df.columns:
    # Fallback: Intentar extraer de dirección o usar vendedor como proxy (muy básico)
    df['Poblacion_Objetivo'] = "NO DEFINIDO"
else:
    df['Poblacion_Objetivo'] = df['ciudad_cliente'].apply(normalizar_texto)

# ==============================================================================
# 2. BARRA LATERAL DE CONTROL (COCKPIT)
# ==============================================================================
st.title("🧠 Centro de Control de Categorías & Estrategia")
st.markdown("### Análisis de Desempeño, Rentabilidad y Logística")

with st.sidebar:
    st.header("🎛️ Panel de Control")
    
    # Años
    anios_disp = sorted(df['anio'].unique(), reverse=True)
    anio_actual = st.selectbox("📅 Año de Análisis (Actual)", anios_disp, index=0)
    
    anios_comp = [a for a in anios_disp if a != anio_actual]
    anio_previo = st.selectbox("📅 Año Anterior (Comparativo)", anios_comp + ["Ninguno"], index=0 if anios_comp else 0)
    
    st.divider()
    
    # Filtro Global de Categoría / Marca Agrupada
    opciones_marca = ["TODAS"] + sorted(df['Marca_Analisis'].unique())
    marca_sel = st.selectbox("🏷️ Filtrar por Marca (Agrupada)", opciones_marca)

# --- FILTRADO DE DATOS ---
# Dataset Año Actual
df_act = df[df['anio'] == anio_actual].copy()
# Dataset Año Anterior (si aplica)
df_ant = df[df['anio'] == anio_previo].copy() if anio_previo != "Ninguno" else pd.DataFrame()

if marca_sel != "TODAS":
    df_act = df_act[df_act['Marca_Analisis'] == marca_sel]
    if not df_ant.empty:
        df_ant = df_ant[df_ant['Marca_Analisis'] == marca_sel]

# ==============================================================================
# 3. RESUMEN EJECUTIVO (HEADLINES)
# ==============================================================================
st.markdown("---")

# Cálculos KPI Año Actual
venta_act = df_act['valor_venta'].sum()
margen_act = df_act['Margen_Pesos'].sum()
pct_margen_act = (margen_act / venta_act * 100) if venta_act else 0
clientes_act = df_act['cliente_id'].nunique() if 'cliente_id' in df_act.columns else 0

# Cálculos KPI Año Anterior y Variaciones
if not df_ant.empty:
    venta_ant = df_ant['valor_venta'].sum()
    margen_ant = df_ant['Margen_Pesos'].sum()
    pct_margen_ant = (margen_ant / venta_ant * 100) if venta_ant else 0
    
    var_venta = ((venta_act - venta_ant) / venta_ant) * 100 if venta_ant else 0
    var_margen_abs = margen_act - margen_ant
    var_margen_pct = pct_margen_act - pct_margen_ant # Puntos porcentuales
else:
    venta_ant = 0
    var_venta = 0
    var_margen_pct = 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric("Ventas Totales", f"${venta_act:,.0f}", f"{var_venta:+.1f}% vs Año Ant")
with kpi2:
    st.metric("Margen Bruto ($)", f"${margen_act:,.0f}", f"${var_margen_abs:,.0f} vs Año Ant")
with kpi3:
    st.metric("Margen %", f"{pct_margen_act:.2f}%", f"{var_margen_pct:+.2f} pp vs Año Ant")
with kpi4:
    st.metric("Clientes Activos", f"{clientes_act}", help="Clientes únicos con compra en el periodo")

# ==============================================================================
# 4. ANÁLISIS PROFUNDO (TABS)
# ==============================================================================
tab_market, tab_profit, tab_growth, tab_logistic = st.tabs([
    "📊 Participación & Share", 
    "💎 Matriz de Rentabilidad", 
    "🚀 Motores de Crecimiento", 
    "🚚 Logística & Costo x Servir"
])

# --- TAB 1: PARTICIPACIÓN DE MERCADO (SHARE) ---
with tab_market:
    st.subheader("¿Cómo se compone nuestra venta?")
    st.markdown("Análisis de la composición de ventas por la agrupación estratégica definida.")
    
    col_m1, col_m2 = st.columns([2, 1])
    
    with col_m1:
        # Agrupación para Treemap
        df_tree = df_act.groupby(['Marca_Analisis', 'categoria_producto']).agg(
            Ventas=('valor_venta', 'sum'),
            Margen=('Margen_Pesos', 'sum')
        ).reset_index()
        
        # Evitar valores negativos en ventas para el Treemap
        df_tree['Ventas'] = df_tree['Ventas'].clip(lower=0)
        
        fig_tree = px.treemap(
            df_tree,
            path=[px.Constant("FERREINOX"), 'Marca_Analisis', 'categoria_producto'],
            values='Ventas',
            color='Margen',
            color_continuous_scale='RdYlGn',
            title="Mapa de Calor de Ventas (Tamaño) y Rentabilidad (Color)",
            hover_data={'Ventas': ':,.0f', 'Margen': ':,.0f'}
        )
        st.plotly_chart(fig_tree, use_container_width=True)
        
    with col_m2:
        st.markdown("##### Top Players (Share de Valor)")
        df_share = df_act.groupby('Marca_Analisis')['valor_venta'].sum().reset_index()
        df_share['Share'] = (df_share['valor_venta'] / df_share['valor_venta'].sum()) * 100
        df_share = df_share.sort_values('Share', ascending=False)
        
        st.dataframe(
            df_share, 
            column_config={
                "valor_venta": st.column_config.NumberColumn("Venta", format="$%d"),
                "Share": st.column_config.ProgressColumn("Participación", format="%.2f%%", min_value=0, max_value=100)
            },
            hide_index=True,
            use_container_width=True
        )
        
         

# --- TAB 2: MATRIZ DE RENTABILIDAD (CORREGIDA) ---
with tab_profit:
    st.subheader("Matriz Estratégica: Volumen vs. Desempeño")
    
    nivel_agrupacion = st.radio("Analizar rentabilidad por:", ["Marca_Analisis", "categoria_producto", "Poblacion_Objetivo"], horizontal=True)
    
    df_matrix = df_act.groupby(nivel_agrupacion).agg(
        Ventas=('valor_venta', 'sum'),
        Margen_Pesos=('Margen_Pesos', 'sum'),
        Unidades=('unidades_vendidas', 'sum')
    ).reset_index()
    
    df_matrix['Margen_Pct'] = np.where(df_matrix['Ventas'] != 0, (df_matrix['Margen_Pesos'] / df_matrix['Ventas']) * 100, 0)
    
    # --- SOLUCIÓN AL ERROR DE PLOTLY ---
    # Plotly 'size' debe ser positivo. Creamos una columna de tamaño absoluto.
    df_matrix['Size_Ref'] = df_matrix['Margen_Pesos'].abs()
    
    # Filtro de ruido visual (eliminar ventas insignificantes)
    umbral_venta = df_matrix['Ventas'].quantile(0.10) # Eliminar el 10% inferior
    df_matrix_viz = df_matrix[df_matrix['Ventas'] > umbral_venta]
    
    fig_scatter = px.scatter(
        df_matrix_viz,
        x="Ventas",
        y="Margen_Pct",
        size="Size_Ref", # Usamos el valor absoluto
        color="Margen_Pct", # El color sí indica si es bueno o malo
        hover_name=nivel_agrupacion,
        text=nivel_agrupacion,
        color_continuous_scale="RdYlGn",
        title=f"Matriz de Rentabilidad por {nivel_agrupacion}",
        labels={"Size_Ref": "Magnitud del Margen ($)"}
    )
    
    # Líneas cuadrantes
    prom_margen = df_matrix_viz['Margen_Pct'].mean()
    prom_venta = df_matrix_viz['Ventas'].mean()
    
    fig_scatter.add_hline(y=prom_margen, line_dash="dot", annotation_text="Margen Promedio")
    fig_scatter.add_vline(x=prom_venta, line_dash="dot", annotation_text="Venta Promedio")
    fig_scatter.update_traces(textposition='top center')
    
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    st.info("💡 **Interpretación:** Cuadrante superior derecho = 'Estrellas' (Alta venta, Alto margen). Cuadrante inferior derecho = 'Vacas Lecheras' o riesgo de precio (Alta venta, Bajo margen).")

# --- TAB 3: MOTORES DE CRECIMIENTO ---
with tab_growth:
    if anio_previo == "Ninguno":
        st.warning("Selecciona un año comparativo en la barra lateral para ver este análisis.")
    else:
        st.subheader(f"Descomposición del Crecimiento: {anio_previo} vs {anio_actual}")
        
        # Agrupación combinada
        df_g_act = df_act.groupby('Marca_Analisis')['valor_venta'].sum().reset_index().rename(columns={'valor_venta': 'Venta_Actual'})
        df_g_ant = df_ant.groupby('Marca_Analisis')['valor_venta'].sum().reset_index().rename(columns={'valor_venta': 'Venta_Anterior'})
        
        df_growth = pd.merge(df_g_act, df_g_ant, on='Marca_Analisis', how='outer').fillna(0)
        
        # Variaciones
        df_growth['Variacion_Pesos'] = df_growth['Venta_Actual'] - df_growth['Venta_Anterior']
        
        # Contribución al crecimiento total
        total_var = df_growth['Variacion_Pesos'].sum()
        df_growth['Contribucion_Pct'] = (df_growth['Variacion_Pesos'] / venta_ant) * 100 if venta_ant else 0
        
        col_g1, col_g2 = st.columns([2, 1])
        
        with col_g1:
            # Gráfico de Cascada (Waterfall)
            df_waterfall = df_growth.sort_values('Variacion_Pesos', ascending=False)
            
            fig_water = go.Figure(go.Waterfall(
                name="20", orientation="v",
                measure=["relative"] * len(df_waterfall),
                x=df_waterfall['Marca_Analisis'],
                textposition="outside",
                text=[f"${v/1e6:.1f}M" for v in df_waterfall['Variacion_Pesos']],
                y=df_waterfall['Variacion_Pesos'],
                connector={"line": {"color": "rgb(63, 63, 63)"}},
            ))
            
            fig_water.update_layout(title="¿Qué marcas impulsaron (o frenaron) el crecimiento?", showlegend=False)
            st.plotly_chart(fig_water, use_container_width=True)
            
        with col_g2:
            st.markdown("##### Detalle de Variación")
            st.dataframe(
                df_growth[['Marca_Analisis', 'Venta_Actual', 'Variacion_Pesos', 'Contribucion_Pct']].sort_values('Variacion_Pesos', ascending=False),
                column_config={
                    "Venta_Actual": st.column_config.NumberColumn(format="$%d"),
                    "Variacion_Pesos": st.column_config.NumberColumn(format="$%d"),
                    "Contribucion_Pct": st.column_config.NumberColumn("Aporte Crecimiento (pp)", format="%.2f pp")
                },
                hide_index=True
            )
            

[Image of financial growth chart]


# --- TAB 4: LOGÍSTICA Y COSTO POR SERVIR (AVANZADO) ---
with tab_logistic:
    st.subheader("🚚 Inteligencia Logística y Costo por Servir (Poblaciones)")
    st.markdown("""
    Este módulo evalúa la **densidad de venta por población**. 
    *Una venta alta con pocas transacciones es eficiente (Bajo costo por servir).*
    *Muchas transacciones pequeñas en zonas lejanas destruyen valor.*
    """)
    
    # Análisis por Población (Ciudad/Municipio)
    # Usamos 'Poblacion_Objetivo' calculada al inicio
    df_log = df_act.groupby(['Poblacion_Objetivo']).agg(
        Venta_Total=('valor_venta', 'sum'),
        Margen_Total=('Margen_Pesos', 'sum'),
        Num_Pedidos=('Serie', 'nunique'), # Asumiendo 'Serie' es el # de factura
        Clientes_Unicos=('cliente_id', 'nunique')
    ).reset_index()
    
    # Métricas Derivadas
    df_log['Ticket_Promedio'] = df_log['Venta_Total'] / df_log['Num_Pedidos']
    df_log['Margen_Pct'] = (df_log['Margen_Total'] / df_log['Venta_Total']) * 100
    df_log['Costo_Servir_Proxy'] = 1 / df_log['Ticket_Promedio'] # Inverso del ticket como proxy de costo
    
    # Filtro de ciudades top para no saturar el gráfico
    top_ciudades = df_log.sort_values('Venta_Total', ascending=False).head(30)
    
    col_log1, col_log2 = st.columns([2, 1])
    
    with col_log1:
        st.markdown("##### Eficiencia Logística: Ticket Promedio vs Margen %")
        fig_bubble_log = px.scatter(
            top_ciudades,
            x="Ticket_Promedio",
            y="Margen_Pct",
            size="Venta_Total",
            color="Poblacion_Objetivo",
            hover_name="Poblacion_Objetivo",
            text="Poblacion_Objetivo",
            title="Ciudades: ¿Dónde es más costoso vender? (Bajo Ticket = Alto Costo Operativo)",
            height=500
        )
        # Zona de peligro
        fig_bubble_log.add_hrect(y0=0, y1=top_ciudades['Margen_Pct'].min(), fillcolor="red", opacity=0.1, line_width=0)
        fig_bubble_log.add_vline(x=top_ciudades['Ticket_Promedio'].median(), line_dash="dash", annotation_text="Ticket Mediana")
        
        st.plotly_chart(fig_bubble_log, use_container_width=True)
        
    with col_log2:
        st.markdown("##### ⚠️ Alerta: Ciudades Ineficientes")
        st.caption("Ciudades con alto volumen de pedidos pero bajo Ticket Promedio (Requiere optimización de rutas o pedido mínimo).")
        
        # Ciudades con muchas transacciones pero ticket bajo
        ineficientes = top_ciudades.nsmallest(10, 'Ticket_Promedio')[['Poblacion_Objetivo', 'Ticket_Promedio', 'Num_Pedidos', 'Margen_Pct']]
        
        st.dataframe(
            ineficientes,
            column_config={
                "Ticket_Promedio": st.column_config.NumberColumn(format="$%d"),
                "Margen_Pct": st.column_config.NumberColumn(format="%.1f %%")
            },
            hide_index=True
        )
        

    st.markdown("### 🔎 Simulador de Impacto Logístico")
    st.info("Selecciona una población para ver qué marcas/categorías estamos vendiendo allí y su rentabilidad específica.")
    
    ciudad_sel = st.selectbox("Seleccionar Población para Rayos X:", sorted(df_act['Poblacion_Objetivo'].unique()))
    
    df_ciudad = df_act[df_act['Poblacion_Objetivo'] == ciudad_sel]
    
    df_ciudad_cat = df_ciudad.groupby('Marca_Analisis').agg(
        Venta=('valor_venta', 'sum'),
        Margen=('Margen_Pesos', 'sum'),
        Pedidos=('Serie', 'nunique')
    ).reset_index()
    
    df_ciudad_cat['Ticket_Cat'] = df_ciudad_cat['Venta'] / df_ciudad_cat['Pedidos']
    df_ciudad_cat['Mg_Pct'] = (df_ciudad_cat['Margen'] / df_ciudad_cat['Venta']) * 100
    
    st.dataframe(
        df_ciudad_cat.sort_values('Venta', ascending=False),
        use_container_width=True,
        column_config={
            "Venta": st.column_config.NumberColumn(format="$%d"),
            "Mg_Pct": st.column_config.ProgressColumn("Rentabilidad", min_value=0, max_value=40, format="%.1f%%"),
            "Ticket_Cat": st.column_config.NumberColumn("Ticket Promedio (Eficiencia)", format="$%d")
        }
    )
