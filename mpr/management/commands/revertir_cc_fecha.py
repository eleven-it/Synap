# MPR — Inventario / apply para revertir el Control de calidad (CC) de una o más fechas.
# Objetivo: poder volver a cargar el parte de producción de la fecha. La grilla del
# parte se bloquea mientras exista alguna fila en mpr_transicion_lote con
# fecha_produccion = fecha (fecha_tiene_control_calidad).
#
# Qué revierte (por fecha):
#   - movimiento_stock de la transición CC (tipo_mov 'OPP', detalle 'Transición MPR ...'):
#     anulado='Si'.
#   - stock (Salida/Entrada) con el mismo CodigoMovimiento: anulado='Si'
#     (o DELETE si la base no tiene la columna, igual que revertir_partes_fecha).
#   - stock_deposito.saldo: saldo += Salida - Entrada por renglón.
#   - DELETE de mpr_transicion_lote WHERE fecha_produccion = fecha.
# No toca: codmov / talonarios (contadores), mpr_parte*, borradores mpr_cc_borrador*,
# ni lista_produccion_historico (la transición CC no escribe ahí; ver
# _transferir_etapa_en_cursor en mpr/services.py).
#
# Uso dry-run:
#   docker exec Synap_app python manage.py revertir_cc_fecha \
#     --base-empresa=administranet1 --fecha=22/07/2026 \
#     --host=192.168.0.2 --port=30804
# Uso apply (pruebas):
#   docker exec Synap_app python manage.py revertir_cc_fecha \
#     --base-empresa=administranet1 \
#     --fecha=22/07/2026 --fecha=23/07/2026 \
#     --host=192.168.0.2 --port=30804 \
#     --apply --confirmar=RESET
# Apply sobre 'administranet' (prod) requiere además --forzar-produccion.

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_decimal_or_none, to_int_or_none
from mpr.management.commands.revertir_partes_fecha import (
    _fmt_decimal,
    _fmt_fecha_es,
    _row_val,
    parse_fecha_arg,
    parse_fechas_args,
    str_or_blank,
)
from mpr.services import MOTIVO_OPP_TEXTO, TIPO_MOV_OPP, _nombre_tabla

__all__ = ["Command", "parse_fecha_arg", "parse_fechas_args"]

MSG_CONFIRMAR_REQUERIDO = (
    "Para --apply indique --confirmar=RESET (revertir CC: anular movimientos de "
    "transición, ajustar stock_deposito y borrar mpr_transicion_lote de la(s) fecha(s))."
)
MSG_PRODUCCION_BLOQUEADA = (
    "Apply bloqueado sobre base 'administranet' (producción). "
    "Use una base de prueba (ej. administranet1) o --forzar-produccion."
)
CONFIRMAR_RESET = "RESET"
DETALLE_TRANSICION_PREFIJO = "Transición MPR"
MAX_FILAS_CC_LISTADO = 200


def _ph(n: int) -> str:
    return ",".join(["%s"] * n)


def _es_anulado(valor: Any) -> bool:
    return str_or_blank(valor).lower() == "si"


def movimiento_es_transicion_mpr(row: Any) -> bool:
    """True si el movimiento_stock es una transición MPR/CC (OPP + 'Transición MPR …')."""
    tipo = str_or_blank(_row_val(row, "tipo_mov")).upper()
    detalle = str_or_blank(_row_val(row, "detalle"))
    motivo = str_or_blank(_row_val(row, "motivo_movimiento"))
    if tipo != TIPO_MOV_OPP:
        return False
    if not detalle.startswith(DETALLE_TRANSICION_PREFIJO):
        return False
    return not motivo or motivo == MOTIVO_OPP_TEXTO


