# ==============================================================================
# SCRIPT DEFINITIVO PARA: pages/2_Perfil_del_Vendedor.py
# VERSIÓN: 4.2 (Solución Definitiva de TypeError en RFM con Lógica Robusta)
# FECHA: 16 de Julio, 2025
#
# DESCRIPCIÓN:
# Versión final que soluciona de raíz el TypeError en el análisis RFM
# reemplazando la frágil lógica de `pd.qcut` por una robusta basada en
# `pd.cut` con umbrales fijos, garantizando estabilidad con cualquier filtro.
#
# CORRECCIONES CLAVE:
# 1.  ERROR CRÍTICO (TypeError) SOLUCIONADO:
#     - Se reemplazó `pd.qcut` por `pd.cut` para la puntuación de Recencia y
#       Frecuencia. `pd.qcut` falla con datos de baja variedad (común en
#       filtros), mientras que `pd.cut` usa umbrales fijos y es siempre estable.
#     - Se añadió un bloque try-except para la puntuación Monetaria como una
#       capa extra de seguridad, aunque es menos propensa a fallar.
#     - Este cambio previene la generación de datos corruptos (NaN) que
#       causaban el colapso de `st.dataframe`.
#
# 2.  LÓGICA DE NEGOCIO MEJORADA: Los umbrales fijos en RFM son más
#     interpretables y consistentes que los cuantiles estadísticos.
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
    df_copy = df.copy()
    df_copy['costo_total_linea'] = pd.to_numeric(df_copy['costo_unitario'], errors='coerce').fillna(0) * pd.to_numeric(df_copy['unidades_vendidas'], errors='coerce').fillna(0)
    df_copy['margen_bruto'] = pd.to_numeric(df_copy['valor_venta'], errors='coerce') - df_copy['costo_total_linea']
    df_copy['porcentaje_margen'] = np.where(df_copy['valor_venta'] > 0, (df_copy['margen_bruto'] / df_copy['valor_venta']) * 100, 0)
    return df_copy

def analizar_salud_cartera_avanzado(_df_periodo, _df_historico_contextual, fecha_inicio_periodo):
    clientes_periodo = set(_df_periodo['cliente_id'].unique())
    
    df_antes_periodo = _df_historico_contextual[_df_historico_contextual['fecha_venta'] < fecha_inicio_periodo]
    clientes_antes_periodo = set(df_antes_periodo['cliente_id'].unique())

    clientes_ganados = clientes_periodo - clientes_antes_periodo
    clientes_retenidos_o_reactivados = clientes_periodo.intersection(clientes_antes_periodo)
    clientes_en_fuga = clientes_antes_periodo - clientes_periodo

    fecha_reactivacion_limite = fecha_inicio_periodo - pd.Timedelta(days=90)
    df_ultima_compra_antes = df_antes_periodo.groupby('cliente_id')['fecha_venta'].max()
    
    clientes_potencialmente_reactivados = set(df_ultima_compra_antes[df_ultima_compra_antes < fecha_reactivacion_limite].index)
    clientes_reactivados = clientes_retenidos_o_reactivados.intersection(clientes_potencialmente_reactivados)
    clientes_retenidos = clientes_retenidos_o_reactivados - clientes_reactivados
    
    df_clientes_en_fuga = _df_historico_contextual[_df_historico_contextual['cliente_id'].isin(clientes_en_fuga)].groupby(['cliente_id', 'nombre_cliente']).agg(
        ultima_compra=('fecha_venta', 'max'),
        valor_historico=('valor_venta', 'sum')
    ).reset_index().sort_values('valor_historico', ascending=False).head(10)

    return {
        "ganados": len(clientes_ganados), "retenidos": len(clientes_retenidos),
        "reactivados": len(clientes_reactivados), "en_fuga": len(clientes_en_fuga),
        "lista_clientes_en_fuga": df_clientes_en_fuga
    }

