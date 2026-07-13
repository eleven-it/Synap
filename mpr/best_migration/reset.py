"""Reinicio del staging Migración BEST (Postgres Synap)."""

from __future__ import annotations

from django.db import transaction

from mpr.best_migration.models import (
    BestArticuloMap,
    BestClienteMap,
    BestDepositoMap,
    BestMigrationParity,
    BestStockInicialMap,
)

STAGING_TABLAS = (
    ("artículos", BestArticuloMap),
    ("clientes", BestClienteMap),
    ("depósitos", BestDepositoMap),
    ("stock inicial", BestStockInicialMap),
    ("paridad / gate", BestMigrationParity),
)


def contar_staging_best(base_empresa: str) -> dict[str, int]:
    return {
        etiqueta: Model.objects.filter(base_empresa=base_empresa).count()
        for etiqueta, Model in STAGING_TABLAS
    }


@transaction.atomic
def reiniciar_staging_best(base_empresa: str) -> dict[str, int]:
    """
    Borra mapas y paridad BEST de ``base_empresa`` en Postgres.

    No toca MySQL AdministraNET ni Azure BEST. Retorna conteos borrados por dominio.
    """
    prev = {
        etiqueta: Model.objects.filter(base_empresa=base_empresa).count()
        for etiqueta, Model in STAGING_TABLAS
    }
    for _etiqueta, Model in STAGING_TABLAS:
        Model.objects.filter(base_empresa=base_empresa).delete()
    return prev
