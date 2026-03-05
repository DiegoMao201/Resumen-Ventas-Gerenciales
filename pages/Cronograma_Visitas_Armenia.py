import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import io
import xlsxwriter

# Intenta importar librerías opcionales
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
    page_title="Tablero Comando: Manizales 2026",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS AVANZADOS ---
st.markdown("""
<style>
    :root {
        --primary: #0F172A;
        --secondary: #047857; /* Verde Eje Cafetero */
        --accent: #F59E0B;
        --bg-light: #F8FAFC;
    }
    h1, h2, h3 {font-family: 'Segoe UI', sans-serif; color: var(--primary);}
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem; font-weight: 800; color: var(--secondary);
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #E2E8F0; border-radius: 5px; color: #475569; font-weight: bold;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: var(--secondary); color: white;
    }
    .badge-vis {background-color: #3B82F6; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8em;}
    .badge-vip {background-color: #8B5CF6; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8em;}
    .badge-novis {background-color: #F59E0B; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8em;}
</style>
""", unsafe_allow_html=True)

# --- 1. CEREBRO DE INTELIGENCIA COMERCIAL ---

class GestorInteligenteManizales:
    def __init__(self):
        # BASE DE DATOS MAESTRA: ESTUDIO DE MERCADO MANIZALES Y ALREDEDORES
        self.db_semilla = [
            # --- CONSTRUCCIÓN: PROYECTOS VIS / VIP ---
            {
                "Cliente": "Constructora CFC", "Proyecto": "Ciudadela Bella Suiza (Etapa 4)", 
                "Tipo": "Construcción Residencial", "Clasificacion": "VIS", "Estado": "Estructura", "Tamano": "45000 m2",
                "Ubicación": "Manizales (Sector Suiza)", "Foco_Venta": "Volumen Vinilo Tipo 2, Cerraduras Básicas Yale", "Probabilidad_Cierre": 75
            },
            {
                "Cliente": "Construcaldas", "Proyecto": "Villas del Rosario", 
                "Tipo": "Construcción Residencial", "Clasificacion": "VIP", "Estado": "Cimentación", "Tamano": "20000 m2",
                "Ubicación": "Villamaría", "Foco_Venta": "Pintura Económica, Volumen Obra Blanca", "Probabilidad_Cierre": 60
            },
            {
                "Cliente": "Constructora Las Galias", "Proyecto": "Torres de Milán VIS", 
                "Tipo": "Construcción Residencial", "Clasificacion": "VIS", "Estado": "Acabados", "Tamano": "30000 m2",
                "Ubicación": "Manizales (Norte)", "Foco_Venta": "Urgente: Pintura Interior, Puertas y Chapas", "Probabilidad_Cierre": 90
            },
            
            # --- CONSTRUCCIÓN: PROYECTOS NO VIS (PREMIUM) ---
            {
                "Cliente": "Constructora Berlín", "Proyecto": "Altos de la Florida Premium", 
                "Tipo": "Construcción Residencial", "Clasificacion": "No VIS", "Estado": "Acabados", "Tamano": "15000 m2",
                "Ubicación": "Manizales (La Florida)", "Foco_Venta": "Vinilos Lavables Tipo 1, Fachadas Premium, Yale Digital", "Probabilidad_Cierre": 85
            },
            {
                "Cliente": "Pranha Constructores", "Proyecto": "Mall Comercial Chinchiná", 
                "Tipo": "Construcción Comercial", "Clasificacion": "Comercial", "Estado": "Estructura", "Tamano": "12000 m2",
                "Ubicación": "Chinchiná", "Foco_Venta": "Pintura Tráfico, Epóxicos, Demarcación Parqueaderos", "Probabilidad_Cierre": 70
            },
            {
                "Cliente": "Gobernación de Caldas", "Proyecto": "Hospital Regional Neira", 
                "Tipo": "Salud / Institucional", "Clasificacion": "Institucional", "Estado": "Licitación", "Tamano": "8000 m2",
                "Ubicación": "Neira", "Foco_Venta": "Pintura Epóxica Antibacterial, Tráfico Pesado", "Probabilidad_Cierre": 40
            },

            # --- GRANDES INDUSTRIAS (MANTENIMIENTO RECURRENTE) ---
            {
                "Cliente": "Casa Luker", "Proyecto": "Planta Principal Torrefactora", 
                "Tipo": "Industria Alimentos", "Clasificacion": "Industrial", "Estado": "Operativo", "Tamano": "Gigante",
                "Ubicación": "Chinchiná", "Foco_Venta": "Mantenimiento Epóxicos, Pintura Asepsia, Abrasivos", "Probabilidad_Cierre": 80
            },
            {
                "Cliente": "Mabe Colombia", "Proyecto": "Planta Ensamblaje Electrodomésticos", 
                "Tipo": "Industria Metalmecánica", "Clasificacion": "Industrial", "Estado": "Operativo", "Tamano": "Gigante",
                "Ubicación": "Manizales (Zona Industrial)", "Foco_Venta": "Alto Volumen Abrasivos, Lijas Industriales, Abracol", "Probabilidad_Cierre": 85
            },
            {
                "Cliente": "Herragro", "Proyecto": "Forjas y Herramientas", 
                "Tipo": "Industria Metalmecánica", "Clasificacion": "Industrial", "Estado": "Operativo", "Tamano": "Grande",
                "Ubicación": "Manizales (Maltería)", "Foco_Venta": "Lijas, Discos de Corte, Pintura Industrial", "Probabilidad_Cierre": 70
            },
            {
                "Cliente": "Efigas", "Proyecto": "Mantenimiento Estaciones", 
                "Tipo": "Infraestructura", "Clasificacion": "Industrial", "Estado": "Operativo", "Tamano": "Mediano",
                "Ubicación": "Manizales / Villamaría", "Foco_Venta": "Pintura Anticorrosiva, Esmaltes Especiales", "Probabilidad_Cierre": 90
            }
        ]

    def analizar_mercado(self, row):
        """
        Algoritmo avanzado que calcula el valor del cliente basado en:
        1. Estrato del proyecto (VIS/VIP vs No VIS) que afecta el margen.
        2. Etapa de la obra que afecta la urgencia.
        3. Consumo recurrente industrial.
        """
        tipo = row['Tipo']
        tamano_str = str(row['Tamano'])
        clasificacion = row['Clasificacion']
        estado = row['Estado']
        
        # PRECIOS BASE Y MÁRGENES 2026
        p_vinilo_estandar = 65000  # VIS/VIP
        p_vinilo_premium = 110000  # No VIS
        p_epoxico = 150000
        p_chapa_estandar = 35000
        p_chapa_digital = 250000
        p_lija_ind = 4000
        
        potencial_total = 0
        detalle = ""
        score_urgencia = 0 # 1 a 10

        # LÓGICA 1: CONSTRUCCIÓN (Venta por Proyecto)
        if "Construcción" in tipo or "Salud" in tipo:
            try:
                m2 = int(tamano_str.replace(" m2", "").replace("Varios KM", "1000"))
            except:
                m2 = 5000
            
            # Diferenciación por tipo de proyecto
            if clasificacion in ["VIS", "VIP"]:
                rendimiento = 25 # M2 por galón
                galones = m2 / rendimiento
                yales = m2 / 60 # Apartamentos más pequeños = más puertas por m2
                potencial_total = (galones * p_vinilo_estandar) + (yales * p_chapa_estandar)
                detalle = f"Volumen: {int(galones)} gal (Estándar) + {int(yales)} Yales básicas"
            elif clasificacion == "No VIS":
                rendimiento = 20 # Más manos, mejor acabado
                galones = m2 / rendimiento
                yales = m2 / 100 # Aptos más grandes
                potencial_total = (galones * p_vinilo_premium) + (yales * p_chapa_digital)
                detalle = f"Premium: {int(galones)} gal (Tipo 1) + {int(yales)} Yales Digitales"
            else: # Comercial/Institucional
                galones = m2 / 30
                potencial_total = (galones * p_epoxico)
                detalle = f"Especializado: {int(galones)} gal Epóxico/Tráfico"

            # Score de Urgencia basado en etapa
            if estado == "Acabados": score_urgencia = 10
            elif estado == "Estructura": score_urgencia = 6
            else: score_urgencia = 3

        # LÓGICA 2: INDUSTRIA (Venta Recurrente Mensual x 12)
        else:
            if "Gigante" in tamano_str:
                vol_lijas = 3000
                vol_epox = 50
            elif "Grande" in tamano_str:
                vol_lijas = 1500
                vol_epox = 20
            else:
                vol_lijas = 500
                vol_epox = 10

            # Ajustes por industria
            if "Metalmecánica" in tipo: vol_lijas *= 2
            if "Alimentos" in tipo: vol_epox *= 1.5

            venta_mes = (vol_lijas * p_lija_ind) + (vol_epox * p_epoxico)
            potencial_total = venta_mes * 12 # Proyección anualizada
            detalle = f"Recurrente/Mes: {int(vol_lijas)} Abrasivos + {int(vol_epox)} gal Epóxicos"
            score_urgencia = 8 # La industria compra siempre

        # Cálculo de prioridad inteligente combinando Dinero + Urgencia + Probabilidad
        prob_factor = row['Probabilidad_Cierre'] / 100
        valor_esperado = potencial_total * prob_factor
        
        if score_urgencia >= 8 and valor_esperado > 50000000:
            prioridad = "🔥 Crítica (Cierre Inmediato)"
        elif score_urgencia >= 5 or valor_esperado > 20000000:
            prioridad = "⚡ Alta (Gestión Activa)"
        else:
            prioridad = "🌱 Media (Siembra/Especificación)"

        return int(potencial_total), int(valor_esperado), detalle, prioridad, score_urgencia

