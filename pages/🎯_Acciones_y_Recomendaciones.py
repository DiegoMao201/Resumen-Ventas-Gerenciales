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
# 1. CONFIGURACIÓN Y ESTILOS (SALA DE GUERRA)
# ==========================================
st.set_page_config(
    page_title="Segumiento Actividad | Pintuco",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Avanzado para Alta Densidad de Información
st.markdown("""
<style>
    /* Fondo general más profesional */
    .reportview-container { background: #f4f6f9; }
    h1, h2, h3 { color: #1565c0; font-family: 'Roboto', sans-serif; margin-bottom: 0px; }
    
    /* Tarjetas KPI Superiores */
    .kpi-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-top: 4px solid #1565c0;
        text-align: center;
    }
    .kpi-val { font-size: 24px; font-weight: 800; color: #2c3e50; }
    .kpi-lbl { font-size: 12px; text-transform: uppercase; color: #7f8c8d; letter-spacing: 0.5px; }
    
    /* Contenedores de Acción (Columnas) */
    .action-col-header {
        font-size: 16px; font-weight: bold; padding: 10px; text-align: center; color: white; border-radius: 5px 5px 0 0;
    }
    .header-red { background-color: #e53935; }
    .header-blue { background-color: #1e88e5; }
    .header-green { background-color: #43a047; }
    
    .action-item {
        background-color: white;
        padding: 10px;
        border-bottom: 1px solid #eee;
        font-size: 13px;
        border-left: 3px solid transparent;
    }
    .action-item:hover { background-color: #f1f8e9; }
    .border-red { border-left-color: #e53935; }
    .border-blue { border-left-color: #1e88e5; }
    .border-green { border-left-color: #43a047; }
    
    /* Tablas compactas */
    .stDataFrame { font-size: 12px; }
</style>
""", unsafe_allow_html=True)

META_CANAL = 590_000_000  # Meta global

# ==========================================
# 2. CONECTIVIDAD Y LIMPIEZA (MOTOR ROBUSTO)
# ==========================================

def get_dropbox_client():
    try:
        return dropbox.Dropbox(
            app_key=st.secrets.dropbox.app_key,
            app_secret=st.secrets.dropbox.app_secret,
            oauth2_refresh_token=st.secrets.dropbox.refresh_token,
        )
    except Exception:
        return None

def normalizar_num(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def _normalizar_txt(txt: str) -> str:
    if pd.isna(txt): return ""
    t = "".join(c for c in unicodedata.normalize("NFD", str(txt)) if unicodedata.category(c) != "Mn")
    return t.strip().upper()

def limpiar_df_ventas(df: pd.DataFrame) -> pd.DataFrame:
    dfc = df.copy()
    if "anio" in dfc: dfc["anio"] = pd.to_numeric(dfc["anio"], errors="coerce").astype(int)
    if "mes" in dfc: dfc["mes"] = pd.to_numeric(dfc["mes"], errors="coerce").astype(int)
    if "valor_venta" in dfc: dfc["valor_venta"] = pd.to_numeric(dfc["valor_venta"], errors="coerce").fillna(0)
    
    cols_str = ["NIT", "cliente_id", "nomvendedor", "marca_producto", "nombre_marca", "nombre_producto", "super_categoria"]
    for col in cols_str:
        if col in dfc: dfc[col] = dfc[col].astype(str).str.strip()
    
    if "fecha_venta" in dfc: 
        dfc["fecha_venta"] = pd.to_datetime(dfc["fecha_venta"], errors="coerce")
    return dfc

def preparar_cliente_tipo(df_raw: pd.DataFrame) -> pd.DataFrame:
    ren = {
        "Código": "codigo_vendedor_tipo", "NOMVENDEDOR": "nomvendedor", 
        "CODIGO_TIPO_NEGOCIO": "codigo_tipo_negocio", "NOMBRE_TIPO_NEGOCIO": "nombre_tipo_negocio",
        "CODIGO_PRODUCTO": "codigo_producto", "NOMBRE_PRODUCTO": "nombre_producto",
        "Cod. Cliente": "codigo_cliente", "NOMBRECLIENTE": "nombre_cliente", "NIT": "nit",
        "Fecha": "fecha", "VALOR_TOTAL_ITEM_VENDIDO": "valor_total_item_vendido"
    }
    df = df_raw.rename(columns=ren)
    
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df["anio"] = df["fecha"].dt.year
        df["mes"] = df["fecha"].dt.month
        
    for col in ["nit", "codigo_cliente", "nomvendedor", "nombre_cliente"]:
        if col in df: df[col] = df[col].astype(str).str.strip()
        
    df = normalizar_num(df, ["valor_total_item_vendido"])
    
    if "nombre_tipo_negocio" in df: df["nombre_tipo_negocio"] = df["nombre_tipo_negocio"].apply(_normalizar_txt)
    if "nomvendedor" in df: df["nomvendedor"] = df["nomvendedor"].apply(_normalizar_txt)
    if "nombre_cliente" in df: df["nombre_cliente"] = df["nombre_cliente"].apply(_normalizar_txt)
    return df

@st.cache_data(ttl=1800)
def cargar_cliente_tipo() -> pd.DataFrame:
    dbx = get_dropbox_client()
    if not dbx: return pd.DataFrame()
    try:
        _, res = dbx.files_download(path="/data/CLIENTE_TIPO.xlsx")
        df = pd.read_excel(io.BytesIO(res.content))
        return preparar_cliente_tipo(df)
    except Exception:
        return pd.DataFrame()

# ==========================================
# 3. LÓGICA DE NEGOCIO (PRESUPUESTO Y REAL)
# ==========================================

def asignar_presupuesto_detallista(df_tipo: pd.DataFrame, meta_total: float, canales=None) -> pd.DataFrame:
    canales = canales or ["DETALLISTAS", "FERRETERIA"]
    canales_norm = [_normalizar_txt(c) for c in canales]
    
    df_tipo["nombre_tipo_negocio_norm"] = df_tipo["nombre_tipo_negocio"].apply(_normalizar_txt)
    mask = df_tipo["nombre_tipo_negocio_norm"].apply(lambda x: any(c in x for c in canales_norm))
    df_det = df_tipo[mask].copy()
    
    if df_det.empty: return pd.DataFrame()

    ventas_2025 = df_det[df_det["anio"] == 2025]
    base_vtas_vend = ventas_2025.groupby("nomvendedor")["valor_total_item_vendido"].sum().reset_index()
    total_base = base_vtas_vend["valor_total_item_vendido"].sum()
    
    if total_base <= 0: return pd.DataFrame()

    base_vtas_vend["presupuesto_vendedor"] = meta_total * (base_vtas_vend["valor_total_item_vendido"] / total_base)
    df_det = df_det.merge(base_vtas_vend[["nomvendedor", "presupuesto_vendedor"]], on="nomvendedor", how="left")
    
    ventas_2025_vend = ventas_2025.groupby("nomvendedor")["valor_total_item_vendido"].sum().to_dict()
    df_det["peso_cliente_vend"] = df_det.apply(
        lambda r: (r["valor_total_item_vendido"] / ventas_2025_vend.get(r["nomvendedor"], 1))
        if ventas_2025_vend.get(r["nomvendedor"], 0) > 0 else 0, axis=1
    )
    df_det["presupuesto_meta"] = df_det["presupuesto_vendedor"] * df_det["peso_cliente_vend"]
    
    total_asignado = df_det["presupuesto_meta"].sum()
    if total_asignado > 0:
        factor = meta_total / total_asignado
        df_det["presupuesto_meta"] *= factor
        
    return df_det

def resumen_por_vendedor(df_det: pd.DataFrame) -> pd.DataFrame:
    if df_det.empty: return pd.DataFrame()
    return df_det.groupby("nomvendedor").agg(
        venta_2025=("valor_total_item_vendido", "sum"),
        presupuesto=("presupuesto_meta", "sum"),
        clientes=("codigo_cliente", "nunique")
    ).reset_index().sort_values("presupuesto", ascending=False)

def ventas_reales_periodo(df_ventas: pd.DataFrame, df_det: pd.DataFrame, canales=None) -> pd.DataFrame:
    if df_ventas.empty or df_det.empty: return pd.DataFrame()
    clientes_det = set(df_det["codigo_cliente"].dropna().astype(str)) | set(df_det["nit"].dropna().astype(str))
    
    df = df_ventas.copy()
    mask_fecha = (df["anio"] == 2026) & (df["mes"] == 1)
    if "fecha_venta" in df.columns:
        mask_fecha = mask_fecha & (df["fecha_venta"].dt.day.between(16, 31))
    
    mask_cliente = False
    if "cliente_id" in df.columns: mask_cliente = df["cliente_id"].astype(str).isin(clientes_det)
    if "NIT" in df.columns: mask_cliente = mask_cliente | df["NIT"].astype(str).isin(clientes_det)
    
    # Filtro de marca FLEXIBLE (No frena si no hay Pintuco)
    mask_marca = True
    col_marca = next((c for c in ["marca_producto", "nombre_marca", "MARCA"] if c in df.columns), None)
    if col_marca:
        filtro = df[col_marca].astype(str).str.upper().str.contains("PINTUCO", na=False)
        if filtro.sum() > 0: mask_marca = filtro

    df_final = df[mask_fecha & mask_cliente & mask_marca]
    if df_final.empty: return pd.DataFrame()
    
    if "nomvendedor" in df_det.columns and "nomvendedor" in df_final.columns:
        df_final["nomvendedor"] = df_final["nomvendedor"].astype(str)
    
    return df_final.groupby(["nomvendedor", "cliente_id"], as_index=False)["valor_venta"].sum()

def tabla_seguimiento_vendedor(df_meta_vend: pd.DataFrame, df_real: pd.DataFrame) -> pd.DataFrame:
    if df_meta_vend.empty: return pd.DataFrame()
    if df_real.empty: 
        out = df_meta_vend.copy()
        out["venta_real"] = 0; out["avance_pct"] = 0
        return out
    
    real_vend = df_real.groupby("nomvendedor", as_index=False)["valor_venta"].sum().rename(columns={"valor_venta": "venta_real"})
    out = df_meta_vend.merge(real_vend, on="nomvendedor", how="left").fillna({"venta_real": 0})
    out["avance_pct"] = np.where(out["presupuesto"] > 0, (out["venta_real"] / out["presupuesto"]) * 100, 0)
    return out.sort_values("presupuesto", ascending=False)

def tabla_seguimiento_cliente(df_det: pd.DataFrame, df_real: pd.DataFrame) -> pd.DataFrame:
    if df_det.empty: return pd.DataFrame()
    base = df_det.groupby(["codigo_cliente", "nombre_cliente", "nomvendedor"], as_index=False)["presupuesto_meta"].sum()
    base = base.rename(columns={"codigo_cliente": "cliente_id"})
    
    if df_real.empty:
        base["venta_real"] = 0; base["avance_pct"] = 0; base["gap"] = base["presupuesto_meta"]
        return base
        
    real_cli = df_real.groupby("cliente_id", as_index=False)["valor_venta"].sum().rename(columns={"valor_venta": "venta_real"})
    out = base.merge(real_cli, on="cliente_id", how="left").fillna({"venta_real": 0})
    out["avance_pct"] = np.where(out["presupuesto_meta"] > 0, (out["venta_real"] / out["presupuesto_meta"]) * 100, 0)
    out["gap"] = out["presupuesto_meta"] - out["venta_real"]
    return out.sort_values("presupuesto_meta", ascending=False)

# ==========================================
# 4. INTELIGENCIA DE NEGOCIO (CATEGORIZADA)
# ==========================================

def clasificar_acciones(df_seg_vend, df_seg_cli):
    """Clasifica las acciones en 3 cubos para mostrarlas en columnas."""
    urgentes = []
    oportunidades = []
    cierres = []
    
    # 1. URGENTES (Vendedores colgados)
    criticos = df_seg_vend[(df_seg_vend["avance_pct"] < 50) & (df_seg_vend["presupuesto"] > 8_000_000)]
    for _, row in criticos.iterrows():
        urgentes.append({
            "titulo": row['nomvendedor'],
            "info": f"Avance: {row['avance_pct']:.1f}% | Gap: ${row['presupuesto'] - row['venta_real']:,.0f}",
            "accion": "📞 Revisar agenda inmediatamente."
        })

    # 2. OPORTUNIDADES (Clientes Grandes Dormidos)
    dormidos = df_seg_cli[(df_seg_cli["venta_real"] == 0) & (df_seg_cli["presupuesto_meta"] > 3_000_000)].head(10)
    for _, row in dormidos.iterrows():
        oportunidades.append({
            "titulo": row['nombre_cliente'][:25],
            "info": f"Vend: {row['nomvendedor'].split(' ')[0]} | Potencial: ${row['presupuesto_meta']:,.0f}",
            "accion": "🚀 Reactivar pedido ahora."
        })

    # 3. CIERRES (Les falta poco)
    casi = df_seg_cli[(df_seg_cli["avance_pct"] >= 70) & (df_seg_cli["avance_pct"] < 95)].head(10)
    for _, row in casi.iterrows():
        cierres.append({
            "titulo": row['nombre_cliente'][:25],
            "info": f"Al {row['avance_pct']:.0f}% | Falta: ${row['gap']:,.0f}",
            "accion": "⭐ Cerrar antes de fin de mes."
        })
        
    return urgentes, oportunidades, cierres

def exportar_plan_accion_excel(df_acciones: pd.DataFrame, vendedor_stats: dict) -> bytes:
    """
    Genera Excel Premium con Plan de Acción por Vendedor
    Formato profesional, visual y accionable
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Escribir datos
        df_acciones.to_excel(writer, sheet_name='Plan_Activacion', startrow=6, index=False)
        
        wb = writer.book
        ws = writer.sheets['Plan_Activacion']
        
        # --- FORMATOS ---
        fmt_titulo = wb.add_format({
            'bold': True, 'font_size': 18, 'font_color': '#FFFFFF',
            'bg_color': '#1565c0', 'align': 'center', 'valign': 'vcenter'
        })
        fmt_subtitulo = wb.add_format({
            'font_size': 11, 'font_color': '#555555', 'italic': True,
            'align': 'center'
        })
        fmt_kpi_label = wb.add_format({
            'bold': True, 'font_size': 10, 'bg_color': '#e3f2fd',
            'border': 1, 'align': 'right'
        })
        fmt_kpi_valor = wb.add_format({
            'font_size': 12, 'num_format': '$#,##0', 'bg_color': '#f1f8e9',
            'border': 1, 'bold': True
        })
        fmt_header = wb.add_format({
            'bold': True, 'font_color': 'white', 'bg_color': '#1e88e5',
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True
        })
        fmt_vendedor = wb.add_format({
            'bold': True, 'font_size': 11, 'bg_color': '#fff9c4',
            'border': 1, 'align': 'left'
        })
        fmt_cliente = wb.add_format({
            'font_size': 10, 'border': 1, 'text_wrap': True
        })
        fmt_producto = wb.add_format({
            'font_size': 10, 'border': 1, 'bg_color': '#e8f5e9', 'text_wrap': True
        })
        fmt_historico = wb.add_format({
            'num_format': '$#,##0', 'border': 1, 'align': 'right'
        })
        fmt_compras = wb.add_format({
            'border': 1, 'align': 'center', 'num_format': '0'
        })
        fmt_accion = wb.add_format({
            'font_size': 9, 'border': 1, 'italic': True, 'text_wrap': True,
            'font_color': '#c62828'
        })
        
        # --- CABECERA ---
        ws.merge_range('A1:F1', '🎯 PLAN DE ACCIÓN COMERCIAL | Pintuco', fmt_titulo)
        ws.merge_range('A2:F2', f'Periodo: 16-31 Enero 2026 | Canal: Detallistas & Ferretería', fmt_subtitulo)
        ws.set_row(0, 30)
        ws.set_row(1, 18)
        
        # --- KPIs EJECUTIVOS (Fila 4) ---
        ws.write('A4', 'META TOTAL:', fmt_kpi_label)
        ws.write('B4', vendedor_stats.get('meta_total', 0), fmt_kpi_valor)
        ws.write('C4', 'VENTA ACTUAL:', fmt_kpi_label)
        ws.write('D4', vendedor_stats.get('venta_actual', 0), fmt_kpi_valor)
        ws.write('E4', 'GAP (FALTA):', fmt_kpi_label)
        ws.write('F4', vendedor_stats.get('gap', 0), fmt_kpi_valor)
        
        # --- ENCABEZADOS TABLA (Fila 7) ---
        headers = ['Vendedor', 'Cliente a Contactar', 'Producto a Ofrecer', 
                   'Compras Históricas', 'Valor Histórico', '🚀 ACCIÓN INMEDIATA']
        for col_idx, header in enumerate(headers):
            ws.write(6, col_idx, header, fmt_header)
        
        # --- APLICAR FORMATOS A DATOS ---
        ultima_fila = 7 + len(df_acciones)
        
        # Columna Vendedor (A)
        ws.set_column('A:A', 22, fmt_vendedor)
        
        # Columna Cliente (B)
        ws.set_column('B:B', 35, fmt_cliente)
        
        # Columna Producto (C)
        ws.set_column('C:C', 40, fmt_producto)
        
        # Columna Compras (D)
        ws.set_column('D:D', 12, fmt_compras)
        
        # Columna Valor (E)
        ws.set_column('E:E', 18, fmt_historico)
        
        # Columna Acción (F)
        ws.set_column('F:F', 45, fmt_accion)
        
        # --- FORMATO CONDICIONAL: Resaltar alta prioridad ---
        ws.conditional_format(f'E8:E{ultima_fila}', {
            'type': '3_color_scale',
            'min_color': '#ffffff',
            'mid_color': '#fff9c4',
            'max_color': '#4caf50'
        })
        
        # --- AJUSTES FINALES ---
        ws.freeze_panes(7, 0)  # Congelar encabezados
        ws.autofilter(6, 0, ultima_fila - 1, 5)  # Filtros automáticos
        ws.set_row(6, 35)  # Altura encabezados
        
        # Ajustar altura de filas de datos (auto-wrap)
        for row_idx in range(7, ultima_fila):
            ws.set_row(row_idx, 45)
    
    return output.getvalue()

# ==========================================
# 5. UI PRINCIPAL (WAR ROOM)
# ==========================================

if "df_ventas" not in st.session_state or st.session_state.df_ventas is None:
    st.error("⚠️ DATA NO CARGADA. Ve a 'Resumen_Mensual' primero.")
    st.stop()

# Carga
df_ventas = limpiar_df_ventas(st.session_state.df_ventas)
df_tipo_raw = cargar_cliente_tipo()
if df_tipo_raw.empty: st.stop()

# Procesamiento
df_det = asignar_presupuesto_detallista(df_tipo_raw, META_CANAL)
df_meta_vendedor = resumen_por_vendedor(df_det)
df_real_periodo = ventas_reales_periodo(df_ventas, df_det)
df_seg_vend = tabla_seguimiento_vendedor(df_meta_vendedor, df_real_periodo)
df_seg_cli = tabla_seguimiento_cliente(df_det, df_real_periodo)

# Métricas Globales
avance_val = df_seg_vend["venta_real"].sum() if not df_seg_vend.empty else 0
avance_pct = (avance_val / META_CANAL * 100)
gap = META_CANAL - avance_val
proyeccion = avance_val * 1.5 # Estimado simple si falta medio mes (ajustable)

# Acciones Clasificadas
lst_urg, lst_opt, lst_cierre = clasificar_acciones(df_seg_vend, df_seg_cli)

# --- CABECERA ---
st.title("⚔️ SALA DE GUERRA | Pintuco")
st.markdown(f"**Periodo:** 16-31 Ene 2026 | **Foco:** Detallistas & Ferretería | **Actualizado:** {datetime.now().strftime('%H:%M')}")
st.markdown("---")

# --- BLOQUE 1: KPIS SUPERIORES (Alta Visibilidad) ---
c1, c2, c3, c4, c5 = st.columns(5)
def kpi(col, lbl, val, color="#1565c0"):
    col.markdown(f"""
    <div class="kpi-card" style="border-top-color: {color};">
        <div class="kpi-val">{val}</div>
        <div class="kpi-lbl">{lbl}</div>
    </div>
    """, unsafe_allow_html=True)

kpi(c1, "META OBJETIVO", f"${META_CANAL/1e6:,.0f}M")
kpi(c2, "VENTA REAL", f"${avance_val/1e6:,.0f}M", "#2e7d32" if avance_pct>90 else "#fbc02d")
kpi(c3, "GAP (FALTA)", f"${gap/1e6:,.0f}M", "#c62828")
kpi(c4, "% EJECUCIÓN", f"{avance_pct:.1f}%", "#1565c0")
kpi(c5, "PROYECCIÓN CIERRE", f"${proyeccion/1e6:,.0f}M", "#6a1b9a")

# --- BLOQUE 2: MATRIZ DE ACCIÓN (3 COLUMNAS - NO SCROLL ETERNO) ---
st.markdown("### 🧠 Centro de Comando Estratégico")
st.markdown("Acciones inmediatas distribuidas para maximizar cobertura.")

col_red, col_blue, col_green = st.columns(3)

# Columna ROJA
with col_red:
    st.markdown('<div class="action-col-header header-red">🔥 GESTIÓN CRÍTICA (Vendedores)</div>', unsafe_allow_html=True)
    if not lst_urg:
        st.info("✅ Todo el equipo en ritmo.")
    else:
        for item in lst_urg:
            st.markdown(f"""
            <div class="action-item border-red">
                <strong>{item['titulo']}</strong><br>
                <span style="color:#666">{item['info']}</span><br>
                <span style="color:#c62828; font-weight:bold">👉 {item['accion']}</span>
            </div>
            """, unsafe_allow_html=True)

# Columna AZUL
with col_blue:
    st.markdown('<div class="action-col-header header-blue">🚀 ACTIVACIÓN (Clientes Dormidos)</div>', unsafe_allow_html=True)
    if not lst_opt:
        st.info("🔎 Sin clientes grandes inactivos.")
    else:
        for item in lst_opt:
            st.markdown(f"""
            <div class="action-item border-blue">
                <strong>{item['titulo']}</strong><br>
                <span style="color:#666">{item['info']}</span><br>
                <span style="color:#1565c0; font-weight:bold">👉 {item['accion']}</span>
            </div>
            """, unsafe_allow_html=True)

# Columna VERDE
with col_green:
    st.markdown('<div class="action-col-header header-green">⭐ CIERRES INMINENTES (Push Final)</div>', unsafe_allow_html=True)
    if not lst_cierre:
        st.info("⏳ Aun en proceso de maduración.")
    else:
        for item in lst_cierre:
            st.markdown(f"""
            <div class="action-item border-green">
                <strong>{item['titulo']}</strong><br>
                <span style="color:#666">{item['info']}</span><br>
                <span style="color:#2e7d32; font-weight:bold">👉 {item['accion']}</span>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# --- BLOQUE 3: ANÁLISIS PROFUNDO (TABS MEJORADOS) ---
tab1, tab2, tab3 = st.tabs(["📊 Performance Vendedores", "👥 Radar Clientes", "📦 Plan de Acción por Producto & Cliente"])

with tab1:
    st.markdown("##### 🏆 Ranking de Cumplimiento por Vendedor")
    
    if not df_seg_vend.empty:
        df_display = df_seg_vend.copy().replace([np.inf, -np.inf], 0).fillna(0)
        st.dataframe(
            df_display.style.background_gradient(subset=["avance_pct"], cmap="RdYlGn", vmin=0, vmax=110)
            .format({"presupuesto": "${:,.0f}", "venta_real": "${:,.0f}", "avance_pct": "{:.1f}%"}),
            use_container_width=True,
            height=300
        )
        # 🔴 Se quita la Matriz de Esfuerzo (scatter) para centrar la acción en clientes
        st.markdown("✅ Enfoque: usa las pestañas de Activación para movilizar clientes.")
    else:
        st.info("No hay datos de vendedores para mostrar.")

with tab2:
    st.markdown("##### 🚀 Activación de Clientes Dormidos")
    filtro_cli = st.multiselect("Filtrar por Vendedor:", df_seg_vend["nomvendedor"].unique())
    
    df_show = df_seg_cli.copy()
    if filtro_cli:
        df_show = df_show[df_show["nomvendedor"].isin(filtro_cli)]
    
    dormidos = df_show[df_show["venta_real"]==0]
    st.metric("Clientes dormidos", f"{len(dormidos):,}")
    st.metric("Potencial dormido", f"${dormidos['presupuesto_meta'].sum():,.0f}")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.markdown("**Top clientes sin compra (prioridad)**")
        st.dataframe(
            dormidos.sort_values("presupuesto_meta", ascending=False)
            .style.format({"presupuesto_meta": "${:,.0f}"}),
            use_container_width=True, height=400,
            column_config={"cliente_id": None, "avance_pct": None, "gap": None}
        )
    with col_f2:
        st.markdown("**Clientes activos para upsell**")
        activos = df_show[df_show["venta_real"]>0].sort_values("avance_pct", ascending=False)
        st.dataframe(
            activos.style.bar(subset=["avance_pct"], color="#4caf50", vmin=0, vmax=100)
            .format({"presupuesto_meta": "${:,.0f}", "venta_real": "${:,.0f}", "avance_pct": "{:.1f}%"}),
            use_container_width=True, height=400,
            column_config={"cliente_id": None}
        )

with tab3:
    st.markdown("##### 📦 Plan de Acción por Producto & Cliente")
    
    if not df_tipo_raw.empty and not df_seg_cli.empty:
        # 1. Identificar productos frecuentes históricos (2024-2025)
        df_hist = df_tipo_raw[df_tipo_raw["anio"].isin([2024, 2025])]
        
        # Productos más vendidos por cliente
        compras_historicas = df_hist.groupby(["codigo_cliente", "nombre_producto"]).agg(
            total_historico=("valor_total_item_vendido", "sum"),
            veces_comprado=("fecha", "count")
        ).reset_index()
        
        # Filtrar solo productos comprados 2+ veces (frecuentes)
        productos_frecuentes = compras_historicas[compras_historicas["veces_comprado"] >= 2]
        
        # 2. Clientes activos SIN compra en enero 2026
        clientes_dormidos = df_seg_cli[df_seg_cli["venta_real"] == 0]["cliente_id"].unique()
        
        # 3. Cruzar: ¿Qué compraban antes y NO compraron este mes?
        oportunidades_producto = productos_frecuentes[
            productos_frecuentes["codigo_cliente"].isin(clientes_dormidos)
        ].sort_values("total_historico", ascending=False).head(50)  # Top 50 acciones
        
        if not oportunidades_producto.empty:
            # Enriquecer con nombre cliente y vendedor
            oportunidades_producto = oportunidades_producto.merge(
                df_seg_cli[["cliente_id", "nombre_cliente", "nomvendedor"]],
                left_on="codigo_cliente",
                right_on="cliente_id",
                how="left"
            )
            
            st.metric("🎯 Acciones de Reactivación Identificadas", len(oportunidades_producto))
            
            # Mostrar preview visual
            st.markdown("**Vista Previa - Top 10 Acciones:**")
            for idx, row in oportunidades_producto.head(10).iterrows():
                vendedor = row["nomvendedor"].split(" ")[0] if pd.notna(row["nomvendedor"]) else "Sin asignar"
                st.markdown(f"""
                <div style="background: white; padding: 12px; margin: 8px 0; border-radius: 5px; border-left: 4px solid #1e88e5;">
                    <strong style="color: #1565c0;">📞 {vendedor}</strong> → Llamar a <strong>{row['nombre_cliente'][:30]}</strong><br>
                    <span style="color: #666;">💡 Producto: <strong>{row['nombre_producto'][:40]}</strong></span><br>
                    <span style="font-size: 12px; color: #999;">Compró {row['veces_comprado']} veces | Histórico: ${row['total_historico']:,.0f}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Preparar DataFrame para Excel Premium
            df_export_excel = oportunidades_producto[[
                "nomvendedor", "nombre_cliente", "nombre_producto", 
                "veces_comprado", "total_historico"
            ]].copy()
            
            df_export_excel.columns = ["Vendedor", "Cliente a Contactar", "Producto a Ofrecer",
                                       "Compras Históricas", "Valor Histórico"]
            
            # Agregar columna de acción
            df_export_excel["🚀 ACCIÓN INMEDIATA"] = df_export_excel.apply(
                lambda r: f"☎️ Contactar HOY y ofrecer {r['Producto a Ofrecer'][:30]}. "
                         f"Cliente ya lo compró {int(r['Compras Históricas'])} veces. "
                         f"Potencial de venta: ${r['Valor Histórico']:,.0f}",
                axis=1
            )
            
            # Calcular stats para el Excel
            vendedor_stats = {
                'meta_total': df_seg_vend["presupuesto"].sum() if not df_seg_vend.empty else 0,
                'venta_actual': df_seg_vend["venta_real"].sum() if not df_seg_vend.empty else 0,
                'gap': (df_seg_vend["presupuesto"].sum() - df_seg_vend["venta_real"].sum()) if not df_seg_vend.empty else 0
            }
            
            # Generar Excel Premium
            excel_bytes = exportar_plan_accion_excel(df_export_excel, vendedor_stats)
            
            # Botón de descarga con estilo
            st.download_button(
                label="💎 📥 DESCARGAR PLAN DE ACCIÓN COMPLETO (Excel Premium)",
                data=excel_bytes,
                file_name=f"Plan_Activacion_Pintuco_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
            
            st.info("📌 **Instrucciones:** Descarga el Excel y distribúyelo a tu equipo. Cada vendedor verá claramente qué clientes contactar y qué productos ofrecer.")
            
        else:
            st.success("✅ Todos los clientes frecuentes están activos este mes.")
            
        # 4. Top Productos Históricos (Referencia)
        st.markdown("---")
        st.markdown("##### 📊 Productos Estrella (Referencia 2025)")
        top_prods = (
            df_tipo_raw[df_tipo_raw["anio"] == 2025]
            .groupby("nombre_producto")["valor_total_item_vendido"].sum()
            .reset_index()
            .sort_values("valor_total_item_vendido", ascending=False)
            .head(10)
        )
        
        if not top_prods.empty:
            fig = px.bar(
                top_prods,
                x="valor_total_item_vendido",
                y="nombre_producto",
                orientation="h",
                color="valor_total_item_vendido",
                color_continuous_scale="Greens",
                labels={"valor_total_item_vendido": "Ventas 2025", "nombre_producto": ""}
            )
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos suficientes para generar acciones.")

# Footer
st.markdown("---")
st.markdown("**💡 Tip:** Exporta el plan de acción y asígnalo en tu reunión matutina de ventas.")