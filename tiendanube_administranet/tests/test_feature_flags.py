"""Tests feature flags Tienda Nube (UI + kill switch env)."""

from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from tiendanube_administranet.utils.feature_flags import (
    tiendanube_auto_sync_disabled_reason,
    tiendanube_auto_sync_enabled,
    tiendanube_sync_disabled_reason,
    tiendanube_sync_enabled,
    tiendanube_webhooks_disabled_reason,
    tiendanube_webhooks_enabled,
)


def _config(*, is_active=True, auto_sync=True):
    return SimpleNamespace(is_active=is_active, auto_sync=auto_sync)


class FeatureFlagTests(SimpleTestCase):
    @override_settings(TIENDANUBE_SYNC_ENABLED=False)
    def test_kill_switch_sync_env(self):
        cfg = _config()
        self.assertFalse(tiendanube_sync_enabled(cfg))
        self.assertIn('emergencia', tiendanube_sync_disabled_reason(cfg))

    @override_settings(TIENDANUBE_WEBHOOKS_ENABLED=False)
    def test_kill_switch_webhooks_env(self):
        cfg = _config()
        self.assertFalse(tiendanube_webhooks_enabled(cfg))
        self.assertIn('emergencia', tiendanube_webhooks_disabled_reason(cfg))

    def test_sync_habilitado_config_activa(self):
        cfg = _config()
        self.assertTrue(tiendanube_sync_enabled(cfg))
        self.assertIsNone(tiendanube_sync_disabled_reason(cfg))

    def test_sync_deshabilitado_config_inactiva_ui(self):
        cfg = _config(is_active=False)
        self.assertFalse(tiendanube_sync_enabled(cfg))
        self.assertIn('inactiva', tiendanube_sync_disabled_reason(cfg))

    def test_auto_sync_respeta_checkbox_ui(self):
        cfg = _config(auto_sync=True)
        self.assertTrue(tiendanube_auto_sync_enabled(cfg))
        cfg.auto_sync = False
        self.assertFalse(tiendanube_auto_sync_enabled(cfg))
        self.assertIn('automática', tiendanube_auto_sync_disabled_reason(cfg))

    def test_webhooks_config_activa(self):
        cfg = _config()
        self.assertTrue(tiendanube_webhooks_enabled(cfg))
        cfg.is_active = False
        self.assertFalse(tiendanube_webhooks_enabled(cfg))
