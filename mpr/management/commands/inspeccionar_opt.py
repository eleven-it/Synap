# MPR - Inspeccionar en la DB cómo quedó registrada una OPT (depósito, movimiento_stock, stock).
# Uso: python manage.py inspeccionar_opt <id_lista>
# Ejemplo: python manage.py inspeccionar_opt 13

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
    help = "Inspecciona en la DB cómo quedó registrada una OPT (depósito, movimiento_stock, stock)."

    def add_arguments(self, parser):
        parser.add_argument(
            "id_lista",
            type=int,
            help="id_lista_produccion de la OPT (ej. 13 para OPT 13).",
        )

    def handle(self, *args, **options):
        id_lista = options["id_lista"]
        from mpr.models import OptLinea

        opt_linea = OptLinea.objects.filter(id_lista_produccion=id_lista).select_related("opt").first()
        if not opt_linea:
            self.stdout.write(self.style.WARNING(f"No existe ninguna OPT con id_lista_produccion={id_lista}."))
            return
        opt = opt_linea.opt
        base_empresa = opt.base_empresa
        codigo_mov = opt.codigo_movimiento
        self.stdout.write(
            f"OPT (id_lista_principal={opt.id_lista_principal}, id_lista consultado={id_lista}), "
            f"base_empresa={base_empresa}, codigo_movimiento={codigo_mov}"
        )
        if not codigo_mov:
            self.stdout.write(
                self.style.WARNING(
                    "En Django la OPT no tiene codigo_movimiento (puede no haberse liberado o falló guardar el vínculo)."
                )
            )
            # Inspeccionar estado en lista_produccion_agrupada y últimos movimientos OPT en MySQL
            agrup = []
            movs = []
            with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
                tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
                tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
                tbl_stock = _nombre_tabla(cursor, "stock")
                if tbl_agrupada:
                    cursor.execute(
                        f"SELECT id_lista_produccion, id_articulo, en_proceso_produccion, cantidad_pendiente_prod "
                        f"FROM {tbl_agrupada} WHERE id_lista_produccion = %s",
                        [id_lista],
                    )
                    agrup = cursor.fetchall()
                    if agrup:
                        self.stdout.write("")
                        self.stdout.write(f"lista_produccion_agrupada (id_lista_produccion={id_lista}):")
                        for r in agrup:
                            self.stdout.write(
                                f"  id_articulo={r.get('id_articulo')} en_proceso_produccion={r.get('en_proceso_produccion')} "
                                f"cantidad_pendiente_prod={r.get('cantidad_pendiente_prod')}"
                            )
                        if any((r.get("en_proceso_produccion") or "").strip() == "Si" for r in agrup):
                            self.stdout.write(
                                self.style.NOTICE(
                                    "  -> En progreso: la liberación sí se ejecutó en MySQL; el vínculo codigo_movimiento no se guardó en Django."
                                )
                            )
                    else:
                        self.stdout.write(self.style.WARNING(f"No hay filas en {tbl_agrupada} para id_lista_produccion={id_lista}."))
                if tbl_mov:
                    cursor.execute(
                        f"SELECT codigo_movimiento, deposito_origen, deposito_destino, tipo_mov, nro_comprobante, fecha, detalle "
                        f"FROM {tbl_mov} WHERE tipo_mov = 'OPT' ORDER BY codigo_movimiento DESC LIMIT 10"
                    )
                    movs = cursor.fetchall()
                    if movs:
                        self.stdout.write("")
                        self.stdout.write("Últimos 10 movimientos OPT en MySQL (para identificar por fecha/nro el de esta OP):")
                        for m in movs:
                            self.stdout.write(
                                f"  codigo_mov={m.get('codigo_movimiento')} dep_destino={m.get('deposito_destino')} "
                                f"fecha={m.get('fecha')} nro={m.get('nro_comprobante')} detalle={str(m.get('detalle') or '')[:50]}"
                            )
                        # Si hay una sola fila en agrupada con en_proceso y un solo movimiento OPT reciente, podría ser este
                        if agrup and len(movs) >= 1:
                            ult = movs[0]
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"  -> Depósito del último movimiento OPT en DB: {ult.get('deposito_destino')} "
                                    f"(codigo_movimiento={ult.get('codigo_movimiento')})."
                                )
                            )
                    else:
                        self.stdout.write(self.style.WARNING("No hay movimientos tipo OPT en la base."))
            return
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
                            f"  -> Depósito donde se generó el stock (origen=destino): {row.get('deposito_destino')}"
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
