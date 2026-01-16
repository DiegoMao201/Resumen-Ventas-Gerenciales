"""Componentes de interfaz de usuario reutilizables"""
import streamlit as st
import pandas as pd
from typing import Dict
from .config import AppConfig

def renderizar_sidebar(df_master: pd.DataFrame, config: Dict) -> Dict:
    """Renderiza sidebar con filtros interactivos"""
    st.sidebar.header("🎯 Filtros de Análisis")
    
    # Filtro de años
    anio_objetivo = st.sidebar.selectbox(
        "Año Objetivo",
        options=config['anios_disponibles'],
        index=0,
        help="Año principal a analizar"
    )
    
    anio_base = st.sidebar.selectbox(
        "Año de Comparación",
        options=[a for a in config['anios_disponibles'] if a < anio_objetivo],
        index=0 if len([a for a in config['anios_disponibles'] if a < anio_objetivo]) > 0 else 0,
        help="Año contra el cual comparar"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filtros Opcionales")
    
    # Filtro de ciudades
    ciudades = st.sidebar.multiselect(
        "Ciudades",
        options=config['ciudades_disponibles'],
        default=[],
        help="Filtrar por ubicación geográfica"
    )
    
    # Filtro de líneas estratégicas
    lineas = st.sidebar.multiselect(
        "Líneas Estratégicas",
        options=config['lineas_disponibles'],
        default=[],
        help="ABRACOL, YALE, GOYA, DELTA, etc."
    )
    
    # Filtro de vendedores
    vendedores = st.sidebar.multiselect(
        "Vendedores",
        options=config['vendedores_disponibles'],
        default=[],
        help="Filtrar por vendedor o grupo"
    )
    
    return {
        'anio_objetivo': anio_objetivo,
        'anio_base': anio_base,
        'ciudades': ciudades,
        'lineas': lineas,
        'vendedores': vendedores
    }

def aplicar_filtros(df: pd.DataFrame, filtros: Dict) -> pd.DataFrame:
    """Aplica filtros seleccionados al DataFrame"""
    df_filtrado = df.copy()
    
    if filtros.get('ciudades'):
        if 'Poblacion_Real' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['Poblacion_Real'].isin(filtros['ciudades'])]
    
    if filtros.get('lineas'):
        if 'Linea_Estrategica' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['Linea_Estrategica'].isin(filtros['lineas'])]
    
    if filtros.get('vendedores'):
        if 'nomvendedor' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['nomvendedor'].isin(filtros['vendedores'])]
    
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
                    f"${df_actual['valor_venta'].sum():,.0f}" if not df_actual.empty and 'valor_venta' in df_actual.columns else "Sin datos"
                )
            
            with col2:
                st.metric(
                    f"Datos {filtros['anio_base']}",
                    f"{len(df_anterior):,} registros",
                    f"${df_anterior['valor_venta'].sum():,.0f}" if not df_anterior.empty and 'valor_venta' in df_anterior.columns else "Sin datos"
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
    delta_html = f'<p style="color: {"green" if "+" in str(delta) else "red"}; margin: 0;">{delta}</p>' if delta else ""
    
    st.markdown(f"""
    <div class="metrica-card" style="border-left-color: {color};">
        <p style="color: #64748b; margin: 0; font-size: 0.875rem;">{etiqueta}</p>
        <h3 style="margin: 0.5rem 0; color: #1e293b;">{valor}</h3>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)