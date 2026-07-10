"""Helpers de permisos comerciales para pedidos (sesión mayoristapp)."""

from __future__ import annotations

from typing import Any, Dict


def _si_no(val: Any, default: str = "No") -> str:
    if val is None:
        return default
    s = str(val).strip().lower()
    if s in ("si", "sí", "1", "true", "yes"):
        return "Si"
    if s in ("no", "0", "false"):
        return "No"
    return str(val).strip() or default


def puede_ver_todos_pedidos(sess_user: Dict[str, Any]) -> bool:
    """
    Supervisor / gerencial: ver pedidos de todos los vendedores.

    Paridad legacy ``todos_clientes=Si`` o permiso Synap ``ecom.pedidos.ver_todos``.
    """
    if _si_no(sess_user.get("todos_clientes"), "No") == "Si":
        return True
    permisos = sess_user.get("synap_permisos") or sess_user.get("permisos") or []
    if isinstance(permisos, str):
        permisos = [p.strip() for p in permisos.split(",") if p.strip()]
    codigos = {str(p).strip() for p in permisos if p}
    return "ecom.pedidos.ver_todos" in codigos or "ecom.*" in codigos or "*" in codigos
