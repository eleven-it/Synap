from io import BytesIO
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from pypdf import PdfReader

from stock.views import movimiento_pdf_view


def generar_pdf_prueba():
    request = RequestFactory().get("/stock/movimientos/77/pdf/")
    request.session = {"user": {"base_empresa": "administranet2"}}
    filas = [
        {"CodigoArticulo": f"ART-{i:03d}", "Descripcion": f"Producto {i:03d}",
         "Entrada": 0, "Salida": 1, "saldo": 9,
         "nombre_deposito": "Principal", "nro_pedi": "0001-00000001"}
        for i in range(90)
    ]
    with patch("core.services.administranet_stock.obtener_movimiento", return_value={
        "nro_comprobante": "0001-00000077", "fecha": "2026-10-24",
        "motivo_movimiento": "Transferencia", "deposito_origen": 1,
        "deposito_destino": 2, "detalle": "Traslado de prueba",
    }), patch("core.services.administranet_stock.obtener_renglones_movimiento",
              return_value=filas), patch(
        "core.services.administranet_stock.get_nombre_deposito",
        side_effect=lambda _base, deposito: f"Depósito {deposito}"), patch(
        "core.report_pdf.get_empresa_para_reporte", return_value={
            "razon_social": "Best Sox SA", "domicilio": "Domicilio de prueba",
            "cuit_formateado": "00-00000000-0", "logo_path": None,
        }):
        return movimiento_pdf_view.__wrapped__(request, 77).content


class PdfMovimientoTests(SimpleTestCase):
    def test_todas_las_lineas_aparecen_en_pdf_multipagina(self):
        pdf = generar_pdf_prueba()
        self.assertTrue(pdf.startswith(b"%PDF"))
        lector = PdfReader(BytesIO(pdf))
        self.assertGreaterEqual(len(lector.pages), 2)
        texto = "\n".join(pagina.extract_text() for pagina in lector.pages)
        self.assertIn("ART-000", texto)
        self.assertIn("ART-089", texto)
        self.assertIn("Pedido interno: 0001-00000001", texto)
