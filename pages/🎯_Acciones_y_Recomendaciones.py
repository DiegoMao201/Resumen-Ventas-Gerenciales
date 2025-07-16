# ==============================================================================
# SCRIPT COMPLETO Y RECONSTRUIDO PARA: pages/1_Acciones_y_Recomendaciones.py
# VERSIÓN: 16 de Julio, 2025
# DESCRIPCIÓN: Este script crea una página de análisis profundo, basándose
#              en la lógica del archivo principal. Ofrece análisis de
#              rentabilidad, segmentación de clientes (RFM), análisis de
#              portafolio de productos (Matriz BCG), y un análisis de
#              dispersión de clientes para identificar oportunidades.
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import io
import unicodedata
from datetime import datetime

# ==============================================================================
# SECCIÓN 1: CONFIGURACIÓN INICIAL Y CARGA DE DATOS
# ==============================================================================

st.set_page_config(page_title="Plan de Acción Estratégico", page_icon="🎯", layout="wide")

# Función de normalización (debe ser idéntica a la del script principal)
def normalizar_texto(texto):
    """
    Normaliza un texto a mayúsculas, sin tildes ni caracteres especiales.
    """
    if not isinstance(texto, str):
        return texto
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').strip().replace('  ', ' ')
    except (TypeError, AttributeError):
        return texto

def mostrar_acceso_restringido():
    """Muestra un mensaje si el usuario no ha iniciado sesión."""
    st.header("🔒 Acceso Restringido")
    st.warning("Por favor, inicie sesión desde la página principal `🏠 Resumen Mensual` para continuar.")
    logo_url = st.session_state.get('APP_CONFIG', {}).get('url_logo', "https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png")
    st.image(logo_url, width=300)
    st.stop()

# --- Verificación del estado de la sesión ---
if not st.session_state.get('autenticado'):
    mostrar_acceso_restringido()

# --- Carga de datos y configuraciones desde la sesión principal ---
# Esta es la conexión clave con tu script principal 'Resumen Mensual.py'
df_ventas_historico = st.session_state.get('df_ventas')
APP_CONFIG = st.session_state.get('APP_CONFIG')
DATA_CONFIG = st.session_state.get('DATA_CONFIG')

# --- Validación de datos cargados ---
if df_ventas_historico is None or df_ventas_historico.empty or not APP_CONFIG or not DATA_CONFIG:
    st.error("Error Crítico: No se pudieron cargar los datos desde la sesión.")
    st.warning("Por favor, regrese a la página '🏠 Resumen Mensual', asegúrese de que los datos se carguen correctamente y luego vuelva a esta página.")
    st.stop()


# ==============================================================================
# SECCIÓN 2: FUNCIONES DE ANÁLISIS DE NEGOCIO (EL "CEREBRO")
# ==============================================================================

@st.cache_data
def preparar_datos_analisis(df_bruto):
    """
    Filtra los datos para incluir solo ventas netas (Facturas y Notas de Crédito)
    y separa los productos de los descuentos comerciales.
    """
    df = df_bruto.copy()
    
    # 1. Filtrar por tipo de documento para obtener ventas netas
    filtro_ventas_netas = df['TipoDocumento'].str.contains('FACTURA|NOTA.*CREDITO', na=False, regex=True)
    df_neto = df[filtro_ventas_netas].copy()

    # 2. Identificar y separar los descuentos comerciales
    # Se utiliza una columna normalizada temporal para una comparación robusta.
    df_neto['nombre_articulo_norm'] = df_neto['nombre_articulo'].apply(normalizar_texto)
    filtro_descuento = df_neto['nombre_articulo_norm'] == 'DESCUENTOS COMERCIALES'
    
    df_descuentos = df_neto[filtro_descuento].copy()
    df_productos = df_neto[~filtro_descuento].copy()

    # 3. Calcular el margen bruto a nivel de línea de producto
    if not df_productos.empty:
        df_productos['costo_unitario'] = pd.to_numeric(df_productos['costo_unitario'], errors='coerce').fillna(0)
        df_productos['unidades_vendidas'] = pd.to_numeric(df_productos['unidades_vendidas'], errors='coerce').fillna(0)
        df_productos['valor_venta'] = pd.to_numeric(df_productos['valor_venta'], errors='coerce').fillna(0)
        
        df_productos['costo_total_linea'] = df_productos['costo_unitario'] * df_productos['unidades_vendidas']
        df_productos['margen_bruto_linea'] = df_productos['valor_venta'] - df_productos['costo_total_linea']
        df_productos['rentabilidad_linea'] = (df_productos['margen_bruto_linea'] / df_productos['valor_venta'].replace(0, np.nan)) * 100

    return df_productos, df_descuentos

