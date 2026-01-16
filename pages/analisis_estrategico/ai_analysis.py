"""Motor de análisis ejecutivo con IA - GPT-4 Mini"""
import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple
import json

def analizar_con_ia_avanzado(
    df_actual: pd.DataFrame,
    df_anterior: pd.DataFrame,
    metricas: Dict,
    lineas_estrategicas: List[str]
) -> Dict[str, any]:
    """
    Genera análisis ejecutivo COMPLETO y PROFUNDO
    
    Returns:
        Dict con análisis detallado por secciones
    """
    
    try:
        # Verificar OpenAI
        try:
            from openai import OpenAI
        except ImportError:
            return _analisis_manual_avanzado(df_actual, df_anterior, metricas, lineas_estrategicas)
        
        api_key = st.secrets.get("OPENAI_API_KEY", "")
        if not api_key:
            return _analisis_manual_avanzado(df_actual, df_anterior, metricas, lineas_estrategicas)
        
        client = OpenAI(api_key=api_key)
        
        # Preparar análisis detallado de líneas
        analisis_lineas = _analizar_lineas_estrategicas(df_actual, df_anterior, lineas_estrategicas)
        
        # Análisis de clientes
        analisis_clientes = _analizar_retencion_clientes(df_actual, df_anterior)
        
        # Construir prompt ejecutivo
        prompt = _construir_prompt_ejecutivo_avanzado(
            metricas, analisis_lineas, analisis_clientes
        )
        
        # Llamar a GPT-4 Mini
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Eres el CFO y Director Estratégico de una empresa de distribución industrial.
                    Tu especialidad es análisis de crecimiento, identificación de motores de negocio y gestión de portafolio.
                    Generas análisis ejecutivos concisos, contundentes y 100% accionables.
                    Usas datos específicos, porcentajes y cifras concretas.
                    Tu estilo es directo, sin relleno, solo insights que generan decisiones."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        analisis_ia = response.choices[0].message.content
        
        return {
            "analisis_ejecutivo": analisis_ia,
            "analisis_lineas": analisis_lineas,
            "analisis_clientes": analisis_clientes,
            "metricas_clave": metricas
        }
        
    except Exception as e:
        st.warning(f"⚠️ IA no disponible: {str(e)}")
        return _analisis_manual_avanzado(df_actual, df_anterior, metricas, lineas_estrategicas)


def _resolver_columnas(df: pd.DataFrame, df_fallback: pd.DataFrame | None = None) -> Dict[str, str]:
    """Mapea columnas reales comprobando presencia en df_actual/df_anterior."""
    def pick(candidatos: List[str]) -> str | None:
        for c in candidatos:
            if c and c in df.columns:
                return c
            if df_fallback is not None and c and c in df_fallback.columns:
                return c
        return None

    col_cliente = pick([
        "nombre_cliente",
        "CLIENTE",
        next((x for x in df.columns if "cliente" in x.lower()), None),
        next((x for x in df_fallback.columns if "cliente" in x.lower()), None) if df_fallback is not None else None,
    ])

    col_valor = pick([
        "valor_venta",
        "VALOR",
        next((x for x in df.columns if "valor" in x.lower()), None),
        next((x for x in df_fallback.columns if "valor" in x.lower()), None) if df_fallback is not None else None,
    ])

    col_linea = pick([
        "Linea_Estrategica",
        "linea_producto",
        next((x for x in df.columns if "linea" in x.lower()), None),
        next((x for x in df_fallback.columns if "linea" in x.lower()), None) if df_fallback is not None else None,
    ])

    return {"cliente": col_cliente, "valor": col_valor, "linea": col_linea}


def _analizar_lineas_estrategicas(df_actual, df_anterior, lineas_estrategicas):
    cols = _resolver_columnas(df_actual, df_anterior)
    columna_linea, columna_valor, columna_cliente = cols["linea"], cols["valor"], cols["cliente"]
    if None in (columna_linea, columna_valor, columna_cliente):
        return {}
    resultados = {}
    for linea in lineas_estrategicas:
        mask_a = df_actual[columna_linea].astype(str).str.upper() == linea.upper()
        mask_b = df_anterior[columna_linea].astype(str).str.upper() == linea.upper()
        ventas_a = df_actual.loc[mask_a, columna_valor].sum()
        ventas_b = df_anterior.loc[mask_b, columna_valor].sum()
        variacion_abs = ventas_a - ventas_b
        variacion_pct = (variacion_abs / ventas_b * 100) if ventas_b > 0 else (100.0 if ventas_a > 0 else 0.0)
        clientes_a = df_actual.loc[mask_a, columna_cliente].nunique()
        clientes_b = df_anterior.loc[mask_b, columna_cliente].nunique()
        resultados[linea] = {
            "ventas_actual": ventas_a,
            "ventas_anterior": ventas_b,
            "variacion_abs": variacion_abs,
            "variacion_pct": variacion_pct,
            "clientes_actual": clientes_a,
            "clientes_anterior": clientes_b,
            "impacto": "MOTOR" if variacion_pct > 10 else "FRENO" if variacion_pct < -10 else "ESTABLE",
        }
    return resultados

