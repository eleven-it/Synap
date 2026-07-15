"""
Fragmentos SQL para filtrar por vendedor según fuente legacy, tabla de asignación o ternas VCM.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none

from ecom.services.ecom_config_mysql import (
    FuenteVendedorAsignacion,
    fuente_vendedor_asignacion,
    leer_valor_configuracion_ecom,
)

logger = logging.getLogger(__name__)

_CLAVE_USA_VCM = "ecom_usa_vcm_ternas"
_vcm_disponible_cache: Dict[str, bool] = {}


def _si_no(val: Any, default: str = "No") -> str:
    if val is None:
        return default
    s = str(val).strip().lower()
    if s in ("si", "sí", "yes", "1", "true"):
        return "Si"
    return "No"


def _cod_viajante_efectivo(sess_user: Dict[str, Any]) -> int | None:
    """Viajante operativo (``resolver_viajante_operativo``) para filtros de pedido."""
    from ecom.services.vendedor_operativo import resolver_viajante_operativo

    return resolver_viajante_operativo(sess_user)


def vcm_ternas_disponible(base_empresa: str) -> bool:
    """
    True si la empresa usa ternas VCM (``ecom_vendedor_cliente_marca``).

    Config ``ecom_usa_vcm_ternas``: ``Si`` | ``No`` | ``auto`` (default).
    En ``auto``, se activa si existe al menos una terna activa en MySQL.
    """
    base = (base_empresa or "").strip()
    if not base:
        return False
    if base in _vcm_disponible_cache:
        return _vcm_disponible_cache[base]
    try:
        cfg = (leer_valor_configuracion_ecom(base, _CLAVE_USA_VCM, "auto") or "auto").strip().lower()
    except Exception as exc:
        logger.debug("vcm_ternas_disponible cfg(%s): %s", base, exc)
        cfg = "auto"
    if cfg in ("si", "sí", "yes", "1", "true"):
        _vcm_disponible_cache[base] = True
        return True
    if cfg in ("no", "0", "false"):
        _vcm_disponible_cache[base] = False
        return False
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT 1
                    FROM ecom_vendedor_cliente_marca
                    WHERE COALESCE(anulado, 'No') = 'No'
                    LIMIT 1
                    """
                )
                ok = cursor.fetchone() is not None
            finally:
                cursor.close()
        _vcm_disponible_cache[base] = ok
        return ok
    except Exception as exc:
        logger.debug("vcm_ternas_disponible(%s): %s", base, exc)
        _vcm_disponible_cache[base] = False
        return False


def _where_cliente_terna_vcm(cod_viajante: int) -> Tuple[str, List[Any]]:
    """Restricción por terna activa (paridad ``listar_clientes_con_ternas``)."""
    return (
        " AND EXISTS ("
        "SELECT 1 FROM ecom_vendedor_cliente_marca vcm "
        "WHERE vcm.id_cliente = cliente.Codigo "
        "AND vcm.CodViajante = %s "
        "AND COALESCE(vcm.anulado, 'No') = 'No'"
        ") ",
        [cod_viajante],
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

    cv = _cod_viajante_efectivo(sess_user)
    if cv is None:
        return " AND 1=0 ", []

    if vcm_ternas_disponible(base_empresa):
        return _where_cliente_terna_vcm(cv)

    if fuente is None:
        fuente = fuente_vendedor_asignacion(
            base_empresa,
            "cliente",
            sesion_valor=sess_user.get("ecom_fuente_vendedor_cliente"),
        )

    sup = _si_no(sess_user.get("supervisor_venta") or sess_user.get("permiso_supervisor_venta_web"), "No")
    cv_propio = to_int_or_none(
        sess_user.get("id_vendedor_usr")
        or sess_user.get("CodViajante")
        or sess_user.get("cod_viajante")
    )
    cargo = _vendedor_a_cargo_desde_sesion(sess_user)
    ids: List[int] = [cv]
    if sup == "Si" and cargo and cv_propio is not None and cv == cv_propio:
        ids = [cv] + [int(x) for x in cargo if to_int_or_none(x) is not None]

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
