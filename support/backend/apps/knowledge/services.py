"""
Servicios RAG reales: búsqueda vectorial y ingesta de conocimiento.
"""
import hashlib
import logging
from typing import Any

from django.conf import settings
from django.db.models import Q, QuerySet

from apps.knowledge.models import KnowledgeChunk

logger = logging.getLogger(__name__)

# Top-K por defecto para búsqueda
DEFAULT_TOP_K = 10
MAX_TOP_K = 50


def _get_embedding_for_query(query: str) -> list[float] | None:
    """
    Obtiene el vector de embedding para la query. Si no hay proveedor configurado, retorna None.
    """
    embedder = getattr(settings, "EMBEDDING_FUNCTION", None)
    if not embedder or not callable(embedder):
        return None
    try:
        return embedder(query)
    except Exception as e:
        logger.warning("Embedding de query falló: %s", e)
        return None


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class RetrievalService:
    """
    Búsqueda real por similitud vectorial en support_knowledge_chunk.
    Filtro: (company_id IS NULL OR company_id = empresa); opcional source_type.
    """

    def __init__(self, top_k: int = DEFAULT_TOP_K):
        self.top_k = min(max(1, top_k), MAX_TOP_K)

    def search(
        self,
        query: str,
        company_id: int | None,
        top_k: int | None = None,
        source_type: str | None = None,
        include_global: bool = True,
        sistema: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Busca chunks por similitud al texto de la query.
        - company_id: empresa del caso; se incluyen chunks globales (company_id IS NULL) si include_global.
        - source_type: opcional (caso, codigo, human_note, resolved_case).
        - sistema: opcional ("synap" | "administranet") para filtrar por metadata.sistema.
        Retorna lista de {"chunk_id", "text", "score", "metadata", "source_type", "source_id"}.
        """
        k = min(max(1, top_k or self.top_k), MAX_TOP_K)
        embedding = _get_embedding_for_query(query)
        if not embedding:
            logger.debug("Sin embedder configurado; búsqueda vectorial devuelve vacío")
            return []

        # Chunks con embedding no nulo, filtro empresa (global + empresa)
        qs: QuerySet[KnowledgeChunk] = KnowledgeChunk.objects.filter(
            embedding__isnull=False
        )
        if include_global and company_id is not None:
            qs = qs.filter(Q(company_id__isnull=True) | Q(company_id=company_id))
        elif company_id is not None:
            qs = qs.filter(company_id=company_id)
        elif not include_global:
            qs = qs.filter(company_id__isnull=False)

        if source_type:
            qs = qs.filter(source_type=source_type)
        if sistema:
            qs = qs.filter(metadata__sistema=sistema)

        from pgvector.django import CosineDistance

        qs = (
            qs.annotate(distance=CosineDistance("embedding", embedding))
            .order_by("distance")[:k]
        )

        results = []
        for chunk in qs:
            d = getattr(chunk, "distance", None)
            score = float(1 - d) if d is not None else 0.0  # cosine similarity [0,1]
            results.append({
                "chunk_id": chunk.id,
                "text": chunk.text,
                "score": round(score, 4),
                "metadata": chunk.metadata or {},
                "source_type": chunk.source_type,
                "source_id": chunk.source_id,
            })
        return results

    def search_text_fallback(
        self,
        query: str,
        company_id: int | None,
        top_k: int | None = None,
        source_type: str | None = None,
        include_global: bool = True,
        sistema: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Búsqueda textual (Postgres full-text) para admin cuando no hay EMBEDDING_FUNCTION.
        Mismo formato de salida que search(); score aproximado por relevancia textual.
        """
        k = min(max(1, top_k or self.top_k), MAX_TOP_K)
        qs = KnowledgeChunk.objects.all()
        if include_global and company_id is not None:
            qs = qs.filter(Q(company_id__isnull=True) | Q(company_id=company_id))
        elif company_id is not None:
            qs = qs.filter(company_id=company_id)
        elif not include_global:
            qs = qs.filter(company_id__isnull=False)
        if source_type:
            qs = qs.filter(source_type=source_type)
        if sistema:
            qs = qs.filter(metadata__sistema=sistema)
        qs = qs.filter(text__icontains=query)[:k]
        return [
            {
                "chunk_id": c.id,
                "text": c.text,
                "score": 0.5,  # Placeholder; no es similitud vectorial
                "metadata": c.metadata or {},
                "source_type": c.source_type,
                "source_id": c.source_id,
            }
            for c in qs
        ]


def is_embedding_configured() -> bool:
    """True si hay EMBEDDING_FUNCTION configurada y callable."""
    fn = getattr(settings, "EMBEDDING_FUNCTION", None)
    return bool(fn and callable(fn))


class KnowledgeIngestionService:
    """
    Ingesta mínima viable: crear/actualizar chunks con content_hash;
    no re-embedir si el contenido no cambia. Encola jobs Celery para embeddings.
    """

    def __init__(self):
        self._embedding_task = None  # Se registra en apps.knowledge.tasks

    def create_or_update_chunks(
        self,
        items: list[dict[str, Any]],
        company_id: int | None = None,
        source_type: str = "caso",
    ) -> tuple[int, int]:
        """
        Crea o actualiza chunks. Cada item: text, source_id (opcional), metadata (opcional).
        Retorna (creados, actualizados).
        """
        created, updated = 0, 0
        for item in items:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            source_id = str(item.get("source_id", ""))[:64]
            metadata = item.get("metadata") or {}
            content_hash = _content_hash(text)

            chunk = KnowledgeChunk.objects.filter(
                company_id=company_id,
                source_type=source_type,
                source_id=source_id,
            ).first()

            if chunk:
                if chunk.content_hash == content_hash:
                    continue  # No re-embed
                chunk.text = text
                chunk.content_hash = content_hash
                chunk.metadata = metadata
                chunk.embedding = None  # Se re-embedirá en Celery
                chunk.save(update_fields=["text", "content_hash", "metadata", "embedding"])
                updated += 1
            else:
                chunk = KnowledgeChunk.objects.create(
                    company_id=company_id,
                    source_type=source_type,
                    source_id=source_id,
                    text=text,
                    content_hash=content_hash,
                    metadata=metadata,
                )
                created += 1

            # Encolar tarea de embedding (stub si no hay proveedor)
            from apps.knowledge.tasks import embed_chunk_task
            embed_chunk_task.delay(chunk.id)

        return created, updated
