import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ==============================================================================
# 1. CONFIGURACIÓN Y ESTADO INICIAL
# ==============================================================================
st.set_page_config(
    page_title="Acciones y Recomendaciones",
    page_icon="🎯",
    layout="wide"
)

# Verifica la autenticación y la carga de datos
if not st.session_state.get('autenticado'):
    st.header("🔒 Acceso Restringido")
    st.warning("Por favor, inicie sesión desde la página principal `🏠 Resumen Mensual` para acceder a esta sección.")
    st.stop()

df_ventas_historico = st.session_state.get('df_ventas')
df_cobros_historico = st.session_state.get('df_cobros')
APP_CONFIG = st.session_state.get('APP_CONFIG')
DATA_CONFIG = st.session_state.get('DATA_CONFIG')

if df_ventas_historico is None or df_ventas_historico.empty or not APP_CONFIG or not DATA_CONFIG:
    st.error("No se pudieron cargar los datos maestros. Por favor, vuelva a la página principal.")
    st.stop()

# ==============================================================================
# 2. LÓGICA DE ANÁLISIS Y RECOMENDACIONES
# ==============================================================================

def preparar_datos_y_margen(df):
    """
    Separa los descuentos de los productos reales y calcula el margen.
    Esta es la función más importante para la precisión del análisis.
    """
    # Identificar descuentos comerciales. Asumimos que contienen la frase clave.
    filtro_descuento = df['nombre_articulo'].str.contains('descuento comercial', case=False, na=False)
    df_descuentos = df[filtro_descuento]
    df_productos = df[~filtro_descuento]

    # Calcular margen solo para productos reales
    df_productos['costo_total_linea'] = df_productos['costo_unitario'].fillna(0) * df_productos['unidades_vendidas'].fillna(0)
    df_productos['margen_bruto'] = df_productos['valor_venta'] - df_productos['costo_total_linea']

    return df_productos, df_descuentos

def analizar_foco_semana(df_productos, df_descuentos):
    """Genera la lista de tareas priorizadas."""
    recomendaciones = []

    # 1. Cliente en Riesgo a contactar (basado en el análisis de clientes del perfil)
    # Reutilizamos una lógica simplificada aquí
    if not df_productos.empty:
        fecha_riesgo = df_productos['fecha_venta'].max() - pd.DateOffset(months=3)
        df_ultima_compra = df_productos.groupby(['cliente_id', 'nombre_cliente'])['fecha_venta'].max().reset_index()
        clientes_en_riesgo = df_ultima_compra[df_ultima_compra['fecha_venta'] < fecha_riesgo]
        if not clientes_en_riesgo.empty:
            cliente_top_riesgo = clientes_en_riesgo.sort_values(by='fecha_venta').iloc[0]
            recomendaciones.append(f"📞 **Contactar Cliente en Riesgo:** Llama a **{cliente_top_riesgo['nombre_cliente']}**. Su última compra fue el {cliente_top_riesgo['fecha_venta'].strftime('%d-%m-%Y')}.")

    # 2. Oportunidad de Venta Cruzada
    if df_productos.shape[0] > 10: # Solo si hay suficientes datos
        top_clientes = df_productos.groupby('nombre_cliente')['margen_bruto'].sum().nlargest(3).index
        top_productos = df_productos.groupby('nombre_articulo')['margen_bruto'].sum().nlargest(3).index
        cliente_fiel = top_clientes[0]
        ventas_cliente_fiel = df_productos[df_productos['nombre_cliente'] == cliente_fiel]['nombre_articulo'].unique()
        for producto in top_productos:
            if producto not in ventas_cliente_fiel:
                recomendaciones.append(f"📈 **Oportunidad de Oro:** Ofrécele **{producto}** a tu cliente estrella **{cliente_fiel}**. Aún no lo ha comprado.")
                break

    # 3. Alerta de Descuento Alto
    if not df_descuentos.empty:
        descuento_reciente = df_descuentos.sort_values(by='fecha_venta', ascending=False).iloc[0]
        recomendaciones.append(f"⚠️ **Revisar Descuento Reciente:** Se otorgó un descuento de **${abs(descuento_reciente['valor_venta']):,.0f}** a **{descuento_reciente['nombre_cliente']}**. Confirma que esté justificado.")

    return recomendaciones

