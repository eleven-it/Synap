"""
Tests — MPR Etapa 10: Clasificación de Producción (pantalla única consolidada).

El planchado deja de ser etapa con stock: la clasificación sale directo de
Producción hacia {Semi Elaborado | 2da Selección | Desperdicio}, con fecha de
carga (permite carga diferida). Reemplaza Inspección/Clasificación de la Etapa 9.

Cobertura:
- TestConstruirGrillaClasificacionProduccion: con produccion>0; vacío; base vacía; aislación por empresa.
- TestTransferirStockLoteFecha: best-effort y propagación de fecha al asiento.
- TestClasificacionProduccionViewGet: 200+contexto; sin empresa→vacío; auth→302.
- TestRegistrarClasificacionProduccionViewPost: reparto 3 destinos; BLOQUEO suma>disponible;
  hidden manipulado (re-validación server-side); best-effort; sin empresa; fecha inválida;
  fecha propagada; cantidades cero ignoradas.
- TestTableroSinPlanchado: sin columna Planchado; botón único 'Clasificación de producción';
  URL transicion_lote backward-safe.

Comando:
    docker exec Synap_app python manage.py test mpr.tests.test_etapa10_clasificacion_produccion --keepdb --noinput
"""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from mpr.services import (
    TIPO_MPR_2DA_SELECCION,
    TIPO_MPR_PRODUCCION,
    TIPO_MPR_SCRAP,
    TIPO_MPR_SEMI_ELABORADO,
    construir_grilla_clasificacion_produccion,
    transferir_stock_lote,
)

User = get_user_model()
EMPRESA = "EmpresaTestEtapa10"
FECHA_OK = "03/07/2026"
FECHA_OBJ = date(2026, 7, 3)
TURNO_ID = 1
ID_OPERARIO = 9
ID_MAQUINA = 0


def _celdas_parte_mock(id_art=42, cantidad=15.0, id_op=ID_OPERARIO, turno=TURNO_ID, id_maq=ID_MAQUINA):
    return {
        (id_maq, id_art, id_op, turno): {
            "cantidad": Decimal(str(cantidad)),
            "operario_nombre": "Operario Test",
            "maquina_nombre": "—" if not id_maq else f"Máq {id_maq}",
            "turno_nombre": "Turno Test",
            "id_mpr_turno": turno,
        }
    }


def _post_clasif_base(**extra):
    data = {"fecha": FECHA_OK, "accion": "confirmar"}
    data.update(extra)
    return data


def _post_cc_keys(id_art=42, id_op=ID_OPERARIO, turno=TURNO_ID, **cantidades):
    """Claves POST canónicas consolidado: semi_{art}, seg2da/scrap_{art}_op_{op}_t_{t}."""
    out = {}
    if "semi" in cantidades:
        out[f"semi_{id_art}"] = str(cantidades["semi"])
    if "seg2da" in cantidades:
        out[f"seg2da_{id_art}_op_{id_op}_t_{turno}"] = str(cantidades["seg2da"])
    if "scrap" in cantidades:
        out[f"scrap_{id_art}_op_{id_op}_t_{turno}"] = str(cantidades["scrap"])
    return out


def _pivot_con_produccion(id_art=42, saldo=15.0):
    """Pivot con saldo en Producción para el artículo dado."""
    return {
        id_art: {
            TIPO_MPR_PRODUCCION: saldo,
            TIPO_MPR_2DA_SELECCION: 0.0,
            TIPO_MPR_SEMI_ELABORADO: 0.0,
            TIPO_MPR_SCRAP: 0.0,
        }
    }


def _desc_map(id_art=42, codigo="ART-01", desc="Artículo test"):
    return {id_art: (codigo, desc)}


def _crear_usuario():
    uid = "test_e10_user"
    try:
        user = User.objects.get(uid=uid)
    except User.DoesNotExist:
        user = User.objects.create(
            uid=uid,
            email="test_e10@synap.test",
            nombre="Test E10",
            is_superuser=True,
            is_staff=True,
            is_active=True,
        )
    user.is_admin = lambda: True
    return user


def _add_messages(request):
    setattr(request, "_messages", FallbackStorage(request))


# ---------------------------------------------------------------------------
# TestConstruirGrillaClasificacionProduccion
# ---------------------------------------------------------------------------

