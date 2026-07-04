"""
Tests — MPR Etapa 6: Trazabilidad OPT.

Cobertura:
- TestIdListaPersistido: id_lista_produccion se persiste al registrar parte (con OPT activa mockeada)
  y queda null si no hay OPT.
- TestHistoricoOppParte: escritura historico (mock) + fallback si tabla ausente (no rompe asiento).
- TestConstruirTrazabilidadOpt: integra y ORDENA eventos de fuentes mockeadas.
- TestEventosHuerfanos: eventos sin OPT marcados fuente='sin_opt'.
- TestTrazabilidadOptView: scoping base_empresa en la vista (404 otra empresa), requiere login.

Comando:
    docker exec Synap_app python manage.py test mpr.tests.test_etapa6_trazabilidad --keepdb --noinput
"""
from datetime import date, time
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase, RequestFactory
from django.urls import reverse

from mpr.models import (
    MprArmadoSurtidoMovimiento,
    MprImputacionArmado,
    MprParte,
    MprParteAjuste,
    MprParteLinea,
    MprTransicionLote,
    MprTurno,
    ESTADO_IMPUTACION_NA,
    MODO_ARMADO_2DA,
    ORIGEN_REGLA_FIFO,
)

EMPRESA = "EmpresaTestEtapa6"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _crear_turno(nombre="Mañana"):
    return MprTurno.objects.create(
        base_empresa=EMPRESA,
        nombre=nombre,
        hora_inicio=time(6, 0),
        hora_fin=time(14, 0),
        activo=True,
    )


def _crear_parte(turno, fecha=None, id_usuario=1, movimiento_fisico_ok=False, id_lista=None):
    return MprParte.objects.create(
        base_empresa=EMPRESA,
        fecha_produccion=fecha or date(2026, 7, 3),
        turno=turno,
        id_usuario=id_usuario,
        movimiento_fisico_ok=movimiento_fisico_ok,
        id_lista_produccion=id_lista,
    )


def _crear_linea(parte, id_articulo=10, id_operario=5, cantidad=20):
    return MprParteLinea.objects.create(
        parte=parte,
        id_articulo=id_articulo,
        id_operario=id_operario,
        operario_nombre="Operario Test",
        cantidad=Decimal(str(cantidad)),
    )


def _fake_connection(base_empresa=None):
    """Context-manager fake de conexión MySQL para tests."""
    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.autocommit = MagicMock()
    conn.rollback = MagicMock()
    conn.commit = MagicMock()

    class _Ctx:
        def __enter__(self_):
            return conn

        def __exit__(self_, *args):
            pass

    return _Ctx(), cursor, conn


def _fake_mysql_cursor_ctx(rows=None):
    """Simula el context manager mysql_cursor con rows pre-cargadas."""
    cursor = MagicMock()
    cursor.fetchall.return_value = rows or []
    cursor.fetchone.return_value = None

    class _Ctx:
        def __enter__(self_):
            return cursor

        def __exit__(self_, *args):
            pass

    return _Ctx(), cursor


# ---------------------------------------------------------------------------
# 1. Persistencia de id_lista_produccion en MprParte
# ---------------------------------------------------------------------------

