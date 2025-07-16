# ==============================================================================
# SCRIPT DEFINITIVO PARA: pages/2_Perfil_del_Vendedor.py
# VERSIÓN: 3.0 (Asistente Estratégico)
# FECHA: 16 de Julio, 2025
#
# DESCRIPCIÓN:
# Esta es una reconstrucción completa del perfil de vendedor para convertirlo en
# una herramienta de inteligencia de negocios proactiva y accionable. El código
# ahora responde de manera explícita y potente a los filtros seleccionados.
#
# MEJORAS CLAVE ("VERSIÓN 1000%"):
# 1.  RESUMEN EJECUTIVO DINÁMICO: Un plan de acción generado automáticamente
#     al inicio que resume los hallazgos más críticos del periodo seleccionado.
#
# 2.  ANÁLISIS DE MOVIMIENTO DE CARTERA: Se reemplaza la lógica básica de
#     "nuevos/recurrentes" por un análisis profesional que identifica clientes
#     GANADOS, RETENIDOS, REACTIVADOS y EN FUGA (DORMIDOS).
#
# 3.  CUADRANTES DE RENTABILIDAD: Un análisis visual de Rentabilidad vs. Volumen
#     que segmenta los productos en "Motores de Ganancia", "Ventas de Volumen",
#     "Gemas Ocultas" y "Drenajes de Rentabilidad".
#
# 4.  RFM ACCIONABLE: La segmentación RFM ahora incluye recomendaciones
#     específicas y listas de clientes para cada segmento, facilitando la acción.
#
# 5.  INTERFAZ REFINADA: La navegación y presentación están diseñadas para guiar
#     al vendedor a través de un viaje analítico lógico y enfocado en resultados.
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import unicodedata

# ==============================================================================
# SECCIÓN 1: CONFIGURACIÓN INICIAL Y VALIDACIÓN
# ==============================================================================

st.set_page_config(page_title="Asistente Estratégico de Ventas", page_icon="💡", layout="wide")

def normalizar_texto(texto):
    if not isinstance(texto, str): return texto
    try:
        return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper().replace('-', ' ').strip().replace('  ', ' ')
    except (TypeError, AttributeError): return texto

def mostrar_acceso_restringido():
    st.header("🔒 Acceso Restringido")
    st.warning("Por favor, inicie sesión desde la página principal `🏠 Resumen Mensual` para continuar.")
    st.image("https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", width=300)
    st.stop()

if not st.session_state.get('autenticado'):
    mostrar_acceso_restringido()

df_ventas_historico = st.session_state.get('df_ventas')
APP_CONFIG = st.session_state.get('APP_CONFIG')
DATA_CONFIG = st.session_state.get('DATA_CONFIG')

if df_ventas_historico is None or df_ventas_historico.empty or not APP_CONFIG or not DATA_CONFIG:
    st.error("Error Crítico: No se pudieron cargar los datos desde la sesión. Por favor, regrese a la página '🏠 Resumen Mensual' y vuelva a cargar los datos.")
    st.stop()


# ==============================================================================
# SECCIÓN 2: LÓGICA DE ANÁLISIS ESTRATÉGICO (El "Cerebro")
# ==============================================================================

def calcular_metricas_base(df):
    """Añade columnas de margen y costo total, asegurando que los datos de entrada sean correctos."""
    df_copy = df.copy()
    df_copy['costo_total_linea'] = pd.to_numeric(df_copy['costo_unitario'], errors='coerce').fillna(0) * pd.to_numeric(df_copy['unidades_vendidas'], errors='coerce').fillna(0)
    df_copy['margen_bruto'] = pd.to_numeric(df_copy['valor_venta'], errors='coerce') - df_copy['costo_total_linea']
    df_copy['porcentaje_margen'] = np.where(df_copy['valor_venta'] > 0, (df_copy['margen_bruto'] / df_copy['valor_venta']) * 100, 0)
    return df_copy

