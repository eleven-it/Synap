"""Cuadre pre/post migración."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from odoo_migracion.models import MigrationEntityMapping, OdooConnection
from odoo_migracion.services.discovery import run_discovery
from odoo_migracion.services.domains import DOMAIN_BY_KEY


@dataclass
class ValidationLine:
    dominio: str
    origen_count: int
    mappings_ok: int
    mappings_pendiente: int
    mappings_error: int
    delta: int


@dataclass
class ValidationReport:
    conexion_id: int
    base_empresa: str
    lineas: List[ValidationLine] = field(default_factory=list)
    anomalias: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conexion_id": self.conexion_id,
            "base_empresa": self.base_empresa,
            "lineas": [
                {
                    "dominio": l.dominio,
                    "origen_count": l.origen_count,
                    "mappings_ok": l.mappings_ok,
                    "mappings_pendiente": l.mappings_pendiente,
                    "mappings_error": l.mappings_error,
                    "delta": l.delta,
                }
                for l in self.lineas
            ],
            "anomalias": self.anomalias,
        }


def run_validation(conexion: OdooConnection) -> ValidationReport:
    discovery = run_discovery(conexion.base_empresa)
    report = ValidationReport(
        conexion_id=conexion.pk,
        base_empresa=conexion.base_empresa,
        anomalias=[a.__dict__ for a in discovery.anomalias],
    )

    for key, spec in DOMAIN_BY_KEY.items():
        origen = discovery.conteos.get(key, 0)
        qs = MigrationEntityMapping.objects.filter(conexion=conexion, entity_type=key)
        ok = qs.filter(sync_state=MigrationEntityMapping.SyncState.OK).count()
        pend = qs.filter(sync_state=MigrationEntityMapping.SyncState.PENDIENTE).count()
        err = qs.filter(sync_state=MigrationEntityMapping.SyncState.ERROR).count()
        report.lineas.append(
            ValidationLine(
                dominio=key,
                origen_count=origen,
                mappings_ok=ok,
                mappings_pendiente=pend,
                mappings_error=err,
                delta=origen - ok - pend,
            )
        )
    return report
