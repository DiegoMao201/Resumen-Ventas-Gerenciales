import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List
import io
import datetime
from xlsxwriter.utility import xl_col_to_name  # añade esta importación

st.set_page_config(page_title="💰 Presupuesto 2026 | Ferreinox", page_icon="💰", layout="wide")

# --- ESTILOS EJECUTIVOS CSS ---
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

# ----------------- Funciones de UI -----------------
def render_header():
    st.markdown(f"""
    <div class="hero">
      <h2 style="margin:0;">💰 Presupuesto 2026 | Ferreinox</h2>
      <p style="margin:4px 0 0 0; color:rgba(255,255,255,0.85);">
        Sistema de Planeación Financiera y Comercial.
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

# ----------------- Utilidades de Datos -----------------
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

# ----------------- Lógica de Negocio (Cálculos) -----------------
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
    agg["crec_ajustado"] = np.clip(agg["crec_pct"], -0.15, 0.30) 
    agg["diversidad"] = 0.6 * norm_col("lineas") + 0.4 * norm_col("clientes")
    agg["score_raw"] = agg["venta_2025"] * (1 + agg["crec_ajustado"]) * (1 + 0.10 * agg["diversidad"])
    
    suma_scores = agg["score_raw"].sum()
    agg["presupuesto_prelim"] = np.where(suma_scores > 0, agg["score_raw"] / suma_scores * total_2026, 0)

    piso_pct = 0.70 
    techo_pct = 1.35 
    agg["presupuesto_ajustado"] = np.clip(
        agg["presupuesto_prelim"],
        agg["venta_2025"] * piso_pct,
        agg["venta_2025"] * techo_pct
    )

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
        # Comentario optimizado para lectura en Excel
        just = (
            f"Meta 26: ${r['presupuesto_2026']/1e6:.1f}M ({delta_pct:+.1f}% vs 25). "
            f"Basado en {trend} del {r['crec_pct']*100:.1f}% y diversidad."
        )
        comentarios.append({"nomvendedor": r["nomvendedor"], "grupo": r["grupo"], "comentario": just})
    return pd.DataFrame(comentarios)

# ----------------- GENERADOR DE EXCEL PREMIUM -----------------
def exportar_excel_ejecutivo(df_mensual_unificado: pd.DataFrame, df_coment: pd.DataFrame, meta_total: float, escenario: str) -> bytes:
    """
    Genera un Excel de Alto Nivel con Sparklines, Formato Condicional y Diseño Moderno.
    """
    output = io.BytesIO()
    
    # 1. Preparación de datos para Excel
    # Pivotar los meses
    df_pivot = df_mensual_unificado.pivot_table(
        index="vendedor_unificado", columns="mes", values="presupuesto_mensual", aggfunc="sum"
    ).fillna(0)
    
    # Ordenar por venta total descendente para impacto visual
    df_pivot["Total_2026"] = df_pivot.sum(axis=1)
    df_pivot = df_pivot.sort_values("Total_2026", ascending=False)
    
    # Mapeo de comentarios (Buscamos el comentario más relevante para el vendedor/grupo)
    # Si es grupo, intentamos concatenar o dejar genérico. Si es vendedor, pegamos su comentario.
    comment_map = {}
    # Crear diccionario rápido de comentarios individuales
    raw_comments = dict(zip(df_coment["nomvendedor"], df_coment["comentario"]))
    
    # Crear diccionario de comentarios de grupo (tomamos el del líder o genérico)
    for idx, row in df_pivot.iterrows():
        nombre = str(idx)
        if nombre in raw_comments:
            comment_map[nombre] = raw_comments[nombre]
        else:
            # Es un grupo o no tiene comentario directo.
            # Buscamos si el nombre coincide con un grupo en df_coment
            sub_c = df_coment[df_coment["grupo"] == nombre]
            if not sub_c.empty:
                 comment_map[nombre] = f"Agrupación de {len(sub_c)} vendedores. Obj. Grupal: ${row['Total_2026']/1e6:.1f}M"
            else:
                 comment_map[nombre] = "Asignación directa."

    # 2. Configuración de Writer y Workbook
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        sheet_name = "Plan_Maestro_2026"
        # Escribimos un dataframe vacío solo para inicializar, escribiremos manualmente
        pd.DataFrame().to_excel(writer, sheet_name=sheet_name)
        
        wb = writer.book
        ws = writer.sheets[sheet_name]
        ws.hide_gridlines(2) # Ocultar líneas de cuadrícula para look limpio
        
        # --- DEFINICIÓN DE FORMATOS ---
        fmt_title = wb.add_format({
            'bold': True, 'font_size': 20, 'font_color': '#FFFFFF',
            'bg_color': '#1e3a8a', 'align': 'left', 'valign': 'vcenter', 'indent': 1
        })
        fmt_subtitle = wb.add_format({
            'font_size': 11, 'font_color': '#cbd5e1', # Gris claro azulado
            'bg_color': '#1e3a8a', 'align': 'left', 'valign': 'top', 'indent': 1, 'italic': True
        })
        fmt_kpi_box = wb.add_format({
            'border': 1, 'border_color': '#cbd5e1', 'bg_color': '#f8fafc',
            'align': 'center', 'valign': 'vcenter', 'font_size': 10
        })
        fmt_kpi_val = wb.add_format({
            'bold': True, 'font_size': 12, 'font_color': '#1e3a8a',
            'align': 'center', 'bg_color': '#f8fafc', 'num_format': '$#,##0'
        })
        
        # Formatos de Tabla
        header_color = '#2563eb' # Azul más brillante para cabecera tabla
        fmt_header = wb.add_format({
            'bold': True, 'font_color': 'white', 'bg_color': header_color,
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': 'white'
        })
        fmt_row_idx = wb.add_format({
            'bold': True, 'font_color': '#334155', 'bg_color': '#f1f5f9',
            'border': 1, 'border_color': '#e2e8f0', 'align': 'left'
        })
        fmt_curr = wb.add_format({'num_format': '$ #,##0', 'border': 1, 'border_color': '#f1f5f9', 'font_size': 10})
        fmt_curr_tot = wb.add_format({
            'num_format': '$ #,##0', 'bold': True, 'bg_color': '#fff7ed', # Naranja muy suave
            'border': 1, 'border_color': '#fdba74'
        })
        fmt_text_sm = wb.add_format({'font_size': 9, 'font_color': '#64748b', 'text_wrap': True, 'valign': 'vcenter'})

        # --- SECCIÓN 1: DASHBOARD HEADER (Filas 0-4) ---
        ws.set_row(0, 35) # Altura Título
        ws.set_row(1, 20) # Altura Subtítulo
        ws.set_row(2, 10) # Espaciador
        ws.set_row(3, 40) # Fila KPIs
        
        # Título Corporativo
        ws.merge_range('A1:Q1', "  FERREINOX SAS BIC | PRESUPUESTO COMERCIAL 2026", fmt_title)
        ws.merge_range('A2:Q2', f"  Escenario seleccionado: {escenario.upper()} | Generado: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", fmt_subtitle)
        
        # KPIs Mini Dashboard en Excel
        ws.write('B4', "META TOTAL AÑO", fmt_kpi_box)
        ws.write('C4', meta_total, fmt_kpi_val)
        ws.write('E4', "PROMEDIO MENSUAL", fmt_kpi_box)
        ws.write('F4', meta_total/12, fmt_kpi_val)
        
        # --- SECCIÓN 2: CABECERAS DE TABLA (Fila 6) ---
        start_row = 6
        cols = ["Vendedor / Grupo", "Tendencia", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic", "TOTAL 2026", "Observaciones Estratégicas"]
        
        for c_idx, col_name in enumerate(cols):
            ws.write(start_row, c_idx, col_name, fmt_header)
            
        # --- SECCIÓN 3: DATOS Y SPARKLINES ---
        curr_row = start_row + 1
        
        # Columnas mapeadas: A=0, B=1(Spark), C=2(Ene)... N=13(Dic), O=14(Total), P=15(Comentario)
        
        for idx_val, row in df_pivot.iterrows():
            # 1. Nombre
            ws.write(curr_row, 0, idx_val, fmt_row_idx)
            
            # 2. Datos Mensuales (Cols 2 a 13) - Escribimos los valores
            months_data = []
            for m in range(1, 13):
                val = row.get(m, 0)
                months_data.append(val)
                ws.write(curr_row, m + 1, val, fmt_curr) # +1 porque hay columna sparkline antes
                
            # 3. Total (Col 14)
            ws.write(curr_row, 14, row["Total_2026"], fmt_curr_tot)
            
            # 4. Comentario (Col 15)
            ws.write(curr_row, 15, comment_map.get(str(idx_val), ""), fmt_text_sm)
            
            # 5. SPARKLINES (Mini gráfico en Col 1 - 'B')
            # Definir el rango de datos de esta fila para el sparkline (C a N)
            # Fila excel es curr_row + 1 (base 1)
            row_excel = curr_row + 1
            data_range = f"C{row_excel}:N{row_excel}" # Rango de Ene a Dic
            
            ws.add_sparkline(curr_row, 1, {
                'range': data_range,
                'type': 'line',
                'style': 12, # Estilo azul
                'markers': True,
                'last_point': True,
                'high_point': True, # Puntos destacados
                'line_weight': 2
            })
            
            curr_row += 1

        # Fila de Totales Generales al final
        ws.write(curr_row, 0, "TOTAL COMPAÑÍA", fmt_header)
        # Sumar Ene-Dic (cols 2..13) y Total (col 14)
        for m_idx in range(1, 13):
            col_letter = xl_col_to_name(m_idx + 1)  # col 2 -> C
            ws.write_formula(
                curr_row, m_idx + 1,
                f"=SUM({col_letter}{start_row+2}:{col_letter}{curr_row})",
                fmt_curr_tot
            )
        total_col_letter = xl_col_to_name(14)
        ws.write_formula(
            curr_row, 14,
            f"=SUM({total_col_letter}{start_row+2}:{total_col_letter}{curr_row})",
            fmt_curr_tot
        )

        # --- SECCIÓN 4: FORMATO CONDICIONAL Y VISUALES ---
        last_data_row = curr_row - 1
        rng_months = f"C{start_row+2}:N{last_data_row+1}"
        rng_totals = f"O{start_row+2}:O{last_data_row+1}"
        
        # 1. Mapa de Calor (Azul suave) para los meses - Identifica estacionalidad
        ws.conditional_format(rng_months, {
            'type': '3_color_scale',
            'min_color': '#ffffff', # Blanco
            'mid_color': '#bfdbfe', # Azul muy claro
            'max_color': '#3b82f6'  # Azul corporativo
        })
        
        # 2. Barras de Datos para el Total - Comparativa visual de tamaño
        ws.conditional_format(rng_totals, {
            'type': 'data_bar',
            'bar_color': '#f59e0b', # Dorado/Ambar Ferreinox
            'bar_solid': True,
        })
        
        # --- SECCIÓN 5: AJUSTES FINALES DE LAYOUT ---
        ws.set_column(0, 0, 35) # Ancho Vendedor
        ws.set_column(1, 1, 12) # Ancho Sparkline
        ws.set_column(2, 13, 14) # Ancho Meses
        ws.set_column(14, 14, 18) # Ancho Total
        ws.set_column(15, 15, 50) # Ancho Comentarios
        
        ws.freeze_panes(start_row + 1, 2) # Congelar encabezados y columnas nombre+sparkline
        ws.autofilter(start_row, 0, last_data_row, 15) # Filtros automáticos
        
        # Insertar Logo (Texto estilizado si no hay imagen) en A1 ya hecho.
        
    return output.getvalue()

# ----------------- EJECUCIÓN PRINCIPAL -----------------
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

# --- Procesamiento de Presupuestos ---
df_asignado = asignar_presupuesto(df_master, grupos_cfg, total_2026)
df_grupos = tabla_grupos(df_asignado)
df_mensual = distribuir_presupuesto_mensual(df_asignado, df_master)
df_coment = comentarios_presupuesto(df_asignado)

# Consolidar mostradores para la vista mensual unificada
df_mensual['vendedor_unificado'] = np.where(
    df_mensual['grupo'].notna() & (df_mensual['grupo'] != '') & (df_mensual['grupo'] != df_mensual['nomvendedor']),
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

# --- Vista Previa Mensual ---
st.markdown("### 🗓️ Plan Mensual unificado (Vista Previa)")
with st.expander("Ver detalle mensual consolidado", expanded=False):
    tabla_mensual_preview = df_mensual_unificado.pivot_table(
        index="vendedor_unificado", columns="mes", values="presupuesto_mensual", aggfunc="sum"
    ).fillna(0)
    tabla_mensual_preview["Total_2026"] = tabla_mensual_preview.sum(axis=1)
    tabla_mensual_preview = tabla_mensual_preview.sort_values("Total_2026", ascending=False)
    
    st.dataframe(
        tabla_mensual_preview.style.format("${:,.0f}").background_gradient(cmap="Blues", subset=list(range(1,13))),
        use_container_width=True
    )

# --- Visualizaciones ---
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

st.markdown("### 🗺️ Mapa de Calor Mensual")
fig_heat = px.imshow(
    df_mensual_unificado.pivot_table(index="vendedor_unificado", columns="mes", values="presupuesto_mensual", aggfunc="sum").fillna(0),
    labels={"x": "Mes", "y": "Vendedor/Grupo", "color": "Presupuesto"},
    aspect="auto", color_continuous_scale="Blues"
)
fig_heat.update_layout(height=520, template="plotly_white", margin=dict(l=40, r=20, t=60, b=40))
st.plotly_chart(fig_heat, use_container_width=True)

# --- Comentarios ejecutivos ---
st.markdown("### 🧠 Justificación Estratégica")
st.dataframe(df_coment, use_container_width=True, hide_index=True)

# --- ZONA DE DESCARGAS ---
st.markdown("### 🧾 Descarga de Informes Oficiales")
col_d1, col_d2 = st.columns(2)

with col_d1:
    csv_bytes = df_asignado.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 CSV Data Bruta (Para Sistemas)", 
        data=csv_bytes, 
        file_name="base_datos_presupuesto_2026.csv", 
        mime="text/csv", 
        use_container_width=True
    )

with col_d2:
    # Generar el Excel Premium
    excel_bytes_premium = exportar_excel_ejecutivo(
        df_mensual_unificado, 
        df_coment, 
        total_2026,
        escenario
    )
    st.download_button(
        "💎 Descargar PRESUPUESTO EJECUTIVO 2026 (Excel Premium)", 
        data=excel_bytes_premium, 
        file_name="Presupuesto_Ferreinox_2026_Ejecutivo.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        use_container_width=True,
        type="primary"
    )

st.markdown("---")
st.caption("Sistema de Inteligencia Comercial | Ferreinox SAS BIC | 2026")