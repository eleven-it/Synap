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
        return User.objects.get(uid=uid)
    except User.DoesNotExist:
        return User.objects.create(
            uid=uid,
            email="test_e10@synap.test",
            nombre="Test E10",
            is_superuser=True,
            is_staff=True,
            is_active=True,
        )


def _add_messages(request):
    setattr(request, "_messages", FallbackStorage(request))


# ---------------------------------------------------------------------------
# TestConstruirGrillaClasificacionProduccion
# ---------------------------------------------------------------------------

class TestConstruirGrillaClasificacionProduccion(SimpleTestCase):
    """La grilla lista componentes con saldo en Producción (origen único)."""

    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map(id_art=42))
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    @patch("mpr.services._nombre_tabla", return_value="stock_deposito")
    @patch("mpr.services.mysql_cursor")
    def test_retorna_componente_con_produccion(self, mock_cursor, mock_nombre, mock_pivot, mock_fetch):
        """Con saldo Producción=15 retorna 1 componente con disponible=15."""
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        ctx.fetchall.return_value = [{"id_articulo": 42}]
        ctx.execute = MagicMock()
        mock_cursor.return_value = ctx

        pivot = _pivot_con_produccion(id_art=42, saldo=15.0)
        mock_pivot.return_value = (pivot, pivot)

        resultado = construir_grilla_clasificacion_produccion(EMPRESA)

        self.assertFalse(resultado["componentes_vacio"])
        self.assertEqual(len(resultado["componentes"]), 1)
        comp = resultado["componentes"][0]
        self.assertEqual(comp["id_articulo"], 42)
        self.assertAlmostEqual(comp["disponible"], 15.0)

    @patch("mpr.services._fetch_descripciones_articulo", return_value={})
    @patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({}, {}))
    @patch("mpr.services._nombre_tabla", return_value="stock_deposito")
    @patch("mpr.services.mysql_cursor")
    def test_sin_stock_retorna_vacio(self, mock_cursor, mock_nombre, mock_pivot, mock_fetch):
        """Sin candidatos con saldo>0 retorna componentes_vacio=True."""
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        ctx.fetchall.return_value = []
        ctx.execute = MagicMock()
        mock_cursor.return_value = ctx

        resultado = construir_grilla_clasificacion_produccion(EMPRESA)

        self.assertTrue(resultado["componentes_vacio"])
        self.assertEqual(resultado["componentes"], [])

    def test_base_empresa_vacia_retorna_vacio(self):
        """base_empresa vacía retorna lista vacía sin llamar a MySQL."""
        resultado = construir_grilla_clasificacion_produccion("")
        self.assertTrue(resultado["componentes_vacio"])
        self.assertEqual(resultado["componentes"], [])

    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map(id_art=42))
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    @patch("mpr.services._nombre_tabla", return_value="stock_deposito")
    @patch("mpr.services.mysql_cursor")
    def test_aislacion_por_base_empresa(self, mock_cursor, mock_nombre, mock_pivot, mock_fetch):
        """Solo se consulta el pivot con los ids de la empresa (scope del cursor)."""
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        ctx.fetchall.return_value = [{"id_articulo": 42}]
        ctx.execute = MagicMock()
        mock_cursor.return_value = ctx

        pivot = {
            42: {TIPO_MPR_PRODUCCION: 15.0, TIPO_MPR_2DA_SELECCION: 0.0,
                 TIPO_MPR_SEMI_ELABORADO: 0.0, TIPO_MPR_SCRAP: 0.0},
            77: {TIPO_MPR_PRODUCCION: 99.0, TIPO_MPR_2DA_SELECCION: 0.0,
                 TIPO_MPR_SEMI_ELABORADO: 0.0, TIPO_MPR_SCRAP: 0.0},
        }
        mock_pivot.return_value = (pivot, pivot)

        resultado = construir_grilla_clasificacion_produccion(EMPRESA)

        self.assertEqual(mock_cursor.call_args.args[0], EMPRESA)
        pivot_ids = mock_pivot.call_args.args[1]
        self.assertIn(42, pivot_ids)
        self.assertNotIn(77, pivot_ids)
        ids_resultado = [c["id_articulo"] for c in resultado["componentes"]]
        self.assertEqual(ids_resultado, [42])


