# ==============================================================================
# SCRIPT PARA: pages/2_📈_Presupuestos.py
# VERSIÓN: 1.0
# FECHA: 17 de Julio, 2025
# DESCRIPCIÓN: Página dedicada a la generación y análisis de presupuestos de
#              venta dinámicos. Utiliza una metodología ponderada (50/50)
#              entre el historial estacional y la tendencia reciente para
#              calcular metas justas, realistas y automáticas.
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Gestión de Presupuestos",
    page_icon="📈",
    layout="wide"
)

# ==============================================================================
# 1. FUNCIÓN CENTRAL DE CÁLCULO DE PRESUPUESTO DINÁMICO
# ==============================================================================
def calcular_presupuesto_dinamico(df_ventas_historicas, nomvendedor, anio_actual, mes_actual, config):
    """
    Calcula un presupuesto de ventas dinámico y ponderado, devolviendo todos los componentes del cálculo.

    Args:
        df_ventas_historicas (pd.DataFrame): El DataFrame completo con todas las ventas.
        nomvendedor (str): El nombre normalizado del vendedor/grupo.
        anio_actual (int): El año para el cual se establece el presupuesto.
        mes_actual (int): El mes para el cual se establece el presupuesto.
        config (dict): Diccionario con pesos y factor de crecimiento.

    Returns:
        dict: Un diccionario con el presupuesto final y todos sus componentes para explicación.
    """
    # --- 1. Definir Periodos de Tiempo ---
    anio_anterior = anio_actual - 1
    fecha_base = datetime(anio_actual, mes_actual, 1)

    # Periodo Histórico (Estacional): 3 meses alrededor del mes objetivo, pero del año anterior.
    # Ejemplo para Julio: [Junio, Julio, Agosto] del año anterior.
    meses_historicos = [(fecha_base - relativedelta(months=1)).month, mes_actual, (fecha_base + relativedelta(months=1)).month]
    anio_historico = anio_anterior

    # Periodo Reciente (Tendencia): 3 meses justo antes del mes objetivo.
    # Ejemplo para Julio: [Abril, Mayo, Junio] del año actual.
    meses_recientes = [(fecha_base - relativedelta(months=3)).month, (fecha_base - relativedelta(months=2)).month, (fecha_base - relativedelta(months=1)).month]
    anio_reciente_inicio = (fecha_base - relativedelta(months=3)).year
    anio_reciente_fin = (fecha_base - relativedelta(months=1)).year
    
    # --- 2. Filtrar el DataFrame para el vendedor/grupo específico ---
    filtro_ventas_netas = 'FACTURA|NOTA.*CREDITO'
    df_vendedor = df_ventas_historicas[
        (df_ventas_historicas['nomvendedor'] == nomvendedor) &
        (df_ventas_historicas['TipoDocumento'].str.contains(filtro_ventas_netas, na=False, case=False, regex=True))
    ]

    if df_vendedor.empty:
        return {'presupuesto_final': 0, 'base_historica': 0, 'tendencia_reciente': 0, 'sin_historial': True}

    # --- 3. Calcular Línea Base Histórica ---
    ventas_historicas = df_vendedor[
        (df_vendedor['anio'] == anio_historico) &
        (df_vendedor['mes'].isin(meses_historicos))
    ]
    # Usamos el promedio de la suma de ventas de cada mes para ser más justos
    base_historica_promedio = ventas_historicas.groupby('mes')['valor_venta'].sum().mean()
    if pd.isna(base_historica_promedio) or base_historica_promedio < 0:
        base_historica_promedio = 0

    # --- 4. Calcular Factor de Tendencia Reciente ---
    ventas_recientes = df_vendedor[
        (df_vendedor['fecha_venta'] >= (fecha_base - relativedelta(months=3))) &
        (df_vendedor['fecha_venta'] < fecha_base)
    ]
    tendencia_reciente_promedio = ventas_recientes.groupby(pd.Grouper(key='fecha_venta', freq='M'))['valor_venta'].sum().mean()
    if pd.isna(tendencia_reciente_promedio) or tendencia_reciente_promedio < 0:
        tendencia_reciente_promedio = 0

    # --- 5. Ponderar, aplicar factor de crecimiento y devolver resultados ---
    if base_historica_promedio == 0 and tendencia_reciente_promedio == 0:
        return {'presupuesto_final': 0, 'base_historica': 0, 'tendencia_reciente': 0, 'sin_historial': True}

    # Si falta uno de los dos componentes, se le da todo el peso al que sí existe.
    if base_historica_promedio == 0:
        presupuesto_base = tendencia_reciente_promedio
    elif tendencia_reciente_promedio == 0:
        presupuesto_base = base_historica_promedio
    else:
        presupuesto_base = (base_historica_promedio * config['pesos']['historia']) + \
                           (tendencia_reciente_promedio * config['pesos']['tendencia'])

    presupuesto_final = presupuesto_base * (1 + config['factor_crecimiento'])

    return {
        'presupuesto_final': presupuesto_final,
        'base_historica': base_historica_promedio,
        'tendencia_reciente': tendencia_reciente_promedio,
        'componente_historico_ponderado': base_historica_promedio * config['pesos']['historia'],
        'componente_reciente_ponderado': tendencia_reciente_promedio * config['pesos']['tendencia'],
        'sin_historial': False
    }

