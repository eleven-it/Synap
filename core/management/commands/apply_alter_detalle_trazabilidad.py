# -*- coding: utf-8 -*-
"""
Aplica el ALTER de trazabilidad en lista_produccion_detalle:
- Renombra id_lista_produccion → id_lista_detalle (identificador de fila)
- Añade id_lista_produccion como FK a lista_produccion_agrupada.id_lista_produccion

Ejecutar con tablas vacías o tras borrar datos.
Uso: python manage.py apply_alter_detalle_trazabilidad <base_empresa> [--dry-run]
Referencia: docs/mpr/sql/alter_lista_produccion_detalle_trazabilidad.sql

La lógica vive en
``core.services.legacy_mysql_schema.catalog.run_mpr_lista_produccion_detalle_trazabilidad_mysql``.
"""
from django.core.management.base import BaseCommand

from core.mysql_pool import get_connection
from core.services.legacy_mysql_schema import run_mpr_lista_produccion_detalle_trazabilidad_mysql
from core.services.legacy_mysql_schema.helpers import columna_existe, nombre_tabla_real


class Command(BaseCommand):
    help = (
        "Aplica ALTER de trazabilidad en lista_produccion_detalle: "
        "id_lista_produccion → id_lista_detalle y añade FK a lista_produccion_agrupada."
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
            help="Solo mostrar qué ALTER se ejecutarían, sin aplicar.",
        )

    def handle(self, *args, **options):
        base_empresa = (options.get("base_empresa") or "").strip()
        dry_run = options.get("dry_run", False)
        if not base_empresa:
            self.stdout.write(self.style.ERROR("Indique base_empresa (ej: administranet92)."))
            return

        try:
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                tbl_detalle = nombre_tabla_real(cursor, "lista_produccion_detalle")
                tbl_agrupada = nombre_tabla_real(cursor, "lista_produccion_agrupada")
                if not tbl_detalle:
                    self.stdout.write(self.style.ERROR("No existe la tabla lista_produccion_detalle en la base."))
                    cursor.close()
                    return
                if not tbl_agrupada:
                    self.stdout.write(self.style.ERROR("No existe la tabla lista_produccion_agrupada en la base."))
                    cursor.close()
                    return

                tiene_id_lista_produccion = columna_existe(cursor, tbl_detalle, "id_lista_produccion")
                tiene_id_lista_detalle = columna_existe(cursor, tbl_detalle, "id_lista_detalle")

                if dry_run:
                    self.stdout.write("Tabla detalle: %s" % tbl_detalle)
                    self.stdout.write("  id_lista_produccion: %s" % tiene_id_lista_produccion)
                    self.stdout.write("  id_lista_detalle: %s" % tiene_id_lista_detalle)
                    if tiene_id_lista_produccion and not tiene_id_lista_detalle:
                        self.stdout.write("Se ejecutaría: DROP FK, CHANGE id_lista_produccion → id_lista_detalle")
                    if not columna_existe(cursor, tbl_detalle, "id_lista_produccion") or (
                        tiene_id_lista_produccion and not tiene_id_lista_detalle
                    ):
                        self.stdout.write("Se ejecutaría: ADD COLUMN id_lista_produccion, ADD FK, CREATE INDEX")
                    cursor.close()
                    return

                cursor.close()

                result = run_mpr_lista_produccion_detalle_trazabilidad_mysql(conn)
                if result.get("success"):
                    self.stdout.write(self.style.SUCCESS(result.get("message", "OK")))
                else:
                    self.stdout.write(self.style.ERROR(result.get("message", "Error")))
        except Exception as e:
            self.stdout.write(self.style.ERROR("Error aplicando ALTER en %s: %s" % (base_empresa, e)))
            raise
