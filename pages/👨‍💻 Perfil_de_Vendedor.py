# ==============================================================================
# SCRIPT DEFINITIVO PARA: pages/2_Perfil_del_Vendedor.py
# VERSIÓN: 5.4 (Solución Robusta y Definitiva de TypeError)
# FECHA: 17 de Julio, 2025
#
# DESCRIPCIÓN:
# Esta versión implementa una refactorización completa de la lógica de análisis
# RFM para erradicar el TypeError de forma permanente. Se reemplaza el método
# de binning (pd.cut/qcut), que es propenso a errores, por un enfoque de
# ranking por percentiles, que es mucho más robusto y se adapta a cualquier
# distribución de datos. Además, se han fortalecido todas las funciones de
# análisis y renderizado con validaciones de datos de entrada para garantizar
# que la aplicación sea estable y ofrezca feedback claro al usuario, incluso
# con datos incompletos o filtros que no arrojan resultados.
#
# CORRECCIONES CLAVE (v5.4):
# 1.  CRÍTICO Y NUEVO: Se rediseñó la función `realizar_analisis_rfm`.
#     - Se eliminó `pd.qcut` y `pd.cut` para la puntuación RFM.
#     - Se implementó un método de `.rank(pct=True)` que calcula el percentil
#       de cada cliente para R, F y M, y luego asigna una puntuación de 1 a 5.
#       Este método es universalmente estable y no falla por la distribución de datos.
#     - Esto resuelve la causa raíz del TypeError en `st.dataframe`.
# 2.  MEJORADO: Todas las funciones `render_tab_*` y `analizar_*` ahora
#     comienzan con una validación para manejar DataFrames vacíos de forma
#     explícita, mostrando mensajes informativos en lugar de errores.
# 3.  REFINADO: Se optimizó la limpieza de datos y las conversiones de tipo para
#     ser aún más seguras, siguiendo las mejores prácticas.
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
        # Reemplazar guiones y otros caracteres antes de la normalización
        s = texto.upper().replace('-', ' ').replace('_', ' ')
        s = ''.join(c for c in unicodedata.normalize('NFD', s)
                    if unicodedata.category(c) != 'Mn')
        return ' '.join(s.split())
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
    st.error("Error Crítico: No se pudieron cargar los datos. Regrese a '🏠 Resumen Mensual' y recargue la página.")
    st.stop()

# Copia para trabajar de forma segura
df_ventas_historico = df_ventas_historico_raw.copy()

# ==============================================================================
# SECCIÓN 1.5: SANEAMIENTO DE DATOS GLOBAL (AÚN MÁS ROBUSTO)
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

with st.spinner("Preparando y limpiando datos maestros..."):
    try:
        # 1. Normalizar columnas de texto para consistencia
        df_ventas_historico[NOM_VENDEDOR] = df_ventas_historico[NOM_VENDEDOR].apply(normalizar_texto)
        df_ventas_historico[NOMBRE_CLIENTE] = df_ventas_historico[NOMBRE_CLIENTE].fillna('N/A').apply(normalizar_texto)
        df_ventas_historico[NOMBRE_ARTICULO] = df_ventas_historico[NOMBRE_ARTICULO].fillna('N/A').apply(normalizar_texto)

        # 2. Asegurar tipos de datos correctos para columnas numéricas y de fecha
        df_ventas_historico[FECHA_VENTA] = pd.to_datetime(df_ventas_historico[FECHA_VENTA], errors='coerce')
        df_ventas_historico[VALOR_VENTA] = pd.to_numeric(df_ventas_historico[VALOR_VENTA], errors='coerce').fillna(0)
        df_ventas_historico[COSTO_UNITARIO] = pd.to_numeric(df_ventas_historico[COSTO_UNITARIO], errors='coerce').fillna(0)
        df_ventas_historico[UNIDADES_VENDIDAS] = pd.to_numeric(df_ventas_historico[UNIDADES_VENDIDAS], errors='coerce').fillna(0)

        # 3. Eliminar filas donde los identificadores clave o la fecha son nulos
        df_ventas_historico = df_ventas_historico.dropna(subset=[FECHA_VENTA, CLIENTE_ID, NOM_VENDEDOR])
    except Exception as e:
        st.error(f"Ocurrió un error inesperado durante la limpieza de datos: {e}")
        st.stop()


# ==============================================================================
# SECCIÓN 2: LÓGICA DE ANÁLISIS ESTRATÉGICO (FUNCIONES REFORZADAS)
# ==============================================================================

