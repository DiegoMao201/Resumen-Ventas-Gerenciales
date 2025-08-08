# ==============================================================================
# SCRIPT COMPLETO Y DEFINITIVO PARA: 🏠 Resumen Mensual.py
# VERSIÓN FINAL: 08 de Agosto, 2025 (MEJORAS DE VISUALIZACIÓN Y EXPORTACIÓN)
# DESCRIPCIÓN: Se ajusta la lógica de agrupación para la descarga de albaranes.
#              Un albarán único se define por la combinación de Fecha, Cliente,
#              Serie y Vendedor, solucionando el problema de series repetidas.
#
# MODIFICACIÓN (07 de Agosto, 2025): Se reemplaza el cálculo de Marquilla por
#              el nuevo análisis de oportunidades basado en el reporte CL4.
#
# MODIFICACIÓN (08 de Agosto, 2025): Se añade la columna NIT a la vista de 
#              oportunidades y se crea una función para descargar un reporte 
#              de oportunidades en Excel con formato condicional.
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import dropbox
import io
import unicodedata
import time
import re # Importado para extracción de código de cliente

# ==============================================================================
# 1. CONFIGURACIÓN CENTRALIZADA (BLOQUE DE CÓDIGO LIMPIO)
# ==============================================================================
APP_CONFIG = {
    "page_title": "Resumen Mensual | Tablero de Ventas",
    "url_logo": "https://raw.githubusercontent.com/DiegoMao2021/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png",
    "dropbox_paths": {
        "ventas": "/data/ventas_detalle.csv",
        "cobros": "/data/cobros_detalle.csv",
        "cl4_report": "/data/reporte_cl4.xlsx" # NUEVA RUTA: Reporte de oportunidades
    },
    "column_names": {
        "ventas": ['anio', 'mes', 'fecha_venta', 'Serie', 'TipoDocumento', 'codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_cliente', 'codigo_articulo', 'nombre_articulo', 'categoria_producto', 'linea_producto', 'marca_producto', 'valor_venta', 'unidades_vendidas', 'costo_unitario', 'super_categoria'],
        "cobros": ['anio', 'mes', 'fecha_cobro', 'codigo_vendedor', 'valor_cobro']
    },
    "kpi_goals": {
        "meta_clientes_cl4": 120 # NUEVA META: Reemplaza la meta de marquilla
    },
    # 'marquillas_clave' ya no se usa para el KPI principal, pero se puede mantener para análisis secundarios
    "marquillas_clave": ['VINILTEX', 'KORAZA', 'ESTUCOMASTIC', 'VINILICO', 'PINTULUX'],
    "productos_oportunidad_cl4": ['ESTUCOMASTIC', 'PINTULUX', 'KORAZA', 'VINILTEX', 'VINILICO'],
    "complementarios": {"exclude_super_categoria": "Pintuco", "presupuesto_pct": 0.10},
    "sub_meta_complementarios": {"nombre_marca_objetivo": "non-AN Third Party", "presupuesto_pct": 0.10},
    "categorias_clave_venta": ['ABRACOL', 'YALE', 'SAINT GOBAIN', 'GOYA', 'ALLEGION', 'SEGUREX'],
    "presupuesto_mostradores": {"incremento_anual_pct": 0.10}
}
DATA_CONFIG = {
    "presupuestos":{'154033':{'presupuesto':123873239, 'presupuestocartera':127071295}, '154044':{'presupuesto':80000000, 'presupuestocartera':60102413}, '154034':{'presupuesto':82753045, 'presupuestocartera':91489169}, '154014':{'presupuesto':268214737, 'presupuestocartera':353291947}, '154046':{'presupuesto':85469798, 'presupuestocartera':27843193}, '154012':{'presupuesto':246616193, 'presupuestocartera':351282011}, '154043':{'presupuesto':124885413, 'presupuestocartera':132985857}, '154035':{'presupuesto':80000000, 'presupuestocartera':30000000}, '154006':{'presupuesto':81250000, 'presupuestocartera':135714573}, '154049':{'presupuesto':56500000, 'presupuestocartera':61684594}, '154013':{'presupuesto':303422639, 'presupuestocartera':386907842}, '154011':{'presupuesto':447060250, 'presupuestocartera':466331701}, '154029':{'presupuesto':60000000, 'presupuestocartera':14630424}, '154040':{'presupuesto':0, 'presupuestocartera':0},'154053':{'presupuesto':0, 'presupuestocartera':0},'154048':{'presupuesto':0, 'presupuestocartera':0},'154042':{'presupuesto':3000000, 'presupuestocartera':19663757},'154031':{'presupuesto':0, 'presupuestocartera':0},'154039':{'presupuesto':0, 'presupuestocartera':0},'154051':{'presupuesto':0, 'presupuestocartera':0},'154008':{'presupuesto':0, 'presupuestocartera':0},'154052':{'presupuesto':3000000, 'presupuestocartera':21785687},'154050':{'presupuesto':0, 'presupuestocartera':0}},
    "grupos_vendedores": {"MOSTRADOR PEREIRA": ["ALEJANDRO CARBALLO MARQUEZ", "GEORGINA A. GALVIS HERRERA"], "MOSTRADOR ARMENIA": ["CRISTIAN CAMILO RENDON MONTES", "FANDRY JOHANA ABRIL PENHA", "JAVIER ORLANDO PATINO HURTADO"], "MOSTRADOR MANIZALES": ["DAVID FELIPE MARTINEZ RIOS", "JHON JAIRO CASTAÑO MONTES"], "MOSTRADOR LAURELES": ["MAURICIO RIOS MORALES"], "MOSTRADOR OPALO": ["MARIA PAULA DEL JESUS GALVIS HERRERA"]},
    "mapeo_meses": {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"},
    "mapeo_marcas": {50:"P8-ASC-MEGA", 54:"MPY-International", 55:"DPP-AN COLORANTS LATAM", 56:"DPP-Pintuco Profesional", 57:"ASC-Mega", 58:"DPP-Pintuco", 59:"DPP-Madetec", 60:"POW-Interpon", 61:"various", 62:"DPP-ICO", 63:"DPP-Terinsa", 64:"MPY-Pintuco", 65:"non-AN Third Party", 66:"ICO-AN Packaging", 67:"ASC-Automotive OEM", 68:"POW-Resicoat", 73:"DPP-Coral", 91:"DPP-Sikkens"}
}

st.set_page_config(page_title=APP_CONFIG["page_title"], page_icon="🏠", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    div[data-testid="stButton"] > button[kind="primary"] {
        height: 3em; font-size: 1.2em; font-weight: bold; border: 2px solid #FF4B4B;
        background-color: #FF4B4B; color: white;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        border-color: #FF6B6B; background-color: #FF6B6B;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 2. LÓGICA DE PROCESAMIENTO DE DATOS
# ==============================================================================
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='AlbaranesPendientes', startrow=1, header=False)

        workbook = writer.book
        worksheet = writer.sheets['AlbaranesPendientes']

        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': False,
            'valign': 'vcenter',
            'align': 'center',
            'fg_color': '#1F4E78',
            'font_color': 'white',
            'border': 1
        })
        currency_format = workbook.add_format({'num_format': '$#,##0', 'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1, 'align': 'left'})
        default_format = workbook.add_format({'border': 1})

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        worksheet.set_column('A:A', 12, date_format)
        worksheet.set_column('B:B', 35, default_format)
        worksheet.set_column('C:C', 25, default_format)
        worksheet.set_column('D:D', 35, default_format)
        worksheet.set_column('E:E', 20, currency_format)
        
        worksheet.autofilter(0, 0, df.shape[0], df.shape[1] - 1)

    return output.getvalue()

# --- NUEVA FUNCIÓN PARA EXPORTAR OPORTUNIDADES CON FORMATO ---
def to_excel_oportunidades(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Oportunidades_CL4')

        workbook = writer.book
        worksheet = writer.sheets['Oportunidades_CL4']

        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter', 
            'align': 'center', 'fg_color': '#1F4E78', 'font_color': 'white', 'border': 1
        })
        
        # Formato para resaltar las oportunidades (celdas con valor 0)
        opportunity_format = workbook.add_format({'bg_color': '#FFFFCC', 'border': 1}) 
        default_format = workbook.add_format({'border': 1})

        # Aplicar formato de cabecera
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Aplicar formato condicional para resaltar oportunidades
        marcas_cols = APP_CONFIG['productos_oportunidad_cl4']
        for marca in marcas_cols:
            if marca in df.columns:
                col_idx = df.columns.get_loc(marca)
                # La condición aplica a todas las filas de datos (desde la fila 1 hasta el final)
                worksheet.conditional_format(1, col_idx, len(df), col_idx, {
                    'type': 'cell',
                    'criteria': '==',
                    'value': 0,
                    'format': opportunity_format
                })
        
        # Ajustar ancho de columnas
        worksheet.set_column('A:A', 45, default_format) # Cliente
        worksheet.set_column('B:B', 15, default_format) # NIT
        worksheet.set_column('C:C', 10, default_format) # Nivel Actual
        worksheet.set_column('D:D', 35, default_format) # Vendedor
        
        # Ajustar columnas de marcas
        col_start_marcas = df.columns.get_loc(marcas_cols[0]) if marcas_cols[0] in df.columns else 4
        worksheet.set_column(col_start_marcas, col_start_marcas + len(marcas_cols) - 1, 15, default_format)

        worksheet.autofilter(0, 0, df.shape[0], df.shape[1] - 1)
        
    return output.getvalue()


def normalizar_texto(texto):
    if not isinstance(texto, str): return texto
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').replace('_', ' ').strip().replace('  ', ' ')
    except (TypeError, AttributeError): return texto

APP_CONFIG['complementarios']['exclude_super_categoria'] = normalizar_texto(APP_CONFIG['complementarios']['exclude_super_categoria'])
APP_CONFIG['sub_meta_complementarios']['nombre_marca_objetivo'] = normalizar_texto(APP_CONFIG['sub_meta_complementarios']['nombre_marca_objetivo'])
APP_CONFIG['categorias_clave_venta'] = [normalizar_texto(cat) for cat in APP_CONFIG['categorias_clave_venta']]

@st.cache_data(ttl=1800)
def cargar_y_limpiar_datos(ruta_archivo, nombres_columnas):
    try:
        with dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, app_secret=st.secrets.dropbox.app_secret, oauth2_refresh_token=st.secrets.dropbox.refresh_token) as dbx:
            _, res = dbx.files_download(path=ruta_archivo)
            contenido_csv = res.content.decode('latin-1')
            
            df = pd.read_csv(io.StringIO(contenido_csv), header=None, sep='|', engine='python', quoting=3, on_bad_lines='warn')

            if df.shape[1] < 5 and not df.empty:
                st.error(f"Error de Carga en {ruta_archivo}: Se leyó una sola columna. Revisa el archivo CSV para asegurar que el separador sea '|'.")
                return pd.DataFrame(columns=nombres_columnas)

            if df.shape[1] != len(nombres_columnas):
                st.warning(f"Formato en {ruta_archivo}: Se esperaban {len(nombres_columnas)} columnas pero se encontraron {df.shape[1]}. Se rellenarán las faltantes.")
                df = df.reindex(columns=range(len(nombres_columnas)))
            df.columns = nombres_columnas
            
            if 'codigo_vendedor' in df.columns:
                df['codigo_vendedor'] = pd.to_numeric(df['codigo_vendedor'], errors='coerce').fillna(0).astype(int).astype(str)

            numeric_cols = ['anio', 'mes', 'valor_venta', 'valor_cobro', 'unidades_vendidas', 'costo_unitario', 'marca_producto']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            df.dropna(subset=['anio', 'mes'], inplace=True)
            df = df.astype({'anio': int, 'mes': int})
            
            if 'fecha_venta' in df.columns: df['fecha_venta'] = pd.to_datetime(df['fecha_venta'], errors='coerce')
            if 'cliente_id' in df.columns: df['cliente_id'] = df['cliente_id'].astype(str)
            if 'marca_producto' in df.columns: df['nombre_marca'] = df['marca_producto'].map(DATA_CONFIG["mapeo_marcas"]).fillna('No Especificada')
            cols_a_normalizar = ['super_categoria', 'categoria_producto', 'nombre_marca', 'nomvendedor', 'TipoDocumento']
            for col in cols_a_normalizar:
                if col in df.columns: df[col] = df[col].apply(normalizar_texto)
            return df
    except Exception as e:
        st.error(f"Error crítico al cargar {ruta_archivo}: {e}")
        return pd.DataFrame(columns=nombres_columnas)

