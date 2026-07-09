"""Bloqueo parte de producción vs Fabricando + techo envíos ledger."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from mpr.models import MprEmpresaConfig, MprTurno
from mpr.services import (
    TIPO_MPR_PRODUCCION,
    TIPO_MPR_SEMI_ELABORADO,
)

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
    """Validaciones fuertes: cupo pipeline + techo envíos (siempre activas)."""

    def setUp(self):
        self.turno = _crear_turno()

    def _mock_turno(self):
        turno = MagicMock()
        turno.id_mpr_turno = self.turno.pk
        return patch("mpr.services.obtener_turno", return_value=turno)

    def _patches_fabricando(self, fab_map, *, stock_extra=None, acum_parte=None):
        enviado_map = {art: Decimal(str(fab + 10)) for art, fab in fab_map.items()}
        stock = {}
        for art, fab in fab_map.items():
            row = {TIPO_MPR_PRODUCCION: float(enviado_map[art] - Decimal(str(fab)))}
            if stock_extra and art in stock_extra:
                row.update(stock_extra[art])
            stock[art] = row
        acum = acum_parte or {art: Decimal("0") for art in fab_map}
        return (
            patch("mpr.services._query_enviado_tablero_componente", return_value=enviado_map),
            patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=(stock, {})),
            patch("mpr.services._fetch_descripciones_articulo", return_value={
                art: (f"C{art}", f"Comp {art}") for art in fab_map
            }),
            patch("mpr.services._registrar_asiento_fisico_opp_parte"),
            patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"}),
            patch("mpr.services.get_deposito_produccion_mpr", return_value=5),
            patch("mpr.repositories.parte.opp_acumulado_por_pack", return_value=acum),
        )

    def test_bloqueo_activo_rechaza_exceso_fabricando(self):
        from mpr.services import registrar_parte_produccion

        MprEmpresaConfig.objects.create(
            base_empresa=EMPRESA,
            bloquear_parte_supera_fabricando=True,
        )
        lineas = [
            {"id_articulo": 42, "id_operario": 1, "cantidad": Decimal("4")},
            {"id_articulo": 42, "id_operario": 2, "cantidad": Decimal("4")},
        ]
        patches = self._patches_fabricando({42: 6.0})
        with self._mock_turno():
            with patch("mpr.repositories.parte.crear_parte_con_lineas") as mock_crear:
                mock_crear.return_value = type("P", (), {"movimiento_fisico_ok": False, "save": lambda *a, **k: None})()
                with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
                    with self.assertRaises(ValidationError) as ctx:
                        registrar_parte_produccion(
                            EMPRESA, date(2026, 7, 3), self.turno.pk, 1, lineas,
                        )
        self.assertIn("Fabricando", str(ctx.exception))

    def test_bloqueo_inactivo_tambien_rechaza_exceso_fabricando(self):
        """Aunque la config legacy esté OFF, las validaciones fuertes bloquean."""
        from mpr.services import registrar_parte_produccion

        MprEmpresaConfig.objects.create(
            base_empresa=EMPRESA,
            bloquear_parte_supera_fabricando=False,
        )
        lineas = [
            {"id_articulo": 42, "id_operario": 1, "cantidad": Decimal("4")},
            {"id_articulo": 42, "id_operario": 2, "cantidad": Decimal("4")},
        ]
        patches = self._patches_fabricando({42: 6.0})
        with self._mock_turno():
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
                with self.assertRaises(ValidationError):
                    registrar_parte_produccion(
                        EMPRESA, date(2026, 7, 3), self.turno.pk, 1, lineas,
                    )

    def test_rechaza_segundo_parte_tras_clasificacion_a_semi(self):
        """Caso 1904: envíos 12, semi 12, prod 0 → cupo Fabricando 0."""
        from mpr.services import registrar_parte_produccion

        lineas = [{"id_articulo": 1275, "id_operario": 2, "cantidad": Decimal("12")}]
        stock_extra = {
            1275: {
                TIPO_MPR_PRODUCCION: 0.0,
                TIPO_MPR_SEMI_ELABORADO: 12.0,
            },
        }
        patches = self._patches_fabricando(
            {1275: 0.0},
            stock_extra=stock_extra,
            acum_parte={1275: Decimal("12")},
        )
        enviado_map = {1275: Decimal("12")}
        with self._mock_turno():
            with patch("mpr.services._query_enviado_tablero_componente", return_value=enviado_map):
                with patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
                    with self.assertRaises(ValidationError) as ctx:
                        registrar_parte_produccion(
                            EMPRESA, date(2026, 7, 7), self.turno.pk, 1, lineas,
                        )
        msg = str(ctx.exception)
        self.assertTrue("Fabricando" in msg or "envíos" in msg)

    def test_rechaza_cuando_partes_acumulados_superan_envios(self):
        from mpr.services import registrar_parte_produccion

        lineas = [{"id_articulo": 99, "id_operario": 1, "cantidad": Decimal("6")}]
        patches = self._patches_fabricando(
            {99: 6.0},
            acum_parte={99: Decimal("10")},
        )
        enviado_map = {99: Decimal("12")}
        with self._mock_turno():
            with patch("mpr.services._query_enviado_tablero_componente", return_value=enviado_map):
                with patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
                    with self.assertRaises(ValidationError) as ctx:
                        registrar_parte_produccion(
                            EMPRESA, date(2026, 7, 7), self.turno.pk, 1, lineas,
                        )
        self.assertIn("envíos", str(ctx.exception).lower())

    def test_obtener_config_default_true(self):
        from mpr.services import obtener_config_mpr

        with patch(
            "mpr.repositories.config.obtener_config",
            return_value={"bloquear_parte_supera_fabricando": True},
        ):
            cfg = obtener_config_mpr(EMPRESA)
        self.assertTrue(cfg["bloquear_parte_supera_fabricando"])

    def test_actualizar_config_bloqueo(self):
        from mpr.services import actualizar_config_mpr_bloqueo_fabricando, obtener_config_mpr

        with patch("mpr.repositories.config.actualizar_bloqueo_fabricando", return_value=(True, None)), \
             patch(
                 "mpr.repositories.config.obtener_config",
                 return_value={"bloquear_parte_supera_fabricando": True},
             ):
            ok, err = actualizar_config_mpr_bloqueo_fabricando(EMPRESA, True)
            self.assertTrue(ok)
            self.assertIsNone(err)
            self.assertTrue(obtener_config_mpr(EMPRESA)["bloquear_parte_supera_fabricando"])
