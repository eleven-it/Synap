"""Servicio de dominio: cotización dólar BCRA + historial MySQL."""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.utils import timezone

from core.mysql_pool import get_connection
from core.services.bcra_cotizacion import consultar_bcra
from core.services.cotizacion_config_resolver import resolver_cotizacion_config
from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)

logger = logging.getLogger(__name__)


def _format_fecha_es(fecha_raw: Any) -> str:
    d = to_date_or_none(fecha_raw)
    if not d:
        return "-"
    try:
        dt = datetime.strptime(d, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return str(d)


def _fetch_vigente_maestro(cursor, id_cotizacion: int) -> Optional[float]:
    try:
        cursor.execute(
            "SELECT ValorPesos FROM cotizacion WHERE id_cotizacion = %s LIMIT 1",
            (id_cotizacion,),
        )
        row = cursor.fetchone()
        if row and row[0] is not None:
            dec = to_decimal_or_none(row[0])
            if dec is not None and dec > 0:
                return float(dec)
    except Exception:
        logger.exception("Error leyendo cotizacion maestro id=%s", id_cotizacion)
    return None


def obtener_vigente(base_empresa: str, *, id_cotizacion: int = 1) -> Dict[str, Any]:
    """Valor vigente en cotizacion.ValorPesos (maestro ERP)."""
    with get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        valor = _fetch_vigente_maestro(cursor, id_cotizacion)
    return {
        "valor": valor,
        "id_cotizacion": id_cotizacion,
        "disponible": valor is not None,
    }


def sugerir(base_empresa: str, *, fecha: Optional[date] = None) -> Dict[str, Any]:
    """Sugerencia BCRA + delta % respecto al vigente local."""
    cfg = resolver_cotizacion_config(base_empresa)
    id_cotizacion = int(cfg.get("id_cotizacion") or 1)
    corte = fecha or date.today()

    vigente = obtener_vigente(base_empresa, id_cotizacion=id_cotizacion)
    vigente_val = vigente.get("valor")

    bcra = consultar_bcra(
        cfg.get("tipo_cotizacion") or "bcra_referencia",
        fecha=corte,
        timeout_seg=int(cfg.get("timeout_seg") or 5),
    )

    sugerido = bcra.get("valor")
    delta_pct: Optional[float] = None
    if sugerido is not None and vigente_val is not None and abs(vigente_val) > 1e-9:
        delta_pct = round(((float(sugerido) - float(vigente_val)) / float(vigente_val)) * 100.0, 4)

    return {
        "valor": sugerido,
        "fecha": bcra.get("fecha") or corte.isoformat(),
        "fecha_es": _format_fecha_es(bcra.get("fecha") or corte.isoformat()),
        "tipo": bcra.get("tipo") or cfg.get("tipo_cotizacion"),
        "disponible": bool(bcra.get("disponible")),
        "mensaje": bcra.get("mensaje") or "",
        "vigente": vigente_val,
        "delta_pct": delta_pct,
        "id_cotizacion": id_cotizacion,
    }


def _upsert_historial(
    cursor,
    *,
    id_cotizacion: int,
    fecha: date,
    valor: Decimal,
    tipo_cotizacion: str,
    origen: str,
    id_usuario: Optional[int],
    observacion: str,
) -> None:
    fecha_sql = to_date_or_none(fecha.isoformat())
    now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    obs = str_or_default(observacion, "-")
    tipo = str_or_default(tipo_cotizacion, "manual")
    orig = str_or_default(origen, "manual")
    uid = to_int_or_none(id_usuario)

    cursor.execute(
        """
        INSERT INTO cotizacion_historial
            (id_cotizacion, fecha, valor_pesos, tipo_cotizacion, origen, id_usuario, observacion, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            valor_pesos = VALUES(valor_pesos),
            tipo_cotizacion = VALUES(tipo_cotizacion),
            origen = VALUES(origen),
            id_usuario = VALUES(id_usuario),
            observacion = VALUES(observacion),
            created_at = VALUES(created_at)
        """,
        (id_cotizacion, fecha_sql, valor, tipo, orig, uid, obs, now),
    )


def _escribir_cotizacion(
    base_empresa: str,
    *,
    valor: float,
    origen: str,
    id_usuario: Optional[int],
    observacion: str = "-",
    fecha: Optional[date] = None,
    tipo_cotizacion: Optional[str] = None,
    id_cotizacion: int = 1,
) -> Dict[str, Any]:
    dec = to_decimal_or_none(valor)
    if dec is None or dec <= 0:
        raise ValueError("El valor de cotización debe ser un número positivo.")

    cfg = resolver_cotizacion_config(base_empresa)
    id_cot = int(id_cotizacion or cfg.get("id_cotizacion") or 1)
    tipo = tipo_cotizacion or cfg.get("tipo_cotizacion") or "manual"
    corte = fecha or date.today()

    with get_connection(base_empresa) as conn:
        conn.autocommit(False)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE cotizacion SET ValorPesos = %s WHERE id_cotizacion = %s",
                (dec, id_cot),
            )
            _upsert_historial(
                cursor,
                id_cotizacion=id_cot,
                fecha=corte,
                valor=dec,
                tipo_cotizacion=tipo,
                origen=origen,
                id_usuario=id_usuario,
                observacion=observacion,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    return {
        "valor": float(dec),
        "fecha": corte.isoformat(),
        "fecha_es": _format_fecha_es(corte.isoformat()),
        "origen": origen,
        "id_cotizacion": id_cot,
    }


def aceptar(
    base_empresa: str,
    *,
    valor: float,
    origen: str,
    id_usuario: Optional[int],
    observacion: str = "-",
    fecha: Optional[date] = None,
) -> Dict[str, Any]:
    """Acepta sugerido BCRA o valor explícito; escribe maestro + historial."""
    return _escribir_cotizacion(
        base_empresa,
        valor=valor,
        origen=origen or "bcra_sugerido",
        id_usuario=id_usuario,
        observacion=observacion,
        fecha=fecha,
    )


def registrar_manual(
    base_empresa: str,
    *,
    valor: float,
    id_usuario: Optional[int],
    observacion: str = "-",
    fecha: Optional[date] = None,
) -> Dict[str, Any]:
    """Override manual supervisor."""
    return _escribir_cotizacion(
        base_empresa,
        valor=valor,
        origen="manual",
        id_usuario=id_usuario,
        observacion=observacion,
        fecha=fecha,
        tipo_cotizacion="manual",
    )


def historial(
    base_empresa: str,
    *,
    limite: int = 30,
    id_cotizacion: int = 1,
) -> List[Dict[str, Any]]:
    """Filas recientes de cotizacion_historial."""
    lim = max(1, min(int(limite or 30), 200))
    filas: List[Dict[str, Any]] = []
    with get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id_historial, fecha, valor_pesos, tipo_cotizacion, origen,
                       id_usuario, observacion, created_at
                FROM cotizacion_historial
                WHERE id_cotizacion = %s
                ORDER BY fecha DESC, id_historial DESC
                LIMIT %s
                """,
                (id_cotizacion, lim),
            )
            for row in cursor.fetchall() or []:
                filas.append(
                    {
                        "id_historial": row[0],
                        "fecha": to_date_or_none(row[1]),
                        "fecha_es": _format_fecha_es(row[1]),
                        "valor_pesos": float(to_decimal_or_none(row[2]) or 0),
                        "tipo_cotizacion": str_or_default(row[3], "manual"),
                        "origen": str_or_default(row[4], "manual"),
                        "id_usuario": row[5],
                        "observacion": str_or_default(row[6], "-"),
                        "created_at": row[7],
                    }
                )
        except Exception:
            logger.exception("Error leyendo historial cotización")
    return filas


def resolver_tc(
    base_empresa: str,
    fecha: Any,
    id_cotizacion: int = 1,
) -> Optional[float]:
    """
    TC a fecha de corte: último historial con fecha <= corte; si no hay → maestro.
    Retorna None si no hay dato (el consumidor aplica fallback).
    """
    corte_sql = to_date_or_none(fecha)
    if not corte_sql:
        corte_sql = date.today().isoformat()

    with get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT valor_pesos FROM cotizacion_historial
                WHERE id_cotizacion = %s AND fecha <= %s
                ORDER BY fecha DESC, id_historial DESC
                LIMIT 1
                """,
                (id_cotizacion, corte_sql),
            )
            row = cursor.fetchone()
            if row and row[0] is not None:
                dec = to_decimal_or_none(row[0])
                if dec is not None and dec > 0:
                    return float(dec)
        except Exception:
            logger.debug("cotizacion_historial no disponible; fallback a maestro", exc_info=True)

        return _fetch_vigente_maestro(cursor, id_cotizacion)
