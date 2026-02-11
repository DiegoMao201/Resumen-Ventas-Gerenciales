import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
from openai import OpenAI

st.set_page_config(page_title="Cronograma Visitas Armenia 2026", page_icon="📅", layout="wide")

st.markdown("""
<style>
.crono-title {font-size:2.2rem;font-weight:800;color:#1e3a8a;margin-bottom:0.5rem;}
.crono-sub {font-size:1.2rem;color:#3b82f6;}
.crono-table td, .crono-table th {padding:8px 12px;}
.crono-table th {background:#1e3a8a;color:white;}
.crono-table tr:nth-child(even) {background:#f8fafc;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="crono-title">📅 Cronograma de Visitas Comerciales Armenia Quindío 2026</div>', unsafe_allow_html=True)
st.markdown('<div class="crono-sub">Obras, Instituciones e Industria | IA para priorización y acompañamiento ejecutivo</div>', unsafe_allow_html=True)

# --- Cargar datos principales de la app ---
df_ventas = st.session_state.get("df_ventas", pd.DataFrame())
if df_ventas.empty:
    st.error("No hay datos de ventas cargados. Ve a 🏠 Resumen Mensual primero.")
    st.stop()

# --- Filtros inteligentes ---
st.markdown("#### 1️⃣ Filtros Inteligentes")
col1, col2, col3 = st.columns(3)
ciudad = col1.selectbox("Ciudad", ["ARMENIA"], index=0)
sectores = col2.multiselect("Sectores", ["OBRA", "INSTITUCION", "INDUSTRIA"], default=["OBRA", "INSTITUCION", "INDUSTRIA"])
anio = col3.selectbox("Año", [2026], index=0)

mask_ciudad = df_ventas["nombre_cliente"].str.contains(ciudad, case=False, na=False) | df_ventas["ciudad"].str.contains(ciudad, case=False, na=False)
mask_sector = df_ventas["categoria_producto"].str.contains("|".join(sectores), case=False, na=False)
df_armenia = df_ventas[mask_ciudad & mask_sector].copy()

if df_armenia.empty:
    st.warning("No se encontraron oportunidades en Armenia para los sectores seleccionados.")
    st.stop()

# --- Análisis IA para priorización de oportunidades ---
st.markdown("#### 2️⃣ Oportunidades Priorizadas por IA")
client = OpenAI()
top_clientes = (
    df_armenia.groupby("nombre_cliente")["valor_venta"]
    .sum().sort_values(ascending=False).head(15)
)
prompt = f"""
Eres un asesor comercial experto en ventas industriales. Analiza la siguiente lista de clientes/obras en Armenia Quindío y prioriza las 8 mejores oportunidades para incrementar ventas en obras, instituciones e industria en 2026. Justifica brevemente cada elección.
{top_clientes.to_string()}
"""

try:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.4
    )
    analisis_ia = response.choices[0].message.content
except Exception as e:
    analisis_ia = f"Error IA: {e}"

st.info(analisis_ia)

# --- Visualización ejecutiva de oportunidades ---
st.markdown("#### 3️⃣ Visualización de Oportunidades")
fig = px.bar(
    top_clientes,
    orientation="h",
    labels={"value": "Ventas Históricas", "nombre_cliente": "Cliente/Obra"},
    title="Top Oportunidades Armenia (Histórico Ventas)",
    color=top_clientes.values,
    color_continuous_scale="Blues"
)
fig.update_layout(height=400, yaxis_title="", xaxis_title="Ventas ($)", showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# --- Cronograma de visitas (primer semestre 2026) ---
st.markdown("#### 4️⃣ Cronograma de Visitas (Enero-Junio 2026)")
clientes_priorizados = list(top_clientes.index[:8])
fecha_inicio = datetime.date(2026, 1, 8)  # Primer lunes de enero 2026
cronograma = []
for i, cliente in enumerate(clientes_priorizados):
    for semana in range(1, 27):  # 26 semanas (primer semestre)
        fecha_visita = fecha_inicio + datetime.timedelta(weeks=semana-1)
        cronograma.append({
            "Semana": semana,
            "Fecha": fecha_visita.strftime("%Y-%m-%d"),
            "Cliente/Obra": cliente,
            "Vendedor": "JAIME ANDRES LONDONO MONTENEGRO",
            "Acompañante": "DIEGO MAURICIO GARCIA" if semana % 7 == 1 else ""
        })
df_crono = pd.DataFrame(cronograma)
# Solo una visita semanal por vendedor, rotando clientes
df_crono = df_crono.groupby("Semana").first().reset_index()

st.dataframe(
    df_crono,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Semana": st.column_config.NumberColumn("Semana", format="%d"),
        "Fecha": "Fecha",
        "Cliente/Obra": "Cliente/Obra",
        "Vendedor": "Vendedor",
        "Acompañante": "Acompañante"
    }
)

# --- Mapa de clientes (si hay coordenadas) ---
if "latitud" in df_armenia.columns and "longitud" in df_armenia.columns:
    st.markdown("#### 5️⃣ Mapa de Clientes/Obras")
    st.map(df_armenia[["latitud", "longitud"]].drop_duplicates())

# --- Exportación profesional a Excel ---
st.markdown("#### 6️⃣ Exportar Cronograma")
def exportar_cronograma_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Cronograma')
        wb = writer.book
        ws = writer.sheets['Cronograma']
        fmt_header = wb.add_format({'bold': True, 'bg_color': '#1e3a8a', 'font_color': 'white', 'border': 1})
        for col_num, value in enumerate(df.columns): ws.write(0, col_num, value, fmt_header)
        ws.set_column('A:A', 8)
        ws.set_column('B:B', 14)
        ws.set_column('C:C', 40)
        ws.set_column('D:D', 30)
        ws.set_column('E:E', 30)
    return output.getvalue()

st.download_button(
    label="📥 Descargar Cronograma (Excel)",
    data=exportar_cronograma_excel(df_crono),
    file_name="Cronograma_Visitas_Armenia_2026.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)

st.markdown("---")
st.success("Cronograma profesional generado con IA y datos históricos. ¡Listo para ejecutar y acompañar ventas estratégicas en Armenia Quindío!")
