"""Tests repositorios MPR MySQL (turnos, parte, transición)."""
import uuid
from datetime import date
from decimal import Decimal

from django.test import TestCase

from mpr.repositories.parte import crear_parte_con_lineas, opp_acumulado_por_pack
from mpr.repositories.transicion_lote import crear_transicion_lote, listar_por_articulo
from mpr.repositories.turno_roster import (
    crear_turno_mysql,
    eliminar_roster,
    listar_turnos_dict,
    upsert_roster,
)

MYSQL_EMPRESA = "administranet93"
TURNO_TEST = "TurnoTestMySQLRepo"


class TestTurnoParteRepositoryMySQL(TestCase):
    def setUp(self):
        from mpr.db import mysql_cursor

        with mysql_cursor(MYSQL_EMPRESA) as c:
            c.execute("DELETE FROM mpr_roster_dia WHERE id_operario = %s", [888001])
            c.execute("DELETE FROM mpr_parte WHERE uuid_parte LIKE %s", ["00000000-0000-4000-8000-%"])

    def tearDown(self):
        from mpr.db import mysql_cursor

        with mysql_cursor(MYSQL_EMPRESA) as c:
            c.execute("DELETE FROM mpr_roster_dia WHERE id_operario = %s", [888001])
            c.execute(
                "DELETE FROM mpr_parte_linea WHERE id_mpr_parte IN "
                "(SELECT id_mpr_parte FROM mpr_parte WHERE uuid_parte LIKE %s)",
                ["00000000-0000-4000-8000-%"],
            )
            c.execute("DELETE FROM mpr_parte WHERE uuid_parte LIKE %s", ["00000000-0000-4000-8000-%"])
            c.execute("DELETE FROM mpr_turno WHERE nombre = %s", [TURNO_TEST])
            c.execute("DELETE FROM mpr_transicion_lote WHERE id_articulo = %s", [999003])

    def test_turno_roster_y_parte(self):
        id_turno = crear_turno_mysql(MYSQL_EMPRESA, TURNO_TEST, "08:00", "16:00")
        self.assertGreater(id_turno, 0)
        turnos = listar_turnos_dict(MYSQL_EMPRESA, solo_activos=True)
        self.assertTrue(any(t["nombre"] == TURNO_TEST for t in turnos))

        upsert_roster(MYSQL_EMPRESA, date(2099, 1, 15), 888001, id_turno)
        self.assertEqual(eliminar_roster(MYSQL_EMPRESA, date(2099, 1, 15), 888001), 1)

        uid = "00000000-0000-4000-8000-" + format(uuid.uuid4().int & 0xFFFFFFFFFFFF, "012x")
        parte = crear_parte_con_lineas(
            MYSQL_EMPRESA,
            date(2099, 1, 10),
            id_turno,
            1,
            [{"id_articulo": 999002, "id_operario": 1, "cantidad": Decimal("3"), "operario_nombre": "Op"}],
            uuid_parte=uid,
        )
        self.assertEqual(parte.uuid_parte, uid)
        acum = opp_acumulado_por_pack(MYSQL_EMPRESA, [999002])
        self.assertEqual(acum.get(999002), Decimal("3"))

    def test_transicion_lote(self):
        tid = crear_transicion_lote(
            MYSQL_EMPRESA,
            999003,
            "Produccion",
            "Planchado",
            Decimal("2"),
            12345,
            1,
        )
        self.assertGreater(tid, 0)
        rows = listar_por_articulo(MYSQL_EMPRESA, 999003)
        self.assertTrue(any(r["codigo_movimiento"] == 12345 for r in rows))
