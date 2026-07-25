"""Cola Finanzas, hold de preparación y resolución de crédito."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool, mysql_cursor
from core.utils.administranet_types import str_or_default, to_int_or_none

from ecom.permissions import puede_aprobar_credito
from ecom.services.ecom_config_mysql import (
    credito_hold_prep_activo,
    credito_pedidos_activo,
)
from ecom.services.mayorista_credito import NO_AUTORIZADO

logger = logging.getLogger(__name__)

ESTADO_NEUTRO = "-"
ESTADO_PENDIENTE = "pendiente"
ESTADO_APROBADO = "aprobado"
ESTADO_RECHAZADO = "rechazado"

ACCION_SOLICITUD = "solicitud"
ACCION_APROBADO = "aprobado"
ACCION_RECHAZADO = "rechazado"


def _ahora() -> datetime:
    return datetime.now()


def _insertar_evento_credito(
    cursor,
    *,
    cod_mov: int,
    accion: str,
    cod_solicita: Optional[int],
    cod_resuelve: Optional[int],
    motivo: str,
) -> None:
    cursor.execute(
        """
        INSERT INTO ecom_credito_evento
            (codigo_movimiento, accion, cod_solicita, cod_resuelve, motivo, creado_en)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            cod_mov,
            str_or_default(accion, "-"),
            cod_solicita,
            cod_resuelve,
            str_or_default(motivo, "-"),
            _ahora(),
        ),
    )


def aplicar_estado_credito_checkout(
    cursor,
    base_empresa: str,
    *,
    cod_mov: int,
    cod_solicita: Optional[int],
    autorizacion_sistema: str,
) -> str:
    """
    Tras alta PED con evaluación unificada: cola Finanzas + hold prep si No Autorizado.
    """
    if not credito_pedidos_activo(base_empresa):
        return ESTADO_NEUTRO

    auth = (autorizacion_sistema or "").strip()
    if auth != NO_AUTORIZADO:
        return ESTADO_NEUTRO

    hold = "Si" if credito_hold_prep_activo(base_empresa) else "No"
    cursor.execute(
        """
        UPDATE comp_ped
        SET estado_credito_finanzas = %s,
            credito_hold_prep = %s
        WHERE CodigoMovimiento = %s AND TipoComprobante = 'PED'
        """,
        (ESTADO_PENDIENTE, hold, cod_mov),
    )
    _insertar_evento_credito(
        cursor,
        cod_mov=cod_mov,
        accion=ACCION_SOLICITUD,
        cod_solicita=to_int_or_none(cod_solicita),
        cod_resuelve=None,
        motivo="Solicitud aprobación Finanzas por crédito",
    )
    return ESTADO_PENDIENTE


