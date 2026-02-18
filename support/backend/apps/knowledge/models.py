"""Chunk de conocimiento para RAG con pgvector (embedding real)."""
from django.conf import settings
from django.db import models
from apps.companies.models import Company

try:
    from pgvector.django import HnswIndex, VectorField
except ImportError:
    HnswIndex = None
    VectorField = None


def _get_embedding_dimension():
    return getattr(settings, "EMBEDDING_DIMENSION", 1536)


class KnowledgeChunk(models.Model):
    """
    Fragmento indexado para RAG. Incluye embedding (pgvector) para búsqueda
    por similitud. company_id NULL = conocimiento global; si no, por empresa.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="knowledge_chunks",
    )
    source_type = models.CharField(
        "Tipo fuente (caso, codigo, human_note, resolved_case)",
        max_length=32,
        default="caso",
    )
    source_id = models.CharField("ID fuente (caso, artefacto)", max_length=64, blank=True)
    text = models.TextField("Texto del chunk")
    content_hash = models.CharField(
        "Hash del contenido (evita re-embed si no cambia)",
        max_length=64,
        blank=True,
        db_index=True,
    )
    metadata = models.JSONField("Metadata", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Embedding para búsqueda vectorial (pgvector). Nullable para filas creadas sin embedder.
    if VectorField is not None:
        embedding = VectorField(
            dimensions=_get_embedding_dimension(),
            null=True,
            blank=True,
        )
    else:
        embedding = None  # type: ignore

    class Meta:
        db_table = "support_knowledge_chunk"
        verbose_name = "Chunk conocimiento"
        verbose_name_plural = "Chunks conocimiento"
        indexes = [
            models.Index(fields=["company", "source_type"]),
            models.Index(fields=["content_hash"]),
        ]
