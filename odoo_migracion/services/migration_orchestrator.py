"""Orquestador de migración por dominio y lote."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from django.utils import timezone

from odoo_migracion.models import MigrationJob, OdooConnection
from odoo_migracion.services.domains import DOMAIN_BY_KEY
from odoo_migracion.loaders.registry import get_loader_for_domain
from odoo_migracion.services.odoo_client import OdooJson2Client, OdooApiError

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    procesados: int = 0
    creados: int = 0
    actualizados: int = 0
    omitidos: int = 0
    errores: int = 0
    pendientes: int = 0
    mensajes: List[str] = field(default_factory=list)


def run_domain_batch(
    conexion: OdooConnection,
    dominio: str,
    *,
    batch_size: int = 100,
    offset: int = 0,
    job: Optional[MigrationJob] = None,
    incremental: bool = False,
) -> BatchResult:
    """
    Ejecuta un lote de migración para un dominio.
    Si ``incremental`` es True, solo procesa filas con hash distinto al mapping.
    """
    spec = DOMAIN_BY_KEY.get(dominio)
    if not spec:
        raise ValueError(f"Dominio desconocido: {dominio}")

    result = BatchResult()
    extractor = spec.extractor_cls(conexion.base_empresa)
    client = OdooJson2Client(conexion)
    loader = get_loader_for_domain(dominio, conexion, client)

    rows = extractor.extract(limit=batch_size, offset=offset)
    for row in rows:
        adminet_id, vals = spec.mapper(row)
        if not adminet_id:
            result.errores += 1
            continue
        lr = loader.load_row(adminet_id, vals, row)
        result.procesados += 1
        if lr.action == "created":
            result.creados += 1
        elif lr.action == "updated":
            result.actualizados += 1
        elif lr.action in ("skipped",):
            result.omitidos += 1
        elif lr.action in ("pending_wizard", "pending_manual"):
            result.pendientes += 1
        elif lr.action == "error":
            result.errores += 1
            if lr.error:
                result.mensajes.append(lr.error)

    if job:
        job.offset = offset + len(rows)
        job.total_procesados += result.procesados
        job.total_errores += result.errores
        job.mensaje = (
            f"Lote offset={offset}: +{result.creados} creados, "
            f"+{result.actualizados} actualizados, {result.omitidos} omitidos, "
            f"{result.pendientes} pendientes, {result.errores} errores."
        )
        total = extractor.count()
        if job.offset >= total or len(rows) < batch_size:
            job.estado = MigrationJob.Estado.OK if result.errores == 0 else MigrationJob.Estado.ERROR
            job.finalizado_at = timezone.now()
        else:
            job.estado = MigrationJob.Estado.EN_CURSO
        job.save()

    return result


def run_full_domain(
    conexion: OdooConnection,
    dominio: str,
    *,
    batch_size: int = 100,
    resume_job: Optional[MigrationJob] = None,
) -> MigrationJob:
    """Migra un dominio completo en lotes reanudables."""
    job = resume_job or MigrationJob.objects.create(
        conexion=conexion,
        dominio=dominio,
        estado=MigrationJob.Estado.EN_CURSO,
        iniciado_at=timezone.now(),
    )
    offset = job.offset
    spec = DOMAIN_BY_KEY[dominio]
    extractor = spec.extractor_cls(conexion.base_empresa)
    total = extractor.count()

    while offset < total:
        try:
            run_domain_batch(
                conexion,
                dominio,
                batch_size=batch_size,
                offset=offset,
                job=job,
            )
        except OdooApiError as exc:
            job.estado = MigrationJob.Estado.ERROR
            job.mensaje = str(exc)[:2000]
            job.finalizado_at = timezone.now()
            job.save()
            raise
        job.refresh_from_db()
        offset = job.offset
        if job.estado in (MigrationJob.Estado.OK, MigrationJob.Estado.ERROR):
            break

    return job
