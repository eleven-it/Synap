"""Programador Mtrix (mismo criterio que backup_tick)."""

from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from mtrix.models import MtrixConfig, MtrixJob
from mtrix.services.orchestrator import crear_job, hay_job_activo

DOW_LABELS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
DEDUPE_MINUTES = 50


def normalize_schedule(schedule_json) -> list[dict]:
    rules = []
    if not isinstance(schedule_json, list):
        return rules
    for item in schedule_json:
        try:
            dow = int(item.get("dow"))
            time_str = str(item.get("time") or "06:00").strip()
            if dow < 0 or dow > 6:
                continue
            datetime.strptime(time_str, "%H:%M")
        except (TypeError, ValueError, AttributeError):
            continue
        rules.append({"dow": dow, "time": time_str})
    return rules


def matching_rules(cfg: MtrixConfig, now=None, *, match_minute: bool = True) -> list[dict]:
    if not cfg.programador_activo:
        return []
    now = now or timezone.localtime()
    dow = now.weekday()  # 0=lunes
    hhmm = now.strftime("%H:%M")
    hour = now.strftime("%H")
    matched = []
    for rule in normalize_schedule(cfg.schedule_json):
        if int(rule["dow"]) != dow:
            continue
        if match_minute and rule["time"] != hhmm:
            continue
        if not match_minute and not rule["time"].startswith(hour):
            continue
        matched.append(rule)
    return matched


def has_recent_scheduled_job(base_empresa: str) -> bool:
    since = timezone.now() - timedelta(minutes=DEDUPE_MINUTES)
    return MtrixJob.objects.filter(
        base_empresa=base_empresa,
        origen=MtrixJob.Origen.CRON,
        created_at__gte=since,
    ).exists()


def jobs_a_lanzar(*, now=None, match_minute: bool = True) -> list[MtrixJob]:
    creados = []
    now = now or timezone.localtime()
    for cfg in MtrixConfig.objects.filter(programador_activo=True):
        if not matching_rules(cfg, now, match_minute=match_minute):
            continue
        if hay_job_activo(cfg.base_empresa):
            continue
        if has_recent_scheduled_job(cfg.base_empresa):
            continue
        try:
            creados.append(
                crear_job(base_empresa=cfg.base_empresa, origen=MtrixJob.Origen.CRON, triggered_by="cron")
            )
        except RuntimeError:
            continue
    return creados
