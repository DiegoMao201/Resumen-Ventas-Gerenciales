import streamlit as st
import pandas as pd
import numpy as np
import dropbox
import io
import unicodedata
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS (UI/UX)
# ==========================================
st.set_page_config(
    page_title="Torre de Control | Pintuco",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS para el Dashboard Gerencial
st.markdown("""
<style>
    /* Fondo y fuentes */
    .reportview-container { background: #f0f2f6; }
    h1, h2, h3 { color: #0d47a1; font-family: 'Segoe UI', sans-serif; }
    
    /* Tarjetas de KPI */
    .kpi-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 5px solid #0d47a1;
        margin-bottom: 10px;
    }
    .kpi-value { font-size: 28px; font-weight: bold; color: #1a1a1a; }
    .kpi-label { color: #666; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Alertas y Acciones */
    .action-card {
        background-color: #e3f2fd;
        border-left: 5px solid #2196f3;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .action-alert {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    
    /* Tablas */
    .stDataFrame { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

META_CANAL = 590_000_000  # Meta global DETALLISTAS + FERRETERIA

# ==========================================
# 2. UTILIDADES Y CONEXIÓN (Mismo motor robusto)
# ==========================================

def get_dropbox_client():
    """Conexión a Dropbox usando st.secrets."""
    try:
        return dropbox.Dropbox(
            app_key=st.secrets.dropbox.app_key,
            app_secret=st.secrets.dropbox.app_secret,
            oauth2_refresh_token=st.secrets.dropbox.refresh_token,
        )
    except Exception:
        return None

def normalizar_num(df: pd.DataFrame, cols):
    """Convierte columnas a numérico forzado, rellenando con 0."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def _normalizar_txt(txt: str) -> str:
    """Elimina tildes y pone en mayúsculas."""
    if pd.isna(txt): return ""
    t = "".join(c for c in unicodedata.normalize("NFD", str(txt)) if unicodedata.category(c) != "Mn")
    return t.strip().upper()

def limpiar_df_ventas(df: pd.DataFrame) -> pd.DataFrame:
    """Limpieza profunda del DF de ventas traído de Resumen_Mensual."""
    dfc = df.copy()
    # Numéricos
    if "anio" in dfc: dfc["anio"] = pd.to_numeric(dfc["anio"], errors="coerce").astype(int)
    if "mes" in dfc: dfc["mes"] = pd.to_numeric(dfc["mes"], errors="coerce").astype(int)
    if "valor_venta" in dfc: dfc["valor_venta"] = pd.to_numeric(dfc["valor_venta"], errors="coerce").fillna(0)
    
    # Strings clave
    cols_str = ["NIT", "cliente_id", "nomvendedor", "marca_producto", "nombre_marca", "nombre_producto", "super_categoria"]
    for col in cols_str:
        if col in dfc: 
            dfc[col] = dfc[col].astype(str).str.strip()
    
    # Fechas
    if "fecha_venta" in dfc: 
        dfc["fecha_venta"] = pd.to_datetime(dfc["fecha_venta"], errors="coerce")
        
    return dfc

def preparar_cliente_tipo(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Estandariza el archivo CLIENTE_TIPO."""
    ren = {
        "Código": "codigo_vendedor_tipo", "NOMVENDEDOR": "nomvendedor", "CEDULA_VENDEDOR": "cedula_vendedor",
        "CODIGO_TIPO_NEGOCIO": "codigo_tipo_negocio", "NOMBRE_TIPO_NEGOCIO": "nombre_tipo_negocio",
        "CODIGO_PRODUCTO": "codigo_producto", "NOMBRE_PRODUCTO": "nombre_producto",
        "TIPO_DE_UNIDAD_PRODUCTO": "tipo_unidad_producto", "TIPO_DE_UNIDAD": "tipo_unidad",
        "Cód. Barras": "cod_barras", "CODIGOMUNICIPIO": "codigomunicipio", "NOMBREMUNICIPIO": "nombremunicipio",
        "Cod. Cliente": "codigo_cliente", "NOMBRECLIENTE": "nombre_cliente", "NIT": "nit",
        "DIRECCION_CLIENTE": "direccion_cliente", "Fecha": "fecha", "NUMERO_DOCUMENTO": "numero_documento",
        "CANTIDAD": "cantidad", "VALOR_TOTAL_ITEM_VENDIDO": "valor_total_item_vendido",
        "Proveedor": "proveedor", "Tipo": "tipo_doc"
    }
    df = df_raw.rename(columns=ren)
    
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df["anio"] = df["fecha"].dt.year
        df["mes"] = df["fecha"].dt.month
        
    for col in ["nit", "codigo_cliente", "nomvendedor", "nombre_cliente"]:
        if col in df: df[col] = df[col].astype(str).str.strip()
        
    df = normalizar_num(df, ["valor_total_item_vendido", "cantidad"])
    
    # Normalizar textos para cruces
    if "nombre_tipo_negocio" in df: df["nombre_tipo_negocio"] = df["nombre_tipo_negocio"].apply(_normalizar_txt)
    if "nomvendedor" in df: df["nomvendedor"] = df["nomvendedor"].apply(_normalizar_txt)
    if "nombre_cliente" in df: df["nombre_cliente"] = df["nombre_cliente"].apply(_normalizar_txt)
    
    return df

@st.cache_data(ttl=1800)
def cargar_cliente_tipo() -> pd.DataFrame:
    """Descarga CLIENTE_TIPO de Dropbox."""
    dbx = get_dropbox_client()
    if not dbx: return pd.DataFrame()
    ruta = "/data/CLIENTE_TIPO.xlsx"
    try:
        _, res = dbx.files_download(path=ruta)
        df = pd.read_excel(io.BytesIO(res.content))
        return preparar_cliente_tipo(df)
    except Exception as e:
        st.error(f"Error cargando Dropbox: {e}")
        return pd.DataFrame()

# ==========================================
# 3. LÓGICA DE CÁLCULO DE PRESUPUESTO
# ==========================================

def asignar_presupuesto_detallista(df_tipo: pd.DataFrame, meta_total: float, canales=None) -> pd.DataFrame:
    """Calcula metas por vendedor y cliente basado en histórico 2025."""
    canales = canales or ["DETALLISTAS", "FERRETERIA"]
    canales_norm = [_normalizar_txt(c) for c in canales]
    
    df_tipo["nombre_tipo_negocio_norm"] = df_tipo["nombre_tipo_negocio"].apply(_normalizar_txt)
    mask_eq = df_tipo["nombre_tipo_negocio_norm"].isin(canales_norm)
    mask_ct = df_tipo["nombre_tipo_negocio_norm"].apply(lambda x: any(c in x for c in canales_norm))
    
    df_det = df_tipo[mask_eq | mask_ct].copy()
    if df_det.empty: return pd.DataFrame()

    # Base 2025
    ventas_2025 = df_det[df_det["anio"] == 2025]
    base_vtas_vend = ventas_2025.groupby("nomvendedor")["valor_total_item_vendido"].sum().reset_index()
    total_base = base_vtas_vend["valor_total_item_vendido"].sum()
    
    if total_base <= 0: return pd.DataFrame()

    # Asignar Meta Vendedor
    base_vtas_vend["presupuesto_vendedor"] = meta_total * (base_vtas_vend["valor_total_item_vendido"] / total_base)
    
    # Asignar Meta Cliente (Peso dentro del vendedor)
    df_det = df_det.merge(base_vtas_vend[["nomvendedor", "presupuesto_vendedor"]], on="nomvendedor", how="left")
    ventas_2025_vend = ventas_2025.groupby("nomvendedor")["valor_total_item_vendido"].sum().to_dict()
    
    df_det["peso_cliente_vend"] = df_det.apply(
        lambda r: (r["valor_total_item_vendido"] / ventas_2025_vend.get(r["nomvendedor"], 1))
        if ventas_2025_vend.get(r["nomvendedor"], 0) > 0 else 0, axis=1
    )
    
    df_det["presupuesto_meta"] = df_det["presupuesto_vendedor"] * df_det["peso_cliente_vend"]
    
    # Ajuste final para cuadrar al centavo
    total_asignado = df_det["presupuesto_meta"].sum()
    if total_asignado > 0:
        factor = meta_total / total_asignado
        df_det["presupuesto_meta"] *= factor
        
    return df_det

def resumen_por_vendedor(df_det: pd.DataFrame) -> pd.DataFrame:
    if df_det.empty: return pd.DataFrame()
    agg = df_det.groupby("nomvendedor").agg(
        venta_2025=("valor_total_item_vendido", "sum"),
        presupuesto=("presupuesto_meta", "sum"),
        clientes=("codigo_cliente", "nunique")
    ).reset_index()
    return agg.sort_values("presupuesto", ascending=False)

# ==========================================
# 4. LÓGICA CRÍTICA DE VENTAS REALES
# ==========================================

def ventas_reales_periodo(df_ventas: pd.DataFrame, df_det: pd.DataFrame, canales=None) -> pd.DataFrame:
    """
    Filtra ventas reales:
    - Periodo: 16 al 31 de Enero 2026.
    - Clientes: Solo los que están en canales objetivo.
    - Marca: Intenta PINTUCO, pero si no hay columna o datos, NO FRENA NADA.
    """
    if df_ventas.empty or df_det.empty: return pd.DataFrame()
    
    # Clientes objetivo (Canal Detallista/Ferreteria)
    clientes_det = set(df_det["codigo_cliente"].dropna().astype(str)) | set(df_det["nit"].dropna().astype(str))
    
    df = df_ventas.copy()
    
    # 1. Filtro Fecha (16-31 Ene 2026)
    mask_fecha = (df["anio"] == 2026) & (df["mes"] == 1)
    if "fecha_venta" in df.columns:
        # Asegurar dia 16 a 31
        mask_fecha = mask_fecha & (df["fecha_venta"].dt.day.between(16, 31))
    
    # 2. Filtro Cliente
    mask_cliente = False
    if "cliente_id" in df.columns: mask_cliente = df["cliente_id"].astype(str).isin(clientes_det)
    if "NIT" in df.columns: mask_cliente = mask_cliente | df["NIT"].astype(str).isin(clientes_det)
    
    # 3. Filtro Marca (FLEXIBLE PARA NO PERDER DATOS)
    # Buscamos columnas candidatas
    col_marca = None
    for c in ["marca_producto", "nombre_marca", "super_categoria", "MARCA"]:
        if c in df.columns:
            col_marca = c
            break
            
    mask_marca = True # Por defecto pasa todo
    if col_marca:
        # Si existe la columna, buscamos PINTUCO
        filtro_pintuco = df[col_marca].astype(str).str.upper().str.contains("PINTUCO", na=False)
        # IMPORTANTE: Si al filtrar Pintuco nos quedamos con 0 filas, 
        # asumimos que la data no tiene la marca bien puesta y DEJAMOS PASAR TODO (para no frenar).
        if filtro_pintuco.sum() > 0:
            mask_marca = filtro_pintuco
        else:
            # Si es 0, ignoramos el filtro de marca
            pass 
            
    # Aplicar Filtros
    df_final = df[mask_fecha & mask_cliente & mask_marca]
    
    if df_final.empty:
        return pd.DataFrame()
        
    if "nomvendedor" in df_det.columns and "nomvendedor" in df_final.columns:
        df_final["nomvendedor"] = df_final["nomvendedor"].astype(str)
    
    # Agrupar por Vendedor y Cliente
    return df_final.groupby(["nomvendedor", "cliente_id"], as_index=False)["valor_venta"].sum()

def tabla_seguimiento_vendedor(df_meta_vend: pd.DataFrame, df_real: pd.DataFrame) -> pd.DataFrame:
    if df_meta_vend.empty: return pd.DataFrame()
    
    if df_real.empty: 
        out = df_meta_vend.copy()
        out["venta_real"] = 0; out["avance_pct"] = 0
        return out.sort_values("presupuesto", ascending=False)
    
    real_vend = df_real.groupby("nomvendedor", as_index=False)["valor_venta"].sum().rename(columns={"valor_venta": "venta_real"})
    out = df_meta_vend.merge(real_vend, on="nomvendedor", how="left").fillna({"venta_real": 0})
    out["avance_pct"] = np.where(out["presupuesto"] > 0, (out["venta_real"] / out["presupuesto"]) * 100, 0)
    return out.sort_values("presupuesto", ascending=False)

def tabla_seguimiento_cliente(df_det: pd.DataFrame, df_real: pd.DataFrame) -> pd.DataFrame:
    if df_det.empty: return pd.DataFrame()
    
    # Agrupar metas por cliente (por si un cliente aparece varias veces en cliente_tipo)
    base = df_det[["codigo_cliente", "nombre_cliente", "nomvendedor", "presupuesto_meta"]].copy()
    base = base.rename(columns={"codigo_cliente": "cliente_id"})
    base = base.groupby(["cliente_id", "nombre_cliente", "nomvendedor"], as_index=False)["presupuesto_meta"].sum()
    
    if df_real.empty:
        out = base.copy(); out["venta_real"] = 0; out["avance_pct"] = 0; out["gap"] = out["presupuesto_meta"]
        return out
        
    real_cli = df_real.groupby("cliente_id", as_index=False)["valor_venta"].sum().rename(columns={"valor_venta": "venta_real"})
    out = base.merge(real_cli, on="cliente_id", how="left").fillna({"venta_real": 0})
    out["avance_pct"] = np.where(out["presupuesto_meta"] > 0, (out["venta_real"] / out["presupuesto_meta"]) * 100, 0)
    out["gap"] = out["presupuesto_meta"] - out["venta_real"]
    return out.sort_values("presupuesto_meta", ascending=False)

# ==========================================
# 5. INTELIGENCIA DE NEGOCIOS (Actionable Insights)
# ==========================================

def generar_acciones_tacticas(df_seg_vend, df_seg_cli, df_hist):
    acciones = []
    
    # 1. Vendedores Críticos (Mucho presupuesto, poca venta)
    criticos = df_seg_vend[(df_seg_vend["avance_pct"] < 40) & (df_seg_vend["presupuesto"] > 10_000_000)]
    for _, row in criticos.iterrows():
        acciones.append({
            "tipo": "alerta",
            "titulo": f"🔴 {row['nomvendedor']} necesita gestión",
            "desc": f"Avance bajo ({row['avance_pct']:.1f}%). Gap: ${row['presupuesto'] - row['venta_real']:,.0f}.",
            "accion": "Revisar agenda y acompañamiento."
        })

    # 2. Clientes Gigantes Dormidos
    dormidos = df_seg_cli[(df_seg_cli["venta_real"] == 0) & (df_seg_cli["presupuesto_meta"] > 4_000_000)].head(5)
    for _, row in dormidos.iterrows():
        acciones.append({
            "tipo": "accion",
            "titulo": f"🚀 Activar: {row['nombre_cliente']}",
            "desc": f"Cliente de {row['nomvendedor']}. Meta: ${row['presupuesto_meta']:,.0f}.",
            "accion": "Llamar para activar pedido."
        })
        
    # 3. Cierre Inminente
    cierre = df_seg_cli[(df_seg_cli["avance_pct"] >= 75) & (df_seg_cli["avance_pct"] < 95)].head(3)
    for _, row in cierre.iterrows():
        acciones.append({
            "tipo": "info",
            "titulo": f"⭐ Cierre Fácil: {row['nombre_cliente']}",
            "desc": f"Está al {row['avance_pct']:.1f}%. Faltan ${row['gap']:,.0f}.",
            "accion": "Push final para cumplir."
        })
        
    return acciones

def analizar_productos_estrella(df_hist):
    if "nombre_producto" not in df_hist.columns: return pd.DataFrame()
    top_prod = df_hist.groupby("nombre_producto")["valor_total_item_vendido"].sum().reset_index()
    top_prod = top_prod.sort_values("valor_total_item_vendido", ascending=False).head(10)
    return top_prod

# ==========================================
# 6. EJECUCIÓN PRINCIPAL
# ==========================================

# Verificación de datos previos
if "df_ventas" not in st.session_state or st.session_state.df_ventas is None or st.session_state.df_ventas.empty:
    st.error("⚠️ No hay datos cargados. Ve a Resumen_Mensual y carga el archivo primero.")
    st.stop()

# Procesamiento de Datos
df_ventas = limpiar_df_ventas(st.session_state.df_ventas)
df_tipo_raw = cargar_cliente_tipo()

if df_tipo_raw.empty:
    st.error("❌ Error con CLIENTE_TIPO en Dropbox. Verifica el archivo.")
    st.stop()

canales_objetivo = ["DETALLISTAS", "FERRETERIA"]

# 1. Asignar Metas
df_det = asignar_presupuesto_detallista(df_tipo_raw, meta_total=META_CANAL, canales=canales_objetivo)
df_meta_vendedor = resumen_por_vendedor(df_det)

# 2. Calcular Real (Sin frenar si falta marca Pintuco)
df_real_periodo = ventas_reales_periodo(df_ventas, df_det, canales=canales_objetivo)

# 3. Tablas de Seguimiento
df_seg_vend = tabla_seguimiento_vendedor(df_meta_vendedor, df_real_periodo)
df_seg_cli = tabla_seguimiento_cliente(df_det, df_real_periodo)

# 4. KPIs Globales
avance_total = df_seg_vend["venta_real"].sum() if not df_seg_vend.empty else 0
avance_pct_global = (avance_total / META_CANAL * 100) if META_CANAL > 0 else 0
gap_total = META_CANAL - avance_total

# 5. Generar Insights
acciones_sugeridas = generar_acciones_tacticas(df_seg_vend, df_seg_cli, df_tipo_raw)
top_productos = analizar_productos_estrella(df_tipo_raw[df_tipo_raw['anio'] == 2025])

# ==========================================
# 7. VISUALIZACIÓN (DASHBOARD)
# ==========================================

st.markdown("## 🗼 Torre de Control Comercial | Pintuco")
st.caption("Foco: Canales Detallistas y Ferretería | Periodo: 16-31 Enero 2026")
st.markdown("---")

# --- BLOQUE KPI SUPERIOR ---
col1, col2, col3, col4 = st.columns(4)
def card(col, label, value, color="#0d47a1"):
    col.markdown(f"""
    <div class="kpi-card" style="border-left: 5px solid {color};">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

card(col1, "META OBJETIVO", f"${META_CANAL/1_000_000:,.0f} M")
card(col2, "VENTA REAL (16-31)", f"${avance_total/1_000_000:,.0f} M", color="#2e7d32" if avance_pct_global > 90 else "#fbc02d")
card(col3, "CUMPLIMIENTO", f"{avance_pct_global:.1f}%", color="#d32f2f" if avance_pct_global < 70 else "#2e7d32")
card(col4, "FALTA PARA META", f"${gap_total/1_000_000:,.0f} M", color="#d32f2f")

# --- BLOQUE CENTRAL: ACCIONES E INSIGHTS ---
st.markdown("### 🧠 Acciones Gerenciales Sugeridas")
col_acc_left, col_acc_right = st.columns([1, 2])

with col_acc_left:
    st.markdown("#### 🚨 Prioridad Alta")
    if not acciones_sugeridas:
        st.success("✅ Sin alertas críticas. Buen ritmo.")
    else:
        for acc in acciones_sugeridas:
            css_class = "action-alert" if acc['tipo'] == 'alerta' else "action-card"
            icon = "🔥" if acc['tipo'] == 'alerta' else "💡"
            st.markdown(f"""
            <div class="{css_class}">
                <strong>{icon} {acc['titulo']}</strong><br>
                <span style="font-size:14px">{acc['desc']}</span><br>
                <em style="color:#0d47a1; font-weight:bold">👉 {acc['accion']}</em>
            </div>
            """, unsafe_allow_html=True)

with col_acc_right:
    st.markdown("#### 📊 Rendimiento de Fuerza de Ventas")
    if not df_seg_vend.empty:
        fig_scatter = px.scatter(
            df_seg_vend, 
            x="presupuesto", 
            y="avance_pct", 
            size="venta_real", 
            color="avance_pct",
            hover_name="nomvendedor",
            text="nomvendedor",
            color_continuous_scale="RdYlGn",
            title="Matriz: Meta vs Cumplimiento"
        )
        fig_scatter.add_hline(y=100, line_dash="dash", line_color="green", annotation_text="Meta 100%")
        fig_scatter.update_traces(textposition='top center')
        fig_scatter.update_layout(height=350, xaxis_title="Presupuesto ($)", yaxis_title="% Cumplimiento")
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Esperando datos de vendedores...")

# --- BLOQUE INFERIOR: DETALLES (TABS) ---
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["👥 Análisis Vendedores", "🏢 Gestión Clientes", "📦 Mix Productos"])

with tab1:
    st.subheader("Ranking Comercial")
    col_v1, col_v2 = st.columns([3, 1])
    with col_v1:
        st.dataframe(
            df_seg_vend.style.background_gradient(subset=["avance_pct"], cmap="RdYlGn", vmin=0, vmax=100)
            .format({"presupuesto": "${:,.0f}", "venta_real": "${:,.0f}", "avance_pct": "{:.1f}%"}),
            use_container_width=True,
            column_config={"nomvendedor": "Vendedor", "clientes": "Clientes Activos"}
        )
    with col_v2:
        st.info("ℹ️ Este ranking ordena por Meta Asignada. Los colores indican % de cumplimiento.")

with tab2:
    st.subheader("Radar de Clientes")
    col_c1, col_c2 = st.columns([3, 1])
    with col_c1:
        filtro = st.radio("Ver:", ["Todos", "Dormidos (Venta=0)", "Casi Logrados"], horizontal=True)
        df_view = df_seg_cli.copy()
        if filtro == "Dormidos (Venta=0)":
            df_view = df_view[df_view["venta_real"] == 0]
        elif filtro == "Casi Logrados":
            df_view = df_view[(df_view["avance_pct"] >= 70) & (df_view["avance_pct"] < 100)]
            
        st.dataframe(
            df_view[["cliente_id", "nombre_cliente", "nomvendedor", "presupuesto_meta", "venta_real", "avance_pct"]]
            .style.bar(subset=["avance_pct"], color="#90caf9", vmin=0, vmax=100)
            .format({"presupuesto_meta": "${:,.0f}", "venta_real": "${:,.0f}", "avance_pct": "{:.1f}%"}),
            use_container_width=True
        )
    with col_c2:
        activos = len(df_seg_cli[df_seg_cli["venta_real"] > 0])
        fig_pie = px.pie(values=[activos, len(df_seg_cli)-activos], names=["Compraron", "Sin Compra"], title="Cobertura Cartera", hole=0.4, color_discrete_sequence=["#2e7d32", "#e0e0e0"])
        st.plotly_chart(fig_pie, use_container_width=True)

with tab3:
    st.subheader("⭐ Productos Estrella (Histórico)")
    if not top_productos.empty:
        fig_prod = px.bar(top_productos.sort_values("valor_total_item_vendido", ascending=True), x="valor_total_item_vendido", y="nombre_producto", orientation='h', title="Top Productos 2025")
        st.plotly_chart(fig_prod, use_container_width=True)
    else:
        st.warning("No hay datos históricos de productos.")

st.caption(f"Actualizado: {datetime.now().strftime('%d-%m-%Y %H:%M')}")