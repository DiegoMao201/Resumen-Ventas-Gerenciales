import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
from openai import OpenAI
import io

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
st.markdown('<div class="crono-sub">Obras, Instituciones e Industria | IA para priorización, búsqueda web y acompañamiento ejecutivo</div>', unsafe_allow_html=True)

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

if "Poblacion_Real" in df_ventas.columns:
    mask_ciudad = df_ventas["Poblacion_Real"].str.contains(ciudad, case=False, na=False)
else:
    mask_ciudad = df_ventas["nombre_cliente"].str.contains(ciudad, case=False, na=False)
mask_sector = df_ventas["categoria_producto"].str.contains("|".join(sectores), case=False, na=False)
df_armenia = df_ventas[mask_ciudad & mask_sector].copy()

if df_armenia.empty:
    st.warning("No se encontraron oportunidades en Armenia para los sectores seleccionados.")
    st.stop()


# --- 2️⃣ Filtrar clientes de JAIME ANDRES LONDOÑO ---
st.markdown("#### 2️⃣ Clientes y Oportunidades de JAIME ANDRES LONDOÑO")
if "vendedor" in df_armenia.columns:
    mask_jaime = df_armenia["vendedor"].str.contains("JAIME ANDRES LONDO", case=False, na=False)
    df_jaime = df_armenia[mask_jaime].copy()
else:
    df_jaime = df_armenia.copy()

if df_jaime.empty:
    st.warning("No se encontraron clientes asignados a JAIME ANDRES LONDOÑO en Armenia.")
else:
    st.dataframe(df_jaime[[c for c in df_jaime.columns if c.lower() in ["nombre_cliente","obra","categoria_producto","valor_venta"]]], use_container_width=True)

# --- 3️⃣ Análisis IA de oportunidades y obras de JAIME ANDRES LONDOÑO ---
st.markdown("#### 3️⃣ Análisis IA de Oportunidades y Obras (Base Interna)")
client = OpenAI()
top_clientes_jaime = (
    df_jaime.groupby("nombre_cliente")["valor_venta"]
    .sum().sort_values(ascending=False).head(10)
)
prompt_jaime = f"""
Eres un asesor comercial experto en ventas industriales. Analiza la siguiente lista de clientes/obras de JAIME ANDRES LONDOÑO en Armenia Quindío y prioriza las 5 mejores oportunidades para incrementar ventas en obras, instituciones e industria en 2026. Justifica brevemente cada elección.
{top_clientes_jaime.to_string()}
"""
try:
    response_jaime = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt_jaime}],
        temperature=0.4
    )
    analisis_ia_jaime = response_jaime.choices[0].message.content
except Exception as e:
    analisis_ia_jaime = f"Error IA: {e}"
st.info(analisis_ia_jaime)

# --- 4️⃣ Búsqueda IA de nuevos clientes/obras/instituciones en internet ---
st.markdown("#### 4️⃣ Sugerencias IA de Nuevos Clientes/Obras/Instituciones (Web)")
prompt_web = f"""
Actúa como un consultor de inteligencia de negocios. Busca en internet (simulado) las principales obras de construcción, industrias grandes, instituciones educativas y de salud, y empresas relevantes en Armenia, Quindío, Colombia, que puedan ser potenciales clientes para ventas industriales en 2026. Devuelve una lista priorizada de al menos 8 oportunidades con nombre, sector y breve justificación de por qué son relevantes.
"""
try:
    response_web = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt_web}],
        temperature=0.5
    )
    sugerencias_web = response_web.choices[0].message.content
except Exception as e:
    sugerencias_web = f"Error IA: {e}"
st.info(sugerencias_web)


# --- 5️⃣ Visualización ejecutiva de oportunidades (clientes de Jaime) ---
st.markdown("#### 5️⃣ Visualización de Oportunidades (Clientes de Jaime)")
if not top_clientes_jaime.empty:
    fig = px.bar(
        top_clientes_jaime,
        orientation="h",
        labels={"value": "Ventas Históricas", "nombre_cliente": "Cliente/Obra"},
        title="Top Oportunidades Armenia (Clientes Jaime, Histórico Ventas)",
        color=top_clientes_jaime.values,
        color_continuous_scale="Blues"
    )
    fig.update_layout(height=400, yaxis_title="", xaxis_title="Ventas ($)", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


# --- 6️⃣ Cronograma de visitas (primer semestre 2026, integrando IA y web) ---
st.markdown("#### 6️⃣ Cronograma de Visitas (Enero-Junio 2026, Integrado IA + Web)")
clientes_priorizados = list(top_clientes_jaime.index[:5])
# Extraer sugerencias IA web (simulado, parseo simple)
import re
web_clientes = []
if sugerencias_web and "1." in sugerencias_web:
    for line in sugerencias_web.split("\n"):
        m = re.match(r"\d+\.\s*([^\-\|]+)[\-\|](.*)", line)
        if m:
            nombre = m.group(1).strip()
            sector = m.group(2).strip()
            web_clientes.append(f"{nombre} ({sector})")
if not web_clientes:
    web_clientes = [l.strip() for l in sugerencias_web.split("\n") if l.strip()][:8]

clientes_cronograma = clientes_priorizados + web_clientes[:8-len(clientes_priorizados)]
fecha_inicio = datetime.date(2026, 1, 8)  # Primer lunes de enero 2026
cronograma = []
for semana in range(1, 27):  # 26 semanas (primer semestre)
    cliente = clientes_cronograma[(semana-1) % len(clientes_cronograma)]
    fecha_visita = fecha_inicio + datetime.timedelta(weeks=semana-1)
    cronograma.append({
        "Semana": semana,
        "Fecha": fecha_visita.strftime("%Y-%m-%d"),
        "Cliente/Obra": cliente,
        "Vendedor": "JAIME ANDRES LONDONO MONTENEGRO",
        "Acompañante": "DIEGO MAURICIO GARCIA" if semana % 1 == 0 else ""
    })
df_crono = pd.DataFrame(cronograma)

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


# --- 7️⃣ Mapa de clientes (si hay coordenadas) ---
if "latitud" in df_armenia.columns and "longitud" in df_armenia.columns:
    st.markdown("#### 7️⃣ Mapa de Clientes/Obras")
    st.map(df_armenia[["latitud", "longitud"]].drop_duplicates())


# --- 8️⃣ Exportación profesional a Excel ---
st.markdown("#### 8️⃣ Exportar Cronograma")
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
st.success("Cronograma profesional potenciado con IA, análisis de clientes de Jaime, búsqueda web de oportunidades y exportación lista para gestión comercial.")
