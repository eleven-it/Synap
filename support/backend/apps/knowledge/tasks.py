"""Tareas Celery para conocimiento RAG. Con LangChain la ingesta es síncrona; este task es stub."""

from celery import shared_task


@shared_task(name="knowledge.embed_chunk", bind=True)
def embed_chunk_task(self, chunk_id: int) -> dict:
    """
    Stub: ya no se usa. El RAG usa LangChain PGVector y los embeddings se generan en add_documents.
    Se mantiene por si algún código encola por error; no hace nada.
    """
    return {"ok": True, "embedded": False, "reason": "deprecated_langchain_rag"}
