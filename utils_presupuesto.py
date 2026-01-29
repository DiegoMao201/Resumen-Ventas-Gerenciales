# ==============================================================================
# ARCHIVO: utils_presupuesto.py
# DESCRIPCIÓN: Lógica de negocio, cálculos estadísticos y reglas de excepción
# ==============================================================================
import pandas as pd
import numpy as np
import unicodedata
import re

def normalizar_texto(texto: str) -> str:
    """
    Normaliza cadenas de texto: mayúsculas, sin tildes, sin caracteres raros
    y ELIMINA espacios dobles o sobrantes.
    """
    if pd.isna(texto): return ""
    texto = str(texto).upper()
    # Eliminar tildes
    texto = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    # Dejar solo letras, números, espacios y guiones
    texto = re.sub(r"[^A-Z0-9\s\-]", "", texto)
    # Colapsar múltiples espacios en uno solo y quitar bordes (CLAVE PARA QUE COINCIDAN NOMBRES)
    return " ".join(texto.split())

def construir_grupo(vendedor: str, grupos: dict) -> str:
    """Asigna el nombre del grupo si el vendedor pertenece a uno."""
    vend_norm = normalizar_texto(vendedor)
    for grupo, lista in grupos.items():
        if vend_norm in [normalizar_texto(v) for v in lista]:
            return normalizar_texto(grupo)
    return vend_norm

def proyectar_total_2026(total_2024, total_2025):
    """Calcula la proyección global para 2026."""
    if total_2024 <= 0 or total_2025 <= 0:
        return total_2025, 0
    tasa_hist = (total_2025 - total_2024) / total_2024
    factor = 0.8  # Factor conservador
    tasa_aplicada = tasa_hist * factor
    return total_2025 * (1 + tasa_aplicada), tasa_aplicada

def asignar_presupuesto(df: pd.DataFrame, grupos: dict, total_2026: float) -> pd.DataFrame:
    """
    Calcula el presupuesto anual y APLICA PISOS MÍNIMOS (Reglas de Oro).
    """
    # Filtrar años base
    base = df[df["anio"].isin([2024, 2025])]
    
    # Agregación inicial
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
    
    # Cálculo preliminar
    agg["score_raw"] = agg["venta_2025"] * (1 + agg["crec_ajustado"]) * (1 + 0.10 * agg["diversidad"])
    suma_scores = agg["score_raw"].sum()
    agg["presupuesto_prelim"] = np.where(suma_scores > 0, agg["score_raw"] / suma_scores * total_2026, 0)

    # Pisos y techos estadísticos
    piso_pct = 0.70
    techo_pct = 1.35
    agg["presupuesto_ajustado"] = np.clip(
        agg["presupuesto_prelim"],
        agg["venta_2025"] * piso_pct,
        agg["venta_2025"] * techo_pct
    )

    # Re-escalado al objetivo
    suma_ajustada = agg["presupuesto_ajustado"].sum()
    factor_rescale = total_2026 / suma_ajustada if suma_ajustada > 0 else 0
    agg["presupuesto_2026"] = agg["presupuesto_ajustado"] * factor_rescale

    # Asignación de grupos
    agg["grupo"] = agg["nomvendedor"].apply(lambda v: construir_grupo(v, grupos))

    # --- REGLAS DE ORO (EXCEPCIONES ANUALES) ---
    def aplicar_reglas_finales(row):
        nombre = normalizar_texto(row["nomvendedor"])
        presupuesto = row["presupuesto_2026"]

        # LEDUYN MELGAREJO ARIAS: Fijo Mensual x 12
        if "LEDUYN" in nombre and "MELGAREJO" in nombre:
            return 146_000_000 * 12

        # JERSON ATEHORTUA OLARTE: Si presupuesto < 100M, subir con % cerrado hasta >= 100M
        if "JERSON" in nombre and "ATEHORTUA" in nombre:
            if presupuesto < 100_000_000:
                for pct in [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.60, 1.70, 2.00, 3.00, 4.00]:
                    nuevo = presupuesto * (1 + pct)
                    if nuevo >= 100_000_000:
                        print("AJUSTE JERSON:", nombre, "PCT:", pct, "NUEVO:", nuevo)
                        return int(nuevo)
                print("AJUSTE JERSON (FALLBACK):", nombre, "100M FIJO")
                return 100_000_000
            print("JERSON OK:", nombre, presupuesto)
            return presupuesto

        # PABLO CESAR MAFLA BANOL: +7%
        if "PABLO" in nombre and "MAFLA" in nombre:
            return presupuesto * 1.07

        # JULIAN MAURICIO ORTIZ GOMEZ: Piso mínimo de 300 Millones
        if "JULIAN" in nombre and "ORTIZ" in nombre:
            if presupuesto < 300_000_000:
                return 300_000_000

        return presupuesto

    # APLICA LAS REGLAS FINALES DESPUÉS DEL REESCALADO
    agg["presupuesto_2026"] = agg.apply(aplicar_reglas_finales, axis=1)

    return agg

def calcular_pesos_mensuales(df_hist: pd.DataFrame, vendedor: str, col_valor: str = "valor_venta") -> np.ndarray:
    """Calcula la estacionalidad (pesos) mensual."""
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
    Distribuye mes a mes y aplica reglas mensuales (Ej. Opalo piso 45M).
    """
    df_hist_2025 = df_hist[df_hist["anio"] == 2025]
    df_hist_base = df_hist_2025 if not df_hist_2025.empty else df_hist[df_hist["anio"] == df_hist["anio"].max()]
    
    registros = []
    
    for _, row in df_asignado.iterrows():
        nombre = normalizar_texto(row["nomvendedor"])
        grupo = normalizar_texto(row["grupo"])
        
        # EXCEPCIÓN: LEDUYN FIJO
        if "LEDUYN" in nombre and "MELGAREJO" in nombre:
            for mes_idx in range(1, 13):
                registros.append({
                    "nomvendedor": row["nomvendedor"],
                    "grupo": row["grupo"],
                    "mes": mes_idx,
                    "presupuesto_mensual": 146_000_000
                })
            continue

        # DISTRIBUCIÓN ESTÁNDAR
        pesos = calcular_pesos_mensuales(df_hist_base, row["nomvendedor"])
        
        for mes_idx, peso in enumerate(pesos, start=1):
            valor_mensual = row["presupuesto_2026"] * peso
            
            # EXCEPCIÓN: MOSTRADOR OPALO PISO 45M
            # Aplica si el grupo es OPALO o el vendedor contiene OPALO
            if "OPALO" in grupo or "OPALO" in nombre:
                # Si el mes es 0 o muy bajo (menor a 5 millones), sube a 45M
                if valor_mensual < 5_000_000:
                    valor_mensual = 45_000_000

            registros.append({
                "nomvendedor": row["nomvendedor"],
                "grupo": row["grupo"],
                "mes": mes_idx,
                "presupuesto_mensual": valor_mensual
            })
            
    return pd.DataFrame(registros)