"""Catálogos de entrega usados por la captura de pedidos y presupuestos."""

from __future__ import annotations

import logging

import MySQLdb

from core.mysql_pool import get_connection
from core.utils.administranet_types import to_int_or_none

logger = logging.getLogger(__name__)


def catalogo_rutas_entrega(base_empresa: str, id_usuario: int | None = None) -> dict:
    """Catálogos que usa la ventana de datos adicionales de AdministraNET."""
    result = {
        "logistica_activa": False,
        "rutas_entrega": [],
        "transportes": [],
        "repartidores": [],
        "operadores_logisticos": ["Mercado envio", "Envio Pack", "OCA Envio"],
        "forma_entrega_default": "",
    }
    try:
        with get_connection(base_empresa) as conn:
            cur = conn.cursor(MySQLdb.cursors.DictCursor)
            cur.execute("SELECT activ_logistica FROM configuracion LIMIT 1")
            cfg = cur.fetchone() or {}
            result["logistica_activa"] = str(cfg.get("activ_logistica") or "").strip() == "Si"
            if id_usuario is not None:
                cur.execute(
                    "SELECT entrega_defecto FROM usuarios WHERE id_usuario = %s LIMIT 1",
                    [id_usuario],
                )
                user = cur.fetchone() or {}
                result["forma_entrega_default"] = str(user.get("entrega_defecto") or "").strip()
            cur.execute(
                "SELECT id_transporte, nombre_transporte FROM transporte "
                "WHERE anulado = 'No' ORDER BY nombre_transporte"
            )
            result["transportes"] = [
                {"id": to_int_or_none(r.get("id_transporte")),
                 "nombre": str(r.get("nombre_transporte") or "").strip()}
                for r in cur.fetchall()
            ]
            cur.execute(
                "SELECT id_usuario, nombre_usuario FROM usuarios "
                "WHERE baja_usuario = 'No' ORDER BY cod_usuario"
            )
            result["repartidores"] = [
                {"id": to_int_or_none(r.get("id_usuario")),
                 "nombre": str(r.get("nombre_usuario") or "").strip()}
                for r in cur.fetchall()
            ]
            if result["logistica_activa"]:
                cur.execute(
                    """
                    SELECT r.id_ruta,
                           GROUP_CONCAT(CAST(z.nombre_zona AS CHAR) SEPARATOR ',') AS nombre_zona,
                           DATE_FORMAT(r.fecha_salida, '%d/%m/%Y') AS fecha_salida
                    FROM logi_hoja_ruta AS r
                    LEFT JOIN logi_ruta_zona AS rz ON rz.id_ruta = r.id_ruta
                    LEFT JOIN erp_zona AS z ON z.id_zona = rz.id_zona
                    WHERE r.Anulado = 'No'
                      AND r.estado_ruta = 'Abierto'
                      AND r.fecha_salida > NOW()
                    GROUP BY r.id_ruta
                    ORDER BY r.fecha_salida ASC, r.id_ruta ASC
                    LIMIT 1000
                    """
                )
                result["rutas_entrega"] = [
                    {"id": to_int_or_none(row.get("id_ruta")),
                     "nombre": str(row.get("nombre_zona") or "").strip(),
                     "fecha_salida": str(row.get("fecha_salida") or "")}
                    for row in cur.fetchall()
                ]
            cur.close()
        result["rutas_entrega"] = [r for r in result["rutas_entrega"] if r["id"] is not None]
        return result
    except Exception:
        logger.exception("No se pudieron cargar los catálogos de entrega")
        return result
