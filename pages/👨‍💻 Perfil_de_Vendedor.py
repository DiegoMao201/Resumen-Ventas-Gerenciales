# ==============================================================================
# SCRIPT DEFINITIVO PARA: pages/2_Perfil_del_Vendedor.py
# VERSIÓN: 5.3 (Solución "Paranoica" y Definitiva de TypeError)
# FECHA: 16 de Julio, 2025
#
# DESCRIPCIÓN:
# Versión final que adopta un enfoque de limpieza de datos "paranoico" para
# erradicar de forma definitiva el persistente TypeError en st.dataframe.
# Esta versión añade limpieza a las columnas de texto y utiliza las prácticas
# de pandas más seguras.
#
# CORRECCIONES CLAVE (v5.3):
# 1.  NUEVO Y CRÍTICO: Se añade un bloque de "Saneamiento de Datos Global" al
#     inicio. Este bloque normaliza las columnas de texto clave (`nomvendedor`,
#     `nombre_cliente`, `nombre_articulo`) en el DataFrame principal una sola vez.
#     Esto resuelve el error fundamental de filtrado al comparar texto
#     normalizado con texto no normalizado.
# 2.  REFINADO: La lógica de filtrado de vendedores ahora funciona correctamente
#     porque tanto la selección del usuario como la columna de datos están
#     en el mismo formato normalizado.
# 3.  MANTIENE: El robusto bloque de saneamiento de datos numéricos y la
#     conversión de tipos segura introducida en versiones anteriores.
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

st.set_page_config(page_title="Perfil del Vendedor", page_icon="💡", layout="wide")

def normalizar_texto(texto):
    """Normaliza un texto a mayúsculas, sin acentos y con espacios simples."""
    if not isinstance(texto, str):
        return str(texto) # Forzar conversión a string si no lo es
    try:
        s = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
        return ' '.join(s.upper().replace('-', ' ').split())
    except (TypeError, AttributeError):
        return str(texto) # Retornar como string en caso de cualquier error

def mostrar_acceso_restringido():
    """Muestra un mensaje de advertencia si el usuario no está autenticado."""
    st.header("🔒 Acceso Restringido")
    st.warning("Por favor, inicie sesión desde la página principal `🏠 Resumen Mensual` para continuar.")
    st.image("https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", width=300)
    st.stop()

if not st.session_state.get('autenticado'):
    mostrar_acceso_restringido()

df_ventas_historico_raw = st.session_state.get('df_ventas')
APP_CONFIG = st.session_state.get('APP_CONFIG')
DATA_CONFIG = st.session_state.get('DATA_CONFIG')

if df_ventas_historico_raw is None or df_ventas_historico_raw.empty or not APP_CONFIG or not DATA_CONFIG:
    st.error("Error Crítico: No se pudieron cargar los datos. Regrese a '🏠 Resumen Mensual' y recargue.")
    st.stop()

# Copia para trabajar de forma segura
df_ventas_historico = df_ventas_historico_raw.copy()

# ==============================================================================
# ### CORRECCIÓN CLAVE ###
# SECCIÓN 1.5: SANEAMIENTO DE DATOS GLOBAL
# Normalizar todas las columnas críticas una sola vez al principio.
# Esto garantiza consistencia en todo el script (filtros, agrupaciones, etc.).
# ==============================================================================

# Definir columnas constantes para evitar errores de tipeo
FECHA_VENTA = 'fecha_venta'
CLIENTE_ID = 'cliente_id'
NOMBRE_CLIENTE = 'nombre_cliente'
VALOR_VENTA = 'valor_venta'
COSTO_UNITARIO = 'costo_unitario'
UNIDADES_VENDIDAS = 'unidades_vendidas'
CODIGO_ARTICULO = 'codigo_articulo'
NOMBRE_ARTICULO = 'nombre_articulo'
NOM_VENDEDOR = 'nomvendedor'
COSTO_TOTAL_LINEA = 'costo_total_linea'
MARGEN_BRUTO = 'margen_bruto'
PORCENTAJE_MARGEN = 'porcentaje_margen'

