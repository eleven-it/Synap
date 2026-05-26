"""
IT-LEG-* — integración MySQL legacy (posting_tests.md §7).

Ejecutar solo con fixture aislada y variable de entorno acordada.
Por defecto omitidos para no tocar AdministraNET en CI.
"""

import os
import unittest


@unittest.skipUnless(
    os.environ.get("RUN_MYSQL_LEGACY_IT") == "1",
    "Definir RUN_MYSQL_LEGACY_IT=1 y fixture MySQL para IT-LEG",
)
class LegacyMysqlIntegrationPlaceholder(unittest.TestCase):
    def test_it_leg_placeholder(self):
        self.fail("Implementar IT-LEG-01..04 contra fixture cuando esté disponible.")
