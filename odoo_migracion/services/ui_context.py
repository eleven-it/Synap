"""Contexto agregado para pantallas de migración (progreso y diagnóstico)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from odoo_migracion.models import MigrationEntityMapping, MigrationJob, OdooConnection
from odoo_migracion.services.domains import DOMAIN_BY_KEY, DOMAIN_SPECS


@dataclass
class DomainProgressUI:
    key: str
    label: str
    fase: str
    orden: int
    origen_count: Optional[int] = None
    mappings_ok: int = 0
    mappings_pendiente: int = 0
    mappings_error: int = 0
    job_estado: Optional[str] = None
    job_offset: int = 0
    job_procesados: int = 0
    job_errores: int = 0
    job_mensaje: str = ""
    job_progress_pct: int = 0
    sync_progress_pct: int = 0
    status: str = "sin_iniciar"
    status_label: str = "Sin iniciar"
    status_tone: str = "slate"


@dataclass
class MigrationPhaseUI:
    id: str
    label: str
    descripcion: str
    fases: List[str]
    dominios: List[DomainProgressUI] = field(default_factory=list)

    @property
    def progress_pct(self) -> int:
        if not self.dominios:
            return 0
        return round(sum(d.sync_progress_pct for d in self.dominios) / len(self.dominios))


@dataclass
class MigrationOverviewUI:
    conexion: Optional[OdooConnection]
    base_empresa: str
    dominios: List[DomainProgressUI]
    fases: List[MigrationPhaseUI]
    kpis: Dict[str, Any]
    discovery_done: bool = False
    anomalias_count: int = 0


PHASE_DEFINITIONS = [
    {
        "id": "f3",
        "label": _("Maestros y partners"),
        "descripcion": _("Empresa, catálogos, vendedores, clientes y proveedores"),
        "fases": ["F3"],
    },
    {
        "id": "f4",
        "label": _("Productos e inventario"),
        "descripcion": _("Artículos, depósitos y saldos (ajuste vía wizard Odoo)"),
        "fases": ["F4"],
    },
    {
        "id": "f5",
        "label": _("Cuentas abiertas"),
        "descripcion": _("Facturas CC históricas sin re-emisión CAE"),
        "fases": ["F5"],
    },
]


def _status_for_domain(
    spec_key: str,
    origen: Optional[int],
    ok: int,
    pend: int,
    err: int,
    job: Optional[MigrationJob],
) -> tuple[str, str, str]:
    if job and job.estado == MigrationJob.Estado.EN_CURSO:
        return "en_curso", str(_("En curso")), "sky"
    if job and job.estado == MigrationJob.Estado.ERROR:
        return "error", str(_("Error")), "red"
    if err > 0:
        return "error", str(_("Con errores")), "red"
    if pend > 0 and spec_key in ("stock_saldo", "cuenta_cliente"):
        return "pendiente_manual", str(_("Pendiente manual")), "amber"
    if origen and origen > 0 and ok >= origen:
        return "completado", str(_("Completado")), "emerald"
    if ok > 0 or (job and job.estado == MigrationJob.Estado.OK):
        return "parcial", str(_("Parcial")), "violet"
    if job and job.estado == MigrationJob.Estado.PENDIENTE:
        return "sin_iniciar", str(_("Pendiente")), "slate"
    return "sin_iniciar", str(_("Sin iniciar")), "slate"


def _latest_jobs_by_domain(conexion: OdooConnection) -> Dict[str, MigrationJob]:
    jobs = (
        MigrationJob.objects.filter(conexion=conexion)
        .order_by("dominio", "-created_at")
        .select_related("conexion")
    )
    out: Dict[str, MigrationJob] = {}
    for job in jobs:
        if job.dominio not in out:
            out[job.dominio] = job
    return out


def _mapping_counts(conexion: OdooConnection) -> Dict[str, Dict[str, int]]:
    rows = (
        MigrationEntityMapping.objects.filter(conexion=conexion)
        .values("entity_type", "sync_state")
        .annotate(n=Count("id"))
    )
    out: Dict[str, Dict[str, int]] = {}
    for row in rows:
        et = row["entity_type"]
        out.setdefault(et, {"ok": 0, "pendiente": 0, "error": 0})
        state = row["sync_state"]
        if state == MigrationEntityMapping.SyncState.OK:
            out[et]["ok"] = row["n"]
        elif state == MigrationEntityMapping.SyncState.PENDIENTE:
            out[et]["pendiente"] = row["n"]
        elif state == MigrationEntityMapping.SyncState.ERROR:
            out[et]["error"] = row["n"]
    return out


def build_domain_progress(
    conexion: OdooConnection,
    *,
    discovery_conteos: Optional[Dict[str, int]] = None,
) -> List[DomainProgressUI]:
    latest = _latest_jobs_by_domain(conexion)
    maps = _mapping_counts(conexion)
    items: List[DomainProgressUI] = []

    for spec in sorted(DOMAIN_SPECS, key=lambda s: s.orden):
        if spec.key == "contribuyente":
            continue
        origen = (discovery_conteos or {}).get(spec.key)
        mc = maps.get(spec.key, {})
        ok = mc.get("ok", 0)
        pend = mc.get("pendiente", 0)
        err = mc.get("error", 0)
        job = latest.get(spec.key)
        job_pct = 0
        if origen and origen > 0 and job:
            job_pct = min(100, round((job.offset / origen) * 100))
        sync_pct = 0
        if origen and origen > 0:
            sync_pct = min(100, round((ok / origen) * 100))
        elif ok > 0:
            sync_pct = 50
        status, status_label, tone = _status_for_domain(spec.key, origen, ok, pend, err, job)
        items.append(
            DomainProgressUI(
                key=spec.key,
                label=spec.label,
                fase=spec.fase,
                orden=spec.orden,
                origen_count=origen,
                mappings_ok=ok,
                mappings_pendiente=pend,
                mappings_error=err,
                job_estado=job.estado if job else None,
                job_offset=job.offset if job else 0,
                job_procesados=job.total_procesados if job else 0,
                job_errores=job.total_errores if job else 0,
                job_mensaje=(job.mensaje or "")[:200] if job else "",
                job_progress_pct=job_pct,
                sync_progress_pct=sync_pct,
                status=status,
                status_label=status_label,
                status_tone=tone,
            )
        )
    return items


def build_migration_overview(
    *,
    conexion: Optional[OdooConnection] = None,
    base_empresa: str = "",
    discovery_conteos: Optional[Dict[str, int]] = None,
    anomalias_count: int = 0,
) -> MigrationOverviewUI:
    dominios: List[DomainProgressUI] = []
    if conexion:
        dominios = build_domain_progress(conexion, discovery_conteos=discovery_conteos)

    fases_ui: List[MigrationPhaseUI] = []
    for phase_def in PHASE_DEFINITIONS:
        phase_domains = [d for d in dominios if d.fase in phase_def["fases"]]
        fases_ui.append(
            MigrationPhaseUI(
                id=phase_def["id"],
                label=str(phase_def["label"]),
                descripcion=str(phase_def["descripcion"]),
                fases=phase_def["fases"],
                dominios=phase_domains,
            )
        )

    completos = sum(1 for d in dominios if d.status == "completado")
    en_curso = sum(1 for d in dominios if d.status == "en_curso")
    con_error = sum(1 for d in dominios if d.status == "error")
    pend_manual = sum(1 for d in dominios if d.status == "pendiente_manual")
    total_ok = sum(d.mappings_ok for d in dominios)
    overall = round(sum(d.sync_progress_pct for d in dominios) / len(dominios)) if dominios else 0

    kpis = {
        "overall_pct": overall,
        "dominios_total": len(dominios),
        "dominios_completos": completos,
        "dominios_en_curso": en_curso,
        "dominios_error": con_error,
        "dominios_pendiente_manual": pend_manual,
        "mapeos_ok": total_ok,
        "jobs_activos": MigrationJob.objects.filter(
            estado=MigrationJob.Estado.EN_CURSO,
            **({"conexion": conexion} if conexion else {}),
        ).count(),
    }

    return MigrationOverviewUI(
        conexion=conexion,
        base_empresa=base_empresa or (conexion.base_empresa if conexion else ""),
        dominios=dominios,
        fases=fases_ui,
        kpis=kpis,
        discovery_done=bool(discovery_conteos),
        anomalias_count=anomalias_count,
    )


def enrich_job_for_ui(job: MigrationJob, origen_count: Optional[int] = None) -> Dict[str, Any]:
    pct = 0
    if origen_count and origen_count > 0:
        pct = min(100, round((job.offset / origen_count) * 100))
    elif job.estado == MigrationJob.Estado.OK:
        pct = 100
    tone = "slate"
    if job.estado == MigrationJob.Estado.OK:
        tone = "emerald"
    elif job.estado == MigrationJob.Estado.EN_CURSO:
        tone = "sky"
    elif job.estado == MigrationJob.Estado.ERROR:
        tone = "red"
    elif job.estado == MigrationJob.Estado.PENDIENTE:
        tone = "amber"
    spec = DOMAIN_BY_KEY.get(job.dominio)
    return {
        "job": job,
        "label": spec.label if spec else job.dominio,
        "fase": spec.fase if spec else "",
        "progress_pct": pct,
        "origen_count": origen_count,
        "tone": tone,
    }
