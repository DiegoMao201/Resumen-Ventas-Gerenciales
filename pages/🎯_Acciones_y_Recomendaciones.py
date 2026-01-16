import streamlit as st
import pandas as pd
import numpy as np
import dropbox
import io
import unicodedata
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="🎯 Acciones y Recomendaciones | Pintuco", page_icon="🎯", layout="wide")

# ---------------- Utilidades ----------------
def get_dropbox_client():
    """Usa la misma configuración de Resumen_Mensual (app_key/app_secret/refresh_token)."""
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

def limpiar_df_ventas(df: pd.DataFrame) -> pd.DataFrame:
    dfc = df.copy()
    if "anio" in dfc: dfc["anio"] = pd.to_numeric(dfc["anio"], errors="coerce").astype(int)
    if "mes" in dfc: dfc["mes"] = pd.to_numeric(dfc["mes"], errors="coerce").astype(int)
    if "valor_venta" in dfc: dfc["valor_venta"] = pd.to_numeric(dfc["valor_venta"], errors="coerce").fillna(0)
    for col in ["NIT", "cliente_id", "nomvendedor", "marca_producto"]:
        if col in dfc: dfc[col] = dfc[col].astype(str).str.strip()
    if "nombre_marca" in dfc: dfc["nombre_marca"] = dfc["nombre_marca"].astype(str).str.strip()
    if "fecha_venta" in dfc: dfc["fecha_venta"] = pd.to_datetime(dfc["fecha_venta"], errors="coerce")
    return dfc

def _normalizar_txt(txt: str) -> str:
    if pd.isna(txt): return ""
    t = "".join(c for c in unicodedata.normalize("NFD", str(txt)) if unicodedata.category(c) != "Mn")
    return t.strip().upper()

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
    for col in ["nit", "codigo_cliente", "nomvendedor", "nombre_cliente"]:
        if col in df: df[col] = df[col].astype(str).str.strip()
    normalizar_num(df, ["valor_total_item_vendido", "cantidad"])
    # normalizar canal/cliente/vendedor
    if "nombre_tipo_negocio" in df: df["nombre_tipo_negocio"] = df["nombre_tipo_negocio"].apply(_normalizar_txt)
    if "nomvendedor" in df: df["nomvendedor"] = df["nomvendedor"].apply(_normalizar_txt)
    if "nombre_cliente" in df: df["nombre_cliente"] = df["nombre_cliente"].apply(_normalizar_txt)
    if "codigo_cliente" in df: df["codigo_cliente"] = df["codigo_cliente"].astype(str).str.strip()
    if "nit" in df: df["nit"] = df["nit"].astype(str).str.strip()
    return df

@st.cache_data(ttl=1800)
def cargar_cliente_tipo() -> pd.DataFrame:
    dbx = get_dropbox_client()
    if not dbx:
        st.error("⚠️ No hay token de Dropbox configurado. Configura st.secrets.dropbox.")
        return pd.DataFrame()

    ruta = "/data/CLIENTE_TIPO.xlsx"
    try:
        _, res = dbx.files_download(path=ruta)
        df = pd.read_excel(io.BytesIO(res.content))
        df = preparar_cliente_tipo(df)
        if df.empty:
            st.error("CLIENTE_TIPO.xlsx se leyó, pero quedó vacío. Revisa columnas y datos.")
        else:
            st.info(f"CLIENTE_TIPO.xlsx cargado: {df.shape[0]:,} filas, {df.shape[1]} cols")
        return df
    except Exception as e:
        st.error(f"No se pudo leer {ruta}: {e}")
        return pd.DataFrame()

