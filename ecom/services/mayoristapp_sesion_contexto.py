"""
Contexto de sesión mayoristapp con paridad ``control.php`` (PHP).

PHP guarda en ``$_SESSION`` raíz: ``todos_clientes``, ``usa_id_manual``,
``supervisor_venta``, ``vendedor_a_cargo``. Synap login solo persiste ``session['user']``
básico; este módulo completa ``id_vendedor_usr`` (CodViajante) y permisos desde MySQL.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_int_or_none

logger = logging.getLogger(__name__)

_CLAVES_RAIZ_PHP = (
    "todos_clientes",
    "usa_id_manual",
    "supervisor_venta",
    "permiso_supervisor_venta_web",
    "vendedor_a_cargo",
    "tipousuario",
    "id_vendedor_usr",
    "CodViajante",
)


def _si_no(val: Any, default: str = "No") -> str:
    if val is None:
        return default
    s = str(val).strip().lower()
    if s in ("si", "sí", "yes", "1", "true"):
        return "Si"
    return "No"


def _valor_permiso_puesto(
    cursor,
    id_puesto: int,
    *,
    key_permiso: str,
    id_permiso_sistema: Optional[int] = None,
) -> Optional[str]:
    """Último valor en ``permiso_sistema_puesto`` (paridad PHP permiso 99 / key)."""
    cursor.execute(
        """
        SELECT psp.valor_permiso
        FROM permiso_sistema_puesto psp
        INNER JOIN permiso_sistema ps ON ps.id_permiso_sistema = psp.id_permiso_sistema
        WHERE psp.id_puesto = %s AND TRIM(ps.key_permiso) = %s
        ORDER BY psp.id_permiso_sistema_puesto DESC
        LIMIT 1
        """,
        [id_puesto, key_permiso.strip()],
    )
    row = cursor.fetchone()
    if row and row[0] is not None:
        return str(row[0]).strip()

    if id_permiso_sistema is not None:
        cursor.execute(
            """
            SELECT valor_permiso
            FROM permiso_sistema_puesto
            WHERE id_puesto = %s AND id_permiso_sistema = %s
            ORDER BY id_permiso_sistema_puesto DESC
            LIMIT 1
            """,
            [id_puesto, id_permiso_sistema],
        )
        row2 = cursor.fetchone()
        if row2 and row2[0] is not None:
            return str(row2[0]).strip()
    return None


def _cargar_campos_mayoristapp_mysql(base_empresa: str, id_usuario: int, id_puesto: Optional[int]) -> Dict[str, Any]:
    """Lee CodViajante y permisos web desde tablas legacy (paridad ``control.php``)."""
    out: Dict[str, Any] = {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            cursor.execute(
                """
                SELECT CodViajante, permiso_supervisor_venta
                FROM usuarios
                WHERE id_usuario = %s
                LIMIT 1
                """,
                [id_usuario],
            )
            row = cursor.fetchone()
            if row:
                cv = to_int_or_none(row[0])
                if cv is not None:
                    out["id_vendedor_usr"] = cv
                    out["CodViajante"] = cv
                sup = (row[1] or "No").strip() if row[1] is not None else "No"
                out["supervisor_venta"] = sup
                out["permiso_supervisor_venta_web"] = sup

            if id_puesto:
                todos = _valor_permiso_puesto(
                    cursor,
                    int(id_puesto),
                    key_permiso="visualiza_clientes_todos_web",
                    id_permiso_sistema=99,
                )
                if todos:
                    out["todos_clientes"] = todos
                else:
                    # Sistema viejo ``permisos_sistema``
                    try:
                        cursor.execute(
                            """
                            SELECT visualiza_clientes_todos_web
                            FROM permisos_sistema
                            WHERE IDPuesto = %s
                            LIMIT 1
                            """,
                            [id_puesto],
                        )
                        leg = cursor.fetchone()
                        if leg and leg[0] is not None:
                            out["todos_clientes"] = str(leg[0]).strip()
                    except Exception:
                        pass
    except Exception as exc:
        logger.warning(
            "No se pudo cargar contexto mayoristapp MySQL (usuario=%s, base=%s): %s",
            id_usuario,
            base_empresa,
            exc,
        )
    return out


def _fusionar_raiz_sesion(sess: dict, base: dict) -> dict:
    """Superpone claves PHP en raíz de sesión sobre el dict de trabajo."""
    merged = dict(base)
    for clave in _CLAVES_RAIZ_PHP:
        if merged.get(clave) is None and sess.get(clave) is not None:
            merged[clave] = sess[clave]
    if merged.get("id_vendedor_usr") is None:
        cv = to_int_or_none(merged.get("CodViajante"))
        if cv is not None:
            merged["id_vendedor_usr"] = cv
    return merged


def _persistir_contexto(request: Any, ctx: dict) -> None:
    sess = getattr(request, "session", None)
    if sess is None:
        return
    user = dict(sess.get("user") or {})
    cambio = False
    for clave in (
        "id_vendedor_usr",
        "CodViajante",
        "todos_clientes",
        "supervisor_venta",
        "permiso_supervisor_venta_web",
        "usa_id_manual",
        "vendedor_a_cargo",
        "tipousuario",
    ):
        val = ctx.get(clave)
        if val is None:
            continue
        if user.get(clave) != val:
            user[clave] = val
            cambio = True
        # Paridad PHP: también en raíz para lecturas legacy
        if sess.get(clave) != val and clave in _CLAVES_RAIZ_PHP:
            sess[clave] = val
            cambio = True
    if cambio:
        sess["user"] = user
        sess.modified = True


def contexto_usuario_mayoristapp(request: Any, *, persistir: bool = True) -> Dict[str, Any]:
    """
    Dict unificado para relays ecom (equivalente a mezclar ``$_SESSION['user']`` +
    flags de ``control.php``).
    """
    sess = getattr(request, "session", None) or {}
    base = _fusionar_raiz_sesion(sess, dict(sess.get("user") or {}))

    id_usuario = to_int_or_none(base.get("id_usuario"))
    id_puesto = to_int_or_none(base.get("id_puesto"))
    base_empresa = str(base.get("base_empresa") or "").strip()

    # Paridad control.php: refrescar siempre desde MySQL (evita sesión Synap incompleta).
    if base_empresa and id_usuario:
        loaded = _cargar_campos_mayoristapp_mysql(base_empresa, id_usuario, id_puesto)
        _CLAVES_MYSQL_SIEMPRE = (
            "id_vendedor_usr",
            "CodViajante",
            "todos_clientes",
            "supervisor_venta",
            "permiso_supervisor_venta_web",
        )
        for k in _CLAVES_MYSQL_SIEMPRE:
            if k in loaded and loaded[k] is not None:
                base[k] = loaded[k]
        for k, v in loaded.items():
            if base.get(k) is None:
                base[k] = v

    cod = (base.get("cod_usuario") or "").strip().lower()
    if cod == "supervisor" and base.get("todos_clientes") is None:
        base["todos_clientes"] = "Si"

    if base.get("usa_id_manual") is None:
        base["usa_id_manual"] = _si_no(sess.get("usa_id_manual"), "No")

    if base.get("todos_clientes") is None:
        base["todos_clientes"] = "No"

    cargo = base.get("vendedor_a_cargo")
    if cargo is not None and not isinstance(cargo, list):
        if isinstance(cargo, str) and cargo.strip().startswith("["):
            try:
                import json

                cargo = json.loads(cargo)
            except Exception:
                cargo = []
        elif isinstance(cargo, str):
            cargo = [x.strip() for x in cargo.split(",") if x.strip()]
        else:
            cargo = []
        base["vendedor_a_cargo"] = cargo

    if persistir:
        _persistir_contexto(request, base)
    return base


def asegurar_contexto_mayoristapp(request: Any) -> Dict[str, Any]:
    """Atajo para vistas/API: hidrata y devuelve contexto listo para ``buscar_clientes_relay``."""
    return contexto_usuario_mayoristapp(request, persistir=True)
