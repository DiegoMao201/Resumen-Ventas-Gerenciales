# ==============================================================================
# SCRIPT COMPLETO Y FUNCIONAL PARA: 🎯 Acciones y Recomendaciones.py
# VERSIÓN: 2.0 (COMPLETA)
# DESCRIPCIÓN: Página completa para el análisis de portafolio de productos.
#              Incluye Matriz BCG, análisis de rendimiento, oportunidades y un
#              plan de acción dinámico, todo controlado por filtros interactivos.
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import unicodedata

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Acciones y Recomendaciones",
    page_icon="🎯",
    layout="wide"
)

# ==============================================================================
# FUNCIONES AUXILIARES Y DE CÁLCULO
# ==============================================================================

def normalizar_texto(texto):
    """Normaliza texto a mayúsculas, sin tildes ni caracteres especiales."""
    if not isinstance(texto, str):
        return texto
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto)
                                  if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().strip()
    except (TypeError, AttributeError):
        return texto

@st.cache_data(ttl=1800)
def calcular_metricas_productos(_df):
    """
    Calcula un completo set de métricas por producto para análisis detallado.
    Devuelve un DataFrame robusto con Volumen de Venta, Costos, Márgenes y Rentabilidad.
    """
    if _df.empty:
        return pd.DataFrame()

    # 1. Filtrar solo ventas reales (positivas) para análisis de rendimiento.
    df_positivas = _df[_df['valor_venta'] > 0].copy()

    # 2. Asegurar que las columnas para el cálculo son numéricas.
    cols_numericas = ['valor_venta', 'costo_unitario', 'unidades_vendidas']
    for col in cols_numericas:
        df_positivas[col] = pd.to_numeric(df_positivas[col], errors='coerce')

    # 3. Eliminar filas donde los datos esenciales son nulos.
    df_positivas.dropna(subset=cols_numericas, inplace=True)
    
    # 4. Calcular el costo total por línea.
    df_positivas['costo_total_linea'] = df_positivas['costo_unitario'] * df_positivas['unidades_vendidas']
    
    # 5. Agrupar por producto para consolidar las métricas.
    df_productos = df_positivas.groupby(['codigo_articulo', 'nombre_articulo']).agg(
        Volumen_Venta=('valor_venta', 'sum'),
        Costo_Total=('costo_total_linea', 'sum'),
        Unidades_Vendidas=('unidades_vendidas', 'sum')
    ).reset_index()

    # 6. Calcular métricas de rentabilidad.
    df_productos['Margen_Absoluto'] = df_productos['Volumen_Venta'] - df_productos['Costo_Total']
    
    # Manejo seguro de división por cero para Rentabilidad.
    num = df_productos['Margen_Absoluto']
    den = df_productos['Volumen_Venta']
    df_productos['Rentabilidad_Pct'] = np.divide(num, den, out=np.zeros_like(num, dtype=float), where=den!=0) * 100

    # 7. Limpieza final y retorno.
    df_productos = df_productos[df_productos['Volumen_Venta'] > 0].sort_values(by="Volumen_Venta", ascending=False)
    
    return df_productos

@st.cache_data(ttl=1800)
def asignar_segmento_bcg(_df_productos):
    """Asigna el segmento BCG a un DataFrame de productos ya calculado."""
    if _df_productos.empty:
        return _df_productos

    df_result = _df_productos.copy()
    
    mediana_volumen = df_result['Volumen_Venta'].median()
    mediana_rentabilidad = df_result['Rentabilidad_Pct'].median()

    def get_segmento(row):
        es_alto_volumen = row['Volumen_Venta'] >= mediana_volumen
        es_alta_rentabilidad = row['Rentabilidad_Pct'] >= mediana_rentabilidad

        if es_alto_volumen and es_alta_rentabilidad: return '⭐ Estrella'
        if es_alto_volumen and not es_alta_rentabilidad: return '🐄 Vaca Lechera'
        if not es_alto_volumen and es_alta_rentabilidad: return '❓ Interrogante'
        return '🐕 Perro'

    df_result['Segmento_BCG'] = df_result.apply(get_segmento, axis=1)
    return df_result

