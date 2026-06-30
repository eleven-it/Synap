# MPR — Eliminar OPT(s) de prueba o inconsistentes (agrupada, detalle, histórico, movimientos, stock).
# Uso dry-run: docker exec Synap_app python manage.py eliminar_opt 2 5 7 --base-empresa=administranet96
# Ejecutar:       docker exec Synap_app python manage.py eliminar_opt 2 5 7 --base-empresa=administranet96 --confirmar

from decimal import Decimal
from typing import Any, Dict, List, Set, Tuple

import MySQLdb.cursors
from django.core.management.base import BaseCommand

from core.mysql_pool import get_connection
from core.utils.administranet_types import to_int_or_none
from mpr.services import (
    _mpr_es_codigo_movimiento_opt_mstock,
    _nombre_tabla,
    get_opt_detalle,
    listar_opa_por_opt,
    listar_opp_por_opt,
)


def _row_val(row: Any, *keys: str):
    if not row:
        return None
    if isinstance(row, dict):
        lower = {str(k).lower(): v for k, v in row.items()}
    elif isinstance(row, (list, tuple)):
        return row[0] if len(row) == 1 and not keys else None
    else:
        return None
    for key in keys:
        if key.lower() in lower:
            return lower[key.lower()]
    return None


def _codigos_movimiento_opt(base: str, id_lista: int) -> Set[int]:
    codigos: Set[int] = set()
    for opp in listar_opp_por_opt(base, id_lista):
        c = to_int_or_none(opp.get("codigo_movimiento"))
        if c:
            codigos.add(c)
    for opa in listar_opa_por_opt(base, id_lista):
        c = to_int_or_none(opa.get("codigo_movimiento"))
        if c:
            codigos.add(c)
    patrones = [f"OPT {id_lista} desde", f"OPT {id_lista} ", f"OPT {id_lista})"]
    try:
        with get_connection(base) as conn:
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)
            try:
                tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
                if not tbl_mov:
                    return codigos
                for patron in patrones:
                    cursor.execute(
                        f"""
                        SELECT codigo_movimiento FROM {tbl_mov}
                        WHERE INSTR(COALESCE(detalle,''), %s) > 0
                          AND COALESCE(anulado,'No') <> 'Si'
                        """,
                        [patron],
                    )
                    for row in cursor.fetchall() or []:
                        c = to_int_or_none(_row_val(row, "codigo_movimiento"))
                        if c:
                            codigos.add(c)
            finally:
                cursor.close()
    except Exception:
        pass
    return codigos


def _ids_grupo_opt(base: str, id_lista: int) -> List[int]:
    lineas = get_opt_detalle(base, id_lista)
    ids = sorted(
        {
            int(l["id_lista_produccion"])
            for l in lineas
            if l.get("id_lista_produccion") is not None
        }
    )
    return ids or [id_lista]


