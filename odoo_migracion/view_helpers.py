"""Helpers de vistas — contexto UI compartido."""

from __future__ import annotations

from typing import Optional

from odoo_migracion.models import OdooConnection
from odoo_migracion.services.discovery import run_discovery
from odoo_migracion.services.ui_context import build_migration_overview


def resolve_conexion(
    *,
    base_empresa: str,
    conexion_id: Optional[str] = None,
    solo_activas: bool = True,
) -> Optional[OdooConnection]:
    qs = OdooConnection.objects.all()
    if solo_activas:
        qs = qs.filter(activo=True)
    if conexion_id:
        return qs.filter(pk=conexion_id).first()
    if base_empresa:
        return qs.filter(base_empresa=base_empresa).order_by("-updated_at").first()
    return qs.order_by("-updated_at").first()


def panel_context(
    *,
    base_empresa: str = "",
    conexion_id: Optional[str] = None,
    run_discovery_flag: bool = False,
) -> dict:
    conexion = resolve_conexion(base_empresa=base_empresa, conexion_id=conexion_id)
    conteos = None
    anomalias_count = 0
    be = base_empresa or (conexion.base_empresa if conexion else "")
    if run_discovery_flag and be:
        try:
            report = run_discovery(be)
            conteos = report.conteos
            anomalias_count = len(report.anomalias)
        except Exception:
            pass
    overview = build_migration_overview(
        conexion=conexion,
        base_empresa=be,
        discovery_conteos=conteos,
        anomalias_count=anomalias_count,
    )
    conexiones = OdooConnection.objects.filter(activo=True)
    if base_empresa:
        conexiones = conexiones.filter(base_empresa=base_empresa)
    return {
        "overview": overview,
        "conexion_sel": conexion,
        "conexiones": conexiones,
        "base_empresa": be,
        "discovery_conteos": conteos,
    }
