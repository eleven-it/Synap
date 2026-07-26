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

    def test_includes_credito_sin_dialogos_nativos(self):
        includes = sorted(
            (ECOM_DIR / "templates/ecom/credito/includes").glob("*.html")
        )
        self.assertTrue(includes)
        for template in includes:
            contenido = template.read_text()
            self.assertNotIn("alert(", contenido, template.name)
            self.assertNotIn("confirm(", contenido, template.name)
            self.assertNotIn("prompt(", contenido, template.name)

    def test_cola_finanzas_muestra_cupos_adminet_semaforo_e_importe(self):
        contenido = (
            ECOM_DIR / "templates/ecom/credito/cola_finanzas.html"
        ).read_text()
        # Cupo AdministraNET, saldo, disponible e importe del pedido en cada fila.
        self.assertIn("Cupo AdministraNET", contenido)
        self.assertIn("row.credito_cupo", contenido)
        self.assertIn("row.saldo", contenido)
        self.assertIn("money(row.ImporteVenta)", contenido)
        self.assertIn("disponible(row)", contenido)
        # Semáforo con la paleta canónica de pedidos_order_header.
        self.assertIn("bg-emerald-500", contenido)
        self.assertIn("bg-amber-500", contenido)
        self.assertIn("bg-rose-500", contenido)
        # Aprobación con modal Synap (no diálogo nativo) y filtros de la cola.
        self.assertIn("aprobarOpen", contenido)
        self.assertIn('aria-modal="true"', contenido)
        self.assertIn("cambiarDias()", contenido)
        # Banner de workflow desactivado y empty state educativo.
        self.assertIn('x-show="!activo"', contenido)
        self.assertIn("No hay PED retenidos.", contenido)

    def test_alta_politica_usa_busqueda_predictiva_y_capas(self):
        contenido = (
            ECOM_DIR / "templates/ecom/credito/politica_form.html"
        ).read_text()
        # El ID de cliente a mano quedó reemplazado por el combobox predictivo.
        self.assertNotIn("form.id_cliente", contenido)
        self.assertIn("cliente_predictivo.html", contenido)
        self.assertIn("cliente_credito_panel.html", contenido)
        self.assertIn("usarDefault", contenido)
        # Capas de exposición enviadas en el POST.
        for capa in (
            "capa_cxc",
            "capa_ped_abiertos",
            "capa_remitos_nf",
            "capa_cheques",
            "capa_doc_actual",
            "incluir_mora",
        ):
            self.assertIn(capa, contenido, capa)

    def test_predictivo_cliente_usa_debounce_y_endpoint_de_busqueda(self):
        predictivo = (
            ECOM_DIR / "templates/ecom/credito/includes/cliente_predictivo.html"
        ).read_text()
        self.assertIn('role="combobox"', predictivo)
        self.assertIn("@input.debounce.280ms", predictivo)
        for nombre in ("politica_form.html", "politica_list.html", "plantillas.html"):
            contenido = (
                ECOM_DIR / "templates/ecom/credito" / nombre
            ).read_text()
            self.assertIn("urls.buscar_clientes", contenido, nombre)
            self.assertIn("modoBus=texto", contenido, nombre)

    def test_politicas_lista_expone_cupos_adminet_y_consulta(self):
        contenido = (
            ECOM_DIR / "templates/ecom/credito/politica_list.html"
        ).read_text()
        self.assertIn("Consultar cupo AdministraNET", contenido)
        self.assertIn("urls.cliente_resumen", contenido)
        self.assertIn("Cupo AdministraNET", contenido)
        self.assertIn("capasActivas(p)", contenido)
        self.assertIn("Default empresa", contenido)

    def test_plantillas_usa_select_de_tipo_aviso(self):
        contenido = (
            ECOM_DIR / "templates/ecom/credito/plantillas.html"
        ).read_text()
        self.assertIn('value="pedido_bloqueado"', contenido)
        self.assertIn('value="cobranza"', contenido)
        self.assertIn("nro_comprobante", contenido)