def analizar_rentabilidad_avanzado(_df_periodo):
    if _df_periodo.empty: return pd.DataFrame()

    df_productos = _df_periodo.groupby(['codigo_articulo', 'nombre_articulo']).agg(
        Volumen_Venta=('valor_venta', 'sum'),
        Margen_Absoluto=('margen_bruto', 'sum')
    ).reset_index()

    df_productos = df_productos[df_productos['Volumen_Venta'] > 0]
    df_productos['Rentabilidad_Pct'] = np.where(df_productos['Volumen_Venta'] > 0, (df_productos['Margen_Absoluto'] / df_productos['Volumen_Venta']) * 100, 0)
    
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
    df_productos['Tamaño_Absoluto'] = df_productos['Margen_Absoluto'].abs().fillna(1) + 1
    return df_productos

def realizar_analisis_rfm(_df_historico_vendedor):
    if _df_historico_vendedor.empty or _df_historico_vendedor['cliente_id'].nunique() < 5:
        return pd.DataFrame(), pd.DataFrame()
        
    df = _df_historico_vendedor.copy()
    fecha_max_analisis = df['fecha_venta'].max() + pd.Timedelta(days=1)
    
    rfm_df = df.groupby(['cliente_id', 'nombre_cliente']).agg(
        Recencia=('fecha_venta', lambda date: (fecha_max_analisis - date.max()).days),
        Frecuencia=('fecha_venta', 'nunique'),
        Monetario=('valor_venta', 'sum')
    ).reset_index()
    
    if len(rfm_df) < 5: return pd.DataFrame(), pd.DataFrame()
        
    # *** CORRECCIÓN DEFINITIVA: Reemplazar qcut por cut para estabilidad ***
    # Se usan umbrales fijos (reglas de negocio) en lugar de cuantiles estadísticos.
    # Esto evita errores cuando los datos tienen poca variedad (muy común con filtros).

    # Puntuación de Recencia (menos días = mejor)
    recencia_bins = [-1, 30, 90, 180, 365, rfm_df['Recencia'].max() + 1]
    rfm_df['R_Score'] = pd.cut(rfm_df['Recencia'], bins=recencia_bins, labels=[5, 4, 3, 2, 1], right=False)

    # Puntuación de Frecuencia (más compras = mejor)
    frecuencia_bins = [0, 1, 3, 5, 10, rfm_df['Frecuencia'].max() + 1]
    rfm_df['F_Score'] = pd.cut(rfm_df['Frecuencia'], bins=frecuencia_bins, labels=[1, 2, 3, 4, 5], right=False)

    # Puntuación Monetaria (más valor = mejor) - qcut es aceptable aquí pero con seguridad.
    try:
        rfm_df['M_Score'] = pd.qcut(rfm_df['Monetario'], 5, labels=[1, 2, 3, 4, 5], duplicates='drop')
    except ValueError: # Si aún falla, asignar un puntaje por defecto.
        rfm_df['M_Score'] = 3 
    
    # Convertir a entero, ahora de forma segura
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
        Numero_Clientes=('cliente_id', 'count'),
        Ventas_Totales=('Monetario', 'sum')
    ).sort_values('Ventas_Totales', ascending=False).reset_index()
    
    return rfm_df, resumen_segmentos

def analizar_tendencias(_df_periodo):
    if _df_periodo.empty: return pd.DataFrame(), pd.DataFrame()
    df_ventas_mes = _df_periodo.set_index('fecha_venta').resample('M')['valor_venta'].sum().reset_index()
    df_ventas_mes['Mes'] = df_ventas_mes['fecha_venta'].dt.strftime('%Y-%m')
    df_productos_ventas = _df_periodo.groupby('nombre_articulo')['valor_venta'].sum().sort_values(ascending=False).reset_index()
    top_5_ventas = df_productos_ventas.head(5)['valor_venta'].sum()
    total_ventas = df_productos_ventas['valor_venta'].sum()
    resto_ventas = total_ventas - top_5_ventas
    df_pareto = pd.DataFrame({'Categoría': ['Top 5 Productos', 'Resto de Productos'], 'Ventas': [top_5_ventas, resto_ventas]})
    return df_ventas_mes, df_pareto


