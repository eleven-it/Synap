"""Bloqueo configurable parte de producción vs Fabricando + suma multi-operario."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from mpr.models import MprEmpresaConfig, MprTurno
from mpr.services import TIPO_MPR_PRODUCCION as TIPO_PROD

EMPRESA = "test_bloqueo_fab"


def _crear_turno():
    return MprTurno.objects.create(
        base_empresa=EMPRESA,
        nombre="Mañana",
        hora_inicio="06:00",
        hora_fin="14:00",
        activo=True,
    )


class TestBloqueoFabricandoConfigurable(TestCase):
    """Bloqueo por MprEmpresaConfig + warning con suma de operarios."""

    def setUp(self):
        self.turno = _crear_turno()

    def _patches_fabricando(self, fab_map):
        enviado_map = {art: Decimal(str(fab + 10)) for art, fab in fab_map.items()}
        stock = {
            art: {TIPO_PROD: float(enviado_map[art] - Decimal(str(fab)))}
            for art, fab in fab_map.items()
        }
        return patch("mpr.services._query_enviado_tablero_componente", return_value=enviado_map), \
            patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=(stock, {})), \
            patch("mpr.services._fetch_descripciones_articulo", return_value={
                art: (f"C{art}", f"Comp {art}") for art in fab_map
            }), \
            patch("mpr.services._registrar_asiento_fisico_opp_parte"), \
            patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"}), \
            patch("mpr.services.get_deposito_produccion_mpr", return_value=5)

    def test_bloqueo_activo_rechaza_exceso(self):
        from mpr.services import registrar_parte_produccion

        MprEmpresaConfig.objects.create(
            base_empresa=EMPRESA,
            bloquear_parte_supera_fabricando=True,
        )
        lineas = [
            {"id_articulo": 42, "id_operario": 1, "cantidad": Decimal("4")},
            {"id_articulo": 42, "id_operario": 2, "cantidad": Decimal("4")},
        ]
        p1, p2, p3, p4, p5, p6 = self._patches_fabricando({42: 6.0})
        with p1, p2, p3, p4, p5, p6:
            with self.assertRaises(ValidationError) as ctx:
                registrar_parte_produccion(
                    EMPRESA, date(2026, 7, 3), self.turno.pk, 1, lineas,
                )
        self.assertIn("Fabricando", str(ctx.exception))

    def test_bloqueo_inactivo_warning_suma_operarios(self):
        from mpr.services import registrar_parte_produccion

        MprEmpresaConfig.objects.create(
            base_empresa=EMPRESA,
            bloquear_parte_supera_fabricando=False,
        )
        lineas = [
            {"id_articulo": 42, "id_operario": 1, "cantidad": Decimal("4")},
            {"id_articulo": 42, "id_operario": 2, "cantidad": Decimal("4")},
        ]
        p1, p2, p3, p4, p5, p6 = self._patches_fabricando({42: 6.0})
        with p1, p2, p3, p4, p5, p6:
            parte, warnings = registrar_parte_produccion(
                EMPRESA, date(2026, 7, 3), self.turno.pk, 1, lineas,
            )
        self.assertEqual(len(warnings), 1)
        self.assertIn("8.0", warnings[0])
        self.assertIn("6.0", warnings[0])
        self.assertTrue(parte.movimiento_fisico_ok)

    def test_obtener_config_default_true(self):
        from mpr.services import obtener_config_mpr

        cfg = obtener_config_mpr(EMPRESA)
        self.assertTrue(cfg["bloquear_parte_supera_fabricando"])

    def test_actualizar_config_bloqueo(self):
        from mpr.services import actualizar_config_mpr_bloqueo_fabricando, obtener_config_mpr

        ok, err = actualizar_config_mpr_bloqueo_fabricando(EMPRESA, True)
        self.assertTrue(ok)
        self.assertIsNone(err)
        self.assertTrue(obtener_config_mpr(EMPRESA)["bloquear_parte_supera_fabricando"])
