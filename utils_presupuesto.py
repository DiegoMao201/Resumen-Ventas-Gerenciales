import pandas as pd
import numpy as np

def normalizar_texto(texto: str) -> str:
    import unicodedata, re
    if pd.isna(texto): return ""
    texto = str(texto).upper()
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^A-Z0-9\s\-]", "", texto)
    return texto.strip()

def construir_grupo(vendedor: str, grupos: dict) -> str:
    vend_norm = normalizar_texto(vendedor)
    for grupo, lista in grupos.items():
        if vend_norm in [normalizar_texto(v) for v in lista]:
            return normalizar_texto(grupo)
    return vend_norm

def proyectar_total_2026(total_2024, total_2025):
    if total_2024 <= 0 or total_2025 <= 0:
        return total_2025, 0
    tasa_hist = (total_2025 - total_2024) / total_2024
    factor = 0.8  # Conservador
    tasa_aplicada = tasa_hist * factor
    return total_2025 * (1 + tasa_aplicada), tasa_aplicada

def asignar_presupuesto(df: pd.DataFrame, grupos: dict, total_2026: float) -> pd.DataFrame:
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