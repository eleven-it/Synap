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

    def _conteo_dir(self) -> Path:
        return Path(settings.BASE_DIR) / 'stock' / 'templates' / 'stock' / 'conteo'

    def _conteo_template_path(self) -> Path:
        return self._conteo_dir() / 'conteo.html'

    def _alpine_include_path(self) -> Path:
        return self._conteo_dir() / 'includes' / '_conteo_alpine.html'

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
        self.assertIn('agregarDigitoCantidad(digito)', contenido)
        self.assertIn('borrarDigitoCantidad()', contenido)
        self.assertIn('limpiarCantidad()', contenido)

    def test_logica_alpine_extraida_a_include_compartido(self):
        """El Alpine vive en un partial que comparten desktop y mobile."""
        include = self._alpine_include_path()
        self.assertTrue(include.is_file(), f'Falta {include}')
        contenido = include.read_text(encoding='utf-8')
        self.assertIn('function conteoInvFisico()', contenido)
        self.assertIn('enfocarCantidad(opciones)', contenido)
        self.assertIn('await this.cerrarScanner();', contenido)
        self.assertIn('agregarDigitoCantidad(digito)', contenido)

        ruta_include = 'stock/conteo/includes/_conteo_alpine.html'
        for template in ('conteo.html', 'mobile/conteo.html'):
            texto = (self._conteo_dir() / template).read_text(encoding='utf-8')
            self.assertIn(ruta_include, texto, f'{template} no incluye el Alpine compartido')
            self.assertNotIn(
                'function conteoInvFisico()', texto,
                f'{template} volvió a duplicar la lógica Alpine',
            )

    def test_validacion_anti_codigo_barras_en_cantidad(self):
        """La cantidad rechaza largos de EAN/UPC y bloquea el wedge tras el scan."""
        contenido = self._alpine_include_path().read_text(encoding='utf-8')
        self.assertIn('LARGOS_CODIGO_BARRAS', contenido)
        self.assertIn('MAX_DIGITOS_CANTIDAD', contenido)
        self.assertIn('validarCantidad(valor)', contenido)
        self.assertIn('sanitizarCantidad()', contenido)
        self.assertIn('onKeydownCantidad(evento)', contenido)
        self.assertIn('bloquearWedgeCantidad(ms)', contenido)
        self.assertIn('wedgeBloqueado()', contenido)
        self.assertIn('código de barras', contenido)
