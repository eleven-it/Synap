"""Kardex artículo MPR: movimiento_stock OPP/OPA por depósito (extraído de services.py por tamaño)."""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_int_or_none,
)

logger = logging.getLogger(__name__)

ClasificacionKardex = Literal["entrada", "salida", "ignorar"]

MOTIVO_PARTE_PRODUCCION = "Parte producción"

_RE_UUID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_RE_DETALLE_OPP_PARTE_UUID = re.compile(
    r"OPP-parte\s+(" + _RE_UUID.pattern + r")\s+desde\s+MPR",
    re.IGNORECASE,
)

# Keywords LIKE sobre movimiento_stock.motivo_movimiento (LOWER … LIKE %kw%).
MOTIVOS_MSTOCK_MOTIVO_LIKE_KEYWORDS = (
    "faltante",
    "sobrante",
    "inventario",
    "conteo",
    "stock inicial",
    "ajuste",
    "rotura",
    "transferencia",
    "mov. interno",
    "desarmado",
)

MOTIVOS_INVENTARIO_KEYWORDS = ("faltante", "sobrante", "inventario", "conteo")

MOTIVOS_STOCK_INICIAL_KEYWORDS = ("stock inicial",)

MOTIVOS_AJUSTE_DEPOSITO_KEYWORDS = (
    "ajuste",
    "rotura",
    "transferencia",
    "mov. interno",
    "desarmado",
)

# Valores exactos LOWER para stock.TipoComp IN (…).
MOTIVOS_MSTOCK_TIPOCOMP_INVENTARIO = (
    "faltante",
    "sobrante",
    "inventario",
    "ajuste inventario",
    "conteo",
)
MOTIVOS_MSTOCK_TIPOCOMP_STOCK_INICIAL = ("stock inicial",)
MOTIVOS_MSTOCK_TIPOCOMP_AJUSTE = (
    "ajuste",
    "rotura",
    "transferencia",
    "mov. interno salida",
    "mov. interno entrada",
    "desarmado",
)
MOTIVOS_MSTOCK_TIPOCOMP_DEPOSITO = (
    *MOTIVOS_MSTOCK_TIPOCOMP_INVENTARIO,
    *MOTIVOS_MSTOCK_TIPOCOMP_STOCK_INICIAL,
    *MOTIVOS_MSTOCK_TIPOCOMP_AJUSTE,
)

PRIORIDAD_FUENTE_DEDUPE = {
    "mstock": 0,
    "stock": 1,
    "mpr_parte": 2,
    "mpr_envio": 3,
    "mpr_clasificacion": 4,
}


def _clausula_filtro_depositos(
    *,
    id_deposito: Optional[int] = None,
    ids_deposito: Optional[List[int]] = None,
    alias: str = "s",
) -> tuple[str, List[Any]]:
    """Fragmento SQL ``AND alias.CodDeposito …`` para un depósito o lista (pipeline)."""
    dep = to_int_or_none(id_deposito)
    if dep is not None:
        return f" AND {alias}.CodDeposito = %s", [dep]
    ids = [d for d in (to_int_or_none(x) for x in (ids_deposito or [])) if d is not None]
    if ids:
        placeholders = ",".join(["%s"] * len(ids))
        return f" AND {alias}.CodDeposito IN ({placeholders})", ids
    return "", []


def _afecta_deposito_terminado(comprobante: Optional[str]) -> bool:
    """FA se lista pero no mueve saldo corrido Terminado (paridad _gen_kardex_610_t6)."""
    return (comprobante or "").upper() != "FA"


def _es_motivo_inventario(
    motivo_movimiento: Optional[str],
    tipo_comp: Optional[str] = None,
) -> bool:
    motivo = (motivo_movimiento or "").strip().lower()
    if any(kw in motivo for kw in MOTIVOS_INVENTARIO_KEYWORDS):
        return True
    tipo = (tipo_comp or "").strip().lower()
    return tipo in (
        "faltante",
        "sobrante",
        "inventario",
        "ajuste inventario",
        "conteo",
    )


def _es_motivo_stock_inicial(
    motivo_movimiento: Optional[str],
    tipo_comp: Optional[str] = None,
) -> bool:
    motivo = (motivo_movimiento or "").strip().lower()
    if any(kw in motivo for kw in MOTIVOS_STOCK_INICIAL_KEYWORDS):
        return True
    return (tipo_comp or "").strip().lower() in MOTIVOS_MSTOCK_TIPOCOMP_STOCK_INICIAL


def _es_motivo_ajuste_deposito(
    motivo_movimiento: Optional[str],
    tipo_comp: Optional[str] = None,
) -> bool:
    """Ajuste, rotura, transferencia, mov. interno o desarmado (no inventario/conteo)."""
    motivo = (motivo_movimiento or "").strip().lower()
    if _es_motivo_inventario(motivo_movimiento, tipo_comp):
        return False
    if _es_motivo_stock_inicial(motivo_movimiento, tipo_comp):
        return False
    if any(kw in motivo for kw in MOTIVOS_AJUSTE_DEPOSITO_KEYWORDS):
        return True
    tipo = (tipo_comp or "").strip().lower()
    return tipo in MOTIVOS_MSTOCK_TIPOCOMP_AJUSTE


def _es_motivo_ingreso_deposito(
    motivo_movimiento: Optional[str],
    tipo_comp: Optional[str] = None,
) -> bool:
    """MSTOCK ingreso que mueve stock en el eje (tipo_mov vacío típico)."""
    return (
        _es_motivo_stock_inicial(motivo_movimiento, tipo_comp)
        or _es_motivo_inventario(motivo_movimiento, tipo_comp)
        or _es_motivo_ajuste_deposito(motivo_movimiento, tipo_comp)
    )


def _clasificar_movimiento_analisis(
    *,
    tipo_mov: Optional[str],
    motivo_movimiento: Optional[str],
    comprobante: Optional[str] = None,
    tipo_comp: Optional[str] = None,
    fuente: str = "mstock",
) -> tuple[str, bool]:
    """Extiende clasificación kardex → opa|opp|rem|fa|inventario|mpr_*."""
    comp = (comprobante or "").strip().upper()
    tipo = (tipo_mov or "").strip().upper()

    if comp in ("REM", "FA"):
        clase = "rem" if comp == "REM" else "fa"
        return clase, _afecta_deposito_terminado(comp)

    if fuente.startswith("mpr_"):
        return fuente.replace("mpr_", "mpr_"), True

    if _es_motivo_stock_inicial(motivo_movimiento, tipo_comp):
        return "stock_inicial", True

    if _es_motivo_inventario(motivo_movimiento, tipo_comp):
        return "inventario", True

    if _es_motivo_ajuste_deposito(motivo_movimiento, tipo_comp):
        return "ajuste", True

    clasif = _clasificar_movimiento_kardex(tipo_mov, motivo_movimiento)
    if clasif == "entrada":
        if tipo in ("OPA", "ARMADO"):
            return "opa", True
        return "opp", True
    if clasif == "salida":
        if tipo in ("OPA", "ARMADO"):
            return "opa", True
        return "opp", True
    return "otro", True


def _clasificar_movimiento_kardex(
    tipo_mov: Optional[str],
    motivo_movimiento: Optional[str],
) -> ClasificacionKardex:
    """Clasifica movimiento MSTOCK para kardex: OPP/legacy → entrada, OPA/ARMADO → salida."""
    tipo = (tipo_mov or "").strip().upper()
    motivo = (motivo_movimiento or "").strip()

    if tipo == "OPT":
        return "ignorar"
    if tipo == "OPP" or motivo == MOTIVO_PARTE_PRODUCCION:
        return "entrada"
    if tipo in ("OPA", "ARMADO"):
        return "salida"
    return "ignorar"


