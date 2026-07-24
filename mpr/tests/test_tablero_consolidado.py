"""Tests unitarios — MPR Etapa 2: Tablero de Demanda Consolidado por Artículo.

Suite pura: no requiere base de datos MySQL real. Usa SimpleTestCase y mocks.
Comando: docker exec Synap_app python manage.py test mpr.tests.test_tablero_consolidado
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.pipeline import TIPOS_QUE_SUMAN_STOCK
from mpr.services import (
    TIPO_MPR_2DA_SELECCION,
    TIPO_MPR_PLANCHADO,
    TIPO_MPR_PRODUCCION,
    TIPO_MPR_SCRAP,
    TIPO_MPR_SEMI_ELABORADO,
    TIPO_MPR_TERMINADO,
    _calcular_fabricando_componente,
    _calcular_fabricando_para_parte,
    _calcular_pendiente_componente,
    _enviado_produccion_por_componente,
    listar_tablero_por_articulo,
)


# ---------------------------------------------------------------------------
# Fixtures reutilizables
# ---------------------------------------------------------------------------

def _abm_map_simple():
    """Pack 1 tiene id_en_abm=100."""
    return {1: 100}


def _bom_map_simple():
    """ABM 100 tiene componente 10 con cantidad 2."""
    return {
        100: {
            "cabecera": {"id_en_abm": 100, "nombre_en_abm": "Pack A"},
            "componentes": [
                {"id_articulo": 10, "cantidad_articulo": 2.0, "codigo_articulo": "COMP-10", "descripcion_articulo": "Componente 10"},
            ],
        }
    }


def _stock_pivot_completo():
    """Stock para componente 10 con múltiples etapas."""
    return {
        10: {
            TIPO_MPR_PRODUCCION: 10.0,
            TIPO_MPR_PLANCHADO: 15.0,
            TIPO_MPR_2DA_SELECCION: 5.0,
            TIPO_MPR_SEMI_ELABORADO: 0.0,
            TIPO_MPR_SCRAP: 8.0,
            TIPO_MPR_TERMINADO: 20.0,
        }
    }


def _desc_map_simple():
    """Descripción del componente 10."""
    return {10: ("COMP-10", "Componente Diez")}


# ---------------------------------------------------------------------------
# Fase 5.2: Tests de helpers puros
# ---------------------------------------------------------------------------

class TestCalcularFabricandoComponente(SimpleTestCase):
    """Fabricando no repunta al clasificar fuera de Producido."""

    def test_solo_producido_descuenta_envios(self):
        stock = {TIPO_MPR_PRODUCCION: 286.0}
        self.assertAlmostEqual(_calcular_fabricando_componente(300.0, stock), 14.0)

    def test_clasificacion_no_repunta_fabricando(self):
        stock = {
            TIPO_MPR_PRODUCCION: 0.0,
            TIPO_MPR_SEMI_ELABORADO: 281.0,
            TIPO_MPR_2DA_SELECCION: 28.0,
            TIPO_MPR_SCRAP: 1.0,
        }
        self.assertAlmostEqual(_calcular_fabricando_componente(300.0, stock), 0.0)

    def test_nunca_negativo(self):
        stock = {
            TIPO_MPR_PRODUCCION: 10.0,
            TIPO_MPR_SEMI_ELABORADO: 20.0,
        }
        self.assertAlmostEqual(_calcular_fabricando_componente(15.0, stock), 0.0)

    def test_clasificado_desde_produccion_sin_stock_fisico(self):
        """Semi consumido en armado: trazabilidad acredita envíos aunque stock semi=0."""
        stock = {
            TIPO_MPR_PRODUCCION: 0.0,
            TIPO_MPR_SEMI_ELABORADO: 0.0,
            TIPO_MPR_2DA_SELECCION: 12.0,
            TIPO_MPR_SCRAP: 0.0,
        }
        self.assertAlmostEqual(
            _calcular_fabricando_componente(2400.0, stock, clasificado_desde_produccion=2400.0),
            0.0,
        )

    def test_terminado_no_acredita_componente(self):
        stock = {
            TIPO_MPR_PRODUCCION: 0.0,
            TIPO_MPR_TERMINADO: 500.0,
        }
        self.assertAlmostEqual(_calcular_fabricando_componente(12.0, stock), 12.0)

    def test_parte_acumulado_acredita_sin_stock(self):
        stock = {TIPO_MPR_PRODUCCION: 0.0}
        self.assertAlmostEqual(
            _calcular_fabricando_componente(12.0, stock, parte_acumulado=12.0),
            0.0,
        )


class TestCalcularFabricandoParaParte(SimpleTestCase):
    """Parte usa el mismo cupo Fabricando que el tablero (incluye Semi/2da tras clasificar)."""

    def test_igual_a_tablero_con_semi_acreditado(self):
        stock = {
            TIPO_MPR_PRODUCCION: 0.0,
            TIPO_MPR_SEMI_ELABORADO: 12.0,
        }
        self.assertAlmostEqual(_calcular_fabricando_para_parte(12.0, stock), 0.0)
        self.assertAlmostEqual(
            _calcular_fabricando_para_parte(12.0, stock),
            _calcular_fabricando_componente(12.0, stock),
        )

    def test_con_stock_solo_produccion(self):
        stock = {TIPO_MPR_PRODUCCION: 4.0}
        self.assertAlmostEqual(_calcular_fabricando_para_parte(12.0, stock), 8.0)


class TestCalcularPendienteComponente(SimpleTestCase):
    """Pendiente legacy con envíos ledger."""

    def test_envio_cubre_brecha(self):
        self.assertAlmostEqual(_calcular_pendiente_componente(12.0, 11.0, 1.0), 0.0)

    def test_sin_envio_mantiene_brecha(self):
        self.assertAlmostEqual(_calcular_pendiente_componente(12.0, 11.0, 0.0), 1.0)

    def test_sobre_envio_no_negativo(self):
        self.assertAlmostEqual(_calcular_pendiente_componente(12.0, 11.0, 3.0), 0.0)


class TestCalcularAEnviarComponente(SimpleTestCase):
    """Tope Enviar: urgente−envíos si Fabricando>0; reabre a urgente si Fabricando=0."""

    def test_resta_menos_envios(self):
        from mpr.services import _calcular_a_enviar_componente

        self.assertAlmostEqual(
            _calcular_a_enviar_componente(12.0, 12.0, fabricando=12.0), 0.0
        )

    def test_parcial_envios(self):
        from mpr.services import _calcular_a_enviar_componente

        self.assertAlmostEqual(
            _calcular_a_enviar_componente(12.0, 5.0, fabricando=5.0), 7.0
        )

    def test_sin_envios(self):
        from mpr.services import _calcular_a_enviar_componente

        self.assertAlmostEqual(_calcular_a_enviar_componente(12.0, 0.0), 12.0)

    def test_envio_exacto_con_stock_preexistente_queda_cero(self):
        """Con Fabricando>0 no residual: stock_proceso ya bajó resta; ledger cubre el hueco."""
        from mpr.services import _calcular_a_enviar_componente

        dem_ped, stock_proceso, envios = 3540.0, 1027.0, 2513.0
        resta = max(0.0, dem_ped - stock_proceso)
        fabricando = 1486.0  # envíos − acreditado(1027)
        self.assertAlmostEqual(resta, 2513.0)
        self.assertAlmostEqual(
            _calcular_a_enviar_componente(resta, envios, fabricando=fabricando),
            0.0,
        )

    def test_reabre_cuando_fabricando_cero_y_urgente_positiva(self):
        """Ciclo acreditado (Fabricando=0): si el recálculo deja urgente>0, reabre Enviar."""
        from mpr.services import _calcular_a_enviar_componente

        self.assertAlmostEqual(
            _calcular_a_enviar_componente(100.0, 100.0, fabricando=0.0),
            100.0,
        )

    def test_a_enviar_no_supera_resta_total(self):
        from mpr.services import _calcular_a_enviar_componente

        self.assertAlmostEqual(
            _calcular_a_enviar_componente(100.0, 0.0, resta_total=40.0),
            40.0,
        )

class TestEnviadoProduccionPorComponente(SimpleTestCase):
    """Tests de la función pura _enviado_produccion_por_componente."""

    def test_explota_bom_correctamente(self):
        """REQ-024, REQ-021 Esc.21.1: pack con OPT=50 y BOM 1:2 → componente recibe 100."""
        enviado_pack_map = {1: 50.0}
        abm_map = _abm_map_simple()
        bom_map = _bom_map_simple()

        resultado = _enviado_produccion_por_componente(enviado_pack_map, abm_map, bom_map)

        self.assertIn(10, resultado)
        self.assertAlmostEqual(resultado[10], 100.0)

    def test_pack_sin_bom_retorna_vacio(self):
        """REQ-021 Esc.21.3: pack sin BOM configurada no aporta componentes."""
        enviado_pack_map = {1: 50.0}
        abm_map = {}
        bom_map = {}

        resultado = _enviado_produccion_por_componente(enviado_pack_map, abm_map, bom_map)

        self.assertEqual(resultado, {})

    def test_acumula_multiples_packs_mismo_componente(self):
        """REQ-021 Esc.21.2: dos packs con mismo componente acumulan correctamente."""
        enviado_pack_map = {1: 10.0, 2: 5.0}
        abm_map = {1: 100, 2: 200}
        bom_map = {
            100: {
                "componentes": [{"id_articulo": 10, "cantidad_articulo": 2.0}]
            },
            200: {
                "componentes": [{"id_articulo": 10, "cantidad_articulo": 3.0}]
            },
        }

        resultado = _enviado_produccion_por_componente(enviado_pack_map, abm_map, bom_map)

        # 10×2 + 5×3 = 35
        self.assertIn(10, resultado)
        self.assertAlmostEqual(resultado[10], 35.0)

    def test_cantidad_opt_cero_no_aporta(self):
        """Pack con OPT=0 no aporta componentes."""
        enviado_pack_map = {1: 0.0}
        abm_map = _abm_map_simple()
        bom_map = _bom_map_simple()

        resultado = _enviado_produccion_por_componente(enviado_pack_map, abm_map, bom_map)

        self.assertNotIn(10, resultado)

    def test_pack_sin_componentes_en_bom(self):
        """Pack con ABM pero sin componentes no aporta."""
        enviado_pack_map = {1: 50.0}
        abm_map = {1: 100}
        bom_map = {100: {"componentes": []}}

        resultado = _enviado_produccion_por_componente(enviado_pack_map, abm_map, bom_map)

        self.assertEqual(resultado, {})

    def test_mapa_enviado_vacio(self):
        """Sin packs con OPT liberada → resultado vacío."""
        resultado = _enviado_produccion_por_componente({}, _abm_map_simple(), _bom_map_simple())
        self.assertEqual(resultado, {})


# ---------------------------------------------------------------------------
# Fase 5.3: Tests del servicio principal listar_tablero_por_articulo
# ---------------------------------------------------------------------------

def _mock_filas_pack():
    """Pack 1 con demanda 10 (pedido), sin stock terminado."""
    return [
        {
            "id_articulo": 1,
            "cantidad_a_fabricar": 10.0,
            "cantidad_pedida_pedido": 10.0,
            "stock_terminado": 0.0,
        }
    ]


class TestListarTableroPorArticulo(SimpleTestCase):
    """Tests del servicio principal con mocks completos."""

    def _patch_servicio(self, filas_pack=None, enviados_tablero=None,
                        enviado_tablero_map=None,
                        abm_map=None, bom_map=None, stock_pivot=None, desc_map=None,
                        stock_suma_pivot=None):
        """Aplica todos los parches necesarios y devuelve context manager apilado."""
        if filas_pack is None:
            filas_pack = _mock_filas_pack()
        if enviados_tablero is None:
            enviados_tablero = {}
        if enviado_tablero_map is None:
            enviado_tablero_map = {}
        if abm_map is None:
            abm_map = _abm_map_simple()
        if bom_map is None:
            bom_map = _bom_map_simple()
        if stock_pivot is None:
            stock_pivot = _stock_pivot_completo()
        if stock_suma_pivot is None:
            stock_suma_pivot = stock_pivot
        if desc_map is None:
            desc_map = _desc_map_simple()

        patches = [
            patch("mpr.services.listar_demanda_pack_desde_pedidos", return_value=filas_pack),
            patch("mpr.services._query_enviados_todos_componentes", return_value=enviados_tablero),
            patch("mpr.services.bulk_id_en_abm", return_value=abm_map),
            patch("mpr.services.bulk_bom_detalle", return_value=bom_map),
            patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=(stock_pivot, stock_suma_pivot)),
            patch("mpr.services._fetch_descripciones_articulo", return_value=desc_map),
            patch("mpr.services._query_enviado_tablero_componente", return_value=enviado_tablero_map),
            patch(
                "mpr.repositories.transicion_lote.sumar_salidas_desde_produccion_por_articulo",
                return_value={},
            ),
            patch(
                "mpr.repositories.parte.opp_acumulado_por_pack",
                return_value={},
            ),
        ]
        return patches

    def _call_con_parches(self, patches, **kwargs):
        activos = [p.start() for p in patches]
        try:
            return listar_tablero_por_articulo("empresa_test", **kwargs)
        finally:
            for p in patches:
                p.stop()

    def test_consolidacion_por_componente(self):
        """REQ-021 Esc.21.2: dos packs con mismo componente → una sola fila consolidada."""
        filas_pack = [
            {"id_articulo": 1, "cantidad_a_fabricar": 10.0, "cantidad_pedida_pedido": 10.0, "stock_terminado": 0.0},
            {"id_articulo": 2, "cantidad_a_fabricar": 5.0, "cantidad_pedida_pedido": 5.0, "stock_terminado": 0.0},
        ]
        abm_map = {1: 100, 2: 200}
        bom_map = {
            100: {"componentes": [{"id_articulo": 10, "cantidad_articulo": 2.0}]},
            200: {"componentes": [{"id_articulo": 10, "cantidad_articulo": 3.0}]},
        }
        stock_pivot = {10: {t: 0.0 for t in [TIPO_MPR_PRODUCCION, TIPO_MPR_PLANCHADO, TIPO_MPR_2DA_SELECCION, TIPO_MPR_SEMI_ELABORADO, TIPO_MPR_SCRAP, TIPO_MPR_TERMINADO]}}
        desc_map = {10: ("C-10", "Componente Diez")}

        patches = self._patch_servicio(
            filas_pack=filas_pack, abm_map=abm_map, bom_map=bom_map,
            stock_pivot=stock_pivot, desc_map=desc_map,
        )
        resultado = self._call_con_parches(patches)

        # Debe haber una sola fila para el componente 10
        ids = [r["id_articulo"] for r in resultado]
        self.assertEqual(ids.count(10), 1, "Solo debe haber una fila para el componente 10")
        fila = next(r for r in resultado if r["id_articulo"] == 10)
        # demanda = 10×2 + 5×3 = 35
        self.assertAlmostEqual(fila["demanda"], 35.0)

    def test_total_excluye_desperdicio(self):
        """REQ-023 Esc.23.1, Esc.23.3: Total no incluye Desperdicio (Scrap)."""
        patches = self._patch_servicio()
        resultado = self._call_con_parches(patches)

        self.assertTrue(len(resultado) > 0, "Debe haber al menos una fila")
        fila = resultado[0]
        # stock_pivot_completo: Produccion=10, 2da=5, Semi=0, Scrap=8, Terminado=20
        # Etapa 10: Planchado ya no suma. Total esperado = 10+5+0 = 15 (sin Scrap ni Terminado)
        self.assertAlmostEqual(fila["total"], 15.0)
        self.assertAlmostEqual(fila["desperdicio"], 8.0)

    def test_total_respeta_suma_stock_por_deposito(self):
        """El Total usa el saldo que suma stock por depósito, no el saldo bruto.

        La columna de la etapa muestra el saldo real (p. ej. Terminado=20), pero si
        ese depósito tiene suma_stock='No' su saldo NO se cuenta en el Total.
        """
        stock_pivot = _stock_pivot_completo()
        # Simula que el depósito Terminado NO suma stock: saldo real 20, pero 0 para el Total.
        stock_suma_pivot = {
            10: {
                TIPO_MPR_PRODUCCION: 10.0,
                TIPO_MPR_PLANCHADO: 15.0,
                TIPO_MPR_2DA_SELECCION: 5.0,
                TIPO_MPR_SEMI_ELABORADO: 0.0,
                TIPO_MPR_SCRAP: 0.0,
                TIPO_MPR_TERMINADO: 0.0,
            }
        }
        patches = self._patch_servicio(stock_pivot=stock_pivot, stock_suma_pivot=stock_suma_pivot)
        resultado = self._call_con_parches(patches)

        fila = resultado[0]
        # Componentes: Terminado no aplica en tablero de producción
        self.assertAlmostEqual(fila["terminado"], 0.0)
        # Etapa 10: Planchado ya no suma. Total excluye Terminado: 10+5+0 = 15
        self.assertAlmostEqual(fila["total"], 15.0)

    def test_pendiente_derivado_sin_stock(self):
        """REQ-025 Esc.25.1: demanda=20, enviado=0, total=0 → pendiente=20."""
        stock_pivot = {10: {t: 0.0 for t in [TIPO_MPR_PRODUCCION, TIPO_MPR_PLANCHADO, TIPO_MPR_2DA_SELECCION, TIPO_MPR_SEMI_ELABORADO, TIPO_MPR_SCRAP, TIPO_MPR_TERMINADO]}}
        patches = self._patch_servicio(stock_pivot=stock_pivot)
        resultado = self._call_con_parches(patches)

        self.assertTrue(len(resultado) > 0)
        fila = resultado[0]
        # demanda = 10×2 = 20, enviado=0, total=0 → pendiente=20
        self.assertAlmostEqual(fila["pendiente"], 20.0)

    def test_pendiente_reducido_por_stock(self):
        """REQ-025 Esc.25.2: demanda=20, enviado=0, total=12 → pendiente=8."""
        stock_pivot = {
            10: {
                TIPO_MPR_PRODUCCION: 5.0,
                # Etapa 10: sin stock en Planchado; el saldo intermedio ya está clasificado.
                TIPO_MPR_2DA_SELECCION: 7.0,
                TIPO_MPR_SEMI_ELABORADO: 0.0,
                TIPO_MPR_SCRAP: 0.0,
                TIPO_MPR_TERMINADO: 0.0,
            }
        }
        patches = self._patch_servicio(stock_pivot=stock_pivot)
        resultado = self._call_con_parches(patches)

        fila = resultado[0]
        # demanda=20, total=12, enviado=0 → pendiente=8
        self.assertAlmostEqual(fila["total"], 12.0)
        self.assertAlmostEqual(fila["pendiente"], 8.0)

    def test_pendiente_reducido_por_enviado_y_stock(self):
        """REQ-025 Esc.25.3: resta PCP no descuenta envíos; Fabricando sí refleja envíos no acreditados."""
        stock_pivot = {
            10: {
                TIPO_MPR_PRODUCCION: 5.0,
                TIPO_MPR_2DA_SELECCION: 7.0,
                TIPO_MPR_SEMI_ELABORADO: 0.0,
                TIPO_MPR_SCRAP: 0.0,
                TIPO_MPR_TERMINADO: 0.0,
            }
        }
        patches = self._patch_servicio(
            stock_pivot=stock_pivot,
            enviado_tablero_map={10: Decimal("13")},
        )
        resultado = self._call_con_parches(patches)

        fila = resultado[0]
        # demanda=20, stock_proceso=12 → resta_total=8 (PCP); envíos no restan brecha
        self.assertAlmostEqual(fila["enviado"], 1.0)
        self.assertAlmostEqual(fila["total"], 12.0)
        self.assertAlmostEqual(fila["resta_total"], 8.0)
        self.assertAlmostEqual(fila["pendiente"], 8.0)

    def test_enviado_diferente_de_produccion(self):
        """Enviado (virtual tablero) ≠ produccion (físico) por construcción."""
        stock_pivot = {
            10: {
                TIPO_MPR_PRODUCCION: 20.0,
                TIPO_MPR_PLANCHADO: 0.0,
                TIPO_MPR_2DA_SELECCION: 0.0,
                TIPO_MPR_SEMI_ELABORADO: 0.0,
                TIPO_MPR_SCRAP: 0.0,
                TIPO_MPR_TERMINADO: 0.0,
            }
        }
        patches = self._patch_servicio(
            stock_pivot=stock_pivot,
            enviado_tablero_map={10: Decimal("50")},
        )
        resultado = self._call_con_parches(patches)

        fila = resultado[0]
        # enviado = max(0, 50 - 20) = 30
        self.assertAlmostEqual(fila["enviado"], 30.0)
        self.assertAlmostEqual(fila["produccion"], 20.0)
        self.assertNotAlmostEqual(fila["enviado"], fila["produccion"])

    def test_pendiente_no_negativo(self):
        """REQ-025 Esc.25.4: oferta supera demanda → pendiente=0 (no negativo)."""
        stock_pivot = {
            10: {
                TIPO_MPR_PRODUCCION: 100.0,
                TIPO_MPR_PLANCHADO: 0.0,
                TIPO_MPR_2DA_SELECCION: 0.0,
                TIPO_MPR_SEMI_ELABORADO: 0.0,
                TIPO_MPR_SCRAP: 0.0,
                TIPO_MPR_TERMINADO: 0.0,
            }
        }
        patches = self._patch_servicio(stock_pivot=stock_pivot)
        resultado = self._call_con_parches(patches)

        fila = resultado[0]
        self.assertGreaterEqual(fila["pendiente"], 0.0)

    def test_tablero_vacio_sin_error(self):
        """REQ-035 Esc.35.1: sin demanda ni envíos → resultado vacío sin excepción."""
        patches = self._patch_servicio(filas_pack=[], enviados_tablero={})
        resultado = self._call_con_parches(patches)

        self.assertEqual(resultado, [])

    def test_solo_urgente_filtra_cero(self):
        """Filas con resta_urgente=0 no aparecen cuando solo_urgente=True."""
        stock_pivot = {
            10: {
                TIPO_MPR_PRODUCCION: 20.0,
                TIPO_MPR_PLANCHADO: 0.0,
                TIPO_MPR_2DA_SELECCION: 0.0,
                TIPO_MPR_SEMI_ELABORADO: 0.0,
                TIPO_MPR_SCRAP: 0.0,
                TIPO_MPR_TERMINADO: 0.0,
            }
        }
        patches = self._patch_servicio(stock_pivot=stock_pivot)
        resultado = self._call_con_parches(patches, solo_urgente=True)

        self.assertEqual(len(resultado), 0)

    def test_solo_pendiente_filtra_demanda_total(self):
        """solo_pendiente=True conserva filas con demanda total pendiente."""
        patches = self._patch_servicio()
        resultado = self._call_con_parches(patches, solo_pendiente=True)
        for r in resultado:
            self.assertGreater(r["resta_total"], 0)

    def test_resta_urgente_excluye_terminado_del_stock(self):
        """stock_proceso no incluye Terminado — paridad PCP col G."""
        stock_pivot = {
            10: {
                TIPO_MPR_PRODUCCION: 5.0,
                TIPO_MPR_2DA_SELECCION: 0.0,
                TIPO_MPR_SEMI_ELABORADO: 0.0,
                TIPO_MPR_SCRAP: 0.0,
                TIPO_MPR_TERMINADO: 100.0,
            }
        }
        stock_suma = {
            10: {
                TIPO_MPR_PRODUCCION: 5.0,
                TIPO_MPR_2DA_SELECCION: 0.0,
                TIPO_MPR_SEMI_ELABORADO: 0.0,
                TIPO_MPR_SCRAP: 0.0,
                TIPO_MPR_TERMINADO: 100.0,
            }
        }
        patches = self._patch_servicio(stock_pivot=stock_pivot, stock_suma_pivot=stock_suma)
        resultado = self._call_con_parches(patches)
        fila = resultado[0]
        self.assertAlmostEqual(fila["stock_proceso"], 5.0)
        # dem_ped=20, stock_proceso=5 → resta_urgente=resta_total=15 (demanda total)
        self.assertAlmostEqual(fila["resta_urgente"], 15.0)
        self.assertAlmostEqual(fila["resta_total"], 15.0)
        self.assertAlmostEqual(fila["total"], 5.0)

    def test_articulo_sin_bom_no_aparece(self):
        """REQ-021 Esc.21.3: pack sin BOM no aporta componentes → tablero vacío."""
        patches = self._patch_servicio(abm_map={}, bom_map={})
        resultado = self._call_con_parches(patches)

        self.assertEqual(resultado, [])

    def test_orden_descendente_por_resta_urgente(self):
        """Filas ordenadas por resta_urgente descendente."""
        filas_pack = [
            {"id_articulo": 1, "cantidad_a_fabricar": 5.0, "cantidad_pedida_pedido": 5.0, "stock_terminado": 0.0},
            {"id_articulo": 2, "cantidad_a_fabricar": 20.0, "cantidad_pedida_pedido": 20.0, "stock_terminado": 0.0},
        ]
        abm_map = {1: 100, 2: 200}
        bom_map = {
            100: {"componentes": [{"id_articulo": 10, "cantidad_articulo": 1.0}]},
            200: {"componentes": [{"id_articulo": 20, "cantidad_articulo": 1.0}]},
        }
        stock_pivot = {
            10: {t: 0.0 for t in [TIPO_MPR_PRODUCCION, TIPO_MPR_PLANCHADO, TIPO_MPR_2DA_SELECCION, TIPO_MPR_SEMI_ELABORADO, TIPO_MPR_SCRAP, TIPO_MPR_TERMINADO]},
            20: {t: 0.0 for t in [TIPO_MPR_PRODUCCION, TIPO_MPR_PLANCHADO, TIPO_MPR_2DA_SELECCION, TIPO_MPR_SEMI_ELABORADO, TIPO_MPR_SCRAP, TIPO_MPR_TERMINADO]},
        }
        desc_map = {10: ("C-10", "Comp Diez"), 20: ("C-20", "Comp Veinte")}

        patches = self._patch_servicio(
            filas_pack=filas_pack, abm_map=abm_map, bom_map=bom_map,
            stock_pivot=stock_pivot, desc_map=desc_map,
        )
        resultado = self._call_con_parches(patches)

        self.assertEqual(len(resultado), 2)
        # Componente 20 tiene demanda=20, componente 10 tiene demanda=5
        self.assertEqual(resultado[0]["id_articulo"], 20)
        self.assertEqual(resultado[1]["id_articulo"], 10)

    def test_base_empresa_vacia_retorna_lista_vacia(self):
        """Sin base_empresa el servicio retorna [] sin excepción."""
        resultado = listar_tablero_por_articulo("")
        self.assertEqual(resultado, [])


# ---------------------------------------------------------------------------
# Fase 5.4: Test de idempotencia del índice
# ---------------------------------------------------------------------------

class TestIndiceIdempotente(SimpleTestCase):
    """REQ-036: idx_sd_art_dep es idempotente."""

    def test_indice_no_se_crea_si_ya_existe(self):
        """REQ-036 Esc.36.2: si indice_existe retorna True, no se llama CREATE INDEX."""
        from core.services.legacy_mysql_schema.catalog import run_mpr_deposito_articulo_mysql

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with (
            patch("core.services.legacy_mysql_schema.catalog.nombre_tabla_real", return_value="stock_deposito"),
            patch("core.services.legacy_mysql_schema.catalog.columna_existe", return_value=True),
            patch("core.services.legacy_mysql_schema.catalog.indice_existe", return_value=True),
        ):
            run_mpr_deposito_articulo_mysql(mock_conn)

        # Ninguna llamada a execute debe contener CREATE INDEX idx_sd_art_dep
        create_calls = [
            call for call in mock_cursor.execute.call_args_list
            if "idx_sd_art_dep" in str(call)
        ]
        self.assertEqual(len(create_calls), 0, "No debe crear el índice si ya existe")

    def test_indice_se_crea_si_no_existe(self):
        """REQ-036 Esc.36.1: si el índice no existe, se ejecuta CREATE INDEX."""
        from core.services.legacy_mysql_schema.catalog import run_mpr_deposito_articulo_mysql

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with (
            patch("core.services.legacy_mysql_schema.catalog.nombre_tabla_real", return_value="stock_deposito"),
            patch("core.services.legacy_mysql_schema.catalog.columna_existe", return_value=True),
            patch("core.services.legacy_mysql_schema.catalog.indice_existe", return_value=False),
        ):
            run_mpr_deposito_articulo_mysql(mock_conn)

        create_calls = [
            call for call in mock_cursor.execute.call_args_list
            if "idx_sd_art_dep" in str(call)
        ]
        self.assertGreater(len(create_calls), 0, "Debe haber al menos una llamada CREATE INDEX idx_sd_art_dep")


# ---------------------------------------------------------------------------
# Fase 5.3 extra: Verificación de constantes TIPOS_QUE_SUMAN_STOCK
# ---------------------------------------------------------------------------

class TestTiposQueSumanStock(SimpleTestCase):
    """Verifica que TIPOS_QUE_SUMAN_STOCK excluye explícitamente Scrap."""

    def test_scrap_no_en_tipos_que_suman_stock(self):
        """REQ-023 Esc.23.4: Scrap (Desperdicio) NO debe estar en TIPOS_QUE_SUMAN_STOCK."""
        self.assertNotIn(TIPO_MPR_SCRAP, TIPOS_QUE_SUMAN_STOCK)

    def test_fisicos_en_tipos_que_suman_stock(self):
        """REQ-023 (Etapa 10): los 4 tipos físicos (sin Scrap ni Planchado) suman al Total."""
        for tipo in [TIPO_MPR_PRODUCCION, TIPO_MPR_2DA_SELECCION,
                     TIPO_MPR_SEMI_ELABORADO, TIPO_MPR_TERMINADO]:
            self.assertIn(tipo, TIPOS_QUE_SUMAN_STOCK, f"{tipo} debe estar en TIPOS_QUE_SUMAN_STOCK")
        self.assertNotIn(TIPO_MPR_PLANCHADO, TIPOS_QUE_SUMAN_STOCK,
                         "Planchado ya no suma al Total (Etapa 10)")