# ==============================================================================
# 2. LÓGICA PRINCIPAL DE LA PÁGINA
# ==============================================================================
def render_presupuestos_page():
    st.title("📈 Gestión de Presupuestos Dinámicos")
    st.markdown("""
    Esta herramienta calcula automáticamente las metas de venta para cada vendedor o grupo.
    La metodología se basa en un **análisis ponderado (50/50)** para crear objetivos justos y alcanzables:
    - **50% Componente Histórico:** El rendimiento promedio en el mismo periodo del año anterior (considerando estacionalidad).
    - **50% Componente de Tendencia:** El rendimiento promedio en los últimos 3 meses (considerando el impulso actual).
    - **+8% Factor de Crecimiento:** Un incremento sobre la base calculada para impulsar la mejora continua.
    """)

    # --- Cargar datos desde st.session_state (poblado por la página principal) ---
    if 'df_ventas' not in st.session_state or st.session_state.df_ventas.empty:
        st.error("🚨 ¡Error de datos! Por favor, ve a la página '🏠 Resumen Mensual' primero para cargar los datos.")
        st.stop()
        
    df_ventas_historicas = st.session_state.df_ventas
    APP_CONFIG = st.session_state.APP_CONFIG
    DATA_CONFIG = st.session_state.DATA_CONFIG

    # --- Barra Lateral de Filtros ---
    st.sidebar.header("Filtros de Cálculo")
    lista_anios = sorted(df_ventas_historicas['anio'].unique(), reverse=True)
    anio_sel = st.sidebar.selectbox("Seleccione el Año para el Presupuesto", lista_anios, index=0)

    lista_meses_num = sorted(df_ventas_historicas[df_ventas_historicas['anio'] == anio_sel]['mes'].unique())
    mes_sel_num = st.sidebar.selectbox("Seleccione el Mes para el Presupuesto", options=range(1, 13), format_func=lambda x: DATA_CONFIG['mapeo_meses'].get(x, 'N/A'), index=datetime.now().month-1)

    # --- Preparar datos y calcular presupuestos para todos ---
    # Normalizar nombres de vendedores y grupos para consistencia
    vendedores_grupos_norm = set()
    for grupo, lista_vendedores in DATA_CONFIG['grupos_vendedores'].items():
        vendedores_grupos_norm.add(grupo.upper().replace('-', ' ').strip())
    
    vendedores_individuales_norm = set(df_ventas_historicas['nomvendedor'].unique())
    todos_los_vendedores = sorted(list(vendedores_grupos_norm.union(vendedores_individuales_norm)))

    config_calculo = {
        "pesos": {"historia": 0.50, "tendencia": 0.50},
        "factor_crecimiento": 0.08
    }

    presupuestos_calculados = []
    with st.spinner(f"Calculando presupuestos para {DATA_CONFIG['mapeo_meses'][mes_sel_num]} {anio_sel}..."):
        # Mapeo de vendedores a sus grupos
        mapa_vendedor_a_grupo = {}
        for grupo, lista in DATA_CONFIG['grupos_vendedores'].items():
            for vendedor in lista:
                mapa_vendedor_a_grupo[vendedor.upper().replace('-', ' ').strip()] = grupo.upper().replace('-', ' ').strip()
        
        # Agrupar ventas individuales bajo sus nombres de grupo
        df_ventas_historicas['nomvendedor_grupo'] = df_ventas_historicas['nomvendedor'].map(mapa_vendedor_a_grupo).fillna(df_ventas_historicas['nomvendedor'])

        # Calcular para todos los vendedores y grupos
        nombres_unicos = sorted(list(df_ventas_historicas['nomvendedor_grupo'].unique()))
        
        for nombre in nombres_unicos:
            resultado = calcular_presupuesto_dinamico(df_ventas_historicas, nombre, anio_sel, mes_sel_num, config_calculo)
            resultado['Vendedor/Grupo'] = nombre
            # Traer el presupuesto de cartera desde la configuración original
            codigo = next((k for k,v in DATA_CONFIG['presupuestos'].items() if DATA_CONFIG['presupuestos'][k].get('nomvendedor', '').upper() == nombre), None)
            if nombre in DATA_CONFIG['grupos_vendedores']:
                # Sumar presupuestos de cartera para los grupos
                presupuesto_cartera_grupo = 0
                for vendedor_del_grupo in DATA_CONFIG['grupos_vendedores'][nombre]:
                    v_codigo = next((k for k,v in DATA_CONFIG['presupuestos'].items() if DATA_CONFIG['presupuestos'][k].get('nomvendedor','').upper() == vendedor_del_grupo.upper()), None)
                    if v_codigo:
                        presupuesto_cartera_grupo += DATA_CONFIG['presupuestos'][v_codigo].get('presupuestocartera', 0)
                resultado['Presupuesto Cartera'] = presupuesto_cartera_grupo
            elif codigo:
                 resultado['Presupuesto Cartera'] = DATA_CONFIG['presupuestos'][codigo].get('presupuestocartera', 0)
            else:
                 resultado['Presupuesto Cartera'] = 0

            presupuestos_calculados.append(resultado)

    df_presupuestos = pd.DataFrame(presupuestos_calculados)

    # --- Filtro de vista en la página principal ---
    filtro_vista = st.radio(
        "Filtrar Vista",
        ["Todos", "✅ Con Historial", "❓ Nuevos / Sin Datos"],
        horizontal=True, key="filtro_vista_presupuesto"
    )

    if filtro_vista == "✅ Con Historial":
        df_vista = df_presupuestos[df_presupuestos['sin_historial'] == False].copy()
    elif filtro_vista == "❓ Nuevos / Sin Datos":
        df_vista = df_presupuestos[df_presupuestos['sin_historial'] == True].copy()
    else:
        df_vista = df_presupuestos.copy()

    st.markdown("---")

    # --- Resumen de Métricas Clave ---
    total_presupuesto_propuesto = df_vista[df_vista['sin_historial'] == False]['presupuesto_final'].sum()
    vendedores_con_historial = len(df_presupuestos[df_presupuestos['sin_historial'] == False])
    vendedores_sin_historial = len(df_presupuestos[df_presupuestos['sin_historial'] == True])

    st.header("Resumen General de Presupuestos")
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Presupuesto Total Propuesto", f"${total_presupuesto_propuesto:,.0f}", help="Suma de las metas de venta para todos los vendedores con historial.")
    col2.metric("👥 Vendedores con Presupuesto", str(vendedores_con_historial), help="Cantidad de vendedores o grupos con suficientes datos para un cálculo automático.")
    col3.metric("❓ Vendedores a Asignar", str(vendedores_sin_historial), "⚠️ Requieren asignación manual de meta.", delta_color="inverse")

    # --- Tabla Principal de Presupuestos ---
    st.subheader("Desglose de Presupuestos Propuestos")
    st.dataframe(
        df_vista,
        column_config={
            "Vendedor/Grupo": st.column_config.TextColumn("Vendedor / Grupo", width="medium"),
            "presupuesto_final": st.column_config.NumberColumn("Meta de Venta Propuesta 💵", format="$ %d"),
            "base_historica": st.column_config.NumberColumn("Base Histórica (Estacional) 🗓️", format="$ %d"),
            "tendencia_reciente": st.column_config.NumberColumn("Tendencia Reciente (Impulso) 🚀", format="$ %d"),
            "Presupuesto Cartera": st.column_config.NumberColumn("Meta de Cartera 🏦", format="$ %d"),
            "sin_historial": st.column_config.CheckboxColumn("¿Sin Historial?"),
        },
        use_container_width=True,
        hide_index=True
    )
    st.caption("Pase el cursor sobre los encabezados para más detalles. Haga clic en la columna para ordenar.")

    # --- Sección de Análisis Individual y Explicación ---
    st.markdown("---")
    st.header("Análisis y Justificación por Vendedor")
    st.info("Expanda cada sección para ver el porqué detrás de cada cifra y entender el rendimiento individual.")

    for index, row in df_vista.iterrows():
        nombre = row['Vendedor/Grupo']
        with st.expander(f"**{nombre}** | Meta Propuesta: **${row['presupuesto_final']:,.0f}**"):
            if row['sin_historial']:
                st.warning(f"**No hay suficientes datos históricos para {nombre}.** Se requiere una asignación de meta manual.")
                st.markdown("Posibles razones:")
                st.markdown("- Es un vendedor o grupo nuevo.")
                st.markdown("- No se registraron ventas en los periodos de análisis (últimos 3 meses y mismo periodo del año anterior).")
            else:
                col1, col2 = st.columns([0.6, 0.4])
                with col1:
                    st.subheader("Justificación del Cálculo")
                    st.markdown(f"""
                    - **🗓️ Línea Base Histórica (Estacional):** El promedio de ventas en el mismo periodo del año anterior fue de **${row['base_historica']:,.0f}**.
                    - **🚀 Tendencia de Rendimiento Reciente:** El promedio de ventas en los últimos 3 meses fue de **${row['tendencia_reciente']:,.0f}**.
                    
                    Combinando estos dos factores con un peso del **50% cada uno**, la base de cálculo es de **${(row['componente_historico_ponderado'] + row['componente_reciente_ponderado']):,.0f}**.
                    
                    Aplicando un **factor de crecimiento del 8%**, la meta de venta final se establece en:
                    ### <center>${row['presupuesto_final']:,.0f}</center>
                    """, unsafe_allow_html=True)

                with col2:
                    st.subheader("Componentes del Presupuesto")
                    df_componentes = pd.DataFrame([
                        {'Componente': 'Base Histórica', 'Valor': row['base_historica']},
                        {'Componente': 'Tendencia Reciente', 'Valor': row['tendencia_reciente']}
                    ])
                    fig = px.bar(df_componentes, x='Componente', y='Valor',
                                 title=f"Comparativa de Rendimiento para {nombre}",
                                 text_auto='.2s', color='Componente',
                                 color_discrete_map={'Base Histórica': '#636EFA', 'Tendencia Reciente': '#EF553B'})
                    fig.update_layout(showlegend=False, yaxis_title="Venta Promedio Mensual")
                    st.plotly_chart(fig, use_container_width=True)

    # --- Sección de Acción para Vendedores Nuevos ---
    df_nuevos = df_presupuestos[df_presupuestos['sin_historial'] == True]
    if not df_nuevos.empty:
        st.markdown("---")
        st.header("🛠️ Asignación de Metas para Vendedores Nuevos")
        st.warning("Los siguientes vendedores no tienen historial suficiente para un cálculo automático. Por favor, asigne una meta de venta y cartera manualmente.")

        for index, row in df_nuevos.iterrows():
            nombre = row['Vendedor/Grupo']
            st.subheader(nombre)
            col1, col2 = st.columns(2)
            meta_venta_manual = col1.number_input(f"Asignar Meta de Venta para {nombre}", min_value=0, step=1000000, key=f"venta_{nombre}")
            meta_cartera_manual = col2.number_input(f"Asignar Meta de Cartera para {nombre}", min_value=0, step=1000000, key=f"cartera_{nombre}")
        
        if st.button("Guardar Metas Manuales", type="primary"):
            st.success("¡Metas guardadas! (Funcionalidad de guardado en base de datos a implementar)")
            # Aquí iría la lógica para guardar estas metas en un archivo o base de datos.
            
# --- Punto de Entrada del Script ---
if __name__ == "__main__":
    # La autenticación y carga de datos se maneja en la página principal.
    # Esta página asume que ya se ha pasado por ese proceso.
    render_presupuestos_page()