def asignar_presupuesto_detallista(df_tipo: pd.DataFrame, meta_total: float, canales=None) -> pd.DataFrame:
    canales = canales or ["DETALLISTAS", "FERRETERIA"]
    canales_norm = [_normalizar_txt(c) for c in canales]
    df_tipo["nombre_tipo_negocio_norm"] = df_tipo["nombre_tipo_negocio"].apply(_normalizar_txt)

    mask_eq = df_tipo["nombre_tipo_negocio_norm"].isin(canales_norm)
    mask_ct = df_tipo["nombre_tipo_negocio_norm"].apply(lambda x: any(c in x for c in canales_norm))
    df_det = df_tipo[mask_eq | mask_ct].copy()
    if df_det.empty:
        st.error(
            f"❌ No hay registros de canal {canales} en CLIENTE_TIPO (NOMBRE_TIPO_NEGOCIO). "
            f"Ejemplos: {df_tipo['nombre_tipo_negocio'].dropna().unique()[:10]}"
        )
        return pd.DataFrame()

    # Participación 2025 por vendedor (sobre los canales objetivo)
    ventas_2025 = df_det[df_det["anio"] == 2025]
    base_vtas_vend = ventas_2025.groupby("nomvendedor")["valor_total_item_vendido"].sum().reset_index()
    total_base = base_vtas_vend["valor_total_item_vendido"].sum()
    if total_base <= 0:
        st.error("❌ No hay ventas 2025 en los canales objetivo para calcular la participación.")
        return pd.DataFrame()

    base_vtas_vend["presupuesto_vendedor"] = meta_total * (base_vtas_vend["valor_total_item_vendido"] / total_base)

    # Asignar presupuesto a nivel cliente proporcional a su peso dentro del vendedor
    df_det = df_det.merge(base_vtas_vend[["nomvendedor", "presupuesto_vendedor"]], on="nomvendedor", how="left")
    df_det["peso_cliente_vend"] = 0.0
    df_det["presupuesto_meta"] = 0.0

    # Evita división por cero por vendedor
    ventas_2025_vend = ventas_2025.groupby("nomvendedor")["valor_total_item_vendido"].sum().to_dict()
    df_det["peso_cliente_vend"] = df_det.apply(
        lambda r: (r["valor_total_item_vendido"] / ventas_2025_vend.get(r["nomvendedor"], 1))
        if ventas_2025_vend.get(r["nomvendedor"], 0) > 0 else 0,
        axis=1,
    )
    df_det["presupuesto_meta"] = df_det["presupuesto_vendedor"] * df_det["peso_cliente_vend"]

    # Suma total debe coincidir con meta_total (reescala por seguridad)
    total_asignado = df_det["presupuesto_meta"].sum()
    if total_asignado > 0:
        factor = meta_total / total_asignado
        df_det["presupuesto_meta"] *= factor
        base_vtas_vend["presupuesto_vendedor"] *= factor

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

