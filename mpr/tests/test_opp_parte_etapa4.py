"""
Tests — MPR Etapa 4: Parte de Producción (Ledger OPP-parte).

Cobertura:
- TestMprParteModelos: creación modelos y constraints DB.
- TestMprParteAjuste: ajuste positivo/negativo, rechazo si negativo.
- TestOppParteAcumulado: acumulado por pack, backward-safe.
- TestTableroRefinamiento: enviado usa fórmula definitiva OPT−OPP.

Comando:
    docker exec Synap_app python manage.py test mpr.tests.test_opp_parte_etapa4 --keepdb --noinput
"""
from datetime import date, time
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import SimpleTestCase, TestCase

from mpr.models import MprParte, MprParteAjuste, MprParteLinea, MprRosterDia, MprTurno
from mpr.services import (
    TIPO_MPR_2DA_SELECCION,
    TIPO_MPR_PLANCHADO,
    TIPO_MPR_PRODUCCION,
    TIPO_MPR_SCRAP,
    TIPO_MPR_SEMI_ELABORADO,
    TIPO_MPR_TERMINADO,
    agregar_ajuste_parte,
    listar_tablero_por_articulo,
    opp_parte_acumulado_por_pack,
)

EMPRESA = "EmpresaTestEtapa4"


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


def _crear_parte(turno, fecha=None, id_usuario=1):
    if fecha is None:
        fecha = date(2026, 7, 3)
    return MprParte.objects.create(
        base_empresa=EMPRESA,
        fecha_produccion=fecha,
        turno=turno,
        id_usuario=id_usuario,
    )


def _crear_linea(parte, id_articulo, id_operario, cantidad):
    return MprParteLinea.objects.create(
        parte=parte,
        id_articulo=id_articulo,
        id_operario=id_operario,
        operario_nombre="Operario Test",
        cantidad=Decimal(str(cantidad)),
    )


# ---------------------------------------------------------------------------
# Fase 1: Modelos y constraints DB
# ---------------------------------------------------------------------------

class TestMprParteModelos(TestCase):
    """REQ-OPP-001: Modelos MprParte, MprParteLinea — constraints y persistencia."""

    def setUp(self):
        self.turno = _crear_turno()

    def test_crear_parte_y_linea_ok(self):
        """Parte + línea se persisten sin error."""
        parte = _crear_parte(self.turno)
        linea = _crear_linea(parte, id_articulo=10, id_operario=5, cantidad=8)
        self.assertIsNotNone(parte.pk)
        self.assertIsNotNone(linea.pk)
        self.assertEqual(linea.cantidad, Decimal("8"))

    def test_unique_constraint_parte_linea(self):
        """Duplicate (parte, id_articulo, id_operario) lanza IntegrityError."""
        parte = _crear_parte(self.turno)
        _crear_linea(parte, id_articulo=10, id_operario=5, cantidad=8)
        with self.assertRaises(IntegrityError):
            _crear_linea(parte, id_articulo=10, id_operario=5, cantidad=3)

    def test_multiples_partes_mismo_turno_fecha_ok(self):
        """Múltiples MprParte con mismo turno+fecha se permiten (no hay constraint de cabecera)."""
        parte1 = _crear_parte(self.turno, fecha=date(2026, 7, 3))
        parte2 = _crear_parte(self.turno, fecha=date(2026, 7, 3))
        self.assertNotEqual(parte1.pk, parte2.pk)

    def test_parte_str_formato_fecha(self):
        """__str__ de MprParte incluye fecha en formato dd/MM/yyyy."""
        parte = _crear_parte(self.turno, fecha=date(2026, 7, 3))
        str_parte = str(parte)
        self.assertIn("03/07/2026", str_parte)

    def test_ledger_only_no_cambia_stock(self):
        """
        REQ-OPP-004: Registrar parte NO escribe en stock_deposito ni tablas MySQL legacy.
        Verificamos indirectamente: MprParteLinea no tiene campo que referencie stock_deposito.
        """
        parte = _crear_parte(self.turno)
        linea = _crear_linea(parte, id_articulo=10, id_operario=5, cantidad=20)
        # No debe existir relación con stock_deposito
        self.assertFalse(hasattr(linea, "stock_deposito_id"))
        self.assertFalse(hasattr(linea, "movimiento_stock_id"))

    def test_fecha_pasada_permitida(self):
        """REQ-OPP-005: fecha_produccion pasada se persiste sin error."""
        parte = _crear_parte(self.turno, fecha=date(2026, 6, 28))
        self.assertEqual(parte.fecha_produccion, date(2026, 6, 28))

    def test_aislacion_base_empresa(self):
        """REQ-OPP-008: partes de otra empresa no se mezclan."""
        otra_empresa = "OtraEmpresa"
        turno_otra = MprTurno.objects.create(
            base_empresa=otra_empresa, nombre="Tarde",
            hora_inicio=time(14, 0), hora_fin=time(22, 0), activo=True
        )
        parte_otra = MprParte.objects.create(
            base_empresa=otra_empresa, fecha_produccion=date(2026, 7, 3),
            turno=turno_otra, id_usuario=1,
        )
        partes_empresa = list(MprParte.objects.filter(base_empresa=EMPRESA))
        self.assertNotIn(parte_otra, partes_empresa)


