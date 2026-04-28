from __future__ import annotations

from ia.models import ProviderKind


PROVIDER_PRESETS = {
    ProviderKind.OPENAI: {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "supports_structured_output": True,
        "supports_tool_use": True,
        "supports_streaming": True,
        "supports_vision": True,
        "available_models": [
            "gpt-5.4",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4o",
            "gpt-4o-mini",
        ],
        "recommended_model": "gpt-4.1",
    },
    ProviderKind.ANTHROPIC: {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "supports_structured_output": True,
        "supports_tool_use": True,
        "supports_streaming": True,
        "supports_vision": True,
        "available_models": [
            "claude-sonnet-4-5",
            "claude-sonnet-4-6",
            "claude-opus-4-6",
        ],
        "recommended_model": "claude-sonnet-4-6",
    },
    ProviderKind.OPENAI_COMPATIBLE: {
        "name": "OpenAI-Compatible",
        "base_url": "",
        "supports_structured_output": True,
        "supports_tool_use": True,
        "supports_streaming": True,
        "supports_vision": False,
        "available_models": [
            "modelo-compatible-1",
            "modelo-compatible-2",
        ],
        "recommended_model": "modelo-compatible-1",
    },
    ProviderKind.LOCAL: {
        "name": "Local",
        "base_url": "http://host.docker.internal:11434/v1",
        "supports_structured_output": False,
        "supports_tool_use": False,
        "supports_streaming": False,
        "supports_vision": False,
        "available_models": [
            "llama3.1:8b",
            "qwen2.5:7b",
            "mistral:7b",
        ],
        "recommended_model": "llama3.1:8b",
    },
}


def get_provider_preset(provider_kind: str) -> dict:
    return PROVIDER_PRESETS.get(provider_kind, {})


def get_provider_models(provider) -> list[str]:
    if provider and provider.available_models:
        return list(provider.available_models)
    preset = get_provider_preset(getattr(provider, "provider_kind", None))
    return list(preset.get("available_models", []))


def get_recommended_model(provider) -> str:
    models = get_provider_models(provider)
    if getattr(provider, "available_models", None):
        return models[0] if models else ""
    preset = get_provider_preset(getattr(provider, "provider_kind", None))
    return preset.get("recommended_model", models[0] if models else "")


def apply_provider_preset(provider) -> None:
    preset = get_provider_preset(provider.provider_kind)
    if not preset:
        return
    if not provider.name:
        provider.name = preset.get("name", provider.name)
    if not provider.base_url:
        provider.base_url = preset.get("base_url", provider.base_url)
    if not provider.available_models:
        provider.available_models = list(preset.get("available_models", []))
    provider.supports_structured_output = preset.get("supports_structured_output", provider.supports_structured_output)
    provider.supports_tool_use = preset.get("supports_tool_use", provider.supports_tool_use)
    provider.supports_streaming = preset.get("supports_streaming", provider.supports_streaming)
    provider.supports_vision = preset.get("supports_vision", provider.supports_vision)