def ventas_reales_periodo(df_ventas: pd.DataFrame, df_det: pd.DataFrame, canales=None) -> pd.DataFrame:
    """
    Ventas reales Pintuco entre 16-31 enero 2026, solo clientes de los canales objetivo.
    Log de depuración para detectar cortes en el cruce.
    """
    if df_ventas.empty:
        st.warning("Log ventas_reales_periodo: df_ventas vacío")
        return pd.DataFrame()
    if df_det.empty:
        st.warning("Log ventas_reales_periodo: df_det vacío (no hay clientes de canales objetivo)")
        return pd.DataFrame()

    # columnas esperadas
    cols_necesarias = ["anio", "mes", "valor_venta"]
    cols_cliente = [c for c in ["cliente_id", "NIT"] if c in df_ventas.columns]
    cols_vendedor = [c for c in ["nomvendedor"] if c in df_ventas.columns]
    faltantes = [c for c in cols_necesarias if c not in df_ventas.columns]
    if faltantes:
        st.error(f"Log ventas_reales_periodo: faltan columnas en ventas: {faltantes}")
        return pd.DataFrame()

    clientes_det = set(df_det["codigo_cliente"].dropna().astype(str)) | set(df_det["nit"].dropna().astype(str))
    st.info(f"Log ventas_reales_periodo: clientes_det={len(clientes_det)}, cols_cliente={cols_cliente}, cols_vendedor={cols_vendedor}")

    df = df_ventas.copy()
    mask_fecha = (df["anio"] == 2026) & (df["mes"] == 1)
    if "fecha_venta" in df.columns:
        mask_fecha = mask_fecha & (df["fecha_venta"].dt.day.between(16, 31))
    if "marca_producto" in df.columns:
        mask_marca = df["marca_producto"].str.upper().str.contains("PINTUCO", na=False)
    elif "nombre_marca" in df.columns:
        mask_marca = df["nombre_marca"].str.upper().str.contains("PINTUCO", na=False)
    elif "super_categoria" in df.columns:
        mask_marca = df["super_categoria"].str.upper().str.contains("PINTUCO", na=False)
    else:
        mask_marca = True

    # Si no hay coincidencias, no cortar por marca y loguear
    if isinstance(mask_marca, pd.Series) and mask_marca.sum() == 0:
        st.warning("Log ventas_reales_periodo: sin coincidencias de marca PINTUCO; se omite filtro de marca")
        mask_marca = True

    mask_cliente = False
    if "cliente_id" in df.columns:
        mask_cliente = df["cliente_id"].astype(str).isin(clientes_det)
    if "NIT" in df.columns:
        mask_cliente = mask_cliente | df["NIT"].astype(str).isin(clientes_det)

    # Logs de filtrado (seguro para bool/Series)
    marca_cnt = int(mask_marca.sum()) if isinstance(mask_marca, pd.Series) else int(mask_marca) * len(df)
    cliente_cnt = int(mask_cliente.sum()) if isinstance(mask_cliente, pd.Series) else int(mask_cliente) * len(df)
    fecha_cnt = int(mask_fecha.sum()) if isinstance(mask_fecha, pd.Series) else int(mask_fecha) * len(df)

    st.info(
        f"Log ventas_reales_periodo: candidatos iniciales={len(df)}, "
        f"fecha={fecha_cnt}, marca={marca_cnt}, cliente={cliente_cnt}"
    )

    df = df[mask_fecha & mask_marca & mask_cliente]
    if df.empty:
        st.warning("Log ventas_reales_periodo: sin filas tras filtros (fecha/marca/cliente)")
        return pd.DataFrame()

    if "nomvendedor" in df_det.columns:
        df["nomvendedor"] = df["nomvendedor"].astype(str)

    st.info(f"Log ventas_reales_periodo: filas finales={len(df)}, valor_total=${df['valor_venta'].sum():,.0f}")
    return df.groupby(["nomvendedor", "cliente_id"], as_index=False)["valor_venta"].sum()

def tabla_seguimiento_vendedor(df_meta_vend: pd.DataFrame, df_real: pd.DataFrame) -> pd.DataFrame:
    if df_meta_vend.empty:
        return pd.DataFrame()
    if df_real.empty or ("nomvendedor" not in df_real.columns) or ("valor_venta" not in df_real.columns):
        out = df_meta_vend.copy()
        out["venta_real"] = 0
        out["avance_pct"] = 0
        return out.sort_values("presupuesto", ascending=False)

    real_vend = (
        df_real.groupby("nomvendedor", as_index=False)["valor_venta"]
        .sum()
        .rename(columns={"valor_venta": "venta_real"})
    )
    out = df_meta_vend.merge(real_vend, on="nomvendedor", how="left").fillna({"venta_real": 0})
    out["avance_pct"] = np.where(out["presupuesto"] > 0, (out["venta_real"] / out["presupuesto"]) * 100, 0)
    return out.sort_values("presupuesto", ascending=False)

def tabla_seguimiento_cliente(df_det: pd.DataFrame, df_real: pd.DataFrame) -> pd.DataFrame:
    if df_det.empty:
        return pd.DataFrame()
    base = df_det[["codigo_cliente", "nombre_cliente", "nomvendedor", "presupuesto_meta"]].copy()
    base = base.rename(columns={"codigo_cliente": "cliente_id"})
    if df_real.empty or ("cliente_id" not in df_real.columns) or ("valor_venta" not in df_real.columns):
        out = base.copy()
        out["venta_real"] = 0
        out["avance_pct"] = 0
        return out.sort_values("presupuesto_meta", ascending=False)

    real_cli = (
        df_real.groupby("cliente_id", as_index=False)["valor_venta"]
        .sum()
        .rename(columns={"valor_venta": "venta_real"})
    )
    out = base.merge(real_cli, on="cliente_id", how="left").fillna({"venta_real": 0})
    out["avance_pct"] = np.where(out["presupuesto_meta"] > 0, (out["venta_real"] / out["presupuesto_meta"]) * 100, 0)
    return out.sort_values("presupuesto_meta", ascending=False)

