"""
Estado de sesión específico mayoristapp (paridad claves PHP ``$_SESSION`` aisladas).
"""

from __future__ import annotations

from typing import Any, Optional


def _mayoristapp_bag(request: Any) -> dict:
    sess = getattr(request, "session", None)
    if sess is None:
        return {}
    if "mayoristapp" not in sess or not isinstance(sess["mayoristapp"], dict):
        sess["mayoristapp"] = {}
    return sess["mayoristapp"]


def guardar_filtro_catalogo_rubro(request: Any, id_rubro: Any) -> None:
    """
    Paridad relay-rubro-catalogo.php: ``buscaRubro`` + ``claseLista`` = galeria.
    """
    bag = _mayoristapp_bag(request)
    bag["busca_rubro"] = id_rubro
    bag["clase_lista"] = "galeria"
    request.session["mayoristapp"] = bag
    request.session.modified = True


def leer_busca_rubro(request: Any) -> Optional[Any]:
    bag = (getattr(request, "session", None) or {}).get("mayoristapp") or {}
    return bag.get("busca_rubro")


def leer_cliente_seleccionado(request: Any) -> Optional[Any]:
    """Paridad ``$_SESSION['cliente']`` (prioridad bolsa ``mayoristapp``)."""
    sess = getattr(request, "session", None) or {}
    c = (sess.get("mayoristapp") or {}).get("cliente")
    if c is not None:
        return c
    return sess.get("cliente")


def guardar_formulario_comprobante_mayoristapp(request: Any, formulario: str, u_formulario: str) -> None:
    """Paridad ``seleccionarComprobante`` → ``formulario`` + ``uFormulario``."""
    bag = _mayoristapp_bag(request)
    bag["formulario"] = formulario
    bag["u_formulario"] = u_formulario
    request.session["mayoristapp"] = bag
    request.session.modified = True


def guardar_cliente_seleccion_mayoristapp(
    request: Any,
    *,
    cliente_datos: dict,
    autoriza_credito: dict,
    idcliente: int,
    domicilios_cliente: list,
    iva_incluido: str,
) -> None:
    """
    Paridad ``seleccionar_cliente`` en PHP: ``cliente`` (tupla objeto + autoriza),
    ``idcliente``, ``domicilios_cliente``, ``ivaIncluido``; vacía carrito web.
    """
    bag = _mayoristapp_bag(request)
    bag["cliente"] = [cliente_datos, autoriza_credito]
    bag["idcliente"] = idcliente
    bag["domicilios_cliente"] = domicilios_cliente
    bag["iva_incluido"] = iva_incluido
    request.session["mayoristapp"] = bag
    request.session["idcliente"] = idcliente
    request.session["cliente"] = [cliente_datos, autoriza_credito]
    request.session["domicilios_cliente"] = domicilios_cliente
    request.session["ivaIncluido"] = iva_incluido
    request.session.pop("jcart", None)
    request.session.modified = True


def guardar_cliente_rapido_lista_sesion(request: Any, json_str: str) -> None:
    """Paridad ``$_SESSION['clienteRapido']`` (JSON string como en PHP)."""
    request.session["clienteRapido"] = json_str
    request.session.modified = True


def leer_idcliente_mayoristapp(request: Any) -> Optional[int]:
    bag = (getattr(request, "session", None) or {}).get("mayoristapp") or {}
    raw = bag.get("idcliente")
    if raw is None:
        raw = (getattr(request, "session", None) or {}).get("idcliente")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
