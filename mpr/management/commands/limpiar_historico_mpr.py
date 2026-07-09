# Limpia ledgers operativos MPR y stock en depósitos tipo_mpr (entorno de pruebas).
# Uso:
#   docker exec Synap_app python manage.py limpiar_historico_mpr --base-empresa=administranet96 --confirm
#   docker exec Synap_app python manage.py limpiar_historico_mpr --base-empresa=administranet96 --dry-run
# No borra: mpr_config, mpr_turno, mpr_articulo_armado_surtido (catálogo / parámetros).

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from core.mysql_pool import mysql_cursor

# Orden: hijos antes que padres (FK).
_TABLAS_LEDGER = (
    "mpr_armado_surtido_linea",
    "mpr_armado_surtido_movimiento",
    "mpr_imputacion_armado",
    "mpr_armado_lote",
    "mpr_parte_ajuste",
    "mpr_parte_linea",
    "mpr_parte",
    "mpr_transicion_lote",
    "mpr_envio_produccion",
    "mpr_roster_dia",
)


def _nombre_tabla(cursor, nombre_lower: str) -> str | None:
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall() or []:
        if isinstance(row, dict):
            nombre = (list(row.values())[0] or "").strip()
        else:
            nombre = (row[0] if row else "").strip()
        if nombre and nombre.lower() == nombre_lower:
            return nombre
    return None


def _conteo_tabla(cursor, tabla: str) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM `{tabla}`")
    row = cursor.fetchone()
    if isinstance(row, dict):
        return int(list(row.values())[0] or 0)
    return int(row[0] or 0)


def _conteo_stock_mpr(cursor) -> tuple[int, float]:
    tbl_sd = _nombre_tabla(cursor, "stock_deposito")
    tbl_dep = _nombre_tabla(cursor, "deposito")
    if not tbl_sd or not tbl_dep:
        return 0, 0.0
    cursor.execute(
        f"""
        SELECT COUNT(*) AS n, COALESCE(SUM(sd.saldo), 0) AS s
        FROM `{tbl_sd}` sd
        INNER JOIN `{tbl_dep}` d ON d.CodDeposito = sd.id_deposito
        WHERE d.tipo_mpr IS NOT NULL AND TRIM(d.tipo_mpr) <> ''
          AND COALESCE(sd.saldo, 0) <> 0
        """
    )
    row = cursor.fetchone()
    if isinstance(row, dict):
        return int(row.get("n") or 0), float(row.get("s") or 0)
    return int(row[0] or 0), float(row[1] or 0)


class Command(BaseCommand):
    help = (
        "Elimina historial operativo MPR (envíos, partes, transiciones, armado, roster) "
        "y pone saldo 0 en depósitos con tipo_mpr. Requiere --confirm."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-empresa",
            required=True,
            help="Base MySQL de la empresa (ej. administranet96).",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Ejecutar borrado (sin esto solo informa conteos con --dry-run implícito).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo mostrar qué se borraría, sin modificar datos.",
        )
        parser.add_argument(
            "--sin-cero-stock",
            action="store_true",
            help="No poner saldo 0 en stock_deposito de depósitos MPR.",
        )

    def handle(self, *args, **options):
        base = (options.get("base_empresa") or "").strip()
        if not base:
            raise CommandError("Indique --base-empresa.")

        confirm = bool(options.get("confirm"))
        dry_run = bool(options.get("dry_run")) or not confirm
        cero_stock = not bool(options.get("sin_cero_stock"))

        if not dry_run and not confirm:
            raise CommandError("Use --confirm para ejecutar el borrado.")

        with mysql_cursor(base) as cursor:
            tablas_existentes: list[str] = []
            conteos: dict[str, int] = {}
            for t in _TABLAS_LEDGER:
                real = _nombre_tabla(cursor, t)
                if not real:
                    self.stdout.write(self.style.WARNING(f"  Omitida (no existe): {t}"))
                    continue
                tablas_existentes.append(real)
                conteos[real] = _conteo_tabla(cursor, real)

            filas_stock, suma_stock = _conteo_stock_mpr(cursor)

        self.stdout.write(f"Base: {base}")
        self.stdout.write("Ledgers MPR:")
        total_filas = 0
        for t in tablas_existentes:
            n = conteos.get(t, 0)
            total_filas += n
            self.stdout.write(f"  {t}: {n}")
        self.stdout.write(f"  Total filas ledger: {total_filas}")
        if cero_stock:
            self.stdout.write(
                f"Stock MPR (filas con saldo ≠ 0 en depósitos tipo_mpr): {filas_stock} "
                f"(suma saldo: {suma_stock})"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: no se modificó la base."))
            return

        with mysql_cursor(base) as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            try:
                for t in tablas_existentes:
                    cursor.execute(f"DELETE FROM `{t}`")
                    self.stdout.write(f"  Borrado {t}: {conteos.get(t, 0)} fila(s)")

                if cero_stock:
                    tbl_sd = _nombre_tabla(cursor, "stock_deposito")
                    tbl_dep = _nombre_tabla(cursor, "deposito")
                    if tbl_sd and tbl_dep:
                        cursor.execute(
                            f"""
                            UPDATE `{tbl_sd}` sd
                            INNER JOIN `{tbl_dep}` d ON d.CodDeposito = sd.id_deposito
                            SET sd.saldo = 0
                            WHERE d.tipo_mpr IS NOT NULL AND TRIM(d.tipo_mpr) <> ''
                            """
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  Stock MPR: {cursor.rowcount} fila(s) en stock_deposito → saldo 0"
                            )
                        )
            finally:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        self.stdout.write(self.style.SUCCESS(f"Historial MPR limpiado en {base}."))
