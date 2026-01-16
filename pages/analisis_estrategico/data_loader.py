"""Gestión de carga y transformación de datos"""
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
            st.error("⚠️ Token de Dropbox no configurado")
            return None
        return dropbox.Dropbox(token)
    except Exception as e:
        st.error(f"Error conectando a Dropbox: {e}")
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
        df_clean.columns = ['Key_Nit', 'Poblacion_Real']
        df_clean['Key_Nit'] = df_clean['Key_Nit'].astype(str).str.strip().str.replace('.0', '', regex=False)
        df_clean['Poblacion_Real'] = df_clean['Poblacion_Real'].astype(str).str.strip().str.upper()
        
        return df_clean.dropna()
    except Exception as e:
        st.warning(f"Error procesando poblaciones: {e}")
        return pd.DataFrame()

def cargar_y_validar_datos() -> Tuple[pd.DataFrame, Dict]:
    """Pipeline completo de carga y limpieza de datos"""
    if 'df_ventas' not in st.session_state:
        st.warning("⚠️ **Por favor, carga el archivo maestro en la página principal.**")
        st.info("👉 Ve a **🏠 Resumen Mensual** para cargar los datos")
        st.stop()
    
    try:
        df_raw = st.session_state.df_ventas.copy()
        
        # Validar que hay datos
        if df_raw.empty:
            st.error("❌ El DataFrame está vacío")
            st.stop()
        
        st.info(f"📊 Registros iniciales: {len(df_raw):,}")
        
        # Pipeline de transformación con manejo de errores
        df_clean = df_raw.copy()
        
        # PASO 1: Mapear columnas
        with st.spinner("🔄 Mapeando columnas..."):
            df_clean = _mapear_columnas(df_clean)
            st.success(f"✅ Columnas mapeadas. Registros: {len(df_clean):,}")
        
        # PASO 2: Limpiar tipos de datos
        with st.spinner("🔄 Limpiando tipos de datos..."):
            df_clean = _limpiar_tipos_datos(df_clean)
            st.success(f"✅ Tipos limpiados. Registros: {len(df_clean):,}")
        
        # PASO 3: Clasificar marcas
        with st.spinner("🔄 Clasificando marcas..."):
            df_clean = _clasificar_marcas(df_clean)
            st.success(f"✅ Marcas clasificadas. Registros: {len(df_clean):,}")
        
        # PASO 4: Enriquecer geografía
        with st.spinner("🔄 Enriqueciendo datos geográficos..."):
            df_clean = _enriquecer_geografia(df_clean)
            st.success(f"✅ Geografía enriquecida. Registros: {len(df_clean):,}")
        
        # PASO 5: Aplicar filtro YTD
        with st.spinner("🔄 Aplicando filtro Year-To-Date..."):
            df_clean = _aplicar_filtro_ytd(df_clean)
            st.success(f"✅ Filtro YTD aplicado. Registros: {len(df_clean):,}")
        
        # Validar resultado final
        if df_clean.empty:
            st.error("❌ No hay datos después del procesamiento")
            st.warning("Verifica que:")
            st.markdown("- Los datos tengan años válidos (> 2000)")
            st.markdown("- Existan registros dentro del año actual (YTD)")
            st.stop()
        
        # Extraer años válidos
        anios_disponibles = sorted([
            int(a) for a in df_clean['anio'].unique() 
            if pd.notna(a) and a > 2000
        ], reverse=True)
        
        if len(anios_disponibles) < 2:
            st.error("❌ Se necesitan al menos 2 años de datos para análisis comparativo")
            st.info(f"Años disponibles: {anios_disponibles}")
            st.stop()
        
        config_filtros = {
            'anios_disponibles': anios_disponibles,
            'ciudades_disponibles': sorted(df_clean['Poblacion_Real'].dropna().unique()),
            'marcas_disponibles': sorted(df_clean['Marca_Master'].dropna().unique()),
            'categorias_disponibles': sorted(df_clean['Categoria_Master'].dropna().unique())
        }
        
        st.success(f"✅ **Datos cargados exitosamente:** {len(df_clean):,} registros")
        
        return df_clean, config_filtros
        
    except Exception as e:
        st.error(f"❌ Error en pipeline de datos: {str(e)}")
        st.exception(e)
        st.stop()

def _mapear_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Mapea columnas a nombres estándar"""
    config = AppConfig()
    
    # Mapear solo las columnas que existen
    rename_dict = {}
    for idx, new_name in config.COLUMNAS_MAESTRAS.items():
        if idx < len(df.columns):
            rename_dict[df.columns[idx]] = new_name
    
    df = df.rename(columns=rename_dict)
    
    # Asegurar columna 'dia' existe
    if 'dia' not in df.columns:
        df['dia'] = 15
    
    # Asegurar columnas críticas existen
    columnas_requeridas = ['anio', 'mes', 'VALOR', 'CLIENTE', 'COD']
    for col in columnas_requeridas:
        if col not in df.columns:
            if col == 'VALOR':
                df[col] = 0
            elif col in ['anio', 'mes']:
                from datetime import date
                df[col] = date.today().year if col == 'anio' else 1
            else:
                df[col] = 'N/A'
    
    return df

def _limpiar_tipos_datos(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas a tipos correctos"""
    from datetime import date
    hoy = date.today()
    
    # Limpiar valores antes de convertir
    if 'VALOR' in df.columns:
        df['VALOR'] = pd.to_numeric(df['VALOR'], errors='coerce').fillna(0)
    
    if 'anio' in df.columns:
        df['anio'] = pd.to_numeric(df['anio'], errors='coerce').fillna(hoy.year).astype(int)
    
    if 'mes' in df.columns:
        df['mes'] = pd.to_numeric(df['mes'], errors='coerce').fillna(1).astype(int)
        df['mes'] = df['mes'].clip(1, 12)
    
    if 'dia' in df.columns:
        df['dia'] = pd.to_numeric(df['dia'], errors='coerce').fillna(15).astype(int)
        df['dia'] = df['dia'].clip(1, 31)
    
    if 'COD' in df.columns:
        df['Key_Nit'] = df['COD'].astype(str).str.strip().str.replace('.0', '', regex=False)
    
    # Asegurar que las columnas de texto no sean nulas
    if 'CLIENTE' in df.columns:
        df['CLIENTE'] = df['CLIENTE'].fillna('Sin Cliente')
    
    return df

def _clasificar_marcas(df: pd.DataFrame) -> pd.DataFrame:
    """Clasifica marcas según código"""
    config = AppConfig()
    
    def clasificar_fila(codigo_marca):
        try:
            codigo = int(codigo_marca) if pd.notna(codigo_marca) else 0
        except (ValueError, TypeError):
            codigo = 0
        
        marca = config.MAPEO_MARCAS.get(codigo, f"Código {codigo}")
        prefijo = marca.split('-')[0] if '-' in marca else marca[:3]
        categoria = config.CATEGORIAS_MARCA.get(prefijo, "Otros")
        return marca, categoria
    
    # Aplicar y desempaquetar
    if 'CODIGO_MARCA_N' in df.columns:
        resultados = df['CODIGO_MARCA_N'].apply(clasificar_fila)
        df['Marca_Master'] = [r[0] for r in resultados]
        df['Categoria_Master'] = [r[1] for r in resultados]
    else:
        df['Marca_Master'] = 'Sin Marca'
        df['Categoria_Master'] = 'Sin Categoría'
    
    return df

def _enriquecer_geografia(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega información geográfica"""
    # Primero asegurar que existe la columna Vendedor
    if 'Vendedor' not in df.columns:
        df['Vendedor'] = 'GENERAL'
    else:
        df['Vendedor'] = df['Vendedor'].fillna('GENERAL')
    
    # Cargar poblaciones
    df_poblaciones = cargar_poblaciones()
    
    # Si no hay datos de poblaciones, asignar valor por defecto
    if df_poblaciones.empty:
        df['Poblacion_Real'] = 'Sin Geo'
        return df
    
    # Hacer merge solo si hay datos
    df = pd.merge(df, df_poblaciones, on='Key_Nit', how='left')
    df['Poblacion_Real'] = df['Poblacion_Real'].fillna('Sin Geo')
    
    return df

def _aplicar_filtro_ytd(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica filtro Year-To-Date"""
    hoy = date.today()
    
    def es_ytd(row):
        try:
            if row['mes'] < hoy.month:
                return True
            if row['mes'] == hoy.month:
                return row['dia'] <= hoy.day
            return False
        except:
            return False
    
    df_ytd = df[df.apply(es_ytd, axis=1)].copy()
    
    # Si el filtro YTD deja el DataFrame vacío, mostrar advertencia
    if df_ytd.empty:
        st.warning("⚠️ El filtro Year-To-Date no devolvió registros. Mostrando todos los datos disponibles.")
        return df
    
    return df_ytd