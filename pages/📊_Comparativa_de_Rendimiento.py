# ==============================================================================
# SCRIPT PARA PÁGINA: 🎯 Análisis de Potencial en Marquillas Clave
# VERSIÓN: 2.8 (26 de Agosto, 2025)
# AUTOR: Gemini (Basado en el script principal y mejorado profesionalmente)
#
# DESCRIPCIÓN:
# Esta página proporciona un análisis profundo de venta cruzada para las
# marquillas de productos más estratégicas. Identifica qué clientes compran
# qué productos, segmentándolos para descubrir oportunidades de venta.
#
# MEJORAS (Versión 2.8):
# - AJUSTE CLAVE (Potencial de Venta Aterrizado): Se modifica drásticamente
#   el cálculo del KPI "Potencial Total". Ahora, el potencial se calcula
#   exclusivamente sobre los CLIENTES ACTIVOS en el mes y año seleccionados.
#   Esto responde a la necesidad de un indicador realista, que refleje la
#   oportunidad de venta cruzada inmediata sobre la cartera de clientes
#   que ya mostró actividad en el periodo. El cálculo sigue usando el ticket
#   promedio por transacción para simular la venta de "una unidad".
# ==============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re
import io
import unicodedata # Necesario para la función de normalización
from typing import Dict, Tuple

# ==============================================================================
# 1. FUNCIONES DE UTILIDAD Y ANÁLISIS DE DATOS
# ==============================================================================

def normalizar_texto(texto: str) -> str:
    """
    Convierte un texto a mayúsculas, elimina tildes y caracteres especiales.
    """
    if not isinstance(texto, str):
        return texto
    try:
        # NFD (Normalization Form D) descompone los caracteres en sus componentes base
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        # Convierte a mayúsculas y limpia otros caracteres
        return texto_sin_tildes.upper().replace('-', ' ').replace('_', ' ').replace('.', ' ').strip().replace('  ', ' ')
    except (TypeError, AttributeError):
        return texto

