import json

import pytest


@pytest.mark.django_db
class TestFlujoMetadatos:
    def test_health_y_migration_info_consistentes(self, api_client, migration_info_expected):
        h = api_client.get("/ecom/api/health/")
        m = api_client.get("/ecom/api/migration-info/")
        assert h.status_code == 200
        assert m.status_code == 200
        info = json.loads(m.content.decode())
        assert info["source"] == migration_info_expected["source"]
        assert info["php_file_count"] >= 1000