# --- FUNCIÓN CORREGIDA Y MEJORADA PARA CARGAR REPORTE CL4 ---
@st.cache_data(ttl=1800)
def cargar_reporte_cl4(ruta_archivo):
    try:
        with dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, app_secret=st.secrets.dropbox.app_secret, oauth2_refresh_token=st.secrets.dropbox.refresh_token) as dbx:
            _, res = dbx.files_download(path=ruta_archivo)
            df = pd.read_excel(io.BytesIO(res.content))

            # 1. Verificar si la columna 'id_cliente' existe, que es la correcta para el cruce.
            if 'id_cliente' in df.columns:
                # 2. Asegurar que la columna sea de tipo 'str' para que coincida con el DataFrame de ventas.
                df['id_cliente'] = df['id_cliente'].astype(str)
                # 3. Asegurar que el NIT también sea de tipo 'str'
                if 'NIT' in df.columns:
                    df['NIT'] = df['NIT'].astype(str)
            else:
                # 4. Si 'id_cliente' no existe, mostrar un error claro al usuario.
                st.error("El archivo de oportunidades (reporte_cl4.xlsx) NO contiene la columna 'id_cliente'. El cruce de datos para asignar vendedor no es posible.")
                return pd.DataFrame()
            
            return df

    except Exception as e:
        st.error(f"Error crítico al cargar el reporte de oportunidades desde {ruta_archivo}: {e}")
        return pd.DataFrame()


