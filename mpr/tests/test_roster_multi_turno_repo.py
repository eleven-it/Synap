# -*- coding: utf-8 -*-
"""Tests Fase 2: repo multi-turno, override por turno, listar_roster_semana."""
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services import (
    asignar_turno_roster,
    eliminar_asignacion_roster,
    listar_roster_semana,
    set_linea_override_roster,
)
from mpr.services_operario import resolver_linea_operario

EMPRESA = "EmpresaTest"
FECHA = date(2026, 8, 4)
FECHA_STR = "04/08/2026"


class TestRepoMultiTurno(SimpleTestCase):
    """Repositorio turno_roster: turnos_del_operario_dia, override, delete por turno."""

    @patch("mpr.repositories.turno_roster.mysql_cursor")
    def test_turnos_del_operario_dia_devuelve_lista(self, mock_ctx):
        from mpr.repositories import turno_roster as repo

        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"id_mpr_turno": 1},
            {"id_mpr_turno": 2},
        ]
        mock_ctx.return_value.__enter__.return_value = cursor

        turnos = repo.turnos_del_operario_dia(EMPRESA, 7, FECHA)

        self.assertEqual(turnos, [1, 2])
        sql = cursor.execute.call_args[0][0].lower()
        self.assertNotIn("limit 1", sql)

    @patch("mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[1, 2])
    def test_turno_del_operario_dia_compat_primer_turno(self, mock_turnos):
        from mpr.repositories import turno_roster as repo

        self.assertEqual(repo.turno_del_operario_dia(EMPRESA, 7, FECHA), 1)
        mock_turnos.assert_called_once()

    @patch("mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[])
    def test_turno_del_operario_dia_none_si_vacio(self, _mock_turnos):
        from mpr.repositories import turno_roster as repo

        self.assertIsNone(repo.turno_del_operario_dia(EMPRESA, 7, FECHA))

    @patch("mpr.repositories.turno_roster.mysql_cursor")
    def test_override_linea_filtra_por_turno(self, mock_ctx):
        from mpr.repositories import turno_roster as repo

        cursor = MagicMock()
        cursor.fetchone.return_value = {"id_mpr_linea": 5}
        mock_ctx.return_value.__enter__.return_value = cursor

        linea = repo.override_linea_roster(EMPRESA, FECHA, 7, id_mpr_turno=2)

        self.assertEqual(linea, 5)
        sql, params = cursor.execute.call_args[0]
        self.assertIn("id_mpr_turno = %s", sql)
        self.assertEqual(params, [FECHA, 7, 2])

    @patch("mpr.repositories.turno_roster.mysql_cursor")
    def test_eliminar_roster_turno_solo_un_turno(self, mock_ctx):
        from mpr.repositories import turno_roster as repo

        cursor = MagicMock()
        cursor.rowcount = 1
        mock_ctx.return_value.__enter__.return_value = cursor

        n = repo.eliminar_roster_turno(EMPRESA, FECHA, 7, 2)

        self.assertEqual(n, 1)
        sql, params = cursor.execute.call_args[0]
        self.assertIn("id_mpr_turno = %s", sql)
        self.assertEqual(params[-1], 2)


class TestResolverLineaPorTurno(SimpleTestCase):
    @patch("mpr.repositories.turno_roster.override_linea_roster", return_value=99)
    @patch("mpr.services_operario.linea_habitual_operario")
    def test_resolver_pasa_id_turno_al_override(self, mock_hab, mock_override):
        resolver_linea_operario(EMPRESA, 7, FECHA, id_turno=2)
        mock_override.assert_called_once_with(EMPRESA, FECHA, 7, id_mpr_turno=2)
        mock_hab.assert_not_called()

    @patch("mpr.repositories.turno_roster.override_linea_roster", return_value=None)
    @patch("mpr.services_operario.linea_habitual_operario", return_value=3)
    def test_resolver_sin_override_usa_habitual(self, mock_hab, mock_override):
        lid = resolver_linea_operario(EMPRESA, 7, FECHA, id_turno=1)
        self.assertEqual(lid, 3)
        mock_override.assert_called_once_with(EMPRESA, FECHA, 7, id_mpr_turno=1)


class TestSetLineaOverrideRoster(SimpleTestCase):
    def test_bloquea_si_parte_aprobado(self):
        msg = "No se puede modificar: el operario tiene un parte aprobado"
        with patch("mpr.services.obtener_operario", return_value={"id": 7}), patch(
            "mpr.repositories.maquina_linea.obtener_linea",
            return_value={"activo": True},
        ), patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=True
        ), patch("mpr.services._motivo_bloqueo_roster_celda", return_value=msg):
            ok, error = set_linea_override_roster(EMPRESA, FECHA_STR, 7, 1, id_linea=2)
        self.assertFalse(ok)
        self.assertEqual(error, msg)

    def test_clear_override_a_null(self):
        with patch("mpr.services.obtener_operario", return_value={"id": 7}), patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=True
        ), patch("mpr.services._motivo_bloqueo_roster_celda", return_value=None), patch(
            "mpr.repositories.turno_roster.update_roster_linea", return_value=1
        ) as mock_upd:
            ok, error = set_linea_override_roster(EMPRESA, FECHA_STR, 7, 1, id_linea=None)
        self.assertTrue(ok, error)
        mock_upd.assert_called_once_with(EMPRESA, FECHA, 7, 1, None)

    def test_rechaza_sin_turno_asignado(self):
        with patch("mpr.services.obtener_operario", return_value={"id": 7}), patch(
            "mpr.repositories.maquina_linea.obtener_linea",
            return_value={"activo": True},
        ), patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ):
            ok, error = set_linea_override_roster(EMPRESA, FECHA_STR, 7, 1, id_linea=2)
        self.assertFalse(ok)
        self.assertIn("no tiene ese turno", error.lower())


