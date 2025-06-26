import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import io
import unicodedata # << AÑADIDO >> Import necesario para la normalización

# ==============================================================================
# 1. CONFIGURACIÓN Y ESTADO INICIAL
# ==============================================================================
st.set_page_config(page_title="Acciones y Recomendaciones", page_icon="🎯", layout="wide")

# << AÑADIDO >> Se incluye la misma función de normalización de la página principal
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return texto
    texto_sin_tildes = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sin_tildes.upper().replace('-', ' ').strip().replace('  ', ' ')

def mostrar_acceso_restringido():
    st.header("🔒 Acceso Restringido")
    st.warning("Por favor, inicie sesión desde la página principal `🏠 Resumen Mensual`.")
    st.image("https://raw.githubusercontent.com/DiegoMao201/Resumen-Ventas-Gerenciales/main/LOGO%20FERREINOX%20SAS%20BIC%202024.png", width=300)
    st.stop()

if not st.session_state.get('autenticado'):
    mostrar_acceso_restringido()

# Carga segura de datos desde el estado de la sesión
df_ventas_historico = st.session_state.get('df_ventas')
APP_CONFIG = st.session_state.get('APP_CONFIG')
DATA_CONFIG = st.session_state.get('DATA_CONFIG')

if df_ventas_historico is None or df_ventas_historico.empty or not APP_CONFIG or not DATA_CONFIG:
    st.error("No se pudieron cargar los datos maestros. Vuelva a la página principal.")
    st.stop()

# ==============================================================================
# 2. LÓGICA DE ANÁLISIS Y RECOMENDACIONES (El "Cerebro")
# (Sin modificaciones en esta sección)
# ==============================================================================

@st.cache_data
def preparar_datos_y_margen(df):
    filtro_descuento = (df['nombre_articulo'].str.contains('DESCUENTO', case=False, na=False)) & \
                       (df['nombre_articulo'].str.contains('COMERCIAL', case=False, na=False))
    df_descuentos = df[filtro_descuento]
    df_productos = df[~filtro_descuento].copy()
    if not df_productos.empty:
        df_productos['costo_total_linea'] = df_productos['costo_unitario'].fillna(0) * df_productos['unidades_vendidas'].fillna(0)
        df_productos['margen_bruto'] = df_productos['valor_venta'] - df_productos['costo_total_linea']
    return df_productos, df_descuentos

@st.cache_data
def analizar_rentabilidad(df_productos, df_descuentos):
    venta_bruta = df_productos['valor_venta'].sum()
    margen_bruto_productos = df_productos['margen_bruto'].sum()
    total_descuentos = abs(df_descuentos['valor_venta'].sum())
    margen_operativo = margen_bruto_productos - total_descuentos
    porcentaje_descuento = (total_descuentos / venta_bruta * 100) if venta_bruta > 0 else 0
    
    df_productos_copy = df_productos.copy()
    df_descuentos_copy = df_descuentos.copy()
    if not df_productos_copy.empty:
        df_productos_copy.loc[:, 'mes_anio'] = df_productos_copy['fecha_venta'].dt.to_period('M')
    if not df_descuentos_copy.empty:
        df_descuentos_copy.loc[:, 'mes_anio'] = df_descuentos_copy['fecha_venta'].dt.to_period('M')
    
    margen_bruto_mensual = df_productos_copy.groupby('mes_anio')['margen_bruto'].sum() if not df_productos_copy.empty else pd.Series()
    descuentos_mensual = abs(df_descuentos_copy.groupby('mes_anio')['valor_venta'].sum()) if not df_descuentos_copy.empty else pd.Series()
    
    df_evolucion = pd.DataFrame(margen_bruto_mensual).reset_index()
    df_evolucion = pd.merge(df_evolucion, pd.DataFrame(descuentos_mensual).reset_index(), on='mes_anio', how='outer').fillna(0)
    df_evolucion['margen_operativo'] = df_evolucion['margen_bruto'] - df_evolucion['valor_venta']
    df_evolucion['mes_anio'] = df_evolucion['mes_anio'].dt.to_timestamp()
    top_clientes_descuento = abs(df_descuentos.groupby('nombre_cliente')['valor_venta'].sum()).nlargest(5).reset_index()
    return {
        "venta_bruta": venta_bruta, "margen_bruto_productos": margen_bruto_productos,
        "total_descuentos": total_descuentos, "margen_operativo": margen_operativo,
        "porcentaje_descuento": porcentaje_descuento, "df_evolucion": df_evolucion,
        "top_clientes_descuento": top_clientes_descuento
    }

