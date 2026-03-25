from rest_framework.throttling import UserRateThrottle


class ComprasDocumentUploadThrottle(UserRateThrottle):
    """Rate limit subida de documentos (Fase 5 hardening)."""

    scope = "compras_document_upload"
