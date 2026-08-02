"""
Constantes y helpers para la UI móvil / PWA (Nivel A).

Debe mantenerse alineado con `MobileLevelAOnlyMiddleware`: solo rutas y módulos
explicitamente soportados en dispositivos móviles.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from django.http import HttpRequest

# IDs de `APPS_MENU` (`app["id"]`) que pueden mostrarse en el menú principal en móvil/PWA.
PWA_MENU_APP_IDS = frozenset({"self_checkout", "ecom", "stock", "mpr"})

# Submenús stock accesibles en Nivel A (conteo móvil).
PWA_STOCK_MENU_ITEM_IDS = frozenset({"stock_inv_fisico_conteo"})

# Deep links PWA stock conteo.
PWA_STOCK_CONTEO_DEEP_LINKS = (
    "/stock/conteo/",
)

# Submenús e-com accesibles en Nivel A (`menu_item_id` en APPS_MENU / menu_config).
PWA_ECOM_MENU_ITEM_IDS = frozenset(
    {
        "ecom_compra",  # Pedido simple → /mayoristapp/pedido-masivo-sucursales/?modo=simple
        "ecom_pedidos",  # Hub pedidos → /mayoristapp/pedidos/
        "ecom_pedido_masivo",  # Pedido masivo → /mayoristapp/pedido-masivo-sucursales/
    }
)

# Deep links PWA e-com (rutas HTML Nivel A).
PWA_ECOM_DEEP_LINKS = (
    "/ecom/mayoristapp/pedidos/",
    "/ecom/mayoristapp/pedido-masivo-sucursales/",
    "/ecom/mayoristapp/venta/",  # redirect legacy → masivo ?modo=simple
    "/ecom/mayoristapp/compra/",  # alias redirect legacy
)

# Submenús MPR accesibles en Nivel A (tablero KPIs e inventario móvil).
PWA_MPR_MENU_ITEM_IDS = frozenset({"mpr_prod_kpis", "mpr_prod_inventario"})

# Deep links PWA MPR.
PWA_MPR_DEEP_LINKS = (
    "/mpr/",
    "/mpr/inventario/",
)


def usuario_tiene_tpv_en_menu(user, request: Optional[HttpRequest] = None) -> bool:
    """
    True si Self-Checkout / TPV figuraría en el menú de escritorio.

    Mismas reglas que `apps_visibles_sin_filtro_pwa`: permisos, navbar granular,
    submenús visibles y ocultación global del menú.
    """
    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return False
    from core.utils.utils import apps_visibles_sin_filtro_pwa

    return any(a.get("id") == "self_checkout" for a in apps_visibles_sin_filtro_pwa(user, request))


def usuario_tiene_ecom_en_menu(user, request: Optional[HttpRequest] = None) -> bool:
    """True si E-commerce mayorista figuraría en el menú de escritorio."""
    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return False
    from core.utils.utils import apps_visibles_sin_filtro_pwa

    return any(a.get("id") == "ecom" for a in apps_visibles_sin_filtro_pwa(user, request))


def tpv_visible_en_movil(user, request: Optional[HttpRequest] = None) -> bool:
    """TPV accesible en móvil: el usuario tiene el módulo activo en menú (no solo PWA)."""
    return usuario_tiene_tpv_en_menu(user, request)


def ecom_visible_en_movil(user, request: Optional[HttpRequest] = None) -> bool:
    """E-com hub+venta accesible en móvil si el módulo está en menú de escritorio."""
    return usuario_tiene_ecom_en_menu(user, request)


def usuario_tiene_mpr_en_menu(user, request: Optional[HttpRequest] = None) -> bool:
    """True si Producción (MPR) figuraría en el menú de escritorio."""
    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return False
    from core.utils.utils import apps_visibles_sin_filtro_pwa

    return any(a.get("id") == "mpr" for a in apps_visibles_sin_filtro_pwa(user, request))


def mpr_visible_en_movil(user, request: Optional[HttpRequest] = None) -> bool:
    """MPR tablero/inventario accesible en móvil si el módulo está en menú de escritorio."""
    return usuario_tiene_mpr_en_menu(user, request)


def usuario_tiene_conteo_en_menu(user, request: Optional[HttpRequest] = None) -> bool:
    """True si el usuario puede contar inventario físico desde PWA."""
    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return False
    if hasattr(user, "is_admin") and user.is_admin():
        return True
    if hasattr(user, "tiene_permiso"):
        return user.tiene_permiso("stock.inventario_fisico.contar")
    return False


def conteo_visible_en_movil(user, request: Optional[HttpRequest] = None) -> bool:
    """Conteo inventario físico accesible en móvil con permiso contar."""
    return usuario_tiene_conteo_en_menu(user, request)


def filtrar_submenus_stock_para_pwa_movil(
    submenus: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Deja solo conteo inventario físico del sidebar stock en móvil."""
    resultado: List[Dict[str, Any]] = []
    for seccion in submenus or []:
        items = [
            item
            for item in seccion.get("items") or []
            if item.get("menu_item_id") in PWA_STOCK_MENU_ITEM_IDS
        ]
        if items:
            copia = dict(seccion)
            copia["items"] = items
            resultado.append(copia)
    return resultado