@st.cache_data
def analizar_salud_cartera_avanzado(_df_periodo, _df_historico_completo, fecha_inicio_periodo):
    """Realiza un análisis avanzado de movimiento de cartera: Ganados, Retenidos, Reactivados y En Fuga."""
    clientes_periodo = set(_df_periodo['cliente_id'].unique())
    
    # Clientes que compraron ANTES de que el periodo seleccionado comenzara
    df_antes_periodo = _df_historico_completo[_df_historico_completo['fecha_venta'] < fecha_inicio_periodo]
    clientes_antes_periodo = set(df_antes_periodo['cliente_id'].unique())

    # Lógica de segmentación
    clientes_ganados = clientes_periodo - clientes_antes_periodo
    clientes_retenidos_o_reactivados = clientes_periodo.intersection(clientes_antes_periodo)
    clientes_en_fuga = clientes_antes_periodo - clientes_periodo

    # Para diferenciar retenidos de reactivados, definimos un umbral de inactividad (ej. 90 días)
    fecha_reactivacion_limite = fecha_inicio_periodo - pd.Timedelta(days=90)
    df_ultima_compra_antes = df_antes_periodo.groupby('cliente_id')['fecha_venta'].max()
    
    clientes_potencialmente_reactivados = set(df_ultima_compra_antes[df_ultima_compra_antes < fecha_reactivacion_limite].index)
    clientes_reactivados = clientes_retenidos_o_reactivados.intersection(clientes_potencialmente_reactivados)
    clientes_retenidos = clientes_retenidos_o_reactivados - clientes_reactivados
    
    # DataFrames para listas de acción
    df_clientes_en_fuga = _df_historico_completo[_df_historico_completo['cliente_id'].isin(clientes_en_fuga)].groupby(['cliente_id', 'nombre_cliente']).agg(
        ultima_compra=('fecha_venta', 'max'),
        valor_historico=('valor_venta', 'sum')
    ).nlargest(10, 'valor_historico').reset_index()

    return {
        "ganados": len(clientes_ganados),
        "retenidos": len(clientes_retenidos),
        "reactivados": len(clientes_reactivados),
        "en_fuga": len(clientes_en_fuga),
        "lista_clientes_en_fuga": df_clientes_en_fuga
    }

@st.cache_data
def analizar_rentabilidad_avanzado(_df_periodo):
    """Crea cuadrantes de rentabilidad y analiza productos clave."""
    if _df_periodo.empty: return pd.DataFrame()

    df_productos = _df_periodo.groupby(['codigo_articulo', 'nombre_articulo']).agg(
        Volumen_Venta=('valor_venta', 'sum'),
        Margen_Absoluto=('margen_bruto', 'sum')
    ).reset_index()

    df_productos = df_productos[df_productos['Volumen_Venta'] > 0]
    df_productos['Rentabilidad_Pct'] = np.where(df_productos['Volumen_Venta'] > 0, (df_productos['Margen_Absoluto'] / df_productos['Volumen_Venta']) * 100, 0)
    
    # Definición de cuadrantes
    volumen_medio = df_productos['Volumen_Venta'].median()
    rentabilidad_media = df_productos['Rentabilidad_Pct'].median()
    
    def get_cuadrante(row):
        alto_volumen = row['Volumen_Venta'] >= volumen_medio
        alta_rentabilidad = row['Rentabilidad_Pct'] >= rentabilidad_media
        if alto_volumen and alta_rentabilidad: return '⭐ Motores de Ganancia'
        if alto_volumen and not alta_rentabilidad: return '🐄 Ventas de Volumen'
        if not alto_volumen and alta_rentabilidad: return '💎 Gemas Ocultas'
        return '🤔 Drenajes de Rentabilidad'
    
    df_productos['Cuadrante'] = df_productos.apply(get_cuadrante, axis=1)
    return df_productos


