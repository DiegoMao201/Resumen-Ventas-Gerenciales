# ==============================================================================
# SCRIPT COMPLETO Y DEFINITIVO PARA: 🏠 Resumen Mensual.py
# VERSIÓN: CORREGIDA Y OPTIMIZADA (Para Producción)
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import dropbox
import io
import unicodedata
import time
import re
import datetime
import calendar
import functools
import hashlib

# ==============================================================================
# 1. CONFIGURACIÓN CENTRALIZADA
# ==============================================================================
APP_CONFIG = {
    "page_title": "Resumen Mensual | Tablero de Ventas",
    "url_logo": "https://raw.githubusercontent.com/DiegoMao2021/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png",
    "dropbox_paths": {
        "ventas": "/data/ventas_detalle.csv",
        "cobros": "/data/cobros_detalle.csv",
        "cl4_report": "/data/reporte_cl4.xlsx"
    },
    "column_names": {
        "ventas": ['anio', 'mes', 'fecha_venta', 'Serie', 'TipoDocumento', 'codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_cliente', 'codigo_articulo', 'nombre_articulo', 'categoria_producto', 'linea_producto', 'marca_producto', 'valor_venta', 'unidades_vendidas', 'costo_unitario', 'super_categoria'],
        "cobros": ['anio', 'mes', 'fecha_cobro', 'codigo_vendedor', 'valor_cobro']
    },
    "kpi_goals": {
        "meta_clientes_cl4": 120 
    },
    "marquillas_clave": ['VINILTEX', 'KORAZA', 'ESTUCOMAS', 'VINILICO', 'PINTULUX'],
    "productos_oportunidad_cl4": ['ESTUCOMAS', 'PINTULUX', 'KORAZA', 'VINILTEX', 'VINILICO'],
    "complementarios": {"exclude_super_categoria": "Pintuco", "presupuesto_pct": 0.10},
    "sub_meta_complementarios": {"nombre_marca_objetivo": "non-AN Third Party", "presupuesto_pct": 0.10},
    "categorias_clave_venta": ['ABRACOL', 'YALE', 'SAINT GOBAIN', 'GOYA', 'ALLEGION', 'SEGUREX', 'ARTECOLA', 'ATLAS', 'INDUMA'],
    "presupuesto_mostradores": {"incremento_anual_pct": 0.10}
}