class TestConstruirGrillaClasificacionProduccion(SimpleTestCase):
    """Grilla consolidada: día completo, saldo Producción, sin filtro turno."""

    def setUp(self):
        self._patches = [
            patch("mpr.repositories.clasificacion_borrador.listar_lineas_borrador", return_value={}),
            patch("mpr.repositories.clasificacion_borrador.tiene_borrador", return_value=False),
            patch("mpr.repositories.clasificacion_borrador.tiene_borrador_cc_consolidado", return_value=False),
            patch("mpr.repositories.clasificacion_borrador.listar_lineas_borrador_cc_consolidado", return_value=[]),
            patch("mpr.repositories.transicion_lote.semi_agregado_por_articulo_fecha", return_value={}),
            patch("mpr.repositories.transicion_lote.clasificado_segunda_scrap_por_celda_fecha", return_value={}),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    def test_sin_fecha_requiere_seleccion(self):
        resultado = construir_grilla_clasificacion_produccion(EMPRESA)
        self.assertTrue(resultado["requiere_fecha"])
        self.assertEqual(resultado["filas"], [])

    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion", return_value={42: {"Produccion": 15.0}})
    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map(id_art=42))
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    def test_grilla_sin_turno_lista_filas(self, mock_celdas, _fetch, _pivot):
        mock_celdas.return_value = _celdas_parte_mock(cantidad=15.0)
        resultado = construir_grilla_clasificacion_produccion(EMPRESA, FECHA_OBJ)
        self.assertFalse(resultado["filas_vacio"])
        self.assertEqual(len(resultado["bloques"]), 1)
        self.assertEqual(resultado["bloques"][0]["saldo_produccion"], Decimal("15"))
        mock_celdas.assert_called_with(EMPRESA, FECHA_OBJ, None)

    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion", return_value={42: {"Produccion": 10.0}})
    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map(id_art=42))
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    def test_turno_id_ignorado_pasa_none(self, mock_celdas, _fetch, _pivot):
        mock_celdas.return_value = _celdas_parte_mock(cantidad=10.0)
        construir_grilla_clasificacion_produccion(EMPRESA, FECHA_OBJ, TURNO_ID)
        mock_celdas.assert_called_once_with(EMPRESA, FECHA_OBJ, None)

    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion", return_value={42: {"Produccion": 24.0}})
    @patch("mpr.services._fetch_descripciones_articulo", return_value={42: ("C-42", "Art 42")})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    def test_colapsa_maquinas_mismo_operario_turno(self, mock_celdas, _fetch, _pivot):
        mock_celdas.return_value = {
            (20, 42, ID_OPERARIO, TURNO_ID): {
                "cantidad": Decimal("12"),
                "operario_nombre": "Op A",
                "maquina_nombre": "Maquina 20",
                "turno_nombre": "Mañana",
            },
            (21, 42, ID_OPERARIO, TURNO_ID): {
                "cantidad": Decimal("12"),
                "operario_nombre": "Op A",
                "maquina_nombre": "Maquina 21",
                "turno_nombre": "Mañana",
            },
        }
        resultado = construir_grilla_clasificacion_produccion(EMPRESA, FECHA_OBJ)
        self.assertEqual(len(resultado["bloques"]), 1)
        self.assertEqual(len(resultado["bloques"][0]["filas"]), 1)
        self.assertEqual(resultado["bloques"][0]["filas"][0]["fabricado"], Decimal("24"))

    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion", return_value={99: {"Produccion": 50.0}})
    @patch("mpr.services._fetch_descripciones_articulo", return_value={99: ("H", "Huerfano")})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno", return_value={})
    def test_huerfano_solo_semi(self, _celdas, _fetch, _pivot):
        resultado = construir_grilla_clasificacion_produccion(EMPRESA, FECHA_OBJ)
        self.assertEqual(len(resultado["bloques"]), 1)
        self.assertTrue(resultado["bloques"][0]["huerfano"])
        self.assertEqual(len(resultado["bloques"][0]["filas"]), 1)

    def test_base_empresa_vacia(self):
        resultado = construir_grilla_clasificacion_produccion("")
        self.assertTrue(resultado["filas_vacio"])


