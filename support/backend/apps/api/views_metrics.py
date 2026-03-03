"""API métricas básicas."""
from django.urls import path
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count

from apps.audit.models import AuditEvent, AuditEventType
from apps.cases.models import Case, CaseStatus


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def metrics(request):
    """Métricas: SLA cumplido/vencido, uso por empresa. Query: desde_fecha, hasta_fecha, empresa_id."""
    desde = request.query_params.get("desde_fecha")
    hasta = request.query_params.get("hasta_fecha")
    empresa_id = request.query_params.get("empresa_id")
    if not hasta:
        hasta_dt = timezone.now()
    else:
        try:
            hasta_dt = timezone.datetime.fromisoformat(hasta.replace("Z", "+00:00"))
        except Exception:
            hasta_dt = timezone.now()
    if not desde:
        desde_dt = hasta_dt - timedelta(days=30)
    else:
        try:
            desde_dt = timezone.datetime.fromisoformat(desde.replace("Z", "+00:00"))
        except Exception:
            desde_dt = hasta_dt - timedelta(days=30)

    events = AuditEvent.objects.filter(created_at__gte=desde_dt, created_at__lte=hasta_dt)
    if empresa_id:
        events = events.filter(company_id=empresa_id)

    sla_inicios = events.filter(event_type=AuditEventType.SLA_INICIO).count()
    sla_vencidos = events.filter(event_type=AuditEventType.SLA_VENCIDO).count()
    casos_resueltos = events.filter(event_type=AuditEventType.CAMBIO_ESTADO, payload__estado_nuevo=CaseStatus.RESUELTO).count()

    return Response({
        "desde": desde_dt.isoformat(),
        "hasta": hasta_dt.isoformat(),
        "sla_inicios": sla_inicios,
        "sla_vencidos": sla_vencidos,
        "casos_resueltos": casos_resueltos,
        "sla_cumplimiento_pct": ((sla_inicios - sla_vencidos) / sla_inicios * 100) if sla_inicios else None,
    })


urlpatterns = [
    path("", metrics),
]
