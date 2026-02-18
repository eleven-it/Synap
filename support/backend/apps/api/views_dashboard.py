"""GET /api/dashboard — KPIs y resumen de casos."""
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Q

from apps.cases.models import Case, CaseStatus
from apps.cases.domain import open_status_values


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """Resumen: totales por estado, abiertos, en riesgo SLA."""
    open_statuses = open_status_values()
    by_status = dict(
        Case.objects.values("status").annotate(count=Count("id")).values_list("status", "count")
    )
    open_count = sum(by_status.get(s, 0) for s in open_statuses)
    sla_at_risk = Case.objects.filter(
        status__in=[CaseStatus.ASIGNADO_A_AGENTE_HUMANO, CaseStatus.EN_PROCESO_HUMANO],
        sla_due_at__isnull=False,
        sla_breached_at__isnull=True,
        sla_paused_since__isnull=True,
    ).count()
    return Response({
        "cases_by_status": by_status,
        "open_count": open_count,
        "sla_at_risk_count": sla_at_risk,
    })


urlpatterns = [
    path("dashboard/", dashboard),
    path("stats/", dashboard),
]
