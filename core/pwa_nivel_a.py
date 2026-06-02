"""
Constantes y helpers para la UI móvil / PWA (Nivel A).

Debe mantenerse alineado con `MobileLevelAOnlyMiddleware`: solo rutas y módulos
explicitamente soportados en dispositivos móviles.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from django.http import HttpRequest

# IDs de `APPS_MENU` (`app["id"]`) que pueden mostrarse en el menú principal en móvil/PWA.
PWA_MENU_APP_IDS = frozenset({"self_checkout"})


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


def tpv_visible_en_movil(user, request: Optional[HttpRequest] = None) -> bool:
    """TPV accesible en móvil: el usuario tiene el módulo activo en menú (no solo PWA)."""
    return usuario_tiene_tpv_en_menu(user, request)


def filtrar_apps_menu_para_pwa_movil(
    apps_menu: List[Dict[str, Any]],
    request: Optional[HttpRequest],
    user=None,
) -> List[Dict[str, Any]]:
    """
    Deja solo las apps permitidas en navbar cuando el cliente es móvil (PWA).

    Los permisos por ítem ya debieron aplicarse en `apps_visibles_sin_filtro_pwa`;
    aquí solo se restringe el conjunto de módulos a los previstos para Nivel A y
    se excluye TPV si el usuario no lo tiene habilitado en menú.
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
        resultado.append(app)
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
    return True
