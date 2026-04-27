from __future__ import annotations

from django.http import Http404
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ia.models import AgentConversation, AgentDefinition, AgentLearningExample, LearningExampleSource, LearningExampleStatus
from ia.serializers import (
    AgentConversationSerializer,
    AgentDefinitionSerializer,
    AgentMemoryItemSerializer,
    ConversationCreateSerializer,
    ConversationMessageCreateSerializer,
    LearningExampleReviewSerializer,
)
from ia.services.memory_service import MemoryService
from ia.services.orchestrator import AgentOrchestrator
from ia.services.policy_gate import PolicyGate


def _get_empresa_for_request(request):
    return getattr(request.user, "empresa_activa", None)


def _get_agent_for_request(request, slug: str) -> AgentDefinition:
    empresa = _get_empresa_for_request(request)
    queryset = AgentDefinition.objects.filter(slug=slug, is_active=True)
    if empresa:
        queryset = queryset.filter(Q(empresa=empresa) | Q(empresa__isnull=True)).order_by("-empresa_id")
    else:
        queryset = queryset.filter(empresa__isnull=True)
    agent = queryset.first()
    if not agent:
        raise Http404("Agente no encontrado.")
    return agent


def _conversation_belongs_to_request(conversation: AgentConversation, policy_context) -> bool:
    if conversation.empresa_id and policy_context.empresa and conversation.empresa_id != policy_context.empresa.id:
        return False
    if conversation.owner_user_id and policy_context.owner_user:
        return conversation.owner_user_id == policy_context.owner_user.id
    if conversation.owner_legacy_user_id and policy_context.legacy_user_id:
        return conversation.owner_legacy_user_id == policy_context.legacy_user_id
    return conversation.owner_user_id is None and conversation.owner_legacy_user_id is None


class AgentCatalogAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        PolicyGate.ensure_authenticated(request)
        empresa = _get_empresa_for_request(request)
        agents = AgentDefinition.objects.filter(is_active=True)
        if empresa:
            agents = agents.filter(Q(empresa=empresa) | Q(empresa__isnull=True)).order_by("-empresa_id", "name")
        else:
            agents = agents.filter(empresa__isnull=True).order_by("name")

        deduped_by_slug = {}
        for agent in agents:
            if agent.slug in deduped_by_slug:
                continue
            if agent.required_permission and not PolicyGate.has_permission(request.user, agent.required_permission):
                continue
            deduped_by_slug[agent.slug] = agent

        visible_agents = list(deduped_by_slug.values())
        return Response(AgentDefinitionSerializer(visible_agents, many=True).data)


class AgentCapabilitiesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug, *args, **kwargs):
        agent = _get_agent_for_request(request, slug)
        PolicyGate.ensure_agent_access(request, agent)
        serializer = AgentDefinitionSerializer(agent)
        return Response(serializer.data)


class AgentConversationCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent = _get_agent_for_request(request, serializer.validated_data["agent_slug"])
        context = PolicyGate.ensure_agent_access(request, agent)

        conversation = AgentConversation.objects.create(
            agent=agent,
            empresa=context.empresa,
            owner_user=context.owner_user,
            owner_legacy_user_id=context.legacy_user_id,
            owner_legacy_user_code=context.legacy_user_code,
            title=serializer.validated_data.get("title", ""),
            channel=serializer.validated_data.get("channel", "web"),
            metadata=serializer.validated_data.get("metadata", {}),
        )
        return Response(AgentConversationSerializer(conversation).data, status=201)


class AgentConversationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_uuid, *args, **kwargs):
        PolicyGate.ensure_authenticated(request)
        context = PolicyGate.build_context(request)
        conversation = get_object_or_404(
            AgentConversation.objects.select_related("agent", "agent__default_provider").prefetch_related("messages"),
            conversation_uuid=conversation_uuid,
        )
        if not _conversation_belongs_to_request(conversation, context):
            raise Http404("Conversación no encontrada.")
        return Response(AgentConversationSerializer(conversation).data)


class AgentConversationMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_uuid, *args, **kwargs):
        serializer = ConversationMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = get_object_or_404(
            AgentConversation.objects.select_related("agent", "agent__default_provider"),
            conversation_uuid=conversation_uuid,
        )
        context = PolicyGate.ensure_agent_access(request, conversation.agent)
        if not _conversation_belongs_to_request(conversation, context):
            raise Http404("Conversación no encontrada.")

        result = AgentOrchestrator(
            agent=conversation.agent,
            conversation=conversation,
            policy_context=context,
        ).handle_user_message(serializer.validated_data["message"])

        return Response(
            {
                "conversation_uuid": str(conversation.conversation_uuid),
                "assistant_message": result.assistant_message.content,
                "phase": result.assistant_message.structured_content.get("phase"),
                "execution_status": result.execution.status,
                "selected_model": {
                    "provider_name": result.selected_model.provider_name,
                    "provider_kind": result.selected_model.provider_kind,
                    "model_name": result.selected_model.model_name,
                    "task_type": result.selected_model.task_type,
                    "used_fallback": result.selected_model.used_fallback,
                },
                "memory_hits": len(result.memories_used),
                "execution_id": result.execution.id,
                "learning_example_id": result.learning_example.id if result.learning_example else None,
            },
            status=201,
        )


class AgentLearningExampleReviewAPIView(APIView):
    """Aprueba, rechaza o marca como exportado un ejemplo de aprendizaje del hilo."""

    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_uuid, pk, *args, **kwargs):
        serializer = LearningExampleReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        example = get_object_or_404(
            AgentLearningExample.objects.select_related("agent", "conversation"),
            pk=pk,
        )
        if str(example.conversation.conversation_uuid) != str(conversation_uuid):
            raise Http404("Ejemplo no encontrado.")
        context = PolicyGate.ensure_agent_access(request, example.agent)
        if not _conversation_belongs_to_request(example.conversation, context):
            raise Http404("Ejemplo no encontrado.")

        action = serializer.validated_data["action"]
        notes = serializer.validated_data.get("notes") or ""
        corrected = (serializer.validated_data.get("corrected_assistant_text") or "").strip()

        if action == "approve":
            new_status = LearningExampleStatus.APPROVED
            if corrected:
                payload = list(example.messages_payload or [])
                for i in range(len(payload) - 1, -1, -1):
                    if payload[i].get("role") == "assistant":
                        payload[i] = {**payload[i], "content": corrected}
                        break
                example.messages_payload = payload
                example.source = LearningExampleSource.USER_CORRECTION
        elif action == "reject":
            new_status = LearningExampleStatus.REJECTED
        else:
            new_status = LearningExampleStatus.EXPORTED

        example.status = new_status
        example.review_notes = notes
        example.reviewed_at = timezone.now()
        example.reviewed_by = request.user if request.user.is_authenticated else None
        example.save()

        return Response(
            {
                "id": example.id,
                "status": example.status,
                "source": example.source,
            },
            status=200,
        )


class AgentMemoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug, *args, **kwargs):
        agent = _get_agent_for_request(request, slug)
        context = PolicyGate.ensure_agent_access(request, agent)
        try:
            limit = min(int(request.query_params.get("limit", 10)), 25)
        except (TypeError, ValueError):
            limit = 10
        items = MemoryService.get_relevant_memory(
            agent,
            context,
            request.query_params.get("q", ""),
            limit=limit,
        )
        return Response(AgentMemoryItemSerializer(items, many=True).data)
