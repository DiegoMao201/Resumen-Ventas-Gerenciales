import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import io
import time

# Intentar importar la búsqueda web, si falla, usar modo seguro
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

# --- ESTILOS CSS PROFESIONALES (MODO GERENCIAL & IA) ---
st.markdown("""
<style>
    /* Estilos Generales */
    h1 {color: #0f172a; font-weight: 800; letter-spacing: -1px;}
    h2 {color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 10px;}
    
    /* Métricas */
    div[data-testid="stMetricValue"] {font-size: 1.8rem; font-weight: 700; color: #1e40af;}
    
    /* ESTILOS DE LA IA (NUEVO) */
    .ia-box {
        background-color: #1e293b; 
        color: #f8fafc; 
        padding: 20px; 
        border-radius: 10px; 
        border-left: 6px solid #10b981;
        font-family: 'Courier New', monospace;
        margin-bottom: 15px;
    }
    .ia-title {
        color: #34d399; 
        font-weight: bold; 
        text-transform: uppercase; 
        font-size: 1.1rem;
    }
    .ia-alert {
        color: #f87171; 
        font-weight: bold;
    }
    .ia-money {
        color: #a3e635; 
        font-weight: bold;
    }
    
    /* Alertas */
    .alerta-compra {
        background-color: #dcfce7;
        border-left: 5px solid #22c55e;
        padding: 15px;
        color: #14532d;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. MOTOR DE INTELIGENCIA DE NEGOCIOS ---

class GestorOportunidades:
    def __init__(self):
        # Base de datos SEMILLA
        self.db_semilla = [
            {"Cliente": "Constructora CAMU", "Proyecto": "Torre Valparaíso", "Tipo": "Residencial", "Etapa": "Acabados", "m2_aprox": 12000, "Ubicación": "Av Centenario", "Contacto": "Ing. Carlos M."},
            {"Cliente": "Constructora Centenario", "Proyecto": "San Juan de la Loma", "Tipo": "Residencial", "Etapa": "Estructura", "m2_aprox": 8500, "Ubicación": "Norte Armenia", "Contacto": "Arq. Luisa"},
            {"Cliente": "Márquez y Fajardo", "Proyecto": "Mall de la Avenida", "Tipo": "Comercial", "Etapa": "Pintura", "m2_aprox": 5000, "Ubicación": "Av Bolívar", "Contacto": "Ing. Pedro"},
            {"Cliente": "Gobernación del Quindío", "Proyecto": "Mantenimiento Vías", "Tipo": "Infraestructura", "Etapa": "Licitación", "m2_aprox": 0, "Ubicación": "Departamental", "Contacto": "Sec. Infraestructura"},
            {"Cliente": "Clínica Avidanti", "Proyecto": "Ampliación Torre Médica", "Tipo": "Salud", "Etapa": "Obra Gris", "m2_aprox": 4000, "Ubicación": "Av 19", "Contacto": "Dr. Jorge R."},
            {"Cliente": "Constructora Soriano", "Proyecto": "Reserva de los Álamos", "Tipo": "Residencial", "Etapa": "Cimentación", "m2_aprox": 15000, "Ubicación": "Álamos", "Contacto": "Ing. Sofia"},
            {"Cliente": "Industria Cafe Quindio", "Proyecto": "Nueva Planta", "Tipo": "Industria", "Etapa": "Acabados", "m2_aprox": 2000, "Ubicación": "Zona Franca", "Contacto": "Gerente Planta"},
        ]

    def buscar_web_real(self, query):
        """Busca oportunidades reales en vivo"""
        if not SEARCH_AVAILABLE: return []
        resultados = []
        try:
            with DDGS() as ddgs:
                busqueda = ddgs.text(f"{query} Armenia Quindio 2025 2026", region='co-co', max_results=3)
                for r in busqueda:
                    resultados.append({"Título": r['title'], "Enlace": r['href'], "Resumen": r['body']})
        except Exception: pass
        return resultados

    def calcular_potencial_compra(self, m2, etapa, tipo):
        """
        CORRECCIÓN DEL ERROR: Ahora esta función devuelve EXACTAMENTE 4 VALORES.
        1. Galones Pintuco
        2. Unidades Yale
        3. Unidades Habitacionales
        4. Probabilidad de Cierre (0.0 a 1.0)
        """
        if m2 == 0: return 0, 0, 0, 0.1 # Infraestructura
        
        # Lógica de Probabilidad (El 4to valor que faltaba)
        prob = 0.1
        if etapa == "Acabados": prob = 0.95
        elif etapa == "Pintura": prob = 0.90
        elif etapa == "Obra Gris": prob = 0.60
        elif etapa == "Estructura": prob = 0.30
        
        # Cálculos Físicos
        area_pintable = m2 * 2.2 
        galones_pintuco = int(area_pintable / 20) 
        
        num_unidades_habitacionales = int(m2 / 70)
        cerraduras_yale = int(num_unidades_habitacionales * 5) 
        
        return galones_pintuco, cerraduras_yale, num_unidades_habitacionales, prob

# --- 2. CARGA DE DATOS ---

gestor = GestorOportunidades()
df_proyectos = pd.DataFrame(gestor.db_semilla)

# --- 3. CÁLCULO VECTORIZADO (SOLUCIÓN DEL ERROR) ---
# Aquí aplicamos la función corregida que devuelve 4 columnas para igualar las 4 llaves
datos_calculados = df_proyectos.apply(
    lambda x: gestor.calcular_potencial_compra(x['m2_aprox'], x['Etapa'], x['Tipo']), 
    axis=1, 
    result_type='expand'
)
# Asignación correcta 4 columnas = 4 datos
df_proyectos[['Galones_Pintuco', 'Und_Yale', 'Und_Hab', 'Prob_Cierre']] = datos_calculados

# Precios 2026
PRECIO_GALON = 65000 
PRECIO_YALE = 45000 

df_proyectos['Valor_Pintura'] = df_proyectos['Galones_Pintuco'] * PRECIO_GALON
df_proyectos['Valor_Yale'] = df_proyectos['Und_Yale'] * PRECIO_YALE
df_proyectos['Total_Oportunidad'] = df_proyectos['Valor_Pintura'] + df_proyectos['Valor_Yale']

# --- 4. INTERFAZ DE USUARIO ---

st.markdown("# 🎯 Centro de Comando Comercial: Armenia 2026")
st.markdown("**Usuario:** Diego Mauricio García | **Fuerza de Ventas:** Jaime Andrés Londoño")

# PESTAÑAS PRINCIPALES
tab_kpis, tab_ia, tab_crono = st.tabs(["📊 DASHBOARD GENERAL", "🧠 IA ESTRATEGA (Nueva)", "📅 CRONOGRAMA & WEB"])

# --- PESTAÑA 1: DASHBOARD GENERAL (Tu código original mejorado) ---
with tab_kpis:
    col1, col2, col3, col4 = st.columns(4)
    total_pipeline = df_proyectos['Total_Oportunidad'].sum()
    total_galones = df_proyectos['Galones_Pintuco'].sum()
    
    col1.metric("Pipeline Total ($)", f"${total_pipeline:,.0f}")
    col2.metric("Pintuco (Galones)", f"{total_galones:,.0f}")
    col3.metric("Obras Activas", len(df_proyectos))
    col4.metric("Cierre Inminente", len(df_proyectos[df_proyectos['Etapa'].isin(['Acabados', 'Pintura'])]))

    st.markdown("### 🚀 Radar de Proyectos")
    st.dataframe(
        df_proyectos[['Cliente', 'Proyecto', 'Etapa', 'Total_Oportunidad', 'Prob_Cierre']],
        column_config={
            "Total_Oportunidad": st.column_config.ProgressColumn("Valor Potencial", format="$%d", min_value=0, max_value=int(df_proyectos['Total_Oportunidad'].max())),
            "Prob_Cierre": st.column_config.NumberColumn("Probabilidad", format="%.2f")
        },
        use_container_width=True
    )

# --- PESTAÑA 2: IA ESTRATEGA (LA NUEVA PESTAÑA FUERTE Y CLARA) ---
with tab_ia:
    st.subheader("Órdenes Estratégicas Generadas por IA")
    st.caption("Análisis basado en Etapa Constructiva y Volumen de Compra")
    
    # Lógica de la IA para generar texto
    obras_cierre = df_proyectos[df_proyectos['Etapa'].isin(['Acabados', 'Pintura'])]
    total_cierre = obras_cierre['Total_Oportunidad'].sum()
    
    # 1. EL RESUMEN EJECUTIVO (VOZ DE MANDO)
    st.markdown(f"""
    <div class="ia-box">
        <div class="ia-title">🤖 INFORME DE SITUACIÓN PARA DIEGO GARCÍA:</div>
        <br>
        Diego, la situación es crítica pero positiva. Tienes <span class="ia-money">${total_cierre:,.0f}</span> 
        listos para facturar en las próximas 3 semanas en obras que ya están pintando.
        <br><br>
        No pierdas tiempo en proyectos en "Cimentación" ahora mismo. Tu prioridad absoluta es cerrar 
        <b>{len(obras_cierre)} proyectos</b> antes de que entre la competencia.
    </div>
    """, unsafe_allow_html=True)
    
    # 2. ÓRDENES DIRECTAS
    col_izq, col_der = st.columns(2)
    
    with col_izq:
        st.markdown("### 📢 Órdenes para JAIME (Ventas)")
        if not obras_cierre.empty:
            for i, row in obras_cierre.iterrows():
                st.info(f"👉 **VE AHORA DONDE:** {row['Cliente']} ({row['Proyecto']}). \n\n"
                        f"🗣️ **DILE ESTO AL {row['Contacto']}:** 'Ingeniero, tengo el stock de Viniltex listo para despacho inmediato. Si cerramos orden hoy, le sostengo precios 2025'.\n\n"
                        f"💰 **OBJETIVO:** ${row['Total_Oportunidad']:,.0f}")
        else:
            st.warning("No hay obras en cierre inmediato. Jaime debe salir a prospectar obras en Obra Gris URGENTE.")
            
    with col_der:
        st.markdown("### ⚠️ Alertas de Riesgo")
        obras_gris = df_proyectos[df_proyectos['Etapa'] == 'Obra Gris']
        st.error(f"🚨 **PELIGRO DE FUGA:** Tienes {len(obras_gris)} obras en Obra Gris (ej. {obras_gris.iloc[0]['Cliente'] if not obras_gris.empty else ''}). \n\n"
                 "Si no especificas la marca **YALE** ya mismo con el residente, instalarán cerraduras chinas baratas. Envía muestras físicas MAÑANA.")

# --- PESTAÑA 3: CRONOGRAMA Y WEB (Tu código original) ---
with tab_crono:
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.markdown("### 📅 Cronograma Táctico")
        # Generamos Cronograma
        cronograma = []
        fecha = datetime.date.today()
        for i, row in df_proyectos.sort_values('Prob_Cierre', ascending=False).head(5).iterrows():
            cronograma.append({
                "Fecha": fecha,
                "Cliente": row['Cliente'],
                "Acción": "CERRAR VENTA" if row['Prob_Cierre'] > 0.8 else "SEGUIMIENTO",
                "Responsable": "Jaime Londoño"
            })
            fecha += datetime.timedelta(days=2)
        st.table(pd.DataFrame(cronograma))
        
        # Botón descarga
        def generar_excel():
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_proyectos.to_excel(writer, sheet_name='Obras')
            return output.getvalue()
            
        st.download_button("📥 Descargar Plan Maestro Excel", data=generar_excel(), file_name="Plan_Armenia.xlsx")

    with c2:
        st.markdown("### 🌐 Escáner Web")
        if st.button("🔄 Escanear Nuevas Obras"):
            with st.spinner("Buscando licitaciones..."):
                res = gestor.buscar_web_real("Construcción Vivienda")
                if res:
                    for r in res:
                        st.info(f"📰 {r['Título']}")
                else:
                    st.warning("Sin novedades web hoy. Enfócate en las obras activas.")

# --- MENSAJE FINAL ---
st.markdown("---")
st.caption("Sistema Nexus Pro | Desarrollado para GM-DATOVATE")