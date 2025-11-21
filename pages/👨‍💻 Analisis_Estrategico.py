# ==============================================================================
# ANÁLISIS ESTRATÉGICO POTENTE - FERREINOX
# Guarda este archivo en la carpeta: pages/Analisis_Estrategico.py
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import unicodedata

st.set_page_config(page_title="Análisis Estratégico Profundo", page_icon="🚀", layout="wide")

# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================
def normalizar_texto(texto):
    if not isinstance(texto, str): return str(texto) if texto is not None else ""
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').replace('_', ' ').replace('.', ' ').strip().replace('  ', ' ')
    except: return str(texto)

# ==============================================================================
# 1. CARGA Y PREPARACIÓN DE DATOS (Inteligente)
# ==============================================================================
if 'df_ventas' not in st.session_state:
    st.warning("⚠️ Por favor, inicia sesión primero desde la página principal ('Resumen Mensual') para cargar los datos seguros.")
    st.stop()

df_ventas = st.session_state.df_ventas.copy()

# FILTRO INICIAL: Solo Ventas Netas (Facturas y Notas Crédito)
filtro_neto = 'FACTURA|NOTA.*CREDITO'
# Aseguramos que TipoDocumento sea string para evitar errores
df_ventas['TipoDocumento'] = df_ventas['TipoDocumento'].astype(str)
df = df_ventas[df_ventas['TipoDocumento'].str.contains(filtro_neto, na=False, case=False, regex=True)].copy()

# CÁLCULOS MAESTROS DE RENTABILIDAD
# Calculamos el Costo Total de la venta (Unidades * Costo Unitario)
# Aseguramos que sean numéricos
df['unidades_vendidas'] = pd.to_numeric(df['unidades_vendidas'], errors='coerce').fillna(0)
df['costo_unitario'] = pd.to_numeric(df['costo_unitario'], errors='coerce').fillna(0)
df['valor_venta'] = pd.to_numeric(df['valor_venta'], errors='coerce').fillna(0)

df['Costo_Total'] = df['unidades_vendidas'] * df['costo_unitario']
# Calculamos el Margen Bruto en pesos (Venta - Costo)
df['Margen_Pesos'] = df['valor_venta'] - df['Costo_Total']
# Calculamos el Margen Porcentual
df['Margen_Pct'] = np.where(df['valor_venta'] != 0, (df['Margen_Pesos'] / df['valor_venta']) * 100, 0)

# ==============================================================================
# 2. INTERFAZ DE FILTROS AVANZADOS
# ==============================================================================
st.title("🚀 Inteligencia de Negocios: Análisis Estratégico 360°")
st.markdown("Analiza la evolución, rentabilidad y oportunidades ocultas en todas las categorías y marcas (Incluyendo: ARTECOLA, INDUMA, ATLAS).")

with st.sidebar:
    st.header("⚙️ Filtros de Análisis")
    
    # Filtro de Año
    anios_disp = sorted(df['anio'].unique(), reverse=True)
    anio_sel = st.selectbox("Año Principal de Análisis", anios_disp)
    
    # Comparativa
    anio_comparar = st.selectbox("Comparar contra (Crecimiento)", [a for a in anios_disp if a != anio_sel] + ["Ninguno"], index=0)
    
    # --- CORRECCIÓN DE ERROR DE ORDENAMIENTO ---
    # Rellenamos nulos con 'SIN CATEGORIA' y forzamos a string antes de obtener únicos y ordenar
    cats_raw = df['categoria_producto'].fillna('SIN CATEGORIA').astype(str).unique()
    # Filtramos strings vacíos si los hubiera y ordenamos
    cats_clean = sorted([c for c in cats_raw if c.strip() != ''])
    cats_disp = ["TODAS"] + cats_clean
    
    cat_sel = st.selectbox("Filtrar por Categoría", cats_disp)

# Aplicar Filtros al DataFrame Principal (Año Seleccionado)
df_analisis = df[df['anio'] == anio_sel].copy()
if cat_sel != "TODAS":
    df_analisis = df_analisis[df_analisis['categoria_producto'].astype(str) == cat_sel]

# ==============================================================================
# 3. DASHBOARD KPI DE ALTO NIVEL
# ==============================================================================
st.divider()
col1, col2, col3, col4 = st.columns(4)

