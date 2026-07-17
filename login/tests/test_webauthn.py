"""
Tests WebAuthn unlock (login-pwa-webauthn).

Ejecutar:
  docker exec Synap_app python manage.py test login.tests.test_webauthn --keepdb -v1
"""
from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from core.models import SystemConfiguration
from core.utils.rate_limit import check_rate_limit
from login.models import WebAuthnCredential, WebAuthnUserPreference
from login.services import webauthn_service as svc
from login.services.webauthn_config import (
    get_user_quick_auth_enabled,
    set_user_quick_auth_enabled,
    set_webauthn_feature_enabled,
)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _sample_user(id_usuario: int = 99, cod_usuario: str = "testuser") -> dict:
    return {
        "id_usuario": id_usuario,
        "cod_usuario": cod_usuario,
        "nombre_usuario": "Test",
        "apellido_usuario": "Usuario",
        "id_empresa": 1,
        "id_sucursal": 1,
        "id_puesto": 1,
    }


def _create_credential(
    *,
    base_empresa: str = "empresa_test",
    id_usuario: int = 99,
    cred_id: bytes | None = None,
    fingerprint: str = "fp_original",
    device_label: str = "Dispositivo test",
) -> WebAuthnCredential:
    if cred_id is None:
        cred_id = b"test-credential-id-bytes-001"
    return WebAuthnCredential.objects.create(
        credential_id=cred_id,
        public_key=b"fake-public-key-material",
        sign_count=0,
        base_empresa=base_empresa,
        id_usuario=id_usuario,
        device_label=device_label,
        password_fingerprint=fingerprint,
    )


def _enable_webauthn_feature(enabled: bool = True) -> bool:
    return set_webauthn_feature_enabled(enabled)


def _enable_user_pref(
    base_empresa: str = "empresa_test",
    id_usuario: int = 99,
    enabled: bool = True,
) -> bool:
    return set_user_quick_auth_enabled(base_empresa, id_usuario, enabled)


class WebAuthnConfigTests(TestCase):
    def test_feature_flag_persisted_in_system_configuration(self):
        self.assertFalse(_enable_webauthn_feature(False))
        row = SystemConfiguration.objects.get(key="login.webauthn.unlock_enabled")
        self.assertEqual(row.value, "false")

        self.assertTrue(_enable_webauthn_feature(True))
        row.refresh_from_db()
        self.assertEqual(row.value, "true")

    def test_user_preference_default_false(self):
        self.assertFalse(get_user_quick_auth_enabled("empresa_test", 42))

    def test_user_preference_persisted(self):
        self.assertTrue(_enable_user_pref("empresa_test", 42, True))
        pref = WebAuthnUserPreference.objects.get(
            base_empresa="empresa_test",
            id_usuario=42,
        )
        self.assertTrue(pref.enabled)
        self.assertFalse(_enable_user_pref("empresa_test", 42, False))


class WebAuthnServiceTests(TestCase):
    """Tests unitarios del servicio (límite, challenge, fingerprint, TTL)."""

    def setUp(self):
        cache.clear()
        self.base = "empresa_test"
        self.id_usuario = 99
        self.session_key = "test-session-key"
        _enable_webauthn_feature(True)
        _enable_user_pref(self.base, self.id_usuario, True)

    def test_resolve_webauthn_rp_from_request_host(self):
        rf = RequestFactory()
        request = rf.get("/login/api/webauthn/register/options/", HTTP_HOST="192.168.0.2:8000")
        rp_id, origin = svc.resolve_webauthn_rp(request)
        self.assertEqual(rp_id, "192.168.0.2")
        self.assertEqual(origin, "http://192.168.0.2:8000")

    def test_resolve_webauthn_rp_fallback_settings(self):
        rp_id, origin = svc.resolve_webauthn_rp(None)
        self.assertEqual(rp_id, settings.WEBAUTHN_RP_ID)
        self.assertEqual(origin, settings.WEBAUTHN_ORIGIN)

    def test_max_three_credentials_rejects_enrollment(self):
        for i in range(3):
            _create_credential(
                base_empresa=self.base,
                id_usuario=self.id_usuario,
                cred_id=f"cred-{i}".encode(),
                device_label=f"D{i}",
            )
        with self.assertRaises(svc.WebAuthnServiceError) as ctx:
            svc.generate_register_options(
                session_key=self.session_key,
                base_empresa=self.base,
                id_usuario=self.id_usuario,
                cod_usuario="testuser",
                nombre_completo="Test Usuario",
            )
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("3", ctx.exception.message)

    def test_register_rejected_when_user_preference_off(self):
        _enable_user_pref(self.base, self.id_usuario, False)
        with self.assertRaises(svc.WebAuthnServiceError) as ctx:
            svc.generate_register_options(
                session_key=self.session_key,
                base_empresa=self.base,
                id_usuario=self.id_usuario,
                cod_usuario="testuser",
                nombre_completo="Test Usuario",
            )
        self.assertEqual(ctx.exception.status, 403)

    def test_authenticate_rejected_when_user_preference_off(self):
        _create_credential(
            base_empresa=self.base,
            id_usuario=self.id_usuario,
            cred_id=b"pref-off-cred",
        )
        mock_auth = MagicMock()
        mock_auth.get_user_by_cod.return_value = _sample_user(self.id_usuario)
        _enable_user_pref(self.base, self.id_usuario, False)
        with self.assertRaises(svc.WebAuthnServiceError) as ctx:
            svc.generate_authenticate_options(
                session_key=self.session_key,
                base_empresa=self.base,
                cod_usuario="testuser",
                auth_service=mock_auth,
            )
        self.assertEqual(ctx.exception.status, 403)

    def test_challenge_single_use_on_register_verify(self):
        svc.generate_register_options(
            session_key=self.session_key,
            base_empresa=self.base,
            id_usuario=self.id_usuario,
            cod_usuario="testuser",
            nombre_completo="Test Usuario",
        )
        with self.assertRaises(svc.WebAuthnServiceError):
            svc.verify_register(
                session_key=self.session_key,
                credential_json={"id": "x", "rawId": "x"},
            )
        with self.assertRaises(svc.WebAuthnServiceError) as ctx:
            svc.verify_register(
                session_key=self.session_key,
                credential_json={"id": "x", "rawId": "x"},
            )
        self.assertIn("expiró", ctx.exception.message.lower())

    def test_challenge_single_use_on_authenticate_verify(self):
        cred_id = b"auth-challenge-cred-id"
        _create_credential(
            base_empresa=self.base,
            id_usuario=self.id_usuario,
            cred_id=cred_id,
        )
        mock_auth = MagicMock()
        mock_auth.get_user_by_cod.return_value = _sample_user(self.id_usuario)
        svc.generate_authenticate_options(
            session_key=self.session_key,
            base_empresa=self.base,
            cod_usuario="testuser",
            auth_service=mock_auth,
        )
        cred_b64 = _b64url(cred_id)
        credential_json = {"id": cred_b64, "rawId": cred_b64, "type": "public-key"}
        with self.assertRaises(svc.WebAuthnServiceError):
            svc.verify_authenticate(
                session_key=self.session_key,
                credential_json=credential_json,
                request=RequestFactory().get("/"),
                auth_service=mock_auth,
            )
        with self.assertRaises(svc.WebAuthnServiceError) as ctx:
            svc.verify_authenticate(
                session_key=self.session_key,
                credential_json=credential_json,
                request=RequestFactory().get("/"),
                auth_service=mock_auth,
            )
        self.assertIn("expiró", ctx.exception.message.lower())

    def test_fingerprint_mismatch_revokes_all_credentials(self):
        cred_id = b"fingerprint-revoke-cred"
        _create_credential(
            base_empresa=self.base,
            id_usuario=self.id_usuario,
            cred_id=cred_id,
            fingerprint="fp_viejo",
        )
        svc._store_challenge(
            "auth",
            self.session_key,
            {
                "challenge": _b64url(b"challenge-bytes-test"),
                "base_empresa": self.base,
                "id_usuario": self.id_usuario,
            },
        )
        mock_auth = MagicMock()
        mock_auth.get_password_fingerprint.return_value = "fp_nuevo"
        mock_auth.get_user_by_id.return_value = _sample_user(self.id_usuario)
        cred_b64 = _b64url(cred_id)
        verified = MagicMock(new_sign_count=1)
        with patch(
            "login.services.webauthn_service.verify_authentication_response",
            return_value=verified,
        ):
            with self.assertRaises(svc.WebAuthnServiceError) as ctx:
                svc.verify_authenticate(
                    session_key=self.session_key,
                    credential_json={"id": cred_b64, "rawId": cred_b64},
                    request=RequestFactory().get("/"),
                    auth_service=mock_auth,
                )
        self.assertIn("contraseña", ctx.exception.message.lower())
        self.assertEqual(
            WebAuthnCredential.objects.filter(
                base_empresa=self.base,
                id_usuario=self.id_usuario,
                revoked_at__isnull=True,
            ).count(),
            0,
        )

    def test_unlock_uses_webauthn_session_age(self):
        cred_id = b"ttl-session-cred-id"
        db_cred = _create_credential(
            base_empresa=self.base,
            id_usuario=self.id_usuario,
            cred_id=cred_id,
        )
        svc._store_challenge(
            "auth",
            self.session_key,
            {
                "challenge": _b64url(b"ttl-challenge-bytes"),
                "base_empresa": self.base,
                "id_usuario": self.id_usuario,
            },
        )
        mock_auth = MagicMock()
        mock_auth.get_password_fingerprint.return_value = db_cred.password_fingerprint
        mock_auth.get_user_by_id.return_value = _sample_user(self.id_usuario)
        request = RequestFactory().get("/")
        cred_b64 = _b64url(cred_id)
        verified = MagicMock(new_sign_count=2)
        with patch(
            "login.services.webauthn_service.verify_authentication_response",
            return_value=verified,
        ):
            with patch(
                "login.services.session_bootstrap.bootstrap_synap_session",
            ) as mock_bootstrap:
                svc.verify_authenticate(
                    session_key=self.session_key,
                    credential_json={"id": cred_b64, "rawId": cred_b64},
                    request=request,
                    auth_service=mock_auth,
                )
                mock_bootstrap.assert_called_once()
                self.assertEqual(
                    mock_bootstrap.call_args.kwargs["session_age"],
                    settings.WEBAUTHN_SESSION_AGE,
                )


class WebAuthnViewTests(TestCase):
    """Tests HTTP: flag off, rate limit, integración options+verify."""

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.base = "empresa_test"
        self.cod_usuario = "testuser"
        self.id_usuario = 99
        _enable_webauthn_feature(True)
        _enable_user_pref(self.base, self.id_usuario, True)

    def _csrf_post(self, url: str, payload: dict | None = None):
        self.client.get(reverse("login:login"))
        token = self.client.cookies["csrftoken"].value
        body = json.dumps(payload or {})
        return self.client.post(
            url,
            data=body,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

    def test_feature_off_returns_404_json(self):
        _enable_webauthn_feature(False)
        post_endpoints = [
            reverse("login:webauthn_register_options"),
            reverse("login:webauthn_register_verify"),
            reverse("login:webauthn_authenticate_options"),
            reverse("login:webauthn_authenticate_verify"),
            reverse("login:webauthn_credentials_revoke"),
        ]
        for url in post_endpoints:
            response = self._csrf_post(url, {})
            self.assertEqual(response.status_code, 404, msg=url)
            self.assertEqual(response.json()["error"], "WebAuthn deshabilitado")

        list_url = reverse("login:webauthn_credentials_list")
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "WebAuthn deshabilitado")

    def test_authenticate_verify_rate_limit(self):
        url = reverse("login:webauthn_authenticate_verify")
        rf = RequestFactory()
        for _ in range(41):
            req = rf.post(url, REMOTE_ADDR="10.0.0.99")
            check_rate_limit(
                req,
                key_prefix="webauthn_auth_verify",
                limit=40,
                period_seconds=300,
                exceeded_body={"error": "Demasiados intentos."},
            )
        self.client.get(reverse("login:login"), REMOTE_ADDR="10.0.0.99")
        token = self.client.cookies["csrftoken"].value
        response = self.client.post(
            url,
            data="{}",
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
            REMOTE_ADDR="10.0.0.99",
        )
        self.assertEqual(response.status_code, 429)
        self.assertIn("Demasiados intentos", response.json()["error"])

    @patch("login.services.webauthn_service.verify_authentication_response")
    @patch("login.services.session_bootstrap.bootstrap_synap_session")
    @patch("login.administranet_auth.AdministraNETAuth.get_user_by_cod")
    @patch("login.administranet_auth.AdministraNETAuth.get_user_by_id")
    @patch("login.administranet_auth.AdministraNETAuth.get_password_fingerprint")
    def test_authenticate_options_and_verify_integration(
        self,
        mock_fingerprint,
        mock_get_by_id,
        mock_get_by_cod,
        mock_bootstrap,
        mock_verify_auth,
    ):
        cred_id = b"integration-cred-id-xyz"
        db_cred = _create_credential(
            base_empresa=self.base,
            id_usuario=self.id_usuario,
            cred_id=cred_id,
        )
        user = _sample_user(self.id_usuario, self.cod_usuario)
        mock_get_by_cod.return_value = user
        mock_get_by_id.return_value = user
        mock_fingerprint.return_value = db_cred.password_fingerprint
        mock_verify_auth.return_value = MagicMock(new_sign_count=1)
        mock_bootstrap.return_value = {"id_sesion": 123}

        options_url = reverse("login:webauthn_authenticate_options")
        verify_url = reverse("login:webauthn_authenticate_verify")

        opt_resp = self._csrf_post(
            options_url,
            {"base_empresa": self.base, "cod_usuario": self.cod_usuario},
        )
        self.assertEqual(opt_resp.status_code, 200)
        self.assertIn("challenge", opt_resp.json())

        cred_b64 = _b64url(cred_id)
        verify_resp = self._csrf_post(
            verify_url,
            {
                "credential": {
                    "id": cred_b64,
                    "rawId": cred_b64,
                    "type": "public-key",
                    "response": {
                        "clientDataJSON": "e30",
                        "authenticatorData": "e30",
                        "signature": "e30",
                    },
                }
            },
        )
        self.assertEqual(verify_resp.status_code, 200)
        self.assertIn("redirect", verify_resp.json())
        mock_bootstrap.assert_called_once()
        db_cred.refresh_from_db()
        self.assertEqual(db_cred.sign_count, 1)
        self.assertIsNotNone(db_cred.last_used_at)

    def test_authenticate_options_403_when_user_preference_off(self):
        _create_credential(
            base_empresa=self.base,
            id_usuario=self.id_usuario,
            cred_id=b"pref-off-view-cred",
        )
        _enable_user_pref(self.base, self.id_usuario, False)
        url = reverse("login:webauthn_authenticate_options")
        with patch(
            "login.administranet_auth.AdministraNETAuth.get_user_by_cod",
            return_value=_sample_user(self.id_usuario, self.cod_usuario),
        ):
            response = self._csrf_post(
                url,
                {"base_empresa": self.base, "cod_usuario": self.cod_usuario},
            )
        self.assertEqual(response.status_code, 403)
        self.assertIn("desactivada", response.json()["error"].lower())

    def test_credentials_list_includes_user_enabled(self):
        from django.contrib.sessions.middleware import SessionMiddleware

        from login import webauthn_views

        _enable_user_pref(self.base, self.id_usuario, False)
        _create_credential(base_empresa=self.base, id_usuario=self.id_usuario)

        def _dummy_get_response(request):
            return None

        request = RequestFactory().get(reverse("login:webauthn_credentials_list"))
        SessionMiddleware(_dummy_get_response).process_request(request)
        request.session["user"] = {
            "base_empresa": self.base,
            "id_usuario": self.id_usuario,
            "cod_usuario": self.cod_usuario,
        }
        request.session.save()

        response = webauthn_views.credentials_list(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data["user_enabled"])
        self.assertEqual(data["count"], 1)
