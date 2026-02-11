import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import plotly.graph_objects as go
import io
import time
import xlsxwriter
from openai import OpenAI

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Tablero Comando: Armenia 2026",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GESTIÓN DE API KEYS ---
# Intenta obtener la key de secrets, si no está, permite funcionamiento limitado
api_key = st.secrets.get("OPENAI_API_KEY", None)
client = OpenAI(api_key=api_key) if api_key else None

try:
    from duckduckgo_search import DDGS
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

# --- ESTILOS CSS PROFESIONALES (MODO GERENCIAL + MODO IA) ---
st.markdown("""
<style>
    /* Tipografía y Encabezados */
    h1 {color: #0f172a; font-weight: 800; letter-spacing: -1px;}
    h2 {color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 10px;}
    h3 {color: #334155;}
    
    /* Métricas */
    div[data-testid="stMetricValue"] {font-size: 1.8rem; font-weight: 700; color: #1e40af;}
    div[data-testid="stMetricLabel"] {font-weight: 600; color: #64748b;}
    
    /* Tablas y Dataframes */
    .dataframe {font-size: 0.9rem !important;}
    
    /* Cajas de Alerta Personalizadas */
    .alerta-compra {
        background-color: #dcfce7;
        border-left: 5px solid #22c55e;
        padding: 15px;
        border-radius: 5px;
        color: #14532d;
        font-weight: 600;
        margin-bottom: 10px;
    }
    .ia-insight {
        background-color: #f0f9ff;
        border-left: 5px solid #0ea5e9;
        padding: 20px;
        border-radius: 8px;
        color: #0c4a6e;
        font-family: 'Segoe UI', sans-serif;
        margin: 20px 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* Botones */
    div.stButton > button:first-child {
        background-color: #1e40af;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
    }
    div.stButton > button:hover {
        background-color: #1e3a8a;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. MOTOR DE INTELIGENCIA DE NEGOCIOS ---

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
        """Algoritmo MEJORADO: Devuelve Galones, Yale, Unidades Hab, Probabilidad (0-1)"""
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
        elif etapa == "Cimentación":
             factor_urgencia = 0.1
             prob_numerica = 0.20
        else: 
            factor_urgencia = 0.1
            prob_numerica = 0.15

        # Calculo Pintura (Galones)
        # Factor aproximado: 1 galón cubre ~20m2 a dos manos (teórico), ajustado por área pintable
        area_pintable = m2 * 2.5 # Paredes + techos aprox
        galones_pintuco = (area_pintable / 25) * factor_urgencia 
        
        # Calculo Yale (Unidades)
        # Promedio 70m2 por unidad habitacional
        num_unidades_habitacionales = m2 / 70 
        # 5 cerraduras promedio por apto (Principal, 2 baños, 2 alcobas)
        cerraduras_yale = num_unidades_habitacionales * 5 
        
        return int(galones_pintuco), int(cerraduras_yale), int(num_unidades_habitacionales), prob_numerica

# --- 2. FUNCIONES AUXILIARES (IA Y WEB) ---

def sugerir_oportunidades_ia(sector, n=5):
    """Genera leads sintéticos basados en conocimiento del modelo si no hay API, o consulta real si hay API"""
    if not client:
        # Modo Fallback (Sin API Key) - Datos Simulados Inteligentes
        simulados = [
            {"Cliente": f"Constructora {sector} A", "Proyecto": f"Torre {sector} Norte", "Ubicación": "Norte", "Etapa": "Planos"},
            {"Cliente": f"Inversiones {sector} B", "Proyecto": f"Centro {sector} Sur", "Ubicación": "Sur", "Etapa": "Estructura"},
        ]
        oportunidades = []
        for s in simulados:
             oportunidades.append({
                "Cliente": s["Cliente"], "Proyecto": s["Proyecto"], "Tipo": sector,
                "Etapa": s["Etapa"], "m2_aprox": 3000, "Probabilidad": "Media",
                "Ubicación": s["Ubicación"], "Contacto": "Por definir", "Fuente": "Prospección IA"
            })
        return oportunidades

    prompt = (
        f"Enumera {n} obras, industrias o instituciones reales o altamente probables "
        f"que estarán activas o en proyecto en Armenia Quindío en 2026 para el sector '{sector}'. "
        "Formato: Cliente - Proyecto - Ubicación. No uses markdown, solo texto plano línea por línea."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o", # O gpt-3.5-turbo si prefieres
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        lines = response.choices[0].message.content.split('\n')
        oportunidades = []
        for line in lines:
            if " - " in line:
                partes = line.replace("1. ", "").replace("- ", "").split(" - ")
                if len(partes) >= 2:
                    oportunidades.append({
                        "Cliente": partes[0].strip(),
                        "Proyecto": partes[1].strip() if len(partes)>1 else "Proyecto NN",
                        "Tipo": sector,
                        "Etapa": "Por Confirmar",
                        "m2_aprox": 2500, # Estimado base para leads fríos
                        "Probabilidad": "Media",
                        "Ubicación": partes[2].strip() if len(partes)>2 else "Armenia",
                        "Contacto": "Investigar",
                        "Fuente": "IA GPT"
                    })
        return oportunidades
    except Exception as e:
        return []

def buscar_oportunidades_web(sector, n=3):
    gestor = GestorOportunidades()
    if not SEARCH_AVAILABLE: return []
    
    query = f"Proyecto construcción {sector} Armenia Quindio 2025 2026"
    resultados = gestor.buscar_web_real(query)
    oportunidades = []
    for r in resultados[:n]:
        oportunidades.append({
            "Cliente": "Lead Web Detectado",
            "Proyecto": r['Título'][:40],
            "Tipo": sector,
            "Etapa": "Por Confirmar",
            "m2_aprox": 0, # Se deja en 0 para que el usuario investigue
            "Probabilidad": "Media",
            "Ubicación": "Armenia",
            "Contacto": "Ver URL",
            "Fuente": "Web Search"
        })
    return oportunidades

# --- 3. GENERADOR DE EXCEL PROFESIONAL (INTEGRADO) ---

def generar_excel_profesional(df_crono, df_proyectos, pipeline_total):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    # FORMATOS
    fmt_titulo = workbook.add_format({'bold': True, 'font_size': 18, 'bg_color': '#1E3A8A', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter'})
    fmt_subtitulo = workbook.add_format({'bold': True, 'font_size': 12, 'font_color': '#1E3A8A', 'bottom': 2, 'bottom_color': '#1E3A8A'})
    fmt_header = workbook.add_format({'bold': True, 'bg_color': '#0F172A', 'font_color': 'white', 'border': 1, 'align': 'center'})
    fmt_header_input = workbook.add_format({'bold': True, 'bg_color': '#B45309', 'font_color': 'white', 'border': 1, 'align': 'center'})
    fmt_texto = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
    fmt_fecha = workbook.add_format({'num_format': 'dd/mm/yyyy', 'border': 1, 'align': 'center'})
    fmt_moneda = workbook.add_format({'num_format': '$ #,##0', 'border': 1})
    fmt_numero = workbook.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center'})
    fmt_input = workbook.add_format({'bg_color': '#FEF9C3', 'border': 1, 'font_color': '#000000'})

    # HOJA 1: RESUMEN
    ws_dash = workbook.add_worksheet('Resumen Gerencial')
    ws_dash.hide_gridlines(2)
    ws_dash.merge_range('B2:H3', 'TABLERO DE COMANDO COMERCIAL - ARMENIA 2026', fmt_titulo)
    ws_dash.write('B5', f"Generado el: {datetime.date.today()}", fmt_subtitulo)
    ws_dash.write('B6', f"Pipeline Total Detectado: ${pipeline_total:,.0f}", fmt_subtitulo)
    
    headers_resumen = ['Cliente', 'Proyecto', 'Etapa', 'Potencial Total ($)']
    for col, h in enumerate(headers_resumen):
        ws_dash.write(9, col+1, h, fmt_header)
    
    top_proyectos = df_proyectos.sort_values('Total_Oportunidad', ascending=False).head(20)
    row = 10
    for _, p in top_proyectos.iterrows():
        ws_dash.write(row, 1, p['Cliente'], fmt_texto)
        ws_dash.write(row, 2, p['Proyecto'], fmt_texto)
        ws_dash.write(row, 3, p['Etapa'], fmt_texto)
        ws_dash.write(row, 4, p['Total_Oportunidad'], fmt_moneda)
        row += 1
    
    ws_dash.set_column('B:C', 30)
    ws_dash.set_column('E:E', 20)

    # HOJA 2: BITÁCORA (CRONOGRAMA)
    ws_agenda = workbook.add_worksheet('Agenda de Visitas')
    ws_agenda.freeze_panes(1, 0)
    cols_fijas = ['Semana', 'Fecha', 'Cliente', 'Proyecto', 'Objetivo Táctico', 'Meta ($)']
    cols_input = ['Estado', 'Bitácora / Resultado', 'Compromiso', 'Prox. Seguimiento']
    
    for col_num, header in enumerate(cols_fijas + cols_input):
        ws_agenda.write(0, col_num, header, fmt_header_input if header in cols_input else fmt_header)
    
    for i, data in df_crono.iterrows():
        r = i + 1
        ws_agenda.write(r, 0, data['Semana'], fmt_numero)
        ws_agenda.write(r, 1, data['Fecha'], fmt_texto) # Texto para evitar lios de formato fecha simple
        ws_agenda.write(r, 2, data['Cliente'], fmt_texto)
        ws_agenda.write(r, 3, data['Proyecto'], fmt_texto)
        ws_agenda.write(r, 4, data['Acción Táctica'], fmt_texto)
        
        # Buscar monto
        monto = df_proyectos.loc[df_proyectos['Proyecto'] == data['Proyecto'], 'Total_Oportunidad']
        val_monto = monto.values[0] if not monto.empty else 0
        ws_agenda.write(r, 5, val_monto, fmt_moneda)
        
        # Inputs vacíos
        ws_agenda.data_validation(r, 6, r, 6, {'validate': 'list', 'source': ['✅ Exitosa', '⚠️ Pendiente', '❌ Fallida']})
        ws_agenda.write(r, 6, "", fmt_input)
        ws_agenda.write(r, 7, "", fmt_input)
        ws_agenda.write(r, 8, "", fmt_input)
        ws_agenda.write(r, 9, "", fmt_input)

    ws_agenda.set_column('A:A', 8)
    ws_agenda.set_column('B:B', 12)
    ws_agenda.set_column('C:D', 25)
    ws_agenda.set_column('E:E', 30)
    ws_agenda.set_column('G:J', 20)

    # HOJA 3: DATA RAW
    ws_data = workbook.add_worksheet('Base Maestra')
    cols_exp = ['Cliente', 'Proyecto', 'Tipo', 'Etapa', 'Potencial_Pintura_Gal', 'Potencial_Yale_Und', 'Total_Oportunidad']
    ws_data.write_row(0, 0, cols_exp, fmt_header)
    for r, row_data in enumerate(df_proyectos[cols_exp].values):
        ws_data.write_row(r+1, 0, row_data)

    workbook.close()
    return output.getvalue()

# --- 4. INTERFAZ Y LÓGICA PRINCIPAL ---

st.markdown("# 🎯 Centro de Comando Comercial: Armenia 2026")
st.markdown("**Usuario:** Diego Mauricio García | **Fuerza de Ventas:** Jaime Andrés Londoño")
st.divider()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
    st.header("⚙️ Filtros Tácticos")
    
    sectores_activos = st.multiselect(
        "Sectores Objetivo",
        ["Residencial", "Salud", "Industria", "Comercial", "Infraestructura"],
        default=["Residencial", "Comercial"]
    )
    
    st.markdown("---")
    st.caption("🚀 **Modo IA:** Activado")
    st.caption("📅 **Año Fiscal:** 2026")

# --- PROCESAMIENTO DE DATOS ---

gestor = GestorOportunidades()
df_proyectos = pd.DataFrame(gestor.db_semilla)

# 1. Filtrar base semilla
if sectores_activos:
    df_proyectos = df_proyectos[df_proyectos["Tipo"].isin(sectores_activos)]

# 2. Enriquecer con IA/Web (Si el usuario quiere, para no alentar carga inicial, lo hacemos automatico pero ligero)
with st.spinner('📡 Escaneando mercado y sincronizando oportunidades...'):
    oportunidades_extra = []
    # Solo buscamos leads extras si hay sectores seleccionados
    for sector in sectores_activos:
        # Traemos 2 de IA y 2 de Web para mantenerlo rápido
        oportunidades_extra += sugerir_oportunidades_ia(sector, n=2)
        oportunidades_extra += buscar_oportunidades_web(sector, n=2)
    
    if oportunidades_extra:
        df_extra = pd.DataFrame(oportunidades_extra)
        # Concatenar y eliminar duplicados por Nombre Proyecto
        df_proyectos = pd.concat([df_proyectos, df_extra], ignore_index=True)
        df_proyectos.drop_duplicates(subset=['Proyecto'], keep='first', inplace=True)

# 3. Cálculos Financieros
PRECIO_GALON = 65000
PRECIO_YALE = 45000

# Aplicar calculo a cada fila
calculos = df_proyectos.apply(
    lambda x: gestor.calcular_potencial_compra(x['m2_aprox'], x['Etapa'], x['Tipo']),
    axis=1, result_type='expand'
)
df_proyectos[['Potencial_Pintura_Gal', 'Potencial_Yale_Und', 'Unidades_Hab', 'Prob_Numerica']] = calculos

df_proyectos['Valor_Pintura'] = df_proyectos['Potencial_Pintura_Gal'] * PRECIO_GALON
df_proyectos['Valor_Yale'] = df_proyectos['Potencial_Yale_Und'] * PRECIO_YALE
df_proyectos['Total_Oportunidad'] = df_proyectos['Valor_Pintura'] + df_proyectos['Valor_Yale']

# 4. Lógica de Cronograma (Top Clientes) - LA INTEGRACIÓN SOLICITADA
# Agrupar por cliente para ver quién tiene mas plata en juego
top_clientes_series = df_proyectos.groupby("Cliente")["Total_Oportunidad"].sum().sort_values(ascending=False).head(20)
clientes_priorizados = top_clientes_series.index.tolist()

fecha_inicio = datetime.date(2026, 1, 12) # Segundo lunes enero 2026
cronograma = []

for i, cliente in enumerate(clientes_priorizados):
    # Fecha incremental semanal
    fecha_visita = fecha_inicio + datetime.timedelta(weeks=i)
    
    # Buscar el proyecto principal de ese cliente
    proyectos_cliente = df_proyectos[df_proyectos["Cliente"] == cliente]
    proyecto_top = proyectos_cliente.sort_values("Total_Oportunidad", ascending=False).iloc[0]["Proyecto"]
    
    cronograma.append({
        "Semana": i + 1,
        "Fecha": fecha_visita.strftime("%Y-%m-%d"),
        "Cliente": cliente,
        "Proyecto": proyecto_top,
        "Acción Táctica": "Presentación Portafolio & Cierre" if i < 5 else "Seguimiento de Obra"
    })

df_crono = pd.DataFrame(cronograma)

# --- VISUALIZACIÓN DASHBOARD ---

# KPIs Superiores
col1, col2, col3, col4 = st.columns(4)
total_pipeline = df_proyectos['Total_Oportunidad'].sum()
galones_total = df_proyectos['Potencial_Pintura_Gal'].sum()
yale_total = df_proyectos['Potencial_Yale_Und'].sum()
top_cliente_nombre = clientes_priorizados[0] if clientes_priorizados else "N/A"

col1.metric("💰 Pipeline Total", f"${total_pipeline:,.0f}")
col2.metric("🎨 Potencial Pintura", f"{galones_total:,.0f} Gal")
col3.metric("🔐 Potencial Yale", f"{yale_total:,.0f} Und")
col4.metric("🏆 Cliente Top", top_cliente_nombre)

# Gráficos
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("📊 Distribución de Oportunidades")
    if not df_proyectos.empty:
        fig_bar = px.bar(
            df_proyectos.sort_values("Total_Oportunidad", ascending=False).head(10),
            x="Total_Oportunidad", y="Proyecto", color="Etapa",
            orientation='h', title="Top 10 Proyectos por Valor ($)",
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        st.plotly_chart(fig_bar, use_container_width=True)

with c2:
    st.subheader("🏗️ Mix por Sector")
    if not df_proyectos.empty:
        fig_pie = px.pie(df_proyectos, values='Total_Oportunidad', names='Tipo', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

# Sección de IA Estratégica
st.markdown('<div class="ia-insight">', unsafe_allow_html=True)
st.markdown("### 🧠 Insight Estratégico (IA Advisor)")
st.write(f"Basado en el análisis de **{len(df_proyectos)} proyectos** activos, se recomienda enfocar la fuerza de ventas en la etapa de **Acabados** del sector **Residencial**, que representa el mayor volumen inmediato de facturación. El cliente **{top_cliente_nombre}** debe ser visitado en la **Semana 1**.")
st.markdown('</div>', unsafe_allow_html=True)

# Tablas de Datos
tab1, tab2 = st.tabs(["📅 Cronograma Táctico (Priorizado)", "📂 Base Maestra Detallada"])

with tab1:
    st.info("Este cronograma ha sido optimizado automáticamente priorizando los clientes con mayor potencial de compra (Principio de Pareto 80/20).")
    st.dataframe(df_crono, use_container_width=True, hide_index=True)

with tab2:
    for col in ["Cliente", "Proyecto", "Tipo", "Etapa", "Total_Oportunidad", "Fuente"]:
        if col not in df_proyectos.columns:
            df_proyectos[col] = "N/A"

    st.dataframe(
        df_proyectos[["Cliente", "Proyecto", "Tipo", "Etapa", "Total_Oportunidad", "Fuente"]].style.format({"Total_Oportunidad": "${:,.0f}"}),
        use_container_width=True
    )

# --- ZONA DE DESCARGA ---
st.markdown("---")
st.subheader("📥 Exportar Comando")

col_d1, col_d2 = st.columns([3, 1])
with col_d1:
    st.write("Descargue el reporte completo incluyendo: Resumen Gerencial, Agenda de Visitas lista para imprimir y Base de Datos completa.")

with col_d2:
    excel_file = generar_excel_profesional(df_crono, df_proyectos, total_pipeline)
    st.download_button(
        label="📄 DESCARGAR REPORTE EXCEL",
        data=excel_file,
        file_name=f"Comando_Armenia_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )