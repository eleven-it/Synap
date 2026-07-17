"""
Tests para Etapa 3 MPR: Turnos (CRUD) + Roster Rotativo (Planificación Manual).

Cobertura:
- Modelos: unicidad, on_delete PROTECT, turno nocturno válido.
- Servicios: crear turno válido/inválido, toggle, asignar fecha futura/pasada,
  reasignación (update, no duplica), eliminar asignación.
"""
from datetime import date, time, timedelta

from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from mpr.models import MprRosterDia, MprTurno
from mpr.templatetags.mpr_filters import turno_color
from mpr.services import (
    actualizar_turno,
    asignar_turno_roster,
    asignar_turno_roster_rango,
    crear_turno,
    eliminar_asignacion_roster,
    listar_turnos,
    obtener_turno,
    toggle_turno_activo,
)

EMPRESA = "EmpresaTest"
EMPRESA_2 = "EmpresaTest2"


def _crear_turno_db(empresa=EMPRESA, nombre="Mañana", h_ini="06:00", h_fin="14:00"):
    """Helper: crea MprTurno directamente en DB y lo retorna."""
    return MprTurno.objects.create(
        base_empresa=empresa,
        nombre=nombre,
        hora_inicio=time(int(h_ini.split(":")[0]), int(h_ini.split(":")[1])),
        hora_fin=time(int(h_fin.split(":")[0]), int(h_fin.split(":")[1])),
        activo=True,
    )


class TestModeloMprTurno(TestCase):
    """Tests de modelo MprTurno: constraints, índices, turno nocturno."""

    def test_turno_nombre_unico_por_empresa(self):
        """Nombre único por empresa: duplicado en misma empresa lanza IntegrityError."""
        _crear_turno_db(nombre="Mañana")
        with self.assertRaises(IntegrityError):
            _crear_turno_db(nombre="Mañana")

    def test_turno_nombre_unico_permite_mismo_nombre_otra_empresa(self):
        """Mismo nombre en empresa diferente es válido."""
        _crear_turno_db(empresa=EMPRESA, nombre="Tarde")
        t2 = _crear_turno_db(empresa=EMPRESA_2, nombre="Tarde")
        self.assertIsNotNone(t2.pk)

    def test_turno_nocturno_valido(self):
        """Turno nocturno (hora_fin < hora_inicio) se guarda sin error."""
        turno = _crear_turno_db(nombre="Noche", h_ini="22:00", h_fin="06:00")
        self.assertIsNotNone(turno.pk)
        self.assertEqual(turno.hora_inicio, time(22, 0))
        self.assertEqual(turno.hora_fin, time(6, 0))
        self.assertLess(turno.hora_fin, turno.hora_inicio)

    def test_str_turno(self):
        """__str__ muestra horario correcto."""
        turno = _crear_turno_db(nombre="Tarde", h_ini="14:00", h_fin="22:00")
        self.assertIn("Tarde", str(turno))
        self.assertIn("14:00", str(turno))
        self.assertIn("22:00", str(turno))


class TestModeloMprRosterDia(TestCase):
    """Tests de modelo MprRosterDia: constraints, on_delete PROTECT."""

    def setUp(self):
        self.turno1 = _crear_turno_db(nombre="Mañana")
        self.turno2 = _crear_turno_db(nombre="Tarde", h_ini="14:00", h_fin="22:00")
        self.fecha_futura = date.today() + timedelta(days=5)

    def test_roster_constraint_unico_operario_fecha(self):
        """Unicidad (base_empresa, fecha, id_operario): segunda asignación lanza IntegrityError."""
        MprRosterDia.objects.create(
            base_empresa=EMPRESA,
            fecha=self.fecha_futura,
            id_operario=123,
            turno=self.turno1,
        )
        with self.assertRaises(IntegrityError):
            MprRosterDia.objects.create(
                base_empresa=EMPRESA,
                fecha=self.fecha_futura,
                id_operario=123,
                turno=self.turno2,
            )

    def test_roster_on_delete_protect(self):
        """No se puede eliminar un turno que tiene asignaciones en roster (on_delete=PROTECT)."""
        MprRosterDia.objects.create(
            base_empresa=EMPRESA,
            fecha=self.fecha_futura,
            id_operario=456,
            turno=self.turno1,
        )
        with self.assertRaises(ProtectedError):
            self.turno1.delete()


