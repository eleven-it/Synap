"""
Microservicio de IA para el módulo de reportes de Synap
Proporciona funcionalidades de IA para generación, análisis y optimización de reportes
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

from services.ai_service import AIService
from services.report_generator import ReportGenerator
from services.data_analyzer import DataAnalyzer
from services.design_optimizer import DesignOptimizer
from services.vector_store import VectorStore
from services.export_service import ExportService
from utils.auth import verify_token
from utils.logging import setup_logging
from config import settings

# Configurar logging
setup_logging()
logger = logging.getLogger(__name__)

# Configurar seguridad
security = HTTPBearer()

# Modelos Pydantic para las requests
class ReportGenerationRequest(BaseModel):
    """Request para generación de reportes"""
    title: str = Field(..., description="Título del reporte")
    description: str = Field(..., description="Descripción del reporte")
    data_sources: List[str] = Field(default=[], description="Fuentes de datos")
    template_type: str = Field(..., description="Tipo de template")
    company_context: Dict[str, Any] = Field(default={}, description="Contexto de la empresa")
    user_preferences: Dict[str, Any] = Field(default={}, description="Preferencias del usuario")

class ContentAnalysisRequest(BaseModel):
    """Request para análisis de contenido"""
    content: str = Field(..., description="Contenido a analizar")
    analysis_type: str = Field(..., description="Tipo de análisis")
    context: Dict[str, Any] = Field(default={}, description="Contexto adicional")

class DesignOptimizationRequest(BaseModel):
    """Request para optimización de diseño"""
    current_layout: Dict[str, Any] = Field(..., description="Layout actual")
    target_audience: str = Field(..., description="Audiencia objetivo")
    brand_guidelines: Dict[str, Any] = Field(default={}, description="Guías de marca")

class DataInsightRequest(BaseModel):
    """Request para insights de datos"""
    data: List[Dict[str, Any]] = Field(..., description="Datos a analizar")
    insight_type: str = Field(..., description="Tipo de insight")
    business_context: Dict[str, Any] = Field(default={}, description="Contexto de negocio")

class ExportRequest(BaseModel):
    """Request para exportación de reportes"""
    report_data: Dict[str, Any] = Field(..., description="Datos del reporte")
    export_format: str = Field(..., description="Formato de exportación (pdf/pptx)")
    branding: Dict[str, Any] = Field(default={}, description="Configuración de branding")
    optimize_for_executive: bool = Field(default=True, description="Optimizar para audiencia ejecutiva")

class BrandingGenerationRequest(BaseModel):
    """Request para generación de branding"""
    company_data: Dict[str, Any] = Field(..., description="Datos de la empresa")
    report_type: str = Field(..., description="Tipo de reporte")
    target_audience: str = Field(default="executive", description="Audiencia objetivo")

# Modelos Pydantic para las responses
class ReportGenerationResponse(BaseModel):
    """Response para generación de reportes"""
    report_id: str
    title: str
    content: Dict[str, Any]
    components: List[Dict[str, Any]]
    suggestions: List[str]
    confidence_score: float

class ContentAnalysisResponse(BaseModel):
    """Response para análisis de contenido"""
    analysis_id: str
    insights: List[str]
    recommendations: List[str]
    sentiment_score: float
    readability_score: float
    keywords: List[str]

class DesignOptimizationResponse(BaseModel):
    """Response para optimización de diseño"""
    optimization_id: str
    improved_layout: Dict[str, Any]
    suggestions: List[str]
    visual_hierarchy: Dict[str, Any]
    accessibility_score: float

class DataInsightResponse(BaseModel):
    """Response para insights de datos"""
    insight_id: str
    key_findings: List[str]
    trends: List[Dict[str, Any]]
    recommendations: List[str]
    visualizations: List[Dict[str, Any]]

# Variables globales para servicios
ai_service: Optional[AIService] = None
report_generator: Optional[ReportGenerator] = None
data_analyzer: Optional[DataAnalyzer] = None
design_optimizer: Optional[DesignOptimizer] = None
vector_store: Optional[VectorStore] = None
export_service: Optional[ExportService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    global ai_service, report_generator, data_analyzer, design_optimizer, vector_store, export_service
    
    # Inicializar servicios
    logger.info("Inicializando servicios de IA...")
    
    try:
        # Inicializar vector store
        vector_store = VectorStore()
        await vector_store.initialize()
        
        # Inicializar servicios de IA
        ai_service = AIService(vector_store=vector_store)
        report_generator = ReportGenerator(ai_service=ai_service)
        data_analyzer = DataAnalyzer(ai_service=ai_service)
        design_optimizer = DesignOptimizer(ai_service=ai_service)
        export_service = ExportService(ai_service=ai_service)
        
        logger.info("Servicios de IA inicializados correctamente")
        
    except Exception as e:
        logger.error(f"Error inicializando servicios de IA: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Cerrando servicios de IA...")
    if vector_store:
        await vector_store.close()

# Crear aplicación FastAPI
app = FastAPI(
    title="Synap Reports AI Service",
    description="Microservicio de IA para generación y optimización de reportes",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependencia para autenticación
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verificar token de autenticación"""
    try:
        user = verify_token(credentials.credentials)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Endpoints de salud
