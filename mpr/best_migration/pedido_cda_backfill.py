"""Remediación de cliente_datos_adicionales para PED BEST ya migrados."""

from __future__ import annotations

import logging
from typing import Any

import MySQLdb

from core.mysql_pool import get_connection
from core.utils.administranet_types import to_date_or_none, to_int_or_none

logger = logging.getLogger(__name__)

_DETALLE_OMITIDOS_MAX = 20
_DETALLE_ESCRITOS_MAX = 20

_SQL_PEDIDOS = """
    SELECT
        cp.CodigoMovimiento AS cod_mov,
        cp.NroComprobante AS nro_comprobante,
        cp.Codigo AS id_cliente,
        cp.Fecha AS fecha,
        cp.FechaEntrega AS fecha_entrega,
        cp.id_deposito_despacho AS id_deposito_despacho,
        cda_ok.id_cliente_domicilio AS cda_id_domicilio,
        CASE WHEN cda_any.CodigoMovimiento IS NOT NULL THEN 1 ELSE 0 END AS tiene_cda
    FROM comp_ped cp
    LEFT JOIN (
        SELECT CodigoMovimiento, MAX(id_cliente_domicilio) AS id_cliente_domicilio
        FROM cliente_datos_adicionales
        WHERE COALESCE(id_cliente_domicilio, 0) > 0
        GROUP BY CodigoMovimiento
    ) cda_ok ON cda_ok.CodigoMovimiento = cp.CodigoMovimiento
    LEFT JOIN (
        SELECT DISTINCT CodigoMovimiento
        FROM cliente_datos_adicionales
    ) cda_any ON cda_any.CodigoMovimiento = cp.CodigoMovimiento
    WHERE cp.TipoComprobante = 'PED'
      AND COALESCE(cp.Anulado, 'No') = 'No'
      AND cp.NroComprobante LIKE %s
    ORDER BY cp.NroComprobante
"""

_SQL_PRIMER_DOMICILIO = """
    SELECT id_cliente_domicilio
    FROM cliente_domicilio
    WHERE id_cliente = %s AND COALESCE(anulado, 'No') = 'No'
    ORDER BY id_cliente_domicilio ASC
    LIMIT 1
"""

_SQL_INSERT_CDA = """
    INSERT INTO cliente_datos_adicionales
        (fechaEntrega, id_deposito_despacho, Fentrega, origen_pedido,
         TipoComprobante, id_cliente, CodigoMovimiento, id_cliente_domicilio, id_ruta)
    VALUES (%s, %s, '', 'Migracion BEST', 'PED', %s, %s, %s, NULL)
"""

_SQL_UPDATE_CDA = """
    UPDATE cliente_datos_adicionales SET
        fechaEntrega = %s,
        id_deposito_despacho = %s,
        Fentrega = '',
        origen_pedido = 'Migracion BEST',
        TipoComprobante = 'PED',
        id_cliente = %s,
        id_cliente_domicilio = %s,
        id_ruta = NULL
    WHERE CodigoMovimiento = %s
"""


def _resolver_fecha_entrega(row: dict[str, Any]) -> Any:
    fecha_entrega = to_date_or_none(row.get("fecha_entrega"))
    if fecha_entrega is not None:
        return fecha_entrega
    return to_date_or_none(row.get("fecha"))


def _resolver_deposito(row: dict[str, Any]) -> int:
    dep = to_int_or_none(row.get("id_deposito_despacho"))
    if dep is not None and dep > 0:
        return dep
    return 1


def _tiene_cda_ok(row: dict[str, Any]) -> bool:
    id_dom = to_int_or_none(row.get("cda_id_domicilio"))
    return id_dom is not None and id_dom > 0


def _buscar_primer_domicilio(cur, id_cliente: int) -> int | None:
    cur.execute(_SQL_PRIMER_DOMICILIO, [id_cliente])
    dom_row = cur.fetchone()
    if not dom_row:
        return None
    return to_int_or_none(dom_row.get("id_cliente_domicilio"))