total_ventas = df_analisis['valor_venta'].sum()
total_margen = df_analisis['Margen_Pesos'].sum()
margen_promedio = (total_margen / total_ventas * 100) if total_ventas != 0 else 0
ticket_promedio = total_ventas / df_analisis['Serie'].nunique() if not df_analisis.empty else 0

with col1:
    st.metric("Ventas Totales (Año)", f"${total_ventas:,.0f}", help="Suma de Facturas - Notas Crédito")
with col2:
    st.metric("Margen Bruto Total", f"${total_margen:,.0f}", help="Venta Neta - (Unidades * Costo Unitario)")
with col3:
    color_margen = "normal" if margen_promedio > 15 else "inverse"
    st.metric("Margen % Promedio", f"{margen_promedio:.2f}%", delta_color=color_margen)
with col4:
    st.metric("Ticket Promedio", f"${ticket_promedio:,.0f}", help="Venta Promedio por Factura")

# ==============================================================================
# 4. PESTAÑAS DE ANÁLISIS PROFUNDO
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Evolución & Tendencias", 
    "💎 Rentabilidad por Marca/Categoría", 
    "📈 Matriz de Crecimiento",
    "🚚 Logística & Costo por Servir"
])

# --- TAB 1: EVOLUCIÓN TEMPORAL ---
with tab1:
    st.subheader("Tendencia Mensual de Ventas y Rentabilidad")
    
    df_monthly = df_analisis.groupby('mes').agg(
        Ventas=('valor_venta', 'sum'),
        Margen=('Margen_Pesos', 'sum')
    ).reset_index()
    
    fig_combo = go.Figure()
    fig_combo.add_trace(go.Bar(x=df_monthly['mes'], y=df_monthly['Ventas'], name='Ventas', marker_color='#1F4E78'))
    fig_combo.add_trace(go.Scatter(x=df_monthly['mes'], y=df_monthly['Margen'], name='Margen ($)', yaxis='y2', line=dict(color='#FF4B4B', width=3)))
    
    fig_combo.update_layout(
        title="Ventas vs Margen Bruto (Mensual)",
        xaxis=dict(title="Mes"),
        yaxis=dict(title="Ventas ($)"),
        yaxis2=dict(title="Margen ($)", overlaying='y', side='right'),
        legend=dict(x=0, y=1.1, orientation='h')
    )
    st.plotly_chart(fig_combo, use_container_width=True)

# --- TAB 2: RENTABILIDAD (MARCAS Y CATEGORÍAS) ---
with tab2:
    col_a, col_b = st.columns([1, 3])
    
    with col_a:
        st.markdown("### Configuración")
        nivel_agrupacion = st.radio("Agrupar por:", ["marca_producto", "categoria_producto", "nombre_articulo"])
        min_venta = st.number_input("Venta Mínima para visualizar ($)", value=1000000, step=500000)

    with col_b:
        # Agrupación Dinámica
        # Asegurar que la columna de agrupación no tenga nulos
        if nivel_agrupacion in df_analisis.columns:
            df_analisis[nivel_agrupacion] = df_analisis[nivel_agrupacion].fillna("SIN DATOS").astype(str)
            
            df_group = df_analisis.groupby(nivel_agrupacion).agg(
                Ventas=('valor_venta', 'sum'),
                Costo=('Costo_Total', 'sum'),
                Unidades=('unidades_vendidas', 'sum'),
                Transacciones=('Serie', 'nunique')
            ).reset_index()
            
            df_group['Margen_Pesos'] = df_group['Ventas'] - df_group['Costo']
            df_group['Margen_Pct'] = np.where(df_group['Ventas']!=0, (df_group['Margen_Pesos'] / df_group['Ventas']) * 100, 0)
            
            total_ventas_grupo = df_group['Ventas'].sum()
            df_group['Peso_Venta_Pct'] = np.where(total_ventas_grupo!=0, (df_group['Ventas'] / total_ventas_grupo) * 100, 0)
            
            # Filtrar ruido
            df_viz = df_group[df_group['Ventas'] >= min_venta].copy()
            
            if not df_viz.empty:
                # SCATTER PLOT DE RENTABILIDAD
                st.subheader("Matriz de Rentabilidad: Volumen vs Margen %")
                st.info("Identifica tus 'Vacas Lecheras' (Alto Volumen, Margen Medio) y 'Estrellas' (Alto Volumen, Alto Margen).")
                
                fig_scatter = px.scatter(
                    df_viz, 
                    x="Ventas", 
                    y="Margen_Pct", 
                    size="Margen_Pesos", 
                    color="Margen_Pct",
                    hover_name=nivel_agrupacion,
                    text=nivel_agrupacion,
                    color_continuous_scale="RdYlGn",
                    title=f"Mapa de Rentabilidad por {nivel_agrupacion.replace('_', ' ').title()}"
                )
                fig_scatter.update_traces(textposition='top center')
                # Línea promedio
                avg_margin = df_viz['Margen_Pct'].mean()
                fig_scatter.add_hline(y=avg_margin, line_dash="dash", annotation_text=f"Promedio: {avg_margin:.1f}%")
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                # TABLA DE DETALLE
                st.markdown("### Detalle de Datos")
                st.dataframe(
                    df_viz.sort_values('Ventas', ascending=False),
                    column_config={
                        "Ventas": st.column_config.NumberColumn(format="$ %d"),
                        "Costo": st.column_config.NumberColumn(format="$ %d"),
                        "Margen_Pesos": st.column_config.NumberColumn(format="$ %d"),
                        "Margen_Pct": st.column_config.ProgressColumn(format="%.2f%%", min_value=0, max_value=100),
                        "Peso_Venta_Pct": st.column_config.NumberColumn(format="%.2f %%")
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.warning("No hay datos que cumplan con el filtro de venta mínima seleccionado.")
        else:
            st.error(f"La columna {nivel_agrupacion} no se encuentra en los datos.")

# --- TAB 3: CRECIMIENTO ---
with tab3:
    if anio_comparar == "Ninguno":
        st.warning("Selecciona un año para comparar en el menú lateral.")
    else:
        st.subheader(f"Comparativa de Crecimiento: {anio_comparar} vs {anio_sel}")
        
        # Preparar datos año anterior
        df_prev = df[df['anio'] == anio_comparar].copy()
        # Asegurar tipos
        if 'categoria_producto' in df_prev.columns:
             df_prev['categoria_producto'] = df_prev['categoria_producto'].fillna('SIN CATEGORIA').astype(str)

        if cat_sel != "TODAS": 
            df_prev = df_prev[df_prev['categoria_producto'] == cat_sel]
        
        # Asegurar tipos en actual
        df_analisis['categoria_producto'] = df_analisis['categoria_producto'].fillna('SIN CATEGORIA').astype(str)

        # Agrupar ambos años
        df_curr_g = df_analisis.groupby('categoria_producto')['valor_venta'].sum().reset_index().rename(columns={'valor_venta': 'Venta_Actual'})
        df_prev_g = df_prev.groupby('categoria_producto')['valor_venta'].sum().reset_index().rename(columns={'valor_venta': 'Venta_Anterior'})
        
        # Merge
        df_growth = pd.merge(df_curr_g, df_prev_g, on='categoria_producto', how='outer').fillna(0)
        
        # Calcular Variación
        df_growth['Variacion_Abs'] = df_growth['Venta_Actual'] - df_growth['Venta_Anterior']
        df_growth['Crecimiento_Pct'] = np.where(df_growth['Venta_Anterior'] > 0, (df_growth['Variacion_Abs'] / df_growth['Venta_Anterior']) * 100, 0)
        
        # Gráfico de cascada (Waterfall) para ver qué categorías aportaron o restaron
        st.markdown("#### ¿Qué impulsó el cambio en las ventas?")
        
        df_growth_sorted = df_growth.sort_values('Variacion_Abs', ascending=False)
        
        if not df_growth_sorted.empty:
            fig_waterfall = go.Figure(go.Waterfall(
                name = "Crecimiento", orientation = "v",
                measure = ["relative"] * len(df_growth_sorted),
                x = df_growth_sorted['categoria_producto'],
                textposition = "outside",
                text = [f"{v/1e6:.1f}M" for v in df_growth_sorted['Variacion_Abs']],
                y = df_growth_sorted['Variacion_Abs'],
                connector = {"line":{"color":"rgb(63, 63, 63)"}},
            ))
            fig_waterfall.update_layout(title = "Contribución al Crecimiento por Categoría (Pesos)", showlegend = True)
            st.plotly_chart(fig_waterfall, use_container_width=True)
        else:
            st.info("No hay datos suficientes para calcular el crecimiento.")

# --- TAB 4: LOGÍSTICA Y COSTO POR SERVIR ---
with tab4:
    st.subheader("🚚 Análisis Logístico y Costo por Servir Estimado")
    st.markdown("""
    **Metodología:** Este módulo analiza la distribución de ventas según el centro de operación (Asumiendo zonas de vendedores).
    El *Costo por Servir* es una estimación de qué tan costoso es atender ciertas zonas geográficas relativo a su margen.
    """)
    
    df_geo = df_analisis.copy()
    
    # Buscamos si podemos mapear el grupo desde DATA_CONFIG en session_state
    grupos_config = st.session_state.DATA_CONFIG.get('grupos_vendedores', {}) if 'DATA_CONFIG' in st.session_state else {}
    
    def map_zona_avanzado(nom_vendedor):
        nom_norm = normalizar_texto(nom_vendedor)
        # Primero buscar en grupos configurados
        for grupo, vendedores in grupos_config.items():
            if nom_norm in [normalizar_texto(v) for v in vendedores]:
                return grupo 
        # Si no está en grupo, intentar inferir por nombre
        if "PEREIRA" in nom_norm: return "Eje Cafetero - Risaralda"
        if "ARMENIA" in nom_norm: return "Eje Cafetero - Quindío"
        if "MANIZALES" in nom_norm: return "Eje Cafetero - Caldas"
        if "OPALO" in nom_norm: return "Digital / Remoto"
        return "Otras Zonas / Viajeros"

    df_geo['nomvendedor'] = df_geo['nomvendedor'].fillna("DESCONOCIDO").astype(str)
    df_geo['Zona_Logistica'] = df_geo['nomvendedor'].apply(map_zona_avanzado)
    
    # Análisis por Zona
    df_zona = df_geo.groupby('Zona_Logistica').agg(
        Ventas=('valor_venta', 'sum'),
        Margen=('Margen_Pesos', 'sum'),
        Transacciones=('Serie', 'nunique'),
        Clientes_Unicos=('cliente_id', 'nunique')
    ).reset_index()
    
    df_zona['Ticket_Promedio_Zona'] = np.where(df_zona['Transacciones']!=0, df_zona['Ventas'] / df_zona['Transacciones'], 0)
    df_zona['Margen_Pct_Zona'] = np.where(df_zona['Ventas']!=0, (df_zona['Margen'] / df_zona['Ventas']) * 100, 0)
    
    if not df_zona.empty:
        col_l1, col_l2 = st.columns(2)
        
        with col_l1:
            st.markdown("##### Rentabilidad por Zona Geográfica (Origen)")
            fig_bar_zona = px.bar(
                df_zona, 
                x='Zona_Logistica', 
                y='Margen_Pct_Zona', 
                color='Ventas',
                title="Margen % por Zona (Color = Volumen de Venta)",
                text_auto='.1f'
            )
            st.plotly_chart(fig_bar_zona, use_container_width=True)
            
        with col_l2:
            st.markdown("##### Eficiencia Logística (Ticket Promedio)")
            st.info("Un ticket promedio bajo en zonas lejanas implica un **Alto Costo por Servir**.")
            fig_bubble = px.scatter(
                df_zona,
                x="Transacciones",
                y="Ticket_Promedio_Zona",
                size="Ventas",
                color="Zona_Logistica",
                hover_name="Zona_Logistica",
                title="Eficiencia: Frecuencia vs Tamaño de Pedido"
            )
            st.plotly_chart(fig_bubble, use_container_width=True)

        st.markdown("### 🧠 Insights Automáticos de Logística")
        if not df_zona.empty:
            zona_menor_ticket = df_zona.loc[df_zona['Ticket_Promedio_Zona'].idxmin()]
            zona_mayor_margen = df_zona.loc[df_zona['Margen_Pct_Zona'].idxmax()]
            
            st.warning(f"⚠️ **Atención:** La zona **{zona_menor_ticket['Zona_Logistica']}** tiene el ticket promedio más bajo (${zona_menor_ticket['Ticket_Promedio_Zona']:,.0f}). Si esta zona está lejos de tus bodegas, el costo de transporte puede estar erosionando la utilidad.")
            st.success(f"✅ **Fortaleza:** La zona **{zona_mayor_margen['Zona_Logistica']}** es la más rentable porcentualmente ({zona_mayor_margen['Margen_Pct_Zona']:.1f}%).")
    else:
        st.info("No hay información suficiente para el análisis logístico.")