@st.cache_data
def analizar_rentabilidad_total(df_productos, df_descuentos):
    """
    Calcula las métricas de rentabilidad clave para el período seleccionado.
    """
    venta_neta_productos = df_productos['valor_venta'].sum()
    total_descuentos = abs(df_descuentos['valor_venta'].sum())
    venta_bruta_reconstruida = venta_neta_productos + total_descuentos
    margen_bruto_total = df_productos['margen_bruto_linea'].sum()
    margen_operativo_real = margen_bruto_total - total_descuentos
    
    rentabilidad_bruta_ponderada = (margen_bruto_total / venta_neta_productos * 100) if venta_neta_productos > 0 else 0
    rentabilidad_operativa_ponderada = (margen_operativo_real / venta_bruta_reconstruida * 100) if venta_bruta_reconstruida > 0 else 0
    
    return {
        "venta_neta": venta_neta_productos,
        "total_descuentos": total_descuentos,
        "venta_bruta": venta_bruta_reconstruida,
        "margen_bruto": margen_bruto_total,
        "margen_operativo": margen_operativo_real,
        "rentabilidad_bruta_pct": rentabilidad_bruta_ponderada,
        "rentabilidad_operativa_pct": rentabilidad_operativa_ponderada
    }

@st.cache_data
def analizar_segmentacion_rfm(df_productos, fecha_fin_analisis):
    """
    Realiza un análisis RFM (Recencia, Frecuencia, Monetario) para segmentar clientes.
    """
    if df_productos.empty:
        return pd.DataFrame(columns=['nombre_cliente', 'Recencia', 'Frecuencia', 'Monetario', 'Segmento_RFM'])
        
    df_rfm = df_productos.groupby('nombre_cliente').agg(
        Recencia=('fecha_venta', lambda date: (fecha_fin_analisis - date.max()).days),
        Frecuencia=('Serie', 'nunique'), # Contar facturas únicas
        Monetario=('valor_venta', 'sum')
    ).reset_index()

    if len(df_rfm) < 4: return df_rfm # No se puede calcular si hay muy pocos clientes

    # Asignar puntajes basados en cuantiles
    df_rfm['R_Score'] = pd.qcut(df_rfm['Recencia'], 4, labels=[4, 3, 2, 1], duplicates='drop')
    df_rfm['F_Score'] = pd.qcut(df_rfm['Frecuencia'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop')
    df_rfm['M_Score'] = pd.qcut(df_rfm['Monetario'].rank(method='first'), 4, labels=[1, 2, 3, 4], duplicates='drop')
    df_rfm['RFM_Score'] = df_rfm['R_Score'].astype(str) + df_rfm['F_Score'].astype(str) + df_rfm['M_Score'].astype(str)

    # Mapeo de segmentos
    mapa_segmentos = {
        r'[3-4][3-4][3-4]': '🏆 Campeones',
        r'[3-4][1-2][3-4]': '💰 Grandes Compradores',
        r'[3-4][3-4][1-2]': '💖 Leales Recientes',
        r'1[3-4][3-4]': '😬 En Riesgo de Abandono',
        r'[1-2][1-2][1-2]': '😥 Hibernando',
        r'[1-2][3-4][1-2]': '😕 Clientes de Baja Compra',
        r'41[1-4]': '🌱 Nuevos Potenciales'
    }
    df_rfm['Segmento_RFM'] = df_rfm['R_Score'].astype(str) + df_rfm['F_Score'].astype(str)
    df_rfm['Segmento_RFM'] = df_rfm['Segmento_RFM'].replace({r'^[3-4][3-4]$': '🏆 Campeones', r'^[3-4][1-2]$': '🌱 Nuevos o Potenciales', r'^[1-2][3-4]$': '😬 En Riesgo', r'^[1-2][1-2]$': '😥 Hibernando'}, regex=True)
    df_rfm.loc[df_rfm['Segmento_RFM'].str.match(r'^\d{2}$'), 'Segmento_RFM'] = 'Otros'
    
    return df_rfm[['nombre_cliente', 'Recencia', 'Frecuencia', 'Monetario', 'Segmento_RFM']].sort_values('Monetario', ascending=False)

@st.cache_data
def analizar_matriz_bcg(df_productos):
    """
    Crea una Matriz BCG (Boston Consulting Group) para clasificar el portafolio de productos.
    """
    if df_productos.empty:
        return pd.DataFrame()
        
    df_matriz = df_productos.groupby('nombre_articulo').agg(
        Volumen_Venta=('valor_venta', 'sum'),
        Margen_Absoluto=('margen_bruto_linea', 'sum')
    ).reset_index()
    
    df_matriz = df_matriz[(df_matriz['Volumen_Venta'] > 0) & (df_matriz['Margen_Absoluto'].notna())]
    if df_matriz.empty: return pd.DataFrame()

    df_matriz['Rentabilidad_Pct'] = (df_matriz['Margen_Absoluto'] / df_matriz['Volumen_Venta']) * 100
    
    # Usar la mediana como punto de corte
    vol_medio = df_matriz['Volumen_Venta'].median()
    rent_media = df_matriz['Rentabilidad_Pct'].median()

    def clasificar_bcg(row):
        if row['Volumen_Venta'] >= vol_medio and row['Rentabilidad_Pct'] >= rent_media:
            return '⭐ Estrella'
        if row['Volumen_Venta'] >= vol_medio and row['Rentabilidad_Pct'] < rent_media:
            return '🐄 Vaca Lechera'
        if row['Volumen_Venta'] < vol_medio and row['Rentabilidad_Pct'] >= rent_media:
            return '❓ Interrogante'
        return '🐕 Perro'

    df_matriz['Segmento_BCG'] = df_matriz.apply(clasificar_bcg, axis=1)
    return df_matriz

def generar_excel_completo(datos_exportar):
    """Crea un archivo Excel con múltiples hojas a partir de un diccionario de DataFrames."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for nombre_hoja, df in datos_exportar.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                df.to_excel(writer, sheet_name=nombre_hoja, index=False)
    return output.getvalue()

# ==============================================================================
# SECCIÓN 3: INTERFAZ DE USUARIO Y VISUALIZACIONES
# ==============================================================================
def render_pagina_acciones():
    st.title("🎯 Plan de Acción Estratégico")
    st.markdown("Análisis profundo para la toma de decisiones. Explore la rentabilidad, clientes y productos para descubrir oportunidades de crecimiento.")

    # --- FILTROS DE LA PÁGINA ---
    st.sidebar.title("Filtros del Análisis")
    
    # Selección de Vendedor/Grupo (lógica heredada del script principal)
    vendedores_unicos_norm = sorted(list(df_ventas_historico['nomvendedor'].dropna().unique()))
    grupos = DATA_CONFIG.get('grupos_vendedores', {})
    vendedores_en_grupos_norm = [normalizar_texto(v) for lista in grupos.values() for v in lista]
    mapa_norm_a_orig = {normalizar_texto(v): v for v in df_ventas_historico['nomvendedor'].dropna().unique()}
    vendedores_solos_norm = [v_norm for v_norm in vendedores_unicos_norm if v_norm not in vendedores_en_grupos_norm]
    vendedores_solos_orig = sorted([mapa_norm_a_orig.get(v_norm) for v_norm in vendedores_solos_norm if mapa_norm_a_orig.get(v_norm)])
    nombres_grupos = sorted(grupos.keys())
    opciones_analisis = ["TODOS (VISIÓN GERENCIAL)"] + nombres_grupos + vendedores_solos_orig
    
    usuario_actual = st.session_state.usuario
    if normalizar_texto(usuario_actual) == "GERENTE":
        default_index = 0
    else:
        try:
            default_index = opciones_analisis.index(usuario_actual)
        except ValueError:
            opciones_analisis.insert(1, usuario_actual)
            default_index = 1

    seleccion = st.sidebar.selectbox("Seleccione Vendedor o Grupo a analizar:", opciones_analisis, index=default_index)

    # Selección de Rango de Fechas
    fecha_min = df_ventas_historico['fecha_venta'].min().date()
    fecha_max = df_ventas_historico['fecha_venta'].max().date()
    
    fecha_inicio, fecha_fin = st.sidebar.date_input(
        "Seleccione el rango de fechas:",
        value=(fecha_max.replace(day=1), fecha_max),
        min_value=fecha_min,
        max_value=fecha_max,
        key="date_range_selector"
    )

    if not fecha_inicio or not fecha_fin or fecha_inicio > fecha_fin:
        st.sidebar.error("Rango de fechas inválido. Por favor, seleccione un rango correcto.")
        st.stop()
    
    # --- PROCESAMIENTO DE DATOS CON FILTROS ---
    with st.spinner(f"Analizando datos para '{seleccion}'..."):
        # Filtrar DataFrame base según la selección
        if seleccion == "TODOS (VISIÓN GERENCIAL)":
            df_filtrado_vendedor = df_ventas_historico
        else:
            lista_vendedores_filtrar = grupos.get(seleccion, [seleccion])
            df_filtrado_vendedor = df_ventas_historico[df_ventas_historico['nomvendedor'].isin([normalizar_texto(v) for v in lista_vendedores_filtrar])]

        # Filtrar por rango de fecha
        fecha_inicio_dt = pd.to_datetime(fecha_inicio)
        fecha_fin_dt = pd.to_datetime(fecha_fin)
        df_periodo = df_filtrado_vendedor[(df_filtrado_vendedor['fecha_venta'] >= fecha_inicio_dt) & (df_filtrado_vendedor['fecha_venta'] <= fecha_fin_dt)]

        if df_periodo.empty:
            st.warning(f"No se encontraron datos de ventas para '{seleccion}' en el período seleccionado.")
            st.stop()

        # Ejecutar todas las funciones de análisis
        df_productos, df_descuentos = preparar_datos_analisis(df_periodo)
        analisis_rentabilidad = analizar_rentabilidad_total(df_productos, df_descuentos)
        df_rfm = analizar_segmentacion_rfm(df_productos, fecha_fin_dt)
        df_bcg = analizar_matriz_bcg(df_productos)
        
        # Preparar datos para el gráfico de dispersión de clientes
        df_dispersion_clientes = df_productos.groupby('nombre_cliente').agg(
            Frecuencia=('Serie', 'nunique'),
            Ticket_Promedio=('valor_venta', 'mean'),
            Venta_Total=('valor_venta', 'sum')
        ).reset_index()

    # Botón de descarga
    datos_para_exportar = {
        "Analisis_Rentabilidad": pd.DataFrame([analisis_rentabilidad]),
        "Segmentacion_Clientes_RFM": df_rfm,
        "Matriz_Productos_BCG": df_bcg,
        "Detalle_Productos_Vendidos": df_productos,
        "Detalle_Descuentos": df_descuentos
    }
    st.download_button(
        label="📥 Descargar Análisis Completo en Excel",
        data=generar_excel_completo(datos_para_exportar),
        file_name=f"Analisis_Estrategico_{seleccion.replace(' ', '_')}_{fecha_inicio}_a_{fecha_fin}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")

    # --- PESTAÑAS DE ANÁLISIS ---
    tab1, tab2, tab3, tab4 = st.tabs(["💰 Análisis de Rentabilidad", "👥 Análisis de Clientes", "📦 Análisis de Productos", "💡 Recomendaciones Clave"])

    with tab1:
        st.header("Análisis de Rentabilidad y Descuentos")
        st.info(f"Análisis para **{seleccion}** desde el **{fecha_inicio.strftime('%d/%m/%Y')}** hasta el **{fecha_fin.strftime('%d/%m/%Y')}**.")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Venta Neta de Productos", f"${analisis_rentabilidad['venta_neta']:,.0f}")
        col2.metric("Descuentos Otorgados", f"-${analisis_rentabilidad['total_descuentos']:,.0f}")
        col3.metric("Venta Bruta (Reconstruida)", f"${analisis_rentabilidad['venta_bruta']:,.0f}")
        
        col4, col5, col6 = st.columns(3)
        col4.metric("Margen Bruto Total", f"${analisis_rentabilidad['margen_bruto']:,.0f}", f"{analisis_rentabilidad['rentabilidad_bruta_pct']:.1f}% Rentabilidad")
        col5.metric("Margen Operativo Real", f"${analisis_rentabilidad['margen_operativo']:,.0f}", f"{analisis_rentabilidad['rentabilidad_operativa_pct']:.1f}% Rentabilidad")
        
        if not df_descuentos.empty:
            st.subheader("Análisis de Descuentos Otorgados")
            top_clientes_dcto = df_descuentos.groupby('nombre_cliente')['valor_venta'].sum().abs().nlargest(10).reset_index()
            fig_dcto = px.bar(top_clientes_dcto, x='valor_venta', y='nombre_cliente', orientation='h',
                              title="Top 10 Clientes con Mayor Descuento",
                              labels={'valor_venta': 'Monto Descuento ($)', 'nombre_cliente': 'Cliente'},
                              text='valor_venta')
            fig_dcto.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
            fig_dcto.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_dcto, use_container_width=True)

    with tab2:
        st.header("Segmentación Estratégica de Clientes")
        
        st.subheader("Análisis RFM (Recencia, Frecuencia, Monetario)")
        if not df_rfm.empty:
            col1, col2 = st.columns([0.6, 0.4])
            with col1:
                st.markdown("Clasifica a tus clientes para personalizar estrategias:")
                st.markdown("- **🏆 Campeones:** Tus mejores clientes. ¡Fidelízalos!")
                st.markdown("- **😬 En Riesgo:** Han comprado bien, pero hace tiempo no vuelven. ¡Re actívalos!")
                st.markdown("- **🌱 Nuevos o Potenciales:** Recientes o de baja frecuencia. ¡Hazlos crecer!")
                st.markdown("- **😥 Hibernando:** Clientes perdidos. ¿Vale la pena recuperarlos?")
                
                fig_rfm = px.pie(df_rfm, names='Segmento_RFM', title="Distribución de Clientes por Segmento RFM", hole=0.3)
                st.plotly_chart(fig_rfm, use_container_width=True)

            with col2:
                st.dataframe(df_rfm, use_container_width=True, height=500)
        else:
            st.warning("No hay suficientes datos de clientes para realizar el análisis RFM.")

        st.markdown("---")
        st.subheader("Dispersión de Clientes: Frecuencia vs. Ticket Promedio")
        if not df_dispersion_clientes.empty:
            fig_disp = px.scatter(df_dispersion_clientes, x="Ticket_Promedio", y="Frecuencia",
                                  size="Venta_Total", color="Venta_Total",
                                  hover_name="nombre_cliente", log_x=True, size_max=60,
                                  title="Mapa de Valor de Clientes",
                                  labels={"Ticket_Promedio": "Ticket Promedio de Compra ($)", "Frecuencia": "N° de Compras"})
            st.plotly_chart(fig_disp, use_container_width=True)

    with tab3:
        st.header("Estrategia de Portafolio de Productos (Matriz BCG)")
        st.info("Clasifica tus productos para optimizar el enfoque de ventas y marketing. Pasa el mouse sobre las burbujas para ver el detalle.")
        
        if not df_bcg.empty:
            fig_bcg = px.scatter(df_bcg, x="Volumen_Venta", y="Rentabilidad_Pct",
                                 size="Margen_Absoluto", color="Segmento_BCG",
                                 hover_name="nombre_articulo", log_x=True, size_max=60,
                                 title="Matriz de Rendimiento de Productos (BCG)",
                                 labels={"Volumen_Venta": "Volumen de Venta Neta ($)", "Rentabilidad_Pct": "Rentabilidad (%)"},
                                 color_discrete_map={'⭐ Estrella': 'gold', '🐄 Vaca Lechera': 'dodgerblue', '❓ Interrogante': 'limegreen', '🐕 Perro': 'tomato'})
            st.plotly_chart(fig_bcg, use_container_width=True)
            
            st.subheader("Explorar Datos por Segmento BCG")
            segmento_sel = st.selectbox("Selecciona un segmento para ver el detalle:", sorted(df_bcg['Segmento_BCG'].unique()))
            df_bcg_filtrado = df_bcg[df_bcg['Segmento_BCG'] == segmento_sel].sort_values('Volumen_Venta', ascending=False)
            st.dataframe(df_bcg_filtrado, height=400, use_container_width=True,
                         column_config={
                             "Volumen_Venta": st.column_config.NumberColumn("Venta Neta", format="$ %d"),
                             "Margen_Absoluto": st.column_config.NumberColumn("Margen Bruto", format="$ %d"),
                             "Rentabilidad_Pct": st.column_config.ProgressColumn("Rentabilidad", format="%.1f%%", min_value=df_bcg['Rentabilidad_Pct'].min(), max_value=df_bcg['Rentabilidad_Pct'].max())
                         })
        else:
            st.warning("No hay suficientes datos de productos para generar la matriz BCG en este período.")

    with tab4:
        st.header("💡 Recomendaciones Estratégicas Clave")
        st.markdown("Basado en los análisis, aquí tienes un plan de acción sugerido:")

        # Recomendaciones de Rentabilidad
        with st.container(border=True):
            st.subheader("🎯 Rentabilidad y Descuentos")
            if analisis_rentabilidad['total_descuentos'] / analisis_rentabilidad['venta_bruta'] > 0.05: # Si los descuentos son más del 5%
                 st.warning(f"**Atención:** Los descuentos representan un {analisis_rentabilidad['total_descuentos']/analisis_rentabilidad['venta_bruta']:.1%} de la venta bruta. Revisa las políticas de descuento, especialmente con los clientes que reciben los montos más altos, para proteger el margen operativo.")
            else:
                 st.success("**Buen Control:** La política de descuentos parece controlada. Continúa monitoreando para mantener la salud del margen.")
            st.info("**Acción:** Identifica los productos 'Vaca Lechera' y 'Perro' en la matriz BCG. Busca oportunidades para mejorar su rentabilidad, ya sea ajustando precios, negociando costos o reduciendo su visibilidad si no son estratégicos.")

        # Recomendaciones de Clientes
        with st.container(border=True):
            st.subheader("👥 Clientes")
            if not df_rfm.empty:
                campeones = df_rfm[df_rfm['Segmento_RFM'] == '🏆 Campeones']
                en_riesgo = df_rfm[df_rfm['Segmento_RFM'] == '😬 En Riesgo']
                st.success(f"**Fidelizar:** Tienes **{len(campeones)} clientes Campeones**. Lanza un programa de lealtad exclusivo para ellos, ofréceles acceso anticipado a productos o un servicio premium. ¡No los descuides!")
                if not en_riesgo.empty:
                    st.warning(f"**Reactivar:** Hay **{len(en_riesgo)} clientes En Riesgo**. Crea una campaña de reactivación con una oferta atractiva para su próxima compra. Averigua por qué no han vuelto.")
            st.info("**Acción:** Usa el gráfico de dispersión. Los clientes con alta frecuencia pero bajo ticket promedio son ideales para estrategias de venta cruzada (cross-selling). Ofréceles productos complementarios a lo que ya compran.")

        # Recomendaciones de Productos
        with st.container(border=True):
            st.subheader("📦 Productos")
            if not df_bcg.empty:
                interrogantes = df_bcg[df_bcg['Segmento_BCG'] == '❓ Interrogante']
                perros = df_bcg[df_bcg['Segmento_BCG'] == '🐕 Perro']
                st.success(f"**Impulsar:** Identificaste **{len(interrogantes)} productos Interrogante** (alta rentabilidad, baja venta). Son tus mayores oportunidades. Destácalos en el punto de venta, capacita al equipo sobre sus beneficios y considera invertir en marketing para aumentar su volumen.")
                if not perros.empty:
                    st.warning(f"**Evaluar:** Hay **{len(perros)} productos Perro** (baja rentabilidad, baja venta). Analiza si son necesarios para completar el portafolio. Si no, considera deslistarlos para simplificar la operación y enfocar esfuerzos en productos más rentables.")
            st.info("**Acción:** Revisa los productos 'Estrella'. Asegúrate de tener siempre inventario disponible. Son la base de tu negocio y no puedes permitirte quiebres de stock.")


# --- Ejecución Principal de la Página ---
if __name__ == "__main__":
    render_pagina_acciones()