def filtrar_submenus_ecom_para_pwa_movil(
    submenus: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Deja solo entradas hub, venta y pedido masivo del sidebar e-com en móvil."""
    resultado: List[Dict[str, Any]] = []
    for seccion in submenus or []:
        items = [
            item
            for item in seccion.get("items") or []
            if item.get("menu_item_id") in PWA_ECOM_MENU_ITEM_IDS
        ]
        if items:
            copia = dict(seccion)
            copia["items"] = items
            resultado.append(copia)
    return resultado


def filtrar_submenus_mpr_para_pwa_movil(
    submenus: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Deja solo tablero KPIs e inventario del sidebar MPR en móvil."""
    resultado: List[Dict[str, Any]] = []
    for seccion in submenus or []:
        items = [
            item
            for item in seccion.get("items") or []
            if item.get("menu_item_id") in PWA_MPR_MENU_ITEM_IDS
        ]
        if items:
            copia = dict(seccion)
            copia["items"] = items
            resultado.append(copia)
    return resultado


def filtrar_apps_menu_para_pwa_movil(
    apps_menu: List[Dict[str, Any]],
    request: Optional[HttpRequest],
    user=None,
) -> List[Dict[str, Any]]:
    """
    Deja solo las apps permitidas en navbar cuando el cliente es móvil (PWA).

    Los permisos por ítem ya debieron aplicarse en `apps_visibles_sin_filtro_pwa`;
    aquí solo se restringe el conjunto de módulos a los previstos para Nivel A y
    se excluye TPV/e-com si el usuario no los tiene habilitados en menú.
    """
    if not request or not getattr(request, "is_mobile", False):
        return apps_menu
    usuario = user or getattr(request, "user", None)
    resultado: List[Dict[str, Any]] = []
    for app in apps_menu:
        app_id = app.get("id")
        if app_id not in PWA_MENU_APP_IDS:
            continue
        if app_id == "self_checkout" and not usuario_tiene_tpv_en_menu(usuario, request):
            continue
        if app_id == "ecom" and not usuario_tiene_ecom_en_menu(usuario, request):
            continue
        if app_id == "stock" and not usuario_tiene_conteo_en_menu(usuario, request):
            continue
        if app_id == "mpr" and not usuario_tiene_mpr_en_menu(usuario, request):
            continue
        app_copy = dict(app)
        if app_id == "ecom" and app_copy.get("submenus"):
            app_copy["submenus"] = filtrar_submenus_ecom_para_pwa_movil(app_copy["submenus"])
        if app_id == "stock" and app_copy.get("submenus"):
            app_copy["submenus"] = filtrar_submenus_stock_para_pwa_movil(app_copy["submenus"])
        if app_id == "mpr" and app_copy.get("submenus"):
            app_copy["submenus"] = filtrar_submenus_mpr_para_pwa_movil(app_copy["submenus"])
        resultado.append(app_copy)
    return resultado


def sidebar_visible_en_pwa(
    current_app_id: Optional[str],
    request: Optional[HttpRequest] = None,
    user=None,
) -> bool:
    """True si el sidebar contextual puede mostrarse en móvil para esta app."""
    if not current_app_id or current_app_id not in PWA_MENU_APP_IDS:
        return False
    if current_app_id == "self_checkout":
        usuario = user or (getattr(request, "user", None) if request else None)
        return usuario_tiene_tpv_en_menu(usuario, request)
    if current_app_id == "ecom":
        usuario = user or (getattr(request, "user", None) if request else None)
        return usuario_tiene_ecom_en_menu(usuario, request)
    if current_app_id == "stock":
        usuario = user or (getattr(request, "user", None) if request else None)
        return usuario_tiene_conteo_en_menu(usuario, request)
    if current_app_id == "mpr":
        usuario = user or (getattr(request, "user", None) if request else None)
        return usuario_tiene_mpr_en_menu(usuario, request)
    return True
