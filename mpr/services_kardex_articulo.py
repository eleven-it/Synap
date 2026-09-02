"""Kardex artículo MPR: movimiento_stock OPP/OPA por depósito (extraído de services.py por tamaño)."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_int_or_none,
)

logger = logging.getLogger(__name__)

ClasificacionKardex = Literal["entrada", "salida", "ignorar"]

MOTIVO_PARTE_PRODUCCION = "Parte producción"

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
                    COALESCE(SUM(s.Salida), 0) AS total_salida
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
                    m.nro_comprobante, m.detalle, m.id_operario_opt
                ORDER BY m.fecha ASC, m.codigo_movimiento ASC
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
    return {
        "fecha_display": _fmt_fecha_display_kardex(row.get("fecha")),
        "tipo_mov": str_or_default(row.get("tipo_mov"), "-"),
        "entrada": entrada,
        "salida": salida,
        "codigo_movimiento": cod_mov,
        "nro_comprobante": str_or_default(row.get("nro_comprobante"), "-"),
        "detalle": str_or_default(row.get("detalle"), ""),
        "operario": str(operario_id) if operario_id is not None else "-",
    }


def _consultar_movimientos_stock_rem_fa(
    base_empresa: str,
    id_articulo: int,
    *,
    id_deposito: Optional[int] = None,
    ids_deposito: Optional[List[int]] = None,
    fecha_desde: Optional[Any] = None,
    fecha_hasta: Optional[Any] = None,
    limit: int = 500,
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
                    COALESCE(SUM(s.Salida), 0) AS total_salida
                FROM {tbl_stock} s
                WHERE s.IDArt = %s
                  AND s.Comprobante IN ('REM', 'FA')
                  AND COALESCE(s.Anulado, 'No') <> 'Si'
                  {filtros_extra}
                GROUP BY
                    s.CodigoMovimiento, s.Fecha, s.FechaControl,
                    s.Comprobante, s.NroComprobante, s.Descripcion, s.TipoComp
                ORDER BY COALESCE(s.FechaControl, CAST(s.Fecha AS DATETIME)) ASC,
                         s.CodigoMovimiento ASC
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
                    COALESCE(SUM(s.Salida), 0) AS total_salida
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
                    m.nro_comprobante, m.detalle, s.TipoComp, s.Comprobante, s.FechaControl
                ORDER BY COALESCE(s.FechaControl, CAST(m.fecha AS DATETIME)) ASC,
                         m.codigo_movimiento ASC
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
    return {
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
    return {
        **fila_k,
        "fecha_sort": row.get("fecha"),
        "clase_ui": clase_ui,
        "afecta_deposito": afecta,
        "fuente": str_or_default(row.get("fuente"), "mstock"),
    }


def _deduplicar_movimientos(movimientos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clave codigo_movimiento; preferir MSTOCK sobre mpr_parte."""
    por_codigo: Dict[int, Dict[str, Any]] = {}
    sin_codigo: List[Dict[str, Any]] = []
    for mov in movimientos or []:
        cod = to_int_or_none(mov.get("codigo_movimiento"))
        if cod is None:
            sin_codigo.append(mov)
            continue
        prev = por_codigo.get(cod)
        if prev is None:
            por_codigo[cod] = mov
            continue
        fuente_prev = str_or_default(prev.get("fuente"), "zz")
        fuente_new = str_or_default(mov.get("fuente"), "zz")
        rank_prev = PRIORIDAD_FUENTE_DEDUPE.get(fuente_prev, 99)
        rank_new = PRIORIDAD_FUENTE_DEDUPE.get(fuente_new, 99)
        if rank_new < rank_prev:
            por_codigo[cod] = mov
    return sorted(
        list(por_codigo.values()) + sin_codigo,
        key=lambda m: (
            str(m.get("fecha_sort") or ""),
            to_int_or_none(m.get("codigo_movimiento")) or 0,
        ),
    )


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
    filtro_dep = {
        "id_deposito": id_deposito,
        "ids_deposito": ids_deposito,
    }

    for row in _consultar_movimientos_kardex_articulo(
        base_empresa,
        id_articulo,
        fecha_desde=q_desde,
        fecha_hasta=q_hasta,
        limit=limit,
        **filtro_dep,
    ):
        fila = _normalizar_fila_analisis_mstock(row)
        if fila:
            movs.append(fila)

    for row in _consultar_movimientos_stock_rem_fa(
        base_empresa,
        id_articulo,
        fecha_desde=q_desde,
        fecha_hasta=q_hasta,
        limit=limit,
        **filtro_dep,
    ):
        fila = _normalizar_fila_analisis_stock(row, fuente="stock")
        if fila:
            movs.append(fila)

    for row in _consultar_movimientos_inventario_mstock(
        base_empresa,
        id_articulo,
        fecha_desde=q_desde,
        fecha_hasta=q_hasta,
        limit=limit,
        **filtro_dep,
    ):
        fila = _normalizar_fila_analisis_mstock(row)
        if fila:
            movs.append(fila)

    # Los eventos MPR (envío/parte/clasificación) no mueven stock_deposito; van en
    # ``eventos_mpr`` para timeline, no en el kardex de saldo (paridad Excel).

    return _deduplicar_movimientos(movs)


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
        _fetch_descripciones_articulo,
        calcular_max_packs_armado_1ra,
        get_bom_detalle,
        get_deposito_semi_elaborado_mpr,
        get_deposito_terminado_mpr,
        get_depositos_pipeline_fabricados_mpr,
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
    if dep_id is None:
        if es_pack:
            dep_canon = get_deposito_terminado_mpr(base_empresa)
            dep_id = to_int_or_none(dep_canon)
        else:
            dep_ids = get_depositos_pipeline_fabricados_mpr(base_empresa)
            es_pipeline_fabricados = bool(dep_ids)
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

    demanda_filas = listar_demanda_ped_por_articulo(base_empresa, id_art, limit=limit)
    p_ped = sum(int(to_int_or_none(f.get("cantidad_pendiente_prod")) or 0) for f in demanda_filas)

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
        limit=limit,
        solo_pre_periodo=True,
        **filtro_eje,
    )
    pre_movs_stock = [m for m in pre_movs if m.get("afecta_deposito", True)]
    if len(pre_movs) >= limit:
        advertencias.append(
            "El historial anterior al Desde puede estar incompleto (límite de movimientos). "
            "El saldo inicial histórico podría no reflejar todo el stock previo."
        )
    saldo_inicial, calculado_ok = _calcular_saldo_inicial_terminado(
        pre_periodo_movimientos=pre_movs_stock,
    )
    if not calculado_ok and stock_terminado is not None:
        movs_crudos = _recolectar_movimientos_analisis(
            base_empresa,
            id_art,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limit=limit,
            **filtro_eje,
        )
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
        limit=limit,
        **filtro_eje,
    )
    if len(movimientos) >= limit:
        advertencias.append(
            "Se alcanzó el límite de movimientos del período; la historia listada puede estar truncada."
        )
    # Solo movimientos que mueven stock Terminado (p. ej. FA se omite).
    movimientos = [m for m in movimientos if m.get("afecta_deposito", True)]
    movimientos = _unificar_y_saldo_corrido(movimientos, saldo_inicial=saldo_inicial)

    eventos_mpr = _consultar_eventos_mpr_articulo(
        base_empresa,
        id_art,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )

    saldo_final = saldo_inicial
    if movimientos:
        saldo_final = int(movimientos[-1].get("saldo_corrido") or saldo_inicial)

    # Conciliación: con Hasta ≥ hoy sobre el eje elegido, el corrido debe cerrar.
    hasta_str = to_date_or_none(fecha_hasta)
    hasta_date: Optional[date_type] = None
    if hasta_str:
        try:
            hasta_date = datetime_type.strptime(hasta_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            hasta_date = None
    hoy = date_type.today()
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
        },
        "saldo_inicial": {
            "valor": saldo_inicial,
            "calculado_ok": calculado_ok,
            "origen": "historico_pre_periodo",
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
