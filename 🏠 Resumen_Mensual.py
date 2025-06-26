import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import dropbox
import io

# ==============================================================================
# 1. CONFIGURACIÓN CENTRALIZADA
# ==============================================================================

APP_CONFIG = {
    "page_title": "Resumen Mensual | Tablero de Ventas",
    "url_logo": "https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png",
    "dropbox_paths": {
        "ventas": "/data/ventas_detalle.csv",
        "cobros": "/data/cobros_detalle.csv"
    },
    "column_names": {
        # << MODIFICADO >> Se añadió 'categoria_producto' según tu nueva consulta SQL
        "ventas": ['anio', 'mes', 'fecha_venta', 'codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_cliente', 'codigo_articulo', 'nombre_articulo', 'categoria_producto', 'linea_producto', 'marca_producto', 'valor_venta', 'unidades_vendidas', 'costo_unitario', 'super_categoria'],
        "cobros": ['anio', 'mes', 'fecha_cobro', 'codigo_vendedor', 'valor_cobro']
    },
    "kpi_goals": {
        "meta_marquilla": 2.4
    },
    "marquillas_clave": ['VINILTEX', 'KORAZA', 'ESTUCOMASTIC', 'VINILICO'],
    # << NUEVO >> Configuración para las nuevas funcionalidades
    "complementarios": {
        "departamento": "ACC PARA PINTAR", # Departamento que identifica a los complementarios
        "presupuesto_pct": 0.10 # El presupuesto es el 10% del de ventas
    },
    "categorias_clave_venta": ['ABRACOL', 'YALE', 'SAINT GOBAIN', 'GOYA', 'ALLEGION', 'SEGUREX']
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

@st.cache_data(ttl=1800)
def cargar_y_limpiar_datos(ruta_archivo, nombres_columnas):
    """Descarga y limpia datos desde Dropbox."""
    try:
        with dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, app_secret=st.secrets.dropbox.app_secret, oauth2_refresh_token=st.secrets.dropbox.refresh_token) as dbx:
            _, res = dbx.files_download(path=ruta_archivo)
            contenido_csv = res.content.decode('latin-1')
            df = pd.read_csv(io.StringIO(contenido_csv), header=None, sep=',', on_bad_lines='skip', dtype=str)
            if df.shape[1] != len(nombres_columnas):
                st.warning(f"Formato en {ruta_archivo}: Se esperaban {len(nombres_columnas)} cols pero hay {df.shape[1]}.")
                return pd.DataFrame(columns=nombres_columnas)
            df.columns = nombres_columnas
            numeric_cols = ['anio', 'mes', 'valor_venta', 'valor_cobro', 'unidades_vendidas', 'costo_unitario', 'marca_producto']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df.dropna(subset=['anio', 'mes', 'codigo_vendedor'], inplace=True)
            df = df.astype({'anio': int, 'mes': int, 'codigo_vendedor': str})
            if 'fecha_venta' in df.columns: df['fecha_venta'] = pd.to_datetime(df['fecha_venta'], errors='coerce')
            if 'marca_producto' in df.columns: df['nombre_marca'] = df['marca_producto'].map(DATA_CONFIG["mapeo_marcas"]).fillna('No Especificada')
            return df
    except Exception as e:
        st.error(f"Error crítico al cargar {ruta_archivo}: {e}")
        return pd.DataFrame(columns=nombres_columnas)

def calcular_marquilla_optimizado(df_periodo):
    """Calcula el promedio de marquilla de forma eficiente."""
    if df_periodo.empty or 'nombre_articulo' not in df_periodo.columns:
        return pd.DataFrame(columns=['codigo_vendedor', 'nomvendedor', 'promedio_marquilla'])
    df_temp = df_periodo[['codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_articulo']].copy()
    df_temp['nombre_articulo'] = df_temp['nombre_articulo'].astype(str)
    for palabra in APP_CONFIG['marquillas_clave']:
        df_temp[palabra] = df_temp['nombre_articulo'].str.contains(palabra, case=False)
    df_cliente_marcas = df_temp.groupby(['codigo_vendedor', 'nomvendedor', 'cliente_id'])[APP_CONFIG['marquillas_clave']].any()
    df_cliente_marcas['puntaje_marquilla'] = df_cliente_marcas[APP_CONFIG['marquillas_clave']].sum(axis=1)
    df_final_marquilla = df_cliente_marcas.groupby(['codigo_vendedor', 'nomvendedor'])['puntaje_marquilla'].mean().reset_index()
    return df_final_marquilla.rename(columns={'puntaje_marquilla': 'promedio_marquilla'})