with st.spinner("Preparando y limpiando datos..."):
    # 1. Normalizar columnas de texto para consistencia
    df_ventas_historico[NOM_VENDEDOR] = df_ventas_historico[NOM_VENDEDOR].apply(normalizar_texto)
    df_ventas_historico[NOMBRE_CLIENTE] = df_ventas_historico[NOMBRE_CLIENTE].fillna('N/A').apply(normalizar_texto)
    df_ventas_historico[NOMBRE_ARTICULO] = df_ventas_historico[NOMBRE_ARTICULO].fillna('N/A').apply(normalizar_texto)

    # 2. Asegurar tipos de datos correctos para columnas numéricas y de fecha
    df_ventas_historico[FECHA_VENTA] = pd.to_datetime(df_ventas_historico[FECHA_VENTA], errors='coerce')
    df_ventas_historico[VALOR_VENTA] = pd.to_numeric(df_ventas_historico[VALOR_VENTA], errors='coerce').fillna(0)
    df_ventas_historico[COSTO_UNITARIO] = pd.to_numeric(df_ventas_historico[COSTO_UNITARIO], errors='coerce').fillna(0)
    df_ventas_historico[UNIDADES_VENDIDAS] = pd.to_numeric(df_ventas_historico[UNIDADES_VENDIDAS], errors='coerce').fillna(0)

    # 3. Eliminar filas donde la fecha es nula, ya que son inútiles para el análisis
    df_ventas_historico = df_ventas_historico.dropna(subset=[FECHA_VENTA])


# ==============================================================================
# SECCIÓN 2: LÓGICA DE ANÁLISIS ESTRATÉGICO
# (Las funciones ahora pueden asumir que reciben datos limpios)
# ==============================================================================

def calcular_metricas_base(df):
    """Calcula el costo, margen y porcentaje de margen para cada línea de venta."""
    df_copy = df.copy()
    # Los datos ya vienen limpios, pero una comprobación extra no hace daño
    costo_unit = pd.to_numeric(df_copy[COSTO_UNITARIO], errors='coerce').fillna(0)
    unidades = pd.to_numeric(df_copy[UNIDADES_VENDIDAS], errors='coerce').fillna(0)
    valor_venta = pd.to_numeric(df_copy[VALOR_VENTA], errors='coerce').fillna(0)

    df_copy[COSTO_TOTAL_LINEA] = costo_unit * unidades
    df_copy[MARGEN_BRUTO] = valor_venta - df_copy[COSTO_TOTAL_LINEA]
    df_copy[PORCENTAJE_MARGEN] = np.where(valor_venta > 0, (df_copy[MARGEN_BRUTO] / valor_venta) * 100, 0)
    return df_copy

def analizar_salud_cartera_avanzado(_df_periodo, _df_historico_contextual, fecha_inicio_periodo):
    """Analiza la cartera para identificar clientes ganados, retenidos, reactivados y en fuga."""
    clientes_periodo = set(_df_periodo[CLIENTE_ID].unique())
    
    df_antes_periodo = _df_historico_contextual[_df_historico_contextual[FECHA_VENTA] < fecha_inicio_periodo]
    clientes_antes_periodo = set(df_antes_periodo[CLIENTE_ID].unique())

    clientes_ganados = clientes_periodo - clientes_antes_periodo
    clientes_retenidos_o_reactivados = clientes_periodo.intersection(clientes_antes_periodo)
    clientes_en_fuga = clientes_antes_periodo - clientes_periodo

    fecha_reactivacion_limite = fecha_inicio_periodo - pd.Timedelta(days=90)
    df_ultima_compra_antes = df_antes_periodo.groupby(CLIENTE_ID)[FECHA_VENTA].max()
    
    clientes_potencialmente_reactivados = set(df_ultima_compra_antes[df_ultima_compra_antes < fecha_reactivacion_limite].index)
    clientes_reactivados = clientes_retenidos_o_reactivados.intersection(clientes_potencialmente_reactivados)
    clientes_retenidos = clientes_retenidos_o_reactivados - clientes_reactivados
    
    df_clientes_en_fuga = _df_historico_contextual[_df_historico_contextual[CLIENTE_ID].isin(clientes_en_fuga)].groupby([CLIENTE_ID, NOMBRE_CLIENTE]).agg(
        ultima_compra=(FECHA_VENTA, 'max'),
        valor_historico=(VALOR_VENTA, 'sum')
    ).reset_index().sort_values('valor_historico', ascending=False).head(10)

    return {
        "ganados": len(clientes_ganados), "retenidos": len(clientes_retenidos),
        "reactivados": len(clientes_reactivados), "en_fuga": len(clientes_en_fuga),
        "lista_clientes_en_fuga": df_clientes_en_fuga
    }

