"""
Servicio de optimización de diseño usando IA
Optimiza la presentación visual y la experiencia de usuario de los reportes
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .ai_service import AIService

logger = logging.getLogger(__name__)

class DesignOptimizer:
    """Optimizador de diseño usando IA"""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
    
    async def optimize_layout(
        self,
        current_layout: Dict[str, Any],
        target_audience: str,
        brand_guidelines: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimizar layout del reporte"""
        try:
            logger.info(f"Optimizando layout para audiencia: {target_audience}")
            
            optimization_id = f"optimization_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # Analizar layout actual
            layout_analysis = await self._analyze_current_layout(current_layout)
            
            # Generar mejoras
            improvements = await self._generate_improvements(
                layout_analysis, target_audience, brand_guidelines
            )
            
            # Aplicar optimizaciones
            improved_layout = await self._apply_optimizations(
                current_layout, improvements
            )
            
            # Calcular score de accesibilidad
            accessibility_score = self._calculate_accessibility_score(improved_layout)
            
            return {
                "optimization_id": optimization_id,
                "improved_layout": improved_layout,
                "suggestions": improvements.get("suggestions", []),
                "visual_hierarchy": improvements.get("visual_hierarchy", {}),
                "accessibility_score": accessibility_score
            }
            
        except Exception as e:
            logger.error(f"Error optimizando layout: {e}")
            raise
    
    async def _analyze_current_layout(self, layout: Dict[str, Any]) -> Dict[str, Any]:
        """Analizar layout actual"""
        layout_str = json.dumps(layout, indent=2)
        
        prompt = f"""
        Analiza el siguiente layout de reporte:
        
        {layout_str}
        
        Evalúa:
        1. Jerarquía visual
        2. Balance de elementos
        3. Uso del espacio
        4. Consistencia de diseño
        5. Legibilidad
        
        Proporciona un análisis detallado en formato JSON.
        """
        
        analysis = await self.ai_service.generate_text(prompt, temperature=0.2)
        
        try:
            return json.loads(analysis)
        except:
            return {
                "visual_hierarchy": "moderate",
                "balance": "good",
                "space_usage": "efficient",
                "consistency": "consistent",
                "readability": "good"
            }
    
    async def _generate_improvements(
        self,
        layout_analysis: Dict[str, Any],
        target_audience: str,
        brand_guidelines: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generar mejoras de diseño"""
        analysis_str = json.dumps(layout_analysis, indent=2)
        guidelines_str = json.dumps(brand_guidelines, indent=2)
        
        prompt = f"""
        Basándote en el análisis del layout actual y las guías de marca, genera mejoras de diseño:
        
        Análisis actual: {analysis_str}
        Audiencia objetivo: {target_audience}
        Guías de marca: {guidelines_str}
        
        Genera:
        1. Sugerencias específicas de mejora
        2. Jerarquía visual optimizada
        3. Recomendaciones de color y tipografía
        4. Mejoras de accesibilidad
        
        Responde en formato JSON con suggestions, visual_hierarchy, color_recommendations y accessibility_improvements.
        """
        
        improvements = await self.ai_service.generate_text(prompt, temperature=0.4)
        
        try:
            return json.loads(improvements)
        except:
            return {
                "suggestions": [
                    "Mejorar contraste de colores",
                    "Optimizar espaciado entre elementos",
                    "Reforzar jerarquía visual"
                ],
                "visual_hierarchy": {
                    "primary": "títulos principales",
                    "secondary": "subtítulos",
                    "tertiary": "contenido"
                },
                "color_recommendations": {
                    "primary": "#007bff",
                    "secondary": "#6c757d",
                    "accent": "#28a745"
                },
                "accessibility_improvements": [
                    "Aumentar contraste",
                    "Mejorar tamaño de fuente",
                    "Agregar alt text a imágenes"
                ]
            }
    
    async def _apply_optimizations(
        self,
        current_layout: Dict[str, Any],
        improvements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aplicar optimizaciones al layout"""
        improved_layout = current_layout.copy()
        
        # Aplicar mejoras de color
        if "color_recommendations" in improvements:
            improved_layout["colors"] = improvements["color_recommendations"]
        
        # Aplicar mejoras de tipografía
        if "typography_recommendations" in improvements:
            improved_layout["typography"] = improvements["typography_recommendations"]
        
        # Aplicar mejoras de espaciado
        if "spacing_recommendations" in improvements:
            improved_layout["spacing"] = improvements["spacing_recommendations"]
        
        # Aplicar mejoras de componentes
        if "components" in improved_layout:
            for component in improved_layout["components"]:
                component = await self._optimize_component(component, improvements)
        
        return improved_layout
    
    async def _optimize_component(
        self,
        component: Dict[str, Any],
        improvements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimizar componente individual"""
        optimized_component = component.copy()
        
        # Aplicar mejoras de estilo
        if "styling" not in optimized_component:
            optimized_component["styling"] = {}
        
        # Mejorar contraste si es necesario
        if "backgroundColor" in optimized_component["styling"]:
            optimized_component["styling"]["backgroundColor"] = self._improve_contrast(
                optimized_component["styling"]["backgroundColor"]
            )
        
        # Mejorar tipografía
        if "fontSize" in optimized_component["styling"]:
            current_size = optimized_component["styling"]["fontSize"]
            optimized_component["styling"]["fontSize"] = self._optimize_font_size(current_size)
        
        return optimized_component
    
    def _improve_contrast(self, color: str) -> str:
        """Mejorar contraste de color"""
        # Implementación simplificada
        if color == "#ffffff":  # Blanco
            return "#f8f9fa"  # Gris muy claro
        elif color == "#000000":  # Negro
            return "#212529"  # Gris muy oscuro
        else:
            return color
    
    def _optimize_font_size(self, current_size: str) -> str:
        """Optimizar tamaño de fuente"""
        # Implementación simplificada
        if "px" in current_size:
            size = int(current_size.replace("px", ""))
            if size < 12:
                return "14px"
            elif size > 24:
                return "20px"
        
        return current_size
    
    def _calculate_accessibility_score(self, layout: Dict[str, Any]) -> float:
        """Calcular score de accesibilidad"""
        score = 0.5  # Score base
        
        # Factores que mejoran la accesibilidad
        if "colors" in layout:
            score += 0.1
        
        if "typography" in layout:
            score += 0.1
        
        if "spacing" in layout:
            score += 0.1
        
        if "components" in layout:
            for component in layout["components"]:
                if "styling" in component:
                    styling = component["styling"]
                    if "fontSize" in styling and "px" in styling["fontSize"]:
                        size = int(styling["fontSize"].replace("px", ""))
                        if size >= 14:
                            score += 0.05
                    
                    if "backgroundColor" in styling and "color" in styling:
                        score += 0.05
        
        return min(score, 1.0)  # Máximo 1.0
    
    async def suggest_color_scheme(
        self,
        brand_colors: List[str],
        report_type: str,
        target_audience: str
    ) -> Dict[str, Any]:
        """Sugerir esquema de colores"""
        try:
            prompt = f"""
            Sugiere un esquema de colores para un reporte de tipo "{report_type}" dirigido a una audiencia de "{target_audience}".
            
            Colores de marca disponibles: {', '.join(brand_colors)}
            
            Genera un esquema que incluya:
            1. Color primario
            2. Color secundario
            3. Color de acento
            4. Colores neutros
            5. Justificación de las elecciones
            
            Responde en formato JSON.
            """
            
            response = await self.ai_service.generate_text(prompt, temperature=0.3)
            
            try:
                return json.loads(response)
            except:
                return {
                    "primary": "#007bff",
                    "secondary": "#6c757d",
                    "accent": "#28a745",
                    "neutral": ["#f8f9fa", "#e9ecef", "#dee2e6"],
                    "justification": "Esquema profesional y accesible"
                }
                
        except Exception as e:
            logger.error(f"Error sugiriendo esquema de colores: {e}")
            return {}
    
    async def optimize_for_mobile(self, layout: Dict[str, Any]) -> Dict[str, Any]:
        """Optimizar layout para dispositivos móviles"""
        try:
            layout_str = json.dumps(layout, indent=2)
            
            prompt = f"""
            Optimiza el siguiente layout para dispositivos móviles:
            
            {layout_str}
            
            Considera:
            1. Responsive design
            2. Tamaños de pantalla pequeños
            3. Navegación táctil
            4. Carga rápida
            5. Legibilidad en pantallas pequeñas
            
            Proporciona un layout optimizado en formato JSON.
            """
            
            response = await self.ai_service.generate_text(prompt, temperature=0.3)
            
            try:
                return json.loads(response)
            except:
                return layout
                
        except Exception as e:
            logger.error(f"Error optimizando para móvil: {e}")
            return layout
    
    async def generate_visual_hierarchy(
        self,
        content_structure: Dict[str, Any],
        target_audience: str
    ) -> Dict[str, Any]:
        """Generar jerarquía visual optimizada"""
        try:
            structure_str = json.dumps(content_structure, indent=2)
            
            prompt = f"""
            Genera una jerarquía visual optimizada para el siguiente contenido:
            
            Estructura: {structure_str}
            Audiencia objetivo: {target_audience}
            
            Define:
            1. Niveles de importancia
            2. Tamaños de fuente
            3. Espaciado
            4. Colores por nivel
            5. Elementos de énfasis
            
            Responde en formato JSON.
            """
            
            response = await self.ai_service.generate_text(prompt, temperature=0.3)
            
            try:
                return json.loads(response)
            except:
                return {
                    "levels": {
                        "h1": {"fontSize": "24px", "fontWeight": "bold", "color": "#000000"},
                        "h2": {"fontSize": "20px", "fontWeight": "bold", "color": "#333333"},
                        "h3": {"fontSize": "16px", "fontWeight": "600", "color": "#666666"},
                        "body": {"fontSize": "14px", "fontWeight": "normal", "color": "#333333"}
                    },
                    "spacing": {
                        "section": "32px",
                        "subsection": "24px",
                        "element": "16px"
                    }
                }
                
        except Exception as e:
            logger.error(f"Error generando jerarquía visual: {e}")
            return {} 