class TestServiciosTurnos(TestCase):
    """Tests de servicios CRUD de turnos."""

    def test_crear_turno_valido(self):
        """crear_turno con datos válidos retorna (True, id, None)."""
        ok, id_turno, error = crear_turno(EMPRESA, "Mañana", "06:00", "14:00")
        self.assertTrue(ok)
        self.assertIsNotNone(id_turno)
        self.assertIsNone(error)
        self.assertTrue(MprTurno.objects.filter(id=id_turno).exists())

    def test_crear_turno_hora_inicio_igual_fin(self):
        """crear_turno con hora_inicio == hora_fin retorna (False, None, mensaje)."""
        ok, id_turno, error = crear_turno(EMPRESA, "Inválido", "08:00", "08:00")
        self.assertFalse(ok)
        self.assertIsNone(id_turno)
        self.assertIn("iguales", error)

    def test_crear_turno_nombre_duplicado(self):
        """crear_turno con nombre duplicado en misma empresa retorna (False, None, mensaje)."""
        crear_turno(EMPRESA, "Tarde", "14:00", "22:00")
        ok, id_turno, error = crear_turno(EMPRESA, "Tarde", "14:00", "22:00")
        self.assertFalse(ok)
        self.assertIsNone(id_turno)
        self.assertIsNotNone(error)

    def test_crear_turno_nocturno_valido(self):
        """crear_turno nocturno (hora_fin < hora_inicio) se crea exitosamente."""
        ok, id_turno, error = crear_turno(EMPRESA, "Noche", "22:00", "06:00")
        self.assertTrue(ok)
        self.assertIsNotNone(id_turno)
        self.assertIsNone(error)

    def test_actualizar_turno(self):
        """actualizar_turno cambia nombre y horas correctamente."""
        ok, id_turno, _ = crear_turno(EMPRESA, "Mañana", "06:00", "14:00")
        ok2, error = actualizar_turno(EMPRESA, id_turno, "Mañana V2", "07:00", "15:00")
        self.assertTrue(ok2)
        self.assertIsNone(error)
        turno = obtener_turno(EMPRESA, id_turno)
        self.assertEqual(turno.nombre, "Mañana V2")

    def test_toggle_turno_activo(self):
        """toggle_turno_activo cambia estado activo/inactivo."""
        ok, id_turno, _ = crear_turno(EMPRESA, "Tarde", "14:00", "22:00")
        turno = obtener_turno(EMPRESA, id_turno)
        self.assertTrue(turno.activo)
        ok2, error = toggle_turno_activo(EMPRESA, id_turno, False)
        self.assertTrue(ok2)
        self.assertIsNone(error)
        turno.refresh_from_db()
        self.assertFalse(turno.activo)

    def test_listar_turnos_solo_activos(self):
        """listar_turnos(solo_activos=True) excluye turnos inactivos."""
        crear_turno(EMPRESA, "Activo", "06:00", "14:00")
        ok, id_inactivo, _ = crear_turno(EMPRESA, "Inactivo", "14:00", "22:00")
        toggle_turno_activo(EMPRESA, id_inactivo, False)
        lista = listar_turnos(EMPRESA, solo_activos=True)
        nombres = [t["nombre"] for t in lista]
        self.assertIn("Activo", nombres)
        self.assertNotIn("Inactivo", nombres)


