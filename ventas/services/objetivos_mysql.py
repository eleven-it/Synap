# -*- coding: utf-8 -*-
"""Lectura/escritura de objetivos de venta (cabecera + detalle) en MySQL AdministraNET."""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
from reports.services.connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)


def _table_exists(cursor, name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = %s
        """,
        [name],
    )
    row = cursor.fetchone()
    return bool(row and int(row[0] or 0) > 0)


def _ensure_descripcion_column_viajantes_periodo(conn, cursor) -> None:
    """
    Bases que crearon la tabla antes de Synap 2026 pueden no tener `descripcion`.
    Alineado con core/services/legacy_mysql_schema/catalog.run_viajantes_objetivos_ventas_mysql.
    """
    from core.services.legacy_mysql_schema.helpers import columna_existe, nombre_tabla_real

    if not _table_exists(cursor, "viajantes_objetivos_periodo"):
        return
    tbl = nombre_tabla_real(cursor, "viajantes_objetivos_periodo")
    if not tbl or columna_existe(cursor, tbl, "descripcion"):
        return
    try:
        cursor.execute(
            """
            ALTER TABLE `{}`
            ADD COLUMN descripcion VARCHAR(120) NOT NULL DEFAULT '-'
                COMMENT 'Etiqueta del período (ej. mes y año); "-" si no se informa'
            AFTER fecha_hasta
            """.format(
                tbl.replace("`", "``"),
            )
        )
        conn.commit()
        logger.info(
            "viajantes_objetivos_periodo: columna descripcion añadida automáticamente (tabla %s).",
            tbl,
        )
    except Exception as e:
        err_no = getattr(e, "args", [None])[0]
        msg = str(e).lower()
        if err_no == 1060 or "duplicate column" in msg:
            conn.rollback()
            return
        raise


def listar_periodos_objetivos(
    base_empresa: str,
    solo_activos: bool = True,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Lista cabeceras de intervalo (opcionalmente excluye anulados)."""
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                if not _table_exists(cursor, "viajantes_objetivos_periodo"):
                    return (
                        False,
                        "La tabla viajantes_objetivos_periodo no existe. Ejecute la migración MySQL (legacy schema).",
                        [],
                    )
                _ensure_descripcion_column_viajantes_periodo(conn, cursor)
                where = "WHERE COALESCE(anulado, 'No') = 'No'" if solo_activos else ""
                cursor.execute(
                    f"""
                    SELECT id, fecha_desde, fecha_hasta, anulado, descripcion
                    FROM viajantes_objetivos_periodo
                    {where}
                    ORDER BY fecha_desde DESC, id DESC
                    """
                )
                rows = []
                for r in cursor.fetchall():
                    fd = r[1]
                    fh = r[2]
                    if isinstance(fd, datetime):
                        fd = fd.date()
                    if isinstance(fh, datetime):
                        fh = fh.date()
                    desc_raw = r[4]
                    rows.append(
                        {
                            "id": int(r[0]),
                            "fecha_desde": fd if isinstance(fd, date) else None,
                            "fecha_hasta": fh if isinstance(fh, date) else None,
                            "anulado": (r[3] or "No").strip(),
                            "descripcion": str_or_default(desc_raw, "-"),
                        }
                    )
                return True, "", rows
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("listar_periodos_objetivos: %s", e)
        return False, str(e), []


def obtener_periodo_objetivos(
    base_empresa: str,
    id_periodo: int,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                if not _table_exists(cursor, "viajantes_objetivos_periodo"):
                    return False, "La tabla viajantes_objetivos_periodo no existe.", None
                _ensure_descripcion_column_viajantes_periodo(conn, cursor)
                cursor.execute(
                    """
                    SELECT id, fecha_desde, fecha_hasta, anulado, descripcion
                    FROM viajantes_objetivos_periodo
                    WHERE id = %s
                    LIMIT 1
                    """,
                    [int(id_periodo)],
                )
                r = cursor.fetchone()
                if not r:
                    return True, "", None
                fd = r[1]
                fh = r[2]
                if isinstance(fd, datetime):
                    fd = fd.date()
                if isinstance(fh, datetime):
                    fh = fh.date()
                desc_raw = r[4]
                return (
                    True,
                    "",
                    {
                        "id": int(r[0]),
                        "fecha_desde": fd if isinstance(fd, date) else None,
                        "fecha_hasta": fh if isinstance(fh, date) else None,
                        "anulado": (r[3] or "No").strip(),
                        "descripcion": str_or_default(desc_raw, "-"),
                    },
                )
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("obtener_periodo_objetivos: %s", e)
        return False, str(e), None


def _hay_solape_periodo_activo(
    cursor,
    fecha_desde: date,
    fecha_hasta: date,
    excluir_id: Optional[int] = None,
) -> bool:
    fd_s = fecha_desde.isoformat()
    fh_s = fecha_hasta.isoformat()
    params: List[Any] = [fh_s, fd_s]
    excl = ""
    if excluir_id is not None:
        excl = " AND id <> %s"
        params.append(int(excluir_id))
    cursor.execute(
        f"""
        SELECT COUNT(*) FROM viajantes_objetivos_periodo
        WHERE COALESCE(anulado, 'No') = 'No'
          AND fecha_desde <= %s AND fecha_hasta >= %s
          {excl}
        """,
        params,
    )
    row = cursor.fetchone()
    return bool(row and int(row[0] or 0) > 0)


def crear_periodo_objetivos(
    base_empresa: str,
    fecha_desde: date,
    fecha_hasta: date,
    descripcion: Optional[str] = None,
) -> Tuple[bool, str, Optional[int]]:
    if fecha_desde > fecha_hasta:
        return False, "La fecha desde no puede ser posterior a la fecha hasta.", None
    desc_norm = str_or_default(descripcion, "-")
    if len(desc_norm) > 120:
        desc_norm = desc_norm[:120]
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                if not _table_exists(cursor, "viajantes_objetivos_periodo"):
                    return False, "La tabla viajantes_objetivos_periodo no existe.", None
                _ensure_descripcion_column_viajantes_periodo(conn, cursor)
                if _hay_solape_periodo_activo(cursor, fecha_desde, fecha_hasta):
                    return (
                        False,
                        "Ya existe un período activo que se solapa con las fechas indicadas.",
                        None,
                    )
                fd_s = fecha_desde.isoformat()
                fh_s = fecha_hasta.isoformat()
                cursor.execute(
                    """
                    INSERT INTO viajantes_objetivos_periodo (fecha_desde, fecha_hasta, anulado, descripcion)
                    VALUES (%s, %s, 'No', %s)
                    """,
                    [fd_s, fh_s, desc_norm],
                )
                new_id = int(cursor.lastrowid)
                conn.commit()
                return True, "", new_id
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("crear_periodo_objetivos: %s", e)
        return False, str(e), None


def actualizar_descripcion_periodo_objetivos(
    base_empresa: str,
    id_periodo: int,
    descripcion: Optional[str],
) -> Tuple[bool, str, Optional[str]]:
    """
    Actualiza la etiqueta `descripcion` de un período activo (no anulado).
    Devuelve la descripción normalizada en el tercer elemento si ok.
    """
    desc_norm = str_or_default(descripcion, "-")
    if len(desc_norm) > 120:
        desc_norm = desc_norm[:120]
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                if not _table_exists(cursor, "viajantes_objetivos_periodo"):
                    return False, "La tabla viajantes_objetivos_periodo no existe.", None
                _ensure_descripcion_column_viajantes_periodo(conn, cursor)
                cursor.execute(
                    """
                    UPDATE viajantes_objetivos_periodo
                    SET descripcion = %s
                    WHERE id = %s AND COALESCE(anulado, 'No') = 'No'
                    """,
                    [desc_norm, int(id_periodo)],
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    return (
                        False,
                        "No se pudo actualizar la descripción (período inexistente o anulado).",
                        None,
                    )
                conn.commit()
                return True, "", desc_norm
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("actualizar_descripcion_periodo_objetivos: %s", e)
        return False, str(e), None


def anular_periodo_objetivos(base_empresa: str, id_periodo: int) -> Tuple[bool, str]:
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                if not _table_exists(cursor, "viajantes_objetivos_periodo"):
                    return False, "La tabla viajantes_objetivos_periodo no existe."
                cursor.execute(
                    """
                    UPDATE viajantes_objetivos_periodo
                    SET anulado = 'Si'
                    WHERE id = %s AND COALESCE(anulado, 'No') = 'No'
                    """,
                    [int(id_periodo)],
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    return False, "No se pudo anular el período (no existe o ya estaba anulado)."
                conn.commit()
                return True, ""
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("anular_periodo_objetivos: %s", e)
        return False, str(e)


def listar_grupos_objetivos(
    base_empresa: str,
    id_periodo: int,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Filas agrupables por vendedor para un id de cabecera de período.
    """
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                if not _table_exists(cursor, "viajantes_objetivos_ventas"):
                    return False, "La tabla viajantes_objetivos_ventas no existe. Ejecute la migración MySQL (legacy schema).", []

                sql = """
                    SELECT cl.Codigo,
                           COALESCE(NULLIF(TRIM(cl.nombre_cliente), ''), CONCAT('Cliente ', cl.Codigo)) AS nombre_cliente,
                           cl.CodViajante,
                           COALESCE(NULLIF(TRIM(v.Nombre), ''), CONCAT('Vendedor ', cl.CodViajante)) AS nombre_vendedor,
                           COALESCE(ov.objetivo, 0) AS objetivo,
                           COALESCE(hv.base_ventas, 0) AS base_ventas,
                           COALESCE(NULLIF(TRIM(cl.id_manual_cli), ''), '-') AS id_manual_cli
                    FROM cliente cl
                    INNER JOIN viajantes v ON v.CodViajante = cl.CodViajante
                    LEFT JOIN (
                        SELECT v1.Codigo, v1.objetivo
                        FROM viajantes_objetivos_ventas v1
                        INNER JOIN (
                            SELECT Codigo, MAX(id) AS max_id
                            FROM viajantes_objetivos_ventas
                            WHERE id_periodo = %s
                            GROUP BY Codigo
                        ) x ON x.Codigo = v1.Codigo AND x.max_id = v1.id
                    ) ov ON ov.Codigo = cl.Codigo
                    LEFT JOIN (
                        SELECT cc.Codigo,
                               SUM(
                                   CASE
                                       WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM') THEN COALESCE(cc.SubtotalDesc, 0)
                                       WHEN cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') THEN -COALESCE(cc.SubtotalDesc, 0)
                                       ELSE 0
                                   END
                               ) AS base_ventas
                        FROM cuentacliente cc
                        WHERE cc.Anulado = 'No'
                        GROUP BY cc.Codigo
                    ) hv ON hv.Codigo = cl.Codigo
                    WHERE cl.CodViajante IS NOT NULL AND cl.CodViajante <> 0
                      AND cl.Estado = 'Activo'
                      AND COALESCE(v.anulado, 'No') = 'No'
                    ORDER BY nombre_vendedor ASC, nombre_cliente ASC
                """
                cursor.execute(sql, [int(id_periodo)])
                rows = []
                totals_por_viajante: Dict[int, Decimal] = {}
                objetivos_por_viajante: Dict[int, Decimal] = {}
                raw_rows: List[Dict[str, Any]] = []
                for r in cursor.fetchall():
                    cv = int(r[2] or 0)
                    base = Decimal(str(r[5] or 0))
                    obj = Decimal(str(r[4] or 0))
                    id_manual_cli = str_or_default(r[6], "-")
                    raw_rows.append(
                        {
                            "codigo": int(r[0]),
                            "nombre_cliente": (r[1] or "").strip(),
                            "cod_viajante": cv,
                            "nombre_vendedor": (r[3] or "").strip(),
                            "objetivo": obj,
                            "base_ventas": base,
                            "id_manual_cli": id_manual_cli,
                        }
                    )
                    totals_por_viajante[cv] = totals_por_viajante.get(cv, Decimal("0")) + base
                    objetivos_por_viajante[cv] = objetivos_por_viajante.get(cv, Decimal("0")) + obj
                for item in raw_rows:
                    cv = item["cod_viajante"]
                    total_base = totals_por_viajante.get(cv, Decimal("0"))
                    peso = (item["base_ventas"] / total_base) if total_base > 0 else Decimal("0")
                    peso_f = float(peso)
                    obj_f = float(item["objetivo"])
                    rows.append(
                        {
                            "codigo": item["codigo"],
                            "id_manual_cli": item["id_manual_cli"],
                            "nombre_cliente": item["nombre_cliente"],
                            "cod_viajante": cv,
                            "nombre_vendedor": item["nombre_vendedor"],
                            "objetivo": obj_f,
                            "objetivo_entero": int(round(obj_f)),
                            "base_ventas": float(item["base_ventas"]),
                            "peso_prorrateo": peso_f,
                            "peso_prorrateo_pct": round(peso_f * 100.0, 6),
                            "objetivo_vendedor": float(objetivos_por_viajante.get(cv, Decimal("0"))),
                        }
                    )
                return True, "", rows
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("listar_grupos_objetivos: %s", e)
        return False, str(e), []


def guardar_objetivos(
    base_empresa: str,
    id_periodo: int,
    filas: List[Dict[str, Any]],
) -> Tuple[bool, str]:
    """filas: [{\"codigo\": int, \"objetivo\": number}] — persiste snapshot CodViajante desde cliente."""
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                if not _table_exists(cursor, "viajantes_objetivos_ventas"):
                    return False, "La tabla viajantes_objetivos_ventas no existe. Ejecute la migración MySQL."
                if not _table_exists(cursor, "viajantes_objetivos_periodo"):
                    return False, "La tabla viajantes_objetivos_periodo no existe. Ejecute la migración MySQL."

                cursor.execute(
                    """
                    SELECT fecha_desde, fecha_hasta, COALESCE(anulado, 'No')
                    FROM viajantes_objetivos_periodo WHERE id = %s LIMIT 1
                    """,
                    [int(id_periodo)],
                )
                pr = cursor.fetchone()
                if not pr:
                    return False, "Período no encontrado."
                fd_raw, fh_raw, anul = pr[0], pr[1], (pr[2] or "No").strip()
                if anul != "No":
                    return False, "El período está anulado; no se puede editar."

                fecha_desde = fd_raw.date() if isinstance(fd_raw, datetime) else fd_raw
                fecha_hasta = fh_raw.date() if isinstance(fh_raw, datetime) else fh_raw
                if not isinstance(fecha_desde, date) or not isinstance(fecha_hasta, date):
                    return False, "Fechas de período inválidas."
                if fecha_desde > fecha_hasta:
                    return False, "La fecha desde no puede ser posterior a la fecha hasta."

                fd_s = fecha_desde.isoformat()
                fh_s = fecha_hasta.isoformat()

                for item in filas:
                    codigo = to_int_or_none(item.get("codigo"))
                    if codigo is None:
                        continue
                    obj = to_decimal_or_none(item.get("objetivo"))
                    if obj is None:
                        obj = Decimal("0")
                    cursor.execute(
                        """
                        SELECT cl.CodViajante
                        FROM cliente cl
                        INNER JOIN viajantes v ON v.CodViajante = cl.CodViajante
                        WHERE cl.Codigo = %s
                          AND cl.Estado = 'Activo'
                          AND COALESCE(v.anulado, 'No') = 'No'
                        LIMIT 1
                        """,
                        [codigo],
                    )
                    r = cursor.fetchone()
                    if not r or r[0] is None or int(r[0] or 0) == 0:
                        continue
                    cod_v = int(r[0])
                    cursor.execute(
                        """
                        DELETE FROM viajantes_objetivos_ventas
                        WHERE Codigo = %s AND id_periodo = %s
                        """,
                        [codigo, int(id_periodo)],
                    )
                    cursor.execute(
                        """
                        INSERT INTO viajantes_objetivos_ventas
                        (Codigo, CodViajante, id_periodo, fecha_desde, fecha_hasta, objetivo)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        [codigo, cod_v, int(id_periodo), fd_s, fh_s, obj],
                    )
                conn.commit()
                return True, ""
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("guardar_objetivos: %s", e)
        return False, str(e)


def buscar_vendedores(base_empresa: str, q: str, limit: int = 30) -> Tuple[bool, List[Dict[str, Any]]]:
    q = (q or "").strip()
    if len(q) < 2:
        return True, []
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT CodViajante, Nombre FROM viajantes
                    WHERE Nombre LIKE %s
                      AND COALESCE(anulado, 'No') = 'No'
                    ORDER BY Nombre ASC
                    LIMIT %s
                    """,
                    [f"%{q}%", int(limit)],
                )
                out = [{"cod_viajante": int(r[0]), "nombre": (r[1] or "").strip()} for r in cursor.fetchall()]
                return True, out
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("buscar_vendedores: %s", e)
        return False, []
