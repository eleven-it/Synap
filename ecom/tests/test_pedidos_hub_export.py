"""Exportación del mismo conjunto de pedidos que muestra el hub."""

from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase
from openpyxl import load_workbook

from ecom.services.pedidos_hub_export import (
    filtrar_pedidos_hub, generar_excel_pedidos, generar_pdf_pedidos,
)


ITEMS = [
    {"fecha": "13/11/2026", "titulo": "PED 0008-00000951", "cliente": "ARIZU SRL",
     "columna": "enviado", "tipo": "ped", "neto": 100, "total": 121},
    {"fecha": "12/11/2026", "titulo": "PED 0008-00000950", "cliente": "OTRO",
     "columna": "anulado", "tipo": "ped", "neto": 200, "total": 242},
]


class PedidosHubExportTests(SimpleTestCase):
    def test_fecha_busqueda_y_totales_no_incluyen_anulados(self):
        items = filtrar_pedidos_hub(ITEMS, busqueda="arizu", fecha_desde="2026-11-13")
        self.assertEqual(len(items), 1)
        with patch("ecom.services.pedidos_hub_export.get_empresa_para_reporte", return_value={"razon_social": "Best Sox"}):
            ws = load_workbook(BytesIO(generar_excel_pedidos(ITEMS, "administranet"))).active
        self.assertEqual(ws["G8"].value, 100)
        self.assertEqual(ws["H8"].value, 121)

    def test_pdf_exporta_documento(self):
        with patch("ecom.services.pedidos_hub_export.get_empresa_para_reporte", return_value={"razon_social": "Best Sox"}):
            pdf = generar_pdf_pedidos(ITEMS[:1], "administranet")
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_fecha_invertida_es_rechazada(self):
        with self.assertRaises(ValueError):
            filtrar_pedidos_hub(ITEMS, fecha_desde="2026-11-14", fecha_hasta="2026-11-13")
