"""Cargador de pedidos abiertos BEST → PED AdministraNET (comp_ped + stockp)."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

import MySQLdb

from core.mysql_pool import get_connection
from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)
from mpr.best_migration.connection import connect_best, fetch_dict
from mpr.best_migration.deposit_matcher import norm_text
from mpr.best_migration.models import (
    BestArticuloMap,
    BestClienteMap,
    BestDepositoMap,
)
from mpr.best_migration.services import refresh_parity_counters

logger = logging.getLogger(__name__)

Q2 = Decimal("0.01")
_ESTADOS_PRODUCCION_BLOQUEO = frozenset({"Produccion", "Terminado"})
_HUERFANOS_DETALLE_MAX = 20


def _fetch_best_open_order_lines() -> list[dict[str, Any]]:
    """Extrae líneas de pedidos abiertos desde REP_ORDENES_COMBINADO (solo lectura Azure)."""
    conn = connect_best()
    try:
        return fetch_dict(
            conn,
            """
            SELECT
                c.[Orden Nro] AS orden_nro,
                c.Cliente AS cliente,
                c.CUIT AS cuit,
                c.[Id Articulo] AS id_articulo,
                c.Codigo AS codigo,
                c.Articulo AS articulo,
                c.Pendiente AS pendiente,
                c.[Deposito Origen] AS deposito_origen,
                c.Precio AS precio,
                c.[Fecha Emision] AS fecha_emision
            FROM REP_ORDENES_COMBINADO c
            WHERE c.Finalizada = 0 AND c.Pendiente > 0
            ORDER BY c.[Orden Nro], c.[Id Articulo]
            """,
        )
    finally:
        conn.close()


def _load_articulo_maps(base_empresa: str) -> dict[str, BestArticuloMap]:
    qs = BestArticuloMap.objects.filter(base_empresa=base_empresa)
    return {m.best_id_articulo: m for m in qs}


def _load_cliente_maps(base_empresa: str) -> dict[tuple[str, str], BestClienteMap]:
    out: dict[tuple[str, str], BestClienteMap] = {}
    for m in BestClienteMap.objects.filter(base_empresa=base_empresa):
        key = (
            (m.best_cliente or "").strip(),
            (m.best_cuit or "").strip(),
        )
        out[key] = m
    return out


def _load_deposito_maps(base_empresa: str) -> dict[str, int]:
    """Nombre depósito BEST normalizado → CodDeposito Admin (solo VALIDADO)."""
    by_name: dict[str, int] = {}
    for m in BestDepositoMap.objects.filter(
        base_empresa=base_empresa,
        estado=BestDepositoMap.Estado.VALIDADO,
        admin_cod_deposito__isnull=False,
    ):
        nombre = norm_text(m.best_nombre)
        cod = to_int_or_none(m.admin_cod_deposito)
        if nombre and cod:
            by_name[nombre] = cod
    return by_name


def _load_articulos_admin(
    base_empresa: str, ids_articulo: list[int]
) -> dict[int, dict[str, str]]:
    from mpr.db import mysql_cursor

    ids_validos = sorted({i for i in ids_articulo if i})
    if not ids_validos:
        return {}
    placeholders = ", ".join(["%s"] * len(ids_validos))
    with mysql_cursor(base_empresa, dict_cursor=True) as cur:
        cur.execute(
            f"""
            SELECT IDArt,
                   TRIM(COALESCE(CodigoArticuloT, '')) AS codigo_articulo,
                   TRIM(COALESCE(NombreArticulo, '')) AS nombre_articulo,
                   TRIM(COALESCE(id_manual, '')) AS id_manual
            FROM articulo
            WHERE IDArt IN ({placeholders})
            """,
            ids_validos,
        )
        rows = cur.fetchall()
    return {
        id_art: {
            "codigo_articulo": str_or_default(row.get("codigo_articulo"), ""),
            "nombre_articulo": str_or_default(row.get("nombre_articulo"), ""),
            "id_manual": str_or_default(row.get("id_manual"), ""),
        }
        for row in rows
        if (id_art := to_int_or_none(row.get("IDArt"))) is not None
    }


def _resolve_cliente_map(
    cliente_maps: dict[tuple[str, str], BestClienteMap],
    cliente: str,
    cuit: str,
) -> BestClienteMap | None:
    key = ((cliente or "").strip(), (cuit or "").strip())
    m = cliente_maps.get(key)
    if (
        m
        and m.estado == BestClienteMap.Estado.VALIDADO
        and m.admin_codigo is not None
    ):
        return m
    return None


def _resolve_articulo_linea(
    articulo_maps: dict[str, BestArticuloMap],
    id_articulo: str,
) -> tuple[int | None, str]:
    """Retorna (admin_idart, motivo_huérfano). None + '' = línea OK."""
    bid = str_or_default(id_articulo, "").strip()
    m = articulo_maps.get(bid)
    if not m:
        return None, "sin_mapeo_articulo"
    if m.estado == BestArticuloMap.Estado.DESCARTADO:
        return None, "articulo_descartado"
    if (
        m.estado == BestArticuloMap.Estado.VALIDADO
        and m.admin_idart is not None
    ):
        return to_int_or_none(m.admin_idart), ""
    return None, "articulo_sin_validar"


def _resolve_deposito(
    deposito_maps: dict[str, int],
    deposito_origen: str,
) -> int:
    nombre = norm_text(deposito_origen)
    if nombre and nombre in deposito_maps:
        return deposito_maps[nombre]
    return 1


def _agrupar_por_orden(lineas: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    por_orden: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in lineas:
        orden = str_or_default(row.get("orden_nro"), "").strip()
        if orden:
            por_orden[orden].append(row)
    return dict(por_orden)


def _mapear_ordenes(
    por_orden: dict[str, list[dict[str, Any]]],
    *,
    articulo_maps: dict[str, BestArticuloMap],
    cliente_maps: dict[tuple[str, str], BestClienteMap],
    deposito_maps: dict[str, int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    """
    Retorna (ordenes_migrables, ordenes_omitidas, huerfanos_detalle).
    """
    migrables: list[dict[str, Any]] = []
    omitidas: list[dict[str, Any]] = []
    huerfanos: list[dict[str, str]] = []

    for orden_nro, filas in sorted(por_orden.items()):
        primera = filas[0]
        cliente = str_or_default(primera.get("cliente"), "")
        cuit = str_or_default(primera.get("cuit"), "")
        cli_map = _resolve_cliente_map(cliente_maps, cliente, cuit)
        if not cli_map:
            omitidas.append(
                {
                    "orden_nro": orden_nro,
                    "motivo": "cliente_sin_mapeo",
                    "cliente": cliente,
                    "cuit": cuit,
                }
            )
            huerfanos.append(
                {
                    "orden": orden_nro,
                    "tipo": "cliente",
                    "detalle": f"{cliente} (CUIT {cuit or '-'})",
                }
            )
            continue

        lineas_ok: list[dict[str, Any]] = []
        for row in filas:
            id_art = str_or_default(row.get("id_articulo"), "").strip()
            admin_id, motivo = _resolve_articulo_linea(articulo_maps, id_art)
            pendiente = to_decimal_or_none(row.get("pendiente"))
            if pendiente is None or pendiente <= 0:
                continue
            if admin_id is None:
                huerfanos.append(
                    {
                        "orden": orden_nro,
                        "tipo": "linea",
                        "detalle": f"{id_art} ({motivo})",
                    }
                )
                continue
            dep_nombre = str_or_default(row.get("deposito_origen"), "")
            lineas_ok.append(
                {
                    "id_articulo_best": id_art,
                    "admin_idart": admin_id,
                    "codigo_best": str_or_default(row.get("codigo"), ""),
                    "articulo_best": str_or_default(row.get("articulo"), ""),
                    "pendiente": pendiente,
                    "precio": to_decimal_or_none(row.get("precio")) or Decimal("0"),
                    "cod_deposito": _resolve_deposito(deposito_maps, dep_nombre),
                    "deposito_origen": dep_nombre,
                }
            )

        if not lineas_ok:
            omitidas.append(
                {
                    "orden_nro": orden_nro,
                    "motivo": "sin_lineas_validas",
                    "cliente": cliente,
                }
            )
            continue

        fecha_best = to_date_or_none(primera.get("fecha_emision")) or date.today()
        migrables.append(
            {
                "orden_nro": orden_nro,
                "cliente": cliente,
                "cuit": cuit,
                "admin_codigo": to_int_or_none(cli_map.admin_codigo),
                "fecha": fecha_best,
                "lineas": lineas_ok,
            }
        )

    return migrables, omitidas, huerfanos[:_HUERFANOS_DETALLE_MAX]


def _columnas_comp_ped_opcionales(cursor) -> set[str]:
    cols: set[str] = set()
    for col in ("estado_pedido_opt", "tipo_pedido_opt"):
        try:
            cursor.execute("SHOW COLUMNS FROM comp_ped LIKE %s", [col])
            if cursor.fetchone():
                cols.add(col)
        except Exception:
            pass
    return cols


def _nro_comp_busq(orden_nro: str, talonario_nro: int | None) -> int:
    n = to_int_or_none(orden_nro)
    if n is not None and 0 < n <= 2147483647:
        return n
    return talonario_nro or 0


def _params_stockp_linea(
    *,
    linea: dict[str, Any],
    orden: int,
    cod_mov: int,
    nro_comp: str,
    cod_cliente: int,
    id_usuario: int,
    articulo_admin: dict[str, str],
    fecha: date,
) -> dict[str, Any]:
    cant = to_decimal_or_none(linea.get("pendiente")) or Decimal("0")
    precio = to_decimal_or_none(linea.get("precio")) or Decimal("0")
    neto_r = (precio * cant).quantize(Q2)
    return {
        "IDArt": linea["admin_idart"],
        "CodigoArticulo": str_or_default(
            articulo_admin.get("codigo_articulo") or linea.get("codigo_best"), ""
        )[:64],
        "Descripcion": str_or_default(
            articulo_admin.get("nombre_articulo") or linea.get("articulo_best"), ""
        )[:255],
        "id_manual": str_or_default(articulo_admin.get("id_manual"), "")[:64],
        "CodigoMovimiento": cod_mov,
        "Fecha": fecha,
        "Salida": cant,
        "Cantidad": cant,
        "Alicuota": Decimal("21"),
        "imp_alicuota_iva": Decimal("21"),
        "PrecioVentaxU": precio,
        "PrecioNetoxU": precio,
        "PrecioIVAxU": Decimal("0"),
        "PrecioBrutoxU": precio,
        "PrecioCostoxU": Decimal("0"),
        "PrecioVentaxR": neto_r,
        "PrecioNetoxR": neto_r,
        "PrecioIVAxR": Decimal("0"),
        "PrecioBrutoxR": neto_r,
        "PrecioCostoxR": Decimal("0"),
        "PorDesc": Decimal("0"),
        "ImpDesc": Decimal("0"),
        "impuesto_interno": Decimal("0"),
        "impuesto_interno_subtotal": Decimal("0"),
        "TipoIVA": "Gravado",
        "CodigoCP": cod_cliente,
        "TipoComp": "Pedido",
        "Comprobante": "PED",
        "NroComprobante": nro_comp,
        "CodDeposito": linea["cod_deposito"],
        "CodSucursal": 1,
        "idusuario": id_usuario,
        "CodViajante": 0,
        "CodLaboratorio": 0,
        "lista_precio": 0,
        "tipo_art": "",
        "Orden": orden,
        "saldo": cant,
        "cantidad_entregada": cant,
        "cantidad_pendiente": cant,
        "promocion": "No",
        "promocion_por": Decimal("0"),
        "promocion_tipo": "",
        "promocion_cant": 0,
        "tipo_unidad": "Unidad",
        "cantidad_dividir": Decimal("1"),
        "cantidad_unidad_display": Decimal("1"),
        "codmov_presupuesto": 0,
        "NroPresupuesto": "",
    }


_SQL_INSERT_STOCKP = """
    INSERT INTO stockp SET
        IDArt = %(IDArt)s,
        CodigoArticulo = %(CodigoArticulo)s,
        Descripcion = %(Descripcion)s,
        id_manual = %(id_manual)s,
        CodigoMovimiento = %(CodigoMovimiento)s,
        Fecha = %(Fecha)s,
        Salida = %(Salida)s,
        Cantidad = %(Cantidad)s,
        saldo = %(saldo)s,
        Alicuota = %(Alicuota)s,
        imp_alicuota_iva = %(imp_alicuota_iva)s,
        PrecioVentaxU = %(PrecioVentaxU)s,
        PrecioNetoxU = %(PrecioNetoxU)s,
        PrecioIVAxU = %(PrecioIVAxU)s,
        PrecioBrutoxU = %(PrecioBrutoxU)s,
        PrecioCostoxU = %(PrecioCostoxU)s,
        PrecioVentaxR = %(PrecioVentaxR)s,
        PrecioNetoxR = %(PrecioNetoxR)s,
        PrecioIVAxR = %(PrecioIVAxR)s,
        PrecioBrutoxR = %(PrecioBrutoxR)s,
        PrecioCostoxR = %(PrecioCostoxR)s,
        PorDesc = %(PorDesc)s,
        ImpDesc = %(ImpDesc)s,
        impuesto_interno = %(impuesto_interno)s,
        impuesto_interno_subtotal = %(impuesto_interno_subtotal)s,
        TipoIVA = %(TipoIVA)s,
        CodigoCP = %(CodigoCP)s,
        Tipo = 'Cliente',
        TipoComp = %(TipoComp)s,
        Comprobante = %(Comprobante)s,
        Anulado = 'No',
        NroComprobante = %(NroComprobante)s,
        CodDeposito = %(CodDeposito)s,
        CodSucursal = %(CodSucursal)s,
        idusuario = %(idusuario)s,
        CodViajante = %(CodViajante)s,
        CodLaboratorio = %(CodLaboratorio)s,
        lista_precio = %(lista_precio)s,
        tipo_art = %(tipo_art)s,
        Orden = %(Orden)s,
        cantidad_entregada = %(cantidad_entregada)s,
        cantidad_pendiente = %(cantidad_pendiente)s,
        promocion = %(promocion)s,
        promocion_por = %(promocion_por)s,
        promocion_tipo = %(promocion_tipo)s,
        promocion_cant = %(promocion_cant)s,
        tipo_unidad = %(tipo_unidad)s,
        cantidad_dividir = %(cantidad_dividir)s,
        cantidad_unidad_display = %(cantidad_unidad_display)s,
        codmov_presupuesto = %(codmov_presupuesto)s,
        NroPresupuesto = %(NroPresupuesto)s