@st.cache_data
def analizar_segmentacion_rfm(df_productos, fecha_fin_analisis_dt):
    if df_productos.empty: return pd.DataFrame()
    df_rfm = df_productos.groupby(['cliente_id', 'nombre_cliente']).agg(
        Recencia=('fecha_venta', lambda date: (fecha_fin_analisis_dt - date.max()).days),
        Frecuencia=('fecha_venta', 'nunique'),
        Monetario=('valor_venta', 'sum')
    ).reset_index()

    if df_rfm.empty or len(df_rfm) < 4: return df_rfm

    quintiles = df_rfm[['Recencia', 'Frecuencia', 'Monetario']].quantile([.25, .5, .75]).to_dict()
    def r_score(x, q): return 1 if x <= q['Recencia'][.25] else 2 if x <= q['Recencia'][.5] else 3 if x <= q['Recencia'][.75] else 4
    def fm_score(x, c, q): return 4 if x >= q[c][.75] else 3 if x >= q[c][.5] else 2 if x >= q[c][.25] else 1
    
    df_rfm['R'] = df_rfm['Recencia'].apply(lambda x: r_score(x, quintiles))
    df_rfm['F'] = df_rfm['Frecuencia'].apply(lambda x: fm_score(x, 'Frecuencia', quintiles))
    df_rfm['M'] = df_rfm['Monetario'].apply(lambda x: fm_score(x, 'Monetario', quintiles))
    
    mapa_segmentos = {
        r'^[1-2][3-4]$': '🏆 Campeones', r'^[1-2]2$': '💖 Clientes Leales',
        r'^[3-4][3-4]$': '😬 En Riesgo', r'^[3-4][1-2]$': '😥 Hibernando',
        r'^[1-2]1$': '🌱 Clientes Nuevos'
    }
    df_rfm['Clasificacion'] = (df_rfm['R'].astype(str) + df_rfm['F'].astype(str)).replace(mapa_segmentos, regex=True)
    df_rfm.loc[df_rfm['Clasificacion'].str.match(r'^\d{2}$'), 'Clasificacion'] = 'Otros'
    return df_rfm[['nombre_cliente', 'Recencia', 'Frecuencia', 'Monetario', 'Clasificacion']].sort_values('Monetario', ascending=False)


@st.cache_data
def analizar_matriz_productos(df_productos):
    if df_productos.empty: return pd.DataFrame()
    df_matriz = df_productos.groupby('nombre_articulo').agg(
        Volumen=('valor_venta', 'sum'),
        Margen_Total=('margen_bruto', 'sum')
    ).reset_index()
    df_matriz = df_matriz[df_matriz['Volumen'] > 0]
    if df_matriz.empty: return pd.DataFrame()

    df_matriz['Rentabilidad'] = (df_matriz['Margen_Total'] / df_matriz['Volumen']) * 100
    vol_medio = df_matriz['Volumen'].median()
    rent_media = df_matriz['Rentabilidad'].median()

    def clasificar(row):
        if row['Volumen'] > vol_medio and row['Rentabilidad'] > rent_media: return '⭐ Estrella'
        if row['Volumen'] > vol_medio and row['Rentabilidad'] <= rent_media: return '🐄 Vaca Lechera'
        if row['Volumen'] <= vol_medio and row['Rentabilidad'] > rent_media: return '❓ Interrogante'
        return '🐕 Perro'
    df_matriz['Segmento'] = df_matriz.apply(clasificar, axis=1)
    return df_matriz

def generar_excel_descargable(datos_para_exportar):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in datos_para_exportar.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()

# ==============================================================================
# 3. LÓGICA DE LA INTERFAZ DE USUARIO (UI) Y EJECUCIÓN
# ==============================================================================
st.title("🎯 Acciones y Recomendaciones Estratégicas")
st.markdown("Planes de acción inteligentes basados en tus datos para impulsar los resultados.")

# --- 1. SELECCIÓN DE VENDEDOR ---
# << CORREGIDO >> Se normalizan los nombres para hacer comparaciones consistentes.
lista_vendedores_norm = sorted(list(df_ventas_historico['nomvendedor'].dropna().unique()))
vendedores_en_grupos_norm = [normalizar_texto(v) for lista in DATA_CONFIG['grupos_vendedores'].values() for v in lista]
vendedores_solos_norm = [v for v in lista_vendedores_norm if v not in vendedores_en_grupos_norm]

# Se muestran los nombres originales en el dropdown para una mejor experiencia de usuario.
opciones_analisis = sorted(list(DATA_CONFIG['grupos_vendedores'].keys())) + sorted([v for v in df_ventas_historico['nomvendedor'].unique() if normalizar_texto(v) in vendedores_solos_norm])

usuario_actual = st.session_state.usuario
usuario_actual_norm = normalizar_texto(usuario_actual)

if usuario_actual_norm == "GERENTE":
    opciones_analisis.insert(0, "Seleccione un Vendedor o Grupo")
    default_index = 0
else:
    # Encuentra la opción correcta para el usuario actual, manteniendo el nombre original.
    opciones_analisis = [usuario_actual] if usuario_actual in opciones_analisis else []
    default_index = 0

if not opciones_analisis:
    st.warning(f"No se encontraron datos asociados al usuario '{usuario_actual}'.")
    st.stop()

seleccion = st.selectbox("Seleccione el Vendedor o Grupo a analizar:", opciones_analisis, index=default_index, key="seller_selector")

if seleccion == "Seleccione un Vendedor o Grupo":
    st.info("Por favor, elija un vendedor o grupo para comenzar.")
    st.stop()

# --- 2. FILTRADO INICIAL POR VENDEDOR ---
# << CORREGIDO >> Se normalizan los nombres del grupo/vendedor seleccionado antes de filtrar el DataFrame.
seleccion_norm = normalizar_texto(seleccion)
# Se obtiene la lista de vendedores originales del grupo y se normaliza para el filtro.
lista_vendedores_a_filtrar = DATA_CONFIG['grupos_vendedores'].get(seleccion, [seleccion])
lista_vendedores_a_filtrar_norm = [normalizar_texto(v) for v in lista_vendedores_a_filtrar]
df_vendedor_base = df_ventas_historico[df_ventas_historico['nomvendedor'].isin(lista_vendedores_a_filtrar_norm)]


if df_vendedor_base.empty:
    st.warning(f"No hay datos históricos para {seleccion}.")
    st.stop()

# --- 3. SELECCIÓN DE RANGO DE MESES ---
st.markdown("---")
# Usamos .copy() para evitar SettingWithCopyWarning
df_vendedor_base_copy = df_vendedor_base.copy()
df_vendedor_base_copy['periodo'] = df_vendedor_base_copy['fecha_venta'].dt.to_period('M')
meses_disponibles = sorted(df_vendedor_base_copy['periodo'].unique())
mapa_meses = {f"{DATA_CONFIG['mapeo_meses'][p.month]} {p.year}": p for p in meses_disponibles}
opciones_slider = list(mapa_meses.keys())

if len(opciones_slider) > 1:
    mes_inicio_str, mes_fin_str = st.select_slider("Seleccione rango de meses para el análisis:", options=opciones_slider, value=(opciones_slider[0], opciones_slider[-1]))
elif len(opciones_slider) == 1:
    mes_inicio_str = mes_fin_str = opciones_slider[0]
    st.info(f"Periodo de análisis: {mes_inicio_str}") # Usamos st.info para mejor visibilidad
else:
    st.warning("No hay periodos de venta para analizar para este vendedor.")
    st.stop()

# --- 4. FILTRADO FINAL Y EJECUCIÓN DE ANÁLISIS ---
periodo_inicio, periodo_fin = mapa_meses[mes_inicio_str], mapa_meses[mes_fin_str]
fecha_inicio, fecha_fin = periodo_inicio.start_time, periodo_fin.end_time
df_vendedor_periodo = df_vendedor_base[(df_vendedor_base['fecha_venta'] >= fecha_inicio) & (df_vendedor_base['fecha_venta'] <= fecha_fin)]

if df_vendedor_periodo.empty:
    st.warning(f"No se encontraron datos para '{seleccion}' en el rango de meses seleccionado.")
    st.stop()

with st.spinner(f"Generando plan de acción para {seleccion}..."):
    df_productos, df_descuentos = preparar_datos_y_margen(df_vendedor_periodo.copy())
    analisis_rentabilidad = analizar_rentabilidad(df_productos, df_descuentos)
    df_rfm = analizar_segmentacion_rfm(df_productos, fecha_fin.to_pydatetime()) # Convertir a datetime de Python
    df_matriz_productos = analizar_matriz_productos(df_productos)

# --- 5. RENDERIZADO DE LA PÁGINA ---
st.download_button(
    label="📥 Descargar Análisis en Excel",
    data=generar_excel_descargable({
        "Segmentacion_RFM": df_rfm,
        "Matriz_de_Productos": df_matriz_productos,
        "Rentabilidad_y_Dcto": analisis_rentabilidad['df_evolucion'],
        "Top_Clientes_con_Dcto": analisis_rentabilidad['top_clientes_descuento']
    }),
    file_name=f"Plan_Accion_{seleccion.replace(' ', '_')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
st.markdown("---")

# Módulo de Rentabilidad
st.header("💰 Optimización de Rentabilidad y Descuentos")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Margen Bruto de Productos", f"${analisis_rentabilidad['margen_bruto_productos']:,.0f}")
col2.metric("Total Descuentos Otorgados", f"-${analisis_rentabilidad['total_descuentos']:,.0f}", help="Suma de todos los artículos 'Descuento Comercial'")
col3.metric("Margen Operativo Real", f"${analisis_rentabilidad['margen_operativo']:,.0f}", delta_color="off")
col4.metric("% Descuento sobre Venta", f"{analisis_rentabilidad['porcentaje_descuento']:.1f}%", help="(Total Descuentos / Venta Bruta de Productos) * 100")

df_evo = analisis_rentabilidad['df_evolucion']
if not df_evo.empty:
    fig_evo = px.line(df_evo, x='mes_anio', y=['margen_bruto', 'margen_operativo'], title="Evolución de Margen Bruto vs. Margen Operativo", labels={"value": "Monto ($)", "mes_anio": "Mes"}, markers=True)
    fig_evo.update_layout(legend_title_text='Leyenda')
    st.plotly_chart(fig_evo, use_container_width=True)
    st.info("La brecha entre las dos líneas representa el total de descuentos comerciales otorgados cada mes.")

st.subheader("Clientes con Mayor Descuento Otorgado")
st.dataframe(analisis_rentabilidad['top_clientes_descuento'], use_container_width=True, hide_index=True, column_config={"valor_venta": st.column_config.NumberColumn(format="$ %d")})

# Módulo de Segmentación RFM
st.header("👥 Segmentación Estratégica de Clientes (RFM)")
with st.container(border=True):
    st.info("Clasifica a tus clientes para enfocar tus esfuerzos: **Campeones** (tus mejores clientes), **Leales** (compran consistentemente), **En Riesgo** (necesitan atención para no perderlos) e **Hibernando** (necesitan reactivación).")
    if not df_rfm.empty:
        st.dataframe(df_rfm, use_container_width=True, hide_index=True, height=350)
    else:
        st.warning("No hay suficientes datos de clientes para realizar la segmentación RFM en este periodo.")

# Módulo Matriz de Productos
st.header("📦 Estrategia de Portafolio de Productos")
with st.container(border=True):
    st.info("""
    Clasifica tus productos para saber dónde invertir tu tiempo. **Pasa el mouse sobre las burbujas para ver el detalle de cada producto.**
    - **⭐ Estrellas:** Alta Venta y Alta Rentabilidad. ¡Tus productos clave!
    - **❓ Interrogantes:** Baja Venta, Alta Rentabilidad. ¡Tus mayores oportunidades de crecimiento! Impúlsalos.
    - **🐄 Vacas Lecheras:** Alta Venta, Baja Rentabilidad. Generan flujo de caja, gestiona su eficiencia.
    - **🐕 Perros:** Baja Venta, Baja Rentabilidad. Considera reducir su foco.
    """)
    if not df_matriz_productos.empty:
        fig_matriz = px.scatter(
            df_matriz_productos, x="Volumen", y="Rentabilidad", color="Segmento",
            size='Volumen', hover_name="nombre_articulo", log_x=True,
            color_discrete_map={'⭐ Estrella': 'gold', '🐄 Vaca Lechera': 'dodgerblue', '❓ Interrogante': 'limegreen', '🐕 Perro': 'tomato'},
            title="Matriz de Rendimiento de Productos"
        )
        st.plotly_chart(fig_matriz, use_container_width=True)
        
        st.subheader("Explorar Datos de Productos")
        segmentos_seleccionados = st.multiselect("Filtrar por segmento:", options=sorted(df_matriz_productos['Segmento'].unique()), default=sorted(df_matriz_productos['Segmento'].unique()))
        df_filtrada = df_matriz_productos[df_matriz_productos['Segmento'].isin(segmentos_seleccionados)]
        if not df_filtrada.empty:
            max_rentabilidad = df_filtrada['Rentabilidad'].max()
            min_rentabilidad = df_filtrada['Rentabilidad'].min()
            st.dataframe(df_filtrada, use_container_width=True, hide_index=True, height=350,
                         column_config={
                             "Volumen": st.column_config.NumberColumn(format="$ %d"), 
                             "Rentabilidad": st.column_config.ProgressColumn(
                                 format="%.1f%%", 
                                 min_value=float(min_rentabilidad-abs(min_rentabilidad*0.1)), 
                                 max_value=float(max_rentabilidad+abs(max_rentabilidad*0.1))
                              )
                         })
    else:
        st.warning("No hay suficientes datos de productos para generar la matriz en este periodo.")
