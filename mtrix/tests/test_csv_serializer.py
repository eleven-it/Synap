"""Tests del serializer CSV MTRIX (contrato V.3.5)."""

from datetime import datetime
from pathlib import Path

from django.test import SimpleTestCase

from mtrix.services import crypto as crypto_mod
from mtrix.services.csv_serializer import (
    HEADERS,
    agregar_fv,
    agregar_vd,
    cep_mtrix,
    cnpj_cliente_mtrix,
    ean_mtrix,
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

    def test_ci_acepta_alias_ciudad_vb6(self):
        _fn, data = serialize(
            "CI",
            [
                {
                    "CNPJ_CLIENTE": "20123456789",
                    "RAZAO_SOCIAL": "ACME",
                    "ENDERECO": "Calle 1",
                    "BAIRRO": "Centro",
                    "CEP": "1000",
                    "CIUDAD": "Rosario",
                    "ESTADO": "SF",
                    "NOME_RESPONSAVEL": "NA",
                    "TELEFONE": "",
                    "ROTA": "RUTA",
                    "TIPO_LOJ": "Tienda",
                    "REPRESENTATIVIDADE": "0,10",
                }
            ],
            CFG,
            datetime(2026, 8, 12, 10, 0, 0),
        )
        self.assertIn("Rosario", data.decode("latin-1"))

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

    def test_vd_agrupa_por_cuit_crudo_no_por_cnpj_pantalla(self):
        agrupados = agregar_vd(
            [
                {
                    "COD_CLIENTE": "0",
                    "RAZAO_SOCIAL": "CONSUMIDOR FINAL",
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
                    "RAZAO_SOCIAL": "CONSUMIDOR FINAL",
                    "DATA": "20260812",
                    "NOTA_FISCAL": "50",
                    "EAN": "779",
                    "QTDE": 2,
                    "PRECO": 5,
                    "VENDEDOR": "1",
                    "TIPO_COMP": "FA",
                    "CEP": "0",
                },
            ]
        )
        self.assertEqual(len(agrupados), 2)
        self.assertEqual({row["COD_CLIENTE"] for row in agrupados}, {"99999999999"})

    def test_fv_escribe_cuit_crudo_sin_999(self):
        _fn, data = serialize(
            "FV",
            [
                {
                    "CNPJ_CLIENTE": "0",
                    "COD_GERENTE": "1",
                    "NOME_GERENTE": "GERENTE GENERAL",
                    "COD_SUPERVISOR": "1",
                    "NOME_SUPERVISOR": "SUPERVISOR",
                    "COD_VENDEDOR": "5",
                    "NOME_VENDEDOR": "JUAN",
                }
            ],
            CFG,
            datetime(2026, 8, 12, 11, 0, 0),
        )
        texto = data.decode("latin-1")
        self.assertIn(";0;", texto)
        self.assertNotIn("99999999999", texto)

    def test_fv_deduplica_mismo_cuit_distinto_cliente_y_vendedor(self):
        filas = [
            {
                "CNPJ_CLIENTE": "20111111112",
                "COD_CLIENTE": "100",
                "COD_VENDEDOR": "10",
                "NOME_VENDEDOR": "ZETA",
            },
            {
                "CNPJ_CLIENTE": "20111111112",
                "COD_CLIENTE": "200",
                "COD_VENDEDOR": "3",
                "NOME_VENDEDOR": "ANA",
            },
            {
                "CNPJ_CLIENTE": "20111111112",
                "COD_CLIENTE": "300",
                "COD_VENDEDOR": "5",
                "NOME_VENDEDOR": "BOB",
            },
        ]
        agrupados = agregar_fv(filas)
        self.assertEqual(len(agrupados), 1)
        self.assertEqual(agrupados[0]["COD_VENDEDOR"], "3")
        self.assertEqual(agrupados[0]["NOME_VENDEDOR"], "ANA")
        _fn, data = serialize("FV", filas, CFG, datetime(2026, 8, 12, 11, 0, 0))
        lineas = [ln for ln in data.decode("latin-1").strip().split("\r\n") if ln]
        self.assertEqual(len(lineas), 2)
        self.assertIn(";3;ANA", lineas[1])

    def test_fv_dos_cuits_distintos_dos_lineas(self):
        filas = [
            {"CNPJ_CLIENTE": "20111111112", "COD_VENDEDOR": "1", "NOME_VENDEDOR": "A"},
            {"CNPJ_CLIENTE": "20999999999", "COD_VENDEDOR": "2", "NOME_VENDEDOR": "B"},
        ]
        agrupados = agregar_fv(filas)
        self.assertEqual(len(agrupados), 2)
        self.assertEqual([r["CNPJ_CLIENTE"] for r in agrupados], ["20111111112", "20999999999"])
        _fn, data = serialize("FV", filas, CFG, datetime(2026, 8, 12, 11, 0, 0))
        lineas = [ln for ln in data.decode("latin-1").strip().split("\r\n") if ln]
        self.assertEqual(len(lineas), 3)

    def test_fv_orden_estable_por_primera_aparicion_cuit(self):
        filas = [
            {"CNPJ_CLIENTE": "30111111111", "COD_VENDEDOR": "1", "NOME_VENDEDOR": "A"},
            {"CNPJ_CLIENTE": "20111111112", "COD_VENDEDOR": "2", "NOME_VENDEDOR": "B"},
            {"CNPJ_CLIENTE": "30111111111", "COD_VENDEDOR": "9", "NOME_VENDEDOR": "C"},
        ]
        agrupados = agregar_fv(filas)
        self.assertEqual([r["CNPJ_CLIENTE"] for r in agrupados], ["30111111111", "20111111112"])

    def test_fv_empate_vendedor_por_nombre(self):
        filas = [
            {"CNPJ_CLIENTE": "20111111112", "COD_VENDEDOR": "5", "NOME_VENDEDOR": "ZULIA"},
            {"CNPJ_CLIENTE": "20111111112", "COD_VENDEDOR": "5", "NOME_VENDEDOR": "ANA"},
        ]
        agrupados = agregar_fv(filas)
        self.assertEqual(len(agrupados), 1)
        self.assertEqual(agrupados[0]["NOME_VENDEDOR"], "ANA")

    def test_cep_incompleto_es_9400(self):
        self.assertEqual(cep_mtrix("0"), "9400")
        self.assertEqual(cep_mtrix(""), "9400")
        self.assertEqual(cep_mtrix("NA"), "9400")
        self.assertEqual(cep_mtrix("123"), "9400")
        self.assertEqual(cep_mtrix("0000"), "9400")
        self.assertEqual(cep_mtrix("9405"), "9405")
        _fn, data = serialize(
            "CI",
            [
                {
                    "CNPJ_CLIENTE": "20111",
                    "RAZAO_SOCIAL": "ACME",
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
            ],
            CFG,
            datetime(2026, 8, 12, 11, 0, 0),
        )
        self.assertIn(";9400;NA;NA;", data.decode("latin-1"))

    def test_ean_cero_usa_codigo_interno(self):
        self.assertEqual(ean_mtrix("0", "168114"), "168114")
        self.assertIsNone(ean_mtrix("0", "", None))
        _fn, data = serialize(
            "ES",
            [{"EAN": "0", "CODIGO_INTERNO": "168114", "QTDE_TOTAL": 6}],
            CFG,
            datetime(2026, 8, 12, 11, 0, 0),
        )
        self.assertIn(";168114;6", data.decode("latin-1"))
        self.assertNotIn(";0;6", data.decode("latin-1"))

    def test_ean_cero_sin_identificador_se_omite(self):
        _fn, data = serialize(
            "ES",
            [{"EAN": "0", "QTDE_TOTAL": 20}],
            CFG,
            datetime(2026, 8, 12, 11, 0, 0),
        )
        self.assertEqual(len(data.decode("latin-1").strip().split("\r\n")), 1)

    def test_pd_codigo_vacio_es_na(self):
        _fn, data = serialize(
            "PD",
            [
                {
                    "CODIGO_PRODUTO": "",
                    "DESCRICAO": "ART",
                    "DIVISAO_MARCA": "-Ninguno-",
                    "DIVISAO_RUBRO": "RUBRO",
                    "EAN": "1",
                    "TIPO_EMBALAGEM": "0",
                    "TIPO_COD_BARRAS": "1",
                    "DISCONTINUO": "No",
                }
            ],
            CFG,
            datetime(2026, 8, 12, 11, 0, 0),
        )
        linea = data.decode("latin-1").split("\r\n")[1]
        self.assertIn(";NA;", linea)
        self.assertIn(";-Ninguno-;", linea)

    def test_crypto_pepper_distinto_de_backup(self):
        src = Path(crypto_mod.__file__).read_text(encoding="utf-8")
        self.assertIn("synap-mtrix-sftp", src)
        self.assertNotIn("BACKUP_SFTP", src)
        cifrado = encrypt_secret("clave-secreta")
        self.assertNotEqual(cifrado, "clave-secreta")
        self.assertEqual(decrypt_secret(cifrado), "clave-secreta")
