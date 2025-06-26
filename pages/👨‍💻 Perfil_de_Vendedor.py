import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import unicodedata

# ==============================================================================
# 1. CONFIGURACIÓN Y ESTADO INICIAL
# ==============================================================================
st.set_page_config(
    page_title="Perfil del Vendedor",
    page_icon="👨‍💻",
    layout="wide"
)

# << AÑADIDO >> Función de normalización para consistencia con la app principal.
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return texto
    try:
        texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto_sin_tildes.upper().replace('-', ' ').strip().replace('  ', ' ')
    except (TypeError, AttributeError):
        return texto

# Bloque de seguridad para verificar autenticación y carga de datos.
if not st.session_state.get('autenticado'):
    st.header("🔒 Acceso Restringido")
    st.warning("Por favor, inicie sesión desde la página principal `🏠 Resumen Mensual` para acceder a esta sección.")
    st.image("https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", width=300)
    st.stop()

df_ventas_historico = st.session_state.get('df_ventas')
APP_CONFIG = st.session_state.get('APP_CONFIG')
DATA_CONFIG = st.session_state.get('DATA_CONFIG')

if df_ventas_historico is None or df_ventas_historico.empty or not APP_CONFIG or not DATA_CONFIG:
    st.error("No se pudieron cargar los datos maestros. Por favor, vuelva a la página principal y asegúrese de haber iniciado sesión correctamente.")
    st.stop()

# ==============================================================================
# 2. LÓGICA DE ANÁLISIS DEL PERFIL (El "Cerebro" de la Página)
# (Sin modificaciones en la lógica de estas funciones)
# ==============================================================================

def calcular_margen(df):
    df_copy = df.copy()
    df_copy['costo_total_linea'] = df_copy['costo_unitario'].fillna(0) * df_copy['unidades_vendidas'].fillna(0)
    df_copy['margen_bruto'] = df_copy['valor_venta'] - df_copy['costo_total_linea']
    df_copy['porcentaje_margen'] = np.where(df_copy['valor_venta'] > 0, (df_copy['margen_bruto'] / df_copy['valor_venta']) * 100, 0)
    return df_copy

@st.cache_data
def analizar_tendencias(df_vendedor):
    df_vendedor_copy = df_vendedor.copy()
    df_vendedor_copy['mes_anio'] = df_vendedor_copy['fecha_venta'].dt.to_period('M')
    df_evolucion = df_vendedor_copy.groupby('mes_anio').agg(
        valor_venta=('valor_venta', 'sum'),
        margen_bruto=('margen_bruto', 'sum')
    ).reset_index()
    df_evolucion['mes_anio'] = df_evolucion['mes_anio'].dt.to_timestamp()

    def calcular_marquilla_local(df_periodo):
        if df_periodo.empty or 'nombre_articulo' not in df_periodo.columns:
            return pd.DataFrame([{'promedio_marquilla': 0}])
        df_temp = df_periodo[['cliente_id', 'nombre_articulo']].copy()
        df_temp['nombre_articulo'] = df_temp['nombre_articulo'].astype(str)
        for palabra in APP_CONFIG['marquillas_clave']:
            df_temp[palabra] = df_temp['nombre_articulo'].str.contains(palabra, case=False)
        df_cliente_marcas = df_temp.groupby('cliente_id')[APP_CONFIG['marquillas_clave']].any()
        df_cliente_marcas['puntaje_marquilla'] = df_cliente_marcas[APP_CONFIG['marquillas_clave']].sum(axis=1)
        return pd.DataFrame([{'promedio_marquilla': df_cliente_marcas['puntaje_marquilla'].mean()}])

    marquilla_mensual = []
    for periodo, df_mes in df_vendedor_copy.groupby('mes_anio'):
        resumen_marquilla_mes = calcular_marquilla_local(df_mes)
        if not resumen_marquilla_mes.empty:
            marquilla_mensual.append({
                'mes_anio': periodo.to_timestamp(),
                'promedio_marquilla': resumen_marquilla_mes['promedio_marquilla'].iloc[0]
            })
    df_marquilla_evolucion = pd.DataFrame(marquilla_mensual)
    if not df_marquilla_evolucion.empty:
        df_evolucion = pd.merge(df_evolucion, df_marquilla_evolucion, on='mes_anio', how='left')

    return df_evolucion.fillna(0)

