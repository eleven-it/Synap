# -*- coding: utf-8 -*-
"""
Crea tablas de trazabilidad MPR por máquina/línea/operario y extiende el ledger de partes.
Referencia: mpr/sql/003_mpr_maquina_linea_tables.sql, mpr/sql/004_mpr_parte_maquina_gap.sql,
openspec/changes/mpr-trazabilidad-maquina-linea-operario/design.md

Lógica: core.services.legacy_mysql_schema.catalog.run_mpr_maquina_linea_mysql
"""
from django.core.management.base import BaseCommand

from core.mysql_pool import get_connection
from core.services.legacy_mysql_schema.catalog import run_mpr_maquina_linea_mysql


class Command(BaseCommand):
    help = (
        "Crea tablas mpr_linea/mpr_maquina/... y extiende mpr_parte, mpr_parte_linea y "
        "mpr_roster_dia en la base administranet. Ejemplo: apply_mpr_maquina_linea administranet92"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "base_empresa",
            type=str,
            help="Base de datos de la empresa (ej: administranet92).",
        )

    def handle(self, *args, **options):
        base_empresa = (options.get("base_empresa") or "").strip()
        if not base_empresa:
            self.stdout.write(self.style.ERROR("Indique base_empresa (ej: administranet92)."))
            return

        try:
            with get_connection(base_empresa) as conn:
                result = run_mpr_maquina_linea_mysql(conn)
                if result.get("success"):
                    self.stdout.write(self.style.SUCCESS(result.get("message", "OK")))
                    for item in result.get("migrations_applied") or []:
                        self.stdout.write(f"  · {item}")
                else:
                    self.stdout.write(self.style.ERROR(result.get("message", "Error")))
                    for item in result.get("migrations_failed") or []:
                        self.stdout.write(self.style.ERROR(f"  · {item}"))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    "Error aplicando trazabilidad máquina/línea en %s: %s" % (base_empresa, e)
                )
            )