def procesar_datos_periodo(df_ventas_periodo, df_cobros_periodo, df_ventas_historicas, anio_sel, mes_sel):
    filtro_ventas_netas = 'FACTURA|NOTA.*CREDITO'
    df_ventas_reales = df_ventas_periodo[df_ventas_periodo['TipoDocumento'].str.contains(filtro_ventas_netas, na=False, case=False, regex=True)].copy()
    
    resumen_ventas = df_ventas_reales.groupby(['codigo_vendedor', 'nomvendedor']).agg(ventas_totales=('valor_venta', 'sum'), impactos=('cliente_id', 'nunique')).reset_index()
    resumen_cobros = df_cobros_periodo.groupby('codigo_vendedor').agg(cobros_totales=('valor_cobro', 'sum')).reset_index()
    
    categorias_objetivo = APP_CONFIG['categorias_clave_venta']
    df_ventas_comp = df_ventas_reales[df_ventas_reales['categoria_producto'].isin(categorias_objetivo)]
    resumen_complementarios = df_ventas_comp.groupby(['codigo_vendedor','nomvendedor']).agg(ventas_complementarios=('valor_venta', 'sum')).reset_index()
    
    marca_sub_meta = APP_CONFIG['sub_meta_complementarios']['nombre_marca_objetivo']
    df_ventas_sub_meta = df_ventas_reales[df_ventas_reales['nombre_marca'] == marca_sub_meta]
    resumen_sub_meta = df_ventas_sub_meta.groupby(['codigo_vendedor','nomvendedor']).agg(ventas_sub_meta=('valor_venta', 'sum')).reset_index()
    
    df_albaranes_historicos_bruto = df_ventas_historicas[df_ventas_historicas['TipoDocumento'].str.contains('ALBARAN', na=False, case=False)].copy()
    grouping_keys = ['Serie', 'cliente_id', 'codigo_articulo', 'codigo_vendedor']
    if not df_albaranes_historicos_bruto.empty:
        df_neto_historico = df_albaranes_historicos_bruto.groupby(grouping_keys).agg(valor_neto=('valor_venta', 'sum')).reset_index()
        df_grupos_cancelados_global = df_neto_historico[df_neto_historico['valor_neto'] == 0]
    else:
        df_grupos_cancelados_global = pd.DataFrame(columns=grouping_keys)

    df_albaranes_bruto_periodo = df_ventas_periodo[df_ventas_periodo['TipoDocumento'].str.contains('ALBARAN', na=False, case=False)].copy()
    if not df_albaranes_bruto_periodo.empty and not df_grupos_cancelados_global.empty:
        df_albaranes_reales_pendientes = df_albaranes_bruto_periodo.merge(
            df_grupos_cancelados_global[grouping_keys], on=grouping_keys, how='left', indicator=True
        ).query('_merge == "left_only"').drop(columns=['_merge'])
    else:
        df_albaranes_reales_pendientes = df_albaranes_bruto_periodo.copy()

    if not df_albaranes_reales_pendientes.empty:
        resumen_albaranes = df_albaranes_reales_pendientes[df_albaranes_reales_pendientes['valor_venta'] > 0].groupby(['codigo_vendedor', 'nomvendedor']).agg(albaranes_pendientes=('valor_venta', 'sum')).reset_index()
    else:
        resumen_albaranes = pd.DataFrame(columns=['codigo_vendedor', 'nomvendedor', 'albaranes_pendientes'])

    df_resumen = pd.merge(resumen_ventas, resumen_cobros, on='codigo_vendedor', how='left')
    df_resumen = pd.merge(df_resumen, resumen_complementarios, on=['codigo_vendedor', 'nomvendedor'], how='left')
    df_resumen = pd.merge(df_resumen, resumen_sub_meta, on=['codigo_vendedor', 'nomvendedor'], how='left')
    df_resumen = pd.merge(df_resumen, resumen_albaranes, on=['codigo_vendedor', 'nomvendedor'], how='left')

    presupuestos_fijos = DATA_CONFIG['presupuestos']
    df_resumen['presupuesto'] = df_resumen['codigo_vendedor'].map(lambda x: presupuestos_fijos.get(x, {}).get('presupuesto', 0))
    df_resumen['presupuestocartera'] = df_resumen['codigo_vendedor'].map(lambda x: presupuestos_fijos.get(x, {}).get('presupuestocartera', 0))
    df_resumen.fillna(0, inplace=True)
    
    registros_agrupados = []
    incremento_mostradores = 1 + APP_CONFIG['presupuesto_mostradores']['incremento_anual_pct']
    for grupo, lista_vendedores in DATA_CONFIG['grupos_vendedores'].items():
        lista_vendedores_norm = [normalizar_texto(v) for v in lista_vendedores]
        df_grupo_actual = df_resumen[df_resumen['nomvendedor'].isin(lista_vendedores_norm)]
        if not df_grupo_actual.empty:
            anio_anterior = anio_sel - 1
            df_grupo_historico_facturas = df_ventas_historicas[
                (df_ventas_historicas['TipoDocumento'].str.contains(filtro_ventas_netas, na=False, case=False, regex=True)) &
                (df_ventas_historicas['anio'] == anio_anterior) & (df_ventas_historicas['mes'] == mes_sel) & 
                (df_ventas_historicas['nomvendedor'].isin(lista_vendedores_norm))
            ]
            ventas_anio_anterior = df_grupo_historico_facturas['valor_venta'].sum() if not df_grupo_historico_facturas.empty else 0
            presupuesto_dinamico = ventas_anio_anterior * incremento_mostradores
            
            cols_a_sumar = ['ventas_totales', 'cobros_totales', 'impactos', 'presupuestocartera', 'ventas_complementarios', 'ventas_sub_meta', 'albaranes_pendientes']
            suma_grupo = df_grupo_actual[cols_a_sumar].sum().to_dict()
            
            suma_grupo['presupuesto'] = df_grupo_actual['presupuesto'].sum()
            registro = {'nomvendedor': normalizar_texto(grupo), 'codigo_vendedor': normalizar_texto(grupo), **suma_grupo}
            
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
# 3. LÓGICA DE LA INTERFAZ DE USUARIO Y EJECUCIÓN
# ==============================================================================
def generar_comentario_asesor(avance_v, avance_c, clientes_meta, meta_clientes, avance_comp, avance_sub_meta):
    comentarios = []
    if avance_v >= 100: comentarios.append("📈 **Ventas:** ¡Felicitaciones! Has superado la meta de ventas netas.")
    elif avance_v >= 80: comentarios.append("📈 **Ventas:** ¡Estás muy cerca de la meta neta! Un último esfuerzo.")
    else: comentarios.append("📈 **Ventas:** Planifica tus visitas y aprovecha cada oportunidad para mejorar tu venta neta.")
    if avance_c >= 100: comentarios.append("💰 **Cartera:** Objetivo de recaudo cumplido. ¡Gestión impecable!")
    else: comentarios.append("💰 **Cartera:** Recuerda hacer seguimiento a la cartera pendiente.")
    
    if clientes_meta >= meta_clientes:
        comentarios.append(f"🎯 **Meta Clientes (CL4):** ¡Objetivo Cumplido! Tienes {clientes_meta} clientes en la meta de {meta_clientes}.")
    else:
        comentarios.append(f"🎯 **Meta Clientes (CL4):** Tu avance es de {clientes_meta} de {meta_clientes} clientes. ¡Revisa el tablero de oportunidades para cerrar la brecha!")

    if avance_comp >= 100: comentarios.append("⚙️ **Complementarios:** ¡Excelente! Cumpliste la meta de venta neta de complementarios.")
    else: comentarios.append(f"⚙️ **Complementarios:** Tu avance neto es del {avance_comp:.1f}%. ¡Impulsa la venta cruzada!")
    
    sub_meta_label = APP_CONFIG['sub_meta_complementarios']['nombre_marca_objetivo']
    if avance_sub_meta >= 100: comentarios.append(f"⭐ **Meta Específica:** ¡Logrado! Superaste la meta de venta neta de '{sub_meta_label}'.")
    else: comentarios.append(f"⭐ **Meta Específica:** Tu avance neto en '{sub_meta_label}' es del {avance_sub_meta:.1f}%. ¡Hay una gran oportunidad ahí!")
    
    return comentarios

