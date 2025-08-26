# ==============================================================================
# SCRIPT PARA PÁGINA: 🎯 Análisis de Potencial en Marquillas Clave
# VERSIÓN: 1.1 (26 de Agosto, 2025)
# AUTOR: Gemini (Basado en el script principal)
# CORRECCIÓN: Se añade la importación del módulo 're' para solucionar NameError.
# DESCRIPCIÓN: Esta página se enfoca exclusivamente en el análisis de las 5
#              marquillas clave de la compañía. Calcula la venta actual, el
#              promedio histórico y proyecta el potencial de venta máximo
#              (punto de quiebre) si todos los clientes compraran el portafolio
#              completo de marquillas.
# ==============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re # <-- ESTA ES LA LÍNEA QUE SOLUCIONA EL ERROR

# ==============================================================================
# 1. CONFIGURACIÓN Y ESTILO DE LA PÁGINA
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
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    /* Estilo para el valor de la métrica */
    div[data-testid="stMetricValue"] {
        font-size: 2.5em;
        font-weight: bold;
    }
    /* Estilo para el delta de la métrica */
    div[data-testid="stMetricDelta"] {
        font-size: 1.2em;
        font-weight: 600;
        color: #28a745 !important; /* Verde para el delta positivo */
    }
</style>
""", unsafe_allow_html=True)

# Las marquillas clave definidas en el script principal
MARQUILLAS_CLAVE = ['VINILTEX', 'KORAZA', 'ESTUCOMAS', 'VINILICO', 'PINTULUX']

# ==============================================================================
# 2. FUNCIONES DE CÁLCULO Y ANÁLISIS
# ==============================================================================

@st.cache_data
def filtrar_ventas_marquillas(_df_ventas_historicas):
    """
    Filtra el historial de ventas para incluir solo transacciones de las
    marquillas clave y añade una columna con la marquilla identificada.
    """
    # Crear una expresión regex para buscar cualquiera de las marquillas
    regex_marquillas = '|'.join(MARQUILLAS_CLAVE)
    
    # Filtrar el DataFrame
    df_filtrado = _df_ventas_historicas[
        _df_ventas_historicas['nombre_articulo'].str.contains(regex_marquillas, case=False, na=False)
    ].copy()

    # Extraer la marquilla específica para cada venta
    # Esto asegura que si un nombre de artículo contiene dos (poco probable), se tome la primera
    df_filtrado['marquilla'] = df_filtrado['nombre_articulo'].str.extract(f'({regex_marquillas})', flags=re.IGNORECASE)[0].str.upper()
    df_filtrado.dropna(subset=['marquilla'], inplace=True)
    
    return df_filtrado

@st.cache_data
def calcular_matriz_compra(_df_ventas_marquillas):
    """
    Crea una matriz que muestra qué clientes han comprado qué marquillas.
    Retorna la matriz y el número de marquillas compradas por cliente.
    """
    if _df_ventas_marquillas.empty:
        return pd.DataFrame(), pd.Series(dtype=int)

    matriz = pd.crosstab(
        index=_df_ventas_marquillas['nombre_cliente'],
        columns=_df_ventas_marquillas['marquilla'],
        values=_df_ventas_marquillas['valor_venta'],
        aggfunc='sum'
    ).fillna(0)

    # Convertir a binario (1 si compró, 0 si no)
    matriz_binaria = (matriz > 0).astype(int)
    
    # Asegurarse de que todas las marquillas clave estén como columnas
    for marquilla in MARQUILLAS_CLAVE:
        if marquilla not in matriz_binaria.columns:
            matriz_binaria[marquilla] = 0
            
    # Contar cuántas marquillas ha comprado cada cliente
    matriz_binaria['conteo_marquillas'] = matriz_binaria[MARQUILLAS_CLAVE].sum(axis=1)
    
    return matriz_binaria.sort_values('conteo_marquillas', ascending=False)


@st.cache_data
def calcular_potencial_venta(_df_ventas_marquillas, _df_todos_los_clientes):
    """
    Calcula el "punto de quiebre": el potencial de venta si cada cliente
    comprara las marquillas que le faltan.
    """
    if _df_ventas_marquillas.empty or _df_todos_los_clientes.empty:
        return 0, {}

    # 1. Calcular el valor de compra promedio por marquilla para los clientes que SÍ la compran
    ticket_promedio_por_marquilla = {}
    for marquilla in MARQUILLAS_CLAVE:
        df_marquilla_especifica = _df_ventas_marquillas[_df_ventas_marquillas['marquilla'] == marquilla]
        if not df_marquilla_especifica.empty:
            # Agrupar por cliente para obtener el total que cada uno ha gastado en la marquilla
            gasto_por_cliente = df_marquilla_especifica.groupby('nombre_cliente')['valor_venta'].sum()
            ticket_promedio = gasto_por_cliente.mean()
            ticket_promedio_por_marquilla[marquilla] = ticket_promedio
        else:
            ticket_promedio_por_marquilla[marquilla] = 0 # Si una marquilla nunca se ha vendido

    # 2. Crear la matriz de compra
    matriz_compra = calcular_matriz_compra(_df_ventas_marquillas)[0]

    # 3. Calcular el potencial
    venta_potencial_total = 0
    potencial_por_marquilla = {m: 0 for m in MARQUILLAS_CLAVE}
    
    # Iterar sobre todos los clientes únicos de la empresa
    for cliente in _df_todos_los_clientes['nombre_cliente'].unique():
        for marquilla in MARQUILLAS_CLAVE:
            # Verificar si el cliente ha comprado esta marquilla
            compro = False
            if cliente in matriz_compra.index and matriz_compra.loc[cliente, marquilla] == 1:
                compro = True
            
            # Si no la ha comprado, es una oportunidad
            if not compro:
                potencial = ticket_promedio_por_marquilla.get(marquilla, 0)
                venta_potencial_total += potencial
                potencial_por_marquilla[marquilla] += potencial

    return venta_potencial_total, potencial_por_marquilla

# ==============================================================================
# 3. RENDERIZADO DE LA PÁGINA
# ==============================================================================

def render_pagina_analisis():
    """Función principal que dibuja todos los componentes de la página."""
    
    st.title("🎯 Análisis de Potencial en Marquillas Clave")
    st.markdown("Esta sección ofrece una visión profunda del rendimiento y las oportunidades de venta cruzada para las **5 líneas de productos más importantes**. Descubre el potencial oculto en tu cartera de clientes.")
    
    # --- VERIFICACIÓN DE DATOS ---
    if 'df_ventas' not in st.session_state or st.session_state.df_ventas.empty:
        st.error("No se han cargado los datos de ventas. Por favor, ve a la página principal 'Resumen Mensual' y carga los datos primero.")
        st.warning("Esta página depende de los datos cargados en la sesión principal de la aplicación.")
        return

    df_ventas_historicas = st.session_state.df_ventas

    # --- FILTROS DE PERIODO ---
    st.sidebar.header("Filtros de Periodo")
    lista_anios = sorted(df_ventas_historicas['anio'].unique(), reverse=True)
    anio_sel = st.sidebar.selectbox(
        "Elija el Año", 
        lista_anios, 
        index=0, 
        key="sb_anio_analisis"
    )
    
    lista_meses_num = sorted(df_ventas_historicas[df_ventas_historicas['anio'] == anio_sel]['mes'].unique())
    if not lista_meses_num:
        st.warning(f"No hay datos de ventas para el año {anio_sel}.")
        return

    # Usar el mapeo de meses desde el session_state si existe, si no, un fallback
    mapeo_meses = st.session_state.get('DATA_CONFIG', {}).get('mapeo_meses', {i: str(i) for i in range(1, 13)})
    mes_sel_num = st.sidebar.selectbox(
        "Elija el Mes", 
        options=lista_meses_num, 
        format_func=lambda x: mapeo_meses.get(x, 'N/A'), 
        index=len(lista_meses_num) - 1, 
        key="sb_mes_analisis"
    )

    # --- CÁLCULOS PRINCIPALES ---
    with st.spinner("Analizando el universo de ventas..."):
        df_ventas_marquillas = filtrar_ventas_marquillas(df_ventas_historicas)
        
        # Datos del mes actual
        df_mes_actual = df_ventas_marquillas[
            (df_ventas_marquillas['anio'] == anio_sel) & 
            (df_ventas_marquillas['mes'] == mes_sel_num)
        ]
        venta_mes_actual = df_mes_actual['valor_venta'].sum()
        
        # Promedio mensual histórico (incluyendo mes actual)
        total_meses_con_venta = df_ventas_marquillas.groupby(['anio', 'mes']).ngroups
        venta_total_historica = df_ventas_marquillas['valor_venta'].sum()
        promedio_mensual = venta_total_historica / total_meses_con_venta if total_meses_con_venta > 0 else 0

        # Potencial de Venta (Punto de Quiebre)
        potencial_total, potencial_por_marquilla = calcular_potencial_venta(df_ventas_marquillas, df_ventas_historicas)
        
    # --- VISUALIZACIÓN DE MÉTRICAS CLAVE ---
    st.header(f"Indicadores para {mapeo_meses.get(mes_sel_num, '')} {anio_sel}")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="📈 Venta del Mes Actual (Marquillas)",
            value=f"${venta_mes_actual:,.0f}",
            help="Suma de las ventas netas de las 5 marquillas clave en el periodo seleccionado."
        )
    with col2:
        st.metric(
            label="📊 Promedio Mensual Histórico",
            value=f"${promedio_mensual:,.0f}",
            delta=f"{(venta_mes_actual - promedio_mensual):,.0f} vs Promedio",
            help="Venta promedio mensual de las marquillas clave, calculado sobre todo el historial de datos."
        )
    with col3:
        st.metric(
            label="🚀 POTENCIAL TOTAL (Punto de Quiebre)",
            value=f"${potencial_total:,.0f}",
            help="Estimación de la venta adicional si cada cliente activo comprara las marquillas que le faltan, basado en el ticket promedio por marquilla."
        )

    st.markdown("---")
    
    # --- GRÁFICOS DE ANÁLISIS ---
    
    st.header("Análisis Visual del Potencial")
    
    col_g1, col_g2 = st.columns([0.6, 0.4])
    
    with col_g1:
        st.subheader("Comparativa: Realidad vs. Potencial")
        
        fig_comparativa = go.Figure(data=[
            go.Bar(name='Venta Mes Actual', x=['Análisis'], y=[venta_mes_actual], text=f"${venta_mes_actual/1e6:.1f}M", textposition='auto'),
            go.Bar(name='Promedio Mensual', x=['Análisis'], y=[promedio_mensual], text=f"${promedio_mensual/1e6:.1f}M", textposition='auto'),
            go.Bar(name='Potencial Adicional', x=['Análisis'], y=[potencial_total], text=f"${potencial_total/1e6:.1f}M", textposition='auto')
        ])
        fig_comparativa.update_layout(
            barmode='group',
            title_text='Venta Actual vs. Oportunidad de Crecimiento',
            yaxis_title='Valor (COP)',
            legend_title_text='Métricas',
            height=400
        )
        st.plotly_chart(fig_comparativa, use_container_width=True)

    with col_g2:
        st.subheader("Oportunidad por Marquilla")
        df_potencial = pd.DataFrame(list(potencial_por_marquilla.items()), columns=['Marquilla', 'Potencial'])
        df_potencial = df_potencial.sort_values('Potencial', ascending=False)
        
        fig_pie_potencial = px.pie(
            df_potencial, 
            names='Marquilla', 
            values='Potencial', 
            title="Distribución del Potencial de Venta",
            hole=0.4
        )
        fig_pie_potencial.update_traces(textinfo='percent+label', textposition='outside')
        fig_pie_potencial.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_pie_potencial, use_container_width=True)

    # --- ANÁLISIS Y SEGMENTACIÓN DE CLIENTES ---
    st.markdown("---")
    st.header("Segmentación de Clientes por Portafolio de Marquillas")
    st.info("Utilice estas listas para enfocar sus esfuerzos de venta cruzada en los clientes con mayor potencial.")

    matriz_clientes, _ = calcular_matriz_compra(df_ventas_marquillas)

    # Definir los segmentos
    campeones = matriz_clientes[matriz_clientes['conteo_marquillas'] == 5]
    alto_potencial = matriz_clientes[matriz_clientes['conteo_marquillas'] == 4]
    oportunidades = matriz_clientes[matriz_clientes['conteo_marquillas'] == 3]
    bajo_penetracion = matriz_clientes[matriz_clientes['conteo_marquillas'] < 3]

    # Función para identificar las marquillas faltantes
    def get_faltantes(row):
        return ", ".join([m for m in MARQUILLAS_CLAVE if row[m] == 0])

    tab1, tab2, tab3, tab4 = st.tabs([
        f"🏆 Campeones ({len(campeones)})",
        f"🥇 Alto Potencial ({len(alto_potencial)})",
        f"🥈 Oportunidades Claras ({len(oportunidades)})",
        f"🥉 Baja Penetración ({len(bajo_penetracion)})"
    ])

    with tab1:
        st.subheader("Clientes que ya compran todo el portafolio clave.")
        if campeones.empty:
            st.info("Aún no hay clientes que hayan comprado las 5 marquillas clave.")
        else:
            st.dataframe(campeones.reset_index()[['nombre_cliente', 'conteo_marquillas']], use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Clientes a punto de completar el portafolio (Falta 1 marquilla).")
        if alto_potencial.empty:
            st.info("No hay clientes en este segmento.")
        else:
            alto_potencial['marquilla_faltante'] = alto_potencial.apply(get_faltantes, axis=1)
            st.dataframe(alto_potencial.reset_index()[['nombre_cliente', 'conteo_marquillas', 'marquilla_faltante']], use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Clientes con potencial claro de crecimiento (Faltan 2 marquillas).")
        if oportunidades.empty:
            st.info("No hay clientes en este segmento.")
        else:
            oportunidades['marquillas_faltantes'] = oportunidades.apply(get_faltantes, axis=1)
            st.dataframe(oportunidades.reset_index()[['nombre_cliente', 'conteo_marquillas', 'marquillas_faltantes']], use_container_width=True, hide_index=True)
            
    with tab4:
        st.subheader("Clientes con la mayor oportunidad de venta cruzada (Faltan 3 o más).")
        if bajo_penetracion.empty:
            st.info("No hay clientes en este segmento.")
        else:
            bajo_penetracion['marquillas_faltantes'] = bajo_penetracion.apply(get_faltantes, axis=1)
            st.dataframe(bajo_penetracion.reset_index()[['nombre_cliente', 'conteo_marquillas', 'marquillas_faltantes']], use_container_width=True, hide_index=True)


# --- Punto de entrada del script ---
if __name__ == '__main__':
    # Verificar autenticación
    if 'autenticado' in st.session_state and st.session_state.autenticado:
        render_pagina_analisis()
    else:
        st.title("Acceso Restringido")
        st.image("https://raw.githubusercontent.com/DiegoMao2021/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", width=300)
        st.warning("🔒 Por favor, inicie sesión desde la página principal para acceder a este análisis.")
        st.info("Esta es una página de análisis avanzado que requiere que los datos maestros sean cargados primero.")
        st.page_link("Resumen_Mensual.py", label="Ir a la página de inicio de sesión", icon="🏠")
