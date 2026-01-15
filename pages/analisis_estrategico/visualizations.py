"""Utilidades avanzadas para generación de gráficos empresariales"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Dict

# Paleta de colores corporativos Ferreinox
COLORES_FERREINOX = {
    'primary': '#1e3a8a',
    'secondary': '#3b82f6',
    'accent': '#f59e0b',
    'success': '#10b981',
    'error': '#ef4444'
}

def crear_grafico_comparativo(
    df_actual: pd.DataFrame,
    df_anterior: pd.DataFrame,
    columna_agrupacion: str,
    columna_valor: str = 'VALOR',
    top_n: int = 10,
    titulo: str = "Comparación Año a Año"
) -> go.Figure:
    """Crea gráfico comparativo profesional entre dos periodos"""
    
    # Agrupar y ordenar datos
    actual = df_actual.groupby(columna_agrupacion)[columna_valor].sum().sort_values(ascending=False).head(top_n)
    anterior = df_anterior.groupby(columna_agrupacion)[columna_valor].sum()
    
    # Crear figura
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Periodo Anterior',
        x=actual.index,
        y=[anterior.get(x, 0) for x in actual.index],
        marker_color=COLORES_FERREINOX['secondary'],
        hovertemplate='<b>%{x}</b><br>Ventas: $%{y:,.0f}<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        name='Periodo Actual',
        x=actual.index,
        y=actual.values,
        marker_color=COLORES_FERREINOX['accent'],
        hovertemplate='<b>%{x}</b><br>Ventas: $%{y:,.0f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=titulo,
        barmode='group',
        height=450,
        hovermode='x unified',
        template='plotly_white',
        xaxis_title=columna_agrupacion,
        yaxis_title='Ventas ($)',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def crear_mapa_calor_crecimiento(
    df_actual: pd.DataFrame,
    df_anterior: pd.DataFrame,
    columna_entidad: str,
    columna_valor: str = 'VALOR',
    top_n: int = 15
) -> go.Figure:
    """Crea mapa de calor de tasas de crecimiento"""
    
    # Calcular ventas por entidad
    ventas_actual = df_actual.groupby(columna_entidad)[columna_valor].sum()
    ventas_anterior = df_anterior.groupby(columna_entidad)[columna_valor].sum()
    
    # Crear DataFrame de crecimiento
    df_crec = pd.DataFrame({
        'Actual': ventas_actual,
        'Anterior': ventas_anterior
    }).fillna(0)
    
    df_crec['Crecimiento'] = np.where(
        df_crec['Anterior'] > 0,
        ((df_crec['Actual'] - df_crec['Anterior']) / df_crec['Anterior']) * 100,
        0
    )
    
    df_crec = df_crec.sort_values('Crecimiento', ascending=False).head(top_n)
    
    # Crear gráfico
    fig = px.bar(
        df_crec.reset_index(),
        x=columna_entidad,
        y='Crecimiento',
        title=f"Top {top_n} Entidades por Crecimiento",
        color='Crecimiento',
        color_continuous_scale='RdYlGn',
        labels={'Crecimiento': 'Crecimiento (%)'},
        hover_data={'Actual': ':$,.0f', 'Anterior': ':$,.0f'}
    )
    
    fig.update_layout(
        height=450,
        template='plotly_white',
        xaxis_tickangle=-45
    )
    
    return fig


def crear_grafico_tendencia_mensual(
    df: pd.DataFrame,
    columna_fecha: str = 'mes',
    columna_valor: str = 'VALOR',
    columna_agrupacion: str = 'anio'
) -> go.Figure:
    """Crea gráfico de tendencia mensual por año"""
    
    df_tendencia = df.groupby([columna_agrupacion, columna_fecha])[columna_valor].sum().reset_index()
    
    fig = px.line(
        df_tendencia,
        x=columna_fecha,
        y=columna_valor,
        color=columna_agrupacion,
        title="Evolución de Ventas Mensuales",
        labels={columna_valor: 'Ventas ($)', columna_fecha: 'Mes'},
        markers=True
    )
    
    fig.update_layout(
        height=400,
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig


def crear_grafico_pareto(
    df: pd.DataFrame,
    columna_entidad: str,
    columna_valor: str = 'VALOR',
    top_n: int = 20,
    titulo: str = "Análisis de Pareto"
) -> go.Figure:
    """Crea gráfico de Pareto (80/20)"""
    
    # Agrupar y ordenar
    datos = df.groupby(columna_entidad)[columna_valor].sum().sort_values(ascending=False).head(top_n)
    
    # Calcular porcentaje acumulado
    total = datos.sum()
    porcentaje_acum = (datos.cumsum() / total * 100)
    
    # Crear figura con doble eje
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=datos.index,
        y=datos.values,
        name='Ventas',
        marker_color=COLORES_FERREINOX['primary'],
        yaxis='y'
    ))
    
    fig.add_trace(go.Scatter(
        x=porcentaje_acum.index,
        y=porcentaje_acum.values,
        name='% Acumulado',
        marker_color=COLORES_FERREINOX['error'],
        yaxis='y2',
        mode='lines+markers'
    ))
    
    # Línea de referencia 80%
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color="red",
        annotation_text="80%",
        yref='y2'
    )
    
    fig.update_layout(
        title=titulo,
        yaxis=dict(title='Ventas ($)'),
        yaxis2=dict(
            title='% Acumulado',
            overlaying='y',
            side='right',
            range=[0, 100]
        ),
        height=450,
        template='plotly_white',
        hovermode='x unified'
    )
    
    return fig