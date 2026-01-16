"""Configuración centralizada del módulo de análisis estratégico"""
from dataclasses import dataclass, field
from typing import Dict
import streamlit as st

@dataclass
class FerreinoxColors:
    """Paleta de colores corporativos"""
    PRIMARY: str = "#1e40af"
    SECONDARY: str = "#7c3aed"
    SUCCESS: str = "#10b981"
    WARNING: str = "#f59e0b"
    DANGER: str = "#ef4444"
    INFO: str = "#3b82f6"

@dataclass
class AppConfig:
    """Configuración centralizada de la aplicación"""
    PAGE_TITLE: str = "Análisis Estratégico | Ferreinox"
    PAGE_ICON: str = "📊"
    LAYOUT: str = "wide"
    CACHE_TTL: int = 3600
    
    LOGO_URL: str = "https://raw.githubusercontent.com/DiegoMao2021/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png"
    WEBSITE_URL: str = "https://www.ferreinox.co"
    
    MAPEO_MARCAS: Dict[int, str] = field(default_factory=lambda: {
        50: "P8-ASC-MEGA", 54: "MPY-International", 55: "DPP-AN Colorantes Latam",
        56: "DPP-Pintuco Profesional", 57: "ASC-Mega", 58: "DPP-Pintuco",
        61: "S-M Sika", 65: "HPG-Habro Pack", 66: "ASI-Anypsa Internacional",
        67: "ASC-Anypsa", 68: "ASI-Anypsa", 69: "MPY-Master Pro",
        73: "C&D-Corona", 74: "WEG-Weg", 75: "GEN-Generico",
        76: "LAM-Lamosa", 77: "ABR-Abrasivos", 78: "HER-Herramientas",
        79: "FER-Ferreteria", 80: "SEG-Seguridad", 81: "ELE-Electricos",
        82: "TUB-Tuberia", 83: "PEG-Pegantes", 84: "IMP-Impermeabilizantes",
        85: "DEC-Decoracion"
    })
    
    CATEGORIAS_MARCA: Dict[str, str] = field(default_factory=lambda: {
        "P8": "Pinturas Premium", "MPY": "Pinturas Master", "DPP": "Pinturas Profesional",
        "ASC": "Complementos", "S": "Sika", "HPG": "Empaque",
        "ASI": "Internacional", "C&D": "Acabados", "WEG": "Electricos",
        "GEN": "Genericos", "LAM": "Ceramica", "ABR": "Abrasivos",
        "HER": "Herramientas", "FER": "Ferreteria", "SEG": "Seguridad",
        "ELE": "Electricos", "TUB": "Tuberia", "PEG": "Pegantes",
        "IMP": "Impermeabilizantes", "DEC": "Decoracion"
    })
    
    COLUMNAS_MAESTRAS: Dict[int, str] = field(default_factory=lambda: {
        0: 'anio', 1: 'mes', 2: 'dia', 7: 'COD', 8: 'CLIENTE',
        10: 'NOMBRE_PRODUCTO_K', 11: 'CATEGORIA_L', 
        13: 'CODIGO_MARCA_N', 14: 'VALOR'
    })

def configurar_pagina():
    """Configura página con estilos corporativos Ferreinox"""
    config = AppConfig()
    colors = FerreinoxColors()
    
    st.set_page_config(
        page_title=config.PAGE_TITLE,
        page_icon=config.PAGE_ICON,
        layout=config.LAYOUT,
        initial_sidebar_state="expanded"
    )
    
    st.markdown(f"""
    <style>
        .encabezado-estrategico {{
            background: linear-gradient(135deg, {colors.PRIMARY}, {colors.SECONDARY});
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .encabezado-estrategico h1 {{
            color: white;
            margin: 0;
            font-size: 2.5rem;
        }}
        
        .metrica-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            border-left: 4px solid {colors.PRIMARY};
        }}
        
        .stTabs [aria-selected="true"] {{
            background: linear-gradient(135deg, {colors.PRIMARY}, {colors.SECONDARY}) !important;
            color: white !important;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="encabezado-estrategico">
        <h1>📊 Análisis Estratégico de Crecimiento</h1>
        <p style="color: white; margin: 0;">Ferreinox S.A.S. BIC | <a href="{config.WEBSITE_URL}" target="_blank" style="color: white;">www.ferreinox.co</a></p>
    </div>
    """, unsafe_allow_html=True)