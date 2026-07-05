"""Placeholder integración guardado recibo — ejecutar manualmente con MySQL legacy."""

import unittest

from django.test import TestCase


@unittest.skip("Requiere MySQL legacy con cliente/facturas de prueba.")
class TestReciboGuardadoIntegration(TestCase):
    def test_placeholder(self):
        self.assertTrue(True)