def _analizar_retencion_clientes(df_actual, df_anterior):
    cols = _resolver_columnas(df_actual, df_anterior)
    col_cliente, col_valor = cols["cliente"], cols["valor"]
    if None in (col_cliente, col_valor):
        return {
            "total_clientes_actual": 0,
            "total_clientes_anterior": 0,
            "clientes_retenidos": 0,
            "clientes_nuevos": 0,
            "clientes_perdidos": 0,
            "ventas_retenidos": 0,
            "ventas_nuevos": 0,
            "tasa_retencion": 0,
            "top_retenidos": {},
            "top_nuevos": {},
        }
    clientes_actual = set(df_actual[col_cliente].unique())
    clientes_anterior = set(df_anterior[col_cliente].unique())
    clientes_retenidos = clientes_actual & clientes_anterior
    clientes_nuevos = clientes_actual - clientes_anterior
    clientes_perdidos = clientes_anterior - clientes_actual
    ventas_retenidos = df_actual[df_actual[col_cliente].isin(clientes_retenidos)][col_valor].sum()
    ventas_nuevos = df_actual[df_actual[col_cliente].isin(clientes_nuevos)][col_valor].sum()
    top_retenidos = df_actual[df_actual[col_cliente].isin(clientes_retenidos)].groupby(col_cliente)[col_valor].sum().nlargest(10)
    top_nuevos = df_actual[df_actual[col_cliente].isin(clientes_nuevos)].groupby(col_cliente)[col_valor].sum().nlargest(10)
    tasa_retencion = (len(clientes_retenidos) / len(clientes_anterior) * 100) if len(clientes_anterior) > 0 else 0
    return {
        "total_clientes_actual": len(clientes_actual),
        "total_clientes_anterior": len(clientes_anterior),
        "clientes_retenidos": len(clientes_retenidos),
        "clientes_nuevos": len(clientes_nuevos),
        "clientes_perdidos": len(clientes_perdidos),
        "ventas_retenidos": ventas_retenidos,
        "ventas_nuevos": ventas_nuevos,
        "tasa_retencion": tasa_retencion,
        "top_retenidos": top_retenidos.to_dict(),
        "top_nuevos": top_nuevos.to_dict(),
    }


def _construir_prompt_ejecutivo_avanzado(
    metricas: Dict,
    analisis_lineas: Dict,
    analisis_clientes: Dict
) -> str:
    """Construye prompt ejecutivo con datos reales"""
    
    # Identificar motores y frenos
    motores = [l for l, data in analisis_lineas.items() if data['impacto'] == 'MOTOR']
    frenos = [l for l, data in analisis_lineas.items() if data['impacto'] == 'FRENO']
    
    prompt = f"""
# ANÁLISIS ESTRATÉGICO EJECUTIVO

## CONTEXTO GENERAL
- **Ventas Actuales**: ${metricas['venta_actual']:,.0f}
- **Ventas Anteriores**: ${metricas['venta_anterior']:,.0f}
- **Variación**: {metricas['pct_variacion']:.1f}% (${metricas['diferencia']:,.0f})

## ANÁLISIS POR LÍNEAS ESTRATÉGICAS

### MOTORES DE CRECIMIENTO (Líneas que impulsaron):
{_formatear_lineas(motores, analisis_lineas)}

### FRENOS AL CRECIMIENTO (Líneas que retrocedieron):
{_formatear_lineas(frenos, analisis_lineas)}

## ANÁLISIS DE CLIENTES
- **Tasa de Retención**: {analisis_clientes['tasa_retencion']:.1f}%
- **Clientes Retenidos**: {analisis_clientes['clientes_retenidos']} generaron ${analisis_clientes['ventas_retenidos']:,.0f}
- **Clientes Nuevos**: {analisis_clientes['clientes_nuevos']} aportaron ${analisis_clientes['ventas_nuevos']:,.0f}
- **Clientes Perdidos**: {analisis_clientes['clientes_perdidos']}

---

**GENERA UN ANÁLISIS EJECUTIVO CON:**

1. **RESUMEN EJECUTIVO (3 párrafos)**: 
   - ¿Qué pasó realmente? ¿Creímos o decreímos y por qué?
   - ¿Qué líneas fueron los VERDADEROS MOTORES?
   - ¿Qué líneas FRENARON y por qué?

2. **5 INSIGHTS CLAVE ACCIONABLES**:
   - Usa datos específicos de las líneas
   - Identifica oportunidades concretas
   - Señala riesgos reales

3. **5 DECISIONES ESTRATÉGICAS INMEDIATAS**:
   - Qué hacer con los motores (potenciarlos)
   - Cómo corregir los frenos
   - Estrategias de retención de clientes
   - Acciones con clientes nuevos

**IMPORTANTE**: Sé específico, usa números, menciona líneas por nombre, genera decisiones ejecutables AHORA.
"""
    
    return prompt