"""


def _sql_insert_comp_ped(extra_cols: set[str]) -> str:
    base = """
        INSERT INTO comp_ped SET
            Fecha = %(Fecha)s,
            TipoComprobante = %(TipoComprobante)s,
            NroComprobante = %(NroComprobante)s,
            NroCompBusq = %(NroCompBusq)s,
            Codigo = %(Codigo)s,
            CodigoMovimiento = %(CodigoMovimiento)s,
            id_pv = %(id_pv)s,
            CodSucursal = %(CodSucursal)s,
            IdUsuario = %(IdUsuario)s,
            CodViajante = %(CodViajante)s,
            TipoPedido = %(TipoPedido)s,
            Detalle = %(Detalle)s,
            ImporteVenta = %(ImporteVenta)s,
            IVA1 = %(IVA1)s,
            IVA2 = %(IVA2)s,
            Alicuota1 = 21,
            Alicuota2 = 10.5,
            Exento = %(Exento)s,
            SubTotal1 = %(SubTotal1)s,
            SubTotal2 = %(SubTotal2)s,
            SubTotalGral = %(SubTotalGral)s,
            PorDesc1 = 0,
            PorDesc2 = 0,
            ImpDesc1 = 0,
            ImpDesc2 = 0,
            SubTotalDesc1 = %(SubTotal1)s,
            SubTotalDesc2 = %(SubTotal2)s,
            SubtotalDesc = %(SubTotalGral)s,
            impuesto_interno_total = 0,
            total_percep = 0,
            autorizacion_sistema = '',
            Estado = 'Pendiente',
            Anulado = 'No',
            Vencimiento = %(Vencimiento)s,
            FechaEntrega = %(FechaEntrega)s,
            FormaEntrega = '',
            id_deposito_despacho = %(id_deposito_despacho)s,
            CondVenta = '',
            id_condventa = NULL,
            fecha_control = %(fecha_control)s
    """
    if "estado_pedido_opt" in extra_cols:
        base += ",\n            estado_pedido_opt = %(estado_pedido_opt)s"
    if "tipo_pedido_opt" in extra_cols:
        base += ",\n            tipo_pedido_opt = %(tipo_pedido_opt)s"
    return base


def _sql_update_comp_ped(extra_cols: set[str]) -> str:
    base = """
        UPDATE comp_ped SET
            Fecha = %(Fecha)s,
            Codigo = %(Codigo)s,
            Detalle = %(Detalle)s,
            ImporteVenta = %(ImporteVenta)s,
            SubTotal1 = %(SubTotal1)s,
            SubTotal2 = %(SubTotal2)s,
            SubTotalGral = %(SubTotalGral)s,
            SubTotalDesc1 = %(SubTotal1)s,
            SubTotalDesc2 = %(SubTotal2)s,
            SubtotalDesc = %(SubTotalGral)s,
            FechaEntrega = %(FechaEntrega)s,
            id_deposito_despacho = %(id_deposito_despacho)s,
            Anulado = 'No',
            Estado = 'Pendiente'
    """
    if "estado_pedido_opt" in extra_cols:
        base += ",\n            estado_pedido_opt = %(estado_pedido_opt)s"
    if "tipo_pedido_opt" in extra_cols:
        base += ",\n            tipo_pedido_opt = %(tipo_pedido_opt)s"
    base += "\n        WHERE CodigoMovimiento = %(CodigoMovimiento)s"
    return base


def _totales_pedido(lineas: list[dict[str, Any]]) -> Decimal:
    total = Decimal("0")
    for ln in lineas:
        cant = to_decimal_or_none(ln.get("pendiente")) or Decimal("0")
        precio = to_decimal_or_none(ln.get("precio")) or Decimal("0")
        total += cant * precio
    return total.quantize(Q2)


def _escribir_pedidos_mysql(
    base_empresa: str,
    ordenes: list[dict[str, Any]],
    *,
    id_usuario: int,
    id_pv: int,
    prefijo: str,
) -> tuple[int, int, list[str]]:
    """
    Inserta o actualiza PED en MySQL. Retorna (escritos, omitidos_existentes, errores).
    """
    if not ordenes:
        return 0, 0, []

    ids_art = [
        ln["admin_idart"]
        for orden in ordenes
        for ln in orden["lineas"]
    ]
    articulos_admin = _load_articulos_admin(base_empresa, ids_art)

    escritos = 0
    omitidos_existentes = 0
    errores: list[str] = []

    with get_connection(base_empresa) as conn:
        try:
            conn.autocommit(False)
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            extra_cols = _columnas_comp_ped_opcionales(cur)
            sql_insert = _sql_insert_comp_ped(extra_cols)
            sql_update = _sql_update_comp_ped(extra_cols)

            for orden in ordenes:
                orden_nro = orden["orden_nro"]
                nro_comp = f"{prefijo}-{orden_nro}"
                try:
                    cur.execute(
                        """
                        SELECT CodigoMovimiento, Anulado,
                               COALESCE(estado_pedido_opt, '') AS estado_pedido_opt
                        FROM comp_ped
                        WHERE NroComprobante = %s AND TipoComprobante = 'PED'
                        LIMIT 1
                        """,
                        [nro_comp],
                    )
                    existente = cur.fetchone()
                    cod_mov: int | None = None
                    modo_upsert = False

                    if existente:
                        cod_mov = to_int_or_none(existente.get("CodigoMovimiento"))
                        anulado = str_or_default(existente.get("Anulado"), "No") == "Si"
                        if not anulado:
                            estado_opt = str_or_default(
                                existente.get("estado_pedido_opt"), ""
                            ).strip()
                            if estado_opt in _ESTADOS_PRODUCCION_BLOQUEO:
                                omitidos_existentes += 1
                                errores.append(
                                    f"Orden {orden_nro}: PED existente en producción "
                                    f"({estado_opt}), omitido."
                                )
                                continue
                        modo_upsert = cod_mov is not None

                    if cod_mov is None:
                        cur.execute(
                            "SELECT CodigoMovimiento FROM codmov WHERE codigo = 1 FOR UPDATE"
                        )
                        row_cm = cur.fetchone()
                        if not row_cm:
                            raise RuntimeError("No se pudo obtener codmov.")
                        cod_mov = (to_int_or_none(row_cm.get("CodigoMovimiento")) or 0) + 1
                        cur.execute(
                            "UPDATE codmov SET CodigoMovimiento = %s WHERE codigo = 1",
                            [cod_mov],
                        )

                    talonario_nro: int | None = None
                    if not modo_upsert:
                        cur.execute(
                            """
                            SELECT Nro FROM talonarios
                            WHERE id_punto_venta = %s AND TipoComprobante = 'PED'
                            LIMIT 1 FOR UPDATE
                            """,
                            [id_pv],
                        )
                        tal = cur.fetchone()
                        if tal:
                            talonario_nro = to_int_or_none(tal.get("Nro"))
                            cur.execute(
                                """
                                UPDATE talonarios SET Nro = Nro + 1
                                WHERE id_punto_venta = %s AND TipoComprobante = 'PED'
                                """,
                                [id_pv],
                            )

                    lineas = orden["lineas"]
                    total = _totales_pedido(lineas)
                    fecha = orden.get("fecha") or date.today()
                    cod_cliente = to_int_or_none(orden.get("admin_codigo")) or 0
                    dep_despacho = lineas[0]["cod_deposito"] if lineas else 1

                    params_cab = {
                        "Fecha": fecha,
                        "TipoComprobante": "PED",
                        "NroComprobante": nro_comp,
                        "NroCompBusq": _nro_comp_busq(orden_nro, talonario_nro),
                        "Codigo": cod_cliente,
                        "CodigoMovimiento": cod_mov,
                        "id_pv": id_pv,
                        "CodSucursal": 1,
                        "IdUsuario": id_usuario,
                        "CodViajante": 0,
                        "TipoPedido": "Migracion BEST",
                        "Detalle": f"Cutover BEST orden {orden_nro}"[:255],
                        "ImporteVenta": total,
                        "IVA1": Decimal("0"),
                        "IVA2": Decimal("0"),
                        "Exento": total,
                        "SubTotal1": total,
                        "SubTotal2": Decimal("0"),
                        "SubTotalGral": total,
                        "Vencimiento": fecha,
                        "FechaEntrega": fecha,
                        "id_deposito_despacho": dep_despacho,
                        "fecha_control": date.today().strftime("%d/%m/%Y %H:%M"),
                    }
                    if "estado_pedido_opt" in extra_cols:
                        params_cab["estado_pedido_opt"] = "Pendiente"
                    if "tipo_pedido_opt" in extra_cols:
                        params_cab["tipo_pedido_opt"] = "Fabrica"

                    if modo_upsert:
                        cur.execute(sql_update, params_cab)
                        cur.execute(
                            """
                            UPDATE stockp SET Anulado = 'Si'
                            WHERE CodigoMovimiento = %s AND COALESCE(Anulado, 'No') = 'No'
                            """,
                            [cod_mov],
                        )
                    else:
                        cur.execute(sql_insert, params_cab)

                    for idx, ln in enumerate(lineas, start=1):
                        art_admin = articulos_admin.get(ln["admin_idart"], {})
                        cur.execute(
                            _SQL_INSERT_STOCKP,
                            _params_stockp_linea(
                                linea=ln,
                                orden=idx,
                                cod_mov=cod_mov,
                                nro_comp=nro_comp,
                                cod_cliente=cod_cliente,
                                id_usuario=id_usuario,
                                articulo_admin=art_admin,
                                fecha=fecha,
                            ),
                        )

                    escritos += 1
                except Exception as exc:
                    logger.exception(
                        "Error escribiendo pedido BEST %s en %s", orden_nro, base_empresa
                    )
                    errores.append(f"Orden {orden_nro}: {exc}")

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                conn.autocommit(True)
            except Exception:
                pass

    return escritos, omitidos_existentes, errores


def migrar_pedidos_best(
    base_empresa: str,
    *,
    dry_run: bool = True,
    id_usuario: int | None = None,
    id_pv: int = 1,
    prefijo: str = "BEST",
) -> dict[str, Any]:
    """
    Siembra pedidos abiertos BEST como PED AdministraNET.

    Retorna dict con métricas de extract/map/load y post-proceso MPR.
    """
    parity = refresh_parity_counters(base_empresa)
    gate_ok = bool(parity.migracion_habilitada)

    if not dry_run and not gate_ok:
        raise ValueError(
            "Gate de migración cerrado: completá artículos, clientes requeridos "
            "y confirmación de unidades antes de confirmar la siembra."
        )

    lineas_raw = _fetch_best_open_order_lines()
    por_orden = _agrupar_por_orden(lineas_raw)
    articulo_maps = _load_articulo_maps(base_empresa)
    cliente_maps = _load_cliente_maps(base_empresa)
    deposito_maps = _load_deposito_maps(base_empresa)

    migrables, omitidas, huerfanos = _mapear_ordenes(
        por_orden,
        articulo_maps=articulo_maps,
        cliente_maps=cliente_maps,
        deposito_maps=deposito_maps,
    )

    lineas_ok = sum(len(o["lineas"]) for o in migrables)
    lineas_huerfanas = max(0, len(lineas_raw) - lineas_ok)

    result: dict[str, Any] = {
        "dry_run": dry_run,
        "gate_ok": gate_ok,
        "ordenes_leidas": len(por_orden),
        "ordenes_migrables": len(migrables),
        "ordenes_omitidas": len(omitidas),
        "lineas_ok": lineas_ok,
        "lineas_huerfanas": lineas_huerfanas,
        "pedidos_escritos": 0,
        "pedidos_omitidos_existentes": 0,
        "huerfanos_detalle": huerfanos,
        "errores": [],
        "post_actualizar_ok": None,
        "post_actualizar_mensaje": "",
    }

    if not gate_ok and dry_run:
        result["errores"].append(
            "Aviso: gate cerrado; la confirmación estará bloqueada hasta completar paridad."
        )

    if dry_run:
        return result

    uid = to_int_or_none(id_usuario)
    if not uid:
        raise ValueError(
            "Se requiere id_usuario para confirmar la siembra de pedidos BEST."
        )

    escritos, omitidos_existentes, errores_esc = _escribir_pedidos_mysql(
        base_empresa,
        migrables,
        id_usuario=uid,
        id_pv=id_pv,
        prefijo=prefijo,
    )
    result["pedidos_escritos"] = escritos
    result["pedidos_omitidos_existentes"] = omitidos_existentes
    result["errores"].extend(errores_esc)

    if escritos > 0:
        from mpr.services import actualizar_pedidos_produccion

        try:
            ok, msg = actualizar_pedidos_produccion(base_empresa, uid)
            result["post_actualizar_ok"] = ok
            result["post_actualizar_mensaje"] = msg or ""
            if not ok:
                result["errores"].append(
                    f"Post actualizar_pedidos_produccion: {msg or 'error desconocido'}"
                )
        except Exception as exc:
            logger.exception("post actualizar_pedidos_produccion tras migrar pedidos BEST")
            result["post_actualizar_ok"] = False
            result["post_actualizar_mensaje"] = str(exc)
            result["errores"].append(f"Post actualizar_pedidos_produccion: {exc}")

    return result