DATA_CONFIG = {
    "presupuestos": {'154033':{'presupuesto':123873239, 'presupuestocartera':138086459}, '154044':{'presupuesto':80000000, 'presupuestocartera':74547413}, '154034':{'presupuesto':82753045, 'presupuestocartera':134853042}, '154014':{'presupuesto':268214737, 'presupuestocartera':306818938}, '154046':{'presupuesto':85469798, 'presupuestocartera':42529021}, '154012':{'presupuesto':246616193, 'presupuestocartera':447901941}, '154043':{'presupuesto':124885413, 'presupuestocartera':147264596}, '154035':{'presupuesto':80000000, 'presupuestocartera':39864540}, '154006':{'presupuesto':81250000, 'presupuestocartera':127377725}, '154049':{'presupuesto':0, 'presupuestocartera':0}, '154013':{'presupuesto':303422639, 'presupuestocartera':483720267}, '154011':{'presupuesto':447060250, 'presupuestocartera':589086338}, '154029':{'presupuesto':50000000, 'presupuestocartera':34239301}, '154040':{'presupuesto':0, 'presupuestocartera':0},'154053':{'presupuesto':0, 'presupuestocartera':0},'154048':{'presupuesto':0, 'presupuestocartera':0},'154042':{'presupuesto':30000000, 'presupuestocartera':2900555},'154031':{'presupuesto':0, 'presupuestocartera':0},'154039':{'presupuesto':0, 'presupuestocartera':36593510},'154051':{'presupuesto':0, 'presupuestocartera':0},'154008':{'presupuesto':0, 'presupuestocartera':0},'154052':{'presupuesto':30000000, 'presupuestocartera':22401378},'154055':{'presupuesto':40000000, 'presupuestocartera':85788263},'154050':{'presupuesto':0, 'presupuestocartera':0}},
    "grupos_vendedores": {"MOSTRADOR PEREIRA": ["ALEJANDRO CARBALLO MARQUEZ", "GEORGINA A. GALVIS HERRERA"], "MOSTRADOR ARMENIA": ["CRISTIAN CAMILO RENDON MONTES", "FANDRY JOHANA ABRIL PENHA", "JAVIER ORLANDO PATINO HURTADO"], "MOSTRADOR MANIZALES": ["DAVID FELIPE MARTINEZ RIOS", "JHON JAIRO CASTAÑO MONTES"], "MOSTRADOR LAURELES": ["MAURICIO RIOS MORALES"], "MOSTRADOR OPALO": ["MARIA PAULA DEL JESUS GALVIS HERRERA"]},
    "metas_cl4_individual": {
        '154033': 15, '154044': 2, '154034': 2, '154014': 30, '154046': 2, '154012': 30,
        '154043': 15, '154035': 2, '154006': 15, '154049': 15, '154013': 3, '154011': 3, '154029': 10, '154055': 10,
        'MOSTRADOR PEREIRA': 3, 'MOSTRADOR ARMENIA': 3, 'MOSTRADOR MANIZALES': 3,
        'MOSTRADOR LAURELES': 3, 'MOSTRADOR OPALO': 3
    },
    "mapeo_meses": {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"},
    "mapeo_marcas": {50:"P8-ASC-MEGA", 54:"MPY-International", 55:"DPP-AN COLORANTS LATAM", 56:"DPP-Pintuco Profesional", 57:"ASC-Mega", 58:"DPP-Pintuco", 59:"DPP-Madetec", 60:"POW-Interpon", 61:"various", 62:"DPP-ICO", 63:"DPP-Terinsa", 64:"MPY-Pintuco", 65:"non-AN Third Party", 66:"ICO-AN Packaging", 67:"ASC-Automotive OEM", 68:"POW-Resicoat", 73:"DPP-Coral", 91:"DPP-Sikkens"}
}

st.set_page_config(page_title=APP_CONFIG["page_title"], page_icon="🏠", layout="wide", initial_sidebar_state="expanded")

# === ESTILOS CSS CORREGIDOS ===
st.markdown("""
<style>
    :root {
        --ferreinox-primary: #1e3a8a;
        --ferreinox-secondary: #3b82f6;
        --ferreinox-accent: #f59e0b;
        --ferreinox-success: #10b981;
        --ferreinox-danger: #ef4444;
        --ferreinox-light: #f8fafc;
        --ferreinox-dark: #1f2937;
    }
    
    /* Header Profesional */
    .main-header {
        background: linear-gradient(135deg, var(--ferreinox-primary) 0%, var(--ferreinox-secondary) 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(30, 58, 138, 0.3);
        text-align: center;
    }
    .main-header h1 {
        color: white; font-size: 2.5rem; font-weight: 800; margin: 0 0 0.5rem 0;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3); letter-spacing: -0.5px;
    }
    .main-header p { color: rgba(255, 255, 255, 0.95); font-size: 1.1rem; margin: 0; font-weight: 500; }
    
    /* Métricas */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
        padding: 1.5rem; border-radius: 12px;
        border-left: 5px solid var(--ferreinox-secondary);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08); transition: all 0.3s ease;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15); border-left-color: var(--ferreinox-accent); }
    div[data-testid="stMetric"] label { color: var(--ferreinox-dark); font-weight: 700; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.5px; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: var(--ferreinox-primary); font-size: 2.2rem; font-weight: 800; }
    
    /* Botones */
    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, var(--ferreinox-primary) 0%, var(--ferreinox-secondary) 100%);
        color: white; font-weight: 700; border: none; border-radius: 10px;
        padding: 0.85rem 2.5rem; font-size: 1.1rem;
        box-shadow: 0 6px 20px rgba(30, 58, 138, 0.4); transition: all 0.3s ease;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background: linear-gradient(135deg, var(--ferreinox-secondary) 0%, var(--ferreinox-primary) 100%);
        box-shadow: 0 8px 30px rgba(30, 58, 138, 0.5); transform: translateY(-3px);
    }

    /* Tablas */
    div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08); border: 1px solid #e5e7eb; }

    /* Footer */
    .ferreinox-footer { text-align: center; padding: 2rem; margin-top: 4rem; border-top: 2px solid #e5e7eb; background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%); }
    .ferreinox-footer a { color: var(--ferreinox-primary); text-decoration: none; font-weight: 700; transition: color 0.2s; }
    .ferreinox-footer a:hover { color: var(--ferreinox-secondary); }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. FUNCIONES DE CARGA Y PROCESAMIENTO
# ==============================================================================
@st.cache_resource(show_spinner=False)
def get_dropbox_client():
    return dropbox.Dropbox(
        app_key=st.secrets.dropbox.app_key,
        app_secret=st.secrets.dropbox.app_secret,
        oauth2_refresh_token=st.secrets.dropbox.refresh_token
    )

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='AlbaranesPendientes', startrow=1, header=False)
        workbook = writer.book
        worksheet = writer.sheets['AlbaranesPendientes']
        header_format = workbook.add_format({'bold': True, 'text_wrap': False, 'valign': 'vcenter', 'align': 'center', 'fg_color': '#1F4E78', 'font_color': 'white', 'border': 1})
        currency_format = workbook.add_format({'num_format': '$#,##0', 'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1, 'align': 'left'})
        default_format = workbook.add_format({'border': 1})
        for col_num, value in enumerate(df.columns.values): worksheet.write(0, col_num, value, header_format)
        worksheet.set_column('A:A', 12, date_format)
        worksheet.set_column('B:B', 35, default_format)
        worksheet.set_column('C:C', 25, default_format)
        worksheet.set_column('D:D', 35, default_format)
        worksheet.set_column('E:E', 20, currency_format)
        worksheet.autofilter(0, 0, df.shape[0], df.shape[1] - 1)
    return output.getvalue()

def to_excel_oportunidades(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Oportunidades_CL4')
        workbook = writer.book
        worksheet = writer.sheets['Oportunidades_CL4']
        header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center', 'fg_color': '#1F4E78', 'font_color': 'white', 'border': 1})
        opportunity_format = workbook.add_format({'bg_color': '#FFFFCC', 'border': 1})
        default_format = workbook.add_format({'border': 1})
        for col_num, value in enumerate(df.columns.values): worksheet.write(0, col_num, value, header_format)
        marcas_cols = APP_CONFIG['productos_oportunidad_cl4']
        for marca in marcas_cols:
            if marca in df.columns:
                col_idx = df.columns.get_loc(marca)
                worksheet.conditional_format(1, col_idx, len(df), col_idx, {'type': 'cell', 'criteria': '==', 'value': 0, 'format': opportunity_format})
        worksheet.set_column('A:A', 45, default_format)
        worksheet.set_column('B:B', 15, default_format)
        col_start_marcas = df.columns.get_loc(marcas_cols[0]) if marcas_cols and marcas_cols[0] in df.columns else 4
        worksheet.set_column(col_start_marcas, col_start_marcas + len(marcas_cols) - 1, 15, default_format)
        worksheet.autofilter(0, 0, df.shape[0], df.shape[1] - 1)
    return output.getvalue()

def to_excel_ventas_mensual(df):
    output = io.BytesIO()
    df_excel = df[['fecha_venta', 'TipoDocumento', 'Serie', 'nombre_cliente', 'nombre_articulo', 'unidades_vendidas', 'valor_venta', 'nomvendedor']].copy()
    df_excel.columns = ['Fecha', 'Tipo Documento', 'Serie', 'Cliente', 'Artículo', 'Unidades', 'Valor Venta', 'Vendedor']
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_excel.to_excel(writer, index=False, sheet_name='Ventas_del_Mes')
        workbook = writer.book
        worksheet = writer.sheets['Ventas_del_Mes']
        header_format = workbook.add_format({'bold': True, 'valign': 'vcenter', 'align': 'center', 'fg_color': '#4472C4', 'font_color': 'white', 'border': 1})
        currency_format = workbook.add_format({'num_format': '$#,##0.00', 'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1})
        default_format = workbook.add_format({'border': 1})
        for col_num, value in enumerate(df_excel.columns): worksheet.write(0, col_num, value, header_format)
        worksheet.set_column('A:A', 12, date_format)
        worksheet.set_column('B:B', 18, default_format)
        worksheet.set_column('C:C', 15, default_format)
        worksheet.set_column('D:D', 40, default_format)
        worksheet.set_column('E:E', 45, default_format)
        worksheet.set_column('G:G', 18, currency_format)
        worksheet.autofilter(0, 0, df_excel.shape[0], df_excel.shape[1] - 1)
        worksheet.freeze_panes(1, 0)
    return output.getvalue()

def to_excel_analisis_cliente(df, cliente_nombre, fecha_inicio, fecha_fin, total_venta, num_facturas):
    output = io.BytesIO()
    df_excel = df[['fecha_venta', 'TipoDocumento', 'Serie', 'nombre_articulo', 'unidades_vendidas', 'valor_venta']].copy()
    df_excel.columns = ['Fecha', 'Tipo Documento', 'Serie', 'Artículo', 'Unidades', 'Valor Venta']
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_excel.to_excel(writer, index=False, sheet_name='Analisis_Cliente', startrow=5)
        workbook = writer.book
        worksheet = writer.sheets['Analisis_Cliente']
        title_format = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#1F4E78', 'valign': 'vcenter'})
        subtitle_format = workbook.add_format({'bold': True, 'font_size': 12, 'fg_color': '#DDEBF7', 'border': 1, 'align': 'right'})
        value_format = workbook.add_format({'font_size': 12, 'border': 1, 'num_format': '$#,##0.00'})
        header_format = workbook.add_format({'bold': True, 'valign': 'vcenter', 'align': 'center', 'fg_color': '#4472C4', 'font_color': 'white', 'border': 1})
        currency_format = workbook.add_format({'num_format': '$#,##0.00', 'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1})
        default_format = workbook.add_format({'border': 1})
        worksheet.merge_range('B1:F1', f"Análisis de Compras: {cliente_nombre}", title_format)
        worksheet.write('B2', 'Periodo Desde:', subtitle_format)
        worksheet.write('C2', fecha_inicio.strftime('%Y-%m-%d'), value_format)
        worksheet.write('B3', 'Periodo Hasta:', subtitle_format)
        worksheet.write('C3', fecha_fin.strftime('%Y-%m-%d'), value_format)
        worksheet.write('E2', 'Total Venta Neta:', subtitle_format)
        worksheet.write('F2', total_venta, value_format)
        worksheet.write('E3', 'Número de Facturas:', subtitle_format)
        worksheet.write('F3', num_facturas, workbook.add_format({'font_size': 12, 'border': 1}))
        for col_num, value in enumerate(df_excel.columns): worksheet.write(4, col_num, value, header_format)
        worksheet.set_column(0, 0, 12, date_format)
        worksheet.set_column(1, 1, 18, default_format)
        worksheet.set_column(3, 3, 50, default_format)
        worksheet.set_column(5, 5, 18, currency_format)
        worksheet.autofilter(4, 0, df_excel.shape[0] + 4, df_excel.shape[1] - 1)
        worksheet.freeze_panes(5, 0)
    return output.getvalue()

def normalizar_texto(texto):
    if not isinstance(texto, str): return texto
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').replace('_', ' ').replace('.', ' ').strip().replace('  ', ' ')
    except (TypeError, AttributeError): return texto

APP_CONFIG['complementarios']['exclude_super_categoria'] = normalizar_texto(APP_CONFIG['complementarios']['exclude_super_categoria'])
APP_CONFIG['sub_meta_complementarios']['nombre_marca_objetivo'] = normalizar_texto(APP_CONFIG['sub_meta_complementarios']['nombre_marca_objetivo'])
APP_CONFIG['categorias_clave_venta'] = [normalizar_texto(cat) for cat in APP_CONFIG['categorias_clave_venta']]

@st.cache_data(ttl=1800)
def cargar_y_limpiar_datos(ruta_archivo, nombres_columnas):
    try:
        dbx = get_dropbox_client()
        _, res = dbx.files_download(path=ruta_archivo)
        contenido_csv = res.content.decode('latin-1')
        df = pd.read_csv(io.StringIO(contenido_csv), header=None, sep='|', engine='python', quoting=3, on_bad_lines='warn')
        if df.shape[1] < 5 and not df.empty:
            st.error(f"Error de Carga en {ruta_archivo}: Se leyó una sola columna.")
            return pd.DataFrame(columns=nombres_columnas)
        if df.shape[1] != len(nombres_columnas):
            if df.shape[1] < len(nombres_columnas): df = df.reindex(columns=range(len(nombres_columnas)))
        df.columns = nombres_columnas
        if 'codigo_vendedor' in df.columns:
            df['codigo_vendedor'] = pd.to_numeric(df['codigo_vendedor'], errors='coerce').fillna(0).astype(int).astype(str)
        numeric_cols = ['anio', 'mes', 'valor_venta', 'valor_cobro', 'unidades_vendidas', 'costo_unitario', 'marca_producto']
        for col in numeric_cols:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=['anio', 'mes'], inplace=True)
        df = df.astype({'anio': int, 'mes': int})
        if 'fecha_venta' in df.columns: df['fecha_venta'] = pd.to_datetime(df['fecha_venta'], errors='coerce')
        if 'cliente_id' in df.columns: df['cliente_id'] = df['cliente_id'].astype(str)
        if 'marca_producto' in df.columns: df['nombre_marca'] = df['marca_producto'].map(DATA_CONFIG["mapeo_marcas"]).fillna('No Especificada')
        cols_a_normalizar = ['super_categoria', 'categoria_producto', 'nombre_marca', 'nomvendedor', 'TipoDocumento', 'nombre_articulo', 'nombre_cliente']
        for col in cols_a_normalizar:
            if col in df.columns: df[col] = df[col].apply(normalizar_texto)
        return df
    except Exception as e:
        st.error(f"Error crítico al cargar {ruta_archivo}: {e}")
        return pd.DataFrame(columns=nombres_columnas)

@st.cache_data(ttl=1800)
def cargar_reporte_cl4(ruta_archivo):
    try:
        dbx = get_dropbox_client()
        _, res = dbx.files_download(path=ruta_archivo)
        df = pd.read_excel(io.BytesIO(res.content))
        df.columns = [normalizar_texto(col) for col in df.columns]
        columna_id_encontrada = None
        for nombre in ['ID CLIENTE', 'IDCLIENTE']:
            if nombre in df.columns:
                columna_id_encontrada = nombre
                break
        if columna_id_encontrada:
            df.rename(columns={columna_id_encontrada: 'cliente_id'}, inplace=True)
            df['cliente_id'] = df['cliente_id'].astype(str)
            if 'NIT' in df.columns: df['NIT'] = df['NIT'].astype(str).str.strip()
            if 'NOMBRE' in df.columns: df['NOMBRE'] = df['NOMBRE'].astype(str)
            for producto in APP_CONFIG['productos_oportunidad_cl4']:
                if producto in df.columns: df[producto] = pd.to_numeric(df[producto], errors='coerce').fillna(0)
        else:
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Error crítico al cargar el reporte de oportunidades: {e}")
        return pd.DataFrame()

def actualizar_oportunidades_con_ventas_del_trimestre(df_cl4_original, df_ventas_historicas, anio_seleccionado, mes_seleccionado):
    if df_cl4_original is None or df_cl4_original.empty: return pd.DataFrame()
    df_cl4_actualizado = df_cl4_original.copy()
    inicio_trimestre = (((mes_seleccionado - 1) // 3) * 3) + 1
    meses_a_buscar = list(range(inicio_trimestre, mes_seleccionado + 1))
    df_ventas_trimestre = df_ventas_historicas[
        (df_ventas_historicas['anio'] == anio_seleccionado) &
        (df_ventas_historicas['mes'].isin(meses_a_buscar))
    ].copy()
    if df_ventas_trimestre.empty: return df_cl4_actualizado
    productos_oportunidad = APP_CONFIG['productos_oportunidad_cl4']
    clientes_cl4 = set(df_cl4_actualizado['cliente_id'])
    df_ventas_clientes_cl4 = df_ventas_trimestre[df_ventas_trimestre['cliente_id'].isin(clientes_cl4)]
    if df_ventas_clientes_cl4.empty: return df_cl4_actualizado
    mes_inicio_str = DATA_CONFIG['mapeo_meses'].get(inicio_trimestre, '')
    mes_fin_str = DATA_CONFIG['mapeo_meses'].get(mes_seleccionado, '')
    st.toast(f"Actualizando oportunidades con ventas de {mes_inicio_str} a {mes_fin_str}...", icon="🔍")
    compras_por_cliente = {}
    for producto in productos_oportunidad:
        clientes_que_compraron = df_ventas_clientes_cl4[
            df_ventas_clientes_cl4['nombre_articulo'].str.contains(producto, case=False, na=False)
        ]['cliente_id'].unique()
        compras_por_cliente[producto] = set(clientes_que_compraron)
    for producto in productos_oportunidad:
        if producto in df_cl4_actualizado.columns:
            df_cl4_actualizado[producto] = df_cl4_actualizado['cliente_id'].apply(
                lambda cid: 1 if cid in compras_por_cliente[producto] else 0
            )
    columnas_producto_existentes = [p for p in productos_oportunidad if p in df_cl4_actualizado.columns]
    if columnas_producto_existentes:
        df_cl4_actualizado['CL4'] = df_cl4_actualizado[columnas_producto_existentes].sum(axis=1)
    return df_cl4_actualizado

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
        anio_anterior = anio_sel - 1
        df_grupo_historico_facturas = df_ventas_historicas[
            (df_ventas_historicas['TipoDocumento'].str.contains(filtro_ventas_netas, na=False, case=False, regex=True)) &
            (df_ventas_historicas['anio'] == anio_anterior) & (df_ventas_historicas['mes'] == mes_sel) &
            (df_ventas_historicas['nomvendedor'].isin(lista_vendedores_norm))
        ]
        ventas_anio_anterior = df_grupo_historico_facturas['valor_venta'].sum() if not df_grupo_historico_facturas.empty else 0
        presupuesto_dinamico = ventas_anio_anterior * incremento_mostradores
        df_grupo_actual = df_resumen[df_resumen['nomvendedor'].isin(lista_vendedores_norm)]
        cols_a_sumar = ['ventas_totales', 'cobros_totales', 'impactos', 'presupuestocartera', 'ventas_complementarios', 'ventas_sub_meta', 'albaranes_pendientes']
        suma_grupo = df_grupo_actual[cols_a_sumar].sum().to_dict()
        suma_grupo['presupuesto'] = df_grupo_actual['presupuesto'].sum() 
        codigo_grupo_norm = normalizar_texto(grupo)
        registro = {'nomvendedor': codigo_grupo_norm, 'codigo_vendedor': codigo_grupo_norm, **suma_grupo}
        if presupuesto_dinamico > 0: registro['presupuesto'] = presupuesto_dinamico
        registros_agrupados.append(registro)
    df_agrupado = pd.DataFrame(registros_agrupados)
    vendedores_en_grupos = [v for lista in DATA_CONFIG['grupos_vendedores'].values() for v in [normalizar_texto(i) for i in lista]]
    df_individuales = df_resumen[~df_resumen['nomvendedor'].isin(vendedores_en_grupos)]
    df_final = pd.concat([df_agrupado, df_individuales], ignore_index=True)
    df_final.fillna(0, inplace=True)
    df_final['presupuesto_complementarios'] = df_final['presupuesto'] * APP_CONFIG['complementarios']['presupuesto_pct']
    df_final['presupuesto_sub_meta'] = df_final['presupuesto_complementarios'] * APP_CONFIG['sub_meta_complementarios']['presupuesto_pct']
    return df_final, df_albaranes_reales_pendientes

def generar_comentario_asesor(avance_v, avance_c, clientes_meta, meta_clientes, avance_comp, avance_sub_meta):
    comentarios = []
    if avance_v >= 100: comentarios.append("📈 **Ventas:** ¡Felicitaciones! Has superado la meta de ventas netas.")
    elif avance_v >= 80: comentarios.append("📈 **Ventas:** ¡Estás muy cerca de la meta neta! Un último esfuerzo.")
    else: comentarios.append("📈 **Ventas:** Planifica tus visitas y aprovecha cada oportunidad para mejorar tu venta neta.")
    if avance_c >= 100: comentarios.append("💰 **Cartera:** Objetivo de recaudo cumplido. ¡Gestión impecable!")
    else: comentarios.append("💰 **Cartera:** Recuerda hacer seguimiento a la cartera pendiente.")
    if meta_clientes > 0:
        if clientes_meta >= meta_clientes: comentarios.append(f"🎯 **Meta Clientes (CL4):** ¡Objetivo Cumplido! {clientes_meta}/{meta_clientes} clientes.")
        else: comentarios.append(f"🎯 **Meta Clientes (CL4):** Avance: {clientes_meta}/{meta_clientes}. ¡Revisa oportunidades!")
    if avance_comp >= 100: comentarios.append("⚙️ **Complementarios:** ¡Excelente! Cumpliste la meta.")
    else: comentarios.append(f"⚙️ **Complementarios:** Avance: {avance_comp:.1f}%. ¡Impulsa venta cruzada!")
    sub_meta_label = APP_CONFIG['sub_meta_complementarios']['nombre_marca_objetivo']
    if avance_sub_meta >= 100: comentarios.append(f"⭐ **Meta {sub_meta_label}:** ¡Logrado!")
    else: comentarios.append(f"⭐ **Meta {sub_meta_label}:** Avance: {avance_sub_meta:.1f}%.")
    return comentarios

def mostrar_alerta_inteligente(avance_ventas, avance_cobros, avance_cl4, dias_restantes):
    """Sistema de alertas contextuales basadas en rendimiento"""
    if dias_restantes <= 7:
        if avance_ventas < 80:
            st.toast("⚠️ ¡Solo quedan 7 días! Acelera gestión de ventas", icon="⚠️")
        if avance_cobros < 70:
            st.toast("💰 Prioriza gestión de cartera esta semana", icon="💰")
    if avance_ventas >= 100:
        st.toast("🎉 ¡Meta de ventas alcanzada! ¡Excelente trabajo!", icon="🎉")
    if avance_cl4 >= 100:
        st.toast("🏆 ¡Meta CL4 cumplida! Clientes bien atendidos", icon="🏆")
    if avance_cobros >= 100 and avance_ventas >= 100:
        st.toast("⭐ ¡Doble meta! Ventas y Cobros al 100%", icon="⭐")

def render_analisis_detallado(df_vista, df_ventas_periodo):
    st.markdown("---")
    st.header("🔬 Análisis Detallado del Periodo")
    opciones_enfoque = ["Visión General"] + sorted(df_vista['nomvendedor'].unique())
    enfoque_sel = st.selectbox("Enfocar análisis en:", opciones_enfoque, index=0, key="sb_enfoque_analisis")
    if enfoque_sel == "Visión General":
        nombres_a_filtrar = []
        for vendedor in df_vista['nomvendedor']:
            vendedor_norm = normalizar_texto(vendedor)
            nombre_grupo_orig = next((k for k in DATA_CONFIG['grupos_vendedores'] if normalizar_texto(k) == vendedor_norm), None)
            if nombre_grupo_orig:
                lista_vendedores = DATA_CONFIG['grupos_vendedores'].get(nombre_grupo_orig, [])
                nombres_a_filtrar.extend([normalizar_texto(v) for v in lista_vendedores])
            else:
                nombres_a_filtrar.append(vendedor_norm)
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
            if not df_ventas_enfocadas.empty and 'nombre_marca' in df_ventas_enfocadas:
                df_marcas = df_ventas_enfocadas.groupby('nombre_marca')['valor_venta'].sum().reset_index()
                fig = px.treemap(df_marcas, path=[px.Constant("Todas las Marcas"), 'nombre_marca'], values='valor_venta')
                fig.update_layout(margin=dict(t=25, l=25, r=25, b=25))
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("No hay datos de marcas de productos para mostrar.")
        with col2:
            if not df_ventas_enfocadas.empty and 'nombre_articulo' in df_ventas_enfocadas:
                ventas_marquillas = {p: df_ventas_enfocadas[df_ventas_enfocadas['nombre_articulo'].str.contains(p, case=False, na=False)]['valor_venta'].sum() for p in APP_CONFIG['marquillas_clave']}
                df_ventas_marquillas = pd.DataFrame(list(ventas_marquillas.items()), columns=['Marquilla', 'Ventas']).sort_values('Ventas', ascending=False)
                fig = px.pie(df_ventas_marquillas, names='Marquilla', values='Ventas', title="Distribución Venta Neta Marquillas", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("No hay datos de marquillas para mostrar.")
    with tab2:
        df_ranking_con_meta = df_ranking[df_ranking['presupuesto'] > 0].copy()
        if not df_ranking_con_meta.empty:
            df_ranking_con_meta['avance_ventas'] = (df_ranking_con_meta['ventas_totales'] / df_ranking_con_meta['presupuesto']) * 100
            df_ranking_con_meta.sort_values('avance_ventas', ascending=True, inplace=True)
            fig = px.bar(df_ranking_con_meta, x='avance_ventas', y='nomvendedor', orientation='h', text='avance_ventas', title="Cumplimiento de Meta de Ventas Netas (%)")
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("No hay datos de presupuesto para generar el ranking.")
    with tab3:
        filtro_ventas_netas = 'FACTURA|NOTA.*CREDITO'
        if not df_ventas_enfocadas.empty:
            df_facturas_enfocadas = df_ventas_enfocadas[df_ventas_enfocadas['TipoDocumento'].str.contains(filtro_ventas_netas, na=False, case=False, regex=True)]
            top_clientes = df_facturas_enfocadas.groupby('nombre_cliente')['valor_venta'].sum().nlargest(10).reset_index()
            st.dataframe(top_clientes, column_config={"nombre_cliente": "Cliente", "valor_venta": st.column_config.NumberColumn("Total Compra (Neta)", format="$ %d")}, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("📥 Descargar Reporte de Ventas del Mes")
            df_para_descarga_mes = df_facturas_enfocadas.copy()
            excel_data_mes = to_excel_ventas_mensual(df_para_descarga_mes)
            st.download_button(label="📥 Descargar Ventas del Mes (Excel)", data=excel_data_mes, file_name=f"Ventas_Mes_{enfoque_sel.replace(' ', '_')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
            st.markdown("---")
            st.subheader("🔍 Análisis Específico por Cliente")
            lista_clientes = sorted(df_facturas_enfocadas['nombre_cliente'].unique())
            if lista_clientes:
                cliente_seleccionado = st.selectbox("Seleccione un Cliente:", options=lista_clientes)
                col1, col2 = st.columns(2)
                with col1: fecha_inicio = st.date_input("Fecha de Inicio", datetime.date(st.session_state.get('anio_sel', 2024), st.session_state.get('mes_sel_num', 1), 1))
                with col2: fecha_fin = st.date_input("Fecha de Fin", datetime.date.today())

                if fecha_inicio and fecha_fin and fecha_inicio <= fecha_fin:
                    df_ventas_historicas = st.session_state.df_ventas
                    mask_documento = df_ventas_historicas['TipoDocumento'].str.contains(filtro_ventas_netas, na=False, case=False, regex=True)
                    df_historico_facturas = df_ventas_historicas[mask_documento]
                    mask_cliente_rango = ((df_historico_facturas['nombre_cliente'] == cliente_seleccionado) & (df_historico_facturas['fecha_venta'].dt.date >= fecha_inicio) & (df_historico_facturas['fecha_venta'].dt.date <= fecha_fin))
                    df_cliente_rango = df_historico_facturas[mask_cliente_rango].copy()
                    if not df_cliente_rango.empty:
                        total_venta_cliente = df_cliente_rango['valor_venta'].sum()
                        num_facturas_cliente = df_cliente_rango[df_cliente_rango['TipoDocumento'] == 'FACTURA']['Serie'].nunique()
                        m_col1, m_col2 = st.columns(2)
                        m_col1.metric("Total Venta Neta en Rango", f"${total_venta_cliente:,.0f}")
                        m_col2.metric("Número de Facturas", f"{num_facturas_cliente}")
                        st.dataframe(df_cliente_rango[['fecha_venta', 'TipoDocumento', 'Serie', 'nombre_articulo', 'valor_venta']], use_container_width=True, hide_index=True)
                        excel_data_cliente = to_excel_analisis_cliente(df_cliente_rango, cliente_seleccionado, fecha_inicio, fecha_fin, total_venta_cliente, num_facturas_cliente)
                        st.download_button(label=f"📥 Descargar Análisis para {cliente_seleccionado}", data=excel_data_cliente, file_name=f"Analisis_{cliente_seleccionado.replace(' ', '_')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                    else: st.warning("El cliente seleccionado no tiene ventas en el rango de fechas especificado.")
            else: st.info("No hay clientes con ventas para analizar en la selección actual.")
    with tab4:
        st.subheader(f"Desempeño en Categorías Clave")
        categorias_objetivo = sorted(list(set(APP_CONFIG['categorias_clave_venta'])))
        df_ventas_cat = df_ventas_enfocadas[df_ventas_enfocadas['categoria_producto'].isin(categorias_objetivo)]
        if not df_ventas_cat.empty:
            col1, col2 = st.columns([0.5, 0.5])
            with col1:
                resumen_cat = df_ventas_cat.groupby('categoria_producto').agg(Ventas=('valor_venta', 'sum')).reset_index()
                total_ventas_enfocadas = df_ventas_enfocadas['valor_venta'].sum()
                resumen_cat['Participacion (%)'] = (resumen_cat['Ventas'] / total_ventas_enfocadas * 100) if total_ventas_enfocadas > 0 else 0
                resumen_cat = resumen_cat.sort_values('Ventas', ascending=False)
                st.dataframe(resumen_cat, column_config={"categoria_producto": "Categoría", "Ventas": st.column_config.NumberColumn("Total Venta", format="$ %d"),"Participacion (%)": st.column_config.ProgressColumn("Part. %", format="%.2f%%", min_value=0, max_value=resumen_cat['Participacion (%)'].max())}, use_container_width=True, hide_index=True)
            with col2:
                fig = px.pie(resumen_cat, names='categoria_producto', values='Ventas', title="Distribución Categorías Clave", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
        else: st.info("No hay ventas en categorías clave.")

@st.cache_data
def calcular_albaranes_anuales(df_ventas_historicas, anio_sel):
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
    return df_albaranes_pendientes_del_anio[df_albaranes_pendientes_del_anio['valor_venta'] > 0]

# ==============================================================================
# 3. INTERFAZ Y RENDERIZADO (DASHBOARD)
# ==============================================================================
def render_dashboard():
    st.sidebar.markdown("---")
    st.sidebar.header("Filtros de Periodo")

    df_ventas_historicas = st.session_state.df_ventas
    df_cobros_historicos = st.session_state.df_cobros
    df_cl4_base = st.session_state.df_cl4

    if df_ventas_historicas is None or df_ventas_historicas.empty:
        st.error("No se pudieron cargar los datos de ventas.")
        return

    lista_anios = sorted(df_ventas_historicas['anio'].unique(), reverse=True)
    anio_reciente = int(df_ventas_historicas['anio'].max())
    mes_reciente = int(df_ventas_historicas[df_ventas_historicas['anio'] == anio_reciente]['mes'].max())
    anio_sel = st.sidebar.selectbox("Elija el Año", lista_anios, index=0, key="sb_anio")
    st.session_state.anio_sel = anio_sel 
    lista_meses_num = sorted(df_ventas_historicas[df_ventas_historicas['anio'] == anio_sel]['mes'].unique())

    if not lista_meses_num:
        st.warning(f"No hay datos de ventas para el año {anio_sel}.")
        return

    index_mes_defecto = lista_meses_num.index(mes_reciente) if anio_sel == anio_reciente and mes_reciente in lista_meses_num else len(lista_meses_num) - 1
    mes_sel_num = st.sidebar.selectbox("Elija el Mes", options=lista_meses_num, format_func=lambda x: DATA_CONFIG['mapeo_meses'].get(x, 'N/A'), index=index_mes_defecto, key="sb_mes")
    st.session_state.mes_sel_num = mes_sel_num 

    df_ventas_periodo = df_ventas_historicas[(df_ventas_historicas['anio'] == anio_sel) & (df_ventas_historicas['mes'] == mes_sel_num)]

    if df_ventas_periodo.empty and (df_cl4_base is None or df_cl4_base.empty):
        st.warning("No se encontraron datos de ventas ni de oportunidades CL4 para el periodo seleccionado.")
        return
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
            return
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

            col_refresh, col_info = st.columns([1, 2])
            with col_refresh:
                if st.button("🔄 Actualizar Datos", type="primary", use_container_width=True):
                    with st.spinner("🔄 Limpiando caché y recargando..."):
                        st.cache_data.clear()
                        usuario_temp = st.session_state.usuario
                        autenticado_temp = st.session_state.autenticado
                        st.session_state.clear()
                        st.session_state.usuario = usuario_temp
                        st.session_state.autenticado = autenticado_temp
                        time.sleep(0.5)
                    st.toast("✅ Datos actualizados exitosamente", icon="✅")
                    st.rerun()

            vista_para = st.session_state.usuario if len(df_vista['nomvendedor'].unique()) == 1 else 'Múltiples Seleccionados'
            st.markdown(f"**Vista para:** `{vista_para}`")

            # Lógica Oportunidades
            df_cl4_actualizado = actualizar_oportunidades_con_ventas_del_trimestre(df_cl4_base, df_ventas_historicas, anio_sel, mes_sel_num)
            mapa_cliente_vendedor = df_ventas_historicas.drop_duplicates(subset=['cliente_id'], keep='last')[['cliente_id', 'nomvendedor', 'codigo_vendedor']]
            if not df_cl4_actualizado.empty:
                df_cl4_con_vendedor = pd.merge(df_cl4_actualizado, mapa_cliente_vendedor, on='cliente_id', how='left')
                df_cl4_con_vendedor['nomvendedor'] = df_cl4_con_vendedor['nomvendedor'].apply(normalizar_texto).fillna('SIN ASIGNAR')
                df_cl4_con_vendedor['codigo_vendedor'].fillna('SIN ASIGNAR', inplace=True)
            else:
                df_cl4_con_vendedor = pd.DataFrame()

            vendedores_vista_actual = df_vista['nomvendedor'].unique() if not df_vista.empty else []
            codigos_vista_actual = df_vista['codigo_vendedor'].unique() if not df_vista.empty else []

            nombres_a_filtrar = []
            for vendedor_norm in vendedores_vista_actual:
                nombre_grupo_orig = next((k for k in DATA_CONFIG['grupos_vendedores'] if normalizar_texto(k) == vendedor_norm), None)
                if nombre_grupo_orig:
                    lista_vendedores = DATA_CONFIG['grupos_vendedores'].get(nombre_grupo_orig, [])
                    nombres_a_filtrar.extend([normalizar_texto(v) for v in lista_vendedores])
                else:
                    nombres_a_filtrar.append(vendedor_norm)

            if not df_cl4_con_vendedor.empty:
                df_cl4_filtrado = df_cl4_con_vendedor[df_cl4_con_vendedor['nomvendedor'].isin(nombres_a_filtrar)]
            else:
                df_cl4_filtrado = pd.DataFrame()

            meta_clientes_cl4 = 0
            if usuario_actual_norm == "GERENTE":
                metas_a_sumar = {k: v for k, v in DATA_CONFIG['metas_cl4_individual'].items()}
                for codigo_v_o_g in codigos_vista_actual:
                    meta_clientes_cl4 += metas_a_sumar.get(str(codigo_v_o_g), 0)
            else:
                codigo_usuario_actual = df_vista['codigo_vendedor'].iloc[0] if not df_vista.empty else None
                if codigo_usuario_actual:
                    meta_clientes_cl4 = DATA_CONFIG['metas_cl4_individual'].get(str(codigo_usuario_actual), 0)

            clientes_en_meta = df_cl4_filtrado[df_cl4_filtrado['CL4'] >= 4].shape[0] if not df_cl4_filtrado.empty else 0
            avance_clientes_cl4 = (clientes_en_meta / meta_clientes_cl4 * 100) if meta_clientes_cl4 > 0 else 0

            ventas_total, meta_ventas, cobros_total, meta_cobros, comp_total, meta_comp, sub_meta_total, meta_sub_meta, total_albaranes = [0] * 9
            if not df_vista.empty:
                ventas_total = df_vista['ventas_totales'].sum()
                meta_ventas = df_vista['presupuesto'].sum()
                cobros_total = df_vista['cobros_totales'].sum()
                meta_cobros = df_vista['presupuestocartera'].sum()
                comp_total = df_vista['ventas_complementarios'].sum()
                meta_comp = df_vista['presupuesto_complementarios'].sum()
                sub_meta_total = df_vista['ventas_sub_meta'].sum()
                meta_sub_meta = df_vista['presupuesto_sub_meta'].sum()
                total_albaranes = df_vista['albaranes_pendientes'].sum()

            avance_ventas = (ventas_total / meta_ventas * 100) if meta_ventas > 0 else 0
            avance_cobros = (cobros_total / meta_cobros * 100) if meta_cobros > 0 else 0
            avance_comp = (comp_total / meta_comp * 100) if meta_comp > 0 else 0
            avance_sub_meta = (sub_meta_total / meta_sub_meta * 100) if meta_sub_meta > 0 else 0
            
            # --- Lógica de Días Restantes (Nuevo) ---
            ultimo_dia = calendar.monthrange(anio_sel, mes_sel_num)[1]
            es_mes_actual = (anio_sel == datetime.datetime.now().year) and (mes_sel_num == datetime.datetime.now().month)
            dias_restantes = ultimo_dia - datetime.datetime.now().day if es_mes_actual else 0

            with st.container(border=True):
                st.subheader(f"👨‍💼 Asesor Virtual para: {st.session_state.usuario}")
                comentarios = generar_comentario_asesor(avance_ventas, avance_cobros, clientes_en_meta, meta_clientes_cl4, avance_comp, avance_sub_meta)
                for comentario in comentarios: st.markdown(f"- {comentario}")
                
                # Alerta Inteligente Integrada
                if dias_restantes >= 0 and es_mes_actual:
                    mostrar_alerta_inteligente(avance_ventas, avance_cobros, avance_clientes_cl4, dias_restantes)

            st.subheader("Métricas Clave del Periodo")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Ventas Netas Facturadas", value=f"${ventas_total:,.0f}", delta=f"{ventas_total - meta_ventas:,.0f}", help=f"Meta: ${meta_ventas:,.0f}")
                st.progress(min(avance_ventas / 100, 1.0), text=f"Avance Ventas Netas: {avance_ventas:.1f}%")
            with col2:
                st.metric(label="Recaudo de Cartera", value=f"${cobros_total:,.0f}", delta=f"{cobros_total - meta_cobros:,.0f}", help=f"Meta: ${meta_cobros:,.0f}")
                st.progress(min(avance_cobros / 100, 1.0), text=f"Avance Cartera: {avance_cobros:.1f}%")
            with col3:
                st.metric(label="Albaranes Pendientes", value=f"${total_albaranes:,.0f}")
                st.info("Valor por facturar")
            st.markdown("<br>", unsafe_allow_html=True)
            col4, col5, col6 = st.columns(3)
            with col4:
                st.metric(label="Venta Complementarios", value=f"${comp_total:,.0f}", delta=f"{comp_total - meta_comp:,.0f}", help=f"Meta: ${meta_comp:,.0f}")
                st.progress(min(avance_comp / 100, 1.0), text=f"Avance: {avance_comp:.1f}%")
            with col5:
                sub_meta_label = APP_CONFIG['sub_meta_complementarios']['nombre_marca_objetivo']
                st.metric(label=f"Venta '{sub_meta_label}'", value=f"${sub_meta_total:,.0f}", delta=f"{sub_meta_total - meta_sub_meta:,.0f}", help=f"Meta: ${meta_sub_meta:,.0f}")
                st.progress(min(avance_sub_meta / 100, 1.0), text=f"Avance: {avance_sub_meta:.1f}%")
            with col6:
                st.metric(label="Clientes en Meta (CL4 ≥ 4)", value=f"{clientes_en_meta}", delta=f"{clientes_en_meta - meta_clientes_cl4}", help=f"Meta: {meta_clientes_cl4} clientes")
                st.progress(min((avance_clientes_cl4 / 100), 1.0), text=f"Avance: {avance_clientes_cl4:.1f}%")

            with st.expander("🎯 Análisis de Oportunidades (Clientes con CL4 < 4)", expanded=True):
                st.info(f"Utiliza esta tabla para identificar clientes con potencial de crecimiento. **(Datos actualizados con ventas del trimestre en curso)**")
                df_oportunidades = df_cl4_filtrado[df_cl4_filtrado['CL4'] < 4].copy() if not df_cl4_filtrado.empty else pd.DataFrame()
                if df_oportunidades.empty:
                    st.success("¡Felicidades! No tienes clientes con oportunidades pendientes en la selección actual.")
                else:
                    def encontrar_faltantes(row):
                        faltantes = [prod for prod in APP_CONFIG['productos_oportunidad_cl4'] if prod in row.index and row[prod] == 0]
                        return ", ".join(faltantes) if faltantes else "N/A"
                    df_oportunidades['Productos a Ofrecer'] = df_oportunidades.apply(encontrar_faltantes, axis=1)
                    cols_display = ['NOMBRE', 'NIT', 'CL4', 'Productos a Ofrecer', 'nomvendedor']
                    df_oportunidades_display = df_oportunidades[cols_display].rename(columns={'NOMBRE': 'Cliente', 'NIT': 'NIT', 'CL4': 'Nivel Actual', 'nomvendedor': 'Vendedor Asignado'})
                    st.dataframe(df_oportunidades_display, use_container_width=True, hide_index=True, column_config={ "NIT": st.column_config.TextColumn("NIT", width="medium") })
                    st.markdown("---")
                    st.subheader("📥 Descargar Reporte de Oportunidades Filtrado")
                    cols_excel = ['NOMBRE', 'NIT', 'CL4', 'nomvendedor'] + APP_CONFIG['productos_oportunidad_cl4']
                    cols_excel_existentes = [c for c in cols_excel if c in df_oportunidades.columns]
                    df_para_descargar_oportunidades = df_oportunidades[cols_excel_existentes].rename(columns={'NOMBRE': 'Cliente', 'NIT': 'NIT Cliente', 'CL4': 'Nivel Actual', 'nomvendedor': 'Vendedor Asignado'})
                    excel_data_oportunidades = to_excel_oportunidades(df_para_descargar_oportunidades)
                    st.download_button(label="📥 Descargar Reporte de Oportunidades (Excel)", data=excel_data_oportunidades, file_name=f"Reporte_Oportunidades_CL4_{anio_sel}_{mes_sel_num}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

            st.markdown("---")
            st.subheader("Desglose por Vendedor / Grupo")
            if not df_vista.empty:
                def contar_clientes_meta_por_vendedor(nomvendedor_o_grupo):
                    vendedor_norm = normalizar_texto(nomvendedor_o_grupo)
                    nombre_grupo_orig = next((k for k in DATA_CONFIG['grupos_vendedores'] if normalizar_texto(k) == vendedor_norm), None)
                    vendedores_del_grupo = [normalizar_texto(v) for v in DATA_CONFIG['grupos_vendedores'].get(nombre_grupo_orig, [nomvendedor_o_grupo])]
                    df_cl4_vendedor = df_cl4_con_vendedor[df_cl4_con_vendedor['nomvendedor'].isin(vendedores_del_grupo)] if not df_cl4_con_vendedor.empty else pd.DataFrame()
                    return df_cl4_vendedor[df_cl4_vendedor['CL4'] >= 4].shape[0] if not df_cl4_vendedor.empty else 0

                df_vista['clientes_meta_cl4'] = df_vista['nomvendedor'].apply(contar_clientes_meta_por_vendedor)
                df_display = df_vista.copy()
                df_display['Avance Ventas %'] = ((df_display['ventas_totales'] / df_display['presupuesto']) * 100).fillna(0)
                df_display['Avance Cobros %'] = ((df_display['cobros_totales'] / df_display['presupuestocartera']) * 100).fillna(0)
                
                cols_desglose = ['Estatus', 'nomvendedor', 'ventas_totales', 'presupuesto', 'Avance Ventas %', 'cobros_totales', 'presupuestocartera', 'Avance Cobros %', 'albaranes_pendientes', 'impactos', 'clientes_meta_cl4']
                
                st.dataframe(df_display[cols_desglose], column_config={
                    "Estatus": st.column_config.TextColumn("🚦", width="small"), "nomvendedor": "Vendedor/Grupo",
                    "ventas_totales": st.column_config.NumberColumn("Ventas Netas", format="$ %d"),
                    "presupuesto": st.column_config.NumberColumn("Meta Ventas", format="$ %d"),
                    "Avance Ventas %": st.column_config.ProgressColumn("Avance V%", format="%.1f%%", min_value=0, max_value=150),
                    "cobros_totales": st.column_config.NumberColumn("Recaudo", format="$ %d"),
                    "presupuestocartera": st.column_config.NumberColumn("Meta Recaudo", format="$ %d"),
                    "Avance Cobros %": st.column_config.ProgressColumn("Avance C%", format="%.1f%%", min_value=0, max_value=150),
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
                st.info("No hay albaranes pendientes de facturación para la selección de filtros actual.")
            else:
                st.dataframe(df_albaranes_a_mostrar[['Serie', 'fecha_venta', 'nombre_cliente', 'valor_venta', 'nomvendedor']],
                             column_config={"Serie": "Documento", "fecha_venta": "Fecha", "nombre_cliente": "Cliente",
                                            "valor_venta": st.column_config.NumberColumn("Valor Pendiente", format="$ %d"),
                                            "nomvendedor": "Vendedor"}, use_container_width=True, hide_index=True)

            st.subheader(f"Descarga Anual de Albaranes ({anio_sel})")
            st.info(f"Descarga el reporte con el valor total por albarán para TODO el año {anio_sel}.")
            with st.spinner(f"Calculando albaranes totales del año {anio_sel}..."):
                df_albaranes_pendientes_del_anio = calcular_albaranes_anuales(df_ventas_historicas, anio_sel)
            if df_albaranes_pendientes_del_anio.empty:
                st.warning(f"No se encontraron albaranes pendientes para descargar en todo el año {anio_sel}.")
            else:
                claves_agrupacion = ['fecha_venta', 'nombre_cliente', 'Serie', 'nomvendedor']
                df_agrupado_anual = df_albaranes_pendientes_del_anio.groupby(claves_agrupacion).agg(valor_venta=('valor_venta', 'sum')).reset_index()
                df_para_descargar_anual = df_agrupado_anual.copy()
                df_para_descargar_anual.columns = ['Fecha', 'Nombre Cliente', 'Numero Albaran/Serie', 'Nombre Vendedor', 'Valor Total Albaran']
                df_para_descargar_anual = df_para_descargar_anual.sort_values(by=['Fecha', 'Nombre Cliente'], ascending=[False, True])
                excel_data_anual = to_excel(df_para_descargar_anual)
                st.download_button(label=f"📥 Descargar Reporte Anual de Albaranes de {anio_sel}", data=excel_data_anual,
                                   file_name=f"Reporte_Albaranes_Pendientes_{anio_sel}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True, type="primary")

    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div class="ferreinox-footer">
        <p style="font-size: 1.1rem; margin-bottom: 1rem;"><strong>Ferreinox S.A.S. BIC</strong> | <a href="https://www.ferreinox.co" target="_blank">www.ferreinox.co</a></p>
        <p style="color: #6b7280; font-size: 0.9rem; margin: 0.5rem 0;">Sistema de Inteligencia de Negocios v3.1 | Última actualización: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        <p style="color: #9ca3af; font-size: 0.85rem; margin-top: 0.5rem;">© {datetime.datetime.now().year} Ferreinox. Todos los derechos reservados.</p>
    </div>
    """, unsafe_allow_html=True)

def main():
    if 'autenticado' not in st.session_state: st.session_state.autenticado = False
    if not st.session_state.autenticado:
        st.sidebar.image(APP_CONFIG["url_logo"], use_container_width=True)
        st.sidebar.header("Control de Acceso")
        if 'df_ventas_login' not in st.session_state:
            with st.spinner("Cargando configuración de usuarios..."):
                df_ventas_temp = cargar_y_limpiar_datos(APP_CONFIG["dropbox_paths"]["ventas"], APP_CONFIG["column_names"]["ventas"])
                st.session_state.df_ventas_login = df_ventas_temp if not df_ventas_temp.empty else pd.DataFrame(columns=['nomvendedor'])

        @st.cache_data
        def obtener_lista_usuarios(_df_ventas_cache):
            if not _df_ventas_cache.empty and 'nomvendedor' in _df_ventas_cache.columns:
                grupos_orig = list(DATA_CONFIG['grupos_vendedores'].keys())
                vendedores_en_grupos_norm = {normalizar_texto(v) for lista in DATA_CONFIG['grupos_vendedores'].values() for v in lista}
                vendedores_unicos_df = _df_ventas_cache['nomvendedor'].dropna().unique()
                mapa_norm_a_orig = {normalizar_texto(v): v for v in vendedores_unicos_df}
                vendedores_solos_norm = {normalizar_texto(v) for v in vendedores_unicos_df} - vendedores_en_grupos_norm
                vendedores_solos_orig = sorted([mapa_norm_a_orig.get(v_norm) for v_norm in vendedores_solos_norm if mapa_norm_a_orig.get(v_norm)])
                return ["GERENTE"] + sorted(grupos_orig) + vendedores_solos_orig
            return ["GERENTE"] + list(DATA_CONFIG['grupos_vendedores'].keys())

        todos_usuarios = obtener_lista_usuarios(st.session_state.df_ventas_login)
        usuarios_fijos_orig = {"GERENTE": "1234", "MOSTRADOR PEREIRA": "2345", "MOSTRADOR ARMENIA": "3456", "MOSTRADOR MANIZALES": "4567", "MOSTRADOR LAURELES": "5678", "MOSTRADOR OPALO": "opalo123"}
        usuarios = {normalizar_texto(k): v for k, v in usuarios_fijos_orig.items()}
        codigo = 1001
        for u in todos_usuarios:
            u_norm = normalizar_texto(u)
            if u_norm not in usuarios: usuarios[u_norm] = str(codigo); codigo += 1

        usuario_seleccionado = st.sidebar.selectbox("Seleccione su usuario", options=todos_usuarios, key="sb_login_user")
        clave = st.sidebar.text_input("Contraseña", type="password", key="txt_login_pass")
        if st.sidebar.button("Ingresar", key="btn_login"):
            usuario_sel_norm = normalizar_texto(usuario_seleccionado)
            if usuarios.get(usuario_sel_norm) == clave:
                st.session_state.autenticado = True
                st.session_state.usuario = usuario_seleccionado
                if 'df_ventas_login' in st.session_state: del st.session_state.df_ventas_login
                st.rerun()
            else: st.sidebar.error("Usuario o contraseña incorrectos")

        st.title("Plataforma de Inteligencia de Negocios")
        st.image(APP_CONFIG["url_logo"], width=400)
        st.header("Bienvenido")
        st.info("Por favor, utilice el panel de la izquierda para ingresar sus credenciales de acceso.")
    else:
        if 'df_ventas' not in st.session_state:
            progress_container = st.empty()
            status_container = st.empty()
            with progress_container.container():
                st.markdown("""<div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%); border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);"><h3 style="color: #1e3a8a; margin-bottom: 1rem;">🔄 Inicializando Sistema</h3><p style="color: #6b7280;">Cargando datos desde Dropbox...</p></div>""", unsafe_allow_html=True)
            progress_bar = st.progress(0)
            try:
                status_container.info("📊 Cargando datos de ventas...")
                progress_bar.progress(25)
                st.session_state.df_ventas = cargar_y_limpiar_datos(APP_CONFIG["dropbox_paths"]["ventas"], APP_CONFIG["column_names"]["ventas"])
                status_container.info("💰 Cargando datos de cobros...")
                progress_bar.progress(50)
                st.session_state.df_cobros = cargar_y_limpiar_datos(APP_CONFIG["dropbox_paths"]["cobros"], APP_CONFIG["column_names"]["cobros"])
                status_container.info("🎯 Cargando oportunidades CL4...")
                progress_bar.progress(75)
                st.session_state.df_cl4 = cargar_reporte_cl4(APP_CONFIG["dropbox_paths"]["cl4_report"])
                progress_bar.progress(100)
                status_container.success("✅ ¡Datos cargados exitosamente!")
                time.sleep(0.5)
                progress_bar.empty()
                status_container.empty()
                progress_container.empty()
                st.session_state.APP_CONFIG = APP_CONFIG
                st.session_state.DATA_CONFIG = DATA_CONFIG
            except Exception as e:
                st.error(f"❌ Error al cargar datos: {str(e)}")
                st.stop()

        st.sidebar.image(APP_CONFIG["url_logo"], use_container_width=True)
        st.sidebar.header(f"Bienvenido, {st.session_state.usuario}")
        render_dashboard()
        if st.sidebar.button("Salir", key="btn_logout"):
            st.session_state.clear()
            st.rerun()

if __name__ == '__main__':
    main()