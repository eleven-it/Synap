"""
Fragmentos SQL para filtrar por vendedor según fuente legacy o tabla de asignación.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from core.utils.administranet_types import to_int_or_none

from ecom.services.ecom_config_mysql import FuenteVendedorAsignacion, fuente_vendedor_asignacion


def _si_no(val: Any, default: str = "No") -> str:
    if val is None:
        return default
    s = str(val).strip().lower()
    if s in ("si", "sí", "yes", "1", "true"):
        return "Si"
    return "No"


def _cod_viajante_desde_sesion(sess_user: Dict[str, Any]) -> int | None:
    return to_int_or_none(
        sess_user.get("id_vendedor_usr")
        or sess_user.get("CodViajante")
        or sess_user.get("cod_viajante")
    )


def _vendedor_a_cargo_desde_sesion(sess_user: Dict[str, Any]) -> List[int]:
    raw = sess_user.get("vendedor_a_cargo")
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = raw.strip()
        if raw.startswith("["):
            try:
                import json

                raw = json.loads(raw)
            except Exception:
                return []
        else:
            out: List[int] = []
            for p in [x.strip() for x in raw.split(",") if x.strip()]:
                n = to_int_or_none(p)
                if n is not None:
                    out.append(n)
            return out
    if isinstance(raw, (list, tuple)):
        out = []
        for x in raw:
            n = to_int_or_none(x)
            if n is not None:
                out.append(n)
        return out
    return []


def where_vendedor_cliente(
    base_empresa: str,
    sess_user: Dict[str, Any],
    *,
    fuente: FuenteVendedorAsignacion | None = None,
) -> Tuple[str, List[Any]]:
    """
    Restricción de clientes visibles para el vendedor logueado.

    Paridad PHP ``buscarCliente`` / ``relay-clientes.php`` y ``cliente_relay._where_viajante``.
    """
    todos = _si_no(sess_user.get("todos_clientes"), "No")
    if todos == "Si":
        return "", []

    if fuente is None:
        fuente = fuente_vendedor_asignacion(
            base_empresa,
            "cliente",
            sesion_valor=sess_user.get("ecom_fuente_vendedor_cliente"),
        )

    sup = _si_no(sess_user.get("supervisor_venta") or sess_user.get("permiso_supervisor_venta_web"), "No")
    cv = _cod_viajante_desde_sesion(sess_user)
    if cv is None:
        return " AND 1=0 ", []

    cargo = _vendedor_a_cargo_desde_sesion(sess_user)
    ids: List[int] = [cv]
    if sup == "Si" and cargo:
        ids = [cv] + [int(x) for x in cargo]

    if fuente == "tabla":
        placeholders = ",".join(["%s"] * len(ids))
        return (
            f" AND EXISTS ("
            f"SELECT 1 FROM vendedores_clientes_asignacion vca "
            f"WHERE vca.id_cliente = cliente.Codigo "
            f"AND vca.id_vendedor IN ({placeholders})"
            f") ",
            list(ids),
        )

    if sup == "No":
        return " AND cliente.CodViajante = %s ", [cv]

    if cargo:
        placeholders = ",".join(["%s"] * len(ids))
        return f" AND cliente.CodViajante IN ({placeholders}) ", ids

    return " AND cliente.CodViajante = %s ", [cv]