def procesar_datos_periodo(df_ventas, df_cobros):
    """<< MODIFICADO >> Centraliza la lógica de negocio, ahora incluyendo complementarios."""
    resumen_ventas = df_ventas.groupby(['codigo_vendedor', 'nomvendedor']).agg(
        ventas_totales=('valor_venta', 'sum'), impactos=('cliente_id', 'nunique')).reset_index()
    
    resumen_cobros = df_cobros.groupby('codigo_vendedor').agg(cobros_totales=('valor_cobro', 'sum')).reset_index()
    
    # << NUEVO >> Cálculo de ventas de productos complementarios
    df_ventas_comp = df_ventas[df_ventas['linea_producto'] == APP_CONFIG['complementarios']['departamento']]
    resumen_complementarios = df_ventas_comp.groupby('codigo_vendedor').agg(
        ventas_complementarios=('valor_venta', 'sum')).reset_index()
    
    resumen_marquilla = calcular_marquilla_optimizado(df_ventas)
    
    df_resumen = pd.merge(resumen_ventas, resumen_cobros, on='codigo_vendedor', how='left')
    df_resumen = pd.merge(df_resumen, resumen_marquilla, on=['codigo_vendedor', 'nomvendedor'], how='left')
    # << NUEVO >> Se integra el resumen de complementarios
    df_resumen = pd.merge(df_resumen, resumen_complementarios, on='codigo_vendedor', how='left')

    presupuestos = DATA_CONFIG['presupuestos']
    df_resumen['presupuesto'] = df_resumen['codigo_vendedor'].map(lambda x: presupuestos.get(x, {}).get('presupuesto', 0))
    df_resumen['presupuestocartera'] = df_resumen['codigo_vendedor'].map(lambda x: presupuestos.get(x, {}).get('presupuestocartera', 0))
    # << NUEVO >> Se calcula el presupuesto de complementarios
    df_resumen['presupuesto_complementarios'] = df_resumen['presupuesto'] * APP_CONFIG['complementarios']['presupuesto_pct']
    
    df_resumen.fillna(0, inplace=True)
    
    registros_agrupados = []
    for grupo, lista_vendedores in DATA_CONFIG['grupos_vendedores'].items():
        df_grupo = df_resumen[df_resumen['nomvendedor'].isin(lista_vendedores)]
        if not df_grupo.empty:
            # << MODIFICADO >> Se agregan las nuevas columnas a la suma del grupo
            cols_a_sumar = ['ventas_totales', 'cobros_totales', 'impactos', 'presupuesto', 'presupuestocartera', 'ventas_complementarios', 'presupuesto_complementarios']
            suma_grupo = df_grupo[cols_a_sumar].sum().to_dict()
            total_impactos = df_grupo['impactos'].sum()
            promedio_marquilla_grupo = np.average(df_grupo['promedio_marquilla'], weights=df_grupo['impactos']) if total_impactos > 0 else 0.0
            registro = {'nomvendedor': grupo, 'codigo_vendedor': grupo, **suma_grupo, 'promedio_marquilla': promedio_marquilla_grupo}
            registros_agrupados.append(registro)
            
    df_agrupado = pd.DataFrame(registros_agrupados)
    vendedores_en_grupos = [v for lista in DATA_CONFIG['grupos_vendedores'].values() for v in lista]
    df_individuales = df_resumen[~df_resumen['nomvendedor'].isin(vendedores_en_grupos)]
    
    df_final = pd.concat([df_agrupado, df_individuales], ignore_index=True)
    return df_final

