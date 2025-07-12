"""
Servicio principal de IA para el módulo de reportes
Maneja las interacciones con OpenAI, Anthropic y otros proveedores de IA
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import json
import openai
import anthropic
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from config import settings

logger = logging.getLogger(__name__)

class AIService:
    """Servicio principal de IA"""
    
    def __init__(self, vector_store=None):
        self.vector_store = vector_store
        self.openai_client = None
        self.anthropic_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Inicializar clientes de IA"""
        try:
            if settings.OPENAI_API_KEY:
                self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("Cliente OpenAI inicializado")
            
            if settings.ANTHROPIC_API_KEY:
                self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                logger.info("Cliente Anthropic inicializado")
                
        except Exception as e:
            logger.error(f"Error inicializando clientes de IA: {e}")
    
    async def generate_text(self, prompt: str, model: str = "openai", **kwargs) -> str:
        """Generar texto usando IA"""
        try:
            if model == "openai" and self.openai_client:
                return await self._generate_openai_text(prompt, **kwargs)
            elif model == "anthropic" and self.anthropic_client:
                return await self._generate_anthropic_text(prompt, **kwargs)
            else:
                raise ValueError(f"Modelo {model} no disponible")
                
        except Exception as e:
            logger.error(f"Error generando texto: {e}")
            raise
    
    async def _generate_openai_text(self, prompt: str, **kwargs) -> str:
        """Generar texto usando OpenAI"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", 2000),
                temperature=kwargs.get("temperature", 0.7),
                **kwargs
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error con OpenAI: {e}")
            raise
    
    async def _generate_anthropic_text(self, prompt: str, **kwargs) -> str:
        """Generar texto usando Anthropic"""
        try:
            response = await self.anthropic_client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=kwargs.get("max_tokens", 2000),
                temperature=kwargs.get("temperature", 0.7),
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error con Anthropic: {e}")
            raise
    
    async def improve_text(self, text: str, improvement_type: str = "general") -> str:
        """Mejorar texto usando IA"""
        prompts = {
            "general": f"Mejora el siguiente texto manteniendo su significado pero haciéndolo más claro y profesional:\n\n{text}",
            "executive": f"Reescribe el siguiente texto para una audiencia ejecutiva, usando un tono profesional y conciso:\n\n{text}",
            "technical": f"Mejora el siguiente texto para una audiencia técnica, agregando precisión y claridad:\n\n{text}",
            "creative": f"Reescribe el siguiente texto de manera más creativa y atractiva:\n\n{text}"
        }
        
        prompt = prompts.get(improvement_type, prompts["general"])
        return await self.generate_text(prompt, temperature=0.3)
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analizar sentimiento del texto"""
        prompt = f"""
        Analiza el sentimiento del siguiente texto y proporciona:
        1. Sentimiento general (positivo, negativo, neutro)
        2. Puntuación de confianza (0-1)
        3. Palabras clave que influyen en el sentimiento
        4. Sugerencias de mejora si es necesario
        
        Texto: {text}
        
        Responde en formato JSON.
        """
        
        response = await self.generate_text(prompt, temperature=0.1)
        try:
            return json.loads(response)
        except:
            return {
                "sentiment": "neutral",
                "confidence": 0.5,
                "keywords": [],
                "suggestions": []
            }
    
    async def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extraer palabras clave del texto"""
        prompt = f"""
        Extrae las {max_keywords} palabras clave más importantes del siguiente texto:
        
        {text}
        
        Responde solo con las palabras clave separadas por comas.
        """
        
        response = await self.generate_text(prompt, temperature=0.1)
        return [kw.strip() for kw in response.split(",") if kw.strip()]
    
    async def summarize_text(self, text: str, max_length: int = 200) -> str:
        """Resumir texto"""
        prompt = f"""
        Resume el siguiente texto en máximo {max_length} caracteres, manteniendo los puntos más importantes:
        
        {text}
        """
        
        return await self.generate_text(prompt, temperature=0.3)
    
    async def generate_insights(self, data: List[Dict[str, Any]], context: str = "") -> List[str]:
        """Generar insights a partir de datos"""
        data_str = json.dumps(data, indent=2)
        prompt = f"""
        Analiza los siguientes datos y genera 5 insights valiosos para el negocio:
        
        Contexto: {context}
        Datos: {data_str}
        
        Genera insights específicos, accionables y relevantes para el contexto de negocio.
        """
        
        response = await self.generate_text(prompt, temperature=0.4)
        return [insight.strip() for insight in response.split("\n") if insight.strip()]
    
    async def suggest_visualizations(self, data: List[Dict[str, Any]], report_type: str) -> List[Dict[str, Any]]:
        """Sugerir visualizaciones para los datos"""
        data_str = json.dumps(data[:5], indent=2)  # Solo primeros 5 registros para el prompt
        
        prompt = f"""
        Para un reporte de tipo "{report_type}", sugiere visualizaciones apropiadas para estos datos:
        
        {data_str}
        
        Para cada visualización, especifica:
        - Tipo de gráfico
        - Variables a usar
        - Justificación
        - Configuración recomendada
        
        Responde en formato JSON con una lista de visualizaciones.
        """
        
        response = await self.generate_text(prompt, temperature=0.3)
        try:
            return json.loads(response)
        except:
            return []
    
    async def optimize_content(self, content: str, target_audience: str, goals: List[str]) -> str:
        """Optimizar contenido para una audiencia específica"""
        goals_str = ", ".join(goals)
        prompt = f"""
        Optimiza el siguiente contenido para una audiencia de {target_audience} con los siguientes objetivos: {goals_str}
        
        Contenido original: {content}
        
        Proporciona una versión optimizada que sea más efectiva para esta audiencia y objetivos.
        """
        
        return await self.generate_text(prompt, temperature=0.4)
    
    async def generate_recommendations(self, context: Dict[str, Any]) -> List[str]:
        """Generar recomendaciones basadas en contexto"""
        context_str = json.dumps(context, indent=2)
        prompt = f"""
        Basándote en el siguiente contexto, genera 5 recomendaciones específicas y accionables:
        
        Contexto: {context_str}
        
        Las recomendaciones deben ser:
        - Específicas y medibles
        - Accionables
        - Relevantes para el contexto
        - Priorizadas por impacto
        """
        
        response = await self.generate_text(prompt, temperature=0.3)
        return [rec.strip() for rec in response.split("\n") if rec.strip()]
    
    async def validate_data_quality(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validar calidad de datos"""
        data_str = json.dumps(data[:10], indent=2)  # Solo primeros 10 registros
        
        prompt = f"""
        Analiza la calidad de los siguientes datos y proporciona un reporte de validación:
        
        {data_str}
        
        Incluye:
        - Completitud de datos
        - Consistencia
        - Valores atípicos
        - Problemas identificados
        - Recomendaciones de mejora
        
        Responde en formato JSON.
        """
        
        response = await self.generate_text(prompt, temperature=0.1)
        try:
            return json.loads(response)
        except:
            return {
                "completeness": 0.8,
                "consistency": 0.7,
                "outliers": [],
                "issues": [],
                "recommendations": []
            } 