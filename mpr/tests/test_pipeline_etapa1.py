"""Tests unitarios — MPR Etapa 1: Topología de Etapas y Modelo de Estados.

Suite pura: no requiere base de datos MySQL. Usa SimpleTestCase y mocks.
Comando: docker exec Synap_app python manage.py test mpr.tests.test_pipeline_etapa1
"""
from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase

from mpr.services import (
    TIPO_MPR_2DA_SELECCION,
    TIPO_MPR_PLANCHADO,
    TIPO_MPR_PRODUCCION,
    TIPO_MPR_SCRAP,
    TIPO_MPR_SEMI_ELABORADO,
    TIPO_MPR_TERMINADO,
    TIPOS_MPR_OPP,
    actualizar_deposito_tipo_mpr,
    get_deposito_planchado_mpr,
)
from mpr.pipeline import (
    ESTADO_VIRTUAL_ENVIADO,
    ESTADO_VIRTUAL_PENDIENTE,
    ORDEN_ETAPAS_MPR,
    TRANSICIONES_LEGALES,
    TIPOS_QUE_SUMAN_STOCK,
    es_transicion_legal,
    validar_transicion,
)
from mpr.views import TIPOS_MPR_CON_ETIQUETA


class TestConstantesPlanchado(SimpleTestCase):
    """REQ-001, REQ-003, REQ-004, REQ-007."""

    def test_tipo_mpr_planchado_valor(self):
        """REQ-001: TIPO_MPR_PLANCHADO debe ser el string 'Planchado'."""
        self.assertEqual(TIPO_MPR_PLANCHADO, "Planchado")
        self.assertIsInstance(TIPO_MPR_PLANCHADO, str)

    def test_planchado_no_en_tipos_mpr_opp(self):
        """REQ-007: Planchado no debe estar en TIPOS_MPR_OPP (destinos válidos de OPP)."""
        self.assertNotIn(TIPO_MPR_PLANCHADO, TIPOS_MPR_OPP)
        # Los destinos válidos de OPP son SemiElaborado, Scrap y 2daSeleccion
        self.assertIn(TIPO_MPR_SEMI_ELABORADO, TIPOS_MPR_OPP)
        self.assertIn(TIPO_MPR_SCRAP, TIPOS_MPR_OPP)
        self.assertIn(TIPO_MPR_2DA_SELECCION, TIPOS_MPR_OPP)

    def test_planchado_en_validos_actualizar_deposito(self):
        """REQ-003: actualizar_deposito_tipo_mpr debe aceptar Planchado (whitebox: no retorna error de tipo)."""
        with patch("mpr.services.get_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (0,)
            mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn.return_value)
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.return_value.cursor.return_value = mock_cursor
            with patch("mpr.services._nombre_tabla", return_value="deposito"):
                ok, error = actualizar_deposito_tipo_mpr("empresa_test", 1, TIPO_MPR_PLANCHADO)
            self.assertIsNone(error, f"No debe haber error de tipo inválido, obtenido: {error}")

    def test_planchado_en_tipos_mpr_con_etiqueta(self):
        """REQ-004: TIPOS_MPR_CON_ETIQUETA debe incluir entrada con TIPO_MPR_PLANCHADO."""
        valores = [v for v, _ in TIPOS_MPR_CON_ETIQUETA]
        self.assertIn(TIPO_MPR_PLANCHADO, valores)

    def test_etiqueta_planchado_correcta(self):
        """REQ-004: La etiqueta asociada a TIPO_MPR_PLANCHADO debe ser 'Planchado'."""
        etiquetas = {v: label for v, label in TIPOS_MPR_CON_ETIQUETA}
        self.assertEqual(etiquetas.get(TIPO_MPR_PLANCHADO), "Planchado")


class TestGetDepositoPlanchado(SimpleTestCase):
    """REQ-002: getter get_deposito_planchado_mpr."""

    def test_base_vacia_retorna_none(self):
        """Sin base_empresa retorna None sin consultar MySQL."""
        self.assertIsNone(get_deposito_planchado_mpr(""))

    def test_base_none_retorna_none(self):
        """Con None retorna None sin consultar MySQL."""
        self.assertIsNone(get_deposito_planchado_mpr(None))

    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services._nombre_tabla", return_value="deposito")
    def test_retorna_cod_deposito_cuando_existe(self, _mock_tabla, mock_cursor_ctx):
        """Con depósito configurado retorna CodDeposito como int."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"CodDeposito": 7}
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        resultado = get_deposito_planchado_mpr("empresa_test")
        self.assertEqual(resultado, 7)

    @patch("mpr.services.mysql_cursor")
    @patch("mpr.services._nombre_tabla", return_value="deposito")
    def test_retorna_none_cuando_no_existe(self, _mock_tabla, mock_cursor_ctx):
        """Sin depósito configurado retorna None."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor_ctx.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor_ctx.return_value.__exit__ = MagicMock(return_value=False)
        resultado = get_deposito_planchado_mpr("empresa_test")
        self.assertIsNone(resultado)


