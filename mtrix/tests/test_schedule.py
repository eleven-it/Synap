"""Programador Mtrix: ventana horaria, lock y origen cron."""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone

from mtrix.models import MtrixConfig, MtrixJob
from mtrix.services.schedule import jobs_a_lanzar, matching_rules


TZ = ZoneInfo("America/Argentina/Buenos_Aires")


class ScheduleTests(TestCase):
    def _cfg(self, **kwargs):
        data = {
            "base_empresa": "emp_cron",
            "programador_activo": True,
            "schedule_json": [{"dow": 0, "time": "06:00"}],
        }
        data.update(kwargs)
        return MtrixConfig.objects.create(**data)

    def test_match_hora_y_dow(self):
        cfg = self._cfg()
        now = datetime(2026, 8, 10, 6, 0, tzinfo=TZ)  # lunes
        self.assertEqual(now.weekday(), 0)
        self.assertTrue(matching_rules(cfg, now))

    def test_fuera_de_ventana_no_crea_job(self):
        self._cfg()
        now = datetime(2026, 8, 11, 6, 0, tzinfo=TZ)  # martes
        with timezone.override(TZ):
            creados = jobs_a_lanzar(now=now)
        self.assertEqual(creados, [])
        self.assertFalse(MtrixJob.objects.exists())

    def test_crea_job_origen_cron(self):
        self._cfg()
        now = datetime(2026, 8, 10, 6, 0, tzinfo=TZ)
        with timezone.override(TZ):
            creados = jobs_a_lanzar(now=now)
        self.assertEqual(len(creados), 1)
        self.assertEqual(creados[0].origen, MtrixJob.Origen.CRON)
        self.assertEqual(creados[0].triggered_by, "cron")
        self.assertEqual(creados[0].status, MtrixJob.Estado.QUEUED)

    def test_lock_omite_nueva_corrida(self):
        self._cfg()
        MtrixJob.objects.create(
            base_empresa="emp_cron",
            status=MtrixJob.Estado.RUNNING,
            origen=MtrixJob.Origen.UI,
        )
        now = datetime(2026, 8, 10, 6, 0, tzinfo=TZ)
        with timezone.override(TZ):
            creados = jobs_a_lanzar(now=now)
        self.assertEqual(creados, [])

    def test_inactivo_no_dispara(self):
        self._cfg(programador_activo=False)
        now = datetime(2026, 8, 10, 6, 0, tzinfo=TZ)
        with timezone.override(TZ):
            self.assertEqual(jobs_a_lanzar(now=now), [])
