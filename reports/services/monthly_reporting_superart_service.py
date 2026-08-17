# -*- coding: utf-8 -*-
"""Catálogo SuperArt congelado y QA pendientes Puma."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from django.db import transaction

from reports.models import (
    MonthlyReportingSuperArtCatalogEntry,
    MonthlyReportingSuperArtCatalogVersion,
    MonthlyReportingSuperArtQAPending,
)


def get_active_catalog_version() -> Optional[MonthlyReportingSuperArtCatalogVersion]:
    return (
        MonthlyReportingSuperArtCatalogVersion.objects.filter(
            estado=MonthlyReportingSuperArtCatalogVersion.Estado.ACTIVE
        )
        .order_by("-version")
        .first()
    )


def build_genero_lookup(version: MonthlyReportingSuperArtCatalogVersion) -> dict[str, str]:
    return {
        entry.superart.strip().upper(): entry.genero
        for entry in version.entries.all()
    }


def classify_superart(superart: str, lookup: dict[str, str]) -> Optional[str]:
    key = (superart or "").strip().upper()
    if not key:
        return None
    return lookup.get(key)


@transaction.atomic
def activate_catalog_version(
    version: MonthlyReportingSuperArtCatalogVersion,
    *,
    actor_id_usuario: Optional[int] = None,
    actor_cod_usuario: str = "",
    actor_nombre: str = "",
) -> MonthlyReportingSuperArtCatalogVersion:
    MonthlyReportingSuperArtCatalogVersion.objects.filter(
        estado=MonthlyReportingSuperArtCatalogVersion.Estado.ACTIVE
    ).update(estado=MonthlyReportingSuperArtCatalogVersion.Estado.ARCHIVED)
    version.estado = MonthlyReportingSuperArtCatalogVersion.Estado.ACTIVE
    version.actor_id_usuario = actor_id_usuario
    version.actor_cod_usuario = actor_cod_usuario
    version.actor_nombre = actor_nombre
    version.save(
        update_fields=[
            "estado",
            "actor_id_usuario",
            "actor_cod_usuario",
            "actor_nombre",
        ]
    )
    return version


@transaction.atomic
def seed_catalog_entries(
    version: MonthlyReportingSuperArtCatalogVersion,
    entries: Iterable[tuple[str, str]],
) -> int:
    created = 0
    for superart, genero in entries:
        _, was_created = MonthlyReportingSuperArtCatalogEntry.objects.get_or_create(
            version=version,
            superart=superart.strip(),
            defaults={"genero": genero},
        )
        if was_created:
            created += 1
    return created


@transaction.atomic
def register_qa_pending(superart: str, sample: Optional[Dict[str, Any]] = None) -> MonthlyReportingSuperArtQAPending:
    key = (superart or "").strip()
    pending, created = MonthlyReportingSuperArtQAPending.objects.get_or_create(
        superart=key,
        defaults={"sample_json": sample or {}, "occurrence_count": 1},
    )
    if not created:
        pending.occurrence_count += 1
        if sample:
            pending.sample_json = {**(pending.sample_json or {}), **sample}
        pending.save(update_fields=["occurrence_count", "sample_json", "last_seen_at"])
    return pending


def make_classify_fn(version: Optional[MonthlyReportingSuperArtCatalogVersion] = None):
    """Factory: classify_superart bound al catálogo activo o versión dada."""
    ver = version or get_active_catalog_version()
    if ver is None:
        lookup: dict[str, str] = {}
    else:
        lookup = build_genero_lookup(ver)

    def _fn(superart: str) -> Optional[str]:
        return classify_superart(superart, lookup)

    return _fn