def analizar_rentabilidad_y_descuentos(df_productos, df_descuentos):
    """Realiza el análisis de rentabilidad separando los descuentos."""
    venta_bruta = df_productos['valor_venta'].sum()
    margen_bruto_productos = df_productos['margen_bruto'].sum()
    total_descuentos = abs(df_descuentos['valor_venta'].sum())
    margen_operativo = margen_bruto_productos - total_descuentos
    porcentaje_descuento = (total_descuentos / venta_bruta * 100) if venta_bruta > 0 else 0
    
    # Gráfico de evolución
    df_productos['mes_anio'] = df_productos['fecha_venta'].dt.to_period('M')
    df_descuentos['mes_anio'] = df_descuentos['fecha_venta'].dt.to_period('M')
    
    margen_bruto_mensual = df_productos.groupby('mes_anio')['margen_bruto'].sum()
    descuentos_mensual = abs(df_descuentos.groupby('mes_anio')['valor_venta'].sum())
    
    df_evolucion = pd.DataFrame(margen_bruto_mensual).reset_index()
    df_evolucion = pd.merge(df_evolucion, pd.DataFrame(descuentos_mensual).reset_index(), on='mes_anio', how='outer').fillna(0)
    df_evolucion['margen_operativo'] = df_evolucion['margen_bruto'] - df_evolucion['valor_venta']
    df_evolucion['mes_anio'] = df_evolucion['mes_anio'].dt.to_timestamp()

    # Top clientes por descuento
    top_clientes_descuento = abs(df_descuentos.groupby('nombre_cliente')['valor_venta'].sum()).nlargest(5).reset_index()

    return {
        "venta_bruta": venta_bruta, "margen_bruto_productos": margen_bruto_productos,
        "total_descuentos": total_descuentos, "margen_operativo": margen_operativo,
        "porcentaje_descuento": porcentaje_descuento, "df_evolucion": df_evolucion,
        "top_clientes_descuento": top_clientes_descuento
    }

def analizar_desarrollo_cartera(df_productos):
    """Genera el mapa de oportunidades de venta cruzada."""
    if df_productos.shape[0] < 20: return pd.DataFrame() # No analizar si hay muy pocos datos

    top_10_clientes = df_productos.groupby('nombre_cliente')['valor_venta'].sum().nlargest(10).index
    top_10_productos = df_productos.groupby('nombre_articulo')['valor_venta'].sum().nlargest(10).index

    df_filtrado = df_productos[(df_productos['nombre_cliente'].isin(top_10_clientes)) & (df_productos['nombre_articulo'].isin(top_10_productos))]
    
    mapa_oportunidades = pd.crosstab(df_filtrado['nombre_cliente'], df_filtrado['nombre_articulo'])
    mapa_oportunidades = mapa_oportunidades.applymap(lambda x: "✅" if x > 0 else "➕ Oportunidad")

    return mapa_oportunidades

# ==============================================================================
# 3. LÓGICA DE LA INTERFAZ DE USUARIO (UI)
# ==============================================================================

