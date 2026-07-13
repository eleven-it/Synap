"""Resolución CodViajante desde ``ecom_usuario_viajante`` (complemento a ``usuarios.CodViajante``)."""

from __future__ import annotations

import logging
from typing import Optional

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_int_or_none

logger = logging.getLogger(__name__)


def resolver_cod_viajante_usuario(base_empresa: str, id_usuario: int) -> Optional[int]:
    """
    Devuelve ``CodViajante`` activo en ``ecom_usuario_viajante`` para el usuario.

    Si la tabla no existe o no hay fila, retorna ``None`` (el caller usa
    ``usuarios.CodViajante`` / sesión).
    """
    id_u = to_int_or_none(id_usuario)
    if not base_empresa or id_u is None:
        return None
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                """
                SELECT CodViajante
                FROM ecom_usuario_viajante
                WHERE id_usuario = %s AND COALESCE(activo, 1) = 1
                LIMIT 1
                """,
                [id_u],
            )
            row = cursor.fetchone()
            if row:
                return to_int_or_none(row[0])
    except Exception as exc:
        # Tabla ausente u otro error MySQL: no bloquear login/sesión
        logger.debug(
            "ecom_usuario_viajante no disponible (usuario=%s, base=%s): %s",
            id_u,
            base_empresa,
            exc,
        )
    return None
