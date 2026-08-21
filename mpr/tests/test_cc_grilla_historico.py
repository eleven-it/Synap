"""Tests de grilla CC consolidada: orden, saldo entero e histórico visible."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from mpr.services_cc_consolidado import (
    _enteros_docenas_pares,
    construir_bloques_cc_articulo,
)

EMPRESA = "EmpresaTestCcGrilla"
FECHA = date(2026, 8, 11)


class EnterosDocenasParesTest(SimpleTestCase):
    def test_pares_completos_sin_decimal(self):
        self.assertEqual(_enteros_docenas_pares(24), (24, 2, 0))
        self.assertEqual(_enteros_docenas_pares(1188), (1188, 99, 0))
        self.assertEqual(_enteros_docenas_pares(13), (13, 1, 1))
        self.assertEqual(_enteros_docenas_pares(Decimal("24.0")), (24, 2, 0))


class ConstruirBloquesCcHistoricoTest(SimpleTestCase):
    def _parches(self):
        return (
            patch(
                "mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno",
                return_value={
                    (0, 10, 5, 1): {
                        "cantidad": Decimal("100"),
                        "operario_nombre": "García",
                        "turno_nombre": "Tarde",
                    }
                },
            ),
            patch(
                "mpr.services_cc_consolidado._pivot_saldo_produccion",
                return_value={
                    10: {"Produccion": 120.0},
                    99: {"Produccion": 48.0},
                },
            ),
            patch(
                "mpr.repositories.transicion_lote.semi_agregado_por_articulo_fecha",
                return_value={10: Decimal("96")},
            ),
            patch(
                "mpr.repositories.transicion_lote.desglose_cc_confirmado_por_celda_fecha",
                return_value={
                    (10, 5, 1): {
                        "semi": Decimal("96"),
                        "segunda": Decimal("12"),
                        "scrap": Decimal("0"),
                        "operario_nombre": "García",
                    }
                },
            ),
            patch(
                "mpr.repositories.transicion_lote.clasificado_segunda_scrap_por_celda_fecha",
                return_value={(10, 5, 1): Decimal("12")},
            ),
            patch(
                "mpr.repositories.clasificacion_borrador.tiene_borrador_cc_consolidado",
                return_value=False,
            ),
            patch(
                "mpr.repositories.clasificacion_borrador.listar_lineas_borrador_cc_consolidado",
                return_value=[],
            ),
            patch(
                "mpr.repositories.clasificacion_borrador.tiene_borrador",
                return_value=False,
            ),
            patch(
                "mpr.services._fetch_descripciones_articulo",
                return_value={
                    10: ("3765", "Puma con operario"),
                    99: ("883765", "Huérfano saldo"),
                },
            ),
            patch(
                "mpr.repositories.turno_roster.listar_turnos_dict",
                return_value=[{"id": 1, "nombre": "Tarde"}],
            ),
        )

    def test_operarios_primero_saldo_entero_e_historico_visible(self):
        parches = self._parches()
        for p in parches:
            p.start()
        try:
            resultado = construir_bloques_cc_articulo(
                EMPRESA, FECHA, solo_pendiente=False
            )
        finally:
            for p in reversed(parches):
                p.stop()

        bloques = resultado["bloques"]
        self.assertEqual(len(bloques), 2)
        primero, segundo = bloques
        self.assertTrue(primero["tiene_operarios"])
        self.assertEqual(primero["filas"][0]["operario_nombre"], "García")
        self.assertEqual(primero["saldo_produccion"], 120)
        self.assertEqual(primero["saldo_produccion_docenas"], 10)
        self.assertEqual(primero["saldo_produccion_pares"], 0)
        self.assertEqual(primero["semi_mostrar"], 96)
        self.assertEqual(primero["semi_mostrar_docenas"], 8)
        self.assertEqual(primero["semi_mostrar_pares"], 0)
        self.assertEqual(primero["filas"][0]["clasificado_segunda"], 12)
        self.assertEqual(primero["filas"][0]["clasificado_segunda_docenas"], 1)
        self.assertFalse(segundo["tiene_operarios"])
        self.assertEqual(segundo["filas"][0]["operario_nombre"], "Sin operario en el parte")
        self.assertEqual(segundo["saldo_produccion_docenas"], 4)
        self.assertEqual(segundo["saldo_produccion_pares"], 0)

    def test_descarta_borrador_legacy_sin_aviso(self):
        parches = [
            patch(
                "mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno",
                return_value={},
            ),
            patch(
                "mpr.services_cc_consolidado._pivot_saldo_produccion",
                return_value={},
            ),
            patch(
                "mpr.repositories.transicion_lote.semi_agregado_por_articulo_fecha",
                return_value={},
            ),
            patch(
                "mpr.repositories.transicion_lote.desglose_cc_confirmado_por_celda_fecha",
                return_value={},
            ),
            patch(
                "mpr.repositories.transicion_lote.clasificado_segunda_scrap_por_celda_fecha",
                return_value={},
            ),
            patch(
                "mpr.repositories.clasificacion_borrador.tiene_borrador_cc_consolidado",
                return_value=False,
            ),
            patch(
                "mpr.repositories.clasificacion_borrador.listar_lineas_borrador_cc_consolidado",
                return_value=[],
            ),
            patch(
                "mpr.repositories.clasificacion_borrador.tiene_borrador",
                return_value=True,
            ),
            patch(
                "mpr.repositories.clasificacion_borrador.eliminar_borrador_legacy_fecha",
                return_value=1,
            ),
            patch(
                "mpr.services._fetch_descripciones_articulo",
                return_value={},
            ),
            patch(
                "mpr.repositories.turno_roster.listar_turnos_dict",
                return_value=[],
            ),
        ]
        started = [p.start() for p in parches]
        try:
            resultado = construir_bloques_cc_articulo(
                EMPRESA, FECHA, solo_pendiente=False
            )
        finally:
            for p in reversed(parches):
                p.stop()

        self.assertFalse(resultado["borrador_incompatible"])
        self.assertEqual(resultado["aviso_borrador"], "")
        started[8].assert_called_once_with(EMPRESA, FECHA)
