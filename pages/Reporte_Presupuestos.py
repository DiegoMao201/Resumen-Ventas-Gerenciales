# ==============================================================================
# ARCHIVO: pages/Reporte_Presupuestos.py
# DESCRIPCIÓN: Generador de Acuerdos de Gestión Comercial (PDF Profesional)
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
import datetime
import io
import utils_presupuesto
import dropbox

# --- CONFIGURACIÓN ---
APP_CONFIG = {
    "url_logo": "https://raw.githubusercontent.com/DiegoMao2021/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png",
    "dropbox_path_ventas": "/data/ventas_detalle.csv",
    "column_names_ventas": ['anio', 'mes', 'fecha_venta', 'Serie', 'TipoDocumento', 'codigo_vendedor', 'nomvendedor', 'cliente_id', 'nombre_cliente', 'codigo_articulo', 'nombre_articulo', 'categoria_producto', 'linea_producto', 'marca_producto', 'valor_venta', 'unidades_vendidas', 'costo_unitario', 'super_categoria'],
    "grupos_vendedores": {"MOSTRADOR PEREIRA": ["ALEJANDRO CARBALLO MARQUEZ", "GEORGINA A. GALVIS HERRERA"], "MOSTRADOR ARMENIA": ["CRISTIAN CAMILO RENDON MONTES", "FANDRY JOHANA ABRIL PENHA", "JAVIER ORLANDO PATINO HURTADO"], "MOSTRADOR MANIZALES": ["DAVID FELIPE MARTINEZ RIOS", "JHON JAIRO CASTAÑO MONTES"], "MOSTRADOR LAURELES": ["MAURICIO RIOS MORALES"], "MOSTRADOR OPALO": ["MARIA PAULA DEL JESUS GALVIS HERRERA"]}
}

st.set_page_config(page_title="Generador de Acuerdos 2026", page_icon="📄", layout="centered")

# --- FUNCIONES DE CARGA DE DATOS (REUTILIZADAS) ---
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
        
        # Normalización de vendedores
        df['nomvendedor'] = df['nomvendedor'].apply(utils_presupuesto.normalizar_texto)
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

# --- CLASE PDF PROFESIONAL ---
class PDFReport(FPDF):
    def header(self):
        # Logo
        try:
            self.image(APP_CONFIG["url_logo"], 10, 8, 33)
        except:
            pass # Si falla el logo, no detiene el reporte
            
        # Título
        self.set_font('Helvetica', 'B', 15)
        self.set_text_color(30, 58, 138) # Azul Ferreinox
        self.cell(0, 10, 'ACUERDO DE GESTIÓN COMERCIAL 2026', 0, 1, 'R')
        
        # Subtítulo
        self.set_font('Helvetica', 'I', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'FERREINOX S.A.S. BIC', 0, 1, 'R')
        self.ln(15)
        
        # Línea divisoria
        self.set_draw_color(30, 58, 138)
        self.set_line_width(0.5)
        self.line(10, 30, 200, 30)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()} | Generado el {datetime.datetime.now().strftime("%d/%m/%Y")}', 0, 0, 'C')

    def chapter_title(self, label):
        self.set_font('Helvetica', 'B', 12)
        self.set_fill_color(230, 240, 255) # Azul muy claro
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, f'  {label}', 0, 1, 'L', 1)
        self.ln(4)

    def body_text(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5, text)
        self.ln()