class TestTransferirStockLoteFecha(SimpleTestCase):
    """transferir_stock_lote best-effort y propagación de la fecha del parte."""

    def _item(self, id_art, destino=TIPO_MPR_SEMI_ELABORADO, cantidad=5):
        return {
            "id_articulo": id_art,
            "tipo_origen": TIPO_MPR_PRODUCCION,
            "tipo_destino": destino,
            "cantidad": Decimal(str(cantidad)),
        }

    @patch(
        "mpr.services.transferir_stock_entre_etapas",
        return_value=(True, 999, "MSTOCK-0001-00001", None),
    )
    def test_propaga_fecha_al_asiento(self, mock_tf):
        """La fecha del parte se propaga a transferir_stock_entre_etapas."""
        fecha = date(2026, 7, 3)
        resultado = transferir_stock_lote(EMPRESA, 1, [self._item(42)], fecha=fecha)

        self.assertEqual(resultado["exitosas"], 1)
        self.assertEqual(mock_tf.call_args.kwargs["fecha"], fecha)

    @patch("mpr.services.transferir_stock_entre_etapas")
    def test_best_effort_un_ok_un_fail(self, mock_tf):
        """Ítem 1 ok, ítem 2 falla → exitosas=1, fallidas=1, continúa."""
        mock_tf.side_effect = [
            (True, 1, "MSTOCK-0001-00001", None),
            (False, None, None, "Saldo insuficiente"),
        ]
        resultado = transferir_stock_lote(EMPRESA, 1, [self._item(42), self._item(99)])

        self.assertEqual(resultado["exitosas"], 1)
        self.assertEqual(resultado["fallidas"], 1)
        self.assertIn("Saldo insuficiente", resultado["errores"][0][1])

    def test_lista_vacia_retorna_ceros(self):
        resultado = transferir_stock_lote(EMPRESA, 1, [])
        self.assertEqual(resultado["exitosas"], 0)
        self.assertEqual(resultado["fallidas"], 0)

    @patch("mpr.services.transferir_stock_entre_etapas", side_effect=RuntimeError("fallo inesperado"))
    def test_excepcion_por_item_se_captura(self, mock_tf):
        resultado = transferir_stock_lote(EMPRESA, 1, [self._item(42)])
        self.assertEqual(resultado["fallidas"], 1)
        self.assertIn("fallo inesperado", resultado["errores"][0][1])

    @patch("mpr.services.transferir_stock_entre_etapas", return_value=(True, 1, "MSTOCK-1", None))
    def test_propaga_cantidad_extra(self, mock_tf):
        items = [{
            "id_articulo": 42,
            "tipo_origen": TIPO_MPR_PRODUCCION,
            "tipo_destino": TIPO_MPR_SEMI_ELABORADO,
            "cantidad": Decimal("20"),
            "cantidad_extra": Decimal("5"),
        }]
        transferir_stock_lote(EMPRESA, 1, items, fecha=FECHA_OBJ)
        self.assertEqual(float(mock_tf.call_args.kwargs["cantidad_extra"]), 5.0)


# ---------------------------------------------------------------------------
# TestClasificacionProduccionViewGet
# ---------------------------------------------------------------------------

