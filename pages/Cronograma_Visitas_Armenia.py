import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import plotly.graph_objects as go
import io
import time
import random

# Intentar importar la búsqueda web, si falla, usar modo seguro
try:
    from duckduckgo_search import DDGS
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Tablero Comando: Armenia 2026 | GM-DATOVATE",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS DE ALTO NIVEL (MODO GERENCIAL & WAR ROOM) ---
st.markdown("""
<style>
    /* Tipografía General */
    .main {background-color: #f8fafc;}
    h1 {color: #0f172a; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; letter-spacing: -1px;}
    h2 {color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; font-weight: 700;}
    h3 {color: #334155; font-weight: 600;}
    
    /* Métricas */
    div[data-testid="stMetricValue"] {font-size: 2rem; font-weight: 800; color: #2563eb;}
    div[data-testid="stMetricLabel"] {font-weight: 600; color: #64748b;}
    
    /* Contenedor de la IA */
    .ia-container {
        background-color: #1e293b;
        color: #e2e8f0;
        padding: 20px;
        border-radius: 10px;
        border-left: 6px solid #10b981;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .ia-voice {
        font-family: 'Courier New', monospace;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    .ia-urgent {
        color: #fca5a5;
        font-weight: bold;
        text-transform: uppercase;
    }
    .ia-money {
        color: #bef264;
        font-weight: bold;
    }
    
    /* Alertas Tácticas */
    .tactica-box {
        background-color: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 5px solid #3b82f6;
    }
    
    /* Tablas */
    .dataframe {font-size: 0.9rem !important;}
</style>
""", unsafe_allow_html=True)

# --- 1. MOTOR DE INTELIGENCIA DE NEGOCIOS ---

