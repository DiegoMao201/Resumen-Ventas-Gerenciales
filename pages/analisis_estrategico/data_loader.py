"""Gestión de carga y transformación de datos"""
import streamlit as st
import pandas as pd
import dropbox
import io
from datetime import date
from typing import Tuple, Dict
from .config import AppConfig

# ✅ TODOS LOS IMPORTS CORRECTOS

@st.cache_resource
def get_dropbox_client():
    """Cliente Dropbox singleton"""
    try:
        return dropbox.Dropbox(
            app_key=st.secrets.dropbox.app_key,
            app_secret=st.secrets.dropbox.app_secret,
            oauth2_refresh_token=st.secrets.dropbox.refresh_token
        )
    except Exception as e:
        st.error(f"❌ Error conectando a Dropbox: {e}")
        return None

@st.cache_data(ttl=7200)
def cargar_poblaciones() -> pd.DataFrame:
    """Carga datos geográficos desde Dropbox"""
    dbx = get_dropbox_client()
    if not dbx:
        return pd.DataFrame()
    
    rutas = ['/clientes_detalle.xlsx', '/data/clientes_detalle.xlsx', '/Master/clientes_detalle.xlsx']
    
    for ruta in rutas:
        try:
            _, res = dbx.files_download(path=ruta)
            df = pd.read_excel(io.BytesIO(res.content), engine='openpyxl')
            return _procesar_poblaciones(df)
        except:
            continue
    
    st.info("ℹ️ No se encontró archivo de poblaciones. Análisis geográfico limitado.")
    return pd.DataFrame()

def _procesar_poblaciones(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia datos de poblaciones"""
    df.columns = df.columns.str.strip().str.lower()
    
    col_nit = next((c for c in df.columns if 'nit' in c), None)
    col_pob = next((c for c in df.columns if 'poblacion' in c or 'ciudad' in c), None)
    
    if not (col_nit and col_pob):
        return pd.DataFrame()
    
    df_clean = df[[col_nit, col_pob]].copy()
    df_clean.columns = ['Key_Nit', 'Poblacion_Real']
    df_clean['Key_Nit'] = df_clean['Key_Nit'].astype(str).str.strip().str.replace('.0', '', regex=False)
    df_clean['Poblacion_Real'] = df_clean['Poblacion_Real'].astype(str).str.strip().str.upper()
    
    return df_clean.dropna()

def cargar_y_validar_datos() -> Tuple[pd.DataFrame, Dict]:
    """Pipeline completo de carga y limpieza de datos"""
    if 'df_ventas' not in st.session_state:
        st.warning("⚠️ **Por favor, carga el archivo maestro en la página principal.**")
        st.info("👉 Ve a **🏠 Resumen Mensual** para cargar los datos")
        st.stop()
    
    df_raw = st.session_state.df_ventas.copy()
    
    df_clean = (
        df_raw
        .pipe(_mapear_columnas)
        .pipe(_limpiar_tipos_datos)
        .pipe(_clasificar_marcas)
        .pipe(_enriquecer_geografia)
        .pipe(_aplicar_filtro_ytd)
    )
    
    config_filtros = {
        'anios_disponibles': sorted([int(a) for a in df_clean['anio'].unique() if pd.notna(a) and a > 2000], reverse=True),
        'ciudades_disponibles': sorted(df_clean['Poblacion_Real'].dropna().unique()),
        'marcas_disponibles': sorted(df_clean['Marca_Master'].dropna().unique()),
        'categorias_disponibles': sorted(df_clean['Categoria_Master'].dropna().unique())
    }
    
    return df_clean, config_filtros

def _mapear_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Mapea columnas a nombres estándar"""
    config = AppConfig()
    rename_dict = {df.columns[idx]: new_name for idx, new_name in config.COLUMNAS_MAESTRAS.items() if idx < len(df.columns)}
    df = df.rename(columns=rename_dict)
    
    if 'dia' not in df.columns:
        df['dia'] = 15
    
    return df

def _limpiar_tipos_datos(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas a tipos correctos"""
    hoy = date.today()
    
    df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce').fillna(0)
    df['anio'] = pd.to_numeric(df['anio'], errors='coerce').fillna(hoy.year).astype(int)
    df['mes'] = pd.to_numeric(df['mes'], errors='coerce').fillna(1).astype(int)
    df['dia'] = pd.to_numeric(df['dia'], errors='coerce').fillna(15).astype(int)
    df['Key_Nit'] = df['COD'].astype(str).str.strip().str.replace('.0', '', regex=False)
    
    return df

def _clasificar_marcas(df: pd.DataFrame) -> pd.DataFrame:
    """Clasifica marcas según código"""
    config = AppConfig()
    
    def clasificar_fila(codigo_marca):
        codigo = int(codigo_marca) if pd.notna(codigo_marca) else 0
        marca = config.MAPEO_MARCAS.get(codigo, f"Código {codigo}")
        prefijo = marca.split('-')[0] if '-' in marca else marca[:3]
        categoria = config.CATEGORIAS_MARCA.get(prefijo, "Otros")
        return pd.Series([marca, categoria])
    
    df[['Marca_Master', 'Categoria_Master']] = df['CODIGO_MARCA_N'].apply(clasificar_fila)
    return df

def _enriquecer_geografia(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega información geográfica"""
    df_poblaciones = cargar_poblaciones()
    
    if df_poblaciones.empty:
        df['Poblacion_Real'] = 'Sin Geo'
        df['Vendedor'] = df.get('Vendedor', 'GENERAL').fillna('GENERAL')
        return df
    
    df = pd.merge(df, df_poblaciones, on='Key_Nit', how='left')
    df['Poblacion_Real'] = df['Poblacion_Real'].fillna('Sin Geo')
    df['Vendedor'] = df.get('Vendedor', 'GENERAL').fillna('GENERAL')
    
    return df

def _aplicar_filtro_ytd(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica filtro Year-To-Date"""
    hoy = date.today()
    
    def es_ytd(row):
        if row['mes'] < hoy.month:
            return True
        if row['mes'] == hoy.month:
            return row['dia'] <= hoy.day
        return False
    
    return df[df.apply(es_ytd, axis=1)].copy()