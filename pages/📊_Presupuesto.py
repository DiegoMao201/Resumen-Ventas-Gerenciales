import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List
import io

st.set_page_config(page_title="💰 Presupuesto 2026 | Ferreinox", page_icon="💰", layout="wide")

# --- NUEVO: Estilos ejecutivos ---
st.markdown("""
<style>
:root {
  --ferreinox-primary:#1e3a8a; --ferreinox-secondary:#3b82f6;
  --ferreinox-accent:#f59e0b; --ferreinox-success:#10b981;
  --ferreinox-gray:#f8fafc; --ferreinox-dark:#0f172a;
}
.hero {
  background: linear-gradient(135deg, var(--ferreinox-primary), var(--ferreinox-secondary));
  color:white; padding:18px 24px; border-radius:16px; box-shadow:0 12px 30px rgba(17,24,39,0.25);
}
.kpi-grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:14px; margin:10px 0 6px 0;}
.kpi-card {
  background: white; border-radius:14px; padding:14px 16px;
  border:1px solid #e5e7eb; box-shadow:0 6px 18px rgba(0,0,0,0.05);
}
.kpi-label {color:#6b7280; font-size:0.9rem; margin:0;}
.kpi-value {color:var(--ferreinox-dark); font-size:1.8rem; font-weight:800; margin:2px 0;}
.kpi-delta {color:var(--ferreinox-success); font-weight:700;}
.section-title {margin:4px 0 2px 0; font-size:1.05rem;}
.dataframe tbody tr:hover {background:#f1f5f9;}
</style>
""", unsafe_allow_html=True)

def render_header():
    st.markdown(f"""
    <div class="hero">
      <h2 style="margin:0;">💰 Presupuesto 2026 | Ferreinox</h2>
      <p style="margin:4px 0 0 0; color:rgba(255,255,255,0.85);">
        Asignación anual y mensual por participación real 2025, crecimiento y estacionalidad.
      </p>
    </div>
    """, unsafe_allow_html=True)

