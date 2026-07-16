"""Tests unificación pedido simple en matriz masiva (modo simple)."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.models import EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda
from ecom.pedido_masivo_views import PedidoMasivoCeldaAPIView
from ecom.permissions import EcomPedidoCapturaPermission, usuario_puede_matriz_multi_columna
from ecom.services.batch_checkout_masivo import confirmar_lote_masivo
from ecom.services.pedido_plantilla_service import (
    _salida_a_packs_matriz,
    cargar_pedido_en_draft_masivo,
)


class _PermUser:
    """Usuario mock con permisos configurables."""

    is_authenticated = True
    is_superuser = False

    def __init__(self, perms=None):
        self._perms = set(perms or [])

    def tiene_permiso(self, codigo: str) -> bool:
        if "*" in self._perms or "ecom.*" in self._perms:
            return True
        return codigo in self._perms


class TestSalidaAPacksMatriz(TestCase):
    @patch("ecom.services.pedido_plantilla_service._pack_tipo_y_mult")
    def test_redondeo_genera_aviso(self, mock_pack):
        mock_pack.return_value = ("Bulto", Decimal("12"))
        packs, aviso = _salida_a_packs_matriz(
            "emp_psu",
            101,
            Decimal("25"),
            descripcion="Arvejas",
        )
        self.assertEqual(packs, Decimal("2.083"))
        self.assertIn("redondeo", aviso or "")
        self.assertIn("Arvejas", aviso or "")

    @patch("ecom.services.pedido_plantilla_service._pack_tipo_y_mult")
    def test_uom_no_estandar_genera_aviso(self, mock_pack):
        mock_pack.return_value = ("Display", Decimal("6"))
        packs, aviso = _salida_a_packs_matriz(
            "emp_psu",
            55,
            Decimal("12"),
            tipo_unidad_linea="Caja chica",
            descripcion="Galletitas",
        )
        self.assertEqual(packs, Decimal("2"))
        self.assertIn("Caja chica", aviso or "")
        self.assertIn("Display", aviso or "")


class TestCargarPedidoEnDraftMasivo(TestCase):
    _CAB = {
        "tipo_comprobante": "PED",
        "anulado": "No",
        "estado": "Pendiente",
        "id_cliente": 500,
        "id_cliente_domicilio": 77,
        "cod_viajante": 3,
        "nro_comprobante": "0001-00009999",
    }
    _RENGLONES = [
        {
            "IDArt": 10,
            "Salida": Decimal("25"),
            "tipo_unidad": "Unidad",
            "Descripcion": "Arvejas",
        },
        {
            "IDArt": 11,
            "Salida": Decimal("0"),
            "tipo_unidad": "Unidad",
            "Descripcion": "Sin qty",
        },
    ]

    @patch("ecom.services.pedido_plantilla_service.leer_contexto_cliente_masivo")
    @patch("ecom.services.pedido_plantilla_service.detalle_pedido_relay")
    @patch("ecom.services.pedido_plantilla_service.cabecera_pedido_relay")
    @patch("ecom.services.pedido_plantilla_service.validar_pedido_como_plantilla")
    @patch("ecom.services.pedido_plantilla_service._salida_a_packs_matriz")
    def test_carga_celdas_y_advertencias(
        self,
        mock_packs,
        mock_validar,
        mock_cab,
        mock_detalle,
        mock_ctx,
    ):
        mock_validar.return_value = (self._CAB, None)
        mock_cab.return_value = self._CAB
        mock_detalle.return_value = self._RENGLONES
        mock_ctx.return_value = {"descPie": Decimal("0")}
        mock_packs.return_value = (Decimal("2.083"), "Arvejas: cantidad ajustada por redondeo.")

        draft, err, meta = cargar_pedido_en_draft_masivo(
            "emp_psu",
            9001,
            {"todos_clientes": "Si", "id_vendedor_usr": 3},
            id_usuario=22,
            idcliente_contexto=500,
        )
        self.assertIsNone(err)
        self.assertIsNotNone(draft)
        self.assertEqual(draft.modo, EcomPedidoMasivoDraft.MODO_SIMPLE)
        self.assertEqual(draft.cod_mov_origen, 9001)
        self.assertEqual(draft.id_domicilio_fijo, 77)
        self.assertEqual(draft.celdas.count(), 1)
        celda = draft.celdas.first()
        self.assertEqual(celda.id_articulo, 10)
        self.assertEqual(celda.id_cliente_domicilio, 77)
        self.assertEqual(celda.cantidad_packs, Decimal("2.083"))
        self.assertTrue(meta["editable"])
        self.assertEqual(len(meta["advertencias"]), 1)
        self.assertIn("redondeo", meta["advertencias"][0])

    @patch("ecom.services.pedido_plantilla_service.cabecera_pedido_relay")
    def test_rechaza_pedido_anulado(self, mock_cab):
        mock_cab.return_value = {
            **self._CAB,
            "anulado": "Si",
        }
        draft, err, _meta = cargar_pedido_en_draft_masivo(
            "emp_psu",
            9002,
            {"todos_clientes": "Si"},
            id_usuario=22,
        )
        self.assertIsNone(draft)
        self.assertIn("anulado", err.lower())


class TestEcomPedidoCapturaPermissionOR(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.perm = EcomPedidoCapturaPermission()

    def _req(self, user, session_user=None):
        req = self.factory.get("/ecom/api/mayoristapp/pedido-masivo/celda/")
        req.user = user
        req.session = {"user": session_user or {"base_empresa": "emp_psu"}}
        return req

    def test_permiso_pedidos_crear_solo(self):
        user = _PermUser(["ecom.pedidos.crear"])
        self.assertTrue(self.perm.has_permission(self._req(user), None))

    def test_permiso_pedido_masivo_usar_solo(self):
        user = _PermUser(["ecom.pedido_masivo.usar"])
        self.assertTrue(self.perm.has_permission(self._req(user), None))

    def test_sin_ningun_permiso_denegado(self):
        user = _PermUser(["ecom.pedidos.ver"])
        self.assertFalse(self.perm.has_permission(self._req(user), None))

    def test_sin_base_empresa_denegado(self):
        user = _PermUser(["ecom.pedidos.crear"])
        req = self.factory.get("/")
        req.user = user
        req.session = {}
        self.assertFalse(self.perm.has_permission(req, None))

    def test_api_celda_con_pedidos_crear(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_psu",
            id_usuario=55,
            id_cliente=1,
        )
        api = APIRequestFactory()
        req = api.post(
            "/ecom/api/mayoristapp/pedido-masivo/celda/",
            {
                "draft_id": d.pk,
                "id_articulo": 8,
                "id_cliente_domicilio": 2,
                "cantidad_packs": "1",
            },
            format="json",
        )
        req.session = {"user": {"base_empresa": "emp_psu", "id_usuario": 55}}
        force_authenticate(req, user=_PermUser(["ecom.pedidos.crear"]))
        resp = PedidoMasivoCeldaAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)

    def test_api_celda_sin_permiso_403(self):
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_psu",
            id_usuario=55,
            id_cliente=1,
        )
        api = APIRequestFactory()
        req = api.post(
            "/ecom/api/mayoristapp/pedido-masivo/celda/",
            {"draft_id": d.pk, "id_articulo": 8, "id_cliente_domicilio": 2, "cantidad_packs": "1"},
            format="json",
        )
        req.session = {"user": {"base_empresa": "emp_psu", "id_usuario": 55}}
        force_authenticate(req, user=_PermUser(["ecom.pedidos.ver"]))
        resp = PedidoMasivoCeldaAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 403)

    def test_matriz_multi_columna_requiere_masivo_usar(self):
        user = _PermUser(["ecom.pedidos.crear"])
        req = self._req(user)
        self.assertFalse(usuario_puede_matriz_multi_columna(req))
        user2 = _PermUser(["ecom.pedido_masivo.usar"])
        req2 = self._req(user2)
        self.assertTrue(usuario_puede_matriz_multi_columna(req2))


class TestConfirmarAnulaOrigenSimple(TestCase):
    @patch("ecom.services.batch_checkout_masivo.anular_pedido_relay")
    @patch("ecom.services.batch_checkout_masivo.puede_anular_pedido_relay")
    @patch("ecom.services.batch_checkout_masivo.opciones_presentacion_articulo")
    @patch("ecom.services.batch_checkout_masivo.agregar_item")
    @patch("ecom.services.batch_checkout_masivo.confirmar")
    def test_confirmar_anula_cod_mov_origen(
        self, mock_conf, mock_add, mock_opts, mock_puede, mock_anular
    ):
        mock_puede.return_value = (True, None)
        mock_anular.return_value = {"msg": "ok"}
        mock_opts.return_value = {
            "tipo_unidad_defecto": "Unidad",
            "opciones": [{"tipo": "Unidad", "multiplicador": 1}],
        }
        mock_add.return_value = (MagicMock(), None)
        mock_conf.return_value = (
            True,
            None,
            {"codigo_movimiento": 9100, "nro_comprobante": "P-1"},
        )
        d = EcomPedidoMasivoDraft.objects.create(
            base_empresa="emp_psu",
            id_usuario=9,
            id_cliente=100,
            modo=EcomPedidoMasivoDraft.MODO_SIMPLE,
            id_domicilio_fijo=10,
            cod_mov_origen=8000,
            estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        )
        EcomPedidoMasivoDraftCelda.objects.create(
            draft=d,
            id_articulo=1,
            id_cliente_domicilio=10,
            cantidad_packs=Decimal("2"),
        )
        ok, _msg, payload = confirmar_lote_masivo(
            d, id_usuario=9, id_punto_venta=1, cod_viajante=2
        )
        self.assertTrue(ok)
        mock_anular.assert_called_once()
        self.assertEqual(payload.get("cod_mov_origen_anulado"), 8000)
        d.refresh_from_db()
        self.assertEqual(d.estado, EcomPedidoMasivoDraft.ESTADO_CONFIRMADO)