def backfill_cda_pedidos_best(
    base_empresa: str,
    *,
    dry_run: bool = True,
    prefijo: str = "BEST",
) -> dict[str, Any]:
    """
    Asocia filas en cliente_datos_adicionales a PED BEST ya sembrados en comp_ped.

    Por defecto ensayo (dry_run=True): no escribe, solo reporta conteos.
    """
    pref = (prefijo or "BEST").strip() or "BEST"
    patron_nro = f"{pref}-%"

    resultado: dict[str, Any] = {
        "dry_run": dry_run,
        "pedidos_revisados": 0,
        "ya_ok": 0,
        "insertados": 0,
        "actualizados": 0,
        "omitidos_sin_domicilio": 0,
        "errores": [],
        "detalle_omitidos": [],
        "detalle_escritos": [],
    }

    with get_connection(base_empresa) as conn:
        try:
            conn.autocommit(False)
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            cur.execute(_SQL_PEDIDOS, [patron_nro])
            pedidos = list(cur.fetchall())

            for row in pedidos:
                resultado["pedidos_revisados"] += 1
                cod_mov = to_int_or_none(row.get("cod_mov"))
                nro = str(row.get("nro_comprobante") or "").strip()
                id_cliente = to_int_or_none(row.get("id_cliente"))

                if cod_mov is None or id_cliente is None:
                    resultado["errores"].append(
                        f"{nro or '?'}: CodigoMovimiento o cliente inválido."
                    )
                    continue

                if _tiene_cda_ok(row):
                    resultado["ya_ok"] += 1
                    continue

                try:
                    id_domicilio = _buscar_primer_domicilio(cur, id_cliente)
                except Exception as exc:
                    logger.exception(
                        "Error buscando domicilio para PED %s (cliente %s)",
                        nro,
                        id_cliente,
                    )
                    resultado["errores"].append(f"{nro}: domicilio — {exc}")
                    continue

                if id_domicilio is None or id_domicilio <= 0:
                    resultado["omitidos_sin_domicilio"] += 1
                    if len(resultado["detalle_omitidos"]) < _DETALLE_OMITIDOS_MAX:
                        resultado["detalle_omitidos"].append(
                            {
                                "nro_comprobante": nro,
                                "cod_mov": cod_mov,
                                "id_cliente": id_cliente,
                            }
                        )
                    continue

                fecha_entrega = _resolver_fecha_entrega(row)
                id_deposito = _resolver_deposito(row)
                tiene_cda = bool(to_int_or_none(row.get("tiene_cda")))

                if dry_run:
                    if tiene_cda:
                        resultado["actualizados"] += 1
                    else:
                        resultado["insertados"] += 1
                    if len(resultado["detalle_escritos"]) < _DETALLE_ESCRITOS_MAX:
                        resultado["detalle_escritos"].append(
                            {
                                "nro_comprobante": nro,
                                "cod_mov": cod_mov,
                                "id_domicilio": id_domicilio,
                                "accion": "update" if tiene_cda else "insert",
                            }
                        )
                    continue

                try:
                    if tiene_cda:
                        # fecha, dep, id_cliente, id_domicilio, WHERE cod_mov
                        cur.execute(
                            _SQL_UPDATE_CDA,
                            (
                                fecha_entrega,
                                id_deposito,
                                id_cliente,
                                id_domicilio,
                                cod_mov,
                            ),
                        )
                        resultado["actualizados"] += 1
                        accion = "update"
                    else:
                        # fecha, dep, id_cliente, CodigoMovimiento, id_domicilio
                        cur.execute(
                            _SQL_INSERT_CDA,
                            (
                                fecha_entrega,
                                id_deposito,
                                id_cliente,
                                cod_mov,
                                id_domicilio,
                            ),
                        )
                        resultado["insertados"] += 1
                        accion = "insert"

                    if len(resultado["detalle_escritos"]) < _DETALLE_ESCRITOS_MAX:
                        resultado["detalle_escritos"].append(
                            {
                                "nro_comprobante": nro,
                                "cod_mov": cod_mov,
                                "id_domicilio": id_domicilio,
                                "accion": accion,
                            }
                        )
                except Exception as exc:
                    logger.exception(
                        "Error escribiendo CDA para PED %s (cod_mov=%s)",
                        nro,
                        cod_mov,
                    )
                    resultado["errores"].append(f"{nro}: escritura — {exc}")

            if dry_run:
                conn.rollback()
            else:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                conn.autocommit(True)
            except Exception:
                pass

    return resultado
