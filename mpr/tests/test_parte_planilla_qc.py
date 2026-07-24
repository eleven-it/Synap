"""Tests grilla analista planilla QC (/mpr/parte-produccion/)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from mpr.services_maquina_linea import construir_grilla_parte_planilla
from mpr.views import ParteProduccionView, RegistrarParteProduccionView, _parte_lineas_desde_post

User = get_user_model()

EMPRESA = "test_parte_planilla_qc"


def _planilla_maquinas_dos_filas():
    return {
        "fecha": "2026-07-21",
        "fecha_articulos": "2026-07-21",
        "es_futuro": False,
        "maquinas": [
            {
                "id": 10,
                "codigo": "M1",
                "nombre": "Máquina 1",
                "id_linea_actual": 1,
                "linea_actual_nombre": "L1",
                "articulos": [
                    {
                        "id_articulo": 100,
                        "codigo_manual": "A100",
                        "codigo_articulo": "ART100",
                        "descripcion_articulo": "Artículo cien",
                        "cantidades": {"manana": 12, "tarde": None, "noche": None},
                    },
                ],
            },
            {
                "id": 20,
                "codigo": "M2",
                "nombre": "Máquina 2",
                "id_linea_actual": 1,
                "linea_actual_nombre": "L1",
                "articulos": [
                    {
                        "id_articulo": 200,
                        "codigo_manual": "A200",
                        "codigo_articulo": "ART200",
                        "descripcion_articulo": "Artículo doscientos",
                        "cantidades": {"manana": None, "tarde": 6, "noche": None},
                    },
                ],
            },
        ],
        "operadores_por_linea": {1: {"manana": "JUAN PÉREZ", "tarde": "ANA GÓMEZ", "noche": ""}},
    }


def _turnos_mtn():
    return [
        {"id": 1, "nombre": "Mañana", "hora_inicio": "06:00", "activo": True},
        {"id": 2, "nombre": "Tarde", "hora_inicio": "14:00", "activo": True},
        {"id": 3, "nombre": "Noche", "hora_inicio": "22:00", "activo": True},
    ]


class ConstruirGrillaPartePlanillaTest(SimpleTestCase):
    """T1/T2: builder planilla QC."""

    @patch("mpr.repositories.parte.precarga_planilla_por_fecha")
    @patch("mpr.services._fabricando_por_componentes")
    @patch("mpr.services._query_enviados_todos_componentes")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    @patch("mpr.services_maquina_linea._operarios_roster_celda_por_linea")
    @patch("mpr.services.listar_turnos")
    @patch("mpr.services_maquina_linea.construir_datos_planilla_control_calidad")
    def test_filas_coinciden_orden_planilla_con_payload(
        self,
        mock_planilla,
        mock_turnos,
        mock_operarios_celda,
        mock_pivot,
        mock_envios,
        mock_fabricando,
        mock_precarga,
    ):
        mock_planilla.return_value = _planilla_maquinas_dos_filas()
        mock_turnos.return_value = _turnos_mtn()
        mock_operarios_celda.return_value = {
            1: {
                "manana": [{"id_operario": 5, "nombre": "JUAN PÉREZ"}],
                "tarde": [{"id_operario": 6, "nombre": "ANA GÓMEZ"}],
                "noche": [],
            }
        }
        mock_envios.return_value = {100: 24, 200: 24}
        mock_pivot.return_value = ({}, {})
        mock_fabricando.return_value = {100: 24.0, 200: 12.0}
        mock_precarga.return_value = {}

        out = construir_grilla_parte_planilla("emp", date(2026, 7, 21))

        self.assertEqual(len(out["filas"]), 2)
        self.assertEqual(out["filas"][0]["id_mpr_maquina"], 10)
        self.assertEqual(out["filas"][0]["id_articulo"], 100)
        self.assertEqual(out["filas"][1]["id_mpr_maquina"], 20)
        self.assertEqual(out["filas"][1]["id_articulo"], 200)
        fila1 = out["filas"][0]
        self.assertEqual(fila1["maquina_nombre"], "Máquina 1")
        self.assertEqual(fila1["descripcion"], "Artículo cien")
        self.assertIn("codigo_tooltip", fila1)
        self.assertEqual(fila1["fabricando"], 24.0)
        self.assertIn("turnos", fila1)

    @patch("mpr.repositories.parte.precarga_planilla_por_fecha")
    @patch("mpr.services._fabricando_por_componentes")
    @patch("mpr.services._query_enviados_todos_componentes")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    @patch("mpr.services_maquina_linea._operarios_roster_celda_por_linea")
    @patch("mpr.services.listar_turnos")
    @patch("mpr.services_maquina_linea.construir_datos_planilla_control_calidad")
    def test_turnos_m_t_n_docenas_pares_e_ingresado(
        self,
        mock_planilla,
        mock_turnos,
        mock_operarios_celda,
        mock_pivot,
        mock_envios,
        mock_fabricando,
        mock_precarga,
    ):
        mock_planilla.return_value = _planilla_maquinas_dos_filas()
        mock_turnos.return_value = _turnos_mtn()
        mock_operarios_celda.return_value = {1: {"manana": [], "tarde": [], "noche": []}}
        mock_envios.return_value = {100: 24}
        mock_pivot.return_value = ({}, {})
        mock_fabricando.return_value = {100: 24.0}
        mock_precarga.return_value = {
            (10, 100, 1): {"docenas": 1, "pares": 0},
            (10, 100, 2): {"docenas": 0, "pares": 6},
        }

        out = construir_grilla_parte_planilla("emp", date(2026, 7, 21))
        fila = out["filas"][0]
        turnos = fila["turnos"]

        self.assertIn(1, turnos)
        self.assertIn(2, turnos)
        self.assertIn(3, turnos)
        self.assertEqual(turnos[1]["docenas"], 1)
        self.assertEqual(turnos[1]["pares"], 0)
        self.assertEqual(turnos[2]["docenas"], 0)
        self.assertEqual(turnos[2]["pares"], 6)
        self.assertEqual(fila["ingresado"], 18)

    @patch("mpr.repositories.parte.precarga_planilla_por_fecha")
    @patch("mpr.services._fabricando_por_componentes")
    @patch("mpr.services._query_enviados_todos_componentes")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    @patch("mpr.services_maquina_linea._operarios_roster_celda_por_linea")
    @patch("mpr.services.listar_turnos")
    @patch("mpr.services_maquina_linea.construir_datos_planilla_control_calidad")
    def test_fila_sin_cupo_fabricando_cero(
        self,
        mock_planilla,
        mock_turnos,
        mock_operarios_celda,
        mock_pivot,
        mock_envios,
        mock_fabricando,
        mock_precarga,
    ):
        datos = _planilla_maquinas_dos_filas()
        datos["maquinas"] = [datos["maquinas"][0]]
        mock_planilla.return_value = datos
        mock_turnos.return_value = _turnos_mtn()
        mock_operarios_celda.return_value = {1: {"manana": [], "tarde": [], "noche": []}}
        mock_envios.return_value = {100: 0}
        mock_pivot.return_value = ({}, {})
        mock_fabricando.return_value = {100: 0.0}
        mock_precarga.return_value = {}

        out = construir_grilla_parte_planilla("emp", date(2026, 7, 21))

        self.assertEqual(out["filas"][0]["fabricando"], 0.0)
        self.assertFalse(out["filas"][0]["inputs_habilitados"])


class PrecargaPlanillaPorFechaTest(SimpleTestCase):
    """T3/T4: helper precarga por (fecha, máquina, artículo, turno)."""

    @patch("mpr.repositories.parte.mysql_cursor")
    @patch("mpr.services.listar_turnos")
    def test_precarga_devuelve_docenas_y_pares_por_turno(self, mock_turnos, mock_cursor_ctx):
        from mpr.repositories.parte import precarga_planilla_por_fecha

        mock_turnos.return_value = _turnos_mtn()
        cursor = mock_cursor_ctx.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            {
                "id_mpr_maquina": 10,
                "id_articulo": 100,
                "id_mpr_turno": 1,
                "estado": "aprobado",
                "cantidad_declarada": 5,
                "cantidad_aprobada": 18,
            },
            {
                "id_mpr_maquina": 10,
                "id_articulo": 100,
                "id_mpr_turno": 2,
                "estado": "pendiente",
                "cantidad_declarada": 7,
                "cantidad_aprobada": None,
            },
        ]

        out = precarga_planilla_por_fecha("emp", date(2026, 7, 21))

        self.assertEqual(out[(10, 100, 1)]["docenas"], 1)
        self.assertEqual(out[(10, 100, 1)]["pares"], 6)
        self.assertEqual(out[(10, 100, 2)]["docenas"], 0)
        self.assertEqual(out[(10, 100, 2)]["pares"], 7)


class CrearParteConLineasMaquinaTest(SimpleTestCase):
    """T5/T6: persistencia id_mpr_maquina en crear_parte_con_lineas."""

    @patch("mpr.repositories.parte.mysql_cursor")
    def test_inserta_maquina_y_cantidades_declaradas(self, mock_cursor_ctx):
        from mpr.repositories.parte import crear_parte_con_lineas

        cursor = mock_cursor_ctx.return_value.__enter__.return_value
        cursor.lastrowid = 99

        with patch("mpr.repositories.parte.obtener_parte_por_pk") as mock_obtener:
            mock_obtener.return_value = MagicMock(id_mpr_parte=99)
            crear_parte_con_lineas(
                EMPRESA,
                date(2026, 7, 21),
                1,
                1,
                [
                    {
                        "id_articulo": 100,
                        "id_operario": 5,
                        "cantidad": Decimal("12"),
                        "operario_nombre": "JUAN",
                        "id_mpr_maquina": 10,
                        "maquina_nombre": "M1",
                    }
                ],
            )

        insert_calls = [
            c for c in cursor.execute.call_args_list
            if "INSERT INTO mpr_parte_linea" in str(c.args[0])
        ]
        self.assertEqual(len(insert_calls), 1)
        sql = insert_calls[0].args[0]
        params = insert_calls[0].args[1]
        self.assertIn("id_mpr_maquina", sql)
        self.assertIn("cantidad_declarada", sql)
        self.assertIn("cantidad_aprobada", sql)
        self.assertIn("ON DUPLICATE KEY UPDATE", sql)
        self.assertEqual(params[5], 10)
        self.assertEqual(params[6], "M1")
        self.assertEqual(params[7], Decimal("12"))
        self.assertEqual(params[8], Decimal("12"))


class RegistrarParteProduccionPlanillaTest(TestCase):
    """T7/T8: cupo multi-turno y multi-máquina."""

    def _lineas_planilla_exceso_fila(self):
        return [
            {
                "id_articulo": 100,
                "id_operario": 5,
                "cantidad": Decimal("12"),
                "id_mpr_maquina": 10,
                "maquina_nombre": "M1",
                "turno_id": 1,
            },
            {
                "id_articulo": 100,
                "id_operario": 5,
                "cantidad": Decimal("15"),
                "id_mpr_maquina": 10,
                "maquina_nombre": "M1",
                "turno_id": 2,
            },
        ]

    @patch("mpr.services._registrar_asiento_fisico_opp_parte")
    @patch("mpr.services.get_deposito_produccion_mpr", return_value=5)
    @patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"})
    @patch("mpr.repositories.parte.crear_parte_con_lineas")
    @patch("mpr.services.cupo_fabricando_por_articulo")
    def test_rechaza_suma_turnos_sobre_cupo_fila(
        self, mock_cupo, mock_crear, _op, _dep, _asiento
    ):
        from mpr.services import registrar_parte_produccion

        mock_cupo.return_value = {100: 24.0}
        with self.assertRaises(ValidationError) as ctx:
            registrar_parte_produccion(
                EMPRESA,
                date(2026, 7, 21),
                None,
                1,
                self._lineas_planilla_exceso_fila(),
                modo_planilla=True,
            )
        self.assertIn("Fabricando", str(ctx.exception))
        mock_crear.assert_not_called()

    @patch("mpr.services._registrar_asiento_fisico_opp_parte")
    @patch("mpr.services.get_deposito_produccion_mpr", return_value=5)
    @patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"})
    @patch("mpr.repositories.parte.crear_parte_con_lineas")
    @patch("mpr.services.cupo_fabricando_por_articulo")
    def test_rechaza_suma_agregada_articulo_multi_maquina(
        self, mock_cupo, mock_crear, _op, _dep, _asiento
    ):
        from mpr.services import registrar_parte_produccion

        mock_cupo.return_value = {100: 24.0}
        lineas = [
            {
                "id_articulo": 100,
                "id_operario": 5,
                "cantidad": Decimal("12"),
                "id_mpr_maquina": 10,
                "maquina_nombre": "M1",
                "turno_id": 1,
            },
            {
                "id_articulo": 100,
                "id_operario": 6,
                "cantidad": Decimal("12"),
                "id_mpr_maquina": 20,
                "maquina_nombre": "M2",
                "turno_id": 1,
            },
            {
                "id_articulo": 100,
                "id_operario": 5,
                "cantidad": Decimal("6"),
                "id_mpr_maquina": 10,
                "maquina_nombre": "M1",
                "turno_id": 2,
            },
        ]
        with self.assertRaises(ValidationError) as ctx:
            registrar_parte_produccion(
                EMPRESA,
                date(2026, 7, 21),
                None,
                1,
                lineas,
                modo_planilla=True,
            )
        self.assertIn("Fabricando", str(ctx.exception))
        mock_crear.assert_not_called()

    @patch("mpr.services._registrar_asiento_fisico_opp_parte")
    @patch("mpr.services.get_deposito_produccion_mpr", return_value=5)
    @patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"})
    @patch("mpr.repositories.parte.crear_parte_con_lineas")
    @patch("mpr.services.cupo_fabricando_por_articulo")
    @patch("mpr.services.obtener_turno")
    def test_modo_planilla_crea_un_parte_por_turno(
        self, mock_turno, mock_cupo, mock_crear, _op, _dep, _asiento
    ):
        from mpr.services import registrar_parte_produccion

        turno_rec = MagicMock()
        turno_rec.id_mpr_turno = 1
        mock_turno.return_value = turno_rec
        mock_cupo.return_value = {100: 48.0}
        parte_mock = MagicMock(movimiento_fisico_ok=False, save=lambda *a, **k: None)
        mock_crear.return_value = parte_mock
        lineas = [
            {
                "id_articulo": 100,
                "id_operario": 5,
                "cantidad": Decimal("12"),
                "id_mpr_maquina": 10,
                "maquina_nombre": "M1",
                "turno_id": 1,
            },
            {
                "id_articulo": 100,
                "id_operario": 5,
                "cantidad": Decimal("6"),
                "id_mpr_maquina": 10,
                "maquina_nombre": "M1",
                "turno_id": 2,
            },
        ]
        partes, warnings = registrar_parte_produccion(
            EMPRESA,
            date(2026, 7, 21),
            None,
            1,
            lineas,
            modo_planilla=True,
        )
        self.assertEqual(mock_crear.call_count, 2)
        self.assertEqual(len(partes), 2)
        self.assertEqual(warnings, [])


class ParteLineasDesdePostPlanillaTest(SimpleTestCase):
    """T10: parseo POST planilla."""

    def test_parsea_celdas_maq_art_turno(self):
        post = QueryDict(mutable=True)
        post["parte_maq_10_art_100_turno_1_docenas"] = "1"
        post["parte_maq_10_art_100_turno_1_pares"] = "0"
        post["parte_maq_10_art_100_turno_1_op"] = "5"
        post["parte_maq_10_art_100_turno_2_docenas"] = "0"
        post["parte_maq_10_art_100_turno_2_pares"] = "6"
        post["parte_maq_10_art_100_turno_2_op"] = "5"

        lineas = _parte_lineas_desde_post(post, modo_planilla=True)

        self.assertEqual(len(lineas), 2)
        self.assertEqual(lineas[0]["id_mpr_maquina"], 10)
        self.assertEqual(lineas[0]["turno_id"], 1)
        self.assertEqual(lineas[0]["cantidad"], Decimal("12"))
        self.assertEqual(lineas[1]["turno_id"], 2)
        self.assertEqual(lineas[1]["cantidad"], Decimal("6"))


class ParteProduccionViewPlanillaTest(SimpleTestCase):
    """T9: filtros vista analista."""

    @patch("mpr.views._get_base_empresa", return_value="emp")
    @patch("mpr.services.obtener_config_mpr", return_value={"bloquear_parte_supera_fabricando": True})
    @patch("mpr.services.listar_turnos", return_value=_turnos_mtn())
    @patch("mpr.services_maquina_linea.listar_lineas", return_value=[{"id": 1, "nombre": "L1"}])
    @patch("mpr.services_maquina_linea.listar_maquinas", return_value=[{"id": 10, "nombre": "M1"}])
    @patch("mpr.services_maquina_linea.construir_grilla_parte_planilla")
    def test_get_usa_filtros_sin_turno(
        self,
        mock_grilla,
        _maquinas,
        _lineas,
        _turnos,
        _cfg,
        _base,
    ):
        mock_grilla.return_value = {"filas": [], "filas_vacio": True, "turnos_columnas": []}
        request = RequestFactory().get(
            "/mpr/parte-produccion/?fecha=21/07/2026&id_linea=1&id_maquina=10&q=art"
        )
        request.session = {"user": {"base_empresa": "emp"}}
        view = ParteProduccionView()
        view.setup(request)
        context = view.get_context_data()

        mock_grilla.assert_called_once()
        kwargs = mock_grilla.call_args.kwargs
        self.assertEqual(kwargs["id_linea"], 1)
        self.assertEqual(kwargs["id_maquina"], 10)
        self.assertEqual(kwargs["q"], "art")
        self.assertIn("grilla_planilla", context)
        self.assertNotIn("turno_id", context)


def _crear_usuario_planilla_qc():
    uid = "test_parte_planilla_qc_user"
    try:
        return User.objects.get(uid=uid)
    except User.DoesNotExist:
        return User.objects.create(
            uid=uid,
            email="test_planilla_qc@synap.test",
            nombre="Test Planilla QC",
            is_superuser=True,
            is_staff=True,
            is_active=True,
        )


def _add_messages(request):
    setattr(request, "_messages", FallbackStorage(request))


def _post_planilla_base(**extra):
    data = {
        "fecha": "21/07/2026",
        "parte_maq_10_nombre": "Máquina 1",
    }
    data.update(extra)
    return data


class RegistrarParteProduccionViewPlanillaIntegrationTest(TestCase):
    """T15: integración vista POST planilla QC multi-turno."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = _crear_usuario_planilla_qc()

    def _post_registrar(self, data, empresa=EMPRESA):
        request = self.factory.post(reverse("mpr:parte_produccion_registrar"), data=data)
        request.session = {"user": {"id_usuario": 1, "base_empresa": empresa}}
        request.user = self.user
        _add_messages(request)
        response = RegistrarParteProduccionView.as_view()(request)
        return response, request

    @patch("mpr.services.registrar_parte_produccion")
    @patch("mpr.views._get_base_empresa", return_value=EMPRESA)
    def test_post_multi_turno_persiste_id_mpr_maquina(self, _base, mock_registrar):
        mock_registrar.return_value = ([MagicMock(), MagicMock()], [])
        data = _post_planilla_base(
            parte_maq_10_art_100_turno_1_docenas="1",
            parte_maq_10_art_100_turno_1_pares="0",
            parte_maq_10_art_100_turno_1_op="5",
            parte_maq_10_art_100_turno_2_docenas="0",
            parte_maq_10_art_100_turno_2_pares="6",
            parte_maq_10_art_100_turno_2_op="5",
        )
        response, request = self._post_registrar(data)

        self.assertEqual(response.status_code, 302)
        self.assertIn("fecha=21%2F07%2F2026", response.url)
        mock_registrar.assert_called_once()
        call_kwargs = mock_registrar.call_args.kwargs
        self.assertTrue(call_kwargs.get("modo_planilla"))
        lineas = mock_registrar.call_args.args[4]
        self.assertEqual(len(lineas), 2)
        self.assertEqual(lineas[0]["id_mpr_maquina"], 10)
        self.assertEqual(lineas[1]["id_mpr_maquina"], 10)
        self.assertEqual({ln["turno_id"] for ln in lineas}, {1, 2})
        msgs = [m.message for m in get_messages(request)]
        self.assertTrue(any("registrado exitosamente" in m.lower() for m in msgs))

    @patch("mpr.repositories.parte.precarga_planilla_por_fecha")
    @patch("mpr.services._fabricando_por_componentes")
    @patch("mpr.services._query_enviados_todos_componentes")
    @patch("mpr.services._pivot_stock_por_tipo_mpr")
    @patch("mpr.services_maquina_linea._operarios_roster_celda_por_linea")
    @patch("mpr.services.listar_turnos")
    @patch("mpr.services_maquina_linea.construir_datos_planilla_control_calidad")
    @patch("mpr.views._get_base_empresa", return_value=EMPRESA)
    @patch("mpr.services.obtener_config_mpr", return_value={"bloquear_parte_supera_fabricando": True})
    @patch("mpr.services_maquina_linea.listar_lineas", return_value=[{"id": 1, "nombre": "L1"}])
    @patch("mpr.services_maquina_linea.listar_maquinas", return_value=[{"id": 10, "nombre": "M1"}])
    def test_get_precarga_reedicion_muestra_cantidades_guardadas(
        self,
        _maquinas,
        _lineas,
        _cfg,
        _base,
        mock_planilla,
        mock_turnos,
        mock_operarios_celda,
        mock_pivot,
        mock_envios,
        mock_fabricando,
        mock_precarga,
    ):
        """Tras un registro previo, la grilla precarga docenas/pares por turno."""
        mock_planilla.return_value = _planilla_maquinas_dos_filas()
        mock_turnos.return_value = _turnos_mtn()
        mock_operarios_celda.return_value = {1: {"manana": [], "tarde": [], "noche": []}}
        mock_envios.return_value = {100: 24}
        mock_pivot.return_value = ({}, {})
        mock_fabricando.return_value = {100: 24.0}
        mock_precarga.return_value = {
            (10, 100, 1): {"docenas": 1, "pares": 0},
            (10, 100, 2): {"docenas": 0, "pares": 6},
        }

        request = self.factory.get("/mpr/parte-produccion/?fecha=21/07/2026")
        request.session = {"user": {"base_empresa": EMPRESA}}
        request.user = self.user
        _add_messages(request)
        response = ParteProduccionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        filas = response.context_data["grilla_planilla"]["filas"]
        fila = next(f for f in filas if f["id_articulo"] == 100)
        self.assertEqual(fila["turnos"][1]["docenas"], 1)
        self.assertEqual(fila["turnos"][2]["pares"], 6)
        self.assertEqual(fila["ingresado"], 18)

    @patch("mpr.services._registrar_asiento_fisico_opp_parte")
    @patch("mpr.services.get_deposito_produccion_mpr", return_value=5)
    @patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"})
    @patch("mpr.repositories.parte.crear_parte_con_lineas")
    @patch("mpr.services.cupo_fabricando_por_articulo")
    @patch("mpr.views._get_base_empresa", return_value=EMPRESA)
    def test_post_rechaza_sobre_cupo_mensaje_es(
        self,
        _base,
        mock_cupo,
        mock_crear,
        _op,
        _dep,
        _asiento,
    ):
        mock_cupo.return_value = {100: 24.0}
        data = _post_planilla_base(
            parte_maq_10_art_100_turno_1_docenas="1",
            parte_maq_10_art_100_turno_1_pares="0",
            parte_maq_10_art_100_turno_1_op="5",
            parte_maq_10_art_100_turno_2_docenas="1",
            parte_maq_10_art_100_turno_2_pares="6",
            parte_maq_10_art_100_turno_2_op="5",
        )
        response, request = self._post_registrar(data)

        self.assertEqual(response.status_code, 302)
        mock_crear.assert_not_called()
        msgs = [m.message for m in get_messages(request)]
        self.assertTrue(any("Fabricando" in m for m in msgs))
        self.assertFalse(any("registrado exitosamente" in m.lower() for m in msgs))
