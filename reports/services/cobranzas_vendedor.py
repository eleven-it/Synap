"""
Servicio — Informe "Cobranzas por vendedor" (paridad mayoristapp
``listado-cobranzas-vendedor.php`` + ``informes-json/cobranza_lista_vendedor_resumen.php``).

Resume por período (mensual o totalizado) los cobros de ``cuentacliente``
(recibos ``REC`` y ventas de contado) desglosados por medio de pago:
efectivo, dólares, cheques, transferencias, percepciones y total.

Reglas de proyecto:
- SQL 100% parametrizado (``cursor.execute(sql, params)``); nunca concatenar
  fechas ni ``CodViajante``.
- ``CodViajante`` normalizado a ``int`` antes de armar cláusulas ``IN``.
- Conexión legacy vía ``core.mysql_pool`` (mismo patrón que
  ``reports/services/clientes_sin_ventas.py``).
- Montos calculados con ``Decimal`` (sin float en los agregados).
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from core.utils.administranet_types import to_date_or_none, to_decimal_or_none, to_int_or_none
from reports.services.connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)

# Comprobantes considerados cobranza (paridad PHP).
TIPOS_COBRANZA = ("REC", "FA", "FB", "FM", "FE", "FC")

COLUMNS: List[Dict[str, str]] = [
    {"title": "Período", "data": "periodo"},
    {"title": "Efectivo", "data": "efectivo"},
    {"title": "Dólares", "data": "dolar"},
    {"title": "Cheques", "data": "cheque"},
    {"title": "Transferencias", "data": "transferencia"},
    {"title": "Percepciones", "data": "percepcion"},
    {"title": "Total", "data": "total"},
]

MESES_ES: Dict[int, str] = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

MODO_MES = "mes"
MODO_TOTALIZADO = "totalizado"

# Claves numéricas de cada renglón (para acumular el pie).
_CAMPOS_MONTO = ("efectivo", "dolar", "cheque", "transferencia", "percepcion", "total")


def _clausula_in(column: str, ids: Sequence[int]) -> tuple[str, List[int]]:
    """Devuelve (fragmento SQL parametrizado, params) para ``column IN (...)``."""
    ids_int = [int(i) for i in ids]
    placeholders = ", ".join(["%s"] * len(ids_int))
    return (f" AND {column} IN ({placeholders})", ids_int)


def _dec(value: Any) -> Decimal:
    """Monto a Decimal; None/vacío/no numérico → 0."""
    d = to_decimal_or_none(value)
    return d if d is not None else Decimal("0")


def _fmt_ddmmaaaa(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.strftime("%d/%m/%Y")
    iso = to_date_or_none(value)
    if not iso:
        return str(value)
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(value)


def _normalizar_modo(modo: Any) -> str:
    m = str(modo or "").strip().lower()
    if m in ("1", "totalizado", "total"):
        return MODO_TOTALIZADO
    return MODO_MES


def get_cobranzas_vendedor(
    base_empresa: str,
    *,
    fecha_desde: Any,
    fecha_hasta: Any,
    cod_viajantes: Optional[Sequence[int]] = None,
    modo: Any = MODO_MES,
) -> Dict[str, Any]:
    """
    Devuelve el resumen de cobranzas por período.

    ``cod_viajantes``: lista no vacía = restringe a esos ``CodViajante`` (``IN``);
    ``None``/vacía = sin restricción (gerencial "todos"). La vista relay resuelve
    permisos y anti-bypass.

    ``modo``: ``"mes"`` (una fila por mes) o ``"totalizado"`` (una fila por rango).
    """
    desde = to_date_or_none(fecha_desde)
    hasta = to_date_or_none(fecha_hasta)
    if not desde or not hasta:
        raise ValueError("fecha_desde y fecha_hasta son obligatorias (YYYY-MM-DD).")

    modo = _normalizar_modo(modo)

    where_vendedor = ""
    where_params: List[Any] = []
    if cod_viajantes:
        frag, ids = _clausula_in("cuentacliente.CodViajante", cod_viajantes)
        where_vendedor = frag
        where_params = ids

    tipos_ph = ", ".join(["%s"] * len(TIPOS_COBRANZA))

    sumas = (
        "SUM(CASE WHEN cuentacliente.TipoComprobante='REC' "
        "THEN cuentacliente.TotalEfectivoP ELSE cuentacliente.ImporteVenta END) AS totalEfectivo, "
        "SUM(cuentacliente.TotalEfectivoD) AS totalDolar, "
        "SUM(cuentacliente.TotalCheque) AS totalCheque, "
        "SUM(cuentacliente.total_trans) AS totalTransferencia, "
        "SUM(cuentacliente.total_percep) AS totalPercep, "
        "SUM(CASE WHEN cuentacliente.TipoComprobante='REC' "
        "THEN cuentacliente.ImporteCobro ELSE cuentacliente.ImporteVenta END) AS total"
    )

    where_comun = (
        f"cuentacliente.TipoComprobante IN ({tipos_ph}) "
        "AND (cuentacliente.Fecha BETWEEN %s AND %s) "
        "AND (cuentacliente.CodigoMovimiento <> 0) "
        "AND (cuentacliente.Anulado = 'No') "
        "AND (cuentacliente.CondVenta = 'Contado' OR cuentacliente.CondVenta = '-')"
        f"{where_vendedor}"
    )
    params: List[Any] = [*TIPOS_COBRANZA, desde, hasta, *where_params]

    if modo == MODO_MES:
        sql = (
            "SELECT YEAR(cuentacliente.Fecha) AS aaaa, MONTH(cuentacliente.Fecha) AS m, "
            f"{sumas} FROM cuentacliente WHERE {where_comun} "
            "GROUP BY YEAR(cuentacliente.Fecha), MONTH(cuentacliente.Fecha) "
            "ORDER BY aaaa ASC, m ASC"
        )
    else:
        sql = f"SELECT {sumas} FROM cuentacliente WHERE {where_comun}"

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        colnames = [d[0] for d in cursor.description] if cursor.description else []

    filas = _armar_filas(rows, colnames, modo, desde, hasta)
    totales = _armar_totales(filas)

    return {
        "columns": COLUMNS,
        "modo": modo,
        "filas": filas,
        "totales": totales,
    }


def _armar_filas(
    rows: Sequence[Sequence[Any]],
    colnames: Sequence[str],
    modo: str,
    desde: str,
    hasta: str,
) -> List[Dict[str, Any]]:
    filas: List[Dict[str, Any]] = []
    etiqueta_total = f"{_fmt_ddmmaaaa(desde)} al {_fmt_ddmmaaaa(hasta)}"

    for row in rows:
        item = dict(zip(colnames, row))
        efectivo = _dec(item.get("totalEfectivo"))
        dolar = _dec(item.get("totalDolar"))
        cheque = _dec(item.get("totalCheque"))
        transferencia = _dec(item.get("totalTransferencia"))
        percepcion = _dec(item.get("totalPercep"))
        total = _dec(item.get("total"))

        if modo == MODO_MES:
            m = to_int_or_none(item.get("m")) or 0
            aaaa = to_int_or_none(item.get("aaaa")) or 0
            periodo = f"{MESES_ES.get(m, '?')} {aaaa}"
            orden = f"{aaaa:04d}{m:02d}"
        else:
            periodo = etiqueta_total
            orden = "1"
            # En totalizado sin filas (sin datos) MySQL devuelve una fila con NULLs;
            # se conserva igualmente para mostrar ceros.

        filas.append(
            {
                "periodo": periodo,
                "ordenPeriodo": orden,
                "efectivo": float(efectivo),
                "dolar": float(dolar),
                "cheque": float(cheque),
                "transferencia": float(transferencia),
                "percepcion": float(percepcion),
                "total": float(total),
            }
        )

    # En totalizado, si no hubo comprobantes MySQL igual devuelve 1 fila de NULLs
    # (total=0); la descartamos para no mostrar un renglón vacío.
    if modo == MODO_TOTALIZADO:
        filas = [f for f in filas if any(f[c] for c in _CAMPOS_MONTO)]

    return filas


def _armar_totales(filas: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    acum: Dict[str, Decimal] = {c: Decimal("0") for c in _CAMPOS_MONTO}
    for fila in filas:
        for c in _CAMPOS_MONTO:
            acum[c] += Decimal(str(fila.get(c, 0)))
    salida: Dict[str, Any] = {"periodo": "Total Gral"}
    salida.update({c: float(acum[c]) for c in _CAMPOS_MONTO})
    return salida
