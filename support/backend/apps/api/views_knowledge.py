"""API conocimiento RAG: ingesta (admin), listado (admin), búsqueda (admin/debug), sync desde Synap."""
from django.conf import settings
from django.urls import path
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.api.permissions import IsAdmin, IsAgentOrAdmin
from apps.knowledge.models import KnowledgeChunk
from apps.knowledge.services import (
    RetrievalService,
    KnowledgeIngestionService,
    is_embedding_configured,
)
from apps.system_config.services import invalidate_config_cache


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
@permission_classes([IsAuthenticated, IsAgentOrAdmin])
def knowledge_chunks_list(request):
    """
    GET /api/knowledge/chunks/
    Listado paginado de chunks de conocimiento. Params: limit, offset, source_type, company_id.
    """
    limit = request.query_params.get("limit")
    offset = request.query_params.get("offset")
    try:
        limit = min(100, max(1, int(limit))) if limit else 20
    except (TypeError, ValueError):
        limit = 20
    try:
        offset = max(0, int(offset)) if offset else 0
    except (TypeError, ValueError):
        offset = 0
    source_type = (request.query_params.get("source_type") or "").strip() or None
    company_id = request.query_params.get("company_id")
    if company_id is not None:
        try:
            company_id = int(company_id)
        except (TypeError, ValueError):
            company_id = None

    qs = KnowledgeChunk.objects.all().order_by("-created_at")
    if source_type:
        qs = qs.filter(source_type=source_type)
    if company_id is not None:
        qs = qs.filter(company_id=company_id)
    total = qs.count()
    chunks = list(qs[offset : offset + limit])

    def serialize(chunk):
        meta = chunk.metadata or {}
        has_embedding = getattr(chunk, "embedding", None) is not None
        return {
            "id": chunk.id,
            "source_type": chunk.source_type,
            "source_id": chunk.source_id or "",
            "company_id": chunk.company_id,
            "text": chunk.text[:500] + "…" if chunk.text and len(chunk.text) > 500 else (chunk.text or ""),
            "text_length": len(chunk.text) if chunk.text else 0,
            "metadata": meta,
            "sistema": meta.get("sistema"),
            "file": meta.get("file"),
            "has_embedding": has_embedding,
            "created_at": chunk.created_at.isoformat() if chunk.created_at else None,
        }

    return Response({
        "count": total,
        "limit": limit,
        "offset": offset,
        "results": [serialize(c) for c in chunks],
    })


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
    sistema = (request.query_params.get("sistema") or "").strip() or None
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
                sistema=sistema,
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
        sistema=sistema,
    )
    return Response({"results": results, "mode": "vector"})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdmin])
def sync_from_synap(request):
    """
    POST /api/knowledge/sync-from-synap/
    Obtiene conocimiento desde Synap (GET /core/api/support/conocimiento/) e ingesta en RAG.
    Body: { "company_id": number | null }. Opcional; si no se envía, ingesta global (company_id null).
    """
    base_url = getattr(settings, "SUPPORT_SYNAP_API_URL", "") or ""
    if not base_url.strip():
        return Response(
            {
                "message": (
                    "Synap no está configurado. En el backend Support configurá SUPPORT_SYNAP_API_URL "
                    "en el .env (ej. http://host.docker.internal:8000 si Synap corre en el host) y reiniciá el servicio."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    company_id = request.data.get("company_id")
    if company_id is not None:
        try:
            company_id = int(company_id)
        except (TypeError, ValueError):
            company_id = None

    from apps.integrations.adapters.synap_client import SynapClient, SynapClientError

    try:
        client = SynapClient()
        items = client.get_conocimiento()
    except SynapClientError as e:
        return Response(
            {
                "message": f"No se pudo conectar con Synap: {e!s}. Revisá SUPPORT_SYNAP_API_URL y SUPPORT_SYNAP_JWT_SECRET.",
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception as e:
        return Response(
            {"message": f"Error al obtener conocimiento desde Synap: {e!s}."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if not items:
        return Response(
            {
                "created": 0,
                "updated": 0,
                "message": "Synap no devolvió ítems (la URL puede ser incorrecta o el endpoint no existe).",
            },
            status=status.HTTP_200_OK,
        )

    try:
        svc = KnowledgeIngestionService()
        created, updated = svc.create_or_update_chunks(
            items=items,
            company_id=company_id,
            source_type="synap",
        )
        invalidate_config_cache("rag", company_id)
        return Response(
            {
                "created": created,
                "updated": updated,
                "message": f"Cargado desde Synap: {created} creados, {updated} actualizados.",
            },
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response(
            {"message": f"Error al ingestar en la base de conocimiento: {e!s}."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


urlpatterns = [
    path("chunks/", knowledge_chunks_list),
    path("ingest/", knowledge_ingest),
    path("search/", knowledge_search),
    path("sync-from-synap/", sync_from_synap),
]
