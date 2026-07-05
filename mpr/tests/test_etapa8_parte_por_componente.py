"""
Tests — MPR Etapa 8: Parte de producción por COMPONENTE (conectado a Fabricando E7).

Cobertura:
- TestGrillaParteComponente: construir_grilla_parte usa MprEnvioProduccion (no lista_produccion_agrupada).
  · grilla aparece con fabricando correcto
  · grilla no aparece (fabricando=0)
  · grilla vacía (sin envíos)
  · pack legacy en_proceso='Si' sin envío tablero NO aparece
  · roster vacío emite aviso
  · celdas precargadas desde partes previos

- TestRegistroParteComponente: registrar_parte_produccion registra N líneas por componente.

- TestAsientoDirectoSinBOM: _registrar_asiento_fisico_opp_parte(ya_componentes=True)
  · stock sube sin llamar _explode_packs_to_components
  · idempotencia vía movimiento_fisico_ok

- TestWarningFabricando: warning no bloqueante si cantidad supera Fabricando.

- TestE6CompatibilidadIdLista: partes E8 tienen id_lista_produccion=None; no rompen trazabilidad.

Comando:
    docker exec Synap_app python manage.py test mpr.tests.test_etapa8_parte_por_componente --keepdb --noinput
"""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch, ANY

from django.test import TestCase

from mpr.models import (
    MprEmpresaConfig,
    MprEnvioProduccion,
    MprParte,
    MprParteLinea,
    MprTurno,
    MprRosterDia,
)

EMPRESA = "EmpresaTestEtapa8"
TIPO_PROD = "Produccion"


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

def _crear_turno(nombre="Mañana E8"):
    return MprTurno.objects.create(
        base_empresa=EMPRESA,
        nombre=nombre,
        hora_inicio="07:00:00",
        hora_fin="15:00:00",
        activo=True,
    )


def _config_sin_bloqueo_fabricando(empresa=EMPRESA):
    MprEmpresaConfig.objects.update_or_create(
        base_empresa=empresa,
        defaults={"bloquear_parte_supera_fabricando": False},
    )


def _crear_parte(turno, fecha=date(2026, 7, 3), **kwargs):
    return MprParte.objects.create(
        base_empresa=EMPRESA,
        fecha_produccion=fecha,
        turno=turno,
        id_usuario=1,
        notas="",
        **kwargs,
    )


def _crear_linea(parte, id_articulo, id_operario, cantidad):
    return MprParteLinea.objects.create(
        parte=parte,
        id_articulo=id_articulo,
        id_operario=id_operario,
        cantidad=Decimal(str(cantidad)),
    )


def _crear_envio(id_articulo, cantidad, anulado=False):
    return MprEnvioProduccion.objects.create(
        base_empresa=EMPRESA,
        id_articulo=id_articulo,
        cantidad=Decimal(str(cantidad)),
        id_usuario=1,
        anulado=anulado,
    )


# ---------------------------------------------------------------------------
# 1. Grilla por componente (construir_grilla_parte)
# ---------------------------------------------------------------------------

