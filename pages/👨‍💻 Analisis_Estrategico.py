import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import unicodedata
import io

# ==============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO "MASTER BRAIN"
# ==============================================================================
st.set_page_config(page_title="Master Brain Ultra - Gerencia 360", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    /* Estilo Ejecutivo */
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #0f172a; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2563eb;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricValue"] { color: #1e40af; font-size: 28px; }
    div[data-testid="stMetricDelta"] { font-size: 16px; }
    
    /* Alertas */
    .alerta-negativa { color: #dc2626; font-weight: bold; }
    .alerta-positiva { color: #16a34a; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🧠 Master Brain Ultra: Estrategia & Logística")
st.markdown("### Visión Unificada: Crecimiento Real + Eficiencia Operativa")

# ==============================================================================
# 2. FUNCIONES DE LIMPIEZA E INTELIGENCIA DE NEGOCIO
# ==============================================================================

def limpiar_texto_clave(texto):
    """Normaliza claves para asegurar el cruce (quita ceros izq, espacios, etc)."""
    if pd.isna(texto): return "0"
    texto = str(texto).strip().upper()
    # Eliminar caracteres no numéricos para claves limpias
    texto_num = ''.join(filter(str.isdigit, texto))
    return str(int(texto_num)) if texto_num else "0"

def normalizar_ciudad(texto):
    """Estandariza nombres de ciudades."""
    if not isinstance(texto, str): return "SIN POBLACION"
    txt = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return txt.upper().strip()

def clasificar_marca_inteligente(row):
    """Clasificación basada en tu lógica de negocio (Lista Blanca + Códigos Árbol)."""
    nombre = str(row.get('Producto', '')).upper()
    categoria = str(row.get('Categoria', '')).upper()
    cod_marca = str(row.get('CodMarca', '0')).split('.')[0] # Quitar decimales

    texto_completo = f"{nombre} {categoria}"

    # 1. Lista Blanca (Aliados Estratégicos)
    aliados = ['ABRACOL', 'INDUMA', 'YALE', 'ARTECOLA', 'GOYA', 'ATLAS', 
               'SAINT GOBAIN', 'ALLEGION', 'SEGUREX', 'POLVOS', 'DELTA', 
               'MASTERD', 'GLOBAL', 'SANTENO', 'BELLOTA']
    
    for a in aliados:
        if a in texto_completo: return a

    # 2. Mapeo de la Imagen del Árbol (Columna N)
    mapa_arbol = {
        '58': 'PINTUCO', '50': 'PINTUCO (ASC)', '56': 'PINTUCO PROF', 
        '64': 'PINTUCO CONST', '40': 'ICO', '62': 'ICO', '66': 'ICO PACK',
        '41': 'TERINSA', '63': 'TERINSA', '34': 'PROTECTO', '94': 'PROTECTO PROF',
        '33': 'OCEANIC', '37': 'INTERNATIONAL', '54': 'INTERNATIONAL',
        '59': 'MADETEC', '60': 'INTERPON', '87': 'SIKKENS', '89': 'WANDA'
    }
    
    if cod_marca in mapa_arbol: return mapa_arbol[cod_marca]
    
    # 3. Rescate
    if 'PINTUCO' in texto_completo or 'VINILTEX' in texto_completo: return 'PINTUCO'
    
    return 'OTROS / GENERICOS'

# ==============================================================================
# 3. CARGA Y PROCESAMIENTO DE DATOS (EL MOTOR)
# ==============================================================================

c1, c2 = st.columns(2)
archivo_ventas = c1.file_uploader("1. Cargar CSV Ventas (Separado por |)", type=['csv', 'txt'])
archivo_cartera = c2.file_uploader("2. Cargar CSV Cartera/Logística (Separado por |)", type=['csv', 'txt'])

if archivo_ventas and archivo_cartera:
    try:
        # --- A. PROCESAR VENTAS ---
        # Col A(0): Año, Col C(2): Fecha, Col H(7): CodCliente, Col K(10): Producto
        # Col L(11): Categoria, Col N(13): CodMarca, Col O(14): Valor
        df_v = pd.read_csv(archivo_ventas, sep='|', header=None, 
                           usecols=[0, 2, 7, 10, 11, 13, 14], 
                           names=['Anio', 'Fecha', 'CodCliente_Ventas', 'Producto', 'Categoria', 'CodMarca', 'ValorVenta'])
        
        # Limpieza Ventas
        df_v['Key_Cliente'] = df_v['CodCliente_Ventas'].apply(limpiar_texto_clave)
        df_v['ValorVenta'] = pd.to_numeric(df_v['ValorVenta'], errors='coerce').fillna(0)
        df_v['Marca_Master'] = df_v.apply(clasificar_marca_inteligente, axis=1)
        df_v['Fecha'] = pd.to_datetime(df_v['Fecha'], dayfirst=True, errors='coerce') # Para logística

        # --- B. PROCESAR CARTERA (POBLACIONES) ---
        # Col E(4): CodCliente, Col G(6): Poblacion
        df_c = pd.read_csv(archivo_cartera, sep='|', header=None,
                           usecols=[4, 6],
                           names=['CodCliente_Cartera', 'Poblacion'])
        
        # Limpieza Cartera y Deduplicación (Un cliente puede tener varias facturas, solo necesitamos 1 registro de ciudad)
        df_c['Key_Cliente'] = df_c['CodCliente_Cartera'].apply(limpiar_texto_clave)
        df_c['Poblacion'] = df_c['Poblacion'].apply(normalizar_ciudad)
        
        # Quedarnos con la población única por cliente (tomamos la primera que aparezca)
        maestro_poblaciones = df_c.drop_duplicates(subset=['Key_Cliente'])[['Key_Cliente', 'Poblacion']]

        # --- C. EL GRAN CRUCE (MERGE) ---
        # Left Join: Mantenemos todas las ventas, traemos población si existe
        df_full = pd.merge(df_v, maestro_poblaciones, on='Key_Cliente', how='left')
        
        # Rellenar nulos
        df_full['Poblacion'] = df_full['Poblacion'].fillna("SIN ASIGNAR")

        st.success("✅ Datos cruzados y procesados correctamente.")
        
    except Exception as e:
        st.error(f"Error crítico al procesar archivos: {e}")
        st.stop()

    # ==============================================================================
    # 4. INTERFAZ GERENCIAL Y FILTROS
    # ==============================================================================
    
    st.sidebar.header("🕹️ Centro de Control")
    
    anios_disponibles = sorted(df_full['Anio'].unique(), reverse=True)
    anio_actual = st.sidebar.selectbox("Año Análisis (Actual)", anios_disponibles, index=0)
    
    # Selección automática del año anterior si existe
    idx_prev = 1 if len(anios_disponibles) > 1 else 0
    anio_base = st.sidebar.selectbox("Año Base (Comparativo)", anios_disponibles, index=idx_prev)

    # Filtros globales
    poblaciones = sorted(df_full['Poblacion'].unique())
    sel_pob = st.sidebar.multiselect("Filtrar Poblaciones", poblaciones)
    
    # Aplicar filtros
    df_filtrado = df_full.copy()
    if sel_pob:
        df_filtrado = df_filtrado[df_filtrado['Poblacion'].isin(sel_pob)]

    # Separar DataFrames para cálculos
    df_act = df_filtrado[df_filtrado['Anio'] == anio_actual]
    df_ant = df_filtrado[df_filtrado['Anio'] == anio_base]

    # ==============================================================================
    # 5. KPIs PRINCIPALES (HEADLINES)
    # ==============================================================================
    
    total_act = df_act['ValorVenta'].sum()
    total_ant = df_ant['ValorVenta'].sum()
    var_pesos = total_act - total_ant
    var_porc = ((total_act / total_ant) - 1) * 100 if total_ant > 0 else 0
    
    # Cálculo de Tickets y Clientes
    clientes_act = df_act['Key_Cliente'].nunique()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ventas Totales", f"${total_act:,.0f}", f"{var_porc:+.1f}%")
    col2.metric("Variación Neta ($)", f"${var_pesos:,.0f}", delta_color="normal")
    col3.metric("Total Clientes Activos", f"{clientes_act}")
    col4.metric("Promedio Venta/Cliente", f"${(total_act/clientes_act if clientes_act else 0):,.0f}")

    st.divider()

    # ==============================================================================
    # 6. ANÁLISIS DE PESO DE CRECIMIENTO (WATERFALL)
    # ==============================================================================
    
    st.subheader("📊 ¿Quién está impulsando (o hundiendo) el barco?")
    st.markdown("Este gráfico muestra la **contribución real** de cada marca al crecimiento total. Si la barra es verde, sumó dinero nuevo; si es roja, perdimos venta frente al año pasado.")

    # Agrupación por Marca
    g_act = df_act.groupby('Marca_Master')['ValorVenta'].sum().reset_index(name='Venta_2025')
    g_ant = df_ant.groupby('Marca_Master')['ValorVenta'].sum().reset_index(name='Venta_2024')
    
    # Merge para comparar
    df_growth = pd.merge(g_act, g_ant, on='Marca_Master', how='outer').fillna(0)
    df_growth['Variacion'] = df_growth['Venta_2025'] - df_growth['Venta_2024']
    df_growth['Crecimiento_Pct'] = ((df_growth['Venta_2025'] / df_growth['Venta_2024']) - 1) * 100
    
    # Ordenar por impacto absoluto (las que más movieron la aguja primero)
    df_growth = df_growth.sort_values('Variacion', ascending=False)
    
    # Top 5 Positivas y Top 5 Negativas para el Waterfall (más 'Otros')
    top_pos = df_growth[df_growth['Variacion'] > 0].head(6)
    top_neg = df_growth[df_growth['Variacion'] < 0].tail(6) # Las peores
    
    # Crear gráfico Waterfall
    fig_water = go.Figure(go.Waterfall(
        name = "20", orientation = "v",
        measure = ["relative"] * len(df_growth),
        x = df_growth['Marca_Master'],
        textposition = "outside",
        text = (df_growth['Variacion'] / 1e6).astype(int).astype(str) + "M",
        y = df_growth['Variacion'],
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
        decreasing = {"marker":{"color":"#ef4444"}}, # Rojo
        increasing = {"marker":{"color":"#22c55e"}}, # Verde
        totals = {"marker":{"color":"#3b82f6"}}
    ))

    fig_water.update_layout(
        title=f"Contribución Neta al Crecimiento por Marca ({anio_base} vs {anio_actual})",
        showlegend = False,
        height=500,
        yaxis_title="Variación en Pesos ($)"
    )
    st.plotly_chart(fig_water, use_container_width=True)

    # Tabla detalle rápida
    with st.expander("Ver Detalle Numérico del Crecimiento"):
        st.dataframe(df_growth.style.format({
            'Venta_2025': '${:,.0f}', 
            'Venta_2024': '${:,.0f}', 
            'Variacion': '${:,.0f}',
            'Crecimiento_Pct': '{:+.1f}%'
        }))

    # ==============================================================================
    # 7. INTELIGENCIA LOGÍSTICA Y COSTO DE SERVIR
    # ==============================================================================
    
    st.divider()
    st.subheader("🚚 Eficiencia Logística: Costo de Servir")
    st.markdown("""
    Analizamos la **frecuencia de envíos**. Agrupamos todas las facturas de un mismo día para una misma población como **1 Viaje/Despacho**.
    * **Riesgo:** Ciudades con **Muchos Viajes** pero **Poca Venta** (Ticket bajo = Costo logístico alto).
    """)

    # 1. Definir qué es un "Despacho/Viaje": Una combinación única de Fecha + Población
    # (Asumimos que si vendes a 3 clientes en Armenia el mismo día, sale en el mismo camión/envío)
    df_logistica = df_act.groupby(['Poblacion', 'Fecha']).agg({
        'ValorVenta': 'sum',
        'Key_Cliente': 'nunique' # Cuantos clientes atendidos en ese viaje
    }).reset_index()

    # 2. Agrupar por Población para ver el resumen anual
    resumen_log = df_logistica.groupby('Poblacion').agg({
        'Fecha': 'count',           # Número de días con venta (Viajes)
        'ValorVenta': 'sum'         # Venta total
    }).rename(columns={'Fecha': 'Num_Viajes', 'ValorVenta': 'Venta_Total'}).reset_index()

    # 3. Calcular Ticket Promedio por Viaje
    resumen_log['Ticket_Promedio_Viaje'] = resumen_log['Venta_Total'] / resumen_log['Num_Viajes']

    # 4. Clasificación de Eficiencia
    ciudades_nucleo = ['PEREIRA', 'DOSQUEBRADAS', 'ARMENIA', 'MANIZALES', 'CARTAGO', 'SANTA ROSA DE CABAL']
    
    def clasificar_eficiencia(row):
        es_nucleo = row['Poblacion'] in ciudades_nucleo
        ticket = row['Ticket_Promedio_Viaje']
        viajes = row['Num_Viajes']
        
        # Umbrales (ajustables)
        if es_nucleo:
            return "Núcleo (Costo Bajo)"
        elif ticket < 500000 and viajes > 5:
            return "🚨 INEFICIENTE (Lejos + Poco $$)"
        elif ticket > 2000000:
            return "🌟 Rentable (Lejos pero paga)"
        else:
            return "Regular"

    resumen_log['Eficiencia'] = resumen_log.apply(clasificar_eficiencia, axis=1)
    resumen_log = resumen_log.sort_values('Venta_Total', ascending=False)

    # --- VISUALIZACIÓN LOGÍSTICA ---
    
    col_log1, col_log2 = st.columns([2, 1])
    
    with col_log1:
        # Scatter Plot: Viajes vs Ventas
        fig_eff = px.scatter(
            resumen_log, 
            x="Num_Viajes", 
            y="Ticket_Promedio_Viaje", 
            size="Venta_Total",
            color="Eficiencia",
            hover_name="Poblacion",
            color_discrete_map={
                "Núcleo (Costo Bajo)": "#cbd5e1", # Gris suave
                "🚨 INEFICIENTE (Lejos + Poco $$)": "#ef4444", # Rojo Alerta
                "🌟 Rentable (Lejos pero paga)": "#16a34a", # Verde
                "Regular": "#3b82f6"
            },
            title="Matriz de Rentabilidad Logística (Ticket Promedio por Despacho)",
            log_y=True # Escala logarítmica porque los tickets varían mucho
        )
        # Líneas de referencia
        fig_eff.add_hline(y=500000, line_dash="dot", annotation_text="Umbral Rentabilidad Mínima Envío")
        st.plotly_chart(fig_eff, use_container_width=True)
    
    with col_log2:
        st.write("#### Top Alertas de Ineficiencia")
        st.write("Poblaciones fuera del eje principal con ticket por viaje bajo:")
        # Mostrar solo las rojas
        alertas = resumen_log[resumen_log['Eficiencia'].str.contains("INEFICIENTE")][['Poblacion', 'Num_Viajes', 'Ticket_Promedio_Viaje']]
        st.dataframe(alertas.style.format({'Ticket_Promedio_Viaje': '${:,.0f}'}), hide_index=True)

    # ==============================================================================
    # 8. ANÁLISIS DE PORTAFOLIO (TREEMAP)
    # ==============================================================================
    st.subheader("📦 Composición del Portafolio")
    
    fig_tree = px.treemap(
        df_act, 
        path=[px.Constant("VENTA TOTAL"), 'Marca_Master', 'Categoria', 'Producto'], 
        values='ValorVenta',
        color='Marca_Master',
        title=f"Peso de Ventas por Categoría y Marca ({anio_actual})"
    )
    fig_tree.update_traces(root_color="lightgrey")
    st.plotly_chart(fig_tree, use_container_width=True)

else:
    st.info("👋 Esperando archivos... Por favor carga ambos CSV (Ventas y Cartera) en el menú superior.")
