"""
Interfaces para el agente IA: AgentService, RetrievalService, ToolsService.
Stubs/dummy para no acoplar a un LLM real en el primer despliegue.
"""
from typing import Any
from dataclasses import dataclass


@dataclass
class ToolResult:
    success: bool
    message: str
    data: dict | None = None


class RetrievalServiceInterface:
    """Retrieval RAG: query + empresa_id -> fragmentos."""

    def search(self, query: str, company_id: int | None, top_k: int = 5, include_global: bool = True) -> list[dict]:
        """Busca fragmentos relevantes. Stub: lista vacía."""
        return []


class ToolsServiceInterface:
    """Registry de tools para el LLM. Ejecución con idempotencia."""

    def execute(self, tool_name: str, params: dict, context: dict) -> ToolResult:
        """Ejecuta una tool. Stub: éxito genérico."""
        return ToolResult(success=True, message="OK (stub)", data={})


class AgentServiceInterface:
    """Orquestador: mensaje usuario + case_id -> respuesta y/o acciones."""

    def process_message(self, case_id: int | None, user_message: str, context: dict) -> tuple[str, dict]:
        """Procesa mensaje y devuelve (respuesta_texto, acciones_ejecutadas). Stub."""
        return "Respuesta stub del agente IA. Conecte un LLM real.", {}
