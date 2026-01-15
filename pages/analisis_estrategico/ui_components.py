"""Componentes de interfaz de usuario reutilizables"""
import streamlit as st  # ✅ AGREGAR
import pandas as pd     # ✅ AGREGAR
from typing import Dict

def renderizar_sidebar(df_master: pd.DataFrame, config: Dict) -> Dict:
    """Renderiza sidebar con filtros interactivos"""
    from .config import AppConfig
    
    st.sidebar.image(AppConfig.LOGO_URL, use_container_width=True)
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Configuración de Análisis")
    
    anios_validos = config['anios_disponibles']
    
    if len(anios_validos) < 2:
        st.sidebar.error("⚠️ Se necesitan al menos 2 años de datos")
        st.stop()
    
    anio_objetivo = st.sidebar.selectbox(
        "🎯 Año Objetivo",
        anios_validos,
        index=0,
        help="Año a analizar en detalle"
    )
    
    anios_comparacion = [a for a in anios_validos if a != anio_objetivo]
    anio_base = st.sidebar.selectbox(
        "📊 Año Base",
        anios_comparacion,
        index=0,
        help="Año de comparación"
    )
    
    st.sidebar.info(f"""
    **Análisis Configurado:**
    - 🎯 Objetivo: **{anio_objetivo}**
    - 📊 Base: **{anio_base}**
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔧 Filtros Adicionales")
    
    ciudades = st.sidebar.multiselect(
        "🏙️ Ciudades",
        config['ciudades_disponibles'],
        help="Filtrar por ciudades"
    )
    
    marcas = st.sidebar.multiselect(
        "🏷️ Marcas",
        config['marcas_disponibles'],
        help="Filtrar por marcas"
    )
    
    if marcas:
        cats_disponibles = sorted(
            df_master[df_master['Marca_Master'].isin(marcas)]['Categoria_Master'].dropna().unique()
        )
    else:
        cats_disponibles = config['categorias_disponibles']
    
    categorias = st.sidebar.multiselect(
        "📂 Categorías",
        cats_disponibles,
        help="Filtrar por categorías"
    )
    
    return {
        'anio_objetivo': anio_objetivo,
        'anio_base': anio_base,
        'ciudades': ciudades,
        'marcas': marcas,
        'categorias': categorias
    }

def aplicar_filtros(df: pd.DataFrame, filtros: Dict) -> pd.DataFrame:
    """Aplica filtros seleccionados al DataFrame"""
    df_filtrado = df.copy()
    
    if filtros['ciudades']:
        df_filtrado = df_filtrado[df_filtrado['Poblacion_Real'].isin(filtros['ciudades'])]
    
    if filtros['marcas']:
        df_filtrado = df_filtrado[df_filtrado['Marca_Master'].isin(filtros['marcas'])]
    
    if filtros['categorias']:
        df_filtrado = df_filtrado[df_filtrado['Categoria_Master'].isin(filtros['categorias'])]
    
    return df_filtrado

def validar_datos_filtrados(df: pd.DataFrame, filtros: Dict) -> bool:
    """Valida datos suficientes después de filtros"""
    df_actual = df[df['anio'] == filtros['anio_objetivo']]
    df_anterior = df[df['anio'] == filtros['anio_base']]
    
    if df_actual.empty or df_anterior.empty:
        st.warning(f"""
        ⚠️ **No hay datos suficientes para análisis comparativo.**
        
        **Registros encontrados:**
        - {filtros['anio_objetivo']}: {len(df_actual):,} registros
        - {filtros['anio_base']}: {len(df_anterior):,} registros
        """)
        
        with st.expander("🔍 Diagnóstico Detallado"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    f"Datos {filtros['anio_objetivo']}",
                    f"{len(df_actual):,} registros",
                    f"${df_actual['VALOR'].sum():,.0f}" if not df_actual.empty else "Sin datos"
                )
            
            with col2:
                st.metric(
                    f"Datos {filtros['anio_base']}",
                    f"{len(df_anterior):,} registros",
                    f"${df_anterior['VALOR'].sum():,.0f}" if not df_anterior.empty else "Sin datos"
                )
        
        return False
    
    st.sidebar.success(f"""
    ✅ **Datos Validados**
    - {filtros['anio_objetivo']}: {len(df_actual):,} registros
    - {filtros['anio_base']}: {len(df_anterior):,} registros
    """)
    
    return True

def tarjeta_metrica(etiqueta: str, valor: str, delta: str = None, color: str = "blue"):
    """Renderiza tarjeta de métrica estilizada"""
    delta_html = f'<p style="color: {color}; margin: 0.5rem 0 0 0;">{delta}</p>' if delta else ''
    
    st.markdown(f"""
    <div class="metric-card">
        <p style="font-size: 0.85rem; color: #64748b; margin: 0;">{etiqueta}</p>
        <p style="font-size: 1.8rem; font-weight: 800; margin: 0.5rem 0;">{valor}</p>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)