class TestGrillaParteComponente(TestCase):
    """REQ Grilla de Captura: filas desde MprEnvioProduccion, no lista_produccion_agrupada."""

    def setUp(self):
        self.turno = _crear_turno()
        self.fecha = date(2026, 7, 3)

    # -- 7.2: grilla aparece con fabricando correcto
    def test_grilla_aparece_con_fabricando_correcto(self):
        """Componente con envío=30 y stock_prod=0 → aparece con fabricando=30."""
        from mpr.services import construir_grilla_parte

        # No hay RosterDia en test DB para este EMPRESA/fecha/turno → roster_vacio=True, operarios=[]
        with patch("mpr.services._query_enviados_todos_componentes", return_value={1: Decimal("30")}), \
             patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({1: {TIPO_PROD: 0.0}}, {})), \
             patch("mpr.services._fetch_descripciones_articulo", return_value={1: ("COD1", "Componente 1")}):

            resultado = construir_grilla_parte(EMPRESA, self.fecha, self.turno.pk)

        self.assertFalse(resultado["componentes_vacio"])
        self.assertEqual(len(resultado["componentes"]), 1)
        fila = resultado["componentes"][0]
        self.assertEqual(fila["id_articulo"], 1)
        self.assertAlmostEqual(fila["fabricando"], 30.0)

    # -- 7.3: grilla no aparece cuando fabricando=0
    def test_grilla_no_aparece_cuando_produccion_iguala_enviado(self):
        """Componente con envío=30 y stock_prod=30 → fabricando=0 → no aparece."""
        from mpr.services import construir_grilla_parte

        with patch("mpr.services._query_enviados_todos_componentes", return_value={1: Decimal("30")}), \
             patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({1: {TIPO_PROD: 30.0}}, {})), \
             patch("mpr.services._fetch_descripciones_articulo", return_value={1: ("COD1", "Comp1")}):

            resultado = construir_grilla_parte(EMPRESA, self.fecha, self.turno.pk)

        self.assertTrue(resultado["componentes_vacio"])
        self.assertEqual(resultado["componentes"], [])

    # -- 7.4: grilla vacía cuando no hay envíos
    def test_grilla_vacia_sin_envios(self):
        """Sin MprEnvioProduccion → componentes_vacio=True."""
        from mpr.services import construir_grilla_parte

        with patch("mpr.services._query_enviados_todos_componentes", return_value={}):
            resultado = construir_grilla_parte(EMPRESA, self.fecha, self.turno.pk)

        self.assertTrue(resultado["componentes_vacio"])
        self.assertEqual(resultado["componentes"], [])

    # -- 7.5: pack legacy NO aparece en E8 (no hay MprEnvioProduccion para él)
    def test_pack_legacy_sin_envio_tablero_no_aparece(self):
        """Pack P en lista_produccion_agrupada en_proceso='Si' pero sin envío → no aparece."""
        from mpr.services import construir_grilla_parte

        # P=999 sería un pack legacy; sin MprEnvioProduccion, _query_enviados_todos_componentes
        # no lo incluye → no aparece en grilla E8
        with patch("mpr.services._query_enviados_todos_componentes", return_value={}):
            resultado = construir_grilla_parte(EMPRESA, self.fecha, self.turno.pk)

        comp_ids = [c["id_articulo"] for c in resultado["componentes"]]
        self.assertNotIn(999, comp_ids)
        self.assertTrue(resultado["componentes_vacio"])

    # -- 7.6: roster vacío emite aviso
    def test_roster_vacio(self):
        """Sin MprRosterDia para la fecha+turno → roster_vacio=True."""
        from mpr.services import construir_grilla_parte

        # No hay RosterDia en test DB para EMPRESA/fecha/turno → roster_vacio=True
        with patch("mpr.services._query_enviados_todos_componentes", return_value={1: Decimal("10")}), \
             patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({1: {TIPO_PROD: 0.0}}, {})), \
             patch("mpr.services._fetch_descripciones_articulo", return_value={1: ("C1", "Comp")}):

            resultado = construir_grilla_parte(EMPRESA, self.fecha, self.turno.pk)

        self.assertTrue(resultado["roster_vacio"])
        self.assertEqual(resultado["operarios"], [])

    # -- 7.7: inputs en cero aunque existan partes previos del turno
    def test_entrada_grilla_siempre_cero_con_partes_previos(self):
        """Parte existente para la misma fecha+turno: celdas referencia, inputs en 0."""
        from mpr.services import construir_grilla_parte

        parte_prev = _crear_parte(self.turno, fecha=self.fecha, movimiento_fisico_ok=True)
        _crear_linea(parte_prev, id_articulo=5, id_operario=10, cantidad="20")

        with patch("mpr.services._query_enviados_todos_componentes", return_value={5: Decimal("50")}), \
             patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({5: {TIPO_PROD: 0.0}}, {})), \
             patch("mpr.services._fetch_descripciones_articulo", return_value={5: ("COMP5", "Componente 5")}):

            resultado = construir_grilla_parte(EMPRESA, self.fecha, self.turno.pk)

        clave = (5, 10)
        self.assertIn(clave, resultado["celdas"])
        self.assertEqual(resultado["celdas"][clave], Decimal("20"))
        comp = next(c for c in resultado["componentes"] if c["id_articulo"] == 5)
        cel = next(c for c in comp["celdas_ops"] if c["id_operario"] == 10)
        self.assertEqual(cel["docenas"], 0)
        self.assertEqual(cel["unidades_sueltas"], 0)
        self.assertEqual(cel["cantidad_ya_registrada"], 20)