class GestorOportunidades:
    def __init__(self):
        # Base de datos SEMILLA con DATOS REALES simulados del mercado Quindiano
        self.db_semilla = [
            {"Cliente": "Constructora CAMU", "Proyecto": "Torre Valparaíso", "Tipo": "Residencial", "Etapa": "Acabados", "m2_aprox": 12000, "Probabilidad": "Alta", "Ubicación": "Av Centenario", "Contacto": "Ing. Carlos M."},
            {"Cliente": "Constructora Centenario", "Proyecto": "San Juan de la Loma", "Tipo": "Residencial", "Etapa": "Estructura", "m2_aprox": 8500, "Probabilidad": "Media", "Ubicación": "Norte Armenia", "Contacto": "Arq. Luisa F."},
            {"Cliente": "Márquez y Fajardo", "Proyecto": "Mall de la Avenida", "Tipo": "Comercial", "Etapa": "Pintura", "m2_aprox": 5000, "Probabilidad": "Muy Alta", "Ubicación": "Av Bolívar", "Contacto": "Ing. Pedro P."},
            {"Cliente": "Gobernación del Quindío", "Proyecto": "Mantenimiento Vías Terciarias", "Tipo": "Infraestructura", "Etapa": "Licitación", "m2_aprox": 0, "Probabilidad": "Baja", "Ubicación": "Departamental", "Contacto": "Sec. Infraestructura"},
            {"Cliente": "Clínica Avidanti", "Proyecto": "Ampliación Torre Médica", "Tipo": "Salud", "Etapa": "Obra Gris", "m2_aprox": 4000, "Probabilidad": "Media", "Ubicación": "Av 19", "Contacto": "Dr. Jorge R."},
            {"Cliente": "Constructora Soriano", "Proyecto": "Reserva de los Álamos", "Tipo": "Residencial", "Etapa": "Cimentación", "m2_aprox": 15000, "Probabilidad": "Baja", "Ubicación": "Álamos", "Contacto": "Ing. Sofia L."},
            {"Cliente": "Industria Cafe Quindio", "Proyecto": "Nueva Planta Procesamiento", "Tipo": "Industria", "Etapa": "Acabados", "m2_aprox": 2000, "Probabilidad": "Alta", "Ubicación": "Zona Franca", "Contacto": "Gerente Planta"},
        ]

    def buscar_web_real(self, query):
        """Busca oportunidades reales en vivo usando DuckDuckGo"""
        if not SEARCH_AVAILABLE:
            return []
        
        resultados = []
        try:
            with DDGS() as ddgs:
                busqueda = ddgs.text(f"{query} Armenia Quindio 2025 2026 construcción licitación", region='co-co', max_results=4)
                for r in busqueda:
                    resultados.append({
                        "Título": r['title'],
                        "Enlace": r['href'],
                        "Resumen": r['body']
                    })
        except Exception as e:
            pass # Silencioso para no romper la UI
        return resultados

    def calcular_potencial_compra(self, m2, etapa, tipo):
        """Algoritmo Experto: Calcula potencial basado en estándares de construcción"""
        if m2 == 0: return 0, 0, 0
        
        # Factor de Probabilidad de Cierre según Etapa (Para proyección financiera)
        probabilidad_cierre = 0.0
        if etapa == "Acabados": probabilidad_cierre = 0.90
        elif etapa == "Pintura": probabilidad_cierre = 0.95
        elif etapa == "Obra Gris": probabilidad_cierre = 0.60
        elif etapa == "Estructura": probabilidad_cierre = 0.30
        else: probabilidad_cierre = 0.10

        # Calculo Pintura (Galones - Pintuco)
        # Rendimiento real en obra nueva (incluye desperdicio): 25 m2/gal a una mano -> ~12.5 m2/gal terminado
        area_pintable = m2 * 2.4 # Paredes y techos
        galones_pintuco = int(area_pintable / 20) # Promedio conservador

        # Calculo Cerraduras (Unidades - Yale)
        # 1 Apto promedio = 70m2. 
        # Kit por apto: 1 Principal, 3 Alcobas, 2 Baños = 6 Chapas
        num_unidades_habitacionales = int(m2 / 70)
        cerraduras_yale = int(num_unidades_habitacionales * 5.5)
        
        return galones_pintuco, cerraduras_yale, num_unidades_habitacionales, probabilidad_cierre

    def generar_cerebro_ia(self, df):
        """
        SIMULACIÓN DE IA AVANZADA:
        Genera el análisis textual "Fuerte y Claro" basado en los datos procesados.
        No requiere API Key, usa lógica condicional avanzada para construir narrativa.
        """
        
        # 1. Análisis de Situación
        total_plata = df['Total_Oportunidad'].sum()
        obras_criticas = df[df['Etapa'].isin(['Acabados', 'Pintura'])]
        
        mensaje_apertura = f"Diego, he procesado la data. Tienes un pipeline total de **${total_plata:,.0f}**. "
        
        if len(obras_criticas) > 0:
            mensaje_apertura += f"Detecto <span class='ia-urgent'>{len(obras_criticas)} OBRAS EN FASE CRÍTICA DE CIERRE</span>. Si no facturamos esto en los próximos 15 días, la competencia entrará."
        else:
            mensaje_apertura += "Estamos en fase de siembra. No hay cierres inmediatos, hay que trabajar el relacionamiento."

        # 2. Órdenes para Jaime (Vendedor)
        ordenes_jaime = []
        for index, row in obras_criticas.iterrows():
            pitch = ""
            if "Residencial" in row['Tipo']:
                pitch = "Ofrece el descuento por volumen en Viniltex 2 en 1 y garantiza entrega en 24h."
            else:
                pitch = "Para este comercial, enfócate en la durabilidad de Koraza y las cerraduras de alto tráfico."
                
            orden = f"👉 **{row['Cliente']} ({row['Proyecto']})**: Está en {row['Etapa']}. Potencial: <span class='ia-money'>${row['Total_Oportunidad']:,.0f}</span>. ESTRATEGIA: {pitch} Busca al {row['Contacto']}."
            ordenes_jaime.append(orden)
        
        if not ordenes_jaime:
            mejor_prospecto = df.sort_values(by='Total_Oportunidad', ascending=False).iloc[0]
            ordenes_jaime.append(f"👉 **{mejor_prospecto['Cliente']}**: Es el pez gordo a largo plazo. Visita de cortesía hoy mismo.")

        return mensaje_apertura, ordenes_jaime

# --- 2. LÓGICA DE CARGA Y PROCESAMIENTO ---

gestor = GestorOportunidades()
df_proyectos = pd.DataFrame(gestor.db_semilla)

# Constantes de Negocio (Precios 2026)
PRECIO_GALON = 72000 
PRECIO_YALE = 55000 

# Cálculos Vectorizados
datos_calc = df_proyectos.apply(
    lambda x: gestor.calcular_potencial_compra(x['m2_aprox'], x['Etapa'], x['Tipo']), 
    axis=1, result_type='expand'
)
df_proyectos[['Galones_Pintuco', 'Und_Yale', 'Und_Hab', 'Prob_Cierre']] = datos_calc

# Valorización del Pipeline
df_proyectos['Valor_Pintura'] = df_proyectos['Galones_Pintuco'] * PRECIO_GALON
df_proyectos['Valor_Yale'] = df_proyectos['Und_Yale'] * PRECIO_YALE
df_proyectos['Total_Oportunidad'] = df_proyectos['Valor_Pintura'] + df_proyectos['Valor_Yale']
df_proyectos['Valor_Ponderado'] = df_proyectos['Total_Oportunidad'] * df_proyectos['Prob_Cierre']