def analizar_rentabilidad_avanzado(_df_periodo):
    """Clasifica los productos en cuadrantes de rentabilidad vs. volumen."""
    if _df_periodo.empty: return pd.DataFrame()

    df_productos = _df_periodo.groupby([CODIGO_ARTICULO, NOMBRE_ARTICULO]).agg(
        Volumen_Venta=(VALOR_VENTA, 'sum'),
        Margen_Absoluto=(MARGEN_BRUTO, 'sum')
    ).reset_index()

    df_productos = df_productos[df_productos['Volumen_Venta'] > 0]
    if df_productos.empty: return pd.DataFrame()
    
    df_productos['Rentabilidad_Pct'] = np.where(df_productos['Volumen_Venta'] > 0, (df_productos['Margen_Absoluto'] / df_productos['Volumen_Venta']) * 100, 0)
    
    # Usar np.median para mayor robustez ante outliers
    volumen_medio = np.median(df_productos['Volumen_Venta'])
    rentabilidad_media = np.median(df_productos['Rentabilidad_Pct'])
    
    def get_cuadrante(row):
        alto_volumen = row['Volumen_Venta'] >= volumen_medio
        alta_rentabilidad = row['Rentabilidad_Pct'] >= rentabilidad_media
        if alto_volumen and alta_rentabilidad: return '⭐ Motores de Ganancia'
        if alto_volumen and not alta_rentabilidad: return '🐄 Ventas de Volumen'
        if not alto_volumen and alta_rentabilidad: return '💎 Gemas Ocultas'
        return '🤔 Drenajes de Rentabilidad'
    
    df_productos['Cuadrante'] = df_productos.apply(get_cuadrante, axis=1)
    df_productos['Tamaño_Absoluto'] = df_productos['Margen_Absoluto'].abs().fillna(1) + 1
    return df_productos

def realizar_analisis_rfm(_df_historico_vendedor):
    """
    Realiza un análisis RFM. Asume que el DF de entrada ya ha pasado la limpieza global.
    """
    if _df_historico_vendedor.empty or _df_historico_vendedor[CLIENTE_ID].nunique() < 5:
        return pd.DataFrame(), pd.DataFrame()

    df = _df_historico_vendedor.copy()
    fecha_max_analisis = df[FECHA_VENTA].max() + pd.Timedelta(days=1)

    rfm_df = df.groupby([CLIENTE_ID, NOMBRE_CLIENTE]).agg(
        Recencia=(FECHA_VENTA, lambda date: (fecha_max_analisis - date.max()).days),
        Frecuencia=(FECHA_VENTA, 'nunique'),
        Monetario=(VALOR_VENTA, 'sum')
    ).reset_index()

    # --- SANEAMIENTO ADICIONAL ESPECIAL PARA RFM ---
    rfm_df = rfm_df.replace([np.inf, -np.inf], np.nan)
    rfm_df = rfm_df.dropna(subset=['Recencia', 'Frecuencia', 'Monetario'])
    rfm_df = rfm_df[rfm_df['Monetario'] > 0]

    if rfm_df.empty or len(rfm_df) < 5:
        return pd.DataFrame(), pd.DataFrame()

    try:
        rfm_df['Recencia'] = rfm_df['Recencia'].astype(int)
        rfm_df['Frecuencia'] = rfm_df['Frecuencia'].astype(int)
        rfm_df['Monetario'] = rfm_df['Monetario'].astype(float)
    except (ValueError, TypeError):
        st.error("Error al convertir tipos de datos en análisis RFM.")
        return pd.DataFrame(), pd.DataFrame()
    
    # Puntuación de Recencia (menos días = mejor)
    recencia_bins = [-1, 30, 90, 180, 365, rfm_df['Recencia'].max() + 1]
    rfm_df['R_Score'] = pd.cut(rfm_df['Recencia'], bins=recencia_bins, labels=[5, 4, 3, 2, 1], right=False)

    # Puntuación de Frecuencia (más compras = mejor)
    frecuencia_bins = [0, 1, 3, 5, 10, rfm_df['Frecuencia'].max() + 1]
    rfm_df['F_Score'] = pd.cut(rfm_df['Frecuencia'], bins=frecuencia_bins, labels=[1, 2, 3, 4, 5], right=False)

    # Puntuación Monetaria (más valor = mejor)
    try:
        rfm_df['M_Score'] = pd.qcut(rfm_df['Monetario'], 5, labels=[1, 2, 3, 4, 5], duplicates='drop')
    except ValueError:
        rfm_df['M_Score'] = 3

    rfm_df[['R_Score', 'F_Score', 'M_Score']] = rfm_df[['R_Score', 'F_Score', 'M_Score']].fillna(3).astype(int)

    segt_map = {
        r'55[4-5]': 'Campeones', r'[3-4]5[4-5]': 'Campeones',
        r'54[4-5]': 'Clientes Leales', r'44[4-5]': 'Clientes Leales',
        r'[4-5][4-5]3': 'Potenciales Leales', r'[3-4][3-4][3-5]': 'Potenciales Leales',
        r'5[1-3][1-5]': 'Nuevos Clientes', r'4[1-3][1-5]': 'Prometedores',
        r'333': 'Necesitan Atención', r'3[1-2][1-5]': 'Necesitan Atención',
        r'1[3-5][1-5]': 'En Riesgo', r'2[3-5][1-5]': 'En Riesgo',
        r'12[1-5]': 'A Punto de Dormir', r'22[1-5]': 'A Punto de Dormir',
        r'11[1-5]': 'Hibernando', r'21[1-5]': 'Hibernando',
    }
    rfm_df['RFM_Score_Str'] = rfm_df['R_Score'].astype(str) + rfm_df['F_Score'].astype(str) + rfm_df['M_Score'].astype(str)
    rfm_df['Segmento'] = rfm_df['RFM_Score_Str'].replace(segt_map, regex=True)
    rfm_df['Segmento'] = rfm_df['Segmento'].apply(lambda x: 'Otros' if x.isnumeric() else x)

    resumen_segmentos = rfm_df.groupby('Segmento').agg(
        Numero_Clientes=(CLIENTE_ID, 'count'),
        Ventas_Totales=('Monetario', 'sum')
    ).sort_values('Ventas_Totales', ascending=False).reset_index()

    return rfm_df, resumen_segmentos

