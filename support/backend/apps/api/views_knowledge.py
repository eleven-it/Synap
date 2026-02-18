"""API conocimiento RAG: ingesta (admin) y búsqueda (admin/debug)."""
from django.urls import path
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.api.permissions import IsAdmin
from apps.knowledge.services import (
    RetrievalService,
    KnowledgeIngestionService,
    is_embedding_configured,
)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def knowledge_ingest(request):
    """
    POST /api/knowledge/ingest
    Admin. Ingesta chunks: body.items = [ { "text", "source_id?", "metadata?" } ];
    opcional company_id, source_type. Dispara jobs de embedding.
    """
    items = request.data.get("items")
    if not items or not isinstance(items, list):
        return Response(
            {"code": "VALIDATION_ERROR", "message": "items (lista) requerido", "details": []},
            status=status.HTTP_400_BAD_REQUEST,
        )
    company_id = request.data.get("company_id")
    source_type = (request.data.get("source_type") or "caso")[:32]

    svc = KnowledgeIngestionService()
    created, updated = svc.create_or_update_chunks(
        items=items,
        company_id=company_id,
        source_type=source_type,
    )
    return Response({
        "created": created,
        "updated": updated,
        "message": f"Ingesta: {created} creados, {updated} actualizados.",
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def knowledge_search(request):
    """
    GET /api/knowledge/search?q=...&company_id=...&top_k=...&source_type=...&fallback=text
    Admin (debug). Búsqueda vectorial si EMBEDDING_FUNCTION está configurada.
    Si no: 501 salvo que fallback=text, entonces búsqueda textual (full-text) para debug.
    """
    q = (request.query_params.get("q") or "").strip()
    if not q:
        return Response(
            {"code": "VALIDATION_ERROR", "message": "q (query) requerido", "details": []},
            status=status.HTTP_400_BAD_REQUEST,
        )
    company_id = request.query_params.get("company_id")
    if company_id is not None:
        try:
            company_id = int(company_id)
        except (TypeError, ValueError):
            company_id = None
    top_k = request.query_params.get("top_k")
    if top_k is not None:
        try:
            top_k = int(top_k)
        except (TypeError, ValueError):
            top_k = 10
    else:
        top_k = 10
    source_type = (request.query_params.get("source_type") or "").strip() or None
    fallback_text = request.query_params.get("fallback", "").strip().lower() == "text"

    if not is_embedding_configured():
        if fallback_text:
            retrieval = RetrievalService(top_k=top_k)
            results = retrieval.search_text_fallback(
                query=q,
                company_id=company_id,
                top_k=top_k,
                source_type=source_type,
                include_global=True,
            )
            return Response({
                "results": results,
                "mode": "text",
                "message": "Búsqueda textual (embeddings provider not configured).",
            })
        return Response(
            {
                "code": "NOT_IMPLEMENTED",
                "message": "embeddings provider not configured",
                "details": ["Configure EMBEDDING_FUNCTION in settings or use ?fallback=text for text search."],
            },
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    retrieval = RetrievalService(top_k=top_k)
    results = retrieval.search(
        query=q,
        company_id=company_id,
        top_k=top_k,
        source_type=source_type,
        include_global=True,
    )
    return Response({"results": results, "mode": "vector"})


urlpatterns = [
    path("ingest/", knowledge_ingest),
    path("search/", knowledge_search),
]