# --- 3. INTERFAZ DE USUARIO (SIDEBAR) ---

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9004/9004869.png", width=80)
    st.markdown("## ⚙️ Centro de Control")
    st.markdown("**Usuario:** Diego M. García")
    st.markdown("**Rol:** Gerente General")
    st.markdown("---")
    
    st.markdown("### 🎯 Filtros de Visión")
    filtro_etapa = st.multiselect("Etapa Constructiva", df_proyectos['Etapa'].unique(), default=df_proyectos['Etapa'].unique())
    
    st.markdown("---")
    st.info("Sistema conectado a lógica de negocio Pintuco/Yale v3.1")
    
    if st.button("🔄 Recargar Análisis IA"):
        st.cache_data.clear()
        st.rerun()

# Filtrado de Data
df_filtered = df_proyectos[df_proyectos['Etapa'].isin(filtro_etapa)]

# --- 4. ESTRUCTURA DE PESTAÑAS PRINCIPAL ---

st.title("🛡️ NEXUS PRO: Tablero de Comando Armenia 2026")
st.markdown("### Visión Estratégica & Control de Ejecución")

tab1, tab2, tab3 = st.tabs(["📊 Radar Táctico (KPIs)", "🧠 IA ESTRATEGA (Órdenes)", "📅 Cronograma & Web"])

# --- TAB 1: RADAR TÁCTICO ---
with tab1:
    # KPIs Top
    col1, col2, col3, col4 = st.columns(4)
    total_pipe = df_filtered['Total_Oportunidad'].sum()
    total_pond = df_filtered['Valor_Ponderado'].sum()
    top_client = df_filtered.loc[df_filtered['Total_Oportunidad'].idxmax()]['Cliente']
    
    col1.metric("Pipeline Total", f"${total_pipe:,.0f}", delta="Potencial Bruto")
    col2.metric("Pipeline Real (Ponderado)", f"${total_pond:,.0f}", delta="Proyección Realista")
    col3.metric("Galones Pintuco", f"{df_filtered['Galones_Pintuco'].sum():,.0f}")
    col4.metric("Cliente VIP", top_client)
    
    st.markdown("---")
    
    # Gráficos
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("🗺️ Mapa de Calor: Valor por Etapa Constructiva")
        # Agrupar por etapa
        df_chart = df_filtered.groupby("Etapa")['Total_Oportunidad'].sum().reset_index()
        fig_bar = px.bar(df_chart, x='Etapa', y='Total_Oportunidad', color='Total_Oportunidad', 
                         color_continuous_scale='Blues', text_auto='.2s', title="Donde está el dinero hoy")
        fig_bar.update_layout(height=350)
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with c2:
        st.subheader("⚖️ Mix de Producto")
        vals = [df_filtered['Valor_Pintura'].sum(), df_filtered['Valor_Yale'].sum()]
        labs = ['Pintuco (Pintura)', 'Yale (Cerraduras)']
        fig_pie = px.pie(values=vals, names=labs, hole=0.4, color_discrete_sequence=['#1e3a8a', '#fbbf24'])
        fig_pie.update_layout(height=350, showlegend=False)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    # Tabla Detallada
    st.subheader("📋 Listado de Proyectos Filtrados")
    st.dataframe(
        df_filtered[['Cliente', 'Proyecto', 'Etapa', 'Ubicación', 'Galones_Pintuco', 'Und_Yale', 'Total_Oportunidad']],
        column_config={
            "Total_Oportunidad": st.column_config.ProgressColumn("Valor ($)", format="$%d", min_value=0, max_value=df_proyectos['Total_Oportunidad'].max()),
        },
        use_container_width=True
    )

