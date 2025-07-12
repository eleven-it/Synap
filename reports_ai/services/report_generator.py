"""
Servicio de generación de reportes usando IA
Genera reportes completos basados en datos y contexto
"""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from .ai_service import AIService

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generador de reportes usando IA"""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.template_prompts = self._load_template_prompts()
    
    def _load_template_prompts(self) -> Dict[str, str]:
        """Cargar prompts de templates"""
        return {
            "sales": """
            Genera un reporte de ventas ejecutivo que incluya:
            1. Resumen ejecutivo con KPIs principales
            2. Análisis de tendencias de ventas
            3. Productos más vendidos
            4. Análisis de clientes
            5. Recomendaciones estratégicas
            
            Contexto: {context}
            Datos disponibles: {data_sources}
            """,
            
            "financial": """
            Genera un reporte financiero que incluya:
            1. Resumen financiero ejecutivo
            2. Análisis de rentabilidad
            3. Flujo de caja
            4. Análisis de costos
            5. Proyecciones financieras
            
            Contexto: {context}
            Datos disponibles: {data_sources}
            """,
            
            "inventory": """
            Genera un reporte de inventario que incluya:
            1. Estado actual del inventario
            2. Análisis de rotación
            3. Productos con bajo stock
            4. Productos con exceso de inventario
            5. Recomendaciones de gestión
            
            Contexto: {context}
            Datos disponibles: {data_sources}
            """,
            
            "executive": """
            Genera un dashboard ejecutivo que incluya:
            1. KPIs principales del negocio
            2. Resumen de métricas clave
            3. Alertas y tendencias importantes
            4. Decisiones estratégicas recomendadas
            5. Próximos pasos
            
            Contexto: {context}
            Datos disponibles: {data_sources}
            """
        }
    
    async def generate_report(
        self,
        title: str,
        description: str,
        data_sources: List[str],
        template_type: str,
        company_context: Dict[str, Any],
        user_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generar reporte completo usando IA"""
        try:
            logger.info(f"Generando reporte: {title}")
            
            # Generar ID único
            report_id = str(uuid.uuid4())
            
            # Preparar contexto
            context = self._prepare_context(company_context, user_preferences)
            
            # Generar contenido del reporte
            content = await self._generate_report_content(
                title, description, data_sources, template_type, context
            )
            
            # Generar componentes
            components = await self._generate_components(
                content, template_type, data_sources
            )
            
            # Generar sugerencias
            suggestions = await self._generate_suggestions(content, template_type)
            
            # Calcular score de confianza
            confidence_score = self._calculate_confidence_score(content, components)
            
            return {
                "report_id": report_id,
                "title": title,
                "content": content,
                "components": components,
                "suggestions": suggestions,
                "confidence_score": confidence_score,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")
            raise
    
    def _prepare_context(self, company_context: Dict[str, Any], user_preferences: Dict[str, Any]) -> str:
        """Preparar contexto para la generación"""
        context_parts = []
        
        if company_context:
            context_parts.append(f"Empresa: {company_context.get('name', 'N/A')}")
            context_parts.append(f"Industria: {company_context.get('industry', 'N/A')}")
            context_parts.append(f"Tamaño: {company_context.get('size', 'N/A')}")
        
        if user_preferences:
            context_parts.append(f"Audiencia objetivo: {user_preferences.get('audience', 'General')}")
            context_parts.append(f"Tono preferido: {user_preferences.get('tone', 'Profesional')}")
            context_parts.append(f"Detalle requerido: {user_preferences.get('detail_level', 'Medio')}")
        
        return "\n".join(context_parts) if context_parts else "Sin contexto específico"
    
    async def _generate_report_content(
        self,
        title: str,
        description: str,
        data_sources: List[str],
        template_type: str,
        context: str
    ) -> Dict[str, Any]:
        """Generar contenido del reporte"""
        # Obtener prompt del template
        template_prompt = self.template_prompts.get(template_type, self.template_prompts["executive"])
        
        # Construir prompt completo
        full_prompt = f"""
        Título del reporte: {title}
        Descripción: {description}
        
        {template_prompt.format(context=context, data_sources=", ".join(data_sources))}
        
        Genera el contenido del reporte en formato JSON con la siguiente estructura:
        {{
            "executive_summary": "Resumen ejecutivo",
            "key_findings": ["Hallazgo 1", "Hallazgo 2", ...],
            "detailed_analysis": {{
                "section1": "Análisis detallado de la sección 1",
                "section2": "Análisis detallado de la sección 2",
                ...
            }},
            "recommendations": ["Recomendación 1", "Recomendación 2", ...],
            "next_steps": ["Paso 1", "Paso 2", ...],
            "metrics": {{
                "metric1": {{"value": "valor", "trend": "tendencia", "description": "descripción"}},
                ...
            }}
        }}
        """
        
        # Generar contenido usando IA
        content_text = await self.ai_service.generate_text(full_prompt, temperature=0.3)
        
        try:
            return json.loads(content_text)
        except json.JSONDecodeError:
            # Fallback si no se puede parsear JSON
            return {
                "executive_summary": content_text[:500] + "...",
                "key_findings": ["Análisis generado por IA"],
                "detailed_analysis": {"main": content_text},
                "recommendations": ["Revisar datos para recomendaciones específicas"],
                "next_steps": ["Validar análisis con datos reales"],
                "metrics": {}
            }
    
    async def _generate_components(
        self,
        content: Dict[str, Any],
        template_type: str,
        data_sources: List[str]
    ) -> List[Dict[str, Any]]:
        """Generar componentes visuales del reporte"""
        components = []
        
        # Componente de título
        components.append({
            "id": "title",
            "type": "header",
            "content": content.get("title", "Reporte"),
            "position": {"x": 0, "y": 0, "width": 800, "height": 60},
            "styling": {"fontSize": "24px", "fontWeight": "bold", "textAlign": "center"}
        })
        
        # Componente de resumen ejecutivo
        if "executive_summary" in content:
            components.append({
                "id": "executive_summary",
                "type": "text",
                "content": content["executive_summary"],
                "position": {"x": 0, "y": 80, "width": 800, "height": 120},
                "styling": {"fontSize": "14px", "lineHeight": "1.6"}
            })
        
        # Componentes de métricas
        if "metrics" in content:
            y_offset = 220
            for i, (metric_name, metric_data) in enumerate(content["metrics"].items()):
                components.append({
                    "id": f"metric_{i}",
                    "type": "kpi",
                    "content": {
                        "title": metric_name,
                        "value": metric_data.get("value", "N/A"),
                        "trend": metric_data.get("trend", "neutral"),
                        "description": metric_data.get("description", "")
                    },
                    "position": {"x": (i % 3) * 270, "y": y_offset, "width": 250, "height": 100},
                    "styling": {"backgroundColor": "#f8f9fa", "borderRadius": "8px", "padding": "16px"}
                })
                if (i + 1) % 3 == 0:
                    y_offset += 120
        
        # Componente de hallazgos clave
        if "key_findings" in content:
            findings_text = "\n• ".join(content["key_findings"])
            components.append({
                "id": "key_findings",
                "type": "list",
                "content": f"Hallazgos Clave:\n• {findings_text}",
                "position": {"x": 0, "y": y_offset + 20, "width": 400, "height": 150},
                "styling": {"fontSize": "14px", "backgroundColor": "#e3f2fd"}
            })
        
        # Componente de recomendaciones
        if "recommendations" in content:
            rec_text = "\n• ".join(content["recommendations"])
            components.append({
                "id": "recommendations",
                "type": "list",
                "content": f"Recomendaciones:\n• {rec_text}",
                "position": {"x": 420, "y": y_offset + 20, "width": 380, "height": 150},
                "styling": {"fontSize": "14px", "backgroundColor": "#f3e5f5"}
            })
        
        return components
    
    async def _generate_suggestions(self, content: Dict[str, Any], template_type: str) -> List[str]:
        """Generar sugerencias para mejorar el reporte"""
        suggestions = []
        
        # Analizar contenido y generar sugerencias
        if len(content.get("key_findings", [])) < 3:
            suggestions.append("Considerar agregar más hallazgos clave para mayor impacto")
        
        if len(content.get("recommendations", [])) < 2:
            suggestions.append("Incluir más recomendaciones específicas y accionables")
        
        if not content.get("metrics"):
            suggestions.append("Agregar métricas cuantitativas para mayor precisión")
        
        # Sugerencias específicas por tipo de template
        if template_type == "sales":
            suggestions.extend([
                "Incluir análisis de estacionalidad",
                "Agregar comparación con períodos anteriores",
                "Considerar análisis de segmentación de clientes"
            ])
        elif template_type == "financial":
            suggestions.extend([
                "Incluir análisis de ratios financieros",
                "Agregar proyecciones de flujo de caja",
                "Considerar análisis de sensibilidad"
            ])
        elif template_type == "inventory":
            suggestions.extend([
                "Incluir análisis de costos de almacenamiento",
                "Agregar recomendaciones de reabastecimiento",
                "Considerar análisis de obsolescencia"
            ])
        
        return suggestions[:5]  # Limitar a 5 sugerencias
    
    def _calculate_confidence_score(self, content: Dict[str, Any], components: List[Dict[str, Any]]) -> float:
        """Calcular score de confianza del reporte generado"""
        score = 0.5  # Score base
        
        # Factores que aumentan la confianza
        if content.get("executive_summary"):
            score += 0.1
        
        if len(content.get("key_findings", [])) >= 3:
            score += 0.1
        
        if len(content.get("recommendations", [])) >= 2:
            score += 0.1
        
        if content.get("metrics"):
            score += 0.1
        
        if len(components) >= 5:
            score += 0.1
        
        return min(score, 1.0)  # Máximo 1.0
    
    async def suggest_components(self, report_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Sugerir componentes para un reporte"""
        try:
            prompt = f"""
            Basándote en el siguiente contexto de reporte, sugiere componentes visuales apropiados:
            
            Contexto: {json.dumps(report_context, indent=2)}
            
            Para cada componente, especifica:
            - Tipo de componente (chart, table, kpi, text, image)
            - Propósito
            - Datos requeridos
            - Posición recomendada
            - Configuración sugerida
            
            Responde en formato JSON con una lista de componentes.
            """
            
            response = await self.ai_service.generate_text(prompt, temperature=0.4)
            
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return []
                
        except Exception as e:
            logger.error(f"Error sugiriendo componentes: {e}")
            return []
    
    async def enhance_report(self, existing_report: Dict[str, Any], enhancement_type: str) -> Dict[str, Any]:
        """Mejorar un reporte existente"""
        try:
            if enhancement_type == "content":
                return await self._enhance_content(existing_report)
            elif enhancement_type == "design":
                return await self._enhance_design(existing_report)
            elif enhancement_type == "insights":
                return await self._enhance_insights(existing_report)
            else:
                raise ValueError(f"Tipo de mejora no válido: {enhancement_type}")
                
        except Exception as e:
            logger.error(f"Error mejorando reporte: {e}")
            raise
    
    async def _enhance_content(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Mejorar el contenido del reporte"""
        content = report.get("content", {})
        
        # Mejorar resumen ejecutivo
        if "executive_summary" in content:
            enhanced_summary = await self.ai_service.improve_text(
                content["executive_summary"], "executive"
            )
            content["executive_summary"] = enhanced_summary
        
        # Mejorar recomendaciones
        if "recommendations" in content:
            enhanced_recommendations = []
            for rec in content["recommendations"]:
                enhanced_rec = await self.ai_service.improve_text(rec, "general")
                enhanced_recommendations.append(enhanced_rec)
            content["recommendations"] = enhanced_recommendations
        
        report["content"] = content
        return report
    
    async def _enhance_design(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Mejorar el diseño del reporte"""
        # Implementar mejoras de diseño
        return report
    
    async def _enhance_insights(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Mejorar los insights del reporte"""
        content = report.get("content", {})
        
        # Generar insights adicionales
        if "key_findings" in content:
            additional_insights = await self.ai_service.generate_insights(
                [{"findings": content["key_findings"]}],
                "Análisis de hallazgos clave del reporte"
            )
            content["additional_insights"] = additional_insights
        
        report["content"] = content
        return report 