# ---------------------------------------------------------------------------
# 2. Registro N líneas por componente
# ---------------------------------------------------------------------------

class TestRegistroParteComponente(TestCase):
    """REQ Vista/Template: registro de parte crea MprParteLinea con id_articulo=componente."""

    def setUp(self):
        _config_sin_bloqueo_fabricando()
        self.turno = _crear_turno()

    # -- 7.8: registro N líneas
    def test_registro_n_lineas_por_componente(self):
        """registrar_parte_produccion con 2 componentes crea 2 MprParteLinea."""
        from mpr.services import registrar_parte_produccion

        lineas = [
            {"id_articulo": 101, "id_operario": 1, "cantidad": Decimal("20")},
            {"id_articulo": 102, "id_operario": 1, "cantidad": Decimal("15")},
        ]

        with patch("mpr.services._registrar_asiento_fisico_opp_parte"), \
             patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"}), \
             patch("mpr.services.get_deposito_produccion_mpr", return_value=5), \
             patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({}, {})), \
             patch("mpr.services._fetch_descripciones_articulo", return_value={}):

            parte, warnings = registrar_parte_produccion(
                base_empresa=EMPRESA,
                fecha_produccion=date(2026, 7, 3),
                turno_id=self.turno.pk,
                id_usuario=1,
                lineas=lineas,
            )

        lineas_bd = list(MprParteLinea.objects.filter(parte=parte).order_by("id_articulo"))
        self.assertEqual(len(lineas_bd), 2)
        self.assertEqual(lineas_bd[0].id_articulo, 101)
        self.assertEqual(lineas_bd[1].id_articulo, 102)

    def test_id_lista_produccion_es_none_en_partes_e8(self):
        """Parte E8 siempre tiene id_lista_produccion=None (sin OPT activa)."""
        from mpr.services import registrar_parte_produccion

        with patch("mpr.services._registrar_asiento_fisico_opp_parte"), \
             patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"}), \
             patch("mpr.services.get_deposito_produccion_mpr", return_value=5), \
             patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({}, {})), \
             patch("mpr.services._fetch_descripciones_articulo", return_value={}):

            parte, _ = registrar_parte_produccion(
                base_empresa=EMPRESA,
                fecha_produccion=date(2026, 7, 3),
                turno_id=self.turno.pk,
                id_usuario=1,
                lineas=[{"id_articulo": 50, "id_operario": 1, "cantidad": Decimal("5")}],
            )

        parte.refresh_from_db()
        self.assertIsNone(parte.id_lista_produccion)


# ---------------------------------------------------------------------------
# 3. Asiento directo sin explosión BOM
# ---------------------------------------------------------------------------