# --- LÓGICA DE GENERACIÓN ---
def generar_pdf_presupuestos(df_mensual):
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- 1. RESUMEN EJECUTIVO (PRIMERA PÁGINA) ---
    pdf.add_page()
    pdf.chapter_title("RESUMEN EJECUTIVO DE METAS 2026")
    
    # Tabla Resumen
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(100, 8, 'Vendedor / Grupo', 1, 0, 'C', 1)
    pdf.cell(50, 8, 'Meta Anual Total', 1, 1, 'C', 1)
    
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(0, 0, 0)
    
    # Agrupar para el resumen
    df_resumen = df_mensual.groupby("nomvendedor")['presupuesto_mensual'].sum().reset_index()
    df_resumen = df_resumen.sort_values('presupuesto_mensual', ascending=False)
    
    total_compania = 0
    for index, row in df_resumen.iterrows():
        nombre = row['nomvendedor']
        valor = row['presupuesto_mensual']
        total_compania += valor
        
        pdf.cell(100, 7, f" {nombre}", 1)
        pdf.cell(50, 7, f"$ {valor:,.0f}", 1, 1, 'R')
        
    # Total Final
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(100, 8, 'TOTAL COMPAÑÍA 2026', 1)
    pdf.cell(50, 8, f"$ {total_compania:,.0f}", 1, 1, 'R')
    
    # --- 2. HOJAS INDIVIDUALES ---
    vendedores_unicos = df_mensual['nomvendedor'].unique()
    
    for vendedor in vendedores_unicos:
        pdf.add_page()
        
        # Datos del vendedor
        df_v = df_mensual[df_mensual['nomvendedor'] == vendedor].sort_values('mes')
        total_vendedor = df_v['presupuesto_mensual'].sum()
        
        # Título Personalizado
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(0, 10, f"META ASIGNADA: {vendedor}", 0, 1, 'C')
        pdf.ln(5)
        
        # Texto Motivacional y Explicativo
        intro_text = (
            "El 2026 se perfila como un año decisivo para la consolidación y expansión de FERREINOX SAS BIC. "
            "Hemos diseñado este presupuesto basándonos en un análisis riguroso de su histórico de ventas, "
            "la estacionalidad del mercado y el potencial de crecimiento de su zona/segmento.\n\n"
            "REGLAS DE ASIGNACIÓN:\n"
            "1. Crecimiento Sostenible: Las metas incluyen un factor de crecimiento retador pero alcanzable.\n"
            "2. Estacionalidad: Se respeta el comportamiento histórico de los meses de mayor demanda.\n"
            "3. Compromiso: El cumplimiento de esta meta es vital para los objetivos estratégicos de la compañía.\n\n"
            "Su rol es fundamental. Más que números, buscamos su liderazgo, su capacidad de negociación y su "
            "compromiso con la excelencia en el servicio."
        )
        pdf.body_text(intro_text)
        pdf.ln(5)
        
        # Tabla Mensual
        pdf.chapter_title("DETALLE MENSUAL DE PRESUPUESTO")
        
        # Encabezados tabla
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_fill_color(30, 58, 138)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(30, 8, 'MES', 1, 0, 'C', 1)
        pdf.cell(50, 8, 'META DE VENTA', 1, 0, 'C', 1)
        pdf.cell(50, 8, '% ANUAL', 1, 1, 'C', 1)
        
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(0, 0, 0)
        
        mapeo_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        for index, row in df_v.iterrows():
            mes_nombre = mapeo_meses.get(row['mes'], str(row['mes']))
            valor = row['presupuesto_mensual']
            pct = (valor / total_vendedor * 100) if total_vendedor > 0 else 0
            
            pdf.cell(30, 7, mes_nombre, 1, 0, 'C')
            pdf.cell(50, 7, f"$ {valor:,.0f}", 1, 0, 'R')
            pdf.cell(50, 7, f"{pct:.1f}%", 1, 1, 'C')
            
        # Total Tabla
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(30, 8, 'TOTAL 2026', 1, 0, 'C', 1)
        pdf.cell(50, 8, f"$ {total_vendedor:,.0f}", 1, 0, 'R', 1)
        pdf.cell(50, 8, '100%', 1, 1, 'C', 1)
        
        pdf.ln(25)
        
        # Sección de Firmas
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 5, "En señal de conocimiento y compromiso:", 0, 1, 'L')
        pdf.ln(20)
        
        y_pos = pdf.get_y()
        
        # Línea Vendedor
        pdf.line(20, y_pos, 80, y_pos)
        pdf.text(20, y_pos + 5, "Firma del Asesor / Responsable")
        pdf.text(20, y_pos + 10, f"{vendedor}")
        
        # Línea Gerencia
        pdf.line(110, y_pos, 170, y_pos)
        pdf.text(110, y_pos + 5, "Firma Gerencia General")
        pdf.text(110, y_pos + 10, "FERREINOX SAS BIC")

    return pdf.output(dest='S')
    if isinstance(pdf_data, str):
        return pdf_data.encode('latin-1')
    return pdf_data

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
            st.error("No hay datos históricos disponibles.")
            return

        # 2. Calcular Presupuesto (Usando tu UTILS completo)
        # Paso A: Totales para proyección
        total_2024 = df_historico[df_historico['anio'] == 2024]['valor_venta'].sum()
        total_2025 = df_historico[df_historico['anio'] == 2025]['valor_venta'].sum()
        
        # Paso B: Proyección 2026
        target_2026, tasa = utils_presupuesto.proyectar_total_2026(total_2024, total_2025)
        
        # Paso C: Asignación Anual (Aquí se aplican las reglas de Leduyn, Jerson, etc.)
        df_anual = utils_presupuesto.asignar_presupuesto(df_historico, APP_CONFIG['grupos_vendedores'], target_2026)
        
        # Paso D: Distribución Mensual (Aquí se aplican las reglas mensuales como Opalo)
        df_mensual_final = utils_presupuesto.distribuir_presupuesto_mensual(df_anual, df_historico)

    # 3. Mostrar Previsualización
    st.success("✅ Cálculos realizados exitosamente.")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Vista Previa (Tabla Resumen)")
        st.dataframe(
            df_mensual_final.groupby('nomvendedor')['presupuesto_mensual'].sum().reset_index().sort_values('presupuesto_mensual', ascending=False),
            column_config={"presupuesto_mensual": st.column_config.NumberColumn("Meta 2026", format="$ %d")},
            use_container_width=True,
            hide_index=True
        )
    
    with col2:
        st.subheader("Descargar Documento")
        st.info("El PDF incluye una hoja por vendedor lista para imprimir y firmar.")
        
        if st.button("Generar PDF Oficial", type="primary"):
            with st.spinner("Maquetando documento de alta calidad..."):
                pdf_bytes = generar_pdf_presupuestos(df_mensual_final)
                
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