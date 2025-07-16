# ==============================================================================
# SCRIPT COMPLETO Y FUNCIONAL PARA: 🎯 Acciones y Recomendaciones.py
# VERSIÓN: 1.0
# DESCRIPCIÓN: Script robusto para el análisis de portafolio de productos
#              utilizando una matriz BCG interactiva. Incluye limpieza de datos
#              preventiva para evitar errores de graficación en Plotly.
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Acciones y Recomendaciones",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Acciones y Recomendaciones de Portafolio")
st.markdown("---")

# ==============================================================================
# FUNCIÓN DE CÁLCULO DE LA MATRIZ BCG
# ==============================================================================
@st.cache_data(ttl=1800)
def calcular_matriz_bcg(_df_ventas):
    """
    Calcula las métricas necesarias para la matriz BCG a partir de los datos de ventas.

    Args:
        _df_ventas (pd.DataFrame): DataFrame con el detalle de ventas del periodo.

    Returns:
        pd.DataFrame: DataFrame con los productos y sus métricas y segmento BCG.
    """
    # 1. Filtrar solo ventas reales (positivas) y excluir notas de crédito.
    #    Se consideran solo facturas directas y albaranes (potenciales ventas).
    df_positivas = _df_ventas[_df_ventas['valor_venta'] > 0].copy()

    # 2. Asegurar que las columnas para el cálculo son numéricas.
    cols_numericas = ['valor_venta', 'costo_unitario', 'unidades_vendidas']
    for col in cols_numericas:
        df_positivas[col] = pd.to_numeric(df_positivas[col], errors='coerce')

    # 3. Eliminar filas donde los datos esenciales son nulos después de la conversión.
    df_positivas.dropna(subset=cols_numericas, inplace=True)
    
    # 4. Calcular el costo total por línea.
    df_positivas['costo_total_linea'] = df_positivas['costo_unitario'] * df_positivas['unidades_vendidas']
    
    # 5. Agrupar por producto para consolidar las métricas.
    df_productos = df_positivas.groupby(['codigo_articulo', 'nombre_articulo']).agg(
        Volumen_Venta=('valor_venta', 'sum'),
        Costo_Total=('costo_total_linea', 'sum')
    ).reset_index()

    # 6. Calcular métricas de rentabilidad.
    df_productos['Margen_Absoluto'] = df_productos['Volumen_Venta'] - df_productos['Costo_Total']
    
    # Se usa np.divide para manejar de forma segura la división por cero.
    rentabilidad_num = df_productos['Margen_Absoluto']
    rentabilidad_den = df_productos['Volumen_Venta']
    df_productos['Rentabilidad_Pct'] = np.divide(rentabilidad_num, rentabilidad_den, out=np.zeros_like(rentabilidad_num, dtype=float), where=rentabilidad_den!=0) * 100

    # 7. Segmentación BCG
    #    - Eje X (Cuota de mercado relativa) -> Usaremos Volumen_Venta como proxy.
    #    - Eje Y (Tasa de crecimiento) -> Usaremos Rentabilidad_Pct como proxy.
    
    # Se eliminan productos con venta cero o negativa que pudieran quedar.
    df_productos = df_productos[df_productos['Volumen_Venta'] > 0]

    # Calcular los puntos de corte (medianas) para la segmentación.
    mediana_volumen = df_productos['Volumen_Venta'].median()
    mediana_rentabilidad = df_productos['Rentabilidad_Pct'].median()

    def get_segmento_bcg(row):
        es_alto_volumen = row['Volumen_Venta'] >= mediana_volumen
        es_alta_rentabilidad = row['Rentabilidad_Pct'] >= mediana_rentabilidad

        if es_alto_volumen and es_alta_rentabilidad:
            return '⭐ Estrella'
        elif es_alto_volumen and not es_alta_rentabilidad:
            return '🐄 Vaca Lechera'
        elif not es_alto_volumen and es_alta_rentabilidad:
            return '❓ Interrogante'
        else:
            return '🐕 Perro'

    if not df_productos.empty:
        df_productos['Segmento_BCG'] = df_productos.apply(get_segmento_bcg, axis=1)

    return df_productos


