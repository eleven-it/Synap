# -*- coding: utf-8 -*-
"""
Elimina tablas OPT legacy lista_produccion_* en la base MySQL de una empresa.

Destructivo e irreversible. Sirve para forzar la detección de código no migrado
al flujo MPR diario (ledgers mpr_*).

Ver ``core.services.legacy_mysql_schema.catalog.run_mpr_drop_lista_produccion_legacy_mysql``.
"""
from django.core.management.base import BaseCommand

from core.mysql_pool import get_connection
from core.services.legacy_mysql_schema import run_mpr_drop_lista_produccion_legacy_mysql


class Command(BaseCommand):
    help = (
        "DROP lista_produccion_historico, lista_produccion_detalle y lista_produccion_agrupada "
        "en la base MySQL indicada. Requiere --confirm."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "base_empresa",
            type=str,
            help="Base de datos de la empresa (ej: administranet96).",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirma la eliminación irreversible de las tablas legacy.",
        )

    def handle(self, *args, **options):
        base_empresa = (options.get("base_empresa") or "").strip()
        if not base_empresa:
            self.stdout.write(self.style.ERROR("Indique base_empresa (ej: administranet96)."))
            return
        if not options.get("confirm"):
            self.stdout.write(
                self.style.WARNING(
                    "Operación destructiva. Repita con --confirm para ejecutar el DROP."
                )
            )
            return

        try:
            with get_connection(base_empresa) as conn:
                result = run_mpr_drop_lista_produccion_legacy_mysql(conn)
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Error de conexión o ejecución: {exc}"))
            return

        for line in result.get("migrations_applied") or []:
            self.stdout.write(self.style.SUCCESS(f"  ✓ {line}"))
        for line in result.get("migrations_failed") or []:
            self.stdout.write(self.style.ERROR(f"  ✗ {line}"))

        if result.get("success"):
            self.stdout.write(self.style.SUCCESS(result.get("message") or "OK"))
        else:
            self.stdout.write(self.style.ERROR(result.get("message") or "Falló"))