# --- 2. GENERADOR DE CRONOGRAMA GEORREFERENCIADO ---
def generar_rutero_inteligente(df):
    """Agrupa las visitas por ubicación para no hacer perder tiempo al vendedor"""
    df_rutero = df.sort_values(by=['Score_Urgencia', 'Potencial_Estimado'], ascending=[False, False])
    
    rutas_por_dia = []
    fecha_actual = datetime.date(2026, 3, 2) # Lunes
    
    # Agrupar por macro-sectores para optimizar transporte
    zonas = {
        "Manizales Norte/Milán": df_rutero[df_rutero['Ubicación'].str.contains('Norte|Florida', case=False, na=False)],
        "Zona Industrial & Maltería": df_rutero[df_rutero['Ubicación'].str.contains('Maltería|Industrial', case=False, na=False)],
        "Sur & Villamaría": df_rutero[df_rutero['Ubicación'].str.contains('Villamaría|Suiza', case=False, na=False)],
        "Ruta Chinchiná - Neira": df_rutero[df_rutero['Ubicación'].str.contains('Chinchiná|Neira', case=False, na=False)]
    }

    dia_semana = 0 # 0=Lunes, 4=Viernes
    
    for nombre_zona, clientes_zona in zonas.items():
        if clientes_zona.empty: continue
        
        # Saltar fines de semana
        if dia_semana > 4: 
            fecha_actual += datetime.timedelta(days=2)
            dia_semana = 0

        for _, cliente in clientes_zona.iterrows():
            accion = "Cierre Comercial Obra" if "Acabados" in str(cliente['Estado']) else "Auditoría de Planta y Stock"
            rutas_por_dia.append({
                "Fecha": fecha_actual.strftime("%Y-%m-%d"),
                "Día": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"][dia_semana],
                "Zona": nombre_zona,
                "Cliente": cliente['Cliente'],
                "Clasificación": cliente['Clasificacion'],
                "Acción Clave": accion,
                "Portafolio Sugerido": cliente['Foco_Venta']
            })
        
        # Avanzar un día por zona
        fecha_actual += datetime.timedelta(days=1)
        dia_semana += 1

    return pd.DataFrame(rutas_por_dia)