def render_pagina_acciones():
    st.title("🎯 Acciones y Recomendaciones")
    st.markdown("Planes de acción inteligentes basados en tus datos para impulsar los resultados.")
    st.markdown("---")
    
    # Selector de vendedor (reutilizado de la página de perfil)
    lista_vendedores = sorted(list(df_ventas_historico['nomvendedor'].dropna().unique()))
    vendedores_en_grupos = [v for lista in DATA_CONFIG['grupos_vendedores'].values() for v in lista]
    vendedores_solos = [v for v in lista_vendedores if v not in vendedores_en_grupos]
    opciones_analisis = list(DATA_CONFIG['grupos_vendedores'].keys()) + vendedores_solos
    usuario_actual = st.session_state.usuario
    if usuario_actual == "GERENTE":
        opciones_analisis.insert(0, "Seleccione un Vendedor o Grupo")
        default_index = 0
    else:
        opciones_analisis = [usuario_actual] if usuario_actual in opciones_analisis else []
        default_index = 0
    if not opciones_analisis: st.warning(f"No se encontraron datos asociados al usuario '{usuario_actual}'."); st.stop()
    seleccion = st.selectbox("Seleccione el Vendedor o Grupo a analizar:", opciones_analisis, index=default_index)
    if seleccion == "Seleccione un Vendedor o Grupo": st.info("Por favor, elija un vendedor para comenzar el análisis."); st.stop()
    
    # Filtrado de datos para el vendedor seleccionado
    if seleccion in DATA_CONFIG['grupos_vendedores']:
        df_vendedor = df_ventas_historico[df_ventas_historico['nomvendedor'].isin(DATA_CONFIG['grupos_vendedores'][seleccion])]
    else:
        df_vendedor = df_ventas_historico[df_ventas_historico['nomvendedor'] == seleccion]

    if df_vendedor.empty: st.warning(f"No se encontraron datos para '{seleccion}'."); st.stop()
        
    # --- Ejecutar Análisis ---
    with st.spinner(f"Generando plan de acción para {seleccion}..."):
        df_productos, df_descuentos = preparar_datos_y_margen(df_vendedor.copy())
        recomendaciones_foco = analizar_foco_semana(df_productos, df_descuentos)
        analisis_rentabilidad = analizar_rentabilidad_y_descuentos(df_productos, df_descuentos)
        mapa_oportunidades = analizar_desarrollo_cartera(df_productos)

    # --- Renderizar Módulos ---

    # Módulo 1: Foco de la Semana
    st.header("⚡ Foco de la Semana: Tu Plan de Acción Inmediato")
    with st.container(border=True):
        if recomendaciones_foco:
            for i, rec in enumerate(recomendaciones_foco):
                st.checkbox(rec, key=f"rec_{i}")
        else:
            st.success("¡Excelente trabajo! No hay alertas urgentes en este momento.")

    # Módulo 2: Optimización de Rentabilidad y Descuentos
    st.header("💰 Optimización de Rentabilidad y Descuentos")
    st.subheader("Análisis del Impacto del Descuento Comercial")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Margen Bruto de Productos", f"${analisis_rentabilidad['margen_bruto_productos']:,.0f}")
    col2.metric("Total Descuentos Otorgados", f"-${analisis_rentabilidad['total_descuentos']:,.0f}")
    col3.metric("Margen Operativo Real", f"${analisis_rentabilidad['margen_operativo']:,.0f}")
    col4.metric("% Descuento sobre Venta", f"{analisis_rentabilidad['porcentaje_descuento']:.1f}%")

    df_evo = analisis_rentabilidad['df_evolucion']
    if not df_evo.empty:
        fig = px.line(df_evo, x='mes_anio', y=['margen_bruto', 'margen_operativo'], title="Evolución de Margen Bruto vs. Margen Operativo", labels={"value": "Monto ($)", "mes_anio": "Mes"})
        fig.update_layout(legend_title_text='Leyenda')
        st.plotly_chart(fig, use_container_width=True)
        st.info("La brecha entre las dos líneas representa el total de descuentos comerciales otorgados cada mes.")

    st.subheader("Clientes con Mayor Descuento Otorgado")
    st.dataframe(analisis_rentabilidad['top_clientes_descuento'], use_container_width=True, hide_index=True)
    
    # Módulo 3: Desarrollo de Cartera
    st.header("👥 Desarrollo de Cartera: Oportunidades Ocultas")
    st.subheader("Mapa de Oportunidades de Venta Cruzada (Cross-Sell)")
    if not mapa_oportunidades.empty:
        st.dataframe(mapa_oportunidades, use_container_width=True)
        st.info("Revisa la tabla: '✅' significa que el cliente ya compra ese producto. '➕ Oportunidad' es tu señal para ofrecerlo.")
    else:
        st.info("No hay suficientes datos para generar un mapa de oportunidades detallado.")

# ==============================================================================
# 4. EJECUCIÓN PRINCIPAL
# ==============================================================================
render_pagina_acciones()