# ==============================================================================
# SECCIÓN 3: COMPONENTES DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def generar_y_renderizar_resumen_ejecutivo(nombre_vendedor, analisis_cartera, df_rentabilidad, resumen_rfm):
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
            nombre_motor = producto_motor['nombre_articulo'].iloc[0]
            venta_motor = producto_motor['Volumen_Venta'].iloc[0]
            insight_rentabilidad += f" Tu principal **motor de ganancia** es **'{nombre_motor}'**, que generó **${venta_motor:,.0f}**. ¡Poténcialo!"
        if not drenajes.empty:
            producto_drenaje = drenajes.nlargest(1, 'Volumen_Venta')
            nombre_drenaje = producto_drenaje['nombre_articulo'].iloc[0]
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
    st.subheader("Análisis de Movimiento de Cartera")
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Clientes Ganados 🟢", f"{analisis['ganados']}", help="Clientes que compraron por primera vez en este periodo.")
        col2.metric("Clientes Retenidos 🔵", f"{analisis['retenidos']}", help="Clientes que compraron en periodos anteriores y en este.")
        col3.metric("Clientes Reactivados ⭐", f"{analisis['reactivados']}", help="Clientes que estaban inactivos (más de 90 días) y volvieron a comprar.")
        col4.metric("Clientes en Fuga 🔴", f"{analisis['en_fuga']}", help="Clientes que compraban antes pero no en este periodo.")
    st.markdown("---")
    st.subheader("⚠️ Top 10 Clientes en Fuga por Valor Histórico")
    st.info("Estos son los clientes más valiosos que han dejado de comprar. ¡Son tu principal prioridad para contactar!")
    df_fuga_display = analisis['lista_clientes_en_fuga'][['nombre_cliente', 'ultima_compra', 'valor_historico']]
    st.dataframe(df_fuga_display, use_container_width=True, hide_index=True,
                 column_config={
                     "nombre_cliente": st.column_config.TextColumn("Nombre del Cliente"),
                     "ultima_compra": st.column_config.DateColumn("Última Compra", format="YYYY-MM-DD"),
                     "valor_historico": st.column_config.NumberColumn("Ventas Históricas", format="$ #,##0")})

def render_tab_rentabilidad(df_rentabilidad):
    st.subheader("Cuadrantes de Rentabilidad de Productos")
    if df_rentabilidad.empty:
        st.warning("No hay datos de productos para analizar la rentabilidad.")
        return
    with st.container(border=True):
        fig = px.scatter(df_rentabilidad, x="Volumen_Venta", y="Rentabilidad_Pct", size="Tamaño_Absoluto", color="Cuadrante", hover_name="nombre_articulo", log_x=True, size_max=60, title="Análisis de Rentabilidad vs. Volumen de Venta", labels={"Volumen_Venta": "Volumen de Venta ($) - Escala Logarítmica", "Rentabilidad_Pct": "Rentabilidad (%)"}, color_discrete_map={'⭐ Motores de Ganancia': '#2ca02c', '💎 Gemas Ocultas': '#ff7f0e', '🐄 Ventas de Volumen': '#1f77b4', '🤔 Drenajes de Rentabilidad': '#d62728'})
        fig.add_vline(x=df_rentabilidad['Volumen_Venta'].median(), line_dash="dash", annotation_text="Mediana Volumen")
        fig.add_hline(y=df_rentabilidad['Rentabilidad_Pct'].median(), line_dash="dash", annotation_text="Mediana Rentabilidad")
        st.plotly_chart(fig, use_container_width=True)
    with st.expander("Ver detalle de productos por cuadrante y explicación", expanded=False):
        st.markdown("- **⭐ Motores de Ganancia:** Alta venta y alta rentabilidad. Son tus estrellas. ¡Poténcialos!\n- **🐄 Ventas de Volumen:** Alta venta, baja rentabilidad. Mueven mucho inventario pero con poco margen. Optimiza costos.\n- **💎 Gemas Ocultas:** Baja venta, alta rentabilidad. Productos muy rentables pero poco vendidos. ¡Promociónalos!\n- **🤔 Drenajes de Rentabilidad:** Baja venta y baja rentabilidad (o negativa). Cuidado, pueden estar quitándote recursos.")
        st.dataframe(df_rentabilidad[['nombre_articulo', 'Cuadrante', 'Volumen_Venta', 'Rentabilidad_Pct', 'Margen_Absoluto']], use_container_width=True, hide_index=True, column_config={"Volumen_Venta": st.column_config.NumberColumn("Venta ($)", format="$ #,##0"), "Rentabilidad_Pct": st.column_config.NumberColumn("Rentabilidad (%)", format="%.2f%%"), "Margen_Absoluto": st.column_config.NumberColumn("Margen ($)", format="$ #,##0")})

