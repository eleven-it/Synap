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
    TABLAS_BACKUP_PERMITIDAS,
    _crear_backups,
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
    """Lista asientos agrupados por (id_ejercicio, nro_asiento) con paginación."""
    where_sql, params = _where_listar(filtros)
    page = max(1, to_int_or_none(filtros.get("page")) or 1)
    page_size = min(200, max(1, to_int_or_none(filtros.get("page_size")) or 200))
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


def _cargar_renglones_asientos(
    dict_cur,
    asientos: list[tuple[int, int]],
    *,
    for_update: bool = False,
) -> list[dict]:
    lock = " FOR UPDATE" if for_update else ""
    renglones: list[dict] = []
    for id_ej, nro in asientos:
        dict_cur.execute(
            f"""
            SELECT id_ejercicio, nro_asiento, id_pc, id_periodo, fecha_asiento,
                   codigo_movimiento, debe_asiento, haber_asiento, anulado,
                   id_concepto_asiento, desc_concepto_asiento, desc_asiento,
                   desc_renglon_asiento, saldo_asiento
            FROM cont_asiento
            WHERE id_ejercicio = %s AND nro_asiento = %s
            ORDER BY id_pc
            {lock}
            """,
            (id_ej, nro),
        )
        filas = dict_cur.fetchall()
        if not filas:
            raise EliminacionAsientosError(
                f"No existe el asiento ejercicio {id_ej} nro {nro}."
            )
        renglones.extend(filas)
    return renglones


def preview_eliminacion(base_empresa: str, asientos: list[dict]) -> dict:
    """Vista previa de impacto antes de eliminar."""
    claves = _normalizar_asientos(asientos)
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        dict_cur = conn.cursor(MySQLdb.cursors.DictCursor)
        try:
            renglones = _cargar_renglones_asientos(dict_cur, claves)
        finally:
            dict_cur.close()

    cuentas: set[tuple[int, int]] = set()
    periodos: set[tuple[int, int, int]] = set()
    por_concepto: dict[str, int] = defaultdict(int)
    avisos: list[str] = []

    items_detalle: list[dict] = []
    agrupados: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for r in renglones:
        clave = (to_int_or_none(r.get("id_ejercicio")) or 0, to_int_or_none(r.get("nro_asiento")) or 0)
        agrupados[clave].append(r)
        id_pc = to_int_or_none(r.get("id_pc"))
        id_ej = to_int_or_none(r.get("id_ejercicio"))
        id_per = to_int_or_none(r.get("id_periodo"))
        if id_pc is not None and id_ej is not None:
            cuentas.add((id_pc, id_ej))
        if id_pc is not None and id_ej is not None and id_per is not None:
            periodos.add((id_pc, id_ej, id_per))
        concepto = str_or_default(r.get("desc_concepto_asiento"), "—")
        por_concepto[concepto] += 1
        if str_or_default(r.get("anulado"), "No") == "Si":
            avisos.append(
                f"Asiento {clave[1]} incluye renglones ya anulados; se eliminarán igualmente."
            )

    avisos = list(dict.fromkeys(avisos))

    for (id_ej, nro), filas_asiento in sorted(agrupados.items()):
        total_debe = sum(_r2(f.get("debe_asiento")) for f in filas_asiento)
        total_haber = sum(_r2(f.get("haber_asiento")) for f in filas_asiento)
        items_detalle.append(
            {
                "id_ejercicio": id_ej,
                "nro_asiento": nro,
                "fecha_asiento": _fecha_ui(filas_asiento[0].get("fecha_asiento")),
                "cant_lineas": len(filas_asiento),
                "total_debe": str(total_debe),
                "total_haber": str(total_haber),
                "desc_asiento": str_or_default(filas_asiento[0].get("desc_asiento")),
            }
        )

    return {
        "asientos_solicitados": len(claves),
        "total_renglones": len(renglones),
        "cuentas_impactadas": len(cuentas),
        "periodos_impactados": len(periodos),
        "por_concepto": dict(sorted(por_concepto.items(), key=lambda x: (-x[1], x[0]))),
        "avisos": avisos,
        "items": items_detalle,
        "cuentas": [{"id_pc": pc, "id_ejercicio": ej} for pc, ej in sorted(cuentas)],
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
) -> int:
    """Actualiza o inserta filas de saldo; retorna cantidad de cuentas/períodos tocados."""
    recalculadas = 0
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
        recalculadas += 1

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
        recalculadas += 1

    return recalculadas


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


def eliminar_asientos(
    base_empresa: str,
    asientos: list[dict],
    usuario: str,
    *,
    tiene_permiso_corregir: bool = False,
) -> dict:
    """Elimina asientos completos y recalcula saldos impactados en transacción."""
    if not tiene_permiso_corregir:
        raise EliminacionAsientosError(
            "No tiene permiso para eliminar asientos contables (contabilidad.auditoria.corregir)."
        )

    claves = _normalizar_asientos(asientos)
    ahora = timezone.now()
    timestamp = timezone.localtime(ahora).strftime("%Y%m%d_%H%M%S")
    lote_id = f"L{timestamp}-{uuid.uuid4().hex[:8]}"
    tablas_backup = {
        t for t in TABLAS_BACKUP_PERMITIDAS
        if t in ("cont_asiento", "cont_ejercicio_saldo_cta", "cont_periodo_saldo_cta")
    }

    pool = get_mysql_pool()
    try:
        with pool.get_connection(base_empresa) as conn:
            backups = _crear_backups(conn, tablas_backup, timestamp)
    except Exception as exc:
        logger.exception("eliminar_asientos: fallo backup base=%s", base_empresa)
        raise EliminacionAsientosError(f"No se pudo crear el backup previo: {exc}") from exc

    filas_borradas = 0
    cuentas_recalculadas = 0
    asientos_eliminados = 0

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
                    json.dumps(backups, sort_keys=True),
                ),
            )

            for id_ej, nro in claves:
                cur.execute(
                    "DELETE FROM cont_asiento WHERE id_ejercicio=%s AND nro_asiento=%s",
                    (id_ej, nro),
                )
                filas_borradas += cur.rowcount
                asientos_eliminados += 1

            cuentas_recalculadas = _recalcular_saldos(cur, dict_cur, cuentas_ej, cuentas_per)

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
            logger.exception("eliminar_asientos: error transaccional base=%s lote=%s", base_empresa, lote_id)
            raise EliminacionAsientosError(f"Error al eliminar asientos: {exc}") from exc
        finally:
            try:
                conn.autocommit(True)
            except Exception:
                pass

    return {
        "ok": True,
        "lote_id": lote_id,
        "filas_borradas": filas_borradas,
        "asientos_eliminados": asientos_eliminados,
        "backups": backups,
        "cuentas_recalculadas": cuentas_recalculadas,
        "fecha": _fecha_db_ui(ahora),
    }
