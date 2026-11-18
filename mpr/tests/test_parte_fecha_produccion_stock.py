"""Los asientos de stock de partes se fechan con la fecha de producción del parte.

Regresión: ``_registrar_asiento_fisico_opp_parte`` y ``_registrar_delta_stock_ajuste``
usaban ``date.today()`` (fecha de aprobación) en lugar de ``parte.fecha_produccion``.
Un parte producido el 09/09 y aprobado después debe generar un movimiento del 09/09.
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from mpr import services

FECHA_PROD = date(2026, 9, 9)
FECHA_APROBACION = date(2026, 10, 29)


class _FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((" ".join(str(sql).split()), list(params or [])))
        self._last = str(sql)

    def fetchone(self):
        s = self._last
        if "CodigoMovimiento FROM" in s:
            return (100,)
        if "FROM talonarios" in s or "Orden, Nro" in s:
            return (1, 7)
        if "FROM stock_deposito" in s:
            return None
        return None

    def fetchall(self):
        return []


class _FakeConn:
    def __init__(self):
        self.cur = _FakeCursor()

    def autocommit(self, v):
        pass

    def cursor(self):
        return self.cur

    def commit(self):
        pass

    def rollback(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeDate(date):
    @classmethod
    def today(cls):
        return FECHA_APROBACION


def _fechas_insertadas(cursor):
    """Fechas ISO presentes en los INSERT ejecutados (movimiento_stock y stock)."""
    fechas = set()
    for sql, params in cursor.executed:
        if sql.startswith("INSERT INTO movimiento_stock") or sql.startswith("INSERT INTO stock "):
            fechas.update(p for p in params if isinstance(p, str) and len(p) == 10 and p[4] == "-")
    return fechas


def _patches(conn):
    return [
        patch("mpr.services.get_connection", return_value=conn),
        patch("mpr.services._nombre_tabla", side_effect=lambda c, n: n),
        patch("mpr.services._escribir_historico_opp_parte"),
        patch("mpr.services.texto_detalle_parte_produccion", return_value="det"),
        patch("mpr.services.date", _FakeDate),
    ]


class TestAsientoOppParteFechaProduccion(SimpleTestCase):
    def test_parte_producido_0909_aprobado_despues_fecha_0909(self):
        conn = _FakeConn()
        parte = SimpleNamespace(id_mpr_parte=1, fecha_produccion=FECHA_PROD, turno_id=None)
        ps = _patches(conn)
        for p in ps:
            p.start()
        try:
            services._registrar_asiento_fisico_opp_parte(
                "db", 1, parte, [({"id_articulo": 10}, 5)], 3, ya_componentes=True
            )
        finally:
            for p in ps:
                p.stop()
        fechas = _fechas_insertadas(conn.cur)
        self.assertEqual(fechas, {"2026-09-09"})


class TestDeltaAjusteFechaProduccion(SimpleTestCase):
    def test_delta_con_fecha_parte_usa_fecha_produccion(self):
        conn = _FakeConn()
        ps = _patches(conn)
        for p in ps:
            p.start()
        try:
            services._registrar_delta_stock_ajuste(
                "db", 1, 10, Decimal("2"), 3, fecha=FECHA_PROD
            )
        finally:
            for p in ps:
                p.stop()
        self.assertEqual(_fechas_insertadas(conn.cur), {"2026-09-09"})

    def test_agregar_ajuste_pasa_fecha_produccion_del_parte(self):
        """El call site de ajuste pasa la fecha de producción del parte."""
        import inspect

        src = inspect.getsource(services)
        self.assertNotIn("fecha_mov = date.today().isoformat()\n    detalle_mov = \"Ajuste", src)
        self.assertEqual(src.count("fecha=_fecha_parte_date(parte)"), 2)