def _fetch_ped_credito(base_empresa: str, cod_mov: int) -> Optional[Dict[str, Any]]:
    sql = """
        SELECT
            cp.CodigoMovimiento,
            cp.Codigo,
            TRIM(COALESCE(cp.estado_credito_finanzas, '-')) AS estado_credito_finanzas,
            TRIM(COALESCE(cp.credito_hold_prep, 'No')) AS credito_hold_prep,
            TRIM(COALESCE(cp.autorizacion_sistema, '')) AS autorizacion_sistema,
            cp.Anulado
        FROM comp_ped cp
        WHERE cp.CodigoMovimiento = %s AND cp.TipoComprobante = 'PED'
        LIMIT 1
    """
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(sql, (cod_mov,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as exc:
        logger.warning("_fetch_ped_credito (%s, %s): %s", base_empresa, cod_mov, exc)
        return None


def puede_avanzar_a_preparacion(cursor, cod_mov: int) -> Tuple[bool, str]:
    """
    Gate Synap: rechaza transición a preparación si ``credito_hold_prep='Si'``.
    """
    cursor.execute(
        """
        SELECT TRIM(COALESCE(credito_hold_prep, 'No')) AS credito_hold_prep
        FROM comp_ped
        WHERE CodigoMovimiento = %s AND TipoComprobante = 'PED'
        LIMIT 1
        """,
        (cod_mov,),
    )
    row = cursor.fetchone()
    if not row:
        return True, ""
    hold = row.get("credito_hold_prep") if isinstance(row, dict) else row[0]
    if str(hold or "").strip().lower() in ("si", "sí"):
        return (
            False,
            "El pedido está retenido por crédito pendiente de aprobación Finanzas.",
        )
    return True, ""


def puede_aprobar_credito_pedido(
    base_empresa: str,
    sess_user: Dict[str, Any],
    ped: Dict[str, Any],
) -> bool:
    if not credito_pedidos_activo(base_empresa):
        return False
    if not puede_aprobar_credito(sess_user):
        return False
    estado = str(ped.get("estado_credito_finanzas") or ESTADO_NEUTRO).strip().lower()
    return estado == ESTADO_PENDIENTE


def resolver_finanzas(
    base_empresa: str,
    cod_mov: int,
    accion: str,
    cod_resuelve: int,
    motivo: str,
    *,
    sess_user: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Aprueba o rechaza un PED en cola Finanzas. MUST NOT mutar ``cliente.Credito``."""
    if not credito_pedidos_activo(base_empresa):
        return False, "El workflow de crédito no está activo.", None

    if sess_user and not puede_aprobar_credito(sess_user):
        return False, "No tiene permiso para aprobar crédito (finance.credito.aprobar).", None

    acc = (accion or "").strip().lower()
    if acc not in ("aprobar", "rechazar"):
        return False, "Acción inválida. Use aprobar o rechazar.", None

    ped = _fetch_ped_credito(base_empresa, cod_mov)
    if not ped:
        return False, "Pedido no encontrado.", None
    if (ped.get("Anulado") or "").strip().lower() in ("si", "sí"):
        return False, "El pedido está anulado.", None

    estado = str(ped.get("estado_credito_finanzas") or ESTADO_NEUTRO).strip().lower()
    if estado != ESTADO_PENDIENTE:
        return False, "El pedido no está pendiente de aprobación Finanzas.", None

    if acc == "rechazar" and not str(motivo or "").strip():
        return False, "Indique el motivo del rechazo.", None

    motivo_txt = str_or_default(motivo, "-")
    resuelve = to_int_or_none(cod_resuelve)
    if resuelve is None:
        return False, "Resolutor inválido.", None

    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            try:
                conn.autocommit(False)
                if acc == "rechazar":
                    cursor.execute(
                        """
                        UPDATE comp_ped
                        SET estado_credito_finanzas = %s
                        WHERE CodigoMovimiento = %s AND TipoComprobante = 'PED'
                        """,
                        (ESTADO_RECHAZADO, cod_mov),
                    )
                    _insertar_evento_credito(
                        cursor,
                        cod_mov=cod_mov,
                        accion=ACCION_RECHAZADO,
                        cod_solicita=None,
                        cod_resuelve=resuelve,
                        motivo=motivo_txt,
                    )
                    conn.commit()
                    return True, "Crédito rechazado.", {
                        "estado_credito_finanzas": ESTADO_RECHAZADO,
                    }

                cursor.execute(
                    """
                    UPDATE comp_ped
                    SET estado_credito_finanzas = %s,
                        autorizacion_sistema = 'Autorizado',
                        credito_hold_prep = 'No'
                    WHERE CodigoMovimiento = %s AND TipoComprobante = 'PED'
                    """,
                    (ESTADO_APROBADO, cod_mov),
                )
                _insertar_evento_credito(
                    cursor,
                    cod_mov=cod_mov,
                    accion=ACCION_APROBADO,
                    cod_solicita=None,
                    cod_resuelve=resuelve,
                    motivo=motivo_txt,
                )
                conn.commit()
                return True, "Crédito aprobado; pedido liberado.", {
                    "estado_credito_finanzas": ESTADO_APROBADO,
                    "autorizacion_sistema": "Autorizado",
                }
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
                try:
                    conn.autocommit(True)
                except Exception:
                    pass
    except Exception as exc:
        logger.exception("resolver_finanzas cod_mov=%s: %s", cod_mov, exc)
        return False, "No se pudo resolver la aprobación Finanzas.", None


def listar_pendientes_finanzas(
    base_empresa: str,
    *,
    dias: int = 60,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """PED con cola Finanzas pendiente."""
    if not credito_pedidos_activo(base_empresa):
        return []

    params: List[Any] = [ESTADO_PENDIENTE, max(1, min(int(dias), 365))]
    params.append(max(1, min(int(limit), 500)))
    sql = """
        SELECT
            cp.CodigoMovimiento,
            cp.NroComprobante,
            cp.CodViajante,
            DATE_FORMAT(cp.Fecha, '%%d/%%m/%%Y') AS fecha,
            TRIM(COALESCE(cp.estado_credito_finanzas, '-')) AS estado_credito_finanzas,
            cp.ImporteVenta,
            COALESCE(c.nombre_cliente, '') AS nombre_cliente,
            cp.Codigo AS id_cliente
        FROM comp_ped cp
        LEFT JOIN cliente c ON c.Codigo = cp.Codigo
        WHERE cp.TipoComprobante = 'PED'
          AND cp.estado_credito_finanzas = %s
          AND COALESCE(cp.Anulado, 'No') = 'No'
          AND cp.Fecha >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY cp.Fecha DESC, cp.CodigoMovimiento DESC
        LIMIT %s
    """
    out: List[Dict[str, Any]] = []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(sql, params)
            for row in cursor.fetchall() or []:
                out.append(dict(row))
    except Exception as exc:
        logger.warning("listar_pendientes_finanzas: %s", exc)
    return out
