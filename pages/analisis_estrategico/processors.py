"""Procesadores de tabs de análisis estratégico"""
from abc import ABC, abstractmethod
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict
import numpy as np

class BaseTab(ABC):
    """Clase base abstracta para tabs de análisis"""
    
    def __init__(self, df: pd.DataFrame, filtros: Dict):
        self.df = df
        self.filtros = filtros
        self.df_actual = df[df['anio'] == filtros['anio_objetivo']]
        self.df_anterior = df[df['anio'] == filtros['anio_base']]
    
    @abstractmethod
    def render(self):
        """Método que cada tab debe implementar"""
        pass
    
    def calcular_metricas_basicas(self) -> Dict:
        """Calcula métricas comparativas básicas"""
        venta_actual = self.df_actual['VALOR'].sum()
        venta_anterior = self.df_anterior['VALOR'].sum()
        diferencia = venta_actual - venta_anterior
        pct_variacion = (diferencia / venta_anterior * 100) if venta_anterior > 0 else 0
        
        return {
            'venta_actual': venta_actual,
            'venta_anterior': venta_anterior,
            'diferencia': diferencia,
            'pct_variacion': pct_variacion
        }


class TabADNCrecimiento(BaseTab):
    """Tab 1: Análisis de ADN de crecimiento"""
    
    def render(self):
        st.header("📊 ADN de Crecimiento")
        
        metricas = self.calcular_metricas_basicas()
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric(
            "Ventas Año Objetivo",
            f"${metricas['venta_actual']/1e6:.1f}M",
            f"{metricas['pct_variacion']:+.1f}%"
        )
        
        col2.metric(
            "Ventas Año Base",
            f"${metricas['venta_anterior']/1e6:.1f}M"
        )
        
        col3.metric(
            "Variación Absoluta",
            f"${abs(metricas['diferencia'])/1e6:.1f}M"
        )
        
        clientes_actual = self.df_actual['CLIENTE'].nunique()
        clientes_anterior = self.df_anterior['CLIENTE'].nunique()
        col4.metric(
            "Clientes Activos",
            f"{clientes_actual:,}",
            f"{clientes_actual - clientes_anterior:+,}"
        )
        
        st.markdown("---")
        self._analisis_tendencias()
        self._analisis_marcas()
        
        # NUEVO: Botón de descarga PDF
        st.markdown("---")
        if st.button("📥 Descargar Reporte PDF", key="btn_pdf_adn"):
            from .pdf_generator import generar_reporte_completo
            
            # Preparar datos para PDF
            df_marcas = self.df_actual.groupby('Marca_Master')['VALOR'].sum().reset_index()
            df_marcas.columns = ['Marca', 'Ventas']
            
            df_clientes = self.df_actual.groupby('CLIENTE')['VALOR'].sum().reset_index()
            df_clientes.columns = ['Cliente', 'Ventas']
            
            conclusiones = [
                f"Las ventas crecieron {metricas['pct_variacion']:.1f}% respecto al año anterior",
                f"Se generó un incremento absoluto de ${metricas['diferencia']:,.0f}",
                "Se recomienda mantener el enfoque en las marcas líderes identificadas"
            ]
            
            pdf_bytes = generar_reporte_completo(
                metricas_basicas=metricas,
                df_marcas=df_marcas,
                df_clientes=df_clientes,
                anio_objetivo=self.filtros['anio_objetivo'],
                anio_base=self.filtros['anio_base'],
                conclusiones=conclusiones
            )
            
            st.download_button(
                label="💾 Guardar PDF",
                data=pdf_bytes,
                file_name=f"Analisis_ADN_Crecimiento_{self.filtros['anio_objetivo']}.pdf",
                mime="application/pdf"
            )
    
    def _analisis_tendencias(self):
        """Tendencias mensuales"""
        st.subheader("📈 Tendencias Mensuales")
        
        df_tendencias = self.df.groupby(['anio', 'mes'])['VALOR'].sum().reset_index()
        
        fig = px.line(
            df_tendencias,
            x='mes',
            y='VALOR',
            color='anio',
            title="Evolución de Ventas",
            labels={'VALOR': 'Ventas ($)', 'mes': 'Mes'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    def _analisis_marcas(self):
        """Análisis por marca"""
        st.subheader("🏷️ Desempeño por Marca")
        
        marcas_actual = self.df_actual.groupby('Marca_Master')['VALOR'].sum().sort_values(ascending=False).head(10)
        marcas_anterior = self.df_anterior.groupby('Marca_Master')['VALOR'].sum()
        
        df_comp = pd.DataFrame({
            'Actual': marcas_actual,
            'Anterior': marcas_anterior
        }).fillna(0)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(name=f'{self.filtros["anio_base"]}', x=df_comp.index, y=df_comp['Anterior']))
        fig.add_trace(go.Bar(name=f'{self.filtros["anio_objetivo"]}', x=df_comp.index, y=df_comp['Actual']))
        
        fig.update_layout(barmode='group', title="Top 10 Marcas")
        st.plotly_chart(fig, use_container_width=True)


class TabOportunidadGeografica(BaseTab):
    """Tab de análisis geográfico"""
    
    def render(self):
        st.header("📍 Oportunidad Geográfica")
        st.markdown("Identificación de mercados con mayor potencial de crecimiento.")
        
        df_geo = self.df.groupby(['Poblacion_Real', 'anio'])['VALOR'].sum().reset_index()
        
        fig = px.bar(
            df_geo,
            x='Poblacion_Real',
            y='VALOR',
            color='anio',
            title="Ventas por Ciudad",
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        self._mapa_calor_ciudades()
    
    def _mapa_calor_ciudades(self):
        """Mapa de calor de crecimiento"""
        st.subheader("🗺️ Crecimiento por Ciudad")
        
        ciudades_actual = self.df_actual.groupby('Poblacion_Real')['VALOR'].sum()
        ciudades_anterior = self.df_anterior.groupby('Poblacion_Real')['VALOR'].sum()
        
        df_crec = pd.DataFrame({
            'Actual': ciudades_actual,
            'Anterior': ciudades_anterior
        }).fillna(0)
        
        df_crec['Crecimiento'] = ((df_crec['Actual'] - df_crec['Anterior']) / df_crec['Anterior'] * 100).fillna(0)
        df_crec = df_crec.sort_values('Crecimiento', ascending=False).head(15)
        
        fig = px.bar(
            df_crec.reset_index(),
            x='Poblacion_Real',
            y='Crecimiento',
            title="Top 15 Ciudades por Crecimiento",
            color='Crecimiento',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig, use_container_width=True)


class TabTopClientes(BaseTab):
    """Tab de análisis de clientes"""
    
    def render(self):
        st.header("👥 Top 50 Clientes")
        st.markdown("Análisis de la cartera de clientes más importantes.")
        
        df_clientes = self.df_actual.groupby('CLIENTE')['VALOR'].sum().sort_values(ascending=False).head(50)
        
        fig = px.bar(
            df_clientes.reset_index(),
            x='CLIENTE',
            y='VALOR',
            title="Top 50 Clientes por Ventas"
        )
        st.plotly_chart(fig, use_container_width=True)


class TabProductosEstrella(BaseTab):
    """Tab de análisis de productos"""
    
    def render(self):
        st.header("📦 Productos Estrella")
        st.markdown("Productos con mejor desempeño comercial.")
        
        df_productos = self.df_actual.groupby('NOMBRE_PRODUCTO_K')['VALOR'].sum().sort_values(ascending=False).head(50)
        
        fig = px.treemap(
            df_productos.reset_index(),
            path=['NOMBRE_PRODUCTO_K'],
            values='VALOR',
            title="Top 50 Productos"
        )
        st.plotly_chart(fig, use_container_width=True)


class TabGestionRiesgo(BaseTab):
    """Tab de gestión de riesgo"""
    
    def render(self):
        st.header("⚠️ Gestión de Riesgo")
        st.markdown("Identificación de factores de riesgo comercial.")
        
        # Clientes en decrecimiento
        clientes_actual = self.df_actual.groupby('CLIENTE')['VALOR'].sum()
        clientes_anterior = self.df_anterior.groupby('CLIENTE')['VALOR'].sum()
        
        df_comp = pd.DataFrame({
            'Actual': clientes_actual,
            'Anterior': clientes_anterior
        }).fillna(0)
        
        df_comp['Variacion'] = df_comp['Actual'] - df_comp['Anterior']
        clientes_riesgo = df_comp[df_comp['Variacion'] < 0].sort_values('Variacion').head(20)
        
        st.subheader("⚠️ Top 20 Clientes en Riesgo")
        st.dataframe(clientes_riesgo.reset_index())


class TabAnalisisIA(BaseTab):
    """Tab de análisis con IA"""
    
    def render(self):
        st.header("🤖 Análisis con IA")
        st.markdown("Predicciones y patrones detectados por inteligencia artificial.")
        
        from sklearn.linear_model import LinearRegression
        
        df_entreno = self.df[self.df['anio'] < self.filtros['anio_objetivo']]
        X = df_entreno[['mes', 'dia']].values
        y = df_entreno['VALOR'].values
        
        modelo = LinearRegression()
        modelo.fit(X, y)
        
        df_pred = self.df_actual[['mes', 'dia']].copy()
        df_pred['Prediccion'] = modelo.predict(df_pred[['mes', 'dia']])
        
        st.subheader("📈 Predicciones vs Real")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_pred.index,
            y=self.df_actual['VALOR'].values,
            name='Real',
            mode='lines'
        ))
        fig.add_trace(go.Scatter(
            x=df_pred.index,
            y=df_pred['Prediccion'],
            name='Predicción IA',
            mode='lines',
            line=dict(dash='dash')
        ))
        
        st.plotly_chart(fig, use_container_width=True)


