# -*- coding: utf-8 -*-
"""
Aplica el schema MPR en la base administranet (base_empresa): columnas
deposito.suma_stock y articulo.stock_reserva. Si ya existen, no hace nada.
Referencia: docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md

La lógica vive en ``core.services.legacy_mysql_schema.catalog.run_mpr_deposito_articulo_mysql``.
"""
from django.core.management.base import BaseCommand

from core.mysql_pool import get_connection
from core.services.legacy_mysql_schema import run_mpr_deposito_articulo_mysql
from core.services.legacy_mysql_schema.helpers import columna_existe


class Command(BaseCommand):
    help = (
        "Aplica columnas MPR en base administranet: deposito.suma_stock, articulo.stock_reserva. "
        "Ejecutar por base de empresa (ej: administranet89)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "base_empresa",
            type=str,
            help="Base de datos de la empresa (ej: administranet89, administranet92).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo mostrar qué ALTER se ejecutarían, sin aplicar.",
        )

    def handle(self, *args, **options):
        base_empresa = (options.get("base_empresa") or "").strip()
        dry_run = options.get("dry_run", False)
        if not base_empresa:
            self.stdout.write(self.style.ERROR("Indique base_empresa (ej: administranet89)."))
            return

        try:
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                alter_deposito = not columna_existe(cursor, "deposito", "suma_stock")
                alter_articulo = not columna_existe(cursor, "articulo", "stock_reserva")
                cursor.close()

                if dry_run:
                    if alter_deposito:
                        self.stdout.write(
                            "Se ejecutaría: ALTER TABLE deposito ADD COLUMN suma_stock VARCHAR(2) DEFAULT 'Si';"
                        )
                    else:
                        self.stdout.write("deposito.suma_stock ya existe, no se modifica.")
                    if alter_articulo:
                        self.stdout.write(
                            "Se ejecutaría: ALTER TABLE articulo ADD COLUMN stock_reserva DECIMAL(15,2) DEFAULT NULL;"
                        )
                    else:
                        self.stdout.write("articulo.stock_reserva ya existe, no se modifica.")
                    return

                result = run_mpr_deposito_articulo_mysql(conn)
                if result.get("success"):
                    self.stdout.write(self.style.SUCCESS(result.get("message", "OK")))
                else:
                    self.stdout.write(self.style.ERROR(result.get("message", "Error")))
        except Exception as e:
            self.stdout.write(self.style.ERROR("Error aplicando schema MPR en %s: %s" % (base_empresa, e)))
