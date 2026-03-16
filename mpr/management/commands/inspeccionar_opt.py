# MPR - Inspeccionar en la DB cómo quedó registrada una OPT (lista_produccion_agrupada, movimiento_stock, stock).
# Uso: python manage.py inspeccionar_opt <id_lista> --base-empresa=administranet92
# Ejemplo: python manage.py inspeccionar_opt 13 --base-empresa=administranet92

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
    help = "Inspecciona en la DB cómo quedó registrada una OPT (lista_produccion_agrupada, movimiento_stock, stock)."

    def add_arguments(self, parser):
        parser.add_argument(
            "id_lista",
            type=int,
            help="id_lista_produccion de la OPT (ej. 13 para OPT 13).",
        )
        parser.add_argument(
            "--base-empresa",
            type=str,
            required=True,
            help="Base de datos MySQL (ej. administranet92).",
        )

    def handle(self, *args, **options):
        id_lista = options["id_lista"]
        base_empresa = (options.get("base_empresa") or "").strip()
        if not base_empresa:
            self.stdout.write(self.style.ERROR("Indique --base-empresa (ej. administranet92)."))
            return

        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl_agrupada:
                self.stdout.write(self.style.WARNING(f"No existe la tabla lista_produccion_agrupada en {base_empresa}."))
                return

            # Resolver OPT desde agrupada: id_opt y codigo_movimiento_opt
            try:
                cursor.execute(
                    f"SELECT id_opt, codigo_movimiento_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s LIMIT 1",
                    [id_lista],
                )
                row = cursor.fetchone()
            except Exception as e:
                if "1054" in str(e) or "unknown column" in str(e).lower():
                    row = None
                else:
                    raise

            if not row:
                self.stdout.write(self.style.WARNING(f"No hay fila en {tbl_agrupada} para id_lista_produccion={id_lista}."))
                return

            id_opt = row.get("id_opt")
            codigo_mov = row.get("codigo_movimiento_opt")

            # Si la fila no es la principal (id_lista != id_opt), leer codigo_movimiento_opt de la fila principal
            if id_opt is not None and id_lista != id_opt:
                cursor.execute(
                    f"SELECT codigo_movimiento_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s LIMIT 1",
                    [id_opt],
                )
                row_principal = cursor.fetchone()
                codigo_mov = row_principal.get("codigo_movimiento_opt") if row_principal else codigo_mov

            id_lista_principal = id_opt if id_opt is not None else id_lista
            self.stdout.write(
                f"OPT (id_lista_principal={id_lista_principal}, id_lista consultado={id_lista}), "
                f"base_empresa={base_empresa}, codigo_movimiento_opt={codigo_mov}"
            )

            # Líneas de la OPT (todas las filas con el mismo id_opt)
            if id_opt is not None:
                try:
                    cursor.execute(
                        f"SELECT id_lista_produccion, id_articulo, en_proceso_produccion, cantidad_pendiente_prod, id_operario_opt "
                        f"FROM {tbl_agrupada} WHERE id_opt = %s ORDER BY id_lista_produccion",
                        [id_opt],
                    )
                except Exception:
                    cursor.execute(
                        f"SELECT id_lista_produccion, id_articulo, en_proceso_produccion, cantidad_pendiente_prod "
                        f"FROM {tbl_agrupada} WHERE id_opt = %s ORDER BY id_lista_produccion",
                        [id_opt],
                    )
                lineas = cursor.fetchall()
                if lineas:
                    self.stdout.write("")
                    self.stdout.write(f"Líneas OPT (id_opt={id_opt}):")
                    for r in lineas:
                        extra = f" id_operario_opt={r.get('id_operario_opt')}" if "id_operario_opt" in (r or {}) else ""
                        self.stdout.write(
                            f"  id_lista_produccion={r.get('id_lista_produccion')} id_articulo={r.get('id_articulo')} "
                            f"en_proceso_produccion={r.get('en_proceso_produccion')} cantidad_pendiente_prod={r.get('cantidad_pendiente_prod')}{extra}"
                        )
            else:
                cursor.execute(
                    f"SELECT id_lista_produccion, id_articulo, en_proceso_produccion, cantidad_pendiente_prod "
                    f"FROM {tbl_agrupada} WHERE id_lista_produccion = %s",
                    [id_lista],
                )
                lineas = cursor.fetchall()
                if lineas:
                    self.stdout.write("")
                    self.stdout.write(f"lista_produccion_agrupada (id_lista_produccion={id_lista}, sin id_opt):")
                    for r in lineas:
                        self.stdout.write(
                            f"  id_articulo={r.get('id_articulo')} en_proceso_produccion={r.get('en_proceso_produccion')} "
                            f"cantidad_pendiente_prod={r.get('cantidad_pendiente_prod')}"
                        )

            if not codigo_mov:
                self.stdout.write(
                    self.style.WARNING(
                        "La OPT no tiene codigo_movimiento_opt (puede no haberse liberado aún)."
                    )
                )
                tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
                if tbl_mov:
                    cursor.execute(
                        f"SELECT codigo_movimiento, deposito_origen, deposito_destino, tipo_mov, nro_comprobante, fecha, detalle "
                        f"FROM {tbl_mov} WHERE tipo_mov = 'OPT' ORDER BY codigo_movimiento DESC LIMIT 10"
                    )
                    movs = cursor.fetchall()
                    if movs:
                        self.stdout.write("")
                        self.stdout.write("Últimos 10 movimientos OPT en MySQL:")
                        for m in movs:
                            self.stdout.write(
                                f"  codigo_mov={m.get('codigo_movimiento')} dep_destino={m.get('deposito_destino')} "
                                f"fecha={m.get('fecha')} nro={m.get('nro_comprobante')}"
                            )
                return

        # Mostrar movimiento_stock y stock para codigo_mov
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            if tbl_mov:
                cursor.execute(
                    f"SELECT codigo_movimiento, deposito_origen, deposito_destino, tipo_mov, nro_comprobante, fecha, detalle "
                    f"FROM {tbl_mov} WHERE codigo_movimiento = %s",
                    [codigo_mov],
                )
                row = cursor.fetchone()
                if row:
                    self.stdout.write("")
                    self.stdout.write("movimiento_stock (cabecera OPT):")
                    for k, v in row.items():
                        self.stdout.write(f"  {k}: {v}")
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  -> Depósito donde se generó el stock: {row.get('deposito_destino')}"
                        )
                    )
                else:
                    self.stdout.write(self.style.WARNING(f"No se encontró fila en {tbl_mov} para codigo_movimiento={codigo_mov}."))
            if tbl_stock:
                cursor.execute(
                    f"SELECT CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, CodDeposito, Entrada, Salida, TipoComp, NroComprobante "
                    f"FROM {tbl_stock} WHERE CodigoMovimiento = %s",
                    [codigo_mov],
                )
                rows = cursor.fetchall()
                if rows:
                    self.stdout.write("")
                    self.stdout.write("stock (renglones de este movimiento):")
                    for r in rows:
                        self.stdout.write(
                            f"  Art {r.get('IDArt')} ({r.get('CodigoArticulo')}) "
                            f"CodDeposito={r.get('CodDeposito')} Entrada={r.get('Entrada')} Salida={r.get('Salida')} "
                            f"TipoComp={r.get('TipoComp')} NroComp={r.get('NroComprobante')}"
                        )
                else:
                    self.stdout.write(self.style.WARNING(f"No se encontraron renglones en {tbl_stock} para codigo_movimiento={codigo_mov}."))
