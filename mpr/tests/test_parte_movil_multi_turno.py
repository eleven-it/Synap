# -*- coding: utf-8 -*-
"""Tests Fase 4: carga móvil con multi-turno y resolución de línea por turno."""
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services_parte_movil import construir_grilla_carga_movil, registrar_parte_movil

EMPRESA = "EmpresaTest"
FECHA = date(2026, 8, 12)
ID_OPERARIO = 7
ID_USUARIO = 3

PATCH_BLOQUEO = patch("mpr.services._motivo_bloqueo_roster_celda", return_value=None)


class TestParteMovilMultiTurno(SimpleTestCase):
    """Operario con Mañana+Tarde: línea independiente; bloqueo por turno."""

    def _mock_turno(self, tid, nombre):
        t = MagicMock()
        t.nombre = nombre
        return t

    @PATCH_BLOQUEO
    @patch("mpr.repositories.maquina_linea.maquinas_de_linea", return_value=[])
    @patch("mpr.repositories.maquina_linea.obtener_linea", return_value={"nombre": "L1"})
    @patch("mpr.services_operario.resolver_linea_operario")
    @patch("mpr.repositories.turno_roster.obtener_turno_record")
    @patch("mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[1, 2])
    def test_dos_turnos_resuelve_linea_independiente(
        self, mock_turnos, mock_obtener_turno, mock_resolver, *_rest
    ):
        mock_obtener_turno.side_effect = lambda _b, tid: self._mock_turno(
            tid, "Mañana" if tid == 1 else "Tarde"
        )
        mock_resolver.side_effect = lambda _b, _op, _f, id_turno: 10 if id_turno == 1 else 20

        ctx_manana = construir_grilla_carga_movil(
            EMPRESA, ID_OPERARIO, ID_USUARIO, fecha=FECHA, id_turno=1
        )
        ctx_tarde = construir_grilla_carga_movil(
            EMPRESA, ID_OPERARIO, ID_USUARIO, fecha=FECHA, id_turno=2
        )

        self.assertEqual(ctx_manana["id_turno"], 1)
        self.assertEqual(ctx_manana["id_linea"], 10)
        self.assertEqual(ctx_tarde["id_turno"], 2)
        self.assertEqual(ctx_tarde["id_linea"], 20)
        self.assertTrue(ctx_manana["multi_turno"])
        mock_resolver.assert_any_call(EMPRESA, ID_OPERARIO, FECHA, 1)
        mock_resolver.assert_any_call(EMPRESA, ID_OPERARIO, FECHA, 2)

    @patch("mpr.services._motivo_bloqueo_roster_celda")
    @patch("mpr.repositories.maquina_linea.maquinas_de_linea", return_value=[{"id": 1, "codigo": "M1"}])
    @patch("mpr.repositories.maquina_linea.obtener_linea", return_value={"nombre": "L1"})
    @patch("mpr.services_operario.resolver_linea_operario", return_value=10)
    @patch("mpr.repositories.maquina_articulo.listar_articulos_vigentes", return_value=[])
    @patch("mpr.repositories.parte_movil.obtener_parte_movil_editable", return_value=None)
    @patch("mpr.repositories.turno_roster.obtener_turno_record")
    @patch("mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[1, 2])
    def test_turno_bloqueado_no_impide_otro(
        self, mock_turnos, mock_obtener_turno, _editable, _arts, _resolver, _linea, _maqs, mock_bloqueo
    ):
        mock_obtener_turno.side_effect = lambda _b, tid: self._mock_turno(
            tid, "Mañana" if tid == 1 else "Tarde"
        )
        mock_bloqueo.side_effect = lambda _b, _f, _op, tid: (
            "bloqueado" if tid == 1 else None
        )

        ctx_bloq = construir_grilla_carga_movil(
            EMPRESA, ID_OPERARIO, ID_USUARIO, fecha=FECHA, id_turno=1
        )
        ctx_ok = construir_grilla_carga_movil(
            EMPRESA, ID_OPERARIO, ID_USUARIO, fecha=FECHA, id_turno=2
        )

        self.assertEqual(ctx_bloq["estado_borde"], "turno_bloqueado")
        self.assertEqual(ctx_ok["estado_borde"], "ok")
        self.assertEqual(len(ctx_ok["turnos_dia"]), 2)

    @patch("mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[])
    def test_sin_turnos_estado_borde(self, _mock_turnos):
        ctx = construir_grilla_carga_movil(
            EMPRESA, ID_OPERARIO, ID_USUARIO, fecha=FECHA
        )
        self.assertEqual(ctx["estado_borde"], "sin_turno")
        self.assertEqual(ctx["turnos_dia"], [])

    @PATCH_BLOQUEO
    @patch("mpr.repositories.maquina_linea.maquinas_de_linea", return_value=[])
    @patch("mpr.repositories.maquina_linea.obtener_linea", return_value={"nombre": "L1"})
    @patch("mpr.services_operario.resolver_linea_operario", return_value=10)
    @patch("mpr.repositories.turno_roster.obtener_turno_record")
    @patch("mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[1])
    def test_un_solo_turno_sin_multi(
        self, mock_turnos, mock_obtener_turno, mock_resolver, *_rest
    ):
        mock_obtener_turno.return_value = self._mock_turno(1, "Mañana")

        ctx = construir_grilla_carga_movil(
            EMPRESA, ID_OPERARIO, ID_USUARIO, fecha=FECHA
        )

        self.assertEqual(ctx["id_turno"], 1)
        self.assertFalse(ctx["multi_turno"])
        mock_resolver.assert_called_with(EMPRESA, ID_OPERARIO, FECHA, 1)

    @PATCH_BLOQUEO
    @patch("mpr.repositories.parte_movil.crear_o_actualizar_parte_movil", return_value=(99, "uuid"))
    @patch("mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[1, 2])
    def test_registrar_parte_usa_turno_indicado(self, _mock_turnos, mock_crear, *_rest):
        ok, error, id_parte = registrar_parte_movil(
            EMPRESA,
            ID_OPERARIO,
            "Operario Test",
            ID_USUARIO,
            [{"id_articulo": 1, "id_maquina": 2, "docenas": 1, "pares": 0}],
            fecha=FECHA,
            id_turno=2,
        )
        self.assertTrue(ok, error)
        self.assertEqual(id_parte, 99)
        self.assertEqual(mock_crear.call_args.kwargs["id_mpr_turno"], 2)
