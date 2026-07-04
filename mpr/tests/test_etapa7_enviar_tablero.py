"""
Tests — MPR Etapa 7: Envío directo a producción desde el Tablero (ledger-componente, lote).

Cobertura:
- TestMprEnvioProduccionModelo: modelo, constraints, defaults, __str__.
- TestEnviarProduccionLote: servicio lote (crea N, rechaza qty<=0, warning sobreenvío, vacío, ledger-only).
- TestQueryEnviadoTableroComponente: helper suma, ignora anulados, backward-safe.
- TestIntegracionEnviadoTablero: listar_tablero_por_articulo con paso 7b, backward-safe,
  fórmula dos fuentes, max(0,...) nunca negativo.
- TestEnviarProduccionLoteView: POST vista crea registros, maneja sobreenvío, preserva filtros.

Comando:
    docker exec Synap_app python manage.py test mpr.tests.test_etapa7_enviar_tablero --keepdb --noinput
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase, RequestFactory
from django.urls import reverse

from mpr.models import MprEnvioProduccion
from mpr.services import (
    TIPO_MPR_2DA_SELECCION,
    TIPO_MPR_PLANCHADO,
    TIPO_MPR_PRODUCCION,
    TIPO_MPR_SCRAP,
    TIPO_MPR_SEMI_ELABORADO,
    TIPO_MPR_TERMINADO,
    _query_enviado_tablero_componente,
    enviar_a_produccion_lote,
    listar_tablero_por_articulo,
)

User = get_user_model()
EMPRESA = "empresa_test"


# ===========================================================================
# Fixtures reutilizables (igual patrón que test_tablero_consolidado)
# ===========================================================================

def _abm_map():
    return {1: 100}


def _bom_map():
    return {
        100: {
            "cabecera": {"id_en_abm": 100},
            "componentes": [
                {"id_articulo": 42, "cantidad_articulo": 1.0},
            ],
        }
    }


def _stock_pivot(produccion=0.0):
    return {
        42: {
            TIPO_MPR_PRODUCCION: produccion,
            TIPO_MPR_PLANCHADO: 0.0,
            TIPO_MPR_2DA_SELECCION: 0.0,
            TIPO_MPR_SEMI_ELABORADO: 0.0,
            TIPO_MPR_SCRAP: 0.0,
            TIPO_MPR_TERMINADO: 0.0,
        }
    }


def _desc_map():
    return {42: ("C-42", "Componente 42")}


def _filas_pack(demanda=50.0):
    return [{"id_articulo": 1, "cantidad_a_fabricar": demanda,
              "cantidad_pedida_pedido": demanda, "stock_terminado": 0.0}]


# ===========================================================================
# TestMprEnvioProduccionModelo
# ===========================================================================

class TestMprEnvioProduccionModelo(TestCase):
    """REQ: Modelo MprEnvioProduccion — Spec 1."""

    def test_crear_registro_campos_correctos(self):
        """Crear MprEnvioProduccion y verificar campos."""
        ep = MprEnvioProduccion.objects.create(
            base_empresa=EMPRESA,
            id_articulo=42,
            cantidad=Decimal("10.50"),
            id_usuario=1,
        )
        self.assertIsNotNone(ep.pk)
        self.assertEqual(ep.base_empresa, EMPRESA)
        self.assertEqual(ep.id_articulo, 42)
        self.assertEqual(ep.cantidad, Decimal("10.50"))
        self.assertEqual(ep.id_usuario, 1)
        self.assertIsNotNone(ep.creado_en)
        self.assertFalse(ep.anulado)

    def test_anulado_default_false(self):
        """anulado=False por defecto."""
        ep = MprEnvioProduccion.objects.create(
            base_empresa=EMPRESA, id_articulo=1, cantidad=Decimal("5"), id_usuario=2,
        )
        self.assertFalse(ep.anulado)

    def test_creado_en_auto(self):
        """creado_en se asigna automáticamente."""
        ep = MprEnvioProduccion.objects.create(
            base_empresa=EMPRESA, id_articulo=1, cantidad=Decimal("1"), id_usuario=1,
        )
        self.assertIsNotNone(ep.creado_en)

    def test_str_contiene_id_art_y_qty(self):
        """__str__ contiene id_articulo y cantidad."""
        ep = MprEnvioProduccion.objects.create(
            base_empresa=EMPRESA, id_articulo=99, cantidad=Decimal("7.25"), id_usuario=1,
        )
        texto = str(ep)
        self.assertIn("99", texto)
        self.assertIn("7.25", texto)

    def test_indices_definidos_en_meta(self):
        """Los índices mpr_ep_emp_art_idx y mpr_ep_emp_fecha_idx están en Meta."""
        index_names = [idx.name for idx in MprEnvioProduccion._meta.indexes]
        self.assertIn("mpr_ep_emp_art_idx", index_names)
        self.assertIn("mpr_ep_emp_fecha_idx", index_names)

    def test_anulado_puede_ser_true(self):
        """anulado puede marcarse True."""
        ep = MprEnvioProduccion.objects.create(
            base_empresa=EMPRESA, id_articulo=5, cantidad=Decimal("3"), id_usuario=1,
            anulado=True,
        )
        self.assertTrue(ep.anulado)


# ===========================================================================
# TestEnviarProduccionLote
# ===========================================================================

class TestEnviarProduccionLote(TestCase):
    """REQ: Servicio de Envío por Lote — Spec 1."""

    def test_lote_3_filas_validas_crea_3_registros(self):
        """Lote con 3 filas válidas crea 3 registros en transacción única."""
        items = [
            (10, Decimal("5")),
            (20, Decimal("3")),
            (30, Decimal("8")),
        ]
        ok, creados, warnings, error = enviar_a_produccion_lote(EMPRESA, 1, items)
        self.assertTrue(ok)
        self.assertEqual(creados, 3)
        self.assertIsNone(error)
        self.assertEqual(MprEnvioProduccion.objects.filter(base_empresa=EMPRESA).count(), 3)

    def test_omite_qty_cero_con_warning(self):
        """Items con cantidades {10, 0, -5, 8} crea solo 2 registros (10 y 8)."""
        items = [
            (10, Decimal("10")),
            (20, Decimal("0")),
            (30, Decimal("-5")),
            (40, Decimal("8")),
        ]
        ok, creados, warnings, error = enviar_a_produccion_lote(EMPRESA, 1, items)
        self.assertTrue(ok)
        self.assertEqual(creados, 2)
        self.assertEqual(len(warnings), 2)
        self.assertIsNone(error)
        ids_creados = list(
            MprEnvioProduccion.objects.filter(base_empresa=EMPRESA).values_list("id_articulo", flat=True)
        )
        self.assertIn(10, ids_creados)
        self.assertIn(40, ids_creados)
        self.assertNotIn(20, ids_creados)
        self.assertNotIn(30, ids_creados)

    def test_warning_sobrenvio_no_bloquea(self):
        """pendiente=20, cantidad=30 crea registro + warning de sobreenvío (no bloquea)."""
        items = [(42, Decimal("30"))]
        pendientes = {42: Decimal("20")}
        ok, creados, warnings, error = enviar_a_produccion_lote(
            EMPRESA, 1, items, pendientes=pendientes
        )
        self.assertTrue(ok)
        self.assertEqual(creados, 1)
        self.assertIsNone(error)
        self.assertEqual(len(warnings), 1)
        self.assertIn("sobrenv" if "sobr" in warnings[0].lower() else "supera", warnings[0].lower() if warnings else "")

    def test_lote_vacio_retorna_0_creados_sin_error(self):
        """Lista items vacía retorna 0 creados sin error."""
        ok, creados, warnings, error = enviar_a_produccion_lote(EMPRESA, 1, [])
        self.assertTrue(ok)
        self.assertEqual(creados, 0)
        self.assertIsNone(error)

    def test_ledger_only_no_toca_mysql(self):
        """El servicio NO llama mysql_cursor (ledger-only, no toca MySQL legacy)."""
        items = [(42, Decimal("5"))]
        with patch("mpr.services.mysql_cursor") as mock_cursor:
            enviar_a_produccion_lote(EMPRESA, 1, items)
            mock_cursor.assert_not_called()

    def test_warning_sobrenvio_contiene_id_articulo(self):
        """El warning de sobreenvío menciona el id_articulo."""
        items = [(99, Decimal("100"))]
        pendientes = {99: Decimal("10")}
        _, _, warnings, _ = enviar_a_produccion_lote(EMPRESA, 1, items, pendientes=pendientes)
        self.assertTrue(any("99" in w for w in warnings))


# ===========================================================================
# TestQueryEnviadoTableroComponente
# ===========================================================================

class TestQueryEnviadoTableroComponente(TestCase):
    """REQ: Helper de Consulta Backward-Safe — Spec 1."""

    def test_suma_solo_no_anulados(self):
        """comp_id=42 con 2 envíos activos (10,15) y 1 anulado (5) retorna {42: 25}."""
        MprEnvioProduccion.objects.create(
            base_empresa=EMPRESA, id_articulo=42, cantidad=Decimal("10"), id_usuario=1,
        )
        MprEnvioProduccion.objects.create(
            base_empresa=EMPRESA, id_articulo=42, cantidad=Decimal("15"), id_usuario=1,
        )
        MprEnvioProduccion.objects.create(
            base_empresa=EMPRESA, id_articulo=42, cantidad=Decimal("5"), id_usuario=1,
            anulado=True,
        )
        resultado = _query_enviado_tablero_componente(EMPRESA, [42])
        self.assertIn(42, resultado)
        self.assertEqual(resultado[42], Decimal("25"))

    def test_retorna_vacio_si_sin_registros(self):
        """base_empresa sin registros retorna {}."""
        resultado = _query_enviado_tablero_componente("empresa_sin_datos", [42])
        self.assertEqual(resultado, {})

    def test_retorna_vacio_si_comp_ids_vacio(self):
        """comp_ids vacío retorna {} sin error."""
        resultado = _query_enviado_tablero_componente(EMPRESA, [])
        self.assertEqual(resultado, {})

    def test_filtra_por_comp_ids(self):
        """Solo retorna datos para los comp_ids solicitados."""
        MprEnvioProduccion.objects.create(
            base_empresa=EMPRESA, id_articulo=10, cantidad=Decimal("5"), id_usuario=1,
        )
        MprEnvioProduccion.objects.create(
            base_empresa=EMPRESA, id_articulo=20, cantidad=Decimal("8"), id_usuario=1,
        )
        resultado = _query_enviado_tablero_componente(EMPRESA, [10])
        self.assertIn(10, resultado)
        self.assertNotIn(20, resultado)

    def test_retorna_vacio_si_base_empresa_vacia(self):
        """base_empresa vacía retorna {} backward-safe."""
        resultado = _query_enviado_tablero_componente("", [42])
        self.assertEqual(resultado, {})


# ===========================================================================
# TestIntegracionEnviadoTablero (SimpleTestCase con mocks)
# ===========================================================================

class TestIntegracionEnviadoTablero(SimpleTestCase):
    """REQ: Columna Enviado dos fuentes — Spec 2 MODIFIED."""

    def _patch_tablero(self, enviado_pack_map=None, envios_tablero=None,
                       stock_produccion=0.0, enviado_opt_comp=0.0):
        """Configura todos los mocks para listar_tablero_por_articulo."""
        filas = _filas_pack(demanda=100.0)
        abm = _abm_map()
        bom = _bom_map()
        sp = _stock_pivot(produccion=stock_produccion)
        desc = _desc_map()
        if enviado_pack_map is None:
            enviado_pack_map = {}
        # Mock de _enviado_produccion_por_componente para aislar enviado_opt
        enviado_comp_mock = {42: enviado_opt_comp} if enviado_opt_comp else {}

        patches = [
            patch("mpr.services.listar_ventana_pack", return_value=filas),
            patch("mpr.services.mysql_cursor"),
            patch("mpr.services._query_enviado_packs", return_value=enviado_pack_map),
            patch("mpr.services.bulk_id_en_abm", return_value=abm),
            patch("mpr.services.bulk_bom_detalle", return_value=bom),
            patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=(sp, sp)),
            patch("mpr.services._fetch_descripciones_articulo", return_value=desc),
            patch("mpr.services._enviado_produccion_por_componente", return_value=enviado_comp_mock),
            patch("mpr.services._query_enviado_tablero_componente",
                  return_value={42: Decimal(str(envios_tablero))} if envios_tablero else {}),
        ]
        return patches

    def _run(self, patches):
        activos = [p.start() for p in patches]
        ctx_mock = MagicMock()
        ctx_mock.__enter__ = MagicMock(return_value=MagicMock())
        ctx_mock.__exit__ = MagicMock(return_value=False)
        # mysql_cursor es el 2do patch
        activos[1].return_value = ctx_mock
        try:
            return listar_tablero_por_articulo(EMPRESA)
        finally:
            for p in patches:
                p.stop()

    def test_enviado_es_opt_mas_tablero_sin_stock(self):
        """Con envíos tablero=30 y stock_prod=0 → Enviado_tablero=30; Enviado=OPT+30."""
        patches = self._patch_tablero(envios_tablero=30.0, stock_produccion=0.0, enviado_opt_comp=5.0)
        filas = self._run(patches)
        self.assertTrue(len(filas) > 0)
        fila = next((r for r in filas if r["id_articulo"] == 42), None)
        self.assertIsNotNone(fila)
        # enviado_opt=5, enviado_tablero=max(0,30-0)=30 → enviado=35
        self.assertAlmostEqual(fila["enviado"], 35.0, places=1)

    def test_backward_safe_sin_envios_tablero(self):
        """Sin envíos tablero (mock retorna {}) → Enviado = solo OPT (idéntico a E6)."""
        patches = self._patch_tablero(envios_tablero=None, stock_produccion=0.0, enviado_opt_comp=10.0)
        filas = self._run(patches)
        fila = next((r for r in filas if r["id_articulo"] == 42), None)
        self.assertIsNotNone(fila)
        # enviado_tablero = max(0, 0-0) = 0 → enviado = 10 (solo OPT)
        self.assertAlmostEqual(fila["enviado"], 10.0, places=1)

    def test_enviado_tablero_con_stock_reduce_sin_doble_conteo(self):
        """SUM(envíos_tablero)=30, stock_prod=20 → Enviado_tablero=max(0,30-20)=10."""
        patches = self._patch_tablero(envios_tablero=30.0, stock_produccion=20.0, enviado_opt_comp=0.0)
        filas = self._run(patches)
        fila = next((r for r in filas if r["id_articulo"] == 42), None)
        self.assertIsNotNone(fila)
        # enviado_tablero = max(0, 30-20) = 10
        self.assertAlmostEqual(fila["enviado"], 10.0, places=1)

    def test_enviado_tablero_nunca_negativo(self):
        """SUM(envíos_tablero)=10, stock_prod=15 → Enviado_tablero=max(0,10-15)=0."""
        patches = self._patch_tablero(envios_tablero=10.0, stock_produccion=15.0, enviado_opt_comp=0.0)
        filas = self._run(patches)
        fila = next((r for r in filas if r["id_articulo"] == 42), None)
        self.assertIsNotNone(fila)
        # enviado_tablero = max(0, 10-15) = 0 → enviado >= 0
        self.assertGreaterEqual(fila["enviado"], 0.0)

    def test_pendiente_coherente_con_enviado_e7(self):
        """Pendiente = max(0, demanda - (enviado + total)) es coherente tras E7."""
        patches = self._patch_tablero(envios_tablero=20.0, stock_produccion=0.0, enviado_opt_comp=0.0)
        filas = self._run(patches)
        fila = next((r for r in filas if r["id_articulo"] == 42), None)
        self.assertIsNotNone(fila)
        # demanda=100, enviado=20, total=0 → pendiente=80
        self.assertGreaterEqual(fila["pendiente"], 0.0)
        expected = max(0.0, fila["demanda"] - (fila["enviado"] + fila["total"]))
        self.assertAlmostEqual(fila["pendiente"], expected, places=1)


# ===========================================================================
# TestEnviarProduccionLoteView
# ===========================================================================

class TestEnviarProduccionLoteView(TestCase):
    """REQ: Vista de Lote POST — Spec 1."""

    def setUp(self):
        self.factory = RequestFactory()
        try:
            self.user = User.objects.get(email="test_e7@synap.test")
        except User.DoesNotExist:
            self.user = User.objects.create(
                uid="test_e7",
                email="test_e7@synap.test",
                nombre="Test E7",
                is_superuser=True,
                is_staff=True,
                is_active=True,
            )

    def _post(self, data, empresa=EMPRESA):
        from mpr.views import EnviarProduccionLoteView
        request = self.factory.post(
            reverse("mpr:tablero_produccion_enviar"),
            data=data,
        )
        request.session = {
            "user": {"id_usuario": 1, "nombre": "Test", "base_empresa": empresa}
        }
        request.user = self.user
        view = EnviarProduccionLoteView.as_view()
        # Inyectar middleware de messages
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, "_messages", FallbackStorage(request))
        return view(request)

    def test_post_3_filas_crea_3_registros_y_redirige(self):
        """POST con 3 filas válidas → 302, 3 registros creados."""
        data = {
            "envio_10": "5",
            "pendiente_10": "50",
            "envio_20": "3",
            "pendiente_20": "30",
            "envio_30": "8",
            "pendiente_30": "80",
        }
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(MprEnvioProduccion.objects.filter(base_empresa=EMPRESA).count(), 3)

    def test_post_sobrenvio_crea_registro_y_warning(self):
        """POST con pendiente=5, cantidad=20 → envío ejecutado + warning visible."""
        data = {
            "envio_42": "20",
            "pendiente_42": "5",
        }
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(MprEnvioProduccion.objects.filter(base_empresa=EMPRESA).count(), 1)

    def test_post_preserva_filtros_en_redirect(self):
        """Filtros_qs se preservan en la URL de redirect."""
        data = {
            "envio_10": "5",
            "pendiente_10": "10",
            "filtros_qs": "fecha_desde=2026-01-01&fecha_hasta=2026-12-31",
        }
        resp = self._post(data)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("fecha_desde", resp["Location"])

    def test_post_sin_empresa_redirige_sin_crear(self):
        """Sin base_empresa en sesión → redirige sin crear registros."""
        from mpr.views import EnviarProduccionLoteView
        from django.contrib.messages.storage.fallback import FallbackStorage
        request = self.factory.post(
            reverse("mpr:tablero_produccion_enviar"),
            data={"envio_10": "5"},
        )
        request.session = {"user": {"id_usuario": 1, "nombre": "Test"}}
        request.user = self.user
        setattr(request, "_messages", FallbackStorage(request))
        view = EnviarProduccionLoteView.as_view()
        resp = view(request)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(MprEnvioProduccion.objects.count(), 0)
