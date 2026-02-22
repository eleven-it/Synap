"""
Servicios RAG: compatibilidad con LangChain.
El RAG real está en apps.knowledge.langchain_rag (PGVector, ingesta, retriever, cadena LCEL).
"""

from apps.knowledge import langchain_rag


def is_embedding_configured() -> bool:
    """True si el RAG con LangChain está disponible (OPENAI_API_KEY y PostgreSQL)."""
    return langchain_rag.is_langchain_rag_available()
