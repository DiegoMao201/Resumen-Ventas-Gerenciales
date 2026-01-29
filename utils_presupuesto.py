# ==============================================================================
# ARCHIVO: utils_presupuesto.py
# DESCRIPCIÓN: Lógica de negocio, cálculos estadísticos y reglas de excepción
# ==============================================================================
import pandas as pd
import numpy as np
import unicodedata
import re

def normalizar_texto(texto: str) -> str:
    """Normaliza cadenas de texto eliminando tildes y caracteres especiales."""
    if pd.isna(texto): return ""
    texto = str(texto).upper()
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^A-Z0-9\s\-]", "", texto)
    return texto.strip()

def construir_grupo(vendedor: str, grupos: dict) -> str:
    """Asigna el nombre del grupo si el vendedor pertenece a uno, sino devuelve el nombre del vendedor."""
    vend_norm = normalizar_texto(vendedor)
    for grupo, lista in grupos.items():
        if vend_norm in [normalizar_texto(v) for v in lista]:
            return normalizar_texto(grupo)
    return vend_norm

def proyectar_total_2026(total_2024, total_2025):
    """Calcula la proyección global para 2026 basada en el crecimiento histórico conservador."""
    if total_2024 <= 0 or total_2025 <= 0:
        return total_2025, 0
    tasa_hist = (total_2025 - total_2024) / total_2024
    factor = 0.8  # Factor conservador
    tasa_aplicada = tasa_hist * factor
    return total_2025 * (1 + tasa_aplicada), tasa_aplicada

def asignar_presupuesto(df: pd.DataFrame, grupos: dict, total_2026: float) -> pd.DataFrame:
    """
    Calcula el presupuesto anual por vendedor aplicando reglas estadísticas
    y excepciones puntuales de negocio (Reglas de Oro: Jerson, Julian, Pablo).
    """
    # Filtrar años base
    base = df[df["anio"].isin([2024, 2025])]
    
    # Agregación inicial por vendedor
    agg = base.groupby("nomvendedor").agg(
        venta_2024=("valor_venta", lambda s: s[df.loc[s.index, "anio"] == 2024].sum()),
        venta_2025=("valor_venta", lambda s: s[df.loc[s.index, "anio"] == 2025].sum()),
        clientes=("cliente_id", "nunique"),
        lineas=("linea_producto", "nunique"),
        marcas=("marca_producto", "nunique")
    ).reset_index()

    total_2025 = agg["venta_2025"].sum()
    
    # Cálculo de métricas para distribución automática
    agg["participacion_2025"] = np.where(total_2025 > 0, agg["venta_2025"] / total_2025, 0)

    def norm_col(col):
        mx = agg[col].max()
        mn = agg[col].min()
        return np.where(mx > mn, (agg[col] - mn) / (mx - mn), 0.0)

    agg["crec_pct"] = np.where(agg["venta_2024"] > 0, (agg["venta_2025"] - agg["venta_2024"]) / agg["venta_2024"], 0)
    agg["crec_ajustado"] = np.clip(agg["crec_pct"], -0.15, 0.30)
    agg["diversidad"] = 0.6 * norm_col("lineas") + 0.4 * norm_col("clientes")
    
    # Score compuesto
    agg["score_raw"] = agg["venta_2025"] * (1 + agg["crec_ajustado"]) * (1 + 0.10 * agg["diversidad"])

    # Distribución preliminar del total proyectado
    suma_scores = agg["score_raw"].sum()
    agg["presupuesto_prelim"] = np.where(suma_scores > 0, agg["score_raw"] / suma_scores * total_2026, 0)

    # Aplicación de pisos y techos automáticos
    piso_pct = 0.70
    techo_pct = 1.35
    agg["presupuesto_ajustado"] = np.clip(
        agg["presupuesto_prelim"],
        agg["venta_2025"] * piso_pct,
        agg["venta_2025"] * techo_pct
    )

    # Re-escalado para ajustar al total objetivo 2026
    suma_ajustada = agg["presupuesto_ajustado"].sum()
    factor_rescale = total_2026 / suma_ajustada if suma_ajustada > 0 else 0
    agg["presupuesto_2026"] = agg["presupuesto_ajustado"] * factor_rescale

    # Asignación de grupos
    agg["grupo"] = agg["nomvendedor"].apply(lambda v: construir_grupo(v, grupos))

    # ==============================================================================
    # APLICACIÓN DE REGLAS DE NEGOCIO (EXCEPCIONES ANUALES)
    # ==============================================================================
    def aplicar_reglas_anuales(row):
        nombre = normalizar_texto(row["nomvendedor"])
        presupuesto = row["presupuesto_2026"]

        # 1. LEDUYN MELGAREJO ARIAS: Presupuesto fijo mensual -> se multiplica por 12 para el anual
        if "LEDUYN MELGAREJO" in nombre:
            return 146_000_000 * 12

        # 2. JERSON ATEHORTUA OLARTE: PISO ESTRICTO DE 100 MILLONES
        if "JERSON ATEHORTUA" in nombre:
            if presupuesto < 100_000_000:
                return 100_000_000  # Forzar a 100 Millones exactos si dio menos
            return presupuesto

        # 3. PABLO CESAR MAFLA BANOL: Aumento del 7% sobre lo calculado
        if "PABLO CESAR MAFLA" in nombre:
            return presupuesto * 1.07

        # 4. JULIAN MAURICIO ORTIZ GOMEZ: PISO ESTRICTO DE 300 MILLONES
        if "JULIAN MAURICIO ORTIZ" in nombre:
            if presupuesto < 300_000_000:
                return 300_000_000  # Forzar a 300 Millones exactos si dio menos
            return presupuesto

        return presupuesto

    agg["presupuesto_2026"] = agg.apply(aplicar_reglas_anuales, axis=1)

    return agg