class TestIdListaPersistido(TestCase):
    """REQ-OPP-009: id_lista_produccion se captura y persiste al registrar parte."""

    def setUp(self):
        self.turno = _crear_turno()

    def _patched_registrar(self, mysql_rows, id_lista_esperado):
        """Helper: llama registrar_parte_produccion con MySQL mockeado para captura de OPT."""
        from mpr.services import registrar_parte_produccion

        mock_ctx, mock_cursor = _fake_mysql_cursor_ctx(rows=mysql_rows)
        mock_cursor.fetchall.return_value = mysql_rows

        with patch("mpr.services._registrar_asiento_fisico_opp_parte"), \
             patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"}), \
             patch("mpr.services.get_deposito_produccion_mpr", return_value=5), \
             patch("mpr.services.opp_parte_acumulado_por_pack", return_value={}), \
             patch("mpr.services.mysql_cursor") as mock_mc, \
             patch("mpr.services._nombre_tabla", side_effect=lambda c, n: n):
            mock_mc.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_mc.return_value.__exit__ = MagicMock(return_value=False)

            parte, _ = registrar_parte_produccion(
                base_empresa=EMPRESA,
                fecha_produccion=date(2026, 7, 3),
                turno_id=self.turno.pk,
                id_usuario=1,
                lineas=[{"id_articulo": 10, "id_operario": 5, "cantidad": 20}],
            )
        return parte

    def test_id_lista_persistido_cuando_opt_activa(self):
        """E8: registrar_parte_produccion siempre persiste id_lista_produccion=None (componentes sin OPT)."""
        # En E8, _capturar_id_lista_opt_activa ya no se llama: siempre None.
        mysql_rows = [{"id_lista_produccion": 42}]
        parte = self._patched_registrar(mysql_rows, None)
        parte.refresh_from_db()
        self.assertIsNone(parte.id_lista_produccion)

    def test_id_lista_null_cuando_sin_opt(self):
        """Cuando no hay OPT activa, id_lista_produccion es None."""
        parte = self._patched_registrar([], None)
        parte.refresh_from_db()
        self.assertIsNone(parte.id_lista_produccion)

    def test_warning_cuando_multiples_opts_activas(self):
        """E8: registrar_parte_produccion siempre retorna id_lista=None; no hay captura de OPT ni warning de ambigüedad."""
        # En E8, _capturar_id_lista_opt_activa ya no se llama → no se produce warning de ambigüedad.
        mysql_rows = [{"id_lista_produccion": 99}, {"id_lista_produccion": 50}]
        parte = self._patched_registrar(mysql_rows, None)
        parte.refresh_from_db()
        self.assertIsNone(parte.id_lista_produccion)

    def test_id_lista_null_cuando_mysql_falla(self):
        """Si MySQL falla al capturar OPT, id_lista queda None (best-effort)."""
        from mpr.services import registrar_parte_produccion

        def _raise_mysql(*args, **kwargs):
            class _ErrCtx:
                def __enter__(self_):
                    raise RuntimeError("Simulated MySQL failure")

                def __exit__(self_, *args):
                    pass
            return _ErrCtx()

        with patch("mpr.services._registrar_asiento_fisico_opp_parte"), \
             patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"}), \
             patch("mpr.services.get_deposito_produccion_mpr", return_value=5), \
             patch("mpr.services.opp_parte_acumulado_por_pack", return_value={}), \
             patch("mpr.services.mysql_cursor", side_effect=_raise_mysql), \
             patch("mpr.services._nombre_tabla", side_effect=lambda c, n: n):
            parte, _ = registrar_parte_produccion(
                base_empresa=EMPRESA,
                fecha_produccion=date(2026, 7, 3),
                turno_id=self.turno.pk,
                id_usuario=1,
                lineas=[{"id_articulo": 10, "id_operario": 5, "cantidad": 20}],
            )
        parte.refresh_from_db()
        self.assertIsNone(parte.id_lista_produccion)


# ---------------------------------------------------------------------------
# 2. Escritura a lista_produccion_historico
# ---------------------------------------------------------------------------