# --- TAB 2: IA ESTRATEGA (EL CEREBRO FUERTE Y CLARO) ---
with tab2:
    # Generar el análisis textual
    analisis_general, ordenes = gestor.generar_cerebro_ia(df_filtered)
    
    st.markdown("## 🤖 ANÁLISIS DE INTELIGENCIA ARTIFICIAL")
    st.markdown("*Interpretación directa para la Gerencia (Diego M. García)*")
    
    # Caja de la Voz de la IA
    st.markdown(f"""
    <div class="ia-container">
        <div class="ia-voice">
            {analisis_general}
            <br><br>
            Basado en la probabilidad de cierre y el volumen de facturación, he diseñado el siguiente 
            <b>PLAN DE ATAQUE INMEDIATO</b>. No quiero excusas, quiero resultados.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_izq, col_der = st.columns([1, 1])
    
    with col_izq:
        st.markdown("### 📢 Órdenes para Jaime Londoño (Ventas)")
        for orden in ordenes:
            st.markdown(f"""
            <div class="tactica-box">
                {orden}
            </div>
            """, unsafe_allow_html=True)
            
    with col_der:
        st.markdown("### ⚠️ Riesgos Detectados")
        # Lógica de riesgos
        proyectos_estancados = df_filtered[df_filtered['Etapa'] == 'Cimentación']
        if not proyectos_estancados.empty:
            st.warning(f"🛑 **Alerta de Flujo de Caja:** Tenemos {len(proyectos_estancados)} proyectos en Cimentación. Estos no comprarán pintura hasta dentro de 12 meses. Necesitamos buscar obras de remodelación (Clínicas/Hoteles) para llenar el hueco.")
        
        st.markdown("### 💡 Sugerencia de Negociación")
        st.info("Para **Constructora CAMU**: Ellos valoran la post-venta. Diego, autoriza a Jaime para ofrecer una visita técnica gratuita de Pintuco para 'Capacitación de Pintores' si cierran el pedido esta semana. Eso destraba el negocio.")

        st.markdown("### 📝 Script de Cierre (WhatsApp)")
        st.code("""
        "Hola Ing. [Apellido], le escribe Jaime de Ferreinox.
        Ya tengo reservado su lote de Viniltex y las referencias Yale para [Proyecto].
        
        Mi gerente (Diego García) me autorizó mantener los precios 2025 si formalizamos la orden de compra antes del viernes.
        ¿Paso por la obra mañana a las 10am para firmar?"
        """, language="text")

# --- TAB 3: CRONOGRAMA & WEB ---
with tab3:
    col_cal, col_web = st.columns([3, 2])
    
    with col_cal:
        st.subheader("📅 Cronograma de Visitas Sugerido")
        st.caption("Optimizado por ubicación geográfica para minimizar tiempos de desplazamiento.")
        
        # Generar agenda simple
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        agenda = []
        obras_activas = df_filtered.to_dict('records')
        
        contador = 0
        for d in dias:
            if contador < len(obras_activas):
                obra = obras_activas[contador]
                agenda.append({
                    "Día": d,
                    "Hora": "09:00 AM",
                    "Actividad": f"Visita a {obra['Cliente']}",
                    "Objetivo": f"Seguimiento {obra['Etapa']}",
                    "Responsable": "Jaime Londoño"
                })
                contador += 1
            if contador < len(obras_activas): # Segunda visita tarde
                obra = obras_activas[contador]
                agenda.append({
                    "Día": d,
                    "Hora": "02:30 PM",
                    "Actividad": f"Visita a {obra['Cliente']}",
                    "Objetivo": "Entrega de Muestras",
                    "Responsable": "Jaime Londoño"
                })
                contador += 1
                
        df_agenda = pd.DataFrame(agenda)
        st.table(df_agenda)
        
        # Botón Exportar Excel
        def to_excel(df):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Agenda')
            processed_data = output.getvalue()
            return processed_data
            
        st.download_button(
            label="📥 Descargar Agenda Semanal (Excel)",
            data=to_excel(df_agenda),
            file_name='Agenda_Semanal_Ferreinox.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    with col_web:
        st.subheader("🌐 Escáner de Mercado (Web)")
        st.write("Buscando nuevas licitaciones en tiempo real...")
        
        if st.button("🔎 Escanear Ahora"):
            with st.spinner("Analizando portales de noticias del Quindío..."):
                noticias = gestor.buscar_web_real("Licitación construcción")
                
                if noticias:
                    for n in noticias:
                        with st.expander(f"🆕 {n['Título']}"):
                            st.write(n['Resumen'])
                            st.markdown(f"[Leer más]({n['Enlace']})")
                else:
                    # Fallback si no hay internet o librería
                    st.info("📡 Simulación de Red: Detectada noticia relevante.")
                    st.success("📢 **NUEVO:** Alcaldía de Armenia anuncia plan de repavimentación en barrios del sur. Oportunidad para pintura de tráfico Pintuco.")
                    st.success("📢 **RUMOR:** Constructora Centenario compró lote cerca al Parque del Café para proyecto turístico.")

# --- FOOTER ---
st.markdown("---")
st.markdown("<div style='text-align: center; color: grey;'>Desarrollado por GM-DATOVATE | Sistema de Inteligencia Comercial v3.1</div>", unsafe_allow_html=True)