# ---------------------------------------------------------------------------
# Fase 2: Ajuste delta
# ---------------------------------------------------------------------------

class TestMprParteAjuste(TestCase):
    """REQ-OPP-006: Ajustes append-only, cantidad efectiva, rechazo si negativo."""

    def setUp(self):
        self.turno = _crear_turno(nombre="Tarde")
        self.parte = _crear_parte(self.turno)
        self.linea = _crear_linea(self.parte, id_articulo=20, id_operario=7, cantidad=10)

    def test_ajuste_positivo_incrementa_efectiva(self):
        """delta=+5 → cantidad_efectiva = 10+5 = 15. linea.cantidad sigue en 10."""
        ajuste = agregar_ajuste_parte(
            EMPRESA, str(self.parte.pk),
            id_articulo=20, id_operario=7,
            delta=Decimal("5"), motivo="corrección manual", id_usuario=1,
        )
        self.assertIsNotNone(ajuste.pk)
        # linea.cantidad no se modifica
        self.linea.refresh_from_db()
        self.assertEqual(self.linea.cantidad, Decimal("10"))
        # cantidad efectiva = 10 + 5 = 15
        deltas = MprParteAjuste.objects.filter(
            parte=self.parte, id_articulo=20, id_operario=7
        ).aggregate(total=__import__("django.db.models", fromlist=["Sum"]).Sum("delta"))["total"]
        self.assertEqual(self.linea.cantidad + (deltas or 0), Decimal("15"))

    def test_ajuste_negativo_reduce_efectiva(self):
        """delta=-3 → cantidad_efectiva = 10-3 = 7."""
        agregar_ajuste_parte(
            EMPRESA, str(self.parte.pk),
            id_articulo=20, id_operario=7,
            delta=Decimal("-3"), motivo="descuento", id_usuario=1,
        )
        from django.db.models import Sum
        deltas = MprParteAjuste.objects.filter(
            parte=self.parte, id_articulo=20, id_operario=7
        ).aggregate(total=Sum("delta"))["total"]
        self.linea.refresh_from_db()
        self.assertEqual(self.linea.cantidad + (deltas or 0), Decimal("7"))

    def test_ajuste_rechazado_si_negativa(self):
        """delta=-10 sobre cantidad=5 lanza ValidationError en español."""
        linea_chica = _crear_linea(self.parte, id_articulo=30, id_operario=8, cantidad=5)
        with self.assertRaises(ValidationError) as cm:
            agregar_ajuste_parte(
                EMPRESA, str(self.parte.pk),
                id_articulo=30, id_operario=8,
                delta=Decimal("-10"), motivo="test", id_usuario=1,
            )
        msg = str(cm.exception)
        self.assertIn("negativ", msg.lower())

    def test_ajuste_rechaza_parte_de_otra_empresa(self):
        """ValidationError si parte_id no pertenece a la empresa solicitada."""
        with self.assertRaises(ValidationError):
            agregar_ajuste_parte(
                "OtraEmpresa", str(self.parte.pk),
                id_articulo=20, id_operario=7,
                delta=Decimal("1"), motivo="test", id_usuario=1,
            )

    def test_ajuste_acumula_multiples_deltas(self):
        """Varios ajustes se acumulan: 10+3-2 = 11."""
        agregar_ajuste_parte(
            EMPRESA, str(self.parte.pk), id_articulo=20, id_operario=7,
            delta=Decimal("3"), motivo="A", id_usuario=1,
        )
        agregar_ajuste_parte(
            EMPRESA, str(self.parte.pk), id_articulo=20, id_operario=7,
            delta=Decimal("-2"), motivo="B", id_usuario=1,
        )
        from django.db.models import Sum
        deltas = MprParteAjuste.objects.filter(
            parte=self.parte, id_articulo=20, id_operario=7
        ).aggregate(total=Sum("delta"))["total"]
        self.linea.refresh_from_db()
        self.assertEqual(self.linea.cantidad + (deltas or 0), Decimal("11"))


