# RAG en Support: implementación con LangChain (Opción A)

Resumen de lo **implementado** en el refactor del RAG del módulo Support: reemplazo total del desarrollo propio por **LangChain** y **PGVector** (Opción A del plan). No se edita el plan; este documento describe el estado actual del código y la documentación asociada.

## Decisión y alcance

- **Opción elegida:** Reemplazo total (Opción A): schema LangChain PGVector, ingesta vía `vector_store.add_documents()`, retrieval y generación 100 % LangChain; eliminación de la tabla Django `support_knowledge_chunk` y de los servicios propios (RetrievalService, KnowledgeIngestionService, embed_chunk_task).
- **Plan de referencia:** `.cursor/plans/refactor_rag_support_langchain_*.plan.md` (análisis, ventajas/riesgos, orden de tareas).

## Tareas realizadas

1. **Dependencias y configuración**
   - Añadidas en `support/backend/requirements.txt`: `langchain-core`, `langchain-openai`, `langchain-postgres`.
   - En `support/backend/config/settings/base.py`: `LANGCHAIN_PGVECTOR_COLLECTION_NAME` (por defecto `"support_rag"`). Conexión al store construida desde `DATABASES["default"]` (postgresql+psycopg).

2. **Módulo RAG (LangChain)**
   - **Ubicación:** `support/backend/apps/knowledge/langchain_rag.py`.
   - **Funciones principales:** `get_store()`, `add_documents_from_synap_items()`, `get_retriever()`, `search_documents()`, `invoke_rag_chain()`, `is_langchain_rag_available()`.
   - Ingesta: conversión de ítems (text, source_id, metadata) a `Document` y `store.add_documents()` con IDs estables; embeddings vía OpenAI.
   - Filtros: `company_id` (global + empresa con `$or`) y `sistema` en metadata.
   - Cadena RAG: retriever → prompt template (contexto + pregunta, reglas en español) → ChatOpenAI; si no hay documentos se devuelve `None` para derivar a humano.

3. **Ingesta**
   - `support/backend/apps/api/views_knowledge.py`: `knowledge_ingest` y `sync_from_synap` usan `langchain_rag.add_documents_from_synap_items`.
   - `support/backend/apps/system_config/views.py`: acción de ingesta del RAG config usa el mismo flujo.
   - `support/backend/apps/knowledge/management/commands/sync_rag_from_synap.py`: usa `add_documents_from_synap_items`.
   - `support/backend/apps/api/views_cases.py`: al guardar respuesta como conocimiento se llama a `add_documents_from_synap_items`; ya no se usa el modelo `KnowledgeChunk` ni `knowledge_chunk_id` en la escritura (el campo en respuesta puede ser `null`).

4. **Copiloto**
   - `support/backend/apps/integrations/services.py`: `_openai_reply` usa `langchain_rag.invoke_rag_chain()`; si el RAG no está disponible o la cadena devuelve `None` (sin docs), se deriva a humano y se devuelve el mensaje fijo de derivación.

5. **Listado y búsqueda**
   - `knowledge_chunks_list`: devuelve `count=0`, `results=[]` y mensaje indicando que con RAG LangChain el listado completo no está disponible y se use la búsqueda.
   - `knowledge_search`: usa `langchain_rag.search_documents()`; respuesta con `chunk_id`, `text`, `score`, `metadata`, `source_type`, `source_id`. Si el RAG no está configurado devuelve 501.

6. **Eliminación de código propio**
   - **Modelo:** `support/backend/apps/knowledge/models.py`: eliminado `KnowledgeChunk`; el archivo queda con un comentario.
   - **Admin:** `support/backend/apps/knowledge/admin.py`: eliminado el registro de `KnowledgeChunk`.
   - **Servicios:** `support/backend/apps/knowledge/services.py`: reemplazado por un módulo que expone `is_embedding_configured()` usando `langchain_rag.is_langchain_rag_available()`.
   - **Tareas:** `support/backend/apps/knowledge/tasks.py`: `embed_chunk_task` es un stub que no realiza embedding (ingesta síncrona vía LangChain).
   - **Embedding:** eliminado `support/backend/apps/knowledge/embedding.py`.
   - **Settings:** eliminada la asignación de `EMBEDDING_FUNCTION` desde `embedding.py`.
   - **Migración:** `support/backend/apps/knowledge/migrations/0004_delete_knowledgechunk.py` ejecuta `DeleteModel("KnowledgeChunk")`.

7. **Tests y documentación**
   - **Tests:** `support/backend/apps/api/tests_smoke.py`: eliminado el uso de `KnowledgeChunk`; tests de búsqueda y multi-tenant mockean `langchain_rag`; test de sync mockea `add_documents_from_synap_items`.
   - **Documentación RAG (uso):** `support/docs/RAG_Y_SYNAP.md` actualizado: LangChain PGVector, ingesta síncrona, variables, implementación técnica, eliminación de tabla y servicios propios.
   - **README backend:** `support/backend/README.md`: actualizada la descripción de la app `knowledge`.

## Dónde está cada cosa

| Concepto | Ubicación |
| -------- | --------- |
| Store, retriever, cadena RAG | `support/backend/apps/knowledge/langchain_rag.py` |
| Vistas conocimiento (sync, ingest, search, list) | `support/backend/apps/api/views_knowledge.py` |
| Copiloto (uso de la cadena RAG) | `support/backend/apps/integrations/services.py` |
| Config RAG (ingesta desde UI) | `support/backend/apps/system_config/views.py` |
| Comando sync desde Synap | `support/backend/apps/knowledge/management/commands/sync_rag_from_synap.py` |
| Guardar respuesta como conocimiento | `support/backend/apps/api/views_cases.py` |
| Migración que elimina la tabla | `support/backend/apps/knowledge/migrations/0004_delete_knowledgechunk.py` |
| Documentación de uso del RAG | `support/docs/RAG_Y_SYNAP.md` |

## Comandos útiles

- Aplicar migración (eliminar tabla):  
  `docker exec Synap_app python manage.py migrate knowledge --noinput`
- Tests smoke (incl. RAG):  
  `docker exec Synap_app python manage.py test apps.api.tests_smoke`
- Cargar conocimiento desde Synap:  
  `docker exec Synap_app python manage.py sync_rag_from_synap [--company-id ID]`

## Referencias

- Plan de refactor: `.cursor/plans/refactor_rag_support_langchain_*.plan.md`
- Uso y configuración del RAG: [support/docs/RAG_Y_SYNAP.md](../../support/docs/RAG_Y_SYNAP.md)
- Política de documentación: [docs/general/POLITICA_DOCUMENTACION.md](../general/POLITICA_DOCUMENTACION.md)