def calcular_pesos_mensuales(df_hist: pd.DataFrame, vendedor: str, col_valor: str = "valor_venta") -> np.ndarray:
    """Calcula la estacionalidad (pesos) mensual basada en el histórico."""
    df_vend = df_hist[df_hist["nomvendedor"] == vendedor]
    df_base = df_vend if not df_vend.empty else df_hist
    pesos = df_base.groupby("mes")[col_valor].sum()
    pesos = pesos.reindex(range(1, 13), fill_value=0)
    total = pesos.sum()
    if total > 0:
        return (pesos / total).values
    return np.array([1 / 12.0] * 12)

def distribuir_presupuesto_mensual(df_asignado: pd.DataFrame, df_hist: pd.DataFrame) -> pd.DataFrame:
    """
    Distribuye el presupuesto anual mes a mes aplicando estacionalidad
    y reglas de negocio mensuales específicas (Ej. Opalo mes 0 -> 45M).
    """
    # Usar 2025 como base de estacionalidad, o el último año disponible
    df_hist_2025 = df_hist[df_hist["anio"] == 2025]
    df_hist_base = df_hist_2025 if not df_hist_2025.empty else df_hist[df_hist["anio"] == df_hist["anio"].max()]
    
    registros = []
    
    for _, row in df_asignado.iterrows():
        nombre = normalizar_texto(row["nomvendedor"])
        grupo = normalizar_texto(row["grupo"])
        
        # --- EXCEPCIÓN MENSUAL: LEDUYN MELGAREJO ---
        # Debe tener fijo 146m mensual (ignora estacionalidad)
        if "LEDUYN MELGAREJO" in nombre:
            for mes_idx in range(1, 13):
                registros.append({
                    "nomvendedor": row["nomvendedor"],
                    "grupo": row["grupo"],
                    "mes": mes_idx,
                    "presupuesto_mensual": 146_000_000
                })
            continue

        # --- DISTRIBUCIÓN ESTÁNDAR ---
        pesos = calcular_pesos_mensuales(df_hist_base, row["nomvendedor"])
        
        for mes_idx, peso in enumerate(pesos, start=1):
            valor_mensual = row["presupuesto_2026"] * peso
            
            # --- EXCEPCIÓN MENSUAL: MOSTRADOR OPALO ---
            # Si el cálculo da 0 (mes vacío en histórico), forzar 45m
            # Se aplica si es el grupo OPALO o el vendedor está en OPALO
            if "OPALO" in grupo or "OPALO" in nombre:
                # Si el valor es muy bajo (cercano a 0) o 0, asignamos 45M
                if valor_mensual < 1_000_000: 
                    valor_mensual = 45_000_000

            registros.append({
                "nomvendedor": row["nomvendedor"],
                "grupo": row["grupo"],
                "mes": mes_idx,
                "presupuesto_mensual": valor_mensual
            })
            
    return pd.DataFrame(registros)