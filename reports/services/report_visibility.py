"""
Visibilidad de informes (ReportDefinition.is_visible).

Regla: si is_visible=False, el informe no se muestra ni se abre para ningún puesto.
Solo el usuario AdministraNET con cod_usuario «supervisor» (no el puesto Supervisor) lo ve igual.
"""
from __future__ import annotations

from django.db.models import Q

from core.utils.permissions import user_has_full_access, user_has_permission

from ..models import ReportDefinition

COMMAND_CENTER_SLUG = "command-center-gerencial"


def report_visible_for_user(report: ReportDefinition | None, user) -> bool:
    """True si el informe está activado (is_visible) o el usuario es cod_usuario supervisor."""
    if report is None:
        return False
    if getattr(report, "is_visible", True):
        return True
    return user_has_full_access(user)


def get_report_definition(slug: str, empresa_id: int | None = None) -> ReportDefinition | None:
    filters = Q(slug=slug, is_active=True)
    if empresa_id:
        filters &= Q(empresa__isnull=True) | Q(empresa_id=empresa_id)
    else:
        filters &= Q(empresa__isnull=True)
    return ReportDefinition.objects.filter(filters).first()


def command_center_visible_for_user(user, empresa_id: int | None = None) -> bool:
    """Command Center en inicio/API: permiso gerencial + is_visible (o usuario supervisor)."""
    if not user_has_permission(user, "reports.view_managerial"):
        return False
    report = get_report_definition(COMMAND_CENTER_SLUG, empresa_id=empresa_id)
    return report_visible_for_user(report, user)