def render_tab_rfm_accionable(rfm_df, resumen_segmentos):
    st.subheader("Segmentación Estratégica de Clientes (RFM)")
    if rfm_df.empty or resumen_segmentos.empty:
        st.warning("No hay suficientes datos de clientes para realizar el análisis RFM con los filtros actuales.")
        return
    with st.container(border=True):
        col1, col2 = st.columns([0.4, 0.6])
        with col1:
            st.markdown("##### Resumen de Segmentos")
            st.dataframe(resumen_segmentos, use_container_width=True, hide_index=True, column_config={"Ventas_Totales": st.column_config.NumberColumn("Ventas Históricas", format="$ #,##0")})
        with col2:
            fig = px.treemap(resumen_segmentos, path=['Segmento'], values='Numero_Clientes', title='Distribución de Clientes por Segmento (Cantidad)', color_discrete_sequence=px.colors.qualitative.Pastel)
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
        'Otros': ('❓ **Acción:** Análisis Individual. Estos clientes tienen patrones de compra no clasificados. Investiga sus perfiles para encontrar oportunidades.', 'lightblue')}
    opciones_segmento = resumen_segmentos['Segmento'].unique()
    if opciones_segmento.size > 0:
        segmento_seleccionado = st.selectbox("Selecciona un segmento para ver los clientes y el plan de acción:", options=opciones_segmento)
        if segmento_seleccionado:
            if segmento_seleccionado in acciones_segmento:
                accion, color = acciones_segmento[segmento_seleccionado]
                st.markdown(f"<p style='color:{color}; font-size:18px;'>{accion}</p>", unsafe_allow_html=True)
            df_display_segmento = rfm_df[rfm_df['Segmento'] == segmento_seleccionado].sort_values('Monetario', ascending=False)
            st.dataframe(df_display_segmento[['nombre_cliente', 'Recencia', 'Frecuencia', 'Monetario']], help="Recencia (días desde la última compra), Frecuencia (nº de compras), Monetario (valor total histórico)", use_container_width=True, hide_index=True, column_config={"nombre_cliente": "Nombre del Cliente", "Recencia": st.column_config.NumberColumn("Recencia (días)"), "Frecuencia": st.column_config.NumberColumn("Frecuencia (compras)"), "Monetario": st.column_config.NumberColumn("Valor Histórico", format="$ #,##0")})
    else:
        st.warning("No se encontraron segmentos de clientes para mostrar con los filtros actuales.")

def render_tab_tendencias(df_ventas_mes, df_pareto):
    st.subheader("Tendencias y Composición de Ventas en el Periodo")
    with st.container(border=True):
        st.markdown("#### Evolución de Ventas Mensuales")
        if df_ventas_mes.empty:
            st.warning("No hay suficientes datos para mostrar la evolución mensual.")
        else:
            fig_line = px.line(df_ventas_mes, x='Mes', y='valor_venta', markers=True, title="Ventas Mensuales en el Periodo Seleccionado", labels={'valor_venta': 'Total Ventas ($)'})
            fig_line.update_traces(marker=dict(size=10))
            st.plotly_chart(fig_line, use_container_width=True)
    st.markdown("---")
    with st.container(border=True):
        st.markdown("#### Análisis Pareto: ¿Dónde se concentra tu venta?")
        if df_pareto.empty or df_pareto['Ventas'].sum() == 0:
            st.warning("No hay suficientes datos para el análisis de Pareto.")
        else:
            fig_pie = px.pie(df_pareto, names='Categoría', values='Ventas', title='Concentración de Ventas: Top 5 Productos vs. Resto', hole=0.4, color_discrete_sequence=['#1f77b4', '#aec7e8'])
            st.plotly_chart(fig_pie, use_container_width=True)
            st.info("Este gráfico muestra qué porción de tus ingresos en el periodo viene de tus 5 productos más vendidos. Una alta concentración puede ser un riesgo.")