def kpi_card(label:str, value:str, delta:str=None):
    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ''
    st.markdown(f"""
    <div class="kpi-card">
        <p class="kpi-label">{label}</p>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

# ----------------- Utilidades -----------------
def normalizar_texto(texto: str) -> str:
    import unicodedata, re
    if pd.isna(texto): return ""
    texto = str(texto).upper()
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^A-Z0-9\s\-]", "", texto)
    return texto.strip()

def validar_sesion():
    if "df_ventas" not in st.session_state or st.session_state.df_ventas is None or st.session_state.df_ventas.empty:
        st.error("⚠️ No se encontraron datos de ventas en sesión.")
        st.page_link("🏠 Resumen_Mensual.py", label="Ir a la página principal", icon="🏠")
        st.stop()
    if "DATA_CONFIG" not in st.session_state:
        st.error("⚠️ No se encontró DATA_CONFIG en sesión.")
        st.page_link("🏠 Resumen_Mensual.py", label="Ir a la página principal", icon="🏠")
        st.stop()

def preparar_df(df: pd.DataFrame) -> pd.DataFrame:
    dfc = df.copy()
    dfc["anio"] = pd.to_numeric(dfc["anio"], errors="coerce")
    dfc["mes"] = pd.to_numeric(dfc["mes"], errors="coerce")
    if "valor_venta" in dfc.columns:
        dfc["valor_venta"] = pd.to_numeric(dfc["valor_venta"], errors="coerce").fillna(0)
    if "nomvendedor" in dfc.columns:
        dfc["nomvendedor"] = dfc["nomvendedor"].fillna("SIN VENDEDOR")
    if "linea_producto" in dfc.columns:
        dfc["linea_producto"] = dfc["linea_producto"].fillna("Sin Línea").astype(str)
    return dfc

def _lista_lineas(df: pd.DataFrame) -> List[str]:
    return sorted({str(v).strip() for v in df["linea_producto"].dropna() if str(v).strip()})

def construir_grupo(vendedor: str, grupos: Dict[str, List[str]]) -> str:
    vend_norm = normalizar_texto(vendedor)
    for grupo, lista in grupos.items():
        if vend_norm in [normalizar_texto(v) for v in lista]:
            return normalizar_texto(grupo)
    return vend_norm

def proyectar_total_2026(total_2024, total_2025, escenario: str):
    if total_2024 <= 0 or total_2025 <= 0:
        return total_2025, 0
    tasa_hist = (total_2025 - total_2024) / total_2024
    factor = {"Conservador": 0.8, "Realista": 1.0, "Optimista": 1.2}.get(escenario, 1.0)
    tasa_aplicada = tasa_hist * factor
    return total_2025 * (1 + tasa_aplicada), tasa_aplicada

def calcular_pesos_mensuales(df_hist: pd.DataFrame, vendedor: str, col_valor: str = "valor_venta") -> np.ndarray:
    df_vend = df_hist[df_hist["nomvendedor"] == vendedor]
    df_base = df_vend if not df_vend.empty else df_hist
    pesos = df_base.groupby("mes")[col_valor].sum()
    pesos = pesos.reindex(range(1, 13), fill_value=0)
    total = pesos.sum()
    if total > 0:
        return (pesos / total).values
    return np.array([1 / 12.0] * 12)

def distribuir_presupuesto_mensual(df_asignado: pd.DataFrame, df_hist: pd.DataFrame) -> pd.DataFrame:
    df_hist_2025 = df_hist[df_hist["anio"] == 2025]
    df_hist_base = df_hist_2025 if not df_hist_2025.empty else df_hist[df_hist["anio"] == df_hist["anio"].max()]
    registros = []
    for _, row in df_asignado.iterrows():
        pesos = calcular_pesos_mensuales(df_hist_base, row["nomvendedor"])
        for mes_idx, peso in enumerate(pesos, start=1):
            registros.append({
                "nomvendedor": row["nomvendedor"],
                "grupo": row["grupo"],
                "mes": mes_idx,
                "presupuesto_mensual": row["presupuesto_2026"] * peso
            })
    return pd.DataFrame(registros)

def asignar_presupuesto(df: pd.DataFrame, grupos: Dict[str, List[str]], total_2026: float) -> pd.DataFrame:
    """
    Asigna presupuesto 2026 basado en participación 2025 y tendencia 24-25.
    - Base: venta_2025 (participación real).
    - Ajuste: crecimiento 24-25 limitado para evitar distorsiones.
    - Piso: no cae más de 30% vs 2025.
    - Techo: no sube más de 35% vs 2025 antes de reescalar.
    - Reescalado final al total_2026.
    """
    base = df[df["anio"].isin([2024, 2025])]
    agg = base.groupby("nomvendedor").agg(
        venta_2024=("valor_venta", lambda s: s[df.loc[s.index, "anio"] == 2024].sum()),
        venta_2025=("valor_venta", lambda s: s[df.loc[s.index, "anio"] == 2025].sum()),
        clientes=("cliente_id", "nunique"),
        lineas=("linea_producto", "nunique"),
        marcas=("marca_producto", "nunique")
    ).reset_index()

    total_2025 = agg["venta_2025"].sum()
    agg["participacion_2025"] = np.where(total_2025 > 0, agg["venta_2025"] / total_2025, 0)

    def norm_col(col):
        mx = agg[col].max()
        mn = agg[col].min()
        return np.where(mx > mn, (agg[col] - mn) / (mx - mn), 0.0)

    agg["crec_pct"] = np.where(agg["venta_2024"] > 0, (agg["venta_2025"] - agg["venta_2024"]) / agg["venta_2024"], 0)
    # Limitar impacto para evitar distorsiones extremas
    agg["crec_ajustado"] = np.clip(agg["crec_pct"], -0.15, 0.30)  # -15% a +30%
    agg["diversidad"] = 0.6 * norm_col("lineas") + 0.4 * norm_col("clientes")

    # Score proporcional a venta_2025 con ajuste de crecimiento y ligera prima por diversidad
    agg["score_raw"] = agg["venta_2025"] * (1 + agg["crec_ajustado"]) * (1 + 0.10 * agg["diversidad"])
    suma_scores = agg["score_raw"].sum()
    agg["presupuesto_prelim"] = np.where(suma_scores > 0, agg["score_raw"] / suma_scores * total_2026, 0)

    # Aplicar piso y techo relativos a 2025 antes de reescalar
    piso_pct = 0.70  # no cae más de 30% vs 2025
    techo_pct = 1.35 # no sube más de 35% vs 2025
    agg["presupuesto_ajustado"] = np.clip(
        agg["presupuesto_prelim"],
        agg["venta_2025"] * piso_pct,
        agg["venta_2025"] * techo_pct
    )

    # Reescalar para que la suma final sea exactamente total_2026
    suma_ajustada = agg["presupuesto_ajustado"].sum()
    factor_rescale = total_2026 / suma_ajustada if suma_ajustada > 0 else 0
    agg["presupuesto_2026"] = agg["presupuesto_ajustado"] * factor_rescale

    agg["grupo"] = agg["nomvendedor"].apply(lambda v: construir_grupo(v, grupos))
    return agg

def tabla_grupos(df_asignado: pd.DataFrame) -> pd.DataFrame:
    return df_asignado.groupby("grupo").agg(
        presupuesto_grupo=("presupuesto_2026", "sum"),
        venta_2025=("venta_2025", "sum"),
        venta_2024=("venta_2024", "sum"),
        clientes=("clientes", "sum")
    ).reset_index().sort_values("presupuesto_grupo", ascending=False)

def comentarios_presupuesto(df_asignado: pd.DataFrame) -> pd.DataFrame:
    comentarios = []
    for _, r in df_asignado.iterrows():
        delta_vs_2025 = (r["presupuesto_2026"] - r["venta_2025"])
        delta_pct = (delta_vs_2025 / r["venta_2025"] * 100) if r["venta_2025"] > 0 else 0
        trend = "crecimiento" if r["crec_pct"] > 0 else "decrecimiento"
        just = (
            f"Part. 2025: {r['participacion_2025']*100:.1f}%. "
            f"Tendencia 24-25: {trend} {r['crec_pct']*100:.1f}%. "
            f"Diversidad (líneas/clientes): {r['diversidad']*100:.1f}%. "
            f"Presupuesto 2026: ${r['presupuesto_2026']:,.0f} ({delta_pct:+.1f}% vs 2025)."
        )
        comentarios.append({"nomvendedor": r["nomvendedor"], "grupo": r["grupo"], "comentario": just})
    return pd.DataFrame(comentarios)

def exportar_excel_mensual_unificado(tabla_mensual: pd.DataFrame) -> bytes:
    """Genera Excel profesional para la tabla mensual unificada."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        tabla_mensual.to_excel(writer, index=False, sheet_name="Plan_Mensual_2026")
        wb = writer.book
        ws = writer.sheets["Plan_Mensual_2026"]

        header_fmt = wb.add_format({
            "bold": True, "font_color": "white", "align": "center", "valign": "vcenter",
            "fg_color": "#1e3a8a", "border": 1
        })
        money_fmt = wb.add_format({"num_format": "$#,##0", "border": 1})
        total_fmt = wb.add_format({"num_format": "$#,##0", "border": 1, "bold": True, "fg_color": "#fef3c7"})
        index_fmt = wb.add_format({"border": 1, "bold": True, "bg_color": "#eef2ff"})

        # Detectar columna índice (primera columna del DF)
        idx_col = tabla_mensual.columns[0]

        for col, name in enumerate(tabla_mensual.columns):
            ws.write(0, col, name, header_fmt)
        for row_idx in range(1, len(tabla_mensual) + 1):
            ws.set_row(row_idx, None, money_fmt)

        # Primera columna (vendedor/grupo) con formato de índice
        ws.set_column(0, 0, 30, index_fmt)
        # Resto de columnas numéricas
        ws.set_column(1, len(tabla_mensual.columns) - 2, 14, money_fmt)
        ws.set_column(len(tabla_mensual.columns) - 1, len(tabla_mensual.columns) - 1, 16, total_fmt)

        # Fila total con formato destacado si existe
        if idx_col in tabla_mensual.columns and (tabla_mensual[idx_col] == "TOTAL_MES").any():
            r = tabla_mensual.index[tabla_mensual[idx_col] == "TOTAL_MES"][0] + 1
            ws.set_row(r, None, total_fmt)

        ws.freeze_panes(1, 1)
        ws.autofilter(0, 0, len(tabla_mensual), len(tabla_mensual.columns) - 1)
        ws.merge_range("A1:A1", "Plan Mensual 2026 Ferreinox", header_fmt)

    return output.getvalue()

# ----------------- UI -----------------
validar_sesion()
df_raw = preparar_df(st.session_state.df_ventas)
DATA_CONFIG = st.session_state.DATA_CONFIG
grupos_cfg = DATA_CONFIG.get("grupos_vendedores", {})

render_header()

# ----------------- Filtros -----------------
col_a, col_b, col_c = st.columns([1.2, 1, 1])
escenario = col_a.selectbox("Escenario de Proyección", ["Conservador", "Realista", "Optimista"], index=1)
anio_base = col_b.selectbox("Año Base", sorted(df_raw["anio"].dropna().unique(), reverse=True), index=0)
kpi_lineas = col_c.multiselect("Líneas estratégicas foco (opcional)", _lista_lineas(df_raw), default=[])

df_master = df_raw[df_raw["anio"] >= 2023].copy()
if kpi_lineas:
    df_master = df_master[df_master["linea_producto"].isin(kpi_lineas)]

total_2024 = df_master[df_master["anio"] == 2024]["valor_venta"].sum()
total_2025 = df_master[df_master["anio"] == 2025]["valor_venta"].sum()
total_2026, tasa_apl = proyectar_total_2026(total_2024, total_2025, escenario)

# --- KPIs ejecutivos ---
st.markdown("### 📌 Resumen Ejecutivo 2026")
kpi_cols = st.container()
with kpi_cols:
    st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
    kpi_card("Venta 2024", f"${total_2024:,.0f}")
    kpi_card("Venta 2025", f"${total_2025:,.0f}")
    kpi_card("Proyección 2026", f"${total_2026:,.0f}", f"{tasa_apl*100:+.1f}%")
    kpi_card("Vendedores activos", f"{df_master['nomvendedor'].nunique():,}")
    st.markdown('</div>', unsafe_allow_html=True)

df_asignado = asignar_presupuesto(df_master, grupos_cfg, total_2026)
df_grupos = tabla_grupos(df_asignado)
df_mensual = distribuir_presupuesto_mensual(df_asignado, df_master)
df_coment = comentarios_presupuesto(df_asignado)

# --- NUEVO: consolidar mostradores en la vista mensual ---
df_mensual['vendedor_unificado'] = np.where(
    df_mensual['grupo'].notna() & (df_mensual['grupo'] != ''),
    df_mensual['grupo'],
    df_mensual['nomvendedor']
)
df_mensual_unificado = (
    df_mensual
    .groupby(['vendedor_unificado', 'mes'], as_index=False)['presupuesto_mensual']
    .sum()
)

st.markdown("---")
st.subheader("🧭 Asignación Anual por Vendedor")
st.dataframe(
    df_asignado.sort_values("presupuesto_2026", ascending=False),
    use_container_width=True, hide_index=True,
    column_config={
        "nomvendedor": "Vendedor",
        "grupo": "Grupo/MOSTRADOR",
        "venta_2024": st.column_config.NumberColumn("Venta 2024", format="$%d"),
        "venta_2025": st.column_config.NumberColumn("Venta 2025", format="$%d"),
        "participacion_2025": st.column_config.ProgressColumn("Part. 2025", format="%.1f%%", min_value=0, max_value=1),
        "crec_pct": st.column_config.NumberColumn("Crec. %", format="%.1f%%"),
        "diversidad": st.column_config.ProgressColumn("Diversidad", format="%.1f%%", min_value=0, max_value=1),
        "score": st.column_config.NumberColumn("Score", format="%.3f"),
        "presupuesto_2026": st.column_config.NumberColumn("Presupuesto 2026", format="$%d"),
        "clientes": st.column_config.NumberColumn("Clientes", format="%d"),
        "lineas": st.column_config.NumberColumn("Líneas", format="%d"),
        "marcas": st.column_config.NumberColumn("Marcas", format="%d"),
    }
)

st.markdown("### 🏢 Consolidado por Grupo MOSTRADOR")
st.dataframe(
    df_grupos,
    use_container_width=True, hide_index=True,
    column_config={
        "grupo": "Grupo",
        "presupuesto_grupo": st.column_config.NumberColumn("Presupuesto 2026", format="$%d"),
        "venta_2025": st.column_config.NumberColumn("Venta 2025", format="$%d"),
        "venta_2024": st.column_config.NumberColumn("Venta 2024", format="$%d"),
        "clientes": st.column_config.NumberColumn("Clientes", format="%d"),
    }
)

# --- Plan mensual unificado (solo mostradores y vendedores individuales) ---
st.markdown("### 🗓️ Plan Mensual unificado (agrupa mostradores)")
with st.expander("Ver detalle mensual consolidado", expanded=False):
    tabla_mensual = df_mensual_unificado.pivot_table(
        index="vendedor_unificado",
        columns="mes",
        values="presupuesto_mensual",
        aggfunc="sum"
    ).fillna(0)
    tabla_mensual["Total_2026"] = tabla_mensual.sum(axis=1)

    # Fila total por mes (Total 1=Ene, ..., Total 12=Dic, Total_2026)
    fila_total = tabla_mensual.sum(axis=0)
    fila_total.name = "TOTAL_MES"
    tabla_mensual = pd.concat([tabla_mensual, fila_total.to_frame().T])

    # Redondear y usar solo enteros
    tabla_mensual = tabla_mensual.round(0).astype(int)

    # Renombrar columnas de mes a nombre
    mapeo_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                   7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    tabla_mensual.rename(columns={k: v for k, v in mapeo_meses.items()}, inplace=True)

    # Preparar configuración de columnas
    tabla_mensual_reset = tabla_mensual.reset_index().rename(columns={"vendedor_unificado": "Vendedor/Grupo"})
    col_config = {
        "Vendedor/Grupo": "Vendedor/Grupo",
        "Total_2026": st.column_config.NumberColumn("Total 2026", format="$ %d"),
    }
    for num, nombre in mapeo_meses.items():
        if nombre in tabla_mensual_reset.columns:
            col_config[nombre] = st.column_config.NumberColumn(f"Total {nombre}", format="$ %d")

    st.dataframe(
        tabla_mensual_reset,
        use_container_width=True,
        hide_index=True,
        column_config=col_config
    )

# --- Visualizaciones ejecutivas mejoradas ---
st.markdown("### 📊 Visualizaciones Ejecutivas")
c1, c2 = st.columns([1.4, 1])
with c1:
    fig = px.bar(
        df_asignado.sort_values("presupuesto_2026", ascending=False).head(20),
        x="nomvendedor", y="presupuesto_2026", color="grupo",
        title="Top 20 Vendedores por Presupuesto 2026",
        labels={"presupuesto_2026": "Presupuesto", "nomvendedor": "Vendedor"},
        height=520, text_auto=".2s"
    )
    fig.update_layout(xaxis_tickangle=-35, template="plotly_white", margin=dict(t=60, b=60, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)
with c2:
    fig_g = px.pie(
        df_grupos, values="presupuesto_grupo", names="grupo",
        title="Participación de Grupos en Presupuesto 2026", hole=0.45
    )
    fig_g.update_layout(height=520, template="plotly_white", margin=dict(t=60, b=20, l=10, r=10))
    st.plotly_chart(fig_g, use_container_width=True)

st.markdown("### 🗺️ Distribución Mensual (Heatmap Unificado)")
fig_heat = px.imshow(
    df_mensual_unificado.pivot_table(index="vendedor_unificado", columns="mes", values="presupuesto_mensual", aggfunc="sum").fillna(0),
    labels={"x": "Mes", "y": "Vendedor/Grupo", "color": "Presupuesto"},
    aspect="auto", color_continuous_scale="Blues", text_auto=True
)
fig_heat.update_layout(height=520, template="plotly_white", margin=dict(l=40, r=20, t=60, b=40))
st.plotly_chart(fig_heat, use_container_width=True)

# --- Comentarios ejecutivos con badge ---
st.markdown("### 🧠 Comentarios Ejecutivos")
st.dataframe(df_coment, use_container_width=True, hide_index=True)

st.markdown("### 🧾 Descargar Asignaciones")
csv_bytes = df_asignado.to_csv(index=False).encode("utf-8")
st.download_button("📥 CSV Vendedores", data=csv_bytes, file_name="presupuesto_2026_vendedores.csv", mime="text/csv", use_container_width=True)

csv_bytes_g = df_grupos.to_csv(index=False).encode("utf-8")
st.download_button("📥 CSV Grupos", data=csv_bytes_g, file_name="presupuesto_2026_grupos.csv", mime="text/csv", use_container_width=True)

csv_bytes_m = df_mensual.to_csv(index=False).encode("utf-8")
st.download_button("📥 CSV Plan Mensual", data=csv_bytes_m, file_name="presupuesto_2026_mensual.csv", mime="text/csv", use_container_width=True)

excel_bytes_unificado = exportar_excel_mensual_unificado(tabla_mensual_reset)
st.download_button("📥 Excel Plan Mensual Unificado", data=excel_bytes_unificado, file_name="presupuesto_2026_plan_mensual_unificado.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

st.markdown("---")
st.caption("Sistema de Inteligencia Comercial | Presupuesto 2026 con participación 2025, crecimiento, diversidad y estacionalidad mensual.")