class TestClasificacionProduccionViewGet(TestCase):
    """GET ClasificacionProduccionView retorna 200 con contexto correcto."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = _crear_usuario()

    def _get(self, empresa=EMPRESA, autenticado=True):
        from mpr.views import ClasificacionProduccionView
        request = self.factory.get(reverse("mpr:clasificacion_produccion"))
        if autenticado:
            request.session = {"user": {"id_usuario": 1, "base_empresa": empresa}}
            request.user = self.user
        else:
            request.session = {}
            request.user = MagicMock(is_authenticated=False)
        _add_messages(request)
        return ClasificacionProduccionView.as_view()(request)
    def test_get_200_con_contexto(self):
        resp = self._get()
        self.assertEqual(resp.status_code, 200)

    def test_get_sin_empresa_retorna_grilla_vacia(self):
        resp = self._get(empresa=None)
        self.assertEqual(resp.status_code, 200)

    def test_get_no_autenticado_redirige(self):
        resp = self._get(autenticado=False)
        self.assertEqual(resp.status_code, 302)

    @patch("mpr.services.construir_grilla_clasificacion_produccion")
    def test_default_ver_roster_completo(self, mock_grilla):
        """Sin param ver_roster: se pide roster completo (default)."""
        from mpr.views import ClasificacionProduccionView

        mock_grilla.return_value = {
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
            "aviso_borrador": "",
            "borrador_incompatible": False,
        }
        request = self.factory.get(
            reverse("mpr:clasificacion_produccion"),
            {"fecha": "24/07/2026"},
        )
        request.session = {"user": {"id_usuario": 1, "base_empresa": EMPRESA}}
        request.user = self.user
        _add_messages(request)
        resp = ClasificacionProduccionView.as_view()(request)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(mock_grilla.called)
        self.assertTrue(mock_grilla.call_args.kwargs.get("ver_roster_completo"))
        self.assertIsNone(mock_grilla.call_args.args[2] if len(mock_grilla.call_args.args) > 2 else None)

    @patch("mpr.services.construir_grilla_clasificacion_produccion")
    def test_ver_roster_0_solo_pendiente(self, mock_grilla):
        """ver_roster=0 activa filtro solo pendiente."""
        from mpr.views import ClasificacionProduccionView

        mock_grilla.return_value = {
            "bloques": [],
            "filas": [],
            "filas_vacio": True,
            "hay_filas_editables": False,
            "confirmadas_ocultas": 2,
            "bloqueos": [],
            "requiere_fecha": False,
            "requiere_fecha_turno": False,
            "componentes": [],
            "componentes_vacio": True,
            "tiene_borrador": False,
            "aviso_borrador": "",
            "borrador_incompatible": False,
        }
        request = self.factory.get(
            reverse("mpr:clasificacion_produccion"),
            {"fecha": "24/07/2026", "ver_roster": "0"},
        )
        request.session = {"user": {"id_usuario": 1, "base_empresa": EMPRESA}}
        request.user = self.user
        _add_messages(request)
        resp = ClasificacionProduccionView.as_view()(request)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(mock_grilla.call_args.kwargs.get("ver_roster_completo"))


# ---------------------------------------------------------------------------
# TestRegistrarClasificacionProduccionViewPost
# ---------------------------------------------------------------------------

class TestRegistrarClasificacionProduccionViewPost(TestCase):
    """POST consolidado: parsear + confirmar; sin transferir_stock_lote directo."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = _crear_usuario()

    def _post(self, data, empresa=EMPRESA):
        from mpr.views import RegistrarClasificacionProduccionView
        request = self.factory.post(reverse("mpr:clasificacion_produccion_registrar"), data=data)
        session = {"user": {"id_usuario": 1, "base_empresa": empresa}}
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
    def test_reparto_semi_y_2da_via_confirmar(self, mock_confirmar, mock_lote):
        data = _post_clasif_base(**_post_cc_keys(semi=18, seg2da=2, scrap=0))
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        mock_confirmar.assert_called_once()
        payload = mock_confirmar.call_args.args[3]
        self.assertEqual(payload[42]["semi"], Decimal("18"))
        self.assertEqual(payload[42]["lineas"][0][3], Decimal("2"))
        mock_lote.assert_not_called()
        self.assertEqual(resp._test_session["clasificacion_feedback_modal"]["tipo"], "success")

    @patch("mpr.services.transferir_stock_lote")
    @patch(
        "mpr.services_cc_consolidado.confirmar_cc_consolidado",
        return_value={"ok": [42], "errores": [], "comprobantes": ["A"]},
    )
    def test_reparto_valido_tres_destinos(self, mock_confirmar, mock_lote):
        data = _post_clasif_base(**_post_cc_keys(semi=5, seg2da=2, scrap=1))
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("clasificacion-produccion", resp["Location"])
        payload = mock_confirmar.call_args.args[3]
        self.assertEqual(payload[42]["semi"], Decimal("5"))
        destinos = {ln[2]: ln[3] for ln in payload[42]["lineas"]}
        self.assertEqual(destinos["2da"], Decimal("2"))
        self.assertEqual(destinos["scrap"], Decimal("1"))
        mock_lote.assert_not_called()

    @patch("mpr.services.transferir_stock_lote")
    @patch(
        "mpr.services_cc_consolidado.confirmar_cc_consolidado",
        return_value={
            "ok": [],
            "errores": [(42, "La cantidad total supera el saldo Producción disponible.")],
            "comprobantes": [],
        },
    )
    def test_bloqueo_suma_excede_disponible(self, mock_confirmar, mock_lote):
        """Stock safety: exceso semi+2da+scrap → error feedback, sin lote."""
        data = _post_clasif_base(**_post_cc_keys(semi=100, seg2da=30, scrap=0))
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        mock_confirmar.assert_called_once()
        mock_lote.assert_not_called()
        fb = resp._test_session["clasificacion_feedback_modal"]
        self.assertEqual(fb["tipo"], "error")
        self.assertIn("saldo", fb["mensaje"].lower())

    @patch("mpr.services.transferir_stock_lote")
    @patch(
        "mpr.services_cc_consolidado.confirmar_cc_consolidado",
        return_value={
            "ok": [],
            "errores": [(42, "La cantidad total supera el saldo Producción disponible.")],
            "comprobantes": [],
        },
    )
    def test_hidden_manipulado_server_revalida(self, mock_confirmar, mock_lote):
        data = _post_clasif_base(**_post_cc_keys(semi=0, seg2da=80, scrap=0))
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        mock_confirmar.assert_called_once()
        mock_lote.assert_not_called()

    @patch("mpr.services.transferir_stock_lote")
    @patch(
        "mpr.services_cc_consolidado.confirmar_cc_consolidado",
        return_value={"ok": [42], "errores": [], "comprobantes": ["A"]},
    )
    def test_fecha_se_propaga_al_confirmar(self, mock_confirmar, mock_lote):
        data = _post_clasif_base(**_post_cc_keys(semi=10, seg2da=0, scrap=0))
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(mock_confirmar.call_args.args[2], date(2026, 7, 3))
        mock_lote.assert_not_called()

    @patch("mpr.services.transferir_stock_lote")
    @patch("mpr.services_cc_consolidado.confirmar_cc_consolidado")
    def test_fecha_invalida_bloquea(self, mock_confirmar, mock_lote):
        data = {"semi_42": "5"}
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        mock_confirmar.assert_not_called()
        mock_lote.assert_not_called()

    def test_sin_empresa_redirige(self):
        data = {"fecha": FECHA_OK, "semi_42": "5"}
        resp = self._post(data, empresa=None)
        self.assertEqual(resp.status_code, 302)

    @patch("mpr.services.transferir_stock_lote")
    @patch("mpr.services_cc_consolidado.confirmar_cc_consolidado")
    def test_cantidades_cero_ignoradas(self, mock_confirmar, mock_lote):
        data = _post_clasif_base(**_post_cc_keys(semi=0, seg2da=0, scrap=0))
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        mock_confirmar.assert_not_called()
        mock_lote.assert_not_called()

    @patch("mpr.services.transferir_stock_lote")
    @patch(
        "mpr.services_cc_consolidado.confirmar_cc_consolidado",
        return_value={"ok": [42], "errores": [], "comprobantes": ["A"]},
    )
    def test_semi_explicito_consume_saldo(self, mock_confirmar, mock_lote):
        """Semi consolidado se envía explícito (no auto-atribuible)."""
        data = _post_clasif_base(**_post_cc_keys(semi=25, seg2da=0, scrap=0))
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(mock_confirmar.call_args.args[3][42]["semi"], Decimal("25"))
        mock_lote.assert_not_called()

    @patch("mpr.services.transferir_stock_lote")
    @patch(
        "mpr.services_cc_consolidado.confirmar_cc_consolidado",
        return_value={
            "ok": [],
            "errores": [(42, "La cantidad total supera el saldo Producción disponible.")],
            "comprobantes": [],
        },
    )
    def test_bloqueo_si_supera_saldo_vivo_produccion(self, mock_confirmar, mock_lote):
        data = _post_clasif_base(**_post_cc_keys(semi=200, seg2da=0, scrap=0))
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        mock_lote.assert_not_called()
        self.assertEqual(resp._test_session["clasificacion_feedback_modal"]["tipo"], "error")

    @patch("mpr.services.transferir_stock_lote")
    @patch("mpr.repositories.clasificacion_borrador.upsert_borrador_cc_consolidado")
    @patch("mpr.services_cc_consolidado.confirmar_cc_consolidado")
    def test_post_borrador_no_llama_transferir_stock(self, mock_confirmar, mock_upsert, mock_lote):
        data = _post_clasif_base(accion="borrador", **_post_cc_keys(semi=8, seg2da=2, scrap=0))
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        mock_lote.assert_not_called()
        mock_confirmar.assert_not_called()
        mock_upsert.assert_called_once()
        lineas = mock_upsert.call_args.args[3]
        self.assertTrue(any(float(ln.get("cant_2da") or 0) == 2.0 for ln in lineas))

    @patch("mpr.services.transferir_stock_lote")
    @patch(
        "mpr.services_cc_consolidado.confirmar_cc_consolidado",
        return_value={"ok": [42], "errores": [], "comprobantes": ["A"]},
    )
    def test_post_confirmar_ok_feedback(self, mock_confirmar, mock_lote):
        """Confirmación OK deja feedback para mprShowAviso; borrador se limpia en el servicio."""
        data = _post_clasif_base(**_post_cc_keys(semi=10, seg2da=0, scrap=0))
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        mock_confirmar.assert_called_once()
        mock_lote.assert_not_called()
        self.assertEqual(resp._test_session["clasificacion_feedback_modal"]["tipo"], "success")