class TestListarRosterSemanaMultiTurno(SimpleTestCase):
    def test_payload_lista_turnos_por_celda(self):
        fecha_lunes = date(2026, 8, 3)
        filas = [
            {
                "fecha": date(2026, 8, 4),
                "id_operario": 7,
                "id_mpr_turno": 1,
                "nombre_turno": "Mañana",
                "id_mpr_linea": 10,
                "nombre_linea": "Fila 1",
            },
            {
                "fecha": date(2026, 8, 4),
                "id_operario": 7,
                "id_mpr_turno": 2,
                "nombre_turno": "Tarde",
                "id_mpr_linea": None,
                "nombre_linea": None,
            },
        ]
        with patch("mpr.services.listar_empleados_operarios", return_value=[{"id": 7, "label": "Op"}]), patch(
            "mpr.repositories.turno_roster.listar_roster_rango", return_value=filas
        ), patch(
            "mpr.services._mapa_celdas_bloqueadas_roster", return_value={}
        ), patch(
            "mpr.services_operario.resolver_linea_operario", side_effect=[10, 20]
        ):
            data = listar_roster_semana(EMPRESA, fecha_lunes)

        turnos = data["asignaciones"][7]["2026-08-04"]
        self.assertIsInstance(turnos, list)
        self.assertEqual(len(turnos), 2)
        self.assertEqual(turnos[0]["id_turno"], 1)
        self.assertEqual(turnos[0]["id_linea_override"], 10)
        self.assertEqual(turnos[0]["id_linea_efectiva"], 10)
        self.assertEqual(turnos[1]["id_turno"], 2)
        self.assertEqual(turnos[1]["id_linea_efectiva"], 20)
        self.assertFalse(turnos[1]["bloqueada"])


class TestAsignarMultiTurno(SimpleTestCase):
    def test_segundo_turno_inserta_sin_migrar(self):
        turno = MagicMock(id=2)
        with patch("mpr.services.obtener_turno", return_value=turno), patch(
            "mpr.services.obtener_operario", return_value={"id": 7}
        ), patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.parte.migrar_lineas_operario_entre_turnos"
        ) as migrar, patch("mpr.repositories.turno_roster.upsert_roster") as upsert:
            ok, error = asignar_turno_roster(EMPRESA, FECHA_STR, 7, 2)
        self.assertTrue(ok, error)
        migrar.assert_not_called()
        upsert.assert_called_once()

    def test_eliminar_requiere_turno_si_hay_varios(self):
        with patch(
            "mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[1, 2]
        ):
            ok, error = eliminar_asignacion_roster(EMPRESA, FECHA_STR, 7)
        self.assertFalse(ok)
        self.assertIn("varios turnos", error.lower())

    def test_eliminar_por_turno_usa_eliminar_roster_turno(self):
        with patch(
            "mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[1, 2]
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.eliminar_roster_turno", return_value=1
        ) as mock_del:
            ok, error = eliminar_asignacion_roster(EMPRESA, FECHA_STR, 7, id_turno=2)
        self.assertTrue(ok, error)
        mock_del.assert_called_once_with(EMPRESA, FECHA, 7, 2)