def analizar_tendencias(_df_periodo):
    """Analiza la evolución de ventas y la concentración de productos (Pareto)."""
    if _df_periodo.empty: return pd.DataFrame(), pd.DataFrame()
    
    df_ventas_mes = _df_periodo.set_index(FECHA_VENTA).resample('M')[VALOR_VENTA].sum().reset_index()
    df_ventas_mes['Mes'] = df_ventas_mes[FECHA_VENTA].dt.strftime('%Y-%m')
    
    df_productos_ventas = _df_periodo.groupby(NOMBRE_ARTICULO)[VALOR_VENTA].sum().sort_values(ascending=False).reset_index()
    if df_productos_ventas.empty: return df_ventas_mes, pd.DataFrame()

    total_ventas = df_productos_ventas[VALOR_VENTA].sum()
    top_5_ventas = df_productos_ventas.head(5)[VALOR_VENTA].sum()
    resto_ventas = total_ventas - top_5_ventas
    
    df_pareto = pd.DataFrame({'Categoría': ['Top 5 Productos', 'Resto de Productos'], 'Ventas': [top_5_ventas, resto_ventas]})
    return df_ventas_mes, df_pareto


# ==============================================================================
# SECCIÓN 3: COMPONENTES DE LA INTERFAZ DE USUARIO (UI)
# (Las funciones de renderizado no cambian, pero ahora reciben datos más fiables)
# ==============================================================================

