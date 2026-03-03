# RAG real: pgvector, source_type, content_hash, índice HNSW (fallback IVFFlat)

from django.db import migrations, models
import pgvector.django

# Dimensión fija para migración reproducible; cambiar EMBEDDING_DIMENSION requiere nueva migración
EMBEDDING_DIMENSION = 1536


def create_vector_index(apps, schema_editor):
    """Crea índice de similitud: HNSW si pgvector lo soporta, sino IVFFlat."""
    from django.db import connection

    with connection.cursor() as cursor:
        # HNSW requiere pgvector ~0.5+ (Postgres 14+). Si falla, usar IVFFlat.
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS support_knowledge_chunk_embedding_hnsw
                ON support_knowledge_chunk
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """)
        except Exception:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS support_knowledge_chunk_embedding_ivfflat
                ON support_knowledge_chunk
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)


def drop_vector_index(apps, schema_editor):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("DROP INDEX IF EXISTS support_knowledge_chunk_embedding_hnsw;")
        cursor.execute("DROP INDEX IF EXISTS support_knowledge_chunk_embedding_ivfflat;")


class Migration(migrations.Migration):

    dependencies = [
        ("knowledge", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;",
        ),
        migrations.RenameField(
            model_name="knowledgechunk",
            old_name="chunk_type",
            new_name="source_type",
        ),
        migrations.AddField(
            model_name="knowledgechunk",
            name="content_hash",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=64,
                verbose_name="Hash del contenido (evita re-embed si no cambia)",
            ),
        ),
        migrations.AddField(
            model_name="knowledgechunk",
            name="embedding",
            field=pgvector.django.VectorField(
                blank=True,
                dimensions=EMBEDDING_DIMENSION,
                null=True,
            ),
        ),
        migrations.RunPython(create_vector_index, reverse_code=drop_vector_index),
    ]