def _fmt_fecha_display_kardex(value: Any) -> str:
    """Fecha dd/MM/yyyy para UI kardex."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    parsed = to_date_or_none(value)
    if parsed:
        try:
            dt = datetime.strptime(str(parsed)[:10], "%Y-%m-%d").date()
            return dt.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            pass
    return str_or_default(value, "")


def _calcular_saldo_corrido_movimientos(
    movimientos: List[Dict[str, Any]],
    *,
    saldo_inicial: int = 0,
) -> List[Dict[str, Any]]:
    """Acumula saldo_corrido fila a fila (Σ entradas − Σ salidas desde saldo_inicial)."""
    saldo = int(saldo_inicial)
    resultado: List[Dict[str, Any]] = []
    for mov in movimientos or []:
        entrada = int(to_int_or_none(mov.get("entrada")) or 0)
        salida = int(to_int_or_none(mov.get("salida")) or 0)
        saldo += entrada - salida
        fila = dict(mov)
        fila["saldo_corrido"] = saldo
        resultado.append(fila)
    return resultado


def _consultar_movimientos_kardex_articulo(
    base_empresa: str,
    id_articulo: int,
    *,
    id_deposito: Optional[int] = None,
    ids_deposito: Optional[List[int]] = None,
    fecha_desde: Optional[Any] = None,
    fecha_hasta: Optional[Any] = None,
    limit: int = 500,
    desglosar_por_deposito: bool = False,
) -> List[Dict[str, Any]]:
    """Filas crudas de movimiento_stock+stock para kardex (sin saldo corrido)."""
    from mpr.services import _nombre_tabla

    id_art = to_int_or_none(id_articulo)
    if not (base_empresa or "").strip() or id_art is None:
        return []

    lim = max(1, min(int(limit or 500), 5000))
    params: List[Any] = [id_art, MOTIVO_PARTE_PRODUCCION]
    filtros_extra = ""
    clausula_dep, params_dep = _clausula_filtro_depositos(
        id_deposito=id_deposito,
        ids_deposito=ids_deposito,
    )
    filtros_extra += clausula_dep
    params.extend(params_dep)

    fd = to_date_or_none(fecha_desde)
    fh = to_date_or_none(fecha_hasta)
    if fd:
        filtros_extra += " AND m.fecha >= %s"
        params.append(fd)
    if fh:
        filtros_extra += " AND m.fecha <= %s"
        params.append(fh)

    params.append(lim)

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            if not tbl_mov or not tbl_stock:
                return []
            col_dep = ", s.CodDeposito AS cod_deposito" if desglosar_por_deposito else ""
            grp_dep = ", s.CodDeposito" if desglosar_por_deposito else ""
            ord_dep = ", s.CodDeposito ASC" if desglosar_por_deposito else ""
            cursor.execute(
                f"""
                SELECT
                    m.codigo_movimiento,
                    m.fecha,
                    m.tipo_mov,
                    m.motivo_movimiento,
                    m.nro_comprobante,
                    m.detalle,
                    m.id_operario_opt,
                    COALESCE(SUM(s.Entrada), 0) AS total_entrada,
                    COALESCE(SUM(s.Salida), 0) AS total_salida{col_dep}
                FROM {tbl_mov} m
                INNER JOIN {tbl_stock} s ON s.CodigoMovimiento = m.codigo_movimiento
                WHERE s.IDArt = %s
                  AND COALESCE(m.anulado, 'No') <> 'Si'
                  AND UPPER(TRIM(COALESCE(m.tipo_comprobante, ''))) = 'MSTOCK'
                  AND (
                    UPPER(TRIM(COALESCE(m.tipo_mov, ''))) = 'OPP'
                    OR COALESCE(m.motivo_movimiento, '') = %s
                    OR UPPER(TRIM(COALESCE(m.tipo_mov, ''))) IN ('OPA', 'ARMADO')
                  )
                  AND UPPER(TRIM(COALESCE(m.tipo_mov, ''))) <> 'OPT'
                  {filtros_extra}
                GROUP BY
                    m.codigo_movimiento, m.fecha, m.tipo_mov, m.motivo_movimiento,
                    m.nro_comprobante, m.detalle, m.id_operario_opt{grp_dep}
                ORDER BY m.fecha ASC, m.codigo_movimiento ASC{ord_dep}
                LIMIT %s
                """,
                params,
            )
            return list(cursor.fetchall() or [])
    except Exception as exc:
        logger.warning(
            "_consultar_movimientos_kardex_articulo error base=%s art=%s: %s",
            base_empresa,
            id_articulo,
            exc,
            exc_info=True,
        )
        return []


def _fetch_nombre_deposito(base_empresa: str, id_deposito: int) -> str:
    from mpr.services import _nombre_tabla

    dep = to_int_or_none(id_deposito)
    if not dep or not (base_empresa or "").strip():
        return "-"
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "deposito")
            if not tbl:
                return "-"
            cursor.execute(
                f"SELECT COALESCE(NombreDeposito, '') AS nombre FROM {tbl} WHERE CodDeposito = %s LIMIT 1",
                [dep],
            )
            row = cursor.fetchone()
            return str_or_default(row.get("nombre") if row else None, "-")
    except Exception:
        return "-"


def _extraer_cod_deposito(row: Dict[str, Any]) -> Optional[int]:
    """Extrae el depósito tolerando variantes de nombre devueltas por MySQL."""
    for clave in ("cod_deposito", "CodDeposito", "CODDEPOSITO", "codDeposito"):
        if row.get(clave) is not None:
            return to_int_or_none(row.get(clave))
    return None


def _normalizar_fila_kardex(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convierte fila SQL a movimiento kardex con entrada/salida según clasificación.

    OPP:
    - producción nueva: suele tener solo ``Entrada``;
    - transferencia interna del pipeline: tiene ``Salida`` en origen y ``Entrada``
      en destino bajo el mismo movimiento. Se conservan ambos lados para que
      netee cero al consolidar varios depósitos.

    OPA/ARMADO:
    - componente: suele tener ``Salida`` (egreso de Semi);
    - pack terminado: suele tener ``Entrada`` (ingreso a Terminado).
    Se usa el sentido de stock real del renglón para no dejar cantidad 0 en packs.
    """
    clasif = _clasificar_movimiento_kardex(
        row.get("tipo_mov"),
        row.get("motivo_movimiento"),
    )
    if clasif == "ignorar":
        return None

    total_entrada = int(float(row.get("total_entrada") or 0))
    total_salida = int(float(row.get("total_salida") or 0))
    if clasif == "entrada":
        entrada, salida = total_entrada, total_salida
    elif total_salida > 0:
        entrada, salida = 0, total_salida
    elif total_entrada > 0:
        # Pack terminado: armado acredita el pack (Entrada).
        entrada, salida = total_entrada, 0
    else:
        entrada, salida = 0, 0

    cod_mov = to_int_or_none(row.get("codigo_movimiento"))
    operario_id = to_int_or_none(row.get("id_operario_opt"))
    mov = {
        "fecha_display": _fmt_fecha_display_kardex(row.get("fecha")),
        "tipo_mov": str_or_default(row.get("tipo_mov"), "-"),
        "entrada": entrada,
        "salida": salida,
        "codigo_movimiento": cod_mov,
        "nro_comprobante": str_or_default(row.get("nro_comprobante"), "-"),
        "detalle": str_or_default(row.get("detalle"), ""),
        "operario": str(operario_id) if operario_id is not None else "-",
    }
    cod_deposito = _extraer_cod_deposito(row)
    if cod_deposito is not None:
        mov["cod_deposito"] = cod_deposito
    return mov


def _consultar_movimientos_stock_rem_fa(
    base_empresa: str,
    id_articulo: int,
    *,
    id_deposito: Optional[int] = None,
    ids_deposito: Optional[List[int]] = None,
    fecha_desde: Optional[Any] = None,
    fecha_hasta: Optional[Any] = None,
    limit: int = 500,
    desglosar_por_deposito: bool = False,
) -> List[Dict[str, Any]]:
    """REM/FA directos en tabla stock (no MSTOCK)."""
    from mpr.services import _nombre_tabla

    id_art = to_int_or_none(id_articulo)
    if not (base_empresa or "").strip() or id_art is None:
        return []

    lim = max(1, min(int(limit or 500), 5000))
    params: List[Any] = [id_art]
    filtros_extra = ""
    clausula_dep, params_dep = _clausula_filtro_depositos(
        id_deposito=id_deposito,
        ids_deposito=ids_deposito,
    )
    filtros_extra += clausula_dep
    params.extend(params_dep)

    fd = to_date_or_none(fecha_desde)
    fh = to_date_or_none(fecha_hasta)
    if fd:
        filtros_extra += " AND COALESCE(s.FechaControl, CAST(s.Fecha AS DATETIME)) >= %s"
        params.append(fd)
    if fh:
        filtros_extra += " AND COALESCE(s.FechaControl, CAST(s.Fecha AS DATETIME)) <= %s"
        params.append(f"{fh} 23:59:59")

    params.append(lim)

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_stock = _nombre_tabla(cursor, "stock")
            if not tbl_stock:
                return []
            col_dep = ", s.CodDeposito AS cod_deposito" if desglosar_por_deposito else ""
            grp_dep = ", s.CodDeposito" if desglosar_por_deposito else ""
            ord_dep = ", s.CodDeposito ASC" if desglosar_por_deposito else ""
            cursor.execute(
                f"""
                SELECT
                    s.CodigoMovimiento AS codigo_movimiento,
                    COALESCE(s.FechaControl, CAST(s.Fecha AS DATETIME)) AS fecha,
                    s.Comprobante AS comprobante,
                    s.Comprobante AS tipo_mov,
                    s.NroComprobante AS nro_comprobante,
                    COALESCE(s.Descripcion, '') AS detalle,
                    s.TipoComp AS tipo_comp,
                    COALESCE(SUM(s.Entrada), 0) AS total_entrada,
                    COALESCE(SUM(s.Salida), 0) AS total_salida{col_dep}
                FROM {tbl_stock} s
                WHERE s.IDArt = %s
                  AND s.Comprobante IN ('REM', 'FA')
                  AND COALESCE(s.Anulado, 'No') <> 'Si'
                  {filtros_extra}
                GROUP BY
                    s.CodigoMovimiento, s.Fecha, s.FechaControl,
                    s.Comprobante, s.NroComprobante, s.Descripcion, s.TipoComp{grp_dep}
                ORDER BY COALESCE(s.FechaControl, CAST(s.Fecha AS DATETIME)) ASC,
                         s.CodigoMovimiento ASC{ord_dep}
                LIMIT %s
                """,
                params,
            )
            rows = list(cursor.fetchall() or [])
            for row in rows:
                row["fuente"] = "stock"
            return rows
    except Exception as exc:
        logger.warning(
            "_consultar_movimientos_stock_rem_fa error base=%s art=%s: %s",
            base_empresa,
            id_articulo,
            exc,
            exc_info=True,
        )
        return []