# ==============================================================================
# 3. LÓGICA DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def generar_comentario_asesor(avance_v, avance_c, marquilla_p, avance_comp):
    """<< MODIFICADO >> Genera comentarios dinámicos, ahora incluyendo complementarios."""
    comentarios = []
    if avance_v >= 100: comentarios.append("📈 **Ventas:** ¡Felicitaciones! Has superado la meta de ventas.")
    elif avance_v >= 80: comentarios.append("📈 **Ventas:** ¡Estás muy cerca de la meta! Un último esfuerzo.")
    else: comentarios.append("📈 **Ventas:** Planifica tus visitas y aprovecha cada oportunidad.")
    
    if avance_c >= 100: comentarios.append("💰 **Cartera:** Objetivo de recaudo cumplido. ¡Gestión impecable!")
    else: comentarios.append("💰 **Cartera:** Recuerda hacer seguimiento a la cartera pendiente.")

    # << NUEVO >> Comentario para la meta de complementarios
    if avance_comp >= 100: comentarios.append("⚙️ **Complementarios:** ¡Excelente! Cumpliste la meta de venta de complementarios.")
    else: comentarios.append(f"⚙️ **Complementarios:** Tu avance es del {avance_comp:.1f}%. ¡Impulsa la venta cruzada!")

    if marquilla_p >= APP_CONFIG['kpi_goals']['meta_marquilla']: comentarios.append(f"🎨 **Marquilla:** Tu promedio de {marquilla_p:.2f} es excelente.")
    elif marquilla_p > 0: comentarios.append(f"🎨 **Marquilla:** Tu promedio es {marquilla_p:.2f}. Hay oportunidad de crecimiento.")
    else: comentarios.append("🎨 **Marquilla:** Aún no registras ventas en las marcas clave. ¡Son una gran oportunidad!")
    
    return comentarios

