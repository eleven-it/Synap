"""
Tests del export de lista de precios PDF (Fase P3).

Se mockean los accesos a MySQL (contar/obtener filas, precio, empresa) y el pool;
reportlab renderiza en memoria (sin archivos ni base real).
"""

from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from ecom.services import lista_precio_pdf as svc


def _fake_pool():
    class _Pool:
        @contextmanager
        def get_connection(self, _base):
            yield object()
    return _Pool()


def _patchers(filas, *, total=None, precio="121.00"):
    total = len(filas) if total is None else total
    return [
        patch.object(svc, "get_mysql_pool", return_value=_fake_pool()),
        patch.object(svc, "contar_articulos_catalogo", return_value=total),
        patch.object(svc, "obtener_filas_catalogo", return_value=filas),
        patch.object(svc, "calcular_precio_articulo_row", return_value=Decimal(precio)),
        patch.object(svc, "get_empresa_para_reporte", return_value={
            "razon_social": "ACME SA", "cuit_formateado": "30-11111111-2",
            "domicilio": "Calle 1", "logo_path": None,
        }),
    ]


def _fila(idart=1, nombre="Producto"):
    return {
        "IDArt": idart, "id_manual": f"M{idart}", "CodigoArticuloT": f"C{idart}",
        "NombreArticulo": nombre, "NombreRubro": "Rubro", "NombreSubRubro": "Sub",
        "promocion": "No", "alic_iva": "21",
    }


class TestFormatoMoneda(SimpleTestCase):
    def test_formato_es_ar(self):
        self.assertEqual(svc._fmt_money(Decimal("1234567.5")), "$1.234.567,50")
        self.assertEqual(svc._fmt_money(Decimal("0")), "$0,00")
        self.assertEqual(svc._fmt_money(Decimal("99.9")), "$99,90")


class TestExportPDF(SimpleTestCase):
    def _run(self, filas, **kw):
        ps = _patchers(filas, **kw)
        for p in ps:
            p.start()
        try:
            return svc.exportar_lista_precios_pdf(
                "emp1", filtros={}, lista_id=1, codigo_cliente=None,
                descuento_cliente=Decimal("0"), iva_incluido=True, id_deposito=1,
            )
        finally:
            for p in ps:
                p.stop()

    def test_happy_path_genera_pdf(self):
        ok, err, pdf = self._run([_fila(1), _fila(2, "Otro")])
        self.assertTrue(ok, err)
        self.assertIsNone(err)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_guardrail_volumen(self):
        # total supera LP_PDF_MAX_ITEMS (default 2500)
        ok, err, pdf = self._run([_fila(1)], total=3000)
        self.assertFalse(ok)
        self.assertEqual(err["tipo"], svc.ERROR_VOLUMEN)
        self.assertEqual(err["cantidad"], 3000)
        self.assertIsNone(pdf)

    def test_guardrail_tiempo(self):
        filas = [_fila(i) for i in range(60)]
        with patch.object(svc.time, "monotonic", side_effect=[0.0, 10_000.0]):
            ok, err, pdf = self._run(filas)
        self.assertFalse(ok)
        self.assertEqual(err["tipo"], svc.ERROR_TIEMPO)
        self.assertIsNone(pdf)
