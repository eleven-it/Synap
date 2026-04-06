"""
Paridad con valores documentados en docs/ecom/REVERSE_ENGINEERING.md (Apéndice A).
"""

import pytest

from ecom.services.mayoristapp_relays import MAYORISTAPP_RELAY_PATHS
from ecom.services.migration_info import (
    FRAMEWORK_LABEL,
    MAYORISTAPP_PHP_FILE_COUNT,
    PHP_FILE_COUNT,
    RELAY_ENDPOINT_COUNT,
    SOURCE_LABEL,
    build_migration_info_dict,
)


@pytest.mark.django_db
def test_parity_snapshot_migration_info():
    d = build_migration_info_dict()
    assert d["php_file_count"] == PHP_FILE_COUNT == 1287
    assert d["mayoristapp_php_file_count"] == MAYORISTAPP_PHP_FILE_COUNT == 1276
    assert d["relay_endpoint_count"] == RELAY_ENDPOINT_COUNT == 44
    assert len(MAYORISTAPP_RELAY_PATHS) == RELAY_ENDPOINT_COUNT
    assert d["framework"] == FRAMEWORK_LABEL
    assert d["source"] == SOURCE_LABEL
    assert "checkpoints" in d
    assert isinstance(d["checkpoints"], list)
    slugs = {c["module_slug"] for c in d["checkpoints"]}
    assert "mayoristapp_clientes" in slugs
    assert "mayoristapp_comprobantes" in slugs
    assert "mayoristapp_ctacte" in slugs
    assert "mayoristapp_recibos" in slugs
    assert "mayoristapp_fe" in slugs
