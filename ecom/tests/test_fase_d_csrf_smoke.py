import unittest
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

pytestmark = pytest.mark.django_db


class TestFaseDCsrfSmoke(unittest.TestCase):
    def _client_con_sesion(self) -> Client:
        User = get_user_model()
        u = User(
            email=f"csrf-{uuid4().hex[:8]}@test.local",
            nombre="CSRF User",
            uid=f"uid-{uuid4().hex}",
        )
        u.set_password("x")
        u.save()
        c = Client(enforce_csrf_checks=True)
        c.force_login(u)
        return c

    def test_post_sin_csrf_da_403(self):
        c = self._client_con_sesion()
        r = c.post(
            "/ecom/api/health/",
            data={},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)

    def test_post_con_csrf_valido_pasa(self):
        c = self._client_con_sesion()
        csrf = "a" * 32
        c.cookies["csrftoken"] = csrf
        r = c.post(
            "/ecom/api/health/",
            data={},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(r.status_code, 200)
