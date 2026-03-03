"""API copiloto IA: mensaje y historial (chat agente ↔ IA)."""
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.cases.models import Case
from apps.integrations.models import CopilotMessage
from apps.integrations.services import copilot_reply


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def copilot_message(request):
    """POST texto; opcional case_id. Devuelve respuesta_ia y sugerencia_respuesta (stub)."""
    texto = request.data.get("texto", request.data.get("text", ""))
    case_id = request.data.get("case_id")
    sistema = request.data.get("sistema")  # opcional: "synap" | "administranet" para filtrar RAG
    if not texto:
        return Response(
            {"code": "VALIDATION_ERROR", "message": "texto requerido", "details": []},
            status=400,
        )
    case = get_object_or_404(Case, pk=case_id) if case_id else None
    CopilotMessage.objects.create(
        case=case,
        user=request.user,
        role="user",
        content=texto,
    )
    reply_text, suggestion, derivado_a_humano = copilot_reply(
        texto, case=case, user=request.user, sistema=sistema
    )
    CopilotMessage.objects.create(
        case=case,
        user=request.user,
        role="assistant",
        content=reply_text,
    )
    return Response({
        "respuesta_ia": reply_text,
        "sugerencia_respuesta": suggestion,
        "derivado_a_humano": derivado_a_humano,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def copilot_history(request):
    """Historial del chat copiloto; opcional ?case_id=."""
    case_id = request.query_params.get("case_id")
    qs = CopilotMessage.objects.filter(user=request.user).order_by("created_at")
    if case_id:
        qs = qs.filter(case_id=case_id)
    messages = [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in qs[:100]]
    return Response({"messages": messages})


urlpatterns = [
    path("mensaje/", copilot_message),
    path("historial/", copilot_history),
]
