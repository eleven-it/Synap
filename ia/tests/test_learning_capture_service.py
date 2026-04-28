import json

from django.test import TestCase

from ia.models import (
    AgentConversation,
    AgentDefinition,
    AgentExecution,
    AgentLearningExample,
    AgentMessage,
    ExecutionStatus,
    LearningExampleStatus,
    MessageRole,
)
from ia.services.learning_capture_service import LearningCaptureService, LearningExportService


class LearningCaptureServiceTests(TestCase):
    def test_no_captura_si_config_desactivada(self):
        agent = AgentDefinition.objects.create(slug="learn-a", name="Learn A", config={})
        conv = AgentConversation.objects.create(agent=agent)
        um = AgentMessage.objects.create(conversation=conv, role=MessageRole.USER, content="Hola")
        am = AgentMessage.objects.create(conversation=conv, role=MessageRole.ASSISTANT, content="Hola.")
        ex = AgentExecution.objects.create(
            conversation=conv,
            agent=agent,
            request_message=um,
            response_message=am,
            status=ExecutionStatus.SUCCESS,
        )
        out = LearningCaptureService.record_turn_from_execution(
            agent=agent,
            conversation=conv,
            execution=ex,
            user_message=um,
            assistant_message=am,
        )
        self.assertIsNone(out)
        self.assertEqual(AgentLearningExample.objects.count(), 0)

    def test_captura_turno_exitoso_cuando_esta_activado(self):
        agent = AgentDefinition.objects.create(
            slug="learn-b",
            name="Learn B",
            system_prompt="Eres un asistente de prueba.",
            config={"learning": {"capture_successful_turns": True}},
        )
        conv = AgentConversation.objects.create(agent=agent)
        um = AgentMessage.objects.create(conversation=conv, role=MessageRole.USER, content="¿Qué hora es?")
        am = AgentMessage.objects.create(conversation=conv, role=MessageRole.ASSISTANT, content="No tengo reloj.")
        ex = AgentExecution.objects.create(
            conversation=conv,
            agent=agent,
            request_message=um,
            response_message=am,
            status=ExecutionStatus.SUCCESS,
        )
        example = LearningCaptureService.record_turn_from_execution(
            agent=agent,
            conversation=conv,
            execution=ex,
            user_message=um,
            assistant_message=am,
        )
        self.assertIsNotNone(example)
        self.assertEqual(example.status, LearningExampleStatus.PENDING)
        self.assertEqual(len(example.messages_payload), 3)
        self.assertEqual(example.messages_payload[0]["role"], "system")
        self.assertEqual(example.messages_payload[1]["content"], "¿Qué hora es?")
        self.assertEqual(example.messages_payload[2]["role"], "assistant")

    def test_export_jsonl_line_es_objeto_con_messages(self):
        agent = AgentDefinition.objects.create(slug="learn-c", name="Learn C", config={})
        conv = AgentConversation.objects.create(agent=agent)
        um = AgentMessage.objects.create(conversation=conv, role=MessageRole.USER, content="u")
        am = AgentMessage.objects.create(conversation=conv, role=MessageRole.ASSISTANT, content="a")
        ex = AgentExecution.objects.create(
            conversation=conv,
            agent=agent,
            request_message=um,
            response_message=am,
            status=ExecutionStatus.SUCCESS,
        )
        ex2 = AgentLearningExample.objects.create(
            agent=agent,
            conversation=conv,
            execution=ex,
            user_message=um,
            assistant_message=am,
            messages_payload=[
                {"role": "user", "content": "u"},
                {"role": "assistant", "content": "a"},
            ],
        )
        line = LearningExportService.render_jsonl_line(ex2)
        data = json.loads(line)
        self.assertIn("messages", data)
        self.assertEqual(len(data["messages"]), 2)
