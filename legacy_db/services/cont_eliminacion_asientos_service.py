"""Eliminación física de asientos contables legacy con recálculo de saldos.

Unidad de borrado: ``(id_ejercicio, nro_asiento)``. Requiere permiso
``contabilidad.auditoria.corregir`` para ejecutar; listado y vista previa
solo lectura con ``contabilidad.auditoria.leer``.
"""
from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from collections.abc import Callable, Iterator
from typing import Any

import MySQLdb.cursors

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)
from django.utils import timezone

from legacy_db.services.cont_recalculo_service import (
    CorreccionContableError,
    _insertar_log_detalle,
)

logger = logging.getLogger(__name__)

CHECK_ID_ELIMINACION = "eliminacion_asiento"
CONFIG_HASH_ELIMINACION = "eliminacion_asiento_v1"
Q2 = Decimal("0.01")


class EliminacionAsientosError(Exception):
    """Error de validación u operación en eliminación de asientos."""


def _wrap_error(exc: Exception) -> EliminacionAsientosError:
    if isinstance(exc, EliminacionAsientosError):
        return exc
    if isinstance(exc, CorreccionContableError):
        return EliminacionAsientosError(str(exc))
    return EliminacionAsientosError(str(exc))


def _r2(valor: Any) -> Decimal:
    dec = to_decimal_or_none(valor)
    return (dec if dec is not None else Decimal("0")).quantize(Q2, rounding=ROUND_HALF_UP)


