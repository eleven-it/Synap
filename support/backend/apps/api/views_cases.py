"""API casos: lista, detalle, PATCH, timeline, adjuntos, respuesta."""
from django.urls import path
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from apps.cases.models import Case, Message
from apps.cases.services import transition_case_status, assign_case
from apps.cases.domain import can_transition
from apps.core.exceptions import CaseStateTransitionError
from .serializers_cases import (
    CaseListSerializer,
    CaseDetailSerializer,
    MessageSerializer,
    CaseSummarySerializer,
    CasePatchSerializer,
)
from apps.api.permissions import IsAgentOrAdmin
from apps.core.idempotency import (
    get_idempotency_key,
    get_stored_idempotent_response,
    store_idempotent_response,
)


class CaseListView(ListAPIView):
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]
    serializer_class = CaseListSerializer
    filterset_fields = ["status", "company", "assigned_to"]
    ordering_fields = ["created_at", "updated_at", "number_display"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Case.objects.select_related("company", "assigned_to").all()


class CaseDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get(self, request, pk):
        case = get_object_or_404(Case.objects.select_related("company", "assigned_to"), pk=pk)
        return Response(CaseDetailSerializer(case).data)

    def patch(self, request, pk):
        case = get_object_or_404(Case, pk=pk)
        action_key = get_idempotency_key(request)
        if action_key:
            stored = get_stored_idempotent_response(case.id, action_key, request.user.id)
            if stored:
                status_code, payload = stored
                return Response(payload, status=status_code)
        ser = CasePatchSerializer(data=request.data, partial=True)
        if not ser.is_valid():
            return Response(
                {"code": "VALIDATION_ERROR", "message": "Datos inválidos", "details": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            if "assigned_to_id" in ser.validated_data and ser.validated_data["assigned_to_id"]:
                assign_case(case, ser.validated_data["assigned_to_id"], actor_id=request.user.id)
            if "status" in ser.validated_data:
                transition_case_status(
                    case,
                    ser.validated_data["status"],
                    actor_id=request.user.id,
                )
        except CaseStateTransitionError as e:
            return Response(
                {"code": e.code, "message": e.message, "details": e.details},
                status=status.HTTP_409_CONFLICT,
            )
        case.refresh_from_db()
        data = CaseDetailSerializer(case).data
        if action_key:
            store_idempotent_response(case.id, action_key, request.user.id, status.HTTP_200_OK, data)
        return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAgentOrAdmin])
def case_timeline(request, pk):
    """Timeline: mensajes + resúmenes ordenados por tiempo."""
    case = get_object_or_404(Case, pk=pk)
    messages = list(case.messages.all().order_by("created_at"))
    summaries = list(case.summaries.all().order_by("created_at"))
    return Response({
        "messages": MessageSerializer(messages, many=True).data,
        "summaries": CaseSummarySerializer(summaries, many=True).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAgentOrAdmin])
def case_attachments(request, pk):
    """Lista adjuntos del caso con URL firmada (expiración corta)."""
    case = get_object_or_404(Case, pk=pk)
    from apps.attachments.services import list_attachments_with_presigned_urls
    items = list_attachments_with_presigned_urls(case)
    return Response({"attachments": items})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAgentOrAdmin])
def response_preview(request, pk):
    """Preview de respuesta multicanal. Stub: devuelve el texto."""
    case = get_object_or_404(Case, pk=pk)
    texto = request.data.get("texto", request.data.get("text", ""))
    return Response({"preview": {"text": texto, "channels": []}})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAgentOrAdmin])
