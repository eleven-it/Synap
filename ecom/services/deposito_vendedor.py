"""Resolución del depósito de despacho del vendedor (pedidos ecom).

El checkout NUNCA debe caer en depósito 1 por default silencioso: eso reservó
y remitió stock de Producción en lugar del depósito del usuario (p. ej. Terminado).
"""
from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_int_or_none

logger = logging.getLogger(__name__)


class DepositoVendedorNoResuelto(Exception):
    """No se pudo determinar el depósito del vendedor (fail-closed)."""


def _primer_deposito_positivo(*candidatos: Any) -> Optional[int]:
    for raw in candidatos:
        dep = to_int_or_none(raw)
        if dep is not None and dep > 0:
            return dep
    return None


def fetch_id_deposito_usuario(base_empresa: str, id_usuario: int) -> Optional[int]:
    """Lee ``usuarios.id_deposito`` en MySQL AdministraNET."""
    base = (base_empresa or "").strip()
    uid = to_int_or_none(id_usuario)
    if not base or uid is None:
        return None
    try:
        with mysql_cursor(base, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT id_deposito FROM usuarios WHERE id_usuario = %s LIMIT 1",
                [uid],
            )
            row = cursor.fetchone() or {}
            return _primer_deposito_positivo(row.get("id_deposito"))
    except Exception as exc:
        logger.warning(
            "fetch_id_deposito_usuario base=%s user=%s: %s",
            base,
            uid,
            exc,
        )
        return None


def resolver_id_deposito_vendedor(
    *,
    session: Optional[Mapping[str, Any]] = None,
    data: Optional[Mapping[str, Any]] = None,
    base_empresa: Optional[str] = None,
    id_usuario: Optional[int] = None,
    permitir_body: bool = True,
    priorizar_vendedor: bool = True,
    consultar_mysql: bool = True,
) -> int:
    """
    Resuelve el depósito de despacho del vendedor.

    Con ``priorizar_vendedor=True`` (default, checkout):
    1. ``session.user.id_deposito``
    2. ``session.deposito`` / ``mayoristapp.deposito``
    3. MySQL ``usuarios.id_deposito``
    4. ``data.id_deposito`` solo si aún no hay valor (y ``permitir_body``)

    Así un body erróneo con ``id_deposito=1`` no pisa el depósito del vendedor.

    Raises:
        DepositoVendedorNoResuelto: si no hay depósito válido (no usa default 1).
    """
    sess = dict(session or {})
    user = dict(sess.get("user") or {})
    bag = dict(sess.get("mayoristapp") or {})
    payload = dict(data or {})

    uid = to_int_or_none(id_usuario)
    if uid is None:
        uid = to_int_or_none(user.get("id_usuario")) or to_int_or_none(sess.get("id_usuario"))

    base = (base_empresa or "").strip() or str(
        user.get("base_empresa") or sess.get("base_empresa") or ""
    ).strip()

    candidatos_vendedor = [
        user.get("id_deposito"),
        sess.get("id_deposito"),
        sess.get("deposito"),
        bag.get("deposito"),
        bag.get("id_deposito"),
    ]
    dep = _primer_deposito_positivo(*candidatos_vendedor)
    if dep is not None:
        return dep

    if consultar_mysql and base and uid is not None:
        dep_db = fetch_id_deposito_usuario(base, uid)
        if dep_db is not None:
            return dep_db

    if permitir_body and not priorizar_vendedor:
        dep_body = _primer_deposito_positivo(payload.get("id_deposito"))
        if dep_body is not None:
            return dep_body

    if permitir_body and priorizar_vendedor:
        # Último recurso: body solo si no hubo nada del vendedor/MySQL.
        dep_body = _primer_deposito_positivo(payload.get("id_deposito"))
        if dep_body is not None:
            return dep_body

    raise DepositoVendedorNoResuelto(
        "No se pudo resolver el depósito del vendedor. "
        "Configure usuarios.id_deposito o reinicie sesión."
    )


def resolver_id_deposito_desde_request(
    request: Any,
    *,
    data: Optional[Mapping[str, Any]] = None,
    permitir_body: bool = True,
) -> int:
    """Atajo desde request Django/DRF."""
    sess = getattr(request, "session", None) or {}
    user = sess.get("user") or {}
    base = (
        str(user.get("base_empresa") or sess.get("base_empresa") or "").strip()
    )
    return resolver_id_deposito_vendedor(
        session=sess,
        data=data,
        base_empresa=base,
        id_usuario=to_int_or_none(user.get("id_usuario")),
        permitir_body=permitir_body,
    )