@st.cache_data
def realizar_analisis_rfm(_df_vendedor):
    """Realiza un análisis RFM completo y robusto."""
    if _df_vendedor.empty: return pd.DataFrame(), {}
    df = _df_vendedor.copy()
    fecha_max_analisis = df['fecha_venta'].max() + pd.Timedelta(days=1)
    rfm_df = df.groupby(['cliente_id', 'nombre_cliente']).agg(
        Recencia=('fecha_venta', lambda date: (fecha_max_analisis - date.max()).days),
        Frecuencia=('fecha_venta', 'nunique'),
        Monetario=('valor_venta', 'sum')
    ).reset_index()
    
    rfm_df['R_Score'] = pd.qcut(rfm_df['Recencia'].rank(method='first'), 5, labels=[5, 4, 3, 2, 1])
    rfm_df['F_Score'] = pd.qcut(rfm_df['Frecuencia'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
    rfm_df['M_Score'] = pd.qcut(rfm_df['Monetario'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5])
    rfm_df['R_Score'] = rfm_df['R_Score'].astype(int)
    rfm_df['F_Score'] = rfm_df['F_Score'].astype(int)
    rfm_df['M_Score'] = rfm_df['M_Score'].astype(int)
    
    segt_map = {
        r'[1-2][1-2]': 'Hibernando', r'[1-2][3-4]': 'En Riesgo', r'[1-2]5': 'No Se Pueden Perder',
        r'3[1-2]': 'Necesitan Atención', r'33': 'Leales Promedio', r'[3-4][4-5]': 'Clientes Leales',
        r'41': 'Prometedores', r'51': 'Nuevos Clientes', r'[4-5][2-3]': 'Potenciales Leales', r'5[4-5]': 'Campeones'
    }
    rfm_df['Segmento'] = (rfm_df['R_Score'].astype(str) + rfm_df['F_Score'].astype(str)).replace(segt_map, regex=True)
    resumen_segmentos = rfm_df.groupby('Segmento').agg(
        Numero_Clientes=('cliente_id', 'count'),
        Ventas_Totales=('Monetario', 'sum')
    ).reset_index()
    return rfm_df, resumen_segmentos

# ==============================================================================
# SECCIÓN 3: COMPONENTES DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def generar_y_renderizar_resumen_ejecutivo(nombre_vendedor, analisis_cartera, df_rentabilidad):
    """Genera y muestra un resumen con los hallazgos y acciones más importantes."""
    st.header(f"💡 Resumen Ejecutivo y Plan de Acción para: {nombre_vendedor}")
    
    with st.container(border=True):
        st.markdown("#### Puntos Clave del Periodo:")
        
        # Punto 1: Movimiento de cartera
        st.markdown(f"- **Movimiento de Cartera:** Has conseguido **{analisis_cartera['ganados']} clientes nuevos** y **reactivado a {analisis_cartera['reactivados']}**. ¡Excelente trabajo! Sin embargo, **{analisis_cartera['en_fuga']} clientes entraron en estado de fuga**. Revisa la pestaña `Diagnóstico de Cartera` para ver la lista y contactarlos.")
        
        # Punto 2: Rentabilidad
        motores = df_rentabilidad[df_rentabilidad['Cuadrante'] == '⭐ Motores de Ganancia']
        drenajes = df_rentabilidad[df_rentabilidad['Cuadrante'] == '🤔 Drenajes de Rentabilidad']
        
        if not motores.empty:
            producto_motor = motores.nlargest(1, 'Volumen_Venta')['nombre_articulo'].iloc[0]
            st.markdown(f"- **Rentabilidad:** Tu principal motor de ganancia es **{producto_motor}**. Asegura su disponibilidad y promociónalo activamente. Por otro lado, hay **{len(drenajes)} productos que están drenando tu rentabilidad**. Analízalos en la pestaña `Análisis de Rentabilidad`.")
        
        st.markdown("- **Próximos Pasos:** Utiliza las pestañas de abajo para profundizar en cada área. Enfócate en contactar a los clientes en fuga y en impulsar tus productos 'Gemas Ocultas'.")

def render_tab_diagnostico_cartera(analisis):
    st.subheader("Análisis de Movimiento de Cartera")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Clientes Ganados 🟢", f"{analisis['ganados']}", help="Clientes que compraron por primera vez en este periodo.")
    col2.metric("Clientes Retenidos 🔵", f"{analisis['retenidos']}", help="Clientes que compraron en periodos anteriores y en este.")
    col3.metric("Clientes Reactivados ⭐", f"{analisis['reactivados']}", help="Clientes que estaban inactivos y volvieron a comprar.")
    col4.metric("Clientes en Fuga 🔴", f"{analisis['en_fuga']}", help="Clientes que compraban antes pero no en este periodo.")

    st.markdown("---")
    st.subheader("⚠️ Top 10 Clientes en Fuga por Valor Histórico")
    st.info("Estos son los clientes más valiosos que han dejado de comprar. ¡Son tu principal prioridad para contactar!")
    st.dataframe(analisis['lista_clientes_en_fuga'], use_container_width=True, hide_index=True,
                 column_config={"ultima_compra": st.column_config.DateColumn("Última Compra", format="YYYY-MM-DD"),
                                "valor_historico": st.column_config.NumberColumn("Ventas Históricas", format="$ {:,.0f}")})

def render_tab_rentabilidad(df_rentabilidad):
    st.subheader("Cuadrantes de Rentabilidad de Productos")
    if df_rentabilidad.empty:
        st.warning("No hay datos de productos para analizar la rentabilidad.")
        return
    
    fig = px.scatter(
        df_rentabilidad,
        x="Volumen_Venta", y="Rentabilidad_Pct",
        size="Margen_Absoluto", color="Cuadrante",
        hover_name="nombre_articulo", log_x=True, size_max=60,
        title="Análisis de Rentabilidad vs. Volumen de Venta",
        labels={"Volumen_Venta": "Volumen de Venta ($)", "Rentabilidad_Pct": "Rentabilidad (%)"},
        color_discrete_map={
            '⭐ Motores de Ganancia': 'green', '💎 Gemas Ocultas': 'gold',
            '🐄 Ventas de Volumen': 'dodgerblue', '🤔 Drenajes de Rentabilidad': 'tomato'
        }
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Ver detalle de productos por cuadrante", expanded=False):
        st.dataframe(df_rentabilidad[['nombre_articulo', 'Cuadrante', 'Volumen_Venta', 'Rentabilidad_Pct', 'Margen_Absoluto']], use_container_width=True, hide_index=True)


def render_tab_rfm_accionable(rfm_df, resumen_segmentos):
    st.subheader("Segmentación Estratégica de Clientes (RFM)")
    if rfm_df.empty:
        st.warning("No hay suficientes datos para realizar el análisis RFM.")
        return

    col1, col2 = st.columns([0.4, 0.6])
    with col1:
        st.markdown("##### Clientes por Segmento")
        st.dataframe(resumen_segmentos, use_container_width=True, hide_index=True)
    with col2:
        fig = px.treemap(resumen_segmentos, path=['Segmento'], values='Numero_Clientes', title='Distribución de Clientes por Segmento',
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Plan de Acción por Segmento")
    
    segmentos_accion = {
        'Campeones': ('⭐ **Acción:** Fidelizar y Recompensar. Son tus mejores clientes. Ofréceles acceso anticipado a productos y pídeles referidos.', 'green'),
        'Clientes Leales': ('🔵 **Acción:** Venta cruzada (upsell). Ya confían en ti. Ofréceles productos de mayor valor o complementarios.', 'blue'),
        'En Riesgo': ('🟠 **Acción:** Contacto proactivo. Llámalos, ofréceles un pequeño incentivo. Descubre por qué han disminuido su frecuencia.', 'orange'),
        'No Se Pueden Perder': ('🔴 **Acción:** ¡Urgente! Estos clientes eran muy frecuentes pero no han vuelto recientemente. Contacto personalizado inmediato.', 'red')
    }
    
    for segmento, (accion, color) in segmentos_accion.items():
        with st.expander(f"Clientes en Segmento: {segmento}"):
            st.markdown(f"<p style='color:{color};'>{accion}</p>", unsafe_allow_html=True)
            df_segmento = rfm_df[rfm_df['Segmento'] == segmento].nlargest(5, 'Monetario')
            st.dataframe(df_segmento[['nombre_cliente', 'Recencia', 'Frecuencia', 'Monetario']], use_container_width=True, hide_index=True)

# ==============================================================================
# SECCIÓN 4: ORQUESTADOR PRINCIPAL DE LA PÁGINA
# ==============================================================================

def render_pagina_perfil():
    """Función principal que orquesta el renderizado completo de la página."""
    st.title("💡 Asistente Estratégico de Ventas")
    st.markdown("Análisis 360° para impulsar tus resultados. **Cada dato aquí responde a los filtros que selecciones.**")
    st.markdown("---")

    # --- Filtros de Selección ---
    col1, col2 = st.columns([0.4, 0.6])
    with col1:
        # Lógica de selección de Vendedor/Grupo (sin cambios)
        vendedores_unicos_norm = sorted(list(df_ventas_historico['nomvendedor'].dropna().unique()))
        grupos = DATA_CONFIG.get('grupos_vendedores', {})
        vendedores_en_grupos_norm = [normalizar_texto(v) for lista in grupos.values() for v in lista]
        mapa_norm_a_orig = {normalizar_texto(v): v for v in df_ventas_historico['nomvendedor'].dropna().unique()}
        vendedores_solos_norm = [v_norm for v_norm in vendedores_unicos_norm if v_norm not in vendedores_en_grupos_norm]
        vendedores_solos_orig = sorted([mapa_norm_a_orig.get(v_norm) for v_norm in vendedores_solos_norm if mapa_norm_a_orig.get(v_norm)])
        nombres_grupos = sorted(grupos.keys())
        opciones_analisis = nombres_grupos + vendedores_solos_orig
        
        usuario_actual = st.session_state.usuario
        default_index = 0
        if normalizar_texto(usuario_actual) != "GERENTE":
            opciones_analisis = [usuario_actual] if usuario_actual in opciones_analisis else []
        else:
            opciones_analisis.insert(0, "Visión General de la Empresa")

        if not opciones_analisis:
            st.warning(f"No se encontraron datos asociados al usuario '{usuario_actual}'.")
            st.stop()
        
        seleccion = st.selectbox("Seleccione el Vendedor, Grupo o Visión a analizar:", opciones_analisis, index=default_index, help="Elija un perfil individual, un grupo consolidado o la visión general.")

    with col2:
        # Lógica del selector de rango de meses (sin cambios)
        df_vendedor_base_copy = df_ventas_historico.copy()
        df_vendedor_base_copy['periodo'] = df_vendedor_base_copy['fecha_venta'].dt.to_period('M')
        meses_disponibles = sorted(df_vendedor_base_copy['periodo'].unique())
        mapa_meses = {f"{DATA_CONFIG['mapeo_meses'].get(p.month, p.month)} {p.year}": p for p in meses_disponibles}
        opciones_slider = list(mapa_meses.keys())
        
        start_index = max(0, len(opciones_slider) - 12)
        end_index = len(opciones_slider) - 1
        if start_index > end_index: start_index = end_index

        mes_inicio_str, mes_fin_str = st.select_slider(
            "Seleccione el Rango de Meses para el Análisis:",
            options=opciones_slider, value=(opciones_slider[start_index], opciones_slider[end_index])
        )
        periodo_inicio, periodo_fin = mapa_meses[mes_inicio_str], mapa_meses[mes_fin_str]
        fecha_inicio, fecha_fin = periodo_inicio.start_time, periodo_fin.end_time.normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    # --- Filtrado de Datos Explícito ---
    if seleccion == "Visión General de la Empresa":
        df_base_filtrada = df_ventas_historico
    else:
        lista_vendedores_a_filtrar = grupos.get(seleccion, [seleccion])
        lista_vendedores_a_filtrar_norm = [normalizar_texto(v) for v in lista_vendedores_a_filtrar]
        df_base_filtrada = df_ventas_historico[df_ventas_historico['nomvendedor'].isin(lista_vendedores_a_filtrar_norm)]
    
    df_periodo_seleccionado = df_base_filtrada[(df_base_filtrada['fecha_venta'] >= fecha_inicio) & (df_base_filtrada['fecha_venta'] <= fecha_fin)]

    if df_periodo_seleccionado.empty:
        st.warning(f"No se encontraron datos para '{seleccion}' en el rango de meses seleccionado.")
        st.stop()

    # --- Ejecución de TODOS los análisis con los datos filtrados ---
    with st.spinner(f"Generando inteligencia de negocios para {seleccion}..."):
        df_procesado = calcular_metricas_base(df_periodo_seleccionado)
        analisis_cartera = analizar_salud_cartera_avanzado(df_procesado, df_base_filtrada, fecha_inicio)
        df_rentabilidad = analizar_rentabilidad_avanzado(df_procesado)
        rfm_df, resumen_rfm = realizar_analisis_rfm(df_procesado)
    
    st.markdown("---")
    
    # --- Renderizado de la página con los resultados del análisis ---
    generar_y_renderizar_resumen_ejecutivo(seleccion, analisis_cartera, df_rentabilidad)
    
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs([
        "🩺 **Diagnóstico de Cartera**",
        "🏆 **Segmentación de Clientes (RFM)**",
        "💰 **Análisis de Rentabilidad**"
    ])

    with tab1:
        render_tab_diagnostico_cartera(analisis_cartera)
    with tab2:
        render_tab_rfm_accionable(rfm_df, resumen_rfm)
    with tab3:
        render_tab_rentabilidad(df_rentabilidad)

# --- Punto de Entrada del Script ---
if __name__ == "__main__":
    render_pagina_perfil()
