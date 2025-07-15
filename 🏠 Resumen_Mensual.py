import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import dropbox
import io
import unicodedata
import time # Importamos la librería time para dar feedback visual al usuario

# ==============================================================================
# 1. CONFIGURACIÓN CENTRALIZADA (Con un nuevo parámetro para descuentos)
# ==============================================================================
APP_CONFIG = {
    "page_title": "Resumen Mensual | Tablero de Ventas",
    "url_logo": "https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png",
    "dropbox_paths": {"ventas": "/data/ventas_detalle.csv", "cobros": "/data/cobros_detalle.csv"},
    "column_names": {
        "ventas": ['anio', 'mes', 'fecha_venta', 'Serie', 'TipoDocumento', 'codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_cliente', 'codigo_articulo', 'nombre_articulo', 'categoria_producto', 'linea_producto', 'marca_producto', 'valor_venta', 'unidades_vendidas', 'costo_unitario', 'super_categoria'],
        "cobros": ['anio', 'mes', 'fecha_cobro', 'codigo_vendedor', 'valor_cobro']
    },
    "kpi_goals": {"meta_marquilla": 2.4},
    "marquillas_clave": ['VINILTEX', 'KORAZA', 'ESTUCOMASTIC', 'VINILICO'],
    "complementarios": {"exclude_super_categoria": "Pintuco", "presupuesto_pct": 0.10},
    "sub_meta_complementarios": {"nombre_marca_objetivo": "non-AN Third Party", "presupuesto_pct": 0.10},
    "categorias_clave_venta": ['ABRACOL', 'YALE', 'SAINT GOBAIN', 'GOYA', 'ALLEGION', 'SEGUREX'],
    "presupuesto_mostradores": {"incremento_anual_pct": 0.10},
    "discount_keywords": ["DESCUENTOS COMERCIAL", "DSCTO COMERCIAL", "DCTO COMERCIAL", "DESCUENTO COMERCIAL"] 
}
DATA_CONFIG = {
    "presupuestos": {'154033':{'presupuesto':123873239, 'presupuestocartera':97569726}, '154044':{'presupuesto':80000000, 'presupuestocartera':300000000}, '154034':{'presupuesto':82753045, 'presupuestocartera':89446836}, '154014':{'presupuesto':268214737, 'presupuestocartera':324928043}, '154046':{'presupuesto':85469798, 'presupuestocartera':57798651}, '154012':{'presupuesto':246616193, 'presupuestocartera':293099708}, '154043':{'presupuesto':124885413, 'presupuestocartera':142269964}, '154035':{'presupuesto':80000000, 'presupuestocartera':300000000}, '154006':{'presupuesto':81250000, 'presupuestocartera':140820089}, '154049':{'presupuesto':56500000, 'presupuestocartera':56299929}, '154013':{'presupuesto':303422639, 'presupuestocartera':245098321}, '154011':{'presupuesto':447060250, 'presupuestocartera':465472631}, '154029':{'presupuesto':32500000, 'presupuestocartera':15128410}, '154040':{'presupuesto':0, 'presupuestocartera':0},'154053':{'presupuesto':0, 'presupuestocartera':0},'154048':{'presupuesto':0, 'presupuestocartera':0},'154042':{'presupuesto':0, 'presupuestocartera':0},'154031':{'presupuesto':0, 'presupuestocartera':0},'154039':{'presupuesto':0, 'presupuestocartera':0},'154051':{'presupuesto':0, 'presupuestocartera':0},'154008':{'presupuesto':0, 'presupuestocartera':0},'154052':{'presupuesto':0, 'presupuestocartera':0},'154050':{'presupuesto':0, 'presupuestocartera':0}},
    "grupos_vendedores": {"MOSTRADOR PEREIRA": ["ALEJANDRO CARBALLO MARQUEZ", "GEORGINA A. GALVIS HERRERA"], "MOSTRADOR ARMENIA": ["CRISTIAN CAMILO RENDON MONTES", "FANDRY JOHANA ABRIL PENHA", "JAVIER ORLANDO PATINO HURTADO"], "MOSTRADOR MANIZALES": ["DAVID FELIPE MARTINEZ RIOS", "JHON JAIRO CASTAÑO MONTES"], "MOSTRADOR LAURELES": ["MAURICIO RIOS MORALES"], "MOSTRADOR OPALO": ["MARIA PAULA DEL JESUS GALVIS HERRERA"]},
    "mapeo_meses": {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"},
    "mapeo_marcas": {50:"P8-ASC-MEGA", 54:"MPY-International", 55:"DPP-AN COLORANTS LATAM", 56:"DPP-Pintuco Profesional", 57:"ASC-Mega", 58:"DPP-Pintuco", 59:"DPP-Madetec", 60:"POW-Interpon", 61:"various", 62:"DPP-ICO", 63:"DPP-Terinsa", 64:"MPY-Pintuco", 65:"non-AN Third Party", 66:"ICO-AN Packaging", 67:"ASC-Automotive OEM", 68:"POW-Resicoat", 73:"DPP-Coral", 91:"DPP-Sikkens"}
}

st.set_page_config(page_title=APP_CONFIG["page_title"], page_icon="🏠", layout="wide", initial_sidebar_state="expanded")

# Estilos CSS para el botón de actualización.
st.markdown("""
<style>
    /* Estilo para el botón de actualización para hacerlo más grande y visible */
    div[data-testid="stButton"] > button[kind="primary"] {
        height: 3em;
        font-size: 1.2em;
        font-weight: bold;
        border: 2px solid #FF4B4B;
        background-color: #FF4B4B;
        color: white;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        border-color: #FF6B6B;
        background-color: #FF6B6B;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 2. LÓGICA DE PROCESAMIENTO DE DATOS
# ==============================================================================
def normalizar_texto(texto):
    if not isinstance(texto, str): return texto
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').strip().replace('  ', ' ') # Corregido doble espacio a uno simple
    except (TypeError, AttributeError): return texto

# Normaliza textos de la configuración una sola vez al inicio
APP_CONFIG['complementarios']['exclude_super_categoria'] = normalizar_texto(APP_CONFIG['complementarios']['exclude_super_categoria'])
APP_CONFIG['sub_meta_complementarios']['nombre_marca_objetivo'] = normalizar_texto(APP_CONFIG['sub_meta_complementarios']['nombre_marca_objetivo'])
APP_CONFIG['categorias_clave_venta'] = [normalizar_texto(cat) for cat in APP_CONFIG['categorias_clave_venta']]
# ✨ NUEVO: Normalizar las palabras clave de descuentos
APP_CONFIG['discount_keywords'] = [normalizar_texto(k) for k in APP_CONFIG['discount_keywords']]


@st.cache_data(ttl=1800)
def cargar_y_limpiar_datos(ruta_archivo, nombres_columnas):
    try:
        with dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, app_secret=st.secrets.dropbox.app_secret, oauth2_refresh_token=st.secrets.dropbox.refresh_token) as dbx:
            _, res = dbx.files_download(path=ruta_archivo)
            contenido_csv = res.content.decode('latin-1')
            df = pd.read_csv(io.StringIO(contenido_csv), header=None, sep=',', on_bad_lines='skip', dtype=str)
            if df.shape[1] != len(nombres_columnas):
                st.warning(f"Formato en {ruta_archivo}: Se esperaban {len(nombres_columnas)} columnas pero se encontraron {df.shape[1]}. Algunas columnas podrían faltar.")
                df = df.reindex(columns=range(len(nombres_columnas)))
            df.columns = nombres_columnas
            numeric_cols = ['anio', 'mes', 'valor_venta', 'valor_cobro', 'unidades_vendidas', 'costo_unitario', 'marca_producto']
            for col in numeric_cols:
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
            df.dropna(subset=['anio', 'mes'], inplace=True)
            df = df.astype({'anio': int, 'mes': int})
            if 'codigo_vendedor' in df.columns: df['codigo_vendedor'] = df['codigo_vendedor'].astype(str)
            if 'fecha_venta' in df.columns: df['fecha_venta'] = pd.to_datetime(df['fecha_venta'], errors='coerce')
            if 'marca_producto' in df.columns: df['nombre_marca'] = df['marca_producto'].map(DATA_CONFIG["mapeo_marcas"]).fillna('No Especificada')
            cols_a_normalizar = ['super_categoria', 'categoria_producto', 'nombre_marca', 'nomvendedor', 'TipoDocumento', 'nombre_articulo'] # Asegurarse de normalizar nombre_articulo
            for col in cols_a_normalizar:
                if col in df.columns: df[col] = df[col].apply(normalizar_texto)
            return df
    except Exception as e:
        st.error(f"Error crítico al cargar {ruta_archivo}: {e}")
        return pd.DataFrame(columns=nombres_columnas)

def calcular_marquilla_optimizado(df_periodo):
    if df_periodo.empty or 'nombre_articulo' not in df_periodo.columns:
        return pd.DataFrame(columns=['codigo_vendedor', 'nomvendedor', 'promedio_marquilla'])
    df_temp = df_periodo[['codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_articulo']].copy()
    df_temp['nombre_articulo'] = df_temp['nombre_articulo'].astype(str)
    for palabra in APP_CONFIG['marquillas_clave']:
        df_temp[palabra] = df_temp['nombre_articulo'].str.contains(palabra, case=False, na=False)
    df_cliente_marcas = df_temp.groupby(['codigo_vendedor', 'nomvendedor', 'cliente_id'])[APP_CONFIG['marquillas_clave']].any()
    df_cliente_marcas['puntaje_marquilla'] = df_cliente_marcas[APP_CONFIG['marquillas_clave']].sum(axis=1)
    df_final_marquilla = df_cliente_marcas.groupby(['codigo_vendedor', 'nomvendedor'])['puntaje_marquilla'].mean().reset_index()
    return df_final_marquilla.rename(columns={'puntaje_marquilla': 'promedio_marquilla'})

def procesar_datos_periodo(df_ventas_periodo, df_cobros_periodo, df_ventas_historicas, anio_sel, mes_sel):
    ### PASO 1: SEPARACIÓN DE MOVIMIENTOS Y CÁLCULOS BÁSICOS ###
    # Filtra los documentos operativos (Facturas y Albaranes)
    df_ventas_operativas = df_ventas_periodo[
        df_ventas_periodo['TipoDocumento'].str.contains('FACTURA|ALBARAN', na=False, case=False)
    ].copy()

    # ✨ NUEVO: Identificar las filas que son "DESCUENTOS COMERCIALES" por el nombre del artículo
    # y que tienen un valor negativo.
    # Usamos .any() para buscar cualquiera de las palabras clave de descuento en nombre_articulo
    is_commercial_discount_item = df_ventas_operativas['nombre_articulo'].apply(
        lambda x: any(kw in x for kw in APP_CONFIG['discount_keywords']) if isinstance(x, str) else False
    )

    df_descuentos_comerciales_identificados = df_ventas_operativas[
        is_commercial_discount_item & (df_ventas_operativas['valor_venta'] < 0)
    ].copy()

    # Calcular el total de estos descuentos comerciales identificados (en valor absoluto)
    resumen_descuentos = df_descuentos_comerciales_identificados.groupby(['codigo_vendedor', 'nomvendedor']).agg(
        descuentos_comerciales_totales=('valor_venta', lambda x: x.abs().sum())
    ).reset_index()

    # Crear el DataFrame para los cálculos de ventas "reales",
    # excluyendo explícitamente solo los "DESCUENTOS COMERCIALES" por artículo.
    # Otros movimientos negativos (devoluciones, anulaciones que NO son "descuentos comerciales")
    # seguirán afectando las ventas totales, como parece ser el comportamiento deseado.
    df_ventas_para_sumar = df_ventas_operativas[
        ~df_ventas_operativas.index.isin(df_descuentos_comerciales_identificados.index)
    ].copy()

    # Cálculos basados en df_ventas_para_sumar (Ventas brutas - devoluciones/anulaciones normales)
    resumen_ventas = df_ventas_para_sumar.groupby(['codigo_vendedor', 'nomvendedor']).agg(
        ventas_totales=('valor_venta', 'sum'),
        impactos=('cliente_id', 'nunique')
    ).reset_index()
    
    resumen_cobros = df_cobros_periodo.groupby('codigo_vendedor').agg(cobros_totales=('valor_cobro', 'sum')).reset_index()
    
    df_ventas_comp = df_ventas_para_sumar[df_ventas_para_sumar['super_categoria'] != APP_CONFIG['complementarios']['exclude_super_categoria']]
    resumen_complementarios = df_ventas_comp.groupby(['codigo_vendedor','nomvendedor']).agg(ventas_complementarios=('valor_venta', 'sum')).reset_index()
    
    marca_sub_meta = APP_CONFIG['sub_meta_complementarios']['nombre_marca_objetivo']
    df_ventas_sub_meta = df_ventas_para_sumar[df_ventas_para_sumar['nombre_marca'] == marca_sub_meta]
    resumen_sub_meta = df_ventas_sub_meta.groupby(['codigo_vendedor','nomvendedor']).agg(ventas_sub_meta=('valor_venta', 'sum')).reset_index()
    
    # Marquilla aún se calcula sobre todo el df_ventas_periodo para incluir todos los artículos vendidos
    # para el cálculo del promedio por cliente, incluso si luego se descuentan.
    resumen_marquilla = calcular_marquilla_optimizado(df_ventas_periodo)

    ### PASO 2: LÓGICA DE NETEO GLOBAL PARA ALBARANES HISTÓRICOS ###
    df_albaranes_historicos_bruto = df_ventas_historicas[df_ventas_historicas['TipoDocumento'].str.contains('ALBARAN', na=False, case=False)].copy()
    grouping_keys = ['Serie', 'cliente_id', 'codigo_articulo', 'codigo_vendedor']
    if not df_albaranes_historicos_bruto.empty:
        df_neto_historico = df_albaranes_historicos_bruto.groupby(grouping_keys).agg(valor_neto=('valor_venta', 'sum')).reset_index()
        df_grupos_cancelados_global = df_neto_historico[df_neto_historico['valor_neto'] == 0]
    else:
        df_grupos_cancelados_global = pd.DataFrame(columns=grouping_keys)

    ### PASO 3: LIMPIEZA DE ALBARANES DEL PERIODO ACTUAL ###
    df_albaranes_bruto_periodo = df_ventas_periodo[df_ventas_periodo['TipoDocumento'].str.contains('ALBARAN', na=False, case=False)].copy()
    if not df_albaranes_bruto_periodo.empty and not df_grupos_cancelados_global.empty:
        df_albaranes_reales_pendientes = df_albaranes_bruto_periodo.merge(
            df_grupos_cancelados_global[grouping_keys], on=grouping_keys, how='left', indicator=True
        ).query('_merge == "left_only"').drop(columns=['_merge'])
    else:
        df_albaranes_reales_pendientes = df_albaranes_bruto_periodo.copy()

    ### PASO 4: CÁLCULOS FINALES Y ENSAMBLAJE ###
    if not df_albaranes_reales_pendientes.empty:
        # Asegurarse de que solo sumamos albaranes con valor positivo para pendientes
        resumen_albaranes = df_albaranes_reales_pendientes[df_albaranes_reales_pendientes['valor_venta'] > 0].groupby(['codigo_vendedor', 'nomvendedor']).agg(albaranes_pendientes=('valor_venta', 'sum')).reset_index()
    else:
        resumen_albaranes = pd.DataFrame(columns=['codigo_vendedor', 'nomvendedor', 'albaranes_pendientes'])

    df_resumen = pd.merge(resumen_ventas, resumen_cobros, on='codigo_vendedor', how='left')
    df_resumen = pd.merge(df_resumen, resumen_descuentos, on=['codigo_vendedor', 'nomvendedor'], how='left') # ✨ NUEVO: Merge con el resumen de descuentos
    df_resumen = pd.merge(df_resumen, resumen_marquilla, on=['codigo_vendedor', 'nomvendedor'], how='left')
    df_resumen = pd.merge(df_resumen, resumen_complementarios, on=['codigo_vendedor', 'nomvendedor'], how='left')
    df_resumen = pd.merge(df_resumen, resumen_sub_meta, on=['codigo_vendedor', 'nomvendedor'], how='left')
    df_resumen = pd.merge(df_resumen, resumen_albaranes, on=['codigo_vendedor', 'nomvendedor'], how='left')

    presupuestos_fijos = DATA_CONFIG['presupuestos']
    df_resumen['presupuesto'] = df_resumen['codigo_vendedor'].map(lambda x: presupuestos_fijos.get(str(x), {}).get('presupuesto', 0))
    df_resumen['presupuestocartera'] = df_resumen['codigo_vendedor'].map(lambda x: presupuestos_fijos.get(str(x), {}).get('presupuestocartera', 0))
    df_resumen.fillna(0, inplace=True)
    
    registros_agrupados = []
    incremento_mostradores = 1 + APP_CONFIG['presupuesto_mostradores']['incremento_anual_pct']
    for grupo, lista_vendedores in DATA_CONFIG['grupos_vendedores'].items():
        lista_vendedores_norm = [normalizar_texto(v) for v in lista_vendedores]
        df_grupo_actual = df_resumen[df_resumen['nomvendedor'].isin(lista_vendedores_norm)]
        if not df_grupo_actual.empty:
            anio_anterior = anio_sel - 1
            
            # ✨ NUEVO: Al calcular el presupuesto histórico, también excluir los "descuentos comerciales" por artículo
            df_ventas_historicas_operativas = df_ventas_historicas[
                df_ventas_historicas['TipoDocumento'].str.contains('FACTURA|ALBARAN', na=False, case=False)
            ].copy()
            is_commercial_discount_item_hist = df_ventas_historicas_operativas['nombre_articulo'].apply(
                lambda x: any(kw in x for kw in APP_CONFIG['discount_keywords']) if isinstance(x, str) else False
            )
            df_descuentos_comerciales_articulo_hist = df_ventas_historicas_operativas[
                is_commercial_discount_item_hist & (df_ventas_historicas_operativas['valor_venta'] < 0)
            ].copy()

            df_ventas_hist_para_sumar_presupuesto = df_ventas_historicas_operativas[
                ~df_ventas_historicas_operativas.index.isin(df_descuentos_comerciales_articulo_hist.index)
            ].copy()

            df_grupo_historico_facturas = df_ventas_hist_para_sumar_presupuesto[
                (df_ventas_hist_para_sumar_presupuesto['anio'] == anio_anterior) & 
                (df_ventas_hist_para_sumar_presupuesto['mes'] == mes_sel) & 
                (df_ventas_hist_para_sumar_presupuesto['nomvendedor'].isin(lista_vendedores_norm))
            ]
            ventas_anio_anterior = df_grupo_historico_facturas['valor_venta'].sum() if not df_grupo_historico_facturas.empty else 0
            presupuesto_dinamico = ventas_anio_anterior * incremento_mostradores
            
            # Incluye 'descuentos_comerciales_totales' en las columnas a sumar para grupos
            cols_a_sumar = ['ventas_totales', 'cobros_totales', 'impactos', 'presupuestocartera', 'ventas_complementarios', 'ventas_sub_meta', 'albaranes_pendientes', 'descuentos_comerciales_totales']
            suma_grupo = df_grupo_actual[cols_a_sumar].sum().to_dict()
            total_impactos = df_grupo_actual['impactos'].sum()
            promedio_marquilla_grupo = np.average(df_grupo_actual['promedio_marquilla'], weights=df_grupo_actual['impactos']) if total_impactos > 0 else 0.0
            
            suma_grupo['presupuesto'] = df_grupo_actual['presupuesto'].sum()
            registro = {'nomvendedor': normalizar_texto(grupo), 'codigo_vendedor': normalizar_texto(grupo), **suma_grupo, 'promedio_marquilla': promedio_marquilla_grupo}
            
            if presupuesto_dinamico > 0:
                registro['presupuesto'] = presupuesto_dinamico

            registros_agrupados.append(registro)
            
    df_agrupado = pd.DataFrame(registros_agrupados)
    vendedores_en_grupos = [v for lista in DATA_CONFIG['grupos_vendedores'].values() for v in [normalizar_texto(i) for i in lista]]
    df_individuales = df_resumen[~df_resumen['nomvendedor'].isin(vendedores_en_grupos)]
    df_final = pd.concat([df_agrupado, df_individuales], ignore_index=True)
    df_final.fillna(0, inplace=True)
    df_final['presupuesto_complementarios'] = df_final['presupuesto'] * APP_CONFIG['complementarios']['presupuesto_pct']
    df_final['presupuesto_sub_meta'] = df_final['presupuesto_complementarios'] * APP_CONFIG['sub_meta_complementarios']['presupuesto_pct']
    
    return df_final, df_albaranes_reales_pendientes

# ==============================================================================
# 3. LÓGICA DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================
def generar_comentario_asesor(avance_v, avance_c, marquilla_p, avance_comp, avance_sub_meta):
    comentarios = []
    if avance_v >= 100: comentarios.append("📈 **Ventas:** ¡Felicitaciones! Has superado la meta de ventas.")
    elif avance_v >= 80: comentarios.append("📈 **Ventas:** ¡Estás muy cerca de la meta! Un último esfuerzo.")
    else: comentarios.append("📈 **Ventas:** Planifica tus visitas y aprovecha cada oportunidad.")
    if avance_c >= 100: comentarios.append("💰 **Cartera:** Objetivo de recaudo cumplido. ¡Gestión impecable!")
    else: comentarios.append("💰 **Cartera:** Recuerda hacer seguimiento a la cartera pendiente.")
    if avance_comp >= 100: comentarios.append("⚙️ **Complementarios:** ¡Excelente! Cumpliste la meta de venta de complementarios.")
    else: comentarios.append(f"⚙️ **Complementarios:** Tu avance es del {avance_comp:.1f}%. ¡Impulsa la venta cruzada!**")
    sub_meta_label = APP_CONFIG['sub_meta_complementarios']['nombre_marca_objetivo']
    if avance_sub_meta >= 100: comentarios.append(f"🎯 **Meta Específica:** ¡Logrado! Superaste la meta de venta de '{sub_meta_label}'.")
    else: comentarios.append(f"🎯 **Meta Específica:** Tu avance en '{sub_meta_label}' es del {avance_sub_meta:.1f}%. ¡Hay una gran oportunidad ahí!")
    if marquilla_p >= APP_CONFIG['kpi_goals']['meta_marquilla']: comentarios.append(f"🎨 **Marquilla:** Tu promedio de {marquilla_p:.2f} es excelente.")
    elif marquilla_p > 0: comentarios.append(f"🎨 **Marquilla:** Tu promedio es {marquilla_p:.2f}. Hay oportunidad de crecimiento.")
    else: comentarios.append("🎨 **Marquilla:** Aún no registras ventas en las marcas clave.")
    return comentarios

def render_analisis_detallado(df_vista, df_ventas_periodo):
    st.markdown("---")
    st.header("🔬 Análisis Detallado del Periodo")
    opciones_enfoque = ["Visión General"] + sorted(df_vista['nomvendedor'].unique())
    enfoque_sel = st.selectbox("Enfocar análisis en:", opciones_enfoque, index=0, key="sb_enfoque_analisis")
    
    # Pre-filtrar las ventas operativas para el periodo
    df_ventas_operativas_periodo = df_ventas_periodo[
        df_ventas_periodo['TipoDocumento'].str.contains('FACTURA|ALBARAN', na=False, case=False)
    ].copy()

    # Identificar y excluir los "DESCUENTOS COMERCIALES" por artículo para el análisis detallado
    is_commercial_discount_item_analysis = df_ventas_operativas_periodo['nombre_articulo'].apply(
        lambda x: any(kw in x for kw in APP_CONFIG['discount_keywords']) if isinstance(x, str) else False
    )
    df_ventas_filtradas_para_analisis = df_ventas_operativas_periodo[
        ~df_ventas_operativas_periodo.index.isin(
            df_ventas_operativas_periodo[is_commercial_discount_item_analysis & (df_ventas_operativas_periodo['valor_venta'] < 0)].index
        )
    ].copy()

    if enfoque_sel == "Visión General":
        nombres_a_filtrar = []
        for vendedor in df_vista['nomvendedor']:
            vendedor_norm = normalizar_texto(vendedor)
            nombre_grupo_orig = next((k for k in DATA_CONFIG['grupos_vendedores'] if normalizar_texto(k) == vendedor_norm), vendedor_norm)
            lista_vendedores = DATA_CONFIG['grupos_vendedores'].get(nombre_grupo_orig, [vendedor_norm])
            nombres_a_filtrar.extend([normalizar_texto(v) for v in lista_vendedores])
        
        # Usar el DataFrame ya filtrado para el análisis
        df_ventas_enfocadas = df_ventas_filtradas_para_analisis[df_ventas_filtradas_para_analisis['nomvendedor'].isin(nombres_a_filtrar)]
        df_ranking = df_vista
    else:
        enfoque_sel_norm = normalizar_texto(enfoque_sel)
        nombre_grupo_orig = next((k for k in DATA_CONFIG['grupos_vendedores'] if normalizar_texto(k) == enfoque_sel_norm), enfoque_sel_norm)
        nombres_a_filtrar = [normalizar_texto(n) for n in DATA_CONFIG['grupos_vendedores'].get(nombre_grupo_orig, [enfoque_sel_norm])]
        
        # Usar el DataFrame ya filtrado para el análisis
        df_ventas_enfocadas = df_ventas_filtradas_para_analisis[df_ventas_filtradas_para_analisis['nomvendedor'].isin(nombres_a_filtrar)]
        df_ranking = df_vista[df_vista['nomvendedor'] == enfoque_sel_norm]
        
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
            if not df_ventas_enfocadas.empty and 'nombre_articulo' in df_ventas_enfocadas:
                # La marquilla debe seguir considerando el nombre_articulo para el conteo de impacto,
                # pero las ventas mostradas aquí deben ser consistentes con df_ventas_enfocadas
                ventas_marquillas = {p: df_ventas_enfocadas[df_ventas_enfocadas['nombre_articulo'].str.contains(p, case=False, na=False)]['valor_venta'].sum() for p in APP_CONFIG['marquillas_clave']}
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
            # df_ventas_enfocadas ya está pre-filtrado y excluye descuentos comerciales específicos
            top_clientes = df_ventas_enfocadas.groupby('nombre_cliente')['valor_venta'].sum().nlargest(10).reset_index()
            st.dataframe(top_clientes, column_config={"nombre_cliente": "Cliente", "valor_venta": st.column_config.NumberColumn("Total Compra", format="$ %d")}, use_container_width=True, hide_index=True)
        else: st.info("No hay datos de clientes para este periodo.")
    with tab4:
        st.subheader(f"Desempeño en Categorías Clave para: {enfoque_sel}")
        categorias_objetivo = sorted(list(set(APP_CONFIG['categorias_clave_venta'])))
        df_ventas_cat = df_ventas_enfocadas[df_ventas_enfocadas['categoria_producto'].isin(categorias_objetivo)]
        if df_ventas_cat.empty:
            st.info("No se encontraron ventas en las categorías clave para la selección actual.")
        else:
            col1, col2 = st.columns([0.5, 0.5])
            with col1:
                st.markdown("##### Ventas por Categoría")
                resumen_cat = df_ventas_cat.groupby('categoria_producto').agg(Ventas=('valor_venta', 'sum')).reset_index()
                total_ventas_enfocadas_positivas = df_ventas_enfocadas['valor_venta'].sum()
                if total_ventas_enfocadas_positivas > 0: resumen_cat['Participacion (%)'] = (resumen_cat['Ventas'] / total_ventas_enfocadas_positivas) * 100
                else: resumen_cat['Participacion (%)'] = 0
                resumen_cat = resumen_cat.sort_values('Ventas', ascending=False)
                st.dataframe(resumen_cat, column_config={"categoria_producto": "Categoría", "Ventas": st.column_config.NumberColumn("Total Venta", format="$ %d"),"Participacion (%)": st.column_config.ProgressColumn("Part. sobre Venta Total", format="%.2f%%", min_value=0, max_value=resumen_cat['Participacion (%)'].max())}, use_container_width=True, hide_index=True)
            with col2:
                st.markdown("##### Distribución de Ventas")
                fig = px.pie(resumen_cat, names='categoria_producto', values='Ventas', title="Distribución entre Categorías Clave", hole=0.4)
                fig.update_traces(textinfo='percent+label', textposition='inside')
                st.plotly_chart(fig, use_container_width=True)

def render_dashboard():
    st.sidebar.markdown("---")
    st.sidebar.header("Filtros de Periodo")

    df_ventas_historicas = st.session_state.df_ventas
    df_cobros_historicos = st.session_state.df_cobros
    
    if 'anio' not in df_ventas_historicas.columns or df_ventas_historicas.empty:
        st.error("No hay datos históricos de ventas para analizar.")
        return

    lista_anios = sorted(df_ventas_historicas['anio'].unique(), reverse=True)
    anio_reciente = int(df_ventas_historicas['anio'].max())
    mes_reciente = int(df_ventas_historicas[df_ventas_historicas['anio'] == anio_reciente]['mes'].max())
    anio_sel = st.sidebar.selectbox("Elija el Año", lista_anios, index=0, key="sb_anio")
    lista_meses_num = sorted(df_ventas_historicas[df_ventas_historicas['anio'] == anio_sel]['mes'].unique())
    
    if not lista_meses_num:
        st.warning(f"No hay datos de ventas para el año {anio_sel}.")
        return
        
    index_mes_defecto = lista_meses_num.index(mes_reciente) if anio_sel == anio_reciente and mes_reciente in lista_meses_num else 0
    mes_sel_num = st.sidebar.selectbox("Elija el Mes", options=lista_meses_num, format_func=lambda x: DATA_CONFIG['mapeo_meses'].get(x, 'N/A'), index=index_mes_defecto, key="sb_mes")

    df_ventas_periodo = df_ventas_historicas[(df_ventas_historicas['anio'] == anio_sel) & (df_ventas_historicas['mes'] == mes_sel_num)]
    
    if df_ventas_periodo.empty:
        st.warning("No se encontraron datos de ventas para el periodo seleccionado.")
    else:
        df_cobros_periodo = df_cobros_historicos[(df_cobros_historicos['anio'] == anio_sel) & (df_cobros_historicos['mes'] == mes_sel_num)]
        df_resumen_final, df_albaranes_pendientes = procesar_datos_periodo(df_ventas_periodo, df_cobros_periodo, df_ventas_historicas, anio_sel, mes_sel_num)
        
        usuario_actual_norm = normalizar_texto(st.session_state.usuario)
        if usuario_actual_norm == "GERENTE":
            lista_filtro = sorted(df_resumen_final['nomvendedor'].unique())
            vendedores_sel = st.sidebar.multiselect("Filtrar Vendedores/Grupos", options=lista_filtro, default=lista_filtro, key="ms_vendedores")
            df_vista = df_resumen_final[df_resumen_final['nomvendedor'].isin(vendedores_sel)]
        else:
            df_vista = df_resumen_final[df_resumen_final['nomvendedor'] == usuario_actual_norm]
        
        if df_vista.empty:
            st.warning("No hay datos disponibles para la selección de usuario/grupo actual.")
        else:
            def asignar_estatus(row):
                if row['presupuesto'] > 0:
                    avance = (row['ventas_totales'] / row['presupuesto']) * 100
                    if avance >= 95: return "🟢 En Objetivo"
                    if avance >= 70: return "🟡 Cerca del Objetivo"
                return "🔴 Necesita Atención"
            df_vista['Estatus'] = df_vista.apply(asignar_estatus, axis=1)

            st.title("🏠 Resumen de Rendimiento")
            st.header(f"{DATA_CONFIG['mapeo_meses'].get(mes_sel_num, '')} {anio_sel}")

            # BOTÓN DE ACTUALIZACIÓN FORZADA
            if st.button("🔄 ¡Actualizar Todos los Datos!", type="primary", use_container_width=True, help="Fuerza la recarga de los archivos desde Dropbox. Útil si los datos se actualizaron recientemente."):
                st.cache_data.clear()
                if 'df_ventas' in st.session_state:
                    del st.session_state.df_ventas
                if 'df_cobros' in st.session_state:
                    del st.session_state.df_cobros
                st.toast("Limpiando caché y recargando datos... ¡Un momento!", icon="⏳")
                time.sleep(3)
                st.rerun()

            vista_para = st.session_state.usuario if len(df_vista['nomvendedor'].unique()) == 1 else 'Múltiples Seleccionados'
            st.markdown(f"**Vista para:** `{vista_para}`")
            
            ventas_total = df_vista['ventas_totales'].sum(); meta_ventas = df_vista['presupuesto'].sum()
            cobros_total = df_vista['cobros_totales'].sum(); meta_cobros = df_vista['presupuestocartera'].sum()
            comp_total = df_vista['ventas_complementarios'].sum(); meta_comp = df_vista['presupuesto_complementarios'].sum()
            sub_meta_total = df_vista['ventas_sub_meta'].sum(); meta_sub_meta = df_vista['presupuesto_sub_meta'].sum()
            total_albaranes = df_vista['albaranes_pendientes'].sum()
            # ✨ NUEVO: Suma de los descuentos comerciales totales
            total_descuentos_comerciales = df_vista['descuentos_comerciales_totales'].sum()
            
            avance_ventas = (ventas_total / meta_ventas * 100) if meta_ventas > 0 else 0
            avance_cobros = (cobros_total / meta_cobros * 100) if meta_cobros > 0 else 0
            avance_comp = (comp_total / meta_comp * 100) if meta_comp > 0 else 0
            avance_sub_meta = (sub_meta_total / meta_sub_meta * 100) if meta_sub_meta > 0 else 0
            
            total_impactos = df_vista['impactos'].sum()
            marquilla_prom = np.average(df_vista['promedio_marquilla'], weights=df_vista['impactos']) if total_impactos > 0 else 0.0
            meta_marquilla = APP_CONFIG['kpi_goals']['meta_marquilla']
            
            with st.container(border=True):
                st.subheader(f"👨‍💼 Asesor Virtual para: {st.session_state.usuario}")
                comentarios = generar_comentario_asesor(avance_ventas, avance_cobros, marquilla_prom, avance_comp, avance_sub_meta)
                for comentario in comentarios: st.markdown(f"- {comentario}")

            st.subheader("Métricas Clave del Periodo")
            
            # ✨ NUEVO: Añadida una cuarta columna para Descuentos Comerciales
            col1, col2, col3, col_descuentos = st.columns(4) 
            with col1:
                st.metric("Ventas Reales (Facturadas)", f"${ventas_total:,.0f}", f"{ventas_total - meta_ventas:,.0f} vs Meta")
                st.progress(min(avance_ventas / 100, 1.0), text=f"Avance Ventas: {avance_ventas:.1f}%")
            with col2:
                st.metric("Recaudo de Cartera", f"${cobros_total:,.0f}", f"{cobros_total - meta_cobros:,.0f} vs Meta")
                st.progress(min(avance_cobros / 100, 1.0), text=f"Avance Cartera: {avance_cobros:.1f}%")
            with col3:
                st.metric("Valor Albaranes Pendientes", f"${total_albaranes:,.0f}", "Mercancía por facturar")
                st.progress(0, text="Gestión de remisiones")
            with col_descuentos: # Nueva columna para descuentos
                st.metric("Descuentos Comerciales", f"${total_descuentos_comerciales:,.0f}", "Valor de descuentos específicos")
                st.progress(0, text="Impacto en el margen") # Barra de progreso neutra, ya que es un valor informativo
            
            col4, col5, col6 = st.columns(3)
            with col4:
                st.metric("Venta Complementarios", f"${comp_total:,.0f}", f"{comp_total - meta_comp:,.0f} vs Meta")
                st.progress(min(avance_comp / 100, 1.0), text=f"Avance: {avance_comp:.1f}%")
            with col5:
                sub_meta_label = APP_CONFIG['sub_meta_complementarios']['nombre_marca_objetivo']
                st.metric(f"Meta Específica ({sub_meta_label})", f"${sub_meta_total:,.0f}", f"{sub_meta_total - meta_sub_meta:,.0f} vs Meta")
                st.progress(min(avance_sub_meta / 100, 1.0), text=f"Avance: {avance_sub_meta:.1f}%")
            with col6:
                st.metric("Promedio Marquilla", f"{marquilla_prom:.2f}", f"{marquilla_prom - meta_marquilla:.2f} vs Meta")
                st.progress(min((marquilla_prom / meta_marquilla), 1.0) if meta_marquilla > 0 else 0, text=f"Meta: {meta_marquilla:.2f}")

            st.markdown("---")
            st.subheader("Desglose por Vendedor / Grupo")
            # ✨ NUEVO: Añadir 'descuentos_comerciales_totales' a la lista de columnas a mostrar
            cols_desglose = ['Estatus', 'nomvendedor', 'ventas_totales', 'presupuesto', 'cobros_totales', 'presupuestocartera', 'descuentos_comerciales_totales', 'albaranes_pendientes', 'impactos', 'promedio_marquilla']
            st.dataframe(df_vista[cols_desglose], column_config={
                "Estatus": st.column_config.TextColumn("🚦", width="small"), 
                "nomvendedor": "Vendedor/Grupo", 
                "ventas_totales": st.column_config.NumberColumn("Ventas Reales", format="$ %d"), 
                "presupuesto": st.column_config.NumberColumn("Meta Ventas", format="$ %d"),
                "cobros_totales": st.column_config.NumberColumn("Recaudo", format="$ %d"),
                "presupuestocartera": st.column_config.NumberColumn("Meta Recaudo", format="$ %d"),
                "descuentos_comerciales_totales": st.column_config.NumberColumn("Dsctos. Comerciales", format="$ %d"), # Configuración de columna para descuentos
                "albaranes_pendientes": st.column_config.NumberColumn("Valor Albaranes", format="$ %d"),
                "impactos": st.column_config.NumberColumn("Clientes Únicos", format="%d"),
                "promedio_marquilla": st.column_config.ProgressColumn("Prom. Marquilla", format="%.2f", min_value=0, max_value=len(APP_CONFIG['marquillas_clave']))
            }, use_container_width=True, hide_index=True)

            render_analisis_detallado(df_vista, df_ventas_periodo)

            st.markdown("---")
            st.header("📄 Detalle de Albaranes Pendientes por Facturar (Neto)")
            vendedores_vista_actual = df_vista['nomvendedor'].unique()
            nombres_a_filtrar = []
            for vendedor in vendedores_vista_actual:
                vendedor_norm = normalizar_texto(vendedor)
                nombre_grupo_orig = next((k for k in DATA_CONFIG['grupos_vendedores'] if normalizar_texto(k) == vendedor_norm), vendedor_norm)
                lista_vendedores = DATA_CONFIG['grupos_vendedores'].get(nombre_grupo_orig, [vendedor_norm])
                nombres_a_filtrar.extend([normalizar_texto(v) for v in lista_vendedores])
            df_albaranes_vista = df_albaranes_pendientes[df_albaranes_pendientes['nomvendedor'].isin(nombres_a_filtrar)]
            df_albaranes_a_mostrar = df_albaranes_vista[df_albaranes_vista['valor_venta'] > 0]

            if df_albaranes_a_mostrar.empty:
                st.info("No hay albaranes pendientes de facturación para la selección actual en este periodo.")
            else:
                st.dataframe(df_albaranes_a_mostrar[['Serie', 'fecha_venta', 'nombre_cliente', 'valor_venta', 'nomvendedor']], 
                    column_config={
                        "Serie": "Documento",
                        "fecha_venta": "Fecha",
                        "nombre_cliente": "Cliente",
                        "valor_venta": st.column_config.NumberColumn("Valor Pendiente", format="$ %d"),
                        "nomvendedor": "Vendedor"
                    }, use_container_width=True, hide_index=True
                )

# ==============================================================================
# 4. LÓGICA DE AUTENTICACIÓN Y EJECUCIÓN PRINCIPAL
# ==============================================================================
def main():
    # --- PASO 1: Cargar los datos una sola vez por sesión ---
    if 'df_ventas' not in st.session_state:
        with st.spinner('Cargando datos maestros, por favor espere...'):
            st.session_state.df_ventas = cargar_y_limpiar_datos(APP_CONFIG["dropbox_paths"]["ventas"], APP_CONFIG["column_names"]["ventas"])
            st.session_state.df_cobros = cargar_y_limpiar_datos(APP_CONFIG["dropbox_paths"]["cobros"], APP_CONFIG["column_names"]["cobros"])
            st.session_state['APP_CONFIG'] = APP_CONFIG
            st.session_state['DATA_CONFIG'] = DATA_CONFIG
    
    st.sidebar.image(APP_CONFIG["url_logo"], use_container_width=True)
    st.sidebar.header("Control de Acceso")
    
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False

    # --- PASO 2: Lógica de autenticación ---
    if not st.session_state.autenticado:
        df_para_usuarios = st.session_state.get('df_ventas', pd.DataFrame())
        
        @st.cache_data
        def obtener_lista_usuarios(df_ventas_cache):
            if not df_ventas_cache.empty and 'nomvendedor' in df_ventas_cache.columns:
                grupos_orig = list(DATA_CONFIG['grupos_vendedores'].keys())
                vendedores_en_grupos_norm = [normalizar_texto(v) for lista in DATA_CONFIG['grupos_vendedores'].values() for v in lista]
                vendedores_unicos_df = df_ventas_cache['nomvendedor'].dropna().unique()
                mapa_norm_a_orig = {normalizar_texto(v): v for v in vendedores_unicos_df}
                vendedores_solos_norm = [v_norm for v_norm in [normalizar_texto(v) for v in vendedores_unicos_df] if v_norm not in vendedores_en_grupos_norm]
                vendedores_solos_orig = sorted([mapa_norm_a_orig.get(v_norm) for v_norm in vendedores_solos_norm if mapa_norm_a_orig.get(v_norm)])
                return ["GERENTE"] + sorted(grupos_orig) + vendedores_solos_orig
            return ["GERENTE"] + list(DATA_CONFIG['grupos_vendedores'].keys())

        todos_usuarios = obtener_lista_usuarios(df_para_usuarios)
        
        usuarios_fijos_orig = {"GERENTE": "1234", "MOSTRADOR PEREIRA": "2345", "MOSTRADOR ARMENIA": "3456", "MOSTRADOR MANIZALES": "4567", "MOSTRADOR LAURELES": "5678"}
        if "MOSTRADOR OPALO" not in usuarios_fijos_orig: usuarios_fijos_orig["MOSTRADOR OPALO"] = "opalo123"
        usuarios = {normalizar_texto(k): v for k, v in usuarios_fijos_orig.items()}
        codigo = 1001
        for u in todos_usuarios:
            u_norm = normalizar_texto(u)
            if u_norm not in usuarios: usuarios[u_norm] = str(codigo); codigo += 1
            
        usuario_seleccionado = st.sidebar.selectbox("Seleccione su usuario", options=todos_usuarios, key="sb_login_user")
        clave = st.sidebar.text_input("Contraseña", type="password", key="txt_login_pass")

        if st.sidebar.button("Ingresar", key="btn_login"):
            usuario_sel_norm = normalizar_texto(usuario_seleccionado)
            if usuario_sel_norm in usuarios and clave == usuarios[usuario_sel_norm]:
                st.session_state.autenticado = True
                st.session_state.usuario = usuario_seleccionado
                st.rerun() 
            else:
                st.sidebar.error("Usuario o contraseña incorrectos")
        
        st.title("Plataforma de Inteligencia de Negocios")
        st.image(APP_CONFIG["url_logo"], width=400)
        st.header("Bienvenido")
        st.info("Por favor, utilice el panel de la izquierda para ingresar sus credenciales de acceso.")

    # --- PASO 3: Si ya está autenticado, renderiza el dashboard ---
    else:
        render_dashboard()
        if st.sidebar.button("Salir", key="btn_logout"):
            # Limpia TODA la sesión para un logout seguro y completo
            keys_to_clear = list(st.session_state.keys())
            for key in keys_to_clear:
                del st.session_state[key]
            st.rerun()

if __name__ == '__main__':
    main()
