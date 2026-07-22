"""Helpers de permisos comerciales para pedidos (sesión mayoristapp)."""

from __future__ import annotations

import unicodedata
from typing import Any, Dict, Optional

# Puestos AdministraNET que ven el hub/listados de pedidos sin filtro de viajante.
# Comparación tras normalizar (minúsculas, sin acentos).
_PUESTOS_VER_TODOS_PEDIDOS = frozenset(
    {
        "supervisor",
        "supervisor venta",
        "administracion",
    }
)


def _si_no(val: Any, default: str = "No") -> str:
    if val is None:
        return default
    s = str(val).strip().lower()
    if s in ("si", "sí", "1", "true", "yes"):
        return "Si"
    if s in ("no", "0", "false"):
        return "No"
    return str(val).strip() or default


def _normalizar_nombre_puesto(nombre: Optional[str]) -> str:
    """Normaliza nombre de puesto (minúsculas, sin acentos) para comparar."""
    raw = str(nombre or "").strip().lower()
    if not raw:
        return ""
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", raw) if not unicodedata.combining(ch)
    )


def puesto_ve_todos_pedidos(sess_user: Dict[str, Any]) -> bool:
    """
    True si el puesto AdministraNET debe ver todos los pedidos (sin filtro de cartera).

    Aplica a: Supervisor, Supervisor venta, Administracion (y variantes con acento).
    """
    return _normalizar_nombre_puesto(sess_user.get("nombre_puesto")) in _PUESTOS_VER_TODOS_PEDIDOS


def puede_ver_todos_pedidos(sess_user: Dict[str, Any]) -> bool:
    """
    Supervisor / gerencial: ver pedidos de todos los vendedores.

    Criterios (cualquiera alcanza):
    - puesto AdministraNET Supervisor / Supervisor venta / Administracion
    - paridad legacy ``todos_clientes=Si``
    - permiso Synap ``ecom.pedidos.ver_todos`` (o ``ecom.*`` / ``*``)
    """
    if puesto_ve_todos_pedidos(sess_user):
        return True
    if _si_no(sess_user.get("todos_clientes"), "No") == "Si":
        return True
    permisos = sess_user.get("synap_permisos") or sess_user.get("permisos") or []
    if isinstance(permisos, str):
        permisos = [p.strip() for p in permisos.split(",") if p.strip()]
    codigos = {str(p).strip() for p in permisos if p}
    return "ecom.pedidos.ver_todos" in codigos or "ecom.*" in codigos or "*" in codigos
