# ==============================================================================
# SCRIPT PARA: 🧠 Centro de Control de Descuentos y Cartera
# VERSIÓN: 5.1 GERENCIAL (CORREGIDO) - 07 de Julio, 2025
# DESCRIPCIÓN: Versión con corrección de error de sintaxis y lógica para
#              manejar de forma robusta los dataframes vacíos.
# ==============================================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN DE ACCESO ---
st.set_page_config(page_title="Control de Descuentos y Cartera", page_icon="🧠", layout="wide")

st.title("🧠 Centro de Control de Descuentos y Cartera")
st.markdown("Herramienta gerencial para analizar la efectividad de los descuentos comerciales y la salud de la cartera de clientes.")

# Simulación de login para desarrollo. En producción, usar el método real.
# if 'usuario' not in st.session_state:
#     st.session_state['usuario'] = "GERENTE" # Simular login para pruebas

if st.session_state.get('usuario') != "GERENTE":
    st.error("🔒 Acceso Exclusivo para Gerencia.")
    st.info("Por favor, inicie sesión desde la página principal para acceder a esta herramienta.")
    st.stop()

# --- LÓGICA DE CARGA DE DATOS (CACHEADA PARA EFICIENCIA) ---
@st.cache_data(ttl=3600) # Cachear los datos por 1 hora
def cargar_datos_fuente(dropbox_path_cobros):
    """
    Carga los datos de ventas (desde session_state) y el archivo de cobros desde Dropbox.
    Esta función se ejecuta solo una vez si los datos no están en caché.
    """
    try:
        # Carga de Ventas (asumiendo que ya está en st.session_state desde la app principal)
        df_ventas = st.session_state.get('df_ventas')
        if df_ventas is None:
            st.error("Los datos de ventas no se encontraron en la sesión. Por favor, vuelva a la página principal y cargue los datos primero.")
            return None, None
        
        # Carga del archivo de Cobros (Excel) desde Dropbox
        with st.spinner("Cargando y validando archivo de cobros desde Dropbox..."):
            # Este bloque es para simulación si no se tienen las credenciales de Dropbox
            # En un entorno real, el bloque try-except con la API de Dropbox se usaría.
            try:
                import dropbox
                # Las credenciales deben estar configuradas en los secretos de Streamlit
                dbx = dropbox.Dropbox(
                    app_key=st.secrets.dropbox.app_key,
                    app_secret=st.secrets.dropbox.app_secret,
                    oauth2_refresh_token=st.secrets.dropbox.refresh_token
                )
                _, res = dbx.files_download(path=dropbox_path_cobros)
                df_cobros = pd.read_excel(io.BytesIO(res.content))
            except Exception as e:
                st.error(f"Error real al conectar con Dropbox: {e}")
                st.warning("Usando datos de ejemplo para cobros debido al error de conexión.")
                # Datos de ejemplo para desarrollo sin conexión a Dropbox
                data_cobros = {
                    'Serie': [f'F001-{i}' for i in range(100, 200)],
                    'Fecha Documento': pd.to_datetime([f'2025-0{ (i%6)+1 }-{ (i%28)+1 }' for i in range(100)]),
                    'Fecha Saldado': pd.to_datetime([f'2025-0{ (i%6)+1 }-{ (i%28)+1 }' for i in range(100)]) + pd.to_timedelta([i % 60 for i in range(100)], unit='d'),
                    'NOMBRECLIENTE': [f'Cliente {(i%20)+1}' for i in range(100)],
                    'NOMVENDEDOR': [f'Vendedor {(i%4)+1}' for i in range(100)]
                }
                df_cobros = pd.DataFrame(data_cobros)

        return df_ventas, df_cobros

    except Exception as e:
        st.error(f"Error crítico al cargar los archivos: {e}")
        st.info("Asegúrese de que el archivo 'Cobros.xlsx' exista en la carpeta '/data/' de su Dropbox y que las credenciales sean correctas.")
        return None, None

@st.cache_data
def procesar_y_analizar(_df_ventas, _df_cobros, nombre_articulo_descuento, dias_pronto_pago):
    """
    Función central que procesa, une y enriquece los datos para el análisis gerencial.
    """
    if _df_ventas is None or _df_cobros is None:
        return None

    # 1. PREPARACIÓN DE DATOS
    df_ventas = _df_ventas.copy()
    df_ventas['fecha_venta'] = pd.to_datetime(df_ventas['fecha_venta'])
    df_ventas['valor_venta'] = pd.to_numeric(df_ventas['valor_venta'], errors='coerce')
    df_ventas = df_ventas.dropna(subset=['valor_venta', 'Serie'])

    df_cobros = _df_cobros.copy()
    df_cobros = df_cobros.rename(columns={
        'Fecha Documento': 'fecha_documento',
        'Fecha Saldado': 'fecha_saldado',
        'NOMBRECLIENTE': 'nombre_cliente',
        'NOMVENDEDOR': 'nomvendedor'
    })
    df_cobros['fecha_saldado'] = pd.to_datetime(df_cobros['fecha_saldado'], errors='coerce')
    df_cobros = df_cobros.dropna(subset=['fecha_saldado', 'Serie'])

    # 2. SEPARAR VENTAS Y DESCUENTOS
    df_productos = df_ventas[df_ventas['nombre_articulo'] != nombre_articulo_descuento]
    df_descuentos_raw = df_ventas[df_ventas['nombre_articulo'] == nombre_articulo_descuento]

    # 3. AGREGAR DATOS POR FACTURA (SERIE)
    ventas_por_factura = df_productos.groupby('Serie').agg(
        valor_total_productos=('valor_venta', 'sum'),
        fecha_venta=('fecha_venta', 'first'),
        nombre_cliente=('nombre_cliente', 'first'),
        nomvendedor=('nomvendedor', 'first')
    ).reset_index()

    descuentos_por_factura = df_descuentos_raw.groupby('Serie').agg(
        monto_descontado=('valor_venta', 'sum')
    ).reset_index()
    descuentos_por_factura['monto_descontado'] = abs(descuentos_por_factura['monto_descontado'])

    # 4. UNIR VENTAS, DESCUENTOS Y COBROS
    # Partimos de las ventas y añadimos la info de descuentos
    df_facturas = pd.merge(ventas_por_factura, descuentos_por_factura, on='Serie', how='left')
    df_facturas['monto_descontado'] = df_facturas['monto_descontado'].fillna(0)

    # Añadimos la fecha en que se saldó la factura
    df_completo = pd.merge(df_facturas, df_cobros[['Serie', 'fecha_saldado']], on='Serie', how='inner') # inner join para analizar solo facturas pagadas

    # 5. CÁLCULOS Y ENRIQUECIMIENTO DE DATOS
    df_completo['dias_pago'] = (df_completo['fecha_saldado'] - df_completo['fecha_venta']).dt.days
    # Eliminar valores atípicos o erróneos (pagos negativos o muy largos)
    df_completo = df_completo[(df_completo['dias_pago'] >= 0) & (df_completo['dias_pago'] < 365)]

    # 6. AGREGAR A NIVEL DE CLIENTE PARA EL ANÁLISIS FINAL
    analisis_cliente = df_completo.groupby(['nombre_cliente', 'nomvendedor']).agg(
        dias_pago_promedio=('dias_pago', 'mean'),
        total_comprado=('valor_total_productos', 'sum'),
        total_descontado=('monto_descontado', 'sum'),
        numero_facturas=('Serie', 'nunique')
    ).reset_index()

    analisis_cliente['pct_descuento'] = (analisis_cliente['total_descontado'] / analisis_cliente['total_comprado']).fillna(0) * 100

    # 7. CLASIFICACIÓN ESTRATÉGICA DEL CLIENTE (LA "INTELIGENCIA")
    def clasificar_cliente(row):
        paga_a_tiempo = row['dias_pago_promedio'] <= dias_pronto_pago
        recibe_descuento = row['total_descontado'] > 0

        if paga_a_tiempo and recibe_descuento:
            return "✅ Justificado: Paga a tiempo y usa Dcto."
        elif paga_a_tiempo and not recibe_descuento:
            return "💡 Oportunidad: Buen pagador sin Dcto."
        elif not paga_a_tiempo and recibe_descuento:
            return "❌ Crítico: Mal pagador con Dcto."
        else: # not paga_a_tiempo and not recibe_descuento
            return "⚠️ Alerta: Mal pagador sin Dcto."

    analisis_cliente['Clasificacion'] = analisis_cliente.apply(clasificar_cliente, axis=1)
    
    return analisis_cliente.sort_values(by='total_descontado', ascending=False)


# ==============================================================================
# EJECUCIÓN PRINCIPAL Y RENDERIZADO DE LA INTERFAZ
# ==============================================================================

# --- Carga de Datos ---
# Usamos st.session_state para evitar recargar desde Dropbox en cada rerun
if 'df_ventas_raw' not in st.session_state or 'df_cobros_raw' not in st.session_state:
    st.session_state.df_ventas_raw, st.session_state.df_cobros_raw = cargar_datos_fuente(
        dropbox_path_cobros="/data/Cobros.xlsx"
    )

df_ventas = st.session_state.df_ventas_raw
df_cobros = st.session_state.df_cobros_raw

# Si la carga falla, la aplicación se detiene aquí.
if df_ventas is None or df_cobros is None:
    st.error("La carga de datos falló. No se puede continuar con el análisis.")
    st.stop()

# --- Barra Lateral de Filtros ---
st.sidebar.header("Filtros del Análisis")
DIAS_PRONTO_PAGO = st.sidebar.slider(
    "Definir 'Pronto Pago' (días)", 
    min_value=5, max_value=60, value=15,
    help="Este es el umbral para considerar si un cliente paga a tiempo."
)

# Obtener lista de vendedores únicos y añadir opción "Todos"
lista_vendedores = ['Todos'] + sorted(df_ventas['nomvendedor'].unique().tolist())
vendedor_seleccionado = st.sidebar.selectbox(
    "Seleccionar Vendedor",
    options=lista_vendedores,
    help="Filtra el análisis para un vendedor específico o ve la data de todos."
)

# --- Procesamiento de Datos con Filtros Aplicados ---
with st.spinner("Procesando y analizando la información..."):
    df_analisis = procesar_y_analizar(df_ventas, df_cobros, "DESCUENTOS COMERCIALES", DIAS_PRONTO_PAGO)

if df_analisis is None:
    st.warning("No se pudo procesar la información. Revise los datos de origen.")
    st.stop()

# Aplicar filtro de vendedor
if vendedor_seleccionado != "Todos":
    df_filtrado = df_analisis[df_analisis['nomvendedor'] == vendedor_seleccionado].copy()
else:
    df_filtrado = df_analisis.copy()


# --- Pestañas de Análisis ---
st.markdown("---")
tab1, tab2, tab3 = st.tabs([
    "📊 **Visión Gerencial**", 
    "👥 **Análisis Detallado por Cliente**", 
    "🗣️ **Conclusiones y Recomendaciones**"
])

# --- PESTAÑA 1: VISIÓN GERENCIAL ---
with tab1:
    st.header(f"Visión Gerencial para: {vendedor_seleccionado}")

    if df_filtrado.empty:
        st.warning(f"No hay datos suficientes para el vendedor '{vendedor_seleccionado}' con los filtros actuales.")
    else:
        # KPIs Principales
        total_descontado = df_filtrado['total_descontado'].sum()
        dso_real = df_filtrado['dias_pago_promedio'].mean()
        clientes_criticos = df_filtrado[df_filtrado['Clasificacion'] == '❌ Crítico: Mal pagador con Dcto.']['nombre_cliente'].nunique()
        pct_dcto_mal_asignado = (df_filtrado[df_filtrado['Clasificacion'] == '❌ Crítico: Mal pagador con Dcto.']['total_descontado'].sum() / total_descontado * 100) if total_descontado > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Monto Total en Descuentos", f"${total_descontado:,.0f}")
        col2.metric("Días Promedio de Pago (DSO)", f"{dso_real:.1f} días")
        col3.metric("Clientes Críticos", f"{clientes_criticos}", help="Clientes con descuentos que pagan fuera del plazo.")
        col4.metric("% Dcto. en Clientes Críticos", f"{pct_dcto_mal_asignado:.1f}%", help="Porcentaje del total de descuentos que se va a clientes que no pagan a tiempo.")

        st.markdown("---")
        st.subheader("Visualización Estratégica: ¿Dónde están nuestros clientes?")
        st.info(f"""
        Este gráfico es la clave del análisis. Busca clientes en los cuadrantes:
        - **Inferior Izquierda (Verde ✅):** ¡Ideal! Clientes que pagan rápido y usan el descuento.
        - **Superior Izquierda (Azul 💡):** ¡Oportunidad! Buenos pagadores a los que podríamos fidelizar con descuentos.
        - **Inferior Derecha (Rojo ❌):** ¡Crítico! Clientes que reciben descuentos pero no cumplen con el pronto pago. **Requieren acción inmediata.**
        - **Superior Derecha (Naranja ⚠️):** ¡Alerta! Malos pagadores que, afortunadamente, no tienen grandes descuentos.
        """, icon="🎯")

        fig_scatter = px.scatter(
            df_filtrado[df_filtrado['total_comprado'] > 0],
            x='dias_pago_promedio',
            y='pct_descuento',
            size='total_comprado',
            color='Clasificacion',
            hover_name='nombre_cliente',
            hover_data=['total_comprado', 'total_descontado'],
            title="Relación: Comportamiento de Pago vs. % Descuento Otorgado",
            labels={
                'dias_pago_promedio': 'Días Promedio de Pago',
                'pct_descuento': '% Descuento sobre su Compra',
                'Clasificacion': 'Clasificación Estratégica'
            },
            color_discrete_map={
                "✅ Justificado: Paga a tiempo y usa Dcto.": "green",
                "💡 Oportunidad: Buen pagador sin Dcto.": "blue",
                "❌ Crítico: Mal pagador con Dcto.": "red",
                "⚠️ Alerta: Mal pagador sin Dcto.": "orange"
            },
            size_max=60
        )
        fig_scatter.add_vline(x=DIAS_PRONTO_PAGO, line_width=2, line_dash="dash", line_color="black", annotation_text=f"Meta {DIAS_PRONTO_PAGO} días")
        st.plotly_chart(fig_scatter, use_container_width=True)

# --- PESTAÑA 2: ANÁLISIS DETALLADO POR CLIENTE ---
with tab2:
    st.header(f"Análisis Detallado por Cliente para: {vendedor_seleccionado}")
    st.info("Utilice esta tabla para investigar clientes específicos. Puede ordenarla haciendo clic en los encabezados de las columnas.")

    if df_filtrado.empty:
        st.warning(f"No hay datos para mostrar para el vendedor '{vendedor_seleccionado}'.")
    else:
        # ======================================================================
        # INICIO DE LA CORRECCIÓN
        # Se calcula el valor máximo para la barra de progreso de forma segura,
        # evitando errores si el dataframe filtrado está vacío.
        max_pct_value = max(5, df_filtrado['pct_descuento'].max())
        # FIN DE LA CORRECCIÓN
        # ======================================================================

        st.dataframe(
            df_filtrado,
            column_config={
                "nombre_cliente": "Cliente",
                "nomvendedor": "Vendedor",
                "dias_pago_promedio": st.column_config.NumberColumn("Días Prom. Pago", format="%.1f"),
                "total_comprado": st.column_config.NumberColumn("Total Comprado", format="$ {:,.0f}"),
                "total_descontado": st.column_config.NumberColumn("Total Descontado", format="$ {:,.0f}"),
                "numero_facturas": "N° Facturas",
                "pct_descuento": st.column_config.ProgressColumn(
                    "% Dcto.",
                    format="%.2f%%",
                    min_value=0,
                    # Se usa la variable segura calculada previamente
                    max_value=max_pct_value
                ),
                "Clasificacion": st.column_config.Column("Clasificación", width="medium")
            },
            use_container_width=True,
            hide_index=True
        )

# --- PESTAÑA 3: CONCLUSIONES Y RECOMENDACIONES ---
with tab3:
    st.header(f"Conclusiones para: {vendedor_seleccionado}")
    st.info("Aquí se resumen los hallazgos clave y se sugieren acciones basadas en los datos filtrados.", icon="✍️")

    if df_filtrado.empty:
        st.warning(f"No se pueden generar conclusiones para '{vendedor_seleccionado}' debido a la falta de datos.")
    else:
        clientes_criticos_df = df_filtrado[df_filtrado['Clasificacion'] == '❌ Crítico: Mal pagador con Dcto.']
        clientes_oportunidad_df = df_filtrado[df_filtrado['Clasificacion'] == '💡 Oportunidad: Buen pagador sin Dcto.']

        st.subheader("Hallazgos Clave:")
        
        # Conclusión 1: El problema principal
        if not clientes_criticos_df.empty:
            monto_critico = clientes_criticos_df['total_descontado'].sum()
            st.error(f"""
            **Principal Foco Rojo:** Se han otorgado **${monto_critico:,.0f}** en descuentos a **{len(clientes_criticos_df)}** clientes
            que, en promedio, tardan más de {DIAS_PRONTO_PAGO} días en pagar. Esto contradice la política de descuentos por pronto pago.
            """, icon="🔥")
        else:
            st.success("**¡Excelente Noticia!** No se encontraron clientes críticos. Los descuentos se están asignando correctamente a clientes que pagan a tiempo.", icon="🎉")

        # Conclusión 2: La oportunidad escondida
        if not clientes_oportunidad_df.empty:
            st.info(f"""
            **Oportunidad de Crecimiento:** Existen **{len(clientes_oportunidad_df)}** clientes clasificados como 'buenos pagadores' que actualmente
            no reciben descuentos significativos. Podrían ser candidatos para un programa de lealtad que incentive compras mayores a cambio de descuentos.
            """, icon="�")

        st.markdown("---")
        st.subheader("Recomendaciones y Acciones Sugeridas:")

        if not clientes_criticos_df.empty:
            st.markdown("**1. Para Clientes Críticos (Malos Pagadores con Descuento):**")
            st.markdown(f"   - **Acción Inmediata:** Revisar la política de descuentos para los siguientes clientes. Considere suspender los 'descuentos comerciales' hasta que su promedio de pago baje de los {DIAS_PRONTO_PAGO} días.")
            
            # Mostrar los 3 peores para que sea accionable
            top_3_criticos = clientes_criticos_df.sort_values('dias_pago_promedio', ascending=False).head(3)
            for _, row in top_3_criticos.iterrows():
                st.warning(f"   - **{row['nombre_cliente']}**: Días pago: **{row['dias_pago_promedio']:.0f}**, Dcto. total: **${row['total_descontado']:,.0f}**")
        
        if not clientes_oportunidad_df.empty:
            st.markdown("**2. Para Clientes de Oportunidad (Buenos Pagadores sin Descuento):**")
            st.markdown("   - **Acción Estratégica:** Contactar proactivamente a estos clientes. Ofrecerles el 'descuento comercial' en su próxima compra como premio a su buen comportamiento de pago para fortalecer la relación comercial.")
            top_3_oportunidad = clientes_oportunidad_df.sort_values('total_comprado', ascending=False).head(3)
            for _, row in top_3_oportunidad.iterrows():
                st.success(f"   - **{row['nombre_cliente']}**: Días pago: **{row['dias_pago_promedio']:.0f}**, Compras totales: **${row['total_comprado']:,.0f}**")
