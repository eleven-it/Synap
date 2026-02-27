# -*- coding: utf-8 -*-
"""Inspecciona tablas lista_produccion_agrupada y lista_produccion_agrupada_formula en la base MySQL."""
from django.core.management.base import BaseCommand

from core.mysql_pool import get_connection


class Command(BaseCommand):
    help = "Muestra estructura de lista_produccion_agrupada y lista_produccion_agrupada_formula y relaciones."

    def add_arguments(self, parser):
        parser.add_argument("base_empresa", nargs="?", default="administranet89", help="Base de datos (ej: administranet89)")

    def handle(self, *args, **options):
        base_empresa = options.get("base_empresa") or "administranet89"
        with get_connection(base_empresa) as conn:
            c = conn.cursor()
            c.execute("SHOW TABLES")
            tables = [r[0] for r in c.fetchall()]
            agrupada = next((t for t in tables if t.lower() == "lista_produccion_agrupada"), None)
            formula = next((t for t in tables if t.lower() == "lista_produccion_agrupada_formula"), None)

            self.stdout.write("Tabla lista_produccion_agrupada: %s" % (agrupada or "NO EXISTE"))
            self.stdout.write("Tabla lista_produccion_agrupada_formula: %s" % (formula or "NO EXISTE"))

            if agrupada:
                self.stdout.write("\n--- COLUMNAS lista_produccion_agrupada ---")
                c.execute("SHOW COLUMNS FROM `%s`" % agrupada.replace("`", "``"))
                for row in c.fetchall():
                    self.stdout.write("  %s" % (row,))
                self.stdout.write("\n--- CREATE TABLE lista_produccion_agrupada ---")
                c.execute("SHOW CREATE TABLE `%s`" % agrupada.replace("`", "``"))
                self.stdout.write(c.fetchone()[1])

            if formula:
                self.stdout.write("\n--- COLUMNAS lista_produccion_agrupada_formula ---")
                c.execute("SHOW COLUMNS FROM `%s`" % formula.replace("`", "``"))
                for row in c.fetchall():
                    self.stdout.write("  %s" % (row,))
                self.stdout.write("\n--- CREATE TABLE lista_produccion_agrupada_formula ---")
                c.execute("SHOW CREATE TABLE `%s`" % formula.replace("`", "``"))
                self.stdout.write(c.fetchone()[1])

            # Relaciones: information_schema KEY_COLUMN_USAGE si hay FK
            self.stdout.write("\n--- REFERENCIAS (information_schema) ---")
            c.execute(
                """
                SELECT TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s
                  AND (TABLE_NAME LIKE %s OR REFERENCED_TABLE_NAME LIKE %s)
                  AND REFERENCED_TABLE_NAME IS NOT NULL
                """,
                (base_empresa, "lista_produccion_agrupada%", "lista_produccion_agrupada%"),
            )
            rows = c.fetchall()
            if rows:
                for r in rows:
                    self.stdout.write("  %s" % (r,))
            else:
                self.stdout.write("  (No hay FKs declaradas en information_schema para estas tablas)")
