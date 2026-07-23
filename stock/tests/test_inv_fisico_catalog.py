# -*- coding: utf-8 -*-
"""Tests DDL inventario físico vía legacy_mysql_schema.catalog (Fase 1)."""
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.apps import apps
from django.test import SimpleTestCase


class InvFisicoCatalogTests(SimpleTestCase):
    """Provider stock_inv_fisico_tables y archivo SQL idempotente."""

    def test_sql_file_existe_y_declara_tres_tablas(self):
        app_path = Path(apps.get_app_config("stock").path)
        sql_path = app_path / "sql" / "001_inv_fisico_tables.sql"
        self.assertTrue(sql_path.is_file(), f"Falta {sql_path}")
        content = sql_path.read_text(encoding="utf-8")
        for nombre in ("inv_fisico_campana", "inv_fisico_linea", "inv_fisico_evento"):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {nombre}", content)

    def test_sql_inv_fisico_linea_tiene_unique_campana_articulo_deposito(self):
        app_path = Path(apps.get_app_config("stock").path)
        sql_path = app_path / "sql" / "001_inv_fisico_tables.sql"
        content = sql_path.read_text(encoding="utf-8")
        self.assertIn("inv_fisico_linea", content)
        self.assertRegex(
            content,
            r"UNIQUE\s+KEY\s+\w+\s*\(\s*id_campana\s*,\s*id_articulo\s*,\s*id_deposito\s*\)",
        )

    def test_proveedor_registrado_con_riesgo_medio(self):
        from core.services.legacy_mysql_schema.catalog import (
            PROVIDER_REGISTRY,
            run_stock_inv_fisico_tables_mysql,
        )

        provider = next(
            (p for p in PROVIDER_REGISTRY if p["id"] == "stock_inv_fisico_tables"),
            None,
        )
        self.assertIsNotNone(provider, "Falta provider stock_inv_fisico_tables")
        self.assertEqual(provider["risk"], "medio")
        self.assertIn("Inventario físico", provider["title"])
        self.assertIs(provider["run"], run_stock_inv_fisico_tables_mysql)

    @patch("django.apps.apps.get_app_config")
    def test_run_provider_ejecuta_ddl_idempotente(self, mock_cfg):
        from core.services.legacy_mysql_schema.catalog import run_stock_inv_fisico_tables_mysql

        app_path = Path(__file__).resolve().parents[1]
        mock_cfg.return_value.path = str(app_path)

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        result = run_stock_inv_fisico_tables_mysql(conn)

        self.assertTrue(result["success"], result.get("message"))
        self.assertGreaterEqual(cursor.execute.call_count, 3)
        statements = [call.args[0] for call in cursor.execute.call_args_list if call.args]
        joined = "\n".join(statements)
        for tabla in ("inv_fisico_campana", "inv_fisico_linea", "inv_fisico_evento"):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {tabla}", joined)
        self.assertIn("client_event_id", joined)
        conn.commit.assert_called_once()

    @patch("django.apps.apps.get_app_config")
    def test_run_provider_falla_si_falta_sql(self, mock_cfg):
        from core.services.legacy_mysql_schema.catalog import run_stock_inv_fisico_tables_mysql

        mock_cfg.return_value.path = "/ruta/inexistente/stock"

        conn = MagicMock()
        result = run_stock_inv_fisico_tables_mysql(conn)

        self.assertFalse(result["success"])
        self.assertIn("001_inv_fisico_tables.sql", result["message"])
        conn.cursor.assert_not_called()