def response_send(request, pk):
    """Envía respuesta: registra mensaje y opcionalmente adjuntos. Idempotente con Idempotency-Key."""
    case = get_object_or_404(Case, pk=pk)
    action_key = get_idempotency_key(request)
    if action_key:
        stored = get_stored_idempotent_response(case.id, action_key, request.user.id)
        if stored:
            status_code, payload = stored
            return Response(payload, status=status_code)
    texto = request.data.get("texto", request.data.get("text", ""))
    if not texto:
        return Response(
            {"code": "VALIDATION_ERROR", "message": "texto requerido", "details": []},
            status=status.HTTP_400_BAD_REQUEST,
        )
    msg = Message.objects.create(
        case=case,
        sender_type="agent",
        sender_user_id=request.user.id,
        content=texto,
        direction="outbound",
    )
    from apps.audit.models import AuditEvent, AuditEventType
    AuditEvent.objects.create(
        case=case,
        company=case.company,
        event_type=AuditEventType.MENSAJE_ENVIADO,
        payload={"by": "agent", "user_id": request.user.id},
        actor=request.user,
    )
    case.refresh_from_db()
    payload = {
        "resultado_por_canal": [{"canal": "api", "exito": True}],
        "result_id": msg.id,
        "case_id": case.id,
        "case_updated_at": case.updated_at.isoformat() if case.updated_at else None,
    }
    if action_key:
        store_idempotent_response(case.id, action_key, request.user.id, status.HTTP_200_OK, payload)
    return Response(payload)


# --- Copiloto case-scoped: mensajes del caso ---

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAgentOrAdmin])
def case_copilot_mensajes(request, pk):
    """
    GET  /api/casos/:id/copiloto/mensajes — historial copiloto del caso.
    POST /api/casos/:id/copiloto/mensajes — envía texto, devuelve respuesta IA; opcional guardar_respuesta_como_conocimiento.
    """
    case = get_object_or_404(Case, pk=pk)
    from apps.integrations.models import CopilotMessage

    if request.method == "GET":
        qs = CopilotMessage.objects.filter(case_id=case.id, user=request.user).order_by("created_at")
        messages = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
                "saved_to_knowledge": getattr(m, "saved_to_knowledge", False),
                "knowledge_chunk_id": getattr(m, "knowledge_chunk_id", None),
            }
            for m in qs[:200]
        ]
        return Response({"messages": messages})

    # POST
    from apps.integrations.services import copilot_reply
    from apps.knowledge.models import KnowledgeChunk
    from apps.knowledge.services import KnowledgeIngestionService

    texto = request.data.get("texto", request.data.get("text", ""))
    if not texto:
        return Response(
            {"code": "VALIDATION_ERROR", "message": "texto requerido", "details": []},
            status=status.HTTP_400_BAD_REQUEST,
        )
    save_as_knowledge = request.data.get("guardar_respuesta_como_conocimiento", False)

    CopilotMessage.objects.create(
        case=case,
        user=request.user,
        role="user",
        content=texto,
    )
    reply_text, suggestion = copilot_reply(texto, case=case, user=request.user)
    assistant_msg = CopilotMessage.objects.create(
        case=case,
        user=request.user,
        role="assistant",
        content=reply_text,
    )

    knowledge_chunk_id = None
    if save_as_knowledge and reply_text:
        svc = KnowledgeIngestionService()
        source_id = f"copilot_msg_{assistant_msg.id}"
        svc.create_or_update_chunks(
            items=[{"text": reply_text, "source_id": source_id, "metadata": {"case_id": case.id}}],
            company_id=case.company_id,
            source_type="human_note",
        )
        chunk = KnowledgeChunk.objects.filter(
            company_id=case.company_id,
            source_type="human_note",
            source_id=source_id,
        ).first()
        if chunk:
            knowledge_chunk_id = chunk.id
            assistant_msg.saved_to_knowledge = True
            assistant_msg.knowledge_chunk_id = chunk.id
            assistant_msg.save(update_fields=["saved_to_knowledge", "knowledge_chunk_id"])

    return Response({
        "respuesta_ia": reply_text,
        "sugerencia_respuesta": suggestion,
        "mensaje_id": assistant_msg.id,
        "guardado_como_conocimiento": assistant_msg.saved_to_knowledge,
        "knowledge_chunk_id": knowledge_chunk_id,
    })


urlpatterns = [
    path("", CaseListView.as_view(), name="case-list"),
    path("<int:pk>/", CaseDetailView.as_view(), name="case-detail"),
    path("<int:pk>/timeline/", case_timeline),
    path("<int:pk>/adjuntos/", case_attachments),
    path("<int:pk>/respuesta/preview/", response_preview),
    path("<int:pk>/respuesta/enviar/", response_send),
    path("<int:pk>/copiloto/mensajes/", case_copilot_mensajes),
]
