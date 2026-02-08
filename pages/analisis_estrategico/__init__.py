"""
Módulo de Análisis Estratégico - Ferreinox S.A.S. BIC
Versión 2.0 - Arquitectura Modular
"""

from .config import AppConfig, FerreinoxColors, configurar_pagina
from .data_loader import cargar_y_validar_datos
from .ui_components import (
    renderizar_sidebar,
    aplicar_filtros,
    validar_datos_filtrados,
    tarjeta_metrica
)
from .processors import (
    TabADNCrecimiento,
    TabPortafolioMarcasCategorias,
    TabTopClientes,
    TabProductosEstrella,
    TabGestionRiesgo,
    TabAnalisisIA,
    TabProyeccion2026
)

__version__ = "2.0.0"
__all__ = [
    'AppConfig',
    'FerreinoxColors',
    'configurar_pagina',
    'cargar_y_validar_datos',
    'renderizar_sidebar',
    'aplicar_filtros',
    'validar_datos_filtrados',
    'tarjeta_metrica',
    'TabADNCrecimiento',
    'TabPortafolioMarcasCategorias',
    'TabTopClientes',
    'TabProductosEstrella',
    'TabGestionRiesgo',
    'TabAnalisisIA',
    'TabProyeccion2026'
]