def render_analisis_detallado(df_vista, df_ventas_periodo):
    st.markdown("---")
    st.header("🔬 Análisis Detallado del Periodo")
    opciones_enfoque = ["Visión General"] + sorted(df_vista['nomvendedor'].unique())
    enfoque_sel = st.selectbox("Enfocar análisis en:", opciones_enfoque, index=0, key="sb_enfoque_analisis")
    if enfoque_sel == "Visión General":
        nombres_a_filtrar = []
        for vendedor in df_vista['nomvendedor']:
            vendedor_norm = normalizar_texto(vendedor)
            nombre_grupo_orig = next((k for k in DATA_CONFIG['grupos_vendedores'] if normalizar_texto(k) == vendedor_norm), vendedor_norm)
            lista_vendedores = DATA_CONFIG['grupos_vendedores'].get(nombre_grupo_orig, [vendedor_norm])
            nombres_a_filtrar.extend([normalizar_texto(v) for v in lista_vendedores])
        df_ventas_enfocadas = df_ventas_periodo[df_ventas_periodo['nomvendedor'].isin(nombres_a_filtrar)]
        df_ranking = df_vista
    else:
        enfoque_sel_norm = normalizar_texto(enfoque_sel)
        nombre_grupo_orig = next((k for k in DATA_CONFIG['grupos_vendedores'] if normalizar_texto(k) == enfoque_sel_norm), enfoque_sel_norm)
        nombres_a_filtrar = [normalizar_texto(n) for n in DATA_CONFIG['grupos_vendedores'].get(nombre_grupo_orig, [enfoque_sel_norm])]
        df_ventas_enfocadas = df_ventas_periodo[df_ventas_periodo['nomvendedor'].isin(nombres_a_filtrar)]
        df_ranking = df_vista[df_vista['nomvendedor'] == enfoque_sel_norm]
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Análisis de Portafolio", "🏆 Ranking de Rendimiento", "⭐ Clientes Clave", "⚙️ Ventas por Categoría"])
    with tab1:
        st.subheader("Análisis de Marcas y Categorías Estratégicas (Venta Neta)")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Composición de Ventas Netas por Marca")
            if not df_ventas_enfocadas.empty and 'nombre_marca' in df_ventas_enfocadas:
                df_marcas = df_ventas_enfocadas.groupby('nombre_marca')['valor_venta'].sum().reset_index()
                fig = px.treemap(df_marcas, path=[px.Constant("Todas las Marcas"), 'nombre_marca'], values='valor_venta')
                fig.update_layout(margin=dict(t=25, l=25, r=25, b=25))
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("No hay datos de marcas de productos para mostrar.")
        with col2:
            st.markdown("##### Ventas de Marquillas Clave (Venta Bruta)")
            if not df_ventas_enfocadas.empty and 'nombre_articulo' in df_ventas_enfocadas:
                ventas_marquillas = {p: df_ventas_enfocadas[df_ventas_enfocadas['nombre_articulo'].str.contains(p, case=False, na=False)]['valor_venta'].sum() for p in APP_CONFIG['marquillas_clave']}
                df_ventas_marquillas = pd.DataFrame(list(ventas_marquillas.items()), columns=['Marquilla', 'Ventas']).sort_values('Ventas', ascending=False)
                fig = px.pie(df_ventas_marquillas, names='Marquilla', values='Ventas', title="Distribución Venta Neta Marquillas", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("No hay datos de marquillas para mostrar.")
    with tab2:
        st.subheader("Ranking de Cumplimiento de Metas (Sobre Venta Neta)")
        df_ranking_con_meta = df_ranking[df_ranking['presupuesto'] > 0].copy()
        if not df_ranking_con_meta.empty:
            df_ranking_con_meta['avance_ventas'] = (df_ranking_con_meta['ventas_totales'] / df_ranking_con_meta['presupuesto']) * 100
            df_ranking_con_meta.sort_values('avance_ventas', ascending=True, inplace=True)
            fig = px.bar(df_ranking_con_meta, x='avance_ventas', y='nomvendedor', orientation='h', text='avance_ventas', title="Cumplimiento de Meta de Ventas Netas (%)")
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(xaxis_title="Cumplimiento (%)", yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("No hay datos de presupuesto para generar el ranking.")
    with tab3:
        st.subheader("Top 10 Clientes del Periodo (Por Venta Neta)")
        if not df_ventas_enfocadas.empty:
            filtro_ventas_netas = 'FACTURA|NOTA.*CREDITO'
            df_facturas_enfocadas = df_ventas_enfocadas[df_ventas_enfocadas['TipoDocumento'].str.contains(filtro_ventas_netas, na=False, case=False, regex=True)]
            top_clientes = df_facturas_enfocadas.groupby('nombre_cliente')['valor_venta'].sum().nlargest(10).reset_index()
            st.dataframe(top_clientes, column_config={"nombre_cliente": "Cliente", "valor_venta": st.column_config.NumberColumn("Total Compra (Neta)", format="$ %d")}, use_container_width=True, hide_index=True)
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
                st.markdown("##### Ventas Netas por Categoría")
                resumen_cat = df_ventas_cat.groupby('categoria_producto').agg(Ventas=('valor_venta', 'sum')).reset_index()
                total_ventas_enfocadas = df_ventas_enfocadas['valor_venta'].sum()
                if total_ventas_enfocadas > 0: resumen_cat['Participacion (%)'] = (resumen_cat['Ventas'] / total_ventas_enfocadas) * 100
                else: resumen_cat['Participacion (%)'] = 0
                resumen_cat = resumen_cat.sort_values('Ventas', ascending=False)
                st.dataframe(resumen_cat, column_config={"categoria_producto": "Categoría", "Ventas": st.column_config.NumberColumn("Total Venta Neta", format="$ %d"),"Participacion (%)": st.column_config.ProgressColumn("Part. sobre Venta Neta Total", format="%.2f%%", min_value=0, max_value=resumen_cat['Participacion (%)'].max())}, use_container_width=True, hide_index=True)
            with col2:
                st.markdown("##### Distribución de Ventas Netas")
                fig = px.pie(resumen_cat, names='categoria_producto', values='Ventas', title="Distribución entre Categorías Clave (Venta Neta)", hole=0.4)
                fig.update_traces(textinfo='percent+label', textposition='inside')
                st.plotly_chart(fig, use_container_width=True)

def render_dashboard():
    st.sidebar.markdown("---")
    st.sidebar.header("Filtros de Periodo")

    df_ventas_historicas = st.session_state.df_ventas
    df_cobros_historicos = st.session_state.df_cobros
    df_cl4_base = st.session_state.df_cl4
    
    if 'anio' not in df_ventas_historicas.columns or df_ventas_historicas.empty:
        st.error("No se pudieron cargar los datos de ventas. Revisa la conexión o el formato del archivo.")
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
    
    if df_ventas_periodo.empty and (df_cl4_base is None or df_cl4_base.empty):
        st.warning("No se encontraron datos de ventas ni de oportunidades CL4 para el periodo seleccionado.")
    else:
        df_cobros_periodo = df_cobros_historicos[(df_cobros_historicos['anio'] == anio_sel) & (df_cobros_historicos['mes'] == mes_sel_num)] if not df_cobros_historicos.empty else pd.DataFrame()
        df_resumen_final, df_albaranes_pendientes = procesar_datos_periodo(df_ventas_periodo, df_cobros_periodo, df_ventas_historicas, anio_sel, mes_sel_num)
        
        usuario_actual_norm = normalizar_texto(st.session_state.usuario)
        if usuario_actual_norm == "GERENTE":
            lista_filtro = sorted(df_resumen_final['nomvendedor'].unique())
            vendedores_sel = st.sidebar.multiselect("Filtrar Vendedores/Grupos", options=lista_filtro, default=lista_filtro, key="ms_vendedores")
            df_vista = df_resumen_final[df_resumen_final['nomvendedor'].isin(vendedores_sel)]
        else:
            df_vista = df_resumen_final[df_resumen_final['nomvendedor'] == usuario_actual_norm]
        
        if df_vista.empty and (df_cl4_base is None or df_cl4_base.empty):
             st.warning("No hay datos disponibles para la selección de usuario/grupo actual.")
        else:
            def asignar_estatus(row):
                if row['presupuesto'] > 0:
                    avance = (row['ventas_totales'] / row['presupuesto']) * 100
                    if avance >= 95: return "🟢 En Objetivo"
                    if avance >= 70: return "🟡 Cerca del Objetivo"
                return "🔴 Necesita Atención"
            if not df_vista.empty:
                df_vista['Estatus'] = df_vista.apply(asignar_estatus, axis=1)

            st.title("🏠 Resumen de Rendimiento")
            st.header(f"{DATA_CONFIG['mapeo_meses'].get(mes_sel_num, '')} {anio_sel}")

            if st.button("🔄 ¡Actualizar Todos los Datos!", type="primary", use_container_width=True, help="Fuerza la recarga de los archivos desde Dropbox. Útil si los datos se actualizaron recientemente."):
                st.cache_data.clear()
                if 'df_ventas' in st.session_state: del st.session_state.df_ventas
                if 'df_cobros' in st.session_state: del st.session_state.df_cobros
                if 'df_cl4' in st.session_state: del st.session_state.df_cl4
                st.toast("Limpiando caché y recargando datos... ¡Un momento!", icon="⏳")
                time.sleep(3)
                st.rerun()

            vista_para = st.session_state.usuario if len(df_vista['nomvendedor'].unique()) == 1 else 'Múltiples Seleccionados'
            st.markdown(f"**Vista para:** `{vista_para}`")
            
            df_cl4_actualizado = df_cl4_base.copy()
            
            mapa_cliente_vendedor = df_ventas_historicas.drop_duplicates(subset=['cliente_id'], keep='last')[['cliente_id', 'nomvendedor']]
            
            df_cl4_con_vendedor = pd.merge(df_cl4_actualizado, mapa_cliente_vendedor, on='cliente_id', how='left')
            
            df_cl4_con_vendedor['nomvendedor'] = df_cl4_con_vendedor['nomvendedor'].apply(normalizar_texto)
            df_cl4_con_vendedor['nomvendedor'].fillna('SIN ASIGNAR', inplace=True)

            vendedores_vista_actual = df_vista['nomvendedor'].unique() if not df_vista.empty else []
            nombres_a_filtrar = []
            for vendedor in vendedores_vista_actual:
                vendedor_norm = normalizar_texto(vendedor)
                nombre_grupo_orig = next((k for k in DATA_CONFIG['grupos_vendedores'] if normalizar_texto(k) == vendedor_norm), vendedor_norm)
                lista_vendedores = DATA_CONFIG['grupos_vendedores'].get(nombre_grupo_orig, [vendedor_norm])
                nombres_a_filtrar.extend([normalizar_texto(v) for v in lista_vendedores])
            
            if usuario_actual_norm == "GERENTE":
                df_cl4_filtrado = df_cl4_con_vendedor.copy()
            else:
                df_cl4_filtrado = df_cl4_con_vendedor[df_cl4_con_vendedor['nomvendedor'].isin(nombres_a_filtrar)]
            
            clientes_en_meta = df_cl4_filtrado[df_cl4_filtrado['CL4'] >= 4].shape[0] if not df_cl4_filtrado.empty else 0
            meta_clientes_cl4 = APP_CONFIG['kpi_goals']['meta_clientes_cl4']
            avance_clientes_cl4 = (clientes_en_meta / meta_clientes_cl4 * 100) if meta_clientes_cl4 > 0 else 0

            ventas_total = df_vista['ventas_totales'].sum() if not df_vista.empty else 0
            meta_ventas = df_vista['presupuesto'].sum() if not df_vista.empty else 0
            cobros_total = df_vista['cobros_totales'].sum() if not df_vista.empty else 0
            meta_cobros = df_vista['presupuestocartera'].sum() if not df_vista.empty else 0
            comp_total = df_vista['ventas_complementarios'].sum() if not df_vista.empty else 0
            meta_comp = df_vista['presupuesto_complementarios'].sum() if not df_vista.empty else 0
            sub_meta_total = df_vista['ventas_sub_meta'].sum() if not df_vista.empty else 0
            meta_sub_meta = df_vista['presupuesto_sub_meta'].sum() if not df_vista.empty else 0
            total_albaranes = df_vista['albaranes_pendientes'].sum() if not df_vista.empty else 0
            
            avance_ventas = (ventas_total / meta_ventas * 100) if meta_ventas > 0 else 0
            avance_cobros = (cobros_total / meta_cobros * 100) if meta_cobros > 0 else 0
            avance_comp = (comp_total / meta_comp * 100) if meta_comp > 0 else 0
            avance_sub_meta = (sub_meta_total / meta_sub_meta * 100) if meta_sub_meta > 0 else 0
            
            with st.container(border=True):
                st.subheader(f"👨‍💼 Asesor Virtual para: {st.session_state.usuario}")
                comentarios = generar_comentario_asesor(avance_ventas, avance_cobros, clientes_en_meta, meta_clientes_cl4, avance_comp, avance_sub_meta)
                for comentario in comentarios: st.markdown(f"- {comentario}")

            st.subheader("Métricas Clave del Periodo")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Ventas Netas Facturadas", value=f"${ventas_total:,.0f}", delta=f"{ventas_total - meta_ventas:,.0f}", help=f"Meta: ${meta_ventas:,.0f}")
                st.progress(min(avance_ventas / 100, 1.0), text=f"Avance Ventas Netas: {avance_ventas:.1f}%")
            with col2:
          _meta:,.0f}")
                st.progress(min(avance_sub_meta / 100, 1.0), text=f"Avance: {avance_sub_meta:.1f}%")
            with col6:
                st.metric(label="Clientes en Meta (CL4 ≥ 4)", value=f"{clientes_en_meta}", delta=f"{clientes_en_meta - meta_clientes_cl4}", help=f"Meta: {meta_clientes_cl4} clientes")
                st.progress(min((avance_clientes_cl4 / 100), 1.0), text=f"Avance: {avance_clientes_cl4:.1f}%")
            
            with st.expander("🎯 Análisis de Oportunidades (Clientes con CL4 < 4)", expanded=True):
                st.info("Utiliza esta tabla para identificar clientes con potencial de crecimiento. Muestra a qué clientes de tu cartera les puedes ofrecer los productos clave para que alcancen la meta de CL4 ≥ 4.")
                
                df_oportunidades = df_cl4_filtrado[df_cl4_filtrado['CL4'] < 4].copy() if not df_cl4_filtrado.empty else pd.DataFrame()

                if df_oportunidades.empty:
                    st.success("¡Felicidades! No tienes clientes con oportunidades pendientes en la selección actual. ¡Todos están en la meta o no hay datos de oportunidades!")
                else:
                    def encontrar_faltantes(row):
                        faltantes = [prod for prod in APP_CONFIG['productos_oportunidad_cl4'] if prod in row and row[prod] == 0]
                        return ", ".join(faltantes) if faltantes else "N/A"

                    df_oportunidades['Productos a Ofrecer'] = df_oportunidades.apply(encontrar_faltantes, axis=1)
                    
                    # --- MODIFICACIÓN: Añadir NIT a la tabla de visualización ---
                    cols_display = ['NOMBRE', 'NIT', 'CL4', 'Productos a Ofrecer', 'nomvendedor']
                    df_oportunidades_display = df_oportunidades[cols_display].rename(columns={
                        'NOMBRE': 'Cliente',
                        'NIT': 'NIT',
                        'CL4': 'Nivel Actual',
                        'nomvendedor': 'Vendedor Asignado'
                    })

                    st.dataframe(
                        df_oportunidades_display,
                        use_container_width=True,
                        hide_index=True,
                        column_config={ "NIT": st.column_config.TextColumn("NIT", width="medium") }
                    )

                    st.markdown("---")
                    st.subheader("📥 Descargar Reporte de Oportunidades Filtrado")
                    st.info("El siguiente botón descargará un reporte en Excel con el detalle de las oportunidades mostradas en la tabla de arriba, resaltando las marcas que faltan por vender.")

                    # --- MODIFICACIÓN: Preparar y descargar Excel de oportunidades ---
                    cols_excel = ['NOMBRE', 'NIT', 'CL4', 'nomvendedor'] + APP_CONFIG['productos_oportunidad_cl4']
                    df_para_descargar_oportunidades = df_oportunidades[cols_excel].rename(columns={
                        'NOMBRE': 'Cliente',
                        'NIT': 'NIT Cliente',
                        'CL4': 'Nivel Actual',
                        'nomvendedor': 'Vendedor Asignado'
                    })
                    
                    excel_data_oportunidades = to_excel_oportunidades(df_para_descargar_oportunidades)

                    st.download_button(
                        label="📥 Descargar Reporte de Oportunidades (Excel)",
                        data=excel_data_oportunidades,
                        file_name=f"Reporte_Oportunidades_CL4_{anio_sel}_{mes_sel_num}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

            st.markdown("---")
            st.subheader("Desglose por Vendedor / Grupo")
            
            if not df_vista.empty:
                def contar_clientes_meta_por_vendedor(nomvendedor):
                    vendedor_norm = normalizar_texto(nomvendedor)
                    nombre_grupo_orig = next((k for k in DATA_CONFIG['grupos_vendedores'] if normalizar_texto(k) == vendedor_norm), vendedor_norm)
                    vendedores_del_grupo = [normalizar_texto(v) for v in DATA_CONFIG['grupos_vendedores'].get(nombre_grupo_orig, [vendedor_norm])]
                    
                    df_cl4_vendedor = df_cl4_con_vendedor[df_cl4_con_vendedor['nomvendedor'].isin(vendedores_del_grupo)]
                    return df_cl4_vendedor[df_cl4_vendedor['CL4'] >= 4].shape[0]

                df_vista['clientes_meta_cl4'] = df_vista['nomvendedor'].apply(contar_clientes_meta_por_vendedor)

                cols_desglose = ['Estatus', 'nomvendedor', 'ventas_totales', 'presupuesto', 'cobros_totales', 'presupuestocartera', 'albaranes_pendientes', 'impactos', 'clientes_meta_cl4']
                st.dataframe(df_vista[cols_desglose], column_config={
                    "Estatus": st.column_config.TextColumn("🚦", width="small"), "nomvendedor": "Vendedor/Grupo",
                    "ventas_totales": st.column_config.NumberColumn("Ventas Netas", format="$ %d"), 
                    "presupuesto": st.column_config.NumberColumn("Meta Ventas", format="$ %d"),
                    "cobros_totales": st.column_config.NumberColumn("Recaudo", format="$ %d"),
                    "presupuestocartera": st.column_config.NumberColumn("Meta Recaudo", format="$ %d"),
                    "albaranes_pendientes": st.column_config.NumberColumn("Valor Albaranes", format="$ %d"),
                    "impactos": st.column_config.NumberColumn("Clientes Únicos", format="%d"),
                    "clientes_meta_cl4": st.column_config.NumberColumn("Clientes Meta (CL4≥4)", format="%d")
                }, use_container_width=True, hide_index=True)

            if not df_vista.empty:
                render_analisis_detallado(df_vista, df_ventas_periodo)
            
            st.markdown("<hr style='border:2px solid #FF4B4B'>", unsafe_allow_html=True)
            st.header("📦 Gestión de Albaranes Pendientes")

            st.subheader("Vista Mensual Filtrada")
            
            df_albaranes_vista = df_albaranes_pendientes[df_albaranes_pendientes['nomvendedor'].isin(nombres_a_filtrar)] if not df_albaranes_pendientes.empty else pd.DataFrame()
            df_albaranes_a_mostrar = df_albaranes_vista[df_albaranes_vista['valor_venta'] > 0] if not df_albaranes_vista.empty else pd.DataFrame()

            if df_albaranes_a_mostrar.empty:
                st.info("No hay albaranes pendientes de facturación para la selección de filtros actual (mes/vendedor).")
            else:
                st.dataframe(df_albaranes_a_mostrar[['Serie', 'fecha_venta', 'nombre_cliente', 'valor_venta', 'nomvendedor']], 
                    column_config={
                        "Serie": "Documento", "fecha_venta": "Fecha", "nombre_cliente": "Cliente",
                        "valor_venta": st.column_config.NumberColumn("Valor Pendiente", format="$ %d"),
                        "nomvendedor": "Vendedor"
                    }, use_container_width=True, hide_index=True
                )

            st.subheader(f"Descarga Anual de Albaranes ({anio_sel})")
            st.info(f"El siguiente botón descargará un reporte con el **valor total por albarán** para **TODO** el año **{anio_sel}**, sin importar los filtros de mes o vendedor.")

            with st.spinner(f"Calculando albaranes totales del año {anio_sel}..."):
                df_albaranes_historicos_bruto = df_ventas_historicas[df_ventas_historicas['TipoDocumento'].str.contains('ALBARAN', na=False, case=False)].copy()
                grouping_keys = ['Serie', 'cliente_id', 'codigo_articulo', 'codigo_vendedor']
                if not df_albaranes_historicos_bruto.empty:
                    df_neto_historico = df_albaranes_historicos_bruto.groupby(grouping_keys).agg(valor_neto=('valor_venta', 'sum')).reset_index()
                    df_grupos_cancelados_global = df_neto_historico[df_neto_historico['valor_neto'] == 0]
                else:
                    df_grupos_cancelados_global = pd.DataFrame(columns=grouping_keys)

                df_ventas_anual = df_ventas_historicas[df_ventas_historicas['anio'] == anio_sel]
                df_albaranes_bruto_anual = df_ventas_anual[df_ventas_anual['TipoDocumento'].str.contains('ALBARAN', na=False, case=False)].copy()

                if not df_albaranes_bruto_anual.empty and not df_grupos_cancelados_global.empty:
                    df_albaranes_pendientes_del_anio = df_albaranes_bruto_anual.merge(
                        df_grupos_cancelados_global[grouping_keys], on=grouping_keys, how='left', indicator=True
                    ).query('_merge == "left_only"').drop(columns=['_merge'])
                else:
                    df_albaranes_pendientes_del_anio = df_albaranes_bruto_anual.copy()

                df_albaranes_pendientes_del_anio = df_albaranes_pendientes_del_anio[df_albaranes_pendientes_del_anio['valor_venta'] > 0]

            if df_albaranes_pendientes_del_anio.empty:
                st.warning(f"No se encontraron albaranes pendientes para descargar en todo el año {anio_sel}.")
            else:
                claves_agrupacion = ['fecha_venta', 'nombre_cliente', 'Serie', 'nomvendedor']
                df_agrupado_anual = df_albaranes_pendientes_del_anio.groupby(claves_agrupacion).agg(
                    valor_venta=('valor_venta', 'sum')
                ).reset_index()

                df_para_descargar_anual = df_agrupado_anual.copy()
                df_para_descargar_anual.columns = ['Fecha', 'Nombre Cliente', 'Numero Albaran/Serie', 'Nombre Vendedor', 'Valor Total Albaran']
                df_para_descargar_anual = df_para_descargar_anual.sort_values(by=['Fecha', 'Nombre Cliente'], ascending=[False, True])
                
                excel_data_anual = to_excel(df_para_descargar_anual)

                st.download_button(
                    label=f"📥 Descargar Reporte Anual de Albaranes de {anio_sel}",
                    data=excel_data_anual,
                    file_name=f"Reporte_Albaranes_Pendientes_{anio_sel}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary",
                    help=f"Descarga el reporte con el total por albarán de todo el año {anio_sel}."
                )

def main():
    if 'df_ventas' not in st.session_state:
        with st.spinner('Cargando datos maestros, por favor espere...'):
            st.session_state.df_ventas = cargar_y_limpiar_datos(APP_CONFIG["dropbox_paths"]["ventas"], APP_CONFIG["column_names"]["ventas"])
            st.session_state.df_cobros = cargar_y_limpiar_datos(APP_CONFIG["dropbox_paths"]["cobros"], APP_CONFIG["column_names"]["cobros"])
            st.session_state.df_cl4 = cargar_reporte_cl4(APP_CONFIG["dropbox_paths"]["cl4_report"])
            st.session_state['APP_CONFIG'] = APP_CONFIG
            st.session_state['DATA_CONFIG'] = DATA_CONFIG
    
    st.sidebar.image(APP_CONFIG["url_logo"], use_container_width=True)
    st.sidebar.header("Control de Acceso")
    
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False

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

    else:
        render_dashboard()
        if st.sidebar.button("Salir", key="btn_logout"):
            keys_to_clear = list(st.session_state.keys())
            for key in keys_to_clear:
                del st.session_state[key]
            st.rerun()

if __name__ == '__main__':
    main()
