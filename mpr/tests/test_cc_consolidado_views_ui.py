"""RED/GREEN — integración views + humo UI CC consolidado por artículo (PR4)."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

User = get_user_model()
EMPRESA = "EmpresaTestCcViews"
FECHA_OK = "03/07/2026"
FECHA_OBJ = date(2026, 7, 3)
TURNO_ID = 1
ID_OPERARIO = 9


def _crear_usuario():
    uid = "test_cc_views_ui"
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        user = User.objects.create(
            uid=uid,
            email="test_cc_views@synap.test",
            nombre="Test CC Views",
            is_superuser=True,
            is_staff=True,
            is_active=True,
        )
    user.is_admin = lambda: True
    return user


def _add_messages(request):
    setattr(request, "_messages", FallbackStorage(request))


def _grilla_mock(**extra):
    base = {
        "bloques": [],
        "filas": [],
        "filas_vacio": True,
        "hay_filas_editables": False,
        "confirmadas_ocultas": 0,
        "bloqueos": [],
        "requiere_fecha": False,
        "requiere_fecha_turno": False,
        "componentes": [],
        "componentes_vacio": True,
        "tiene_borrador": False,
        "borrador_incompatible": False,
        "aviso_borrador": "",
    }
    base.update(extra)
    return base


class TestGetClasificacionSinTurno(TestCase):
    """7.1 — GET sin filtro turno; aviso borrador viejo en contexto."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = _crear_usuario()

    def _get(self, params=None):
        from mpr.views import ClasificacionProduccionView

        request = self.factory.get(
            reverse("mpr:clasificacion_produccion"), data=params or {}
        )
        request.session = {"user": {"id_usuario": 1, "base_empresa": EMPRESA}}
        request.user = self.user
        _add_messages(request)
        return ClasificacionProduccionView.as_view()(request)

    @patch("mpr.services.construir_grilla_clasificacion_produccion")
    def test_get_no_pasa_turno_id_a_grilla(self, mock_grilla):
        mock_grilla.return_value = _grilla_mock()
        resp = self._get({"fecha": FECHA_OK, "turno_id": "99"})
        self.assertEqual(resp.status_code, 200)
        args, kwargs = mock_grilla.call_args
        # Firma: (base, fecha, turno_id=None, ...) — turno ignorado / None.
        self.assertIsNone(args[2] if len(args) > 2 else kwargs.get("turno_id"))

    @patch("mpr.services.construir_grilla_clasificacion_produccion")
    def test_get_expone_aviso_borrador_incompatible(self, mock_grilla):
        mock_grilla.return_value = _grilla_mock(
            aviso_borrador="El borrador anterior no es compatible; volvé a cargar.",
            borrador_incompatible=True,
        )
        resp = self._get({"fecha": FECHA_OK})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "El borrador anterior no es compatible",
            resp.context_data["aviso_borrador"],
        )
        self.assertTrue(resp.context_data["borrador_incompatible"])

    @patch("mpr.services.construir_grilla_clasificacion_produccion")
    def test_get_expone_bloques_articulo(self, mock_grilla):
        mock_grilla.return_value = _grilla_mock(
            filas_vacio=False,
            hay_filas_editables=True,
            bloques=[{
                "id_articulo": 42,
                "saldo_produccion": Decimal("10"),
                "filas": [],
                "huerfano": True,
            }],
        )
        resp = self._get({"fecha": FECHA_OK})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context_data["bloques"]), 1)
        self.assertEqual(resp.context_data["bloques"][0]["id_articulo"], 42)


