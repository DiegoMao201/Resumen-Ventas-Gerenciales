"""Funciones de proyección y forecasting"""
import pandas as pd
import numpy as np
import streamlit as st
from sklearn.linear_model import LinearRegression

@st.cache_data(ttl=3600)
def proyectar_ventas_2026(df_2024, df_2025, metodo='conservador'):
    """Proyecta ventas 2026 según método seleccionado"""
    
    venta_2024 = df_2024['VALOR'].sum()
    venta_2025 = df_2025['VALOR'].sum()
    
    if venta_2024 == 0:
        return None, "No hay datos de 2024"
    
    tasa_crecimiento_24_25 = ((venta_2025 - venta_2024) / venta_2024) * 100
    
    if metodo == 'conservador':
        tasa_aplicada = tasa_crecimiento_24_25 * 0.8
        proyeccion = venta_2025 * (1 + tasa_aplicada / 100)
        confianza = "Alta (Conservadora)"
    
    elif metodo == 'optimista':
        tasa_aplicada = tasa_crecimiento_24_25 * 1.2
        proyeccion = venta_2025 * (1 + tasa_aplicada / 100)
        confianza = "Media (Optimista)"
    
    elif metodo == 'promedio':
        tasa_aplicada = tasa_crecimiento_24_25
        proyeccion = venta_2025 * (1 + tasa_aplicada / 100)
        confianza = "Alta (Promedio)"
    
    else:  # lineal
        X = np.array([[2024], [2025]])
        y = np.array([venta_2024, venta_2025])
        modelo = LinearRegression()
        modelo.fit(X, y)
        proyeccion = modelo.predict([[2026]])[0]
        tasa_aplicada = ((proyeccion - venta_2025) / venta_2025) * 100
        confianza = "Alta (Modelo Lineal)"
    
    return {
        'metodo': metodo,
        'proyeccion_2026': proyeccion,
        'tasa_crecimiento_24_25': tasa_crecimiento_24_25,
        'tasa_aplicada_26': tasa_aplicada,
        'venta_2024': venta_2024,
        'venta_2025': venta_2025,
        'nivel_confianza': confianza,
        'incremento_absoluto': proyeccion - venta_2025
    }, "OK"


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