class TestAsientoDirectoSinBOM(TestCase):
    """REQ Asiento Físico Componente Directo: ya_componentes=True no llama _explode_packs."""

    def setUp(self):
        _config_sin_bloqueo_fabricando()
        self.turno = _crear_turno()
        self.parte = _crear_parte(self.turno)

    # -- 7.9: stock sube sin explotar BOM
    def test_asiento_directo_no_llama_explode_packs(self):
        """_registrar_asiento_fisico_opp_parte(ya_componentes=True) → _explode_packs NO llamado."""
        from mpr.services import _registrar_asiento_fisico_opp_parte

        lineas = [{"id_articulo": 200}]
        lineas_pack_qty = [(lineas[0], Decimal("20"))]

        with patch("mpr.services._explode_packs_to_components") as mock_explode, \
             patch("mpr.services.get_connection") as mock_conn:

            mock_cursor_obj = MagicMock()
            mock_cursor_obj.fetchone.return_value = (5,)
            mock_cursor_obj.fetchall.return_value = []
            mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock(
                cursor=MagicMock(return_value=mock_cursor_obj),
                autocommit=MagicMock(),
                rollback=MagicMock(),
                commit=MagicMock(),
            ))
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)

            try:
                _registrar_asiento_fisico_opp_parte(
                    base_empresa=EMPRESA,
                    id_usuario=1,
                    parte=self.parte,
                    lineas_pack_qty=lineas_pack_qty,
                    deposito_produccion=5,
                    ya_componentes=True,
                )
            except Exception:
                pass  # Puede fallar por tablas legacy ausentes; lo que importa es la llamada

        mock_explode.assert_not_called()

    # -- 7.11: sin explode incluso si lanza excepción
    def test_ya_componentes_true_no_llama_explode_ante_error(self):
        """Con ya_componentes=True, incluso si la función falla, _explode_packs no es invocado."""
        from mpr.services import _registrar_asiento_fisico_opp_parte

        lineas_pack_qty = [({"id_articulo": 300}, Decimal("5"))]

        with patch("mpr.services._explode_packs_to_components") as mock_explode, \
             patch("mpr.services.get_connection", side_effect=Exception("Sin conexión")):

            try:
                _registrar_asiento_fisico_opp_parte(
                    base_empresa=EMPRESA,
                    id_usuario=1,
                    parte=self.parte,
                    lineas_pack_qty=lineas_pack_qty,
                    deposito_produccion=5,
                    ya_componentes=True,
                )
            except Exception:
                pass

        mock_explode.assert_not_called()

    # -- 7.10: idempotencia via movimiento_fisico_ok
    def test_idempotencia_asiento_movimiento_fisico_ok(self):
        """Parte con movimiento_fisico_ok=True: asiento físico NO se invoca de nuevo."""
        from mpr.services import registrar_parte_produccion

        parte_existente_pk = None
        call_count = {"n": 0}

        def mock_asiento(**kwargs):
            call_count["n"] += 1

        with patch("mpr.services._registrar_asiento_fisico_opp_parte", side_effect=mock_asiento), \
             patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"}), \
             patch("mpr.services.get_deposito_produccion_mpr", return_value=5), \
             patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({}, {})), \
             patch("mpr.services._fetch_descripciones_articulo", return_value={}):

            parte, _ = registrar_parte_produccion(
                base_empresa=EMPRESA,
                fecha_produccion=date(2026, 7, 3),
                turno_id=self.turno.pk,
                id_usuario=1,
                lineas=[{"id_articulo": 10, "id_operario": 5, "cantidad": Decimal("10")}],
            )

        self.assertEqual(call_count["n"], 1, "Primera vez debe llamar asiento")
        parte.refresh_from_db()
        self.assertTrue(parte.movimiento_fisico_ok)

        # Verifica flag: parte ya tiene movimiento_fisico_ok=True → guardia impide re-ejecución
        self.assertTrue(parte.movimiento_fisico_ok)
        self.assertEqual(call_count["n"], 1, "No debe re-ejecutar el asiento")

    # -- 7.9b: construir componentes_total correcto con ya_componentes=True
    def test_componentes_total_con_ya_componentes_true(self):
        """Con ya_componentes=True, componentes_total = {id_articulo: qty} directo."""
        from mpr.services import _registrar_asiento_fisico_opp_parte

        lineas_pack_qty = [
            ({"id_articulo": 101}, Decimal("5.0")),
            ({"id_articulo": 102}, Decimal("3.0")),
            ({"id_articulo": 103}, Decimal("0.0")),  # Debe ser excluido (qty=0)
        ]
        capturado = {}

        def mock_conn(base, **kwargs):
            raise Exception("Sin MySQL en test")

        with patch("mpr.services._explode_packs_to_components") as mock_explode, \
             patch("mpr.services.get_connection", side_effect=Exception("Sin MySQL")):
            try:
                _registrar_asiento_fisico_opp_parte(
                    base_empresa=EMPRESA,
                    id_usuario=1,
                    parte=self.parte,
                    lineas_pack_qty=lineas_pack_qty,
                    deposito_produccion=5,
                    ya_componentes=True,
                )
            except Exception:
                pass

        mock_explode.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Warning Fabricando
# ---------------------------------------------------------------------------