class TestPostClasificacionCcConsolidado(TestCase):
    """7.2 — POST via parsear + confirmar; sin transferir_stock_lote."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = _crear_usuario()

    def _post(self, data):
        from mpr.views import RegistrarClasificacionProduccionView

        request = self.factory.post(
            reverse("mpr:clasificacion_produccion_registrar"), data=data
        )
        session = {"user": {"id_usuario": 1, "base_empresa": EMPRESA}}
        request.session = session
        request.user = self.user
        _add_messages(request)
        resp = RegistrarClasificacionProduccionView.as_view()(request)
        resp._test_session = session
        return resp

    @patch("mpr.services.transferir_stock_lote")
    @patch(
        "mpr.services_cc_consolidado.confirmar_cc_consolidado",
        return_value={"ok": [42], "errores": [], "comprobantes": ["A"]},
    )
    @patch("mpr.services_cc_consolidado.parsear_post_cc_consolidado")
    def test_post_confirma_via_servicio_consolidado(
        self, mock_parse, mock_confirmar, mock_lote
    ):
        mock_parse.return_value = {
            42: {"semi": Decimal("8"), "lineas": [(ID_OPERARIO, TURNO_ID, "2da", Decimal("2"))]}
        }
        data = {
            "fecha": FECHA_OK,
            "accion": "confirmar",
            "semi_42": "8",
            f"seg2da_42_op_{ID_OPERARIO}_t_{TURNO_ID}": "2",
        }
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        mock_parse.assert_called_once()
        mock_confirmar.assert_called_once()
        args = mock_confirmar.call_args.args
        self.assertEqual(args[0], EMPRESA)
        self.assertEqual(args[2], FECHA_OBJ)
        self.assertEqual(args[3][42]["semi"], Decimal("8"))
        mock_lote.assert_not_called()
        fb = resp._test_session.get("clasificacion_feedback_modal")
        self.assertIsNotNone(fb)
        self.assertEqual(fb["tipo"], "success")

    @patch("mpr.services.transferir_stock_lote")
    @patch(
        "mpr.services_cc_consolidado.confirmar_cc_consolidado",
        return_value={
            "ok": [],
            "errores": [(42, "La cantidad total supera el saldo Producción disponible.")],
            "comprobantes": [],
        },
    )
    @patch("mpr.services_cc_consolidado.parsear_post_cc_consolidado")
    def test_post_exceso_saldo_feedback_error_sin_lote(
        self, mock_parse, mock_confirmar, mock_lote
    ):
        """Cobertura stock safety: exceso → error mprShowAviso, sin transferir_stock_lote."""
        mock_parse.return_value = {
            42: {"semi": Decimal("100"), "lineas": [(ID_OPERARIO, TURNO_ID, "2da", Decimal("30"))]}
        }
        resp = self._post({
            "fecha": FECHA_OK,
            "semi_42": "100",
            f"seg2da_42_op_{ID_OPERARIO}_t_{TURNO_ID}": "30",
        })
        self.assertEqual(resp.status_code, 302)
        mock_confirmar.assert_called_once()
        mock_lote.assert_not_called()
        fb = resp._test_session.get("clasificacion_feedback_modal")
        self.assertEqual(fb["tipo"], "error")
        self.assertIn("saldo", fb["mensaje"].lower())

    @patch("mpr.services.transferir_stock_lote")
    @patch("mpr.repositories.clasificacion_borrador.upsert_borrador_cc_consolidado")
    @patch("mpr.services_cc_consolidado.confirmar_cc_consolidado")
    @patch("mpr.services_cc_consolidado.parsear_post_cc_consolidado")
    def test_post_borrador_usa_upsert_007_sin_confirmar(
        self, mock_parse, mock_confirmar, mock_upsert, mock_lote
    ):
        mock_parse.return_value = {
            42: {"semi": Decimal("5"), "lineas": [(ID_OPERARIO, TURNO_ID, "2da", Decimal("1"))]}
        }
        resp = self._post({
            "fecha": FECHA_OK,
            "accion": "borrador",
            "semi_42": "5",
            f"seg2da_42_op_{ID_OPERARIO}_t_{TURNO_ID}": "1",
        })
        self.assertEqual(resp.status_code, 302)
        mock_upsert.assert_called_once()
        mock_confirmar.assert_not_called()
        mock_lote.assert_not_called()
        lineas = mock_upsert.call_args.args[3]
        semis = [ln for ln in lineas if float(ln.get("cant_semi") or 0) > 0]
        self.assertEqual(len(semis), 1)
        self.assertIsNone(semis[0].get("id_operario"))


class TestTemplateCcConsolidadoHumo(SimpleTestCase):
    """8.1–8.3 — plantillas: sin Turno/Máq., Saldo producción, claves POST, footer."""

    def test_thead_sin_maquina_con_saldo(self):
        html = render_to_string("mpr/includes/clasificacion_tabla_thead.html", {})
        self.assertNotIn(">Máq.<", html)
        self.assertIn("Saldo producción", html)
        # Turno permanece como columna de subfila (operario+turno), no como filtro GET.
        self.assertIn(">Turno<", html)

    def test_encabezado_sin_filtro_turno(self):
        html = render_to_string(
            "mpr/includes/clasificacion_encabezado.html",
            {
                "titulo_pantalla": "Control de calidad",
                "fecha_str": FECHA_OK,
                "fecha_hoy": FECHA_OK,
                "modo_presentacion": "docenas",
                "ver_roster": True,
                "puede_ver_roster_completo": True,
                "requiere_fecha": False,
                "tiene_borrador": False,
                "confirmadas_ocultas": 0,
                "presentacion_query_base": "fecha=03%2F07%2F2026",
                "marcas_catalogo": [],
                "marcas_incluidos": [],
                "turno_id": "",
                "turnos_activos": [],
            },
        )
        self.assertNotIn('name="turno_id"', html)
        self.assertNotIn("Turno (opcional)", html)

    def test_qty_semi_clave_consolidada_sin_op(self):
        html = render_to_string(
            "mpr/includes/clasif_qty_docenas_unidades_operario.html",
            {
                "prefix": "semi",
                "id_art": 42,
                "id_operario": None,
                "id_turno": None,
                "id_maquina": None,
                "operario_nombre": "",
                "codigo": "A",
                "destino_label": "semi elaborado",
                "model_doc": "semiDoc",
                "model_uni": "semiUni",
                "subtotal_alpine": "semiUnidades",
                "ring_class": "",
                "readonly": False,
                "consolidado_articulo": True,
            },
        )
        self.assertIn('name="semi_42_docenas"', html)
        self.assertNotIn("_op_", html)

    def test_qty_2da_clave_t_turno(self):
        html = render_to_string(
            "mpr/includes/clasif_qty_docenas_unidades_operario.html",
            {
                "prefix": "seg2da",
                "id_art": 42,
                "id_operario": 9,
                "id_turno": 1,
                "id_maquina": None,
                "operario_nombre": "Luis",
                "codigo": "A",
                "destino_label": "2da selección",
                "model_doc": "seg2daDoc",
                "model_uni": "seg2daUni",
                "subtotal_alpine": "seg2daUnidades",
                "ring_class": "",
                "readonly": False,
            },
        )
        self.assertIn('name="seg2da_42_op_9_t_1_docenas"', html)
        self.assertNotIn("_maq_", html)

    def test_plantillas_sin_dialogos_nativos(self):
        root = Path(__file__).resolve().parents[1] / "templates" / "mpr"
        archivos = [
            root / "clasificacion_produccion.html",
            root / "includes" / "clasificacion_encabezado.html",
            root / "includes" / "clasif_qty_docenas_unidades_operario.html",
        ]
        for path in archivos:
            texto = path.read_text(encoding="utf-8")
            self.assertNotIn("window.alert", texto)
            self.assertNotIn("window.confirm", texto)
            self.assertNotIn("window.prompt", texto)
            # alert( / confirm( / prompt( sueltos (no mprShowAviso)
            self.assertNotRegex(texto, r"(?<![A-Za-z])alert\s*\(")
            self.assertNotRegex(texto, r"(?<![A-Za-z])confirm\s*\(")
            self.assertNotRegex(texto, r"(?<![A-Za-z])prompt\s*\(")

    def test_footer_deshabilitado_sin_editables(self):
        texto = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "mpr"
            / "clasificacion_produccion.html"
        ).read_text(encoding="utf-8")
        self.assertIn("hayFilasEditables:", texto)
        self.assertIn('id="btn-guardar-borrador-cc"', texto)
        self.assertIn(":disabled=\"!hayFilasEditables || hayExcedida\"", texto)
        self.assertIn("clasificacionBloque", texto)
        self.assertIn("rowspan=", texto.lower())
        self.assertIn("id=\"btn-guardar-confirmar-cc\"", texto)