def generar_plan_accion(df_analisis):
    """Genera una lista de recomendaciones textuales basadas en el análisis."""
    recomendaciones = []
    
    # Recomendaciones para productos con margen negativo
    df_negativos = df_analisis[df_analisis['Margen_Absoluto'] < 0].sort_values(by='Margen_Absoluto').head(5)
    if not df_negativos.empty:
        recomendaciones.append("### 🔴 **Acciones Críticas: Margen Negativo**")
        for _, row in df_negativos.iterrows():
            recomendaciones.append(f"- **Revisar Costos/Precios:** El producto **{row['nombre_articulo']}** generó una pérdida de **${-row['Margen_Absoluto']:,.0f}**. Es urgente analizar su estructura de costos o estrategia de precios.")

    # Recomendaciones para productos "Estrella"
    df_estrellas = df_analisis[df_analisis['Segmento_BCG'] == '⭐ Estrella'].sort_values(by='Volumen_Venta', ascending=False).head(3)
    if not df_estrellas.empty:
        recomendaciones.append("### ⭐ **Potenciar Estrellas**")
        for _, row in df_estrellas.iterrows():
            recomendaciones.append(f"- **Invertir y Proteger:** **{row['nombre_articulo']}** es un producto líder en ventas y rentabilidad. Asegura su disponibilidad, visibilidad y considera campañas para mantener su liderazgo.")

    # Recomendaciones para productos "Interrogante"
    df_interrogantes = df_analisis[df_analisis['Segmento_BCG'] == '❓ Interrogante'].sort_values(by='Rentabilidad_Pct', ascending=False).head(3)
    if not df_interrogantes.empty:
        recomendaciones.append("### ❓ **Desarrollar Interrogantes**")
        for _, row in df_interrogantes.iterrows():
            recomendaciones.append(f"- **Impulsar Ventas:** **{row['nombre_articulo']}** es muy rentable pero con bajo volumen. Analiza si una promoción o mayor exposición podría convertirlo en una estrella.")

    # Recomendaciones para productos "Perro"
    df_perros = df_analisis[df_analisis['Segmento_BCG'] == '🐕 Perro'].sort_values(by='Margen_Absoluto').head(3)
    if not df_perros.empty:
        recomendaciones.append("### 🐕 **Gestionar Perros**")
        for _, row in df_perros.iterrows():
            recomendaciones.append(f"- **Evaluar Continuidad:** El producto **{row['nombre_articulo']}** tiene bajo volumen y baja rentabilidad. Considera desinvertir, reemplazarlo o reducir su inventario al mínimo.")
            
    return recomendaciones if recomendaciones else ["¡Excelente! No se han identificado acciones críticas inmediatas en el portafolio."]


# ==============================================================================
# RENDERIZADO DE LA PÁGINA
# ==============================================================================