@st.cache_data
def analizar_clientes(df_vendedor):
    if df_vendedor.empty: return {}
    fecha_max = df_vendedor['fecha_venta'].max()
    mes_actual_inicio = fecha_max.replace(day=1)
    clientes_mes_actual = set(df_vendedor[df_vendedor['fecha_venta'] >= mes_actual_inicio]['cliente_id'].unique())
    clientes_historicos = set(df_vendedor[df_vendedor['fecha_venta'] < mes_actual_inicio]['cliente_id'].unique())
    clientes_nuevos = clientes_mes_actual - clientes_historicos
    clientes_recurrentes = clientes_mes_actual.intersection(clientes_historicos)
    fecha_riesgo = mes_actual_inicio - pd.DateOffset(months=3)
    df_ultima_compra = df_vendedor.groupby('cliente_id')['fecha_venta'].max().reset_index()
    clientes_en_riesgo_ids = set(df_ultima_compra[df_ultima_compra['fecha_venta'] < fecha_riesgo]['cliente_id'].unique())
    clientes_en_riesgo_final_ids = clientes_en_riesgo_ids - clientes_mes_actual
    ventas_por_cliente = df_vendedor.groupby(['cliente_id', 'nombre_cliente'])['valor_venta'].sum().sort_values(ascending=False)
    total_ventas = ventas_por_cliente.sum()
    ventas_por_cliente_acum = ventas_por_cliente.cumsum() / total_ventas * 100 if total_ventas > 0 else ventas_por_cliente
    df_clientes_en_riesgo = df_vendedor[df_vendedor['cliente_id'].isin(clientes_en_riesgo_final_ids)].groupby(
        ['cliente_id', 'nombre_cliente']).agg(valor_venta_total=('valor_venta', 'sum'), ultima_compra=('fecha_venta', 'max')
    ).nlargest(5, 'valor_venta_total').reset_index()
    return {
        "nuevos": len(clientes_nuevos), "recurrentes": len(clientes_recurrentes), "en_riesgo": len(clientes_en_riesgo_final_ids),
        "top_clientes_riesgo": df_clientes_en_riesgo, "concentracion": ventas_por_cliente_acum,
        "top_clientes_volumen": ventas_por_cliente.head(10).reset_index()
    }

@st.cache_data
def analizar_rentabilidad_y_productos(df_vendedor):
    top_productos_margen = df_vendedor.groupby('nombre_articulo')['margen_bruto'].sum().nlargest(5).reset_index()
    bottom_productos_margen = df_vendedor.groupby('nombre_articulo')['margen_bruto'].sum().nsmallest(5).reset_index()
    top_clientes_margen = df_vendedor.groupby(['cliente_id', 'nombre_cliente'])['margen_bruto'].sum().nlargest(10).reset_index()
    distribucion_margen = df_vendedor[df_vendedor['porcentaje_margen'].between(-50, 100)]['porcentaje_margen']
    mix_super_categoria = df_vendedor.groupby('super_categoria')['valor_venta'].sum().reset_index() if 'super_categoria' in df_vendedor.columns else pd.DataFrame()
    mix_marcas = df_vendedor.groupby('nombre_marca')['valor_venta'].sum().reset_index() if 'nombre_marca' in df_vendedor.columns else pd.DataFrame()
    return {
        "top_productos_margen": top_productos_margen, "bottom_productos_margen": bottom_productos_margen,
        "top_clientes_margen": top_clientes_margen, "distribucion_margen": distribucion_margen,
        "mix_super_categoria": mix_super_categoria, "mix_marcas": mix_marcas
    }

