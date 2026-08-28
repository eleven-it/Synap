"""Orquestador de generación MTRIX."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from mtrix.extractors import EXTRACTORS
from mtrix.extractors.base import (
    ExportConfig,
    obtener_cnpj_distribuidor,
    obtener_razon_empresa,
    parse_proveedores,
    resolver_fechas_mysql,
)
from mtrix.models import MtrixArtifact, MtrixConfig, MtrixJob
from mtrix.services.csv_serializer import TIPOS_ORDEN, serialize

logger = logging.getLogger(__name__)

TIPOS_CON_FILTRO_PROV = {"PD", "ES", "VD"}


def job_dir(base_empresa: str, job_id) -> Path:
    root = Path(settings.MEDIA_ROOT) / "mtrix" / base_empresa / str(job_id)
    root.mkdir(parents=True, exist_ok=True)
    return root


def config_to_export(cfg: MtrixConfig) -> ExportConfig:
    desde, hasta = resolver_fechas_mysql(
        cfg.base_empresa,
        personalizada=cfg.fecha_personalizada,
        fecha_inicio=cfg.fecha_inicio,
        fecha_final=cfg.fecha_final,
        dias=cfg.dias_a_procesar,
    )
    fecha_archivo = hasta.replace("-", "")
    return ExportConfig(
        base_empresa=cfg.base_empresa,
        fecha_desde=desde,
        fecha_hasta=hasta,
        proveedores=parse_proveedores(cfg.codigo_proveedor_principal),
        cnpj_fornecedor=cfg.cnpj_fornecedor,
        cnpj_distribuidor=obtener_cnpj_distribuidor(cfg.base_empresa),
        razon_social_fornecedor=obtener_razon_empresa(cfg.base_empresa),
        pvnf=bool(cfg.pvnf),
        multiplicador_cantidad=cfg.multiplicador_cantidad or 1,
        multiplicador_precio=cfg.multiplicador_precio or 1,
        fecha_archivo=fecha_archivo,
    )


def crear_job(*, base_empresa: str, origen: str, triggered_by: str = "") -> MtrixJob:
    try:
        with transaction.atomic():
            return MtrixJob.objects.create(
                base_empresa=base_empresa,
                status=MtrixJob.Estado.QUEUED,
                origen=origen,
                triggered_by=triggered_by or "",
            )
    except IntegrityError as exc:
        raise RuntimeError(
            "Ya hay una corrida Mtrix en curso para esta empresa."
        ) from exc


def hay_job_activo(base_empresa: str) -> bool:
    return MtrixJob.objects.filter(
        base_empresa=base_empresa,
        status__in=[MtrixJob.Estado.QUEUED, MtrixJob.Estado.RUNNING],
    ).exists()


def _append_log(job: MtrixJob, linea: str) -> None:
    job.log_text = (job.log_text or "") + linea + "\n"
    job.progreso = linea[:200]
    job.save(update_fields=["log_text", "progreso"])


def _escribir_artefacto(job: MtrixJob, tipo: str, codigo_prov: str, filename: str, data: bytes, filas: int) -> MtrixArtifact:
    dest = job_dir(job.base_empresa, job.id) / filename
    dest.write_bytes(data)
    rel = dest.relative_to(Path(settings.MEDIA_ROOT)).as_posix()
    digest = hashlib.sha256(data).hexdigest()
    return MtrixArtifact.objects.create(
        job=job,
        tipo=tipo,
        codigo_proveedor="" if codigo_prov == "TODOS" else codigo_prov,
        filename=filename,
        relative_path=rel,
        size_bytes=len(data),
        sha256=digest,
        row_count=filas,
        sftp_status=MtrixArtifact.SftpStatus.PENDING,
    )


def ejecutar_job(job_id) -> MtrixJob:
    job = MtrixJob.objects.get(pk=job_id)
    cfg_row, _created = MtrixConfig.objects.get_or_create(base_empresa=job.base_empresa)
    job.status = MtrixJob.Estado.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])
    try:
        export_cfg = config_to_export(cfg_row)
        job.fecha_desde = export_cfg.fecha_desde
        job.fecha_hasta = export_cfg.fecha_hasta
        job.save(update_fields=["fecha_desde", "fecha_hasta"])
        generated_at = datetime.now()
        ser_cfg = export_cfg.to_serializer_cfg()
        for tipo in TIPOS_ORDEN:
            extractor = EXTRACTORS[tipo]
            kwargs = {}
            etiqueta = "TODOS"
            if tipo in TIPOS_CON_FILTRO_PROV:
                kwargs["codigos_prov"] = export_cfg.proveedores
                if export_cfg.proveedores and export_cfg.proveedores != ["TODOS"]:
                    etiqueta = ",".join(export_cfg.proveedores)
            _append_log(job, f"Generando {tipo} ({etiqueta})…")
            rows = extractor.fetch_rows(None, export_cfg, **kwargs)
            if not rows:
                _append_log(job, f"Sin datos {tipo} ({etiqueta}); archivo no creado.")
                continue
            filename, data = serialize(tipo, rows, ser_cfg, generated_at)
            _escribir_artefacto(job, tipo, etiqueta, filename, data, len(rows))
            _append_log(job, f"Archivo {filename} ({len(rows)} filas).")
        job.status = MtrixJob.Estado.COMPLETED
        job.finished_at = timezone.now()
        job.progreso = "Completado"
        job.save(update_fields=["status", "finished_at", "progreso"])
        if cfg_row.sftp_enviar_automatico and job.origen == MtrixJob.Origen.CRON:
            from mtrix.services.sftp import enviar_job

            enviar_job(job, cfg_row)
        return job
    except Exception as exc:
        logger.exception("Job Mtrix falló: %s", exc)
        job.status = MtrixJob.Estado.FAILED
        job.error_summary = str(exc)
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_summary", "finished_at"])
        raise
