"""Tests mínimos de vistas de auditoría contable (URLs y mocks)."""
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from contabilidad_audit.views import (
    PERMISO_CORREGIR,
    PERMISO_LEER,
    auditoria_lote_rollback,
    auditoria_lotes,
)

_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "contabilidad_audit"


def _session_user(base_empresa: str = "empresa_test"):
    return {
        "id_usuario": 1,
        "cod_usuario": "auditor",
        "base_empresa": base_empresa,
    }


class _UserConPermisoLeer:
    is_authenticated = True
    cod_usuario = "auditor"

    def is_admin(self):
        return False

    def tiene_permiso(self, code):
        return code == PERMISO_LEER


class _UserConPermisoCorregir:
    is_authenticated = True
    cod_usuario = "auditor"

    def is_admin(self):
        return False

    def tiene_permiso(self, code):
        return code in (PERMISO_LEER, PERMISO_CORREGIR)


class _UserSinPermiso:
    is_authenticated = True
    cod_usuario = "vendedor"

    def is_admin(self):
        return False

    def tiene_permiso(self, code):
        return False


class AuditoriaUrlsSmokeTestCase(SimpleTestCase):
    def test_reverse_urls_lotes(self):
        self.assertEqual(
            reverse("contabilidad_audit:auditoria_lotes"),
            "/contabilidad/auditoria/lotes/",
        )
        self.assertEqual(
            reverse("contabilidad_audit:auditoria_lote_rollback", kwargs={"lote_id": "L20260718-001"}),
            "/contabilidad/auditoria/lotes/L20260718-001/rollback/",
        )
        self.assertEqual(
            reverse("contabilidad_audit:auditoria_dry_run"),
            "/contabilidad/auditoria/dry-run/",
        )
        self.assertEqual(
            reverse("contabilidad_audit:manual_usuario"),
            "/contabilidad/manual/",
        )
        self.assertEqual(
            reverse("contabilidad_audit:auditoria_apply"),
            "/contabilidad/auditoria/apply/",
        )


class AuditoriaClaridadUiTemplatesTestCase(SimpleTestCase):
    """Smoke de textos/columnas para huérfanos FA/FC/OP y autorización de escritura."""

    def test_tablero_tiene_detalle_huerfanos_fa_fc_op(self):
        html = (_TEMPLATES / "auditoria_tablero.html").read_text(encoding="utf-8")
        self.assertIn("comprobante_compra_pago_sin_asiento", html)
        self.assertIn("comprobante_venta_cobranza_sin_asiento", html)
        self.assertIn("esCheckHuerfanosComprobante", html)
        self.assertIn("resumenHuerfanosPorTipo", html)
        self.assertIn("Nro comprobante", html)
        self.assertIn("CodigoMovimiento sin filas en cont_asiento", html)
        self.assertIn("Generar dry-run de regeneración", html)
        self.assertIn("mostrarEsperaDryRun", html)
        self.assertIn("Generando dry-run", html)
        self.assertIn("synapShowPostLoadingProgress", html)
        self.assertIn("Ejecutando auditoría", html)
        self.assertIn("partials/synap_post_loading_modal.html", html)

    def test_dry_run_plan_vacio_y_bloque_huerfanos(self):
        html = (_TEMPLATES / "auditoria_dry_run.html").read_text(encoding="utf-8")
        self.assertIn("Plan vacío", html)
        self.assertIn("Asientos huérfanos a regenerar", html)
        self.assertIn("comprobante_venta_cobranza_sin_asiento", html)
        self.assertIn("totalHuerfanosRegenerar", html)
        self.assertIn("no hay comprobantes sin asiento regenerables en el alcance", html)
        self.assertIn("synap-post-loading", html)
        self.assertIn("Generando dry-run", html)

    def test_apply_banner_unica_escritura_y_resumen(self):
        html = (_TEMPLATES / "auditoria_apply.html").read_text(encoding="utf-8")
        self.assertIn("única acción que escribe en MySQL legacy", html)
        self.assertIn("Resumen del plan a aplicar", html)
        self.assertIn("Asientos huérfanos a regenerar (compra/venta)", html)
        self.assertIn("asientos_regenerar_por_tipo", html)
        self.assertIn("confirmacion_entiendo", html)
        self.assertNotIn("confirmacion_final", html)
        self.assertNotIn("APLICAR-", html)
        self.assertIn("synap-post-loading", html)
        self.assertIn("Aplicando corrección contable", html)

    def test_lotes_rollback_tiene_modal_espera(self):
        html = (_TEMPLATES / "auditoria_lotes.html").read_text(encoding="utf-8")
        self.assertIn("synap-post-loading", html)
        self.assertIn("Revirtiendo lote", html)
        self.assertIn('procesando = true', html)
        self.assertIn("partials/synap_post_loading_modal.html", html)


class AuditoriaLotesViewsTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client()

    def _request_get_lotes(self, user=None):
        request = self.factory.get("/contabilidad/auditoria/lotes/")
        request.session = self.client.session
        request.session["user"] = _session_user()
        request.session.save()
        request.user = user or _UserConPermisoLeer()
        return request

    def _request_post_rollback(self, lote_id: str, user=None):
        request = self.factory.post(
            f"/contabilidad/auditoria/lotes/{lote_id}/rollback/",
        )
        request.session = self.client.session
        request.session["user"] = _session_user()
        request.session.save()
        request.user = user or _UserConPermisoCorregir()
        messages = FallbackStorage(request)
        request._messages = messages
        return request

    def test_lotes_sin_permiso_403(self):
        request = self._request_get_lotes(_UserSinPermiso())
        with self.assertRaises(PermissionDenied):
            auditoria_lotes(request)

    @patch("contabilidad_audit.views.render")
    @patch(
        "contabilidad_audit.views._listar_lotes_correccion",
        return_value=[
            {
                "lote_id": "L20260718-001",
                "fecha": "18/07/2026 14:30",
                "usuario": "auditor",
                "estado": "aplicado",
                "dry_run_id": "abc-123",
                "filas_correccion": 5,
            }
        ],
    )
    def test_lotes_con_permiso_lista(self, mock_listar, mock_render):
        mock_render.return_value = HttpResponse("ok")
        request = self._request_get_lotes()
        response = auditoria_lotes(request)
        self.assertEqual(response.status_code, 200)
        mock_listar.assert_called_once_with("empresa_test")
        ctx = mock_render.call_args[0][2]
        self.assertEqual(len(ctx["lotes"]), 1)
        self.assertEqual(ctx["lotes"][0]["lote_id"], "L20260718-001")

    def test_rollback_sin_permiso_403(self):
        request = self._request_post_rollback("L20260718-001", _UserSinPermiso())
        with self.assertRaises(PermissionDenied):
            auditoria_lote_rollback(request, "L20260718-001")

    @patch("legacy_db.services.cont_recalculo_service.rollback_lote")
    def test_rollback_con_permiso_redirige(self, mock_rollback):
        mock_rollback.return_value = {"ok": True, "lote_id": "L20260718-001"}
        request = self._request_post_rollback("L20260718-001")
        response = auditoria_lote_rollback(request, "L20260718-001")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("contabilidad_audit:auditoria_lotes"))
        mock_rollback.assert_called_once()
        args, kwargs = mock_rollback.call_args
        self.assertEqual(args[0], "empresa_test")
        self.assertEqual(args[1], "L20260718-001")
        self.assertTrue(kwargs.get("tiene_permiso_corregir"))

    @patch("contabilidad_audit.views.get_mysql_pool")
    def test_listar_lotes_helper(self, mock_pool):
        from contabilidad_audit.views import _listar_lotes_correccion

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            ("L1", datetime(2026, 7, 18, 14, 30, 0), "u1", "aplicado", "dry-1", 3),
        ]
        conn.cursor.return_value = cursor
        mock_pool.return_value.get_connection.return_value.__enter__.return_value = conn

        lotes = _listar_lotes_correccion("empresa_test")
        self.assertEqual(len(lotes), 1)
        self.assertEqual(lotes[0]["lote_id"], "L1")
        self.assertEqual(lotes[0]["filas_correccion"], 3)
        self.assertIn("/", lotes[0]["fecha"])
