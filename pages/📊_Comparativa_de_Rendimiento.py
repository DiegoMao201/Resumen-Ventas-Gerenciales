# ==============================================================================
# SCRIPT CORREGIDO PARA: pages/Comparativa de Rendimiento.py
# VERSIÓN: 16 de Julio, 2025
# CORRECCIÓN: Se verifica y alinea la lógica de cálculo de KPIs para que sea
#             100% compatible con los datos pre-procesados por la página principal.
#             Se añaden docstrings y comentarios para máxima claridad.
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import unicodedata

# ==============================================================================
# SECCIÓN 1: CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN DE ACCESO
# ==============================================================================

st.set_page_config(page_title="Comparativa de Rendimiento", page_icon="📊", layout="wide")

def normalizar_texto(texto):
    """
    Normaliza un texto a mayúsculas, sin tildes ni caracteres especiales.
    Función de ayuda para consistencia.
    """
    if not isinstance(texto, str):
        return texto
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').strip().replace('  ', ' ')
    except (TypeError, AttributeError):
        return texto

# --- Validación de Acceso y Datos ---

# Esta página es exclusiva para el perfil de Gerente
if normalizar_texto(st.session_state.get('usuario', '')) != "GERENTE":
    st.header("🔒 Acceso Exclusivo para Gerencia")
    st.warning("Esta sección solo está disponible para el perfil de 'GERENTE'.")
    st.image("https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", width=300)
    st.stop()

# Carga de datos PRE-PROCESADOS desde la sesión principal
df_ventas_historico = st.session_state.get('df_ventas')

# Validar que los datos existen
if df_ventas_historico is None or df_ventas_historico.empty:
    st.error("Error crítico: No se pudieron cargar los datos. Por favor, regrese a la página '🏠 Resumen Mensual' y vuelva a intentarlo.")
    st.stop()


# ==============================================================================
# SECCIÓN 2: LÓGICA DE ANÁLISIS (El "Cerebro")
# ==============================================================================

@st.cache_data
def calcular_kpis_globales(_df_ventas):
    """
    Calcula un conjunto de KPIs para cada vendedor sobre el histórico completo.

    Args:
        _df_ventas (pd.DataFrame): El DataFrame de ventas pre-procesado.

    Returns:
        tuple: Un DataFrame con los KPIs por vendedor y una Serie con los promedios.
    """
    # Usar una copia para evitar advertencias de cache
    df_ventas = _df_ventas.copy()
    df_ventas = df_ventas.dropna(subset=['nomvendedor', 'nombre_articulo'])

    # Identificar descuentos de forma global para usar en el cálculo del margen
    # Se asume que los nombres de artículo ya están normalizados por el script principal
    filtro_descuento = (df_ventas['nombre_articulo'].str.contains('DESCUENTO', case=False, na=False)) & \
                       (df_ventas['nombre_articulo'].str.contains('COMERCIAL', case=False, na=False))

    df_descuentos_global = df_ventas[filtro_descuento]
    df_productos_global = df_ventas[~filtro_descuento]

    kpis_list = []
    # Usar la columna 'nomvendedor' que ya viene normalizada del script principal
    vendedores = df_productos_global['nomvendedor'].unique()

    for vendedor in vendedores:
        df_vendedor_prods = df_productos_global[df_productos_global['nomvendedor'] == vendedor]
        df_vendedor_dctos = df_descuentos_global[df_descuentos_global['nomvendedor'] == vendedor]

        if df_vendedor_prods.empty:
            continue

        # Se calcula la Venta Bruta solo sobre productos, excluyendo descuentos.
        venta_bruta = df_vendedor_prods['valor_venta'].sum()

        # Se calcula el margen bruto a partir de los productos.
        # Confía en que costo_unitario y unidades_vendidas son numéricos.
        margen_bruto = (df_vendedor_prods['valor_venta'] - (df_vendedor_prods['costo_unitario'].fillna(0) * df_vendedor_prods['unidades_vendidas'].fillna(0))).sum()
        total_descuentos = abs(df_vendedor_dctos['valor_venta'].sum())

        # El margen operativo es el margen bruto de productos menos los descuentos.
        margen_operativo = margen_bruto - total_descuentos
        clientes_unicos = df_vendedor_prods['cliente_id'].nunique()

        kpis_list.append({
            'Vendedor': vendedor,
            'Ventas Brutas': venta_bruta,
            'Margen Operativo (%)': (margen_operativo / venta_bruta * 100) if venta_bruta > 0 else 0,
            'Descuento Concedido (%)': (total_descuentos / venta_bruta * 100) if venta_bruta > 0 else 0,
            'Clientes Únicos': clientes_unicos,
            'Ticket Promedio': venta_bruta / clientes_unicos if clientes_unicos > 0 else 0
        })

    if not kpis_list:
        return pd.DataFrame(), pd.Series(dtype='float64')

    df_kpis = pd.DataFrame(kpis_list)
    promedios = df_kpis.select_dtypes(include=np.number).mean()
    return df_kpis, promedios