def generar_y_renderizar_resumen_ejecutivo(nombre_vendedor, analisis_cartera, df_rentabilidad, resumen_rfm):
    """Crea y muestra el resumen ejecutivo con los insights más importantes."""
    st.header(f"💡 Resumen Ejecutivo y Plan de Acción para: {nombre_vendedor}")
    with st.container(border=True):
        st.markdown("#### Diagnóstico Rápido del Periodo:")
        insight_cartera = f"**Movimiento de Cartera:** Lograste captar **{analisis_cartera['ganados']} clientes nuevos** y reactivar a **{analisis_cartera['reactivados']}**, ¡bien hecho! Sin embargo, **{analisis_cartera['en_fuga']} clientes importantes están en fuga**. Prioriza contactarlos revisando la pestaña `Diagnóstico de Cartera`."
        st.markdown(f"📈 {insight_cartera}")
        
        motores = df_rentabilidad[df_rentabilidad['Cuadrante'] == '⭐ Motores de Ganancia']
        drenajes = df_rentabilidad[df_rentabilidad['Cuadrante'] == '🤔 Drenajes de Rentabilidad']
        insight_rentabilidad = ""
        if not motores.empty:
            producto_motor = motores.nlargest(1, 'Volumen_Venta')
            nombre_motor = producto_motor[NOMBRE_ARTICULO].iloc[0]
            venta_motor = producto_motor['Volumen_Venta'].iloc[0]
            insight_rentabilidad += f" Tu principal **motor de ganancia** es **'{nombre_motor}'**, que generó **${venta_motor:,.0f}**. ¡Poténcialo!"
        if not drenajes.empty:
            producto_drenaje = drenajes.nlargest(1, 'Volumen_Venta')
            nombre_drenaje = producto_drenaje[NOMBRE_ARTICULO].iloc[0]
            margen_drenaje = producto_drenaje['Margen_Absoluto'].iloc[0]
            insight_rentabilidad += f" ⚠️ **Alerta:** El producto **'{nombre_drenaje}'** es un **drenaje de rentabilidad** significativo (margen de ${margen_drenaje:,.0f}). Revisa su costo o estrategia de precio."
        if insight_rentabilidad:
            st.markdown(f"💰 **Análisis de Rentabilidad:**{insight_rentabilidad}")
            
        if not resumen_rfm.empty:
            campeones = resumen_rfm[resumen_rfm['Segmento'] == 'Campeones']
            if not campeones.empty:
                num_campeones = campeones['Numero_Clientes'].iloc[0]
                ventas_campeones = campeones['Ventas_Totales'].iloc[0]
                insight_rfm = f"Posees **{num_campeones} clientes 'Campeones'** que representan un valor de **${ventas_campeones:,.0f}** en tu historial. Son tu activo más valioso. ¡Cuídalos y recompénsalos!"
                st.markdown(f"❤️ **Fidelidad de Clientes:** {insight_rfm}")
                
        st.markdown("---")
        st.success("**Plan de Acción Sugerido:**\n"
                    "1.  **URGENTE:** Contacta a los **'Clientes en Fuga'** y a los del segmento **'En Riesgo'**.\n"
                    "2.  **ESTRATÉGICO:** Impulsa las ventas de tus **'Gemas Ocultas'** a tus clientes **'Campeones'** y **'Leales'**.\n"
                    "3.  **REVISIÓN:** Analiza los costos de tus productos en el cuadrante **'Drenajes de Rentabilidad'**.")

def render_tab_diagnostico_cartera(analisis):
    """Muestra las métricas y la tabla de clientes en fuga."""
    st.subheader("Análisis de Movimiento de Cartera")
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Clientes Ganados 🟢", f"{analisis['ganados']}", help="Clientes que compraron por primera vez en este periodo.")
        col2.metric("Clientes Retenidos 🔵", f"{analisis['retenidos']}", help="Clientes que compraron en periodos anteriores y en este.")
        col3.metric("Clientes Reactivados ⭐", f"{analisis['reactivados']}", help="Clientes que estaban inactivos (>90 días) y volvieron a comprar.")
        col4.metric("Clientes en Fuga 🔴", f"{analisis['en_fuga']}", help="Clientes que compraban antes pero no en este periodo.")
    st.markdown("---")
    st.subheader("⚠️ Top 10 Clientes en Fuga por Valor Histórico")
    st.info("Estos son los clientes más valiosos que han dejado de comprar. ¡Son tu principal prioridad para contactar!")
    
    df_fuga_display = analisis['lista_clientes_en_fuga'][[NOMBRE_CLIENTE, 'ultima_compra', 'valor_historico']]
    st.dataframe(df_fuga_display, use_container_width=True, hide_index=True,
                 column_config={
                     NOMBRE_CLIENTE: st.column_config.TextColumn("Nombre del Cliente"),
                     "ultima_compra": st.column_config.DateColumn("Última Compra", format="YYYY-MM-DD"),
                     "valor_historico": st.column_config.NumberColumn("Ventas Históricas", format="$ #,##0")})

