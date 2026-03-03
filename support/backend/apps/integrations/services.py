"""Servicio copiloto: respuesta IA usando configuración activa (OpenAI) o stub."""
from __future__ import annotations

from apps.cases.models import Case
from django.contrib.auth import get_user_model

# Mensaje estándar cuando no hay información en RAG: se deriva a humano
MENSAJE_DERIVADO_A_HUMANO = (
    "No encontré información en la base de conocimiento para responder tu consulta. "
    "Se ha derivado tu caso a un agente humano; te atenderá a la brevedad."
)


def copilot_reply(
    text: str,
    case: Case | None = None,
    user=None,
    sistema: str | None = None,
) -> tuple[str, str | None, bool]:
    """
    Responde al mensaje usando solo información del RAG (base de conocimiento).
    Si no hay contexto RAG o la respuesta no está en el RAG, no se inventan datos:
    se devuelve mensaje de derivación y se deriva el caso a un agente humano.
    sistema: opcional "synap" | "administranet" para filtrar RAG por metadata.sistema.
    Devuelve (respuesta_ia, sugerencia_respuesta, derivado_a_humano).
    """
    company_id = case.company_id if case else None
    from apps.system_config.services import get_active_ia_config

    config = get_active_ia_config(company_id=company_id)

    if not config or not config.get("api_key"):
        stub = (
            "El agente IA no está configurado. Un administrador puede activarlo en "
            "**Configuración** → **IA**: añadir proveedor (p. ej. OpenAI), modelo y API key, "
            "y poner el estado en **Activo**."
        )
        return (stub, None, False)

    provider = (config.get("provider") or "").strip().lower()
    if provider == "openai":
        return _openai_reply(text, config, case=case, user=user, sistema=sistema)
    # Otros proveedores se pueden añadir aquí (anthropic, etc.)
    stub = (
        f"Proveedor «{provider or 'sin especificar'}» no implementado. "
        "Use OpenAI en Configuración → IA para respuestas reales."
    )
    return (stub, None, False)


def _openai_reply(
    text: str,
    config: dict,
    case: Case | None = None,
    user=None,
    sistema: str | None = None,
) -> tuple[str, str | None, bool]:
    """
    Responde solo con información del RAG (cadena LangChain).
    Si no hay contexto RAG, no llama al LLM, devuelve mensaje de derivación y deriva el caso a humano.
    """
    company_id = case.company_id if case else None
    from apps.system_config.services import get_branding_config, get_rag_config
    from apps.knowledge import langchain_rag

    rag_config = get_rag_config(company_id)
    has_rag_available = bool(rag_config and langchain_rag.is_langchain_rag_available())
    if not has_rag_available:
        if case:
            from apps.cases.services import derive_case_to_human
            actor_id = getattr(user, "id", None) if user else None
            derive_case_to_human(case, actor_id=actor_id)
        return (MENSAJE_DERIVADO_A_HUMANO, None, True)

    top_k = rag_config.get("top_k") or 10
    case_context = str(getattr(case, "number_display", case.id)) if case else None
    branding = get_branding_config(company_id)
    assistant_name = (branding.get("assistant_name") or "").strip() if branding else None

    reply = langchain_rag.invoke_rag_chain(
        question=text,
        company_id=company_id,
        sistema=sistema,
        top_k=top_k,
        llm_config=config,
        case_context=case_context,
        assistant_name=assistant_name,
    )
    if reply is None:
        if case:
            from apps.cases.services import derive_case_to_human
            actor_id = getattr(user, "id", None) if user else None
            derive_case_to_human(case, actor_id=actor_id)
        return (MENSAJE_DERIVADO_A_HUMANO, None, True)
    suggestion = reply[:300] + ("…" if len(reply) > 300 else "") if reply else None
    return (reply, suggestion, False)
