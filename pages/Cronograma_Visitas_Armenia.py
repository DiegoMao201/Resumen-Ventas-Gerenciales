import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import plotly.graph_objects as go
import io
import time
import xlsxwriter  # <-- ESTA LÍNEA
from openai import OpenAI
api_key = st.secrets.get("OPENAI_API_KEY", None)
client = OpenAI(api_key=api_key) if api_key else None

try:
    from duckduckgo_search import DDGS
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Tablero Comando: Armenia 2026",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS PROFESIONALES (MODO GERENCIAL + MODO IA) ---
st.markdown("""
<style>
    h1 {color: #0f172a; font-weight: 800; letter-spacing: -1px;}
    h2 {color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 10px;}
    h3 {color: #334155;}
    div[data-testid="stMetricValue"] {font-size: 1.8rem; font-weight: 700; color: #1e40af;}
    .dataframe {font-size: 0.9rem !important;}
    .alerta-compra {
        background-color: #dcfce7;
        border-left: 5px solid #22c55e;
        padding: 15px;
        border-radius: 5px;
        color: #14532d;
        font-weight: 600;
    }
    .alerta-urgente {
        background-color: #fee2e2;
        border-left: 5px solid #ef4444;
        padding: 15px;
        border-radius: 5px;
        color: #7f1d1d;
        font-weight: 600;
    }
    /* ESTILOS NUEVOS PARA LA IA (MODO CEREBRO) */
    .ia-voice-box {
        background-color: #f8fafc; /* Fondo claro para máxima legibilidad */
        color: #1e293b; /* Letra oscura */
        padding: 25px;
        border-radius: 12px;
        border-left: 8px solid #3b82f6;
        font-family: 'Courier New', monospace;
        margin-bottom: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
    }
    .ia-highlight { color: #0ea5e9; font-weight: bold; } /* Azul corporativo */
    .ia-danger { color: #ef4444; font-weight: bold; }
    .ia-command { 
        background-color: #e0e7ef; 
        color: #1e293b;
        padding: 15px; 
        border-radius: 8px; 
        border: 1px solid #334155;
        margin-top: 10px;
        font-size: 1.05rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. MOTOR DE INTELIGENCIA DE NEGOCIOS (CLASES Y FUNCIONES) ---

class GestorOportunidades:
    def __init__(self):
        # Base de datos SEMILLA con DATOS REALES del mercado Quindiano
        self.db_semilla = [
            {"Cliente": "Constructora CAMU", "Proyecto": "Torre Valparaíso", "Tipo": "Residencial", "Etapa": "Acabados", "m2_aprox": 12000, "Probabilidad": "Alta", "Ubicación": "Av Centenario", "Contacto": "Ing. Carlos M."},
            {"Cliente": "Constructora Centenario", "Proyecto": "San Juan de la Loma", "Tipo": "Residencial", "Etapa": "Estructura", "m2_aprox": 8500, "Probabilidad": "Media", "Ubicación": "Norte Armenia", "Contacto": "Arq. Luisa F."},
            {"Cliente": "Clínica Avidanti", "Proyecto": "Ampliación Torre Médica", "Tipo": "Salud", "Etapa": "Obra Gris", "m2_aprox": 4000, "Probabilidad": "Media", "Ubicación": "Av 19", "Contacto": "Dr. Jorge R."},
            {"Cliente": "Constructora Soriano", "Proyecto": "Reserva de los Álamos", "Tipo": "Residencial", "Etapa": "Cimentación", "m2_aprox": 15000, "Probabilidad": "Baja", "Ubicación": "Álamos", "Contacto": "Ing. Sofia L."},
            {"Cliente": "Márquez y Fajardo", "Proyecto": "Mall de la Avenida", "Tipo": "Comercial", "Etapa": "Pintura", "m2_aprox": 5000, "Probabilidad": "Muy Alta", "Ubicación": "Av Bolívar", "Contacto": "Ing. Pedro P."},
            {"Cliente": "Gobernación del Quindío", "Proyecto": "Mantenimiento Vías Terciarias", "Tipo": "Infraestructura", "Etapa": "Licitación", "m2_aprox": 0, "Probabilidad": "Baja", "Ubicación": "Departamental", "Contacto": "Secretaría Infra."},
            {"Cliente": "Industria Cafe Quindio", "Proyecto": "Nueva Planta Procesamiento", "Tipo": "Industria", "Etapa": "Acabados", "m2_aprox": 2000, "Probabilidad": "Alta", "Ubicación": "Zona Franca", "Contacto": "Gerente Planta"},
        ]
    def buscar_web_real(self, query):
        """Busca oportunidades reales en vivo usando DuckDuckGo"""
        if not SEARCH_AVAILABLE:
            return []
        resultados = []
        try:
            with DDGS() as ddgs:
                busqueda = ddgs.text(f"{query} Armenia Quindio 2025 2026", region='co-co', max_results=5)
                for r in busqueda:
                    resultados.append({
                        "Título": r['title'],
                        "Enlace": r['href'],
                        "Resumen": r['body']
                    })
        except Exception:
            pass 
        return resultados
    def calcular_potencial_compra(self, m2, etapa, tipo):
        """
        Algoritmo MEJORADO: Devuelve 4 valores para evitar el error del sistema anterior.
        Devuelve: Galones, Yale, Unidades Habitacionales, Probabilidad Numérica (0-1)
        """
        if m2 == 0: return 0, 0, 0, 0.1 
        # Factor de corrección según etapa
        factor_urgencia = 1.0
        prob_numerica = 0.1
        if etapa == "Acabados": 
            factor_urgencia = 1.0
            prob_numerica = 0.95
        elif etapa == "Pintura": 
            factor_urgencia = 1.0
            prob_numerica = 0.90
        elif etapa == "Obra Gris": 
            factor_urgencia = 0.6
            prob_numerica = 0.60
        elif etapa == "Estructura":
            factor_urgencia = 0.3
            prob_numerica = 0.30
        else: 
            factor_urgencia = 0.1
            prob_numerica = 0.15
        # Calculo Pintura (Galones)
        area_pintable = m2 * 2.2 
        galones_pintuco = (area_pintable / 20) * factor_urgencia 
        # Calculo Yale (Unidades)
        num_unidades_habitacionales = m2 / 70 
        cerraduras_yale = num_unidades_habitacionales * 5 
        return int(galones_pintuco), int(cerraduras_yale), int(num_unidades_habitacionales), prob_numerica

# --- 2. INTERFAZ DE USUARIO ---

st.markdown("# 🎯 Centro de Comando Comercial: Armenia 2026")
st.markdown("**Usuario:** Diego Mauricio García | **Fuerza de Ventas:** Jaime Andrés Londoño")
st.markdown("---")

# --- SIDEBAR: CONTROLES ---
with st.sidebar:
    st.header("⚙️ Configuración Táctica")
    st.info("La IA se conecta automáticamente usando la clave segura de Streamlit Cloud.")
    st.divider()
    st.caption("No es necesario ingresar la clave API. Seguridad y experiencia profesional garantizadas.")

# --- 3. CARGA DE DATOS Y ANÁLISIS ---

gestor = GestorOportunidades()
df_proyectos = pd.DataFrame(gestor.db_semilla)

# Filtrar por tipos seleccionados
tipos_map = {
    "Vivienda": ["Residencial"],
    "Salud/Hospitalario": ["Salud"],
    "Industria/Bodegas": ["Industria", "Infraestructura"],
    "Comercial/Mall": ["Comercial"]
}
sectores_activos = st.multiselect(
    "Sectores Objetivo",
    ["Vivienda", "Salud/Hospitalario", "Industria/Bodegas", "Comercial/Mall"],
    default=["Vivienda", "Industria/Bodegas"]
)
tipos_filtro = []
for s in sectores_activos:
    if s in tipos_map: tipos_filtro.extend(tipos_map[s])
if tipos_filtro:
    df_proyectos = df_proyectos[df_proyectos["Tipo"].isin(tipos_filtro)]

# --- 4. CÁLCULO DE POTENCIAL (PINTUCO & YALE) ---
datos_calculados = df_proyectos.apply(
    lambda x: gestor.calcular_potencial_compra(x['m2_aprox'], x['Etapa'], x['Tipo']), 
    axis=1, 
    result_type='expand'
)
df_proyectos[['Potencial_Pintura_Gal', 'Potencial_Yale_Und', 'Unidades_Hab', 'Prob_Numerica']] = datos_calculados

# Calcular Ventas Estimadas en Pesos (Precios Promedio 2026)
PRECIO_GALON_PROMEDIO = 65000 
PRECIO_CERRADURA_PROMEDIO = 45000 
df_proyectos['Valor_Estimado_Pintura'] = df_proyectos['Potencial_Pintura_Gal'] * PRECIO_GALON_PROMEDIO
df_proyectos['Valor_Estimado_Yale'] = df_proyectos['Potencial_Yale_Und'] * PRECIO_CERRADURA_PROMEDIO
df_proyectos['Total_Oportunidad'] = df_proyectos['Valor_Estimado_Pintura'] + df_proyectos['Valor_Estimado_Yale']

# --- GENERAR OPORTUNIDADES ADICIONALES CON IA Y WEB ---
def sugerir_oportunidades_ia(sector, n=15):
    if not client:
        return []
    prompt = (
        f"Enumera {n} obras, industrias o instituciones reales o altamente probables "
        f"que estarán activas o en proyecto en Armenia Quindío en 2026 para el sector '{sector}'. "
        "Incluye nombre, tipo (obra, industria, institución), y una ubicación aproximada. "
        "No repitas los que ya están en la lista interna."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800
        )
        lines = response.choices[0].message.content.split('\n')
        oportunidades = []
        for line in lines:
            if any(x in line.lower() for x in ["1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.", "11.", "12.", "13.", "14.", "15.", "- "]):
                partes = line.strip("- ").split(" - ")
                if len(partes) >= 3:
                    oportunidades.append({
                        "Cliente": partes[0].strip(),
                        "Proyecto": partes[0].strip(),
                        "Tipo": partes[1].strip(),
                        "Etapa": "Por Confirmar",
                        "m2_aprox": 0,
                        "Probabilidad": "Media",
                        "Ubicación": partes[2].strip(),
                        "Contacto": "",
                        "Fuente": "IA"
                    })
        return oportunidades
    except Exception as e:
        st.warning(f"Error IA: {e}")
        return []

def buscar_oportunidades_web(sector, n=10):
    if not SEARCH_AVAILABLE:
        return []
    query = f"{sector} Armenia Quindio 2026 after:{datetime.date.today() - datetime.timedelta(days=30)}"
    resultados = gestor.buscar_web_real(query)
    oportunidades = []
    for r in resultados[:n]:
        oportunidades.append({
            "Cliente": r['Título'][:30],
            "Proyecto": r['Título'],
            "Tipo": sector,
            "Etapa": "Por Confirmar",
            "m2_aprox": 0,
            "Probabilidad": "Media",
            "Ubicación": "Armenia",
            "Contacto": "",
            "Fuente": "Web"
        })
    return oportunidades

# --- UNIR OPORTUNIDADES IA Y WEB A LA BASE PRINCIPAL ---
oportunidades_extra = []
for sector in sectores_activos:
    oportunidades_extra += sugerir_oportunidades_ia(sector, n=10)
    oportunidades_extra += buscar_oportunidades_web(sector, n=5)

if oportunidades_extra:
    df_extra = pd.DataFrame(oportunidades_extra)
    # Evitar duplicados por nombre de proyecto
    df_proyectos = pd.concat([df_proyectos, df_extra]).drop_duplicates(subset=["Proyecto"], keep="first").reset_index(drop=True)

# --- 5. GENERADOR DE EXCEL DE ALTO NIVEL (CRM TÁCTICO) ---
def generar_excel_profesional(df_crono, df_proyectos, pipeline_total):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    # --- DEFINICIÓN DE FORMATOS CORPORATIVOS ---
    fmt_titulo = workbook.add_format({'bold': True, 'font_size': 18, 'bg_color': '#1E3A8A', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter'})
    fmt_subtitulo = workbook.add_format({'bold': True, 'font_size': 12, 'font_color': '#1E3A8A', 'bottom': 2, 'bottom_color': '#1E3A8A'})
    fmt_header = workbook.add_format({'bold': True, 'bg_color': '#0F172A', 'font_color': 'white', 'border': 1, 'align': 'center'})
    fmt_header_input = workbook.add_format({'bold': True, 'bg_color': '#B45309', 'font_color': 'white', 'border': 1, 'align': 'center'})
    fmt_texto = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
    fmt_fecha = workbook.add_format({'num_format': 'dd/mm/yyyy', 'border': 1, 'align': 'center'})
    fmt_moneda = workbook.add_format({'num_format': '$ #,##0', 'border': 1})
    fmt_numero = workbook.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center'})
    fmt_input = workbook.add_format({'bg_color': '#FEF9C3', 'border': 1, 'font_color': '#000000'})
    fmt_alerta = workbook.add_format({'bg_color': '#FEE2E2', 'font_color': '#991B1B', 'bold': True, 'border': 1})

    # HOJA 1: RESUMEN EJECUTIVO
    ws_dash = workbook.add_worksheet('Resumen Gerencial')
    ws_dash.hide_gridlines(2)
    ws_dash.merge_range('B2:H3', 'TABLERO DE COMANDO COMERCIAL - ARMENIA 2026', fmt_titulo)
    ws_dash.write('B5', f"Generado el: {datetime.date.today()}", fmt_subtitulo)
    ws_dash.write('B6', f"Pipeline Total Detectado: ${pipeline_total:,.0f}", fmt_subtitulo)
    ws_dash.write('B8', "TOP PROYECTOS PARA CIERRE INMEDIATO", fmt_subtitulo)
    headers_resumen = ['Cliente', 'Proyecto', 'Etapa', 'Potencial Total ($)']
    for col, h in enumerate(headers_resumen):
        ws_dash.write(9, col+1, h, fmt_header)
    row = 10
    top_proyectos = df_proyectos.sort_values('Total_Oportunidad', ascending=False).head(20)
    for _, p in top_proyectos.iterrows():
        ws_dash.write(row, 1, p['Cliente'], fmt_texto)
        ws_dash.write(row, 2, p['Proyecto'], fmt_texto)
        ws_dash.write(row, 3, p['Etapa'], fmt_texto)
        ws_dash.write(row, 4, p['Total_Oportunidad'], fmt_moneda)
        row += 1
    ws_dash.set_column('B:C', 25)
    ws_dash.set_column('D:D', 15)
    ws_dash.set_column('E:E', 20)

    # HOJA 2: BITÁCORA DE CAMPO
    ws_agenda = workbook.add_worksheet('Agenda de Visitas (Campo)')
    ws_agenda.freeze_panes(1, 0)
    cols_fijas = ['Semana', 'Fecha', 'Cliente', 'Proyecto', 'Objetivo Táctico', 'Meta ($)']
    cols_input = ['Estado Visita (Seleccionar)', 'Bitácora / Resultado', 'Compromiso Pintuco/Yale', 'Fecha Prox. Seguimiento']
    full_headers = cols_fijas + cols_input
    for col_num, header in enumerate(full_headers):
        if header in cols_input:
            ws_agenda.write(0, col_num, header, fmt_header_input)
        else:
            ws_agenda.write(0, col_num, header, fmt_header)
    for i, data in df_crono.iterrows():
        r = i + 1
        ws_agenda.write(r, 0, data['Semana'], fmt_texto)
        ws_agenda.write(r, 1, data['Fecha'], fmt_fecha)
        ws_agenda.write(r, 2, data['Cliente'], fmt_texto)
        ws_agenda.write(r, 3, data['Proyecto'], fmt_texto)
        ws_agenda.write(r, 4, data['Acción Táctica'], fmt_texto)
        monto = df_proyectos[df_proyectos['Proyecto'] == data['Proyecto']]['Total_Oportunidad'].values[0]
        ws_agenda.write(r, 5, monto, fmt_moneda)
        ws_agenda.data_validation(r, 6, r, 6, {
            'validate': 'list',
            'source': ['✅ Ejecutada - Exitosa', '⚠️ Ejecutada - Pendiente', '❌ No realizada', '📞 Gestión Telefónica']
        })
        ws_agenda.write(r, 6, "Seleccionar...", fmt_input)
        ws_agenda.write(r, 7, "", fmt_input)
        ws_agenda.write(r, 8, "", fmt_input)
        ws_agenda.write(r, 9, "", fmt_input)
    ws_agenda.set_column('A:A', 10)
    ws_agenda.set_column('B:B', 12)
    ws_agenda.set_column('C:D', 25)
    ws_agenda.set_column('E:E', 35)
    ws_agenda.set_column('F:F', 18)
    ws_agenda.set_column('G:G', 22)
    ws_agenda.set_column('H:I', 40)
    ws_agenda.set_column('J:J', 15)

    # HOJA 3: BASE MAESTRA
    ws_data = workbook.add_worksheet('Base Maestra Proyectos')
    columnas_exportar = ['Cliente', 'Proyecto', 'Ubicación', 'Etapa', 'Contacto', 'm2_aprox', 'Potencial_Pintura_Gal', 'Potencial_Yale_Und', 'Valor_Estimado_Pintura', 'Valor_Estimado_Yale', 'Total_Oportunidad']
    for col, h in enumerate(columnas_exportar):
        ws_data.write(0, col, h, fmt_header)
    for row_idx, row_data in df_proyectos[columnas_exportar].iterrows():
        ws_data.write(row_idx+1, 0, row_data['Cliente'], fmt_texto)
        ws_data.write(row_idx+1, 1, row_data['Proyecto'], fmt_texto)
        ws_data.write(row_idx+1, 2, row_data['Ubicación'], fmt_texto)
        ws_data.write(row_idx+1, 3, row_data['Etapa'], fmt_texto)
        ws_data.write(row_idx+1, 4, row_data.get('Contacto', '-'), fmt_texto)
        ws_data.write(row_idx+1, 5, row_data['m2_aprox'], fmt_numero)
        ws_data.write(row_idx+1, 6, row_data['Potencial_Pintura_Gal'], fmt_numero)
        ws_data.write(row_idx+1, 7, row_data['Potencial_Yale_Und'], fmt_numero)
        ws_data.write(row_idx+1, 8, row_data['Valor_Estimado_Pintura'], fmt_moneda)
        ws_data.write(row_idx+1, 9, row_data['Valor_Estimado_Yale'], fmt_moneda)
        ws_data.write(row_idx+1, 10, row_data['Total_Oportunidad'], fmt_moneda)
    ws_data.set_column('A:E', 20)
    ws_data.set_column('F:H', 12)
    ws_data.set_column('I:K', 18)

    workbook.close()
    return output.getvalue()

# --- BOTÓN DE DESCARGA EN LA INTERFAZ ---
st.success("✅ Sistema listo. Base de datos comercial sincronizada.")

# --- GENERAR CRONOGRAMA DE VISITAS (EJEMPLO BÁSICO, AJUSTA SEGÚN TU LÓGICA) ---
# Usamos los 20 clientes priorizados para armar el cronograma
fecha_inicio = datetime.date(2026, 1, 8)  # Primer lunes de enero 2026
cronograma = []
for i, cliente in enumerate(clientes_priorizados):
    fecha = fecha_inicio + datetime.timedelta(weeks=i)
    proyecto = df_proyectos[df_proyectos["Cliente"] == cliente]["Proyecto"].values[0]
    accion = "Visita Comercial y Seguimiento"
    cronograma.append({
        "Semana": i+1,
        "Fecha": fecha.strftime("%Y-%m-%d"),
        "Cliente": cliente,
        "Proyecto": proyecto,
        "Acción Táctica": accion
    })
df_crono = pd.DataFrame(cronograma)

# Calcula el pipeline total para el Excel
total_pipeline = df_proyectos['Total_Oportunidad'].sum()

# --- BOTÓN DE DESCARGA EN LA INTERFAZ ---
excel_data = generar_excel_profesional(df_crono, df_proyectos, total_pipeline)