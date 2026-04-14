"""Rutas del módulo Logística — Entregas."""
from django.test import SimpleTestCase
from django.urls import reverse


class LogisticaEntregasUrlsTests(SimpleTestCase):
    def test_reverse_pagina_y_api(self):
        self.assertIn("/logistica/entregas/", reverse("logistica:entregas"))
        self.assertIn("/lista/", reverse("logistica:api_entregas_lista"))
        self.assertIn("/entrega/", reverse("logistica:api_entregas_entrega"))

    def test_redirect_legacy_ecom_names_resolve(self):
        """Los nombres ``ecom:logistica_*`` siguen existiendo y apuntan al módulo nuevo vía 301."""
        self.assertIn("/ecom/logistica/entregas/", reverse("ecom:logistica_entregas"))
