# -*- coding: utf-8 -*-
"""
Aplica el ALTER de trazabilidad en lista_produccion_detalle:
- Renombra id_lista_produccion → id_lista_detalle (identificador de fila)
- Añade id_lista_produccion como FK a lista_produccion_agrupada.id_lista_produccion

Ejecutar con tablas vacías o tras borrar datos.
Uso: python manage.py apply_alter_detalle_trazabilidad <base_empresa> [--dry-run]
Referencia: docs/mpr/sql/alter_lista_produccion_detalle_trazabilidad.sql
"""
from django.core.management.base import BaseCommand

from core.mysql_pool import get_connection


def _nombre_tabla(cursor, nombre_lower: str):
    """Devuelve el nombre real de la tabla (puede variar mayúsculas/minúsculas)."""
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall():
        nombre = (row[0] if row else "").strip() if hasattr(row[0], "strip") else str(row[0] or "").strip()
        if nombre and nombre.lower() == nombre_lower:
            return nombre
    return None


def _columna_existe(cursor, tabla: str, columna: str) -> bool:
    cursor.execute("SHOW COLUMNS FROM `{}` LIKE %s".format(tabla.replace("`", "``")), (columna,))
    return cursor.fetchone() is not None


def _indice_existe(cursor, tabla: str, indice: str) -> bool:
    cursor.execute("SHOW INDEX FROM `{}` WHERE Key_name = %s".format(tabla.replace("`", "``")), (indice,))
    return cursor.fetchone() is not None


def _fk_existe(cursor, tabla: str, fk_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.TABLE_CONSTRAINTS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND CONSTRAINT_NAME = %s AND CONSTRAINT_TYPE = 'FOREIGN KEY'",
        (tabla, fk_name),
    )
    return cursor.fetchone() is not None


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
                tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
                tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
                if not tbl_detalle:
                    self.stdout.write(self.style.ERROR("No existe la tabla lista_produccion_detalle en la base."))
                    return
                if not tbl_agrupada:
                    self.stdout.write(self.style.ERROR("No existe la tabla lista_produccion_agrupada en la base."))
                    return

                tiene_id_lista_produccion = _columna_existe(cursor, tbl_detalle, "id_lista_produccion")
                tiene_id_lista_detalle = _columna_existe(cursor, tbl_detalle, "id_lista_detalle")

                if dry_run:
                    self.stdout.write("Tabla detalle: %s" % tbl_detalle)
                    self.stdout.write("  id_lista_produccion: %s" % tiene_id_lista_produccion)
                    self.stdout.write("  id_lista_detalle: %s" % tiene_id_lista_detalle)
                    if tiene_id_lista_produccion and not tiene_id_lista_detalle:
                        self.stdout.write("Se ejecutaría: DROP FK, CHANGE id_lista_produccion → id_lista_detalle")
                    if not _columna_existe(cursor, tbl_detalle, "id_lista_produccion") or (tiene_id_lista_produccion and not tiene_id_lista_detalle):
                        self.stdout.write("Se ejecutaría: ADD COLUMN id_lista_produccion, ADD FK, CREATE INDEX")
                    return

                conn.autocommit(False)
                try:
                    # 1) Si existe id_lista_produccion y no existe id_lista_detalle: eliminar FK y renombrar
                    if tiene_id_lista_produccion and not tiene_id_lista_detalle:
                        cursor.execute(
                            "SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE "
                            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = 'id_lista_produccion' "
                            "AND REFERENCED_TABLE_NAME IS NOT NULL LIMIT 1",
                            (tbl_detalle,),
                        )
                        row = cursor.fetchone()
                        fk_name = (row[0] if row and row[0] else "").strip() if row else None
                        if fk_name:
                            cursor.execute("ALTER TABLE `{}` DROP FOREIGN KEY `{}`".format(tbl_detalle.replace("`", "``"), fk_name.replace("`", "``")))
                            self.stdout.write(self.style.SUCCESS("FK %s eliminada." % fk_name))
                        cursor.execute(
                            "ALTER TABLE `{}` CHANGE COLUMN id_lista_produccion id_lista_detalle BIGINT NOT NULL AUTO_INCREMENT".format(
                                tbl_detalle.replace("`", "``")
                            )
                        )
                        self.stdout.write(self.style.SUCCESS("Columna renombrada a id_lista_detalle."))
                        tiene_id_lista_produccion = False

                    # 2) Añadir id_lista_produccion si no existe
                    if not _columna_existe(cursor, tbl_detalle, "id_lista_produccion"):
                        after_clause = " AFTER id_lista_detalle" if _columna_existe(cursor, tbl_detalle, "id_lista_detalle") else ""
                        cursor.execute(
                            "ALTER TABLE `{}` ADD COLUMN id_lista_produccion BIGINT NULL DEFAULT NULL{}".format(
                                tbl_detalle.replace("`", "``"), after_clause
                            )
                        )
                        self.stdout.write(self.style.SUCCESS("Columna id_lista_produccion añadida."))

                    # 3) FK a lista_produccion_agrupada
                    fk_name = "fk_detalle_agrupada_lista_produccion"
                    if not _fk_existe(cursor, tbl_detalle, fk_name):
                        cursor.execute(
                            "ALTER TABLE `{det}` ADD CONSTRAINT `{fk}` FOREIGN KEY (id_lista_produccion) "
                            "REFERENCES `{agr}`(id_lista_produccion)".format(
                                det=tbl_detalle.replace("`", "``"),
                                fk=fk_name,
                                agr=tbl_agrupada.replace("`", "``"),
                            )
                        )
                        self.stdout.write(self.style.SUCCESS("FK fk_detalle_agrupada_lista_produccion creada."))

                    # 4) Índice
                    idx_name = "idx_detalle_id_lista_produccion"
                    if not _indice_existe(cursor, tbl_detalle, idx_name):
                        cursor.execute(
                            "CREATE INDEX `{}` ON `{}`(id_lista_produccion)".format(
                                idx_name, tbl_detalle.replace("`", "``")
                            )
                        )
                        self.stdout.write(self.style.SUCCESS("Índice %s creado." % idx_name))

                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    raise e
        except Exception as e:
            self.stdout.write(self.style.ERROR("Error aplicando ALTER en %s: %s" % (base_empresa, e)))
            raise