def render_pagina():
    """Orquesta la renderización de toda la página, incluyendo filtros y contenido en pestañas."""
    st.markdown("<style> .stTabs [data-baseweb='tab-list'] { gap: 2px; } </style>", unsafe_allow_html=True)
    st.title("🎯 Acciones y Recomendaciones de Portafolio")
    st.markdown("---")

    # --- Carga de datos y configuración desde la sesión ---
    if 'df_ventas' not in st.session_state or st.session_state.df_ventas.empty:
        st.error("No se han cargado los datos de ventas. Por favor, ve a la página principal y carga los datos primero.")
        st.stop()
        
    df_ventas_historicas = st.session_state.df_ventas
    # Cargar configuraciones (si no existen, crear placeholders para evitar errores)
    DATA_CONFIG = st.session_state.get('DATA_CONFIG', {'grupos_vendedores': {}, 'mapeo_meses': {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}})
    mapeo_meses = DATA_CONFIG.get('mapeo_meses', {})

    # --- Barra Lateral de Filtros ---
    st.sidebar.header("🗓️ Filtros de Periodo y Enfoque")
    lista_anios = sorted(df_ventas_historicas['anio'].unique(), reverse=True)
    anio_sel = st.sidebar.selectbox("Selecciona el Año", lista_anios, index=0, key="sel_anio_acciones")

    meses_disponibles = sorted(df_ventas_historicas[df_ventas_historicas['anio'] == anio_sel]['mes'].unique())
    if not meses_disponibles:
        st.warning(f"No hay datos disponibles para el año {anio_sel}.")
        st.stop()
        
    mes_sel = st.sidebar.selectbox("Selecciona el Mes", meses_disponibles, format_func=lambda x: mapeo_meses.get(x, "N/A"), key="sel_mes_acciones")
    
    # Filtro de Enfoque (General, Vendedor, Grupo)
    vendedores_unicos = sorted(df_ventas_historicas['nomvendedor'].dropna().unique())
    opciones_enfoque = ["Visión General"] + vendedores_unicos
    enfoque_sel = st.sidebar.selectbox("Enfocar análisis en:", opciones_enfoque, index=0, key="sel_enfoque_acciones")

    # --- Filtrado de Datos según Selección ---
    df_filtrado = df_ventas_historicas[
        (df_ventas_historicas['anio'] == anio_sel) &
        (df_ventas_historicas['mes'] == mes_sel)
    ]

    if enfoque_sel != "Visión General":
        df_filtrado = df_filtrado[df_filtrado['nomvendedor'] == enfoque_sel]

    if df_filtrado.empty:
        st.info(f"No se encontraron datos para la selección: {enfoque_sel} en {mapeo_meses.get(mes_sel)} {anio_sel}.")
        st.stop()
    
    # --- Cálculo principal ---
    df_analisis_productos = calcular_metricas_productos(df_filtrado)
    df_analisis_productos = asignar_segmento_bcg(df_analisis_productos)

    # --- Contenido en Pestañas ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Matriz de Portafolio (BCG)", 
        "📉 Productos de Bajo Rendimiento", 
        "🚀 Oportunidades de Crecimiento",
        "✍️ Plan de Acción Sugerido"
    ])

    with tab1:
        st.header(f"Análisis de Portafolio de Productos (BCG)")
        st.markdown(f"Análisis para: **{enfoque_sel}** | Periodo: **{mapeo_meses.get(mes_sel)} {anio_sel}**")

        if df_analisis_productos.empty:
            st.warning("No hay datos suficientes para generar la matriz de portafolio.")
        else:
            # Lógica de graficación robusta
            df_plot = df_analisis_productos[df_analisis_productos['Volumen_Venta'] > 0].copy()
            df_plot['Tamaño_Grafico'] = df_plot['Margen_Absoluto'].abs()

            if not df_plot.empty:
                fig_bcg = px.scatter(
                    df_plot,
                    x="Volumen_Venta", y="Rentabilidad_Pct",
                    size="Tamaño_Grafico", color="Segmento_BCG",
                    hover_name="nombre_articulo",
                    hover_data={'Volumen_Venta': ':,.0f', 'Rentabilidad_Pct': ':.2f', 'Margen_Absoluto': ':,.0f'},
                    log_x=True, size_max=60, title="Matriz de Rendimiento de Productos",
                    labels={"Volumen_Venta": "Volumen de Venta ($)", "Rentabilidad_Pct": "Rentabilidad (%)"},
                    color_discrete_map={'⭐ Estrella': 'gold', '🐄 Vaca Lechera': 'dodgerblue', '❓ Interrogante': 'limegreen', '🐕 Perro': 'tomato'}
                )
                st.plotly_chart(fig_bcg, use_container_width=True)
            
            # Detalle por cuadrante
            for segmento, emoji in [("⭐ Estrella", "⭐"), ("🐄 Vaca Lechera", "🐄"), ("❓ Interrogante", "❓"), ("🐕 Perro", "🐕")]:
                with st.expander(f"{emoji} Productos en el cuadrante: {segmento}", expanded=False):
                    df_segmento = df_analisis_productos[df_analisis_productos['Segmento_BCG'] == segmento]
                    if not df_segmento.empty:
                        st.dataframe(df_segmento[['nombre_articulo', 'Volumen_Venta', 'Rentabilidad_Pct', 'Margen_Absoluto']], use_container_width=True, hide_index=True)
                    else:
                        st.info(f"No hay productos en el cuadrante '{segmento}' para la selección actual.")
    
    with tab2:
        st.header("Análisis de Productos de Bajo Rendimiento")
        st.markdown(f"Análisis para: **{enfoque_sel}** | Periodo: **{mapeo_meses.get(mes_sel)} {anio_sel}**")

        st.subheader("Productos con Margen de Contribución Negativo")
        df_margen_negativo = df_analisis_productos[df_analisis_productos['Margen_Absoluto'] < 0].sort_values(by="Margen_Absoluto")
        if not df_margen_negativo.empty:
            st.warning("Estos productos generaron pérdidas. Es crítico revisar su costo o precio de venta.")
            st.dataframe(df_margen_negativo, use_container_width=True, hide_index=True,
                         column_config={"Volumen_Venta": st.column_config.NumberColumn(format="$ {:,.0f}"),
                                        "Margen_Absoluto": st.column_config.NumberColumn(format="$ {:,.0f}"),
                                        "Rentabilidad_Pct": st.column_config.ProgressColumn(format="%.2f%%", min_value=float(df_margen_negativo['Rentabilidad_Pct'].min()), max_value=0)})
        else:
            st.success("¡Buenas noticias! No se encontraron productos con margen negativo.")
            
        st.subheader("Productos 'Perro' (Bajo Volumen y Baja Rentabilidad)")
        df_perros = df_analisis_productos[df_analisis_productos['Segmento_BCG'] == '🐕 Perro'].sort_values(by='Volumen_Venta')
        if not df_perros.empty:
            st.info("Estos productos tienen baja rotación y baja rentabilidad. Considere reducir inventario o descontinuarlos.")
            st.dataframe(df_perros[['nombre_articulo', 'Volumen_Venta', 'Rentabilidad_Pct']], use_container_width=True, hide_index=True)
        else:
            st.success("No se encontraron productos en la categoría 'Perro'.")


    with tab3:
        st.header("Identificación de Oportunidades de Crecimiento")
        st.markdown(f"Análisis para: **{enfoque_sel}** | Periodo: **{mapeo_meses.get(mes_sel)} {anio_sel}**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏆 Top 10 Productos por Venta")
            st.dataframe(df_analisis_productos.nlargest(10, 'Volumen_Venta'), use_container_width=True, hide_index=True)

        with col2:
            st.subheader("💰 Top 10 Productos por Margen Absoluto")
            st.dataframe(df_analisis_productos.nlargest(10, 'Margen_Absoluto'), use_container_width=True, hide_index=True)
            
        st.subheader("🚀 Productos 'Estrella' e 'Interrogante' con Mayor Potencial")
        df_oportunidades = df_analisis_productos[df_analisis_productos['Segmento_BCG'].isin(['⭐ Estrella', '❓ Interrogante'])]
        if not df_oportunidades.empty:
            st.info("Enfoque sus esfuerzos de venta y marketing en estos productos para maximizar el retorno.")
            st.dataframe(df_oportunidades[['nombre_articulo', 'Segmento_BCG', 'Volumen_Venta', 'Rentabilidad_Pct']], use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron productos en las categorías de alto potencial ('Estrella' o 'Interrogante').")

    with tab4:
        st.header("Plan de Acción Sugerido y Personalizado")
        st.markdown(f"Análisis para: **{enfoque_sel}** | Periodo: **{mapeo_meses.get(mes_sel)} {anio_sel}**")
        
        if df_analisis_productos.empty:
            st.info("No hay datos suficientes para generar un plan de acción.")
        else:
            with st.container(border=True):
                st.subheader("Resumen de Acciones Clave")
                plan_de_accion = generar_plan_accion(df_analisis_productos)
                for punto in plan_de_accion:
                    st.markdown(punto)

# ==============================================================================
# EJECUCIÓN DEL SCRIPT
# ==============================================================================
render_pagina()