class TestServiciosRoster(TestCase):
    """Tests de servicios de roster (asignación/eliminación)."""

    def setUp(self):
        self.turno = _crear_turno_db(nombre="Mañana")
        self.turno2 = _crear_turno_db(nombre="Tarde", h_ini="14:00", h_fin="22:00")
        self.fecha_futura = date.today() + timedelta(days=3)
        self.fecha_futura_str = self.fecha_futura.strftime("%d/%m/%Y")
        self.fecha_ayer = date.today() - timedelta(days=1)
        self.fecha_ayer_str = self.fecha_ayer.strftime("%d/%m/%Y")

    def test_asignar_turno_fecha_pasada_rechazado(self):
        """asignar_turno_roster con fecha ayer retorna (False, mensaje_pasado)."""
        ok, error = asignar_turno_roster(EMPRESA, self.fecha_ayer_str, 999, self.turno.id)
        self.assertFalse(ok)
        self.assertIn("pasadas", error)

    def test_eliminar_asignacion_fecha_pasada_rechazada(self):
        """eliminar_asignacion_roster con fecha ayer retorna (False, mensaje_pasado)."""
        ok, error = eliminar_asignacion_roster(EMPRESA, self.fecha_ayer_str, 999)
        self.assertFalse(ok)
        self.assertIn("pasadas", error)

    def test_asignar_turno_reasignacion_no_duplica(self):
        """Reasignar mismo operario/fecha actualiza el turno (update_or_create), no duplica."""
        from unittest.mock import patch
        fecha_str = self.fecha_futura_str
        id_op = 101

        with patch("mpr.services.obtener_operario") as mock_op:
            mock_op.return_value = {"id_sue_abm_empleado": id_op, "nombre_empleado": "Operario Uno"}
            ok1, err1 = asignar_turno_roster(EMPRESA, fecha_str, id_op, self.turno.id)
            self.assertTrue(ok1, err1)

            ok2, err2 = asignar_turno_roster(EMPRESA, fecha_str, id_op, self.turno2.id)
            self.assertTrue(ok2, err2)

        total = MprRosterDia.objects.filter(
            base_empresa=EMPRESA,
            fecha=self.fecha_futura,
            id_operario=id_op,
        ).count()
        self.assertEqual(total, 1, "Debe existir solo UNA asignación (update, no duplicado)")

        asig = MprRosterDia.objects.get(
            base_empresa=EMPRESA,
            fecha=self.fecha_futura,
            id_operario=id_op,
        )
        self.assertEqual(asig.turno.id, self.turno2.id, "La asignación debe tener el turno2 (reasignado)")

    def test_asignar_turno_fecha_futura_ok(self):
        """asignar_turno_roster con fecha futura y operario mock retorna (True, None)."""
        from unittest.mock import patch
        with patch("mpr.services.obtener_operario") as mock_op:
            mock_op.return_value = {"id_sue_abm_empleado": 200, "nombre_empleado": "Test Op"}
            ok, error = asignar_turno_roster(EMPRESA, self.fecha_futura_str, 200, self.turno.id)
        self.assertTrue(ok, error)
        self.assertIsNone(error)

    def test_eliminar_asignacion_existente(self):
        """eliminar_asignacion_roster elimina correctamente una asignación futura."""
        fecha = self.fecha_futura
        MprRosterDia.objects.create(
            base_empresa=EMPRESA,
            fecha=fecha,
            id_operario=300,
            turno=self.turno,
        )
        ok, error = eliminar_asignacion_roster(EMPRESA, self.fecha_futura_str, 300)
        self.assertTrue(ok, error)
        self.assertFalse(
            MprRosterDia.objects.filter(
                base_empresa=EMPRESA, fecha=fecha, id_operario=300
            ).exists()
        )

    def test_eliminar_asignacion_inexistente(self):
        """eliminar_asignacion_roster sobre asignación inexistente retorna (False, mensaje)."""
        ok, error = eliminar_asignacion_roster(EMPRESA, self.fecha_futura_str, 9999)
        self.assertFalse(ok)
        self.assertIsNotNone(error)


