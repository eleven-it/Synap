"""Registro de rutas web listados mayoristapp (F1/F2)."""

from __future__ import annotations

from django.urls import path

from ecom.mayoristapp_listado_config import MAYORISTAPP_LISTADOS, PORTAL_CLIENTE_LISTADOS
from ecom.mayoristapp_listado_views import ClientesMayoristappView, listado_view_factory


def mayoristapp_listado_urlpatterns():
    """Genera urlpatterns para shells F1/F2."""
    patterns = [
        path(
            "mayoristapp/clientes/",
            ClientesMayoristappView.as_view(),
            name="mayoristapp_clientes",
        ),
    ]
    for slug in MAYORISTAPP_LISTADOS:
        name = f"mayoristapp_listado_{slug.replace('-', '_')}"
        patterns.append(
            path(
                f"mayoristapp/listado/{slug}/",
                listado_view_factory(slug).as_view(),
                name=name,
            )
        )
    for slug in PORTAL_CLIENTE_LISTADOS:
        name = f"mayoristapp_portal_{slug.replace('-', '_')}"
        patterns.append(
            path(
                f"mayoristapp/portal/{slug}/",
                listado_view_factory(slug, portal=True).as_view(),
                name=name,
            )
        )
    return patterns
