import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import io
import xlsxwriter

# Intenta importar librerías opcionales sin romper el código si faltan
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from duckduckgo_search import DDGS
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Tablero Comando: Armenia 2026",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GESTIÓN DE API KEYS ---
api_key = st.secrets.get("OPENAI_API_KEY", None)
client = OpenAI(api_key=api_key) if (api_key and OPENAI_AVAILABLE) else None

# --- ESTILOS CSS AVANZADOS ---
st.markdown("""
<style>
    /* Colores Corporativos y Estilo Gerencial */
    :root {
        --primary: #0F172A;
        --secondary: #1E40AF;
        --accent: #F59E0B;
        --success: #10B981;
        --bg-light: #F8FAFC;
    }
    
    h1, h2, h3 {font-family: 'Segoe UI', sans-serif; color: var(--primary);}
    
    /* Métricas */
    div[data-testid="stMetricValue"] {
        font-size: 2rem; font-weight: 800; color: var(--secondary);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #E2E8F0; border-radius: 5px; color: #475569;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: var(--secondary); color: white;
    }

    /* Cards de Insight */
    .insight-card {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border-left: 5px solid #2563eb;
        padding: 15px; border-radius: 8px; margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .oportunidad-tag {
        font-size: 0.8em; padding: 2px 8px; border-radius: 12px; font-weight: bold;
    }
    .tag-obra { background-color: #dcfce7; color: #166534; }
    .tag-ind { background-color: #ffedd5; color: #9a3412; }
</style>
""", unsafe_allow_html=True)

# --- 1. CEREBRO DE INTELIGENCIA COMERCIAL (CLASE PRINCIPAL) ---

