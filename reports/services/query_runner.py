from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import logging

from django.utils import timezone

from ..models import ReportDefinition, ReportExecutionLog
from ..tasks import enqueue_report_refresh
from .sample_data import get_sample_data

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Respuesta estructurada para consultas de reportes."""

    meta: Dict
    data: List[Dict]
    totals: Dict[str, float]
    notes: List[str]


class QueryRunnerService:
    """Servicio responsable de ejecutar consultas declarativas."""

    def __init__(self, user):
        self.user = user

    def run(self, report: ReportDefinition, payload: Dict) -> QueryResult:
        """Ejecuta la consulta solicitada (placeholder inicial)."""
        started_at = timezone.now()

        # Comentario: Aquí se conectará con pipelines SQL, vistas materializadas o servicios externos.
        meta, data, totals, notes = get_sample_data(report.slug, payload)
        if not data:
            data = []
            totals = {}
            notes = ["Data source execution not implemented yet."]
            meta = {
                "slug": report.slug,
                "name": report.name,
                "category": report.category,
                "version": report.version,
            }
        else:
            meta.update(
                {
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                }
            )

        # Registrar log básico
        duration = (timezone.now() - started_at).total_seconds() * 1000
        ReportExecutionLog.objects.create(
            report=report,
            executed_by=self.user if getattr(self.user, "is_authenticated", False) else None,
            status="success",
            filters_snapshot=payload.get("filters", {}),
            duration_ms=int(duration),
            notes="\n".join(notes),
        )

        # Programar refresco si corresponde
        try:
            enqueue_report_refresh.delay(report.slug)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unable to enqueue refresh for %s: %s", report.slug, exc)

        return QueryResult(
            meta=meta,
            data=data,
            totals=totals,
            notes=notes,
        )


