"""Exportación del mismo conjunto de pedidos que muestra el hub."""

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import call, patch

from django.test import SimpleTestCase
from openpyxl import load_workbook
from pypdf import PdfReader, PdfWriter

from ecom.pedido_gestion_views import PedidosHubItemPDFAPIView
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

    def test_excel_usa_domicilio_adicional_completo(self):
        item = {**ITEMS[0], "sucursal": "Sucursal 1", "meta": {"sucursal": "ROQUE SAENZ PEÑA 90 - JUNIN"}}
        with patch("ecom.services.pedidos_hub_export.get_empresa_para_reporte", return_value={"razon_social": "Best Sox"}):
            ws = load_workbook(BytesIO(generar_excel_pedidos([item], "administranet"))).active
        self.assertEqual(ws["D4"].value, "Domicilio adicional")
        self.assertEqual(ws["D5"].value, "ROQUE SAENZ PEÑA 90 - JUNIN")

    @patch("ecom.pedido_gestion_views._session_base_empresa", return_value="administranet")
    @patch("ecom.pedido_gestion_views._session_user", return_value={"nombre_puesto": "Vendedor"})
    @patch("ecom.pedido_gestion_views.construir_hub_pedidos", return_value={"items": []})
    @patch("ecom.pedido_gestion_views.generar_pedido_pdf")
    def test_pdf_individual_rechaza_pedido_fuera_de_cartera(self, generar, _hub, _user, _base):
        response = PedidosHubItemPDFAPIView().get(SimpleNamespace(session={}), "ped", 123)
        self.assertEqual(response.status_code, 404)
        generar.assert_not_called()

    @patch("ecom.pedido_gestion_views._session_base_empresa", return_value="administranet")
    @patch("ecom.pedido_gestion_views._session_user", return_value={"nombre_puesto": "Vendedor"})
    @patch("ecom.pedido_gestion_views.construir_hub_pedidos", return_value={"items": [{"id_ref": "lote-5", "tipo": "lote_masivo"}]})
    @patch("ecom.pedido_gestion_views.construir_resumen_lote", return_value={"sucursales": [
        {"cod_mov": 10, "presente": True}, {"cod_mov": 11, "presente": True},
        {"cod_mov": 12, "presente": False},
    ]})
    @patch("ecom.pedido_gestion_views.generar_pedido_pdf")
    def test_pdf_lote_solo_incluye_confirmados(self, generar, _resumen, _hub, _user, _base):
        sample = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=400)
        writer.write(sample)
        generar.return_value = (True, None, sample.getvalue())
        response = PedidosHubItemPDFAPIView().get(SimpleNamespace(session={}), "lote", 5)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(PdfReader(BytesIO(response.content)).pages), 2)
        self.assertEqual([call.args[1] for call in generar.call_args_list], [10, 11])

    def test_fecha_invertida_es_rechazada(self):
        with self.assertRaises(ValueError):
            filtrar_pedidos_hub(ITEMS, fecha_desde="2026-11-14", fecha_hasta="2026-11-13")
