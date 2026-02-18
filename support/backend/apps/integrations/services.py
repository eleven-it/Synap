"""Servicio copiloto: respuesta IA usando configuración activa (OpenAI) o stub."""
from __future__ import annotations

from apps.cases.models import Case
from django.contrib.auth import get_user_model


def copilot_reply(
    text: str,
    case: Case | None = None,
    user=None,
) -> tuple[str, str | None]:
    """
    Responde al mensaje del agente usando la configuración IA activa (global o por empresa).
    Si hay config activa con provider openai y api_key, llama a OpenAI Chat Completions.
    Si no, devuelve un stub e indica configurar IA en Configuración.
    Devuelve (respuesta_ia, sugerencia_respuesta para el usuario).
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
        return (stub, None)

    provider = (config.get("provider") or "").strip().lower()
    if provider == "openai":
        return _openai_reply(text, config, case=case)
    # Otros proveedores se pueden añadir aquí (anthropic, etc.)
    stub = (
        f"Proveedor «{provider or 'sin especificar'}» no implementado. "
        "Use OpenAI en Configuración → IA para respuestas reales."
    )
    return (stub, None)


def _openai_reply(text: str, config: dict, case: Case | None = None) -> tuple[str, str | None]:
    """Genera respuesta con OpenAI Chat Completions."""
    try:
        from openai import OpenAI
    except ImportError:
        return (
            "El paquete «openai» no está instalado. Ejecute: pip install openai",
            None,
        )

    api_key = config.get("api_key") or ""
    model = (config.get("model") or "gpt-4o-mini").strip() or "gpt-4o-mini"
    if not api_key:
        return (
            "Configuración IA sin API key. Añádala en Configuración → IA y guarde.",
            None,
        )

    client = OpenAI(api_key=api_key)
    system_content = (
        "Eres un asistente de soporte dentro del backoffice. "
        "Ayudas al agente humano con respuestas concisas y sugerencias de réplica al cliente. "
        "Responde en el mismo idioma que el mensaje del agente."
    )
    if case:
        system_content += (
            f" Contexto: caso {getattr(case, 'number_display', case.id)}; "
            "puedes usar este contexto para sugerir respuestas más relevantes."
        )

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
            return ("La IA no devolvió contenido.", None)
        reply = choice.message.content.strip()
        # Sugerencia corta para el agente (misma respuesta o resumen)
        suggestion = reply[:300] + ("…" if len(reply) > 300 else "") if reply else None
        return (reply, suggestion)
    except Exception as e:
        return (
            f"Error al llamar a la IA: {e!s}. Revise la API key y el modelo en Configuración → IA.",
            None,
        )