class TestHistoricoOppParte(TestCase):
    """REQ-OPP-010: _escribir_historico_opp_parte escribe o falla gracefully."""

    def setUp(self):
        self.turno = _crear_turno()

    def _make_parte_con_lista(self, id_lista=42):
        parte = _crear_parte(self.turno, id_lista=id_lista)
        return parte

    def test_insert_llamado_cuando_id_lista_presente(self):
        """Cuando id_lista_produccion está presente, se llama a cursor.execute con INSERT."""
        from mpr.services import _escribir_historico_opp_parte

        cursor = MagicMock()
        cursor.execute = MagicMock()
        parte = self._make_parte_con_lista(id_lista=42)
        lineas_pack_qty = [
            ({"id_articulo": 10}, Decimal("20")),
        ]

        with patch("mpr.services._nombre_tabla", side_effect=lambda c, n: n), \
             patch("mpr.services._mpr_ejecutar_insert_intentos") as mock_insert:
            _escribir_historico_opp_parte(
                cursor=cursor,
                parte=parte,
                lineas_pack_qty=lineas_pack_qty,
                codigo_mov=100,
                id_usuario=1,
                fecha_mov="2026-07-03",
                deposito_produccion=5,
            )

        mock_insert.assert_called()
        args_first_call = mock_insert.call_args_list[0]
        intentos = args_first_call[0][1]
        self.assertGreater(len(intentos), 0, "Debe haber al menos un intento de INSERT")

    def test_skip_cuando_id_lista_none(self):
        """Cuando id_lista_produccion es None, no se llama INSERT (silencioso)."""
        from mpr.services import _escribir_historico_opp_parte

        cursor = MagicMock()
        parte = _crear_parte(self.turno, id_lista=None)

        with patch("mpr.services._nombre_tabla", side_effect=lambda c, n: n), \
             patch("mpr.services._mpr_ejecutar_insert_intentos") as mock_insert:
            _escribir_historico_opp_parte(
                cursor=cursor,
                parte=parte,
                lineas_pack_qty=[({"id_articulo": 10}, Decimal("20"))],
                codigo_mov=100,
                id_usuario=1,
                fecha_mov="2026-07-03",
                deposito_produccion=5,
            )

        mock_insert.assert_not_called()

    def test_graceful_cuando_tabla_ausente(self):
        """Cuando _nombre_tabla retorna None para historico, no rompe ni lanza excepción."""
        from mpr.services import _escribir_historico_opp_parte

        cursor = MagicMock()
        parte = self._make_parte_con_lista(id_lista=42)

        with patch("mpr.services._nombre_tabla", return_value=None), \
             patch("mpr.services._mpr_ejecutar_insert_intentos") as mock_insert:
            _escribir_historico_opp_parte(
                cursor=cursor,
                parte=parte,
                lineas_pack_qty=[({"id_articulo": 10}, Decimal("20"))],
                codigo_mov=100,
                id_usuario=1,
                fecha_mov="2026-07-03",
                deposito_produccion=5,
            )

        mock_insert.assert_not_called()

    def test_asiento_fisico_no_se_rompe_si_historico_falla(self):
        """Si _escribir_historico_opp_parte lanza excepción, el asiento físico no se interrumpe.

        Verifica directamente que _registrar_asiento_fisico_opp_parte no propaga la excepción
        del historico, ya que está envuelta en try/except aislado.
        """
        from mpr.services import _registrar_asiento_fisico_opp_parte

        ctx, cursor, conn = _fake_connection()
        # fetchone responses: codmov, talonario, stock_deposito por componente (None = sin fila previa)
        cursor.fetchone.side_effect = [
            (100,),      # codmov
            (1, 50),     # talonario (Orden=1, Nro=50)
            None,        # stock_deposito para componente 20 (sin fila previa)
        ]
        cursor.fetchall.return_value = []

        parte = self._make_parte_con_lista(id_lista=42)
        lineas_pack_qty = [({"id_articulo": 10}, Decimal("20"))]

        with patch("mpr.services._escribir_historico_opp_parte", side_effect=RuntimeError("error historico")), \
             patch("mpr.services._nombre_tabla", side_effect=lambda c, n: n), \
             patch("mpr.services._explode_packs_to_components", return_value={20: 10.0}), \
             patch("mpr.services._mpr_ejecutar_insert_intentos"), \
             patch("mpr.services.get_connection", return_value=ctx):
            # No debe lanzar excepción a pesar de que el historico falla
            try:
                _registrar_asiento_fisico_opp_parte(
                    base_empresa=EMPRESA,
                    id_usuario=1,
                    parte=parte,
                    lineas_pack_qty=lineas_pack_qty,
                    deposito_produccion=5,
                )
            except Exception as exc:
                self.fail(
                    f"_registrar_asiento_fisico_opp_parte no debería propagar excepción del historico, pero lanzó: {exc}"
                )


