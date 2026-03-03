"""Tareas Celery: chequeo SLA, warning, vencimiento, escalado."""
import logging
from django.utils import timezone

from celery import shared_task
from apps.cases.models import Case, CaseStatus
from apps.sla.models import SLAConfig
from apps.sla.services import (
    get_sla_config_for_case,
    effective_sla_seconds_consumed,
    mark_sla_warning_sent,
    mark_sla_breached,
)

logger = logging.getLogger(__name__)


@shared_task(name="sla.run_sla_checks")
def run_sla_checks():
    """
    Job periódico (Beat cada 1-5 min). Casos con SLA activo no pausado;
    si % >= warning_pct -> notificación y evento sla_warning;
    si tiempo >= límite -> marcar vencido, notificar usuario, escalar gerencia.
    """
    now = timezone.now()
    cases = Case.objects.filter(
        status__in=[CaseStatus.ASIGNADO_A_AGENTE_HUMANO, CaseStatus.EN_PROCESO_HUMANO],
        sla_started_at__isnull=False,
        sla_due_at__isnull=False,
        sla_breached_at__isnull=True,
    )
    for case in cases:
        if case.sla_paused_since:
            continue
        config = get_sla_config_for_case(case)
        if not config:
            continue
        total_seconds = config.response_time_minutes * 60
        consumed = effective_sla_seconds_consumed(case, until=now)
        pct = (consumed / total_seconds * 100) if total_seconds else 0
        if consumed >= total_seconds:
            mark_sla_breached(case)
            notify_user_sla_breached.delay(case.id)
            escalate_sla_to_management.delay(case.id)
            logger.info("SLA vencido", extra={"case_id": case.id, "number_display": case.number_display})
        elif pct >= config.warning_pct and not case.sla_warning_sent_at:
            mark_sla_warning_sent(case)
            notify_agent_sla_warning.delay(case.id)
            logger.info("SLA warning enviado", extra={"case_id": case.id})
    return {"processed": cases.count()}


@shared_task(name="sla.notify_user_sla_breached")
def notify_user_sla_breached(case_id: int):
    """Notifica al usuario que el SLA venció y se está escalando. Stub: log."""
    case = Case.objects.filter(pk=case_id).first()
    if case:
        logger.info("Notificar usuario SLA vencido (stub)", extra={"case_id": case_id})


@shared_task(name="sla.escalate_sla_to_management")
def escalate_sla_to_management(case_id: int):
    """Escala a gerencia. Stub: log."""
    logger.info("Escalar a gerencia (stub)", extra={"case_id": case_id})


@shared_task(name="sla.notify_agent_sla_warning")
def notify_agent_sla_warning(case_id: int):
    """Notifica al agente warning SLA. Stub: log."""
    logger.info("Notificar agente SLA warning (stub)", extra={"case_id": case_id})
