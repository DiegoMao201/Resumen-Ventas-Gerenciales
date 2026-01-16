"""Motor de análisis con Inteligencia Artificial usando OpenAI GPT-4"""
import streamlit as st
import pandas as pd
from typing import Dict, List
from openai import OpenAI
from datetime import datetime

def analizar_con_ia(
    df_actual: pd.DataFrame,
    df_anterior: pd.DataFrame,
    metricas: Dict
) -> Dict[str, str]:
    """
    Genera análisis ejecutivo profesional usando GPT-4 Mini
    
    Returns:
        Dict con diferentes secciones de análisis
    """
    
    try:
        # Configurar cliente de OpenAI
        api_key = st.secrets.get("OPENAI_API_KEY", "")
        
        if not api_key:
            return {
                "resumen": "⚠️ API Key de OpenAI no configurada. Configure OPENAI_API_KEY en secrets.",
                "insights": [],
                "recomendaciones": []
            }
        
        client = OpenAI(api_key=api_key)
        
        # Preparar datos para el prompt
        prompt = _construir_prompt_ejecutivo(df_actual, df_anterior, metricas)
        
        # Llamar a GPT-4 Mini con la nueva API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Eres un consultor estratégico senior con 20 años de experiencia en análisis de crecimiento empresarial. 
                    Tu especialidad es identificar patrones, oportunidades y riesgos en datos de ventas.
                    Responde en español con un tono profesional y ejecutivo."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        analisis_completo = response.choices[0].message.content
        
        # Parsear respuesta
        return _parsear_respuesta_ia(analisis_completo)
        
    except Exception as e:
        return {
            "resumen": f"⚠️ Error al conectar con OpenAI: {str(e)}",
            "insights": ["No se pudo generar análisis automático"],
            "recomendaciones": ["Revisar configuración de API Key y conexión a internet"]
        }


def _construir_prompt_ejecutivo(
    df_actual: pd.DataFrame,
    df_anterior: pd.DataFrame,
    metricas: Dict
) -> str:
    """Construye un prompt detallado para GPT-4"""
    
    # Top marcas
    top_marcas_actual = df_actual.groupby('Marca_Master')['VALOR'].sum().nlargest(5)
    top_marcas_anterior = df_anterior.groupby('Marca_Master')['VALOR'].sum()
    
    # Top clientes
    top_clientes_actual = df_actual.groupby('CLIENTE')['VALOR'].sum().nlargest(10)
    
    # Tendencia mensual
    ventas_por_mes_actual = df_actual.groupby('mes')['VALOR'].sum()
    ventas_por_mes_anterior = df_anterior.groupby('mes')['VALOR'].sum()
    
    prompt = f"""
Como consultor estratégico, analiza el siguiente desempeño comercial y genera un informe ejecutivo:

## MÉTRICAS GENERALES
- Ventas Año Actual: ${metricas['venta_actual']:,.0f}
- Ventas Año Anterior: ${metricas['venta_anterior']:,.0f}
- Variación: {metricas['pct_variacion']:.1f}%
- Diferencia: ${metricas['diferencia']:,.0f}

## TOP 5 MARCAS AÑO ACTUAL
{top_marcas_actual.to_string()}

## COMPARACIÓN VS AÑO ANTERIOR (MISMAS MARCAS)
{_comparar_marcas(top_marcas_actual, top_marcas_anterior)}

## TOP 10 CLIENTES
{top_clientes_actual.head(10).to_string()}

## TENDENCIA MENSUAL
Año Actual: {ventas_por_mes_actual.to_dict()}
Año Anterior: {ventas_por_mes_anterior.to_dict()}

---

POR FAVOR GENERA UN ANÁLISIS EJECUTIVO CON:

1. **RESUMEN EJECUTIVO** (2-3 párrafos): ¿Cómo fue el desempeño general? ¿Qué explica el crecimiento/decrecimiento?

2. **INSIGHTS CLAVE** (5-7 puntos): Hallazgos específicos y accionables sobre:
   - Marcas que impulsaron el crecimiento
   - Clientes clave
   - Patrones estacionales
   - Áreas de riesgo

3. **RECOMENDACIONES ESTRATÉGICAS** (5 acciones concretas): ¿Qué debe hacer la gerencia AHORA para:
   - Acelerar el crecimiento
   - Mitigar riesgos
   - Capitalizar oportunidades

Formato: Usa emojis, negritas y bullets para hacerlo ejecutivo y escaneable.
"""
    
    return prompt


def _comparar_marcas(actual: pd.Series, anterior: pd.Series) -> str:
    """Compara ventas de marcas año a año"""
    resultado = []
    for marca in actual.index:
        venta_actual = actual[marca]
        venta_anterior = anterior.get(marca, 0)
        variacion = ((venta_actual - venta_anterior) / venta_anterior * 100) if venta_anterior > 0 else 0
        resultado.append(f"{marca}: ${venta_actual:,.0f} ({variacion:+.1f}%)")
    return "\n".join(resultado)


def _parsear_respuesta_ia(texto: str) -> Dict[str, any]:
    """Extrae secciones del análisis de IA"""
    
    secciones = {
        "resumen": "",
        "insights": [],
        "recomendaciones": []
    }
    
    # Buscar secciones en el texto
    lineas = texto.split('\n')
    seccion_actual = None
    
    for linea in lineas:
        linea_lower = linea.lower()
        
        if 'resumen ejecutivo' in linea_lower or 'resumen' in linea_lower:
            seccion_actual = 'resumen'
        elif 'insight' in linea_lower or 'hallazgo' in linea_lower or 'clave' in linea_lower:
            seccion_actual = 'insights'
        elif 'recomendación' in linea_lower or 'estratégica' in linea_lower or 'acción' in linea_lower:
            seccion_actual = 'recomendaciones'
        elif linea.strip():
            if seccion_actual == 'resumen':
                secciones['resumen'] += linea + "\n"
            elif seccion_actual == 'insights' and (linea.strip().startswith('-') or linea.strip().startswith('•') or linea.strip()[0].isdigit()):
                secciones['insights'].append(linea.strip())
            elif seccion_actual == 'recomendaciones' and (linea.strip().startswith('-') or linea.strip().startswith('•') or linea.strip()[0].isdigit()):
                secciones['recomendaciones'].append(linea.strip())
    
    # Si no se pudo parsear, devolver todo como resumen
    if not secciones['resumen'] and not secciones['insights']:
        secciones['resumen'] = texto
    
    return secciones