class TestEsTransicionLegal(SimpleTestCase):
    """REQ-010 a REQ-015: transiciones legales e ilegales."""

    # Transiciones legales
    def test_enviado_a_produccion(self):
        """Transición (b): Enviado → Produccion legal."""
        self.assertTrue(es_transicion_legal(ESTADO_VIRTUAL_ENVIADO, TIPO_MPR_PRODUCCION))

    def test_produccion_a_semi_elaborado(self):
        """Etapa 10: Produccion → SemiElaborado legal (clasificación directa)."""
        self.assertTrue(es_transicion_legal(TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO))

    def test_produccion_a_2da_seleccion(self):
        """Etapa 10: Produccion → 2daSeleccion legal (clasificación directa)."""
        self.assertTrue(es_transicion_legal(TIPO_MPR_PRODUCCION, TIPO_MPR_2DA_SELECCION))

    def test_produccion_a_scrap(self):
        """Transición reprobatoria: Produccion → Scrap legal."""
        self.assertTrue(es_transicion_legal(TIPO_MPR_PRODUCCION, TIPO_MPR_SCRAP))

    def test_produccion_a_planchado_ilegal(self):
        """Etapa 10: Planchado deja de ser etapa; Produccion → Planchado ilegal."""
        self.assertFalse(es_transicion_legal(TIPO_MPR_PRODUCCION, TIPO_MPR_PLANCHADO))

    def test_planchado_no_es_origen_legal(self):
        """Etapa 10: Planchado no tiene destinos (no es etapa con stock)."""
        self.assertFalse(es_transicion_legal(TIPO_MPR_PLANCHADO, TIPO_MPR_2DA_SELECCION))
        self.assertFalse(es_transicion_legal(TIPO_MPR_PLANCHADO, TIPO_MPR_SEMI_ELABORADO))

    def test_2da_seleccion_a_terminado(self):
        """Transición (e): 2daSeleccion → Terminado legal."""
        self.assertTrue(es_transicion_legal(TIPO_MPR_2DA_SELECCION, TIPO_MPR_TERMINADO))

    def test_semi_elaborado_a_terminado(self):
        """Transición (e): SemiElaborado → Terminado legal."""
        self.assertTrue(es_transicion_legal(TIPO_MPR_SEMI_ELABORADO, TIPO_MPR_TERMINADO))

    # Transiciones ilegales
    def test_produccion_a_terminado_ilegal(self):
        """REQ-015: Produccion → Terminado no está permitida."""
        self.assertFalse(es_transicion_legal(TIPO_MPR_PRODUCCION, TIPO_MPR_TERMINADO))

    def test_2da_seleccion_a_produccion_ilegal(self):
        """REQ-015: 2daSeleccion → Produccion (reversa) no está permitida."""
        self.assertFalse(es_transicion_legal(TIPO_MPR_2DA_SELECCION, TIPO_MPR_PRODUCCION))

    def test_scrap_a_planchado_ilegal(self):
        """REQ-015: Scrap → Planchado no está permitida (terminal)."""
        self.assertFalse(es_transicion_legal(TIPO_MPR_SCRAP, TIPO_MPR_PLANCHADO))

    def test_terminado_a_cualquiera_ilegal(self):
        """REQ-015: Terminado es terminal, ninguna transición está permitida."""
        for destino in [TIPO_MPR_PRODUCCION, TIPO_MPR_PLANCHADO, TIPO_MPR_2DA_SELECCION,
                        TIPO_MPR_SEMI_ELABORADO, TIPO_MPR_SCRAP, ESTADO_VIRTUAL_ENVIADO]:
            with self.subTest(destino=destino):
                self.assertFalse(es_transicion_legal(TIPO_MPR_TERMINADO, destino))

    def test_origen_desconocido_es_ilegal(self):
        """Origen no definido en TRANSICIONES_LEGALES retorna False."""
        self.assertFalse(es_transicion_legal("EtapaInventada", TIPO_MPR_PRODUCCION))


