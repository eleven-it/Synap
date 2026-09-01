"""
Unifica un artículo duplicado: transfiere la receta BOM (id_en_abm) al artículo
que conserva movimientos/stock y elimina el duplicado sin actividad.

Uso:
  docker exec Synap_app python manage.py unificar_articulo_duplicado_bom \\
    --base-empresa administranet --id-destino 1346 --id-origen 1352 --id-en-abm 228 --dry-run
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from core.mysql_pool import get_connection
from core.utils.administranet_types import to_int_or_none
from mpr.services import set_articulo_armado_bom


# Tablas hijas que se eliminan (el destino ya tiene equivalentes o no aplica).
_TABLAS_DELETE = (
    ("articulo_prov", "IDArt"),
    ("articulo_val_ce", "id_articulo"),
    ("articulo_valor_ce", "id_articulo"),
    ("stock_deposito", "id_articulo"),
    ("stockp", "IDArt"),
)

# Historial / auditoría: reasignar al destino si no hay conflicto; si no, eliminar.
_TABLAS_UPDATE = (
    ("precios_historial", "id_articulo"),
)

# Inventario físico: el destino ya tiene líneas propias; se eliminan las del duplicado.
_TABLAS_DELETE_INV_FISICO = (
    ("inv_fisico_ajuste_auditoria", "id_articulo"),
    ("inv_fisico_evento", "id_articulo"),
    ("inv_fisico_linea", "id_articulo"),
)


class Command(BaseCommand):
    help = (
        "Transfiere receta BOM (id_en_abm) de un artículo duplicado al que conserva "
        "movimientos y elimina el duplicado."
    )

    def add_arguments(self, parser):
        parser.add_argument("--base-empresa", required=True, help="Base MySQL AdministraNET.")
        parser.add_argument("--id-destino", type=int, required=True, help="IDArt a conservar.")
        parser.add_argument("--id-origen", type=int, required=True, help="IDArt duplicado a eliminar.")
        parser.add_argument("--id-en-abm", type=int, required=True, help="Conjunto BOM a asignar al destino.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo muestra acciones sin persistir cambios.",
        )

    def handle(self, *args, **options):
        base = (options["base_empresa"] or "").strip()
        id_destino = to_int_or_none(options["id_destino"])
        id_origen = to_int_or_none(options["id_origen"])
        id_en_abm = to_int_or_none(options["id_en_abm"])
        dry_run = bool(options["dry_run"])

        if not base:
            raise CommandError("Indique --base-empresa.")
        if not id_destino or not id_origen or not id_en_abm:
            raise CommandError("IDs destino, origen e id_en_abm deben ser enteros válidos.")
        if id_destino == id_origen:
            raise CommandError("Destino y origen no pueden ser el mismo IDArt.")

        self.stdout.write(
            f"{'[DRY-RUN] ' if dry_run else ''}Base={base} destino={id_destino} "
            f"origen={id_origen} id_en_abm={id_en_abm}"
        )

        self._validar_precondiciones(base, id_destino, id_origen, id_en_abm)

        if dry_run:
            self._simular_limpieza(base, id_destino, id_origen, id_en_abm)
            self.stdout.write(self.style.SUCCESS("Dry-run completado. Sin cambios en la base."))
            return

        ok, err = set_articulo_armado_bom(base, id_en_abm, id_destino)
        if not ok:
            raise CommandError(f"No se pudo asignar BOM al destino: {err}")

        self.stdout.write(self.style.SUCCESS(f"BOM {id_en_abm} asignada a IDArt {id_destino}."))

        with get_connection(base) as conn:
            cursor = conn.cursor()
            try:
                deleted, updated = self._limpiar_y_eliminar(cursor, id_destino, id_origen)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        self.stdout.write(self.style.SUCCESS(f"Filas eliminadas: {deleted}, reasignadas: {updated}."))
        self.stdout.write(self.style.SUCCESS(f"Artículo duplicado IDArt {id_origen} eliminado."))

    def _validar_precondiciones(self, base, id_destino, id_origen, id_en_abm):
        with get_connection(base) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT IDArt, NombreArticulo, ensamblado, id_en_abm FROM articulo WHERE IDArt IN (%s, %s)",
                [id_destino, id_origen],
            )
            rows = {int(r[0]): r for r in cursor.fetchall()}
            if id_destino not in rows:
                raise CommandError(f"IDArt destino {id_destino} no existe en {base}.")
            if id_origen not in rows:
                raise CommandError(f"IDArt origen {id_origen} no existe en {base}.")

            dest, orig = rows[id_destino], rows[id_origen]
            self.stdout.write(f"  Destino: {dest[1]} (ensamblado={dest[2]}, id_en_abm={dest[3]})")
            self.stdout.write(f"  Origen:  {orig[1]} (ensamblado={orig[2]}, id_en_abm={orig[3]})")

            cursor.execute(
                "SELECT COUNT(*) FROM stock WHERE IDArt = %s",
                [id_origen],
            )
            if cursor.fetchone()[0]:
                raise CommandError(
                    f"El artículo origen {id_origen} tiene movimientos en stock; abortando."
                )

            cursor.execute(
                """
                SELECT COUNT(*) FROM en_abm_formula f
                INNER JOIN en_abm e ON e.id_en_abm = f.id_en_abm
                WHERE f.id_articulo = %s
                  AND COALESCE(f.anulado, 'No') = 'No'
                  AND COALESCE(e.anulado, 'No') = 'No'
                """,
                [id_origen],
            )
            if cursor.fetchone()[0]:
                raise CommandError(
                    f"El artículo origen {id_origen} es insumo de otra fórmula activa; abortando."
                )

            cursor.execute(
                "SELECT id_en_abm, COALESCE(anulado, 'No') FROM en_abm WHERE id_en_abm = %s",
                [id_en_abm],
            )
            bom = cursor.fetchone()
            if not bom:
                raise CommandError(f"Conjunto BOM id_en_abm={id_en_abm} no existe.")
            if bom[1] != "No":
                raise CommandError(f"Conjunto BOM {id_en_abm} está anulado.")

            cursor.execute(
                """
                SELECT COUNT(*) FROM en_abm_formula
                WHERE id_en_abm = %s AND COALESCE(anulado, 'No') = 'No'
                """,
                [id_en_abm],
            )
            if not cursor.fetchone()[0]:
                raise CommandError(f"Conjunto BOM {id_en_abm} no tiene componentes activos.")

    def _simular_limpieza(self, base, id_destino, id_origen, id_en_abm):
        with get_connection(base) as conn:
            cursor = conn.cursor()
            self.stdout.write("Acciones previstas:")
            self.stdout.write(f"  1. set_articulo_armado_bom({id_en_abm} -> {id_destino})")
            for tbl, col in _TABLAS_DELETE + _TABLAS_DELETE_INV_FISICO:
                if not self._tabla_existe(cursor, tbl) or self._es_vista(cursor, tbl):
                    continue
                cursor.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {col} = %s", [id_origen])
                n = cursor.fetchone()[0]
                if n:
                    self.stdout.write(f"  DELETE {tbl}.{col}={id_origen} ({n} filas)")
            for tbl, col in _TABLAS_UPDATE:
                if not self._tabla_existe(cursor, tbl):
                    continue
                cursor.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {col} = %s", [id_origen])
                n = cursor.fetchone()[0]
                if n:
                    self.stdout.write(f"  UPDATE {tbl}.{col}: {id_origen} -> {id_destino} ({n} filas)")
            self.stdout.write(f"  DELETE articulo.IDArt={id_origen}")

    def _limpiar_y_eliminar(self, cursor, id_destino, id_origen):
        deleted = 0
        updated = 0

        for tbl, col in _TABLAS_DELETE + _TABLAS_DELETE_INV_FISICO:
            if not self._tabla_existe(cursor, tbl):
                continue
            if self._es_vista(cursor, tbl):
                self.stdout.write(f"  Omitiendo vista {tbl}")
                continue
            cursor.execute(f"DELETE FROM {tbl} WHERE {col} = %s", [id_origen])
            deleted += cursor.rowcount

        for tbl, col in _TABLAS_UPDATE:
            if not self._tabla_existe(cursor, tbl):
                continue
            cursor.execute(
                f"UPDATE {tbl} SET {col} = %s WHERE {col} = %s",
                [id_destino, id_origen],
            )
            updated += cursor.rowcount

        cursor.execute("DELETE FROM articulo WHERE IDArt = %s", [id_origen])
        if cursor.rowcount != 1:
            raise CommandError(
                f"No se eliminó exactamente 1 fila de articulo (rowcount={cursor.rowcount})."
            )
        deleted += 1
        return deleted, updated

    @staticmethod
    def _tabla_existe(cursor, tabla: str) -> bool:
        cursor.execute("SHOW TABLES LIKE %s", [tabla])
        return bool(cursor.fetchone())

    @staticmethod
    def _es_vista(cursor, tabla: str) -> bool:
        cursor.execute(
            """
            SELECT TABLE_TYPE FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            """,
            [tabla],
        )
        row = cursor.fetchone()
        return bool(row and row[0] == "VIEW")
