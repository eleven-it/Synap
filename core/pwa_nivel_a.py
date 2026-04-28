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


def filtrar_apps_menu_para_pwa_movil(
    apps_menu: List[Dict[str, Any]],
    request: Optional[HttpRequest],
) -> List[Dict[str, Any]]:
    """
    Deja solo las apps permitidas en navbar cuando el cliente es móvil (PWA).

    Los permisos por ítem ya debieron aplicarse en `apps_visibles_para_usuario`;
    aquí solo se restringe el conjunto de módulos a los previstos para Nivel A.
    """
    if not request or not getattr(request, "is_mobile", False):
        return apps_menu
    return [a for a in apps_menu if a.get("id") in PWA_MENU_APP_IDS]


def sidebar_visible_en_pwa(current_app_id: Optional[str]) -> bool:
    """True si el sidebar contextual puede mostrarse en móvil para esta app."""
    if not current_app_id:
        return False
    return current_app_id in PWA_MENU_APP_IDS
