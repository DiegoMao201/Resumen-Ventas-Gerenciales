"""Configuración centralizada del módulo de análisis estratégico"""
from dataclasses import dataclass, field
from typing import Dict, List
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
    
    # ✅ LÍNEAS ESTRATÉGICAS REALES DEL NEGOCIO
    LINEAS_ESTRATEGICAS: List[str] = field(default_factory=lambda: [
        'ABRACOL', 'YALE', 'GOYA', 'DELTA', 'SAINT GOBAIN', 
        'ALLEGION', 'ARTECOLA', 'INDUMA', 'ATLAS', 'SEGUREX',
        'PINTUCO'
    ])

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
        
        .insight-box {{
            background: linear-gradient(135deg, #f8fafc, #e0e7ff);
            padding: 1.5rem;
            border-radius: 10px;
            border-left: 5px solid {colors.SUCCESS};
            margin: 1rem 0;
        }}
        
        .warning-box {{
            background: linear-gradient(135deg, #fef3c7, #fde68a);
            padding: 1.5rem;
            border-radius: 10px;
            border-left: 5px solid {colors.WARNING};
            margin: 1rem 0;
        }}
        
        .stTabs [aria-selected="true"] {{
            background: linear-gradient(135deg, {colors.PRIMARY}, {colors.SECONDARY}) !important;
            color: white !important;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="encabezado-estrategico">
        <h1>📊 Análisis Estratégico Ejecutivo</h1>
        <p style="color: white; margin: 0;">Ferreinox S.A.S. BIC | <a href="{config.WEBSITE_URL}" target="_blank" style="color: white;">www.ferreinox.co</a></p>
    </div>
    """, unsafe_allow_html=True)