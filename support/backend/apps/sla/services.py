"""Servicios SLA: inicio, pausa, reanudación, warning, vencimiento."""
from django.utils import timezone
from datetime import timedelta

from apps.cases.models import Case, CaseStatus
from apps.cases.domain import is_sla_paused_status, is_sla_active_status
from apps.sla.models import SLAConfig
from apps.audit.models import AuditEvent, AuditEventType


def get_sla_config_for_case(case: Case, case_type: str = "default") -> SLAConfig | None:
    """Obtiene la configuración SLA para la empresa y tipo de caso."""
    return SLAConfig.objects.filter(
        company=case.company,
        case_type=case_type,
    ).first()


def start_sla_for_case(case: Case, actor=None) -> None:
    """Inicia SLA al asignar agente: setea sla_started_at y sla_due_at. Registra evento."""
    config = get_sla_config_for_case(case)
    if not config:
        return
    now = timezone.now()
    case.sla_started_at = now
    case.sla_due_at = now + timedelta(minutes=config.response_time_minutes)
    case.sla_paused_since = None
    case.save(update_fields=["sla_started_at", "sla_due_at", "sla_paused_since"])
    AuditEvent.objects.create(
        case=case,
        company=case.company,
        event_type=AuditEventType.SLA_INICIO,
        payload={
            "sla_due_at": case.sla_due_at.isoformat(),
            "response_time_minutes": config.response_time_minutes,
        },
        actor=actor,
    )


def pause_sla_for_case(case: Case, actor=None) -> None:
    """Pausa SLA (estado Esperando respuesta del usuario)."""
    if not is_sla_paused_status(case.status):
        return
    now = timezone.now()
    if case.sla_paused_since:
        return  # ya pausado
    case.sla_paused_since = now
    case.save(update_fields=["sla_paused_since"])
    AuditEvent.objects.create(
        case=case,
        company=case.company,
        event_type=AuditEventType.SLA_PAUSA,
        payload={"paused_since": now.isoformat()},
        actor=actor,
    )


def resume_sla_for_case(case: Case, actor=None) -> None:
    """Reanuda SLA al salir de Esperando respuesta. Recalcula sla_due_at si política 'solo tiempo activo'."""
    if case.sla_paused_since is None:
        return
    config = get_sla_config_for_case(case)
    paused_duration = timezone.now() - case.sla_paused_since
    case.sla_paused_since = None
    if config:
        case.sla_due_at = timezone.now() + timedelta(minutes=config.response_time_minutes)
    case.save(update_fields=["sla_paused_since", "sla_due_at"])
    AuditEvent.objects.create(
        case=case,
        company=case.company,
        event_type=AuditEventType.SLA_REANUDACION,
        payload={"paused_duration_seconds": paused_duration.total_seconds()},
        actor=actor,
    )


def mark_sla_warning_sent(case: Case, actor=None) -> None:
    """Marca que se envió el warning (70-80%)."""
    if case.sla_warning_sent_at:
        return
    case.sla_warning_sent_at = timezone.now()
    case.save(update_fields=["sla_warning_sent_at"])
    AuditEvent.objects.create(
        case=case,
        company=case.company,
        event_type=AuditEventType.SLA_WARNING,
        payload={},
        actor=actor,
    )


def mark_sla_breached(case: Case, actor=None) -> None:
    """Marca SLA vencido. Debe notificar usuario y escalar (vía tarea Celery)."""
    if case.sla_breached_at:
        return
    case.sla_breached_at = timezone.now()
    case.save(update_fields=["sla_breached_at"])
    AuditEvent.objects.create(
        case=case,
        company=case.company,
        event_type=AuditEventType.SLA_VENCIDO,
        payload={},
        actor=actor,
    )


def effective_sla_seconds_consumed(case: Case, until: timezone.datetime | None = None) -> float:
    """Tiempo efectivo consumido del SLA (excluyendo pausas). until = ahora si no se pasa."""
    until = until or timezone.now()
    if not case.sla_started_at or not case.sla_due_at:
        return 0.0
    total = (until - case.sla_started_at).total_seconds()
    if case.sla_paused_since:
        pause_end = until
        total -= (pause_end - case.sla_paused_since).total_seconds()
    return max(0, total)


def sla_percentage_consumed(case: Case, until: timezone.datetime | None = None) -> float | None:
    """Porcentaje del tiempo de respuesta consumido. None si no hay config."""
    config = get_sla_config_for_case(case)
    if not config:
        return None
    total_seconds = config.response_time_minutes * 60
    consumed = effective_sla_seconds_consumed(case, until)
    return min(100.0, (consumed / total_seconds) * 100) if total_seconds else None
