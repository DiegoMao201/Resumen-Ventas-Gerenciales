"""Funciones de proyección y forecasting"""
import pandas as pd
import numpy as np
import streamlit as st
from sklearn.linear_model import LinearRegression

@st.cache_data(ttl=3600)
def proyectar_ventas_2026(df_2024, df_2025, metodo='conservador'):
    """Proyecta ventas 2026 según método seleccionado"""
    try:
        col_valor = "valor_venta" if "valor_venta" in df_2024.columns else "VALOR"
        venta_2024 = df_2024[col_valor].sum() if not df_2024.empty else 0
        venta_2025 = df_2025[col_valor].sum() if not df_2025.empty else 0
        
        if venta_2024 == 0 or venta_2025 == 0:
            return None, "Datos insuficientes para proyectar"
        
        tasa_crecimiento_24_25 = ((venta_2025 - venta_2024) / venta_2024) * 100
        
        if metodo == 'conservador':
            tasa_aplicada = tasa_crecimiento_24_25 * 0.8
            proyeccion = venta_2025 * (1 + tasa_aplicada / 100)
            confianza = "Alta (Conservadora)"
        
        elif metodo == 'optimista':
            tasa_aplicada = tasa_crecimiento_24_25 * 1.2
            proyeccion = venta_2025 * (1 + tasa_aplicada / 100)
            confianza = "Media (Optimista)"
        
        else:  # realista
            tasa_aplicada = tasa_crecimiento_24_25
            proyeccion = venta_2025 * (1 + tasa_aplicada / 100)
            confianza = "Alta (Realista)"
        
        return {
            'proyeccion_2026': proyeccion,
            'tasa_aplicada': tasa_aplicada,
            'venta_2024': venta_2024,
            'venta_2025': venta_2025,
            'tasa_historica': tasa_crecimiento_24_25,
            'confianza': confianza,
            'metodo': metodo.capitalize()
        }, None
        
    except Exception as e:
        return None, f"Error al proyectar: {str(e)}"


@st.cache_data(ttl=3600)
def proyectar_por_vendedor(df_2024, df_2025, columna='Vendedor'):
    """Proyecta ventas por vendedor"""
    
    vendedores_2024 = df_2024.groupby(columna)['VALOR'].sum()
    vendedores_2025 = df_2025.groupby(columna)['VALOR'].sum()
    
    df_proyeccion = pd.DataFrame({
        'Venta_2024': vendedores_2024,
        'Venta_2025': vendedores_2025
    }).fillna(0)
    
    df_proyeccion['Tasa_Crecimiento'] = np.where(
        df_proyeccion['Venta_2024'] > 0,
        ((df_proyeccion['Venta_2025'] - df_proyeccion['Venta_2024']) / df_proyeccion['Venta_2024']) * 100,
        0
    )
    
    df_proyeccion['Proyeccion_2026'] = df_proyeccion['Venta_2025'] * (1 + df_proyeccion['Tasa_Crecimiento'] * 0.8 / 100)
    
    return df_proyeccion.sort_values('Proyeccion_2026', ascending=False)


@st.cache_data(ttl=3600)
def proyectar_por_ciudad(df_2024, df_2025, columna='Poblacion_Real'):
    """Proyecta ventas por ciudad"""
    
    ciudades_2024 = df_2024.groupby(columna)['VALOR'].sum()
    ciudades_2025 = df_2025.groupby(columna)['VALOR'].sum()
    
    df_proyeccion = pd.DataFrame({
        'Venta_2024': ciudades_2024,
        'Venta_2025': ciudades_2025
    }).fillna(0)
    
    df_proyeccion['Tasa_Crecimiento'] = np.where(
        df_proyeccion['Venta_2024'] > 0,
        ((df_proyeccion['Venta_2025'] - df_proyeccion['Venta_2024']) / df_proyeccion['Venta_2024']) * 100,
        0
    )
    
    df_proyeccion['Proyeccion_2026'] = df_proyeccion['Venta_2025'] * (1 + df_proyeccion['Tasa_Crecimiento'] * 0.8 / 100)
    
    return df_proyeccion.sort_values('Proyeccion_2026', ascending=False)