def render_tab_rentabilidad(df_rentabilidad):
    """Muestra el gráfico de cuadrantes de rentabilidad y la tabla de productos."""
    st.subheader("Cuadrantes de Rentabilidad de Productos")
    if df_rentabilidad.empty:
        st.warning("No hay datos de productos para analizar la rentabilidad en el periodo seleccionado.")
        return
        
    with st.container(border=True):
        fig = px.scatter(
            df_rentabilidad,
            x="Volumen_Venta",
            y="Rentabilidad_Pct",
            size="Tamaño_Absoluto",
            color="Cuadrante",
            hover_name=NOMBRE_ARTICULO,
            log_x=True,
            size_max=60,
            title="Análisis de Rentabilidad vs. Volumen de Venta",
            labels={"Volumen_Venta": "Volumen de Venta ($) - Escala Logarítmica", "Rentabilidad_Pct": "Rentabilidad (%)"},
            color_discrete_map={
                '⭐ Motores de Ganancia': '#2ca02c', '💎 Gemas Ocultas': '#ff7f0e',
                '🐄 Ventas de Volumen': '#1f77b4', '🤔 Drenajes de Rentabilidad': '#d62728'
            }
        )
        # Usar np.median para consistencia con la función de análisis
        fig.add_vline(x=np.median(df_rentabilidad['Volumen_Venta']), line_dash="dash", annotation_text="Mediana Volumen")
        fig.add_hline(y=np.median(df_rentabilidad['Rentabilidad_Pct']), line_dash="dash", annotation_text="Mediana Rentabilidad")
        st.plotly_chart(fig, use_container_width=True)
        
    with st.expander("Ver detalle de productos por cuadrante y explicación", expanded=False):
        st.markdown(
            "- **⭐ Motores de Ganancia:** Alta venta y alta rentabilidad. Son tus estrellas. ¡Poténcialos!\n"
            "- **🐄 Ventas de Volumen:** Alta venta, baja rentabilidad. Mueven mucho inventario pero con poco margen. Optimiza costos.\n"
            "- **💎 Gemas Ocultas:** Baja venta, alta rentabilidad. Productos muy rentables pero poco vendidos. ¡Promociónalos!\n"
            "- **🤔 Drenajes de Rentabilidad:** Baja venta y baja rentabilidad (o negativa). Cuidado, pueden estar quitándote recursos."
        )
        st.dataframe(
            df_rentabilidad[[NOMBRE_ARTICULO, 'Cuadrante', 'Volumen_Venta', 'Rentabilidad_Pct', 'Margen_Absoluto']],
            use_container_width=True, hide_index=True,
            column_config={
                "Volumen_Venta": st.column_config.NumberColumn("Venta ($)", format="$ #,##0"),
                "Rentabilidad_Pct": st.column_config.NumberColumn("Rentabilidad (%)", format="%.2f%%"),
                "Margen_Absoluto": st.column_config.NumberColumn("Margen ($)", format="$ #,##0")
            }
        )

