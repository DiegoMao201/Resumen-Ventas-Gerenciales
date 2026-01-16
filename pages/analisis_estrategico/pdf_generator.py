"""Generador de reportes PDF empresariales avanzado - Ferreinox"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from io import BytesIO
import pandas as pd
from datetime import datetime
from typing import Dict, List

class EncabezadoPiePagina:
    """Clase para manejar encabezados y pies de página"""
    
    def __init__(self, titulo: str):
        self.titulo = titulo
    
    def en_primera_pagina(self, canvas, doc):
        """Encabezado especial para la primera página"""
        canvas.saveState()
        canvas.setFont('Helvetica-Bold', 16)
        canvas.setFillColorRGB(0.12, 0.23, 0.54)
        canvas.drawCentredString(doc.width/2 + 50, doc.height + 50, "FERREINOX S.A.S. BIC")
        canvas.restoreState()
    
    def en_paginas_posteriores(self, canvas, doc):
        """Encabezado y pie para páginas posteriores"""
        canvas.saveState()
        
        # Encabezado
        canvas.setFont('Helvetica', 9)
        canvas.setFillColorRGB(0.3, 0.3, 0.3)
        canvas.drawString(50, doc.height + 50, self.titulo)
        canvas.line(50, doc.height + 45, doc.width + 50, doc.height + 45)
        
        # Pie de página
        canvas.setFont('Helvetica', 8)
        canvas.setFillColorRGB(0.5, 0.5, 0.5)
        
        fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
        canvas.drawString(50, 30, f"Generado: {fecha_generacion}")
        
        pagina = f"Página {canvas.getPageNumber()}"
        canvas.drawRightString(doc.width + 50, 30, pagina)
        
        canvas.restoreState()


class GeneradorPDFFerreinox:
    """Generador profesional de PDFs para análisis estratégico"""
    
    def __init__(self, titulo: str = "Informe Estratégico de Crecimiento"):
        self.buffer = BytesIO()
        self.titulo = titulo
        self.elementos = []
        self.estilos = self._crear_estilos()
        self.colores = self._definir_paleta_colores()
    
    def _crear_estilos(self) -> Dict:
        """Define estilos personalizados para el documento"""
        estilos_base = getSampleStyleSheet()
        
        estilos_custom = {
            'titulo_principal': ParagraphStyle(
                'TituloPrincipal',
                parent=estilos_base['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1e3a8a'),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            ),
            'titulo_seccion': ParagraphStyle(
                'TituloSeccion',
                parent=estilos_base['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#3b82f6'),
                spaceAfter=12,
                spaceBefore=20,
                fontName='Helvetica-Bold'
            ),
            'subtitulo': ParagraphStyle(
                'Subtitulo',
                parent=estilos_base['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#64748b'),
                spaceAfter=20,
                alignment=TA_CENTER
            ),
            'texto_normal': ParagraphStyle(
                'TextoNormal',
                parent=estilos_base['Normal'],
                fontSize=10,
                textColor=colors.black,
                spaceAfter=10
            ),
            'texto_destacado': ParagraphStyle(
                'TextoDestacado',
                parent=estilos_base['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#1e3a8a'),
                fontName='Helvetica-Bold',
                spaceAfter=10
            )
        }
        
        return estilos_custom
    
    def _definir_paleta_colores(self) -> Dict:
        """Define paleta de colores corporativos"""
        return {
            'primary': colors.HexColor('#1e3a8a'),
            'secondary': colors.HexColor('#3b82f6'),
            'accent': colors.HexColor('#f59e0b'),
            'success': colors.HexColor('#10b981'),
            'error': colors.HexColor('#ef4444'),
            'gray': colors.HexColor('#64748b'),
            'gray_light': colors.HexColor('#f8fafc')
        }
    
    def agregar_portada(
        self, 
        anio_objetivo: int, 
        anio_base: int,
        empresa: str = "Ferreinox S.A.S. BIC"
    ):
        """Crea portada profesional"""
        
        # Título principal
        titulo = Paragraph(
            f"<b>{self.titulo}</b>",
            self.estilos['titulo_principal']
        )
        self.elementos.append(titulo)
        self.elementos.append(Spacer(1, 10))
        
        # Subtítulo con periodo
        subtitulo = Paragraph(
            f"Análisis Comparativo: {anio_base} vs {anio_objetivo}",
            self.estilos['subtitulo']
        )
        self.elementos.append(subtitulo)
        self.elementos.append(Spacer(1, 40))
        
        # Información de empresa
        info_empresa = Paragraph(
            f"<b>{empresa}</b><br/>Sistema de Inteligencia Comercial",
            self.estilos['texto_destacado']
        )
        self.elementos.append(info_empresa)
        self.elementos.append(Spacer(1, 10))
        
        # Fecha de generación
        fecha = datetime.now().strftime('%d de %B de %Y')
        fecha_gen = Paragraph(
            f"Generado el {fecha}",
            self.estilos['texto_normal']
        )
        self.elementos.append(fecha_gen)
        
        self.elementos.append(PageBreak())
    
    def agregar_resumen_ejecutivo(self, metricas: Dict):
        """Agrega resumen ejecutivo con métricas clave"""
        
        titulo = Paragraph(
            "📊 Resumen Ejecutivo",
            self.estilos['titulo_seccion']
        )
        self.elementos.append(titulo)
        self.elementos.append(Spacer(1, 12))
        
        datos_tabla = [
            ['Métrica', 'Valor', 'Variación'],
            [
                'Ventas Año Objetivo',
                f"${metricas['venta_actual']:,.0f}",
                f"{metricas['pct_variacion']:+.1f}%"
            ],
            [
                'Ventas Año Base',
                f"${metricas['venta_anterior']:,.0f}",
                '-'
            ],
            [
                'Diferencia Absoluta',
                f"${abs(metricas['diferencia']):,.0f}",
                'Crecimiento' if metricas['diferencia'] > 0 else 'Decrecimiento'
            ]
        ]
        
        tabla = Table(datos_tabla, colWidths=[3*inch, 2*inch, 1.5*inch])
        
        estilo_tabla = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colores['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.colores['gray_light']])
        ])
        
        tabla.setStyle(estilo_tabla)
        self.elementos.append(tabla)
        self.elementos.append(Spacer(1, 20))
    
    def agregar_analisis_marcas(self, df_marcas: pd.DataFrame):
        """Agrega análisis detallado por marca"""
        
        titulo = Paragraph(
            "🏷️ Análisis por Marca",
            self.estilos['titulo_seccion']
        )
        self.elementos.append(titulo)
        self.elementos.append(Spacer(1, 12))
        
        if df_marcas.empty:
            self.elementos.append(Paragraph(
                "No hay datos de marcas disponibles.",
                self.estilos['texto_normal']
            ))
            return
        
        df_marcas = df_marcas.head(10).reset_index()
        
        datos_tabla = [['Marca', 'Ventas', 'Participación']]
        
        total_ventas = df_marcas['Ventas'].sum()
        
        for _, row in df_marcas.iterrows():
            participacion = (row['Ventas'] / total_ventas * 100) if total_ventas > 0 else 0
            datos_tabla.append([
                row['Marca'],
                f"${row['Ventas']:,.0f}",
                f"{participacion:.1f}%"
            ])
        
        tabla = Table(datos_tabla, colWidths=[3*inch, 2*inch, 1.5*inch])
        
        estilo_tabla = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colores['secondary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.colores['gray_light']])
        ])
        
        tabla.setStyle(estilo_tabla)
        self.elementos.append(tabla)
        self.elementos.append(Spacer(1, 20))
    
    def agregar_top_clientes(self, df_clientes: pd.DataFrame, top_n: int = 20):
        """Agrega lista de top clientes"""
        
        titulo = Paragraph(
            f"👥 Top {top_n} Clientes",
            self.estilos['titulo_seccion']
        )
        self.elementos.append(titulo)
        self.elementos.append(Spacer(1, 12))
        
        if df_clientes.empty:
            self.elementos.append(Paragraph(
                "No hay datos de clientes disponibles.",
                self.estilos['texto_normal']
            ))
            return
        
        df_top = df_clientes.head(top_n).reset_index()
        
        datos_tabla = [['#', 'Cliente', 'Ventas']]
        
        for idx, row in enumerate(df_top.iterrows(), 1):
            datos_tabla.append([
                str(idx),
                row[1]['Cliente'][:40],
                f"${row[1]['Ventas']:,.0f}"
            ])
        
        tabla = Table(datos_tabla, colWidths=[0.5*inch, 4*inch, 2*inch])
        
        estilo_tabla = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colores['accent']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.colores['gray_light']])
        ])
        
        tabla.setStyle(estilo_tabla)
        self.elementos.append(tabla)
    
    def agregar_conclusiones(self, conclusiones: List[str]):
        """Agrega sección de conclusiones y recomendaciones"""
        
        titulo = Paragraph(
            "💡 Conclusiones y Recomendaciones",
            self.estilos['titulo_seccion']
        )
        self.elementos.append(titulo)
        self.elementos.append(Spacer(1, 12))
        
        for i, conclusion in enumerate(conclusiones, 1):
            texto = Paragraph(
                f"<b>{i}.</b> {conclusion}",
                self.estilos['texto_normal']
            )
            self.elementos.append(texto)
            self.elementos.append(Spacer(1, 8))
    
    def generar(self, config: Dict = None) -> bytes:
        """Genera el PDF y retorna bytes"""
        
        if config is None:
            config = {
                'pagesize': A4,
                'leftMargin': 50,
                'rightMargin': 50,
                'topMargin': 80,
                'bottomMargin': 60
            }
        
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=config.get('pagesize', A4),
            leftMargin=config.get('leftMargin', 50),
            rightMargin=config.get('rightMargin', 50),
            topMargin=config.get('topMargin', 80),
            bottomMargin=config.get('bottomMargin', 60)
        )
        
        encabezado = EncabezadoPiePagina(self.titulo)
        
        doc.build(
            self.elementos,
            onFirstPage=encabezado.en_primera_pagina,
            onLaterPages=encabezado.en_paginas_posteriores
        )
        
        self.buffer.seek(0)
        return self.buffer.getvalue()


def generar_reporte_completo(
    metricas_basicas: Dict,
    df_marcas: pd.DataFrame,
    df_clientes: pd.DataFrame,
    anio_objetivo: int,
    anio_base: int,
    conclusiones: List[str] = None
) -> bytes:
    """Genera un reporte PDF completo con todos los análisis"""
    
    generador = GeneradorPDFFerreinox("Análisis Estratégico de Crecimiento")
    
    # Portada
    generador.agregar_portada(
        anio_objetivo=anio_objetivo,
        anio_base=anio_base
    )
    
    # Resumen ejecutivo
    generador.agregar_resumen_ejecutivo(metricas_basicas)
    
    # Análisis por marca
    generador.agregar_analisis_marcas(df_marcas)
    
    # Top clientes
    generador.agregar_top_clientes(df_clientes, top_n=20)
    
    # Conclusiones
    if conclusiones:
        generador.agregar_conclusiones(conclusiones)
    
    return generador.generar()