def generar_resumen_ejecutivo(vendedor, analisis):
    st.subheader("📝 Resumen Ejecutivo")
    resumen_kpis = analisis['resumen_kpis']
    analisis_clientes = analisis['analisis_clientes']
    with st.container(border=True):
        st.markdown(f"""
        - 💼 **Perfil General**: {vendedor} ha generado un **margen bruto de ${resumen_kpis['margen_total']:,.0f}** sobre **${resumen_kpis['venta_total']:,.0f}** en ventas, resultando en un **margen promedio del {resumen_kpis['porcentaje_margen']:.1f}%**.
        - 📈 **Tendencia**: El análisis mensual muestra la evolución en ventas, rentabilidad y marquilla. Es clave monitorear la consistencia para asegurar un crecimiento sostenido.
        - 👥 **Cartera de Clientes**: En el último mes de actividad, se registraron **{analisis_clientes.get('nuevos', 0)} clientes nuevos** y **{analisis_clientes.get('recurrentes', 0)} clientes recurrentes**. Actualmente, hay **{analisis_clientes.get('en_riesgo', 0)} clientes en riesgo** de fuga.
        - 🎯 **Concentración**: La cartera de clientes presenta un nivel de concentración que debe ser evaluado para mitigar riesgos. Revisa la pestaña de 'Análisis de Clientes' para ver el detalle.
        - 💰 **Rentabilidad**: Identificar los productos y clientes más rentables es crucial. La pestaña 'Análisis de Rentabilidad' ofrece un desglose detallado.
        """)