# --- 3. EXPORTADOR EXCEL ULTRAMODERNO ---
def exportar_inteligencia_excel(df, df_rutero):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # Formatos
    f_header = workbook.add_format({'bold': True, 'bg_color': '#047857', 'font_color': 'white', 'border': 1})
    f_money = workbook.add_format({'num_format': '$ #,##0', 'border': 1})
    f_text = workbook.add_format({'border': 1})
    f_h1 = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#047857'})

    # Hoja 1: Market Share
    ws1 = workbook.add_worksheet("Estudio de Mercado")
    ws1.write("B2", "ESTUDIO DE MERCADO MANIZALES Y EJE CAFETERO - 2026", f_h1)
    
    cols = ["Cliente", "Proyecto", "Ubicación", "Tipo", "Clasificación", "Potencial 100% ($)", "Valor Esperado ($) Ponderado", "Prioridad AI"]
    ws1.write_row("B4", cols, f_header)
    
    for i, row in enumerate(df.itertuples(), start=5):
        ws1.write(i, 1, row.Cliente, f_text)
        ws1.write(i, 2, row.Proyecto, f_text)
        ws1.write(i, 3, row.Ubicación, f_text)
        ws1.write(i, 4, row.Tipo, f_text)
        ws1.write(i, 5, row.Clasificacion, f_text)
        ws1.write(i, 6, row.Potencial_Estimado, f_money)
        ws1.write(i, 7, row.Valor_Esperado, f_money)
        ws1.write(i, 8, row.Prioridad_Venta, f_text)
        
    ws1.set_column('B:C', 30)
    ws1.set_column('D:H', 20)

    # Hoja 2: Rutero
    ws2 = workbook.add_worksheet("Rutero Inteligente")
    ws2.write("A1", "CRONOGRAMA OPTIMIZADO POR ZONAS GEOGRÁFICAS", f_h1)
    ws2.write_row("A3", df_rutero.columns, f_header)
    
    for i, row in enumerate(df_rutero.itertuples(index=False), start=3):
        for j, val in enumerate(row):
            ws2.write(i, j, val, f_text)
            
    ws2.set_column('A:B', 15)
    ws2.set_column('C:D', 25)
    ws2.set_column('E:E', 15)
    ws2.set_column('F:G', 45)

    workbook.close()
    return output.getvalue()

