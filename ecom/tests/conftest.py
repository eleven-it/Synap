import pytest


@pytest.fixture
def legacy_db_connection():
    """Conexión Django `mysql` (AdministraNET). Usada por tests @pytest.mark.integration."""
    from django.db import connections

    conn = connections["mysql"]
    try:
        conn.ensure_connection()
    except Exception as exc:
        pytest.skip(f"MySQL legacy no disponible: {exc}")
    return conn


@pytest.fixture
def api_client():
    from django.test import Client

    return Client()


@pytest.fixture
def migration_info_expected():
    from ecom.services.migration_info import build_migration_info_dict

    return build_migration_info_dict()
