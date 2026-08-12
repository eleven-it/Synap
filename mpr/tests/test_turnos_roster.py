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
from django.test import SimpleTestCase, TestCase

from mpr.models import MprRosterDia, MprTurno
from mpr.templatetags.mpr_filters import turno_color, roster_ids_turno
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

    def test_asignar_turno_fecha_pasada_ok_sin_produccion(self):
        """asignar_turno_roster con fecha ayer OK si no hay parte/CC."""
        from unittest.mock import patch

        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch(
            "mpr.services._motivo_bloqueo_cambio_roster", return_value=None
        ), patch("mpr.repositories.turno_roster.upsert_roster"):
            mock_op.return_value = {"id_sue_abm_empleado": 999, "nombre_empleado": "Op Pasado"}
            ok, error = asignar_turno_roster(EMPRESA, self.fecha_ayer_str, 999, self.turno.id)
        self.assertTrue(ok, error)
        self.assertIsNone(error)

    def test_eliminar_asignacion_fecha_pasada_ok_sin_produccion(self):
        """eliminar_asignacion_roster con fecha ayer OK si no hay parte/CC."""
        from unittest.mock import patch

        with patch(
            "mpr.repositories.turno_roster.turnos_del_operario_dia",
            return_value=[self.turno.id],
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.eliminar_roster_turno", return_value=1
        ):
            ok, error = eliminar_asignacion_roster(EMPRESA, self.fecha_ayer_str, 888)
        self.assertTrue(ok, error)
        self.assertIsNone(error)

    def test_asignar_turno_bloqueado_por_parte(self):
        """asignar_turno_roster rechaza si hay parte en la celda."""
        from unittest.mock import patch

        msg = "No se puede modificar: el operario ya tiene partes registrados en esa fecha y turno."
        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=msg):
            mock_op.return_value = {"id_sue_abm_empleado": 501, "nombre_empleado": "Op Bloq"}
            ok, error = asignar_turno_roster(
                EMPRESA, self.fecha_futura_str, 501, self.turno.id
            )
        self.assertFalse(ok)
        self.assertIn("partes registrados", error)

    def test_asignar_turno_bloqueado_por_cc(self):
        """asignar_turno_roster rechaza si hay CC en la celda."""
        from unittest.mock import patch

        msg = (
            "No se puede modificar: el operario ya tiene control de calidad registrado "
            "en esa fecha y turno."
        )
        with patch("mpr.services.obtener_turno", return_value=self.turno2), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=True
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=msg):
            mock_op.return_value = {"id_sue_abm_empleado": 502, "nombre_empleado": "Op CC"}
            ok, error = asignar_turno_roster(
                EMPRESA, self.fecha_futura_str, 502, self.turno2.id
            )
        self.assertFalse(ok)
        self.assertIn("control de calidad", error)

    def test_eliminar_asignacion_bloqueada_por_parte(self):
        """eliminar_asignacion_roster rechaza si hay parte en el turno asignado."""
        from unittest.mock import patch

        msg = "No se puede modificar: el operario ya tiene partes registrados en esa fecha y turno."
        with patch(
            "mpr.repositories.turno_roster.turnos_del_operario_dia",
            return_value=[self.turno.id],
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=msg):
            ok, error = eliminar_asignacion_roster(
                EMPRESA, self.fecha_futura_str, 503
            )
        self.assertFalse(ok)
        self.assertIn("partes registrados", error)

    def test_reasignar_bloqueado_turno_destino_con_cc(self):
        """Reasignar T→T' bloquea si hay CC en T'."""
        from unittest.mock import patch

        msg = (
            "No se puede modificar: el operario ya tiene control de calidad registrado "
            "en esa fecha y turno."
        )
        with patch("mpr.services.obtener_turno", return_value=self.turno2), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=msg):
            mock_op.return_value = {"id_sue_abm_empleado": 504, "nombre_empleado": "Op Reasig"}
            ok, error = asignar_turno_roster(
                EMPRESA, self.fecha_futura_str, 504, self.turno2.id
            )
        self.assertFalse(ok)
        self.assertIn("control de calidad", error)

    def test_asignar_mismo_turno_idempotente_con_parte(self):
        """Misma asignación T→T permite aunque haya parte (override línea)."""
        from unittest.mock import patch

        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=True
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.upsert_roster"
        ) as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": 505, "nombre_empleado": "Op Idem"}
            ok, error = asignar_turno_roster(
                EMPRESA, self.fecha_futura_str, 505, self.turno.id
            )
        self.assertTrue(ok, error)
        mock_upsert.assert_called_once()

    def test_asignar_turno_segundo_turno_agrega_fila(self):
        """Agregar otro turno el mismo día invoca upsert para el segundo turno (multi-turno)."""
        from unittest.mock import patch
        fecha_str = self.fecha_futura_str
        id_op = 101

        def _turno_side_effect(base, tid):
            return self.turno if tid == self.turno.id else self.turno2

        def _asignado_side_effect(base, fecha, oid, tid):
            return tid == self.turno.id

        with patch("mpr.services.obtener_turno", side_effect=_turno_side_effect), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado",
            side_effect=_asignado_side_effect,
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.upsert_roster"
        ) as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": id_op, "nombre_empleado": "Operario Uno"}
            ok1, err1 = asignar_turno_roster(EMPRESA, fecha_str, id_op, self.turno.id)
            self.assertTrue(ok1, err1)

            ok2, err2 = asignar_turno_roster(EMPRESA, fecha_str, id_op, self.turno2.id)
            self.assertTrue(ok2, err2)

        self.assertEqual(mock_upsert.call_count, 2)
        self.assertEqual(mock_upsert.call_args_list[-1][0][3], self.turno2.id)

    def test_asignar_turno_fecha_futura_ok(self):
        """asignar_turno_roster con fecha futura y operario mock retorna (True, None)."""
        from unittest.mock import patch
        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.upsert_roster"
        ):
            mock_op.return_value = {"id_sue_abm_empleado": 200, "nombre_empleado": "Test Op"}
            ok, error = asignar_turno_roster(EMPRESA, self.fecha_futura_str, 200, self.turno.id)
        self.assertTrue(ok, error)
        self.assertIsNone(error)

    def test_eliminar_asignacion_existente(self):
        """eliminar_asignacion_roster elimina correctamente una asignación futura."""
        from unittest.mock import patch

        with patch(
            "mpr.repositories.turno_roster.turnos_del_operario_dia",
            return_value=[self.turno.id],
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.eliminar_roster_turno", return_value=1
        ):
            ok, error = eliminar_asignacion_roster(EMPRESA, self.fecha_futura_str, 300)
        self.assertTrue(ok, error)
        self.assertIsNone(error)

    def test_eliminar_asignacion_inexistente(self):
        """eliminar_asignacion_roster sobre asignación inexistente retorna (False, mensaje)."""
        from unittest.mock import patch

        with patch(
            "mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[]
        ):
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
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.upsert_roster"
        ) as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": 101, "nombre_empleado": "Op Test"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA, ids_op, self.turno.id, desde, hasta
            )

        self.assertTrue(ok, error)
        self.assertIsNone(error)
        self.assertEqual(resumen["aplicados"], 6)
        self.assertEqual(resumen["omitidos_pasados"], 0)
        self.assertEqual(resumen.get("omitidos_bloqueados", 0), 0)
        self.assertEqual(mock_upsert.call_count, 6)

    def test_rango_incluye_ayer_aplica_tambien_pasado(self):
        """Rango con ayer aplica también fechas pasadas si no hay bloqueo."""
        from unittest.mock import patch

        desde = self.ayer
        hasta = self.manana

        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.upsert_roster"
        ) as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": 200, "nombre_empleado": "Op Uno"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA, [200], self.turno.id, desde, hasta
            )

        self.assertTrue(ok, error)
        self.assertEqual(resumen["omitidos_pasados"], 0)
        self.assertEqual(resumen.get("omitidos_bloqueados", 0), 0)
        dias_en_rango = 3
        self.assertEqual(resumen["aplicados"], dias_en_rango)
        self.assertEqual(mock_upsert.call_count, dias_en_rango)

    def test_rango_omite_celdas_bloqueadas(self):
        """Rango omite celdas con parte/CC registrado."""
        from unittest.mock import patch

        desde = self.manana
        hasta = self.manana + timedelta(days=1)
        msg = "No se puede modificar: el operario ya tiene partes registrados en esa fecha y turno."

        def _bloqueo_side_effect(base, fecha, oid, actual, nuevo):
            if fecha == desde:
                return msg
            return None

        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch(
            "mpr.services._motivo_bloqueo_cambio_roster", side_effect=_bloqueo_side_effect
        ), patch("mpr.repositories.turno_roster.upsert_roster") as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": 210, "nombre_empleado": "Op Mix"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA, [210], self.turno.id, desde, hasta
            )

        self.assertTrue(ok, error)
        self.assertEqual(resumen["aplicados"], 1)
        self.assertEqual(resumen["omitidos_bloqueados"], 1)
        self.assertEqual(mock_upsert.call_count, 1)

    def test_rango_solo_bloqueos_retorna_mensaje(self):
        """Si todas las celdas están bloqueadas, ok=False con mensaje claro."""
        from unittest.mock import patch

        msg = "No se puede modificar: el operario ya tiene partes registrados en esa fecha y turno."
        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=True
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=msg):
            mock_op.return_value = {"id_sue_abm_empleado": 220, "nombre_empleado": "Op Todo Bloq"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA, [220], self.turno2.id, self.manana, self.manana
            )

        self.assertFalse(ok)
        self.assertIn("parte aprobado/físico o control de calidad", error)
        self.assertEqual(resumen["aplicados"], 0)
        self.assertEqual(resumen["omitidos_bloqueados"], 1)

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

    def test_rango_agrega_segundo_turno_sin_sobrescribir(self):
        """Dos llamadas mismo operario/fecha con distinto turno invocan upsert (multi-turno)."""
        from unittest.mock import patch

        fecha = self.manana
        id_op = 301

        def _turno_side_effect(base, tid):
            return self.turno if tid == self.turno.id else self.turno2

        with patch("mpr.services.obtener_turno", side_effect=_turno_side_effect), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.upsert_roster"
        ) as mock_upsert:
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

    def test_solo_vacio_omite_si_ya_hay_turno(self):
        """Modo solo_vacio omite días que ya tienen cualquier turno."""
        from unittest.mock import patch

        fecha = self.manana
        id_op = 401

        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[self.turno2.id]
        ), patch("mpr.repositories.turno_roster.upsert_roster") as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": id_op, "nombre_empleado": "Op Solo Vacio"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA, [id_op], self.turno.id, fecha, fecha, modo="solo_vacio"
            )

        self.assertFalse(ok)
        self.assertIn("ya tenían turno", error)
        self.assertEqual(resumen["aplicados"], 0)
        self.assertEqual(resumen["omitidos_con_turno"], 1)
        mock_upsert.assert_not_called()

    def test_solo_vacio_aplica_si_dia_vacio(self):
        """Modo solo_vacio aplica upsert si el día no tiene turnos."""
        from unittest.mock import patch

        fecha = self.manana
        id_op = 402

        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[]
        ), patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.upsert_roster"
        ) as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": id_op, "nombre_empleado": "Op Vacio OK"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA, [id_op], self.turno.id, fecha, fecha, modo="solo_vacio"
            )

        self.assertTrue(ok, error)
        self.assertEqual(resumen["aplicados"], 1)
        self.assertEqual(resumen["omitidos_con_turno"], 0)
        mock_upsert.assert_called_once()

    def test_reemplazar_elimina_turno_previo_no_bloqueado(self):
        """Modo reemplazar quita turno previo no bloqueado y deja el nuevo."""
        from unittest.mock import patch

        fecha = self.manana
        id_op = 501

        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[self.turno2.id]
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch("mpr.repositories.turno_roster.eliminar_roster_turno") as mock_del, patch(
            "mpr.repositories.turno_roster.upsert_roster"
        ) as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": id_op, "nombre_empleado": "Op Reemplazo"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA, [id_op], self.turno.id, fecha, fecha, modo="reemplazar"
            )

        self.assertTrue(ok, error)
        self.assertEqual(resumen["aplicados"], 1)
        mock_del.assert_called_once_with(EMPRESA, fecha, id_op, self.turno2.id)
        mock_upsert.assert_called_once()

    def test_reemplazar_no_borra_turno_bloqueado(self):
        """Modo reemplazar no elimina turnos bloqueados; aplica el target si no está bloqueado."""
        from unittest.mock import patch

        fecha = self.manana
        id_op = 502
        msg = "No se puede modificar: el operario ya tiene partes registrados en esa fecha y turno."

        def _bloqueo_side_effect(base, f, oid, actual, nuevo):
            if actual == self.turno2.id and nuevo is None:
                return msg
            return None

        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.turnos_del_operario_dia", return_value=[self.turno2.id]
        ), patch(
            "mpr.services._motivo_bloqueo_cambio_roster", side_effect=_bloqueo_side_effect
        ), patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch("mpr.repositories.turno_roster.eliminar_roster_turno") as mock_del, patch(
            "mpr.repositories.turno_roster.upsert_roster"
        ) as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": id_op, "nombre_empleado": "Op Bloq"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA, [id_op], self.turno.id, fecha, fecha, modo="reemplazar"
            )

        self.assertTrue(ok, error)
        self.assertEqual(resumen["aplicados"], 1)
        mock_del.assert_not_called()
        mock_upsert.assert_called_once()

    def test_plantilla_lun_vie_omite_fin_de_semana(self):
        """Rango Lun–Dom con dias_semana=[0..4] aplica solo 5 días por operario."""
        from unittest.mock import patch

        lunes = date(2026, 8, 3)
        domingo = lunes + timedelta(days=6)
        id_op = 601

        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.upsert_roster"
        ) as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": id_op, "nombre_empleado": "Op Lun Vie"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA,
                [id_op],
                self.turno.id,
                lunes,
                domingo,
                dias_semana=[0, 1, 2, 3, 4],
            )

        self.assertTrue(ok, error)
        self.assertEqual(resumen["aplicados"], 5)
        self.assertEqual(resumen["omitidos_plantilla"], 2)
        self.assertEqual(mock_upsert.call_count, 5)

    def test_sin_dias_semana_aplica_todos(self):
        """Sin dias_semana sigue aplicando todos los días del rango."""
        from unittest.mock import patch

        lunes = date(2026, 8, 3)
        domingo = lunes + timedelta(days=6)
        id_op = 602

        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.upsert_roster"
        ) as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": id_op, "nombre_empleado": "Op Todos"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA, [id_op], self.turno.id, lunes, domingo
            )

        self.assertTrue(ok, error)
        self.assertEqual(resumen["aplicados"], 7)
        self.assertEqual(resumen.get("omitidos_plantilla", 0), 0)
        self.assertEqual(mock_upsert.call_count, 7)

    def test_plantilla_personalizado_solo_miercoles(self):
        """Plantilla personalizado solo miércoles (2) aplica 1 día."""
        from unittest.mock import patch

        lunes = date(2026, 8, 3)
        domingo = lunes + timedelta(days=6)
        id_op = 603

        with patch("mpr.services.obtener_turno", return_value=self.turno), patch(
            "mpr.services.obtener_operario"
        ) as mock_op, patch(
            "mpr.repositories.turno_roster.roster_turno_asignado", return_value=False
        ), patch("mpr.services._motivo_bloqueo_cambio_roster", return_value=None), patch(
            "mpr.repositories.turno_roster.upsert_roster"
        ) as mock_upsert:
            mock_op.return_value = {"id_sue_abm_empleado": id_op, "nombre_empleado": "Op Mie"}
            ok, error, resumen = asignar_turno_roster_rango(
                EMPRESA,
                [id_op],
                self.turno.id,
                lunes,
                domingo,
                dias_semana=[2],
            )

        self.assertTrue(ok, error)
        self.assertEqual(resumen["aplicados"], 1)
        self.assertEqual(resumen["omitidos_plantilla"], 6)
        mock_upsert.assert_called_once()


class TestFiltroTurnoColor(SimpleTestCase):
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


class TestFiltroRosterIdsTurno(SimpleTestCase):
    """Filtro roster_ids_turno: ids de turnos en celda multi-turno."""

    def test_extrae_ids_de_lista(self):
        asigs = [
            {"id_turno": 1, "nombre_turno": "Mañana"},
            {"id_turno": 3, "nombre_turno": "Noche"},
        ]
        self.assertEqual(roster_ids_turno(asigs), [1, 3])

    def test_none_y_vacio(self):
        self.assertEqual(roster_ids_turno(None), [])
        self.assertEqual(roster_ids_turno([]), [])

    def test_ignora_items_sin_id(self):
        asigs = [{"nombre_turno": "X"}, {"id_turno": "2"}, "ruido"]
        self.assertEqual(roster_ids_turno(asigs), [2])