def filtrar_ventas_foco(df_ventas: pd.DataFrame, df_det: pd.DataFrame) -> pd.DataFrame:
    """Ventas foco 16-31 Ene 2026, clientes canales objetivo (sin agrupar)."""
    if df_ventas.empty or df_det.empty:
        return pd.DataFrame()
    clientes_det = set(df_det["codigo_cliente"].dropna().astype(str)) | set(df_det["nit"].dropna().astype(str))
    df = df_ventas.copy()
    mask_fecha = (df["anio"] == 2026) & (df["mes"] == 1)
    if "fecha_venta" in df.columns:
        mask_fecha = mask_fecha & (df["fecha_venta"].dt.day.between(16, 31))

    # Marca (si existe)
    if "marca_producto" in df.columns:
        mask_marca = df["marca_producto"].str.upper().str.contains("PINTUCO", na=False)
    elif "nombre_marca" in df.columns:
        mask_marca = df["nombre_marca"].str.upper().str.contains("PINTUCO", na=False)
    elif "super_categoria" in df.columns:
        mask_marca = df["super_categoria"].str.upper().str.contains("PINTUCO", na=False)
    else:
        mask_marca = True
    if isinstance(mask_marca, pd.Series) and mask_marca.sum() == 0:
        mask_marca = True

    mask_cliente = False
    if "cliente_id" in df.columns:
        mask_cliente = df["cliente_id"].astype(str).isin(clientes_det)
    if "NIT" in df.columns:
        mask_cliente = mask_cliente | df["NIT"].astype(str).isin(clientes_det)

    df = df[mask_fecha & mask_marca & mask_cliente]
    return df

def construir_insights(df_seg_vend: pd.DataFrame, df_seg_cli: pd.DataFrame, meta_total: float, avance_total: float) -> list:
    insights = []
    avance_pct = (avance_total / meta_total * 100) if meta_total > 0 else 0
    insights.append(f"Avance global: ${avance_total:,.0f} (${avance_pct:.1f}%).")

    if not df_seg_vend.empty:
        top_v = df_seg_vend.sort_values("presupuesto", ascending=False).head(3)
        rezago = df_seg_vend.sort_values("avance_pct").head(3)
        insights.append(f"Top 3 vendedores por meta: {', '.join(top_v['nomvendedor'].tolist())}.")
        insights.append(f"Vendedores con menor avance: {', '.join(rezago['nomvendedor'].tolist())}.")
    if not df_seg_cli.empty:
        top_gap = df_seg_cli.assign(gap=df_seg_cli["presupuesto_meta"] - df_seg_cli["venta_real"]) \
                            .sort_values("gap", ascending=False).head(3)
        insights.append(f"Top 3 clientes con mayor gap: {', '.join(top_gap['nombre_cliente'].tolist())}.")
    return insights

# ---------------- Validación de sesión ----------------
if "df_ventas" not in st.session_state or st.session_state.df_ventas is None or st.session_state.df_ventas.empty:
    st.error("⚠️ Carga primero los datos en 🏠 Resumen_Mensual.py")
    st.stop()

# ---------------- Carga y preparación ----------------
df_ventas = limpiar_df_ventas(st.session_state.df_ventas)
df_tipo_raw = cargar_cliente_tipo()
if df_tipo_raw.empty:
    st.error("❌ CLIENTE_TIPO no se pudo cargar o está vacío. Verifica Dropbox y formato.")
    st.stop()

