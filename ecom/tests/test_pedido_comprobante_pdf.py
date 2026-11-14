"""El PDF PED conserva los datos y totales del comprobante."""

from io import BytesIO
from unittest import TestCase
from unittest.mock import patch

from pypdf import PdfReader

from ecom.services.pedido_comprobante_pdf import _render_pdf


class PedidoComprobantePDFTests(TestCase):
    @patch("ecom.services.pedido_comprobante_pdf.get_empresa_para_reporte")
    def test_pdf_incluye_cabecera_cliente_renglones_y_totales(self, get_empresa):
        get_empresa.return_value = {
            "razon_social": "Empresa de prueba", "domicilio": "Calle 123",
            "cuit_formateado": "30-12345678-9", "logo_path": None,
        }
        cab = {
            "nro_comprobante": "0008-00001124", "fecha": "13/11/2026",
            "nombre_cliente": "Cliente de prueba", "cuit_cliente": "30-98765432-1",
            "subtotal_desc": 100, "iva_1": 21, "total": 121,
            "observaciones": "Entregar por la mañana",
        }
        renglones = [{
            "CodigoArticulo": "289", "Descripcion": "Artículo de prueba",
            "Salida": 2, "PrecioNetoxU": 50, "PrecioNetoxR": 100,
            "PrecioIVAxR": 21, "TipoIVA": 21,
        }]

        pdf = _render_pdf(cab, renglones, base_empresa="prueba")
        contenido = " ".join(p.extract_text() or "" for p in PdfReader(BytesIO(pdf)).pages)

        for esperado in (
            "0008-00001124", "Empresa de prueba", "Cliente de prueba",
            "Artículo de prueba", "$121,00", "Entregar por la mañana",
        ):
            self.assertIn(esperado, contenido)