def _consultar_movimientos_inventario_mstock(
    base_empresa: str,
    id_articulo: int,
    *,
    id_deposito: Optional[int] = None,
    ids_deposito: Optional[List[int]] = None,
    fecha_desde: Optional[Any] = None,
    fecha_hasta: Optional[Any] = None,
    limit: int = 500,
    desglosar_por_deposito: bool = False,
) -> List[Dict[str, Any]]:
    """MSTOCK ingreso depósito: inventario, stock inicial y ajustes por motivo o TipoComp."""
    from mpr.services import _nombre_tabla

    id_art = to_int_or_none(id_articulo)
    if not (base_empresa or "").strip() or id_art is None:
        return []

    lim = max(1, min(int(limit or 500), 5000))
    like_patterns = [f"%{kw}%" for kw in MOTIVOS_MSTOCK_MOTIVO_LIKE_KEYWORDS]
    # Orden MUST coincidir con los %s del SQL: IDArt, N× LIKE motivo, filtros, LIMIT.
    params: List[Any] = [id_art, *like_patterns]
    filtros_extra = ""
    clausula_dep, params_dep = _clausula_filtro_depositos(
        id_deposito=id_deposito,
        ids_deposito=ids_deposito,
    )
    filtros_extra += clausula_dep
    params.extend(params_dep)

    fd = to_date_or_none(fecha_desde)
    fh = to_date_or_none(fecha_hasta)
    if fd:
        filtros_extra += " AND COALESCE(s.FechaControl, CAST(m.fecha AS DATETIME)) >= %s"
        params.append(fd)
    if fh:
        filtros_extra += " AND COALESCE(s.FechaControl, CAST(m.fecha AS DATETIME)) <= %s"
        params.append(f"{fh} 23:59:59")

    params.append(lim)

    like_clauses = "\n                    OR ".join(
        ["LOWER(COALESCE(m.motivo_movimiento, '')) LIKE %s"] * len(like_patterns)
    )
    tipocomp_in = ", ".join([f"'{t}'" for t in MOTIVOS_MSTOCK_TIPOCOMP_DEPOSITO])

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            if not tbl_mov or not tbl_stock:
                return []
            col_dep = ", s.CodDeposito AS cod_deposito" if desglosar_por_deposito else ""
            grp_dep = ", s.CodDeposito" if desglosar_por_deposito else ""
            ord_dep = ", s.CodDeposito ASC" if desglosar_por_deposito else ""
            cursor.execute(
                f"""
                SELECT
                    m.codigo_movimiento,
                    COALESCE(s.FechaControl, CAST(m.fecha AS DATETIME)) AS fecha,
                    m.tipo_mov,
                    m.motivo_movimiento,
                    m.nro_comprobante,
                    m.detalle,
                    s.TipoComp AS tipo_comp,
                    s.Comprobante AS comprobante,
                    COALESCE(SUM(s.Entrada), 0) AS total_entrada,
                    COALESCE(SUM(s.Salida), 0) AS total_salida{col_dep}
                FROM {tbl_mov} m
                INNER JOIN {tbl_stock} s ON s.CodigoMovimiento = m.codigo_movimiento
                WHERE s.IDArt = %s
                  AND COALESCE(m.anulado, 'No') <> 'Si'
                  AND COALESCE(s.Anulado, 'No') <> 'Si'
                  AND UPPER(TRIM(COALESCE(m.tipo_comprobante, ''))) = 'MSTOCK'
                  AND UPPER(TRIM(COALESCE(m.tipo_mov, ''))) NOT IN ('OPP', 'OPA', 'ARMADO', 'OPT')
                  AND (
                    {like_clauses}
                    OR LOWER(COALESCE(s.TipoComp, '')) IN ({tipocomp_in})
                  )
                  {filtros_extra}
                GROUP BY
                    m.codigo_movimiento, m.fecha, m.tipo_mov, m.motivo_movimiento,
                    m.nro_comprobante, m.detalle, s.TipoComp, s.Comprobante, s.FechaControl{grp_dep}
                ORDER BY COALESCE(s.FechaControl, CAST(m.fecha AS DATETIME)) ASC,
                         m.codigo_movimiento ASC{ord_dep}
                LIMIT %s
                """,
                params,
            )
            rows = list(cursor.fetchall() or [])
            for row in rows:
                row["fuente"] = "mstock"
            return rows
    except Exception as exc:
        logger.warning(
            "_consultar_movimientos_inventario_mstock error base=%s art=%s: %s",
            base_empresa,
            id_articulo,
            exc,
            exc_info=True,
        )
        return []


