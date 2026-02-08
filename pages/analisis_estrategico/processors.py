"""Procesadores de tabs de análisis estratégico"""
from abc import ABC, abstractmethod
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from typing import Dict

from .projections import proyectar_ventas_2026, proyectar_por_vendedor, proyectar_por_ciudad
from .pdf_generator import generar_reporte_completo
from .ai_analysis import analizar_con_ia_avanzado
from .config import AppConfig

class BaseTab(ABC):
    """Clase base abstracta para tabs de análisis"""
    def __init__(self, df: pd.DataFrame, filtros: Dict):
        self.df = df
        self.filtros = filtros
        self.df_actual = df[df["anio"] == filtros["anio_objetivo"]]
        self.df_anterior = df[df["anio"] == filtros["anio_base"]]

        def pick(names):
            return next((c for c in names if c in df.columns), names[-1])

        self.col_valor = "valor_venta" if "valor_venta" in df.columns else pick(["VALOR"])
        self.col_linea = pick(["Linea_Estrategica", "super_categoria", "categoria_producto", "linea_producto"])
        self.col_marca = pick(["nombre_marca", "marca_producto", "Marca_Master"])
        self.col_cliente = pick(["nombre_cliente", "CLIENTE"])
        self.col_producto = pick(["nombre_articulo", "NOMBRE_PRODUCTO"])
        self.col_vendedor = pick(["nomvendedor", "Vendedor"])
        self.col_ciudad = pick(["Poblacion_Real", "Ciudad"])
    
    @abstractmethod
    def render(self):
        """Método que cada tab debe implementar"""
        pass
    
    def calcular_metricas_basicas(self) -> Dict:
        """Calcula métricas comparativas básicas"""
        venta_actual = self.df_actual[self.col_valor].sum()
        venta_anterior = self.df_anterior[self.col_valor].sum()
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
        
        clientes_actual = self.df_actual[self.col_cliente].nunique()
        clientes_anterior = self.df_anterior[self.col_cliente].nunique()
        col4.metric(
            "Clientes Activos",
            f"{clientes_actual:,}",
            f"{clientes_actual - clientes_anterior:+,}"
        )
        
        st.markdown("---")
        self._analisis_tendencias()
        self._analisis_marcas()
        
        # Botón de descarga PDF
        st.markdown("---")
        if st.button("📥 Descargar Reporte PDF", key="btn_pdf_adn"):
            
            df_marcas = self.df_actual.groupby(self.col_marca)[self.col_valor].sum().reset_index()
            df_marcas.columns = ['Marca', 'Ventas']
            
            df_clientes = self.df_actual.groupby(self.col_cliente)[self.col_valor].sum().reset_index()
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
                file_name=f"Analisis_Crecimiento_{self.filtros['anio_objetivo']}.pdf",
                mime="application/pdf"
            )
    
    def _analisis_tendencias(self):
        """Tendencias mensuales"""
        st.subheader("📈 Tendencias Mensuales")
        
        df_tendencias = self.df.groupby(['anio', 'mes'])[self.col_valor].sum().reset_index()
        
        fig = px.line(
            df_tendencias,
            x='mes',
            y=self.col_valor,
            color='anio',
            title="Evolución de Ventas",
            labels={self.col_valor: 'Ventas ($)', 'mes': 'Mes'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    def _analisis_marcas(self):
        """Análisis por marca"""
        st.subheader("🏷️ Desempeño por Marca")
        col_marca = "nombre_marca" if "nombre_marca" in self.df.columns else self.col_marca

        marcas_actual = (
            self.df_actual.groupby(col_marca)[self.col_valor]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )
        marcas_anterior = self.df_anterior.groupby(col_marca)[self.col_valor].sum()

        df_comp = pd.DataFrame({
            'Actual': marcas_actual,
            'Anterior': [marcas_anterior.get(m, 0) for m in marcas_actual.index]
        }).fillna(0)

        fig = go.Figure()
        fig.add_trace(go.Bar(name=f'{self.filtros["anio_base"]}', x=df_comp.index, y=df_comp['Anterior']))
        fig.add_trace(go.Bar(name=f'{self.filtros["anio_objetivo"]}', x=df_comp.index, y=df_comp['Actual']))
        fig.update_layout(barmode='group', title="Top 10 Marcas - Comparativo", xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)


class TabAnalisisIA(BaseTab):
    """Tab de análisis ejecutivo con IA avanzada"""
    
    def render(self):
        st.header("🤖 Análisis Estratégico Ejecutivo con IA")
        st.markdown("**Análisis profundo generado por GPT-4 Mini + Análisis Cuantitativo**")
        
        config = AppConfig()
        
        with st.spinner("🧠 Generando análisis estratégico completo..."):
            metricas = self.calcular_metricas_basicas()

            lineas_presentes = sorted(self.df['Linea_Estrategica'].dropna().unique()) if 'Linea_Estrategica' in self.df.columns else []
            if not lineas_presentes:
                st.warning("No se encontraron líneas estratégicas en los datos.")
                return

            # corregir llamada
            analisis_completo = analizar_con_ia_avanzado(self.df_actual, self.df_anterior, metricas, lineas_presentes)
        
        # Análisis Ejecutivo IA
        st.markdown("---")
        st.markdown(analisis_completo['analisis_ejecutivo'])
        
        # Análisis de Líneas Estratégicas
        st.markdown("---")
        st.subheader("📊 Análisis Detallado por Línea Estratégica")
        
        analisis_lineas = analisis_completo['analisis_lineas']
        
        # Crear DataFrame
        df_lineas = pd.DataFrame.from_dict(analisis_lineas, orient='index')
        df_lineas = df_lineas.sort_values('variacion_abs', ascending=False)
        
        st.dataframe(
            df_lineas[['ventas_actual', 'variacion_pct', 'variacion_abs', 'clientes_actual', 'impacto']],
            column_config={
                "ventas_actual": st.column_config.NumberColumn("Ventas Actuales", format="$%d"),
                "variacion_pct": st.column_config.NumberColumn("Var %", format="%.1f%%"),
                "variacion_abs": st.column_config.NumberColumn("Var Absoluta", format="$%d"),
                "clientes_actual": st.column_config.NumberColumn("Clientes", format="%d"),
                "impacto": "Impacto"
            },
            use_container_width=True
        )
        
        # Gráfico de motores vs frenos
        st.markdown("---")
        st.subheader("🎯 Motores vs Frenos de Crecimiento")
        
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        for linea in df_lineas.index:
            data = df_lineas.loc[linea]
            color = '#10b981' if data['impacto'] == 'MOTOR' else '#ef4444' if data['impacto'] == 'FRENO' else '#6b7280'
            
            fig.add_trace(go.Bar(
                name=linea,
                x=[linea],
                y=[data['variacion_abs']],
                marker_color=color,
                text=f"${data['variacion_abs']:,.0f}",
                textposition='outside'
            ))
        
        fig.update_layout(
            title="Impacto por Línea Estratégica",
            showlegend=False,
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Análisis de Clientes
        st.markdown("---")
        st.subheader("👥 Análisis de Retención y Captación")
        
        analisis_clientes = analisis_completo['analisis_clientes']
        
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric(
            "Tasa de Retención",
            f"{analisis_clientes['tasa_retencion']:.1f}%",
            f"{analisis_clientes['clientes_retenidos']} clientes"
        )
        
        col2.metric(
            "Clientes Nuevos",
            f"{analisis_clientes['clientes_nuevos']}",
            f"${analisis_clientes['ventas_nuevos']:,.0f}"
        )
        
        col3.metric(
            "Clientes Perdidos",
            f"{analisis_clientes['clientes_perdidos']}",
            delta_color="inverse"
        )
        
        col4.metric(
            "Ventas Retenidos",
            f"${analisis_clientes['ventas_retenidos']:,.0f}",
            f"{len(analisis_clientes['top_retenidos'])} TOP"
        )
        
        st.markdown("---")
        st.caption("✨ Análisis generado por OpenAI GPT-4 Mini + Motor Cuantitativo Ferreinox | Sistema de Inteligencia Comercial v2.0")


class TabOportunidadGeografica(BaseTab):
    """Tab de análisis geográfico"""
    
    def render(self):
        st.header("📍 Oportunidad Geográfica")
        st.markdown("Identificación de mercados con mayor potencial de crecimiento.")
        
        df_geo = self.df.groupby([self.col_ciudad, 'anio'])[self.col_valor].sum().reset_index()
        
        fig = px.bar(
            df_geo,
            x=self.col_ciudad,
            y=self.col_valor,
            color='anio',
            title="Ventas por Ciudad",
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        self._mapa_calor_ciudades()
    
    def _mapa_calor_ciudades(self):
        """Mapa de calor de crecimiento por ciudad"""
        st.subheader("🗺️ Mapa de Calor de Crecimiento")
        
        ciudades_actual = self.df_actual.groupby(self.col_ciudad)[self.col_valor].sum()
        ciudades_anterior = self.df_anterior.groupby(self.col_ciudad)[self.col_valor].sum()
        
        df_crec = pd.DataFrame({
            'Actual': ciudades_actual,
            'Anterior': ciudades_anterior
        }).fillna(0)
        
        df_crec['Crecimiento'] = np.where(
            df_crec['Anterior'] > 0,
            ((df_crec['Actual'] - df_crec['Anterior']) / df_crec['Anterior']) * 100,
            0
        )
        
        df_crec = df_crec.sort_values('Crecimiento', ascending=False).head(15)
        
        fig = go.Figure(data=go.Heatmap(
            z=[df_crec['Crecimiento'].values],
            x=df_crec.index,
            y=['Crecimiento %'],
            colorscale='RdYlGn',
            text=[[f"{v:.1f}%" for v in df_crec['Crecimiento'].values]],
            texttemplate='%{text}',
            textfont={"size": 10}
        ))
        
        fig.update_layout(
            title="Top 15 Ciudades por Crecimiento",
            xaxis_tickangle=-45,
            height=300
        )
        
        st.plotly_chart(fig, use_container_width=True)


class TabTopClientes(BaseTab):
    """Tab de top clientes"""
    
    def render(self):
        st.header("👥 Top 50 Clientes")
        
        clientes_actual = self.df_actual.groupby(self.col_cliente)[self.col_valor].sum().sort_values(ascending=False).head(50)
        clientes_anterior = self.df_anterior.groupby(self.col_cliente)[self.col_valor].sum()
        
        df_comp = pd.DataFrame({
            'Cliente': clientes_actual.index,
            'Ventas_Actual': clientes_actual.values,
            'Ventas_Anterior': [clientes_anterior.get(c, 0) for c in clientes_actual.index]
        })
        
        df_comp['Variacion'] = df_comp['Ventas_Actual'] - df_comp['Ventas_Anterior']
        df_comp['Variacion_Pct'] = np.where(
            df_comp['Ventas_Anterior'] > 0,
            (df_comp['Variacion'] / df_comp['Ventas_Anterior']) * 100,
            100
        )
        
        st.dataframe(
            df_comp,
            column_config={
                "Cliente": "Cliente",
                "Ventas_Actual": st.column_config.NumberColumn(f"Ventas {self.filtros['anio_objetivo']}", format="$%d"),
                "Ventas_Anterior": st.column_config.NumberColumn(f"Ventas {self.filtros['anio_base']}", format="$%d"),
                "Variacion": st.column_config.NumberColumn("Variación", format="$%d"),
                "Variacion_Pct": st.column_config.NumberColumn("Var %", format="%.1f%%")
            },
            use_container_width=True,
            hide_index=True
        )


class TabProductosEstrella(BaseTab):
    """Tab 4: Análisis de productos estrella"""
    
    def render(self):
        st.header("📦 Productos Estrella")
        
        # Top productos
        df_productos = self.df_actual.groupby(self.col_producto)[self.col_valor].sum().sort_values(ascending=False).head(50)
        df_productos_anterior = self.df_anterior.groupby(self.col_producto)[self.col_valor].sum()
        
        st.subheader("🏆 Top 50 Productos por Ventas")
        
        # Crear DataFrame comparativo
        df_comp = pd.DataFrame({
            'Producto': df_productos.index,
            'Ventas_Actual': df_productos.values,
            'Ventas_Anterior': [df_productos_anterior.get(p, 0) for p in df_productos.index]
        })
        
        df_comp['Variacion'] = df_comp['Ventas_Actual'] - df_comp['Ventas_Anterior']
        df_comp['Variacion_Pct'] = np.where(
            df_comp['Ventas_Anterior'] > 0,
            (df_comp['Variacion'] / df_comp['Ventas_Anterior']) * 100,
            100
        )
        
        # Mostrar tabla
        st.dataframe(
            df_comp,
            column_config={
                "Producto": "Producto",
                "Ventas_Actual": st.column_config.NumberColumn(f"Ventas {self.filtros['anio_objetivo']}", format="$%d"),
                "Ventas_Anterior": st.column_config.NumberColumn(f"Ventas {self.filtros['anio_base']}", format="$%d"),
                "Variacion": st.column_config.NumberColumn("Variación", format="$%d"),
                "Variacion_Pct": st.column_config.NumberColumn("Var %", format="%.1f%%")
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Gráfico
        st.subheader("📊 Visualización Top 20")
        
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        df_top20 = df_comp.head(20)
        
        fig.add_trace(go.Bar(
            name=f'{self.filtros["anio_base"]}',
            x=df_top20['Producto'],
            y=df_top20['Ventas_Anterior'],
            marker_color='lightblue'
        ))
        
        fig.add_trace(go.Bar(
            name=f'{self.filtros["anio_objetivo"]}',
            x=df_top20['Producto'],
            y=df_top20['Ventas_Actual'],
            marker_color='darkblue'
        ))
        
        fig.update_layout(
            barmode='group',
            title="Comparación de Ventas - Top 20 Productos",
            xaxis_tickangle=-45,
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)


class TabGestionRiesgo(BaseTab):
    """Tab de gestión de riesgo"""
    
    def render(self):
        st.header("⚠️ Gestión de Riesgo")
        st.markdown("Identificación de factores de riesgo comercial.")
        
        # Clientes en decrecimiento
        clientes_actual = self.df_actual.groupby(self.col_cliente)[self.col_valor].sum()
        clientes_anterior = self.df_anterior.groupby(self.col_cliente)[self.col_valor].sum()
        
        df_comp = pd.DataFrame({
            'Actual': clientes_actual,
            'Anterior': clientes_anterior
        }).fillna(0)
        
        df_comp['Variacion'] = df_comp['Actual'] - df_comp['Anterior']
        clientes_riesgo = df_comp[df_comp['Variacion'] < 0].sort_values('Variacion').head(20)
        
        st.subheader("⚠️ Top 20 Clientes en Riesgo")
        st.dataframe(clientes_riesgo.reset_index())


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
        
        venta_2024 = df_2024[self.col_valor].sum()
        venta_2025 = df_2025[self.col_valor].sum()
        
        proyeccion, error = proyectar_ventas_2026(df_2024, df_2025, metodo='conservador')
        
        if proyeccion:
            col1, col2, col3 = st.columns(3)
            
            col1.metric("Ventas 2024", f"${proyeccion['venta_2024']:,.0f}")
            col2.metric("Ventas 2025", f"${proyeccion['venta_2025']:,.0f}")
            col3.metric("Proyección 2026", f"${proyeccion['proyeccion_2026']:,.0f}")
        else:
            st.error(f"Error: {error}")


class TabPortafolioMarcasCategorias(BaseTab):
    """Tab de análisis integral de marcas y categorías"""

    def render(self):
        st.header("🧭 Análisis Integral de Marcas y Categorías")
        self._kpis_portafolio()

        st.markdown("---")
        self._panel_segmento("Marcas", self.col_marca, top_n=12)

        st.markdown("---")
        self._panel_segmento("Categorías", self.col_linea, top_n=12)

        st.markdown("---")
        self._alertas_gerenciales()

        st.markdown("---")
        self._simulador_penetracion()

        st.markdown("---")
        self._insights_ia()

    def _kpis_portafolio(self):
        total_actual = self.df_actual[self.col_valor].sum()
        total_anterior = self.df_anterior[self.col_valor].sum()
        var_abs = total_actual - total_anterior
        var_pct = (var_abs / total_anterior * 100) if total_anterior > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Venta actual", f"${total_actual:,.0f}", f"{var_pct:+.1f}%")
        col2.metric("Venta anterior", f"${total_anterior:,.0f}")
        col3.metric("Diferencia", f"${var_abs:,.0f}", delta_color="inverse" if var_abs < 0 else "normal")
        col4.metric("Clientes activos", f"{self.df_actual[self.col_cliente].nunique():,}")

    def _panel_segmento(self, label: str, col_group: str, top_n: int = 10):
        st.subheader(f"⚡ {label}: Ranking, Pareto y Penetración")
        resumen = self._resumen_crecimiento(col_group)

        # Pareto
        resumen["Acumulado"] = resumen["Actual"].cumsum()
        resumen["%Acumulado"] = resumen["Acumulado"] / resumen["Actual"].sum() * 100

        st.dataframe(
            resumen.head(top_n),
            column_config={
                col_group: label,
                "Actual": st.column_config.NumberColumn("Actual", format="$%d"),
                "Anterior": st.column_config.NumberColumn("Anterior", format="$%d"),
                "Var_abs": st.column_config.NumberColumn("Var Abs", format="$%d"),
                "Var_pct": st.column_config.NumberColumn("Var %", format="%.1f%%"),
                "Clientes": st.column_config.NumberColumn("Clientes", format="%d"),
                "Penetracion": st.column_config.ProgressColumn("Penetración", format="%.1f%%"),
                "%Acumulado": st.column_config.ProgressColumn("% Acumulado", format="%.1f%%"),
                "Impacto": "Impacto"
            },
            use_container_width=True,
            hide_index=True
        )

        col_a, col_b = st.columns([0.55, 0.45])
        with col_a:
            st.markdown(f"Top {top_n} por venta actual")
            fig = px.bar(
                resumen.head(top_n),
                x=col_group,
                y="Actual",
                color="Impacto",
                text_auto=".2s",
                title=f"{label} líderes"
            )
            fig.update_layout(xaxis_tickangle=-35, height=380)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown("Pareto (Acumulado %)")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=resumen.head(top_n)[col_group],
                y=resumen.head(top_n)["Actual"],
                name="Venta",
                marker_color="#3b82f6"
            ))
            fig2.add_trace(go.Scatter(
                x=resumen.head(top_n)[col_group],
                y=resumen.head(top_n)["%Acumulado"],
                name="% Acumulado",
                yaxis="y2",
                mode="lines+markers",
                marker_color="#f59e0b"
            ))
            fig2.update_layout(
                yaxis=dict(title="Venta"),
                yaxis2=dict(title="% Acumulado", overlaying="y", side="right", range=[0, 100]),
                height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig2, use_container_width=True)

    def _resumen_crecimiento(self, col_group: str) -> pd.DataFrame:
        actual = self.df_actual.groupby(col_group)[self.col_valor].sum()
        anterior = self.df_anterior.groupby(col_group)[self.col_valor].sum()
        clientes = self.df_actual.groupby(col_group)[self.col_cliente].nunique() if col_group in self.df_actual else pd.Series(dtype=int)
        total_clientes = self.df_actual[self.col_cliente].nunique()

        df_comp = pd.DataFrame({
            col_group: actual.index,
            "Actual": actual.values,
            "Anterior": [anterior.get(x, 0) for x in actual.index],
            "Clientes": [clientes.get(x, 0) for x in actual.index]
        }).fillna(0)

        df_comp["Var_abs"] = df_comp["Actual"] - df_comp["Anterior"]
        df_comp["Var_pct"] = np.where(
            df_comp["Anterior"] > 0,
            (df_comp["Var_abs"] / df_comp["Anterior"]) * 100,
            100
        )
        df_comp["Penetracion"] = np.where(
            total_clientes > 0,
            df_comp["Clientes"] / total_clientes * 100,
            0
        )
        df_comp["Impacto"] = np.select(
            [
                df_comp["Var_pct"] >= 10,
                df_comp["Var_pct"] <= -10
            ],
            ["MOTOR", "FRENO"],
            default="ESTABLE"
        )
        return df_comp.sort_values("Actual", ascending=False).reset_index(drop=True)

    def _alertas_gerenciales(self):
        st.subheader("🚨 Alertas y Oportunidades Automáticas")
        resumen_m = self._resumen_crecimiento(self.col_marca)
        resumen_c = self._resumen_crecimiento(self.col_linea)

        # Oportunidad: Alta penetración y alto margen (simulado)
        oportunidades = resumen_c[(resumen_c["Penetracion"] < 40) & (resumen_c["Var_pct"] > 10)]
        cuidado = resumen_c[(resumen_c["Var_pct"] < -10) & (resumen_c["Penetracion"] > 30)]

        if not oportunidades.empty:
            st.success(f"**Oportunidad:** {', '.join(oportunidades[self.col_linea].head(3))} tienen baja penetración pero están creciendo rápido.")
        if not cuidado.empty:
            st.warning(f"**Cuidado:** {', '.join(cuidado[self.col_linea].head(3))} están cayendo con alta penetración, requieren plan de acción.")
        if oportunidades.empty and cuidado.empty:
            st.info("No se detectaron alertas críticas en las categorías principales.")

    def _simulador_penetracion(self):
        st.subheader("🧮 Simulador de Escenarios de Penetración")
        resumen_c = self._resumen_crecimiento(self.col_linea)
        total_clientes = self.df_actual[self.col_cliente].nunique()

        categoria_sel = st.selectbox("Selecciona una categoría para simular", resumen_c[self.col_linea])
        row = resumen_c[resumen_c[self.col_linea] == categoria_sel].iloc[0]
        actual_pen = row["Penetracion"]
        actual_venta = row["Actual"]

        st.write(f"Penetración actual: **{actual_pen:.1f}%** ({int(row['Clientes'])} clientes)")
        objetivo_pen = st.slider("Penetración objetivo (%)", min_value=int(actual_pen)+1, max_value=100, value=min(int(actual_pen)+10, 100))
        clientes_objetivo = int(total_clientes * objetivo_pen / 100)
        venta_prom_cliente = actual_venta / row["Clientes"] if row["Clientes"] > 0 else 0
        venta_potencial = venta_prom_cliente * clientes_objetivo

        st.info(f"Si {categoria_sel} llegara a {objetivo_pen}% de penetración, la venta potencial sería **${venta_potencial:,.0f}** (+${venta_potencial-actual_venta:,.0f} vs actual)")

    def _insights_ia(self):
        st.subheader("🤖 Insights de IA sobre Marcas y Categorías")
        # Puedes personalizar el prompt en ai_analysis.py si lo deseas
        metricas = {
            "venta_actual": self.df_actual[self.col_valor].sum(),
            "venta_anterior": self.df_anterior[self.col_valor].sum(),
            "diferencia": self.df_actual[self.col_valor].sum() - self.df_anterior[self.col_valor].sum(),
            "pct_variacion": (
                (self.df_actual[self.col_valor].sum() - self.df_anterior[self.col_valor].sum())
                / self.df_anterior[self.col_valor].sum() * 100
            ) if self.df_anterior[self.col_valor].sum() > 0 else 0
        }
        lineas_presentes = sorted(self.df_actual[self.col_linea].dropna().unique())
        with st.spinner("🧠 Analizando con IA..."):
            analisis = analizar_con_ia_avanzado(self.df_actual, self.df_anterior, metricas, lineas_presentes)
        st.markdown(analisis.get("analisis_ejecutivo", "Sin respuesta de IA."))