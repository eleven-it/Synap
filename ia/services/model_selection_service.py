from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SelectedModel:
    provider_name: str | None
    provider_kind: str | None
    model_name: str
    task_type: str
    used_fallback: bool = False


class ModelSelectionService:
    """Selecciona proveedor/modelo según tarea y configuración del agente."""

    @staticmethod
    def select(agent, task_type: str = "conversation") -> SelectedModel:
        provider = agent.default_provider
        model_name = agent.default_model_name or ""
        used_fallback = False

        if task_type == "tool_use" and agent.tool_use_model_name:
            model_name = agent.tool_use_model_name
        elif task_type == "memory_write" and agent.memory_write_model_name:
            model_name = agent.memory_write_model_name
        elif task_type == "fast" and agent.fast_model_name:
            model_name = agent.fast_model_name

        if not model_name and agent.fallback_provider and agent.fallback_model_name:
            provider = agent.fallback_provider
            model_name = agent.fallback_model_name
            used_fallback = True

        if not model_name:
            model_name = "sin-modelo-configurado"

        return SelectedModel(
            provider_name=provider.name if provider else None,
            provider_kind=provider.provider_kind if provider else None,
            model_name=model_name,
            task_type=task_type,
            used_fallback=used_fallback,
        )
