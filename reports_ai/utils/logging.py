"""
Configuración de logging para el microservicio de IA
"""

import logging
import sys
from typing import Optional, Dict
import structlog

from config import settings

def setup_logging(log_level: Optional[str] = None) -> None:
    """Configurar sistema de logging"""
    
    # Usar nivel de log de configuración o por defecto
    level = log_level or settings.LOG_LEVEL
    
    # Configurar structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configurar logging estándar
    logging.basicConfig(
        format=settings.LOG_FORMAT,
        level=getattr(logging, level.upper()),
        stream=sys.stdout
    )
    
    # Configurar loggers específicos
    loggers = [
        "reports_ai",
        "services",
        "utils",
        "uvicorn",
        "fastapi"
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level.upper()))
    
    # Configurar logger principal
    main_logger = logging.getLogger("reports_ai")
    main_logger.info(f"Logging configurado con nivel: {level}")

def get_logger(name: str) -> structlog.BoundLogger:
    """Obtener logger configurado"""
    return structlog.get_logger(name)

def log_request(request_id: str, method: str, path: str, user_id: Optional[str] = None) -> None:
    """Log de request entrante"""
    logger = get_logger("requests")
    logger.info(
        "Request recibida",
        request_id=request_id,
        method=method,
        path=path,
        user_id=user_id
    )

def log_response(request_id: str, status_code: int, response_time: float) -> None:
    """Log de response saliente"""
    logger = get_logger("requests")
    logger.info(
        "Response enviada",
        request_id=request_id,
        status_code=status_code,
        response_time=response_time
    )

def log_ai_request(
    request_id: str,
    service: str,
    operation: str,
    user_id: Optional[str] = None
) -> None:
    """Log de request a servicios de IA"""
    logger = get_logger("ai_requests")
    logger.info(
        "Request a servicio de IA",
        request_id=request_id,
        service=service,
        operation=operation,
        user_id=user_id
    )

def log_ai_response(
    request_id: str,
    service: str,
    operation: str,
    success: bool,
    response_time: float,
    error: Optional[str] = None
) -> None:
    """Log de response de servicios de IA"""
    logger = get_logger("ai_requests")
    
    if success:
        logger.info(
            "Response de servicio de IA exitosa",
            request_id=request_id,
            service=service,
            operation=operation,
            response_time=response_time
        )
    else:
        logger.error(
            "Error en servicio de IA",
            request_id=request_id,
            service=service,
            operation=operation,
            response_time=response_time,
            error=error
        )

def log_vector_store_operation(
    operation: str,
    collection: str,
    success: bool,
    details: Optional[Dict] = None
) -> None:
    """Log de operaciones de vector store"""
    logger = get_logger("vector_store")
    
    if success:
        logger.info(
            "Operación de vector store exitosa",
            operation=operation,
            collection=collection,
            details=details
        )
    else:
        logger.error(
            "Error en operación de vector store",
            operation=operation,
            collection=collection,
            details=details
        )

def log_performance_metric(
    metric_name: str,
    value: float,
    unit: str = "ms",
    context: Optional[Dict] = None
) -> None:
    """Log de métricas de rendimiento"""
    logger = get_logger("performance")
    logger.info(
        "Métrica de rendimiento",
        metric_name=metric_name,
        value=value,
        unit=unit,
        context=context
    )

def log_error(
    error: Exception,
    context: Optional[Dict] = None,
    user_id: Optional[str] = None
) -> None:
    """Log de errores"""
    logger = get_logger("errors")
    logger.error(
        "Error en aplicación",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context,
        user_id=user_id,
        exc_info=True
    ) 