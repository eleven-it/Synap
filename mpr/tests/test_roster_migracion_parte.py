"""Guardrails y migración no física al reasignar el roster."""
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.repositories.parte import migrar_lineas_operario_entre_turnos
from mpr.services import (
    _motivo_bloqueo_cambio_roster,
    asignar_turno_roster,
    asignar_turno_roster_rango,
    eliminar_asignacion_roster,
)


EMPRESA = "EmpresaTest"
FECHA = date(2026, 8, 4)


class TestGuardrailRosterConBorradores(SimpleTestCase):
    def _estado(self, *, lineas=False, duro=False, borrador=False):
        return {
            "tiene_lineas": lineas,
            "tiene_aprobado_o_fisico": duro,
            "tiene_borrador_o_pendiente": borrador,
        }

    def test_asignar_segundo_turno_no_migra_borrador(self):
        """Multi-turno: agregar T2 no migra borrador de T1 automáticamente."""
        turno = MagicMock(id=2)
        with patch("mpr.services.obtener_turno", return_value=turno), patch(
            "mpr.services.obtener_operario", return_value={"id_sue_abm_empleado": 7}
        ), patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch(
            "mpr.services._motivo_bloqueo_cambio_roster", return_value=None
        ), patch(
            "mpr.repositories.parte.migrar_lineas_operario_entre_turnos"
        ) as migrar, patch("mpr.repositories.turno_roster.upsert_roster") as upsert:
            ok, error = asignar_turno_roster(EMPRESA, "04/08/2026", 7, 2)

        self.assertTrue(ok, error)
        migrar.assert_not_called()
        upsert.assert_called_once()

    def test_quitar_borrador_rechaza_y_pide_reasignar(self):
        with patch(
            "mpr.repositories.parte.operario_estado_produccion_roster",
            return_value=self._estado(lineas=True, borrador=True),
        ), patch(
            "mpr.repositories.transicion_lote.operario_tiene_control_calidad_fecha_turno",
            return_value=False,
        ):
            motivo = _motivo_bloqueo_cambio_roster(EMPRESA, FECHA, 7, 1, None)
        self.assertIn("Reasigná a otro turno", motivo)

    def test_aprobado_bloquea_reasignar_y_quitar(self):
        with patch(
            "mpr.repositories.parte.operario_estado_produccion_roster",
            return_value=self._estado(lineas=True, duro=True),
        ), patch(
            "mpr.repositories.transicion_lote.operario_tiene_control_calidad_fecha_turno",
            return_value=False,
        ):
            self.assertIn(
                "aprobado o con movimiento físico",
                _motivo_bloqueo_cambio_roster(EMPRESA, FECHA, 7, 1, 2),
            )
            self.assertIn(
                "aprobado o con movimiento físico",
                _motivo_bloqueo_cambio_roster(EMPRESA, FECHA, 7, 1, None),
            )

    def test_cc_confirmado_bloquea_reasignar(self):
        with patch(
            "mpr.repositories.parte.operario_estado_produccion_roster",
            return_value=self._estado(),
        ), patch(
            "mpr.repositories.transicion_lote.operario_tiene_control_calidad_fecha_turno",
            return_value=True,
        ):
            motivo = _motivo_bloqueo_cambio_roster(EMPRESA, FECHA, 7, 1, 2)
        self.assertIn("control de calidad", motivo)

    def test_mismo_turno_con_borrador_no_migra(self):
        turno = MagicMock(id=1)
        with patch("mpr.services.obtener_turno", return_value=turno), patch(
            "mpr.services.obtener_operario", return_value={"id_sue_abm_empleado": 7}
        ), patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=True
        ), patch(
            "mpr.services._motivo_bloqueo_cambio_roster", return_value=None
        ), patch(
            "mpr.repositories.parte.migrar_lineas_operario_entre_turnos"
        ) as migrar, patch("mpr.repositories.turno_roster.upsert_roster"):
            ok, error = asignar_turno_roster(EMPRESA, "04/08/2026", 7, 1)
        self.assertTrue(ok, error)
        migrar.assert_not_called()

    def test_asignar_desde_vacio_con_solo_cabecera_no_migra(self):
        turno = MagicMock(id=2)
        with patch("mpr.services.obtener_turno", return_value=turno), patch(
            "mpr.services.obtener_operario", return_value={"id_sue_abm_empleado": 7}
        ), patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch(
            "mpr.services._motivo_bloqueo_cambio_roster", return_value=None
        ), patch(
            "mpr.repositories.parte.migrar_lineas_operario_entre_turnos"
        ) as migrar, patch("mpr.repositories.turno_roster.upsert_roster") as upsert:
            ok, error = asignar_turno_roster(EMPRESA, "04/08/2026", 7, 2)
        self.assertTrue(ok, error)
        migrar.assert_not_called()
        upsert.assert_called_once()

    def test_eliminar_aprobado_rechaza(self):
        with patch(
            "mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[1]
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value="bloqueado"):
            ok, error = eliminar_asignacion_roster(EMPRESA, "04/08/2026", 7)
        self.assertFalse(ok)
        self.assertEqual(error, "bloqueado")

    def test_rango_omite_solo_bloqueo_duro(self):
        turno = MagicMock(id=2)
        with patch("mpr.services.obtener_turno", return_value=turno), patch(
            "mpr.services.obtener_operario", return_value={"id_sue_abm_empleado": 7}
        ), patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch(
            "mpr.services._motivo_bloqueo_cambio_roster", side_effect=[None, "bloqueado"]
        ), patch("mpr.repositories.turno_roster.upsert_roster") as upsert:
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA, [7], 2, FECHA, date(2026, 8, 5)
            )
        self.assertTrue(ok, error)
        self.assertEqual(resumen["aplicados"], 1)
        self.assertEqual(resumen["omitidos_bloqueados"], 1)
        upsert.assert_called_once()


