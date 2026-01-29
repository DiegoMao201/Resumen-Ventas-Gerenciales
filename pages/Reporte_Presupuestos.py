# ==============================================================================
# ARCHIVO: pages/Reporte_Presupuestos.py
# DESCRIPCIÓN: Generador de Acuerdos de Gestión Comercial 2026 (PDF Enterprise)
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
import datetime
import io
import dropbox
import utils_presupuesto  # Asegúrate de que este archivo exista en tu carpeta

# --- CONFIGURACIÓN ESTÉTICA ---
COLOR_PRIMARY = (30, 58, 138)       # Azul Corporativo (Navy)
COLOR_SECONDARY = (241, 245, 249)   # Gris muy claro para fondos
COLOR_ACCENT = (220, 38, 38)        # Rojo sutil para énfasis
COLOR_TEXT_HEADER = (255, 255, 255) # Blanco
COLOR_TEXT_BODY = (51, 65, 85)      # Gris Oscuro (Slate)

APP_CONFIG = {
    "url_logo": "https://raw.githubusercontent.com/DiegoMao2021/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png",
    "dropbox_path_ventas": "/data/ventas_detalle.csv",
    "column_names_ventas": ['anio', 'mes', 'fecha_venta', 'Serie', 'TipoDocumento', 'codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_cliente', 'codigo_articulo', 'nombre_articulo', 'categoria_producto', 'linea_producto', 'marca_producto', 'valor_venta', 'unidades_vendidas', 'costo_unitario', 'super_categoria'],
    "grupos_vendedores": {
        "MOSTRADOR PEREIRA": ["ALEJANDRO CARBALLO MARQUEZ", "GEORGINA A. GALVIS HERRERA"], 
        "MOSTRADOR ARMENIA": ["CRISTIAN CAMILO RENDON MONTES", "FANDRY JOHANA ABRIL PENHA", "JAVIER ORLANDO PATINO HURTADO"], 
        "MOSTRADOR MANIZALES": ["DAVID FELIPE MARTINEZ RIOS", "JHON JAIRO CASTAÑO MONTES"], 
        "MOSTRADOR LAURELES": ["MAURICIO RIOS MORALES"], 
        "MOSTRADOR OPALO": ["MARIA PAULA DEL JESUS GALVIS HERRERA"]
    }
}

VENDEDORES_EXCLUIR = [
    "CRISTIAN CAMILO RENDON MONTES",
    "DIEGO MAURICIO GARCIA RENGIFO",
    "CAMILO AGUDELO MARIN",
    "RICHARD RAFAEL FERRER ROZO",
    "PABLO ANDRES CASTANO MONTES",
    "CONTABILIDAD FERREINOX"
]
VENDEDORES_EXCLUIR_NORM = [utils_presupuesto.normalizar_texto(v) for v in VENDEDORES_EXCLUIR]

st.set_page_config(page_title="Generador de Acuerdos 2026", page_icon="📄", layout="centered")

# --- FUNCIONES DE CARGA DE DATOS ---
@st.cache_resource
def get_dropbox_client():
    return dropbox.Dropbox(
        app_key=st.secrets.dropbox.app_key,
        app_secret=st.secrets.dropbox.app_secret,
        oauth2_refresh_token=st.secrets.dropbox.refresh_token
    )

@st.cache_data(ttl=3600)
def cargar_datos_base():
    try:
        dbx = get_dropbox_client()
        _, res = dbx.files_download(path=APP_CONFIG["dropbox_path_ventas"])
        df = pd.read_csv(io.StringIO(res.content.decode('latin-1')), header=None, sep='|', engine='python', quoting=3)
        df.columns = APP_CONFIG["column_names_ventas"]
        df['valor_venta'] = pd.to_numeric(df['valor_venta'], errors='coerce').fillna(0)
        df['anio'] = pd.to_numeric(df['anio'], errors='coerce').fillna(0).astype(int)
        df['mes'] = pd.to_numeric(df['mes'], errors='coerce').fillna(0).astype(int)
        df['nomvendedor'] = df['nomvendedor'].apply(utils_presupuesto.normalizar_texto)
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

