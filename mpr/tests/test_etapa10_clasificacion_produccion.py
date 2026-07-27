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
    data = {"fecha": FECHA_OK, "turno_id": str(TURNO_ID)}
    data.update(extra)
    return data


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
    """La grilla lista filas (artículo × operario) con pendiente de clasificación."""
    def test_sin_fecha_requiere_seleccion(self):
        resultado = construir_grilla_clasificacion_produccion(EMPRESA)
        self.assertTrue(resultado["requiere_fecha"])
        self.assertTrue(resultado["requiere_fecha_turno"])
        self.assertEqual(resultado["filas"], [])
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map(id_art=42))
    def test_grilla_sin_turno_lista_filas(self, _fetch, mock_celdas, _cls, _desglose):
        mock_celdas.return_value = _celdas_parte_mock(cantidad=15.0)
        resultado = construir_grilla_clasificacion_produccion(EMPRESA, FECHA_OBJ)
        self.assertFalse(resultado["filas_vacio"])
        self.assertEqual(len(resultado["filas"]), 1)
        self.assertEqual(resultado["filas"][0]["id_mpr_turno"], TURNO_ID)
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map(id_art=42))
    def test_con_turno_id_filtra_acumular(self, _fetch, mock_celdas, _cls, _desglose):
        mock_celdas.return_value = _celdas_parte_mock(cantidad=10.0)
        construir_grilla_clasificacion_produccion(EMPRESA, FECHA_OBJ, TURNO_ID)
        mock_celdas.assert_called_once_with(EMPRESA, FECHA_OBJ, TURNO_ID)
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map(id_art=42))
    def test_rowspan_maquina_y_articulo_coherentes(self, _fetch, mock_celdas, _cls, _desglose):
        mock_celdas.return_value = {
            (1, 42, ID_OPERARIO, TURNO_ID): {
                "cantidad": Decimal("10"),
                "operario_nombre": "Op A",
                "maquina_nombre": "1",
                "turno_nombre": "Mañana",
            },
            (1, 43, ID_OPERARIO, TURNO_ID): {
                "cantidad": Decimal("5"),
                "operario_nombre": "Op A",
                "maquina_nombre": "1",
                "turno_nombre": "Mañana",
            },
        }
        resultado = construir_grilla_clasificacion_produccion(EMPRESA, FECHA_OBJ, TURNO_ID)
        filas = resultado["filas"]
        self.assertEqual(len(filas), 2)
        self.assertTrue(filas[0]["show_maquina"])
        self.assertEqual(filas[0]["rowspan_maquina"], 2)
        self.assertFalse(filas[1]["show_maquina"])
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map(id_art=42))
    @patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=(_pivot_con_produccion(), _pivot_con_produccion()))
    def test_retorna_fila_con_pendiente_operario(self, _pivot, _fetch, mock_celdas, _cls, _desglose):
        mock_celdas.return_value = _celdas_parte_mock(cantidad=15.0)
        resultado = construir_grilla_clasificacion_produccion(EMPRESA, FECHA_OBJ, TURNO_ID)
        self.assertFalse(resultado["filas_vacio"])
        self.assertEqual(len(resultado["filas"]), 1)
        fila = resultado["filas"][0]
        self.assertEqual(fila["id_articulo"], 42)
        self.assertEqual(fila["id_operario"], ID_OPERARIO)
        self.assertAlmostEqual(fila["disponible"], 15.0)
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno", return_value={})
    def test_sin_parte_retorna_vacio(self, *_mocks):
        resultado = construir_grilla_clasificacion_produccion(EMPRESA, FECHA_OBJ, TURNO_ID)
        self.assertTrue(resultado["filas_vacio"])
        self.assertEqual(resultado["filas"], [])

    def test_base_empresa_vacia_retorna_vacio(self):
        resultado = construir_grilla_clasificacion_produccion("")
        self.assertTrue(resultado["filas_vacio"])
        self.assertEqual(resultado["filas"], [])
    @patch(
        "mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno",
        return_value={(42, ID_OPERARIO): {"semi": Decimal("6"), "segunda": Decimal("0"), "scrap": Decimal("0")}},
    )
    @patch(
        "mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno",
        return_value={(42, ID_OPERARIO): Decimal("6")},
    )
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map(id_art=42))
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_pendiente_resta_clasificado_previo(self, mock_pivot, _fetch, mock_celdas, _cls, _desglose):
        mock_celdas.return_value = _celdas_parte_mock(cantidad=15.0)
        pivot = _pivot_con_produccion(id_art=42, saldo=15.0)
        mock_pivot.return_value = (pivot, pivot)
        resultado = construir_grilla_clasificacion_produccion(EMPRESA, FECHA_OBJ, TURNO_ID)
        # atribuible=9 + extra_pool=6 (stock 15 − atribuible 9)
        self.assertAlmostEqual(resultado["filas"][0]["base_clasificable"], 15.0)
        self.assertAlmostEqual(resultado["filas"][0]["disponible"], 15.0)
        self.assertAlmostEqual(resultado["filas"][0]["parte"], 15.0)
        self.assertAlmostEqual(resultado["filas"][0]["extra_disponible"], 6.0)
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map(id_art=42))
    @patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=(_pivot_con_produccion(saldo=24.0), {}))
    def test_grilla_expone_parte_y_base_editable(self, _pivot, _fetch, mock_celdas, _cls, _desglose):
        mock_celdas.return_value = _celdas_parte_mock(cantidad=24.0)
        resultado = construir_grilla_clasificacion_produccion(EMPRESA, FECHA_OBJ, TURNO_ID)
        fila = resultado["filas"][0]
        self.assertAlmostEqual(fila["parte"], 24.0)
        self.assertAlmostEqual(fila["base_clasificable"], 24.0)
        self.assertEqual(fila["ini_seg2da"], 0)
        self.assertEqual(fila["ini_scrap"], 0)
        self.assertFalse(fila["solo_lectura"])
    @patch(
        "mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno",
        return_value={(42, ID_OPERARIO): {"semi": Decimal("15"), "segunda": Decimal("0"), "scrap": Decimal("0")}},
    )
    @patch(
        "mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno",
        return_value={(42, ID_OPERARIO): Decimal("15")},
    )
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map(id_art=42))
    @patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=(_pivot_con_produccion(saldo=0.0), {}))
    def test_fila_completa_solo_lectura_sin_extra(self, _pivot, _fetch, mock_celdas, _cls, _desglose):
        mock_celdas.return_value = _celdas_parte_mock(cantidad=15.0)
        resultado = construir_grilla_clasificacion_produccion(
            EMPRESA, FECHA_OBJ, TURNO_ID, ver_roster_completo=True,
        )
        fila = resultado["filas"][0]
        self.assertTrue(fila["solo_lectura"])
        self.assertEqual(fila["ini_semi"], 15)
        self.assertAlmostEqual(fila["base_clasificable"], 0.0)

    @patch(
        "mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno",
        return_value={(42, ID_OPERARIO): {"semi": Decimal("15"), "segunda": Decimal("0"), "scrap": Decimal("0")}},
    )
    @patch(
        "mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno",
        return_value={(42, ID_OPERARIO): Decimal("15")},
    )
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map(id_art=42))
    @patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=(_pivot_con_produccion(saldo=30.0), {}))
    def test_fila_parte_completo_editable_con_extra_stock(self, _pivot, _fetch, mock_celdas, _cls, _desglose):
        """Parte 100 % clasificado pero hay stock Prod extra → fila editable."""
        mock_celdas.return_value = _celdas_parte_mock(cantidad=15.0)
        resultado = construir_grilla_clasificacion_produccion(EMPRESA, FECHA_OBJ, TURNO_ID)
        fila = resultado["filas"][0]
        self.assertFalse(fila["solo_lectura"])
        self.assertAlmostEqual(fila["atribuible_parte"], 0.0)
        self.assertAlmostEqual(fila["extra_disponible"], 30.0)
        self.assertAlmostEqual(fila["max_clasificable"], 30.0)


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
    @patch("mpr.services.listar_turnos", return_value=[])
    def test_get_200_con_contexto(self, _turnos):
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
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_reparto_docenas_unidades(self, mock_pivot, mock_celdas, _cls, _desglose, mock_lote):
        """2 u. 2da → semi calculado 18 y 2 unidades al lote."""
        mock_celdas.return_value = _celdas_parte_mock(cantidad=20.0)
        pivot = _pivot_con_produccion(id_art=42, saldo=20.0)
        mock_pivot.return_value = (pivot, pivot)

        data = _post_clasif_base(
            **{
                f"seg2da_42_op_{ID_OPERARIO}_docenas": "0",
                f"seg2da_42_op_{ID_OPERARIO}_unidades": "2",
                f"scrap_42_op_{ID_OPERARIO}_docenas": "0",
                f"scrap_42_op_{ID_OPERARIO}_unidades": "0",
            }
        )
        resp = self._post(data)

        self.assertEqual(resp.status_code, 302)
        items = mock_lote.call_args.args[2]
        self.assertEqual(len(items), 2)
        por_destino = {i["tipo_destino"]: float(i["cantidad"]) for i in items}
        self.assertEqual(por_destino[TIPO_MPR_SEMI_ELABORADO], 18.0)
        self.assertEqual(por_destino[TIPO_MPR_2DA_SELECCION], 2.0)
        self.assertEqual(items[0]["id_operario"], ID_OPERARIO)

    @patch("mpr.services.transferir_stock_lote", return_value={"exitosas": 1, "fallidas": 0, "errores": [], "comprobantes": ["A"]})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_post_con_turno_maq_en_names(self, mock_pivot, mock_celdas, _cls, _desglose, mock_lote):
        """Sin 2da/scrap el servidor clasifica todo el atribuible como semi."""
        mock_celdas.return_value = _celdas_parte_mock(cantidad=10.0, id_maq=2)
        pivot = _pivot_con_produccion(id_art=42, saldo=10.0)
        mock_pivot.return_value = (pivot, pivot)

        data = _post_clasif_base(
            **{
                f"seg2da_42_op_{ID_OPERARIO}_turno_{TURNO_ID}_maq_2_docenas": "0",
                f"seg2da_42_op_{ID_OPERARIO}_turno_{TURNO_ID}_maq_2_unidades": "0",
            }
        )
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        mock_lote.assert_called_once()
        items = mock_lote.call_args.args[2]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id_mpr_turno"], TURNO_ID)
        self.assertEqual(float(items[0]["cantidad"]), 10.0)

    @patch("mpr.services.transferir_stock_lote", return_value={"exitosas": 3, "fallidas": 0, "errores": [], "comprobantes": ["A", "B", "C"]})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_reparto_valido_tres_destinos(self, mock_pivot, mock_celdas, _cls, _desglose, mock_lote):
        """2da=2, scrap=1, atribuible=8 → semi=5 calculado server-side."""
        mock_celdas.return_value = _celdas_parte_mock(cantidad=8.0)
        pivot = _pivot_con_produccion(id_art=42, saldo=8.0)
        mock_pivot.return_value = (pivot, pivot)

        data = _post_clasif_base(
            **{
                f"seg2da_42_op_{ID_OPERARIO}": "2",
                f"scrap_42_op_{ID_OPERARIO}": "1",
            }
        )
        resp = self._post(data)

        self.assertEqual(resp.status_code, 302)
        self.assertIn("clasificacion-produccion", resp["Location"])
        items = mock_lote.call_args.args[2]
        self.assertEqual(len(items), 3)
        destinos = {i["tipo_destino"]: float(i["cantidad"]) for i in items}
        self.assertEqual(destinos[TIPO_MPR_SEMI_ELABORADO], 5.0)
        self.assertEqual(destinos[TIPO_MPR_2DA_SELECCION], 2.0)
        self.assertEqual(destinos[TIPO_MPR_SCRAP], 1.0)

    @patch("mpr.services.transferir_stock_lote")
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_bloqueo_suma_excede_disponible(self, mock_pivot, mock_celdas, _cls, _desglose, mock_lote):
        """2da=3, scrap=3 (=6) > atribuible=5 → BLOQUEO, sin lote."""
        mock_celdas.return_value = _celdas_parte_mock(cantidad=5.0)
        pivot = _pivot_con_produccion(id_art=42, saldo=5.0)
        mock_pivot.return_value = (pivot, pivot)

        data = _post_clasif_base(
            **{
                f"seg2da_42_op_{ID_OPERARIO}": "3",
                f"scrap_42_op_{ID_OPERARIO}": "3",
            }
        )
        resp = self._post(data)

        self.assertEqual(resp.status_code, 302)
        mock_lote.assert_not_called()

    @patch("mpr.services.transferir_stock_lote")
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_hidden_manipulado_server_revalida(self, mock_pivot, mock_celdas, _cls, _desglose, mock_lote):
        """Atribuible=5 pero POST pide 80 en 2da → bloqueo sin lote."""
        mock_celdas.return_value = _celdas_parte_mock(cantidad=5.0)
        pivot = _pivot_con_produccion(id_art=42, saldo=5.0)
        mock_pivot.return_value = (pivot, pivot)

        data = _post_clasif_base(**{f"seg2da_42_op_{ID_OPERARIO}": "80"})
        resp = self._post(data)

        self.assertEqual(resp.status_code, 302)
        mock_lote.assert_not_called()

    @patch("mpr.services.transferir_stock_lote", return_value={"exitosas": 1, "fallidas": 0, "errores": [], "comprobantes": ["A"]})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_fecha_se_propaga_al_lote(self, mock_pivot, mock_celdas, _cls, _desglose, mock_lote):
        """La fecha dd/MM/yyyy se parsea y se pasa como date al servicio de lote."""
        mock_celdas.return_value = _celdas_parte_mock(cantidad=10.0)
        pivot = _pivot_con_produccion(id_art=42, saldo=10.0)
        mock_pivot.return_value = (pivot, pivot)

        data = _post_clasif_base(
            **{
                f"seg2da_42_op_{ID_OPERARIO}": "0",
                f"scrap_42_op_{ID_OPERARIO}": "0",
            }
        )
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
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno", return_value={})
    def test_cantidades_cero_ignoradas(self, _celdas, _cls, _desglose, mock_lote):
        """Cantidades=0 → sin items → warning, sin lote."""
        data = _post_clasif_base(
            **{
                f"semi_42_op_{ID_OPERARIO}": "0",
                f"seg2da_42_op_{ID_OPERARIO}": "0",
                f"scrap_42_op_{ID_OPERARIO}": "0",
            }
        )
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        mock_lote.assert_not_called()

    @patch(
        "mpr.services.transferir_stock_lote",
        return_value={"exitosas": 1, "fallidas": 0, "errores": [], "comprobantes": ["A"]},
    )
    @patch(
        "mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno",
        return_value={(42, ID_OPERARIO): {"semi": Decimal("190"), "segunda": Decimal("0"), "scrap": Decimal("0")}},
    )
    @patch(
        "mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno",
        return_value={(42, ID_OPERARIO): Decimal("190")},
    )
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_clasificado_previo_consumido_no_bloquea(self, mock_pivot, mock_celdas, _cls, _desglose, mock_lote):
        """Regresión: atribuible=10 con saldo vivo Producción=10 clasifica 10 como semi."""
        mock_celdas.return_value = _celdas_parte_mock(cantidad=200.0)
        pivot = _pivot_con_produccion(id_art=42, saldo=10.0)
        mock_pivot.return_value = (pivot, pivot)

        data = _post_clasif_base(
            **{
                f"seg2da_42_op_{ID_OPERARIO}": "0",
                f"scrap_42_op_{ID_OPERARIO}": "0",
            }
        )
        resp = self._post(data)

        self.assertEqual(resp.status_code, 302)
        mock_lote.assert_called_once()
        items = mock_lote.call_args.args[2]
        self.assertEqual(len(items), 1)
        self.assertEqual(float(items[0]["cantidad"]), 10.0)
        self.assertEqual(items[0]["tipo_destino"], TIPO_MPR_SEMI_ELABORADO)

    @patch("mpr.services.transferir_stock_lote")
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_bloqueo_si_supera_saldo_vivo_produccion(self, mock_pivot, mock_celdas, _cls, _desglose, mock_lote):
        """La guarda física sigue vigente: atribuible=200 pero saldo vivo=10 → no lote."""
        mock_celdas.return_value = _celdas_parte_mock(cantidad=200.0)
        pivot = _pivot_con_produccion(id_art=42, saldo=10.0)
        mock_pivot.return_value = (pivot, pivot)

        data = _post_clasif_base(
            **{
                f"seg2da_42_op_{ID_OPERARIO}": "0",
                f"scrap_42_op_{ID_OPERARIO}": "0",
            }
        )
        resp = self._post(data)

        self.assertEqual(resp.status_code, 302)
        mock_lote.assert_not_called()

    @patch("mpr.services.transferir_stock_lote", return_value={"exitosas": 1, "fallidas": 0, "errores": [], "comprobantes": ["A"]})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_clasifica_mas_que_parte_con_stock_extra(self, mock_pivot, mock_celdas, _cls, _desglose, mock_lote):
        """Parte=10, stock Prod=25 → puede clasificar hasta 25 como semi."""
        mock_celdas.return_value = _celdas_parte_mock(cantidad=10.0)
        pivot = _pivot_con_produccion(id_art=42, saldo=25.0)
        mock_pivot.return_value = (pivot, pivot)
        data = _post_clasif_base(
            **{
                f"seg2da_42_op_{ID_OPERARIO}": "0",
                f"scrap_42_op_{ID_OPERARIO}": "0",
            }
        )
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        items = mock_lote.call_args.args[2]
        self.assertEqual(len(items), 1)
        self.assertEqual(float(items[0]["cantidad"]), 25.0)
        self.assertEqual(float(items[0]["cantidad_extra"]), 15.0)

    @patch("mpr.services.transferir_stock_lote")
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_desglose_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    def test_bloqueo_excede_tope_fila_con_extra(self, mock_pivot, mock_celdas, _cls, _desglose, mock_lote):
        """Parte=10, stock=25 pero pide 2da=30 → bloqueo por tope fila."""
        mock_celdas.return_value = _celdas_parte_mock(cantidad=10.0)
        pivot = _pivot_con_produccion(id_art=42, saldo=25.0)
        mock_pivot.return_value = (pivot, pivot)
        data = _post_clasif_base(**{f"seg2da_42_op_{ID_OPERARIO}": "30"})
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        mock_lote.assert_not_called()


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

    @patch("mpr.services._validar_turnos_parte_sin_control_calidad")
    def test_registrar_parte_rechaza_si_hay_cc(self, mock_validar):
        from django.core.exceptions import ValidationError
        from mpr.services import registrar_parte_produccion

        mock_validar.return_value = [
            "El turno Mañana ya tiene control de calidad registrado y no se puede modificar el parte."
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