class TestMultiTurnoBloqueoPorTurno(SimpleTestCase):
    """Bloqueo duro en un turno no afecta al otro turno del mismo día."""

    def test_bloqueo_manana_no_bloquea_tarde(self):
        from mpr.services import _motivo_bloqueo_roster_celda

        with patch(
            "mpr.repositories.parte.operario_estado_produccion_roster",
            side_effect=lambda _b, _f, _op, tid: {
                "tiene_aprobado_o_fisico": tid == 1,
                "tiene_borrador_o_pendiente": False,
                "tiene_lineas": tid == 1,
            },
        ), patch(
            "mpr.repositories.transicion_lote.operario_tiene_control_calidad_fecha_turno",
            return_value=False,
        ):
            self.assertIsNotNone(_motivo_bloqueo_roster_celda(EMPRESA, FECHA, 7, 1))
            self.assertIsNone(_motivo_bloqueo_roster_celda(EMPRESA, FECHA, 7, 2))

    def test_migracion_borrador_t_a_t_prima_ok(self):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [
                {
                    "id_mpr_parte": 10,
                    "id_usuario": 3,
                    "origen": "movil_operario",
                    "estado": "borrador",
                    "movimiento_fisico_ok": 0,
                }
            ],
            [],
        ]
        cursor.fetchone.return_value = None
        cursor.rowcount = 0
        conexion = MagicMock()
        conexion.cursor.return_value = cursor

        with patch("mpr.repositories.parte.get_mysql_connection") as get_conexion, patch(
            "mpr.repositories.clasificacion_borrador.migrar_borrador_operario_entre_turnos",
            return_value=0,
        ):
            get_conexion.return_value.__enter__.return_value = conexion
            ok, error, resumen = migrar_lineas_operario_entre_turnos(
                EMPRESA, FECHA, 7, 1, 2
            )

        self.assertTrue(ok, error)
        self.assertGreaterEqual(resumen.get("lineas_movidas", 0), 0)


class TestMigracionParteSinStock(SimpleTestCase):
    def test_conflicto_destino_fusiona_declarada_sin_crear_stock(self):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [
                {
                    "id_mpr_parte": 10,
                    "id_usuario": 3,
                    "origen": "movil_operario",
                    "estado": "pendiente",
                    "movimiento_fisico_ok": 0,
                }
            ],
            [
                {
                    "id_mpr_parte_linea": 100,
                    "id_articulo": 20,
                    "id_mpr_maquina": 4,
                    "cantidad": 0,
                    "cantidad_declarada": 12,
                }
            ],
        ]
        cursor.fetchone.side_effect = [
            {"id_mpr_parte": 11},
            {"id_mpr_parte_linea": 101},
            {"cantidad": 0},  # destino sin cantidad física
            None,  # sin ajuste físico
        ]
        cursor.rowcount = 0
        conexion = MagicMock()
        conexion.cursor.return_value = cursor

        with patch("mpr.repositories.parte.get_mysql_connection") as get_conexion, patch(
            "mpr.repositories.clasificacion_borrador.migrar_borrador_operario_entre_turnos",
            return_value=0,
        ):
            get_conexion.return_value.__enter__.return_value = conexion
            ok, error, resumen = migrar_lineas_operario_entre_turnos(
                EMPRESA, FECHA, 7, 1, 2
            )

        self.assertTrue(ok, error)
        self.assertEqual(resumen["lineas_combinadas"], 1)
        sql_ejecutado = " ".join(str(call.args[0]).lower() for call in cursor.execute.call_args_list)
        self.assertIn("cantidad_declarada = coalesce(cantidad_declarada, 0) + %s", sql_ejecutado)
        self.assertNotIn("movimiento_stock", sql_ejecutado)
        self.assertNotIn("mstock", sql_ejecutado)

    def test_migracion_vacia_no_emite_operaciones_stock(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        conexion = MagicMock()
        conexion.cursor.return_value = cursor

        with patch("mpr.repositories.parte.get_mysql_connection") as get_conexion:
            get_conexion.return_value.__enter__.return_value = conexion
            ok, error, resumen = migrar_lineas_operario_entre_turnos(
                EMPRESA, FECHA, 7, 1, 2
            )

        self.assertTrue(ok, error)
        self.assertEqual(resumen["lineas_movidas"], 0)
        sql_ejecutado = " ".join(str(call.args[0]).lower() for call in cursor.execute.call_args_list)
        self.assertNotIn("movimiento_stock", sql_ejecutado)
        self.assertNotIn("mstock", sql_ejecutado)