def render_analisis_detallado(df_vista, df_ventas_periodo):
    """<< MODIFICADO >> Renderiza la sección de análisis detallado con la nueva pestaña."""
    st.markdown("---")
    st.header("🔬 Análisis Detallado del Periodo")

    opciones_enfoque = ["Visión General"] + sorted(df_vista['nomvendedor'].unique())
    enfoque_sel = st.selectbox("Enfocar análisis en:", opciones_enfoque, index=0)
    
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
    
    # << MODIFICADO >> Se añade la nueva pestaña "Ventas por Categoría"
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Análisis de Portafolio", "🏆 Ranking de Rendimiento", "⭐ Clientes Clave", "⚙️ Ventas por Categoría"])

    with tab1:
        st.subheader("Análisis de Marcas y Categorías Estratégicas")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Composición de Ventas por Marca")
            if not df_ventas_enfocadas.empty and 'nombre_marca' in df_ventas_enfocadas:
                df_marcas = df_ventas_enfocadas.groupby('nombre_marca')['valor_venta'].sum().reset_index()
                fig = px.treemap(df_marcas, path=[px.Constant("Todas las Marcas"), 'nombre_marca'], values='valor_venta')
                fig.update_layout(margin=dict(t=25, l=25, r=25, b=25))
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("No hay datos de marcas de productos para mostrar.")
        with col2:
            st.markdown("##### Ventas de Marquillas Clave")
            if not df_ventas_enfocadas.empty:
                ventas_marquillas = {p: df_ventas_enfocadas[df_ventas_enfocadas['nombre_articulo'].str.contains(p, case=False)]['valor_venta'].sum() for p in APP_CONFIG['marquillas_clave']}
                df_ventas_marquillas = pd.DataFrame(list(ventas_marquillas.items()), columns=['Marquilla', 'Ventas']).sort_values('Ventas', ascending=False)
                fig = px.pie(df_ventas_marquillas, names='Marquilla', values='Ventas', title="Distribución Venta Marquillas", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("No hay datos de marquillas para mostrar.")
    
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
        else: st.info("No hay datos de presupuesto para generar el ranking.")

    with tab3:
        st.subheader("Top 10 Clientes del Periodo")
        if not df_ventas_enfocadas.empty:
            top_clientes = df_ventas_enfocadas.groupby('nombre_cliente')['valor_venta'].sum().nlargest(10).reset_index()
            st.dataframe(top_clientes, column_config={"nombre_cliente": "Cliente", "valor_venta": st.column_config.NumberColumn("Total Compra", format="$ %d")}, use_container_width=True, hide_index=True)
        else: st.info("No hay datos de clientes para este periodo.")

    # << NUEVO >> Contenido de la nueva pestaña de Ventas por Categoría
    with tab4:
        st.subheader(f"Desempeño en Categorías Clave para: {enfoque_sel}")
        
        categorias_objetivo = APP_CONFIG['categorias_clave_venta']
        df_ventas_cat = df_ventas_enfocadas[df_ventas_enfocadas['categoria_producto'].isin(categorias_objetivo)]
        
        if df_ventas_cat.empty:
            st.info("No se encontraron ventas en las categorías clave (ABRACOL, YALE, etc.) para la selección actual.")
        else:
            col1, col2 = st.columns([0.5, 0.5])
            
            with col1:
                st.markdown("##### Ventas por Categoría")
                resumen_cat = df_ventas_cat.groupby('categoria_producto').agg(Ventas=('valor_venta', 'sum')).reset_index()
                total_ventas_enfocadas = df_ventas_enfocadas['valor_venta'].sum()
                resumen_cat['Participacion (%)'] = (resumen_cat['Ventas'] / total_ventas_enfocadas) * 100
                resumen_cat = resumen_cat.sort_values('Ventas', ascending=False)
                
                st.dataframe(resumen_cat,
                             column_config={
                                 "categoria_producto": "Categoría",
                                 "Ventas": st.column_config.NumberColumn("Total Venta", format="$ %d"),
                                 "Participacion (%)": st.column_config.ProgressColumn("Part. sobre Venta Total", format="%.2f%%", min_value=0, max_value=resumen_cat['Participacion (%)'].max())
                             },
                             use_container_width=True, hide_index=True)

            with col2:
                st.markdown("##### Distribución de Ventas")
                fig = px.pie(resumen_cat, names='categoria_producto', values='Ventas', 
                             title="Distribución entre Categorías Clave", hole=0.4)
                fig.update_traces(textinfo='percent+label', textposition='inside')
                st.plotly_chart(fig, use_container_width=True)


def render_dashboard():
    """<< MODIFICADO >> Función principal que orquesta la renderización, ahora con 4 métricas."""
    st.sidebar.markdown("---"); st.sidebar.header("Filtros de Periodo")
    df_ventas = st.session_state.df_ventas; df_cobros = st.session_state.df_cobros
    
    lista_anios = sorted(df_ventas['anio'].unique(), reverse=True)
    if not lista_anios: st.error("No hay datos históricos para analizar."); st.stop()
        
    anio_reciente = int(df_ventas['anio'].max())
    mes_reciente = int(df_ventas[df_ventas['anio'] == anio_reciente]['mes'].max())
    anio_sel = st.sidebar.selectbox("Elija el Año", lista_anios, index=0)
    lista_meses_num = sorted(df_ventas[df_ventas['anio'] == anio_sel]['mes'].unique())
    index_mes_defecto = lista_meses_num.index(mes_reciente) if anio_sel == anio_reciente and mes_reciente in lista_meses_num else 0
    mes_sel_num = st.sidebar.selectbox("Elija el Mes", options=lista_meses_num, format_func=lambda x: DATA_CONFIG['mapeo_meses'].get(x, 'N/A'), index=index_mes_defecto)

    df_ventas_periodo = df_ventas[(df_ventas['anio'] == anio_sel) & (df_ventas['mes'] == mes_sel_num)]
    df_cobros_periodo = df_cobros[(df_cobros['anio'] == anio_sel) & (df_cobros['mes'] == mes_sel_num)]
    if df_ventas_periodo.empty: st.warning("No hay datos de ventas para el periodo seleccionado."); st.stop()
    
    df_resumen_final = procesar_datos_periodo(df_ventas_periodo, df_cobros_periodo)
    
    usuario_actual = st.session_state.usuario
    if usuario_actual == "GERENTE":
        lista_filtro = sorted(df_resumen_final['nomvendedor'].unique())
        vendedores_sel = st.sidebar.multiselect("Filtrar Vendedores/Grupos", options=lista_filtro, default=lista_filtro)
        df_vista = df_resumen_final[df_resumen_final['nomvendedor'].isin(vendedores_sel)]
    else:
        df_vista = df_resumen_final[df_resumen_final['nomvendedor'] == usuario_actual]
    if df_vista.empty: st.warning("No hay datos para mostrar para tu selección."); st.stop()

    def asignar_estatus(row):
        avance = (row['ventas_totales'] / row['presupuesto'] * 100) if row['presupuesto'] > 0 else 0
        if avance >= 95: return "🟢 En Objetivo"
        if avance >= 70: return "🟡 Cerca del Objetivo"
        return "🔴 Necesita Atención"
    df_vista['Estatus'] = df_vista.apply(asignar_estatus, axis=1)

    st.title("🏠 Resumen de Rendimiento"); st.header(f"{DATA_CONFIG['mapeo_meses'].get(mes_sel_num, '')} {anio_sel}")
    vista_para = st.session_state.usuario if len(df_vista['nomvendedor'].unique()) == 1 else 'Múltiples Seleccionados'
    st.markdown(f"**Vista para:** `{vista_para}`")
    
    with st.container(border=True):
        ventas_total = df_vista['ventas_totales'].sum(); meta_ventas = df_vista['presupuesto'].sum()
        cobros_total = df_vista['cobros_totales'].sum(); meta_cobros = df_vista['presupuestocartera'].sum()
        # << NUEVO >> Cálculo de totales para la nueva métrica
        comp_total = df_vista['ventas_complementarios'].sum(); meta_comp = df_vista['presupuesto_complementarios'].sum()

        avance_ventas = (ventas_total / meta_ventas * 100) if meta_ventas > 0 else 0
        avance_cobros = (cobros_total / meta_cobros * 100) if meta_cobros > 0 else 0
        # << NUEVO >> Cálculo de avance para la nueva métrica
        avance_comp = (comp_total / meta_comp * 100) if meta_comp > 0 else 0

        total_impactos = df_vista['impactos'].sum()
        marquilla_prom = np.average(df_vista['promedio_marquilla'], weights=df_vista['impactos']) if total_impactos > 0 else 0.0
        
        st.subheader(f"👨‍💼 Asesor Virtual para: {st.session_state.usuario}")
        # << MODIFICADO >> Se pasa el nuevo avance al generador de comentarios
        comentarios = generar_comentario_asesor(avance_ventas, avance_cobros, marquilla_prom, avance_comp)
        for comentario in comentarios: st.markdown(f"- {comentario}")

    st.subheader("Métricas Clave del Periodo")
    # << MODIFICADO >> Se cambia a 4 columnas para la nueva métrica
    col1, col2, col3, col4 = st.columns(4)
    meta_marquilla = APP_CONFIG['kpi_goals']['meta_marquilla']
    
    col1.metric("Ventas Totales", f"${ventas_total:,.0f}", f"{ventas_total - meta_ventas:,.0f} vs Meta")
    col1.progress(min(avance_ventas / 100, 1.0), text=f"Avance Ventas: {avance_ventas:.1f}%")
    
    col2.metric("Recaudo de Cartera", f"${cobros_total:,.0f}", f"{cobros_total - meta_cobros:,.0f} vs Meta")
    col2.progress(min(avance_cobros / 100, 1.0), text=f"Avance Cartera: {avance_cobros:.1f}%")

    # << NUEVO >> Se añade la métrica de Complementarios en la nueva columna
    col3.metric("Venta Complementarios", f"${comp_total:,.0f}", f"{comp_total - meta_comp:,.0f} vs Meta")
    col3.progress(min(avance_comp / 100, 1.0), text=f"Avance: {avance_comp:.1f}%")
    
    col4.metric("Promedio Marquilla", f"{marquilla_prom:.2f}", f"{marquilla_prom - meta_marquilla:.2f} vs Meta")
    col4.progress(min((marquilla_prom / meta_marquilla), 1.0) if marquilla_prom > 0 else 0, text=f"Meta: {meta_marquilla}")

    st.subheader("Desglose por Vendedor / Grupo")
    # << MODIFICADO >> Se añaden las nuevas columnas al dataframe de desglose
    cols_desglose = ['Estatus', 'nomvendedor', 'ventas_totales', 'presupuesto', 'ventas_complementarios', 'presupuesto_complementarios', 'cobros_totales', 'presupuestocartera', 'impactos', 'promedio_marquilla']
    st.dataframe(df_vista[cols_desglose],
        column_config={
            "Estatus": st.column_config.TextColumn("🚦", width="small"), "nomvendedor": "Vendedor/Grupo",
            "ventas_totales": st.column_config.NumberColumn("Ventas", format="$ %d"), 
            "presupuesto": st.column_config.NumberColumn("Meta Ventas", format="$ %d"),
            "ventas_complementarios": st.column_config.NumberColumn("Venta Comp.", format="$ %d"),
            "presupuesto_complementarios": st.column_config.NumberColumn("Meta Comp.", format="$ %d"),
            "cobros_totales": st.column_config.NumberColumn("Recaudo", format="$ %d"),
            "presupuestocartera": st.column_config.NumberColumn("Meta Recaudo", format="$ %d"),
            "impactos": st.column_config.NumberColumn("Clientes Únicos", format="%d"),
            "promedio_marquilla": st.column_config.ProgressColumn("Prom. Marquilla", format="%.2f", min_value=0, max_value=len(APP_CONFIG['marquillas_clave']))
        },
        use_container_width=True, hide_index=True)

    render_analisis_detallado(df_vista, df_ventas_periodo)

# ==============================================================================
# 4. LÓGICA DE AUTENTICACIÓN Y EJECUCIÓN PRINCIPAL
# ==============================================================================
# (Esta sección no requiere cambios)
def main():
    """Función principal que controla el flujo de la aplicación."""
    st.sidebar.image(APP_CONFIG["url_logo"], use_container_width=True)
    st.sidebar.header("Control de Acceso")

    if 'autenticado' not in st.session_state: st.session_state.autenticado = False

    if not st.session_state.autenticado:
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
        usuarios = usuarios_fijos.copy(); codigo = 1001
        for u in todos_usuarios:
            if u not in usuarios: usuarios[u] = str(codigo); codigo += 1
        
        usuario_seleccionado = st.sidebar.selectbox("Seleccione su usuario", options=todos_usuarios)
        clave = st.sidebar.text_input("Contraseña", type="password")

        if st.sidebar.button("Ingresar"):
            if usuario_seleccionado in usuarios and clave == usuarios[usuario_seleccionado]:
                st.session_state.autenticado = True
                st.session_state.usuario = usuario_seleccionado
                with st.spinner('Cargando datos maestros, por favor espere...'):
                    st.session_state.df_ventas = cargar_y_limpiar_datos(APP_CONFIG["dropbox_paths"]["ventas"], APP_CONFIG["column_names"]["ventas"])
                    st.session_state.df_cobros = cargar_y_limpiar_datos(APP_CONFIG["dropbox_paths"]["cobros"], APP_CONFIG["column_names"]["cobros"])
                    st.session_state.APP_CONFIG = APP_CONFIG
                    st.session_state.DATA_CONFIG = DATA_CONFIG
                    st.session_state.calcular_marquilla_optimizado = calcular_marquilla_optimizado
                st.rerun()
            else:
                st.sidebar.error("Usuario o contraseña incorrectos")
        
        st.title("Plataforma de Inteligencia de Negocios"); st.image(APP_CONFIG["url_logo"], width=400)
        st.header("Bienvenido"); st.info("Por favor, utilice el panel de la izquierda para ingresar sus credenciales de acceso.")
    
    else:
        render_dashboard()
        if st.sidebar.button("Salir"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

if __name__ == '__main__':
    main()