class GestorInteligente:
    def __init__(self):
        # BASE DE DATOS MAESTRA - MEZCLA OBRAS Y EMPRESAS REALES DEL QUINDÍO
        self.db_semilla = [
            # --- GRANDES INDUSTRIAS (MANTENIMIENTO & CONSUMIBLES) ---
            {
                "Cliente": "Don Pollo S.A.", "Proyecto": "Planta de Procesamiento La Tebaida", 
                "Tipo": "Industria Alimentos", "Estado": "Operativo", "Tamano": "Gigante",
                "Necesidad": "Mantenimiento", "Ubicación": "La Tebaida", "Foco_Venta": "Epóxicos, Demarcación, Lijas"
            },
            {
                "Cliente": "Muebles BL (Bienes Laminados)", "Proyecto": "Fábrica Principal", 
                "Tipo": "Industria Madera", "Estado": "Operativo", "Tamano": "Grande",
                "Necesidad": "Producción", "Ubicación": "Vía al Caimo", "Foco_Venta": "Lijas Industriales, Abracol, Lacas"
            },
            {
                "Cliente": "Café Quindío", "Proyecto": "Planta Torrefactora", 
                "Tipo": "Industria Alimentos", "Estado": "Operativo", "Tamano": "Mediana",
                "Necesidad": "Mantenimiento", "Ubicación": "Zona Franca", "Foco_Venta": "Pintura Aseptica, Demarcación"
            },
            {
                "Cliente": "Busscar de Colombia", "Proyecto": "Planta Ensamblaje (Pereira/Cercanías)", 
                "Tipo": "Industria Automotriz", "Estado": "Operativo", "Tamano": "Gigante",
                "Necesidad": "Producción", "Ubicación": "Cerritos", "Foco_Venta": "Lijas, Masillas, Pintura Industrial"
            },
            {
                "Cliente": "Supermercados Inter/La 14", "Proyecto": "Centros de Distribución", 
                "Tipo": "Comercial Gran Superficie", "Estado": "Operativo", "Tamano": "Grande",
                "Necesidad": "Mantenimiento", "Ubicación": "Armenia", "Foco_Venta": "Pintura Tráfico, Mantenimiento Locativo"
            },
            {
                "Cliente": "Hospital San Juan de Dios", "Proyecto": "Mantenimiento General 2026", 
                "Tipo": "Salud / Institucional", "Estado": "Operativo", "Tamano": "Grande",
                "Necesidad": "Mantenimiento", "Ubicación": "Norte Armenia", "Foco_Venta": "Pintura Antibacterial, Fachadas"
            },

            # --- OBRAS DE CONSTRUCCIÓN (VENTA PROYECTO) ---
            {
                "Cliente": "Constructora CAMU", "Proyecto": "Torre Valparaíso", 
                "Tipo": "Construcción Residencial", "Estado": "Acabados", "Tamano": "12000 m2",
                "Necesidad": "Proyecto Nuevo", "Ubicación": "Av Centenario", "Foco_Venta": "Vinilos, Fachada, Cerraduras Yale"
            },
            {
                "Cliente": "Constructora Centenario", "Proyecto": "San Juan de la Loma", 
                "Tipo": "Construcción Residencial", "Estado": "Estructura", "Tamano": "8500 m2",
                "Necesidad": "Proyecto Nuevo", "Ubicación": "Norte", "Foco_Venta": "Especificación Técnica"
            },
            {
                "Cliente": "Márquez y Fajardo", "Proyecto": "Mall de la Avenida", 
                "Tipo": "Construcción Comercial", "Estado": "Pintura", "Tamano": "5000 m2",
                "Necesidad": "Proyecto Nuevo", "Ubicación": "Av Bolívar", "Foco_Venta": "Cierre de Negocio Pintura"
            },
            {
                "Cliente": "Gobernación del Quindío", "Proyecto": "Señalización Vías Secundarias", 
                "Tipo": "Infraestructura", "Estado": "Licitación", "Tamano": "Varios KM",
                "Necesidad": "Licitación", "Ubicación": "Departamental", "Foco_Venta": "Pintura Tráfico Pesado"
            }
        ]

    def calcular_potencial_real(self, row):
        """
        Algoritmo híbrido: Diferencia entre una Obra (Venta única grande) 
        y una Industria (Venta recurrente mensual x 12 meses).
        """
        tipo = row['Tipo']
        tamano = row['Tamano']
        
        # PRECIOS BASE 2026
        precio_galon_vinilo = 70000
        precio_galon_trafico = 120000
        precio_unidad_lija = 3500
        precio_yale_promedio = 50000
        
        potencial_total = 0
        detalle_calculo = ""
        prioridad = "Baja"

        # LÓGICA 1: INDUSTRIA & MANTENIMIENTO (Venta Recurrente Anualizada)
        if "Industria" in tipo or "Salud" in tipo or "Comercial Gran" in tipo:
            # Factores de consumo mensual estimado según tamaño
            if "Gigante" in tamano: # Ej: Don Pollo, Busscar
                consumo_lijas = 2000 # Unidades mes
                consumo_pintura_mto = 30 # Galones mes (Epoxicos, trafico)
            elif "Grande" in tamano: # Ej: Muebles BL
                consumo_lijas = 1000
                consumo_pintura_mto = 15
            else: # Medianas
                consumo_lijas = 200
                consumo_pintura_mto = 5
            
            # Ajuste específico: Maderas consumen MUCHA más lija
            if "Madera" in tipo:
                consumo_lijas *= 3 
                consumo_pintura_mto *= 0.5 # Menos pared, más laca (asumimos galonaje similar en laca)

            venta_mensual = (consumo_lijas * precio_unidad_lija) + (consumo_pintura_mto * precio_galon_trafico)
            potencial_total = venta_mensual * 12 # Proyección anual
            detalle_calculo = f"Recurrente: {consumo_lijas} lijas/mes + {consumo_pintura_mto} gal/mes"
            prioridad = "Alta" if potencial_total > 50000000 else "Media"

        # LÓGICA 2: CONSTRUCCIÓN (Venta por Proyecto)
        else:
            try:
                m2 = int(str(tamano).replace(" m2", "").replace("Varios KM", "1000"))
            except:
                m2 = 1000
            
            # Etapa afecta probabilidad, no monto total potencial (el monto es el tamaño del pastel)
            # Galones aprox: m2 / 20 rendimiento * manos
            galones_totales = (m2 / 25) 
            yales_totales = (m2 / 70) * 4 # 4 chapas por cada 70m2
            
            potencial_total = (galones_totales * precio_galon_vinilo) + (yales_totales * precio_yale_promedio)
            detalle_calculo = f"Proyecto: {int(galones_totales)} gal + {int(yales_totales)} Yales"
            
            estado = row['Estado']
            if estado in ["Acabados", "Pintura"]:
                prioridad = "Critica (Cierre Ya)"
            elif estado in ["Estructura"]:
                prioridad = "Media (Especificar)"
            else:
                prioridad = "Baja (Prospectar)"

        return int(potencial_total), detalle_calculo, prioridad

    def buscar_leads_ia(self, sector):
        """Simula una búsqueda inteligente si no hay API, o usa OpenAI si existe"""
        nuevos_leads = []
        if not client:
            # Fallback Inteligente (Datos sintéticos realistas)
            if "Madera" in sector:
                nuevos_leads.append({"Cliente": "Maderas de Occidente", "Proyecto": "Taller Industrial", "Tipo": "Industria Madera", "Estado": "Operativo", "Tamano": "Mediana", "Necesidad": "Insumos", "Ubicación": "La Tebaida", "Foco_Venta": "Lijas, Selladores"})
            if "Alimentos" in sector:
                nuevos_leads.append({"Cliente": "Frigocafé", "Proyecto": "Planta Beneficio", "Tipo": "Industria Alimentos", "Estado": "Operativo", "Tamano": "Grande", "Necesidad": "Mantenimiento", "Ubicación": "Montenegro", "Foco_Venta": "Epóxicos"})
        else:
            # Aquí iría la llamada real a GPT-4 si se conecta la API
            pass
        return nuevos_leads