class TestAsignarTurnoRosterRango(TestCase):
    """Tests de asignación masiva de roster por rango de fechas."""

    def setUp(self):
        self.turno = _crear_turno_db(nombre="Mañana")
        self.turno2 = _crear_turno_db(nombre="Tarde", h_ini="14:00", h_fin="22:00")
        self.hoy = date.today()
        self.manana = self.hoy + timedelta(days=1)
        self.pasado_manana = self.hoy + timedelta(days=2)
        self.ayer = self.hoy - timedelta(days=1)

    def test_rango_futuro_tres_dias_dos_operarios(self):
        """Rango futuro 3 días × 2 operarios → aplicados=6, upsert llamado 6 veces."""
        from unittest.mock import patch

        desde = self.manana
        hasta = self.manana + timedelta(days=2)
        ids_op = [101, 102]

        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch("mpr.repositories.turno_roster.upsert_roster") as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": 101, "nombre_empleado": "Op Test"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA, ids_op, self.turno.id, desde, hasta
            )

        self.assertTrue(ok, error)
        self.assertIsNone(error)
        self.assertEqual(resumen["aplicados"], 6)
        self.assertEqual(resumen["omitidos_pasados"], 0)
        self.assertEqual(mock_upsert.call_count, 6)

    def test_rango_incluye_ayer_omite_pasados(self):
        """Rango con ayer omite fechas pasadas y aplica solo hoy o futuras."""
        from unittest.mock import patch

        desde = self.ayer
        hasta = self.manana

        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch("mpr.repositories.turno_roster.upsert_roster") as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": 200, "nombre_empleado": "Op Uno"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA, [200], self.turno.id, desde, hasta
            )

        self.assertTrue(ok, error)
        self.assertEqual(resumen["omitidos_pasados"], 1)
        dias_editables = 2
        self.assertEqual(resumen["aplicados"], dias_editables)
        self.assertEqual(mock_upsert.call_count, dias_editables)

    def test_desde_posterior_hasta_falla(self):
        """desde > hasta retorna ok=False."""
        desde = self.manana + timedelta(days=5)
        hasta = self.manana
        ok, error, resumen = asignar_turno_roster_rango(
            EMPRESA, [100], self.turno.id, desde, hasta
        )
        self.assertFalse(ok)
        self.assertIn("posterior", error)
        self.assertEqual(resumen["aplicados"], 0)

    def test_turno_invalido_falla(self):
        """Turno inexistente retorna ok=False."""
        from unittest.mock import patch

        with patch("mpr.services.obtener_turno", return_value=None), patch(
            "mpr.services.obtener_operario"
        ) as mock_op:
            mock_op.return_value = {"id_sue_abm_empleado": 100, "nombre_empleado": "Op"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA, [100], 999999, self.manana, self.manana
            )
        self.assertFalse(ok)
        self.assertIn("Turno no encontrado", error)
        self.assertEqual(resumen["aplicados"], 0)

    def test_operarios_vacios_falla(self):
        """Lista vacía de operarios retorna ok=False."""
        ok, error, resumen = asignar_turno_roster_rango(
            EMPRESA, [], self.turno.id, self.manana, self.manana
        )
        self.assertFalse(ok)
        self.assertIn("operario", error.lower())
        self.assertEqual(resumen["aplicados"], 0)

    def test_reasignacion_llama_upsert_sobrescribe(self):
        """Dos llamadas mismo operario/fecha con distinto turno invocan upsert (overwrite)."""
        from unittest.mock import patch

        fecha = self.manana
        id_op = 301

        def _turno_side_effect(base, tid):
            return self.turno if tid == self.turno.id else self.turno2

        with patch("mpr.services.obtener_turno", side_effect=_turno_side_effect), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch("mpr.repositories.turno_roster.upsert_roster") as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": id_op, "nombre_empleado": "Op Reasign"}
            ok1, err1, _ = asignar_turno_roster_rango(
                EMPRESA, [id_op], self.turno.id, fecha, fecha
            )
            ok2, err2, _ = asignar_turno_roster_rango(
                EMPRESA, [id_op], self.turno2.id, fecha, fecha
            )

        self.assertTrue(ok1, err1)
        self.assertTrue(ok2, err2)
        self.assertEqual(mock_upsert.call_count, 2)
        ultima_llamada = mock_upsert.call_args_list[-1]
        self.assertEqual(ultima_llamada[0][3], self.turno2.id)


class TestFiltroTurnoColor(TestCase):
    """Filtro turno_color: slug de color por turno para la grilla de roster."""

    def test_heuristica_por_nombre_con_y_sin_acento(self):
        self.assertEqual(turno_color({"nombre_turno": "Mañana", "id_turno": 1}), "manana")
        self.assertEqual(turno_color({"nombre_turno": "manana", "id_turno": 9}), "manana")
        self.assertEqual(turno_color({"nombre_turno": "Tarde", "id_turno": 2}), "tarde")
        self.assertEqual(turno_color({"nombre_turno": "Noche", "id_turno": 3}), "noche")
        self.assertEqual(turno_color({"nombre_turno": "Nocturno", "id_turno": 4}), "noche")

    def test_fallback_rota_paleta_por_id(self):
        self.assertEqual(turno_color({"nombre_turno": "Especial A", "id_turno": 4}), "p0")
        self.assertEqual(turno_color({"nombre_turno": "Especial B", "id_turno": 5}), "p1")
        self.assertEqual(turno_color({"nombre_turno": "Especial C", "id_turno": 6}), "p2")
        self.assertEqual(turno_color({"nombre_turno": "Especial D", "id_turno": 7}), "p3")

    def test_acepta_dict_de_turno_y_cadena(self):
        # dict de listar_turnos usa claves id/nombre
        self.assertEqual(turno_color({"nombre": "Tarde", "id": 2}), "tarde")
        # cadena simple
        self.assertEqual(turno_color("Noche"), "noche")

    def test_entrada_invalida_no_rompe(self):
        self.assertEqual(turno_color(None), "p0")
        self.assertEqual(turno_color({}), "p0")
