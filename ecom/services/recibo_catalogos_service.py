"""
Catálogos y consultas auxiliares para alta de recibo (paridad json_recibo.php).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict, List

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none


def _serializar_punto_venta(row: Any) -> Dict[str, Any]:
    """Normaliza filas de cursores MySQL con o sin diccionario."""
    if isinstance(row, Mapping):
        id_punto_venta = row.get("id_punto_venta")
        nro_punto_venta = row.get("nro_punto_venta")
        cont = row.get("cont")
    else:
        id_punto_venta, nro_punto_venta, cont = row[0], row[1], row[2]

    id_punto_venta = int(id_punto_venta)
    nro_punto_venta = int(nro_punto_venta)
    cont = cont or "no"
    return {
        "id_punto_venta": id_punto_venta,
        "nro_punto_venta": nro_punto_venta,
        "cont": cont,
        "value": f"{id_punto_venta}|{nro_punto_venta}|{cont}",
        "label": str(nro_punto_venta).zfill(4),
    }


def listar_puntos_venta_usuario(base_empresa: str, session_user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """PV disponibles para el usuario (fallback: PV asignado en sesión)."""
    id_usuario = to_int_or_none(session_user.get("id_usuario"))
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        if id_usuario:
            c.execute(
                """
                SELECT DISTINCT pv.id_punto_venta, pv.nro_punto_venta, pv.cont
                FROM punto_venta pv
                INNER JOIN usuarios u ON u.id_punto_venta = pv.id_punto_venta
                WHERE u.id_usuario = %s
                ORDER BY pv.nro_punto_venta
                """,
                [id_usuario],
            )
            rows = c.fetchall() or []
            if rows:
                return [_serializar_punto_venta(row) for row in rows]
        id_pv = to_int_or_none(session_user.get("id_punto_venta"))
        if id_pv:
            c.execute(
                """
                SELECT id_punto_venta, nro_punto_venta, cont
                FROM punto_venta WHERE id_punto_venta = %s LIMIT 1
                """,
                [id_pv],
            )
            r = c.fetchone()
            if r:
                return [_serializar_punto_venta(r)]
    return []


def traer_cotizacion_dolar(base_empresa: str) -> float:
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        c.execute("SELECT ValorPesos AS valor FROM cotizacion LIMIT 1")
        row = c.fetchone()
        return float(row["valor"]) if row and row.get("valor") is not None else 1.0


def traer_saldo_a_cuenta_cliente(base_empresa: str, cod_cliente: int) -> Dict[str, Any]:
    """Paridad ``trae_recibos_a_cuenta``."""
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT COALESCE(SUM(rc.Saldo), 0) AS aCuenta
            FROM recibo_factura AS rc
            WHERE rc.Codigo = %s
              AND rc.Estado = 'N/Canc'
              AND rc.Saldo <> 0
              AND rc.TipoComprobante IN (
                'REC','NCA','NCM','NCE','NCC','NCB','AJC','INIC'
              )
              AND rc.Anulado = 'No'
            """,
            [cod_cliente],
        )
        row = c.fetchone()
        saldo = float(row["aCuenta"] or 0) if row else 0.0
    return {"msg": "ok", "acuenta": saldo}


def listar_tipos_retencion(base_empresa: str) -> List[Dict[str, Any]]:
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT CodRetencion AS id, NombreRetencion AS text
            FROM tipo_retencion_cli
            WHERE Anulado = 'No'
            ORDER BY NombreRetencion
            """
        )
        return list(c.fetchall() or [])


def listar_cuentas_bancarias(base_empresa: str) -> List[Dict[str, Any]]:
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT
              CONCAT(cb.CodBanco, '|', cb.id_cuentabancaria) AS id,
              CONCAT(b.NombreBanco, ' | ', cb.NroCuenta) AS text,
              cb.NroCuenta AS numero_cuenta,
              b.NombreBanco AS banco
            FROM cuentabancaria cb
            LEFT JOIN bancos b ON b.CodBanco = cb.CodBanco
            WHERE cb.Anulado = 'No'
            ORDER BY b.NombreBanco, cb.NroCuenta
            """
        )
        return list(c.fetchall() or [])


def listar_tarjetas(base_empresa: str, tipo_tarjeta: str = "Credito") -> List[Dict[str, Any]]:
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT CONCAT(tj.idTC, '|', tj.id_pc) AS id, tj.nombre AS text
            FROM tarjetas_credito AS tj
            WHERE tj.Anulado = 'No' AND tj.tipo_tarjeta = %s
            ORDER BY tj.nombre
            """,
            [tipo_tarjeta],
        )
        return list(c.fetchall() or [])


def listar_planes_tarjeta(base_empresa: str, id_tc: int) -> List[Dict[str, Any]]:
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT ROUND(Id_tc_plan) AS id,
                   cuotas_tc_plan_desde AS min,
                   cuotas_tc_plan_hasta AS max,
                   nombre_tc_plan AS text
            FROM tc_plan
            WHERE anulado = 'No' AND idTC = %s
            ORDER BY nombre_tc_plan
            """,
            [id_tc],
        )
        return list(c.fetchall() or [])


def traer_caja_efectivo_usuario(base_empresa: str, session_user: Dict[str, Any]) -> List[Dict[str, Any]]:
    id_caja = to_int_or_none(session_user.get("id_caja") or session_user.get("id_caja_efectivo_usr"))
    if not id_caja:
        return []
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT id_caja AS id, nombre_caja AS text
            FROM caja_abm WHERE id_caja = %s
            """,
            [id_caja],
        )
        row = c.fetchone()
        return [row] if row else []