class TestClasificacionBorradorRepo(SimpleTestCase):
    """Repositorio borrador CC — upsert, listado y flags."""

    @patch("mpr.repositories.clasificacion_borrador.eliminar_borrador")
    @patch("mpr.repositories.clasificacion_borrador.mysql_cursor")
    def test_upsert_sin_lineas_elimina_borrador(self, mock_cursor_ctx, mock_eliminar):
        from mpr.repositories.clasificacion_borrador import upsert_borrador

        upsert_borrador(EMPRESA, FECHA_OBJ, TURNO_ID, 1, [])
        mock_eliminar.assert_called_once_with(EMPRESA, FECHA_OBJ, TURNO_ID)
        mock_cursor_ctx.assert_not_called()

    @patch("mpr.repositories.clasificacion_borrador.mysql_cursor")
    def test_listar_lineas_borrador_indexa_por_clave(self, mock_cursor_ctx):
        from mpr.repositories.clasificacion_borrador import listar_lineas_borrador

        cursor = mock_cursor_ctx.return_value.__enter__.return_value
        cursor.fetchall.return_value = [{
            "id_mpr_turno": TURNO_ID,
            "id_articulo": 42,
            "id_operario": ID_OPERARIO,
            "id_mpr_maquina": 2,
            "cant_semi": Decimal("6"),
            "cant_2da": Decimal("2"),
            "cant_scrap": Decimal("1"),
        }]
        out = listar_lineas_borrador(EMPRESA, FECHA_OBJ, TURNO_ID)
        self.assertEqual(out[(2, 42, ID_OPERARIO, TURNO_ID)]["semi"], Decimal("6"))
        self.assertEqual(out[(2, 42, ID_OPERARIO, TURNO_ID)]["segunda"], Decimal("2"))
        self.assertEqual(out[(2, 42, ID_OPERARIO, TURNO_ID)]["scrap"], Decimal("1"))

    @patch("mpr.repositories.clasificacion_borrador.mysql_cursor")
    def test_tiene_borrador_true(self, mock_cursor_ctx):
        from mpr.repositories.clasificacion_borrador import tiene_borrador

        cursor = mock_cursor_ctx.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1,)
        self.assertTrue(tiene_borrador(EMPRESA, FECHA_OBJ, TURNO_ID))


