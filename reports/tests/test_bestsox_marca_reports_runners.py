# -*- coding: utf-8 -*-
import inspect

from django.test import SimpleTestCase

from reports.services.query_runner import QueryRunnerService


class BestsoxMarcaReportsRunnerTests(SimpleTestCase):
    def test_query_runner_registra_slugs(self):
        src = inspect.getsource(QueryRunnerService.run)
        for slug in (
            "produccion-marca-superart",
            "compras-marca-superart",
            "consignacion-stock",
        ):
            with self.subTest(slug=slug):
                self.assertIn(f'"{slug}"', src)
