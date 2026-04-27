from __future__ import annotations

import json
from typing import Any

from django.db import IntegrityError

from ia.models import (
    AgentLearningExample,
    ExecutionStatus,
    LearningExampleSource,
    LearningExampleStatus,
)


class LearningCaptureService:
    """Captura turnos como ejemplos candidatos para revisión y fine-tuning externo."""

    @staticmethod
    def learning_config(agent) -> dict[str, Any]:
        cfg = agent.config if isinstance(agent.config, dict) else {}
        raw = cfg.get("learning")
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def should_capture(agent, execution_status: str) -> bool:
        cfg = LearningCaptureService.learning_config(agent)
        if not cfg.get("capture_successful_turns"):
            return False
        if execution_status == ExecutionStatus.SUCCESS:
            return True
        if cfg.get("include_partial_executions") and execution_status == ExecutionStatus.PARTIAL:
            return True
        return False

    @staticmethod
    def build_messages_payload(agent, *, user_text: str, assistant_text: str) -> list[dict[str, str]]:
        system_prompt = (
            (agent.system_prompt or agent.soul_summary or agent.description or agent.name or "").strip()
        )
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_text or ""})
        messages.append({"role": "assistant", "content": assistant_text or ""})
        return messages

    @staticmethod
    def record_turn_from_execution(
        *,
        agent,
        conversation,
        execution,
        user_message,
        assistant_message,
    ) -> AgentLearningExample | None:
        if not LearningCaptureService.should_capture(agent, execution.status):
            return None

        messages_payload = LearningCaptureService.build_messages_payload(
            agent,
            user_text=user_message.content or "",
            assistant_text=assistant_message.content or "",
        )
        system_snapshot = (agent.system_prompt or "").strip()

        try:
            return AgentLearningExample.objects.create(
                agent=agent,
                conversation=conversation,
                execution=execution,
                user_message=user_message,
                assistant_message=assistant_message,
                source=LearningExampleSource.AUTO_SUCCESS,
                status=LearningExampleStatus.PENDING,
                messages_payload=messages_payload,
                system_prompt_snapshot=system_snapshot,
                metadata={
                    "model_name": execution.model_name or "",
                    "task_type": execution.task_type or "",
                },
            )
        except IntegrityError:
            return AgentLearningExample.objects.filter(execution=execution).first()


class LearningExportService:
    """Serialización de ejemplos a JSONL (formato chat, compatible con fine-tuning OpenAI)."""

    @staticmethod
    def example_to_jsonl_object(example: AgentLearningExample) -> dict[str, Any]:
        return {"messages": example.messages_payload or []}

    @staticmethod
    def render_jsonl_line(example: AgentLearningExample) -> str:
        return json.dumps(LearningExportService.example_to_jsonl_object(example), ensure_ascii=False)
