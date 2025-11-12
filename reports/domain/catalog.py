from __future__ import annotations

from typing import List

from ..services.catalog_service import CatalogService, CatalogEntry


def build_catalog_for_user(user, empresa_id: int | None) -> List[CatalogEntry]:
    """Devuelve catálogo filtrado para el usuario."""
    service = CatalogService(user)
    return service.get_catalog(empresa_id)


