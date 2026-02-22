# RAG migrado a LangChain PGVector; se elimina la tabla support_knowledge_chunk

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("knowledge", "0003_remove_knowledgechunk_support_kno_company_f435ca_idx_and_more"),
    ]

    operations = [
        migrations.DeleteModel(name="KnowledgeChunk"),
    ]