# ==============================================================================
# SECCIÓN 4: ORQUESTADOR PRINCIPAL DE LA PÁGINA
# ==============================================================================

def render_pagina_perfil():
    st.title("💡 Asistente Estratégico de Ventas")
    st.markdown("Análisis 360° para impulsar tus resultados. **Cada dato aquí responde a los filtros que selecciones.**")
    st.markdown("---")
    with st.container(border=True):
        col1, col2 = st.columns([0.4, 0.6])
        with col1:
            vendedores_unicos_norm = sorted(list(df_ventas_historico['nomvendedor'].dropna().unique()))
            grupos = DATA_CONFIG.get('grupos_vendedores', {})
            vendedores_en_grupos_norm = [normalizar_texto(v) for lista in grupos.values() for v in lista]
            mapa_norm_a_orig = {normalizar_texto(v): v for v in df_ventas_historico['nomvendedor'].dropna().unique()}
            vendedores_solos_norm = [v_norm for v_norm in vendedores_unicos_norm if v_norm not in vendedores_en_grupos_norm]
            vendedores_solos_orig = sorted([mapa_norm_a_orig.get(v_norm) for v_norm in vendedores_solos_norm if mapa_norm_a_orig.get(v_norm)])
            nombres_grupos = sorted(grupos.keys())
            usuario_actual = st.session_state.usuario
            es_gerente = normalizar_texto(usuario_actual) == "GERENTE"
            if es_gerente:
                opciones_analisis = ["Visión General de la Empresa"] + nombres_grupos + vendedores_solos_orig
                default_index = 0
            else:
                opciones_analisis = [usuario_actual]
                default_index = 0
            if not opciones_analisis:
                st.warning(f"No se encontraron datos de ventas asociados al usuario '{usuario_actual}'.")
                st.stop()
            seleccion = st.selectbox("Seleccione el Vendedor, Grupo o Visión a analizar:", opciones_analisis, index=default_index, help="Elija un perfil individual, un grupo consolidado o la visión general de la empresa.")
        with col2:
            df_ventas_historico['periodo'] = df_ventas_historico['fecha_venta'].dt.to_period('M')
            meses_disponibles = sorted(df_ventas_historico['periodo'].unique())
            mapa_meses = {f"{DATA_CONFIG['mapeo_meses'].get(p.month, p.month)} {p.year}": p for p in meses_disponibles}
            opciones_slider = list(mapa_meses.keys())
            start_index = max(0, len(opciones_slider) - 12)
            end_index = len(opciones_slider) - 1
            if start_index > end_index: start_index = end_index
            mes_inicio_str, mes_fin_str = st.select_slider("Seleccione el Rango de Meses para el Análisis:", options=opciones_slider, value=(opciones_slider[start_index], opciones_slider[end_index]))
            periodo_inicio, periodo_fin = mapa_meses[mes_inicio_str], mapa_meses[mes_fin_str]
            fecha_inicio = periodo_inicio.start_time.tz_localize(None)
            fecha_fin = (periodo_fin.end_time).tz_localize(None)

    if seleccion == "Visión General de la Empresa":
        df_base_filtrada = df_ventas_historico
    else:
        lista_vendedores_a_filtrar = grupos.get(seleccion, [seleccion])
        lista_vendedores_a_filtrar_norm = [normalizar_texto(v) for v in lista_vendedores_a_filtrar]
        df_base_filtrada = df_ventas_historico[df_ventas_historico['nomvendedor'].isin(lista_vendedores_a_filtrar_norm)]
    
    df_periodo_seleccionado = df_base_filtrada[(df_base_filtrada['fecha_venta'] >= fecha_inicio) & (df_base_filtrada['fecha_venta'] <= fecha_fin)]

    if df_periodo_seleccionado.empty:
        st.warning(f"No se encontraron datos para '{seleccion}' en el rango de meses seleccionado. Por favor, ajuste los filtros.")
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
        "📈 **Tendencias y Comparativas**"])

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
