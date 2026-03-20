"""
Lectura y actualización de la visibilidad granular del menú navbar (supervisor).

Ver docs/general/NAVBAR_OCULTACION_GLOBAL_SUPERVISOR.md
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Módulo que no puede ocultarse desde la UI (siempre visible en navbar).
APP_ID_SIEMPRE_VISIBLE = "archivo"


def _normalizar_modulos_ocultos(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    out = []
    for x in raw:
        if isinstance(x, str) and x.strip():
            s = x.strip()
            if s != APP_ID_SIEMPRE_VISIBLE:
                out.append(s)
    return list(dict.fromkeys(out))


def _normalizar_items_ocultos(raw: Any) -> Dict[str, List[str]]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, List[str]] = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not k.strip():
            continue
        app_id = k.strip()
        if app_id == APP_ID_SIEMPRE_VISIBLE:
            continue
        if not isinstance(v, list):
            out[app_id] = []
            continue
        ids = []
        for mid in v:
            if isinstance(mid, str) and mid.strip():
                ids.append(mid.strip())
        out[app_id] = list(dict.fromkeys(ids))
    return out


def cargar_estado_granular() -> Tuple[Set[str], Dict[str, Set[str]]]:
    """
    Retorna (modulos_ocultos_set, items_ocultos_por_app: app_id -> set(menu_item_id)).
    Si falla DB o migración, retorna conjuntos vacíos.
    """
    try:
        from core.models import NavbarMenuGlobal

        row = NavbarMenuGlobal.get_solo()
        mods = set(_normalizar_modulos_ocultos(getattr(row, "modulos_ocultos", None)))
        raw_items = _normalizar_items_ocultos(getattr(row, "items_menu_ocultos", None))
        items = {app: set(ids) for app, ids in raw_items.items()}
        return mods, items
    except Exception as e:
        logger.debug("Estado granular navbar no disponible: %s", e)
        return set(), {}


def app_visible_en_navbar_granular(app_id: str, modulos_ocultos: Set[str]) -> bool:
    if app_id == APP_ID_SIEMPRE_VISIBLE:
        return True
    return app_id not in modulos_ocultos


def item_visible_en_navbar_granular(
    app_id: str,
    menu_item_id: Optional[str],
    modulos_ocultos: Set[str],
    items_ocultos_por_app: Dict[str, Set[str]],
) -> bool:
    # Archivo: siempre visible en navbar (ítems no se ocultan por granular).
    if app_id == APP_ID_SIEMPRE_VISIBLE:
        return True
    if not menu_item_id:
        return True
    if not app_visible_en_navbar_granular(app_id, modulos_ocultos):
        return False
    ocultos = items_ocultos_por_app.get(app_id) or set()
    return menu_item_id not in ocultos


def validar_app_y_item_contra_menu(app_id: str, menu_item_id: Optional[str]) -> bool:
    """True si app_id existe en APPS_MENU y (si menu_item_id) coincide con alguna hoja."""
    from core.utils.utils import APPS_MENU, iter_menu_hojas_apps_menu

    if app_id == APP_ID_SIEMPRE_VISIBLE:
        return False

    ids_app = {a["id"] for a in APPS_MENU}
    if app_id not in ids_app:
        return False
    if menu_item_id is None:
        return True
    for aid, _, _, _, _, mid in iter_menu_hojas_apps_menu():
        if aid == app_id and mid == menu_item_id:
            return True
    return False


def establecer_modulo_visible(app_id: str, visible: bool) -> bool:
    if app_id == APP_ID_SIEMPRE_VISIBLE:
        return False
    if not validar_app_y_item_contra_menu(app_id, None):
        return False
    from core.models import NavbarMenuGlobal

    row = NavbarMenuGlobal.get_solo()
    mods = _normalizar_modulos_ocultos(row.modulos_ocultos)
    s = set(mods)
    if visible:
        s.discard(app_id)
    else:
        s.add(app_id)
    row.modulos_ocultos = sorted(s)
    row.save(update_fields=["modulos_ocultos", "updated_at"])
    return True


def construir_grupos_visibilidad_navbar_ui() -> List[Dict[str, Any]]:
    """
    Lista de dicts por módulo navbar (excluye Archivo) para la pestaña supervisor:
    app_id, nombre, modulo_visible, filas[{seccion, label, url_name, menu_item_id, item_visible}].
    """
    from collections import defaultdict

    from core.utils.utils import APPS_MENU, iter_menu_hojas_apps_menu

    mod_oc, items_oc = cargar_estado_granular()
    by_app: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for app_id, _nombre_mod, seccion, label, url_name, mid in iter_menu_hojas_apps_menu():
        item_vis = mid not in (items_oc.get(app_id) or set())
        by_app[app_id].append(
            {
                "seccion": seccion,
                "label": label,
                "url_name": url_name,
                "menu_item_id": mid,
                "item_visible": item_vis,
            }
        )
    grupos: List[Dict[str, Any]] = []
    for app in APPS_MENU:
        aid = app["id"]
        if aid == APP_ID_SIEMPRE_VISIBLE:
            continue
        grupos.append(
            {
                "app_id": aid,
                "nombre": str(app["nombre"]),
                "modulo_visible": aid not in mod_oc,
                "filas": list(by_app.get(aid, [])),
            }
        )
    return grupos


def establecer_item_visible(app_id: str, menu_item_id: str, visible: bool) -> bool:
    if not menu_item_id or not validar_app_y_item_contra_menu(app_id, menu_item_id):
        return False
    from core.models import NavbarMenuGlobal

    row = NavbarMenuGlobal.get_solo()
    items = _normalizar_items_ocultos(row.items_menu_ocultos)
    lst = list(items.get(app_id, []))
    s = set(lst)
    if visible:
        s.discard(menu_item_id)
    else:
        s.add(menu_item_id)
    items[app_id] = sorted(s)
    # Limpiar claves vacías
    items = {k: v for k, v in items.items() if v}
    row.items_menu_ocultos = items
    row.save(update_fields=["items_menu_ocultos", "updated_at"])
    return True