# ---------------------------------------------------------------------------
# Fase 3: opp_parte_acumulado_por_pack
# ---------------------------------------------------------------------------

class TestOppParteAcumulado(TestCase):
    """REQ-OPP-008, delta REQ-024: servicio de acumulado por pack."""

    def setUp(self):
        self.turno = _crear_turno(nombre="Noche")

    def test_sin_partes_retorna_vacio(self):
        """Backward-safe: sin MprParteLineas → {} (no falla)."""
        resultado = opp_parte_acumulado_por_pack(EMPRESA)
        self.assertEqual(resultado, {})

    def test_con_lineas_acumula_por_pack(self):
        """Suma cantidades de todas las líneas para el mismo pack."""
        parte = _crear_parte(self.turno)
        _crear_linea(parte, id_articulo=100, id_operario=1, cantidad=10)
        _crear_linea(parte, id_articulo=100, id_operario=2, cantidad=5)
        _crear_linea(parte, id_articulo=200, id_operario=1, cantidad=8)

        resultado = opp_parte_acumulado_por_pack(EMPRESA)
        self.assertIn(100, resultado)
        self.assertIn(200, resultado)
        self.assertEqual(resultado[100], Decimal("15"))
        self.assertEqual(resultado[200], Decimal("8"))

    def test_con_ajustes_suma_deltas(self):
        """Ajustes delta se suman al acumulado del pack."""
        parte = _crear_parte(self.turno)
        _crear_linea(parte, id_articulo=100, id_operario=1, cantidad=10)
        MprParteAjuste.objects.create(
            parte=parte, id_articulo=100, id_operario=1,
            delta=Decimal("3"), motivo="adj", id_usuario=1,
        )
        MprParteAjuste.objects.create(
            parte=parte, id_articulo=100, id_operario=1,
            delta=Decimal("-1"), motivo="adj2", id_usuario=1,
        )

        resultado = opp_parte_acumulado_por_pack(EMPRESA)
        # 10 (linea) + 3 - 1 (ajustes) = 12
        self.assertEqual(resultado[100], Decimal("12"))

    def test_filtrado_por_pack_ids(self):
        """pack_ids filtra solo los artículos solicitados."""
        parte = _crear_parte(self.turno)
        _crear_linea(parte, id_articulo=100, id_operario=1, cantidad=10)
        _crear_linea(parte, id_articulo=200, id_operario=1, cantidad=8)

        resultado = opp_parte_acumulado_por_pack(EMPRESA, pack_ids=[100])
        self.assertIn(100, resultado)
        self.assertNotIn(200, resultado)

    def test_aislacion_empresa(self):
        """No mezcla datos de otra empresa."""
        otra = "OtraEmpresaAcum"
        turno2 = MprTurno.objects.create(
            base_empresa=otra, nombre="X",
            hora_inicio=time(8, 0), hora_fin=time(16, 0), activo=True
        )
        parte2 = MprParte.objects.create(
            base_empresa=otra, fecha_produccion=date(2026, 7, 3),
            turno=turno2, id_usuario=1,
        )
        MprParteLinea.objects.create(
            parte=parte2, id_articulo=100, id_operario=1,
            operario_nombre="-", cantidad=Decimal("50"),
        )

        resultado = opp_parte_acumulado_por_pack(EMPRESA)
        self.assertNotIn(100, resultado)


