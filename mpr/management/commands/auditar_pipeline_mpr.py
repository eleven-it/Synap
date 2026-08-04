# MPR — Auditoría read-only pipeline diario: parte → CC → armado + mstock.
#
# Ejemplo (prueba):
#   docker exec Synap_app python manage.py auditar_pipeline_mpr \
#     --base-empresa=administranet1 \
#     --desde=22/07/2026 --hasta=03/08/2026 \
#     --host=181.174.198.194 --port=30804 \
#     --output=/app/tmp_exports/audit_pipeline_administranet1.json
#
# Producción (solo lectura; misma firma, otra base):
#   ... --base-empresa=administranet ...

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_date_or_none
from mpr.auditoria_pipeline import auditar_rango, _ser


def parse_fecha_arg(valor: str):
    texto = (valor or "").strip()
    if not texto:
        raise CommandError("Indique fecha (YYYY-MM-DD o dd/MM/yyyy).")
    iso = to_date_or_none(texto)
    if iso:
        try:
            return datetime.strptime(iso, "%Y-%m-%d").date()
        except ValueError:
            pass
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    raise CommandError(
        f"Fecha inválida: {valor!r}. Use YYYY-MM-DD o dd/MM/yyyy (ej. 22/07/2026)."
    )


class Command(BaseCommand):
    help = (
        "Audita integridad referencial y coherencia de stock del pipeline MPR "
        "(parte → control de calidad → armado) por día. Solo lectura."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-empresa",
            type=str,
            required=True,
            help="Base MySQL (producción: administranet | prueba: administranet1).",
        )
        parser.add_argument(
            "--desde",
            type=str,
            required=True,
            help="Fecha inicio inclusive (dd/MM/yyyy o YYYY-MM-DD).",
        )
        parser.add_argument(
            "--hasta",
            type=str,
            required=True,
            help="Fecha fin inclusive (dd/MM/yyyy o YYYY-MM-DD).",
        )
        parser.add_argument(
            "--host",
            type=str,
            default="",
            help="Host MySQL opcional (si se omite, usa el pool Synap / DB_HOST).",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=0,
            help="Puerto MySQL opcional (junto con --host).",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Ruta JSON de salida (default: tmp_exports/audit_pipeline_<base>_<desde>_<hasta>.json).",
        )

    def handle(self, *args, **options):
        base = (options.get("base_empresa") or "").strip()
        if not base:
            raise CommandError("Indique --base-empresa.")

        desde = parse_fecha_arg(options["desde"])
        hasta = parse_fecha_arg(options["hasta"])
        if hasta < desde:
            raise CommandError("--hasta no puede ser anterior a --desde.")

        host = (options.get("host") or "").strip()
        port = int(options.get("port") or 0) or 3306
        output = (options.get("output") or "").strip()
        if not output:
            slug_d = desde.strftime("%Y%m%d")
            slug_h = hasta.strftime("%Y%m%d")
            output = (
                f"/app/tmp_exports/audit_pipeline_{base}_{slug_d}_{slug_h}.json"
            )

        self.stdout.write(
            self.style.WARNING(
                f"[READ-ONLY] Auditoría pipeline MPR — base={base}, "
                f"desde={desde.strftime('%d/%m/%Y')}, hasta={hasta.strftime('%d/%m/%Y')}"
                + (f", host={host}:{port}" if host else " (pool Synap)")
            )
        )

        if host:
            informe = self._correr_host_directo(base, desde, hasta, host, port)
        else:
            with mysql_cursor(base, dict_cursor=True) as cursor:
                informe = auditar_rango(cursor, base, desde, hasta)

        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(informe, fh, ensure_ascii=False, indent=2, default=_ser)

        resumen = informe.get("resumen") or {}
        self.stdout.write(self.style.SUCCESS(f"Informe: {path}"))
        self.stdout.write(json.dumps(resumen, ensure_ascii=False, indent=2))
        self.stdout.write("--- por día ---")
        for d in informe.get("dias") or []:
            rd = d.get("resumen_dia") or {}
            self.stdout.write(
                json.dumps(
                    {
                        "fecha": d.get("fecha"),
                        "severidad": d.get("severidad"),
                        "parte_pares": rd.get("parte_pares"),
                        "cc_pares": rd.get("cc_pares"),
                        "delta_cls_fab": rd.get("delta_cls_fab"),
                        "cls_gt_fab_n": rd.get("cls_gt_fab_n"),
                        "armado_lotes": rd.get("armado_lotes"),
                        "armado_packs": rd.get("armado_packs"),
                        "alertas": d.get("alertas") or [],
                    },
                    ensure_ascii=False,
                )
            )

        criticos = [d for d in (informe.get("dias") or []) if d.get("severidad") == "critico"]
        if criticos:
            self.stdout.write(
                self.style.ERROR(
                    f"{len(criticos)} día(s) con severidad crítico "
                    f"(p. ej. cls>fab)."
                )
            )
        elif resumen.get("dias_alerta"):
            self.stdout.write(
                self.style.WARNING(
                    f"{resumen['dias_alerta']} día(s) con alertas de integridad."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Sin alertas en el rango."))

    def _correr_host_directo(self, base, desde, hasta, host, port):
        import MySQLdb

        user = os.environ.get("DB_USER") or ""
        passwd = os.environ.get("DB_PASSWORD") or ""
        if not user:
            raise CommandError("Falta DB_USER en el entorno para --host.")
        conn = MySQLdb.connect(
            host=host,
            port=int(port),
            user=user,
            passwd=passwd,
            db=base,
            connect_timeout=15,
            charset="utf8mb4",
        )
        try:
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)
            return auditar_rango(cursor, base, desde, hasta)
        finally:
            conn.close()