# --- 2. GENERADOR DE EXCEL (POWER REPORT) ---

def generar_reporte_excel(df, cronograma):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # Formatos
    f_header = workbook.add_format({'bold': True, 'bg_color': '#1E40AF', 'font_color': 'white', 'border': 1})
    f_money = workbook.add_format({'num_format': '$ #,##0', 'border': 1})
    f_text = workbook.add_format({'border': 1})
    f_h1 = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#1E40AF'})

    # HOJA 1: ESTRATEGIA
    ws1 = workbook.add_worksheet("Estrategia Comercial")
    ws1.write("B2", "PLAN COMERCIAL ARMENIA 2026 - MANTENIMIENTO Y PROYECTOS", f_h1)
    
    headers = ["Cliente", "Proyecto/Sede", "Tipo", "Ubicación", "Foco de Venta", "Potencial Anual ($)", "Prioridad"]
    ws1.write_row("B5", headers, f_header)
    
    row = 5
    for _, item in df.iterrows():
        ws1.write(row, 1, item['Cliente'], f_text)
        ws1.write(row, 2, item['Proyecto'], f_text)
        ws1.write(row, 3, item['Tipo'], f_text)
        ws1.write(row, 4, item['Ubicación'], f_text)
        ws1.write(row, 5, item['Foco_Venta'], f_text)
        ws1.write(row, 6, item['Potencial_Estimado'], f_money)
        ws1.write(row, 7, item['Prioridad_Venta'], f_text)
        row += 1
        
    ws1.set_column('B:B', 25)
    ws1.set_column('C:C', 30)
    ws1.set_column('F:F', 30)
    ws1.set_column('G:G', 18)

    # HOJA 2: CRONOGRAMA
    ws2 = workbook.add_worksheet("Agenda de Visitas")
    headers_crono = ["Semana", "Fecha", "Cliente Objetivo", "Acción (Venta/Mto)", "Portafolio a Llevar"]
    ws2.write_row("A1", headers_crono, f_header)
    
    r = 1
    for item in cronograma:
        ws2.write(r, 0, item['Semana'], f_text)
        ws2.write(r, 1, item['Fecha'], f_text)
        ws2.write(r, 2, item['Cliente'], f_text)
        ws2.write(r, 3, item['Accion'], f_text)
        ws2.write(r, 4, item['Kit'], f_text)
        r += 1
    
    ws2.set_column('C:C', 30)
    ws2.set_column('E:E', 40)

    workbook.close()
    return output.getvalue()

