import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ==============================================================================
# 1. CONFIGURACIÓN Y ESTADO INICIAL
# ==============================================================================
st.set_page_config(page_title="Comparativa de Rendimiento", page_icon="📊", layout="wide")

# Esta página es exclusiva para el perfil de Gerente
if st.session_state.get('usuario') != "GERENTE":
    st.header("🔒 Acceso Exclusivo para Gerencia")
    st.warning("Esta sección solo está disponible para el perfil de 'GERENTE'.")
    st.stop()

# Carga segura de datos desde el estado de la sesión
df_ventas_historico = st.session_state.get('df_ventas')
APP_CONFIG = st.session_state.get('APP_CONFIG')
DATA_CONFIG = st.session_state.get('DATA_CONFIG')

if df_ventas_historico is None or df_ventas_historico.empty or not APP_CONFIG or not DATA_CONFIG:
    st.error("No se pudieron cargar los datos maestros. Por favor, vuelva a la página principal.")
    st.stop()

# ==============================================================================
# 2. LÓGICA DE ANÁLISIS COMPARATIVO (El "Cerebro")
# ==============================================================================

@st.cache_data
def calcular_kpis_globales(df_ventas):
    """
    Calcula un set de KPIs para cada vendedor y el promedio general.
    Maneja el caso de vendedores sin ventas de productos reales.
    """
    def preparar_datos_y_margen(df):
        filtro_descuento = (df['nombre_articulo'].str.contains('descuento', case=False, na=False)) & \
                           (df['nombre_articulo'].str.contains('comercial', case=False, na=False))
        df_descuentos = df[filtro_descuento]
        df_productos = df[~filtro_descuento].copy()
        if not df_productos.empty:
            df_productos['margen_bruto'] = df_productos['valor_venta'] - (df_productos['costo_unitario'].fillna(0) * df_productos['unidades_vendidas'].fillna(0))
        return df_productos, df_descuentos

    kpis_list = []
    vendedores = df_ventas['nomvendedor'].unique()

    for vendedor in vendedores:
        df_vendedor = df_ventas[df_ventas['nomvendedor'] == vendedor]
        df_productos, df_descuentos = preparar_datos_y_margen(df_vendedor)
        
        if df_productos.empty or df_productos['valor_venta'].sum() <= 0:
            continue

        venta_bruta = df_productos['valor_venta'].sum()
        margen_bruto = df_productos['margen_bruto'].sum()
        total_descuentos = abs(df_descuentos['valor_venta'].sum())
        margen_operativo = margen_bruto - total_descuentos
        
        kpis_list.append({
            'Vendedor': vendedor,
            'Ventas Brutas': venta_bruta,
            'Margen Operativo (%)': (margen_operativo / venta_bruta * 100) if venta_bruta > 0 else 0,
            'Descuento Concedido (%)': (total_descuentos / venta_bruta * 100) if venta_bruta > 0 else 0,
            'Clientes Únicos': df_vendedor['cliente_id'].nunique(),
            'Ticket Promedio': venta_bruta / df_vendedor['cliente_id'].nunique() if df_vendedor['cliente_id'].nunique() > 0 else 0
        })

    if not kpis_list:
        return pd.DataFrame(), pd.Series()

    df_kpis = pd.DataFrame(kpis_list)
    promedios = df_kpis.select_dtypes(include=np.number).mean()
    return df_kpis, promedios

# ==============================================================================
# 3. LÓGICA DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def render_radar_chart(df_kpis, promedios, vendedor_seleccionado):
    st.subheader(f"Radar de Competencias: {vendedor_seleccionado} vs. Promedio")
    
    kpis_radar = {
        'Ventas Brutas': True, 'Margen Operativo (%)': True, 
        'Clientes Únicos': True, 'Ticket Promedio': True,
        'Descuento Concedido (%)': False # False significa que un valor más bajo es mejor
    }
    
    # Calcular percentiles
    df_percentiles = df_kpis.copy()
    for kpi, higher_is_better in kpis_radar.items():
        if higher_is_better:
            df_percentiles[kpi] = df_kpis[kpi].rank(pct=True)
        else:
            df_percentiles[kpi] = 1 - df_kpis[kpi].rank(pct=True)

    datos_vendedor = df_percentiles[df_percentiles['Vendedor'] == vendedor_seleccionado].iloc[0]
    
    fig = go.Figure()
    # Trazo del promedio (siempre en el percentil 50)
    fig.add_trace(go.Scatterpolar(
        r=[0.5] * len(kpis_radar), theta=list(kpis_radar.keys()),
        fill='toself', name='Promedio del Equipo', line=dict(color='lightgrey')
    ))
    # Trazo del vendedor
    fig.add_trace(go.Scatterpolar(
        r=datos_vendedor[list(kpis_radar.keys())].values, theta=list(kpis_radar.keys()),
        fill='toself', name=vendedor_seleccionado, line=dict(color='#0047AB') # Un azul más profesional
    ))
    
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)
    st.info("Este gráfico muestra el percentil de rendimiento del vendedor para cada métrica. Un valor de 0.8 significa que es mejor que el 80% de sus compañeros en esa área. El 'Promedio del Equipo' siempre se ubica en 0.5 (el percentil 50).")