# ---------------------------------------------------------------------------
# 3. construir_trazabilidad_opt
# ---------------------------------------------------------------------------

class TestConstruirTrazabilidadOpt(TestCase):
    """REQ-TRZ-001: construir_trazabilidad_opt integra fuentes y ordena eventos."""

    def setUp(self):
        self.turno = _crear_turno()

    def _cabecera_opt_mock(self):
        return [{
            "id_articulo": 10,
            "codigo_manual": "ART-001",
            "descripcion_articulo": "Artículo Test",
            "cantidad_pedida": 100,
            "en_proceso_produccion": "Si",
        }]

    def test_cabecera_correcta(self):
        """La cabecera retorna id_lista, id_articulo, descripcion y estado."""
        from mpr.services import construir_trazabilidad_opt

        with patch("mpr.services.get_op_detalle", return_value=self._cabecera_opt_mock()), \
             patch("mpr.services.mysql_cursor") as mock_mc, \
             patch("mpr.services._nombre_tabla", return_value=None), \
             patch("mpr.services.listar_opp_por_opt", return_value=[]):
            mock_mc.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_mc.return_value.__exit__ = MagicMock(return_value=False)

            resultado = construir_trazabilidad_opt(EMPRESA, 42)

        self.assertEqual(resultado["cabecera"]["id_lista"], 42)
        self.assertEqual(resultado["cabecera"]["id_articulo"], 10)
        self.assertEqual(resultado["cabecera"]["estado"], "en_proceso")
        self.assertEqual(resultado["cabecera"]["descripcion"], "Artículo Test")

    def test_eventos_de_mpr_parte_integrados(self):
        """MprPartes con id_lista_produccion aparecen como eventos OPP."""
        from mpr.services import construir_trazabilidad_opt

        parte = _crear_parte(self.turno, fecha=date(2026, 7, 1), id_lista=42)
        _crear_linea(parte, id_articulo=10, cantidad=30)

        with patch("mpr.services.get_op_detalle", return_value=self._cabecera_opt_mock()), \
             patch("mpr.services.mysql_cursor") as mock_mc, \
             patch("mpr.services._nombre_tabla", return_value=None), \
             patch("mpr.services.listar_opp_por_opt", return_value=[]):
            mock_mc.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_mc.return_value.__exit__ = MagicMock(return_value=False)

            resultado = construir_trazabilidad_opt(EMPRESA, 42)

        eventos_opp = [e for e in resultado["eventos"] if e["fuente"] == "mpr_parte"]
        self.assertGreater(len(eventos_opp), 0, "Debe haber al menos un evento de tipo mpr_parte")
        self.assertEqual(eventos_opp[0]["tipo"], "OPP")

    def test_orden_cronologico(self):
        """Los eventos deben estar ordenados cronológicamente."""
        from mpr.services import construir_trazabilidad_opt

        parte1 = _crear_parte(self.turno, fecha=date(2026, 7, 3), id_lista=42)
        _crear_linea(parte1, id_articulo=10, cantidad=5)
        parte2 = _crear_parte(self.turno, fecha=date(2026, 7, 1), id_lista=42)
        _crear_linea(parte2, id_articulo=10, cantidad=10)

        with patch("mpr.services.get_op_detalle", return_value=self._cabecera_opt_mock()), \
             patch("mpr.services.mysql_cursor") as mock_mc, \
             patch("mpr.services._nombre_tabla", return_value=None), \
             patch("mpr.services.listar_opp_por_opt", return_value=[]):
            mock_mc.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_mc.return_value.__exit__ = MagicMock(return_value=False)

            resultado = construir_trazabilidad_opt(EMPRESA, 42)

        eventos_parte = [e for e in resultado["eventos"] if e["fuente"] == "mpr_parte"]
        if len(eventos_parte) >= 2:
            fechas_str = [e["fecha"] for e in eventos_parte]
            from datetime import datetime
            fechas_dt = []
            for f in fechas_str:
                if f and "/" in f:
                    parts = f.split("/")
                    fechas_dt.append(date(int(parts[2]), int(parts[1]), int(parts[0])))
            if len(fechas_dt) >= 2:
                self.assertTrue(
                    fechas_dt == sorted(fechas_dt),
                    f"Eventos no están ordenados cronológicamente: {fechas_str}",
                )

    def test_fuentes_fallidas_sin_500_cuando_mysql_falla(self):
        """Si MySQL falla, la función no lanza excepción y reporta fuente_fallida."""
        from mpr.services import construir_trazabilidad_opt

        def _raise_mysql(*args, **kwargs):
            class _ErrCtx:
                def __enter__(self_):
                    raise RuntimeError("MySQL caído")
                def __exit__(self_, *args):
                    pass
            return _ErrCtx()

        with patch("mpr.services.get_op_detalle", return_value=self._cabecera_opt_mock()), \
             patch("mpr.services.mysql_cursor", side_effect=_raise_mysql), \
             patch("mpr.services.listar_opp_por_opt", side_effect=RuntimeError("mysql down")):
            resultado = construir_trazabilidad_opt(EMPRESA, 42)

        self.assertIn("movimiento_stock_opp", resultado["fuentes_fallidas"])
        self.assertIsInstance(resultado["eventos"], list)

    def test_retorna_vacio_si_cabecera_vacia(self):
        """Si get_op_detalle devuelve [] (OPT inexistente), cabecera es {} y eventos []."""
        from mpr.services import construir_trazabilidad_opt

        with patch("mpr.services.get_op_detalle", return_value=[]):
            resultado = construir_trazabilidad_opt(EMPRESA, 9999)

        self.assertEqual(resultado["cabecera"], {})
        self.assertEqual(resultado["eventos"], [])