class TestConstruirGrillaBorradorPrecarga(TestCase):
    """La grilla precarga borrador 007 (Semi consolidado + 2da/scrap)."""

    @patch("mpr.repositories.clasificacion_borrador.tiene_borrador", return_value=False)
    @patch("mpr.repositories.clasificacion_borrador.tiene_borrador_cc_consolidado", return_value=True)
    @patch("mpr.repositories.clasificacion_borrador.listar_lineas_borrador_cc_consolidado")
    @patch("mpr.repositories.transicion_lote.semi_agregado_por_articulo_fecha", return_value={})
    @patch("mpr.repositories.transicion_lote.clasificado_segunda_scrap_por_celda_fecha", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map(id_art=42))
    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion", return_value={42: {"Produccion": 15.0}})
    def test_precarga_borrador_007(self, _pivot, _fetch, mock_celdas, *_rest):
        mock_celdas.return_value = _celdas_parte_mock(cantidad=15.0)
        mock_listar = _rest[2]
        mock_listar.return_value = [
            {
                "id_articulo": 42,
                "id_operario": None,
                "id_mpr_turno": None,
                "cant_semi": Decimal("6"),
                "cant_2da": Decimal("0"),
                "cant_scrap": Decimal("0"),
            },
            {
                "id_articulo": 42,
                "id_operario": ID_OPERARIO,
                "id_mpr_turno": TURNO_ID,
                "cant_semi": Decimal("0"),
                "cant_2da": Decimal("2"),
                "cant_scrap": Decimal("1"),
            },
        ]
        resultado = construir_grilla_clasificacion_produccion(EMPRESA, FECHA_OBJ)
        self.assertTrue(resultado["tiene_borrador"])
        bloque = resultado["bloques"][0]
        self.assertEqual(bloque["borrador_semi"], Decimal("6"))
        self.assertEqual(bloque["filas"][0]["borrador_segunda"], Decimal("2"))
        self.assertEqual(bloque["filas"][0]["borrador_scrap"], Decimal("1"))


