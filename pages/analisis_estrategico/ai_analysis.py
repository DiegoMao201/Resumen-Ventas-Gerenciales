"""Motor de análisis con Inteligencia Artificial usando OpenAI GPT-4"""
import streamlit as st
import pandas as pd
from typing import Dict, List

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
        # Verificar si OpenAI está disponible
        try:
            from openai import OpenAI
        except ImportError:
            return _analisis_manual(df_actual, df_anterior, metricas)
        
        # Configurar cliente de OpenAI
        api_key = st.secrets.get("OPENAI_API_KEY", "")
        
        if not api_key:
            return _analisis_manual(df_actual, df_anterior, metricas)
        
        client = OpenAI(api_key=api_key)
        
        # Preparar datos para el prompt
        prompt = _construir_prompt_ejecutivo(df_actual, df_anterior, metricas)
        
        # Llamar a GPT-4 Mini
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
        st.warning(f"⚠️ No se pudo generar análisis con IA: {str(e)}")
        return _analisis_manual(df_actual, df_anterior, metricas)


def _analisis_manual(df_actual: pd.DataFrame, df_anterior: pd.DataFrame, metricas: Dict) -> Dict:
    """Genera análisis básico sin IA cuando OpenAI no está disponible"""
    
    # Calcular métricas básicas
    venta_actual = metricas['venta_actual']
    venta_anterior = metricas['venta_anterior']
    pct_variacion = metricas['pct_variacion']
    
    # Top marcas
    top_marcas = df_actual.groupby('Marca_Master')['VALOR'].sum().nlargest(3)
    marcas_str = ", ".join([f"{m} (${v:,.0f})" for m, v in top_marcas.items()])
    
    # Top clientes
    top_clientes = df_actual.groupby('CLIENTE')['VALOR'].sum().nlargest(5)
    
    # Construir resumen
    if pct_variacion > 0:
        tendencia = f"crecimiento del {pct_variacion:.1f}%"
        interpretacion = "un desempeño positivo"
    else:
        tendencia = f"decrecimiento del {abs(pct_variacion):.1f}%"
        interpretacion = "un desafío que requiere atención"
    
    resumen = f"""
## 📊 Resumen Ejecutivo

El análisis comparativo del periodo muestra **{tendencia}** en las ventas, pasando de **${venta_anterior:,.0f}** a **${venta_actual:,.0f}**. 

Esto representa {interpretacion} para la organización. Las principales marcas que impulsaron el desempeño fueron: **{marcas_str}**.

La base de clientes activos mostró una composición de {top_clientes.count()} clientes principales que representan una parte significativa de las ventas totales.

### 🎯 Análisis de Tendencias

El comportamiento mensual muestra patrones estacionales que deben ser considerados en la planificación estratégica. Se identifican oportunidades de crecimiento en segmentos específicos del portafolio.
"""
    
    insights = [
        f"📈 Las ventas {'aumentaron' if pct_variacion > 0 else 'disminuyeron'} en ${abs(metricas['diferencia']):,.0f} respecto al periodo anterior",
        f"🏷️ Las 3 marcas principales generaron el {(top_marcas.sum()/venta_actual*100):.1f}% de las ventas totales",
        f"👥 Los 5 clientes principales representan ${top_clientes.sum():,.0f} en ventas acumuladas",
        f"📊 La variación porcentual de {pct_variacion:+.1f}% indica {'una tendencia positiva' if pct_variacion > 0 else 'necesidad de estrategias correctivas'}",
        f"💡 Se identificaron {df_actual['CLIENTE'].nunique()} clientes activos en el periodo"
    ]
    
    recomendaciones = [
        "🎯 **Fortalecer relaciones con clientes TOP**: Implementar programa de fidelización para los 10 clientes principales",
        "📊 **Diversificar portafolio**: Reducir dependencia de las 3 marcas principales mediante promoción cruzada",
        "🔍 **Análisis de rentabilidad**: Evaluar márgenes por línea de producto para optimizar mix de ventas",
        "📈 **Plan de recuperación**: Desarrollar estrategias específicas para productos con bajo desempeño" if pct_variacion < 0 else "🚀 **Capitalizar momentum**: Invertir en las líneas de mayor crecimiento para maximizar resultados",
        "💼 **Capacitación comercial**: Entrenar al equipo en técnicas de venta consultiva y cross-selling"
    ]
    
    return {
        "resumen": resumen,
        "insights": insights,
        "recomendaciones": recomendaciones
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
            elif seccion_actual == 'insights' and (linea.strip().startswith('-') or linea.strip().startswith('•') or (linea.strip() and linea.strip()[0].isdigit())):
                secciones['insights'].append(linea.strip())
            elif seccion_actual == 'recomendaciones' and (linea.strip().startswith('-') or linea.strip().startswith('•') or (linea.strip() and linea.strip()[0].isdigit())):
                secciones['recomendaciones'].append(linea.strip())
    
    # Si no se pudo parsear, devolver todo como resumen
    if not secciones['resumen'] and not secciones['insights']:
        secciones['resumen'] = texto
    
    return secciones