# ==============================================================================
# 3. LÓGICA DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def render_pestañas_analisis(analisis, vendedor):
    tab1, tab2, tab3, tab4 = st.tabs(["📈 **Tendencias**", "👥 **Análisis de Clientes**", "💰 **Análisis de Rentabilidad**", "📦 **Mix de Productos**"])
    with tab1:
        st.subheader(f"Evolución Mensual de {vendedor}")
        df_evolucion = analisis['analisis_tendencias']
        if not df_evolucion.empty:
            fig = px.line(df_evolucion, x='mes_anio', y='valor_venta', title="Ventas Mensuales", markers=True, labels={"mes_anio": "Mes", "valor_venta": "Ventas ($)"})
            st.plotly_chart(fig, use_container_width=True)
            fig2 = px.line(df_evolucion, x='mes_anio', y='margen_bruto', title="Margen Bruto Mensual", markers=True, color_discrete_sequence=['orange'], labels={"mes_anio": "Mes", "margen_bruto": "Margen ($)"})
            st.plotly_chart(fig2, use_container_width=True)
            if 'promedio_marquilla' in df_evolucion.columns:
                fig3 = px.bar(df_evolucion, x='mes_anio', y='promedio_marquilla', title="Evolución del Promedio de Marquilla", text_auto='.2f', labels={"mes_anio": "Mes", "promedio_marquilla": "Promedio Marquilla"})
                fig3.update_traces(marker_color='lightseagreen'); st.plotly_chart(fig3, use_container_width=True)
        else: st.info("No hay datos de evolución para mostrar en este periodo.")
    with tab2:
        st.subheader("Salud y Composición de la Cartera de Clientes")
        analisis_clientes = analisis['analisis_clientes']
        if analisis_clientes:
            col1, col2, col3 = st.columns(3)
            col1.metric("Clientes Nuevos (Últ. Mes)", f"{analisis_clientes.get('nuevos', 0)} 👤")
            col2.metric("Clientes Recurrentes (Últ. Mes)", f"{analisis_clientes.get('recurrentes', 0)} 🔄")
            col3.metric("Clientes en Riesgo de Fuga", f"{analisis_clientes.get('en_riesgo', 0)} ⚠️")
            st.markdown("---"); st.subheader("Concentración de Ventas (Principio de Pareto)")
            concentracion = analisis_clientes.get('concentracion')
            if concentracion is not None and not concentracion.empty:
                top_5_pct = concentracion.iloc[4] if len(concentracion) >= 5 else 100
                top_10_pct = concentracion.iloc[9] if len(concentracion) >= 10 else 100
                st.info(f"El **Top 5 de clientes representa el {top_5_pct:.1f}%** del total de ventas. El **Top 10 representa el {top_10_pct:.1f}%**.")
                st.dataframe(analisis_clientes.get('top_clientes_volumen', pd.DataFrame()), use_container_width=True, hide_index=True)
            st.markdown("---"); st.subheader("Top 5 Clientes en Riesgo (Mayor Volumen de Compra Histórico)")
            st.dataframe(analisis_clientes.get('top_clientes_riesgo', pd.DataFrame()), use_container_width=True, hide_index=True, column_config={"ultima_compra": st.column_config.DateColumn("Última Compra", format="YYYY-MM-DD")})
    with tab3:
        st.subheader("Análisis de Rentabilidad")
        analisis_rent = analisis['analisis_rentabilidad']
        if analisis_rent:
            st.markdown("##### Distribución del Margen en Ventas")
            if not analisis_rent['distribucion_margen'].empty:
                fig = px.histogram(analisis_rent['distribucion_margen'], title="Frecuencia de Porcentaje de Margen por Venta", labels={"value": "Porcentaje de Margen (%)"})
                st.plotly_chart(fig, use_container_width=True)
                st.info("Este gráfico muestra qué tan seguido se vende con ciertos márgenes. Picos altos en márgenes bajos pueden indicar una política de descuentos agresiva.")
            col1, col2 = st.columns(2)
            with col1: st.markdown("##### ✅ Top 5 Productos Más Rentables"); st.dataframe(analisis_rent['top_productos_margen'], use_container_width=True, hide_index=True)
            with col2: st.markdown("##### ❌ Top 5 Productos Menos Rentables"); st.dataframe(analisis_rent['bottom_productos_margen'], use_container_width=True, hide_index=True)
            st.markdown("---"); st.subheader("Top 10 Clientes por Margen Bruto Generado"); st.dataframe(analisis_rent['top_clientes_margen'], use_container_width=True, hide_index=True)
    with tab4:
        st.subheader("Composición de Ventas (Mix de Portafolio)")
        analisis_mix = analisis['analisis_rentabilidad']
        if analisis_mix:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### Ventas por Super Categoría")
                if not analisis_mix['mix_super_categoria'].empty:
                    fig = px.treemap(
                        analisis_mix['mix_super_categoria'],
                        path=[px.Constant("Todas las Categorías"), 'super_categoria'],
                        values='valor_venta',
                        title='Composición de Ventas por Super Categoría'
                    )
                    fig.update_layout(margin=dict(t=50, l=25, r=25, b=25))
                    st.plotly_chart(fig, use_container_width=True)
                else: 
                    st.info("No hay datos de 'Super Categoría' para mostrar.")
            with col2:
                st.markdown("##### Ventas por Nombre de Marca")
                if not analisis_mix['mix_marcas'].empty:
                    df_marcas = analisis_mix['mix_marcas'].nlargest(10, 'valor_venta')
                    fig = px.bar(df_marcas, x='nombre_marca', y='valor_venta', text_auto='.2s')
                    st.plotly_chart(fig, use_container_width=True)
                else: 
                    st.info("No hay datos de 'Marca' para mostrar.")

# ==============================================================================
# 4. EJECUCIÓN PRINCIPAL DE LA PÁGINA
# ==============================================================================

