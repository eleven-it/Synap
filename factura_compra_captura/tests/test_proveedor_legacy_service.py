from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from factura_compra_captura.services.proveedor_legacy_service import (
    buscar_proveedor_por_cuit,
    crear_proveedor_desde_borrador,
)


class _ConnCtx:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, exc_type, exc, tb):
        return False


class ProveedorLegacyServiceTests(SimpleTestCase):
    @patch("factura_compra_captura.services.proveedor_legacy_service.get_connection")
    def test_buscar_proveedor_por_cuit(self, mock_get_connection):
        cursor = MagicMock()
        cursor.fetchone.return_value = (123, "Proveedor Uno", "30711222333")
        conn = MagicMock()
        conn.cursor.return_value = cursor
        mock_get_connection.return_value = _ConnCtx(conn)

        dto = buscar_proveedor_por_cuit("empresa_test", "30-71122233-3")

        self.assertIsNotNone(dto)
        self.assertEqual(dto.codigo, 123)
        self.assertEqual(dto.nombre, "Proveedor Uno")

    @patch("factura_compra_captura.services.proveedor_legacy_service.get_connection")
    def test_crear_proveedor_desde_borrador_alta_minima(self, mock_get_connection):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            None,   # lookup por CUIT (no existe)
            (999,), # max(codigo)+1
        ]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        mock_get_connection.return_value = _ConnCtx(conn)

        dto = crear_proveedor_desde_borrador(
            base_empresa="empresa_test",
            cuit="30711222333",
            razon_social="Proveedor Nuevo SA",
            tipo_factura_sugerida="FA",
        )

        self.assertEqual(dto.codigo, 999)
        self.assertEqual(dto.nombre, "Proveedor Nuevo SA")
        self.assertTrue(conn.commit.called)
        self.assertTrue(cursor.execute.called)