def render_ranking_chart(df_kpis, kpi_seleccionado):
    st.subheader(f"Ranking de Vendedores por: {kpi_seleccionado}")
    ascending_order = True if kpi_seleccionado == 'Descuento Concedido (%)' else False
    df_sorted = df_kpis.sort_values(by=kpi_seleccionado, ascending=ascending_order)
    fig = px.bar(df_sorted, x=kpi_seleccionado, y='Vendedor', orientation='h', text_auto=True)
    fig.update_traces(texttemplate='%{x:,.1f}', marker_color='#6495ED')
    st.plotly_chart(fig, use_container_width=True)

def render_matriz_equipo(df_kpis, promedios, vendedor_seleccionado):
    st.subheader("Matriz Estratégica del Equipo (Ventas vs. Margen)")
    
    avg_ventas = promedios['Ventas Brutas']
    avg_margen = promedios['Margen Operativo (%)']
    
    fig = px.scatter(
        df_kpis, x='Ventas Brutas', y='Margen Operativo (%)',
        size='Clientes Únicos', color='Vendedor',
        hover_name='Vendedor', hover_data={'Vendedor':False, 'Clientes Únicos':True}
    )
    fig.update_traces(marker=dict(sizemin=5))
    fig.add_vline(x=avg_ventas, line_width=1.5, line_dash="dash", line_color="grey")
    fig.add_hline(y=avg_margen, line_width=1.5, line_dash="dash", line_color="grey")
    
    st.plotly_chart(fig, use_container_width=True)

    # --- INICIO DE LA EXPLICACIÓN DINÁMICA ---
    st.subheader(f"Análisis Estratégico para: {vendedor_seleccionado}")
    with st.container(border=True):
        datos_vendedor = df_kpis[df_kpis['Vendedor'] == vendedor_seleccionado].iloc[0]
        ventas_vendedor = datos_vendedor['Ventas Brutas']
        margen_vendedor = datos_vendedor['Margen Operativo (%)']
        
        if ventas_vendedor >= avg_ventas and margen_vendedor >= avg_margen:
            cuadrante = "⭐ Líderes (Rockstars)"
            analisis = "Este vendedor es un pilar del equipo, generando alto volumen con alta rentabilidad. **Estrategia:** Proteger, invertir en su desarrollo y utilizarlo como mentor para replicar sus buenas prácticas."
        elif ventas_vendedor >= avg_ventas and margen_vendedor < avg_margen:
            cuadrante = "🐄 Constructores de Volumen"
            analisis = "Este vendedor es excelente moviendo producto y generando flujo de caja, pero a costa de la rentabilidad. **Estrategia:** Coaching enfocado en técnicas de negociación, defensa de precios y venta de mix de productos con mayor margen."
        elif ventas_vendedor < avg_ventas and margen_vendedor >= avg_margen:
            cuadrante = "❓ Especialistas de Nicho"
            analisis = "Este vendedor es muy eficiente en rentabilidad, pero con un alcance de ventas limitado. **Estrategia:** Identificar si su éxito se puede escalar. Coaching para aumentar su base de clientes y volumen sin sacrificar su buen margen."
        else:
            cuadrante = "🌱 En Desarrollo"
            analisis = "Este vendedor necesita un plan de desarrollo integral en ambos frentes. **Estrategia:** Establecer metas claras y semanales, acompañamiento en campo y formación intensiva en producto y técnicas de venta."

        st.markdown(f"**Posición:** `{vendedor_seleccionado}` se encuentra en el cuadrante de **{cuadrante}**.")
        st.markdown(f"**Análisis:** {analisis}")
    # --- FIN DE LA EXPLICACIÓN DINÁMICA ---

# ==============================================================================
# 4. EJECUCIÓN PRINCIPAL
# ==============================================================================
st.title("📊 Comparativa de Rendimiento de Vendedores")
st.markdown("Analiza y compara el desempeño del equipo para identificar líderes y oportunidades de coaching. Todos los datos corresponden al histórico completo.")
st.markdown("---")

df_kpis, promedios = calcular_kpis_globales(df_ventas_historico)

if df_kpis.empty:
    st.warning("No hay suficientes datos de vendedores con ventas para generar una comparativa.")
    st.stop()

col1, col2 = st.columns(2)
vendedor_seleccionado = col1.selectbox("Seleccione un Vendedor para analizar:", options=sorted(df_kpis['Vendedor'].unique()))
kpi_ranking = col2.selectbox("Seleccione una Métrica para el Ranking:", options=sorted(promedios.index))

if vendedor_seleccionado:
    render_radar_chart(df_kpis, promedios, vendedor_seleccionado)
    st.markdown("---")
    render_matriz_equipo(df_kpis, promedios, vendedor_seleccionado)
    st.markdown("---")
    render_ranking_chart(df_kpis, kpi_ranking)
