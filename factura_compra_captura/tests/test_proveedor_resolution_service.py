"""Resolución proveedor: AdministraNET → padrón AFIP → alta en legacy."""

from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from factura_compra_captura.services.proveedor_legacy_service import ProveedorLegacyDTO
from factura_compra_captura.services.proveedor_resolution_service import (
    resolver_proveedor_desde_legacy_o_padron,
)


class ResolverProveedorPadronYAltaTests(SimpleTestCase):
    @patch(
        "factura_compra_captura.services.proveedor_resolution_service.crear_proveedor_desde_borrador"
    )
    @patch(
        "factura_compra_captura.services.proveedor_resolution_service.consultar_condicion_fiscal"
    )
    @patch(
        "factura_compra_captura.services.proveedor_resolution_service.buscar_proveedores"
    )
    def test_padron_ok_crea_proveedor_administranet(
        self, mock_buscar, mock_padron, mock_crear
    ):
        mock_buscar.return_value = []
        mock_padron.return_value = ("FA", "PROVEEDOR PADRON SA", None)
        mock_crear.return_value = ProveedorLegacyDTO(
            codigo=9001,
            nombre="PROVEEDOR PADRON SA",
            cuit="20123456789",
        )
        r = resolver_proveedor_desde_legacy_o_padron(
            base_empresa="base_test",
            cuit="20-12345678-9",
            razon_social_borrador="",
        )
        self.assertTrue(r.encontrado_legacy)
        self.assertEqual(r.codigo_proveedor_legacy, 9001)
        self.assertEqual(r.proveedor_synap.get("modo"), "legacy_vinculado")
        self.assertEqual(
            r.proveedor_synap.get("origen"), "alta_administranet_tras_padron_afip"
        )
        mock_crear.assert_called_once()

    @patch(
        "factura_compra_captura.services.proveedor_resolution_service.get_fe_config"
    )
    @patch(
        "factura_compra_captura.services.proveedor_resolution_service.crear_proveedor_desde_borrador"
    )
    @patch(
        "factura_compra_captura.services.proveedor_resolution_service.consultar_condicion_fiscal"
    )
    @patch(
        "factura_compra_captura.services.proveedor_resolution_service.buscar_proveedores"
    )
    def test_homologacion_padron_sin_persona_crea_legacy(
        self, mock_buscar, mock_padron, mock_crear, mock_fe_cfg
    ):
        mock_buscar.return_value = []
        mock_padron.return_value = (
            None,
            None,
            {"msg": "soap:Server: No existe persona con ese Id"},
        )
        mock_fe_cfg.return_value = {"homo": True}
        mock_crear.return_value = ProveedorLegacyDTO(
            codigo=8002,
            nombre="PROVEEDOR BORRADOR SA",
            cuit="20270909575",
        )
        r = resolver_proveedor_desde_legacy_o_padron(
            base_empresa="base_test",
            cuit="20-27090957-5",
            razon_social_borrador="PROVEEDOR BORRADOR SA",
            tipo_factura_borrador="FC",
        )
        self.assertTrue(r.encontrado_legacy)
        self.assertEqual(r.codigo_proveedor_legacy, 8002)
        self.assertEqual(
            r.proveedor_synap.get("origen"),
            "alta_administranet_homologacion_sin_padron",
        )
        mock_crear.assert_called_once()
        _, kwargs = mock_crear.call_args
        self.assertEqual(kwargs.get("tipo_factura_sugerida"), "FC")

    @patch(
        "factura_compra_captura.services.proveedor_resolution_service.crear_proveedor_desde_borrador"
    )
    @patch(
        "factura_compra_captura.services.proveedor_resolution_service.get_fe_config"
    )
    @patch(
        "factura_compra_captura.services.proveedor_resolution_service.consultar_condicion_fiscal"
    )
    @patch(
        "factura_compra_captura.services.proveedor_resolution_service.buscar_proveedores"
    )
    def test_produccion_padron_sin_persona_no_crea_legacy(
        self, mock_buscar, mock_padron, mock_fe_cfg, mock_crear
    ):
        mock_buscar.return_value = []
        mock_padron.return_value = (
            None,
            None,
            {"msg": "soap:Server: No existe persona con ese Id"},
        )
        mock_fe_cfg.return_value = {"homo": False}
        r = resolver_proveedor_desde_legacy_o_padron(
            base_empresa="base_test",
            cuit="20-27090957-5",
            razon_social_borrador="ALGUIEN SA",
        )
        self.assertFalse(r.encontrado_legacy)
        self.assertIsNone(r.codigo_proveedor_legacy)
        self.assertEqual(r.proveedor_synap.get("modo"), "borrador_nuevo")
        mock_crear.assert_not_called()
