# -*- coding: utf-8 -*-
"""
Crea las tablas de log de corrección contable Fase 3 en la base MySQL de la empresa.

Referencia: contabilidad_audit/sql/cont_audit_correccion_log.sql,
openspec/changes/contabilidad-auditoria-recalculo/design.md §5 decisión 7.

Lógica: core.services.legacy_mysql_schema.catalog.run_contabilidad_audit_correccion_log_mysql
"""
from django.core.management.base import BaseCommand

from core.mysql_pool import get_connection
from core.services.legacy_mysql_schema.catalog import run_contabilidad_audit_correccion_log_mysql


class Command(BaseCommand):
    help = (
        "Crea cont_audit_correccion_lote y cont_audit_correccion en la base de la empresa. "
        "Ejemplo: apply_contabilidad_audit_correccion_log administranet89"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "base_empresa",
            type=str,
            help="Base de datos de la empresa (ej: administranet89).",
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
            self.stdout.write(self.style.ERROR("Indique base_empresa (ej: administranet89)."))
            return

        if dry_run:
            self.stdout.write(
                "Se ejecutaría DDL desde contabilidad_audit/sql/cont_audit_correccion_log.sql "
                f"en base {base_empresa} (cont_audit_correccion_lote + cont_audit_correccion)."
            )
            return

        try:
            with get_connection(base_empresa) as conn:
                result = run_contabilidad_audit_correccion_log_mysql(conn)
                if result.get("success"):
                    self.stdout.write(self.style.SUCCESS(result.get("message", "OK")))
                    for item in result.get("migrations_applied") or []:
                        self.stdout.write(f"  · {item}")
                else:
                    self.stdout.write(self.style.ERROR(result.get("message", "Error")))
                    for item in result.get("migrations_failed") or []:
                        self.stdout.write(self.style.ERROR(f"  · {item}"))
        except Exception as exc:
            self.stdout.write(
                self.style.ERROR(
                    "Error aplicando log de corrección contable en %s: %s"
                    % (base_empresa, exc)
                )
            )