# ---------------------------------------------------------------------------
# Fase 4: Refinamiento Tablero — fórmula definitiva Enviado
# ---------------------------------------------------------------------------

def _abm_map_simple():
    return {1: 100}


def _bom_map_simple():
    return {
        100: {
            "cabecera": {"id_en_abm": 100, "nombre_en_abm": "Pack A"},
            "componentes": [
                {
                    "id_articulo": 10,
                    "cantidad_articulo": 2.0,
                    "codigo_articulo": "COMP-10",
                    "descripcion_articulo": "Componente 10",
                },
            ],
        }
    }


def _stock_vacio():
    tipos = [
        TIPO_MPR_PRODUCCION, TIPO_MPR_PLANCHADO, TIPO_MPR_2DA_SELECCION,
        TIPO_MPR_SEMI_ELABORADO, TIPO_MPR_SCRAP, TIPO_MPR_TERMINADO,
    ]
    return {10: {t: 0.0 for t in tipos}}


def _desc_map():
    return {10: ("COMP-10", "Componente Diez")}


class TestTableroRefinamiento(SimpleTestCase):
    """
    delta REQ-024: Enviado usa fórmula definitiva OPT−OPP.
    Usa mocks completos (no requiere DB MySQL).
    Importante: _nombre_tabla también se parchea para forzar que _query_enviado_packs sea llamada.
    """

    # Nombre truthy para simular que la tabla existe en la base MySQL legacy
    TABLA_MOCK = "lista_produccion_agrupada"

    def _patch_servicio(self, opt_pack_map=None, opp_map=None,
                        filas_pack=None, abm_map=None, bom_map=None,
                        stock_pivot=None):
        if opt_pack_map is None:
            opt_pack_map = {}
        if opp_map is None:
            opp_map = {}
        if filas_pack is None:
            filas_pack = [
                {
                    "id_articulo": 1,
                    "cantidad_a_fabricar": 10.0,
                    "cantidad_pedida_pedido": 10.0,
                    "stock_terminado": 0.0,
                }
            ]
        if abm_map is None:
            abm_map = _abm_map_simple()
        if bom_map is None:
            bom_map = _bom_map_simple()
        if stock_pivot is None:
            stock_pivot = _stock_vacio()

        # Nota: patch _nombre_tabla para que devuelva el nombre de la tabla y así
        # la rama "if tbl_agrupada:" sea True y _query_enviado_packs sea invocada.
        patches = [
            patch("mpr.services.listar_ventana_pack", return_value=filas_pack),
            patch("mpr.services.mysql_cursor"),
            patch("mpr.services._nombre_tabla", return_value=self.TABLA_MOCK),
            patch("mpr.services._query_enviado_packs", return_value=opt_pack_map),
            patch("mpr.services.opp_parte_acumulado_por_pack", return_value={
                k: Decimal(str(v)) for k, v in (opp_map or {}).items()
            }),
            patch("mpr.services.bulk_id_en_abm", return_value=abm_map),
            patch("mpr.services.bulk_bom_detalle", return_value=bom_map),
            patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=(stock_pivot, stock_pivot)),
            patch("mpr.services._fetch_descripciones_articulo", return_value=_desc_map()),
            # E7 backward-safe: sin envíos tablero → Enviado_tablero=0
            patch("mpr.services._query_enviado_tablero_componente", return_value={}),
        ]
        return patches

    def _call(self, patches):
        activos = [p.start() for p in patches]
        # índice 1 = mysql_cursor context manager mock
        ctx_mock = MagicMock()
        ctx_mock.__enter__ = MagicMock(return_value=MagicMock())
        ctx_mock.__exit__ = MagicMock(return_value=False)
        activos[1].return_value = ctx_mock
        try:
            return listar_tablero_por_articulo("empresa_test")
        finally:
            for p in patches:
                p.stop()

    def test_sin_partes_backward_safe(self):
        """
        REQ-024 Esc.24.1: sin OPP-parte → Enviado == OPT_liberado_acum (backward-safe).
        OPT=50, OPP=0 → Enviado pack=50, explota BOM 1:2 → componente=100.
        """
        patches = self._patch_servicio(opt_pack_map={1: 50.0}, opp_map={})
        resultado = self._call(patches)
        self.assertTrue(len(resultado) > 0)
        fila = resultado[0]
        # pack=1, BOM 1:2, OPP=0 → enviado_pack_map={1:50} → componente 10 = 50*2 = 100
        self.assertAlmostEqual(fila["enviado"], 100.0)

    def test_enviado_con_partes_descuenta_opp(self):
        """
        REQ-024 Esc.24.2: OPT=50, OPP=20 → Enviado_pack=max(0,50-20)=30, componente=60.
        """
        patches = self._patch_servicio(opt_pack_map={1: 50.0}, opp_map={1: 20})
        resultado = self._call(patches)
        fila = resultado[0]
        # enviado_pack_map={1: 30.0} → BOM 1:2 → componente=60
        self.assertAlmostEqual(fila["enviado"], 60.0)

    def test_enviado_nunca_negativo(self):
        """
        REQ-024 Esc.24.3: OPT=30, OPP=50 → max(0, 30-50)=0 → enviado=0.
        """
        patches = self._patch_servicio(opt_pack_map={1: 30.0}, opp_map={1: 50})
        resultado = self._call(patches)
        fila = resultado[0]
        # enviado_pack_map={1: 0} → enviado componente = 0
        self.assertGreaterEqual(fila["enviado"], 0.0)
        self.assertAlmostEqual(fila["enviado"], 0.0)

    def test_produccion_inalterada_por_partes(self):
        """
        REQ-024 Esc.24.4: columna Producción no se ve afectada por OPP-parte.
        """
        stock_pivot = {10: {
            TIPO_MPR_PRODUCCION: 20.0,
            TIPO_MPR_PLANCHADO: 0.0, TIPO_MPR_2DA_SELECCION: 0.0,
            TIPO_MPR_SEMI_ELABORADO: 0.0, TIPO_MPR_SCRAP: 0.0,
            TIPO_MPR_TERMINADO: 0.0,
        }}
        patches = self._patch_servicio(
            opt_pack_map={1: 50.0}, opp_map={1: 10},
            stock_pivot=stock_pivot,
        )
        resultado = self._call(patches)
        fila = resultado[0]
        # Producción sigue siendo 20 (stock_deposito, sin cambio)
        self.assertAlmostEqual(fila["produccion"], 20.0)

    def test_opp_error_backward_safe(self):
        """Si opp_parte_acumulado_por_pack falla, el tablero sigue devolviendo resultado."""
        patches = self._patch_servicio(opt_pack_map={1: 50.0})
        # Reemplaza opp_parte_acumulado_por_pack (índice 4) por uno que lanza excepción
        patches_extra = list(patches)
        patches_extra[4] = patch("mpr.services.opp_parte_acumulado_por_pack", side_effect=Exception("DB error"))
        resultado = self._call(patches_extra)
        # No debe lanzar excepción; debe devolver lista (puede tener enviado reducido o no)
        self.assertIsInstance(resultado, list)
