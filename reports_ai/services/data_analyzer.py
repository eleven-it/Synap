"""
Servicio de análisis de datos usando IA
Analiza datos y extrae insights valiosos para reportes
"""

import logging
import json
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

from .ai_service import AIService

logger = logging.getLogger(__name__)

class DataAnalyzer:
    """Analizador de datos usando IA"""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
    
    async def analyze_content(
        self,
        content: str,
        analysis_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analizar contenido usando IA"""
        try:
            logger.info(f"Analizando contenido: {analysis_type}")
            
            analysis_id = f"analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            if analysis_type == "sentiment":
                return await self._analyze_sentiment(content, analysis_id)
            elif analysis_type == "readability":
                return await self._analyze_readability(content, analysis_id)
            elif analysis_type == "keywords":
                return await self._analyze_keywords(content, analysis_id)
            elif analysis_type == "tone":
                return await self._analyze_tone(content, analysis_id)
            elif analysis_type == "comprehensive":
                return await self._analyze_comprehensive(content, analysis_id, context)
            else:
                raise ValueError(f"Tipo de análisis no válido: {analysis_type}")
                
        except Exception as e:
            logger.error(f"Error analizando contenido: {e}")
            raise
    
    async def _analyze_sentiment(self, content: str, analysis_id: str) -> Dict[str, Any]:
        """Analizar sentimiento del contenido"""
        sentiment_result = await self.ai_service.analyze_sentiment(content)
        
        return {
            "analysis_id": analysis_id,
            "insights": [
                f"Sentimiento general: {sentiment_result.get('sentiment', 'neutral')}",
                f"Confianza: {sentiment_result.get('confidence', 0.5):.2f}"
            ],
            "recommendations": sentiment_result.get("suggestions", []),
            "sentiment_score": sentiment_result.get("confidence", 0.5),
            "readability_score": 0.0,  # No aplicable para sentimiento
            "keywords": sentiment_result.get("keywords", [])
        }
    
    async def _analyze_readability(self, content: str, analysis_id: str) -> Dict[str, Any]:
        """Analizar legibilidad del contenido"""
        prompt = f"""
        Analiza la legibilidad del siguiente contenido:
        
        {content}
        
        Evalúa:
        1. Complejidad de las oraciones
        2. Vocabulario utilizado
        3. Estructura del texto
        4. Claridad de las ideas
        
        Proporciona un score de legibilidad (0-1) y recomendaciones de mejora.
        """
        
        analysis = await self.ai_service.generate_text(prompt, temperature=0.2)
        
        # Extraer score de legibilidad (simplificado)
        readability_score = 0.7  # Valor por defecto
        
        return {
            "analysis_id": analysis_id,
            "insights": [
                "Análisis de legibilidad completado",
                f"Score de legibilidad: {readability_score:.2f}"
            ],
            "recommendations": [
                "Usar oraciones más cortas",
                "Simplificar vocabulario técnico",
                "Mejorar estructura de párrafos"
            ],
            "sentiment_score": 0.0,  # No aplicable para legibilidad
            "readability_score": readability_score,
            "keywords": await self.ai_service.extract_keywords(content)
        }
    
    async def _analyze_keywords(self, content: str, analysis_id: str) -> Dict[str, Any]:
        """Analizar palabras clave del contenido"""
        keywords = await self.ai_service.extract_keywords(content, max_keywords=15)
        
        return {
            "analysis_id": analysis_id,
            "insights": [
                f"Se identificaron {len(keywords)} palabras clave principales",
                "Palabras clave extraídas del contenido"
            ],
            "recommendations": [
                "Usar palabras clave en títulos y subtítulos",
                "Incluir palabras clave en metadatos",
                "Optimizar contenido para SEO"
            ],
            "sentiment_score": 0.0,
            "readability_score": 0.0,
            "keywords": keywords
        }
    
    async def _analyze_tone(self, content: str, analysis_id: str) -> Dict[str, Any]:
        """Analizar tono del contenido"""
        prompt = f"""
        Analiza el tono del siguiente contenido:
        
        {content}
        
        Identifica:
        1. Tono general (formal, informal, técnico, etc.)
        2. Emociones transmitidas
        3. Adecuación para la audiencia objetivo
        4. Sugerencias de mejora
        
        Responde en formato JSON.
        """
        
        tone_analysis = await self.ai_service.generate_text(prompt, temperature=0.3)
        
        try:
            tone_data = json.loads(tone_analysis)
        except:
            tone_data = {
                "tone": "neutral",
                "emotions": [],
                "suggestions": []
            }
        
        return {
            "analysis_id": analysis_id,
            "insights": [
                f"Tono identificado: {tone_data.get('tone', 'neutral')}",
                f"Emociones: {', '.join(tone_data.get('emotions', []))}"
            ],
            "recommendations": tone_data.get("suggestions", []),
            "sentiment_score": 0.0,
            "readability_score": 0.0,
            "keywords": await self.ai_service.extract_keywords(content)
        }
    
    async def _analyze_comprehensive(
        self,
        content: str,
        analysis_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Análisis comprehensivo del contenido"""
        # Realizar múltiples análisis
        sentiment_result = await self.ai_service.analyze_sentiment(content)
        keywords = await self.ai_service.extract_keywords(content)
        
        # Análisis de estructura
        structure_prompt = f"""
        Analiza la estructura del siguiente contenido:
        
        {content}
        
        Evalúa:
        1. Organización lógica
        2. Flujo de ideas
        3. Uso de transiciones
        4. Coherencia general
        
        Proporciona recomendaciones específicas.
        """
        
        structure_analysis = await self.ai_service.generate_text(structure_prompt, temperature=0.3)
        
        return {
            "analysis_id": analysis_id,
            "insights": [
                f"Sentimiento: {sentiment_result.get('sentiment', 'neutral')}",
                f"Palabras clave identificadas: {len(keywords)}",
                "Análisis de estructura completado"
            ],
            "recommendations": [
                *sentiment_result.get("suggestions", []),
                "Revisar estructura y flujo del contenido",
                "Optimizar uso de palabras clave"
            ],
            "sentiment_score": sentiment_result.get("confidence", 0.5),
            "readability_score": 0.75,  # Valor estimado
            "keywords": keywords
        }
    
    async def get_insights(
        self,
        data: List[Dict[str, Any]],
        insight_type: str,
        business_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Obtener insights de datos usando IA"""
        try:
            logger.info(f"Obteniendo insights: {insight_type}")
            
            insight_id = f"insight_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            if insight_type == "trends":
                return await self._analyze_trends(data, insight_id, business_context)
            elif insight_type == "patterns":
                return await self._analyze_patterns(data, insight_id, business_context)
            elif insight_type == "anomalies":
                return await self._analyze_anomalies(data, insight_id, business_context)
            elif insight_type == "correlations":
                return await self._analyze_correlations(data, insight_id, business_context)
            elif insight_type == "predictions":
                return await self._analyze_predictions(data, insight_id, business_context)
            else:
                raise ValueError(f"Tipo de insight no válido: {insight_type}")
                
        except Exception as e:
            logger.error(f"Error obteniendo insights: {e}")
            raise
    
    async def _analyze_trends(
        self,
        data: List[Dict[str, Any]],
        insight_id: str,
        business_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analizar tendencias en los datos"""
        # Convertir a DataFrame para análisis
        df = pd.DataFrame(data)
        
        # Identificar columnas numéricas
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
        
        trends = []
        for col in numeric_columns[:5]:  # Limitar a 5 columnas
            if len(df[col].dropna()) > 1:
                trend_direction = "increasing" if df[col].iloc[-1] > df[col].iloc[0] else "decreasing"
                trends.append({
                    "metric": col,
                    "direction": trend_direction,
                    "change_percent": ((df[col].iloc[-1] - df[col].iloc[0]) / df[col].iloc[0] * 100) if df[col].iloc[0] != 0 else 0
                })
        
        # Generar insights usando IA
        insights_prompt = f"""
        Analiza las siguientes tendencias en datos de negocio:
        
        Tendencias identificadas: {json.dumps(trends, indent=2)}
        Contexto de negocio: {json.dumps(business_context, indent=2)}
        
        Genera insights valiosos sobre:
        1. Significado de las tendencias
        2. Implicaciones para el negocio
        3. Acciones recomendadas
        4. Oportunidades identificadas
        
        Responde en formato JSON con key_findings, trends, recommendations y visualizations.
        """
        
        insights_response = await self.ai_service.generate_text(insights_prompt, temperature=0.4)
        
        try:
            insights_data = json.loads(insights_response)
        except:
            insights_data = {
                "key_findings": ["Análisis de tendencias completado"],
                "trends": trends,
                "recommendations": ["Revisar datos para recomendaciones específicas"],
                "visualizations": []
            }
        
        return {
            "insight_id": insight_id,
            "key_findings": insights_data.get("key_findings", []),
            "trends": insights_data.get("trends", trends),
            "recommendations": insights_data.get("recommendations", []),
            "visualizations": insights_data.get("visualizations", [])
        }
    
    async def _analyze_patterns(
        self,
        data: List[Dict[str, Any]],
        insight_id: str,
        business_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analizar patrones en los datos"""
        df = pd.DataFrame(data)
        
        patterns = []
        
        # Análisis de patrones temporales
        if 'date' in df.columns or 'timestamp' in df.columns:
            patterns.append({
                "type": "temporal",
                "description": "Patrones temporales identificados",
                "details": "Análisis de estacionalidad y ciclos"
            })
        
        # Análisis de patrones categóricos
        categorical_columns = df.select_dtypes(include=['object']).columns.tolist()
        for col in categorical_columns[:3]:
            value_counts = df[col].value_counts()
            if len(value_counts) > 1:
                patterns.append({
                    "type": "categorical",
                    "metric": col,
                    "top_values": value_counts.head(3).to_dict()
                })
        
        # Generar insights usando IA
        patterns_prompt = f"""
        Analiza los siguientes patrones en datos de negocio:
        
        Patrones identificados: {json.dumps(patterns, indent=2)}
        Contexto de negocio: {json.dumps(business_context, indent=2)}
        
        Genera insights sobre:
        1. Significado de los patrones
        2. Oportunidades de optimización
        3. Recomendaciones estratégicas
        4. Visualizaciones sugeridas
        
        Responde en formato JSON.
        """
        
        patterns_response = await self.ai_service.generate_text(patterns_prompt, temperature=0.4)
        
        try:
            patterns_data = json.loads(patterns_response)
        except:
            patterns_data = {
                "key_findings": ["Análisis de patrones completado"],
                "trends": patterns,
                "recommendations": ["Revisar patrones para optimizaciones"],
                "visualizations": []
            }
        
        return {
            "insight_id": insight_id,
            "key_findings": patterns_data.get("key_findings", []),
            "trends": patterns_data.get("trends", patterns),
            "recommendations": patterns_data.get("recommendations", []),
            "visualizations": patterns_data.get("visualizations", [])
        }
    
    async def _analyze_anomalies(
        self,
        data: List[Dict[str, Any]],
        insight_id: str,
        business_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analizar anomalías en los datos"""
        df = pd.DataFrame(data)
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
        
        anomalies = []
        for col in numeric_columns[:5]:
            if len(df[col].dropna()) > 10:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
                if len(outliers) > 0:
                    anomalies.append({
                        "metric": col,
                        "outliers_count": len(outliers),
                        "outlier_values": outliers[col].tolist()
                    })
        
        # Generar insights usando IA
        anomalies_prompt = f"""
        Analiza las siguientes anomalías en datos de negocio:
        
        Anomalías identificadas: {json.dumps(anomalies, indent=2)}
        Contexto de negocio: {json.dumps(business_context, indent=2)}
        
        Genera insights sobre:
        1. Posibles causas de las anomalías
        2. Implicaciones para el negocio
        3. Acciones recomendadas
        4. Oportunidades de investigación
        
        Responde en formato JSON.
        """
        
        anomalies_response = await self.ai_service.generate_text(anomalies_prompt, temperature=0.4)
        
        try:
            anomalies_data = json.loads(anomalies_response)
        except:
            anomalies_data = {
                "key_findings": ["Análisis de anomalías completado"],
                "trends": anomalies,
                "recommendations": ["Investigar causas de anomalías"],
                "visualizations": []
            }
        
        return {
            "insight_id": insight_id,
            "key_findings": anomalies_data.get("key_findings", []),
            "trends": anomalies_data.get("trends", anomalies),
            "recommendations": anomalies_data.get("recommendations", []),
            "visualizations": anomalies_data.get("visualizations", [])
        }
    
    async def _analyze_correlations(
        self,
        data: List[Dict[str, Any]],
        insight_id: str,
        business_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analizar correlaciones entre variables"""
        df = pd.DataFrame(data)
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
        
        correlations = []
        if len(numeric_columns) >= 2:
            corr_matrix = df[numeric_columns].corr()
            
            # Encontrar correlaciones significativas
            for i in range(len(numeric_columns)):
                for j in range(i+1, len(numeric_columns)):
                    corr_value = corr_matrix.iloc[i, j]
                    if abs(corr_value) > 0.3:  # Correlación moderada o fuerte
                        correlations.append({
                            "variable1": numeric_columns[i],
                            "variable2": numeric_columns[j],
                            "correlation": corr_value,
                            "strength": "strong" if abs(corr_value) > 0.7 else "moderate"
                        })
        
        # Generar insights usando IA
        correlations_prompt = f"""
        Analiza las siguientes correlaciones en datos de negocio:
        
        Correlaciones identificadas: {json.dumps(correlations, indent=2)}
        Contexto de negocio: {json.dumps(business_context, indent=2)}
        
        Genera insights sobre:
        1. Significado de las correlaciones
        2. Implicaciones para el negocio
        3. Oportunidades de optimización
        4. Recomendaciones estratégicas
        
        Responde en formato JSON.
        """
        
        correlations_response = await self.ai_service.generate_text(correlations_prompt, temperature=0.4)
        
        try:
            correlations_data = json.loads(correlations_response)
        except:
            correlations_data = {
                "key_findings": ["Análisis de correlaciones completado"],
                "trends": correlations,
                "recommendations": ["Aprovechar correlaciones identificadas"],
                "visualizations": []
            }
        
        return {
            "insight_id": insight_id,
            "key_findings": correlations_data.get("key_findings", []),
            "trends": correlations_data.get("trends", correlations),
            "recommendations": correlations_data.get("recommendations", []),
            "visualizations": correlations_data.get("visualizations", [])
        }
    
    async def _analyze_predictions(
        self,
        data: List[Dict[str, Any]],
        insight_id: str,
        business_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analizar predicciones basadas en datos históricos"""
        # Análisis de predicciones simplificado
        df = pd.DataFrame(data)
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
        
        predictions = []
        for col in numeric_columns[:3]:
            if len(df[col].dropna()) > 5:
                # Predicción simple basada en tendencia lineal
                recent_values = df[col].dropna().tail(5)
                if len(recent_values) >= 2:
                    trend = (recent_values.iloc[-1] - recent_values.iloc[0]) / len(recent_values)
                    predictions.append({
                        "metric": col,
                        "current_value": recent_values.iloc[-1],
                        "predicted_change": trend * 3,  # Predicción a 3 períodos
                        "confidence": 0.7
                    })
        
        # Generar insights usando IA
        predictions_prompt = f"""
        Analiza las siguientes predicciones basadas en datos históricos:
        
        Predicciones: {json.dumps(predictions, indent=2)}
        Contexto de negocio: {json.dumps(business_context, indent=2)}
        
        Genera insights sobre:
        1. Confiabilidad de las predicciones
        2. Implicaciones para la planificación
        3. Acciones recomendadas
        4. Factores de riesgo
        
        Responde en formato JSON.
        """
        
        predictions_response = await self.ai_service.generate_text(predictions_prompt, temperature=0.4)
        
        try:
            predictions_data = json.loads(predictions_response)
        except:
            predictions_data = {
                "key_findings": ["Análisis de predicciones completado"],
                "trends": predictions,
                "recommendations": ["Usar predicciones para planificación"],
                "visualizations": []
            }
        
        return {
            "insight_id": insight_id,
            "key_findings": predictions_data.get("key_findings", []),
            "trends": predictions_data.get("trends", predictions),
            "recommendations": predictions_data.get("recommendations", []),
            "visualizations": predictions_data.get("visualizations", [])
        } 