def _fecha_ui(valor) -> str:
    if valor is None or valor == "":
        return ""
    try:
        return valor.strftime("%d/%m/%Y")
    except AttributeError:
        txt = str(valor).strip()
        if len(txt) >= 10 and txt[4:5] == "-" and txt[7:8] == "-":
            from datetime import datetime as dt_cls

            try:
                return dt_cls.strptime(txt[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                pass
        return txt


def _fecha_db_ui(valor) -> str:
    if valor is None:
        return ""
    try:
        return timezone.localtime(valor).strftime("%d/%m/%Y %H:%M")
    except (AttributeError, ValueError):
        return str(valor)


def _normalizar_asientos(asientos: list[dict]) -> list[tuple[int, int]]:
    if not asientos:
        raise EliminacionAsientosError("Debe indicar al menos un asiento a eliminar.")
    normalizados: list[tuple[int, int]] = []
    vistos: set[tuple[int, int]] = set()
    for raw in asientos:
        id_ej = to_int_or_none(raw.get("id_ejercicio"))
        nro = to_int_or_none(raw.get("nro_asiento"))
        if id_ej is None or nro is None:
            raise EliminacionAsientosError(
                "Cada asiento debe incluir id_ejercicio y nro_asiento enteros válidos."
            )
        clave = (id_ej, nro)
        if clave not in vistos:
            vistos.add(clave)
            normalizados.append(clave)
    return normalizados


def _where_listar(filtros: dict) -> tuple[str, list]:
    id_ejercicio = to_int_or_none(filtros.get("id_ejercicio"))
    if id_ejercicio is None:
        raise EliminacionAsientosError("El filtro id_ejercicio es obligatorio.")

    partes = ["a.id_ejercicio = %s"]
    params: list[Any] = [id_ejercicio]

    fecha_desde = to_date_or_none(filtros.get("fecha_desde"))
    if fecha_desde is not None:
        partes.append("a.fecha_asiento >= %s")
        params.append(fecha_desde)

    fecha_hasta = to_date_or_none(filtros.get("fecha_hasta"))
    if fecha_hasta is not None:
        partes.append("a.fecha_asiento <= %s")
        params.append(fecha_hasta)

    id_concepto = to_int_or_none(filtros.get("id_concepto_asiento"))
    if id_concepto is not None:
        partes.append("a.id_concepto_asiento = %s")
        params.append(id_concepto)

    codigo_mov = filtros.get("codigo_movimiento")
    if codigo_mov not in (None, ""):
        partes.append("a.codigo_movimiento = %s")
        params.append(str_or_default(codigo_mov))

    nros = filtros.get("nros_asiento") or []
    if nros:
        placeholders = ",".join(["%s"] * len(nros))
        partes.append(f"a.nro_asiento IN ({placeholders})")
        params.extend(nros)

    anulado = filtros.get("anulado")
    if anulado in ("Si", "No"):
        if anulado == "Si":
            partes.append("COALESCE(a.anulado,'No') = 'Si'")
        else:
            partes.append("COALESCE(a.anulado,'No') <> 'Si'")

    q = (filtros.get("q") or "").strip()
    if q:
        partes.append("a.desc_asiento LIKE %s")
        params.append(f"%{q}%")

    tipo_comp = (filtros.get("tipo_comprobante") or "").strip()
    if tipo_comp:
        partes.append(
            """(
                EXISTS (
                    SELECT 1 FROM cuentaproveedor cpf
                    WHERE cpf.CodigoMovimiento = a.codigo_movimiento
                      AND a.codigo_movimiento <> 0
                      AND cpf.TipoComprobante = %s
                )
                OR EXISTS (
                    SELECT 1 FROM cuentacliente ccf
                    WHERE ccf.CodigoMovimiento = a.codigo_movimiento
                      AND a.codigo_movimiento <> 0
                      AND ccf.TipoComprobante = %s
                )
            )"""
        )
        params.extend([tipo_comp, tipo_comp])

    return " AND ".join(partes), params


def _sql_agrupado(where_sql: str) -> str:
    return f"""
        SELECT
            a.id_ejercicio,
            a.nro_asiento,
            MIN(a.fecha_asiento) AS fecha_asiento,
            MIN(a.id_concepto_asiento) AS id_concepto_asiento,
            MIN(a.desc_concepto_asiento) AS desc_concepto_asiento,
            MIN(a.codigo_movimiento) AS codigo_movimiento,
            MIN(a.desc_asiento) AS desc_asiento,
            COUNT(*) AS cant_lineas,
            SUM(COALESCE(a.debe_asiento, 0)) AS total_debe,
            SUM(COALESCE(a.haber_asiento, 0)) AS total_haber,
            MAX(COALESCE(a.anulado, 'No')) AS anulado,
            COALESCE(MAX(cp.TipoComprobante), MAX(cc.TipoComprobante)) AS tipo_comprobante,
            CASE
                WHEN MAX(cp.CodigoMovimiento) IS NOT NULL THEN 'proveedor'
                WHEN MAX(cc.CodigoMovimiento) IS NOT NULL THEN 'cliente'
                ELSE ''
            END AS origen
        FROM cont_asiento a
        LEFT JOIN cuentaproveedor cp
            ON cp.CodigoMovimiento = a.codigo_movimiento AND a.codigo_movimiento <> 0
        LEFT JOIN cuentacliente cc
            ON cc.CodigoMovimiento = a.codigo_movimiento AND a.codigo_movimiento <> 0
        WHERE {where_sql}
        GROUP BY a.id_ejercicio, a.nro_asiento
    """


def _item_desde_fila(row: dict) -> dict:
    return {
        "id_ejercicio": to_int_or_none(row.get("id_ejercicio")),
        "nro_asiento": to_int_or_none(row.get("nro_asiento")),
        "fecha_asiento": _fecha_ui(row.get("fecha_asiento")),
        "id_concepto_asiento": to_int_or_none(row.get("id_concepto_asiento")),
        "desc_concepto_asiento": str_or_default(row.get("desc_concepto_asiento")),
        "codigo_movimiento": str_or_default(row.get("codigo_movimiento")),
        "desc_asiento": str_or_default(row.get("desc_asiento")),
        "cant_lineas": int(row.get("cant_lineas") or 0),
        "total_debe": str(_r2(row.get("total_debe"))),
        "total_haber": str(_r2(row.get("total_haber"))),
        "anulado": str_or_default(row.get("anulado"), "No"),
        "tipo_comprobante": str_or_default(row.get("tipo_comprobante")),
        "origen": str_or_default(row.get("origen")),
    }


def listar_conceptos(base_empresa: str, id_ejercicio: int) -> list[dict]:
    """Conceptos distintos del ejercicio para filtro UI."""
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cur = conn.cursor(MySQLdb.cursors.DictCursor)
        try:
            cur.execute(
                """
                SELECT DISTINCT id_concepto_asiento, desc_concepto_asiento
                FROM cont_asiento
                WHERE id_ejercicio = %s AND id_concepto_asiento IS NOT NULL
                ORDER BY desc_concepto_asiento, id_concepto_asiento
                """,
                (id_ejercicio,),
            )
            rows = cur.fetchall()
        finally:
            cur.close()
    return [
        {
            "id_concepto_asiento": to_int_or_none(r.get("id_concepto_asiento")),
            "desc_concepto_asiento": str_or_default(r.get("desc_concepto_asiento")),
        }
        for r in rows
    ]


def listar_asientos(base_empresa: str, filtros: dict) -> dict:
    """Lista asientos agrupados por (id_ejercicio, nro_asiento) con paginación (500)."""
    where_sql, params = _where_listar(filtros)
    page = max(1, to_int_or_none(filtros.get("page")) or 1)
    page_size = min(500, max(1, to_int_or_none(filtros.get("page_size")) or 500))
    offset = (page - 1) * page_size

    sql_base = _sql_agrupado(where_sql)
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cur = conn.cursor(MySQLdb.cursors.DictCursor)
        try:
            cur.execute(f"SELECT COUNT(*) AS total FROM ({sql_base}) AS sub", params)
            total_row = cur.fetchone() or {}
            total = int(total_row.get("total") or 0)

            cur.execute(
                f"{sql_base} ORDER BY a.nro_asiento DESC LIMIT %s OFFSET %s",
                params + [page_size, offset],
            )
            filas = cur.fetchall()
        finally:
            cur.close()

    return {
        "items": [_item_desde_fila(r) for r in filas],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def _where_claves_asientos(asientos: list[tuple[int, int]]) -> tuple[str, list[int]]:
    """Construye un filtro agrupado por ejercicio para un lote de asientos."""
    por_ejercicio: dict[int, list[int]] = defaultdict(list)
    for id_ejercicio, nro_asiento in asientos:
        por_ejercicio[id_ejercicio].append(nro_asiento)

    partes: list[str] = []
    params: list[int] = []
    for id_ejercicio, nros_asiento in sorted(por_ejercicio.items()):
        placeholders = ",".join(["%s"] * len(nros_asiento))
        partes.append(f"(id_ejercicio = %s AND nro_asiento IN ({placeholders}))")
        params.extend([id_ejercicio, *nros_asiento])
    return " OR ".join(partes), params


def _cargar_renglones_asientos(
    dict_cur,
    asientos: list[tuple[int, int]],
    *,
    for_update: bool = False,
) -> list[dict]:
    """Carga renglones de todos los asientos en consultas agrupadas (no N+1)."""
    if not asientos:
        return []

    where_sql, params = _where_claves_asientos(asientos)
    lock = " FOR UPDATE" if for_update else ""
    dict_cur.execute(
        f"""
        SELECT id_ejercicio, nro_asiento, id_pc, id_periodo, fecha_asiento,
               codigo_movimiento, debe_asiento, haber_asiento, anulado,
               id_concepto_asiento, desc_concepto_asiento, desc_asiento,
               desc_renglon_asiento, saldo_asiento
        FROM cont_asiento
        WHERE {where_sql}
        ORDER BY id_ejercicio, nro_asiento, id_pc
        {lock}
        """,
        params,
    )
    filas = list(dict_cur.fetchall() or [])
    existentes = {
        (
            to_int_or_none(r.get("id_ejercicio")),
            to_int_or_none(r.get("nro_asiento")),
        )
        for r in filas
    }
    for id_ej, nro in asientos:
        if (id_ej, nro) not in existentes:
            raise EliminacionAsientosError(
                f"No existe el asiento ejercicio {id_ej} nro {nro}."
            )
    return filas


def preview_eliminacion(base_empresa: str, asientos: list[dict]) -> dict:
    """Vista previa agregada de impacto antes de eliminar, sin bloquear ni escribir."""
    claves = _normalizar_asientos(asientos)
    where_sql, params = _where_claves_asientos(claves)
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        dict_cur = conn.cursor(MySQLdb.cursors.DictCursor)
        try:
            # La consulta agrupada sustituye una consulta por asiento. El preview
            # solo necesita totales, no el detalle completo de cada renglón.
            dict_cur.execute(
                f"""
                SELECT
                    COUNT(*) AS total_renglones,
                    COUNT(DISTINCT id_ejercicio, id_pc) AS cuentas_impactadas,
                    COUNT(DISTINCT id_ejercicio, id_pc, id_periodo) AS periodos_impactados,
                    COUNT(DISTINCT CASE
                        WHEN COALESCE(anulado, 'No') = 'Si'
                        THEN CONCAT(id_ejercicio, ':', nro_asiento)
                    END) AS asientos_con_renglones_anulados
                FROM cont_asiento
                WHERE {where_sql}
                """,
                params,
            )
            resumen = dict_cur.fetchone() or {}

            # Se conserva la validación de existencia sin cargar los renglones.
            dict_cur.execute(
                f"""
                SELECT DISTINCT id_ejercicio, nro_asiento
                FROM cont_asiento
                WHERE {where_sql}
                """,
                params,
            )
            existentes = {
                (
                    to_int_or_none(fila.get("id_ejercicio")),
                    to_int_or_none(fila.get("nro_asiento")),
                )
                for fila in dict_cur.fetchall()
            }
        finally:
            dict_cur.close()

    faltantes = [clave for clave in claves if clave not in existentes]
    if faltantes:
        id_ejercicio, nro_asiento = faltantes[0]
        raise EliminacionAsientosError(
            f"No existe el asiento ejercicio {id_ejercicio} nro {nro_asiento}."
        )

    asientos_anulados = int(resumen.get("asientos_con_renglones_anulados") or 0)
    avisos = []
    if asientos_anulados:
        avisos.append(
            f"{asientos_anulados} asiento(s) incluye(n) renglones ya anulados; se eliminarán igualmente."
        )

    return {
        "asientos_solicitados": len(claves),
        "total_renglones": int(resumen.get("total_renglones") or 0),
        "cuentas_impactadas": int(resumen.get("cuentas_impactadas") or 0),
        "periodos_impactados": int(resumen.get("periodos_impactados") or 0),
        "avisos": avisos,
    }


def _saldo_teorico_ejercicio(dict_cur, id_pc: int, id_ejercicio: int) -> Decimal:
    dict_cur.execute(
        """
        SELECT
            CASE pc.saldo_pc
                WHEN 'Deudor' THEN SUM(COALESCE(a.debe_asiento, 0) - COALESCE(a.haber_asiento, 0))
                WHEN 'Acreedor' THEN SUM(COALESCE(a.haber_asiento, 0) - COALESCE(a.debe_asiento, 0))
                ELSE 0
            END AS saldo_teorico
        FROM cont_asiento a
        JOIN cont_pc pc ON pc.id_pc = a.id_pc
        WHERE a.id_ejercicio = %s AND a.id_pc = %s
          AND COALESCE(a.anulado, 'No') <> 'Si'
        GROUP BY a.id_pc, a.id_ejercicio, pc.saldo_pc
        """,
        (id_ejercicio, id_pc),
    )
    row = dict_cur.fetchone()
    if not row or row.get("saldo_teorico") is None:
        return Decimal("0")
    return _r2(row.get("saldo_teorico"))


def _saldo_teorico_periodo(dict_cur, id_pc: int, id_ejercicio: int, id_periodo: int) -> Decimal:
    dict_cur.execute(
        """
        SELECT
            CASE pc.saldo_pc
                WHEN 'Deudor' THEN SUM(COALESCE(a.debe_asiento, 0) - COALESCE(a.haber_asiento, 0))
                WHEN 'Acreedor' THEN SUM(COALESCE(a.haber_asiento, 0) - COALESCE(a.debe_asiento, 0))
                ELSE 0
            END AS saldo_teorico
        FROM cont_asiento a
        JOIN cont_pc pc ON pc.id_pc = a.id_pc
        WHERE a.id_ejercicio = %s AND a.id_pc = %s AND a.id_periodo = %s
          AND COALESCE(a.anulado, 'No') <> 'Si'
        GROUP BY a.id_pc, a.id_ejercicio, a.id_periodo, pc.saldo_pc
        """,
        (id_ejercicio, id_pc, id_periodo),
    )
    row = dict_cur.fetchone()
    if not row or row.get("saldo_teorico") is None:
        return Decimal("0")
    return _r2(row.get("saldo_teorico"))


def _fila_saldo_ejercicio_existe(cur, id_pc: int, id_ejercicio: int) -> bool:
    cur.execute(
        "SELECT 1 FROM cont_ejercicio_saldo_cta WHERE id_pc=%s AND id_ejercicio=%s LIMIT 1",
        (id_pc, id_ejercicio),
    )
    return cur.fetchone() is not None


def _fila_saldo_periodo_existe(cur, id_pc: int, id_ejercicio: int, id_periodo: int) -> bool:
    cur.execute(
        """SELECT 1 FROM cont_periodo_saldo_cta
           WHERE id_pc=%s AND id_ejercicio=%s AND id_periodo=%s LIMIT 1""",
        (id_pc, id_ejercicio, id_periodo),
    )
    return cur.fetchone() is not None


def _recalcular_saldos(
    cur,
    dict_cur,
    cuentas_ej: set[tuple[int, int]],
    cuentas_per: set[tuple[int, int, int]],
) -> Iterator[dict]:
    """Actualiza o inserta filas de saldo; yield eventos progress y return del total tocado.

    Uso::

        gen = _recalcular_saldos(...)
        try:
            while True:
                yield next(gen)
        except StopIteration as fin:
            total = fin.value or 0
    """
    total = len(cuentas_ej) + len(cuentas_per)
    intervalo = 5 if total > 100 else 1
    current = 0

    yield _evento_progreso(
        phase="recalc",
        current=0,
        total=max(total, 1),
        label="Recalculando saldos…",
    )

    if total == 0:
        return 0

    for id_pc, id_ej in sorted(cuentas_ej):
        saldo = _saldo_teorico_ejercicio(dict_cur, id_pc, id_ej)
        if _fila_saldo_ejercicio_existe(cur, id_pc, id_ej):
            cur.execute(
                "UPDATE cont_ejercicio_saldo_cta SET saldo_ejercicio_cta=%s WHERE id_pc=%s AND id_ejercicio=%s",
                (str(saldo), id_pc, id_ej),
            )
        else:
            cur.execute(
                "INSERT INTO cont_ejercicio_saldo_cta (id_pc, id_ejercicio, saldo_ejercicio_cta) VALUES (%s,%s,%s)",
                (id_pc, id_ej, str(saldo)),
            )
        current += 1
        if current == 1 or current == total or current % intervalo == 0:
            yield _evento_progreso(
                phase="recalc",
                current=current,
                total=total,
                label=f"Ejercicio · cuenta {id_pc}",
            )

    for id_pc, id_ej, id_per in sorted(cuentas_per):
        saldo = _saldo_teorico_periodo(dict_cur, id_pc, id_ej, id_per)
        if _fila_saldo_periodo_existe(cur, id_pc, id_ej, id_per):
            cur.execute(
                """UPDATE cont_periodo_saldo_cta SET saldo_periodo_cta=%s
                   WHERE id_pc=%s AND id_ejercicio=%s AND id_periodo=%s""",
                (str(saldo), id_pc, id_ej, id_per),
            )
        else:
            cur.execute(
                """INSERT INTO cont_periodo_saldo_cta
                   (id_pc, id_ejercicio, id_periodo, saldo_periodo_cta) VALUES (%s,%s,%s,%s)""",
                (id_pc, id_ej, id_per, str(saldo)),
            )
        current += 1
        if current == 1 or current == total or current % intervalo == 0:
            yield _evento_progreso(
                phase="recalc",
                current=current,
                total=total,
                label=f"Período {id_per} · cuenta {id_pc}",
            )

    return current


def _evento_progreso(
    *,
    phase: str,
    current: int,
    total: int,
    label: str = "",
) -> dict:
    return {
        "type": "progress",
        "phase": phase,
        "current": current,
        "total": total,
        "label": label,
    }


def _resumen_asiento_json(renglones: list[dict]) -> str:
    payload = []
    for r in renglones:
        payload.append(
            {
                "id_pc": to_int_or_none(r.get("id_pc")),
                "id_periodo": to_int_or_none(r.get("id_periodo")),
                "debe_asiento": str(_r2(r.get("debe_asiento"))),
                "haber_asiento": str(_r2(r.get("haber_asiento"))),
                "codigo_movimiento": str_or_default(r.get("codigo_movimiento")),
                "anulado": str_or_default(r.get("anulado"), "No"),
                "desc_renglon_asiento": str_or_default(r.get("desc_renglon_asiento")),
            }
        )
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _eliminar_asientos_iter(
    base_empresa: str,
    asientos: list[dict],
    usuario: str,
    *,
    tiene_permiso_corregir: bool = False,
) -> Iterator[dict]:
    """Generador interno: eventos progress y result al eliminar asientos.

    Sin backup de tablas: la atomicidad la da una única transacción MySQL
    (DELETE + recálculo de saldos + log). La operación no es revertible por diseño.
    """
    if not tiene_permiso_corregir:
        raise EliminacionAsientosError(
            "No tiene permiso para eliminar asientos contables (contabilidad.auditoria.corregir)."
        )

    claves = _normalizar_asientos(asientos)
    total_asientos = len(claves)
    ahora = timezone.now()
    timestamp = timezone.localtime(ahora).strftime("%Y%m%d_%H%M%S")
    lote_id = f"L{timestamp}-{uuid.uuid4().hex[:8]}"
    pool = get_mysql_pool()

    filas_borradas = 0
    cuentas_recalculadas = 0
    asientos_eliminados = 0
    intervalo_progreso = 5 if total_asientos > 100 else 1

    # Primer evento ya: evita «Failed to fetch» por timeout sin primer byte.
    yield _evento_progreso(
        phase="prepare",
        current=0,
        total=total_asientos,
        label="Preparando eliminación…",
    )

    with pool.get_connection(base_empresa) as conn:
        try:
            conn.autocommit(False)
            cur = conn.cursor()
            dict_cur = conn.cursor(MySQLdb.cursors.DictCursor)
            fecha_db = timezone.localtime(ahora).replace(tzinfo=None)

            renglones = _cargar_renglones_asientos(dict_cur, claves, for_update=True)

            cuentas_ej: set[tuple[int, int]] = set()
            cuentas_per: set[tuple[int, int, int]] = set()
            agrupados: dict[tuple[int, int], list[dict]] = defaultdict(list)
            for r in renglones:
                clave = (
                    to_int_or_none(r.get("id_ejercicio")) or 0,
                    to_int_or_none(r.get("nro_asiento")) or 0,
                )
                agrupados[clave].append(r)
                id_pc = to_int_or_none(r.get("id_pc"))
                id_ej = to_int_or_none(r.get("id_ejercicio"))
                id_per = to_int_or_none(r.get("id_periodo"))
                if id_pc is not None and id_ej is not None:
                    cuentas_ej.add((id_pc, id_ej))
                if id_pc is not None and id_ej is not None and id_per is not None:
                    cuentas_per.add((id_pc, id_ej, id_per))

            cur.execute(
                """INSERT INTO cont_audit_correccion_lote
                   (lote_id, base_empresa, dry_run_id, config_hash, usuario, fecha,
                    estado, reapertura_flag, autorizador, backups_json)
                   VALUES (%s,%s,%s,%s,%s,%s,'aplicado',0,%s,%s)""",
                (
                    lote_id,
                    base_empresa,
                    CHECK_ID_ELIMINACION,
                    CONFIG_HASH_ELIMINACION,
                    usuario,
                    fecha_db,
                    usuario,
                    "{}",
                ),
            )

            yield _evento_progreso(
                phase="delete",
                current=0,
                total=total_asientos,
                label="Borrando asientos…",
            )

            # DELETE por ejercicio en lotes (mucho más rápido que 1 DELETE por asiento).
            por_ejercicio: dict[int, list[int]] = defaultdict(list)
            for id_ej, nro in claves:
                por_ejercicio[id_ej].append(nro)

            procesados = 0
            for id_ej, nros in sorted(por_ejercicio.items()):
                for i in range(0, len(nros), 50):
                    chunk = nros[i : i + 50]
                    placeholders = ",".join(["%s"] * len(chunk))
                    cur.execute(
                        f"DELETE FROM cont_asiento WHERE id_ejercicio=%s AND nro_asiento IN ({placeholders})",
                        [id_ej, *chunk],
                    )
                    filas_borradas += cur.rowcount
                    procesados += len(chunk)
                    asientos_eliminados = procesados
                    if procesados == total_asientos or procesados % max(intervalo_progreso, 1) == 0:
                        yield _evento_progreso(
                            phase="delete",
                            current=procesados,
                            total=total_asientos,
                            label=f"Ejercicio {id_ej} · {procesados}/{total_asientos}",
                        )

            gen_recalc = _recalcular_saldos(cur, dict_cur, cuentas_ej, cuentas_per)
            try:
                while True:
                    yield next(gen_recalc)
            except StopIteration as fin:
                cuentas_recalculadas = int(fin.value or 0)

            for (id_ej, nro), filas_asiento in sorted(agrupados.items()):
                item_log = {
                    "check_id": CHECK_ID_ELIMINACION,
                    "tabla": "cont_asiento",
                    "clave": {"id_ejercicio": id_ej, "nro_asiento": nro},
                }
                _insertar_log_detalle(
                    cur,
                    lote_id,
                    item_log,
                    _resumen_asiento_json(filas_asiento),
                    None,
                    usuario,
                    fecha_db,
                )

            conn.commit()
        except EliminacionAsientosError:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.exception(
                "eliminar_asientos: error transaccional base=%s lote=%s",
                base_empresa,
                lote_id,
            )
            raise EliminacionAsientosError(f"Error al eliminar asientos: {exc}") from exc
        finally:
            try:
                conn.autocommit(True)
            except Exception:
                pass

    payload = {
        "ok": True,
        "lote_id": lote_id,
        "filas_borradas": filas_borradas,
        "asientos_eliminados": asientos_eliminados,
        "backups": {},
        "cuentas_recalculadas": cuentas_recalculadas,
        "fecha": _fecha_db_ui(ahora),
    }
    yield {"type": "result", "payload": payload}


def eliminar_asientos(
    base_empresa: str,
    asientos: list[dict],
    usuario: str,
    *,
    tiene_permiso_corregir: bool = False,
    on_progress: Callable[[dict], None] | None = None,
) -> dict:
    """Elimina asientos completos y recalcula saldos impactados en transacción."""
    resultado: dict | None = None
    for evento in _eliminar_asientos_iter(
        base_empresa,
        asientos,
        usuario,
        tiene_permiso_corregir=tiene_permiso_corregir,
    ):
        if evento.get("type") == "progress" and on_progress is not None:
            on_progress(evento)
        elif evento.get("type") == "result":
            resultado = evento["payload"]
    if resultado is None:
        raise EliminacionAsientosError("No se obtuvo resultado de la eliminación.")
    return resultado
