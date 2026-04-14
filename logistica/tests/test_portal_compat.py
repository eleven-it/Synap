"""Contrato portal_compat (sin MySQL)."""

from django.test import SimpleTestCase

from logistica.portal_compat import entrega_desde_detalle_remito


class PortalCompatTests(SimpleTestCase):
    def test_entrega_desde_detalle_remito_mapea_estado(self):
        d = {
            "codMovRemito": 123,
            "nroRemito": "0001-00000099",
            "entregado": "Si",
            "motivo_no_entrega": None,
            "detalle_no_entrega": None,
            "fechaHoraEntregaB": "10/04/2026 14:00",
            "nombreUsuarioNoEntrega": "",
        }
        v = entrega_desde_detalle_remito(d)
        self.assertEqual(v.cod_mov_remito, 123)
        self.assertEqual(v.estado_entrega_etiqueta, "Entregado")
        self.assertEqual(v.fecha_hora_entrega, "10/04/2026 14:00")