class TestTurnoTieneControlCalidad(SimpleTestCase):
    """Helpers de bloqueo parte por CC."""

    @patch("mpr.repositories.transicion_lote.mysql_cursor")
    def test_turno_tiene_control_calidad_true(self, mock_cursor_ctx):
        from mpr.repositories.transicion_lote import turno_tiene_control_calidad

        cursor = mock_cursor_ctx.return_value.__enter__.return_value
        cursor.fetchall.return_value = [{"id_mpr_turno": 1}]
        self.assertTrue(turno_tiene_control_calidad(EMPRESA, FECHA_OBJ, 1))

    @patch("mpr.repositories.transicion_lote.mysql_cursor")
    def test_turno_tiene_control_calidad_false(self, mock_cursor_ctx):
        from mpr.repositories.transicion_lote import turno_tiene_control_calidad

        cursor = mock_cursor_ctx.return_value.__enter__.return_value
        cursor.fetchall.return_value = []
        self.assertFalse(turno_tiene_control_calidad(EMPRESA, FECHA_OBJ, 2))


class TestRegistrarParteBloqueoControlCalidad(TestCase):
    """registrar_parte_produccion rechaza turnos con CC previa."""

    @patch("mpr.services._validar_planilla_sin_control_calidad")
    def test_registrar_parte_rechaza_si_hay_cc(self, mock_validar):
        from django.core.exceptions import ValidationError
        from mpr.services import registrar_parte_produccion

        mock_validar.return_value = [
            "Esta fecha ya tiene control de calidad registrado. La planilla es de solo lectura."
        ]
        lineas = [{
            "id_articulo": 100,
            "id_operario": 5,
            "cantidad": Decimal("12"),
            "id_mpr_maquina": 10,
            "maquina_nombre": "M1",
            "turno_id": 1,
        }]
        with self.assertRaises(ValidationError) as ctx:
            registrar_parte_produccion(
                EMPRESA,
                FECHA_OBJ,
                None,
                1,
                lineas,
                modo_planilla=True,
            )
        self.assertIn("control de calidad", str(ctx.exception).lower())
        mock_validar.assert_called_once()


# ---------------------------------------------------------------------------
# TestTableroSinPlanchado
# ---------------------------------------------------------------------------

class TestTableroSinPlanchado(SimpleTestCase):
    """Etapa 10: el tablero no muestra Planchado y expone el botón único."""

    def _tpl_html(self, *partes):
        import os
        tpl_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates", *partes,
        )
        with open(tpl_path, encoding="utf-8") as f:
            return f.read()

    def _tablero_html(self):
        return self._tpl_html("mpr", "tablero_produccion.html")

    def test_tablero_sin_columna_planchado(self):
        """El tablero ya no renderiza la columna Planchado."""
        content = self._tablero_html()
        self.assertNotIn("fila.planchado", content)

    def test_tablero_par_columna_enviado_sin_desperdicio(self):
        """Modo Par: columna Enviado (ledger) reemplaza Desperdicio."""
        content = self._tablero_html()
        self.assertIn('data-col="envios"', content)
        self.assertIn("{{ fila.envios_display }}", content)
        self.assertNotIn("Desperdicio", content)
        self.assertNotIn("desperdicio_display", content)

    def test_tablero_boton_unico_clasificacion_produccion(self):
        """El tablero expone Control de calidad vía chrome_nav_flujo (no botones E9)."""
        content = self._tablero_html()
        self.assertIn("mpr/includes/chrome_nav_flujo.html", content)
        chrome = self._tpl_html("mpr", "includes", "chrome_nav_flujo.html")
        self.assertIn("mpr:clasificacion_produccion", chrome)
        self.assertIn("Control de calidad", chrome)
        # Ya no existen los botones separados Inspección/Clasificación (E9).
        self.assertNotIn("mpr:inspeccion_lote", content)
        self.assertNotIn("mpr:clasificacion_lote'", content)

    def test_include_control_calidad_canonico(self):
        """El include canónico apunta a clasificacion_produccion con estilo teal 'Control de calidad'."""
        include = self._tpl_html("mpr", "includes", "btn_control_calidad.html")
        self.assertIn("mpr:clasificacion_produccion", include)
        self.assertIn("Control de calidad", include)
        self.assertIn("bg-teal-600", include)

    def test_url_clasificacion_produccion_resuelve(self):
        url = reverse("mpr:clasificacion_produccion")
        self.assertTrue(url.endswith("/clasificacion-produccion/"))
        url_reg = reverse("mpr:clasificacion_produccion_registrar")
        self.assertTrue(url_reg.endswith("/clasificacion-produccion/registrar/"))

    def test_url_transicion_lote_backward_safe(self):
        """URL mpr:transicion_lote aún resuelve (backward-safe)."""
        url = reverse("mpr:transicion_lote")
        self.assertTrue(url.endswith("/transicion/"))


