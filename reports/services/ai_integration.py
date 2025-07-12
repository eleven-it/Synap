"""
Servicio de integración con el microservicio de IA para reportes
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class AIReportsService:
    """Servicio de integración con el microservicio de IA"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'REPORTS_AI_URL', 'http://localhost:8003')
        self.timeout = getattr(settings, 'REPORTS_AI_TIMEOUT', 30)
        self.enabled = getattr(settings, 'REPORTS_AI_ENABLED', True)
    
    def _get_auth_headers(self, user) -> Dict[str, str]:
        """Generar headers de autenticación"""
        # En un entorno real, generar token JWT
        return {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json"
        }
    
    def _get_cache_key(self, operation: str, params: Dict[str, Any]) -> str:
        """Generar clave de cache"""
        params_str = json.dumps(params, sort_keys=True)
        return f"ai_reports:{operation}:{hash(params_str)}"
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        user=None
    ) -> Dict[str, Any]:
        """Realizar request al microservicio de IA"""
        if not self.enabled:
            logger.warning("Servicio de IA deshabilitado")
            return {"error": "AI service disabled"}
        
        url = f"{self.base_url}{endpoint}"
        headers = self._get_auth_headers(user)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, params=params, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data, headers=headers)
                else:
                    raise ValueError(f"Método no soportado: {method}")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.TimeoutException:
            logger.error(f"Timeout en request a IA: {endpoint}")
            return {"error": "Request timeout"}
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP en request a IA: {e.response.status_code}")
            return {"error": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Error en request a IA: {e}")
            return {"error": str(e)}
    
    async def generate_report(
        self,
        title: str,
        description: str,
        data_sources: List[str],
        template_type: str,
        company_context: Dict[str, Any],
        user_preferences: Dict[str, Any],
        user=None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Generar reporte usando IA"""
        try:
            # Preparar datos
            request_data = {
                "title": title,
                "description": description,
                "data_sources": data_sources,
                "template_type": template_type,
                "company_context": company_context,
                "user_preferences": user_preferences
            }
            
            # Verificar cache
            if use_cache:
                cache_key = self._get_cache_key("generate_report", request_data)
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.info("Usando resultado cacheado de generación de reporte")
                    return cached_result
            
            # Realizar request
            result = await self._make_request(
                method="POST",
                endpoint="/ai/generate-report",
                data=request_data,
                user=user
            )
            
            # Guardar en cache si fue exitoso
            if use_cache and "error" not in result:
                cache.set(cache_key, result, timeout=3600)  # 1 hora
            
            return result
            
        except Exception as e:
            logger.error(f"Error generando reporte con IA: {e}")
            return {"error": str(e)}
    
    async def analyze_content(
        self,
        content: str,
        analysis_type: str = "comprehensive",
        context: Dict[str, Any] = None,
        user=None
    ) -> Dict[str, Any]:
        """Analizar contenido usando IA"""
        try:
            request_data = {
                "content": content,
                "analysis_type": analysis_type,
                "context": context or {}
            }
            
            return await self._make_request(
                method="POST",
                endpoint="/ai/analyze-content",
                data=request_data,
                user=user
            )
            
        except Exception as e:
            logger.error(f"Error analizando contenido con IA: {e}")
            return {"error": str(e)}
    
    async def optimize_design(
        self,
        current_layout: Dict[str, Any],
        target_audience: str,
        brand_guidelines: Dict[str, Any],
        user=None
    ) -> Dict[str, Any]:
        """Optimizar diseño usando IA"""
        try:
            request_data = {
                "current_layout": current_layout,
                "target_audience": target_audience,
                "brand_guidelines": brand_guidelines
            }
            
            return await self._make_request(
                method="POST",
                endpoint="/ai/optimize-design",
                data=request_data,
                user=user
            )
            
        except Exception as e:
            logger.error(f"Error optimizando diseño con IA: {e}")
            return {"error": str(e)}
    
    async def get_data_insights(
        self,
        data: List[Dict[str, Any]],
        insight_type: str,
        business_context: Dict[str, Any],
        user=None
    ) -> Dict[str, Any]:
        """Obtener insights de datos usando IA"""
        try:
            request_data = {
                "data": data,
                "insight_type": insight_type,
                "business_context": business_context
            }
            
            return await self._make_request(
                method="POST",
                endpoint="/ai/data-insights",
                data=request_data,
                user=user
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo insights con IA: {e}")
            return {"error": str(e)}
    
    async def improve_text(
        self,
        text: str,
        improvement_type: str = "general",
        user=None
    ) -> Dict[str, Any]:
        """Mejorar texto usando IA"""
        try:
            params = {
                "text": text,
                "improvement_type": improvement_type
            }
            
            return await self._make_request(
                method="POST",
                endpoint="/ai/improve-text",
                params=params,
                user=user
            )
            
        except Exception as e:
            logger.error(f"Error mejorando texto con IA: {e}")
            return {"error": str(e)}
    
    async def suggest_components(
        self,
        report_context: Dict[str, Any],
        user=None
    ) -> Dict[str, Any]:
        """Sugerir componentes para reporte"""
        try:
            return await self._make_request(
                method="POST",
                endpoint="/ai/suggest-components",
                data=report_context,
                user=user
            )
            
        except Exception as e:
            logger.error(f"Error sugiriendo componentes con IA: {e}")
            return {"error": str(e)}
    
    async def check_health(self) -> Dict[str, Any]:
        """Verificar salud del microservicio de IA"""
        try:
            return await self._make_request(
                method="GET",
                endpoint="/health/detailed"
            )
        except Exception as e:
            logger.error(f"Error verificando salud del servicio de IA: {e}")
            return {"error": str(e)}
    
    def sync_generate_report(self, *args, **kwargs) -> Dict[str, Any]:
        """Versión síncrona de generate_report"""
        return asyncio.run(self.generate_report(*args, **kwargs))
    
    def sync_analyze_content(self, *args, **kwargs) -> Dict[str, Any]:
        """Versión síncrona de analyze_content"""
        return asyncio.run(self.analyze_content(*args, **kwargs))
    
    def sync_optimize_design(self, *args, **kwargs) -> Dict[str, Any]:
        """Versión síncrona de optimize_design"""
        return asyncio.run(self.optimize_design(*args, **kwargs))
    
    def sync_get_data_insights(self, *args, **kwargs) -> Dict[str, Any]:
        """Versión síncrona de get_data_insights"""
        return asyncio.run(self.get_data_insights(*args, **kwargs))
    
    def sync_improve_text(self, *args, **kwargs) -> Dict[str, Any]:
        """Versión síncrona de improve_text"""
        return asyncio.run(self.improve_text(*args, **kwargs))

    # Métodos de exportación
    async def export_to_pdf(
        self,
        report_data: Dict[str, Any],
        branding: Dict[str, Any],
        optimize_for_executive: bool = True,
        user=None
    ) -> Dict[str, Any]:
        """Exportar reporte a PDF con branding institucional"""
        try:
            request_data = {
                "report_data": report_data,
                "export_format": "pdf",
                "branding": branding,
                "optimize_for_executive": optimize_for_executive
            }
            
            return await self._make_request(
                method="POST",
                endpoint="/export/pdf",
                data=request_data,
                user=user
            )
            
        except Exception as e:
            logger.error(f"Error exportando a PDF: {e}")
            return {"error": str(e)}
    
    async def export_to_pptx(
        self,
        report_data: Dict[str, Any],
        branding: Dict[str, Any],
        optimize_for_executive: bool = True,
        user=None
    ) -> Dict[str, Any]:
        """Exportar reporte a PPTX con branding institucional"""
        try:
            request_data = {
                "report_data": report_data,
                "export_format": "pptx",
                "branding": branding,
                "optimize_for_executive": optimize_for_executive
            }
            
            return await self._make_request(
                method="POST",
                endpoint="/export/pptx",
                data=request_data,
                user=user
            )
            
        except Exception as e:
            logger.error(f"Error exportando a PPTX: {e}")
            return {"error": str(e)}
    
    async def generate_branding_guidelines(
        self,
        company_data: Dict[str, Any],
        report_type: str,
        target_audience: str = "executive",
        user=None
    ) -> Dict[str, Any]:
        """Generar guías de branding usando IA"""
        try:
            request_data = {
                "company_data": company_data,
                "report_type": report_type,
                "target_audience": target_audience
            }
            
            return await self._make_request(
                method="POST",
                endpoint="/export/generate-branding",
                data=request_data,
                user=user
            )
            
        except Exception as e:
            logger.error(f"Error generando branding: {e}")
            return {"error": str(e)}
    
    async def optimize_for_executive_audience(
        self,
        report_data: Dict[str, Any],
        branding: Dict[str, Any] = {},
        user=None
    ) -> Dict[str, Any]:
        """Optimizar contenido para audiencia ejecutiva"""
        try:
            request_data = {
                "report_data": report_data,
                "branding": branding
            }
            
            return await self._make_request(
                method="POST",
                endpoint="/export/optimize-for-executive",
                data=request_data,
                user=user
            )
            
        except Exception as e:
            logger.error(f"Error optimizando para audiencia ejecutiva: {e}")
            return {"error": str(e)}
    
    # Versiones síncronas de exportación
    def sync_export_to_pdf(self, *args, **kwargs) -> Dict[str, Any]:
        """Versión síncrona de export_to_pdf"""
        return asyncio.run(self.export_to_pdf(*args, **kwargs))
    
    def sync_export_to_pptx(self, *args, **kwargs) -> Dict[str, Any]:
        """Versión síncrona de export_to_pptx"""
        return asyncio.run(self.export_to_pptx(*args, **kwargs))
    
    def sync_generate_branding_guidelines(self, *args, **kwargs) -> Dict[str, Any]:
        """Versión síncrona de generate_branding_guidelines"""
        return asyncio.run(self.generate_branding_guidelines(*args, **kwargs))
    
    def sync_optimize_for_executive_audience(self, *args, **kwargs) -> Dict[str, Any]:
        """Versión síncrona de optimize_for_executive_audience"""
        return asyncio.run(self.optimize_for_executive_audience(*args, **kwargs))

# Instancia global del servicio
ai_service = AIReportsService() 