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
    Responde solo con información del RAG. Si no hay contexto RAG, no llama al LLM,
    devuelve mensaje de derivación y deriva el caso a humano.
    """
    try:
        from openai import OpenAI
    except ImportError:
        return (
            "El paquete «openai» no está instalado. Ejecute: pip install openai",
            None,
            False,
        )

    api_key = config.get("api_key") or ""
    model = (config.get("model") or "gpt-4o-mini").strip() or "gpt-4o-mini"
    if not api_key:
        return (
            "Configuración IA sin API key. Añádala en Configuración → IA y guarde.",
            None,
            False,
        )

    company_id = case.company_id if case else None
    from apps.system_config.services import get_branding_config, get_rag_config
    from apps.knowledge.services import RetrievalService, is_embedding_configured

    rag_config = get_rag_config(company_id)
    has_rag_available = bool(rag_config and is_embedding_configured())
    chunks: list = []
    if has_rag_available:
        retrieval = RetrievalService(top_k=rag_config.get("top_k") or 10)
        chunks = retrieval.search(
            query=text,
            company_id=company_id,
            top_k=rag_config.get("top_k"),
            include_global=True,
            sistema=sistema,
        )

    # Sin RAG o sin chunks relevantes: no llamar al LLM, derivar a humano
    if not has_rag_available or not chunks:
        if case:
            from apps.cases.services import derive_case_to_human
            actor_id = getattr(user, "id", None) if user else None
            derive_case_to_human(case, actor_id=actor_id)
        return (MENSAJE_DERIVADO_A_HUMANO, None, True)

    # Hay contexto RAG: responder solo con ese contexto, sin inventar
    rag_context = (
        "\n\nContexto de la base de conocimiento (usar ÚNICAMENTE para responder):\n"
        + "\n---\n".join(c.get("text", "") for c in chunks)
    )

    system_content = (
        "Reglas estrictas (cumplir siempre):\n"
        "- Respondé ÚNICAMENTE con lo que dice el 'Contexto de la base de conocimiento' anterior. "
        "No uses conocimiento general ni de otras plataformas.\n"
        "- No inventes pasos, procedimientos ni listas que no estén escritos en ese contexto. "
        "Si el contexto no describe cómo hacer exactamente lo que pregunta el usuario, está prohibido dar pasos genéricos (ej. 'acceder al menú', 'ir a inventario').\n"
        "- Si la respuesta a la pregunta NO está explícita en el contexto, tu única respuesta debe ser: "
        "que no tenés esa información en la base de conocimiento y que la consulta se derivará a un agente humano. "
        "No agregues sugerencias ni pasos inventados.\n"
        "- La base de conocimiento es sobre Synap y AdministraNET. No des procedimientos genéricos de otros sistemas ni inventes pasos.\n"
        "- Responde en el mismo idioma que el mensaje del usuario."
    )
    branding = get_branding_config(company_id)
    if branding:
        name = (branding.get("assistant_name") or "").strip()
        if name:
            system_content = (
                f"Tu nombre es «{name}». Cuando te pregunten quién sos, respondé solo con este nombre. "
                + system_content
            )
    if case:
        system_content += (
            f" Contexto de caso: {getattr(case, 'number_display', case.id)}."
        )
    system_content += rag_context

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": text},
            ],
            max_tokens=config.get("limits", {}).get("max_tokens") or 1024,
        )
        choice = response.choices[0] if response.choices else None
        if not choice or not choice.message or not choice.message.content:
            return ("La IA no devolvió contenido.", None, False)
        reply = choice.message.content.strip()
        suggestion = reply[:300] + ("…" if len(reply) > 300 else "") if reply else None
        return (reply, suggestion, False)
    except Exception as e:
        return (
            f"Error al llamar a la IA: {e!s}. Revise la API key y el modelo en Configuración → IA.",
            None,
            False,
        )
