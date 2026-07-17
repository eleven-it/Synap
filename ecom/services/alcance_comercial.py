"""
Alcance comercial unificado — origen de CodViajante permitidos según workflow org.

OFF: delega cartera legacy (JSON/sesión). ON: subárbol por rol + ``ecom.pedidos.ver_todos``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none

from ecom.services.ecom_config_mysql import workflow_jerarquia_comercial_activo
from ecom.services.jerarquia_comercial import (
    es_vendedor_real,
    rol_de,
    rol_de_usuario,
    subarbol_de,
    subarbol_de_usuario,
)
from ecom.services.pedido_permisos import puede_ver_todos_pedidos
from ecom.services.vendedor_operativo import cartera_permitida_legacy

logger = logging.getLogger(__name__)

_CACHE_KEY = "_alcance_viajantes_comercial_cache"


def _id_vendedor_desde_ctx(ctx: Dict[str, Any]) -> Optional[int]:
    return to_int_or_none(
        ctx.get("id_vendedor_usr")
        or ctx.get("CodViajante")
        or ctx.get("cod_viajante")
    )


def _id_usuario_desde_ctx(ctx: Dict[str, Any]) -> Optional[int]:
    session_user = ctx.get("user")
    if not isinstance(session_user, dict):
        session_user = ctx.get("session_user")
    return to_int_or_none(
        ctx.get("id_usuario")
        or (session_user or {}).get("id_usuario")
    )


def _listar_todos_viajantes(base_empresa: str) -> List[int]:
    base = (base_empresa or "").strip()
    if not base:
        return []
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT CodViajante FROM viajantes
                    WHERE COALESCE(anulado, 'No') = 'No' AND CodViajante > 1
                    ORDER BY CodViajante
                    """
                )
                rows = cursor.fetchall() or []
                out: List[int] = []
                for row in rows:
                    if isinstance(row, dict):
                        n = to_int_or_none(row.get("CodViajante"))
                    else:
                        n = to_int_or_none(row[0])
                    if n is not None:
                        out.append(n)
                return out
            finally:
                cursor.close()
    except Exception as exc:
        logger.warning("_listar_todos_viajantes (%s): %s", base, exc)
        return []


def alcance_viajantes_comercial(
    base_empresa: str,
    ctx: Dict[str, Any],
) -> List[int]:
    """
    Devuelve lista de ``CodViajante`` visibles para el usuario en ctx.

    Con ``ecom.pedidos.ver_todos`` y workflow ON devuelve todos los viajantes activos.
    Cache por request en ``ctx[_CACHE_KEY]``.
    """
    if _CACHE_KEY in ctx:
        cached = ctx[_CACHE_KEY]
        if isinstance(cached, list):
            return list(cached)

    base = (base_empresa or "").strip()
    if not workflow_jerarquia_comercial_activo(base):
        result = cartera_permitida_legacy(ctx)
    elif puede_ver_todos_pedidos(ctx):
        result = _listar_todos_viajantes(base)
    else:
        id_usuario = _id_usuario_desde_ctx(ctx)
        if id_usuario is not None:
            rol = rol_de_usuario(base, id_usuario)
            result = subarbol_de_usuario(base, id_usuario, rol)
        else:
            cv = _id_vendedor_desde_ctx(ctx)
            if cv is None:
                result = []
            else:
                rol = rol_de(base, cv)
                result = subarbol_de(base, cv, rol)

    result = [cv for cv in result if es_vendedor_real(cv)]
    ctx[_CACHE_KEY] = list(result)
    return result