class Command(BaseCommand):
    help = (
        "Revierte el Control de calidad (CC) de una o más fechas (dry-run o "
        "--apply --confirmar=RESET): anula movimientos de transición, ajusta "
        "stock_deposito y borra mpr_transicion_lote."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-empresa",
            type=str,
            required=True,
            help="Base MySQL de la empresa (obligatorio).",
        )
        parser.add_argument(
            "--fecha",
            action="append",
            dest="fechas",
            default=None,
            help="Fecha de producción (YYYY-MM-DD o dd/MM/yyyy). Repetible o CSV.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Ejecutar reversión (requiere --confirmar=RESET).",
        )
        parser.add_argument(
            "--confirmar",
            type=str,
            default="",
            help=f"Debe ser '{CONFIRMAR_RESET}' junto con --apply.",
        )
        parser.add_argument(
            "--forzar-produccion",
            action="store_true",
            help="Permite --apply sobre base administranet (producción). Por defecto bloqueado.",
        )
        parser.add_argument(
            "--host",
            type=str,
            default="",
            help="Host MySQL opcional (p. ej. LAN planta). Si se indica, no usa el pool Synap.",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=0,
            help="Puerto MySQL opcional (junto con --host).",
        )

    def handle(self, *args, **options):
        base = (options.get("base_empresa") or "").strip()
        if not base:
            raise CommandError("Indique --base-empresa.")

        aplicar = bool(options.get("apply"))
        if aplicar:
            confirmar = str(options.get("confirmar") or "").strip()
            if confirmar != CONFIRMAR_RESET:
                raise CommandError(MSG_CONFIRMAR_REQUERIDO)
            if base.lower() == "administranet" and not options.get("forzar_produccion"):
                raise CommandError(MSG_PRODUCCION_BLOQUEADA)

        fechas_iso = parse_fechas_args(options.get("fechas") or [])
        host = (options.get("host") or "").strip()
        port = int(options.get("port") or 0)
        fechas_es = ", ".join(_fmt_fecha_es(f) for f in fechas_iso)
        modo = "APPLY" if aplicar else "DRY-RUN"

        self.stdout.write(
            self.style.WARNING(
                f"[{modo}] Reversión de CC — base={base}, fechas={fechas_es}"
                + (f", host={host}:{port or 3306}" if host else "")
            )
        )
        if aplicar:
            self.stdout.write(
                self.style.ERROR(
                    "Se anularán los movimientos de transición CC, se ajustará "
                    "stock_deposito y se ELIMINARÁN las filas mpr_transicion_lote "
                    "de la(s) fecha(s).\n"
                )
            )
        else:
            self.stdout.write(
                "Modo: solo lectura. Apply previsto: anular movimientos CC + "
                "ajustar stock_deposito + borrar mpr_transicion_lote de la(s) fecha(s).\n"
            )

        if host:
            self._correr_host_directo(base, fechas_iso, host, port or 3306, aplicar=aplicar)
        else:
            for fecha_iso in fechas_iso:
                # Una transacción por fecha: mysql_cursor hace commit al salir
                # del with y rollback si hay excepción.
                with mysql_cursor(base, dict_cursor=True) as cursor:
                    fecha_es = _fmt_fecha_es(fecha_iso)
                    self._inventariar(cursor, base, fecha_iso, fecha_es)
                    if aplicar:
                        self._aplicar_fecha(cursor, base, fecha_iso, fecha_es)
                if len(fechas_iso) > 1:
                    self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Apply' if aplicar else 'Inventario dry-run'} completado — "
                f"{base}, {fechas_es}."
            )
        )

    def _correr_host_directo(
        self,
        base: str,
        fechas_iso: List[str],
        host: str,
        port: int,
        *,
        aplicar: bool,
    ) -> None:
        """Dry-run/apply contra host explícito. Credenciales DB_USER/DB_PASSWORD."""
        import os

        import MySQLdb

        user = os.environ.get("DB_USER") or ""
        passwd = os.environ.get("DB_PASSWORD") or ""
        if not user:
            raise CommandError("Falta DB_USER en el entorno para --host.")
        conn = MySQLdb.connect(
            host=host,
            port=int(port),
            user=user,
            passwd=passwd,
            db=base,
            charset="utf8mb4",
            connect_timeout=12,
        )
        try:
            conn.autocommit(False)
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)
            for fecha_iso in fechas_iso:
                fecha_es = _fmt_fecha_es(fecha_iso)
                try:
                    self._inventariar(cursor, base, fecha_iso, fecha_es)
                    if aplicar:
                        self._aplicar_fecha(cursor, base, fecha_iso, fecha_es, conn=conn)
                    else:
                        conn.rollback()
                except Exception:
                    conn.rollback()
                    raise
                if len(fechas_iso) > 1:
                    self.stdout.write("")
        finally:
            conn.close()

    # ------------------------------------------------------------------ lectura

    def _tablas(self, cursor, base: str) -> Dict[str, Optional[str]]:
        tablas = {
            "cc": _nombre_tabla(cursor, "mpr_transicion_lote"),
            "mov": _nombre_tabla(cursor, "movimiento_stock"),
            "stock": _nombre_tabla(cursor, "stock"),
            "sd": _nombre_tabla(cursor, "stock_deposito"),
            "art": _nombre_tabla(cursor, "articulo"),
        }
        if not tablas["cc"]:
            raise CommandError(f"No existe mpr_transicion_lote en {base}.")
        return tablas

    def _cargar_cc(self, cursor, tbl_cc: str, fecha_iso: str) -> List[Any]:
        cursor.execute(
            f"""
            SELECT id_mpr_transicion_lote, id_articulo, tipo_origen, tipo_destino,
                   cantidad, id_mpr_turno, id_operario, codigo_movimiento
            FROM `{tbl_cc}`
            WHERE fecha_produccion = %s
            ORDER BY id_mpr_transicion_lote
            """,
            [fecha_iso],
        )
        return list(cursor.fetchall() or [])

    @staticmethod
    def _codigos_de(cc_rows: List[Any]) -> Tuple[List[int], int]:
        """(códigos distintos en orden de aparición, cantidad de filas sin código)."""
        codigos: List[int] = []
        sin_codigo = 0
        for row in cc_rows:
            cm = to_int_or_none(_row_val(row, "codigo_movimiento"))
            if cm is None or cm <= 0:
                sin_codigo += 1
            elif cm not in codigos:
                codigos.append(cm)
        return codigos, sin_codigo

    def _cargar_movimientos(self, cursor, tbl_mov: Optional[str], codigos: List[int]) -> Dict[int, Any]:
        if not tbl_mov or not codigos:
            return {}
        cursor.execute(
            f"""
            SELECT codigo_movimiento, tipo_mov, motivo_movimiento, detalle, anulado
            FROM `{tbl_mov}`
            WHERE codigo_movimiento IN ({_ph(len(codigos))})
            """,
            codigos,
        )
        out: Dict[int, Any] = {}
        for row in cursor.fetchall() or []:
            cm = to_int_or_none(_row_val(row, "codigo_movimiento"))
            if cm is not None:
                out[cm] = row
        return out

    def _stock_tiene_anulado(self, cursor, tbl_stock: Optional[str]) -> bool:
        if not tbl_stock:
            return False
        cursor.execute(f"SHOW COLUMNS FROM `{tbl_stock}` LIKE 'anulado'")
        return bool(cursor.fetchone())

    def _cargar_stock(
        self,
        cursor,
        tbl_stock: Optional[str],
        codigos: List[int],
        tiene_anulado: bool,
    ) -> List[Any]:
        if not tbl_stock or not codigos:
            return []
        col_anulado = ", anulado" if tiene_anulado else ""
        cursor.execute(
            f"""
            SELECT CodigoMovimiento, IDArt, CodDeposito, Entrada, Salida{col_anulado}
            FROM `{tbl_stock}`
            WHERE CodigoMovimiento IN ({_ph(len(codigos))})
            ORDER BY CodigoMovimiento, Orden
            """,
            codigos,
        )
        return list(cursor.fetchall() or [])

    @staticmethod
    def _clasificar_movimientos(
        codigos: List[int], movs: Dict[int, Any]
    ) -> Tuple[List[int], List[int], List[int], List[int]]:
        """(a_revertir, ya_anulados, inesperados, sin_movimiento)."""
        a_revertir: List[int] = []
        ya_anulados: List[int] = []
        inesperados: List[int] = []
        sin_mov: List[int] = []
        for cm in codigos:
            row = movs.get(cm)
            if row is None:
                sin_mov.append(cm)
            elif not movimiento_es_transicion_mpr(row):
                inesperados.append(cm)
            elif _es_anulado(_row_val(row, "anulado")):
                ya_anulados.append(cm)
            else:
                a_revertir.append(cm)
        return a_revertir, ya_anulados, inesperados, sin_mov

    @staticmethod
    def _deltas_por_articulo_deposito(
        stock_rows: List[Any],
    ) -> Dict[Tuple[int, int], Decimal]:
        """saldo += Salida - Entrada, agregado por (articulo, deposito)."""
        deltas: Dict[Tuple[int, int], Decimal] = {}
        for sr in stock_rows:
            id_art = to_int_or_none(_row_val(sr, "IDArt"))
            id_dep = to_int_or_none(_row_val(sr, "CodDeposito"))
            if id_art is None or id_dep is None:
                continue
            entrada = to_decimal_or_none(_row_val(sr, "Entrada")) or Decimal("0")
            salida = to_decimal_or_none(_row_val(sr, "Salida")) or Decimal("0")
            delta = salida - entrada
            if delta == 0:
                continue
            key = (id_art, id_dep)
            deltas[key] = deltas.get(key, Decimal("0")) + delta
        return deltas

    # ---------------------------------------------------------------- dry-run

    def _inventariar(self, cursor, base: str, fecha_iso: str, fecha_es: str) -> None:
        t = self._tablas(cursor, base)
        tbl_cc, tbl_mov, tbl_stock, tbl_sd = t["cc"], t["mov"], t["stock"], t["sd"]

        self.stdout.write(self.style.MIGRATE_HEADING(f"=== Fecha {fecha_es} ({fecha_iso}) ==="))

        cc_rows = self._cargar_cc(cursor, tbl_cc, fecha_iso)
        self.stdout.write(self.style.MIGRATE_HEADING(f"1. mpr_transicion_lote ({fecha_es}) — a ELIMINAR"))
        if not cc_rows:
            self.stdout.write("  (sin CC en esa fecha: la grilla del parte no está bloqueada por CC)")
            return
        self.stdout.write(
            f"  {'ID':>8}  {'Artículo':>8}  {'Cantidad':>10}  {'Origen→Destino':28}  "
            f"{'Turno':>5}  {'Operario':>8}  {'Cód.mov':>8}"
        )
        total = Decimal("0")
        for row in cc_rows[:MAX_FILAS_CC_LISTADO]:
            cant = to_decimal_or_none(_row_val(row, "cantidad")) or Decimal("0")
            ruta = (
                f"{str_or_blank(_row_val(row, 'tipo_origen'))}"
                f"→{str_or_blank(_row_val(row, 'tipo_destino'))}"
            )
            self.stdout.write(
                f"  {_row_val(row, 'id_mpr_transicion_lote') or '-':>8}  "
                f"{_row_val(row, 'id_articulo') or '-':>8}  {_fmt_decimal(cant):>10}  "
                f"{ruta[:28]:28}  {_row_val(row, 'id_mpr_turno') or '-':>5}  "
                f"{_row_val(row, 'id_operario') or '-':>8}  "
                f"{_row_val(row, 'codigo_movimiento') or '-':>8}"
            )
        for row in cc_rows:
            total += to_decimal_or_none(_row_val(row, "cantidad")) or Decimal("0")
        if len(cc_rows) > MAX_FILAS_CC_LISTADO:
            self.stdout.write(f"    … y {len(cc_rows) - MAX_FILAS_CC_LISTADO} filas más")
        self.stdout.write(f"  Total filas CC: {len(cc_rows)} | Σ cantidad: {_fmt_decimal(total)}")

        codigos, sin_codigo = self._codigos_de(cc_rows)
        if sin_codigo:
            self.stdout.write(
                self.style.WARNING(
                    f"  Aviso: {sin_codigo} fila(s) CC sin codigo_movimiento "
                    "(se borrarán; nada que revertir en stock)."
                )
            )

        # 2. movimiento_stock
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("2. movimiento_stock de las transiciones"))
        movs = self._cargar_movimientos(cursor, tbl_mov, codigos)
        if not tbl_mov:
            self.stdout.write(self.style.WARNING("  Tabla movimiento_stock no encontrada."))
        a_revertir, ya_anulados, inesperados, sin_mov = self._clasificar_movimientos(codigos, movs)
        if not codigos:
            self.stdout.write("  (sin códigos de movimiento)")
        else:
            self.stdout.write(f"  {'Código':>8}  {'Tipo':6}  {'Anulado':7}  Detalle")
            for cm in codigos:
                row = movs.get(cm)
                if row is None:
                    self.stdout.write(f"  {cm:>8}  {'-':6}  {'-':7}  (sin movimiento_stock)")
                    continue
                self.stdout.write(
                    f"  {cm:>8}  {str_or_blank(_row_val(row, 'tipo_mov'))[:6]:6}  "
                    f"{str_or_blank(_row_val(row, 'anulado')) or 'No':7}  "
                    f"{str_or_blank(_row_val(row, 'detalle'))[:80]}"
                )
            self.stdout.write(
                f"  A revertir: {len(a_revertir)} | ya anulados (se omiten): "
                f"{len(ya_anulados)} | inesperados: {len(inesperados)} | "
                f"sin movimiento: {len(sin_mov)}"
            )
        if inesperados:
            self.stdout.write(
                self.style.ERROR(
                    "  ABORTARÍA el apply: códigos que no son transición MPR (OPP / "
                    f"'{DETALLE_TRANSICION_PREFIJO} …'): {inesperados}"
                )
            )
        if sin_mov:
            self.stdout.write(
                self.style.ERROR(f"  ABORTARÍA el apply: códigos sin movimiento_stock: {sin_mov}")
            )

        # 3. stock
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("3. stock (Salida/Entrada) de esos movimientos"))
        tiene_anulado = self._stock_tiene_anulado(cursor, tbl_stock)
        stock_rows = self._cargar_stock(cursor, tbl_stock, a_revertir, tiene_anulado)
        stock_todos = self._cargar_stock(cursor, tbl_stock, ya_anulados, tiene_anulado) if ya_anulados else []
        if tiene_anulado:
            activos = [r for r in stock_rows if not _es_anulado(_row_val(r, "anulado"))]
        else:
            activos = stock_rows
        if not stock_rows and not stock_todos:
            self.stdout.write("  (sin renglones stock)")
        else:
            self.stdout.write(
                f"  {'Cód.mov':>8}  {'Artículo':>8}  {'Depósito':>8}  {'Entrada':>10}  "
                f"{'Salida':>10}  Anulado"
            )
            for r in stock_rows + stock_todos:
                self.stdout.write(
                    f"  {_row_val(r, 'CodigoMovimiento') or '-':>8}  "
                    f"{_row_val(r, 'IDArt') or '-':>8}  {_row_val(r, 'CodDeposito') or '-':>8}  "
                    f"{_fmt_decimal(_row_val(r, 'Entrada')):>10}  "
                    f"{_fmt_decimal(_row_val(r, 'Salida')):>10}  "
                    f"{(str_or_blank(_row_val(r, 'anulado')) or 'No') if tiene_anulado else 'n/d'}"
                )

        # 4. saldo proyectado
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("4. stock_deposito — saldo proyectado"))
        deltas = self._deltas_por_articulo_deposito(activos)
        if not deltas:
            self.stdout.write("  (sin cambios de saldo)")
        elif not tbl_sd:
            self.stdout.write(self.style.WARNING("  Tabla stock_deposito no encontrada."))
        else:
            self.stdout.write(
                f"  {'Artículo':>8}  {'Depósito':>8}  {'Saldo act.':>12}  {'Δ':>10}  {'Proyectado':>12}"
            )
            negativos: List[str] = []
            for (id_art, id_dep), delta in sorted(deltas.items()):
                cursor.execute(
                    f"SELECT saldo FROM `{tbl_sd}` WHERE id_articulo = %s AND id_deposito = %s",
                    [id_art, id_dep],
                )
                sd_row = cursor.fetchone()
                saldo = to_decimal_or_none(_row_val(sd_row, "saldo")) or Decimal("0")
                nuevo = saldo + delta
                marca = ""
                if sd_row is None and delta < 0:
                    marca = "  (sin fila stock_deposito: no se ajustaría)"
                elif nuevo < 0:
                    marca = "  <-- NEGATIVO"
                    negativos.append(f"art={id_art} dep={id_dep} saldo={_fmt_decimal(nuevo)}")
                self.stdout.write(
                    f"  {id_art:>8}  {id_dep:>8}  {_fmt_decimal(saldo):>12}  "
                    f"{_fmt_decimal(delta):>10}  {_fmt_decimal(nuevo):>12}{marca}"
                )
            if negativos:
                self.stdout.write(
                    self.style.WARNING(
                        "  ADVERTENCIA: saldos negativos proyectados (movimientos posteriores "
                        "pueden explicarlos): " + "; ".join(negativos[:8])
                    )
                )

        # CC con códigos compartidos con otras fechas
        otras = self._cc_otras_fechas(cursor, tbl_cc, codigos, fecha_iso)
        if otras:
            self.stdout.write(
                self.style.ERROR(
                    f"  ABORTARÍA el apply: {otras} fila(s) CC de OTRA fecha comparten "
                    "codigo_movimiento con esta."
                )
            )

    def _cc_otras_fechas(self, cursor, tbl_cc: str, codigos: List[int], fecha_iso: str) -> int:
        if not codigos:
            return 0
        cursor.execute(
            f"""
            SELECT COUNT(*) AS n FROM `{tbl_cc}`
            WHERE codigo_movimiento IN ({_ph(len(codigos))})
              AND (fecha_produccion IS NULL OR fecha_produccion <> %s)
            """,
            list(codigos) + [fecha_iso],
        )
        return to_int_or_none(_row_val(cursor.fetchone(), "n")) or 0

    # ------------------------------------------------------------------ apply

    def _aplicar_fecha(
        self,
        cursor,
        base: str,
        fecha_iso: str,
        fecha_es: str,
        conn=None,
    ) -> None:
        """Revierte stock de las transiciones CC y borra mpr_transicion_lote de la fecha.

        Todas las validaciones corren antes de cualquier escritura; si algo aborta,
        el caller hace rollback y la fecha queda intacta.
        """
        t = self._tablas(cursor, base)
        tbl_cc, tbl_mov, tbl_stock, tbl_sd = t["cc"], t["mov"], t["stock"], t["sd"]

        cc_rows = self._cargar_cc(cursor, tbl_cc, fecha_iso)
        self.stdout.write(
            self.style.MIGRATE_HEADING(f"APPLY {fecha_es}: {len(cc_rows)} filas CC")
        )
        if not cc_rows:
            self.stdout.write("  (nada que revertir)")
            if conn is not None:
                conn.commit()
            return

        codigos, sin_codigo = self._codigos_de(cc_rows)
        if codigos and not (tbl_mov and tbl_stock and tbl_sd):
            faltan = [
                n
                for n, v in (("movimiento_stock", tbl_mov), ("stock", tbl_stock), ("stock_deposito", tbl_sd))
                if not v
            ]
            raise CommandError(f"Abortado {fecha_es}: faltan tablas {', '.join(faltan)}.")

        movs = self._cargar_movimientos(cursor, tbl_mov, codigos)
        a_revertir, ya_anulados, inesperados, sin_mov = self._clasificar_movimientos(codigos, movs)
        if inesperados:
            raise CommandError(
                f"Abortado {fecha_es}: codigo_movimiento {inesperados} no es una transición "
                f"MPR (tipo_mov '{TIPO_MOV_OPP}', detalle '{DETALLE_TRANSICION_PREFIJO} …'). "
                "No se modificó nada."
            )
        if sin_mov:
            raise CommandError(
                f"Abortado {fecha_es}: codigo_movimiento {sin_mov} sin fila en movimiento_stock. "
                "No se modificó nada."
            )
        otras = self._cc_otras_fechas(cursor, tbl_cc, codigos, fecha_iso)
        if otras:
            raise CommandError(
                f"Abortado {fecha_es}: {otras} fila(s) CC de otra fecha comparten "
                "codigo_movimiento con esta. No se modificó nada."
            )

        n_sd = 0
        n_stock = 0
        n_mov = 0
        saldos_negativos: List[str] = []
        sin_fila_sd: List[str] = []

        if a_revertir:
            tiene_anulado = self._stock_tiene_anulado(cursor, tbl_stock)
            stock_rows = self._cargar_stock(cursor, tbl_stock, a_revertir, tiene_anulado)
            if tiene_anulado:
                stock_rows = [r for r in stock_rows if not _es_anulado(_row_val(r, "anulado"))]
            deltas = self._deltas_por_articulo_deposito(stock_rows)

            for (id_art, id_dep), delta in sorted(deltas.items()):
                cursor.execute(
                    f"""
                    SELECT id_stock_deposito, saldo
                    FROM `{tbl_sd}`
                    WHERE id_articulo = %s AND id_deposito = %s
                    FOR UPDATE
                    """,
                    [id_art, id_dep],
                )
                sd_row = cursor.fetchone()
                if sd_row:
                    sid = to_int_or_none(_row_val(sd_row, "id_stock_deposito"))
                    saldo_actual = to_decimal_or_none(_row_val(sd_row, "saldo")) or Decimal("0")
                    nuevo = saldo_actual + delta
                    cursor.execute(
                        f"UPDATE `{tbl_sd}` SET saldo = %s WHERE id_stock_deposito = %s",
                        [nuevo, sid],
                    )
                    n_sd += 1
                    if nuevo < 0:
                        saldos_negativos.append(
                            f"art={id_art} dep={id_dep} saldo={_fmt_decimal(nuevo)}"
                        )
                elif delta > 0:
                    cursor.execute(
                        f"INSERT INTO `{tbl_sd}` (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                        [id_art, id_dep, delta],
                    )
                    n_sd += 1
                else:
                    sin_fila_sd.append(f"art={id_art} dep={id_dep}")

            ph = _ph(len(a_revertir))
            if tiene_anulado:
                cursor.execute(
                    f"""
                    UPDATE `{tbl_stock}`
                    SET anulado = 'Si'
                    WHERE CodigoMovimiento IN ({ph})
                      AND COALESCE(anulado, 'No') <> 'Si'
                    """,
                    a_revertir,
                )
            else:
                # Sin columna anulado (mismo criterio que revertir_partes_fecha): se borran.
                cursor.execute(
                    f"DELETE FROM `{tbl_stock}` WHERE CodigoMovimiento IN ({ph})",
                    a_revertir,
                )
            n_stock = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0

            cursor.execute(
                f"""
                UPDATE `{tbl_mov}`
                SET anulado = 'Si'
                WHERE codigo_movimiento IN ({ph})
                  AND COALESCE(anulado, 'No') <> 'Si'
                """,
                a_revertir,
            )
            n_mov = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0

        cursor.execute(
            f"DELETE FROM `{tbl_cc}` WHERE fecha_produccion = %s",
            [fecha_iso],
        )
        n_cc = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0

        # Verificación antes de commit: si falla, el caller hace rollback.
        cursor.execute(
            f"SELECT COUNT(*) AS n FROM `{tbl_cc}` WHERE fecha_produccion = %s",
            [fecha_iso],
        )
        quedan = to_int_or_none(_row_val(cursor.fetchone(), "n")) or 0
        if quedan:
            raise CommandError(
                f"Post-apply {fecha_es}: aún quedan {quedan} filas CC (se hace rollback)."
            )

        if conn is not None:
            conn.commit()
        # mysql_cursor del pool commitea al salir del with (una transacción por fecha).

        self.stdout.write(
            f"  Movimientos anulados: {n_mov} mov / {n_stock} stock | "
            f"ya anulados (omitidos): {len(ya_anulados)} | sd ajustes: {n_sd} | "
            f"filas CC sin código: {sin_codigo} | borradas CC: {n_cc}"
        )
        if sin_fila_sd:
            self.stdout.write(
                self.style.WARNING(
                    "  Aviso: sin fila stock_deposito (no se ajustó): " + "; ".join(sin_fila_sd[:8])
                )
            )
        if saldos_negativos:
            self.stdout.write(
                self.style.WARNING(
                    "  Aviso: saldos stock_deposito negativos tras revertir "
                    "(movimientos posteriores pueden explicarlos): "
                    + "; ".join(saldos_negativos[:8])
                    + (" …" if len(saldos_negativos) > 8 else "")
                )
            )
        self.stdout.write(self.style.SUCCESS(f"  OK {fecha_es}: 0 filas CC residuales."))
