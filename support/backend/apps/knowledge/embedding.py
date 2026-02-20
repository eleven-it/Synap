"""
Función de embedding para RAG usando OpenAI.
Requiere OPENAI_API_KEY en settings (o env).
"""
import logging
from typing import List

from django.conf import settings

logger = logging.getLogger(__name__)

# Modelo por defecto: 1536 dimensiones (compatible con EMBEDDING_DIMENSION)
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def openai_embedding(text: str) -> List[float] | None:
    """
    Devuelve el vector de embedding para el texto usando OpenAI.
    Si no hay OPENAI_API_KEY configurada, retorna None.
    """
    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
    if not api_key or not (text or "").strip():
        return None
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai no instalado; pip install openai")
        return None
    client = OpenAI(api_key=api_key)
    model = getattr(settings, "EMBEDDING_MODEL", None) or DEFAULT_EMBEDDING_MODEL
    resp = client.embeddings.create(
        model=model,
        input=(text or "").strip()[:8192],
    )
    if not resp.data:
        return None
    return resp.data[0].embedding