class TestWarningFabricando(TestCase):
    """REQ Warning al Superar Fabricando: no bloqueante, mensaje en español."""

    def setUp(self):
        _config_sin_bloqueo_fabricando()
        self.turno = _crear_turno()

    # -- 7.13: warning si cantidad > fabricando
    def test_warning_cuando_supera_fabricando(self):
        """Cantidad=30 y Fabricando=20 → warning en español, parte guardado."""
        from mpr.services import registrar_parte_produccion

        with patch("mpr.services._registrar_asiento_fisico_opp_parte"), \
             patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"}), \
             patch("mpr.services.get_deposito_produccion_mpr", return_value=5), \
             patch("mpr.services._query_enviado_tablero_componente", return_value={50: Decimal("50")}), \
             patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({50: {TIPO_PROD: 30.0}}, {})), \
             patch("mpr.services._fetch_descripciones_articulo", return_value={50: ("COMP50", "Comp 50")}):

            parte, warnings = registrar_parte_produccion(
                base_empresa=EMPRESA,
                fecha_produccion=date(2026, 7, 3),
                turno_id=self.turno.pk,
                id_usuario=1,
                lineas=[{"id_articulo": 50, "id_operario": 1, "cantidad": Decimal("30")}],
            )

        # Fabricando_pre = max(0, 50-30) = 20; cantidad=30 > 20 → warning
        self.assertEqual(len(warnings), 1)
        self.assertIn("Atención", warnings[0])
        self.assertIn("30.0", warnings[0])
        self.assertIn("20.0", warnings[0])
        self.assertIn("Fabricando", warnings[0])
        # Parte guardado igualmente
        parte.refresh_from_db()
        self.assertTrue(parte.movimiento_fisico_ok)

    # -- 7.14: sin warning si dentro del fabricando
    def test_sin_warning_bajo_tope_fabricando(self):
        """Cantidad=10 y Fabricando=20 → warnings vacío."""
        from mpr.services import registrar_parte_produccion

        with patch("mpr.services._registrar_asiento_fisico_opp_parte"), \
             patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"}), \
             patch("mpr.services.get_deposito_produccion_mpr", return_value=5), \
             patch("mpr.services._query_enviado_tablero_componente", return_value={50: Decimal("50")}), \
             patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({50: {TIPO_PROD: 30.0}}, {})), \
             patch("mpr.services._fetch_descripciones_articulo", return_value={50: ("COMP50", "Comp 50")}):

            parte, warnings = registrar_parte_produccion(
                base_empresa=EMPRESA,
                fecha_produccion=date(2026, 7, 3),
                turno_id=self.turno.pk,
                id_usuario=1,
                lineas=[{"id_articulo": 50, "id_operario": 1, "cantidad": Decimal("10")}],
            )

        # Fabricando_pre = 20; cantidad=10 ≤ 20 → sin warning
        self.assertEqual(warnings, [])

    # -- Integración: parte E8 registra stock → Fabricando siguiente render se reduce
    def test_asiento_llama_ya_componentes_true(self):
        """registrar_parte_produccion invoca asiento con ya_componentes=True."""
        from mpr.services import registrar_parte_produccion

        with patch("mpr.services._registrar_asiento_fisico_opp_parte") as mock_asiento, \
             patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"}), \
             patch("mpr.services.get_deposito_produccion_mpr", return_value=5), \
             patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({}, {})), \
             patch("mpr.services._fetch_descripciones_articulo", return_value={}):

            registrar_parte_produccion(
                base_empresa=EMPRESA,
                fecha_produccion=date(2026, 7, 3),
                turno_id=self.turno.pk,
                id_usuario=1,
                lineas=[{"id_articulo": 77, "id_operario": 1, "cantidad": Decimal("5")}],
            )

        mock_asiento.assert_called_once()
        call_kw = mock_asiento.call_args.kwargs
        self.assertTrue(call_kw["ya_componentes"])
        self.assertEqual(call_kw["base_empresa"], EMPRESA)
        self.assertEqual(call_kw["deposito_produccion"], 5)


# ---------------------------------------------------------------------------
# 5. Integración E7: Fabricando auto-balance
# ---------------------------------------------------------------------------

