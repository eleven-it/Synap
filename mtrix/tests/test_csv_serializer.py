"""Tests del serializer CSV MTRIX (contrato V.3.5)."""

from datetime import datetime
from pathlib import Path

from django.test import SimpleTestCase

from mtrix.services import crypto as crypto_mod
from mtrix.services.csv_serializer import (
    HEADERS,
    agregar_vd,
    cnpj_cliente_mtrix,
    formatear_representatividade,
    nombre_archivo,
    serialize,
)
from mtrix.services.crypto import decrypt_secret, encrypt_secret


CFG = {
    "cnpj_fornecedor": "30712345678",
    "cnpj_distribuidor": "20-11111111-2",
    "razon_social_fornecedor": "DISTRIBUIDORA TEST",
    "fecha_archivo": "20260812",
    "multiplicador_cantidad": 1,
    "multiplicador_precio": 1,
}


class CsvSerializerTests(SimpleTestCase):
    def test_headers_coinciden_con_inventario(self):
        self.assertEqual(
            HEADERS["CI"],
            "CNPJ_FORNECEDOR;CNPJ_DISTRIBUIDOR;CNPJ_CLIENTE;RAZAO_SOCIAL;ENDERECO;"
            "BAIRRO;CEP;CIDADE;ESTADO;NOME_RESPONSAVEL;TELEFONE;CNPJ_CLIENTE;ROTA;"
            "TIPO_LOJ;REPRESENTATIVIDADE",
        )
        self.assertEqual(
            HEADERS["PD"],
            "DT_ARQUIVO;CNPJ_DISTRIBUIDOR;CNPJ_FORNECEDOR;RAZAO_SOCIAL_FORNECEDOR;"
            "CODIGO_PRODUTO;TIPO_EMBALAGEM;EAN;TIPO_COD_BARRAS;DESCRICAO;DIVISAO;STATUS",
        )
        self.assertEqual(HEADERS["ES"], "DT_ESTOQUE;CNPJ_FORNECEDOR;CNPJ_DISTRIBUIDOR;EAN;QTDE_TOTAL")
        self.assertEqual(
            HEADERS["VD"],
            "CNPJ FORNECEDOR;CNPJ DISTRIBUIDOR;COD CLIENTE;DATA;NOTA_FISCAL;EAN;"
            "QTDE;PRECO;VENDEDOR;TIPO DE DOCUMENTO;CEP",
        )
        self.assertEqual(
            HEADERS["FV"],
            "CNPJ FORNECEDOR;CNPJ AGENTE DISTRIBUICAO;IDENTIFICACAO CLIENTE;"
            "CODIGO DO GERENTE;NOME DO GERENTE;CODIGO DO SUPERVISOR;NOME DO SUPERVISOR;"
            "CODIGO DO VENDEDOR;NOME DO VENDEDOR",
        )

    def test_nombre_archivo_sin_version(self):
        dt = datetime(2026, 8, 12, 15, 4, 5, 123000)
        self.assertEqual(nombre_archivo("CI", dt), "CI-INT12082026150405123.csv")
        self.assertNotIn("V19", nombre_archivo("VD", dt))

    def test_encoding_latin1(self):
        filename, data = serialize(
            "CI",
            [
                {
                    "CNPJ_CLIENTE": "20123456789",
                    "RAZAO_SOCIAL": "Ñandú S.A.",
                    "ENDERECO": "Calle 1",
                    "BAIRRO": "Centro",
                    "CEP": "1000",
                    "CIDADE": "CABA",
                    "ESTADO": "CABA",
                    "NOME_RESPONSAVEL": "NA",
                    "TELEFONE": "",
                    "ROTA": "RUTA",
                    "TIPO_LOJ": "Tienda",
                    "REPRESENTATIVIDADE": "1.5",
                }
            ],
            CFG,
            datetime(2026, 8, 12, 10, 0, 0),
        )
        texto = data.decode("latin-1")
        self.assertIn("Ñandú S.A.", texto)
        self.assertTrue(filename.endswith(".csv"))

    def test_consumidor_final_y_cuit_cero(self):
        self.assertEqual(cnpj_cliente_mtrix("20-1", "CONSUMIDOR FINAL"), "99999999999")
        self.assertEqual(cnpj_cliente_mtrix("0", "ACME"), "99999999999")
        self.assertEqual(cnpj_cliente_mtrix("0000", "ACME"), "99999999999")
        self.assertEqual(cnpj_cliente_mtrix("20-11111111-2", "ACME"), "20111111112")

    def test_nc_nd_tipo_n_cantidad_negativa(self):
        agrupados = agregar_vd(
            [
                {
                    "COD_CLIENTE": "20111",
                    "RAZAO_SOCIAL": "ACME",
                    "DATA": "20260812",
                    "NOTA_FISCAL": "100",
                    "EAN": "779123",
                    "QTDE": 4,
                    "PRECO": 10.5,
                    "VENDEDOR": "5",
                    "TIPO_COMP": "NCA",
                    "CEP": "1000",
                }
            ]
        )
        self.assertEqual(agrupados[0]["TIPO_DOC"], "N")
        self.assertEqual(agrupados[0]["QTDE"], "-4")

    def test_fa_tipo_n_cantidad_positiva(self):
        agrupados = agregar_vd(
            [
                {
                    "COD_CLIENTE": "20111",
                    "RAZAO_SOCIAL": "ACME",
                    "DATA": "20260812",
                    "NOTA_FISCAL": "101",
                    "EAN": "779123",
                    "QTDE": 2,
                    "PRECO": 8,
                    "VENDEDOR": "5",
                    "TIPO_COMP": "FA",
                    "CEP": "1000",
                }
            ]
        )
        self.assertEqual(agrupados[0]["TIPO_DOC"], "N")
        self.assertEqual(agrupados[0]["QTDE"], "2")

    def test_agrupacion_vd_suma_cantidad_y_precio(self):
        agrupados = agregar_vd(
            [
                {
                    "COD_CLIENTE": "20111",
                    "RAZAO_SOCIAL": "ACME",
                    "DATA": "20260812",
                    "NOTA_FISCAL": "50",
                    "EAN": "779",
                    "QTDE": 1,
                    "PRECO": 10,
                    "VENDEDOR": "1",
                    "TIPO_COMP": "FA",
                    "CEP": "0",
                },
                {
                    "COD_CLIENTE": "20111",
                    "RAZAO_SOCIAL": "ACME",
                    "DATA": "20260812",
                    "NOTA_FISCAL": "50",
                    "EAN": "779",
                    "QTDE": 3,
                    "PRECO": 5,
                    "VENDEDOR": "1",
                    "TIPO_COMP": "FA",
                    "CEP": "0",
                },
            ]
        )
        self.assertEqual(len(agrupados), 1)
        self.assertEqual(agrupados[0]["QTDE"], "4")
        self.assertEqual(agrupados[0]["PRECO"], "15.00")

    def test_representatividade_coma_decimal(self):
        self.assertEqual(formatear_representatividade("1.5"), "1,50")
        self.assertEqual(formatear_representatividade("0,25"), "0,25")

    def test_vd_csv_usa_tipo_n(self):
        _fn, data = serialize(
            "VD",
            [
                {
                    "COD_CLIENTE": "20111",
                    "RAZAO_SOCIAL": "ACME",
                    "DATA": "20260812",
                    "NOTA_FISCAL": "9",
                    "EAN": "1",
                    "QTDE": 1,
                    "PRECO": 2,
                    "VENDEDOR": "1",
                    "TIPO_COMP": "FB",
                    "CEP": "0",
                }
            ],
            CFG,
            datetime(2026, 8, 12, 11, 0, 0),
        )
        linea = data.decode("latin-1").split("\r\n")[1]
        self.assertIn(";N;", linea)

    def test_crypto_pepper_distinto_de_backup(self):
        src = Path(crypto_mod.__file__).read_text(encoding="utf-8")
        self.assertIn("synap-mtrix-sftp", src)
        self.assertNotIn("BACKUP_SFTP", src)
        cifrado = encrypt_secret("clave-secreta")
        self.assertNotEqual(cifrado, "clave-secreta")
        self.assertEqual(decrypt_secret(cifrado), "clave-secreta")
