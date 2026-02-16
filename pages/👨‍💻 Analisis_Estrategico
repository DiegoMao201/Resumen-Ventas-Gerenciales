"""
📊 Análisis Estratégico de Crecimiento - Ferreinox S.A.S. BIC
Versión 2.0 - Arquitectura Modular Profesional
"""

import sys
import os
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go

# Agregar la carpeta 'pages' al path de Python
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import streamlit as st

# Importar módulos del paquete analisis_estrategico
try:
    from analisis_estrategico import (
        configurar_pagina,
        cargar_y_validar_datos,
        renderizar_sidebar,
        aplicar_filtros,
        validar_datos_filtrados,
        TabADNCrecimiento,
        TabPortafolioMarcasCategorias,
        TabTopClientes,
        TabProductosEstrella,
        TabGestionRiesgo,
        TabAnalisisIA,
        TabProyeccion2026
    )
except ImportError as e:
    st.error(f"""
    ❌ **Error de importación:** {e}
    
    **Diagnóstico:**
    - Verifica que la carpeta `pages/analisis_estrategico/` existe
    - Verifica que `__init__.py` está presente en esa carpeta
    - Estructura esperada:
      ```
      pages/
        analisis_estrategico/
          __init__.py
          config.py
          data_loader.py
          ui_components.py
          processors.py
          projections.py
          visualizations.py
          pdf_generator.py
      ```
    """)
    st.stop()

# ===== CONFIGURACIÓN DE PÁGINA =====
configurar_pagina()

# ===== CARGA Y VALIDACIÓN DE DATOS =====
try:
    df_master, config_filtros = cargar_y_validar_datos()
except Exception as e:
    st.error(f"❌ Error crítico al cargar datos: {e}")
    st.stop()

# ===== SIDEBAR CON FILTROS =====
filtros = renderizar_sidebar(df_master, config_filtros)

# ===== APLICAR FILTROS AL DATAFRAME =====
df_filtrado = aplicar_filtros(df_master, filtros)

# ===== VALIDAR DATOS FILTRADOS =====
if not validar_datos_filtrados(df_filtrado, filtros):
    st.stop()

# ===== CREAR PESTAÑAS DE ANÁLISIS =====
tabs = st.tabs([
    "📊 ADN de Crecimiento",
    "🧭 Marcas & Categorías",
    "👥 Top 50 Clientes",
    "📦 Productos Estrella",
    "⚠️ Gestión de Riesgo",
    "🤖 Análisis con IA",
    "🔮 Proyección 2026"
])

# ===== RENDERIZAR CONTENIDO DE CADA TAB =====
with tabs[0]:
    TabADNCrecimiento(df_filtrado, filtros).render()

with tabs[1]:
    TabPortafolioMarcasCategorias(df_filtrado, filtros).render()

with tabs[2]:
    TabTopClientes(df_filtrado, filtros).render()

with tabs[3]:
    TabProductosEstrella(df_filtrado, filtros).render()

with tabs[4]:
    TabGestionRiesgo(df_filtrado, filtros).render()

with tabs[5]:
    TabAnalisisIA(df_filtrado, filtros).render()

with tabs[6]:
    TabProyeccion2026(df_filtrado, filtros).render()

# ===== PIE DE PÁGINA =====
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; color: #64748b;">
    <p><b>Ferreinox S.A.S. BIC</b> | Sistema de Inteligencia Comercial v2.0</p>
    <p>📧 info@ferreinox.co | 🌐 <a href="https://www.ferreinox.co" target="_blank">www.ferreinox.co</a></p>
</div>
""", unsafe_allow_html=True)
