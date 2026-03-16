# Tests para scanner de código de barras mobile y fix dropdown (plan scanner_barras_mobile_stock).
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.http import HttpRequest


class TestApiArticulosPorCodigo(TestCase):
    """API GET articulos-por-codigo: codigo vacío o inexistente → articulos []; codigo existente → 1 artículo.
    Se prueba la vista directamente con request mockeado para no depender de MySQL/permisos en test."""

    def _request_get(self, codigo, id_deposito=None):
        request = HttpRequest()
        request.method = 'GET'
        request.GET = {'codigo': codigo}
        if id_deposito is not None:
            request.GET = request.GET.copy()
            request.GET['id_deposito'] = str(id_deposito)
        request.session = {'user': {'base_empresa': 'test_db', 'id_usuario': 1, 'id_puesto': 1}}
        request.user = MagicMock()
        request.user.is_authenticated = True
        request.user.tiene_permiso = lambda c: True
        return request

    def _json(self, response):
        return json.loads(response.content.decode('utf-8'))

    def test_codigo_vacio_retorna_articulos_vacio(self):
        from stock.api_views import api_ingreso_articulos_por_codigo
        request = self._request_get('')
        response = api_ingreso_articulos_por_codigo(request)
        self.assertEqual(response.status_code, 200)
        data = self._json(response)
        self.assertIn('articulos', data)
        self.assertEqual(data['articulos'], [])

    @patch('stock.api_views.svc.buscar_articulo_por_codigo_exacto')
    def test_codigo_no_existe_retorna_articulos_vacio(self, mock_buscar):
        mock_buscar.return_value = None
        from stock.api_views import api_ingreso_articulos_por_codigo
        request = self._request_get('CODIGO_INEXISTENTE')
        response = api_ingreso_articulos_por_codigo(request)
        self.assertEqual(response.status_code, 200)
        data = self._json(response)
        self.assertEqual(data['articulos'], [])

    @patch('stock.api_views.svc.buscar_articulo_por_codigo_exacto')
    def test_codigo_existe_retorna_un_articulo(self, mock_buscar):
        mock_buscar.return_value = {
            'IDArt': 1,
            'CodigoArticulo': 'ART001',
            'Descripcion': 'Artículo de prueba',
            'id_manual': 'MANUAL01',
        }
        from stock.api_views import api_ingreso_articulos_por_codigo
        request = self._request_get('ART001')
        response = api_ingreso_articulos_por_codigo(request)
        self.assertEqual(response.status_code, 200)
        data = self._json(response)
        self.assertIn('articulos', data)
        self.assertEqual(len(data['articulos']), 1)
        self.assertEqual(data['articulos'][0]['CodigoArticulo'], 'ART001')


class TestTemplateScanner(TestCase):
    """El template de ingreso movimiento incluye contenedor del scanner y CDN html5-qrcode."""

    def test_template_contiene_scanner_container(self):
        from django.template.loader import get_template
        template = get_template('stock/alta_movimiento.html')
        # Contenido crudo del template incluye el id del contenedor del scanner
        with open(template.origin.name, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('scanner-container', content, 'El template debe contener el id scanner-container para el modal del scanner.')

    def test_template_contiene_html5_qrcode_cdn(self):
        from django.template.loader import get_template
        template = get_template('stock/alta_movimiento.html')
        with open(template.origin.name, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('html5-qrcode', content, 'El template debe referenciar la librería html5-qrcode (CDN).')
        self.assertIn('cdn.jsdelivr.net', content, 'El template debe incluir el CDN jsDelivr para html5-qrcode.')
