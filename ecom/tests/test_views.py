import json

import pytest


@pytest.mark.django_db
class TestEcomApiViews:
    def test_health_ok(self, api_client):
        r = api_client.get("/ecom/api/health/")
        assert r.status_code == 200
        body = json.loads(r.content.decode())
        assert body["status"] == "ok"
        assert body["app"] == "ecom"

    def test_migration_info_shape(self, api_client, migration_info_expected):
        r = api_client.get("/ecom/api/migration-info/")
        assert r.status_code == 200
        body = json.loads(r.content.decode())
        assert body == migration_info_expected
        assert "checkpoints" in body
        slugs = {c.get("module_slug") for c in body["checkpoints"]}
        assert "mayoristapp_clientes" in slugs
        assert "mayoristapp_comprobantes" in slugs
        assert "mayoristapp_ctacte" in slugs
        assert "mayoristapp_recibos" in slugs
        assert "mayoristapp_fe" in slugs

    def test_mayoristapp_relay_inventory_shape(self, api_client):
        from ecom.services.mayoristapp_relays import MAYORISTAPP_RELAY_PATHS
        from ecom.services.migration_info import RELAY_ENDPOINT_COUNT

        r = api_client.get("/ecom/api/mayoristapp/relay-inventory/")
        assert r.status_code == 200
        body = json.loads(r.content.decode())
        assert body["mayoristapp_relay_count"] == RELAY_ENDPOINT_COUNT == 44
        assert body["relays"] == list(MAYORISTAPP_RELAY_PATHS)
