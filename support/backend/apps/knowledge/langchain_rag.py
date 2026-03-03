"""
RAG con LangChain: PGVector, ingesta, retriever con filtros y cadena LCEL.
Reemplazo del RAG propio (RetrievalService + OpenAI directo) por Opción A.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

# Colección/tabla fija para el vector store
COLLECTION_NAME = getattr(
    settings,
    "LANGCHAIN_PGVECTOR_COLLECTION_NAME",
    "support_rag",
)
EMBEDDING_DIMENSION = getattr(settings, "EMBEDDING_DIMENSION", 1536)
MAX_TOP_K = 50


def _pgvector_connection_string() -> str:
    """Construye la connection string para langchain-postgres (psycopg3)."""
    from urllib.parse import quote_plus

    db = settings.DATABASES.get("default") or {}
    if not db:
        raise ValueError("DATABASES['default'] no configurado")
    engine = db.get("ENGINE", "")
    if "postgresql" not in engine:
        raise ValueError("LangChain RAG requiere PostgreSQL como base por defecto")
    user = db.get("USER", "")
    password = db.get("PASSWORD", "") or ""
    host = db.get("HOST", "localhost")
    port = db.get("PORT", "5432")
    name = db.get("NAME", "")
    # psycopg3: postgresql+psycopg://user:password@host:port/dbname
    password_quoted = quote_plus(password)
    return f"postgresql+psycopg://{user}:{password_quoted}@{host}:{port}/{name}"


def _get_embeddings():
    """OpenAI Embeddings para el store (usa OPENAI_API_KEY de settings o de config IA)."""
    from langchain_openai import OpenAIEmbeddings

    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
    model = getattr(settings, "EMBEDDING_MODEL", None) or "text-embedding-3-small"
    return OpenAIEmbeddings(openai_api_key=api_key, model=model)


def is_langchain_rag_available() -> bool:
    """True si hay API key y conexión PostgreSQL para usar el RAG con LangChain."""
    if not (getattr(settings, "OPENAI_API_KEY", "") or "").strip():
        return False
    try:
        _pgvector_connection_string()
        return True
    except Exception:
        return False


def get_store():
    """
    Devuelve la instancia síncrona del vector store (PGVector).
    Crea la extensión y la colección si no existen.
    """
    from langchain_postgres import PGVector

    connection = _pgvector_connection_string()
    embeddings = _get_embeddings()
    return PGVector(
        embeddings=embeddings,
        connection=connection,
        collection_name=COLLECTION_NAME,
        use_jsonb=True,
        embedding_length=EMBEDDING_DIMENSION,
    )


def _item_to_document(
    item: dict,
    company_id: int | None,
    source_type: str,
) -> "Document":
    """Convierte un ítem (text, source_id, metadata) a Document de LangChain."""
    from langchain_core.documents import Document

    text = (item.get("text") or "").strip()
    source_id = str(item.get("source_id", ""))[:64]
    meta = dict(item.get("metadata") or {})
    meta["company_id"] = company_id
    meta["source_type"] = source_type
    meta["source_id"] = source_id
    return Document(page_content=text, metadata=meta)


def _document_id(item: dict, company_id: int | None, source_type: str, index: int) -> str:
    """ID estable para upsert: evita duplicados por (company_id, source_type, source_id)."""
    source_id = str(item.get("source_id", ""))[:64]
    raw = f"{company_id}:{source_type}:{source_id}:{index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def add_documents_from_synap_items(
    items: list[dict],
    company_id: int | None = None,
    source_type: str = "synap",
) -> tuple[int, int]:
    """
    Ingesta ítems (desde Synap o API) en el vector store.
    Cada ítem: { "text", "source_id"?, "metadata"? }.
    metadata puede incluir "sistema" (synap|administranet), "file", etc.
    Retorna (añadidos, total) aproximado; con IDs estables sobrescribe por id.
    """
    if not items:
        return 0, 0
    store = get_store()
    docs = []
    ids = []
    for i, item in enumerate(items):
        text = (item.get("text") or "").strip()
        if not text:
            continue
        doc = _item_to_document(item, company_id, source_type)
        docs.append(doc)
        ids.append(_document_id(item, company_id, source_type, i))
    if not docs:
        return 0, 0
    try:
        store.add_documents(docs, ids=ids)
        return len(docs), len(docs)
    except Exception as e:
        logger.exception("Error en add_documents_from_synap_items: %s", e)
        raise


def _build_filter(company_id: int | None, sistema: str | None) -> dict | None:
    """
    Filtro para retrieval: (company_id IS NULL OR company_id = X) y opcionalmente sistema.
    Formato LangChain: $or para global o empresa; $and si además hay sistema.
    """
    parts = []
    if company_id is not None:
        parts.append({"$or": [{"company_id": None}, {"company_id": company_id}]})
    if sistema:
        parts.append({"sistema": sistema})
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return {"$and": parts}


def get_retriever(
    company_id: int | None = None,
    sistema: str | None = None,
    top_k: int = 10,
):
    """
    Retriever sobre el store con filtros por company_id y sistema.
    top_k entre 1 y MAX_TOP_K.
    """
    k = min(max(1, top_k), MAX_TOP_K)
    store = get_store()
    filt = _build_filter(company_id, sistema)
    return store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k, "filter": filt} if filt else {"k": k},
    )


def search_documents(
    query: str,
    company_id: int | None = None,
    sistema: str | None = None,
    top_k: int = 10,
) -> list[tuple[Any, float]]:
    """
    Búsqueda por similitud con score (para API de búsqueda y para comprobar si hay docs).
    Retorna lista de (Document, score).
    """
    store = get_store()
    k = min(max(1, top_k), MAX_TOP_K)
    filt = _build_filter(company_id, sistema)
    try:
        return store.similarity_search_with_score(query, k=k, filter=filt)
    except Exception as e:
        logger.warning("search_documents falló: %s", e)
        return []


# Prompt y cadena RAG (LCEL)
RAG_SYSTEM_TEMPLATE = """Reglas estrictas (cumplir siempre):
- Respondé ÚNICAMENTE con lo que dice el 'Contexto de la base de conocimiento' anterior. No uses conocimiento general ni de otras plataformas.
- No inventes pasos, procedimientos ni listas que no estén escritos en ese contexto. Si el contexto no describe cómo hacer exactamente lo que pregunta el usuario, está prohibido dar pasos genéricos (ej. 'acceder al menú', 'ir a inventario').
- Si la respuesta a la pregunta NO está explícita en el contexto, tu única respuesta debe ser: que no tenés esa información en la base de conocimiento y que la consulta se derivará a un agente humano. No agregues sugerencias ni pasos inventados.
- La base de conocimiento es sobre Synap y AdministraNET. No des procedimientos genéricos de otros sistemas ni inventes pasos.
- Responde en el mismo idioma que el mensaje del usuario.
"""


def _format_docs(docs: list) -> str:
    """Formatea documentos para inyectar en el prompt."""
    return "\n\n---\n\n".join(d.page_content for d in docs)


def invoke_rag_chain(
    question: str,
    company_id: int | None,
    sistema: str | None,
    top_k: int,
    llm_config: dict,
    case_context: str | None = None,
    assistant_name: str | None = None,
) -> str | None:
    """
    Ejecuta la cadena RAG: retriever → contexto → prompt → LLM.
    Si no hay documentos recuperados, retorna None (el llamador debe derivar a humano).
    llm_config: dict con api_key, model, limits.max_tokens (de get_active_ia_config).
    """
    docs_with_score = search_documents(question, company_id=company_id, sistema=sistema, top_k=top_k)
    if not docs_with_score:
        return None
    docs = [d for d, _ in docs_with_score]
    context = _format_docs(docs)
    system = (
        (f"Tu nombre es «{assistant_name}». Cuando te pregunten quién sos, respondé solo con este nombre. " if assistant_name else "")
        + RAG_SYSTEM_TEMPLATE
        + (f" Contexto de caso: {case_context}." if case_context else "")
        + "\n\nContexto de la base de conocimiento (usar ÚNICAMENTE para responder):\n"
        + context
    )
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    api_key = llm_config.get("api_key") or ""
    model = (llm_config.get("model") or "gpt-4o-mini").strip() or "gpt-4o-mini"
    max_tokens = (llm_config.get("limits") or {}).get("max_tokens") or 1024
    llm = ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        max_tokens=max_tokens,
    )
    messages = [SystemMessage(content=system), HumanMessage(content=question)]
    try:
        response = llm.invoke(messages)
        return response.content.strip() if response and response.content else None
    except Exception as e:
        logger.exception("invoke_rag_chain LLM error: %s", e)
        return None