class TestValidarTransicion(SimpleTestCase):
    """REQ-015, REQ-016: validar_transicion."""

    def test_ok_con_saldo_suficiente(self):
        """REQ-016: transición válida con saldo >= cantidad retorna (True, None)."""
        ok, error = validar_transicion(TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO, 10, 20)
        self.assertTrue(ok)
        self.assertIsNone(error)

    def test_ok_con_saldo_exacto(self):
        """REQ-016: cantidad == saldo disponible es válida."""
        ok, error = validar_transicion(TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO, 15, 15)
        self.assertTrue(ok)
        self.assertIsNone(error)

    def test_error_saldo_insuficiente(self):
        """REQ-016: cantidad > saldo retorna error con indicación del disponible."""
        ok, error = validar_transicion(TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO, 25, 15)
        self.assertFalse(ok)
        self.assertIsNotNone(error)
        self.assertIn("15", error, "El mensaje debe indicar el saldo disponible")
        self.assertIn("25", error, "El mensaje debe indicar la cantidad solicitada")

    def test_error_cantidad_cero(self):
        """REQ-016: cantidad == 0 retorna error."""
        ok, error = validar_transicion(TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO, 0, 100)
        self.assertFalse(ok)
        self.assertIsNotNone(error)

    def test_error_cantidad_negativa(self):
        """REQ-016: cantidad negativa retorna error."""
        ok, error = validar_transicion(TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO, -5, 100)
        self.assertFalse(ok)
        self.assertIsNotNone(error)

    def test_error_transicion_ilegal(self):
        """REQ-015: transición ilegal retorna error independientemente del saldo."""
        ok, error = validar_transicion(TIPO_MPR_PRODUCCION, TIPO_MPR_TERMINADO, 5, 100)
        self.assertFalse(ok)
        self.assertIsNotNone(error)
        self.assertIn("Produccion", error)
        self.assertIn("Terminado", error)

    def test_error_scrap_terminal(self):
        """REQ-015: desde Scrap (terminal) siempre es ilegal."""
        ok, error = validar_transicion(TIPO_MPR_SCRAP, TIPO_MPR_PLANCHADO, 3, 50)
        self.assertFalse(ok)
        self.assertIsNotNone(error)


class TestOrdenCanonicoYSumaStock(SimpleTestCase):
    """REQ-005, REQ-018: orden canónico y conjunto de suma stock."""

    def test_orden_etapas_tiene_7_elementos(self):
        """REQ-005 (Etapa 10): ORDEN_ETAPAS_MPR tiene 7 etapas (sin Planchado)."""
        self.assertEqual(len(ORDEN_ETAPAS_MPR), 7)

    def test_orden_empieza_con_virtuales(self):
        """REQ-005: Las primeras 2 posiciones son los estados virtuales."""
        self.assertEqual(ORDEN_ETAPAS_MPR[0], ESTADO_VIRTUAL_PENDIENTE)
        self.assertEqual(ORDEN_ETAPAS_MPR[1], ESTADO_VIRTUAL_ENVIADO)

    def test_scrap_en_orden_etapas(self):
        """REQ-005: Scrap debe estar en ORDEN_ETAPAS_MPR."""
        self.assertIn(TIPO_MPR_SCRAP, ORDEN_ETAPAS_MPR)

    def test_planchado_no_en_orden_etapas(self):
        """REQ-005 (Etapa 10): Planchado NO es etapa del pipeline."""
        self.assertNotIn(TIPO_MPR_PLANCHADO, ORDEN_ETAPAS_MPR)

    def test_scrap_no_en_tipos_que_suman_stock(self):
        """REQ-018: Scrap (Desperdicio) NO debe sumar al Total."""
        self.assertNotIn(TIPO_MPR_SCRAP, TIPOS_QUE_SUMAN_STOCK)

    def test_planchado_no_en_tipos_que_suman_stock(self):
        """REQ-018 (Etapa 10): Planchado ya no es etapa; no suma al Total."""
        self.assertNotIn(TIPO_MPR_PLANCHADO, TIPOS_QUE_SUMAN_STOCK)

    def test_2da_seleccion_en_tipos_que_suman_stock(self):
        """REQ-018: 2da Selección suma al Total."""
        self.assertIn(TIPO_MPR_2DA_SELECCION, TIPOS_QUE_SUMAN_STOCK)

    def test_produccion_en_tipos_que_suman_stock(self):
        """REQ-018: Produccion sí debe sumar al Total."""
        self.assertIn(TIPO_MPR_PRODUCCION, TIPOS_QUE_SUMAN_STOCK)

    def test_terminado_en_tipos_que_suman_stock(self):
        """REQ-018: Terminado sí debe sumar al Total."""
        self.assertIn(TIPO_MPR_TERMINADO, TIPOS_QUE_SUMAN_STOCK)

    def test_tipos_que_suman_stock_son_frozenset(self):
        """TIPOS_QUE_SUMAN_STOCK debe ser frozenset (inmutable)."""
        self.assertIsInstance(TIPOS_QUE_SUMAN_STOCK, frozenset)

    def test_transiciones_legales_es_dict(self):
        """TRANSICIONES_LEGALES debe ser dict con valores frozenset."""
        self.assertIsInstance(TRANSICIONES_LEGALES, dict)
        for _, destinos in TRANSICIONES_LEGALES.items():
            self.assertIsInstance(destinos, frozenset)
