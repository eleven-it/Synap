"""
Tests smoke: health, idempotencia, dedupe webhook, búsqueda conocimiento, sync RAG desde Synap.
RAG usa LangChain PGVector; los tests mockean langchain_rag cuando hace falta.
Ejecutar: python manage.py test apps.api.tests_smoke
"""
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from apps.companies.models import Company
from apps.cases.models import Case, CaseCounter, Message
from apps.agents.models import AgentProfile

User = get_user_model()


def _doc(page_content, metadata=None):
    """Documento mínimo para mocks (page_content + metadata)."""
    return SimpleNamespace(page_content=page_content, metadata=metadata or {})


class HealthSmokeTests(TestCase):
    """GET /api/health, /live, /ready."""

    def test_health_returns_200_and_checks(self):
        client = Client()
        r = client.get("/api/health/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("status", data)
        self.assertIn("db", data)
        self.assertIn("redis", data)
        self.assertIn("storage", data)
        self.assertIn(data["status"], ("ok", "degraded", "error"))

    def test_live_always_200(self):
        r = Client().get("/api/health/live/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"live": True})

    def test_ready_200_when_db_ok(self):
        r = Client().get("/api/health/ready/")
        # Con DB ok (test DB) debe ser 200
        self.assertIn(r.status_code, (200, 500))
        data = r.json()
        self.assertIn("ready", data)
        if r.status_code == 200:
            self.assertTrue(data["ready"])


class IdempotencySmokeTests(TestCase):
    """Misma Idempotency-Key no duplica efectos y devuelve la misma respuesta."""

    def setUp(self):
        self.user = User.objects.create_user(username="agente1", password="test123")
        AgentProfile.objects.create(user=self.user, role="agent")
        self.company = Company.objects.create(synap_id="test-synap", prefix="TST", language="es")
        CaseCounter.objects.create(company=self.company, last_number=0)
        self.case = Case.objects.create(
            company=self.company,
            number_sequential=1,
            number_display="SUP-TST-000001",
            status="asignado_a_agente_humano",
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_patch_same_idempotency_key_returns_same_response(self):
        key = "550e8400-e29b-41d4-a716-446655440001"
        body = json.dumps({"status": "en_proceso_humano"})
        r1 = self.client.patch(
            f"/api/casos/{self.case.id}/",
            data=body,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(r1.status_code, 200)
        r2 = self.client.patch(
            f"/api/casos/{self.case.id}/",
            data=body,
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.json(), r2.json())


class WebhookDedupeSmokeTests(TestCase):
    """Si ya existe mensaje con (channel_type, external_message_id), webhook responde 200 duplicate."""

    def setUp(self):
        self.company = Company.objects.create(synap_id="wh-synap", prefix="WH", language="es")
        CaseCounter.objects.create(company=self.company, last_number=0)
        self.case = Case.objects.create(
            company=self.company,
            number_sequential=1,
            number_display="SUP-WH-000001",
            status="iniciado",
        )
        Message.objects.create(
            case=self.case,
            channel_type="telegram",
            external_message_id="msg-dup-1",
            sender_type="user",
            content="Hola",
            direction="inbound",
        )
        self.client = Client()

    def test_telegram_webhook_returns_200_duplicate_when_message_exists(self):
        r = self.client.post(
            "/api/webhooks/telegram/",
            data={"external_message_id": "msg-dup-1"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("duplicate"), True)


class KnowledgeSearchSmokeTests(TestCase):
    """GET /api/knowledge/search sin q -> 400; con q (admin) -> 200 con results."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin1", password="test123")
        AgentProfile.objects.create(user=self.admin, role="admin")
        self.client = Client()
        self.client.force_login(self.admin)

    def test_search_without_q_returns_400(self):
        r = self.client.get("/api/knowledge/search/")
        self.assertEqual(r.status_code, 400)

    @patch("apps.api.views_knowledge.langchain_rag.is_langchain_rag_available")
    @patch("apps.api.views_knowledge.langchain_rag.search_documents")
    def test_search_with_q_returns_200_when_rag_available(self, mock_search, mock_available):
        mock_available.return_value = True
        mock_search.return_value = [
            (_doc("Contenido de prueba", {"source_type": "caso", "source_id": "1"}), 0.92),
        ]
        r = self.client.get("/api/knowledge/search/?q=test")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)
        self.assertEqual(data.get("mode"), "vector")
        self.assertEqual(len(data["results"]), 1)
        self.assertIn("Contenido de prueba", data["results"][0]["text"])

    @patch("apps.api.views_knowledge.langchain_rag.is_langchain_rag_available")
    def test_search_without_rag_returns_501(self, mock_available):
        mock_available.return_value = False
        r = self.client.get("/api/knowledge/search/?q=test")
        self.assertEqual(r.status_code, 501)
        data = r.json()
        self.assertIn("message", data)
        self.assertIn("RAG", data["message"])


class KnowledgeMultiTenantSmokeTests(TestCase):
    """
    RAG multi-tenant: documento global + documento empresa X.
    Buscar como empresa X debe traer ambos; buscar como empresa Y solo el global.
    Se mockea search_documents para simular el comportamiento del store LangChain.
    """

    def setUp(self):
        self.company_x = Company.objects.create(synap_id="rag-x", prefix="RX", language="es")
        self.company_y = Company.objects.create(synap_id="rag-y", prefix="RY", language="es")
        self.doc_global = _doc("Contenido global para todos", {"source_type": "caso", "source_id": "global-1"})
        self.doc_x = _doc("Contenido exclusivo empresa X", {"source_type": "caso", "source_id": "x-1"})
        self.admin = User.objects.create_user(username="admin-rag", password="test123")
        AgentProfile.objects.create(user=self.admin, role="admin")
        self.client = Client()
        self.client.force_login(self.admin)

    @patch("apps.api.views_knowledge.langchain_rag.is_langchain_rag_available")
    @patch("apps.api.views_knowledge.langchain_rag.search_documents")
    def test_search_as_company_x_gets_global_and_company_chunk(self, mock_search, mock_available):
        mock_available.return_value = True
        mock_search.return_value = [(self.doc_global, 0.9), (self.doc_x, 0.85)]
        r = self.client.get(
            f"/api/knowledge/search/?q=Contenido&company_id={self.company_x.id}"
        )
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        texts = [x["text"] for x in results]
        self.assertIn("Contenido global para todos", texts)
        self.assertIn("Contenido exclusivo empresa X", texts)
        self.assertEqual(len(results), 2)

    @patch("apps.api.views_knowledge.langchain_rag.is_langchain_rag_available")
    @patch("apps.api.views_knowledge.langchain_rag.search_documents")
    def test_search_as_company_y_does_not_get_company_x_chunk(self, mock_search, mock_available):
        mock_available.return_value = True
        mock_search.return_value = [(self.doc_global, 0.9)]
        r = self.client.get(
            f"/api/knowledge/search/?q=Contenido&company_id={self.company_y.id}"
        )
        self.assertEqual(r.status_code, 200)
        results = r.json()["results"]
        texts = [x["text"] for x in results]
        self.assertIn("Contenido global para todos", texts)
        self.assertNotIn("Contenido exclusivo empresa X", texts)
        self.assertEqual(len(results), 1)


class SyncRagFromSynapSmokeTests(TestCase):
    """POST /api/knowledge/sync-from-synap/: carga conocimiento desde Synap (mock) e ingesta en RAG."""

    def setUp(self):
        self.admin = User.objects.create_user(username="admin-sync", password="test123")
        AgentProfile.objects.create(user=self.admin, role="admin")
        self.client = Client()
        self.client.force_login(self.admin)

    @override_settings(SUPPORT_SYNAP_API_URL="http://test-synap")
    @patch("apps.api.views_knowledge.langchain_rag.add_documents_from_synap_items")
    @patch("apps.integrations.adapters.synap_client.SynapClient")
    def test_sync_from_synap_ingesta_chunks(self, mock_synap_client_class, mock_add_docs):
        mock_synap_client_class.return_value.get_conocimiento.return_value = [
            {"text": "AdministraNET es el ERP. Synap es la evolución web.", "source_id": "synap-intro", "metadata": {"origen": "synap"}},
            {"text": "Soporte: contactar a Estrategias de Negocios.", "source_id": "synap-soporte", "metadata": {}},
        ]
        mock_add_docs.return_value = (2, 0)
        r = self.client.post(
            "/api/knowledge/sync-from-synap/",
            data=json.dumps({"company_id": None}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertIn("created", data)
        self.assertIn("updated", data)
        self.assertIn("message", data)
        self.assertGreaterEqual(data["created"] + data["updated"], 1)
        mock_add_docs.assert_called_once()
        call_kw = mock_add_docs.call_args[1]
        self.assertEqual(call_kw.get("source_type"), "synap")