# --- 4. INTERFAZ Y LÓGICA DE APLICACIÓN ---

gestor = GestorInteligenteManizales()

# --- Sidebar: Filtros de Mercado ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/line-chart.png", width=60)
    st.title("Filtros de Inteligencia")
    
    ubicaciones = st.multiselect(
        "📍 Zonas Geográficas",
        ["Manizales", "Villamaría", "Chinchiná", "Neira"],
        default=["Manizales", "Villamaría", "Chinchiná", "Neira"]
    )
    
    tipo_proyectos = st.multiselect(
        "🏗️ Clasificación de Obra",
        ["VIS", "VIP", "No VIS", "Comercial", "Institucional", "Industrial"],
        default=["VIS", "VIP", "No VIS", "Industrial"]
    )

# Procesamiento Principal
df = pd.DataFrame(gestor.db_semilla)

# Aplicar Filtros Dinámicos
if ubicaciones:
    # Lógica de búsqueda de strings para abarcar ubicaciones compuestas (ej: "Manizales (Norte)")
    patron_ubicacion = '|'.join(ubicaciones)
    df = df[df['Ubicación'].str.contains(patron_ubicacion, case=False, na=False)]

if tipo_proyectos:
    df = df[df['Clasificacion'].isin(tipo_proyectos)]

# Ejecutar el Cerebro IA
if not df.empty:
    resultados = df.apply(gestor.analizar_mercado, axis=1, result_type='expand')
    df[['Potencial_Estimado', 'Valor_Esperado', 'Detalle_Calculo', 'Prioridad_Venta', 'Score_Urgencia']] = resultados
    df = df.sort_values(by="Valor_Esperado", ascending=False)
    
    # Generar Rutero
    df_rutero = generar_rutero_inteligente(df)
else:
    df_rutero = pd.DataFrame()

# --- HEADER DEL DASHBOARD ---
st.title("🎯 Central de Mando: Manizales y Área Metropolitana")
st.markdown("Plataforma de prospección avanzada para **Abrasivos, Pinturas Arquitectónicas/Industriales y Cerrajería**.")
st.divider()

if df.empty:
    st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados en la barra lateral.")
