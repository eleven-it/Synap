"""Tests listados mayoristapp F1/F2."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory, TestCase
from django.urls import reverse

from ecom.mayoristapp_listado_views import ListadoMayoristappView


class TestListadosMayoristappView(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="lst@example.com", nombre="Lst", password="x")
        self.factory = RequestFactory()

    def _get(self, url_name):
        url = reverse(url_name)
        req = self.factory.get(url)
        req.user = self.user
        req.session = SessionStore()
        req.session["user"] = {"base_empresa": "emp1", "id_usuario": 1}
        req._messages = FallbackStorage(req)
        return req, url

    def test_remitos_render(self):
        req, url = self._get("ecom:mayoristapp_listado_remitos")
        from ecom.mayoristapp_listado_urls import mayoristapp_listado_urlpatterns
        from ecom.mayoristapp_listado_views import listado_view_factory

        resp = listado_view_factory("remitos").as_view()(req)
        self.assertEqual(resp.status_code, 200)

    def test_portal_redirect_sin_cliente(self):
        url = reverse("ecom:mayoristapp_portal_consumos")
        req = self.factory.get(url)
        req.user = self.user
        req.session = SessionStore()
        req.session["user"] = {"base_empresa": "emp1"}
        req._messages = FallbackStorage(req)
        from ecom.mayoristapp_listado_views import listado_view_factory

        resp = listado_view_factory("consumos", portal=True).as_view()(req)
        self.assertEqual(resp.status_code, 302)
