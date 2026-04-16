from __future__ import annotations

import time
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from ia.models import AgentExecution, AgentMessage, ExecutionStatus, MessageRole
from ia.services.llm_gateway import LlmGatewayError, LlmGatewayService
from ia.services.memory_service import MemoryService
from ia.services.model_selection_service import ModelSelectionService
from ia.services.report_agent_service import ReportAgentService


@dataclass
class OrchestrationResult:
    conversation: object
    execution: AgentExecution
    user_message: AgentMessage
    assistant_message: AgentMessage
    memories_used: list
    selected_model: object


class AgentOrchestrator:
    """
    Esqueleto inicial del orquestador.

    En esta fase ya intenta llamar al proveedor configurado. Si falta configuración
    o falla el proveedor, degrada a una respuesta segura de bootstrap.
    """

    def __init__(self, *, agent, conversation, policy_context):
        self.agent = agent
        self.conversation = conversation
        self.policy_context = policy_context

    def handle_user_message(self, message_text: str) -> OrchestrationResult:
        started = time.perf_counter()
        selected_model = ModelSelectionService.select(self.agent, task_type="conversation")
        memories = MemoryService.get_relevant_memory(
            self.agent,
            self.policy_context,
            message_text,
            limit=5,
        )

        with transaction.atomic():
            user_message = AgentMessage.objects.create(
                conversation=self.conversation,
                role=MessageRole.USER,
                content=message_text,
                structured_content={},
                metadata={},
            )

            response_text, response_payload, token_usage, execution_status = self._generate_response(
                message_text,
                memories,
                selected_model,
            )

            assistant_message = AgentMessage.objects.create(
                conversation=self.conversation,
                role=MessageRole.ASSISTANT,
                content=response_text,
                structured_content={
                    "phase": response_payload.get("phase", "runtime"),
                    "memory_hits": len(memories),
                    "selected_model": selected_model.model_name,
                    "provider_kind": selected_model.provider_kind,
                },
                metadata={},
                prompt_tokens=token_usage["prompt_tokens"],
                completion_tokens=token_usage["completion_tokens"],
                total_tokens=token_usage["total_tokens"],
            )

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            execution = AgentExecution.objects.create(
                conversation=self.conversation,
                agent=self.agent,
                request_message=user_message,
                response_message=assistant_message,
                provider_config=self.agent.default_provider,
                model_name=selected_model.model_name,
                task_type="conversation",
                status=execution_status,
                request_payload={"message": message_text},
                response_payload=response_payload,
                memory_items_read=len(memories),
                memory_items_written=0,
                prompt_tokens=token_usage["prompt_tokens"],
                completion_tokens=token_usage["completion_tokens"],
                total_tokens=token_usage["total_tokens"],
                duration_ms=elapsed_ms,
            )

            self.conversation.last_message_at = timezone.now()
            if not self.conversation.title:
                self.conversation.title = message_text[:80]
            self.conversation.save(update_fields=["last_message_at", "title", "updated_at"])

        return OrchestrationResult(
            conversation=self.conversation,
            execution=execution,
            user_message=user_message,
            assistant_message=assistant_message,
            memories_used=memories,
            selected_model=selected_model,
        )

    def _generate_response(self, message_text: str, memories: list, selected_model):
        if self.agent.domain == "reportes" or self.agent.slug == "asistente-reportes":
            report_result = ReportAgentService(
                agent=self.agent,
                policy_context=self.policy_context,
                selected_model=selected_model,
            ).handle_query(message_text)
            return (
                report_result.answer,
                report_result.response_payload,
                report_result.token_usage,
                report_result.execution_status,
            )

        provider = self.agent.default_provider
        try:
            llm_response = LlmGatewayService.generate_text(
                provider_config=provider,
                model_name=selected_model.model_name,
                system_prompt=self.agent.system_prompt or self.agent.soul_summary or self.agent.description or self.agent.name,
                user_message=message_text,
                memories=memories,
                max_output_tokens=self.agent.max_output_tokens,
                temperature=self._get_temperature(),
            )
            return (
                llm_response["text"].strip() or self._build_placeholder_response(message_text, memories, selected_model),
                {
                    "phase": "provider_runtime",
                    "memory_hits": len(memories),
                    "provider_kind": selected_model.provider_kind,
                    "provider_name": selected_model.provider_name,
                    "raw_preview": str(llm_response.get("raw", {}))[:1000],
                },
                {
                    "prompt_tokens": llm_response.get("prompt_tokens", 0),
                    "completion_tokens": llm_response.get("completion_tokens", 0),
                    "total_tokens": llm_response.get("total_tokens", 0),
                },
                ExecutionStatus.SUCCESS,
            )
        except LlmGatewayError as exc:
            fallback_text = self._build_placeholder_response(message_text, memories, selected_model, error_message=str(exc))
            return (
                fallback_text,
                {
                    "phase": "bootstrap_fallback",
                    "memory_hits": len(memories),
                    "provider_kind": selected_model.provider_kind,
                    "provider_name": selected_model.provider_name,
                    "error": str(exc),
                },
                {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
                ExecutionStatus.PARTIAL,
            )

    def _get_temperature(self) -> float:
        raw_temperature = None
        if isinstance(self.agent.config, dict):
            raw_temperature = self.agent.config.get("temperature")
        try:
            return float(raw_temperature if raw_temperature is not None else 0.2)
        except (TypeError, ValueError):
            return 0.2

    def _build_placeholder_response(self, message_text: str, memories: list, selected_model, error_message: str = "") -> str:
        memory_line = (
            f"Recuperé {len(memories)} elemento(s) de memoria relevante."
            if memories
            else "No encontré memoria relevante para esta consulta."
        )
        provider_label = selected_model.provider_kind or "sin proveedor"
        error_block = f"\nMotivo del fallback seguro: {error_message}\n" if error_message else "\n"
        return (
            f"{self.agent.name} quedó inicializado en modo bootstrap.\n\n"
            f"Consulta recibida: {message_text}\n"
            f"{memory_line}\n"
            f"Modelo seleccionado para esta tarea: {selected_model.model_name} ({provider_label}).\n\n"
            f"{error_block}"
            "La infraestructura persistente de conversación, memoria y selección de modelo ya quedó disponible. "
            "El siguiente paso es conectar este orquestador con proveedores LLM reales y herramientas seguras del dominio."
        )