# ---------------------------------------------------------------------------
# 4. Eventos huérfanos
# ---------------------------------------------------------------------------

class TestEventosHuerfanos(TestCase):
    """REQ-TRZ-002: eventos sin OPT asociada se marcan fuente='sin_opt'."""

    def test_lista_agrupada_sin_id_lista_marcada_sin_opt(self):
        """construir_trazabilidad_articulo marca como 'sin_opt' las filas sin id_lista_produccion."""
        from mpr.services import construir_trazabilidad_articulo

        opts_mock = [
            {"id_lista_produccion": None, "id_articulo": 10},
        ]

        with patch("mpr.services.listar_lista_produccion_agrupada", return_value=opts_mock):
            resultado = construir_trazabilidad_articulo(EMPRESA, 10)

        eventos_huerfanos = [e for e in resultado["eventos"] if e.get("fuente") == "sin_opt"]
        self.assertGreater(len(eventos_huerfanos), 0, "Debe haber eventos sin_opt")
        self.assertEqual(eventos_huerfanos[0]["descripcion"], "sin OPT asociada")

    def test_construir_trazabilidad_articulo_retorna_vacio_si_sin_opts(self):
        """Si no hay OPTs, retorna lista vacía sin error."""
        from mpr.services import construir_trazabilidad_articulo

        with patch("mpr.services.listar_lista_produccion_agrupada", return_value=[]):
            resultado = construir_trazabilidad_articulo(EMPRESA, 10)

        self.assertEqual(resultado["eventos"], [])


# ---------------------------------------------------------------------------
# 5. Vista de trazabilidad
# ---------------------------------------------------------------------------