# --- 3. INTERFAZ Y LÓGICA DE NEGOCIO ---

gestor = GestorInteligente()

# Sidebar
with st.sidebar:
    st.title("🎛️ Filtros Tácticos")
    tipo_negocio = st.multiselect(
        "Lineas de Negocio",
        ["Industria (Mantenimiento)", "Construcción (Obra Nueva)", "Infraestructura"],
        default=["Industria (Mantenimiento)", "Construcción (Obra Nueva)"]
    )
    
    st.info("💡 **Tip:** 'Industria' buscará clientes recurrentes para Lijas y Epóxicos (Ej: Don Pollo). 'Construcción' buscará obras para Vinilos y Yale.")

# Procesamiento de Datos
df = pd.DataFrame(gestor.db_semilla)

# Filtrado básico
filtro_tipos = []
if "Industria (Mantenimiento)" in tipo_negocio:
    filtro_tipos.extend(["Industria Alimentos", "Industria Madera", "Industria Automotriz", "Salud / Institucional", "Comercial Gran Superficie"])
if "Construcción (Obra Nueva)" in tipo_negocio:
    filtro_tipos.extend(["Construcción Residencial", "Construcción Comercial"])
if "Infraestructura" in tipo_negocio:
    filtro_tipos.append("Infraestructura")

df = df[df["Tipo"].isin(filtro_tipos)]

# Cálculos Avanzados
resultados = df.apply(gestor.calcular_potencial_real, axis=1, result_type='expand')
df[['Potencial_Estimado', 'Detalle_Calculo', 'Prioridad_Venta']] = resultados

# Ordenar por Dinero
df = df.sort_values(by="Potencial_Estimado", ascending=False)

# Generar Cronograma Inteligente (Top 10 Clientes mezclados)
cronograma = []
fecha_base = datetime.date(2026, 2, 1) # Inicio Febrero 2026
top_clientes = df.head(12) # Top 12 para 3 meses aprox

for i, (_, row) in enumerate(top_clientes.iterrows()):
    fecha_visita = fecha_base + datetime.timedelta(days=i*3) # Visitas cada 3 dias aprox
    if row['Tipo'] in ["Industria Madera", "Industria Automotriz"]:
        accion = "Revisión Stock Lijas/Abrasivos"
        kit = "Muestrario Abracol + Ficha Epóxicos"
    elif "Alimentos" in row['Tipo']:
        accion = "Auditoría Pisos & Demarcación"
        kit = "Catálogo Epóxicos + Pintura Tráfico"
    else:
        accion = "Comité de Obra / Cierre"
        kit = "Carta de Colores + Muestras Yale"
        
    cronograma.append({
        "Semana": f"Semana {int(i/5)+1}",
        "Fecha": fecha_visita.strftime("%d-%b"),
        "Cliente": row['Cliente'],
        "Accion": accion,
        "Kit": kit
    })

# --- DASHBOARD PRINCIPAL ---

st.title("🎯 Centro de Comando Comercial: Armenia 2026")
st.markdown("**Gerente:** Diego Mauricio García | **Líder Ventas:** Jaime Andrés Londoño")
st.markdown("---")

# KPIs
col1, col2, col3, col4 = st.columns(4)
total_potencial = df['Potencial_Estimado'].sum()
mejor_cliente = df.iloc[0]['Cliente'] if not df.empty else "N/A"
industrias_activas = df[df['Tipo'].str.contains('Industria')].shape[0]
obras_activas = df[df['Tipo'].str.contains('Construcción')].shape[0]

