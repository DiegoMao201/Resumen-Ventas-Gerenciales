import streamlit as st
import pandas as pd
import numpy as np
import io
import dropbox
import datetime

st.set_page_config(page_title="🎯 Acciones y Recomendaciones | Pintuco", page_icon="🎯", layout="wide")

# ---------------- Utilidades ----------------
def get_dropbox_client():
    try:
        token = st.secrets.get("DROPBOX_ACCESS_TOKEN")
        return dropbox.Dropbox(token) if token else None
    except Exception:
        return None

def normalizar_num(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def limpiar_df_ventas(df: pd.DataFrame) -> pd.DataFrame:
    dfc = df.copy()
    if "anio" in dfc: dfc["anio"] = pd.to_numeric(dfc["anio"], errors="coerce").astype(int)
    if "mes" in dfc: dfc["mes"] = pd.to_numeric(dfc["mes"], errors="coerce").astype(int)
    if "valor_venta" in dfc: dfc["valor_venta"] = pd.to_numeric(dfc["valor_venta"], errors="coerce").fillna(0)
    if "NIT" in dfc: dfc["NIT"] = dfc["NIT"].astype(str).str.strip()
    if "cliente_id" in dfc: dfc["cliente_id"] = dfc["cliente_id"].astype(str).str.strip()
    if "marca_producto" in dfc: dfc["marca_producto"] = dfc["marca_producto"].astype(str)
    return dfc

def preparar_cliente_tipo(df_raw: pd.DataFrame) -> pd.DataFrame:
    ren = {
        "Código": "codigo_vendedor_tipo",
        "NOMVENDEDOR": "nomvendedor",
        "CEDULA_VENDEDOR": "cedula_vendedor",
        "CODIGO_TIPO_NEGOCIO": "codigo_tipo_negocio",
        "NOMBRE_TIPO_NEGOCIO": "nombre_tipo_negocio",
        "CODIGO_PRODUCTO": "codigo_producto",
        "NOMBRE_PRODUCTO": "nombre_producto",
        "TIPO_DE_UNIDAD_PRODUCTO": "tipo_unidad_producto",
        "TIPO_DE_UNIDAD": "tipo_unidad",
        "Cód. Barras": "cod_barras",
        "CODIGOMUNICIPIO": "codigomunicipio",
        "NOMBREMUNICIPIO": "nombremunicipio",
        "Cod. Cliente": "codigo_cliente",
        "NOMBRECLIENTE": "nombre_cliente",
        "NIT": "nit",
        "DIRECCION_CLIENTE": "direccion_cliente",
        "Fecha": "fecha",
        "NUMERO_DOCUMENTO": "numero_documento",
        "CANTIDAD": "cantidad",
        "VALOR_TOTAL_ITEM_VENDIDO": "valor_total_item_vendido",
        "Proveedor": "proveedor",
        "Tipo": "tipo_doc"
    }
    df = df_raw.rename(columns=ren)
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
        df["anio"] = df["fecha"].dt.year
        df["mes"] = df["fecha"].dt.month
    if "nit" in df.columns: df["nit"] = df["nit"].astype(str).str.strip()
    if "codigo_cliente" in df.columns: df["codigo_cliente"] = df["codigo_cliente"].astype(str).str.strip()
    normalizar_num(df, ["valor_total_item_vendido", "cantidad"])
    return df

@st.cache_data(ttl=1800)
def cargar_cliente_tipo() -> pd.DataFrame:
    dbx = get_dropbox_client()
    if not dbx:
        st.warning("No hay token de Dropbox configurado.")
        return pd.DataFrame()
    rutas = ["/data/CLIENTE_TIPO.csv", "/data/CLIENTE_TIPO.xlsx"]
    for ruta in rutas:
        try:
            _, res = dbx.files_download(path=ruta)
            if ruta.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(res.content), encoding="latin-1", sep="|")
            else:
                df = pd.read_excel(io.BytesIO(res.content))
            return preparar_cliente_tipo(df)
        except Exception:
            continue
    st.error("No se encontró el archivo CLIENTE_TIPO en Dropbox.")
    return pd.DataFrame()

def asignar_presupuesto_detallista(df_tipo: pd.DataFrame, meta_total: float, canal="DETALLISTA") -> pd.DataFrame:
    df_det = df_tipo[df_tipo["nombre_tipo_negocio"].str.upper() == canal.upper()].copy()
    if df_det.empty:
        return pd.DataFrame()
    ventas_2025 = df_det[df_det["anio"] == 2025]
    base_sum = ventas_2025["valor_total_item_vendido"].sum()
    df_det["participacion_2025"] = np.where(
        base_sum > 0,
        df_det["valor_total_item_vendido"] / base_sum,
        0
    )
    df_det["presupuesto_meta"] = meta_total * df_det["participacion_2025"]
    return df_det

def resumen_por_vendedor(df_det: pd.DataFrame) -> pd.DataFrame:
    if df_det.empty:
        return pd.DataFrame()
    agg = df_det.groupby("nomvendedor").agg(
        venta_2025=("valor_total_item_vendido", "sum"),
        presupuesto=("presupuesto_meta", "sum"),
        clientes=("codigo_cliente", "nunique")
    ).reset_index()
    total_vta = agg["venta_2025"].sum()
    agg["participacion_2025"] = np.where(total_vta > 0, agg["venta_2025"] / total_vta, 0)
    return agg.sort_values("presupuesto", ascending=False)

def ventas_reales_periodo(df_ventas: pd.DataFrame, df_det: pd.DataFrame, canal="DETALLISTA") -> pd.DataFrame:
    if df_ventas.empty or df_det.empty:
        return pd.DataFrame()
    clientes_det = set(df_det["codigo_cliente"].dropna().astype(str)) | set(df_det["nit"].dropna().astype(str))
    df = df_ventas.copy()
    mask_fecha = (df["anio"] == 2026) & (df["mes"] == 1)
    if "fecha_venta" in df.columns:
        df["fecha_venta"] = pd.to_datetime(df["fecha_venta"], errors="coerce")
        mask_fecha = mask_fecha & (df["fecha_venta"].dt.day.between(16, 31))
    if "marca_producto" in df.columns:
        mask_marca = df["marca_producto"].str.upper().str.contains("PINTUCO", na=False)
    else:
        mask_marca = True
    # cruzar por cliente_id o NIT
    mask_cliente = False
    if "cliente_id" in df.columns:
        mask_cliente = df["cliente_id"].astype(str).isin(clientes_det)
    if "NIT" in df.columns:
        mask_cliente = mask_cliente | df["NIT"].astype(str).isin(clientes_det)
    df = df[mask_fecha & mask_marca & mask_cliente]
    if df.empty:
        return pd.DataFrame()
    return df.groupby(["nomvendedor", "cliente_id"], as_index=False)["valor_venta"].sum()

def tabla_seguimiento_vendedor(df_meta_vend: pd.DataFrame, df_real: pd.DataFrame) -> pd.DataFrame:
    if df_meta_vend.empty:
        return pd.DataFrame()
    real_vend = df_real.groupby("nomvendedor")["valor_venta"].sum().rename("venta_real") if not df_real.empty else pd.Series([], dtype=float)
    out = df_meta_vend.merge(real_vend, on="nomvendedor", how="left").fillna({"venta_real": 0})
    out["avance_pct"] = np.where(out["presupuesto"] > 0, (out["venta_real"] / out["presupuesto"]) * 100, 0)
    return out.sort_values("presupuesto", ascending=False)

def tabla_seguimiento_cliente(df_det: pd.DataFrame, df_real: pd.DataFrame) -> pd.DataFrame:
    if df_det.empty:
        return pd.DataFrame()
    real_cli = df_real.groupby("cliente_id")["valor_venta"].sum().rename("venta_real") if not df_real.empty else pd.Series([], dtype=float)
    base = df_det[["codigo_cliente", "nombre_cliente", "nomvendedor", "presupuesto_meta"]].copy()
    base = base.rename(columns={"codigo_cliente": "cliente_id"})
    out = base.merge(real_cli, on="cliente_id", how="left").fillna({"venta_real": 0})
    out["avance_pct"] = np.where(out["presupuesto_meta"] > 0, (out["venta_real"] / out["presupuesto_meta"]) * 100, 0)
    return out.sort_values("presupuesto_meta", ascending=False)

# ---------------- Validación de sesión ----------------
if "df_ventas" not in st.session_state or st.session_state.df_ventas is None or st.session_state.df_ventas.empty:
    st.error("⚠️ Carga primero los datos en 🏠 Resumen_Mensual.py")
    st.stop()

# ---------------- Carga y preparación ----------------
df_ventas = limpiar_df_ventas(st.session_state.df_ventas)
df_tipo_raw = cargar_cliente_tipo()
df_det = asignar_presupuesto_detallista(df_tipo_raw, meta_total=590_000_000, canal="DETALLISTA")
meta_total = 590_000_000
df_meta_vendedor = resumen_por_vendedor(df_det)
df_real_periodo = ventas_reales_periodo(df_ventas, df_det, canal="DETALLISTA")
df_seg_vend = tabla_seguimiento_vendedor(df_meta_vendedor, df_real_periodo)
df_seg_cli = tabla_seguimiento_cliente(df_det, df_real_periodo)

avance_total = df_seg_vend["venta_real"].sum() if not df_seg_vend.empty else 0
avance_pct = (avance_total / meta_total * 100) if meta_total > 0 else 0

# ---------------- UI ----------------
st.title("🎯 Acciones y Recomendaciones | Seguimiento Pintuco")
st.caption("Actividad Pintuco (16-31 Ene 2026) | Meta $590M canal DETALLISTA | Bono 0.5% fuerza comercial")

tabs = st.tabs(["Actividad Pintuco", "Seguimiento Clientes", "Foco de Crecimiento"])

with tabs[0]:
    st.subheader("📌 Actividad Pintuco | Canal Detallista")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Meta Canal", f"${meta_total:,.0f}")
    k2.metric("Ventas Reales (16-31 Ene)", f"${avance_total:,.0f}", f"{avance_pct:.1f}%")
    k3.metric("Bono Fuerza Comercial", "0.5% sobre cumplimiento")
    k4.metric("Vendedores Activos Canal", f"{df_meta_vendedor.shape[0]:,}")
    st.markdown("#### Asignación de Presupuesto por Vendedor")
    st.dataframe(
        df_seg_vend,
        use_container_width=True,
        hide_index=True,
        column_config={
            "nomvendedor": "Vendedor",
            "venta_2025": st.column_config.NumberColumn("Venta 2025", format="$%d"),
            "presupuesto": st.column_config.NumberColumn("Presupuesto Asignado", format="$%d"),
            "venta_real": st.column_config.NumberColumn("Venta Real 16-31 Ene", format="$%d"),
            "avance_pct": st.column_config.ProgressColumn("Avance %", format="%.1f%%", min_value=0, max_value=200),
            "clientes": st.column_config.NumberColumn("Clientes", format="%d"),
            "participacion_2025": st.column_config.ProgressColumn("Part. 2025", format="%.1f%%", min_value=0, max_value=1),
        },
    )

with tabs[1]:
    st.subheader("👥 Seguimiento por Cliente (Detallista)")
    st.info("Presupuesto distribuido según participación 2025 y seguimiento con ventas reales (16-31 Ene, marca Pintuco).")
    st.dataframe(
        df_seg_cli,
        use_container_width=True,
        hide_index=True,
        column_config={
            "cliente_id": "Cliente ID",
            "nombre_cliente": "Cliente",
            "nomvendedor": "Vendedor",
            "presupuesto_meta": st.column_config.NumberColumn("Presupuesto Cliente", format="$%d"),
            "venta_real": st.column_config.NumberColumn("Venta Real", format="$%d"),
            "avance_pct": st.column_config.ProgressColumn("Avance %", format="%.1f%%", min_value=0, max_value=200),
        },
    )

with tabs[2]:
    st.subheader("🚀 Foco de Crecimiento")
    st.markdown("""
    - Priorizamos el canal **DETALLISTA** según participación 2025 de cada vendedor.
    - Seguimiento diario a la ventana **16-31 Ene 2026** para la marca **Pintuco**.
    - Bonificación del **0.5%** sobre el cumplimiento del presupuesto asignado.
    """)
    if not df_seg_vend.empty:
        top_gap = df_seg_vend.sort_values("avance_pct").head(10)[["nomvendedor", "presupuesto", "venta_real", "avance_pct"]]
        st.markdown("##### Top 10 con mayor oportunidad de cierre")
        st.dataframe(
            top_gap,
            use_container_width=True,
            hide_index=True,
            column_config={
                "nomvendedor": "Vendedor",
                "presupuesto": st.column_config.NumberColumn("Meta", format="$%d"),
                "venta_real": st.column_config.NumberColumn("Real", format="$%d"),
                "avance_pct": st.column_config.ProgressColumn("Avance %", format="%.1f%%", min_value=0, max_value=200),
            },
        )
    else:
        st.info("No hay datos disponibles para focos de crecimiento.")

st.markdown("---")
st.caption("Ferreinox S.A.S. BIC | Seguimiento de Actividades Comerciales Pintuco")