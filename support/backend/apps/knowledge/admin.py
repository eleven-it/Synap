"""Admin para chunks de conocimiento RAG (ver y filtrar lo ingestado desde Synap, etc.)."""
from django.contrib import admin

from apps.knowledge.models import KnowledgeChunk


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "source_type",
        "source_id_short",
        "company",
        "sistema_display",
        "text_preview",
        "has_embedding",
        "created_at",
    )
    list_filter = ("source_type", "company")
    search_fields = ("text", "source_id", "metadata")
    readonly_fields = ("content_hash", "created_at")
    list_per_page = 25

    def source_id_short(self, obj):
        if not obj.source_id:
            return "—"
        return obj.source_id[:40] + "…" if len(obj.source_id) > 40 else obj.source_id

    source_id_short.short_description = "Source ID"

    def sistema_display(self, obj):
        sistema = (obj.metadata or {}).get("sistema")
        if not sistema:
            return "—"
        return sistema

    sistema_display.short_description = "Sistema"

    def text_preview(self, obj):
        if not obj.text:
            return "—"
        preview = (obj.text[:80] + "…") if len(obj.text) > 80 else obj.text
        return preview

    text_preview.short_description = "Texto (vista previa)"

    def has_embedding(self, obj):
        if getattr(obj, "embedding", None) is None:
            return False
        # pgvector: embedding puede ser None o un vector
        try:
            return obj.embedding is not None
        except Exception:
            return False

    has_embedding.boolean = True
    has_embedding.short_description = "Embedding"
