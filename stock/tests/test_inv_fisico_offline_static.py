# -*- coding: utf-8 -*-
"""Smoke test del módulo JS offline inventario físico (Fase 4 — Strict TDD)."""
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class InvFisicoOfflineStaticTests(SimpleTestCase):
    """El bundle IndexedDB existe y expone contrato mínimo (sin runner JS en Docker)."""

    REQUIRED_STRINGS = (
        'synap_inv_fisico',
        'openDB',
        'client_event_id',
        'guardarCatalogo',
        'buscarPorEan',
        'buscarPorEanONombre',
        'contarCatalogo',
        'encolarEvento',
        'listarCola',
        'syncBatch',
        'marcarAceptados',
        'listarConteosLocales',
        'obtenerConteoLocal',
        'guardarConteoLocal',
        'InvFisicoOffline',
    )

    def _js_path(self) -> Path:
        return Path(settings.BASE_DIR) / 'theme' / 'static' / 'js' / 'inv_fisico_offline.js'

    def _conteo_template_path(self) -> Path:
        return (
            Path(settings.BASE_DIR)
            / 'stock'
            / 'templates'
            / 'stock'
            / 'conteo'
            / 'conteo.html'
        )

    def test_archivo_js_existe(self):
        path = self._js_path()
        self.assertTrue(path.is_file(), f'Falta {path}')

    def test_archivo_contiene_contrato_indexeddb(self):
        path = self._js_path()
        contenido = path.read_text(encoding='utf-8')
        for token in self.REQUIRED_STRINGS:
            self.assertIn(token, contenido, f'Falta token {token!r} en inv_fisico_offline.js')

    def test_sw_precache_conteo_shell(self):
        sw_path = Path(settings.BASE_DIR) / 'theme' / 'static' / 'sw.js'
        contenido = sw_path.read_text(encoding='utf-8')
        self.assertIn('CONTEO_SHELL_URLS', contenido)
        self.assertIn('/stock/conteo/', contenido)
        self.assertIn("'/api/'", contenido)

    def test_conteo_movilidad_prioriza_cantidad_tras_seleccionar_articulo(self):
        contenido = self._conteo_template_path().read_text(encoding='utf-8')
        self.assertIn(
            'type="text" inputmode="numeric" pattern="[0-9]*" autocomplete="off"',
            contenido,
        )
        self.assertIn('enfocarCantidad(opciones)', contenido)
        self.assertIn('await this.cerrarScanner();', contenido)
        self.assertIn('agregarDigitoCantidad(digito)', contenido)
        self.assertIn('borrarDigitoCantidad()', contenido)
        self.assertIn('limpiarCantidad()', contenido)
