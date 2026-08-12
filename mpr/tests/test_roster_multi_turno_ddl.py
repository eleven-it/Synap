# -*- coding: utf-8 -*-
"""Tests DDL roster multi-turno vía legacy_mysql_schema.catalog (Fase 1)."""
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.apps import apps
from django.test import SimpleTestCase


def _indice_side_effect(vieja: bool = True, nueva: bool = False):
    """Simula SHOW INDEX: vieja UK presente, nueva ausente."""

    def _fn(cursor, table, name):
        if name == "uk_mpr_roster_fecha_operario_turno":
            return nueva
        if name == "uk_mpr_roster_fecha_operario":
            return vieja
        return False

    return _fn


class RosterMultiTurnoDdlTests(SimpleTestCase):
    """Proveedor ``mpr_roster_multi_turno`` y SQL de referencia."""

    def test_sql_file_existe_y_documenta_uk(self):
        app_path = Path(apps.get_app_config("mpr").path)
        sql_path = app_path / "sql" / "005_mpr_roster_multi_turno_uk.sql"
        self.assertTrue(sql_path.is_file(), f"Falta {sql_path}")
        content = sql_path.read_text(encoding="utf-8")
        self.assertIn("uk_mpr_roster_fecha_operario_turno", content)
        self.assertIn("uk_mpr_roster_fecha_operario", content)
        self.assertIn("no DELETE", content)

    def test_create_core_tables_usa_uk_multi_turno(self):
        app_path = Path(apps.get_app_config("mpr").path)
        sql_path = app_path / "sql" / "001_mpr_core_tables.sql"
        content = sql_path.read_text(encoding="utf-8")
        self.assertIn(
            "uk_mpr_roster_fecha_operario_turno (fecha, id_operario, id_mpr_turno)",
            content,
        )
        self.assertNotIn(
            "uk_mpr_roster_fecha_operario (fecha, id_operario)",
            content,
        )

    def test_proveedor_registrado(self):
        from core.services.legacy_mysql_schema.catalog import (
            PROVIDER_REGISTRY,
            run_mpr_roster_multi_turno_mysql,
        )

        provider = next(
            (p for p in PROVIDER_REGISTRY if p["id"] == "mpr_roster_multi_turno"),
            None,
        )
        self.assertIsNotNone(provider, "Falta provider mpr_roster_multi_turno")
        self.assertEqual(provider["risk"], "medio")
        self.assertIn("multi-turno", provider["title"].lower())
        self.assertIs(provider["run"], run_mpr_roster_multi_turno_mysql)

    @patch("core.services.legacy_mysql_schema.catalog.nombre_tabla_real", return_value=None)
    def test_skip_si_tabla_ausente(self, _mock_nombre):
        from core.services.legacy_mysql_schema.catalog import run_mpr_roster_multi_turno_mysql

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        result = run_mpr_roster_multi_turno_mysql(conn)

        self.assertTrue(result["success"])
        self.assertTrue(
            any("ausente" in m.lower() or "skip" in m.lower() for m in result["migrations_applied"])
        )
        cursor.execute.assert_not_called()
        conn.commit.assert_called_once()

    @patch(
        "core.services.legacy_mysql_schema.catalog.indice_existe",
        side_effect=_indice_side_effect(vieja=False, nueva=True),
    )
    @patch(
        "core.services.legacy_mysql_schema.catalog.nombre_tabla_real",
        return_value="mpr_roster_dia",
    )
    def test_noop_si_uk_nueva_presente(self, _mock_nombre, _mock_idx):
        from core.services.legacy_mysql_schema.catalog import run_mpr_roster_multi_turno_mysql

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        result = run_mpr_roster_multi_turno_mysql(conn)

        self.assertTrue(result["success"])
        cursor.execute.assert_not_called()
        self.assertTrue(any("no-op" in m.lower() for m in result["migrations_applied"]))

    @patch(
        "core.services.legacy_mysql_schema.catalog.indice_existe",
        side_effect=_indice_side_effect(vieja=True, nueva=False),
    )
    @patch(
        "core.services.legacy_mysql_schema.catalog.nombre_tabla_real",
        return_value="mpr_roster_dia",
    )
    def test_migra_uk_vieja_a_nueva(self, _mock_nombre, _mock_idx):
        from core.services.legacy_mysql_schema.catalog import run_mpr_roster_multi_turno_mysql

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        result = run_mpr_roster_multi_turno_mysql(conn)

        self.assertTrue(result["success"])
        statements = [call.args[0] for call in cursor.execute.call_args_list if call.args]
        joined = " ".join(statements).lower()
        self.assertIn("drop index", joined)
        self.assertIn("uk_mpr_roster_fecha_operario", joined)
        self.assertIn("uk_mpr_roster_fecha_operario_turno", joined)
        self.assertNotIn("delete from", joined)
        self.assertNotIn("update mpr_roster_dia", joined)
        conn.commit.assert_called_once()

    @patch(
        "core.services.legacy_mysql_schema.catalog.indice_existe",
        side_effect=_indice_side_effect(vieja=True, nueva=False),
    )
    @patch(
        "core.services.legacy_mysql_schema.catalog.nombre_tabla_real",
        return_value="mpr_roster_dia",
    )
    def test_doble_ejecucion_idempotente(self, _mock_nombre, mock_idx):
        from core.services.legacy_mysql_schema.catalog import run_mpr_roster_multi_turno_mysql

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        result1 = run_mpr_roster_multi_turno_mysql(conn)
        self.assertTrue(result1["success"])
        alter_count = cursor.execute.call_count

        mock_idx.side_effect = _indice_side_effect(vieja=False, nueva=True)
        cursor.execute.reset_mock()
        result2 = run_mpr_roster_multi_turno_mysql(conn)
        self.assertTrue(result2["success"])
        cursor.execute.assert_not_called()
        self.assertGreaterEqual(alter_count, 2)

    @patch(
        "core.services.legacy_mysql_schema.catalog.indice_existe",
        side_effect=_indice_side_effect(vieja=True, nueva=False),
    )
    @patch(
        "core.services.legacy_mysql_schema.catalog.nombre_tabla_real",
        return_value="mpr_roster_dia",
    )
    def test_checklist_conteo_filas_sin_delete(self, _mock_nombre, _mock_idx):
        """Smoke helper: el proveedor no emite DELETE/UPDATE masivo de roster."""
        from core.services.legacy_mysql_schema.catalog import run_mpr_roster_multi_turno_mysql

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        run_mpr_roster_multi_turno_mysql(conn)

        statements = [
            str(call.args[0]).lower() for call in cursor.execute.call_args_list if call.args
        ]
        for forbidden in ("delete from mpr_roster_dia", "truncate", "update mpr_roster_dia"):
            self.assertFalse(any(forbidden in s for s in statements), forbidden)
