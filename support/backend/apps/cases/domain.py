"""
Reglas de dominio para casos: estados y transiciones válidas.
Sin I/O; solo lógica.
"""
from apps.cases.models import CaseStatus

# Matriz de transiciones permitidas: desde -> [hacia, ...]
VALID_TRANSITIONS: dict[str, list[str]] = {
    CaseStatus.INICIADO: [CaseStatus.EN_ANALISIS_IA],
    CaseStatus.EN_ANALISIS_IA: [
        CaseStatus.ESPERANDO_RESPUESTA_USUARIO,
        CaseStatus.DERIVADO_A_HUMANO,
    ],
    CaseStatus.ESPERANDO_RESPUESTA_USUARIO: [
        CaseStatus.EN_ANALISIS_IA,
        CaseStatus.DERIVADO_A_HUMANO,
    ],
    CaseStatus.DERIVADO_A_HUMANO: [CaseStatus.ASIGNADO_A_AGENTE_HUMANO],
    CaseStatus.ASIGNADO_A_AGENTE_HUMANO: [CaseStatus.EN_PROCESO_HUMANO],
    CaseStatus.EN_PROCESO_HUMANO: [
        CaseStatus.ESPERANDO_RESPUESTA_USUARIO,
        CaseStatus.RESUELTO,
    ],
    CaseStatus.RESUELTO: [CaseStatus.CERRADO, CaseStatus.REABIERTO],
    CaseStatus.CERRADO: [CaseStatus.REABIERTO],
    CaseStatus.REABIERTO: [CaseStatus.EN_ANALISIS_IA, CaseStatus.DERIVADO_A_HUMANO],
}


def can_transition(current: str, new: str) -> bool:
    """Indica si la transición de current a new es válida."""
    allowed = VALID_TRANSITIONS.get(current, [])
    return new in allowed


def is_open_status(status: str) -> bool:
    """Estados considerados 'abiertos' para listado de casos abiertos."""
    return status not in (CaseStatus.CERRADO, CaseStatus.RESUELTO)


def open_status_values() -> list[str]:
    """Lista de valores de estado considerados abiertos."""
    return [choice[0] for choice in CaseStatus.choices if is_open_status(choice[0])]


def is_sla_active_status(status: str) -> bool:
    """Estados en los que el SLA puede estar activo (no pausado)."""
    return status in (
        CaseStatus.ASIGNADO_A_AGENTE_HUMANO,
        CaseStatus.EN_PROCESO_HUMANO,
    )


def is_sla_paused_status(status: str) -> bool:
    """Estado en el que el SLA se pausa."""
    return status == CaseStatus.ESPERANDO_RESPUESTA_USUARIO
