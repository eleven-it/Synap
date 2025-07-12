#!/usr/bin/env python3
"""
Script de prueba para verificar la integración con el microservicio de IA
"""

import asyncio
import json
import httpx
import logging
from typing import Dict, Any

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIIntegrationTester:
    """Tester para la integración con el microservicio de IA"""
    
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_health_endpoints(self) -> bool:
        """Probar endpoints de salud"""
        logger.info("Probando endpoints de salud...")
        
        try:
            # Test health básico
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                logger.info("✅ Health endpoint funcionando")
            else:
                logger.error(f"❌ Health endpoint falló: {response.status_code}")
                return False
            
            # Test health detallado
            response = await self.client.get(f"{self.base_url}/health/detailed")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Health detallado: {data.get('status')}")
                logger.info(f"   Servicios: {data.get('services', {})}")
            else:
                logger.error(f"❌ Health detallado falló: {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error probando health endpoints: {e}")
            return False
    
    async def test_report_generation(self) -> bool:
        """Probar generación de reportes"""
        logger.info("Probando generación de reportes...")
        
        try:
            # Datos de prueba
            test_data = {
                "title": "Reporte de Ventas Mensual",
                "description": "Análisis completo de ventas del mes de enero",
                "data_sources": ["sales_data", "customer_data", "product_data"],
                "template_type": "sales",
                "company_context": {
                    "name": "Empresa Test",
                    "industry": "Retail",
                    "size": "Medium"
                },
                "user_preferences": {
                    "audience": "executive",
                    "tone": "professional",
                    "detail_level": "high"
                }
            }
            
            # Simular token de autenticación
            headers = {"Authorization": "Bearer test-token"}
            
            response = await self.client.post(
                f"{self.base_url}/ai/generate-report",
                json=test_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Generación de reporte exitosa")
                logger.info(f"   Report ID: {data.get('report_id')}")
                logger.info(f"   Confidence Score: {data.get('confidence_score')}")
                return True
            else:
                logger.error(f"❌ Generación de reporte falló: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error probando generación de reportes: {e}")
            return False
    
    async def test_content_analysis(self) -> bool:
        """Probar análisis de contenido"""
        logger.info("Probando análisis de contenido...")
        
        try:
            test_data = {
                "content": "Este es un reporte excelente que muestra un crecimiento significativo en las ventas del último trimestre. Los resultados superan las expectativas y demuestran la efectividad de nuestras estrategias de marketing.",
                "analysis_type": "comprehensive",
                "context": {
                    "report_type": "sales",
                    "audience": "executive"
                }
            }
            
            headers = {"Authorization": "Bearer test-token"}
            
            response = await self.client.post(
                f"{self.base_url}/ai/analyze-content",
                json=test_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Análisis de contenido exitoso")
                logger.info(f"   Sentiment Score: {data.get('sentiment_score')}")
                logger.info(f"   Readability Score: {data.get('readability_score')}")
                return True
            else:
                logger.error(f"❌ Análisis de contenido falló: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error probando análisis de contenido: {e}")
            return False
    
    async def test_design_optimization(self) -> bool:
        """Probar optimización de diseño"""
        logger.info("Probando optimización de diseño...")
        
        try:
            test_data = {
                "current_layout": {
                    "components": [
                        {
                            "id": "title",
                            "type": "header",
                            "content": "Reporte de Ventas",
                            "position": {"x": 0, "y": 0, "width": 800, "height": 60},
                            "styling": {"fontSize": "24px", "fontWeight": "bold"}
                        }
                    ]
                },
                "target_audience": "executive",
                "brand_guidelines": {
                    "primary_color": "#007bff",
                    "secondary_color": "#6c757d",
                    "font_family": "Arial, sans-serif"
                }
            }
            
            headers = {"Authorization": "Bearer test-token"}
            
            response = await self.client.post(
                f"{self.base_url}/ai/optimize-design",
                json=test_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Optimización de diseño exitosa")
                logger.info(f"   Accessibility Score: {data.get('accessibility_score')}")
                return True
            else:
                logger.error(f"❌ Optimización de diseño falló: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error probando optimización de diseño: {e}")
            return False
    
    async def test_data_insights(self) -> bool:
        """Probar insights de datos"""
        logger.info("Probando insights de datos...")
        
        try:
            test_data = {
                "data": [
                    {"month": "Jan", "sales": 1000, "customers": 50},
                    {"month": "Feb", "sales": 1200, "customers": 60},
                    {"month": "Mar", "sales": 1100, "customers": 55},
                    {"month": "Apr", "sales": 1400, "customers": 70},
                    {"month": "May", "sales": 1600, "customers": 80}
                ],
                "insight_type": "trends",
                "business_context": {
                    "industry": "retail",
                    "business_type": "ecommerce"
                }
            }
            
            headers = {"Authorization": "Bearer test-token"}
            
            response = await self.client.post(
                f"{self.base_url}/ai/data-insights",
                json=test_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Insights de datos exitosos")
                logger.info(f"   Key Findings: {len(data.get('key_findings', []))}")
                return True
            else:
                logger.error(f"❌ Insights de datos fallaron: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error probando insights de datos: {e}")
            return False
    
    async def test_text_improvement(self) -> bool:
        """Probar mejora de texto"""
        logger.info("Probando mejora de texto...")
        
        try:
            test_text = "Las ventas subieron mucho este mes comparado con el mes pasado."
            improvement_type = "executive"
            
            headers = {"Authorization": "Bearer test-token"}
            
            response = await self.client.post(
                f"{self.base_url}/ai/improve-text",
                params={"text": test_text, "improvement_type": improvement_type},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Mejora de texto exitosa")
                logger.info(f"   Texto original: {data.get('original_text')}")
                logger.info(f"   Texto mejorado: {data.get('improved_text')}")
                return True
            else:
                logger.error(f"❌ Mejora de texto falló: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error probando mejora de texto: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Ejecutar todas las pruebas"""
        logger.info("🚀 Iniciando pruebas de integración con IA...")
        
        results = {}
        
        # Ejecutar pruebas
        results["health"] = await self.test_health_endpoints()
        results["report_generation"] = await self.test_report_generation()
        results["content_analysis"] = await self.test_content_analysis()
        results["design_optimization"] = await self.test_design_optimization()
        results["data_insights"] = await self.test_data_insights()
        results["text_improvement"] = await self.test_text_improvement()
        
        # Resumen
        passed = sum(results.values())
        total = len(results)
        
        logger.info(f"\n📊 Resumen de pruebas:")
        logger.info(f"   ✅ Exitosas: {passed}/{total}")
        logger.info(f"   ❌ Fallidas: {total - passed}/{total}")
        
        for test_name, result in results.items():
            status = "✅" if result else "❌"
            logger.info(f"   {status} {test_name}")
        
        return results
    
    async def close(self):
        """Cerrar cliente HTTP"""
        await self.client.aclose()

async def main():
    """Función principal"""
    tester = AIIntegrationTester()
    
    try:
        results = await tester.run_all_tests()
        
        # Verificar si todas las pruebas pasaron
        all_passed = all(results.values())
        
        if all_passed:
            logger.info("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
            return 0
        else:
            logger.error("\n💥 Algunas pruebas fallaron")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error ejecutando pruebas: {e}")
        return 1
    finally:
        await tester.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 