# --- CLASE PDF PROFESIONAL ENTERPRISE ---
class EnterpriseReport(FPDF):
    def header(self):
        # Franja superior de color
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, 0, 210, 25, 'F')
        
        # Logo (sobre fondo blanco o superpuesto)
        try:
            # Dibujar un cuadro blanco pequeño para el logo si es necesario
            self.set_fill_color(255, 255, 255)
            self.rect(10, 5, 40, 15, 'F')
            self.image(APP_CONFIG["url_logo"], 12, 6, 36)
        except:
            pass
            
        # Título del documento en el Header
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(255, 255, 255)
        self.set_xy(0, 8)
        self.cell(200, 5, 'ACUERDO DE GESTIÓN COMERCIAL 2026', 0, 1, 'R')
        self.set_font('Helvetica', '', 8)
        self.cell(200, 5, 'CONFIDENCIAL - USO INTERNO EXCLUSIVO', 0, 1, 'R')
        self.ln(20)

    def footer(self):
        self.set_y(-20)
        # Línea divisoria elegante
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        
        # Texto pie de página
        self.set_y(-15)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(128, 128, 128)
        
        col1 = 'FERREINOX S.A.S. BIC'
        col2 = f'Generado el: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}'
        col3 = f'Página {self.page_no()}'
        
        self.cell(60, 10, col1, 0, 0, 'L')
        self.cell(70, 10, col2, 0, 0, 'C')
        self.cell(60, 10, col3, 0, 0, 'R')

    def draw_cover_page(self, total_compania):
        self.add_page()
        # Fondo superior azul
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, 0, 210, 60, 'F')
        # Logo centrado arriba
        try:
            self.image(APP_CONFIG["url_logo"], x=80, y=10, w=50)
        except:
            pass
        # Título principal
        self.set_xy(0, 65)
        self.set_text_color(*COLOR_PRIMARY)
        self.set_font('Helvetica', 'B', 22)
        self.cell(0, 12, 'PLAN ESTRATÉGICO DE VENTAS 2026', 0, 1, 'C')
        self.ln(2)
        self.set_font('Helvetica', '', 14)
        self.cell(0, 10, 'DOCUMENTO OFICIAL DE ASIGNACIÓN DE METAS', 0, 1, 'C')
        self.ln(10)
        # Tarjeta central con meta global
        self.set_fill_color(255, 255, 255)
        self.rect(40, 100, 130, 55, 'DF')
        self.set_xy(40, 110)
        self.set_text_color(*COLOR_PRIMARY)
        self.set_font('Helvetica', 'B', 13)
        self.cell(130, 8, 'META GLOBAL FERREINOX S.A.S. BIC', 0, 2, 'C')
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(*COLOR_ACCENT) # Rojo/Naranja
        self.cell(130, 14, f"$ {total_compania:,.0f}", 0, 2, 'C')
        self.set_font('Helvetica', 'I', 10)
        self.set_text_color(100, 100, 100)
        self.cell(130, 8, 'Moneda: COP', 0, 2, 'C')
        self.set_y(-40)
        self.set_text_color(*COLOR_PRIMARY)
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'FERREINOX S.A.S. BIC', 0, 1, 'C')

    def section_title(self, title):
        self.ln(5)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(0, 10, title.upper(), 0, 1, 'L')
        # Subrayado grueso
        self.set_draw_color(*COLOR_PRIMARY)
        self.set_line_width(1)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def draw_kpi_card(self, x, y, w, h, title, value, subtitle):
        # Sombra simple (gris)
        self.set_fill_color(220, 220, 220)
        self.rect(x+1, y+1, w, h, 'F')
        # Fondo blanco
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.2)
        self.rect(x, y, w, h, 'DF')
        
        # Texto
        self.set_xy(x, y+2)
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(100, 100, 100)
        self.cell(w, 5, title, 0, 1, 'C')
        
        self.set_xy(x, y+10)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(w, 8, value, 0, 1, 'C')
        
        self.set_xy(x, y+20)
        self.set_font('Helvetica', '', 7)
        self.set_text_color(128, 128, 128)
        self.cell(w, 4, subtitle, 0, 1, 'C')

    def table_header(self, headers, widths):
        self.set_font('Helvetica', 'B', 9)
        self.set_fill_color(*COLOR_PRIMARY)
        self.set_text_color(255, 255, 255)
        for h, w in zip(headers, widths):
            self.cell(w, 10, h, 0, 0, 'C', 1)
        self.ln()

    def table_row(self, data, widths, fill=False):
        self.set_font('Helvetica', '', 9)
        self.set_text_color(50, 50, 50)
        if fill:
            self.set_fill_color(245, 247, 250) # Zebra muy sutil
        else:
            self.set_fill_color(255, 255, 255)
            
        for i, (datum, w) in enumerate(zip(data, widths)):
            align = 'L' if i == 0 else 'R' # Primer columna izq, resto derecha
            if i == 2: align = 'C' # Centrar porcentajes
            self.cell(w, 8, str(datum), 0, 0, align, 1)
        self.ln()