def _consultar_eventos_mpr_articulo(
    base_empresa: str,
    id_articulo: int,
    *,
    fecha_desde: Optional[Any] = None,
    fecha_hasta: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Ledgers MPR (envío/parte/clasificación) para ancla timeline.

    MUST NOT reinyectar OPP/OPA MSTOCK: esos ya vienen de
    ``_consultar_movimientos_kardex_articulo`` (evita filas duplicadas mpr_opa+opa).
    """
    from mpr.services import reporte_mpr_trazabilidad_componente

    data = reporte_mpr_trazabilidad_componente(
        base_empresa,
        id_articulo,
        fecha_desde,
        fecha_hasta,
    )
    tipos_ledger = frozenset({"envio", "parte", "clasificacion"})
    eventos: List[Dict[str, Any]] = []
    for ev in data.get("eventos") or []:
        tipo = str_or_default(ev.get("tipo"), "").strip().lower()
        if tipo not in tipos_ledger:
            continue
        eventos.append({
            **ev,
            "fuente": f"mpr_{tipo}",
            "clase_ui": f"mpr_{tipo}",
        })
    return eventos


def _evento_mpr_a_movimiento(ev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convierte evento timeline MPR a fila unificada de movimientos."""
    cantidad = int(to_int_or_none(ev.get("cantidad")) or 0)
    if cantidad <= 0:
        return None
    sentido = str_or_default(ev.get("sentido"), "").strip().lower()
    tipo = str_or_default(ev.get("tipo"), "").strip().lower()
    if sentido == "salida" or tipo in ("opa",):
        entrada, salida = 0, cantidad
    else:
        entrada, salida = cantidad, 0
    ts = ev.get("fecha_sort")
    clase_ui = str_or_default(ev.get("clase_ui"), f"mpr_{tipo}" if tipo else "mpr")
    fuente = str_or_default(ev.get("fuente"), f"mpr_{tipo}" if tipo else "mpr_parte")
    if fuente == "mpr_parte" or tipo == "parte":
        fuente = "mpr_parte"
    return {
        "fecha_sort": ts,
        "fecha_display": str_or_default(ev.get("fecha_display"), _fmt_fecha_display_kardex(ts)),
        "tipo_mov": str_or_default(ev.get("tipo_label"), tipo.upper() or "-"),
        "entrada": entrada,
        "salida": salida,
        "codigo_movimiento": to_int_or_none(ev.get("codigo_movimiento")),
        "nro_comprobante": "-",
        "detalle": str_or_default(ev.get("detalle"), ""),
        "operario": str_or_default(ev.get("operario"), "-"),
        "clase_ui": clase_ui,
        "afecta_deposito": True,
        "fuente": fuente,
    }


def _normalizar_fila_analisis_stock(
    row: Dict[str, Any],
    *,
    fuente: str = "stock",
) -> Optional[Dict[str, Any]]:
    comprobante = str_or_default(row.get("comprobante"), "")
    tipo_mov = str_or_default(row.get("tipo_mov"), comprobante)
    clase_ui, afecta = _clasificar_movimiento_analisis(
        tipo_mov=tipo_mov,
        motivo_movimiento=row.get("motivo_movimiento"),
        comprobante=comprobante,
        tipo_comp=row.get("tipo_comp"),
        fuente=fuente,
    )
    total_entrada = int(float(row.get("total_entrada") or 0))
    total_salida = int(float(row.get("total_salida") or 0))
    if total_entrada <= 0 and total_salida <= 0:
        return None
    entrada = total_entrada if total_entrada > 0 else 0
    salida = total_salida if total_salida > 0 else 0
    if clase_ui == "opp" and entrada == 0 and salida == 0:
        entrada = max(total_entrada, total_salida)
    mov = {
        "fecha_sort": row.get("fecha"),
        "fecha_display": _fmt_fecha_display_kardex(row.get("fecha")),
        "tipo_mov": tipo_mov,
        "entrada": entrada,
        "salida": salida,
        "codigo_movimiento": to_int_or_none(row.get("codigo_movimiento")),
        "nro_comprobante": str_or_default(row.get("nro_comprobante"), "-"),
        "detalle": str_or_default(row.get("detalle"), ""),
        "operario": "-",
        "clase_ui": clase_ui,
        "afecta_deposito": afecta,
        "fuente": fuente,
    }
    cod_deposito = _extraer_cod_deposito(row)
    if cod_deposito is not None:
        mov["cod_deposito"] = cod_deposito
    return mov


def _normalizar_fila_analisis_mstock(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    fila_k = _normalizar_fila_kardex(row)
    if not fila_k:
        if _es_motivo_ingreso_deposito(row.get("motivo_movimiento"), row.get("tipo_comp")):
            return _normalizar_fila_analisis_stock(row, fuente="mstock")
        return None
    clase_ui, afecta = _clasificar_movimiento_analisis(
        tipo_mov=row.get("tipo_mov"),
        motivo_movimiento=row.get("motivo_movimiento"),
        comprobante=row.get("comprobante") or "MSTOCK",
        tipo_comp=row.get("tipo_comp"),
        fuente=str_or_default(row.get("fuente"), "mstock"),
    )
    mov = {
        **fila_k,
        "fecha_sort": row.get("fecha"),
        "clase_ui": clase_ui,
        "afecta_deposito": afecta,
        "fuente": str_or_default(row.get("fuente"), "mstock"),
    }
    cod_deposito = _extraer_cod_deposito(row)
    if cod_deposito is not None:
        mov["cod_deposito"] = cod_deposito
    return mov


def _mapa_deposito_etapa(etapas: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for et in etapas or []:
        dep = to_int_or_none(et.get("id_deposito"))
        if dep is not None:
            out[dep] = et
    return out


def _tipos_mpr_pipeline_desde_etapas(etapas: List[Dict[str, Any]]) -> List[str]:
    from mpr.services import TIPOS_MPR_PIPELINE_FABRICADOS

    presentes = {str(e.get("tipo_mpr") or "") for e in (etapas or [])}
    return [t for t in TIPOS_MPR_PIPELINE_FABRICADOS if t in presentes]


def _saldos_vacios_por_etapa(tipos: List[str]) -> Dict[str, int]:
    return {t: 0 for t in tipos}


def _enriquecer_impacto_etapa(
    mov: Dict[str, Any],
    mapa_dep: Dict[int, Dict[str, Any]],
    advertencias: List[str],
) -> Optional[Dict[str, Any]]:
    """Resuelve etapa por cod_deposito; descarta impactos fuera del mapa."""
    dep = to_int_or_none(mov.get("cod_deposito"))
    if dep is None:
        return mov
    et = mapa_dep.get(dep)
    if not et:
        advertencias.append(
            f"Impacto en depósito {dep} excluido del pipeline (no está en etapas activas)."
        )
        return None
    mov = dict(mov)
    mov["etapa"] = {
        "tipo_mpr": et.get("tipo_mpr"),
        "label": et.get("label"),
        "orden": et.get("orden"),
    }
    mov["etapa_label"] = str_or_default(et.get("label"), "")
    return mov


def _clave_dedupe_movimiento(mov: Dict[str, Any]) -> tuple:
    cod = to_int_or_none(mov.get("codigo_movimiento"))
    dep = to_int_or_none(mov.get("cod_deposito"))
    return (cod if cod is not None else -1, dep)


def _orden_impacto_sort_key(mov: Dict[str, Any]) -> tuple:
    etapa = mov.get("etapa") or {}
    return (
        str(mov.get("fecha_sort") or ""),
        to_int_or_none(mov.get("codigo_movimiento")) or 0,
        int(mov.get("orden_impacto") if mov.get("orden_impacto") is not None else 99),
        int(etapa.get("orden") if etapa.get("orden") is not None else 99),
        to_int_or_none(mov.get("cod_deposito")) or 0,
    )


def _deduplicar_movimientos(movimientos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clave (codigo_movimiento, cod_deposito); preferir MSTOCK sobre mpr_parte."""
    por_clave: Dict[tuple, Dict[str, Any]] = {}
    sin_codigo: List[Dict[str, Any]] = []
    for mov in movimientos or []:
        cod = to_int_or_none(mov.get("codigo_movimiento"))
        if cod is None:
            sin_codigo.append(mov)
            continue
        clave = _clave_dedupe_movimiento(mov)
        prev = por_clave.get(clave)
        if prev is None:
            por_clave[clave] = mov
            continue
        fuente_prev = str_or_default(prev.get("fuente"), "zz")
        fuente_new = str_or_default(mov.get("fuente"), "zz")
        rank_prev = PRIORIDAD_FUENTE_DEDUPE.get(fuente_prev, 99)
        rank_new = PRIORIDAD_FUENTE_DEDUPE.get(fuente_new, 99)
        if rank_new < rank_prev:
            por_clave[clave] = mov
    return sorted(list(por_clave.values()) + sin_codigo, key=_orden_impacto_sort_key)


def _marcar_transferencias_internas(
    movimientos: List[Dict[str, Any]],
    *,
    mapa_dep: Dict[int, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """OPP/transferencias entre depósitos pipeline: salida antes que entrada."""
    por_mov: Dict[int, List[Dict[str, Any]]] = {}
    for mov in movimientos or []:
        cod = to_int_or_none(mov.get("codigo_movimiento"))
        if cod is None:
            continue
        por_mov.setdefault(cod, []).append(mov)

    resultado: List[Dict[str, Any]] = []
    for mov in movimientos or []:
        fila = dict(mov)
        cod = to_int_or_none(fila.get("codigo_movimiento"))
        grupo = por_mov.get(cod or -1, [])
        deps = {
            to_int_or_none(m.get("cod_deposito"))
            for m in grupo
            if to_int_or_none(m.get("cod_deposito")) is not None
        }
        if len(deps) >= 2 and cod is not None:
            salida = int(fila.get("salida") or 0)
            entrada = int(fila.get("entrada") or 0)
            es_salida = salida > 0 and entrada <= 0
            es_entrada = entrada > 0 and salida <= 0
            fila["es_transferencia_interna"] = True
            fila["orden_impacto"] = 0 if es_salida else (1 if es_entrada else 0)
            contrapartes = [
                m for m in grupo
                if to_int_or_none(m.get("cod_deposito")) != to_int_or_none(fila.get("cod_deposito"))
            ]
            if contrapartes:
                otro = contrapartes[0]
                et_otro = (otro.get("etapa") or {})
                sentido = "salida" if es_salida else ("entrada" if es_entrada else "")
                fila["contraparte"] = {
                    "tipo_mpr": et_otro.get("tipo_mpr"),
                    "label": et_otro.get("label"),
                    "sentido": sentido,
                }
        else:
            fila.setdefault("es_transferencia_interna", False)
            fila.setdefault("orden_impacto", 0)
        resultado.append(fila)

    vistos_primer_impacto: set[int] = set()
    for fila in sorted(resultado, key=_orden_impacto_sort_key):
        cod = to_int_or_none(fila.get("codigo_movimiento"))
        if cod is None:
            fila["es_primer_impacto"] = True
            continue
        if cod not in vistos_primer_impacto:
            fila["es_primer_impacto"] = True
            vistos_primer_impacto.add(cod)
        else:
            fila["es_primer_impacto"] = False
    return sorted(resultado, key=_orden_impacto_sort_key)


def _calcular_saldo_corrido_por_etapa(
    movimientos: List[Dict[str, Any]],
    *,
    saldo_inicial_por_etapa: Dict[str, int],
    tipos_etapa: List[str],
    mapa_dep: Optional[Dict[int, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    saldos = dict(saldo_inicial_por_etapa)
    for t in tipos_etapa:
        saldos.setdefault(t, 0)
    resultado: List[Dict[str, Any]] = []
    for mov in sorted(movimientos or [], key=_orden_impacto_sort_key):
        entrada = int(to_int_or_none(mov.get("entrada")) or 0)
        salida = int(to_int_or_none(mov.get("salida")) or 0)
        dep = to_int_or_none(mov.get("cod_deposito"))
        etapa_mapa = (mapa_dep or {}).get(dep, {}) if dep is not None else {}
        tipo = etapa_mapa.get("tipo_mpr") or (mov.get("etapa") or {}).get("tipo_mpr")
        if mov.get("afecta_deposito", True) and tipo:
            if tipo not in saldos:
                saldos.setdefault(tipo, 0)
            saldos[tipo] += entrada - salida
        fila = dict(mov)
        # Contrato UI/CSV: solo etapas del pipeline (orden de tipos_etapa).
        snapshot = {t: int(saldos.get(t, 0)) for t in tipos_etapa}
        fila["saldos_por_etapa"] = snapshot
        fila["saldos_etapa_ui"] = [
            {"tipo_mpr": t, "saldo": snapshot.get(t, 0)}
            for t in tipos_etapa
        ]
        fila["saldo_corrido"] = sum(snapshot.values())
        if fila.get("clase_ui") == "inventario" and tipo in snapshot:
            fila["conteo"] = snapshot[tipo]
        elif fila.get("clase_ui") == "inventario":
            fila["conteo"] = fila["saldo_corrido"]
        else:
            fila["conteo"] = mov.get("conteo")
        resultado.append(fila)
    return resultado


def _calcular_saldo_inicial_por_etapa(
    *,
    pre_periodo_movimientos: Optional[List[Dict[str, Any]]] = None,
    stock_por_etapa: Optional[Dict[str, int]] = None,
    neto_periodo_por_etapa: Optional[Dict[str, int]] = None,
    tipos_etapa: List[str],
    mapa_dep: Optional[Dict[int, Dict[str, Any]]] = None,
) -> tuple[Dict[str, int], bool]:
    vacio = _saldos_vacios_por_etapa(tipos_etapa)
    if pre_periodo_movimientos is not None:
        saldos = dict(vacio)
        for mov in pre_periodo_movimientos:
            if not mov.get("afecta_deposito", True):
                continue
            dep = to_int_or_none(mov.get("cod_deposito"))
            etapa_mapa = (mapa_dep or {}).get(dep, {}) if dep is not None else {}
            tipo = etapa_mapa.get("tipo_mpr") or (mov.get("etapa") or {}).get("tipo_mpr")
            if not tipo:
                continue
            saldos.setdefault(tipo, 0)
            entrada = int(to_int_or_none(mov.get("entrada")) or 0)
            salida = int(to_int_or_none(mov.get("salida")) or 0)
            saldos[tipo] += entrada - salida
        return saldos, True

    if stock_por_etapa is not None and neto_periodo_por_etapa is not None:
        inicial = dict(vacio)
        for t in tipos_etapa:
            inicial[t] = int(stock_por_etapa.get(t, 0)) - int(neto_periodo_por_etapa.get(t, 0))
        return inicial, True

    return vacio, False


def _fetch_stock_por_etapa_pipeline(
    base_empresa: str,
    id_articulo: int,
    etapas: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Stock actual por tipo_mpr (paridad inventario fabricados, sin inventario_tabla)."""
    from mpr.services import TIPOS_MPR_PIPELINE_FABRICADOS, _nombre_tabla

    id_art = to_int_or_none(id_articulo)
    tipos = _tipos_mpr_pipeline_desde_etapas(etapas) or list(TIPOS_MPR_PIPELINE_FABRICADOS)
    vacio = _saldos_vacios_por_etapa(tipos)
    dep_ids = [
        d for d in (to_int_or_none(e.get("id_deposito")) for e in (etapas or [])) if d is not None
    ]
    if not (base_empresa or "").strip() or id_art is None or not dep_ids:
        return vacio
    placeholders = ",".join(["%s"] * len(dep_ids))
    mapa_dep_tipo = {
        to_int_or_none(e.get("id_deposito")): str(e.get("tipo_mpr") or "")
        for e in (etapas or [])
        if to_int_or_none(e.get("id_deposito")) is not None
    }
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            if not tbl_sd:
                return vacio
            cursor.execute(
                f"""
                SELECT sd.id_deposito, COALESCE(SUM(sd.saldo), 0) AS saldo
                FROM {tbl_sd} sd
                WHERE sd.id_articulo = %s AND sd.id_deposito IN ({placeholders})
                GROUP BY sd.id_deposito
                """,
                [id_art, *dep_ids],
            )
            rows = cursor.fetchall() or []
    except Exception as exc:
        logger.warning(
            "_fetch_stock_por_etapa_pipeline error base=%s art=%s: %s",
            base_empresa,
            id_articulo,
            exc,
        )
        return vacio

    totales = dict(vacio)
    for row in rows:
        dep = to_int_or_none(row.get("id_deposito"))
        tipo = mapa_dep_tipo.get(dep or -1)
        if not tipo or tipo not in totales:
            continue
        totales[tipo] += int(round(float(row.get("saldo") or 0)))
    return totales


def _neto_periodo_por_etapa(
    movimientos: List[Dict[str, Any]],
    tipos_etapa: List[str],
) -> Dict[str, int]:
    neto = _saldos_vacios_por_etapa(tipos_etapa)
    for mov in movimientos or []:
        if not mov.get("afecta_deposito", True):
            continue
        tipo = (mov.get("etapa") or {}).get("tipo_mpr")
        if tipo not in neto:
            continue
        neto[tipo] += int(mov.get("entrada") or 0) - int(mov.get("salida") or 0)
    return neto


def _conciliar_cierre_por_etapa(
    *,
    saldo_final_por_etapa: Dict[str, int],
    stock_por_etapa: Dict[str, int],
    etapas: List[Dict[str, Any]],
    hasta_date: Optional[date],
    hoy: date,
    calculado_ok: bool,
    advertencias: List[str],
) -> tuple[bool, Dict[str, Dict[str, int]]]:
    conciliacion: Dict[str, Dict[str, int]] = {}
    estricta = (
        calculado_ok
        and hasta_date is not None
        and hasta_date >= hoy
    )
    if not estricta:
        return False, conciliacion

    difs: List[str] = []
    for et in etapas or []:
        tipo = str(et.get("tipo_mpr") or "")
        label = str_or_default(et.get("label"), tipo)
        kardex = int(saldo_final_por_etapa.get(tipo, 0))
        inv = int(stock_por_etapa.get(tipo, 0))
        conciliacion[tipo] = {
            "kardex": kardex,
            "inventario": inv,
            "diferencia": kardex - inv,
        }
        if kardex != inv:
            difs.append(f"{label}: kardex {kardex} vs inventario {inv}")

    if difs:
        advertencias.append(
            "El saldo reconstruido al cierre no coincide con el inventario por etapa: "
            + "; ".join(difs)
        )
    return True, conciliacion


def _contar_movimientos_distintos(movimientos: List[Dict[str, Any]]) -> int:
    return len({
        to_int_or_none(m.get("codigo_movimiento"))
        for m in (movimientos or [])
        if to_int_or_none(m.get("codigo_movimiento")) is not None
    })


def _calcular_saldo_corrido_analisis(
    movimientos: List[Dict[str, Any]],
    *,
    saldo_inicial: int = 0,
) -> List[Dict[str, Any]]:
    """Saldo corrido respetando afecta_deposito (FA excluido del acumulado)."""
    saldo = int(saldo_inicial)
    resultado: List[Dict[str, Any]] = []
    for mov in movimientos or []:
        entrada = int(to_int_or_none(mov.get("entrada")) or 0)
        salida = int(to_int_or_none(mov.get("salida")) or 0)
        if mov.get("afecta_deposito", True):
            saldo += entrada - salida
        fila = dict(mov)
        fila["saldo_corrido"] = saldo
        if mov.get("clase_ui") == "inventario":
            fila["conteo"] = saldo
        else:
            fila["conteo"] = None
        resultado.append(fila)
    return resultado


def _calcular_saldo_inicial_terminado(
    *,
    pre_periodo_movimientos: Optional[List[Dict[str, Any]]] = None,
    stock_terminado_actual: Optional[int] = None,
    neto_periodo: Optional[int] = None,
) -> tuple[int, bool]:
    """Stock real al inicio de ``desde`` vía movimientos previos o delta stock_deposito."""
    if pre_periodo_movimientos is not None:
        saldo = 0
        for mov in pre_periodo_movimientos:
            if not mov.get("afecta_deposito", True):
                continue
            entrada = int(to_int_or_none(mov.get("entrada")) or 0)
            salida = int(to_int_or_none(mov.get("salida")) or 0)
            saldo += entrada - salida
        return saldo, True

    if stock_terminado_actual is not None and neto_periodo is not None:
        return int(stock_terminado_actual) - int(neto_periodo), True

    return 0, False


def _unificar_y_saldo_corrido(
    movimientos: List[Dict[str, Any]],
    *,
    saldo_inicial: int = 0,
) -> List[Dict[str, Any]]:
    ordenados = sorted(
        movimientos or [],
        key=lambda m: (
            str(m.get("fecha_sort") or ""),
            to_int_or_none(m.get("codigo_movimiento")) or 0,
        ),
    )
    return _calcular_saldo_corrido_analisis(ordenados, saldo_inicial=saldo_inicial)


def _fetch_stock_terminado_analisis(
    base_empresa: str,
    id_articulo: int,
    *,
    id_deposito: Optional[int] = None,
    ids_deposito: Optional[List[int]] = None,
) -> Optional[int]:
    """Saldo en depósito(s) del eje de análisis (Terminado puntual o suma pipeline).

    Sin filtro de depósito, prioriza el depósito MPR Terminado (paridad golden sample).
    Con ``ids_deposito``, suma saldo en todos (pipeline fabricados consolidado).
    """
    from mpr.services import _nombre_tabla, get_deposito_terminado_mpr

    id_art = to_int_or_none(id_articulo)
    if not (base_empresa or "").strip() or id_art is None:
        return None
    dep = to_int_or_none(id_deposito)
    dep_ids = [d for d in (to_int_or_none(x) for x in (ids_deposito or [])) if d is not None]
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            if not tbl_sd:
                return None
            if dep_ids:
                placeholders = ",".join(["%s"] * len(dep_ids))
                cursor.execute(
                    f"""
                    SELECT COALESCE(SUM(sd.saldo), 0) AS stock_terminado
                    FROM {tbl_sd} sd
                    WHERE sd.id_articulo = %s AND sd.id_deposito IN ({placeholders})
                    """,
                    [id_art, *dep_ids],
                )
            elif dep is not None:
                cursor.execute(
                    f"""
                    SELECT COALESCE(SUM(sd.saldo), 0) AS stock_terminado
                    FROM {tbl_sd} sd
                    WHERE sd.id_articulo = %s AND sd.id_deposito = %s
                    """,
                    [id_art, dep],
                )
            elif dep is None:
                dep = to_int_or_none(get_deposito_terminado_mpr(base_empresa))
                if dep is not None:
                    cursor.execute(
                        f"""
                        SELECT COALESCE(SUM(sd.saldo), 0) AS stock_terminado
                        FROM {tbl_sd} sd
                        WHERE sd.id_articulo = %s AND sd.id_deposito = %s
                        """,
                        [id_art, dep],
                    )
                elif tbl_dep:
                    cursor.execute(
                        f"""
                        SELECT COALESCE(SUM(sd.saldo), 0) AS stock_terminado
                        FROM {tbl_sd} sd
                        INNER JOIN {tbl_dep} d ON d.CodDeposito = sd.id_deposito
                          AND COALESCE(d.anulado, 'No') = 'No'
                          AND COALESCE(d.suma_stock, 'Si') = 'Si'
                        WHERE sd.id_articulo = %s
                        """,
                        [id_art],
                    )
                else:
                    cursor.execute(
                        f"""
                        SELECT COALESCE(SUM(sd.saldo), 0) AS stock_terminado
                        FROM {tbl_sd} sd
                        WHERE sd.id_articulo = %s
                        """,
                        [id_art],
                    )
            row = cursor.fetchone()
            if not row:
                return None
            return int(round(float(row.get("stock_terminado") or 0)))
    except Exception as exc:
        logger.warning(
            "_fetch_stock_terminado_analisis error base=%s art=%s: %s",
            base_empresa,
            id_articulo,
            exc,
            exc_info=True,
        )
        return None


def _fetch_stock_reserva_articulo(base_empresa: str, id_articulo: int) -> int:
    from mpr.services import _nombre_tabla

    id_art = to_int_or_none(id_articulo)
    if not (base_empresa or "").strip() or id_art is None:
        return 0
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "articulo")
            if not tbl:
                return 0
            cursor.execute(
                f"SELECT COALESCE(stock_reserva, 0) AS stock_reserva FROM {tbl} WHERE IDArt = %s LIMIT 1",
                [id_art],
            )
            row = cursor.fetchone()
            return int(round(float((row or {}).get("stock_reserva") or 0)))
    except Exception:
        return 0


def _clave_fecha_turno_parte(parte: Any) -> Optional[Tuple[Any, int]]:
    from mpr.services import _fecha_parte_date

    fp = _fecha_parte_date(parte)
    tid = to_int_or_none(
        getattr(parte, "turno_id", None) or getattr(parte, "id_mpr_turno", None)
    )
    if fp is None or tid is None:
        return None
    return (fp, tid)


def _humanizar_detalle_movimiento(
    detalle: str,
    *,
    partes_por_uuid: Optional[Dict[str, Any]] = None,
    id_articulo: Optional[int] = None,
    fecha_movimiento: Optional[Any] = None,
    incluir_hora: bool = False,
) -> str:
    """Quita UUID de 'Qué pasó' y arma Parte · turno · OPT · operario."""
    from mpr.services import texto_detalle_parte_produccion

    texto = str_or_default(detalle, "")
    if "Ajuste físico OPP-parte" in texto:
        return "Ajuste de parte de producción"
    match = _RE_DETALLE_OPP_PARTE_UUID.search(texto)
    if match:
        parte = (partes_por_uuid or {}).get(match.group(1).lower())
        if parte is not None:
            return texto_detalle_parte_produccion(
                parte,
                fecha_movimiento=fecha_movimiento,
                incluir_hora=incluir_hora,
                id_articulo=id_articulo,
            )
        return "Parte"
    if _RE_UUID.search(texto):
        return _RE_UUID.sub("", texto).replace("  ", " ").strip(" ·-")
    return texto


def _resolver_partes_kardex_por_uuid(
    base_empresa: str,
    uuids: List[str],
) -> Dict[str, Any]:
    """Carga cabeceras mpr_parte desde MySQL empresa (no el ORM Django)."""
    from mpr.repositories.parte import obtener_parte_por_pk

    partes_por_uuid: Dict[str, Any] = {}
    base = (base_empresa or "").strip()
    if not base:
        return partes_por_uuid
    vistos: set[str] = set()
    for uid in uuids:
        clave = (uid or "").strip().lower()
        if not clave or clave in vistos:
            continue
        vistos.add(clave)
        try:
            parte = obtener_parte_por_pk(base, uid, with_relations=True)
        except Exception:
            logger.debug(
                "No se pudo resolver parte MPR %s en %s", uid, base, exc_info=True
            )
            continue
        if parte is not None:
            partes_por_uuid[clave] = parte
    return partes_por_uuid


def _conteo_partes_mismo_turno(
    base_empresa: str,
    partes: List[Any],
) -> Dict[Tuple[Any, int], int]:
    """Cuántos partes hay por (fecha_produccion, turno) entre los resueltos y en MySQL."""
    from collections import Counter

    from mpr.repositories.parte import contar_partes_fecha_turno

    locales = Counter()
    for parte in partes:
        clave = _clave_fecha_turno_parte(parte)
        if clave is not None:
            locales[clave] += 1
    out: Dict[Tuple[Any, int], int] = dict(locales)
    base = (base_empresa or "").strip()
    if not base:
        return out
    for clave in list(out.keys()):
        fp, tid = clave
        try:
            n_db = contar_partes_fecha_turno(base, fp, tid)
        except Exception:
            n_db = 0
        if n_db > out[clave]:
            out[clave] = n_db
    return out


def _enriquecer_detalles_opp_parte(
    movimientos: List[Dict[str, Any]],
    *,
    id_articulo: Optional[int] = None,
    base_empresa: str = "",
) -> List[Dict[str, Any]]:
    uuids: List[str] = []
    for mov in movimientos or []:
        match = _RE_DETALLE_OPP_PARTE_UUID.search(str(mov.get("detalle") or ""))
        if match:
            uuids.append(match.group(1))
    partes_por_uuid = _resolver_partes_kardex_por_uuid(base_empresa, uuids)
    conteos_turno = _conteo_partes_mismo_turno(
        base_empresa, list(partes_por_uuid.values())
    )
    out: List[Dict[str, Any]] = []
    for mov in movimientos or []:
        fila = dict(mov)
        detalle_orig = str(fila.get("detalle") or "")
        match = _RE_DETALLE_OPP_PARTE_UUID.search(detalle_orig)
        parte = (
            partes_por_uuid.get(match.group(1).lower()) if match else None
        )
        clave = _clave_fecha_turno_parte(parte) if parte is not None else None
        fila["detalle"] = _humanizar_detalle_movimiento(
            detalle_orig,
            partes_por_uuid=partes_por_uuid,
            id_articulo=id_articulo,
            fecha_movimiento=fila.get("fecha_sort") or fila.get("fecha"),
            incluir_hora=bool(clave and conteos_turno.get(clave, 0) > 1),
        )
        out.append(fila)
    return out


def _recolectar_movimientos_analisis(
    base_empresa: str,
    id_articulo: int,
    *,
    id_deposito: Optional[int] = None,
    ids_deposito: Optional[List[int]] = None,
    fecha_desde: Optional[Any] = None,
    fecha_hasta: Optional[Any] = None,
    limit: int = 500,
    solo_pre_periodo: bool = False,
    desglosar_por_deposito: bool = False,
    mapa_dep_etapa: Optional[Dict[int, Dict[str, Any]]] = None,
    advertencias: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Unifica MSTOCK OPP/OPA, REM/FA, inventario y eventos MPR."""
    from datetime import date as date_type, datetime as datetime_type, timedelta

    corte_str = to_date_or_none(fecha_desde)
    corte_date: Optional[date_type] = None
    if corte_str:
        try:
            corte_date = datetime_type.strptime(corte_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            corte_date = None
    if solo_pre_periodo:
        q_desde = None
        q_hasta = (
            (corte_date - timedelta(days=1)).strftime("%Y-%m-%d") if corte_date else None
        )
    else:
        q_desde = fecha_desde
        q_hasta = fecha_hasta

    movs: List[Dict[str, Any]] = []
    avisos = advertencias if advertencias is not None else []
    filtro_dep = {
        "id_deposito": id_deposito,
        "ids_deposito": ids_deposito,
        "desglosar_por_deposito": desglosar_por_deposito,
    }
    mapa = mapa_dep_etapa or {}

    def _agregar(fila: Optional[Dict[str, Any]]) -> None:
        if not fila:
            return
        if desglosar_por_deposito and mapa:
            fila = _enriquecer_impacto_etapa(fila, mapa, avisos)
            if fila is None:
                return
        movs.append(fila)

    for row in _consultar_movimientos_kardex_articulo(
        base_empresa,
        id_articulo,
        fecha_desde=q_desde,
        fecha_hasta=q_hasta,
        limit=limit,
        **filtro_dep,
    ):
        _agregar(_normalizar_fila_analisis_mstock(row))

    for row in _consultar_movimientos_stock_rem_fa(
        base_empresa,
        id_articulo,
        fecha_desde=q_desde,
        fecha_hasta=q_hasta,
        limit=limit,
        **filtro_dep,
    ):
        _agregar(_normalizar_fila_analisis_stock(row, fuente="stock"))

    for row in _consultar_movimientos_inventario_mstock(
        base_empresa,
        id_articulo,
        fecha_desde=q_desde,
        fecha_hasta=q_hasta,
        limit=limit,
        **filtro_dep,
    ):
        _agregar(_normalizar_fila_analisis_mstock(row))

    # Los eventos MPR (envío/parte/clasificación) no mueven stock_deposito; van en
    # ``eventos_mpr`` para timeline, no en el kardex de saldo (paridad Excel).

    return _enriquecer_detalles_opp_parte(
        _deduplicar_movimientos(movs),
        id_articulo=id_articulo,
        base_empresa=base_empresa,
    )


def _texto_explicativo_brecha(p_ped: int, terminado: int, ped_urgente: int) -> str:
    if terminado >= 0:
        return (
            f"PED Urgente = max(0, Pedido − Terminado) = max(0, {p_ped} − {terminado}) = {ped_urgente}."
        )
    return (
        f"Terminado negativo ({terminado}). "
        f"PED Urgente = Pedido + |Terminado| = {p_ped} + {abs(terminado)} = {ped_urgente}."
    )


def construir_analisis_trazabilidad_articulo(
    base_empresa: str,
    id_articulo: int,
    *,
    id_deposito: Optional[int] = None,
    fecha_desde: Optional[Any] = None,
    fecha_hasta: Optional[Any] = None,
    limit: int = 2000,
) -> Dict[str, Any]:
    """
    Análisis completo: PED, stock, BOM, movimientos del rango con saldo corrido.

    Historia reconstruida: movimientos anteriores a ``fecha_desde`` se consolidan
    en ``saldo_inicial`` (no se listan). En el rango solo se listan movimientos
    que mueven stock Terminado (``afecta_deposito``).
    """
    from datetime import date as date_type, datetime as datetime_type

    from mpr.services import (
        ETIQUETA_EJE_PIPELINE_FABRICADOS,
        TIPOS_MPR_PIPELINE_FABRICADOS,
        _fetch_descripciones_articulo,
        calcular_max_packs_armado_1ra,
        get_bom_detalle,
        get_deposito_semi_elaborado_mpr,
        get_deposito_terminado_mpr,
        get_depositos_pipeline_fabricados_mpr,
        get_etapas_pipeline_fabricados_mpr,
        get_id_en_abm_por_articulo,
        listar_demanda_ped_por_articulo,
    )

    id_art = to_int_or_none(id_articulo)
    vacio: Dict[str, Any] = {
        "articulo": None,
        "demanda_ped": {"filas": [], "totales": {"p_ped": 0, "stock": 0, "cubierto_stock": 0, "ped_urgente": 0}},
        "stock": {"terminado": 0, "semi_componentes": [], "negativo": False},
        "brechas": {
            "ped_urgente": 0,
            "tot_urgente": 0,
            "reserva": 0,
            "texto_explicativo": "",
        },
        "bom": None,
        "a_producir": {"cantidad": 0, "capacidad_semi": 0, "alerta_semi_cero": False},
        "movimientos": [],
        "eventos_mpr": [],
        "kpis": {
            "pedido": 0,
            "terminado": 0,
            "ped_urgente": 0,
            "tot_urgente": 0,
            "saldo_final": 0,
        },
        "saldo_inicial": {
            "valor": 0,
            "calculado_ok": False,
            "origen": "historico_pre_periodo",
        },
        "deposito": None,
        "advertencias": [],
    }
    if not (base_empresa or "").strip() or id_art is None:
        vacio["advertencias"] = ["Artículo no indicado."]
        return vacio

    advertencias: List[str] = []
    desc_map = _fetch_descripciones_articulo(base_empresa, [id_art])
    if id_art not in desc_map:
        advertencias.append("Artículo inexistente o sin datos en la base.")
        vacio["advertencias"] = advertencias
        return vacio

    codigo, descripcion = desc_map[id_art]
    id_en_abm = get_id_en_abm_por_articulo(base_empresa, id_art)
    es_pack = id_en_abm is not None
    bom = get_bom_detalle(base_empresa, id_en_abm) if id_en_abm else None

    # Eje por defecto según tipo de artículo (pack → Terminado; componente → pipeline fabricados).
    dep_id = to_int_or_none(id_deposito)
    dep_ids: Optional[List[int]] = None
    es_pipeline_fabricados = False
    dep_default_canonico = False
    etapas_pipeline: List[Dict[str, Any]] = []
    desglosar_por_deposito = False
    mapa_dep_etapa: Dict[int, Dict[str, Any]] = {}
    tipos_etapa: List[str] = list(TIPOS_MPR_PIPELINE_FABRICADOS)

    if dep_id is None:
        if es_pack:
            dep_canon = get_deposito_terminado_mpr(base_empresa)
            dep_id = to_int_or_none(dep_canon)
        else:
            etapas_pipeline = get_etapas_pipeline_fabricados_mpr(base_empresa)
            if etapas_pipeline:
                dep_ids = [
                    d for d in (to_int_or_none(e.get("id_deposito")) for e in etapas_pipeline)
                    if d is not None
                ]
                if len(dep_ids) >= 2:
                    es_pipeline_fabricados = True
                    desglosar_por_deposito = True
                    mapa_dep_etapa = _mapa_deposito_etapa(etapas_pipeline)
                    tipos_etapa = _tipos_mpr_pipeline_desde_etapas(etapas_pipeline)
                elif len(dep_ids) == 1:
                    dep_id = dep_ids[0]
                    dep_ids = None
            if not es_pipeline_fabricados and dep_id is None:
                dep_ids = get_depositos_pipeline_fabricados_mpr(base_empresa)
                if not etapas_pipeline and dep_ids:
                    advertencias.append(
                        "No se encontraron etapas pipeline con suma_stock=Si; "
                        "se usa el listado legacy de depósitos sin desglose por etapa."
                    )
                es_pipeline_fabricados = bool(dep_ids) and len(dep_ids) >= 2
                if len(dep_ids) == 1:
                    dep_id = dep_ids[0]
                    dep_ids = None
                    es_pipeline_fabricados = False
        dep_default_canonico = dep_id is not None or bool(dep_ids)
    deposito: Optional[Dict[str, Any]] = None
    if es_pipeline_fabricados and dep_ids:
        deposito = {
            "id": None,
            "ids": dep_ids,
            "nombre": ETIQUETA_EJE_PIPELINE_FABRICADOS,
            "es_default_canonico": dep_default_canonico,
            "tipo_eje": "pipeline_fabricados",
            "etapas": etapas_pipeline,
        }
    elif dep_id is not None:
        deposito = {
            "id": dep_id,
            "ids": [dep_id],
            "nombre": _fetch_nombre_deposito(base_empresa, dep_id),
            "es_default_canonico": dep_default_canonico,
            "tipo_eje": "terminado" if es_pack else "semi",
        }

    filtro_eje: Dict[str, Any] = {}
    if dep_ids:
        filtro_eje["ids_deposito"] = dep_ids
    elif dep_id is not None:
        filtro_eje["id_deposito"] = dep_id
    if desglosar_por_deposito:
        filtro_eje["desglosar_por_deposito"] = True
        filtro_eje["mapa_dep_etapa"] = mapa_dep_etapa
        filtro_eje["advertencias"] = advertencias

    limite_efectivo = limit
    if es_pipeline_fabricados and etapas_pipeline:
        limite_efectivo = min(max(1, int(limit or 2000)) * max(1, len(etapas_pipeline)), 5000)

    demanda_filas = listar_demanda_ped_por_articulo(base_empresa, id_art, limit=limit)
    p_ped = sum(int(to_int_or_none(f.get("cantidad_pendiente_prod")) or 0) for f in demanda_filas)

    stock_por_etapa: Dict[str, int] = {}
    if es_pipeline_fabricados and etapas_pipeline:
        stock_por_etapa = _fetch_stock_por_etapa_pipeline(base_empresa, id_art, etapas_pipeline)
        stock_terminado = sum(stock_por_etapa.values())
    else:
        stock_terminado = _fetch_stock_terminado_analisis(
            base_empresa,
            id_art,
            id_deposito=dep_id if not dep_ids else None,
            ids_deposito=dep_ids,
        )
    if stock_terminado is None:
        if es_pipeline_fabricados:
            advertencias.append(
                "No se pudo calcular el stock consolidado del pipeline fabricados "
                "(Producción + Semi + 2.ª selección); revise la configuración de depósitos MPR."
            )
        else:
            advertencias.append(
                "No se pudo calcular el stock Terminado actual; revise el depósito "
                "tipo_mpr=Terminado (o depósitos suma_stock)."
            )
        stock_terminado = 0

    reserva = _fetch_stock_reserva_articulo(base_empresa, id_art)
    ped_urgente = max(0, p_ped - stock_terminado)
    tot_urgente = max(0, p_ped + reserva - stock_terminado)

    pre_movs = _recolectar_movimientos_analisis(
        base_empresa,
        id_art,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limit=limite_efectivo,
        solo_pre_periodo=True,
        **filtro_eje,
    )
    pre_movs_stock = [m for m in pre_movs if m.get("afecta_deposito", True)]
    if es_pipeline_fabricados:
        pre_movs_stock = _marcar_transferencias_internas(
            pre_movs_stock, mapa_dep=mapa_dep_etapa
        )
    if _contar_movimientos_distintos(pre_movs) >= limit:
        advertencias.append(
            "El historial anterior al Desde puede estar incompleto (límite de movimientos). "
            "El saldo inicial histórico podría no reflejar todo el stock previo."
        )

    saldo_inicial_por_etapa: Dict[str, int] = {}
    if es_pipeline_fabricados:
        saldo_inicial_por_etapa, calculado_ok = _calcular_saldo_inicial_por_etapa(
            pre_periodo_movimientos=pre_movs_stock,
            tipos_etapa=tipos_etapa,
            mapa_dep=mapa_dep_etapa,
        )
        saldo_inicial = sum(saldo_inicial_por_etapa.values())
    else:
        saldo_inicial, calculado_ok = _calcular_saldo_inicial_terminado(
            pre_periodo_movimientos=pre_movs_stock,
        )

    if not calculado_ok and stock_terminado is not None:
        movs_crudos = _recolectar_movimientos_analisis(
            base_empresa,
            id_art,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limit=limite_efectivo,
            **filtro_eje,
        )
        if es_pipeline_fabricados:
            movs_crudos = [m for m in movs_crudos if m.get("afecta_deposito", True)]
            movs_crudos = _marcar_transferencias_internas(
                movs_crudos, mapa_dep=mapa_dep_etapa
            )
            neto_etapa = _neto_periodo_por_etapa(movs_crudos, tipos_etapa)
            saldo_inicial_por_etapa, calculado_ok = _calcular_saldo_inicial_por_etapa(
                stock_por_etapa=stock_por_etapa,
                neto_periodo_por_etapa=neto_etapa,
                tipos_etapa=tipos_etapa,
                mapa_dep=mapa_dep_etapa,
            )
            saldo_inicial = sum(saldo_inicial_por_etapa.values())
        else:
            neto = sum(
                (int(m.get("entrada") or 0) - int(m.get("salida") or 0))
                for m in movs_crudos
                if m.get("afecta_deposito", True)
            )
            saldo_inicial, calculado_ok = _calcular_saldo_inicial_terminado(
                stock_terminado_actual=stock_terminado,
                neto_periodo=neto,
            )
    if not calculado_ok:
        advertencias.append(
            "No se pudo determinar el saldo inicial histórico al inicio del período; "
            "el saldo corrido puede no reflejar stock previo real."
        )

    movimientos = _recolectar_movimientos_analisis(
        base_empresa,
        id_art,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limit=limite_efectivo,
        **filtro_eje,
    )
    if _contar_movimientos_distintos(movimientos) >= limit:
        advertencias.append(
            "Se alcanzó el límite de movimientos del período; la historia listada puede estar truncada."
        )
    # Solo movimientos que mueven stock Terminado (p. ej. FA se omite).
    movimientos = [m for m in movimientos if m.get("afecta_deposito", True)]
    if es_pipeline_fabricados:
        movimientos = _marcar_transferencias_internas(
            movimientos, mapa_dep=mapa_dep_etapa
        )
        movimientos = _calcular_saldo_corrido_por_etapa(
            movimientos,
            saldo_inicial_por_etapa=saldo_inicial_por_etapa,
            tipos_etapa=tipos_etapa,
            mapa_dep=mapa_dep_etapa,
        )
    else:
        movimientos = _unificar_y_saldo_corrido(movimientos, saldo_inicial=saldo_inicial)

    eventos_mpr = _consultar_eventos_mpr_articulo(
        base_empresa,
        id_art,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )

    saldo_final = saldo_inicial
    saldo_final_por_etapa: Dict[str, int] = dict(saldo_inicial_por_etapa)
    if movimientos:
        saldo_final = int(movimientos[-1].get("saldo_corrido") or saldo_inicial)
        if es_pipeline_fabricados:
            ult = movimientos[-1].get("saldos_por_etapa") or {}
            saldo_final_por_etapa = {t: int(ult.get(t, 0)) for t in tipos_etapa}

    # Conciliación: con Hasta ≥ hoy sobre el eje elegido, el corrido debe cerrar.
    hasta_str = to_date_or_none(fecha_hasta)
    hasta_date: Optional[date_type] = None
    if hasta_str:
        try:
            hasta_date = datetime_type.strptime(hasta_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            hasta_date = None
    hoy = date_type.today()
    conciliacion_estricta = False
    conciliacion_por_etapa: Dict[str, Dict[str, int]] = {}
    if es_pipeline_fabricados:
        conciliacion_estricta, conciliacion_por_etapa = _conciliar_cierre_por_etapa(
            saldo_final_por_etapa=saldo_final_por_etapa,
            stock_por_etapa=stock_por_etapa,
            etapas=etapas_pipeline,
            hasta_date=hasta_date,
            hoy=hoy,
            calculado_ok=calculado_ok,
            advertencias=advertencias,
        )
    else:
        etiqueta_eje_stock = (deposito or {}).get("nombre") or "depósito del análisis"
        if (
            calculado_ok
            and hasta_date is not None
            and hasta_date >= hoy
            and saldo_final != stock_terminado
        ):
            advertencias.append(
                f"El saldo reconstruido al cierre ({saldo_final}) no coincide con "
                f"el stock actual del eje ({stock_terminado} en {etiqueta_eje_stock}). "
                "Puede haber movimientos no capturados, truncado por límite o un depósito "
                "distinto al eje del análisis."
            )

    dep_semi = dep_id
    if es_pack and dep_id is None:
        dep_semi = get_deposito_terminado_mpr(base_empresa)
    elif not es_pack:
        dep_semi = get_deposito_semi_elaborado_mpr(base_empresa)
    capacidad_semi = 0
    if es_pack and dep_semi is not None:
        capacidad_semi = max(
            0,
            int(
                calcular_max_packs_armado_1ra(
                    base_empresa,
                    id_art,
                    deposito_semi=dep_semi,
                )
                or 0
            ),
        )

    max_packs = capacidad_semi if es_pack else 0

    return {
        "articulo": {
            "id": id_art,
            "codigo": codigo,
            "descripcion": descripcion,
            "es_pack": es_pack,
            "id_en_abm": id_en_abm,
        },
        "demanda_ped": {
            "filas": demanda_filas,
            "totales": {
                "p_ped": p_ped,
                "stock": stock_terminado,
                "cubierto_stock": min(p_ped, max(stock_terminado, 0)),
                "ped_urgente": ped_urgente,
            },
        },
        "stock": {
            "terminado": stock_terminado,
            "semi_componentes": [],
            "negativo": stock_terminado < 0,
            **({"por_etapa": stock_por_etapa} if es_pipeline_fabricados else {}),
        },
        "brechas": {
            "ped_urgente": ped_urgente,
            "tot_urgente": tot_urgente,
            "reserva": reserva,
            "texto_explicativo": _texto_explicativo_brecha(p_ped, stock_terminado, ped_urgente),
        },
        "bom": bom,
        "a_producir": {
            "cantidad": tot_urgente,
            "capacidad_semi": capacidad_semi,
            "alerta_semi_cero": ped_urgente > 0 and capacidad_semi <= 0,
        },
        "movimientos": movimientos,
        "eventos_mpr": eventos_mpr,
        "kpis": {
            "pedido": p_ped,
            "terminado": stock_terminado,
            "ped_urgente": ped_urgente,
            "tot_urgente": tot_urgente,
            "saldo_final": saldo_final,
            "total_entradas": sum(int(m.get("entrada") or 0) for m in movimientos),
            "total_salidas": sum(int(m.get("salida") or 0) for m in movimientos),
            "max_packs": max_packs,
            "deposito_id": (deposito or {}).get("id"),
            "deposito_ids": (deposito or {}).get("ids") or [],
            "deposito_nombre": (deposito or {}).get("nombre"),
            "tipo_eje": (deposito or {}).get("tipo_eje"),
            **(
                {
                    "saldo_final_por_etapa": saldo_final_por_etapa,
                    "stock_por_etapa": stock_por_etapa,
                    "etapas": [
                        {"tipo_mpr": e.get("tipo_mpr"), "label": e.get("label")}
                        for e in etapas_pipeline
                    ],
                    "conciliacion_estricta": conciliacion_estricta,
                    "conciliacion_por_etapa": conciliacion_por_etapa,
                }
                if es_pipeline_fabricados
                else {}
            ),
        },
        "saldo_inicial": {
            "valor": saldo_inicial,
            "calculado_ok": calculado_ok,
            "origen": "historico_pre_periodo",
            **({"por_etapa": saldo_inicial_por_etapa} if es_pipeline_fabricados else {}),
        },
        "deposito": deposito,
        "advertencias": advertencias,
    }


def _proyectar_movimientos_kardex_compat(
    movimientos: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Proyección backward-compatible para construir_kardex_articulo."""
    out: List[Dict[str, Any]] = []
    for mov in movimientos or []:
        out.append({
            "fecha_display": mov.get("fecha_display"),
            "tipo_mov": mov.get("tipo_mov"),
            "entrada": mov.get("entrada"),
            "salida": mov.get("salida"),
            "saldo_corrido": mov.get("saldo_corrido"),
            "codigo_movimiento": mov.get("codigo_movimiento"),
            "nro_comprobante": mov.get("nro_comprobante"),
            "detalle": mov.get("detalle"),
            "operario": mov.get("operario"),
        })
    return out


def construir_kardex_articulo(
    base_empresa: str,
    id_articulo: int,
    *,
    id_deposito: Optional[int] = None,
    fecha_desde: Optional[Any] = None,
    fecha_hasta: Optional[Any] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """Wrapper delgado: delega análisis y proyecta payload kardex legacy."""
    analisis = construir_analisis_trazabilidad_articulo(
        base_empresa,
        id_articulo,
        id_deposito=id_deposito,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limit=limit,
    )
    kpis = analisis.get("kpis") or {}
    return {
        "articulo": analisis.get("articulo"),
        "bom": analisis.get("bom"),
        "deposito": analisis.get("deposito"),
        "movimientos": _proyectar_movimientos_kardex_compat(analisis.get("movimientos") or []),
        "kpis": {
            "saldo_final": kpis.get("saldo_final", 0),
            "total_entradas": kpis.get("total_entradas", 0),
            "total_salidas": kpis.get("total_salidas", 0),
            "max_packs": kpis.get("max_packs", 0),
        },
        "advertencias": analisis.get("advertencias") or [],
    }
