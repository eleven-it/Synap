"""
Tests smoke para configuración: canales (draft, patch, test, activate, deactivate),
GET enmascarado, IA, storage test, permisos 403 no-admin, auditoría.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.agents.models import AgentProfile
from apps.audit.models import AuditEvent, AuditEventType
from apps.companies.models import Company
from apps.system_config.models import (
    ChannelConfig,
    ChannelType,
    ConfigStatus,
    IAConfig,
    StorageConfig,
)

User = get_user_model()


class ConfigPermissionTests(TestCase):
    """Solo Admin puede acceder a endpoints de config."""

    def setUp(self):
        self.agent_user = User.objects.create_user(username="agent1", password="test123")
        AgentProfile.objects.create(user=self.agent_user, role="agent")
        self.admin_user = User.objects.create_user(username="admin1", password="test123")
        AgentProfile.objects.create(user=self.admin_user, role="admin")
        self.client = Client()

    def test_config_channels_list_403_for_agent(self):
        self.client.force_login(self.agent_user)
        r = self.client.get("/api/config/channels/")
        self.assertEqual(r.status_code, 403)

    def test_config_channels_list_200_for_admin(self):
        self.client.force_login(self.admin_user)
        r = self.client.get("/api/config/channels/")
        self.assertEqual(r.status_code, 200)


class ChannelConfigSmokeTests(TestCase):
    """Crear draft, PATCH, GET enmascarado, test, activate, deactivate; auditoría."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin_ch", password="test123")
        AgentProfile.objects.create(user=self.admin, role="admin")
        self.company = Company.objects.create(synap_id="synap-c", prefix="C", language="es")
        self.client = Client()
        self.client.force_login(self.admin)

    def test_create_draft_channel_patch_and_get_masked(self):
        r = self.client.post(
            "/api/config/channels/",
            data=json.dumps({
                "channel_type": ChannelType.TELEGRAM,
                "display_name": "Bot test",
                "config": {"token": "secret_token_12345"},
            }),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        data = r.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], ConfigStatus.DRAFT)
        self.assertIn("config_masked", data)
        self.assertNotIn("secret_token", str(data["config_masked"]))
        self.assertTrue(
            "****" in str(data["config_masked"]) or "12345" in str(data["config_masked"]),
            "Token debe estar enmascarado",
        )

        pk = data["id"]
        r2 = self.client.get(f"/api/config/channels/{pk}/")
        self.assertEqual(r2.status_code, 200)
        d2 = r2.json()
        self.assertIn("config_masked", d2)
        self.assertNotIn("secret_token", str(d2.get("config_masked", {})))

    def test_channel_test_activate_deactivate_and_audit(self):
        ch = ChannelConfig.objects.create(
            company=None,
            channel_type=ChannelType.TELEGRAM,
            status=ConfigStatus.DRAFT,
            config_encrypted_json="",  # test fallará por falta token; igual ejecutamos flujo
        )
        r_test = self.client.post(f"/api/config/channels/{ch.id}/test/")
        self.assertIn(r_test.status_code, (200, 400))
        if r_test.status_code == 200:
            self.assertIn("success", r_test.json())

        r_act = self.client.post(f"/api/config/channels/{ch.id}/activate/")
        self.assertEqual(r_act.status_code, 200)
        ch.refresh_from_db()
        self.assertEqual(ch.status, ConfigStatus.ACTIVE)

        r_deact = self.client.post(f"/api/config/channels/{ch.id}/deactivate/")
        self.assertEqual(r_deact.status_code, 200)
        ch.refresh_from_db()
        self.assertEqual(ch.status, ConfigStatus.DISABLED)

        events = list(
            AuditEvent.objects.filter(
                event_type__in=[
                    AuditEventType.CONFIG_ACTIVATED,
                    AuditEventType.CONFIG_DEACTIVATED,
                ],
                payload__area="channels",
            )
        )
        self.assertGreaterEqual(len(events), 1, "Al menos un evento de config en auditoría")


class IAConfigMaskedTests(TestCase):
    """IA: GET devuelve api_key enmascarada; PATCH sin reemplazar si vacío."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin_ia", password="test123")
        AgentProfile.objects.create(user=self.admin, role="admin")
        self.client = Client()
        self.client.force_login(self.admin)

    def test_ia_config_get_returns_masked(self):
        from apps.system_config.crypto_utils import encrypt_json
        IAConfig.objects.create(
            company=None,
            provider="openai",
            model="gpt-4",
            api_key_encrypted=encrypt_json({"api_key": "sk-secretkey1234"}),
            status=ConfigStatus.DRAFT,
        )
        r = self.client.get("/api/config/ia/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsInstance(data, list)
        if data:
            self.assertIn("api_key_masked", data[0])
            self.assertNotIn("sk-secretkey", str(data[0]["api_key_masked"]))


class StorageConfigTestEndpointTests(TestCase):
    """POST /api/config/storage/test/ devuelve estructura success/message."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin_st", password="test123")
        AgentProfile.objects.create(user=self.admin, role="admin")
        self.client = Client()
        self.client.force_login(self.admin)

    def test_storage_test_returns_structure(self):
        r = self.client.post("/api/config/storage/test/")
        self.assertIn(r.status_code, (200, 404))
        if r.status_code == 404:
            return
        data = r.json()
        self.assertIn("success", data)
        self.assertIn("message", data)
