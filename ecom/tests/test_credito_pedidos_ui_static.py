# -*- coding: utf-8 -*-
"""Contratos estáticos de los templates y diálogos de crédito."""

from pathlib import Path

from django.test import SimpleTestCase


ECOM_DIR = Path(__file__).resolve().parents[1]


class CreditoPedidosUiStaticTests(SimpleTestCase):
    def test_advertencia_credito_usa_modal_canon(self):
        modal = (ECOM_DIR / "templates/ecom/includes/pedidos_modal.html").read_text()
        checkout = (
            ECOM_DIR / "static/ecom/js/compra_mayorista_checkout.mjs"
        ).read_text()
        dialogs = (ECOM_DIR / "static/ecom/js/order_dialogs.mjs").read_text()

        self.assertIn("credito_advertencia", modal)
        self.assertIn("abrirDialogo('credito_advertencia'", checkout)
        self.assertIn("this.dialogKind === 'credito_advertencia'", dialogs)

    def test_pantallas_credito_siguen_alta_movimiento_sin_dialogos_nativos(self):
        templates = sorted((ECOM_DIR / "templates/ecom/credito").glob("*.html"))
        self.assertTrue(templates)
        for template in templates:
            contenido = template.read_text()
            self.assertIn("bg-slate-800", contenido, template.name)
            self.assertIn("max-w-none", contenido, template.name)
            self.assertNotIn("alert(", contenido, template.name)
            self.assertNotIn("confirm(", contenido, template.name)
            self.assertNotIn("prompt(", contenido, template.name)

    def test_selectores_de_canal_solo_ofrecen_ped_y_pre(self):
        for nombre in ("politica_form.html", "plantillas.html"):
            contenido = (
                ECOM_DIR / "templates/ecom/credito" / nombre
            ).read_text()
            self.assertIn('value="PED"', contenido, nombre)
            self.assertIn('value="PRE"', contenido, nombre)
            self.assertNotIn("WHATSAPP", contenido, nombre)
