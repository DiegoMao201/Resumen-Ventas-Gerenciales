"""Gestión de carga y transformación de datos - Integrado con Resumen_Mensual"""
import streamlit as st
import pandas as pd
import dropbox
import io
from datetime import date
from typing import Tuple, Dict
from .config import AppConfig

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
        
        # Limpiar tipos de datos
        df_clean = _limpiar_tipos_datos(df_clean)
        
        # Clasificar líneas estratégicas
        df_clean = _clasificar_lineas_estrategicas(df_clean)
        
        # Enriquecer geografía
        df_clean = _enriquecer_geografia(df_clean)
        
        # Aplicar filtro YTD
        df_clean = _aplicar_filtro_ytd(df_clean)
        
        if df_clean.empty:
            st.error("❌ No hay datos después del procesamiento")
            st.stop()
        
        # Extraer años válidos
        anios_disponibles = sorted([
            int(a) for a in df_clean['anio'].unique() 
            if pd.notna(a) and a > 2000
        ], reverse=True)
        
        if len(anios_disponibles) < 2:
            st.error("❌ Se necesitan al menos 2 años de datos para análisis comparativo")
            st.stop()
        
        def obtener_lista_ordenada(serie):
            """Obtiene lista ordenada limpiando tipos mixtos"""
            try:
                valores = serie.dropna().unique()
                valores_str = [str(v).strip() for v in valores if v != '' and str(v).strip() != '']
                return sorted(list(set(valores_str)))
            except Exception as e:
                return []
        
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
    
    if 'anio' in df.columns:
        df['anio'] = pd.to_numeric(df['anio'], errors='coerce').fillna(hoy.year).astype(int)
    
    if 'mes' in df.columns:
        df['mes'] = pd.to_numeric(df['mes'], errors='coerce').fillna(1).astype(int)
        df['mes'] = df['mes'].clip(1, 12)
    
    if 'nombre_cliente' in df.columns:
        df['nombre_cliente'] = df['nombre_cliente'].fillna('Sin Cliente').astype(str)
    
    if 'nomvendedor' in df.columns:
        df['nomvendedor'] = df['nomvendedor'].fillna('GENERAL').astype(str)
    
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