class TabProyeccion2026(BaseTab):
    """Tab de proyección 2026"""
    
    def render(self):
        st.header("🔮 Proyección 2026")
        st.markdown("Proyección inteligente basada en datos históricos.")
        
        # Verificar datos necesarios
        if not (2024 in self.df['anio'].unique() and 2025 in self.df['anio'].unique()):
            st.warning("Se necesitan datos de 2024 y 2025 para proyectar 2026")
            return
        
        df_2024 = self.df[self.df['anio'] == 2024]
        df_2025 = self.df[self.df['anio'] == 2025]
        
        venta_2024 = df_2024['VALOR'].sum()
        venta_2025 = df_2025['VALOR'].sum()
        
        tasa_crecimiento = ((venta_2025 - venta_2024) / venta_2024 * 100) if venta_2024 > 0 else 0
        proyeccion_2026 = venta_2025 * (1 + tasa_crecimiento * 0.8 / 100)
        
        col1, col2, col3 = st.columns(3)
        
        col1.metric("Ventas 2024", f"${venta_2024/1e6:.1f}M")
        col2.metric("Ventas 2025", f"${venta_2025/1e6:.1f}M", f"{tasa_crecimiento:+.1f}%")
        col3.metric("🔮 Proyección 2026", f"${proyeccion_2026/1e6:.1f}M")
        
        # Gráfico de tendencia
        df_tendencia = pd.DataFrame({
            'Año': [2024, 2025, 2026],
            'Ventas': [venta_2024, venta_2025, proyeccion_2026],
            'Tipo': ['Histórico', 'Histórico', 'Proyección']
        })
        
        fig = px.line(
            df_tendencia,
            x='Año',
            y='Ventas',
            title="Proyección de Ventas 2026",
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)