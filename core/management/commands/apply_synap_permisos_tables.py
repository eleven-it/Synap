# -*- coding: utf-8 -*-
"""
Crea las tablas de permisos/roles Synap (synap_*) en la base MySQL de la empresa
y siembra el catálogo synap_permiso. No escribe en tablas VB6 (permiso_sistema*).

Referencia: core/sql/001_synap_permisos_tables.sql,
openspec/changes/permisos-roles-synap-independientes/design.md

Lógica: core.services.legacy_mysql_schema.catalog.run_synap_permisos_tables_mysql
"""
from django.core.management.base import BaseCommand

from core.mysql_pool import get_connection
from core.services.legacy_mysql_schema import run_synap_permisos_tables_mysql


class Command(BaseCommand):
    help = (
        "Crea tablas synap_* (permisos y roles Synap) y siembra el catálogo en la "
        "base de la empresa. Ejemplo: apply_synap_permisos_tables administranet92"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "base_empresa",
            type=str,
            help="Base de datos de la empresa (ej: administranet92).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo indica que se ejecutaría el DDL (sin cambios).",
        )

    def handle(self, *args, **options):
        base_empresa = (options.get("base_empresa") or "").strip()
        dry_run = options.get("dry_run", False)
        if not base_empresa:
            self.stdout.write(self.style.ERROR("Indique base_empresa (ej: administranet92)."))
            return

        if dry_run:
            self.stdout.write(
                "Se ejecutaría DDL desde core/sql/001_synap_permisos_tables.sql "
                f"en base {base_empresa} (4 tablas synap_* + seed synap_permiso)."
            )
            return

        try:
            with get_connection(base_empresa) as conn:
                result = run_synap_permisos_tables_mysql(conn)
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
                self.style.ERROR("Error aplicando tablas Synap permisos en %s: %s" % (base_empresa, e))
            )
