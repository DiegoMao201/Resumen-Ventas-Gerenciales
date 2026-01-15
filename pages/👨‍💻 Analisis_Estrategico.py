"""
📊 Análisis Estratégico de Crecimiento - Ferreinox S.A.S. BIC
Versión 2.0 - Arquitectura Modular Profesional
"""

import streamlit as st
from analisis_estrategico import (
    configurar_pagina,
    cargar_y_validar_datos,
    renderizar_sidebar,
    aplicar_filtros,
    validar_datos_filtrados,
    TabADNCrecimiento,
    TabOportunidadGeografica,
    TabTopClientes,
    TabProductosEstrella,
    TabGestionRiesgo,
    TabAnalisisIA,
    TabProyeccion2026
)

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
    "📍 Oportunidad Geográfica",
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
    TabOportunidadGeografica(df_filtrado, filtros).render()

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