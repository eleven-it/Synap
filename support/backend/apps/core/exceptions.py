"""Excepciones y handler de errores normalizados para la API."""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """Devuelve respuestas de error con code, message y details."""
    from apps.core.exceptions import APIError
    if isinstance(exc, APIError):
        return Response(
            {"code": exc.code, "message": exc.message, "details": exc.details},
            status=exc.status_code,
        )
    response = exception_handler(exc, context)
    if response is not None:
        data = getattr(response, "data", {})
        if isinstance(data, dict) and "detail" in data and "code" not in data:
            code = getattr(exc, "default_code", "ERROR")
            if hasattr(exc, "code"):
                code = exc.code
            response.data = {
                "code": code,
                "message": data.get("detail", str(data)),
                "details": data.get("details", []),
            }
        return response
    return Response(
        {
            "code": "INTERNAL_ERROR",
            "message": "Error interno del servidor",
            "details": [],
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


class APIError(Exception):
    """Error de API con código y mensaje."""

    default_code = "ERROR"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, code: str | None = None, details: list | None = None):
        self.message = message
        self.code = code or self.default_code
        self.details = details or []
        super().__init__(message)


class ValidationError(APIError):
    default_code = "VALIDATION_ERROR"
    status_code = status.HTTP_400_BAD_REQUEST


class CaseStateTransitionError(APIError):
    default_code = "CASE_STATE_TRANSITION_INVALID"
    status_code = status.HTTP_409_CONFLICT
