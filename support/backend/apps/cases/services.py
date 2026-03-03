"""
Servicios de casos: creación, continuación, numeración, transiciones.
Orquestan dominio y persistencia; disparan auditoría.
"""
from django.db import transaction
from django.utils import timezone

from apps.cases.domain import can_transition, is_open_status, open_status_values
from apps.cases.models import Case, CaseStatus, CaseCounter, CaseSummary, Message
from apps.companies.models import Company
from apps.support_users.models import SupportUser, ChannelIdentity
from apps.audit.models import AuditEvent, AuditEventType
from apps.core.exceptions import CaseStateTransitionError


def get_next_case_number(company: Company) -> tuple[int, str]:
    """Obtiene el siguiente número secuencial y el display SUP-{PREFIJO}-000123."""
    with transaction.atomic():
        counter, _ = CaseCounter.objects.select_for_update().get_or_create(
            company=company,
            defaults={"last_number": 0},
        )
        next_num = counter.get_next_number()
    display = f"SUP-{company.prefix}-{next_num:06d}"
    return next_num, display


def create_case(company: Company) -> Case:
    """Crea un caso nuevo con numeración y estado Iniciado. Registra auditoría."""
    number_sequential, number_display = get_next_case_number(company)
    with transaction.atomic():
        case = Case.objects.create(
            company=company,
            number_sequential=number_sequential,
            number_display=number_display,
            status=CaseStatus.INICIADO,
        )
        AuditEvent.objects.create(
            case=case,
            company=company,
            event_type=AuditEventType.CREACION_CASO,
            payload={
                "number_display": number_display,
                "number_sequential": number_sequential,
            },
        )
    return case


def get_open_cases_for_support_user(support_user: SupportUser):
    """Lista casos abiertos del usuario de soporte (por sus identidades/canales)."""
    external_ids = list(
        support_user.channel_identities.values_list("external_id", flat=True)
    )
    return Case.objects.filter(
        company=support_user.company,
        status__in=open_status_values(),
    ).filter(messages__external_channel_id__in=external_ids).distinct().order_by("-updated_at")


def get_or_create_case_for_channel(
    company: Company,
    channel_type: str,
    external_id: str,
    support_user: SupportUser | None,
    prefer_new: bool = False,
) -> tuple[Case, bool]:
    """
    Resuelve caso abierto por canal (external_channel_id + channel_type) o crea uno nuevo.
    Devuelve (case, created).
    Si support_user es None (ej. bot Telegram), se busca caso abierto con mensajes
    en ese canal y external_id; si no hay, se crea uno nuevo.
    """
    open_cases = list(
        Case.objects.filter(
            company=company,
            status__in=open_status_values(),
        )
        .filter(
            messages__channel_type=channel_type,
            messages__external_channel_id=external_id,
        )
        .distinct()
    )
    if open_cases and not prefer_new:
        return open_cases[0], False
    case = create_case(company)
    return case, True


def transition_case_status(
    case: Case,
    new_status: str,
    actor_id: int | None = None,
    payload_extra: dict | None = None,
) -> Case:
    """Transiciona el caso a new_status si es válido. Registra auditoría."""
    if not can_transition(case.status, new_status):
        raise CaseStateTransitionError(
            f"Transición no permitida: {case.status} -> {new_status}",
            code="CASE_STATE_TRANSITION_INVALID",
        )
    from django.contrib.auth import get_user_model
    User = get_user_model()
    actor = User.objects.filter(pk=actor_id).first() if actor_id else None
    old_status = case.status
    case.status = new_status
    case.save(update_fields=["status", "updated_at"])
    from apps.sla.services import pause_sla_for_case, resume_sla_for_case
    if new_status == CaseStatus.ESPERANDO_RESPUESTA_USUARIO:
        pause_sla_for_case(case, actor=actor)
    elif old_status == CaseStatus.ESPERANDO_RESPUESTA_USUARIO:
        resume_sla_for_case(case, actor=actor)
    AuditEvent.objects.create(
        case=case,
        company=case.company,
        event_type=AuditEventType.CAMBIO_ESTADO,
        payload={
            "estado_anterior": old_status,
            "estado_nuevo": new_status,
            **(payload_extra or {}),
        },
        actor=actor,
    )
    return case


def derive_case_to_human(case: Case, actor_id: int | None = None) -> Case:
    """
    Deriva el caso a un agente humano (estado DERIVADO_A_HUMANO).
    Si el caso está INICIADO, primero transiciona a EN_ANALISIS_IA y luego a DERIVADO_A_HUMANO.
    Si ya está en DERIVADO_A_HUMANO o en un estado que no permite derivar, no hace nada.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    actor = User.objects.filter(pk=actor_id).first() if actor_id else None
    status = case.status
    if status == CaseStatus.DERIVADO_A_HUMANO:
        return case
    if status == CaseStatus.INICIADO:
        transition_case_status(case, CaseStatus.EN_ANALISIS_IA, actor_id=actor_id)
        case.refresh_from_db()
    if can_transition(case.status, CaseStatus.DERIVADO_A_HUMANO):
        transition_case_status(case, CaseStatus.DERIVADO_A_HUMANO, actor_id=actor_id)
    return case


def assign_case(case: Case, assigned_to_id: int, actor_id: int | None = None) -> Case:
    """Asigna el caso a un agente. Transiciona a ASIGNADO_A_AGENTE_HUMANO y dispara inicio SLA."""
    from django.contrib.auth import get_user_model
    from apps.sla.services import start_sla_for_case

    User = get_user_model()
    actor = User.objects.filter(pk=actor_id).first() if actor_id else None
    assignee = User.objects.get(pk=assigned_to_id)
    old_assignee_id = case.assigned_to_id
    case.assigned_to_id = assigned_to_id
    case.status = CaseStatus.ASIGNADO_A_AGENTE_HUMANO
    case.save(update_fields=["assigned_to_id", "status", "updated_at"])
    AuditEvent.objects.create(
        case=case,
        company=case.company,
        event_type=AuditEventType.ASIGNACION,
        payload={
            "assigned_to_id": assigned_to_id,
            "assigned_to_username": getattr(assignee, "username", None),
            "anterior_asignado_id": old_assignee_id,
        },
        actor=actor,
    )
    start_sla_for_case(case, actor=actor)
    return case
