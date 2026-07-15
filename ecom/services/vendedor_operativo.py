"""
Vendedor operativo mayoristapp — resolución única de ``CodViajante`` efectivo.

Paridad ``control.php`` (supervisor + ``vendedor_a_cargo``) con clave de sesión
``mayoristapp.cod_viajante_operativo`` (default ``id_vendedor_usr``).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Sequence

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none

from ecom.services.cliente_relay import vendedor_a_cargo_desde_sesion
from ecom.services.ecom_config_mysql import leer_valor_configuracion_ecom

logger = logging.getLogger(__name__)

_CLAVE_CFG_CARTERA = "ecom_vendedores_a_cargo_{cod}"


def _si_no_supervisor(val: Any) -> bool:
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ("si", "sí", "yes", "1", "true")


def clave_config_vendedores_a_cargo(cod_viajante_supervisor: int) -> str:
    return _CLAVE_CFG_CARTERA.format(cod=int(cod_viajante_supervisor))


def normalizar_lista_cod_viajantes(raw: Any) -> List[int]:
    """Normaliza JSON/lista a enteros ``CodViajante`` válidos."""
    if raw is None:
        return []
    data = raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        if s.startswith("["):
            try:
                data = json.loads(s)
            except Exception:
                return []
        else:
            data = [p.strip() for p in s.split(",") if p.strip()]
    if not isinstance(data, (list, tuple)):
        return []
    out: List[int] = []
    seen: set[int] = set()
    for item in data:
        n = to_int_or_none(item)
        if n is not None and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def leer_vendedores_a_cargo_config(
    base_empresa: str,
    cod_viajante_supervisor: int,
) -> List[int]:
    """
    Lee cartera supervisor desde ``configuracion_ecom``.

    Clave: ``ecom_vendedores_a_cargo_<CodViajante>`` · valor JSON ``[10,49,46,54]``.
    Sin fila: fallback ``[cod_viajante_supervisor]``.
    """
    cv = to_int_or_none(cod_viajante_supervisor)
    if cv is None:
        return []
    base = (base_empresa or "").strip()
    if not base:
        return [cv]
    key = clave_config_vendedores_a_cargo(cv)
    raw = leer_valor_configuracion_ecom(base, key, "")
    parsed = normalizar_lista_cod_viajantes(raw)
    if not parsed:
        return [cv]
    if cv not in parsed:
        parsed.insert(0, cv)
    return parsed


def _id_vendedor_desde_ctx(ctx: Dict[str, Any]) -> Optional[int]:
    return to_int_or_none(
        ctx.get("id_vendedor_usr")
        or ctx.get("CodViajante")
        or ctx.get("cod_viajante")
    )


def _operativo_desde_ctx(ctx: Dict[str, Any]) -> Optional[int]:
    return to_int_or_none(ctx.get("cod_viajante_operativo"))


def cartera_permitida(ctx: Dict[str, Any]) -> List[int]:
    """Conjunto permitido: propio viajante + ``vendedor_a_cargo``."""
    cv = _id_vendedor_desde_ctx(ctx)
    if cv is None:
        return []
    cargo = vendedor_a_cargo_desde_sesion(ctx)
    seen: set[int] = {cv}
    out = [cv]
    for c in cargo:
        n = to_int_or_none(c)
        if n is not None and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def resolver_viajante_operativo(ctx: Dict[str, Any]) -> Optional[int]:
    """
    Devuelve ``cod_viajante_operativo`` si está seteado y ∈ cartera; si no, ``id_vendedor_usr``.
    """
    cv = _id_vendedor_desde_ctx(ctx)
    if cv is None:
        return None
    operativo = _operativo_desde_ctx(ctx)
    if operativo is None:
        return cv
    permitidos = set(cartera_permitida(ctx))
    if operativo in permitidos:
        return operativo
    return cv


def ctx_desde_request(request: Any) -> Dict[str, Any]:
    """Fusiona ``user`` + ``mayoristapp`` para el resolver."""
    sess = getattr(request, "session", None) or {}
    ctx = dict(sess.get("user") or {})
    bag = sess.get("mayoristapp") or {}
    if isinstance(bag, dict) and bag.get("cod_viajante_operativo") is not None:
        ctx["cod_viajante_operativo"] = bag["cod_viajante_operativo"]
    for clave in ("vendedor_a_cargo", "supervisor_venta", "id_vendedor_usr", "CodViajante"):
        if ctx.get(clave) is None and sess.get(clave) is not None:
            ctx[clave] = sess[clave]
    return ctx


def resolver_viajante_operativo_request(request: Any) -> Optional[int]:
    return resolver_viajante_operativo(ctx_desde_request(request))


def nombres_viajantes(
    base_empresa: str,
    codigos: Sequence[int],
) -> Dict[int, str]:
    """Mapa ``CodViajante`` → nombre desde tabla ``viajantes``."""
    ids = [to_int_or_none(c) for c in codigos]
    ids = [i for i in ids if i is not None]
    if not ids or not (base_empresa or "").strip():
        return {}
    placeholders = ",".join(["%s"] * len(ids))
    sql = f"""
        SELECT CodViajante, COALESCE(Nombre, '') AS Nombre
        FROM viajantes
        WHERE CodViajante IN ({placeholders})
    """
    out: Dict[int, str] = {}
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, ids)
                for row in cursor.fetchall():
                    if isinstance(row, dict):
                        cv = to_int_or_none(row.get("CodViajante"))
                        nombre = str(row.get("Nombre") or "").strip()
                    else:
                        cv = to_int_or_none(row[0])
                        nombre = str(row[1] or "").strip()
                    if cv is not None:
                        out[cv] = nombre or f"Vendedor {cv}"
            finally:
                cursor.close()
    except Exception as exc:
        logger.warning("nombres_viajantes (%s): %s", base_empresa, exc)
    for c in ids:
        if c not in out:
            out[c] = f"Vendedor {c}"
    return out


def listar_cartera_operativa(
    base_empresa: str,
    ctx: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Payload para GET vendedores-cartera: vendedores, operativo, propio, mostrar_selector.
    """
    cv = _id_vendedor_desde_ctx(ctx)
    operativo = resolver_viajante_operativo(ctx)
    es_supervisor = _si_no_supervisor(ctx.get("supervisor_venta") or ctx.get("permiso_supervisor_venta_web"))
    cartera = cartera_permitida(ctx) if es_supervisor else ([cv] if cv is not None else [])
    nombres = nombres_viajantes(base_empresa, cartera)
    vendedores = [
        {"cod_viajante": c, "nombre": nombres.get(c, f"Vendedor {c}")}
        for c in cartera
    ]
    mostrar = bool(es_supervisor and len(cartera) > 0)
    return {
        "vendedores": vendedores,
        "operativo": operativo,
        "propio": cv,
        "mostrar_selector": mostrar,
        "operando_como_otro": operativo is not None and cv is not None and operativo != cv,
    }


def guardar_cod_viajante_operativo(request: Any, cod_viajante: int) -> bool:
    """Persiste operativo en bolsa ``mayoristapp`` tras validar cartera."""
    ctx = ctx_desde_request(request)
    permitidos = set(cartera_permitida(ctx))
    cv = to_int_or_none(cod_viajante)
    if cv is None or cv not in permitidos:
        return False
    sess = getattr(request, "session", None)
    if sess is None:
        return False
    bag = dict(sess.get("mayoristapp") or {})
    bag["cod_viajante_operativo"] = cv
    sess["mayoristapp"] = bag
    user = dict(sess.get("user") or {})
    user["cod_viajante_operativo"] = cv
    sess["user"] = user
    sess.modified = True
    return True


def reset_cod_viajante_operativo(request: Any) -> None:
    """Restablece operativo al viajante propio (logout / fin de sesión mayoristapp)."""
    sess = getattr(request, "session", None)
    if sess is None:
        return
    bag = dict(sess.get("mayoristapp") or {})
    bag.pop("cod_viajante_operativo", None)
    sess["mayoristapp"] = bag
    user = dict(sess.get("user") or {})
    user.pop("cod_viajante_operativo", None)
    sess["user"] = user
    sess.modified = True
