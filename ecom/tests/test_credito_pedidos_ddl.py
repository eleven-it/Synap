# -*- coding: utf-8 -*-
"""Tests DDL workflow crédito pedidos vía legacy_mysql_schema.catalog (Fase 0)."""
import inspect
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


class CreditoPedidosDdlTests(SimpleTestCase):
    """Proveedor ecom_credito_pedidos: tablas, columnas comp_ped y flags configuracion_ecom."""

    TABLAS_ESPERADAS = (
        "ecom_credito_politica",
        "ecom_credito_evaluacion",
        "ecom_credito_evento",
        "ecom_credito_plantilla_aviso",
        "ecom_credito_aviso_log",
    )

    COLUMNAS_COMP_PED = ("credito_hold_prep", "estado_credito_finanzas")

    FLAGS_CONFIG = (
        "ecom_credito_pedidos_activa",
        "ecom_credito_hold_prep_activo",
        "ecom_credito_aviso_sla_horas",
    )

    def test_proveedor_registrado_en_catalogo(self):
        from core.services.legacy_mysql_schema.catalog import (
            PROVIDER_REGISTRY,
            run_ecom_credito_pedidos_mysql,
        )

        provider = next(
            (p for p in PROVIDER_REGISTRY if p["id"] == "ecom_credito_pedidos"),
            None,
        )
        self.assertIsNotNone(provider, "Falta provider ecom_credito_pedidos")
        self.assertEqual(provider["risk"], "bajo")
        self.assertIn("crédito", provider["title"].lower())
        self.assertIs(provider["run"], run_ecom_credito_pedidos_mysql)

    def test_funcion_proveedor_declara_tablas_y_columnas(self):
        from core.services.legacy_mysql_schema import catalog

        source = inspect.getsource(catalog.run_ecom_credito_pedidos_mysql)
        for tabla in self.TABLAS_ESPERADAS:
            self.assertIn(f"CREATE TABLE {tabla}", source, msg=tabla)
        for col in self.COLUMNAS_COMP_PED:
            self.assertIn(col, source, msg=col)
        config_keys = {row["key_permiso"] for row in catalog._ECOM_CREDITO_PEDIDOS_CONFIG}
        for flag in self.FLAGS_CONFIG:
            self.assertIn(flag, config_keys, msg=flag)

    @patch(
        "core.services.legacy_mysql_schema.catalog._ecom_config_key_existe",
        return_value=False,
    )
    @patch(
        "core.services.legacy_mysql_schema.catalog._columna_existe",
        return_value=False,
    )
    @patch(
        "core.services.legacy_mysql_schema.catalog.nombre_tabla_real",
        return_value="comp_ped",
    )
    @patch(
        "core.services.legacy_mysql_schema.catalog._tabla_existe",
        return_value=False,
    )
    def test_run_provider_ejecuta_ddl_idempotente(
        self,
        _mock_tabla,
        _mock_nombre,
        _mock_col,
        _mock_cfg_key,
    ):
        from core.services.legacy_mysql_schema.catalog import run_ecom_credito_pedidos_mysql

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        result = run_ecom_credito_pedidos_mysql(conn)

        self.assertTrue(result["success"], result.get("message"))
        statements = [call.args[0] for call in cursor.execute.call_args_list if call.args]
        joined = "\n".join(statements)
        for tabla in self.TABLAS_ESPERADAS:
            self.assertIn(f"CREATE TABLE {tabla}", joined, msg=tabla)
        self.assertIn("credito_hold_prep", joined)
        self.assertIn("estado_credito_finanzas", joined)
        self.assertGreaterEqual(cursor.execute.call_count, len(self.TABLAS_ESPERADAS))
        conn.commit.assert_called()

    @patch(
        "core.services.legacy_mysql_schema.catalog._ecom_config_key_existe",
        return_value=False,
    )
    @patch(
        "core.services.legacy_mysql_schema.catalog._columna_existe",
        return_value=False,
    )
    @patch(
        "core.services.legacy_mysql_schema.catalog.nombre_tabla_real",
        return_value="comp_ped",
    )
    @patch(
        "core.services.legacy_mysql_schema.catalog._tabla_existe",
        return_value=False,
    )
    def test_run_provider_siembra_sla_default_24(
        self,
        _mock_tabla,
        _mock_nombre,
        _mock_col,
        _mock_cfg_key,
    ):
        from core.services.legacy_mysql_schema.catalog import run_ecom_credito_pedidos_mysql

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        run_ecom_credito_pedidos_mysql(conn)

        inserts = [
            call.args
            for call in cursor.execute.call_args_list
            if call.args and "INSERT INTO" in str(call.args[0])
        ]
        sla_rows = [
            args for args in inserts if args[1][0] == "ecom_credito_aviso_sla_horas"
        ]
        self.assertTrue(sla_rows, "Debe insertar ecom_credito_aviso_sla_horas")
        self.assertEqual(sla_rows[0][1][5], "24")