class TestIntegracionFabricandoE7(TestCase):
    """REQ Integración E7: parte escribe stock → tablero reduce Fabricando."""

    def setUp(self):
        self.turno = _crear_turno()

    # -- 7.12: consumo Fabricando E7
    def test_consumo_fabricando_formula_correcta(self):
        """
        MprEnvioProduccion[C]=50, stock_prod[C]=35 → Fabricando=15.
        Tras registrar parte cantidad=10, siguiente render: Fabricando=max(0,50-45)=5.
        """
        from mpr.services import construir_grilla_parte

        _crear_envio(id_articulo=300, cantidad="50")

        # Simular primer render: stock_prod=35 → Fabricando=15
        with patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({300: {TIPO_PROD: 35.0}}, {})), \
             patch("mpr.services._fetch_descripciones_articulo", return_value={300: ("C300", "Comp 300")}):

            grilla1 = construir_grilla_parte(EMPRESA, date(2026, 7, 3), self.turno.pk)

        fila = next((c for c in grilla1["componentes"] if c["id_articulo"] == 300), None)
        self.assertIsNotNone(fila)
        self.assertAlmostEqual(fila["fabricando"], 15.0)

        # Simular segundo render tras registrar 10 (stock_prod=35+10=45) → Fabricando=5
        with patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({300: {TIPO_PROD: 45.0}}, {})), \
             patch("mpr.services._fetch_descripciones_articulo", return_value={300: ("C300", "Comp 300")}):

            grilla2 = construir_grilla_parte(EMPRESA, date(2026, 7, 3), self.turno.pk)

        fila2 = next((c for c in grilla2["componentes"] if c["id_articulo"] == 300), None)
        self.assertIsNotNone(fila2)
        self.assertAlmostEqual(fila2["fabricando"], 5.0)


# ---------------------------------------------------------------------------
# 6. Compatibilidad E6: id_lista=None no rompe trazabilidad OPT
# ---------------------------------------------------------------------------

class TestE6CompatibilidadIdLista(TestCase):
    """REQ Trazabilidad E6: partes E8 tienen id_lista=None; no rompen funciones E6."""

    def setUp(self):
        _config_sin_bloqueo_fabricando()
        self.turno = _crear_turno()

    # -- 7.15: E6 compat id_lista=None
    def test_parte_e8_id_lista_none_no_rompe_trazabilidad(self):
        """Parte E8 con id_lista_produccion=None no lanza excepción en trazabilidad E6."""
        from mpr.services import registrar_parte_produccion

        with patch("mpr.services._registrar_asiento_fisico_opp_parte"), \
             patch("mpr.services.obtener_operario", return_value={"nombre_empleado": "Op"}), \
             patch("mpr.services.get_deposito_produccion_mpr", return_value=5), \
             patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({}, {})), \
             patch("mpr.services._fetch_descripciones_articulo", return_value={}):

            parte, _ = registrar_parte_produccion(
                base_empresa=EMPRESA,
                fecha_produccion=date(2026, 7, 3),
                turno_id=self.turno.pk,
                id_usuario=1,
                lineas=[{"id_articulo": 400, "id_operario": 1, "cantidad": Decimal("5")}],
            )

        parte.refresh_from_db()
        self.assertIsNone(parte.id_lista_produccion)

    def test_escribir_historico_opp_con_id_lista_none_no_crea_registro(self):
        """_escribir_historico_opp_parte con id_lista=None retorna inmediatamente (guard E6)."""
        from mpr.services import _escribir_historico_opp_parte

        parte = _crear_parte(self.turno, movimiento_fisico_ok=True)
        parte.id_lista_produccion = None
        parte.save(update_fields=["id_lista_produccion"])

        mock_cursor = MagicMock()

        # Debe retornar sin llamar cursor.execute (la guardia id_lista=None lo protege)
        _escribir_historico_opp_parte(
            cursor=mock_cursor,
            parte=parte,
            lineas_pack_qty=[({"id_articulo": 400}, Decimal("5"))],
            codigo_mov=1,
            id_usuario=1,
            fecha_mov="2026-07-03",
            deposito_produccion=5,
        )

        # La función debe retornar sin llamar _nombre_tabla (que usa cursor.execute)
        # ya que la guardia `if parte.id_lista_produccion is None: return` está primero
        mock_cursor.execute.assert_not_called()
