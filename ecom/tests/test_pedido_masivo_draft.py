"""Tests Phase 1: draft masivo (estados) + DDL/proveedor ternas."""

from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import TestCase

from ecom.models import EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda


class TestEcomPedidoMasivoDraftEstados(TestCase):
    def test_crear_borrador_y_celdas(self):
        draft = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_test",
            id_usuario=10,
            cod_viajante=3,
            id_cliente=100,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        )
        self.assertEqual(draft.estado, "borrador")
        self.assertEqual(draft.ultimo_error, {})
        self.assertEqual(draft.codigos_movimiento, [])

        c = EcomPedidoMasivoDraftCelda.objects.create(
            draft=draft,
            id_articulo=50,
            id_cliente_domicilio=7,
            cantidad_packs=Decimal("2.5"),
        )
        self.assertEqual(draft.celdas.count(), 1)
        self.assertEqual(c.cantidad_packs, Decimal("2.5"))

    def test_unique_celda_mismo_art_dom(self):
        draft = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_test",
            id_usuario=10,
            id_cliente=100,
        )
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=draft,
            id_articulo=1,
            id_cliente_domicilio=2,
            cantidad_packs=Decimal("1"),
        )
        with self.assertRaises(IntegrityError):
            EcomPedidoMasivoDraftCelda.objects.create(
                draft=draft,
                id_articulo=1,
                id_cliente_domicilio=2,
                cantidad_packs=Decimal("3"),
            )

    def test_transicion_confirmando_a_borrador_con_error(self):
        draft = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_test",
            id_usuario=10,
            id_cliente=100,
            estado=EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
        )
        draft.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR
        draft.ultimo_error = {"7": "Stock insuficiente"}
        draft.save(update_fields=["estado", "ultimo_error", "updated_at"])
        draft.refresh_from_db()
        self.assertEqual(draft.estado, "borrador")
        self.assertEqual(draft.ultimo_error["7"], "Stock insuficiente")

    def test_confirmado_guarda_codigos(self):
        draft = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_test",
            id_usuario=10,
            id_cliente=100,
            estado=EcomPedidoMasivoDraft.ESTADO_CONFIRMADO,
            codigos_movimiento=[101, 102],
        )
        self.assertEqual(draft.codigos_movimiento, [101, 102])


class TestCatalogEcomVendedorClienteMarca(TestCase):
    def test_sql_define_unique_activo_cliente_marca(self):
        sql_path = Path(__file__).resolve().parents[1] / "sql" / "001_ecom_vendedor_cliente_marca.sql"
        self.assertTrue(sql_path.is_file())
        text = sql_path.read_text(encoding="utf-8")
        self.assertIn("ecom_vendedor_cliente_marca", text)
        self.assertIn("uk_evcm_cliente_sucursal_marca_activo", text)
        self.assertIn("ecom_usuario_viajante", text)
        self.assertIn("uk_euv_usuario", text)

    def test_split_sql_no_corta_punto_y_coma_en_comment(self):
        from core.services.legacy_mysql_schema.catalog import _split_sql_statements

        statements = _split_sql_statements(
            "CREATE TABLE ejemplo (detalle VARCHAR(255) COMMENT 'cliente; sin sucursal');\n"
            "-- comentario; de línea\n"
            "CREATE TABLE otro (id INT);"
        )

        self.assertEqual(len(statements), 2)
        self.assertIn("COMMENT 'cliente; sin sucursal'", statements[0])
        self.assertIn("CREATE TABLE otro", statements[1])

    def test_proveedor_registrado(self):
        from core.services.legacy_mysql_schema.catalog import PROVIDER_REGISTRY

        ids = [p["id"] for p in PROVIDER_REGISTRY]
        self.assertIn("ecom_vendedor_cliente_marca", ids)

    @patch("django.apps.apps.get_app_config")
    def test_run_provider_ejecuta_sql(self, mock_cfg):
        from core.services.legacy_mysql_schema.catalog import run_ecom_vendedor_cliente_marca_mysql

        app_path = Path(__file__).resolve().parents[1]
        mock_cfg.return_value.path = str(app_path)

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        result = run_ecom_vendedor_cliente_marca_mysql(conn)
        self.assertTrue(result["success"], result.get("message"))
        self.assertGreaterEqual(cursor.execute.call_count, 1)
        statements = [call.args[0] for call in cursor.execute.call_args_list if call.args]
        self.assertFalse(
            any(statement.lstrip().startswith("0 = sin sucursal") for statement in statements)
        )
        self.assertTrue(
            any(
                "CREATE TABLE IF NOT EXISTS ecom_vendedor_cliente_marca" in statement
                and "id_cliente_domicilio" in statement
                for statement in statements
            )
        )
        conn.commit.assert_called()


class TestResolverUsuarioViajante(TestCase):
    @patch("ecom.services.usuario_viajante.mysql_cursor")
    def test_resuelve_cod_viajante(self, mock_cursor_cm):
        from ecom.services.usuario_viajante import resolver_cod_viajante_usuario

        cursor = MagicMock()
        cursor.fetchone.return_value = (42,)
        mock_cursor_cm.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_cursor_cm.return_value.__exit__ = MagicMock(return_value=False)

        self.assertEqual(resolver_cod_viajante_usuario("emp1", 9), 42)

    @patch("ecom.services.usuario_viajante.mysql_cursor")
    def test_tabla_ausente_devuelve_none(self, mock_cursor_cm):
        from ecom.services.usuario_viajante import resolver_cod_viajante_usuario

        mock_cursor_cm.return_value.__enter__ = MagicMock(side_effect=Exception("no table"))
        mock_cursor_cm.return_value.__exit__ = MagicMock(return_value=False)

        self.assertIsNone(resolver_cod_viajante_usuario("emp1", 9))