def eliminar_opt_en_base(
    base: str,
    id_lista: int,
    *,
    confirmar: bool = False,
) -> Tuple[bool, str, Dict[str, int]]:
    """Elimina una OPT y trazabilidad asociada. Devuelve (ok, mensaje, contadores)."""
    ids_grupo = _ids_grupo_opt(base, id_lista)
    codigos_mov = _codigos_movimiento_opt(base, id_lista)

    with get_connection(base) as conn:
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        try:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            tbl_historico = _nombre_tabla(cursor, "lista_produccion_historico")
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")

            if not tbl_agrupada:
                return False, "No existe lista_produccion_agrupada.", {}

            ph_ids = ",".join(["%s"] * len(ids_grupo))
            cursor.execute(
                f"SELECT id_lista_produccion, codigo_movimiento_opt FROM {tbl_agrupada} "
                f"WHERE id_lista_produccion IN ({ph_ids})",
                ids_grupo,
            )
            filas_agr = cursor.fetchall() or []
            if not filas_agr:
                return False, f"OPT {id_lista}: sin filas en agrupada.", {}

            for row in filas_agr:
                cod_opt = to_int_or_none(_row_val(row, "codigo_movimiento_opt"))
                if _mpr_es_codigo_movimiento_opt_mstock(cod_opt):
                    codigos_mov.add(cod_opt)

            codigos = sorted(codigos_mov)
            contadores = {
                "agrupada": 0,
                "detalle": 0,
                "historico": 0,
                "movimiento_stock": 0,
                "stock": 0,
                "stock_deposito_ajustes": 0,
            }

            stock_rows: List[Dict[str, Any]] = []
            if tbl_stock and codigos:
                ph_cod = ",".join(["%s"] * len(codigos))
                cursor.execute(
                    f"""
                    SELECT CodigoMovimiento, IDArt, CodDeposito, Entrada, Salida, anulado
                    FROM {tbl_stock}
                    WHERE CodigoMovimiento IN ({ph_cod})
                      AND COALESCE(anulado,'No') <> 'Si'
                    """,
                    codigos,
                )
                for row in cursor.fetchall() or []:
                    stock_rows.append({
                        "codigo_movimiento": to_int_or_none(_row_val(row, "CodigoMovimiento", "codigomovimiento")),
                        "id_articulo": to_int_or_none(_row_val(row, "IDArt", "idart")),
                        "id_deposito": to_int_or_none(_row_val(row, "CodDeposito", "coddeposito")),
                        "entrada": Decimal(str(_row_val(row, "Entrada", "entrada") or 0)),
                        "salida": Decimal(str(_row_val(row, "Salida", "salida") or 0)),
                    })

            if not confirmar:
                return True, (
                    f"OPT {id_lista} (dry-run): ids_grupo={ids_grupo}, "
                    f"movimientos={codigos}, renglones_stock={len(stock_rows)}"
                ), contadores

            try:
                if tbl_sd and stock_rows:
                    for sr in stock_rows:
                        id_art = sr["id_articulo"]
                        id_dep = sr["id_deposito"]
                        if id_art is None or id_dep is None:
                            continue
                        delta = sr["salida"] - sr["entrada"]
                        if delta == 0:
                            continue
                        cursor.execute(
                            f"SELECT id_stock_deposito, saldo FROM {tbl_sd} "
                            f"WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                            [id_art, id_dep],
                        )
                        sd_row = cursor.fetchone()
                        if sd_row:
                            saldo_actual = Decimal(str(_row_val(sd_row, "saldo") or 0))
                            nuevo = saldo_actual + delta
                            cursor.execute(
                                f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s",
                                [nuevo, _row_val(sd_row, "id_stock_deposito")],
                            )
                            contadores["stock_deposito_ajustes"] += 1

                if tbl_stock and codigos:
                    ph_cod = ",".join(["%s"] * len(codigos))
                    cursor.execute(
                        f"DELETE FROM {tbl_stock} WHERE CodigoMovimiento IN ({ph_cod})",
                        codigos,
                    )
                    contadores["stock"] = cursor.rowcount or 0

                if tbl_mov and codigos:
                    ph_cod = ",".join(["%s"] * len(codigos))
                    cursor.execute(
                        f"DELETE FROM {tbl_mov} WHERE codigo_movimiento IN ({ph_cod})",
                        codigos,
                    )
                    contadores["movimiento_stock"] = cursor.rowcount or 0

                if tbl_historico:
                    ph_ids = ",".join(["%s"] * len(ids_grupo))
                    if codigos:
                        ph_cod = ",".join(["%s"] * len(codigos))
                        cursor.execute(
                            f"""
                            DELETE FROM {tbl_historico}
                            WHERE id_lista_produccion IN ({ph_ids})
                               OR codigo_movimiento_mstock IN ({ph_cod})
                               OR codigo_movimiento_opt IN ({ph_cod})
                            """,
                            ids_grupo + codigos + codigos,
                        )
                    else:
                        cursor.execute(
                            f"DELETE FROM {tbl_historico} WHERE id_lista_produccion IN ({ph_ids})",
                            ids_grupo,
                        )
                    contadores["historico"] = cursor.rowcount or 0

                if tbl_detalle:
                    cursor.execute(
                        f"DELETE FROM {tbl_detalle} WHERE id_lista_produccion IN ({ph_ids})",
                        ids_grupo,
                    )
                    contadores["detalle"] = cursor.rowcount or 0

                cursor.execute(
                    f"DELETE FROM {tbl_agrupada} WHERE id_lista_produccion IN ({ph_ids})",
                    ids_grupo,
                )
                contadores["agrupada"] = cursor.rowcount or 0

                conn.commit()
            except Exception as exc:
                conn.rollback()
                return False, f"OPT {id_lista}: error al eliminar — {exc}", contadores
        finally:
            cursor.close()

    return True, f"OPT {id_lista} eliminada.", contadores


class Command(BaseCommand):
    help = (
        "Elimina OPT(s) y su trazabilidad (movimientos OPT/OPP/OPA, stock, agrupada, detalle, histórico). "
        "Por defecto dry-run; usar --confirmar para ejecutar."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "id_listas",
            nargs="+",
            type=int,
            help="id_lista_produccion a eliminar.",
        )
        parser.add_argument(
            "--base-empresa",
            type=str,
            required=True,
            help="Base MySQL AdministraNET (ej. administranet96).",
        )
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Ejecutar borrado (sin este flag solo muestra qué se eliminaría).",
        )

    def handle(self, *args, **options):
        base = (options.get("base_empresa") or "").strip()
        if not base:
            self.stdout.write(self.style.ERROR("Indique --base-empresa."))
            return

        confirmar = bool(options.get("confirmar"))
        if not confirmar:
            self.stdout.write(self.style.WARNING("Modo dry-run (agregue --confirmar para borrar)."))

        errores = 0
        for id_lista in options["id_listas"]:
            ok, msg, cont = eliminar_opt_en_base(base, int(id_lista), confirmar=confirmar)
            if ok:
                estilo = self.style.SUCCESS if confirmar else self.style.WARNING
                self.stdout.write(estilo(msg))
                if confirmar and cont:
                    self.stdout.write(f"  → {cont}")
            else:
                self.stdout.write(self.style.ERROR(msg))
                errores += 1

        if confirmar and not errores:
            self.stdout.write(self.style.SUCCESS("Eliminación completada."))
