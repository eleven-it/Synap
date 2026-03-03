"""Logging estructurado y correlación (request_id, case_id, empresa_id)."""
import logging
import uuid

import structlog

def add_request_id(logger, method_name, event_dict):
    """Añade request_id al evento si está en contextvars o en el evento."""
    from structlog.contextvars import get_contextvars
    ctx = get_contextvars()
    if "request_id" in ctx:
        event_dict["request_id"] = ctx["request_id"]
    if "case_id" in ctx:
        event_dict["case_id"] = ctx["case_id"]
    if "empresa_id" in ctx:
        event_dict["empresa_id"] = ctx["empresa_id"]
    return event_dict


def configure_structlog():
    """Configura structlog para logging estructurado."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_request_id,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_request_id():
    """Genera o obtiene request_id del contexto."""
    from structlog.contextvars import get_contextvars, bind_contextvars
    ctx = get_contextvars()
    if "request_id" not in ctx:
        bind_contextvars(request_id=str(uuid.uuid4())[:8])
    return get_contextvars().get("request_id", "")