class TestAtribuibleMultiMaquinaSegunda(SimpleTestCase):
    """Regresión: semi+2da no debe dejar remanente fantasma en otras máquinas."""

    def test_cls_igual_fab_sin_remanente_fantasma(self):
        """Caso real 22/07 art812/op5: 4 máquinas, semi+2da = fab → atribuible 0."""
        from mpr.services import (
            _asignacion_clasificado_por_celda,
            _atribuible_clasificacion_por_celda,
        )

        # Orden de nombre: Máquina 19, 20, 21, 25 (como en producción).
        celdas = {
            (19, 812, 5, 2): {
                "cantidad": Decimal("72"),
                "maquina_nombre": "Maquina 19",
                "operario_nombre": "Op",
                "turno_nombre": "T2",
            },
            (20, 812, 5, 2): {
                "cantidad": Decimal("84"),
                "maquina_nombre": "Maquina 20",
                "operario_nombre": "Op",
                "turno_nombre": "T2",
            },
            (21, 812, 5, 2): {
                "cantidad": Decimal("84"),
                "maquina_nombre": "Maquina 21",
                "operario_nombre": "Op",
                "turno_nombre": "T2",
            },
            (25, 812, 5, 2): {
                "cantidad": Decimal("84"),
                "maquina_nombre": "Maquina 25",
                "operario_nombre": "Op",
                "turno_nombre": "T2",
            },
        }
        desglose = {
            2: {
                (812, 5): {
                    "semi": Decimal("310"),
                    "segunda": Decimal("14"),
                    "scrap": Decimal("0"),
                }
            }
        }
        atr = _atribuible_clasificacion_por_celda(celdas, desglose)
        self.assertEqual(sum(atr.values()), Decimal("0"))
        for rem in atr.values():
            self.assertEqual(rem, Decimal("0"))

        asig = _asignacion_clasificado_por_celda(celdas, desglose)
        total_semi = sum(v["semi"] for v in asig.values())
        total_2da = sum(v["segunda"] for v in asig.values())
        self.assertEqual(total_semi, Decimal("310"))
        self.assertEqual(total_2da, Decimal("14"))
        # Ninguna máquina recibe semi+2da por encima de su fab.
        for (mid, *_rest), dest in asig.items():
            fab = celdas[(mid, 812, 5, 2)]["cantidad"]
            self.assertLessEqual(dest["semi"] + dest["segunda"] + dest["scrap"], fab)

    def test_dos_maquinas_semi_y_2da_completos(self):
        """M1+M2 fab=200; semi=100 + 2da=100 → sin remanente (bug viejo dejaba 100 en M2)."""
        from mpr.services import _atribuible_clasificacion_por_celda

        celdas = {
            (1, 42, 9, 1): {
                "cantidad": Decimal("100"),
                "maquina_nombre": "A",
                "operario_nombre": "Op",
                "turno_nombre": "T1",
            },
            (2, 42, 9, 1): {
                "cantidad": Decimal("100"),
                "maquina_nombre": "B",
                "operario_nombre": "Op",
                "turno_nombre": "T1",
            },
        }
        desglose = {
            1: {
                (42, 9): {
                    "semi": Decimal("100"),
                    "segunda": Decimal("100"),
                    "scrap": Decimal("0"),
                }
            }
        }
        atr = _atribuible_clasificacion_por_celda(celdas, desglose)
        self.assertEqual(sum(atr.values()), Decimal("0"))
        self.assertEqual(atr[(1, 42, 9, 1)], Decimal("0"))
        self.assertEqual(atr[(2, 42, 9, 1)], Decimal("0"))
