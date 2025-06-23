import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import dropbox
import io

# ==============================================================================
# 1. CONFIGURACIÓN CENTRALIZADA
# ==============================================================================
# Todos los parámetros y constantes de la aplicación se definen aquí.
# ------------------------------------------------------------------------------

APP_CONFIG = {
    "page_title": "Resumen Mensual | Tablero de Ventas",
    "url_logo": "https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png",
    "dropbox_paths": {
        "ventas": "/data/ventas_detalle.csv",
        "cobros": "/data/cobros_detalle.csv"
    },
    "column_names": {
        "ventas": ['anio', 'mes', 'fecha_venta', 'codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_cliente', 'codigo_articulo', 'nombre_articulo','linea_producto', 'marca_producto', 'valor_venta', 'unidades_vendidas', 'costo_unitario', 'super_categoria'],
        "cobros": ['anio', 'mes', 'fecha_cobro', 'codigo_vendedor', 'valor_cobro']
    },
    "kpi_goals": {
        "meta_marquilla": 2.4
    },
    "marquillas_clave": ['VINILTEX', 'KORAZA', 'ESTUCOMASTIC', 'VINILICO']
}

DATA_CONFIG = {
    "presupuestos": {'154033':{'presupuesto':123873239, 'presupuestocartera':105287598}, '154044':{'presupuesto':80000000, 'presupuestocartera':300000000}, '154034':{'presupuesto':82753045, 'presupuestocartera':44854727}, '154014':{'presupuesto':268214737, 'presupuestocartera':307628243}, '154046':{'presupuesto':85469798, 'presupuestocartera':7129065}, '154012':{'presupuesto':246616193, 'presupuestocartera':295198667}, '154043':{'presupuesto':124885413, 'presupuestocartera':99488960}, '154035':{'presupuesto':80000000, 'presupuestocartera':300000000}, '154006':{'presupuesto':81250000, 'presupuestocartera':103945133}, '154049':{'presupuesto':56500000, 'presupuestocartera':70421127}, '154013':{'presupuesto':303422639, 'presupuestocartera':260017920}, '154011':{'presupuesto':447060250, 'presupuestocartera':428815923}, '154029':{'presupuesto':32500000, 'presupuestocartera':40000000}, '154040':{'presupuesto':0, 'presupuestocartera':0},'154053':{'presupuesto':0, 'presupuestocartera':0},'154048':{'presupuesto':0, 'presupuestocartera':0},'154042':{'presupuesto':0, 'presupuestocartera':0},'154031':{'presupuesto':0, 'presupuestocartera':0},'154039':{'presupuesto':0, 'presupuestocartera':0},'154051':{'presupuesto':0, 'presupuestocartera':0},'154008':{'presupuesto':0, 'presupuestocartera':0},'154052':{'presupuesto':0, 'presupuestocartera':0},'154050':{'presupuesto':0, 'presupuestocartera':0}},
    "grupos_vendedores": {"MOSTRADOR PEREIRA": ["ALEJANDRO CARBALLO MARQUEZ", "GEORGINA A. GALVIS HERRERA"], "MOSTRADOR ARMENIA": ["CRISTIAN CAMILO RENDON MONTES", "FANDRY JOHANA ABRIL PENHA", "JAVIER ORLANDO PATINO HURTADO"], "MOSTRADOR MANIZALES": ["DAVID FELIPE MARTINEZ RIOS", "JHON JAIRO CASTAÑO MONTES"], "MOSTRADOR LAURELES": ["MAURICIO RIOS MORALES"]},
    "mapeo_meses": {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"},
    "mapeo_marcas": {50:"P8-ASC-MEGA", 54:"MPY-International", 55:"DPP-AN COLORANTS LATAM", 56:"DPP-Pintuco Profesional", 57:"ASC-Mega", 58:"DPP-Pintuco", 59:"DPP-Madetec", 60:"POW-Interpon", 61:"various", 62:"DPP-ICO", 63:"DPP-Terinsa", 64:"MPY-Pintuco", 65:"non-AN Third Party", 66:"ICO-AN Packaging", 67:"ASC-Automotive OEM", 68:"POW-Resicoat", 73:"DPP-Coral", 91:"DPP-Sikkens"}
}

st.set_page_config(
    page_title=APP_CONFIG["page_title"],
    page_icon=APP_CONFIG["url_logo"],
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. LÓGICA DE PROCESAMIENTO DE DATOS
# ==============================================================================
# Funciones dedicadas a la carga, limpieza y transformación de los datos.
# ------------------------------------------------------------------------------

@st.cache_data(ttl=1800)
def cargar_y_limpiar_datos(ruta_archivo, nombres_columnas):
    """Descarga y limpia datos desde Dropbox usando el refresh token."""
    try:
        with dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, app_secret=st.secrets.dropbox.app_secret, oauth2_refresh_token=st.secrets.dropbox.refresh_token) as dbx:
            _, res = dbx.files_download(path=ruta_archivo)
            contenido_csv = res.content.decode('latin-1')
            df = pd.read_csv(io.StringIO(contenido_csv), header=None, sep=',', on_bad_lines='skip', dtype=str)

            if df.shape[1] != len(nombres_columnas):
                st.warning(f"Formato en {ruta_archivo}: Se esperaban {len(nombres_columnas)} columnas pero hay {df.shape[1]}.")
                return pd.DataFrame(columns=nombres_columnas)

            df.columns = nombres_columnas
            numeric_cols = ['anio', 'mes', 'valor_venta', 'valor_cobro', 'unidades_vendidas', 'costo_unitario', 'marca_producto']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            df.dropna(subset=['anio', 'mes', 'codigo_vendedor'], inplace=True)
            df = df.astype({'anio': int, 'mes': int, 'codigo_vendedor': str})

            if 'fecha_venta' in df.columns:
                df['fecha_venta'] = pd.to_datetime(df['fecha_venta'], errors='coerce')
            if 'marca_producto' in df.columns:
                df['nombre_marca'] = df['marca_producto'].map(DATA_CONFIG["mapeo_marcas"]).fillna('No Especificada')
            return df
    except Exception as e:
        st.error(f"Error crítico al cargar {ruta_archivo}: {e}")
        return pd.DataFrame(columns=nombres_columnas)

def calcular_marquilla_optimizado(df_periodo):
    """
    Calcula el promedio de marquilla de forma más eficiente.
    Crea un DataFrame temporal para identificar las compras de marcas clave por cliente y luego agrega los resultados.
    """
    if df_periodo.empty or 'nombre_articulo' not in df_periodo.columns:
        return pd.DataFrame(columns=['codigo_vendedor', 'nomvendedor', 'promedio_marquilla'])

    # Crea un DataFrame temporal para no modificar el original con columnas innecesarias
    df_temp = df_periodo[['codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_articulo']].copy()
    df_temp['nombre_articulo'] = df_temp['nombre_articulo'].astype(str)

    # Verifica la presencia de cada marca clave
    for palabra in APP_CONFIG['marquillas_clave']:
        df_temp[palabra] = df_temp['nombre_articulo'].str.contains(palabra, case=False)

    # 1. Agrupar por cliente para ver qué marcas únicas compró
    df_cliente_marcas = df_temp.groupby(['codigo_vendedor', 'nomvendedor', 'cliente_id'])[APP_CONFIG['marquillas_clave']].any()

    # 2. Sumar las marcas únicas (True=1, False=0) para obtener el puntaje por cliente
    df_cliente_marcas['puntaje_marquilla'] = df_cliente_marcas[APP_CONFIG['marquillas_clave']].sum(axis=1)

    # 3. Calcular el promedio de los puntajes por vendedor
    df_final_marquilla = df_cliente_marcas.groupby(['codigo_vendedor', 'nomvendedor'])['puntaje_marquilla'].mean().reset_index()
    return df_final_marquilla.rename(columns={'puntaje_marquilla': 'promedio_marquilla'})


def procesar_datos_periodo(df_ventas, df_cobros):
    """
    Centraliza toda la lógica de negocio para procesar los datos del periodo seleccionado.
    Retorna un DataFrame final listo para ser mostrado.
    """
    # 1. Resúmenes individuales
    resumen_ventas = df_ventas.groupby(['codigo_vendedor', 'nomvendedor']).agg(
        ventas_totales=('valor_venta', 'sum'),
        impactos=('cliente_id', 'nunique')
    ).reset_index()
    resumen_cobros = df_cobros.groupby('codigo_vendedor').agg(cobros_totales=('valor_cobro', 'sum')).reset_index()
    resumen_marquilla = calcular_marquilla_optimizado(df_ventas)

    # 2. Unir los resúmenes
    df_resumen = pd.merge(resumen_ventas, resumen_cobros, on='codigo_vendedor', how='left')
    df_resumen = pd.merge(df_resumen, resumen_marquilla, on=['codigo_vendedor', 'nomvendedor'], how='left')

    # 3. Mapear presupuestos
    presupuestos = DATA_CONFIG['presupuestos']
    df_resumen['presupuesto'] = df_resumen['codigo_vendedor'].map(lambda x: presupuestos.get(x, {}).get('presupuesto', 0))
    df_resumen['presupuestocartera'] = df_resumen['codigo_vendedor'].map(lambda x: presupuestos.get(x, {}).get('presupuestocartera', 0))
    df_resumen.fillna(0, inplace=True)

    # 4. Procesar grupos
    registros_agrupados = []
    for grupo, lista_vendedores in DATA_CONFIG['grupos_vendedores'].items():
        df_grupo = df_resumen[df_resumen['nomvendedor'].isin(lista_vendedores)]
        if not df_grupo.empty:
            suma_grupo = df_grupo[['ventas_totales', 'cobros_totales', 'impactos', 'presupuesto', 'presupuestocartera']].sum().to_dict()
            total_impactos = df_grupo['impactos'].sum()
            promedio_marquilla_grupo = np.average(df_grupo['promedio_marquilla'], weights=df_grupo['impactos']) if total_impactos > 0 else 0.0
            
            registro = {'nomvendedor': grupo, 'codigo_vendedor': grupo, **suma_grupo, 'promedio_marquilla': promedio_marquilla_grupo}
            registros_agrupados.append(registro)
    
    df_agrupado = pd.DataFrame(registros_agrupados)

    # 5. Combinar individuales y grupos
    vendedores_en_grupos = [v for lista in DATA_CONFIG['grupos_vendedores'].values() for v in lista]
    df_individuales = df_resumen[~df_resumen['nomvendedor'].isin(vendedores_en_grupos)]
    
    df_final = pd.concat([df_agrupado, df_individuales], ignore_index=True)
    return df_final

# ==============================================================================
# 3. LÓGICA DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================
# Funciones dedicadas a renderizar los componentes de Streamlit.
# ------------------------------------------------------------------------------

def generar_comentario_asesor(avance_v, avance_c, marquilla_p):
    """Genera comentarios dinámicos basados en los KPIs."""
    comentarios = []
    if avance_v >= 100: comentarios.append("📈 **Ventas:** ¡Felicitaciones! Has superado la meta de ventas.")
    elif avance_v >= 80: comentarios.append("📈 **Ventas:** ¡Estás muy cerca de la meta! Un último esfuerzo.")
    else: comentarios.append("📈 **Ventas:** Planifica tus visitas y aprovecha cada oportunidad.")
    
    if avance_c >= 100: comentarios.append("💰 **Cartera:** Objetivo de recaudo cumplido. ¡Gestión impecable!")
    else: comentarios.append("💰 **Cartera:** Recuerda hacer seguimiento a la cartera pendiente.")
    
    if marquilla_p >= APP_CONFIG['kpi_goals']['meta_marquilla']: comentarios.append(f"🎨 **Marquilla:** Tu promedio de {marquilla_p:.2f} es excelente.")
    elif marquilla_p > 0: comentarios.append(f"🎨 **Marquilla:** Tu promedio es {marquilla_p:.2f}. Hay oportunidad de crecimiento.")
    else: comentarios.append("🎨 **Marquilla:** Aún no registras ventas en las marcas clave. ¡Son una gran oportunidad!")
    return comentarios

def render_kpis(df_vista):
    """Muestra las métricas clave (KPIs) y el asesor virtual."""
    with st.container(border=True):
        ventas_total = df_vista['ventas_totales'].sum()
        meta_ventas = df_vista['presupuesto'].sum()
        cobros_total = df_vista['cobros_totales'].sum()
        meta_cobros = df_vista['presupuestocartera'].sum()

        avance_ventas = (ventas_total / meta_ventas * 100) if meta_ventas > 0 else 0
        avance_cobros = (cobros_total / meta_cobros * 100) if meta_cobros > 0 else 0

        total_impactos = df_vista['impactos'].sum()
        if total_impactos > 0:
            marquilla_prom = np.average(df_vista['promedio_marquilla'], weights=df_vista['impactos'])
        else:
            marquilla_prom = 0.0

        st.subheader(f"👨‍💼 Asesor Virtual para: {st.session_state.usuario}")
        comentarios = generar_comentario_asesor(avance_ventas, avance_cobros, marquilla_prom)
        for comentario in comentarios:
            st.markdown(f"- {comentario}")

    st.subheader("Métricas Clave del Periodo")
    col1, col2, col3 = st.columns(3)
    meta_marquilla = APP_CONFIG['kpi_goals']['meta_marquilla']
    
    col1.metric("Ventas Totales", f"${ventas_total:,.0f}", f"{ventas_total - meta_ventas:,.0f} vs Meta")
    col1.progress(min(avance_ventas / 100, 1.0), text=f"Avance Ventas: {avance_ventas:.1f}%")
    
    col2.metric("Recaudo de Cartera", f"${cobros_total:,.0f}", f"{cobros_total - meta_cobros:,.0f} vs Meta")
    col2.progress(min(avance_cobros / 100, 1.0), text=f"Avance Cartera: {avance_cobros:.1f}%")

    col3.metric("Promedio Marquilla", f"{marquilla_prom:.2f}", f"{marquilla_prom - meta_marquilla:.2f} vs Meta")
    col3.progress(min((marquilla_prom / meta_marquilla), 1.0) if marquilla_prom > 0 else 0, text=f"Meta: {meta_marquilla}")


def render_analisis_detallado(df_vista, df_ventas_periodo):
    """Muestra la sección de análisis con pestañas."""
    st.markdown("---")
    st.header("🔬 Análisis Detallado del Periodo")

    opciones_enfoque = ["Visión General"] + sorted(df_vista['nomvendedor'].unique())
    enfoque_sel = st.selectbox(
        "Enfocar análisis en:",
        opciones_enfoque,
        index=0 if len(opciones_enfoque) > 2 else 1
    )
    
    # Lógica simplificada para filtrar los datos de ventas para los gráficos
    if enfoque_sel == "Visión General":
        nombres_a_filtrar = []
        for vendedor in df_vista['nomvendedor']:
             nombres_a_filtrar.extend(DATA_CONFIG['grupos_vendedores'].get(vendedor, [vendedor]))
        df_ventas_enfocadas = df_ventas_periodo[df_ventas_periodo['nomvendedor'].isin(nombres_a_filtrar)]
        df_ranking = df_vista
    else:
        nombres_a_filtrar = DATA_CONFIG['grupos_vendedores'].get(enfoque_sel, [enfoque_sel])
        df_ventas_enfocadas = df_ventas_periodo[df_ventas_periodo['nomvendedor'].isin(nombres_a_filtrar)]
        df_ranking = df_vista[df_vista['nomvendedor'] == enfoque_sel]

    tab1, tab2, tab3 = st.tabs(["📊 Análisis de Portafolio", "🏆 Ranking de Rendimiento", "⭐ Clientes Clave"])

    with tab1:
        st.subheader("Análisis de Marcas y Categorías Estratégicas")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Ventas por Super Categoría")
            if not df_ventas_enfocadas.empty and 'super_categoria' in df_ventas_enfocadas.columns:
                df_super_cat = df_ventas_enfocadas.groupby('super_categoria')['valor_venta'].sum().nlargest(10).reset_index()
                fig = px.bar(df_super_cat, x='super_categoria', y='valor_venta', text_auto='.2s', title="Top 10 Categorías por Venta")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos de 'super_categoria' para mostrar.")
        with col2:
            st.markdown("##### Ventas de Marquillas Clave")
            if not df_ventas_enfocadas.empty:
                ventas_marquillas = {p: df_ventas_enfocadas[df_ventas_enfocadas['nombre_articulo'].str.contains(p, case=False)]['valor_venta'].sum() for p in APP_CONFIG['marquillas_clave']}
                df_ventas_marquillas = pd.DataFrame(list(ventas_marquillas.items()), columns=['Marquilla', 'Ventas']).sort_values('Ventas', ascending=False)
                fig = px.pie(df_ventas_marquillas, names='Marquilla', values='Ventas', title="Distribución Venta Marquillas", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos de marquillas para mostrar.")
    
    with tab2:
        st.subheader("Ranking de Cumplimiento de Metas")
        df_ranking_con_meta = df_ranking[df_ranking['presupuesto'] > 0].copy()
        if not df_ranking_con_meta.empty:
            df_ranking_con_meta['avance_ventas'] = (df_ranking_con_meta['ventas_totales'] / df_ranking_con_meta['presupuesto']) * 100
            df_ranking_con_meta.sort_values('avance_ventas', ascending=True, inplace=True)
            fig = px.bar(df_ranking_con_meta, x='avance_ventas', y='nomvendedor', orientation='h', text='avance_ventas', title="Cumplimiento de Meta de Ventas (%)")
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(xaxis_title="Cumplimiento (%)", yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de presupuesto para generar el ranking.")

    with tab3:
        st.subheader("Top 10 Clientes del Periodo")
        if not df_ventas_enfocadas.empty:
            top_clientes = df_ventas_enfocadas.groupby('nombre_cliente')['valor_venta'].sum().nlargest(10).reset_index()
            st.dataframe(top_clientes, column_config={"nombre_cliente": "Cliente", "valor_venta": st.column_config.NumberColumn("Total Compra", format="$ %d")}, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos de clientes para este periodo.")

def render_dashboard():
    """Función principal que orquesta la renderización del dashboard."""
    # --- FILTROS DE PERIODO ---
    st.sidebar.markdown("---")
    st.sidebar.header("Filtros de Periodo")
    df_ventas = st.session_state.df_ventas
    df_cobros = st.session_state.df_cobros
    
    lista_anios = sorted(df_ventas['anio'].unique(), reverse=True)
    if not lista_anios:
        st.error("No hay datos históricos de ventas para analizar.")
        st.stop()
        
    anio_reciente = int(df_ventas['anio'].max())
    mes_reciente = int(df_ventas[df_ventas['anio'] == anio_reciente]['mes'].max())
    
    anio_sel = st.sidebar.selectbox("Elija el Año", lista_anios, index=0)
    
    lista_meses_num = sorted(df_ventas[df_ventas['anio'] == anio_sel]['mes'].unique())
    index_mes_defecto = lista_meses_num.index(mes_reciente) if anio_sel == anio_reciente and mes_reciente in lista_meses_num else 0
    mes_sel_num = st.sidebar.selectbox("Elija el Mes", options=lista_meses_num, format_func=lambda x: DATA_CONFIG['mapeo_meses'].get(x, 'N/A'), index=index_mes_defecto)

    # --- FILTRADO DE DATOS ---
    df_ventas_periodo = df_ventas[(df_ventas['anio'] == anio_sel) & (df_ventas['mes'] == mes_sel_num)]
    df_cobros_periodo = df_cobros[(df_cobros['anio'] == anio_sel) & (df_cobros['mes'] == mes_sel_num)]

    if df_ventas_periodo.empty:
        st.warning("No hay datos de ventas para el periodo seleccionado.")
        st.stop()
    
    # --- PROCESAMIENTO Y FILTRADO POR USUARIO ---
    df_resumen_final = procesar_datos_periodo(df_ventas_periodo, df_cobros_periodo)
    
    usuario_actual = st.session_state.usuario
    if usuario_actual == "GERENTE":
        lista_filtro = sorted(df_resumen_final['nomvendedor'].unique())
        vendedores_sel = st.sidebar.multiselect("Filtrar Vendedores/Grupos", options=lista_filtro, default=lista_filtro)
        df_vista = df_resumen_final[df_resumen_final['nomvendedor'].isin(vendedores_sel)]
    else:
        df_vista = df_resumen_final[df_resumen_final['nomvendedor'] == usuario_actual]

    if df_vista.empty:
        st.warning("No hay datos para mostrar para tu selección.")
        st.stop()

    # --- CÁLCULO DE ESTATUS ---
    def asignar_estatus(row):
        avance = (row['ventas_totales'] / row['presupuesto'] * 100) if row['presupuesto'] > 0 else 0
        if avance >= 95: return "🟢 En Objetivo"
        if avance >= 70: return "🟡 Cerca del Objetivo"
        return "🔴 Necesita Atención"
    df_vista['Estatus'] = df_vista.apply(asignar_estatus, axis=1)

    # --- RENDERIZADO DE LA PÁGINA ---
    st.title("🏠 Resumen de Rendimiento")
    st.header(f"{DATA_CONFIG['mapeo_meses'].get(mes_sel_num, '')} {anio_sel}")
    vista_para = st.session_state.usuario if len(df_vista['nomvendedor'].unique()) == 1 else 'Múltiples Seleccionados'
    st.markdown(f"**Vista para:** `{vista_para}`")
    
    render_kpis(df_vista)

    st.subheader("Desglose por Vendedor / Grupo")
    st.dataframe(
        df_vista[['Estatus', 'nomvendedor', 'ventas_totales', 'presupuesto', 'cobros_totales', 'presupuestocartera', 'impactos', 'promedio_marquilla']],
        column_config={
            "Estatus": st.column_config.TextColumn("🚦", width="small"),
            "nomvendedor": "Vendedor/Grupo",
            "ventas_totales": st.column_config.NumberColumn("Ventas", format="$ %d"),
            "presupuesto": st.column_config.NumberColumn("Meta Ventas", format="$ %d"),
            "cobros_totales": st.column_config.NumberColumn("Recaudo", format="$ %d"),
            "presupuestocartera": st.column_config.NumberColumn("Meta Recaudo", format="$ %d"),
            "impactos": st.column_config.NumberColumn("Clientes Únicos", format="%d"),
            "promedio_marquilla": st.column_config.ProgressColumn("Promedio Marquilla", format="%.2f", min_value=0, max_value=len(APP_CONFIG['marquillas_clave']))
        },
        use_container_width=True,
        hide_index=True
    )
    
    render_analisis_detallado(df_vista, df_ventas_periodo)
    # AÑADE ESTE BLOQUE AL FINAL DE LA FUNCIÓN render_dashboard()
    with st.expander("🔍 CAJA DE DIAGNÓSTICO - PÁGINA PRINCIPAL"):
        st.subheader("Estado de la Sesión Actual:")
        st.write(st.session_state)

# ==============================================================================
# 4. LÓGICA DE AUTENTICACIÓN Y EJECUCIÓN PRINCIPAL
# ==============================================================================

def main():
    """Función principal que controla el flujo de la aplicación."""
    st.sidebar.image(APP_CONFIG["url_logo"], use_container_width=True)
    st.sidebar.header("Control de Acceso")

    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        # --- Carga de usuarios para el login ---
        @st.cache_data
        def obtener_lista_usuarios():
            df = cargar_y_limpiar_datos(APP_CONFIG["dropbox_paths"]["ventas"], APP_CONFIG["column_names"]["ventas"])
            if not df.empty:
                vendedores_individuales = sorted(list(df['nomvendedor'].dropna().unique()))
                vendedores_en_grupos = [v for lista in DATA_CONFIG['grupos_vendedores'].values() for v in lista]
                vendedores_solos = [v for v in vendedores_individuales if v not in vendedores_en_grupos]
                return ["GERENTE"] + list(DATA_CONFIG['grupos_vendedores'].keys()) + vendedores_solos
            return ["GERENTE"] + list(DATA_CONFIG['grupos_vendedores'].keys())

        todos_usuarios = obtener_lista_usuarios()
        usuarios_fijos = {"GERENTE": "1234", "MOSTRADOR PEREIRA": "2345", "MOSTRADOR ARMENIA": "3456", "MOSTRADOR MANIZALES": "4567", "MOSTRADOR LAURELES": "5678"}
        
        usuarios = usuarios_fijos.copy()
        codigo = 1001
        for u in todos_usuarios:
            if u not in usuarios:
                usuarios[u] = str(codigo)
                codigo += 1

        # --- Formulario de login ---
        usuario_seleccionado = st.sidebar.selectbox("Seleccione su usuario", options=todos_usuarios)
        clave = st.sidebar.text_input("Contraseña", type="password")

        if st.sidebar.button("Ingresar"):
            if usuario_seleccionado in usuarios and clave == usuarios[usuario_seleccionado]:
                st.session_state.autenticado = True
                st.session_state.usuario = usuario_seleccionado
                with st.spinner('Cargando datos maestros, por favor espere...'):
                    st.session_state.df_ventas = cargar_y_limpiar_datos(APP_CONFIG["dropbox_paths"]["ventas"], APP_CONFIG["column_names"]["ventas"])
                    st.session_state.df_cobros = cargar_y_limpiar_datos(APP_CONFIG["dropbox_paths"]["cobros"], APP_CONFIG["column_names"]["cobros"])
                st.rerun()
            else:
                st.sidebar.error("Usuario o contraseña incorrectos")
        
        # --- Pantalla de bienvenida ---
        st.title("Plataforma de Inteligencia de Negocios")
        st.image(APP_CONFIG["url_logo"], width=400)
        st.header("Bienvenido")
        st.info("Por favor, utilice el panel de la izquierda para ingresar sus credenciales de acceso.")
    
    else:
        # --- Si está autenticado, renderizar el dashboard ---
        render_dashboard()
        if st.sidebar.button("Salir"):
            st.session_state.autenticado = False
            st.rerun()

if __name__ == '__main__':
    main()
