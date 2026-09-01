"""Preview formatea para pantalla; el CSV conserva V.3.5."""

from datetime import datetime

from django.test import SimpleTestCase

from mtrix.services.csv_serializer import serialize
from mtrix.services.preview_formatter import format_row

CFG = {
    "cnpj_fornecedor": "30712345678",
    "cnpj_distribuidor": "20111111112",
    "fecha_archivo": "20230121",
    "multiplicador_cantidad": 1,
    "multiplicador_precio": 1,
}


class PreviewFormatterTests(SimpleTestCase):
    def test_fecha_preview_ddmmyyyy_csv_yyyymmdd(self):
        row = {
            "COD_CLIENTE": "20111",
            "RAZAO_SOCIAL": "ACME",
            "DATA": "20230121",
            "NOTA_FISCAL": "10",
            "EAN": "779",
            "QTDE": 1,
            "PRECO": 2,
            "VENDEDOR": "1",
            "TIPO_COMP": "FA",
            "CEP": "1000",
        }
        preview = format_row("VD", row)
        self.assertEqual(preview["DATA"], "21/01/2023")
        _fn, data = serialize("VD", [row], CFG, datetime(2023, 1, 21, 8, 0, 0))
        self.assertIn("20230121", data.decode("latin-1"))
        self.assertNotIn("21/01/2023", data.decode("latin-1"))

    def test_mismas_claves_de_negocio_ci(self):
        row = {
            "CNPJ_CLIENTE": "0",
            "RAZAO_SOCIAL": "CONSUMIDOR FINAL",
            "ENDERECO": "NA",
            "BAIRRO": "NA",
            "CEP": "0",
            "CIDADE": "NA",
            "ESTADO": "NA",
            "NOME_RESPONSAVEL": "NA",
            "TELEFONE": "",
            "ROTA": "RUTA",
            "TIPO_LOJ": "Tienda",
            "REPRESENTATIVIDADE": "0,00",
        }
        preview = format_row("CI", row)
        self.assertEqual(preview["CNPJ_CLIENTE"], "99999999999")
        self.assertEqual(preview["CEP"], "9400")
        _fn, data = serialize("CI", [row], CFG, datetime(2026, 8, 12, 9, 0, 0))
        self.assertIn("99999999999", data.decode("latin-1"))
        self.assertIn(";9400;", data.decode("latin-1"))

    def test_cep_vd_incompleto_es_9400(self):
        row = {
            "COD_CLIENTE": "20111",
            "RAZAO_SOCIAL": "ACME",
            "DATA": "20230121",
            "NOTA_FISCAL": "10",
            "EAN": "7798130180152",
            "QTDE": 1,
            "PRECO": 2,
            "VENDEDOR": "1",
            "TIPO_COMP": "FA",
            "CEP": "0",
        }
        preview = format_row("VD", row)
        self.assertEqual(preview["CEP"], "9400")

    def test_fv_jerarquia_plana_en_preview(self):
        preview = format_row("FV", {"CNPJ_CLIENTE": "20111", "RAZAO_SOCIAL": "ACME"})
        self.assertEqual(preview["COD_GERENTE"], "1")
        self.assertEqual(preview["NOME_GERENTE"], "GERENTE GENERAL")
        self.assertEqual(preview["COD_SUPERVISOR"], "1")
        self.assertEqual(preview["NOME_SUPERVISOR"], "SUPERVISOR")
