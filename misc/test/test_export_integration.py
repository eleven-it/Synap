#!/usr/bin/env python3
"""
Script de prueba para verificar la integración de exportación avanzada
"""

import asyncio
import json
import httpx
import logging
import base64
from typing import Dict, Any

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExportIntegrationTester:
    """Tester para la integración de exportación avanzada"""
    
    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)  # Timeout más largo para exportación
    
    async def test_branding_generation(self) -> bool:
        """Probar generación de branding"""
        logger.info("Probando generación de branding...")
        
        try:
            test_data = {
                "company_data": {
                    "name": "TechCorp Solutions",
                    "industry": "Technology",
                    "size": "Medium",
                    "primary_color": "#2563eb",
                    "secondary_color": "#64748b"
                },
                "report_type": "financial",
                "target_audience": "executive"
            }
            
            headers = {"Authorization": "Bearer test-token"}
            
            response = await self.client.post(
                f"{self.base_url}/export/generate-branding",
                json=test_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Generación de branding exitosa")
                logger.info(f"   Colores sugeridos: {data.get('branding_guidelines', {}).get('primary_color', 'N/A')}")
                return True
            else:
                logger.error(f"❌ Generación de branding falló: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error probando generación de branding: {e}")
            return False
    
    async def test_pdf_export(self) -> bool:
        """Probar exportación a PDF"""
        logger.info("Probando exportación a PDF...")
        
        try:
            # Datos de prueba para exportación
            test_data = {
                "report_data": {
                    "title": "Reporte Financiero Q4 2024",
                    "description": "Análisis financiero del cuarto trimestre",
                    "content": {
                        "executive_summary": "El cuarto trimestre mostró un crecimiento sólido del 15% en ingresos, con márgenes mejorados y una posición de caja fuerte.",
                        "key_findings": [
                            "Crecimiento de ingresos del 15% vs Q3",
                            "Mejora en márgenes de 2.5 puntos porcentuales",
                            "Reducción de costos operativos del 8%"
                        ],
                        "detailed_analysis": {
                            "ventas": "Las ventas aumentaron significativamente en todos los segmentos de mercado.",
                            "costos": "Los costos se mantuvieron controlados gracias a las optimizaciones implementadas."
                        },
                        "recommendations": [
                            "Mantener la estrategia de crecimiento actual",
                            "Invertir en automatización de procesos",
                            "Expandir a nuevos mercados"
                        ],
                        "next_steps": [
                            "Implementar plan de expansión Q1 2025",
                            "Optimizar procesos de ventas",
                            "Desarrollar nuevos productos"
                        ]
                    }
                },
                "export_format": "pdf",
                "branding": {
                    "primary_color": "#2563eb",
                    "secondary_color": "#64748b",
                    "accent_color": "#059669",
                    "company_name": "TechCorp Solutions",
                    "tagline": "Innovación y Excelencia"
                },
                "optimize_for_executive": True
            }
            
            headers = {"Authorization": "Bearer test-token"}
            
            response = await self.client.post(
                f"{self.base_url}/export/pdf",
                json=test_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Exportación a PDF exitosa")
                logger.info(f"   Tamaño del archivo: {data.get('file_size', 0)} bytes")
                logger.info(f"   Nombre del archivo: {data.get('filename', 'N/A')}")
                
                # Verificar que el archivo tiene contenido
                file_data = data.get('file_data', '')
                if file_data and len(file_data) > 100:
                    logger.info("   ✅ Archivo PDF generado con contenido válido")
                    return True
                else:
                    logger.error("   ❌ Archivo PDF vacío o inválido")
                    return False
            else:
                logger.error(f"❌ Exportación a PDF falló: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error probando exportación a PDF: {e}")
            return False
    
    async def test_pptx_export(self) -> bool:
        """Probar exportación a PPTX"""
        logger.info("Probando exportación a PPTX...")
        
        try:
            # Datos de prueba para exportación
            test_data = {
                "report_data": {
                    "title": "Presentación Ejecutiva Q4 2024",
                    "description": "Presentación para junta directiva",
                    "content": {
                        "executive_summary": "Resultados excepcionales en Q4 con crecimiento sostenible y mejora en rentabilidad.",
                        "key_findings": [
                            "Crecimiento de ingresos del 15%",
                            "Mejora en márgenes de 2.5%",
                            "Reducción de costos del 8%"
                        ],
                        "detailed_analysis": {
                            "rendimiento_financiero": "Excelente rendimiento financiero con superación de objetivos.",
                            "operaciones": "Operaciones eficientes con mejoras en productividad."
                        },
                        "recommendations": [
                            "Continuar estrategia de crecimiento",
                            "Invertir en tecnología",
                            "Expandir mercados"
                        ],
                        "next_steps": [
                            "Plan de expansión Q1 2025",
                            "Optimización de procesos",
                            "Desarrollo de productos"
                        ]
                    }
                },
                "export_format": "pptx",
                "branding": {
                    "primary_color": "#dc2626",
                    "secondary_color": "#6b7280",
                    "accent_color": "#059669",
                    "company_name": "TechCorp Solutions",
                    "tagline": "Innovación y Excelencia"
                },
                "optimize_for_executive": True
            }
            
            headers = {"Authorization": "Bearer test-token"}
            
            response = await self.client.post(
                f"{self.base_url}/export/pptx",
                json=test_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Exportación a PPTX exitosa")
                logger.info(f"   Tamaño del archivo: {data.get('file_size', 0)} bytes")
                logger.info(f"   Nombre del archivo: {data.get('filename', 'N/A')}")
                
                # Verificar que el archivo tiene contenido
                file_data = data.get('file_data', '')
                if file_data and len(file_data) > 100:
                    logger.info("   ✅ Archivo PPTX generado con contenido válido")
                    return True
                else:
                    logger.error("   ❌ Archivo PPTX vacío o inválido")
                    return False
            else:
                logger.error(f"❌ Exportación a PPTX falló: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error probando exportación a PPTX: {e}")
            return False
    
    async def test_executive_optimization(self) -> bool:
        """Probar optimización para audiencia ejecutiva"""
        logger.info("Probando optimización para audiencia ejecutiva...")
        
        try:
            test_data = {
                "report_data": {
                    "content": {
                        "executive_summary": "Las ventas subieron mucho este mes comparado con el mes pasado.",
                        "recommendations": [
                            "Hay que hacer más marketing",
                            "Mejorar el servicio al cliente"
                        ]
                    }
                },
                "branding": {
                    "primary_color": "#2563eb",
                    "company_name": "TechCorp Solutions"
                }
            }
            
            headers = {"Authorization": "Bearer test-token"}
            
            response = await self.client.post(
                f"{self.base_url}/export/optimize-for-executive",
                json=test_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Optimización para audiencia ejecutiva exitosa")
                logger.info(f"   Contenido original: {len(str(data.get('original_content', {})))} caracteres")
                logger.info(f"   Contenido optimizado: {len(str(data.get('optimized_content', {})))} caracteres")
                return True
            else:
                logger.error(f"❌ Optimización para audiencia ejecutiva falló: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error probando optimización para audiencia ejecutiva: {e}")
            return False
    
    async def test_file_download(self, file_data: str, filename: str) -> bool:
        """Probar descarga y validación de archivo"""
        try:
            # Decodificar archivo base64
            file_bytes = base64.b64decode(file_data)
            
            # Guardar archivo temporalmente para validación
            with open(f"test_{filename}", "wb") as f:
                f.write(file_bytes)
            
            logger.info(f"   ✅ Archivo guardado como test_{filename}")
            logger.info(f"   Tamaño real: {len(file_bytes)} bytes")
            
            # Validaciones básicas según el tipo de archivo
            if filename.endswith('.pdf'):
                # Verificar que es un PDF válido
                if file_bytes.startswith(b'%PDF'):
                    logger.info("   ✅ Archivo PDF válido")
                    return True
                else:
                    logger.error("   ❌ Archivo PDF inválido")
                    return False
            elif filename.endswith('.pptx'):
                # Verificar que es un PPTX válido (ZIP con estructura específica)
                if file_bytes.startswith(b'PK'):
                    logger.info("   ✅ Archivo PPTX válido")
                    return True
                else:
                    logger.error("   ❌ Archivo PPTX inválido")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"   ❌ Error validando archivo: {e}")
            return False
    
    async def run_all_export_tests(self) -> Dict[str, bool]:
        """Ejecutar todas las pruebas de exportación"""
        logger.info("🚀 Iniciando pruebas de exportación avanzada...")
        
        results = {}
        
        # Ejecutar pruebas
        results["branding_generation"] = await self.test_branding_generation()
        results["pdf_export"] = await self.test_pdf_export()
        results["pptx_export"] = await self.test_pptx_export()
        results["executive_optimization"] = await self.test_executive_optimization()
        
        # Resumen
        passed = sum(results.values())
        total = len(results)
        
        logger.info(f"\n📊 Resumen de pruebas de exportación:")
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
    tester = ExportIntegrationTester()
    
    try:
        results = await tester.run_all_export_tests()
        
        # Verificar si todas las pruebas pasaron
        all_passed = all(results.values())
        
        if all_passed:
            logger.info("\n🎉 ¡Todas las pruebas de exportación pasaron exitosamente!")
            return 0
        else:
            logger.error("\n💥 Algunas pruebas de exportación fallaron")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error ejecutando pruebas de exportación: {e}")
        return 1
    finally:
        await tester.close()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 