# --- LÓGICA DE GENERACIÓN ---
def generar_pdf_presupuestos(df_mensual_unificado):
    pdf = EnterpriseReport()
    pdf.set_auto_page_break(auto=True, margin=20)

    # --- PORTADA Y RESUMEN EJECUTIVO ---
    total_compania = df_mensual_unificado['presupuesto_mensual'].sum()
    pdf.draw_cover_page(total_compania)
    pdf.add_page()
    pdf.section_title("Resumen Ejecutivo de Asignación")
    pdf.set_font('Helvetica', '', 10)
    pdf.multi_cell(0, 5, "El siguiente resumen presenta la distribución estratégica de metas para el año fiscal 2026. Los valores han sido calculados considerando históricos de venta, estacionalidad y objetivos de crecimiento corporativo.")
    pdf.ln(10)

    # --- TABLA RESUMEN ---
    resumen = (
        df_mensual_unificado.groupby('vendedor_unificado')['presupuesto_mensual']
        .sum()
        .reset_index()
        .sort_values('presupuesto_mensual', ascending=False)
    )
    widths = [110, 50, 30]
    pdf.table_header(['Vendedor / Grupo', 'Meta Anual ($)', '% Part.'], widths)
    fill = False
    for _, row in resumen.iterrows():
        nombre = row['vendedor_unificado']
        valor = row['presupuesto_mensual']
        participacion = (valor / total_compania * 100) if total_compania > 0 else 0
        pdf.table_row([
            f"  {nombre}",
            f"$ {valor:,.0f}",
            f"{participacion:.1f}%"
        ], widths, fill)
        fill = not fill
    pdf.ln(2)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(110, 10, '  TOTAL GENERAL', 0, 0, 'L', 1)
    pdf.cell(50, 10, f"$ {total_compania:,.0f}", 0, 0, 'R', 1)
    pdf.cell(30, 10, '100.0%', 0, 1, 'C', 1)

    # --- PÁGINAS INDIVIDUALES/GROUPS ---
    mapeo_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    for nombre in resumen['vendedor_unificado']:
        df_v = df_mensual_unificado[df_mensual_unificado['vendedor_unificado'] == nombre].sort_values('mes')
        total_vendedor = df_v['presupuesto_mensual'].sum()
        pdf.add_page()
        pdf.section_title(f"META INDIVIDUAL: {nombre}")
        # KPIs
        y_start = pdf.get_y()
        pdf.kpi_card("META ANUAL 2026", f"$ {total_vendedor:,.0f}", "Presupuesto Total Asignado", x=15, y=y_start, w=60, h=28)
        pdf.kpi_card("PROMEDIO MENSUAL", f"$ {total_vendedor/12:,.0f}", "Base de cumplimiento", x=80, y=y_start, w=60, h=28)
        pdf.kpi_card("META PRIMER TRIMESTRE", f"$ {df_v[df_v['mes']<=3]['presupuesto_mensual'].sum():,.0f}", "Ene - Feb - Mar", x=145, y=y_start, w=60, h=28)
        pdf.set_y(y_start + 35)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(70, 70, 70)
        pdf.cell(0, 7, "OBJETIVOS Y COMPROMISO", 0, 1)
        pdf.set_font('Helvetica', '', 10)
        intro_text = (
            "El presente acuerdo establece las metas comerciales para el periodo 2026. "
            "Este presupuesto ha sido diseñado para impulsar un crecimiento sostenible, respetando la estacionalidad "
            "histórica de su zona/segmento. El cumplimiento de estas cifras es fundamental para garantizar "
            "la viabilidad financiera y operativa de FERREINOX S.A.S. BIC."
        )
        pdf.multi_cell(0, 5, intro_text)
        pdf.ln(8)
        # Tabla Mensual
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 6, "DETALLE DE EJECUCIÓN MENSUAL", 0, 1)
        widths_ind = [50, 60, 40, 40]
        pdf.table_header(['MES', 'META DE VENTA', '% ANUAL', 'ACUMULADO'], widths_ind)
        acumulado = 0
        fill = False
        for _, row in df_v.iterrows():
            mes_nombre = mapeo_meses.get(row['mes'], str(row['mes']))
            valor = row['presupuesto_mensual']
            acumulado += valor
            pct = (valor / total_vendedor * 100) if total_vendedor > 0 else 0
            pdf.table_row([
                f"  {mes_nombre}",
                f"$ {valor:,.0f}",
                f"{pct:.1f}%",
                f"$ {acumulado:,.0f}"
            ], widths_ind, fill)
            fill = not fill
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_fill_color(30, 58, 138)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(50, 10, '  TOTAL 2026', 0, 0, 'L', 1)
        pdf.cell(60, 10, f"$ {total_vendedor:,.0f}", 0, 0, 'R', 1)
        pdf.cell(80, 10, '', 0, 1, 'C', 1)
        # Firmas compactas
        pdf.ln(6)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Helvetica', '', 9)
        pdf.cell(0, 5, "Se firma en constancia de aceptación y compromiso:", 0, 1, 'L')
        pdf.ln(4)
        y_firma = pdf.get_y()
        pdf.set_draw_color(100, 100, 100)
        pdf.line(20, y_firma, 90, y_firma)
        pdf.set_xy(20, y_firma + 2)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(70, 5, str(nombre).upper(), 0, 1, 'C')
        pdf.set_x(20)
        pdf.set_font('Helvetica', '', 8)
        pdf.cell(70, 4, "Asesor / Responsable Comercial", 0, 1, 'C')
        pdf.line(120, y_firma, 190, y_firma)
        pdf.set_xy(120, y_firma + 2)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(70, 5, "GERENCIA COMERCIAL", 0, 1, 'C')
        pdf.set_x(120)
        pdf.set_font('Helvetica', '', 8)
        pdf.cell(70, 4, "Aprobación Gerencial", 0, 1, 'C')

    # --- OUTPUT PDF ---
    pdf_bytes = pdf.output(dest='S')
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode('latin-1')
    elif isinstance(pdf_bytes, bytearray):
        pdf_bytes = bytes(pdf_bytes)
    return pdf_bytes

