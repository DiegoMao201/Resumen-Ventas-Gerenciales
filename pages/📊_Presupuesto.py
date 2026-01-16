import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List

st.set_page_config(page_title="💰 Presupuesto 2026 | Ferreinox", page_icon="💰", layout="wide")

# ---------- Utilidades ----------
def normalizar_texto(texto: str) -> str:
    import unicodedata, re
    if pd.isna(texto): return ""
    texto = str(texto).upper()
    texto = ''.join((c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn'))
    texto = re.sub(r'[^A-Z0-9\s\-]', '', texto)
    return texto.strip()

def validar_sesion():
    if 'df_ventas' not in st.session_state or st.session_state.df_ventas is None or st.session_state.df_ventas.empty:
        st.error("⚠️ No se encontraron datos de ventas en sesión.")
        st.page_link("🏠 Resumen_Mensual.py", label="Ir a la página principal", icon="🏠")
        st.stop()
    if 'DATA_CONFIG' not in st.session_state:
        st.error("⚠️ No se encontró DATA_CONFIG en sesión.")
        st.page_link("🏠 Resumen_Mensual.py", label="Ir a la página principal", icon="🏠")
        st.stop()

def preparar_df(df: pd.DataFrame) -> pd.DataFrame:
    dfc = df.copy()
    dfc['anio'] = pd.to_numeric(dfc['anio'], errors='coerce')
    dfc['mes'] = pd.to_numeric(dfc['mes'], errors='coerce')
    if 'valor_venta' in dfc.columns:
        dfc['valor_venta'] = pd.to_numeric(dfc['valor_venta'], errors='coerce').fillna(0)
    if 'nomvendedor' in dfc.columns:
        dfc['nomvendedor'] = dfc['nomvendedor'].fillna('SIN VENDEDOR')
    if 'linea_producto' in dfc.columns:
        dfc['linea_producto'] = dfc['linea_producto'].fillna('Sin Línea').astype(str)
    return dfc

def _lista_lineas(df: pd.DataFrame) -> List[str]:
    return sorted({str(v).strip() for v in df['linea_producto'].dropna() if str(v).strip()})

def calcular_pesos_mensuales(df_hist: pd.DataFrame, vendedor: str, col_valor: str = "valor_venta") -> np.ndarray:
    """Devuelve vector de 12 pesos por vendedor; fallback a pesos globales si no hay datos."""
    df_vend = df_hist[df_hist['nomvendedor'] == vendedor]
    df_base = df_vend if not df_vend.empty else df_hist
    pesos = df_base.groupby('mes')[col_valor].sum()
    pesos = pesos.reindex(range(1, 13), fill_value=0)
    total = pesos.sum()
    if total > 0:
        return (pesos / total).values
    # fallback uniforme
    return np.array([1/12.0] * 12)

def distribuir_presupuesto_mensual(df_asignado: pd.DataFrame, df_hist: pd.DataFrame) -> pd.DataFrame:
    """Expande presupuesto_2026 a 12 meses por vendedor usando estacionalidad histórica (prioriza 2025)."""
    df_hist_2025 = df_hist[df_hist['anio'] == 2025]
    df_hist_base = df_hist_2025 if not df_hist_2025.empty else df_hist[df_hist['anio'] == df_hist['anio'].max()]
    registros = []
    for _, row in df_asignado.iterrows():
        pesos = calcular_pesos_mensuales(df_hist_base, row['nomvendedor'])
        for mes_idx, peso in enumerate(pesos, start=1):
            registros.append({
                "nomvendedor": row["nomvendedor"],
                "grupo": row["grupo"],
                "mes": mes_idx,
                "presupuesto_mensual": row["presupuesto_2026"] * peso
            })
    return pd.DataFrame(registros)

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

def asignar_presupuesto(df: pd.DataFrame, grupos: Dict[str, List[str]], total_2026: float) -> pd.DataFrame:
    # Métricas base por vendedor
    base = df[df['anio'].isin([2024, 2025])]
    agg = base.groupby('nomvendedor').agg(
        venta_2024=('valor_venta', lambda s: s[df.loc[s.index, 'anio'] == 2024].sum()),
        venta_2025=('valor_venta', lambda s: s[df.loc[s.index, 'anio'] == 2025].sum()),
        clientes=('cliente_id', 'nunique'),
        lineas=('linea_producto', 'nunique'),
        marcas=('marca_producto', 'nunique')
    ).reset_index()
    agg['crecimiento_pct'] = np.where(agg['venta_2024'] > 0, (agg['venta_2025'] - agg['venta_2024']) / agg['venta_2024'], 0)
    total_2025 = agg['venta_2025'].sum()
    agg['participacion'] = np.where(total_2025 > 0, agg['venta_2025'] / total_2025, 0)

    # Normalizaciones
    def norm_col(col):
        mx = agg[col].max()
        mn = agg[col].min()
        return np.where(mx > mn, (agg[col] - mn) / (mx - mn), 0.0)
    agg['crec_norm'] = norm_col('crecimiento_pct')
    agg['diversidad'] = 0.6 * norm_col('lineas') + 0.4 * norm_col('clientes')

    # Score y asignación
    # $score = 0.6 s + 0.25 g + 0.15 d$
    agg['score'] = 0.6 * agg['participacion'] + 0.25 * agg['crec_norm'] + 0.15 * agg['diversidad']
    suma_scores = agg['score'].sum()
    agg['presupuesto_2026'] = np.where(suma_scores > 0, agg['score'] / suma_scores * total_2026, 0)

    # Grupo
    agg['grupo'] = agg['nomvendedor'].apply(lambda v: construir_grupo(v, grupos))
    return agg

def tabla_grupos(df_asignado: pd.DataFrame) -> pd.DataFrame:
    return df_asignado.groupby('grupo').agg(
        presupuesto_grupo=('presupuesto_2026', 'sum'),
        venta_2025=('venta_2025', 'sum'),
        venta_2024=('venta_2024', 'sum'),
        clientes=('clientes', 'sum')
    ).reset_index().sort_values('presupuesto_grupo', ascending=False)

# ---------- UI ----------
validar_sesion()
df_raw = preparar_df(st.session_state.df_ventas)
DATA_CONFIG = st.session_state.DATA_CONFIG
grupos_cfg = DATA_CONFIG.get('grupos_vendedores', {})

st.title("💰 Presupuesto 2026 | Ferreinox")
st.caption("Asignación ejecutiva anual y plan mensual por vendedor/grupo basada en histórico, crecimiento, portafolio y estacionalidad.")

col_a, col_b, col_c = st.columns([1.2, 1, 1])
escenario = col_a.selectbox("Escenario de Proyección", ["Conservador", "Realista", "Optimista"], index=1)
anio_base = col_b.selectbox("Año Base", sorted(df_raw['anio'].dropna().unique(), reverse=True), index=0)
kpi_lineas = col_c.multiselect("Líneas estratégicas foco (opcional)", _lista_lineas(df_raw), default=[])

# Filtro opcional de líneas
df_master = df_raw[df_raw['anio'] >= 2023].copy()
if kpi_lineas:
    df_master = df_master[df_master['linea_producto'].isin(kpi_lineas)]

total_2024 = df_master[df_master['anio'] == 2024]['valor_venta'].sum()
total_2025 = df_master[df_master['anio'] == 2025]['valor_venta'].sum()
total_2026, tasa_apl = proyectar_total_2026(total_2024, total_2025, escenario)

st.markdown("### 📌 Resumen Ejecutivo 2026")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Venta 2024", f"${total_2024:,.0f}")
k2.metric("Venta 2025", f"${total_2025:,.0f}")
k3.metric("Proyección 2026", f"${total_2026:,.0f}", f"{tasa_apl*100:+.1f}% vs hist.")
k4.metric("Vendedores activos", f"{df_master['nomvendedor'].nunique():,}")

df_asignado = asignar_presupuesto(df_master, grupos_cfg, total_2026)
df_grupos = tabla_grupos(df_asignado)
df_mensual = distribuir_presupuesto_mensual(df_asignado, df_master)

st.markdown("---")
st.subheader("🧭 Asignación por Vendedor (ponderada)")
st.dataframe(
    df_asignado.sort_values('presupuesto_2026', ascending=False),
    use_container_width=True,
    hide_index=True,
    column_config={
        "nomvendedor": "Vendedor",
        "grupo": "Grupo/MOSTRADOR",
        "venta_2024": st.column_config.NumberColumn("Venta 2024", format="$%d"),
        "venta_2025": st.column_config.NumberColumn("Venta 2025", format="$%d"),
        "crecimiento_pct": st.column_config.NumberColumn("Crec. %", format="%.1f%%"),
        "participacion": st.column_config.ProgressColumn("Part. 2025", format="%.1f%%", min_value=0, max_value=1),
        "score": st.column_config.NumberColumn("Score", format="%.3f"),
        "presupuesto_2026": st.column_config.NumberColumn("Presupuesto 2026", format="$%d"),
        "clientes": st.column_config.NumberColumn("Clientes Únicos", format="%d"),
        "lineas": st.column_config.NumberColumn("Líneas", format="%d"),
        "marcas": st.column_config.NumberColumn("Marcas", format="%d"),
    }
)

st.markdown("### 🗓️ Plan Mensual por Vendedor (2026)")
with st.expander("Ver detalle mensual por vendedor", expanded=False):
    st.dataframe(
        df_mensual.pivot_table(index=["nomvendedor", "grupo"], columns="mes", values="presupuesto_mensual", aggfunc="sum").fillna(0),
        use_container_width=True
    )

st.markdown("### 🗺️ Distribución Mensual (heatmap)")
fig_heat = px.imshow(
    df_mensual.pivot_table(index="nomvendedor", columns="mes", values="presupuesto_mensual", aggfunc="sum").fillna(0),
    labels={"x": "Mes", "y": "Vendedor", "color": "Presupuesto"},
    aspect="auto", color_continuous_scale="Blues"
)
fig_heat.update_layout(height=500, template="plotly_white")
st.plotly_chart(fig_heat, use_container_width=True)

st.markdown("### 🏢 Consolidado por Grupo MOSTRADOR")
st.dataframe(
    df_grupos,
    use_container_width=True,
    hide_index=True,
    column_config={
        "grupo": "Grupo",
        "presupuesto_grupo": st.column_config.NumberColumn("Presupuesto 2026", format="$%d"),
        "venta_2025": st.column_config.NumberColumn("Venta 2025", format="$%d"),
        "venta_2024": st.column_config.NumberColumn("Venta 2024", format="$%d"),
        "clientes": st.column_config.NumberColumn("Clientes", format="%d"),
    }
)

st.markdown("---")
st.subheader("📊 Visualizaciones Ejecutivas")
c1, c2 = st.columns([1.2, 1])
with c1:
    fig = px.bar(
        df_asignado.sort_values('presupuesto_2026', ascending=False).head(20),
        x='nomvendedor', y='presupuesto_2026', color='grupo',
        title="Top 20 Vendedores por Presupuesto 2026",
        labels={'presupuesto_2026': 'Presupuesto', 'nomvendedor': 'Vendedor'}
    )
    fig.update_layout(xaxis_tickangle=-45, height=500, template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)
with c2:
    fig_g = px.pie(
        df_grupos, values='presupuesto_grupo', names='grupo',
        title="Participación de Grupos en Presupuesto 2026", hole=0.45
    )
    fig_g.update_layout(height=500, template='plotly_white')
    st.plotly_chart(fig_g, use_container_width=True)

st.markdown("---")
st.subheader("🧾 Descargar Asignación")
csv_bytes = df_asignado.to_csv(index=False).encode('utf-8')
st.download_button("📥 Descargar CSV Vendedores", data=csv_bytes, file_name="presupuesto_2026_vendedores.csv", mime="text/csv", use_container_width=True)

csv_bytes_g = df_grupos.to_csv(index=False).encode('utf-8')
st.download_button("📥 Descargar CSV Grupos", data=csv_bytes_g, file_name="presupuesto_2026_grupos.csv", mime="text/csv", use_container_width=True)

csv_bytes_m = df_mensual.to_csv(index=False).encode('utf-8')
st.download_button("📥 Descargar CSV Plan Mensual", data=csv_bytes_m, file_name="presupuesto_2026_mensual.csv", mime="text/csv", use_container_width=True)

st.markdown("---")
st.caption("Sistema de Inteligencia Comercial | Presupuesto anual 2026 con distribución mensual por estacionalidad 2025 (o último año disponible).")