def _formatear_lineas(lineas: List[str], analisis: Dict) -> str:
    """Formatea información de líneas para el prompt"""
    resultado = []
    for linea in lineas:
        data = analisis[linea]
        resultado.append(
            f"- **{linea}**: ${data['ventas_actual']:,.0f} ({data['variacion_pct']:+.1f}%) | "
            f"{data['clientes_actual']} clientes | Δ ${data['variacion_abs']:,.0f}"
        )
    return "\n".join(resultado) if resultado else "Ninguna"


def _analisis_manual_avanzado(
    df_actual: pd.DataFrame,
    df_anterior: pd.DataFrame,
    metricas: Dict,
    lineas_estrategicas: List[str]
) -> Dict:
    """Análisis manual cuando IA no está disponible"""
    
    analisis_lineas = _analizar_lineas_estrategicas(df_actual, df_anterior, lineas_estrategicas)
    analisis_clientes = _analizar_retencion_clientes(df_actual, df_anterior)
    
    # Identificar motores y frenos
    motores = sorted(
        [(l, d) for l, d in analisis_lineas.items() if d['impacto'] == 'MOTOR'],
        key=lambda x: x[1]['variacion_abs'],
        reverse=True
    )
    
    frenos = sorted(
        [(l, d) for l, d in analisis_lineas.items() if d['impacto'] == 'FRENO'],
        key=lambda x: x[1]['variacion_abs']
    )
    
    # Construir análisis
    tendencia = "crecimiento" if metricas['pct_variacion'] > 0 else "decrecimiento"
    
    analisis_ejecutivo = f"""
## 📊 RESUMEN EJECUTIVO

El periodo cerró con un **{tendencia} del {metricas['pct_variacion']:.1f}%**, pasando de ${metricas['venta_anterior']:,.0f} a ${metricas['venta_actual']:,.0f}.

### 🚀 MOTORES DE CRECIMIENTO

Las líneas que impulsaron el crecimiento fueron:

{_generar_listado_motores(motores)}

### ⚠️ FRENOS AL CRECIMIENTO

Las líneas que presentaron retrocesos fueron:

{_generar_listado_frenos(frenos)}

### 👥 GESTIÓN DE CLIENTES

- **Tasa de Retención**: {analisis_clientes['tasa_retencion']:.1f}%
- **{analisis_clientes['clientes_retenidos']} clientes retenidos** generaron ${analisis_clientes['ventas_retenidos']:,.0f}
- **{analisis_clientes['clientes_nuevos']} clientes nuevos** aportaron ${analisis_clientes['ventas_nuevos']:,.0f}
- **{analisis_clientes['clientes_perdidos']} clientes perdidos** representan una oportunidad de recuperación

## 💡 INSIGHTS CLAVE

1. 📈 Los motores de crecimiento están concentrados en {len(motores)} líneas estratégicas
2. ⚠️ {len(frenos)} líneas requieren atención inmediata y planes de recuperación
3. 🎯 La retención de clientes está en {analisis_clientes['tasa_retencion']:.1f}%, {'excelente' if analisis_clientes['tasa_retencion'] > 85 else 'requiere mejora'}
4. 🆕 Los clientes nuevos representan el {(analisis_clientes['ventas_nuevos']/metricas['venta_actual']*100):.1f}% de las ventas
5. 💼 Existen {analisis_clientes['clientes_perdidos']} clientes por recuperar

## 🎯 DECISIONES ESTRATÉGICAS

1. **POTENCIAR MOTORES**: Invertir recursos en {', '.join([m[0] for m in motores[:3]])}
2. **CORREGIR FRENOS**: Implementar planes de recuperación para {', '.join([f[0] for f in frenos[:3]])}
3. **RETENCIÓN**: Crear programa VIP para top 20 clientes retenidos
4. **CAPTACIÓN**: Replicar estrategia que trajo {analisis_clientes['clientes_nuevos']} clientes nuevos
5. **RECUPERACIÓN**: Contactar inmediatamente a los {analisis_clientes['clientes_perdidos']} clientes perdidos
"""
    
    return {
        "analisis_ejecutivo": analisis_ejecutivo,
        "analisis_lineas": analisis_lineas,
        "analisis_clientes": analisis_clientes,
        "metricas_clave": metricas
    }


def _generar_listado_motores(motores: List[Tuple]) -> str:
    """Genera listado formateado de motores"""
    if not motores:
        return "- Ninguna línea mostró crecimiento significativo"
    
    resultado = []
    for linea, data in motores[:5]:
        resultado.append(
            f"- **{linea}**: +{data['variacion_pct']:.1f}% (${data['variacion_abs']:,.0f}) | "
            f"{data['clientes_actual']} clientes activos"
        )
    return "\n".join(resultado)


def _generar_listado_frenos(frenos: List[Tuple]) -> str:
    """Genera listado formateado de frenos"""
    if not frenos:
        return "- Ninguna línea mostró decrecimiento significativo"
    
    resultado = []
    for linea, data in frenos[:5]:
        resultado.append(
            f"- **{linea}**: {data['variacion_pct']:.1f}% (${data['variacion_abs']:,.0f}) | "
            f"Perdió {data['clientes_anterior'] - data['clientes_actual']} clientes"
        )
    return "\n".join(resultado)