# ==============================================================================
# SECCIÓN 3: COMPONENTES DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def render_radar_chart(df_kpis, vendedor_seleccionado):
    """Renderiza un gráfico de radar comparando a un vendedor con el promedio."""
    st.subheader(f"Radar de Competencias: {vendedor_seleccionado} vs. Promedio del Equipo")
    
    # KPIs a incluir en el radar y si un valor más alto es mejor (True) o peor (False)
    kpis_radar = {
        'Ventas Brutas': True,
        'Margen Operativo (%)': True,
        'Clientes Únicos': True,
        'Ticket Promedio': True,
        'Descuento Concedido (%)': False  # Para descuentos, un valor más bajo es mejor
    }
    
    # Normalizar los datos a percentiles para que sean comparables en la misma escala
    df_percentiles = df_kpis.copy()
    for kpi, higher_is_better in kpis_radar.items():
        if kpi not in df_percentiles.columns:
            continue
        # rank(pct=True) convierte cada valor a su percentil (0.0 a 1.0)
        rank_series = df_percentiles[kpi].rank(pct=True)
        # Si un valor más bajo es mejor (como en descuentos), invertimos el percentil
        df_percentiles[kpi] = rank_series if higher_is_better else (1 - rank_series)

    datos_vendedor = df_percentiles[df_percentiles['Vendedor'] == vendedor_seleccionado].iloc[0]
    # El "promedio" en un ranking de percentiles es siempre el punto medio (0.5)
    valores_promedio = [0.5] * len(kpis_radar)
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=valores_promedio, theta=list(kpis_radar.keys()), fill='toself', name='Promedio Equipo'))
    fig.add_trace(go.Scatterpolar(r=datos_vendedor[list(kpis_radar.keys())].values, theta=list(kpis_radar.keys()), fill='toself', name=vendedor_seleccionado))
    
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])))
    st.plotly_chart(fig, use_container_width=True)

def render_ranking_chart(df_kpis, kpi_seleccionado):
    """Renderiza un gráfico de barras como ranking para un KPI específico."""
    st.subheader(f"Ranking de Vendedores por: {kpi_seleccionado}")
    
    # Ordenar de forma descendente, excepto para descuentos que es ascendente
    ascending_order = True if kpi_seleccionado == 'Descuento Concedido (%)' else False
    df_sorted = df_kpis.sort_values(by=kpi_seleccionado, ascending=ascending_order)
    
    fig = px.bar(df_sorted, x=kpi_seleccionado, y='Vendedor', orientation='h', text_auto=True, title=f"Ranking por {kpi_seleccionado}")
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

def render_matriz_equipo(df_kpis, promedios, vendedor_seleccionado):
    """Renderiza la matriz estratégica y el análisis automático."""
    st.subheader("Matriz Estratégica del Equipo (Ventas vs. Margen)")
    
    avg_ventas = promedios['Ventas Brutas']
    avg_margen = promedios['Margen Operativo (%)']

    fig = px.scatter(df_kpis, x='Ventas Brutas', y='Margen Operativo (%)',
                     size='Clientes Únicos', color='Vendedor', hover_name='Vendedor',
                     hover_data={'Vendedor': False, 'Clientes Únicos': True, 'Ticket Promedio': ':.2f'})
    
    fig.update_traces(marker=dict(sizemin=5))
    fig.add_vline(x=avg_ventas, line_width=1.5, line_dash="dash", line_color="grey", annotation_text="Promedio Ventas")
    fig.add_hline(y=avg_margen, line_width=1.5, line_dash="dash", line_color="grey", annotation_text="Promedio Margen")
    
    st.plotly_chart(fig, use_container_width=True)

    # --- ANÁLISIS AUTOMÁTICO Y CONCLUSIONES ---
    st.subheader(f"Análisis Estratégico para: {vendedor_seleccionado}")
    with st.container(border=True):
        datos_vendedor = df_kpis[df_kpis['Vendedor'] == vendedor_seleccionado].iloc[0]
        ventas_vendedor = datos_vendedor['Ventas Brutas']
        margen_vendedor = datos_vendedor['Margen Operativo (%)']

        # Lógica para determinar el cuadrante y la recomendación
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
        st.markdown(f"**Análisis y Recomendación:** {analisis}")


# ==============================================================================
# SECCIÓN 4: EJECUCIÓN PRINCIPAL DE LA PÁGINA
# ==============================================================================

st.title("📊 Comparativa de Rendimiento de Vendedores")
st.markdown("Analiza y compara el desempeño del equipo para identificar líderes y oportunidades de coaching. Todos los datos corresponden al histórico completo.")
st.markdown("---")

# 1. Calcular los KPIs para todos los vendedores
df_kpis, promedios = calcular_kpis_globales(df_ventas_historico)

if df_kpis.empty:
    st.warning("No hay suficientes datos de vendedores con ventas para generar una comparativa.")
    st.stop()

# 2. Crear los selectores para la interactividad
col1, col2 = st.columns(2)
with col1:
    vendedores_options = sorted(df_kpis['Vendedor'].unique())
    vendedor_seleccionado = st.selectbox("Seleccione un Vendedor para analizar:", options=vendedores_options)
with col2:
    kpi_options = sorted(promedios.index)
    kpi_ranking = st.selectbox("Seleccione una Métrica para el Ranking:", options=kpi_options)

# 3. Renderizar los componentes de la UI basados en la selección
if vendedor_seleccionado:
    render_radar_chart(df_kpis, vendedor_seleccionado)
    st.markdown("---")
    render_matriz_equipo(df_kpis, promedios, vendedor_seleccionado)
    st.markdown("---")
    render_ranking_chart(df_kpis, kpi_ranking)
