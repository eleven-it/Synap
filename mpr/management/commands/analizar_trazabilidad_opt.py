# MPR - Analiza trazabilidad completa de una OPT en la DB (todas las tablas).
# Uso: python manage.py analizar_trazabilidad_opt 92 --base-empresa=administranet92

import logging
from django.core.management.base import BaseCommand

from core.mysql_pool import mysql_cursor

logger = logging.getLogger(__name__)


def _nombre_tabla(cursor, nombre_lower: str):
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall():
        if isinstance(row, dict):
            nombre = (list(row.values())[0] or "").strip()
        else:
            nombre = (row[0] if row else "").strip()
        if nombre and nombre.lower() == nombre_lower:
            return nombre
    return None


class Command(BaseCommand):
    help = "Analiza trazabilidad OPT en lista_produccion_agrupada, detalle, historico, movimiento_stock, stock, stock_deposito, comp_ped."

    def add_arguments(self, parser):
        parser.add_argument("id_lista", type=int, help="id_lista_produccion (ej. 92).")
        parser.add_argument("--base-empresa", type=str, required=True, help="Base MySQL (ej. administranet92).")

    def handle(self, *args, **options):
        id_lista = options["id_lista"]
        base_empresa = (options.get("base_empresa") or "").strip()
        if not base_empresa:
            self.stdout.write(self.style.ERROR("Indique --base-empresa."))
            return

        hallazgos = []
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            tbl_historico = _nombre_tabla(cursor, "lista_produccion_historico")
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_cp = _nombre_tabla(cursor, "comp_ped")

            # --- lista_produccion_agrupada ---
            if not tbl_agrupada:
                hallazgos.append(("lista_produccion_agrupada", "ERROR", "Tabla no existe."))
            else:
                try:
                    cursor.execute(
                        f"""SELECT id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod,
                            en_proceso_produccion, codigo_movimiento_opt
                            FROM {tbl_agrupada} WHERE id_lista_produccion = %s""",
                        [id_lista],
                    )
                    rows_agrupada = cursor.fetchall()
                    total_pend = sum((r.get("cantidad_pendiente_prod") or 0) for r in rows_agrupada)
                    if not rows_agrupada:
                        hallazgos.append(("lista_produccion_agrupada", "FALTA", f"Ninguna fila con id_lista_produccion={id_lista}."))
                    else:
                        hallazgos.append(("lista_produccion_agrupada", "OK", f"{len(rows_agrupada)} fila(s). Total cantidad_pendiente_prod={total_pend}. en_proceso: {[r.get('en_proceso_produccion') for r in rows_agrupada]}."))
                except Exception as e:
                    hallazgos.append(("lista_produccion_agrupada", "ERROR", str(e)))

            # --- lista_produccion_detalle ---
            if not tbl_detalle:
                hallazgos.append(("lista_produccion_detalle", "ERROR", "Tabla no existe."))
            else:
                try:
                    cursor.execute(
                        f"SELECT id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod, codigo_movimiento_pedido FROM {tbl_detalle} WHERE id_lista_produccion = %s",
                        [id_lista],
                    )
                    rows_detalle = cursor.fetchall()
                    hallazgos.append(("lista_produccion_detalle", "OK" if rows_detalle else "INFO", f"{len(rows_detalle)} fila(s)." + (" (puede ser 0 si OPT creada sin detalle por pedido)" if not rows_detalle else "")))
                except Exception as e:
                    hallazgos.append(("lista_produccion_detalle", "ERROR", str(e)))

            # --- lista_produccion_historico ---
            if not tbl_historico:
                hallazgos.append(("lista_produccion_historico", "ERROR", "Tabla no existe."))
            else:
                try:
                    cursor.execute(
                        f"""SELECT tipo_evento, id_articulo, cantidad_movimiento, cantidad_armada, codigo_movimiento_mstock, id_lista_produccion, fecha, hora_evento
                            FROM {tbl_historico} WHERE id_lista_produccion = %s ORDER BY fecha, hora_evento""",
                        [id_lista],
                    )
                    rows_hist = cursor.fetchall()
                    tipos = {}
                    for r in rows_hist:
                        t = r.get("tipo_evento") or "?"
                        tipos[t] = tipos.get(t, 0) + 1
                    if not rows_hist:
                        hallazgos.append(("lista_produccion_historico", "FALTA", f"Ningún evento con id_lista_produccion={id_lista}. Se esperan OPT, OPP, Armado."))
                    else:
                        esperados = {"OPT", "OPP", "Armado"}
                        faltan = esperados - set(tipos.keys())
                        msg = f"{len(rows_hist)} evento(s). Tipos: {dict(tipos)}."
                        if faltan:
                            msg += f" Faltan tipos: {faltan}."
                        hallazgos.append(("lista_produccion_historico", "OK" if not faltan else "GAP", msg))
                except Exception as e:
                    hallazgos.append(("lista_produccion_historico", "ERROR", str(e)))

            # --- movimiento_stock (OPT, OPP, OPA con detalle OPT 92) ---
            if not tbl_mov:
                hallazgos.append(("movimiento_stock", "ERROR", "Tabla no existe."))
            else:
                try:
                    cursor.execute(
                        f"""SELECT codigo_movimiento, nro_comprobante, tipo_mov, motivo_movimiento,
                            LEFT(detalle, 80) AS detalle_corto, fecha, anulado
                            FROM {tbl_mov}
                            WHERE (INSTR(COALESCE(detalle,''), %s) > 0 OR INSTR(COALESCE(detalle,''), %s) > 0)
                              AND COALESCE(anulado,'No') <> 'Si'
                            ORDER BY codigo_movimiento""",
                        [f"OPT {id_lista} ", f"OPT {id_lista})"],
                    )
                    rows_mov = cursor.fetchall()
                    tipos_mov = {}
                    for r in rows_mov:
                        t = (r.get("tipo_mov") or "").strip()
                        tipos_mov[t] = tipos_mov.get(t, 0) + 1
                    esperados_mov = {"OPT", "OPP", "OPA", "Armado"}
                    tiene_opt = any(t in tipos_mov for t in ("OPT",))
                    tiene_opp = "OPP" in tipos_mov
                    tiene_opa = "OPA" in tipos_mov or "Armado" in tipos_mov
                    msg = f"{len(rows_mov)} movimiento(s). Tipos: {dict(tipos_mov)}."
                    gaps = []
                    if not tiene_opt:
                        gaps.append("OPT (liberación)")
                    if not tiene_opp:
                        gaps.append("OPP")
                    if not tiene_opa:
                        gaps.append("OPA/Armado")
                    if gaps:
                        msg += f" Faltan: {gaps}."
                    hallazgos.append(("movimiento_stock", "OK" if not gaps else "GAP", msg))
                except Exception as e:
                    hallazgos.append(("movimiento_stock", "ERROR", str(e)))

            # --- stock (renglones por codigo_movimiento de la OPT) ---
            if not tbl_stock or not tbl_mov:
                if not tbl_stock:
                    hallazgos.append(("stock", "ERROR", "Tabla no existe."))
            else:
                try:
                    cursor.execute(
                        f"""SELECT codigo_movimiento FROM {tbl_mov}
                            WHERE (INSTR(COALESCE(detalle,''), %s) > 0 OR INSTR(COALESCE(detalle,''), %s) > 0)
                              AND COALESCE(anulado,'No') <> 'Si'""",
                        [f"OPT {id_lista} ", f"OPT {id_lista})"],
                    )
                    codigos = [r["codigo_movimiento"] for r in cursor.fetchall() if r.get("codigo_movimiento")]
                    if not codigos:
                        hallazgos.append(("stock", "INFO", "No hay codigo_movimiento asociados a esta OPT (no hay movimientos)."))
                    else:
                        ph = ",".join(["%s"] * len(codigos))
                        cursor.execute(
                            f"SELECT CodigoMovimiento, IDArt, Entrada, Salida FROM {tbl_stock} WHERE CodigoMovimiento IN ({ph}) ORDER BY CodigoMovimiento, IDArt",
                            codigos,
                        )
                        rows_stock = cursor.fetchall()
                        entradas = sum((r.get("Entrada") or 0) for r in rows_stock)
                        salidas = sum((r.get("Salida") or 0) for r in rows_stock)
                        hallazgos.append(("stock", "OK", f"{len(rows_stock)} renglón(es) para {len(codigos)} movimiento(s). Total Entrada={entradas}, Salida={salidas}."))
                except Exception as e:
                    hallazgos.append(("stock", "ERROR", str(e)))

            # --- stock_deposito: solo resumen (trazabilidad indirecta) ---
            if tbl_sd:
                hallazgos.append(("stock_deposito", "INFO", "Saldos por depósito; coherencia se valida con suma de movimientos en stock."))
            else:
                hallazgos.append(("stock_deposito", "ERROR", "Tabla no existe."))

            # --- comp_ped (pedidos vinculados a la OPT, estado_pedido_opt) ---
            if not tbl_cp:
                hallazgos.append(("comp_ped", "INFO", "Tabla no existe o no usada."))
            elif not tbl_detalle:
                hallazgos.append(("comp_ped", "INFO", "Sin lista_produccion_detalle no se pueden vincular pedidos."))
            else:
                try:
                    cursor.execute(
                        f"SELECT DISTINCT codigo_movimiento_pedido FROM {tbl_detalle} WHERE id_lista_produccion = %s AND codigo_movimiento_pedido IS NOT NULL",
                        [id_lista],
                    )
                    codigos_ped = [r["codigo_movimiento_pedido"] for r in cursor.fetchall() if r.get("codigo_movimiento_pedido")]
                    if not codigos_ped:
                        hallazgos.append(("comp_ped", "INFO", "Ningún pedido vinculado en detalle para esta OPT."))
                    else:
                        col_estado = "estado_pedido_opt"
                        try:
                            cursor.execute("SHOW COLUMNS FROM {} LIKE %s".format(tbl_cp), [col_estado])
                            if not cursor.fetchone():
                                col_estado = None
                        except Exception:
                            col_estado = None
                        if not col_estado:
                            hallazgos.append(("comp_ped", "INFO", "Tabla comp_ped sin columna estado_pedido_opt o no accesible."))
                        else:
                            ph = ",".join(["%s"] * len(codigos_ped))
                            cursor.execute(
                                f"SELECT CodigoMovimiento, {col_estado} FROM {tbl_cp} WHERE CodigoMovimiento IN ({ph})",
                                codigos_ped,
                            )
                            rows_cp = cursor.fetchall()
                            estados = [r.get(col_estado) for r in rows_cp]
                            hallazgos.append(("comp_ped", "OK", f"{len(rows_cp)} pedido(s) vinculado(s). Estados: {estados}."))
                except Exception as e:
                    hallazgos.append(("comp_ped", "ERROR", str(e)))

        # --- Salida ---
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO(f"=== Trazabilidad OPT {id_lista} en {base_empresa} ==="))
        self.stdout.write("")
        for tabla, estado, mensaje in hallazgos:
            if estado == "OK":
                self.stdout.write(self.style.SUCCESS(f"  [{tabla}] OK: {mensaje}"))
            elif estado == "GAP":
                self.stdout.write(self.style.WARNING(f"  [{tabla}] GAP: {mensaje}"))
            elif estado == "FALTA":
                self.stdout.write(self.style.WARNING(f"  [{tabla}] FALTA: {mensaje}"))
            elif estado == "ERROR":
                self.stdout.write(self.style.ERROR(f"  [{tabla}] ERROR: {mensaje}"))
            else:
                self.stdout.write(f"  [{tabla}] {mensaje}")
        self.stdout.write("")