@app.get("/health")
async def health_check():
    """Endpoint de salud del servicio"""
    return {
        "status": "healthy",
        "service": "synap-reports-ai",
        "version": "1.0.0"
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Endpoint de salud detallado"""
    services_status = {
        "ai_service": ai_service is not None,
        "report_generator": report_generator is not None,
        "data_analyzer": data_analyzer is not None,
        "design_optimizer": design_optimizer is not None,
        "vector_store": vector_store is not None
    }
    
    return {
        "status": "healthy" if all(services_status.values()) else "degraded",
        "services": services_status,
        "timestamp": "2024-01-15T10:00:00Z"
    }

# Endpoints principales de IA
@app.post("/ai/generate-report", response_model=ReportGenerationResponse)
async def generate_report(
    request: ReportGenerationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Generar reporte usando IA"""
    try:
        logger.info(f"Generando reporte: {request.title}")
        
        result = await report_generator.generate_report(
            title=request.title,
            description=request.description,
            data_sources=request.data_sources,
            template_type=request.template_type,
            company_context=request.company_context,
            user_preferences=request.user_preferences
        )
        
        return ReportGenerationResponse(**result)
        
    except Exception as e:
        logger.error(f"Error generando reporte: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando reporte: {str(e)}"
        )

@app.post("/ai/analyze-content", response_model=ContentAnalysisResponse)
async def analyze_content(
    request: ContentAnalysisRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Analizar contenido usando IA"""
    try:
        logger.info(f"Analizando contenido: {request.analysis_type}")
        
        result = await data_analyzer.analyze_content(
            content=request.content,
            analysis_type=request.analysis_type,
            context=request.context
        )
        
        return ContentAnalysisResponse(**result)
        
    except Exception as e:
        logger.error(f"Error analizando contenido: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analizando contenido: {str(e)}"
        )

@app.post("/ai/optimize-design", response_model=DesignOptimizationResponse)
async def optimize_design(
    request: DesignOptimizationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Optimizar diseño usando IA"""
    try:
        logger.info(f"Optimizando diseño para audiencia: {request.target_audience}")
        
        result = await design_optimizer.optimize_layout(
            current_layout=request.current_layout,
            target_audience=request.target_audience,
            brand_guidelines=request.brand_guidelines
        )
        
        return DesignOptimizationResponse(**result)
        
    except Exception as e:
        logger.error(f"Error optimizando diseño: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error optimizando diseño: {str(e)}"
        )

@app.post("/ai/data-insights", response_model=DataInsightResponse)
async def get_data_insights(
    request: DataInsightRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Obtener insights de datos usando IA"""
    try:
        logger.info(f"Analizando datos para insights: {request.insight_type}")
        
        result = await data_analyzer.get_insights(
            data=request.data,
            insight_type=request.insight_type,
            business_context=request.business_context
        )
        
        return DataInsightResponse(**result)
        
    except Exception as e:
        logger.error(f"Error obteniendo insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo insights: {str(e)}"
        )

@app.post("/ai/suggest-components")
async def suggest_components(
    report_context: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Sugerir componentes para un reporte"""
    try:
        logger.info("Sugiriendo componentes para reporte")
        
        suggestions = await report_generator.suggest_components(report_context)
        
        return {
            "suggestions": suggestions,
            "confidence_score": 0.85
        }
        
    except Exception as e:
        logger.error(f"Error sugiriendo componentes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sugiriendo componentes: {str(e)}"
        )

@app.post("/ai/improve-text")
async def improve_text(
    text: str,
    improvement_type: str = "general",
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Mejorar texto usando IA"""
    try:
        logger.info(f"Mejorando texto: {improvement_type}")
        
        improved_text = await ai_service.improve_text(text, improvement_type)
        
        return {
            "original_text": text,
            "improved_text": improved_text,
            "improvement_type": improvement_type
        }
        
    except Exception as e:
        logger.error(f"Error mejorando texto: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error mejorando texto: {str(e)}"
        )

# Endpoints de exportación
@app.post("/export/pdf")
async def export_to_pdf(
    request: ExportRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Exportar reporte a PDF con branding institucional"""
    try:
        logger.info(f"Exportando reporte a PDF")
        
        # Optimizar contenido para audiencia ejecutiva si se solicita
        if request.optimize_for_executive:
            request.report_data['content'] = await export_service.optimize_for_executive_audience(
                request.report_data.get('content', {}),
                request.branding
            )
        
        # Generar PDF
        pdf_buffer = await export_service.export_to_pdf(
            report_data=request.report_data,
            branding=request.branding
        )
        
        # Convertir a base64 para respuesta
        import base64
        pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
        
        return {
            "format": "pdf",
            "file_size": len(pdf_buffer.getvalue()),
            "file_data": pdf_base64,
            "filename": f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        }
        
    except Exception as e:
        logger.error(f"Error exportando a PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exportando a PDF: {str(e)}"
        )

@app.post("/export/pptx")
async def export_to_pptx(
    request: ExportRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Exportar reporte a PPTX con branding institucional"""
    try:
        logger.info(f"Exportando reporte a PPTX")
        
        # Optimizar contenido para audiencia ejecutiva si se solicita
        if request.optimize_for_executive:
            request.report_data['content'] = await export_service.optimize_for_executive_audience(
                request.report_data.get('content', {}),
                request.branding
            )
        
        # Generar PPTX
        pptx_buffer = await export_service.export_to_pptx(
            report_data=request.report_data,
            branding=request.branding
        )
        
        # Convertir a base64 para respuesta
        import base64
        pptx_base64 = base64.b64encode(pptx_buffer.getvalue()).decode('utf-8')
        
        return {
            "format": "pptx",
            "file_size": len(pptx_buffer.getvalue()),
            "file_data": pptx_base64,
            "filename": f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
        }
        
    except Exception as e:
        logger.error(f"Error exportando a PPTX: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exportando a PPTX: {str(e)}"
        )

@app.post("/export/generate-branding")
async def generate_branding(
    request: BrandingGenerationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Generar guías de branding usando IA"""
    try:
        logger.info(f"Generando branding para empresa: {request.company_data.get('name', 'N/A')}")
        
        branding_guidelines = await export_service.generate_branding_guidelines(
            company_data=request.company_data,
            report_type=request.report_type
        )
        
        return {
            "branding_guidelines": branding_guidelines,
            "company_name": request.company_data.get('name'),
            "report_type": request.report_type,
            "target_audience": request.target_audience
        }
        
    except Exception as e:
        logger.error(f"Error generando branding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando branding: {str(e)}"
        )

@app.post("/export/optimize-for-executive")
async def optimize_for_executive(
    report_data: Dict[str, Any],
    branding: Dict[str, Any] = {},
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Optimizar contenido para audiencia ejecutiva"""
    try:
        logger.info("Optimizando contenido para audiencia ejecutiva")
        
        optimized_content = await export_service.optimize_for_executive_audience(
            content=report_data.get('content', {}),
            branding=branding
        )
        
        return {
            "original_content": report_data.get('content', {}),
            "optimized_content": optimized_content,
            "optimization_type": "executive_audience"
        }
        
    except Exception as e:
        logger.error(f"Error optimizando para audiencia ejecutiva: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error optimizando contenido: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 