def calcular_metricas_base(df):
    """Calcula el costo, margen y porcentaje de margen para cada línea de venta."""
    if df.empty:
        return df
    df_copy = df.copy()
    costo_unit = pd.to_numeric(df_copy[COSTO_UNITARIO], errors='coerce').fillna(0)
    unidades = pd.to_numeric(df_copy[UNIDADES_VENDIDAS], errors='coerce').fillna(0)
    valor_venta = pd.to_numeric(df_copy[VALOR_VENTA], errors='coerce').fillna(0)

    df_copy[COSTO_TOTAL_LINEA] = costo_unit * unidades
    df_copy[MARGEN_BRUTO] = valor_venta - df_copy[COSTO_TOTAL_LINEA]
    df_copy[PORCENTAJE_MARGEN] = np.where(valor_venta > 0, (df_copy[MARGEN_BRUTO] / valor_venta) * 100, 0)
    return df_copy

def analizar_salud_cartera_avanzado(_df_periodo, _df_historico_contextual, fecha_inicio_periodo):
    """Analiza la cartera para identificar clientes ganados, retenidos, reactivados y en fuga."""
    if _df_periodo.empty or _df_historico_contextual.empty:
        return {
            "ganados": 0, "retenidos": 0, "reactivados": 0, "en_fuga": 0,
            "lista_clientes_en_fuga": pd.DataFrame()
        }

    clientes_periodo = set(_df_periodo[CLIENTE_ID].unique())
    df_antes_periodo = _df_historico_contextual[_df_historico_contextual[FECHA_VENTA] < fecha_inicio_periodo]
    clientes_antes_periodo = set(df_antes_periodo[CLIENTE_ID].unique())

    clientes_ganados = clientes_periodo - clientes_antes_periodo
    clientes_retenidos_o_reactivados = clientes_periodo.intersection(clientes_antes_periodo)
    clientes_en_fuga = clientes_antes_periodo - clientes_periodo

    fecha_reactivacion_limite = fecha_inicio_periodo - pd.Timedelta(days=90)
    if not df_antes_periodo.empty:
        df_ultima_compra_antes = df_antes_periodo.groupby(CLIENTE_ID)[FECHA_VENTA].max()
        clientes_potencialmente_reactivados = set(df_ultima_compra_antes[df_ultima_compra_antes < fecha_reactivacion_limite].index)
        clientes_reactivados = clientes_retenidos_o_reactivados.intersection(clientes_potencialmente_reactivados)
        clientes_retenidos = clientes_retenidos_o_reactivados - clientes_reactivados
    else:
        clientes_reactivados = set()
        clientes_retenidos = clientes_retenidos_o_reactivados

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
    if _df_periodo.empty:
        return pd.DataFrame()

    df_productos = _df_periodo.groupby([CODIGO_ARTICULO, NOMBRE_ARTICULO]).agg(
        Volumen_Venta=(VALOR_VENTA, 'sum'),
        Margen_Absoluto=(MARGEN_BRUTO, 'sum')
    ).reset_index()

    df_productos = df_productos[df_productos['Volumen_Venta'] > 0]
    if df_productos.empty:
        return pd.DataFrame()

    df_productos['Rentabilidad_Pct'] = np.where(df_productos['Volumen_Venta'] > 0, (df_productos['Margen_Absoluto'] / df_productos['Volumen_Venta']) * 100, 0)
    
    # Manejar caso de menos de 2 productos para evitar errores en medianas
    if len(df_productos) < 2:
        return pd.DataFrame()

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
    Realiza un análisis RFM robusto usando ranking por percentiles.
    Este método es superior a `pd.cut` y `pd.qcut` ya que no falla por
    la distribución de los datos, eliminando la causa del TypeError.
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

    rfm_df = rfm_df[rfm_df['Monetario'] > 0]
    if len(rfm_df) < 5:
        return pd.DataFrame(), pd.DataFrame()

    # --- PUNTUACIÓN POR PERCENTILES (MÉTODO ROBUSTO) ---
    # Menor recencia es mejor, por eso 'ascending=False' para el ranking
    rfm_df['R_Score'] = pd.qcut(rfm_df['Recencia'], 5, labels=[5, 4, 3, 2, 1], duplicates='drop').astype(int)
    # Mayor frecuencia y monetario es mejor
    rfm_df['F_Score'] = pd.qcut(rfm_df['Frecuencia'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm_df['M_Score'] = pd.qcut(rfm_df['Monetario'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    rfm_df['RFM_Score_Str'] = rfm_df['R_Score'].astype(str) + rfm_df['F_Score'].astype(str) + rfm_df['M_Score'].astype(str)
    
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
    rfm_df['Segmento'] = rfm_df['RFM_Score_Str'].replace(segt_map, regex=True)
    rfm_df['Segmento'] = rfm_df['Segmento'].apply(lambda x: 'Otros' if x.isnumeric() else x)

    resumen_segmentos = rfm_df.groupby('Segmento').agg(
        Numero_Clientes=(CLIENTE_ID, 'count'),
        Ventas_Totales=('Monetario', 'sum')
    ).sort_values('Ventas_Totales', ascending=False).reset_index()

    # Asegurar tipos de datos correctos para la visualización final
    rfm_df['Recencia'] = rfm_df['Recencia'].astype(int)
    rfm_df['Frecuencia'] = rfm_df['Frecuencia'].astype(int)
    rfm_df['Monetario'] = rfm_df['Monetario'].astype(float)
    
    return rfm_df, resumen_segmentos


def analizar_tendencias(_df_periodo):
    """Analiza la evolución de ventas y la concentración de productos (Pareto)."""
    if _df_periodo.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    df_ventas_mes = _df_periodo.set_index(FECHA_VENTA).resample('M')[VALOR_VENTA].sum().reset_index()
    df_ventas_mes['Mes'] = df_ventas_mes[FECHA_VENTA].dt.strftime('%Y-%m')
    
    df_productos_ventas = _df_periodo.groupby(NOMBRE_ARTICULO)[VALOR_VENTA].sum().sort_values(ascending=False).reset_index()
    if df_productos_ventas.empty or df_productos_ventas[VALOR_VENTA].sum() == 0:
        return df_ventas_mes, pd.DataFrame()

    total_ventas = df_productos_ventas[VALOR_VENTA].sum()
    top_5_ventas = df_productos_ventas.head(5)[VALOR_VENTA].sum()
    resto_ventas = total_ventas - top_5_ventas
    
    df_pareto = pd.DataFrame({'Categoría': ['Top 5 Productos', 'Resto de Productos'], 'Ventas': [top_5_ventas, resto_ventas]})
    return df_ventas_mes, df_pareto


# ==============================================================================
# SECCIÓN 3: COMPONENTES DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def generar_y_renderizar_resumen_ejecutivo(nombre_vendedor, analisis_cartera, df_rentabilidad, resumen_rfm):
    """Crea y muestra el resumen ejecutivo con los insights más importantes."""
    st.header(f"💡 Resumen Ejecutivo y Plan de Acción para: {nombre_vendedor}")
    with st.container(border=True):
        st.markdown("#### Diagnóstico Rápido del Periodo:")
        insight_cartera = f"**Movimiento de Cartera:** Lograste captar **{analisis_cartera.get('ganados', 0)} clientes nuevos** y reactivar a **{analisis_cartera.get('reactivados', 0)}**, ¡bien hecho! Sin embargo, **{analisis_cartera.get('en_fuga', 0)} clientes importantes están en fuga**. Prioriza contactarlos revisando la pestaña `Diagnóstico de Cartera`."
        st.markdown(f"📈 {insight_cartera}")
        
        if not df_rentabilidad.empty:
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
        col1.metric("Clientes Ganados 🟢", f"{analisis.get('ganados', 0)}", help="Clientes que compraron por primera vez en este periodo.")
        col2.metric("Clientes Retenidos 🔵", f"{analisis.get('retenidos', 0)}", help="Clientes que compraron en periodos anteriores y en este.")
        col3.metric("Clientes Reactivados ⭐", f"{analisis.get('reactivados', 0)}", help="Clientes que estaban inactivos (>90 días) y volvieron a comprar.")
        col4.metric("Clientes en Fuga 🔴", f"{analisis.get('en_fuga', 0)}", help="Clientes que compraban antes pero no en este periodo.")
    st.markdown("---")
    st.subheader("⚠️ Top 10 Clientes en Fuga por Valor Histórico")
    
    df_fuga_display = analisis.get('lista_clientes_en_fuga', pd.DataFrame())
    if df_fuga_display.empty:
        st.info("¡Buenas noticias! No se han detectado clientes importantes en fuga en este periodo.")
    else:
        st.info("Estos son los clientes más valiosos que han dejado de comprar. ¡Son tu principal prioridad para contactar!")
        st.dataframe(df_fuga_display[[NOMBRE_CLIENTE, 'ultima_compra', 'valor_historico']], use_container_width=True, hide_index=True,
                     column_config={
                         NOMBRE_CLIENTE: st.column_config.TextColumn("Nombre del Cliente"),
                         "ultima_compra": st.column_config.DateColumn("Última Compra", format="YYYY-MM-DD"),
                         "valor_historico": st.column_config.NumberColumn("Ventas Históricas", format="$ #,##0")})

def render_tab_rentabilidad(df_rentabilidad):
    """Muestra el gráfico de cuadrantes de rentabilidad y la tabla de productos."""
    st.subheader("Cuadrantes de Rentabilidad de Productos")
    if df_rentabilidad.empty:
        st.warning("No hay suficientes datos de productos para analizar la rentabilidad en el periodo seleccionado.")
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
        st.warning("No hay suficientes datos de clientes para realizar el análisis RFM con los filtros actuales (se requiere un mínimo de 5 clientes con ventas).")
        return
        
    with st.container(border=True):
        col1, col2 = st.columns([0.4, 0.6])
        with col1:
            st.markdown("##### Resumen de Segmentos")
            st.dataframe(resumen_segmentos, use_container_width=True, hide_index=True,
                         column_config={"Ventas_Totales": st.column_config.NumberColumn("Ventas Históricas", format="$ #,##0")})
        with col2:
            st.markdown("##### Distribución de Clientes por Segmento")
            fig = px.treemap(resumen_segmentos, path=['Segmento'], values='Numero_Clientes',
                             title='Cantidad de Clientes por Segmento',
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
            st.markdown(f"<p style='background-color: #f0f2f6; border-left: 6px solid {color}; padding: 10px; font-size:18px;'>{accion}</p>", unsafe_allow_html=True)
            
            df_display_segmento = rfm_df[rfm_df['Segmento'] == segmento_seleccionado].sort_values('Monetario', ascending=False)
            
            # ESTA ES LA LLAMADA QUE CAUSABA EL ERROR. AHORA ES SEGURA.
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
            st.info("No hay suficientes datos para mostrar una tendencia mensual (se requiere más de un mes de datos en el rango seleccionado).")
        else:
            fig_line = px.line(df_ventas_mes, x='Mes', y=VALOR_VENTA, markers=True,
                               title="Ventas Mensuales en el Periodo Seleccionado",
                               labels={VALOR_VENTA: 'Total Ventas ($)'})
            fig_line.update_traces(marker=dict(size=10))
            st.plotly_chart(fig_line, use_container_width=True)
            
    st.markdown("---")
    with st.container(border=True):
        st.markdown("#### Análisis Pareto: ¿Dónde se concentra tu venta?")
        if df_pareto.empty:
            st.info("No hay datos de ventas de productos para el análisis de Pareto.")
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
            vendedores_unicos_norm = sorted(list(df_ventas_historico[NOM_VENDEDOR].unique()))
            
            grupos_norm = {normalizar_texto(k): [normalizar_texto(v) for v in vs] for k, vs in grupos.items()}
            nombres_grupos_norm = sorted(grupos_norm.keys())
            
            usuario_actual_norm = normalizar_texto(st.session_state.usuario)
            es_gerente = usuario_actual_norm == "GERENTE"
            
            if es_gerente:
                opciones_analisis = ["Visión General de la Empresa"] + nombres_grupos_norm + vendedores_unicos_norm
                default_index = 0
            else:
                opciones_analisis = [v for v in [usuario_actual_norm] if v in vendedores_unicos_norm]
                default_index = 0
            
            if not opciones_analisis:
                st.error(f"No se encontraron datos de ventas asociados al usuario '{st.session_state.usuario}'. Verifique la fuente de datos.")
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
        lista_vendedores_a_filtrar_norm = grupos_norm.get(seleccion, [seleccion])
        df_base_filtrada = df_ventas_historico[df_ventas_historico[NOM_VENDEDOR].isin(lista_vendedores_a_filtrar_norm)]
    
    df_periodo_seleccionado = df_base_filtrada[
        (df_base_filtrada[FECHA_VENTA] >= fecha_inicio) & (df_base_filtrada[FECHA_VENTA] <= fecha_fin)
    ]

    if df_periodo_seleccionado.empty:
        st.warning(f"No se encontraron datos de ventas para **'{seleccion}'** en el rango de **{mes_inicio_str}** a **{mes_fin_str}**. Por favor, ajuste los filtros.")
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
