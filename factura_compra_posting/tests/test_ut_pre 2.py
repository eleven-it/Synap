"""UT-PRE-* — preflight período y duplicados (posting_tests.md §5)."""

from django.test import SimpleTestCase

from factura_compra_posting.preflight_legacy import PreflightLegacyPostingService


class PreflightTests(SimpleTestCase):
    def test_ut_pre_01_periodo_ok_sin_duplicado(self):
        svc = PreflightLegacyPostingService(
            query_duplicate_count=lambda: 0,
            query_period_open=lambda: True,
        )
        r = svc.run(tipo_factura="FA", nro_busqueda="X")
        self.assertTrue(r.ok)

    def test_ut_pre_02_periodo_cerrado(self):
        svc = PreflightLegacyPostingService(
            query_duplicate_count=lambda: 0,
            query_period_open=lambda: False,
        )
        r = svc.run(tipo_factura="FA", nro_busqueda="X")
        self.assertFalse(r.ok)
        self.assertEqual(r.code, "FISCAL_PERIOD_CLOSED")

    def test_ut_pre_03_duplicado(self):
        svc = PreflightLegacyPostingService(
            query_duplicate_count=lambda: 1,
            query_period_open=lambda: True,
        )
        r = svc.run(tipo_factura="FA", nro_busqueda="X")
        self.assertFalse(r.ok)
        self.assertEqual(r.code, "DUPLICATE_INVOICE")

    def test_ut_pre_04_fm_excluido_si_flag_false(self):
        svc = PreflightLegacyPostingService(
            query_duplicate_count=lambda: 1,
            query_period_open=lambda: True,
            duplicate_includes_fm=False,
        )
        r = svc.run(tipo_factura="FM", nro_busqueda="X")
        self.assertTrue(r.ok)