else:
    # --- KPIs PRINCIPALES ---
    c1, c2, c3, c4 = st.columns(4)
    potencial_bruto = df['Potencial_Estimado'].sum()
    pipeline_ajustado = df['Valor_Esperado'].sum() # Ponderado por probabilidad
    obras_vis_vip = df[df['Clasificacion'].isin(['VIS', 'VIP'])].shape[0]
    obras_novis = df[df['Clasificacion'] == 'No VIS'].shape[0]

    c1.metric("💰 TAM (Mercado Total Disp.)", f"${potencial_bruto:,.0f}", "Bruto")
    c2.metric("🎯 Pipeline Real (Ajustado)", f"${pipeline_ajustado:,.0f}", "Ponderado x Probabilidad")
    c3.metric("🏗️ Obras VIS/VIP (Volumen)", f"{obras_vis_vip} Proyectos")
    c4.metric("💎 Obras No VIS (Margen)", f"{obras_novis} Proyectos")

    # --- GRÁFICOS DE ANÁLISIS ---
    col_chart1, col_chart2 = st.columns([1, 1])
    
    with col_chart1:
        st.subheader("🗺️ Distribución del Mercado por Clasificación")
        fig_sun = px.sunburst(
            df, path=['Ubicación', 'Clasificacion', 'Cliente'], values='Valor_Esperado',
            color='Clasificacion',
            color_discrete_map={'VIS':'#3B82F6', 'VIP':'#8B5CF6', 'No VIS':'#F59E0B', 'Industrial':'#10B981'},
            height=400
        )
        st.plotly_chart(fig_sun, use_container_width=True)

    with col_chart2:
        st.subheader("📊 Top Clientes (Valor Esperado vs Urgencia)")
        fig_scatter = px.scatter(
            df, x="Valor_Esperado", y="Score_Urgencia", 
            size="Potencial_Estimado", color="Clasificacion", hover_name="Cliente",
            text="Cliente", size_max=40, height=400
        )
        fig_scatter.update_traces(textposition='top center')
        st.plotly_chart(fig_scatter, use_container_width=True)

    # --- TABS DE GESTIÓN TÁCTICA ---
    tab_rutero, tab_obras, tab_industrias = st.tabs([
        "📅 Rutero Georreferenciado (IA)", 
        "🏗️ Estudio Obras (VIS/No VIS)", 
        "🏭 Mantenimiento Industrial"
    ])

    with tab_rutero:
        st.markdown("### Ruta Optimizada de Visitas")
        st.markdown("El algoritmo agrupó a los clientes por cercanía geográfica para maximizar el tiempo de los asesores en la calle.")
        st.dataframe(df_rutero, use_container_width=True, hide_index=True)

    with tab_obras:
        st.markdown("### Proyectos Constructivos (Manizales, Villamaría, Neira)")
        st.caption("Estrategia: Volumen en VIS/VIP. Especificación y Margen en No VIS.")
        df_cons = df[df['Tipo'].str.contains('Construcción|Salud')]
        
        for _, row in df_cons.iterrows():
            with st.container():
                cols = st.columns([1, 3, 2, 2])
                
                # Renderizado de Badge HTML
                color = "badge-vis" if row['Clasificacion']=="VIS" else "badge-vip" if row['Clasificacion']=="VIP" else "badge-novis"
                cols[0].markdown(f"<span class='{color}'>{row['Clasificacion']}</span>", unsafe_allow_html=True)
                
                cols[1].markdown(f"**{row['Cliente']}**<br><small>{row['Proyecto']} | {row['Ubicación']}</small>", unsafe_allow_html=True)
                cols[2].markdown(f"**Urgencia:** {row['Prioridad_Venta']}<br><small>Etapa: {row['Estado']}</small>", unsafe_allow_html=True)
                cols[3].metric("Valor Esperado", f"${row['Valor_Esperado']:,.0f}")
                st.divider()

    with tab_industrias:
        st.markdown("### Industrias Base (Flujo de Caja Mensual)")
        st.caption("Foco exclusivo en: Lijas, Discos de corte, Epóxicos y Demarcación.")
        df_ind = df[df['Clasificacion'] == 'Industrial']
        st.dataframe(
            df_ind[['Cliente', 'Ubicación', 'Tamano', 'Foco_Venta', 'Potencial_Estimado']], 
            use_container_width=True, hide_index=True
        )

    # --- EXPORTACIÓN ---
    st.markdown("---")
    st.subheader("📥 Exportación de Reportes")
    st.markdown("Descarga el estudio completo con todas las métricas, ponderaciones de probabilidad y el rutero geolocalizado.")
    
    excel_data = exportar_inteligencia_excel(df, df_rutero)
    st.download_button(
        label="💾 Descargar Estudio Eje Cafetero 2026 (Excel)",
        data=excel_data,
        file_name="Estudio_Mercado_Manizales_2026.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )