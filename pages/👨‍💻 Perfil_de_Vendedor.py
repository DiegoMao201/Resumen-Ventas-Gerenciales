import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import dropbox
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta

# (Constantes y diccionarios se mantienen igual)
# ...

# --- FUNCIÓN DE CARGA DE DATOS ---
@st.cache_data(ttl=1800)
def cargar_y_limpiar_datos(ruta_archivo, nombres_columnas):
    """Descarga y limpia datos desde Dropbox usando el refresh token."""
    try:
        with dropbox.Dropbox(app_key=st.secrets.dropbox.app_key, app_secret=st.secrets.dropbox.app_secret, oauth2_refresh_token=st.secrets.dropbox.refresh_token) as dbx:
            metadata, res = dbx.files_download(path=ruta_archivo)
            contenido_csv = res.content.decode('latin-1')
            df = pd.read_csv(io.StringIO(contenido_csv), header=None, sep=',', on_bad_lines='skip', dtype=str)
            if df.shape[1] != len(nombres_columnas): return pd.DataFrame(columns=nombres_columnas)
            df.columns = nombres_columnas
            numeric_cols = ['anio', 'mes', 'valor_venta', 'valor_cobro', 'unidades_vendidas', 'costo_unitario', 'marca_producto']
            for col in numeric_cols:
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
            df.dropna(subset=['anio', 'mes', 'codigo_vendedor', 'fecha_venta'], inplace=True, how='any')
            for col in ['anio', 'mes']: df[col] = df[col].astype(int)
            df['codigo_vendedor'] = df['codigo_vendedor'].astype(str)
            df['fecha_venta'] = pd.to_datetime(df['fecha_venta'], errors='coerce')
            # --- LÍNEA DE CORRECCIÓN AÑADIDA AQUÍ ---
            if 'marca_producto' in df.columns:
                df['nombre_marca'] = df['marca_producto'].map(MAPEO_MARCAS).fillna('No Especificada')
            return df
    except Exception as e:
        st.error(f"Error crítico al cargar {ruta_archivo}: {e}")
        return pd.DataFrame(columns=nombres_columnas)

# (El resto del código de esta página se mantiene exactamente igual)
# ...

def analizar_cartera_clientes(df_ventas_vendedor):
    if df_ventas_vendedor.empty: return 0, 0, 0, pd.DataFrame()
    fecha_hoy = datetime.now()
    anio_actual, mes_actual = fecha_hoy.year, fecha_hoy.month
    fecha_actual_inicio = fecha_hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    fecha_mes_anterior_fin = fecha_actual_inicio - pd.DateOffset(days=1)
    fecha_riesgo = fecha_actual_inicio - pd.DateOffset(months=3)
    df_ventas_vendedor['fecha_primera_compra'] = df_ventas_vendedor.groupby('cliente_id')['fecha_venta'].transform('min')
    clientes_mes_actual = set(df_ventas_vendedor[(df_ventas_vendedor['fecha_venta'].dt.year == anio_actual) & (df_ventas_vendedor['fecha_venta'].dt.month == mes_actual)]['cliente_id'].unique())
    clientes_historicos = set(df_ventas_vendedor[df_ventas_vendedor['fecha_venta'] <= fecha_mes_anterior_fin]['cliente_id'].unique())
    clientes_nuevos = clientes_mes_actual - clientes_historicos
    clientes_recurrentes = clientes_mes_actual.intersection(clientes_historicos)
    df_ultima_compra = df_ventas_vendedor.groupby('cliente_id')['fecha_venta'].max().reset_index()
    clientes_en_riesgo_ids = set(df_ultima_compra[df_ultima_compra['fecha_venta'] < fecha_riesgo]['cliente_id'].unique())
    clientes_en_riesgo_final_ids = clientes_en_riesgo_ids - clientes_mes_actual
    df_clientes_en_riesgo = df_ventas_vendedor[df_ventas_vendedor['cliente_id'].isin(clientes_en_riesgo_final_ids)]
    top_riesgo = df_clientes_en_riesgo.groupby(['cliente_id', 'nombre_cliente'])['valor_venta'].sum().nlargest(5).reset_index()
    return len(clientes_nuevos), len(clientes_recurrentes), len(clientes_en_riesgo_final_ids), top_riesgo

# --- CONTROLADOR PRINCIPAL Y AUTENTICACIÓN ---
if 'autenticado' not in st.session_state or not st.session_state.autenticado:
    st.image(URL_LOGO, width=300)
    st.header("Acceso Restringido")
    st.warning("Por favor, inicie sesión desde la página principal `🏠 Resumen Mensual` para acceder a esta sección.")
    st.stop()

# --- LÓGICA DE LA PÁGINA ---
st.title("👨‍💻 Perfil de Vendedor y Análisis Detallado")
st.markdown("---")
df_ventas_historico = st.session_state.get('df_ventas')
if df_ventas_historico is None or df_ventas_historico.empty:
    st.error("No se pudieron cargar los datos. Por favor, vuelva a la página principal e inicie sesión de nuevo.")
    st.stop()
df_ventas_historico['fecha_venta'] = pd.to_datetime(df_ventas_historico['fecha_venta'], errors='coerce')
df_ventas_historico.dropna(subset=['fecha_venta'], inplace=True)

# Selector de Vendedor/Grupo
lista_vendedores = sorted(list(df_ventas_historico['nomvendedor'].dropna().unique()))
vendedores_en_grupos = [v for lista in GRUPOS_VENDEDORES.values() for v in lista]
vendedores_solos = [v for v in lista_vendedores if v not in vendedores_en_grupos]
opciones_analisis = ["Seleccione un Vendedor o Grupo"] + list(GRUPOS_VENDEDORES.keys()) + vendedores_solos
usuario_actual = st.session_state.usuario
if usuario_actual != "GERENTE":
    opcion_default = usuario_actual
    opciones_analisis = [opcion_default]
else:
    opcion_default = "Seleccione un Vendedor o Grupo"
seleccion = st.selectbox("Seleccione el Vendedor o Grupo a analizar:", opciones_analisis, index=0 if opcion_default not in opciones_analisis else opciones_analisis.index(opcion_default))

if seleccion == "Seleccione un Vendedor o Grupo": st.info("Por favor, elija un vendedor o grupo para comenzar el análisis."); st.stop()
if seleccion in GRUPOS_VENDEDORES:
    df_vendedor = df_ventas_historico[df_ventas_historico['nomvendedor'].isin(GRUPOS_VENDEDORES[seleccion])]
else:
    df_vendedor = df_ventas_historico[df_ventas_historico['nomvendedor'] == seleccion]
if df_vendedor.empty: st.warning(f"No se encontraron datos históricos para {seleccion}."); st.stop()

# --- CÁLCULOS DE RENTABILIDAD Y EFICIENCIA ---
df_vendedor['costo_total_linea'] = df_vendedor['costo_unitario'] * df_vendedor['unidades_vendidas']
df_vendedor['margen_bruto'] = df_vendedor['valor_venta'] - df_vendedor['costo_total_linea']
margen_total = df_vendedor['margen_bruto'].sum()
venta_total_historica = df_vendedor['valor_venta'].sum()
porcentaje_margen = (margen_total / venta_total_historica * 100) if venta_total_historica > 0 else 0
clientes_unicos_total = df_vendedor['cliente_id'].nunique()
venta_promedio_cliente = venta_total_historica / clientes_unicos_total if clientes_unicos_total > 0 else 0

st.header(f"Análisis para: {seleccion}")
col1, col2, col3 = st.columns(3)
col1.metric("Margen Bruto Total (Histórico)", f"${margen_total:,.0f}")
col2.metric("Porcentaje de Margen Promedio", f"{porcentaje_margen:.1f}%")
col3.metric("Venta Promedio por Cliente", f"${venta_promedio_cliente:,.0f}")

# --- VISUALIZACIONES ---
st.subheader("Evolución de Ventas y Margen")
df_evolucion = df_vendedor.set_index('fecha_venta').resample('ME')[['valor_venta', 'margen_bruto']].sum().reset_index()
fig_evolucion = px.line(df_evolucion, x='fecha_venta', y=['valor_venta', 'margen_bruto'], title=f"Ventas vs. Margen Bruto Mensual de {seleccion}", labels={"fecha_venta": "Mes", "value": "Monto"}, markers=True)
st.plotly_chart(fig_evolucion, use_container_width=True)

# (El resto del código con las pestañas de análisis se mantiene igual)
# ...