# ---------------------------------------------------------------------------
# TestTransferirStockLoteFecha
# ---------------------------------------------------------------------------

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

    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map())
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    @patch("mpr.services._nombre_tabla", return_value="stock_deposito")
    @patch("mpr.services.mysql_cursor")
    def test_get_200_con_contexto(self, mock_cursor, mock_nombre, mock_pivot, mock_fetch):
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        ctx.fetchall.return_value = [{"id_articulo": 42}]
        ctx.execute = MagicMock()
        mock_cursor.return_value = ctx
        pivot = _pivot_con_produccion()
        mock_pivot.return_value = (pivot, pivot)

        resp = self._get()
        self.assertEqual(resp.status_code, 200)

    def test_get_sin_empresa_retorna_grilla_vacia(self):
        resp = self._get(empresa=None)
        self.assertEqual(resp.status_code, 200)

    def test_get_no_autenticado_redirige(self):
        resp = self._get(autenticado=False)
        self.assertEqual(resp.status_code, 302)


# ---------------------------------------------------------------------------
# TestRegistrarClasificacionProduccionViewPost
# ---------------------------------------------------------------------------

class TestRegistrarClasificacionProduccionViewPost(TestCase):
    """POST RegistrarClasificacionProduccionView — reparto válido y bloqueos."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = _crear_usuario()

    def _post(self, data, empresa=EMPRESA):
        from mpr.views import RegistrarClasificacionProduccionView
        request = self.factory.post(reverse("mpr:clasificacion_produccion_registrar"), data=data)
        request.session = {"user": {"id_usuario": 1, "base_empresa": empresa}}
        request.user = self.user
        _add_messages(request)
        return RegistrarClasificacionProduccionView.as_view()(request)

    @patch("mpr.services.transferir_stock_lote", return_value={"exitosas": 3, "fallidas": 0, "errores": [], "comprobantes": ["A", "B", "C"]})
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_reparto_docenas_unidades(self, mock_pivot, mock_lote):
        """1 docena + 5 u. semi, 0 doc + 2 u. 2da → 17 y 2 unidades al lote."""
        pivot = _pivot_con_produccion(id_art=42, saldo=20.0)
        mock_pivot.return_value = (pivot, pivot)

        data = {
            "fecha": FECHA_OK,
            "semi_42_docenas": "1",
            "semi_42_unidades": "5",
            "seg2da_42_docenas": "0",
            "seg2da_42_unidades": "2",
            "scrap_42_docenas": "0",
            "scrap_42_unidades": "0",
        }
        resp = self._post(data)

        self.assertEqual(resp.status_code, 302)
        items = mock_lote.call_args.args[2]
        self.assertEqual(len(items), 2)
        por_destino = {i["tipo_destino"]: float(i["cantidad"]) for i in items}
        self.assertEqual(por_destino[TIPO_MPR_SEMI_ELABORADO], 17.0)
        self.assertEqual(por_destino[TIPO_MPR_2DA_SELECCION], 2.0)

    @patch("mpr.services.transferir_stock_lote", return_value={"exitosas": 3, "fallidas": 0, "errores": [], "comprobantes": ["A", "B", "C"]})
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_reparto_valido_tres_destinos(self, mock_pivot, mock_lote):
        """semi=5, 2da=2, scrap=1, disponible=8 → 3 items enviados al lote."""
        pivot = _pivot_con_produccion(id_art=42, saldo=8.0)
        mock_pivot.return_value = (pivot, pivot)

        data = {"fecha": FECHA_OK, "semi_42": "5", "seg2da_42": "2", "scrap_42": "1", "disponible_42": "8"}
        resp = self._post(data)

        self.assertEqual(resp.status_code, 302)
        self.assertIn("clasificacion-produccion", resp["Location"])
        items = mock_lote.call_args.args[2]
        self.assertEqual(len(items), 3)
        destinos = {i["tipo_destino"] for i in items}
        self.assertEqual(destinos, {TIPO_MPR_SEMI_ELABORADO, TIPO_MPR_2DA_SELECCION, TIPO_MPR_SCRAP})

    @patch("mpr.services.transferir_stock_lote")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_bloqueo_suma_excede_disponible(self, mock_pivot, mock_lote):
        """semi=4, 2da=3, scrap=1 (=8) > disponible_real=5 → BLOQUEO, sin lote."""
        pivot = _pivot_con_produccion(id_art=42, saldo=5.0)
        mock_pivot.return_value = (pivot, pivot)

        data = {"fecha": FECHA_OK, "semi_42": "4", "seg2da_42": "3", "scrap_42": "1", "disponible_42": "5"}
        resp = self._post(data)

        self.assertEqual(resp.status_code, 302)
        mock_lote.assert_not_called()

    @patch("mpr.services.transferir_stock_lote")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_hidden_manipulado_server_revalida(self, mock_pivot, mock_lote):
        """Hidden disponible_42=100 pero stock real=5 → bloqueo sin lote."""
        pivot = _pivot_con_produccion(id_art=42, saldo=5.0)
        mock_pivot.return_value = (pivot, pivot)

        data = {"fecha": FECHA_OK, "semi_42": "80", "disponible_42": "100"}
        resp = self._post(data)

        self.assertEqual(resp.status_code, 302)
        mock_lote.assert_not_called()

    @patch("mpr.services.transferir_stock_lote", return_value={"exitosas": 1, "fallidas": 0, "errores": [], "comprobantes": ["A"]})
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_fecha_se_propaga_al_lote(self, mock_pivot, mock_lote):
        """La fecha dd/MM/yyyy se parsea y se pasa como date al servicio de lote."""
        pivot = _pivot_con_produccion(id_art=42, saldo=10.0)
        mock_pivot.return_value = (pivot, pivot)

        data = {"fecha": "03/07/2026", "semi_42": "5"}
        resp = self._post(data)

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(mock_lote.call_args.kwargs["fecha"], date(2026, 7, 3))

    @patch("mpr.services.transferir_stock_lote")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_fecha_invalida_bloquea(self, mock_pivot, mock_lote):
        """Sin fecha (o inválida) → redirige sin invocar el servicio de lote."""
        pivot = _pivot_con_produccion(id_art=42, saldo=10.0)
        mock_pivot.return_value = (pivot, pivot)

        data = {"semi_42": "5"}  # sin fecha
        resp = self._post(data)

        self.assertEqual(resp.status_code, 302)
        mock_lote.assert_not_called()

    def test_sin_empresa_redirige(self):
        data = {"fecha": FECHA_OK, "semi_42": "5"}
        resp = self._post(data, empresa=None)
        self.assertEqual(resp.status_code, 302)

    @patch("mpr.services.transferir_stock_lote")
    @patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({}, {}))
    def test_cantidades_cero_ignoradas(self, mock_pivot, mock_lote):
        """Cantidades=0 → sin items → warning, sin lote."""
        data = {"fecha": FECHA_OK, "semi_42": "0", "seg2da_42": "0", "scrap_42": "0"}
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        mock_lote.assert_not_called()


# ---------------------------------------------------------------------------
# TestTableroSinPlanchado
# ---------------------------------------------------------------------------

class TestTableroSinPlanchado(SimpleTestCase):
    """Etapa 10: el tablero no muestra Planchado y expone el botón único."""

    def _tablero_html(self):
        import os
        tpl_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates", "mpr", "tablero_produccion.html",
        )
        with open(tpl_path, encoding="utf-8") as f:
            return f.read()

    def test_tablero_sin_columna_planchado(self):
        """El tablero ya no renderiza la columna Planchado."""
        content = self._tablero_html()
        self.assertNotIn("fila.planchado", content)

    def test_tablero_boton_unico_clasificacion_produccion(self):
        """El tablero expone el botón global 'Clasificación de producción'."""
        content = self._tablero_html()
        self.assertIn("mpr:clasificacion_produccion", content)
        self.assertIn("Clasificación de producción", content)
        # Ya no existen los botones separados Inspección/Clasificación (E9).
        self.assertNotIn("mpr:inspeccion_lote", content)
        self.assertNotIn("mpr:clasificacion_lote'", content)

    def test_url_clasificacion_produccion_resuelve(self):
        url = reverse("mpr:clasificacion_produccion")
        self.assertTrue(url.endswith("/clasificacion-produccion/"))
        url_reg = reverse("mpr:clasificacion_produccion_registrar")
        self.assertTrue(url_reg.endswith("/clasificacion-produccion/registrar/"))

    def test_url_transicion_lote_backward_safe(self):
        """URL mpr:transicion_lote aún resuelve (backward-safe)."""
        url = reverse("mpr:transicion_lote")
        self.assertTrue(url.endswith("/transicion/"))