col1.metric("💰 Potencial Total Detectado", f"${total_potencial:,.0f}")
col2.metric("🏆 Cliente #1 (Pareto)", mejor_cliente)
col3.metric("🏭 Industrias (Mantenimiento)", f"{industrias_activas} Activas")
col4.metric("🏗️ Obras (Proyectos)", f"{obras_activas} En curso")

# Gráficas
c1, c2 = st.columns([2,1])
with c1:
    st.subheader("📊 Potencial de Ventas por Cliente")
    if not df.empty:
        fig = px.bar(
            df.head(10), 
            x="Potencial_Estimado", y="Cliente", color="Tipo",
            orientation='h', text_auto='.2s',
            title="Top 10 Clientes (Industria vs Construcción)",
            color_discrete_map={
                "Industria Alimentos": "#EF4444", "Industria Madera": "#D97706",
                "Construcción Residencial": "#3B82F6", "Salud / Institucional": "#10B981"
            }
        )
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("💼 Mix de Portafolio")
    # Crear datos para el pie chart basados en los focos de venta
    if not df.empty:
        df['Categoria_Producto'] = df['Foco_Venta'].apply(lambda x: x.split(',')[0])
        fig_pie = px.pie(df, names='Categoria_Producto', values='Potencial_Estimado', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

# Tabs Detallados
tab_cronograma, tab_industria, tab_obras = st.tabs(["📅 Agenda Táctica (Mix)", "🏭 Foco Industrial (Lijas/Mto)", "🏗️ Foco Proyectos (Obra)"])

with tab_cronograma:
    st.markdown("### 🗓️ Ruta de Visitas Optimizada")
    st.markdown("Esta ruta combina visitas a obras (cierres puntuales) con visitas a fábricas (ventas recurrentes de lijas y epóxicos).")
    
    # Renderizar Cronograma como Tabla Estilizada
    df_crono = pd.DataFrame(cronograma)
    st.dataframe(
        df_crono.style.applymap(lambda x: 'background-color: #dbeafe' if 'Lijas' in str(x) else '', subset=['Kit']),
        use_container_width=True, hide_index=True
    )

with tab_industria:
    st.markdown("### 🏭 Empresas Objetivo para Mantenimiento y Consumibles")
    st.markdown("Use esta lista para vender: **Lijas, Discos, Masillas, Epóxicos, Demarcación.**")
    
    df_ind = df[df['Tipo'].str.contains('Industria|Salud|Comercial')]
    for _, row in df_ind.iterrows():
        with st.container():
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"**🏢 {row['Cliente']}** | {row['Ubicación']}")
                st.caption(f"Necesidad: {row['Foco_Venta']} | Tamaño: {row['Tamano']}")
            with col_b:
                st.markdown(f"**${row['Potencial_Estimado']:,.0f}**")
            st.divider()

with tab_obras:
    st.markdown("### 🏗️ Obras para Cierre de Volumen")
    st.markdown("Use esta lista para vender: **Vinilos Tipo 1, Fachadas, Impermeabilizantes, Cerraduras Yale.**")
    
    df_obra = df[df['Tipo'].str.contains('Construcción')]
    st.dataframe(
        df_obra[['Cliente', 'Proyecto', 'Estado', 'Foco_Venta', 'Potencial_Estimado']],
        use_container_width=True
    )

# --- EXPORTAR ---
st.markdown("---")
col_d1, col_d2 = st.columns([3,1])
with col_d1:
    st.success("✅ **Sistema Listo:** El cronograma incluye ahora Don Pollo, Madereras (para Abracol) y Obras civiles.")
with col_d2:
    excel_data = generar_reporte_excel(df, cronograma)
    st.download_button(
        label="📥 Descargar Excel Maestro",
        data=excel_data,
        file_name="Comando_Comercial_Armenia_2026.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )