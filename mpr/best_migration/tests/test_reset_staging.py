"""Tests del reinicio de staging Migración BEST."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.best_migration.reset import contar_staging_best, reiniciar_staging_best


def _fake_tablas():
    out = []
    for etiqueta, n in (
        ("artículos", 10),
        ("clientes", 2),
        ("depósitos", 4),
        ("stock inicial", 5),
        ("paridad / gate", 1),
    ):
        model = MagicMock()
        qs = MagicMock()
        qs.count.return_value = n
        qs.delete.return_value = (n, {})
        model.objects.filter.return_value = qs
        out.append((etiqueta, model))
    return out


class ContarStagingBestTests(SimpleTestCase):
    @patch("mpr.best_migration.reset.STAGING_TABLAS", new_callable=_fake_tablas)
    def test_contar_agrega_por_tabla(self, _tablas):
        out = contar_staging_best("administranet1")
        self.assertEqual(out["artículos"], 10)
        self.assertEqual(out["paridad / gate"], 1)
        self.assertEqual(sum(out.values()), 22)


class ReiniciarStagingBestTests(SimpleTestCase):
    @patch("mpr.best_migration.reset.STAGING_TABLAS", new_callable=_fake_tablas)
    def test_reiniciar_borra_todas_las_tablas(self, tablas):
        prev = reiniciar_staging_best("administranet1")
        self.assertEqual(prev["artículos"], 10)
        for _etiqueta, model in tablas:
            model.objects.filter.assert_called_with(base_empresa="administranet1")
            model.objects.filter.return_value.delete.assert_called()
