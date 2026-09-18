"""Paridad cierre kardex pipeline vs inventario fabricados (oráculo en test)."""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase

from mpr.services_kardex_articulo import (
    _conciliar_cierre_por_etapa,
    construir_analisis_trazabilidad_articulo,
)

_ETAPAS = [
    {"id_deposito": 3, "tipo_mpr": "Produccion", "label": "Producción", "orden": 0},
    {"id_deposito": 5, "tipo_mpr": "SemiElaborado", "label": "Semi elaborado", "orden": 1},
    {"id_deposito": 7, "tipo_mpr": "2daSeleccion", "label": "2da Selección", "orden": 2},
]


class TestParidadKardexInventarioEtapa(SimpleTestCase):
    def test_descuadre_una_etapa_emite_un_solo_mensaje(self):
        advertencias = []

        estricta, conciliacion = _conciliar_cierre_por_etapa(
            saldo_final_por_etapa={
                "Produccion": 79,
                "SemiElaborado": 27,
                "2daSeleccion": 0,
            },
            stock_por_etapa={
                "Produccion": 79,
                "SemiElaborado": 28,
                "2daSeleccion": 0,
            },
            etapas=_ETAPAS,
            hasta_date=date.today(),
            hoy=date.today(),
            calculado_ok=True,
            advertencias=advertencias,
        )

        self.assertTrue(estricta)
        self.assertEqual(conciliacion["SemiElaborado"]["diferencia"], -1)
        self.assertEqual(len(advertencias), 1)
        self.assertIn("Semi elaborado", advertencias[0])
        self.assertNotIn("Producción:", advertencias[0])
        self.assertNotIn("2da Selección:", advertencias[0])

    @patch("mpr.services_kardex_articulo._consultar_eventos_mpr_articulo", return_value=[])
    @patch("mpr.services.calcular_max_packs_armado_1ra", return_value=0)
    @patch("mpr.services.get_bom_detalle", return_value=None)
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=None)
    @patch("mpr.services.listar_demanda_ped_por_articulo", return_value=[])
    @patch(
        "mpr.services_kardex_articulo._fetch_stock_por_etapa_pipeline",
        return_value={"Produccion": 79, "SemiElaborado": 28, "2daSeleccion": 0},
    )
    @patch(
        "mpr.services._fetch_descripciones_articulo",
        return_value={1115: ("X", "Componente paridad")},
    )
    @patch("mpr.services.get_etapas_pipeline_fabricados_mpr", return_value=_ETAPAS)
    @patch("mpr.services_kardex_articulo._fetch_stock_reserva_articulo", return_value=0)
    @patch("mpr.services_kardex_articulo._recolectar_movimientos_analisis", return_value=[])
    @patch(
        "mpr.services_kardex_articulo._calcular_saldo_inicial_por_etapa",
        return_value=(
            {"Produccion": 79, "SemiElaborado": 28, "2daSeleccion": 0},
            True,
        ),
    )
    def test_cierre_cuadra_sin_advertencia_hasta_hoy(self, *_mocks):
        hoy = date.today().isoformat()
        payload = construir_analisis_trazabilidad_articulo(
            "empresa92",
            1115,
            fecha_desde="2026-01-01",
            fecha_hasta=hoy,
        )
        self.assertEqual(payload["kpis"]["saldo_final"], 107)
        self.assertEqual(payload["kpis"]["saldo_final_por_etapa"]["Produccion"], 79)
        self.assertTrue(payload["kpis"]["conciliacion_estricta"])
        conc = payload["kpis"]["conciliacion_por_etapa"]
        self.assertEqual(conc["Produccion"]["diferencia"], 0)
        adv = " ".join(payload.get("advertencias") or [])
        self.assertNotIn("no coincide con el inventario por etapa", adv)

    @patch("mpr.services_kardex_articulo._consultar_eventos_mpr_articulo", return_value=[])
    @patch("mpr.services.calcular_max_packs_armado_1ra", return_value=0)
    @patch("mpr.services.get_bom_detalle", return_value=None)
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=None)
    @patch("mpr.services.listar_demanda_ped_por_articulo", return_value=[])
    @patch(
        "mpr.services_kardex_articulo._fetch_stock_por_etapa_pipeline",
        return_value={"Produccion": 79, "SemiElaborado": 28, "2daSeleccion": 0},
    )
    @patch(
        "mpr.services._fetch_descripciones_articulo",
        return_value={1115: ("X", "Componente paridad")},
    )
    @patch("mpr.services.get_etapas_pipeline_fabricados_mpr", return_value=_ETAPAS)
    @patch("mpr.services_kardex_articulo._fetch_stock_reserva_articulo", return_value=0)
    @patch("mpr.services_kardex_articulo._recolectar_movimientos_analisis", return_value=[])
    def test_hasta_pasado_sin_conciliacion_estricta(self, *_mocks):
        ayer = (date.today() - timedelta(days=1)).isoformat()
        payload = construir_analisis_trazabilidad_articulo(
            "empresa92",
            1115,
            fecha_desde="2026-01-01",
            fecha_hasta=ayer,
        )
        self.assertFalse(payload["kpis"].get("conciliacion_estricta"))
        adv = " ".join(payload.get("advertencias") or [])
        self.assertNotIn("por etapa", adv.lower())
