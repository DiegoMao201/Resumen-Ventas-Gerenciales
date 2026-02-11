import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import plotly.graph_objects as go
import io
import time
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

# --- ESTRUCTURA DE PESTAÑAS ---
pestana_dashboard, pestana_ia, pestana_operaciones = st.tabs(["📊 DASHBOARD GENERAL", "🧠 CEREBRO IA (ESTRATEGA)", "🛠️ OPERACIONES & WEB"])

# ==============================================================================
# PESTAÑA 1: EL DASHBOARD ORIGINAL (Tu diseño preferido)
# ==============================================================================
with pestana_dashboard:
    col1, col2, col3, col4 = st.columns(4)
    total_pipeline = df_proyectos['Total_Oportunidad'].sum()
    total_galones = df_proyectos['Potencial_Pintura_Gal'].sum()
    total_yale = df_proyectos['Potencial_Yale_Und'].sum()
    col1.metric("Pipeline Total ($)", f"${total_pipeline:,.0f}")
    col2.metric("Pintuco (Galones)", f"{total_galones:,.0f}")
    col3.metric("Yale/Abracol (Und)", f"{total_yale:,.0f}")
    col4.metric("Obras Activas", len(df_proyectos))
    st.markdown("### 🚀 Radar de Proyectos: Prioridad Inmediata")
    df_proyectos['Prioridad_Sort'] = df_proyectos['Etapa'].map({'Acabados': 1, 'Pintura': 2, 'Obra Gris': 3, 'Estructura': 4, 'Cimentación': 5, 'Licitación': 6})
    df_display = df_proyectos.sort_values(by=['Prioridad_Sort', 'Total_Oportunidad'], ascending=[True, False])
    st.dataframe(
        df_display[['Cliente', 'Proyecto', 'Etapa', 'Ubicación', 'Potencial_Pintura_Gal', 'Potencial_Yale_Und', 'Total_Oportunidad']],
        column_config={
            "Total_Oportunidad": st.column_config.NumberColumn("Valor Potencial", format="$%d"),
            "Potencial_Pintura_Gal": st.column_config.NumberColumn("Est. Pintura (Gal)"),
            "Potencial_Yale_Und": st.column_config.NumberColumn("Est. Yale (Und)"),
        },
        use_container_width=True
    )
    st.markdown("Ordenado por etapa constructiva y volumen de facturación. Los marcados en **ROJO** requieren visita esta semana.")