meta_total = META_CANAL
canales_objetivo = ["DETALLISTAS", "FERRETERIA"]
df_det = asignar_presupuesto_detallista(df_tipo_raw, meta_total=meta_total, canales=canales_objetivo)
if df_det.empty:
    st.error(f"❌ No hay registros para los canales {canales_objetivo} en CLIENTE_TIPO.")
    st.dataframe(df_tipo_raw.head(50), use_container_width=True)
    st.stop()

df_meta_vendedor = resumen_por_vendedor(df_det)
df_real_periodo = ventas_reales_periodo(df_ventas, df_det, canales=canales_objetivo)
df_ventas_foco = filtrar_ventas_foco(df_ventas, df_det)

# ---------------- UI ----------------
st.title("🎯 Acciones y Recomendaciones | Seguimiento Pintuco")
st.caption("Actividad Pintuco (16-31 Ene 2026) | Meta $590M canales DETALLISTAS + FERRETERIA | Bono 0.5% fuerza comercial")

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

    # === TORRE DE CONTROL: KPIs + Gráficos ===
    st.markdown("---")
    st.subheader("🧭 Torre de Control | Progreso y Ritmo")

    colg1, colg2 = st.columns(2)
    with colg1:
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number",
            value=avance_pct,
            number={"suffix": "%"},
            title={"text": "Cumplimiento Meta Canal"},
            gauge={"axis": {"range": [0, 120]}, "bar": {"color": "#1e3a8a"}}
        ))
        fig_g.update_layout(height=320)
        st.plotly_chart(fig_g, use_container_width=True)
    with colg2:
        if not df_seg_vend.empty:
            fig_bar = px.bar(
                df_seg_vend.sort_values("presupuesto", ascending=False),
                x="nomvendedor",
                y=["presupuesto", "venta_real"],
                barmode="group",
                title="Meta vs Venta Real por Vendedor",
                labels={"value": "Valor", "nomvendedor": "Vendedor"}
            )
            fig_bar.update_layout(height=320, xaxis_tickangle=-35)
            st.plotly_chart(fig_bar, use_container_width=True)

    # Trend diario si hay fecha
    if not df_ventas_foco.empty and "fecha_venta" in df_ventas_foco.columns:
        st.markdown("#### 📈 Ritmo Diario (16-31 Ene)")
        df_day = df_ventas_foco.groupby(df_ventas_foco["fecha_venta"].dt.date)["valor_venta"].sum().reset_index()
        fig_day = px.line(df_day, x="fecha_venta", y="valor_venta", markers=True, title="Ventas Diarias (Pintuco)")
        fig_day.update_layout(height=300)
        st.plotly_chart(fig_day, use_container_width=True)

    # Recomendaciones ejecutivas
    st.markdown("#### ✅ Recomendaciones Accionables")
    for i in construir_insights(df_seg_vend, df_seg_cli, meta_total, avance_total):
        st.markdown(f"- {i}")

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

    # === ACTIVACIÓN DE CLIENTES ===
    st.markdown("---")
    st.subheader("🚀 Activación de Clientes (Prioridad)")
    if not df_seg_cli.empty:
        df_gap = df_seg_cli.copy()
        df_gap["gap"] = df_gap["presupuesto_meta"] - df_gap["venta_real"]
        activacion = df_gap[df_gap["venta_real"] == 0].sort_values("presupuesto_meta", ascending=False).head(20)
        st.dataframe(
            activacion[["cliente_id", "nombre_cliente", "nomvendedor", "presupuesto_meta", "gap"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "presupuesto_meta": st.column_config.NumberColumn("Presupuesto Cliente", format="$%d"),
                "gap": st.column_config.NumberColumn("Gap por Cerrar", format="$%d"),
            },
        )

with tabs[2]:
    st.subheader("🚀 Foco de Crecimiento")
    st.markdown("""
    - Priorizamos el canal **DETALLISTA** según participación 2025 de cada vendedor.
    - Seguimiento a la ventana **16-31 Ene 2026** para la marca **Pintuco**.
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