# ==============================================================================
# FUNCIÓN PRINCIPAL PARA RENDERIZAR LA PÁGINA
# ==============================================================================
def render_pagina_acciones():
    """
    Orquesta la renderización de toda la página, incluyendo filtros y gráficos.
    """
    # --- Carga de datos desde la sesión ---
    if 'df_ventas' not in st.session_state or st.session_state.df_ventas.empty:
        st.error("No se han cargado los datos de ventas. Por favor, ve a la página principal y carga los datos primero.")
        st.stop()
    
    df_ventas_historicas = st.session_state.df_ventas
    
    # --- Barra Lateral de Filtros ---
    st.sidebar.header("🗓️ Filtros de Periodo")

    lista_anios = sorted(df_ventas_historicas['anio'].unique(), reverse=True)
    anio_sel = st.sidebar.selectbox("Selecciona el Año", lista_anios, index=0)

    meses_disponibles = sorted(df_ventas_historicas[df_ventas_historicas['anio'] == anio_sel]['mes'].unique())
    if not meses_disponibles:
        st.warning(f"No hay datos disponibles para el año {anio_sel}.")
        st.stop()
        
    # Mapeo de número de mes a nombre para el selector
    mapeo_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    mes_sel = st.sidebar.selectbox(
        "Selecciona el Mes", 
        meses_disponibles, 
        format_func=lambda x: mapeo_meses.get(x, "N/A")
    )

    # --- Filtrado de datos según selección ---
    df_ventas_periodo = df_ventas_historicas[
        (df_ventas_historicas['anio'] == anio_sel) &
        (df_ventas_historicas['mes'] == mes_sel)
    ]

    if df_ventas_periodo.empty:
        st.info("No se encontraron datos de ventas para el periodo seleccionado.")
        st.stop()
        
    # --- Cálculo y Visualización de la Matriz BCG ---
    st.header(f"Matriz de Rendimiento de Productos (BCG) - {mapeo_meses.get(mes_sel)} {anio_sel}")

    df_bcg = calcular_matriz_bcg(df_ventas_periodo)

    if df_bcg.empty:
        st.warning("No se pudieron generar las métricas de productos para este periodo. Verifica que haya datos de ventas y costos.")
    else:
        # ---- CÓDIGO DE GRAFICACIÓN ROBUSTO (ANTI-ERROR) ----

        # 1. Crear una copia segura para la visualización.
        df_plot = df_bcg.copy()

        # 2. Filtro de seguridad para eje logarítmico: x debe ser > 0.
        df_plot = df_plot[df_plot['Volumen_Venta'] > 0]

        # 3. Filtro de seguridad para el tamaño: debe ser >= 0.
        #    Se usa el valor absoluto para representar la magnitud del margen.
        df_plot['Tamaño_Grafico'] = df_plot['Margen_Absoluto'].abs()

        # 4. Comprobar si quedan datos después de la limpieza final.
        if not df_plot.empty:
            fig_bcg = px.scatter(
                df_plot,
                x="Volumen_Venta",
                y="Rentabilidad_Pct",
                size="Tamaño_Grafico",  # Usar la columna segura
                color="Segmento_BCG",
                hover_name="nombre_articulo",
                hover_data={ # Añadir más información útil al pasar el ratón
                    'Volumen_Venta': ':,.0f',
                    'Rentabilidad_Pct': ':.2f',
                    'Margen_Absoluto': ':,.0f',
                    'Tamaño_Grafico': False # Ocultar la columna auxiliar
                },
                log_x=True,
                size_max=60,
                title="Análisis de Portafolio de Productos",
                labels={
                    "Volumen_Venta": "Volumen de Venta ($) - Eje Logarítmico",
                    "Rentabilidad_Pct": "Rentabilidad (%)",
                    "Segmento_BCG": "Segmento BCG"
                },
                color_discrete_map={
                    '⭐ Estrella': 'gold',
                    '🐄 Vaca Lechera': 'dodgerblue',
                    '❓ Interrogante': 'limegreen',
                    '🐕 Perro': 'tomato'
                }
            )
            fig_bcg.update_layout(
                xaxis_title="Volumen de Venta ($) - (Refleja Cuota de Mercado)",
                yaxis_title="Rentabilidad (%) - (Refleja Potencial de Crecimiento)"
            )
            st.plotly_chart(fig_bcg, use_container_width=True)
        else:
            st.info("No hay productos con datos válidos para graficar en la matriz BCG después de la limpieza.")

    # --- Sección Adicional: Productos para Revisión ---
    st.markdown("---")
    st.header("🔬 Productos que Requieren Atención")

    if not df_bcg.empty:
        df_margen_negativo = df_bcg[df_bcg['Margen_Absoluto'] < 0].sort_values(by="Margen_Absoluto", ascending=True)

        if not df_margen_negativo.empty:
            st.warning("Se han identificado productos con margen de contribución negativo. Revisa la estrategia de precios o los costos asociados.")
            st.dataframe(
                df_margen_negativo[['nombre_articulo', 'Volumen_Venta', 'Margen_Absoluto', 'Rentabilidad_Pct']],
                column_config={
                    "nombre_articulo": st.column_config.TextColumn("Producto", width="large"),
                    "Volumen_Venta": st.column_config.NumberColumn("Venta Neta", format="$ {:,.0f}"),
                    "Margen_Absoluto": st.column_config.NumberColumn("Margen", format="$ {:,.0f}"),
                    "Rentabilidad_Pct": st.column_config.ProgressColumn(
                        "Rentabilidad (%)", 
                        format="%.2f%%",
                        min_value=float(df_margen_negativo['Rentabilidad_Pct'].min()),
                        max_value=0
                    ),
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("¡Buenas noticias! No se encontraron productos con margen negativo en el periodo seleccionado.")
            
# ==============================================================================
# EJECUCIÓN DEL SCRIPT
# ==============================================================================
render_pagina_acciones()
