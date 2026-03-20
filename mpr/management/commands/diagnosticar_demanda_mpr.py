# Diagnóstico Demanda MPR: verifica pedidos pendientes y estado de lista_produccion_*.
# La vista Demanda (ventana pack) lee lista_produccion_agrupada (cantidad_pendiente_prod > 0, en_proceso='No').
# Esa tabla se alimenta con actualizar_pedidos_produccion (al cargar la página o al pulsar Actualizar).
# Uso: docker exec Synap_app python manage.py diagnosticar_demanda_mpr --base-empresa=administranet92
# Opcional: --fecha-desde=YYYY-MM-DD --fecha-hasta=YYYY-MM-DD --busqueda=texto (mismos criterios que la pantalla)

import logging
from datetime import date

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
    if not row:
        return {}
    if isinstance(row, dict):
        return {str(k).lower(): v for k, v in row.items()}
    return {}


class Command(BaseCommand):
    help = (
        "Diagnóstico Demanda MPR: verifica la query de pedidos pendientes (origen de Actualizar) y el estado "
        "de lista_produccion_detalle/agrupada. La vista Demanda lee agrupada (se llena con Actualizar al cargar o al pulsar el botón)."
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
            help="Fecha desde (YYYY-MM-DD). Igual que en pantalla Actualizar.",
        )
        parser.add_argument(
            "--fecha-hasta",
            type=str,
            default=None,
            help="Fecha hasta (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--busqueda",
            type=str,
            default=None,
            help="Filtro por NroCompBusq/NroComprobante (opcional).",
        )

    def handle(self, *args, **options):
        base_empresa = (options.get("base_empresa") or "").strip()
        if not base_empresa:
            self.stdout.write(self.style.ERROR("Indique --base-empresa (ej. administranet92)."))
            return
        fecha_desde = (options.get("fecha_desde") or "").strip() or None
        fecha_hasta = (options.get("fecha_hasta") or "").strip() or None
        busqueda = (options.get("busqueda") or "").strip() or None

        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_stockp = _nombre_tabla(cursor, "stockp")
            tbl_cp = _nombre_tabla(cursor, "comp_ped")
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_articulo = _nombre_tabla(cursor, "articulo")

            if not all([tbl_stockp, tbl_cp, tbl_articulo]):
                self.stdout.write(
                    self.style.ERROR(
                        f"Faltan tablas en {base_empresa}: comp_ped={bool(tbl_cp)}, stockp={bool(tbl_stockp)}, articulo={bool(tbl_articulo)}."
                    )
                )
                return

            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING(f"Diagnóstico Demanda MPR — Base: {base_empresa}"))
            if fecha_desde or fecha_hasta:
                self.stdout.write(f"Filtro fechas: desde={fecha_desde or '—'} hasta={fecha_hasta or '—'}")
            if busqueda:
                self.stdout.write(f"Filtro búsqueda: {busqueda}")
            self.stdout.write("")
            self.stdout.write(
                "La vista Demanda (OPT) lee lista_produccion_agrupada (cantidad_pendiente_prod > 0, en_proceso='No'). "
                "Esa tabla se alimenta con actualizar_pedidos_produccion (al cargar la página o al pulsar Actualizar), "
                "que toma como origen la query de la sección 1 (pedidos pendientes con filtros de fecha/búsqueda)."
            )
            self.stdout.write("")

            # 1) Query de pedidos pendientes (origen de actualizar_pedidos_produccion → detalle → agrupada → vista)
            sql_origin = f"""
                SELECT cp.CodigoMovimiento AS codigo_movimiento_pedido, cp.Fecha AS fecha_pedido,
                       sp.IDArt AS id_articulo, COALESCE(sp.cantidad, sp.cantidad_pendiente, sp.Cantidad, 0) AS cantidad
                FROM {tbl_stockp} sp
                INNER JOIN {tbl_cp} cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                INNER JOIN {tbl_articulo} a ON a.IDArt = sp.IDArt AND COALESCE(TRIM(a.tipo_art_fab), '') = 'Terminado'
                WHERE COALESCE(cp.Anulado, 'No') = 'No'
                  AND COALESCE(cp.TipoComprobante, '') = 'PED'
            """
            params_origin = []
            try:
                cursor.execute("SHOW COLUMNS FROM {} LIKE %s".format(tbl_cp), ["estado_pedido_opt"])
                if cursor.fetchone():
                    sql_origin += " AND COALESCE(cp.estado_pedido_opt, '') IN ('Pendiente', 'Parcial')"
            except Exception:
                pass
            if fecha_desde:
                sql_origin += " AND cp.Fecha >= %s"
                params_origin.append(to_date_or_none(fecha_desde) or str(fecha_desde)[:10])
            if fecha_hasta:
                sql_origin += " AND cp.Fecha <= %s"
                params_origin.append(to_date_or_none(fecha_hasta) or str(fecha_hasta)[:10])
            if busqueda:
                sql_origin += " AND (cp.NroCompBusq LIKE %s OR cp.NroComprobante LIKE %s)"
                pct = "%" + busqueda + "%"
                params_origin.extend([pct, pct])

            cursor.execute(sql_origin, params_origin)
            filas_origen = cursor.fetchall()

            self.stdout.write("1) PEDIDOS PENDIENTES (origen de Actualizar — comp_ped + stockp + articulo tipo_art_fab='Terminado'):")
            if not filas_origen:
                self.stdout.write(self.style.WARNING("   Ninguna fila. Los pedidos no entran porque:"))
                self.stdout.write("   - comp_ped: Anulado='No', TipoComprobante='PED', estado_pedido_opt IN ('Pendiente','Parcial')")
                self.stdout.write("   - articulo: tipo_art_fab = 'Terminado' (exacto, sin espacios)")
                self.stdout.write("   - stockp: cantidad > 0 (se usa COALESCE(cantidad, cantidad_pendiente, Cantidad, 0))")
                if fecha_desde or fecha_hasta:
                    self.stdout.write("   - comp_ped.Fecha dentro del rango indicado")
                return

            # Filtrar qty <= 0 como hace el código
            filas_validas = []
            for row in filas_origen:
                r = _normalize_row(row)
                cod_ped = to_int_or_none(r.get("codigo_movimiento_pedido"))
                id_art = to_int_or_none(r.get("id_articulo"))
                try:
                    qty = int(float(r.get("cantidad") or 0))
                except (TypeError, ValueError):
                    qty = 0
                fecha_ped = r.get("fecha_pedido")
                if fecha_ped is not None and hasattr(fecha_ped, "strftime"):
                    fecha_str = fecha_ped.strftime("%Y-%m-%d")
                else:
                    fecha_str = (to_date_or_none(str(fecha_ped)) or fecha_ped)
                    fecha_str = str(fecha_str)[:10] if fecha_str else "-"
                if cod_ped is not None and id_art is not None and qty > 0:
                    filas_validas.append((cod_ped, id_art, qty, fecha_str))

            self.stdout.write(f"   Total filas origen: {len(filas_origen)}. Con cantidad > 0 (válidas para INSERT): {len(filas_validas)}")
            if len(filas_origen) != len(filas_validas):
                self.stdout.write(self.style.WARNING("   Hay filas con cantidad 0 o NULL que Actualizar ignora."))
            for item in filas_validas[:20]:
                cod_ped, id_art, qty, fecha_str = item[0], item[1], item[2], item[3]
                self.stdout.write(f"   Pedido={cod_ped} IDArt={id_art} cantidad={qty} fecha={fecha_str}")
            if len(filas_validas) > 20:
                self.stdout.write(f"   ... y {len(filas_validas) - 20} más.")

            if not tbl_detalle or not tbl_agrupada:
                self.stdout.write("")
                self.stdout.write(self.style.ERROR("Faltan lista_produccion_detalle o lista_produccion_agrupada; no se puede seguir el diagnóstico."))
                return

            # 2) ¿Esas (cod_ped, id_articulo) ya están en lista_produccion_detalle? (Actualizar inserta aquí; la vista usa agrupada)
            self.stdout.write("")
            self.stdout.write("2) lista_produccion_detalle (Actualizar inserta aquí; pedidos_resumen en la vista sale de detalle + comp_ped):")
            ya_en_detalle = 0
            for (cod_ped, id_art, _, _) in filas_validas:
                cursor.execute(
                    f"SELECT 1 FROM {tbl_detalle} WHERE codigo_movimiento_pedido = %s AND id_articulo = %s LIMIT 1",
                    [cod_ped, id_art],
                )
                if cursor.fetchone():
                    ya_en_detalle += 1
            self.stdout.write(f"   De {len(filas_validas)} pares (pedido, artículo): ya en detalle = {ya_en_detalle}, nuevos = {len(filas_validas) - ya_en_detalle}")

            # 3) Agregación desde detalle (Actualizar escribe en agrupada con esto; la vista lee agrupada)
            self.stdout.write("")
            self.stdout.write("3) Agregación en detalle (en_proceso_produccion='No') — Actualizar escribe en agrupada con esto:")
            try:
                cursor.execute(
                    f"""
                    SELECT id_articulo, COALESCE(SUM(cantidad_pedida), 0) AS total_pedida
                    FROM {tbl_detalle}
                    WHERE COALESCE(en_proceso_produccion, 'No') = 'No'
                    GROUP BY id_articulo
                    """,
                )
                sumas = cursor.fetchall()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   Error en la agregación: {e}"))
                self.stdout.write("   Posible columna en_proceso_produccion con otro nombre (ej. En_Proceso_Produccion).")
                sumas = []

            id_art_totales = {to_int_or_none(_normalize_row(s).get("id_articulo")): float(_normalize_row(s).get("total_pedida") or 0) for s in sumas}
            self.stdout.write(f"   Artículos con demanda en detalle (en_proceso_produccion='No'): {len(sumas)}")
            for s in sumas[:15]:
                r = _normalize_row(s)
                self.stdout.write(f"   id_articulo={r.get('id_articulo')} total_pedida={r.get('total_pedida')}")
            if len(sumas) > 15:
                self.stdout.write(f"   ... y {len(sumas) - 15} más.")

            # 3b) Artículos en el origen pero sin aporte en detalle (solo informativo; la vista Demanda los muestra igual desde pedidos)
            ids_origen = list({r[1] for r in filas_validas})
            ids_sin_agregar = [i for i in ids_origen if (id_art_totales.get(i) or 0) == 0]
            if ids_sin_agregar:
                self.stdout.write("")
                self.stdout.write("3b) Artículos en pedidos pendientes que no tienen filas en detalle (o todas con en_proceso='Si'):")
                for id_art in ids_sin_agregar:
                    cursor.execute(
                        f"""
                        SELECT codigo_movimiento_pedido, id_articulo, cantidad_pedida,
                               COALESCE(en_proceso_produccion, 'No') AS en_proceso_produccion
                        FROM {tbl_detalle}
                        WHERE id_articulo = %s
                        ORDER BY codigo_movimiento_pedido
                        """,
                        [id_art],
                    )
                    filas_art = cursor.fetchall()
                    total_origen = sum(qty for (_cp, _ia, qty, _) in filas_validas if _ia == id_art)
                    if not filas_art:
                        self.stdout.write(
                            f"   id_articulo={id_art}: no hay filas en detalle; en pedidos pendientes hay {total_origen}. "
                            "No aparecerá en Demanda hasta pulsar Actualizar (o recargar, que ejecuta Actualizar) con filtros que incluyan estos pedidos."
                        )
                    else:
                        con_no = sum(1 for r in filas_art if (_normalize_row(r).get("en_proceso_produccion") or "No").strip() == "No")
                        con_si = len(filas_art) - con_no
                        detalle_str = ", ".join(
                            f"pedido={_normalize_row(r).get('codigo_movimiento_pedido')} en_proceso='{_normalize_row(r).get('en_proceso_produccion')}'"
                            for r in filas_art[:5]
                        )
                        if con_no == 0:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"   id_articulo={id_art}: hay {len(filas_art)} fila(s) en detalle pero TODAS con en_proceso_produccion='Si' "
                                    f"(asignadas a una OPT). Por eso no suman en la agregación. Total en origen: {total_origen}. "
                                    f"Detalle: {detalle_str}"
                                )
                            )
                        else:
                            self.stdout.write(f"   id_articulo={id_art}: en detalle con 'No'={con_no}, con 'Si'={con_si}. {detalle_str}")

            # 4) Estado en lista_produccion_agrupada (la vista Demanda lee esta tabla para mostrar la lista)
            self.stdout.write("")
            self.stdout.write("4) lista_produccion_agrupada (la vista Demanda muestra filas con pendiente > 0 y en_proceso='No'):")
            ids_relevantes = list({x for x in (list(id_art_totales.keys()) + [r[1] for r in filas_validas]) if x is not None})
            ph = ",".join(["%s"] * len(ids_relevantes))
            try:
                cursor.execute(
                    f"""
                    SELECT id_articulo, id_lista_produccion, cantidad_pedida, cantidad_pendiente_prod,
                           COALESCE(en_proceso_produccion, 'No') AS en_proceso_produccion
                    FROM {tbl_agrupada}
                    WHERE id_articulo IN ({ph})
                    ORDER BY id_articulo
                    """,
                    ids_relevantes,
                )
                filas_agrupada = cursor.fetchall()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   Error leyendo agrupada: {e}"))
                filas_agrupada = []

            muestran_demanda = 0
            no_muestran = []
            for row in filas_agrupada:
                r = _normalize_row(row)
                id_art = to_int_or_none(r.get("id_articulo"))
                pend = float(r.get("cantidad_pendiente_prod") or 0)
                en_proc = (r.get("en_proceso_produccion") or "No").strip()
                if pend > 0 and en_proc == "No":
                    muestran_demanda += 1
                else:
                    no_muestran.append((id_art, pend, en_proc))
            self.stdout.write(f"   Filas en agrupada para estos artículos: {len(filas_agrupada)}. Con pendiente > 0 y en_proceso='No': {muestran_demanda}")
            if no_muestran:
                self.stdout.write("   Filas en agrupada con cantidad_pendiente_prod=0 o en_proceso_produccion!='No':")
                for (id_art, pend, en_proc) in no_muestran[:15]:
                    self.stdout.write(f"      id_articulo={id_art} cantidad_pendiente_prod={pend} en_proceso_produccion='{en_proc}'")
                if len(no_muestran) > 15:
                    self.stdout.write(f"      ... y {len(no_muestran) - 15} más.")

            # 5) Nombres de columnas (por si hay diferencias de mayúsculas)
            self.stdout.write("")
            self.stdout.write("5) COLUMNAS EN lista_produccion_detalle y lista_produccion_agrupada (por si el nombre difiere):")
            for nombre, tabla in [("lista_produccion_detalle", tbl_detalle), ("lista_produccion_agrupada", tbl_agrupada)]:
                try:
                    cursor.execute(f"SHOW COLUMNS FROM {tabla}")
                    cols = [row.get("Field") if isinstance(row, dict) else row[0] for row in cursor.fetchall()]
                    en_proc = [c for c in cols if "proceso" in (c or "").lower() or "en_proceso" in (c or "").lower()]
                    pend = [c for c in cols if "pendiente" in (c or "").lower()]
                    self.stdout.write(f"   {nombre}: en_proceso* = {en_proc}, *pendiente* = {pend}")
                except Exception as e:
                    self.stdout.write(f"   {nombre}: error {e}")

            # Resumen: qué debería verse en la vista Demanda
            articulos_origen = list({r[1] for r in filas_validas})
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING("CONCLUSIÓN:"))
            if not filas_validas:
                self.stdout.write(
                    self.style.ERROR(
                        "Ninguna fila válida (cantidad > 0) en pedidos pendientes. Actualizar no insertará nada; "
                        "la vista Demanda estará vacía. Revise: tipo_art_fab='Terminado', estado_pedido_opt IN ('Pendiente','Parcial'), filtros de fecha/búsqueda."
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Hay {len(articulos_origen)} artículo(s) en pedidos pendientes con cantidad > 0. "
                        "Tras cargar la página (o pulsar Actualizar) con el mismo rango de fechas/búsqueda, deberían aparecer en agrupada y en la vista Demanda. "
                        "Si no se ven: revise que los filtros en pantalla coincidan con las fechas de los pedidos (sección 1) y que base_empresa en sesión sea correcta."
                    )
                )
            self.stdout.write("")
            self.stdout.write(
                "La vista Demanda lee lista_produccion_agrupada; se llena al cargar la página (se ejecuta actualizar_pedidos_produccion) o al pulsar Actualizar."
            )