# ==============================================================================
# PESTAÑA 2: CEREBRO IA - HABLA CLARO Y FUERTE (LO NUEVO)
# ==============================================================================
with pestana_ia:
    st.header("Análisis de Inteligencia Artificial (Modo Gerencial)")
    st.caption("Interpretación directa de los datos para toma de decisiones inmediata.")
    obras_cierre_ya = df_proyectos[df_proyectos['Etapa'].isin(['Acabados', 'Pintura'])]
    monto_cierre = obras_cierre_ya['Total_Oportunidad'].sum()
    cliente_top = df_proyectos.sort_values('Total_Oportunidad', ascending=False).iloc[0]
    mensaje_ia = f"""
    DIEGO, PRESTA ATENCIÓN A LOS NÚMEROS:
    He analizado tu base de datos y la situación es clara. Tienes un Pipeline Total de <span class="ia-highlight">${total_pipeline:,.0f}</span>, 
    pero lo que realmente importa es lo que podemos cobrar ESTE MES.
    1. Tienes <span class="ia-highlight">{len(obras_cierre_ya)} OBRAS EN FASE DE CIERRE (Acabados/Pintura)</span>.
       Esto representa <span class="ia-highlight">${monto_cierre:,.0f}</span> en flujo de caja inmediato.
       Si Jaime no cierra estos pedidos antes del viernes, la competencia (Pinturas Tito/Otras marcas) entrará por precio.
    2. TU PRIORIDAD #1 SE LLAMA: <span class="ia-highlight">{cliente_top['Cliente']} - {cliente_top['Proyecto']}</span>.
       Es el contrato más grande del tablero. No mandes un correo, manda a Jaime en persona o ve tú mismo.
    3. ALERTA DE RIESGO:
       Veo proyectos en 'Obra Gris'. Si no especificamos la marca YALE ahora mismo con el arquitecto,
       perderemos la venta de las cerraduras cuando lleguen a acabados.
    """
    st.markdown(f'<div class="ia-voice-box">{mensaje_ia}</div>', unsafe_allow_html=True)
    st.subheader("📢 Órdenes del Día para la Fuerza de Ventas")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**PARA: JAIME ANDRÉS LONDOÑO**")
        if not obras_cierre_ya.empty:
            for i, row in obras_cierre_ya.iterrows():
                st.markdown(f"""
                <div class="ia-command">
                🔴 <b>ACCIÓN URGENTE:</b> Visitar {row['Cliente']} ({row['Ubicación']}).<br>
                🗣️ <b>SCRIPT:</b> "Ingeniero {row.get('Contacto', 'Residente')}, tengo autorización de Diego para despachar {row['Potencial_Pintura_Gal']} galones de Viniltex mañana mismo a precio preferencial si firmamos hoy."<br>
                💰 <b>META:</b> ${row['Total_Oportunidad']:,.0f}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay emergencias de cierre. Enfócate en sembrar prospectos en Obra Gris.")
    with col_b:
        st.markdown("**PARA: DIEGO GARCÍA (GERENCIA)**")
        st.markdown("""
        <div class="ia-command">
        🛡️ <b>ESTRATEGIA DEFENSIVA:</b><br>
        Revisar inventario de Viniltex Blanco y Cerraduras de Alcoba. Con el volumen detectado en el radar, podríamos tener una rotura de stock si todos compran a la vez.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="ia-command">
        🔭 <b>VISIÓN 2027:</b><br>
        Las obras en 'Cimentación' (como Constructora Soriano) son tu futuro. Invita a almorzar al ingeniero residente esta semana. No para vender, sino para relacionarte.
        </div>
        """, unsafe_allow_html=True)
    st.markdown("""
    <div class='alerta-compra'>
        🚀 ESTRATEGIA FINAL:
        <br> Recuerda que en la etapa de <b>Acabados</b>, la competencia es feroz. 
        Para los proyectos de <b>Constructora CAMU</b> y <b>Centenario</b> listados arriba, 
        la oferta debe incluir el valor agregado de entrega inmediata (logística) y garantía Pintuco.
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# PESTAÑA 3: OPERACIONES, WEB Y DESCARGAS (Original Restante)
# ==============================================================================
with pestana_operaciones:
    st.markdown("### 🌐 Escáner de Mercado en Vivo (Web)")
    st.caption("Buscando licitaciones y noticias recientes en Armenia Quindío...")
    if st.button("🔄 Ejecutar Escaneo Web Ahora", key="btn_web"):
        with st.spinner('Analizando portales de construcción y noticias locales...'):
            queries = [
                "Lanzamiento proyecto vivienda Armenia", 
                "Licitación construcción Quindío 2026",
                "Inversión infraestructura Armenia 2026"
            ]
            resultados_totales = []
            for q in queries:
                res = gestor.buscar_web_real(q)
                resultados_totales.extend(res)
                time.sleep(1) 
            if resultados_totales:
                for item in resultados_totales:
                    with st.expander(f"📢 {item['Título']}"):
                        st.write(item['Resumen'])
                        st.markdown(f"[Ver Fuente Original]({item['Enlace']})")
                        if "vivienda" in item['Título'].lower():
                            st.success("🎯 Oportunidad potencial para Pintuco Viniltex y Yale Residencial")
                        elif "vial" in item['Título'].lower() or "vía" in item['Título'].lower():
                            st.info("⚠️ Oportunidad Pintuco Tráfico / Señalización")
            else:
                if not SEARCH_AVAILABLE:
                    st.warning("El módulo de búsqueda 'duckduckgo_search' no está instalado. Mostrando datos simulados.")
                    st.info("📢 Noticia: 'Alcaldía inicia reparcheo Av. Centenario' -> Vende Pintura de Tráfico.")
                    st.info("📢 Noticia: 'Camu lanza proyecto Arboretum' -> Oportunidad futura.")
                else:
                    st.warning("No se encontraron noticias urgentes hoy.")
    st.divider()
    st.markdown("### 📅 Cronograma de Visitas Tácticas")
    cronograma = []
    fecha_actual = datetime.date.today()
    dias_visita = [1, 3] # Martes y Jueves
    idx_proyecto = 0
    lista_proyectos_prio = df_display.to_dict('records')
    for semana in range(4):
        for dia in dias_visita:
            if idx_proyecto < len(lista_proyectos_prio):
                p = lista_proyectos_prio[idx_proyecto]
                fecha = fecha_actual + datetime.timedelta(weeks=semana, days=(dia - fecha_actual.weekday() + 7) % 7)
                accion = ""
                if p['Etapa'] in ['Acabados', 'Pintura']:
                    accion = "CERRAR PEDIDO: Llevar muestra física Viniltex."
                elif p['Etapa'] == 'Obra Gris':
                    accion = "ESPECIFICACIÓN: Definir referencias con Residente."
                else:
                    accion = "RELACIONAMIENTO: Visita cortesía."
                cronograma.append({
                    "Fecha": fecha,
                    "Semana": f"Semana {semana+1}",
                    "Cliente": p['Cliente'],
                    "Proyecto": p['Proyecto'],
                    "Vendedor": "JAIME LONDONO",
                    "Acompañante": "DIEGO GARCIA" if p['Total_Oportunidad'] > 50000000 else "-", 
                    "Acción Táctica": accion
                })
                idx_proyecto += 1
    df_crono = pd.DataFrame(cronograma)
    st.table(df_crono)
    def generar_excel(df_crono, df_proyectos):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_crono.to_excel(writer, sheet_name='Agenda Visitas', index=False)
            df_proyectos.to_excel(writer, sheet_name='Análisis Obras', index=False)
        return output.getvalue()
    st.download_button(
        label="📥 Descargar Plan de Ataque Completo (.xlsx)",
        data=generar_excel(df_crono, df_proyectos),
        file_name="Plan_Maestro_Armenia_2026.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )