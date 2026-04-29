"""Orden y columnas en exportación Excel (alineado con dashboard / schema)."""

from unittest.mock import Mock

from django.test import SimpleTestCase

from reports.models import ReportDefinition
from reports.services.export_service import ExportService


class ExportColumnOrderTest(SimpleTestCase):
    def setUp(self):
        self.svc = ExportService(Mock())

    def test_ventas_netas_solo_columnas_conocidas_en_orden(self):
        r = ReportDefinition(slug="ventas_netas", config={})
        row = {
            "ventas_brutas": 1,
            "mes_formato": "ene",
            "nombre_sucursal": "S1",
            "nro_punto_venta": 1,
            "ventas_netas": 10,
            "notas_credito": 2,
            "id_sucursal": 9,
        }
        h = self.svc._resolve_export_headers(r, row)
        self.assertEqual(
            h,
            [
                "mes_formato",
                "nombre_sucursal",
                "nro_punto_venta",
                "ventas_netas",
                "notas_credito",
                "ventas_brutas",
            ],
        )

    def test_uninvoiced_remitos_excluye_ids_y_ordena_conocidas(self):
        r = ReportDefinition(slug="uninvoiced_remitos", config={})
        row = {
            "id_punto_venta": 1,
            "subtotal_desc": 100,
            "punto_venta": "PV1",
            "fecha": "01/01/2025",
            "id_sucursal": 2,
            "nro_comprobante": "R1",
            "sucursal": "Centro",
        }
        h = self.svc._resolve_export_headers(r, row)
        self.assertNotIn("id_sucursal", h)
        self.assertNotIn("id_punto_venta", h)
        self.assertEqual(h[:5], ["fecha", "nro_comprobante", "sucursal", "punto_venta", "subtotal_desc"])

    def test_pedidos_pendientes_prefiere_fecha_nro_cliente_subtotal(self):
        r = ReportDefinition(slug="pedidos-pendientes", config={})
        row = {
            "subtotal_desc": 1,
            "nro_comprobante": "P1",
            "fecha": "01/01/2025",
            "tipo_comprobante": "PED",
            "estado": "X",
            "otro": "z",
        }
        h = self.svc._resolve_export_headers(r, row)
        self.assertNotIn("tipo_comprobante", h)
        self.assertNotIn("estado", h)
        self.assertEqual(h[:3], ["fecha", "nro_comprobante", "subtotal_desc"])
        self.assertEqual(h[-1], "otro")

    def test_ventas_objetivos_vs_bo_orden_alineado_tabla_web(self):
        r = ReportDefinition(slug="ventas-objetivos-vs-bo", config={})
        row = {
            "cod_viajante": 1,
            "nombre_vendedor": "A",
            "codigo_cliente": 10,
            "nombre_cliente": "C",
            "objetivo": 100.0,
            "falta": 0.0,
            "cantidades_vendidas": 1.0,
            "facturacion": 50.0,
            "remitos": 0.0,
            "total": 50.0,
            "bo_con_stock": 1.0,
            "bo_con_ingreso": 2.0,
            "bo_sin_stock": 3.0,
            "backorder_total": 6.0,
        }
        h = self.svc._resolve_export_headers(r, row)
        self.assertEqual(
            h,
            [
                "cod_viajante",
                "nombre_vendedor",
                "codigo_cliente",
                "nombre_cliente",
                "objetivo",
                "falta",
                "cantidades_vendidas",
                "facturacion",
                "remitos",
                "total",
                "bo_con_stock",
                "bo_con_ingreso",
                "bo_sin_stock",
                "backorder_total",
            ],
        )