def render_tab_rfm_accionable(rfm_df, resumen_segmentos):
    """Muestra los gráficos y tablas del análisis RFM con planes de acción."""
    st.subheader("Segmentación Estratégica de Clientes (RFM)")
    if rfm_df.empty or resumen_segmentos.empty:
        st.warning("No hay suficientes datos de clientes para realizar el análisis RFM con los filtros actuales.")
        return
        
    with st.container(border=True):
        col1, col2 = st.columns([0.4, 0.6])
        with col1:
            st.markdown("##### Resumen de Segmentos")
            st.dataframe(resumen_segmentos, use_container_width=True, hide_index=True,
                          column_config={"Ventas_Totales": st.column_config.NumberColumn("Ventas Históricas", format="$ #,##0")})
        with col2:
            fig = px.treemap(resumen_segmentos, path=['Segmento'], values='Numero_Clientes',
                             title='Distribución de Clientes por Segmento (Cantidad)',
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
            
    st.markdown("---")
    st.subheader("Plan de Acción por Segmento")
    
    acciones_segmento = {
        'Campeones': ('⭐ **Acción:** Fidelizar y Recompensar. Son tus mejores clientes. Ofréceles acceso anticipado, beneficios exclusivos y pídeles referidos.', 'green'),
        'Clientes Leales': ('🔵 **Acción:** Venta cruzada (upsell) y mantener la satisfacción. Ofréceles productos de mayor valor o complementarios.', 'blue'),
        'Potenciales Leales': ('🟡 **Acción:** Aumentar frecuencia y compromiso. Ofréceles membresías o programas de puntos.', 'goldenrod'),
        'Prometedores': ('🟣 **Acción:** Convertirlos en leales. Ofrece seguimiento personalizado y promociones de bienvenida.', 'purple'),
        'Nuevos Clientes': ('⚪ **Acción:** Brindar una excelente primera experiencia. Asegura un onboarding exitoso y soporte post-venta.', 'grey'),
        'Necesitan Atención': ('🟠 **Acción:** Reactivación con ofertas personalizadas. Descubre por qué han disminuido su actividad.', 'orange'),
        'En Riesgo': ('🔴 **Acción:** Contacto proactivo URGENTE. Llámalos, ofréceles un incentivo fuerte. Descubre el motivo de su ausencia.', 'red'),
        'A Punto de Dormir': ('🟤 **Acción:** Última llamada para retener. Ofrece una oferta irresistible para que vuelvan.', 'brown'),
        'Hibernando': ('⚫ **Acción:** Limpieza de base de datos o campaña de reactivación masiva de bajo costo. Probablemente perdidos.', 'black'),
        'Otros': ('❓ **Acción:** Análisis Individual. Estos clientes tienen patrones de compra no clasificados. Investiga sus perfiles.', 'lightblue')
    }
    
    opciones_segmento = resumen_segmentos['Segmento'].unique()
    if opciones_segmento.size > 0:
        segmento_seleccionado = st.selectbox("Selecciona un segmento para ver los clientes y el plan de acción:", options=opciones_segmento)
        if segmento_seleccionado and segmento_seleccionado in acciones_segmento:
            accion, color = acciones_segmento[segmento_seleccionado]
            st.markdown(f"<p style='color:{color}; font-size:18px; font-weight:bold;'>{accion}</p>", unsafe_allow_html=True)
            
            df_display_segmento = rfm_df[rfm_df['Segmento'] == segmento_seleccionado].sort_values('Monetario', ascending=False)
            
            st.dataframe(
                df_display_segmento[[NOMBRE_CLIENTE, 'Recencia', 'Frecuencia', 'Monetario']],
                help="Recencia (días desde la última compra), Frecuencia (nº de compras), Monetario (valor total histórico)",
                use_container_width=True, hide_index=True,
                column_config={
                    NOMBRE_CLIENTE: "Nombre del Cliente",
                    "Recencia": st.column_config.NumberColumn("Recencia (días)"),
                    "Frecuencia": st.column_config.NumberColumn("Frecuencia (compras)"),
                    "Monetario": st.column_config.NumberColumn("Valor Histórico", format="$ #,##0")
                }
            )
    else:
        st.warning("No se encontraron segmentos de clientes para mostrar con los filtros actuales.")

def render_tab_tendencias(df_ventas_mes, df_pareto):
    """Muestra el gráfico de evolución de ventas y el Pareto de productos."""
    st.subheader("Tendencias y Composición de Ventas en el Periodo")
    with st.container(border=True):
        st.markdown("#### Evolución de Ventas Mensuales")
        if df_ventas_mes.empty or len(df_ventas_mes) < 2:
            st.warning("No hay suficientes datos para mostrar una tendencia mensual (se requiere más de un mes).")
        else:
            fig_line = px.line(df_ventas_mes, x='Mes', y=VALOR_VENTA, markers=True,
                               title="Ventas Mensuales en el Periodo Seleccionado",
                               labels={VALOR_VENTA: 'Total Ventas ($)'})
            fig_line.update_traces(marker=dict(size=10))
            st.plotly_chart(fig_line, use_container_width=True)
            
    st.markdown("---")
    with st.container(border=True):
        st.markdown("#### Análisis Pareto: ¿Dónde se concentra tu venta?")
        if df_pareto.empty or df_pareto['Ventas'].sum() == 0:
            st.warning("No hay suficientes datos de ventas de productos para el análisis de Pareto.")
        else:
            fig_pie = px.pie(df_pareto, names='Categoría', values='Ventas',
                             title='Concentración de Ventas: Top 5 Productos vs. Resto',
                             hole=0.4, color_discrete_sequence=['#1f77b4', '#aec7e8'])
            st.plotly_chart(fig_pie, use_container_width=True)
            st.info("Este gráfico muestra qué porción de tus ingresos viene de tus 5 productos más vendidos. Una alta concentración puede ser un riesgo.")


# ==============================================================================
# SECCIÓN 4: ORQUESTADOR PRINCIPAL DE LA PÁGINA
# ==============================================================================

def render_pagina_perfil():
    """Función principal que renderiza la página completa, incluyendo filtros y análisis."""
    st.title("💡 Asistente Estratégico de Ventas")
    st.markdown(f"Bienvenido, **{st.session_state.usuario}**. Usa los filtros para obtener un análisis 360° y potenciar tus resultados.")
    st.markdown("---")
    
    with st.container(border=True):
        col1, col2 = st.columns([0.4, 0.6])
        
        with col1:
            grupos = DATA_CONFIG.get('grupos_vendedores', {})
            # ### CORRECCIÓN CLAVE ###
            # Ahora se obtienen los vendedores únicos del DF ya normalizado.
            vendedores_unicos_norm = sorted(list(df_ventas_historico[NOM_VENDEDOR].unique()))
            
            # Normalizar los nombres de los grupos para la comparación
            grupos_norm = {normalizar_texto(k): [normalizar_texto(v) for v in vs] for k, vs in grupos.items()}
            nombres_grupos_norm = sorted(grupos_norm.keys())
            
            usuario_actual = st.session_state.usuario
            # Normalizar el usuario actual para la lógica de roles
            usuario_actual_norm = normalizar_texto(usuario_actual)
            es_gerente = usuario_actual_norm == "GERENTE"
            
            if es_gerente:
                opciones_analisis = ["Visión General de la Empresa"] + nombres_grupos_norm + vendedores_unicos_norm
                default_index = 0
            else:
                # Si el usuario actual no es gerente, solo puede ver sus propios datos.
                opciones_analisis = [usuario_actual_norm] if usuario_actual_norm in vendedores_unicos_norm else []
                default_index = 0
            
            if not opciones_analisis:
                st.error(f"No se encontraron datos de ventas asociados al usuario '{usuario_actual}'. Verifique la fuente de datos.")
                st.stop()
                
            seleccion = st.selectbox(
                "Seleccione el Vendedor, Grupo o Visión a analizar:",
                opciones_analisis, index=default_index,
                help="Elige un perfil individual, un grupo consolidado o la visión general de la empresa."
            )

        with col2:
            df_ventas_historico['periodo'] = df_ventas_historico[FECHA_VENTA].dt.to_period('M')
            meses_disponibles = sorted(df_ventas_historico['periodo'].unique())
            mapa_meses = {f"{DATA_CONFIG['mapeo_meses'].get(p.month, p.month)} {p.year}": p for p in meses_disponibles}
            opciones_slider = list(mapa_meses.keys())
            
            if not opciones_slider:
                st.error("No hay meses disponibles para el análisis en los datos cargados.")
                st.stop()

            start_index = max(0, len(opciones_slider) - 12)
            end_index = len(opciones_slider) - 1
            if start_index > end_index: start_index = end_index

            mes_inicio_str, mes_fin_str = st.select_slider(
                "Seleccione el Rango de Meses para el Análisis:",
                options=opciones_slider,
                value=(opciones_slider[start_index], opciones_slider[end_index]),
                help="Define el marco de tiempo para todos los análisis en esta página."
            )
            periodo_inicio, periodo_fin = mapa_meses[mes_inicio_str], mapa_meses[mes_fin_str]
            fecha_inicio = periodo_inicio.start_time.tz_localize(None)
            fecha_fin = periodo_fin.end_time.tz_localize(None)

    # --- LÓGICA DE FILTRADO (AHORA CORRECTA Y ROBUSTA) ---
    if seleccion == "Visión General de la Empresa":
        df_base_filtrada = df_ventas_historico
    else:
        # Busca la selección en los grupos normalizados o la trata como un vendedor individual
        lista_vendedores_a_filtrar_norm = grupos_norm.get(seleccion, [seleccion])
        df_base_filtrada = df_ventas_historico[df_ventas_historico[NOM_VENDEDOR].isin(lista_vendedores_a_filtrar_norm)]
    
    df_periodo_seleccionado = df_base_filtrada[
        (df_base_filtrada[FECHA_VENTA] >= fecha_inicio) & (df_base_filtrada[FECHA_VENTA] <= fecha_fin)
    ]

    if df_periodo_seleccionado.empty:
        st.warning(f"No se encontraron datos para **'{seleccion}'** en el rango de **{mes_inicio_str}** a **{mes_fin_str}**. Por favor, ajuste los filtros.")
        st.stop()

    with st.spinner(f"Generando inteligencia de negocios para {seleccion}..."):
        df_procesado = calcular_metricas_base(df_periodo_seleccionado)
        analisis_cartera = analizar_salud_cartera_avanzado(df_procesado, df_base_filtrada, fecha_inicio)
        df_rentabilidad = analizar_rentabilidad_avanzado(df_procesado)
        rfm_df, resumen_rfm = realizar_analisis_rfm(df_base_filtrada)
        df_ventas_mes, df_pareto = analizar_tendencias(df_procesado)
    
    st.markdown("---")
    
    generar_y_renderizar_resumen_ejecutivo(seleccion, analisis_cartera, df_rentabilidad, resumen_rfm)
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🩺 **Diagnóstico de Cartera**",
        "🏆 **Segmentación de Clientes (RFM)**",
        "💰 **Análisis de Rentabilidad**",
        "📈 **Tendencias y Composición**"
    ])

    with tab1:
        render_tab_diagnostico_cartera(analisis_cartera)
    with tab2:
        render_tab_rfm_accionable(rfm_df, resumen_rfm)
    with tab3:
        render_tab_rentabilidad(df_rentabilidad)
    with tab4:
        render_tab_tendencias(df_ventas_mes, df_pareto)

if __name__ == "__main__":
    render_pagina_perfil()
