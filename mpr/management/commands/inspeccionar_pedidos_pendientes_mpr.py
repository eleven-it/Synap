# MPR - Inspeccionar en la DB pedidos pendientes, sus artículos y condiciones para lista_produccion_agrupada.
# Uso: python manage.py inspeccionar_pedidos_pendientes_mpr --base-empresa=administranet92
# Opcional: --fecha-desde=2026-03-01 --fecha-hasta=2026-03-31

import logging
from django.core.management.base import BaseCommand

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_int_or_none, to_date_or_none

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


def _normalize_row(row):
    """Convierte fila a dict con claves en minúsculas para acceso case-insensitive."""
    if not row:
        return {}
    if isinstance(row, dict):
        return {str(k).lower(): v for k, v in row.items()}
    return {}


class Command(BaseCommand):
    help = (
        "Inspecciona en la DB: pedidos con estado_pedido_opt='Pendiente', "
        "sus artículos en stockp y si cumplen condiciones para lista_produccion_agrupada (tipo_art_fab='Terminado')."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-empresa",
            type=str,
            required=True,
            help="Base de datos MySQL (ej. administranet92).",
        )
        parser.add_argument(
            "--fecha-desde",
            type=str,
            default=None,
            help="Fecha desde (YYYY-MM-DD). Opcional, igual que en Actualizar.",
        )
        parser.add_argument(
            "--fecha-hasta",
            type=str,
            default=None,
            help="Fecha hasta (YYYY-MM-DD). Opcional.",
        )

    def handle(self, *args, **options):
        base_empresa = (options.get("base_empresa") or "").strip()
        if not base_empresa:
            self.stdout.write(self.style.ERROR("Indique --base-empresa (ej. administranet92)."))
            return
        fecha_desde = (options.get("fecha_desde") or "").strip() or None
        fecha_hasta = (options.get("fecha_hasta") or "").strip() or None

        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_cp = _nombre_tabla(cursor, "comp_ped")
            tbl_stockp = _nombre_tabla(cursor, "stockp")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_cp or not tbl_stockp or not tbl_articulo:
                self.stdout.write(
                    self.style.ERROR(
                        f"Faltan tablas en {base_empresa}: comp_ped={bool(tbl_cp)}, stockp={bool(tbl_stockp)}, articulo={bool(tbl_articulo)}."
                    )
                )
                return

            # 1) Pedidos que cumplen: Anulado='No', TipoComprobante='PED', estado_pedido_opt='Pendiente'
            sql_pedidos = f"""
                SELECT cp.CodigoMovimiento, cp.NroComprobante, cp.Fecha,
                       COALESCE(cp.Anulado, '') AS Anulado,
                       COALESCE(cp.TipoComprobante, '') AS TipoComprobante,
                       COALESCE(cp.estado_pedido_opt, '') AS estado_pedido_opt
                FROM {tbl_cp} cp
                WHERE COALESCE(cp.Anulado, 'No') = 'No'
                  AND COALESCE(cp.TipoComprobante, '') = 'PED'
            """
            params = []
            try:
                cursor.execute("SHOW COLUMNS FROM {} LIKE %s".format(tbl_cp.replace("`", "`")), ["estado_pedido_opt"])
                if cursor.fetchone():
                    sql_pedidos += " AND COALESCE(cp.estado_pedido_opt, '') = 'Pendiente'"
            except Exception:
                pass
            if fecha_desde:
                sql_pedidos += " AND cp.Fecha >= %s"
                params.append(to_date_or_none(fecha_desde) or str(fecha_desde)[:10])
            if fecha_hasta:
                sql_pedidos += " AND cp.Fecha <= %s"
                params.append(to_date_or_none(fecha_hasta) or str(fecha_hasta)[:10])
            sql_pedidos += " ORDER BY cp.Fecha, cp.CodigoMovimiento"
            cursor.execute(sql_pedidos, params)
            pedidos = cursor.fetchall()

            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING(f"Base: {base_empresa}"))
            if fecha_desde or fecha_hasta:
                self.stdout.write(f"Filtro fechas: desde={fecha_desde or '—'} hasta={fecha_hasta or '—'}")
            self.stdout.write("")
            self.stdout.write("1) PEDIDOS PENDIENTES (Anulado='No', TipoComprobante='PED', estado_pedido_opt='Pendiente'):")
            if not pedidos:
                self.stdout.write(self.style.WARNING("   No hay pedidos que cumplan las condiciones."))
                self.stdout.write("   Compruebe: estado_pedido_opt='Pendiente', Anulado='No', TipoComprobante='PED'.")
                if fecha_desde or fecha_hasta:
                    self.stdout.write(
                        self.style.WARNING(
                            "   Si usó filtro de fechas: comp_ped.Fecha debe estar entre fecha_desde y fecha_hasta. "
                            "Sus pedidos pueden tener Fecha fuera de ese rango."
                        )
                    )
                return
            for p in pedidos:
                r = _normalize_row(p)
                self.stdout.write(
                    f"   CodigoMovimiento={r.get('codigomovimiento')} "
                    f"NroComprobante={r.get('nrocomprobante')} Fecha={r.get('fecha')} "
                    f"estado_pedido_opt={r.get('estado_pedido_opt')}"
                )
            codigos_ped = [to_int_or_none(_normalize_row(p).get("codigomovimiento")) for p in pedidos]
            codigos_ped = [c for c in codigos_ped if c is not None]

            # 2) Renglones en stockp de esos pedidos
            if not codigos_ped:
                return
            placeholders = ",".join(["%s"] * len(codigos_ped))
            cursor.execute(
                f"""
                SELECT sp.CodigoMovimiento, sp.IDArt AS id_articulo,
                       COALESCE(sp.cantidad, sp.cantidad_pendiente, sp.Cantidad, 0) AS cantidad
                FROM {tbl_stockp} sp
                WHERE sp.CodigoMovimiento IN ({placeholders})
                ORDER BY sp.CodigoMovimiento, sp.IDArt
                """,
                codigos_ped,
            )
            renglones = cursor.fetchall()
            self.stdout.write("")
            self.stdout.write("2) RENGLONES EN STOCKP (de esos pedidos):")
            if not renglones:
                self.stdout.write(self.style.WARNING("   No hay renglones en stockp para estos pedidos."))
                self.stdout.write("   Sin renglones, Actualizar no puede agregar nada a lista_produccion_agrupada.")
                return
            ids_articulos = list({to_int_or_none(_normalize_row(r).get("id_articulo")) for r in renglones if to_int_or_none(_normalize_row(r).get("id_articulo")) is not None})
            self.stdout.write(f"   Total renglones: {len(renglones)}. Artículos distintos: {len(ids_articulos)}")

            # 3) tipo_art_fab de esos artículos
            tiene_col_tipo = False
            try:
                cursor.execute("SHOW COLUMNS FROM {} LIKE %s".format(tbl_articulo.replace("`", "`")), ["tipo_art_fab"])
                tiene_col_tipo = cursor.fetchone() is not None
            except Exception:
                pass

            if not ids_articulos:
                return
            ph = ",".join(["%s"] * len(ids_articulos))
            if tiene_col_tipo:
                cursor.execute(
                    f"""
                    SELECT a.IDArt, COALESCE(a.CodigoArticuloT, a.CodigoArticulo, '') AS codigo,
                           COALESCE(a.NombreArticulo, '') AS nombre, COALESCE(TRIM(a.tipo_art_fab), '') AS tipo_art_fab
                    FROM {tbl_articulo} a
                    WHERE a.IDArt IN ({ph})
                    """,
                    ids_articulos,
                )
            else:
                cursor.execute(
                    f"""
                    SELECT a.IDArt, COALESCE(a.CodigoArticuloT, a.CodigoArticulo, '') AS codigo,
                           COALESCE(a.NombreArticulo, '') AS nombre, NULL AS tipo_art_fab
                    FROM {tbl_articulo} a
                    WHERE a.IDArt IN ({ph})
                    """,
                    ids_articulos,
                )
            arts = {to_int_or_none(_normalize_row(x).get("idart")): _normalize_row(x) for x in cursor.fetchall()}

            self.stdout.write("")
            self.stdout.write("3) ARTÍCULOS Y tipo_art_fab (condición para lista_produccion_agrupada):")
            if not tiene_col_tipo:
                self.stdout.write(self.style.WARNING("   La tabla articulo NO tiene columna tipo_art_fab."))
                self.stdout.write("   En el código actual se exige tipo_art_fab = 'Terminado'; sin la columna el JOIN fallaría.")
            else:
                self.stdout.write("   Se exige tipo_art_fab = 'Terminado' para que el renglón entre en Actualizar.")
            self.stdout.write("")

            cualifican = 0
            no_cualifican = []
            for r in renglones:
                row = _normalize_row(r)
                id_art = to_int_or_none(row.get("id_articulo"))
                cod_mov = to_int_or_none(row.get("codigomovimiento"))
                qty = row.get("cantidad") or 0
                try:
                    qty = int(float(qty))
                except (TypeError, ValueError):
                    qty = 0
                art = arts.get(id_art) if id_art is not None else {}
                tipo = (art.get("tipo_art_fab") or "").strip() if art else ""
                cumple = tipo == "Terminado"
                if cumple and qty > 0:
                    cualifican += 1
                else:
                    no_cualifican.append((id_art, cod_mov, qty, tipo, art.get("codigo"), art.get("nombre")))

                tipo_ok = "SÍ (Terminado)" if cumple else f"NO (tipo_art_fab='{tipo or '(vacío/NULL)'}')"
                self.stdout.write(
                    f"   Pedido {cod_mov} | IDArt={id_art} ({art.get('codigo')} {art.get('nombre') or ''}) "
                    f"cantidad={qty} | tipo_art_fab: {tipo_ok}"
                )

            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING("RESUMEN:"))
            self.stdout.write(f"   Pedidos pendientes (con filtros): {len(pedidos)}")
            self.stdout.write(f"   Renglones en stockp: {len(renglones)}")
            self.stdout.write(f"   Renglones que SÍ cumplen (tipo_art_fab='Terminado' y cantidad > 0): {cualifican}")
            self.stdout.write(f"   Renglones que NO cumplen: {len(no_cualifican)}")
            if cualifican == 0 and renglones:
                self.stdout.write("")
                self.stdout.write(
                    self.style.ERROR(
                        "Ningún renglón cumple tipo_art_fab = 'Terminado'. "
                        "Actualizar no insertará nada en lista_produccion_detalle ni lista_produccion_agrupada."
                    )
                )
                self.stdout.write("   Solución: en la tabla articulo, asignar tipo_art_fab = 'Terminado' a los artículos que correspondan.")
            elif cualifican > 0:
                self.stdout.write("")
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Hay {cualifican} renglón/renglones que entrarían al pulsar Actualizar."
                    )
                )