def render_pagina_perfil():
    st.title("👨‍💻 Perfil de Vendedor y Análisis Estratégico")
    st.markdown("Una vista profunda del rendimiento histórico, rentabilidad y cartera de clientes.")
    st.markdown("---")

    # --- Selector de Vendedor/Grupo (CORREGIDO)---
    vendedores_unicos_norm = sorted(list(df_ventas_historico['nomvendedor'].dropna().unique()))
    grupos = DATA_CONFIG.get('grupos_vendedores', {})
    vendedores_en_grupos_norm = [normalizar_texto(v) for lista in grupos.values() for v in lista]
    
    # Se muestran los nombres originales para una mejor UX
    nombres_grupos = sorted(grupos.keys())
    vendedores_solos = sorted([v_orig for v_orig in df_ventas_historico['nomvendedor'].unique() if normalizar_texto(v_orig) not in vendedores_en_grupos_norm])

    opciones_analisis = nombres_grupos + vendedores_solos
    usuario_actual = st.session_state.usuario
    
    if normalizar_texto(usuario_actual) == "GERENTE":
        opciones_analisis.insert(0, "Seleccione un Vendedor o Grupo")
        # Intenta encontrar al usuario actual en la lista para el default, si no, usa el primero.
        try:
            default_index = opciones_analisis.index(st.session_state.get('last_selection', opciones_analisis[0]))
        except ValueError:
            default_index = 0
    else:
        opciones_analisis = [usuario_actual]
        default_index = 0

    if not opciones_analisis:
        st.warning(f"No se encontraron datos asociados al usuario '{usuario_actual}'.")
        st.stop()
        
    seleccion = st.selectbox("Seleccione el Vendedor o Grupo a analizar:", opciones_analisis, index=default_index, key="perfil_vendedor_selector")
    st.session_state['last_selection'] = seleccion
    
    if seleccion == "Seleccione un Vendedor o Grupo":
        st.info("Por favor, elija un vendedor o grupo para comenzar el análisis.")
        st.stop()

    # --- Filtro de Meses ---
    st.markdown("##### Seleccione el rango de meses para el análisis:")
    df_ventas_historico_copy = df_ventas_historico.copy()
    df_ventas_historico_copy['periodo'] = df_ventas_historico_copy['fecha_venta'].dt.to_period('M')
    meses_disponibles = sorted(df_ventas_historico_copy['periodo'].unique())
    mapa_meses = {f"{DATA_CONFIG['mapeo_meses'].get(p.month, p.month)} {p.year}": p for p in meses_disponibles}
    opciones_slider = list(mapa_meses.keys())
    
    # Define el rango por defecto (últimos 12 meses o todos si son menos)
    start_index = max(0, len(opciones_slider) - 12)
    end_index = len(opciones_slider) - 1
    
    if start_index > end_index:
        start_index = end_index

    mes_inicio_str, mes_fin_str = st.select_slider(
        "Rango de Meses:",
        options=opciones_slider,
        value=(opciones_slider[start_index], opciones_slider[end_index])
    )
    periodo_inicio = mapa_meses[mes_inicio_str]
    periodo_fin = mapa_meses[mes_fin_str]
    fecha_inicio = periodo_inicio.start_time
    fecha_fin = periodo_fin.end_time

    # --- Filtrado de Datos (CORREGIDO) ---
    lista_vendedores_a_filtrar = grupos.get(seleccion, [seleccion])
    lista_vendedores_a_filtrar_norm = [normalizar_texto(v) for v in lista_vendedores_a_filtrar]
    
    df_base = df_ventas_historico[df_ventas_historico['nomvendedor'].isin(lista_vendedores_a_filtrar_norm)]
    df_vendedor = df_base[(df_base['fecha_venta'] >= fecha_inicio) & (df_base['fecha_venta'] <= fecha_fin)]
    
    if df_vendedor.empty:
        st.warning(f"No se encontraron datos para '{seleccion}' en el rango de meses seleccionado.")
        st.stop()
    
    # --- Ejecutar Análisis ---
    with st.spinner(f"Analizando perfil de {seleccion} de {mes_inicio_str} a {mes_fin_str}..."):
        df_vendedor_con_margen = calcular_margen(df_vendedor)
        venta_total = df_vendedor_con_margen['valor_venta'].sum()
        margen_total = df_vendedor_con_margen['margen_bruto'].sum()
        
        analisis_completo = {
            "resumen_kpis": {
                "venta_total": venta_total, "margen_total": margen_total,
                "porcentaje_margen": (margen_total / venta_total * 100) if venta_total > 0 else 0,
                "clientes_unicos": df_vendedor_con_margen['cliente_id'].nunique()
            },
            "analisis_tendencias": analizar_tendencias(df_vendedor_con_margen),
            "analisis_clientes": analizar_clientes(df_vendedor_con_margen),
            "analisis_rentabilidad": analizar_rentabilidad_y_productos(df_vendedor_con_margen)
        }
    
    generar_resumen_ejecutivo(seleccion, analisis_completo)
    st.markdown("---")
    render_pestañas_analisis(analisis_completo, seleccion)

# Ejecuta la función principal de la página
render_pagina_perfil()