# --- INTERFAZ STREAMLIT ---
def main():
    if 'autenticado' not in st.session_state or not st.session_state.autenticado:
        st.warning("⚠️ Acceso Restringido. Por favor inicie sesión en la página principal.")
        st.stop()

    st.title("🖨️ Centro de Impresión de Metas 2026")
    st.markdown("Generación de documentos oficiales para firma y legalización de presupuestos.")
    
    # 1. Cargar Datos
    with st.spinner("Cargando histórico y calculando presupuestos inteligentes..."):
        df_historico = cargar_datos_base()
        
        if df_historico.empty:
            st.error("No hay datos históricos disponibles o error en conexión Dropbox.")
            return

        # 2. Calcular Presupuesto
        try:
            # Paso A: Totales para proyección
            total_2024 = df_historico[df_historico['anio'] == 2024]['valor_venta'].sum()
            total_2025 = df_historico[df_historico['anio'] == 2025]['valor_venta'].sum()
            
            # Paso B: Proyección 2026 (Usando utils)
            target_2026, tasa = utils_presupuesto.proyectar_total_2026(total_2024, total_2025)
            
            # Paso C: Asignación Anual
            df_anual = utils_presupuesto.asignar_presupuesto(df_historico, APP_CONFIG['grupos_vendedores'], target_2026)
            
            # Paso D: Distribución Mensual
            df_mensual = utils_presupuesto.distribuir_presupuesto_mensual(df_anual, df_historico)
        
        except Exception as e:
            st.error(f"Error en la lógica de cálculo de presupuestos: {e}")
            st.info("Verifique que 'utils_presupuesto.py' tenga las funciones requeridas.")
            return

    # 3. Mostrar Previsualización
    st.success("✅ Cálculos realizados exitosamente.")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Vista Previa (Resumen)")
        st.dataframe(
            df_mensual_unificado.pivot_table(index="vendedor_unificado", columns="mes", values="presupuesto_mensual", aggfunc="sum").fillna(0),
            use_container_width=True
        )
    
    with col2:
        st.subheader("Descargar Documento")
        st.info("Generar PDF Enterprise con portadas, indicadores y formato contractual.")
        
        if st.button("Generar PDF Oficial", type="primary"):
            with st.spinner("Diseñando documento de alta calidad..."):
                # Generamos los bytes del PDF
                pdf_bytes = generar_pdf_presupuestos(df_mensual_unificado)
                
                # Botón de descarga anidado para aparecer tras la generación
                st.download_button(
                    label="📥 Descargar Acuerdo_Presupuestal_2026.pdf",
                    data=pdf_bytes,
                    file_name="Acuerdo_Presupuestal_2026_Ferreinox.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.balloons()

if __name__ == "__main__":
    main()