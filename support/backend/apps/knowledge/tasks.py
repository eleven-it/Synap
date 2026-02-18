"""Tareas Celery para conocimiento RAG: embeddings e ingesta."""
import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(name="knowledge.embed_chunk", bind=True)
def embed_chunk_task(self, chunk_id: int) -> dict:
    """
    Calcula el embedding del chunk y lo persiste.
    Si no hay EMBEDDING_FUNCTION configurada, deja el chunk sin embedding (contrato listo).
    """
    from apps.knowledge.models import KnowledgeChunk

    chunk = KnowledgeChunk.objects.filter(pk=chunk_id).first()
    if not chunk:
        return {"ok": False, "reason": "chunk_not_found"}

    embedder = getattr(settings, "EMBEDDING_FUNCTION", None)
    if not embedder or not callable(embedder):
        logger.debug("Sin EMBEDDING_FUNCTION; chunk %s sin embedding", chunk_id)
        return {"ok": True, "embedded": False}

    try:
        vector = embedder(chunk.text)
        if vector and len(vector) == getattr(settings, "EMBEDDING_DIMENSION", 1536):
            chunk.embedding = vector
            chunk.save(update_fields=["embedding"])
            return {"ok": True, "embedded": True}
    except Exception as e:
        logger.warning("Embedding falló para chunk %s: %s", chunk_id, e)
        return {"ok": False, "reason": str(e)}

    return {"ok": True, "embedded": False}
