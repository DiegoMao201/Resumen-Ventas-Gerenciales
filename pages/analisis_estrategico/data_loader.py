"""Gestión de carga y transformación de datos - Integrado con Resumen_Mensual"""
import streamlit as st
import pandas as pd
import dropbox
import io
from datetime import date
from typing import Tuple, Dict, Any  # <-- añade Any aquí
from .config import AppConfig
import unicodedata

@st.cache_resource
def get_dropbox_client():
    """Cliente Dropbox singleton"""
    try:
        token = st.secrets.get("DROPBOX_ACCESS_TOKEN")
        if not token:
            return None
        return dropbox.Dropbox(token)
    except Exception as e:
        return None

@st.cache_data(ttl=7200)
def cargar_poblaciones() -> pd.DataFrame:
    """Carga datos geográficos desde Dropbox"""
    dbx = get_dropbox_client()
    if not dbx:
        return pd.DataFrame()
    
    rutas = ['/clientes_detalle.xlsx', '/data/clientes_detalle.xlsx']
    
    for ruta in rutas:
        try:
            _, res = dbx.files_download(path=ruta)
            df = pd.read_excel(io.BytesIO(res.content), engine='openpyxl')
            return _procesar_poblaciones(df)
        except:
            continue
    
    return pd.DataFrame()

def _procesar_poblaciones(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia datos de poblaciones"""
    try:
        df.columns = df.columns.str.strip().str.lower()
        
        col_nit = next((c for c in df.columns if 'nit' in c), None)
        col_pob = next((c for c in df.columns if 'poblacion' in c or 'ciudad' in c), None)
        
        if not (col_nit and col_pob):
            return pd.DataFrame()
        
        df_clean = df[[col_nit, col_pob]].copy()
        df_clean.columns = ['cliente_id', 'Poblacion_Real']
        df_clean['cliente_id'] = df_clean['cliente_id'].astype(str).str.strip()
        df_clean['Poblacion_Real'] = df_clean['Poblacion_Real'].astype(str).str.strip().str.upper()
        
        return df_clean.dropna()
    except Exception as e:
        return pd.DataFrame()

def _normalizar_txt(txt: str) -> str:
    if pd.isna(txt): return ""
    t = "".join(c for c in unicodedata.normalize("NFD", str(txt)) if unicodedata.category(c) != "Mn")
    return t.strip().upper()

def obtener_lista_ordenada(serie: pd.Series) -> list:
    """Devuelve lista ordenada y sin nulos."""
    return sorted(serie.dropna().astype(str).unique())

def _unificar_lineas_marcas(df: pd.DataFrame) -> pd.DataFrame:
    import re

    def _fmt_linea(val: Any) -> str:
        if pd.isna(val):
            return ""
        s = str(val).strip()
        # Si es solo numérico (incluye “1.0”), descártalo para forzar fallback
        if re.fullmatch(r"\d+(\.0+)?", s):
            return ""
        return s

    # 1) Preferir linea_producto con nombres reales
    if "linea_producto" in df.columns:
        df["Linea_Estrategica"] = df["linea_producto"].apply(_fmt_linea)
    else:
        df["Linea_Estrategica"] = ""

    # 2) Fallback a categoria_producto solo donde quedó vacío
    if "categoria_producto" in df.columns:
        mask = df["Linea_Estrategica"].eq("")
        df.loc[mask, "Linea_Estrategica"] = df.loc[mask, "categoria_producto"].apply(_fmt_linea)

    # 3) Último fallback a nombre_articulo
    if "nombre_articulo" in df.columns:
        mask = df["Linea_Estrategica"].eq("")
        df.loc[mask, "Linea_Estrategica"] = df.loc[mask, "nombre_articulo"].apply(_fmt_linea)

    # Normalizar texto final (mayúsculas, sin tildes)
    df["Linea_Estrategica"] = df["Linea_Estrategica"].apply(_normalizar_txt)

    # Marcas
    if "marca_producto" in df.columns:
        df["marca_producto"] = df["marca_producto"].fillna("").apply(_normalizar_txt)
    return df

def cargar_y_validar_datos() -> Tuple[pd.DataFrame, Dict]:
    """Pipeline completo usando los datos de Resumen_Mensual.py"""
    if 'df_ventas' not in st.session_state:
        st.warning("⚠️ **Por favor, carga el archivo maestro en la página principal.**")
        st.info("👉 Ve a **🏠 Resumen Mensual** para cargar los datos")
        st.stop()
    
    try:
        df_raw = st.session_state.df_ventas.copy()
        
        if df_raw.empty:
            st.error("❌ El DataFrame está vacío")
            st.stop()
        
        df_clean = df_raw.copy()

        # --- CORRECCIÓN DE MARCAS Y CATEGORÍAS ---
        # Mapea marcas numéricas a nombres
        if 'marca_producto' in df_clean.columns and 'nombre_marca' not in df_clean.columns:
            DATA_CONFIG = st.session_state.DATA_CONFIG  # <-- Usa la variable de sesión
            df_clean['nombre_marca'] = df_clean['marca_producto'].map(DATA_CONFIG["mapeo_marcas"]).fillna('No Especificada')

        # Normaliza categorías si es necesario
        if 'categoria_producto' in df_clean.columns:
            df_clean['categoria_producto'] = df_clean['categoria_producto'].astype(str)

        # Limpiar tipos de datos
        df_clean = _limpiar_tipos_datos(df_clean)
        # Clasificar líneas y enriquecer
        df_clean = _unificar_lineas_marcas(df_clean)
        df_clean = _clasificar_lineas_estrategicas(df_clean)
        df_clean = _enriquecer_geografia(df_clean)
        anios_disponibles = sorted(df_clean['anio'].unique(), reverse=True)
        config_filtros = {
            'anios_disponibles': anios_disponibles,
            'ciudades_disponibles': obtener_lista_ordenada(df_clean['Poblacion_Real']) if 'Poblacion_Real' in df_clean.columns else [],
            'lineas_disponibles': obtener_lista_ordenada(df_clean['Linea_Estrategica']) if 'Linea_Estrategica' in df_clean.columns else [],
            'marcas_disponibles': obtener_lista_ordenada(df_clean['marca_producto']) if 'marca_producto' in df_clean.columns else [],
            'vendedores_disponibles': obtener_lista_ordenada(df_clean['nomvendedor']) if 'nomvendedor' in df_clean.columns else []
        }
        return df_clean, config_filtros
        
    except Exception as e:
        st.error(f"❌ Error en pipeline de datos: {str(e)}")
        st.exception(e)
        st.stop()

def _limpiar_tipos_datos(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas a tipos correctos SIN perder datos"""
    from datetime import date
    hoy = date.today()
    
    if 'valor_venta' in df.columns:
        df['valor_venta'] = pd.to_numeric(df['valor_venta'], errors='coerce').fillna(0)

    # Fallback de línea estratégica
    if 'Linea_Estrategica' not in df.columns and 'linea_producto' in df.columns:
        df['Linea_Estrategica'] = df['linea_producto']

    if 'anio' in df.columns:
        df['anio'] = pd.to_numeric(df['anio'], errors='coerce').fillna(hoy.year).astype(int)
    if 'mes' in df.columns:
        df['mes'] = pd.to_numeric(df['mes'], errors='coerce').fillna(1).astype(int).clip(1, 12)
    if 'nombre_cliente' in df.columns:
        df['nombre_cliente'] = df['nombre_cliente'].fillna('Sin Cliente').astype(str)
    if 'nomvendedor' in df.columns:
        df['nomvendedor'] = df['nomvendedor'].fillna('SIN VENDEDOR').astype(str)
    df = _unificar_lineas_marcas(df)
    return df

def _clasificar_lineas_estrategicas(df: pd.DataFrame) -> pd.DataFrame:
    """Clasifica productos en líneas estratégicas"""
    config = AppConfig()
    
    if 'linea_producto' in df.columns:
        df['Linea_Estrategica'] = df['linea_producto'].fillna('Otros').astype(str)
    else:
        if 'nombre_articulo' in df.columns:
            def clasificar_por_nombre(nombre):
                if pd.isna(nombre):
                    return 'Otros'
                nombre_upper = str(nombre).upper()
                for linea in config.LINEAS_ESTRATEGICAS:
                    if linea.upper() in nombre_upper:
                        return linea
                return 'Otros'
            
            df['Linea_Estrategica'] = df['nombre_articulo'].apply(clasificar_por_nombre)
        else:
            df['Linea_Estrategica'] = 'Sin Clasificar'
    
    df['Linea_Estrategica'] = df['Linea_Estrategica'].astype(str).str.strip()
    
    if 'marca_producto' in df.columns:
        def clasificar_categoria(marca):
            if pd.isna(marca):
                return 'Otros'
            marca_upper = str(marca).upper()
            if any(x in marca_upper for x in ['PINTUCO', 'SIKA', 'CORONA']):
                return 'Premium'
            elif any(x in marca_upper for x in ['MEGA', 'MASTER']):
                return 'Estandar'
            return 'Otros'
        
        df['Categoria_Master'] = df['marca_producto'].apply(clasificar_categoria)
    else:
        df['Categoria_Master'] = 'Sin Categoría'
    
    return df

def _enriquecer_geografia(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega información geográfica"""
    if 'nomvendedor' not in df.columns:
        df['nomvendedor'] = 'GENERAL'
    else:
        df['nomvendedor'] = df['nomvendedor'].fillna('GENERAL').astype(str)
    
    df_poblaciones = cargar_poblaciones()
    
    if df_poblaciones.empty or 'cliente_id' not in df.columns:
        df['Poblacion_Real'] = 'Sin Geo'
        return df
    
    df = pd.merge(df, df_poblaciones, on='cliente_id', how='left')
    df['Poblacion_Real'] = df['Poblacion_Real'].fillna('Sin Geo').astype(str)
    
    return df

def _aplicar_filtro_ytd(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica filtro Year-To-Date"""
    hoy = date.today()
    
    if 'fecha_venta' not in df.columns:
        if all(col in df.columns for col in ['anio', 'mes']):
            df['fecha_venta'] = pd.to_datetime(
                df[['anio', 'mes']].assign(dia=15),
                errors='coerce'
            )
    
    def es_ytd(row):
        try:
            if row['mes'] < hoy.month:
                return True
            if row['mes'] == hoy.month:
                return True
            return False
        except:
            return False
    
    df_ytd = df[df.apply(es_ytd, axis=1)].copy()
    
    if df_ytd.empty:
        return df
    
    return df_ytd