@st.cache_data
def filtrar_ventas_marquillas(_df_ventas_historicas: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra el historial de ventas para incluir solo transacciones de las
    marquillas clave y añade una columna con la marquilla identificada.
    """
    if _df_ventas_historicas.empty or 'nombre_articulo' not in _df_ventas_historicas.columns:
        return pd.DataFrame()

    regex_marquillas = '|'.join(MARQUILLAS_CLAVE)
    df_filtrado = _df_ventas_historicas[
        _df_ventas_historicas['nombre_articulo'].str.contains(regex_marquillas, case=False, na=False)
    ].copy()

    # Extrae la primera marquilla encontrada en el nombre del artículo.
    df_filtrado['marquilla'] = df_filtrado['nombre_articulo'].str.extract(f'({regex_marquillas})', flags=re.IGNORECASE)[0].str.upper()
    df_filtrado.dropna(subset=['marquilla'], inplace=True)
    return df_filtrado

@st.cache_data
def calcular_matriz_compra(_df_ventas_marquillas: pd.DataFrame) -> pd.DataFrame:
    """
    Crea una matriz que muestra qué clientes (filas) han comprado
    qué marquillas (columnas), marcada con 1 si hubo compra y 0 si no.
    """
    if _df_ventas_marquillas.empty:
        # Devuelve un DF vacío con la estructura esperada si no hay datos.
        return pd.DataFrame(columns=MARQUILLAS_CLAVE + ['conteo_marquillas'])

    matriz_compra_valor = pd.crosstab(
        index=_df_ventas_marquillas['nombre_cliente'],
        columns=_df_ventas_marquillas['marquilla'],
        values=_df_ventas_marquillas['valor_venta'],
        aggfunc='sum'
    ).fillna(0)

    # Convierte los valores de venta a un formato binario (1 si compró, 0 si no).
    matriz_binaria = (matriz_compra_valor > 0).astype(int)

    # Asegura que todas las marquillas clave existan como columnas, incluso si no se vendieron.
    for marquilla in MARQUILLAS_CLAVE:
        if marquilla not in matriz_binaria.columns:
            matriz_binaria[marquilla] = 0

    # Calcula cuántas marquillas únicas ha comprado cada cliente.
    matriz_binaria['conteo_marquillas'] = matriz_binaria[MARQUILLAS_CLAVE].sum(axis=1)

    return matriz_binaria.sort_values('conteo_marquillas', ascending=False)


@st.cache_data
def calcular_potencial_venta(_df_ventas_marquillas_historicas: pd.DataFrame, _df_clientes_activos: pd.DataFrame) -> Tuple[float, Dict]:
    """
    Calcula el potencial de venta si CADA CLIENTE ACTIVO del periodo
    comprara las marquillas que le faltan, basado en el TICKET PROMEDIO POR TRANSACCIÓN.
    """
    if _df_ventas_marquillas_historicas.empty or _df_clientes_activos.empty:
        return 0.0, {m: 0.0 for m in MARQUILLAS_CLAVE}

    # 1. Calcular el valor de venta PROMEDIO POR TRANSACCIÓN para cada marquilla
    #    usando todo el historial disponible para tener un ticket estable.
    ticket_promedio_por_transaccion = {}
    for marquilla in MARQUILLAS_CLAVE:
        df_marquilla = _df_ventas_marquillas_historicas[_df_ventas_marquillas_historicas['marquilla'] == marquilla]
        if not df_marquilla.empty:
            valor_promedio_transaccion = df_marquilla['valor_venta'].mean()
            ticket_promedio_por_transaccion[marquilla] = valor_promedio_transaccion
        else:
            ticket_promedio_por_transaccion[marquilla] = 0.0

    # 2. Crear la matriz de compra histórica para saber quién ha comprado qué en el pasado.
    matriz_compra_historica = calcular_matriz_compra(_df_ventas_marquillas_historicas)

    # 3. Calcular el potencial total sumando las oportunidades perdidas
    #    SOLO para los clientes que estuvieron activos en el periodo seleccionado.
    venta_potencial_total = 0.0
    potencial_por_marquilla = {m: 0.0 for m in MARQUILLAS_CLAVE}
    clientes_activos_unicos = _df_clientes_activos['nombre_cliente'].unique()

    for cliente in clientes_activos_unicos:
        for marquilla in MARQUILLAS_CLAVE:
            # Revisa si el cliente ha comprado la marquilla en su historial.
            ha_comprado_historicamente = cliente in matriz_compra_historica.index and matriz_compra_historica.loc[cliente, marquilla] == 1

            # Si el cliente activo NUNCA ha comprado la marquilla, se suma el potencial.
            if not ha_comprado_historicamente:
                potencial_cliente_marquilla = ticket_promedio_por_transaccion.get(marquilla, 0)
                venta_potencial_total += potencial_cliente_marquilla
                potencial_por_marquilla[marquilla] += potencial_cliente_marquilla

    return venta_potencial_total, potencial_por_marquilla

def generar_reporte_excel(segmentos: Dict[str, pd.DataFrame]) -> bytes:
    """
    Crea un archivo Excel en memoria con cada segmento de cliente en una hoja separada.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for nombre_segmento, df_segmento in segmentos.items():
            # Prepara el dataframe para la exportación
            if not df_segmento.empty:
                df_export = df_segmento.reset_index()[['nombre_cliente', 'conteo_marquillas']].copy()
                if 'marquillas_faltantes' in df_segmento.columns:
                    df_export['marquillas_faltantes'] = df_segmento['marquillas_faltantes'].values

                df_export.to_excel(writer, sheet_name=nombre_segmento, index=False)
                worksheet = writer.sheets[nombre_segmento]
                workbook = writer.book
                header_format = workbook.add_format({
                    'bold': True, 'text_wrap': True, 'valign': 'vcenter',
                    'fg_color': '#1F4E78', 'font_color': 'white', 'border': 1
                })
                # Escribir encabezados con formato
                for col_num, value in enumerate(df_export.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                # Ajustar ancho de columnas
                worksheet.set_column('A:A', 45) # Nombre Cliente
                worksheet.set_column('B:B', 18) # Conteo
                worksheet.set_column('C:C', 45) # Faltantes

    return output.getvalue()

# ==============================================================================
# 2. CONFIGURACIÓN Y ESTILO DE LA PÁGINA
# ==============================================================================

st.set_page_config(
    page_title="Análisis de Potencial | Marquillas Clave",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
<style>
    /* Estilo para los contenedores de métricas */
    div[data-testid="stMetric"] {
        background-color: #F0F2F6;
        border: 1px solid #E0E0E0;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    /* Estilo para el valor de la métrica */
    div[data-testid="stMetricValue"] {
        font-size: 2.5em;
        font-weight: bold;
        color: #1F4E78;
    }
    /* Estilo para el delta de la métrica */
    div[data-testid="stMetricDelta"] {
        font-size: 1.2em;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Las marquillas clave se definen aquí para ser consistentes en todo el script.
MARQUILLAS_CLAVE = sorted(['VINILTEX', 'KORAZA', 'ESTUCOMAS', 'VINILICO', 'PINTULUX'])

# ==============================================================================
# 3. RENDERIZADO DE LA PÁGINA Y COMPONENTES DE UI
# ==============================================================================

def render_pagina_analisis():
    """Función principal que dibuja todos los componentes de la página."""

    st.title("🎯 Análisis de Potencial en Marquillas Clave")
    st.markdown("""
    Esta sección ofrece una visión profunda del rendimiento y las oportunidades de **venta cruzada**
    para las 5 líneas de productos más importantes. Descubre el potencial oculto en tu cartera de clientes.
    """)

    # --- Verificación de Sesión Robusta ---
    if 'df_ventas' not in st.session_state or 'DATA_CONFIG' not in st.session_state:
        st.error("⚠️ No se han cargado los datos o la configuración necesaria.")
        st.warning("Esta página depende de los datos cargados en la aplicación principal. Por favor, ve a la página '🏠 Resumen Mensual', inicia sesión y asegúrate de que los datos se han cargado correctamente.")
        st.page_link("Resumen_Mensual.py", label="Ir a la página principal", icon="🏠")
        return # Detiene la ejecución para prevenir el error

    df_ventas_historicas_completo = st.session_state.df_ventas
    mapeo_meses = st.session_state.DATA_CONFIG.get('mapeo_meses', {i: str(i) for i in range(1, 13)})
    grupos_vendedores = st.session_state.DATA_CONFIG.get('grupos_vendedores', {})

    # --- FILTROS EN SIDEBAR ---
    st.sidebar.header("Filtros de Análisis")

    # Filtro de Periodo
    lista_anios = sorted(df_ventas_historicas_completo['anio'].unique(), reverse=True)
    anio_sel = st.sidebar.selectbox("Año", lista_anios, index=0, key="sb_anio_analisis")
    
    lista_meses_num = sorted(df_ventas_historicas_completo[df_ventas_historicas_completo['anio'] == anio_sel]['mes'].unique())
    if not lista_meses_num:
        st.warning(f"No hay datos de ventas para el año {anio_sel}.")
        return

    mes_sel_num = st.sidebar.selectbox(
        "Mes",
        options=lista_meses_num,
        format_func=lambda x: mapeo_meses.get(x, 'N/A'),
        index=len(lista_meses_num) - 1,
        key="sb_mes_analisis"
    )

    # Filtro de Vendedor/Grupo
    vendedores_en_grupos_flat = [normalizar_texto(v) for sublist in grupos_vendedores.values() for v in sublist]
    
    # --- INICIO DE LA CORRECCIÓN DEFINITIVA DEL TypeError ---
    # 1. Obtener la serie de vendedores que no están en los grupos predefinidos.
    vendedores_individuales_series = df_ventas_historicas_completo[
        ~df_ventas_historicas_completo['nomvendedor'].apply(normalizar_texto).isin(vendedores_en_grupos_flat)
    ]['nomvendedor']

    # 2. Limpiar la serie:
    #    - .dropna() elimina cualquier valor nulo (NaN), que causa el error de tipo.
    #    - .unique() obtiene los nombres únicos.
    #    - list() convierte el resultado en una lista.
    #    - sorted() ordena la lista de strings de forma segura.
    vendedores_individuales_limpios = sorted(list(vendedores_individuales_series.dropna().unique()))
    
    # 3. Crear la lista final y unificada de opciones para el filtro.
    opciones_filtro_orig = ["TODOS"] + sorted(list(grupos_vendedores.keys())) + vendedores_individuales_limpios
    # --- FIN DE LA CORRECCIÓN ---

    seleccion_vendedor_orig = st.sidebar.selectbox("Vendedor / Grupo", options=opciones_filtro_orig, key="sb_vendedor_analisis")


    # --- LÓGICA DE FILTRADO DE DATOS ---
    # Esta sección es clave. Crea un DataFrame 'df_ventas_filtrado' que será la base
    # para TODOS los cálculos e indicadores que se muestran en la página.
    seleccion_vendedor_norm = normalizar_texto(seleccion_vendedor_orig)
    
    if seleccion_vendedor_orig == "TODOS":
        df_ventas_filtrado = df_ventas_historicas_completo.copy()
    else:
        # Busca si la selección es un grupo
        es_grupo = False
        for nombre_grupo_orig, lista_vendedores_orig in grupos_vendedores.items():
            if normalizar_texto(nombre_grupo_orig) == seleccion_vendedor_norm:
                vendedores_del_grupo_norm = [normalizar_texto(v) for v in lista_vendedores_orig]
                df_ventas_filtrado = df_ventas_historicas_completo[
                    df_ventas_historicas_completo['nomvendedor'].apply(normalizar_texto).isin(vendedores_del_grupo_norm)
                ]
                es_grupo = True
                break
        
        # Si no es un grupo, es un vendedor individual
        if not es_grupo:
            df_ventas_filtrado = df_ventas_historicas_completo[
                df_ventas_historicas_completo['nomvendedor'].apply(normalizar_texto) == seleccion_vendedor_norm
            ]


    # --- CÁLCULOS PRINCIPALES ---
    with st.spinner("Procesando datos y calculando potencial..."):
        # 1. Filtra las ventas para incluir solo las marquillas clave, usando el DF ya filtrado por vendedor/grupo.
        df_ventas_marquillas = filtrar_ventas_marquillas(df_ventas_filtrado)

        # 2. Crea un DataFrame específico para el periodo seleccionado (mes y año).
        df_mes_actual = df_ventas_marquillas[
            (df_ventas_marquillas['anio'] == anio_sel) &
            (df_ventas_marquillas['mes'] == mes_sel_num)
        ]
        venta_mes_actual = df_mes_actual['valor_venta'].sum()

        # 3. Calcula métricas históricas para comparación (promedio).
        promedio_mensual = 0.0
        if not df_ventas_marquillas.empty:
            total_meses_con_venta = df_ventas_marquillas.groupby(['anio', 'mes']).ngroups
            venta_total_historica = df_ventas_marquillas['valor_venta'].sum()
            if total_meses_con_venta > 0:
                promedio_mensual = venta_total_historica / total_meses_con_venta

        # 4. Calcula el potencial de venta.
        #    ================================================================================
        #    ===> AJUSTE CRÍTICO: El potencial se calcula usando todo el historial de ventas
        #         de marquillas (para el ticket promedio) PERO se aplica solo a los clientes
        #         ACTIVOS del mes seleccionado (df_mes_actual).
        #    ================================================================================
        potencial_total, potencial_por_marquilla = calcular_potencial_venta(df_ventas_marquillas, df_mes_actual)

    # --- RENDERIZADO DE MÉTRICAS Y VISUALIZACIONES ---
    st.header(f"Indicadores para {mapeo_meses.get(mes_sel_num, '')} {anio_sel} | Foco: {seleccion_vendedor_orig}")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    col1.metric(
        label="📈 Venta del Mes (Marquillas Clave)",
        value=f"${venta_mes_actual:,.0f}",
        help="Suma de las ventas netas de las 5 marquillas clave en el periodo y para la selección actual."
    )
    col2.metric(
        label="📊 Promedio Mensual Histórico",
        value=f"${promedio_mensual:,.0f}",
        delta=f"{venta_mes_actual - promedio_mensual:,.0f} vs Promedio",
        help="Venta promedio mensual de las marquillas clave, calculado sobre todo el historial para la selección actual."
    )
    col3.metric(
        label="🚀 POTENCIAL TOTAL (Aterrizado)",
        value=f"${potencial_total:,.0f}",
        help="Estimación de venta adicional si CADA CLIENTE ACTIVO DEL MES comprara las marquillas que le faltan, basado en el ticket de compra promedio POR TRANSACCIÓN."
    )

    st.markdown("---")
    st.header("Análisis Visual del Desempeño y Potencial")

    col_g1, col_g2 = st.columns([0.5, 0.5])

    with col_g1:
        st.subheader("Rendimiento del Mes vs. Promedio")
        gauge_max_value = max(venta_mes_actual, promedio_mensual) * 1.5 if max(venta_mes_actual, promedio_mensual) > 0 else 1
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=venta_mes_actual,
            number={'prefix': "$", 'valueformat': ',.0f'},
            delta={'reference': promedio_mensual, 'relative': False, 'valueformat': ',.0f'},
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Venta del Mes vs. Promedio Histórico"},
            gauge={
                'axis': {'range': [None, gauge_max_value]},
                'steps': [
                    {'range': [0, promedio_mensual * 0.8], 'color': "#FFCBCB"},
                    {'range': [promedio_mensual * 0.8, promedio_mensual * 1.1], 'color': "#FFF3CB"},
                    {'range': [promedio_mensual * 1.1, gauge_max_value], 'color': '#D4EDDA'}],
                'threshold': {
                    'line': {'color': "#6c757d", 'width': 4},
                    'thickness': 0.85,
                    'value': promedio_mensual}
            }))
        fig_gauge.update_layout(height=400, margin=dict(t=50, b=40))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_g2:
        st.subheader("Oportunidad de Crecimiento por Marquilla")
        df_potencial = pd.DataFrame(list(potencial_por_marquilla.items()), columns=['Marquilla', 'Potencial'])
        df_potencial = df_potencial.sort_values('Potencial', ascending=False)

        fig_pie_potencial = px.pie(
            df_potencial,
            names='Marquilla',
            values='Potencial',
            title="Distribución del Potencial de Venta",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        fig_pie_potencial.update_traces(textinfo='percent+label', textposition='outside', pull=[0.05]*len(df_potencial))
        fig_pie_potencial.update_layout(height=400, showlegend=False, margin=dict(t=50, b=20, l=20, r=20))
        st.plotly_chart(fig_pie_potencial, use_container_width=True)

    # --- SEGMENTACIÓN DE CLIENTES ---
    st.markdown("---")
    st.header("Segmentación de Clientes por Portafolio")
    st.info("Utilice estas listas para enfocar sus esfuerzos de venta cruzada. Los clientes se clasifican según cuántas de las 5 marquillas clave han comprado en su historial.")

    matriz_clientes = calcular_matriz_compra(df_ventas_marquillas)

    # Lógica de segmentación
    campeones = matriz_clientes[matriz_clientes['conteo_marquillas'] == 5]
    alto_potencial = matriz_clientes[matriz_clientes['conteo_marquillas'] == 4]
    oportunidades = matriz_clientes[matriz_clientes['conteo_marquillas'] == 3]
    bajo_penetracion = matriz_clientes[matriz_clientes['conteo_marquillas'] < 3]

    def get_faltantes(row: pd.Series) -> str:
        return ", ".join([m for m in MARQUILLAS_CLAVE if row[m] == 0])

    if not alto_potencial.empty:
        alto_potencial = alto_potencial.copy()
        alto_potencial['marquillas_faltantes'] = alto_potencial.apply(get_faltantes, axis=1)
    if not oportunidades.empty:
        oportunidades = oportunidades.copy()
        oportunidades['marquillas_faltantes'] = oportunidades.apply(get_faltantes, axis=1)
    if not bajo_penetracion.empty:
        bajo_penetracion = bajo_penetracion.copy()
        bajo_penetracion['marquillas_faltantes'] = bajo_penetracion.apply(get_faltantes, axis=1)

    # Renderizado en Pestañas
    tab1, tab2, tab3, tab4 = st.tabs([
        f"🏆 Campeones ({len(campeones)})",
        f"🥇 Alto Potencial ({len(alto_potencial)})",
        f"🥈 Oportunidades Claras ({len(oportunidades)})",
        f"🥉 Baja Penetración ({len(bajo_penetracion)})"
    ])

    with tab1:
        st.subheader("Clientes que ya compran todo el portafolio clave.")
        st.dataframe(campeones.reset_index()[['nombre_cliente', 'conteo_marquillas']], use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Clientes a punto de completar el portafolio (Falta 1 marquilla).")
        st.dataframe(alto_potencial.reset_index()[['nombre_cliente', 'conteo_marquillas', 'marquillas_faltantes']], use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Clientes con potencial claro de crecimiento (Faltan 2 marquillas).")
        st.dataframe(oportunidades.reset_index()[['nombre_cliente', 'conteo_marquillas', 'marquillas_faltantes']], use_container_width=True, hide_index=True)

    with tab4:
        st.subheader("Clientes con la mayor oportunidad de venta cruzada (Faltan 3 o más).")
        st.dataframe(bajo_penetracion.reset_index()[['nombre_cliente', 'conteo_marquillas', 'marquillas_faltantes']], use_container_width=True, hide_index=True)

    # --- Botón de Descarga ---
    st.markdown("---")
    st.subheader("📥 Descargar Segmentación de Clientes")
    st.info("Genere un archivo Excel con la lista de clientes en cada uno de los segmentos definidos anteriormente.")

    segmentos_dict = {
        "Campeones": campeones,
        "Alto_Potencial": alto_potencial,
        "Oportunidades_Claras": oportunidades,
        "Baja_Penetracion": bajo_penetracion
    }
    excel_file = generar_reporte_excel(segmentos_dict)

    st.download_button(
        label="📥 Descargar Reporte de Segmentos (Excel)",
        data=excel_file,
        file_name=f"Segmentacion_Marquillas_{seleccion_vendedor_orig}_{anio_sel}_{mes_sel_num}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# ==============================================================================
# 4. PUNTO DE ENTRADA DE LA APLICACIÓN
# ==============================================================================

if __name__ == '__main__':
    # Verifica si el usuario está autenticado (estado manejado por Resumen_Mensual.py)
    if 'autenticado' in st.session_state and st.session_state.autenticado:
        render_pagina_analisis()
    else:
        # Muestra una página de acceso restringido si no está autenticado.
        st.title("🔒 Acceso Restringido")
        st.image("https://raw.githubusercontent.com/DiegoMao2021/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", width=300)
        st.warning("Por favor, inicie sesión desde la página principal para acceder a este análisis.")
        st.info("Esta es una página de análisis avanzado que requiere que los datos maestros sean cargados primero en la aplicación principal.")
        st.page_link("Resumen_Mensual.py", label="Ir a la página de inicio de sesión", icon="🏠")