class TestTrazabilidadOptView(TestCase):
    """REQ-TRZ-003: TrazabilidadOptView — scoping, 404, requiere login.

    Usa RequestFactory para evitar middleware de permisos de módulo en tests.
    """

    def setUp(self):
        self.factory = RequestFactory()
        UserModel = get_user_model()
        try:
            self.user = UserModel.objects.get(email="test_e6_traz@synap.test")
        except UserModel.DoesNotExist:
            self.user = UserModel.objects.create(
                uid="test_e6_traz",
                email="test_e6_traz@synap.test",
                nombre="Test E6",
                is_superuser=True,
                is_staff=True,
                is_active=True,
            )

    def _trazabilidad_ok(self, base_empresa=EMPRESA, id_lista=42):
        return {
            "cabecera": {
                "id_lista": id_lista,
                "id_articulo": 10,
                "codigo_manual": "ART-001",
                "descripcion": "Artículo Test",
                "cantidad_pedida": 100,
                "estado": "en_proceso",
                "base_empresa": base_empresa,
            },
            "eventos": [],
            "fuentes_fallidas": [],
        }

    def _make_get_request(self, id_lista=42, empresa=EMPRESA, user=None):
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get(reverse("mpr:opt_trazabilidad", kwargs={"id_lista": id_lista}))
        # _get_base_empresa lee request.session["user"]["base_empresa"]
        request.session = {"user": {"id_usuario": 1, "nombre": "Test", "base_empresa": empresa}}
        request.user = user if user is not None else self.user
        return request

    def test_get_200_con_contexto_correcto(self):
        """GET /opt/<id>/trazabilidad/ → contexto correcto con cabecera."""
        from mpr.views import TrazabilidadOptView
        request = self._make_get_request(id_lista=42)
        view = TrazabilidadOptView.as_view()
        with patch("mpr.services.construir_trazabilidad_opt", return_value=self._trazabilidad_ok()):
            resp = view(request, id_lista=42)
        self.assertEqual(resp.status_code, 200)
        resp.render()
        self.assertIn(b"Trazabilidad", resp.content)

    def test_404_si_cabecera_vacia(self):
        """Si construir_trazabilidad_opt retorna cabecera {}, responde 404."""
        from mpr.views import TrazabilidadOptView
        from django.http import Http404
        request = self._make_get_request(id_lista=9999)
        view = TrazabilidadOptView.as_view()
        with patch("mpr.services.construir_trazabilidad_opt", return_value={"cabecera": {}, "eventos": [], "fuentes_fallidas": []}):
            with self.assertRaises(Http404):
                view(request, id_lista=9999)

    def test_404_si_base_empresa_distinta(self):
        """Si la OPT pertenece a otra empresa, responde 404."""
        from mpr.views import TrazabilidadOptView
        from django.http import Http404
        request = self._make_get_request(id_lista=42, empresa=EMPRESA)
        view = TrazabilidadOptView.as_view()
        traza_otra_empresa = self._trazabilidad_ok(base_empresa="OtraEmpresa", id_lista=42)
        with patch("mpr.services.construir_trazabilidad_opt", return_value=traza_otra_empresa):
            with self.assertRaises(Http404):
                view(request, id_lista=42)

    def test_requiere_login_sin_sesion(self):
        """Sin sesión Synap (user no en session), la vista redirige fuera."""
        from mpr.views import TrazabilidadOptView
        from django.contrib.auth.models import AnonymousUser

        class _FakeAnon:
            is_authenticated = False
            is_superuser = False

        request = self.factory.get(reverse("mpr:opt_trazabilidad", kwargs={"id_lista": 42}))
        request.session = {}  # sin "user" en sesión
        request.user = _FakeAnon()
        view = TrazabilidadOptView.as_view()
        resp = view(request, id_lista=42)
        self.assertIn(resp.status_code, [302, 403], "Vista protegida debe redirigir o denegar sin sesión.")
