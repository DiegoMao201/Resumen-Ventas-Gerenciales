"""Configuración centralizada y estilos corporativos"""
from dataclasses import dataclass, field
from typing import Dict
import streamlit as st

@dataclass(frozen=True)
class FerreinoxColors:
    """Paleta de colores corporativos Ferreinox"""
    PRIMARY: str = "#1e3a8a"
    SECONDARY: str = "#3b82f6"
    ACCENT: str = "#f59e0b"
    SUCCESS: str = "#10b981"
    ERROR: str = "#ef4444"
    GRAY: str = "#64748b"
    GRAY_LIGHT: str = "#f8fafc"

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
        59: "DPP-Madetec", 60: "POW-Interpon", 61: "Varios", 62: "DPP-ICO",
        63: "DPP-Terinsa", 64: "MPY-Pintuco", 65: "Terceros No-AN",
        66: "ICO-AN Empaques", 67: "ASC-Automotriz", 68: "POW-Resicoat",
        73: "DPP-Coral", 91: "DPP-Sikkens"
    })
    
    CATEGORIAS_MARCA: Dict[str, str] = field(default_factory=lambda: {
        "DPP": "Pinturas Decorativas",
        "POW": "Recubrimientos en Polvo",
        "ASC": "Automotriz",
        "MPY": "Empaques Marítimos"
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
        :root {{
            --ferreinox-primary: {colors.PRIMARY};
            --ferreinox-secondary: {colors.SECONDARY};
            --ferreinox-accent: {colors.ACCENT};
        }}
        
        .encabezado-estrategico {{
            background: linear-gradient(135deg, {colors.PRIMARY}, {colors.SECONDARY});
            padding: 2.5rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            box-shadow: 0 10px 40px rgba(30, 58, 138, 0.3);
            text-align: center;
        }}
        
        .encabezado-estrategico h1 {{
            color: white;
            font-size: 2.8rem;
            font-weight: 900;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }}
        
        .metric-card {{
            background: linear-gradient(145deg, #ffffff, {colors.GRAY_LIGHT});
            border-left: 4px solid {colors.ACCENT};
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background-color: {colors.GRAY_LIGHT};
            padding: 0.5rem;
            border-radius: 10px;
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