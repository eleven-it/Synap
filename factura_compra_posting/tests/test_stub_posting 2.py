from django.test import SimpleTestCase, override_settings

from factura_compra_posting.contracts import LegacyPostingResult
from factura_compra_posting.stub_adapter import (
    FakeLegacyPostingAdapter,
    NoOpLegacyPostingAdapter,
    get_posting_adapter,
)


class FakeLegacyPostingAdapterTests(SimpleTestCase):
    def test_execute_sin_mysql_devuelve_resultado_estable(self):
        adapter = FakeLegacyPostingAdapter()
        r = adapter.execute({"expediente_id": "dummy"})
        self.assertIsInstance(r, LegacyPostingResult)
        self.assertTrue(r.success)
        self.assertEqual(r.codigo_movimiento, FakeLegacyPostingAdapter.FAKE_CODMOV)
        self.assertIn("FA-", r.nro_comprobante)

    def test_preflight_ok(self):
        adapter = FakeLegacyPostingAdapter()
        self.assertTrue(adapter.preflight(None).ok)

    def test_noop_execute_lanza(self):
        adapter = NoOpLegacyPostingAdapter()
        with self.assertRaises(NotImplementedError):
            adapter.execute({})


class GetPostingAdapterTests(SimpleTestCase):
    @override_settings(FACTURA_COMPRA_POSTING_BACKEND="fake")
    def test_get_fake(self):
        a = get_posting_adapter()
        self.assertIsInstance(a, FakeLegacyPostingAdapter)

    @override_settings(FACTURA_COMPRA_POSTING_BACKEND="noop")
    def test_get_noop(self):
        a = get_posting_adapter()
        self.assertIsInstance(a, NoOpLegacyPostingAdapter)

    @override_settings(FACTURA_COMPRA_POSTING_BACKEND="legacy")
    def test_get_legacy_lanza_en_fase1(self):
        with self.assertRaises(RuntimeError):
            get_posting_adapter()
