"""
Integración con MySQL legacy (conexión `mysql` en DATABASES).
Marcar con @pytest.mark.integration — omitir en CI sin base disponible.
"""

import pytest


@pytest.mark.integration
class TestPriceCalculatorIntegration:
    def test_mysql_legacy_responde(self, legacy_db_connection):
        with legacy_db_connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            one = cursor.fetchone()[0]
        assert one == 1

    def test_existencia_tabla_articulo_o_skip(self, legacy_db_connection):
        """Si existe `articulo`, al menos hay columnas; si no, skip."""
        with legacy_db_connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = 'articulo'"
            )
            existe = cursor.fetchone()[0]
        if not existe:
            pytest.skip("Base sin tabla articulo (entorno vacío)")
        with legacy_db_connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM articulo LIMIT 1")
            row = cursor.fetchone()
        assert row is not None
