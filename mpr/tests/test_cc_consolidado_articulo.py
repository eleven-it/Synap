"""
Tests — CC consolidado por artículo (plan §12.1 S1–S9).

PR1 (RED): infraestructura DDL 007 + tests que fallan hasta implementar
``mpr/services_cc_consolidado.py`` en PR2.

Comando:
    docker exec Synap_app python manage.py test mpr.tests.test_cc_consolidado_articulo --keepdb --noinput
"""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase, TestCase

from mpr.models import MprParte, MprParteLinea, MprTurno
from mpr.services import (
    TIPO_MPR_2DA_SELECCION,
    TIPO_MPR_PRODUCCION,
    TIPO_MPR_SCRAP,
    TIPO_MPR_SEMI_ELABORADO,
)

EMPRESA = "EmpresaTestCcConsolidado"
FECHA = date(2026, 8, 20)
ID_USUARIO = 1

# Artículos de la batería S1–S9
ART_S1 = 1001
ART_S2 = 1002
ART_HUERFANO = 1004
ART_S6 = 1006
ART_S8 = 1008
ART_OK = 2001
ART_EXCEDE = 2002

ID_LUIS = 501
ID_MARIO = 502
TURNO_MANANA = 1
TURNO_TARDE = 2


# ---------------------------------------------------------------------------
# Helpers — fixtures empresa de prueba
# ---------------------------------------------------------------------------


def _import_confirmar():
    from mpr.services_cc_consolidado import confirmar_cc_consolidado  # noqa: WPS433

    return confirmar_cc_consolidado


def _import_bloques():
    from mpr.services_cc_consolidado import construir_bloques_cc_articulo  # noqa: WPS433

    return construir_bloques_cc_articulo


def _assert_modulo_cc_pendiente(import_fn):
    """RED PR1: falla hasta que PR2 implemente el servicio."""
    try:
        import_fn()
    except ImportError as exc:
        if "confirmar_cc_consolidado" in str(exc) or "construir_bloques_cc_articulo" in str(exc):
            raise AssertionError(
                "RED PR1: falta implementar mpr.services_cc_consolidado (PR2)"
            ) from exc
        raise


class _ConexionCcFalsa:
    """Conexión mínima para aislar la unidad de la base legacy."""

    def __init__(self):
        self.cursor_obj = MagicMock()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def autocommit(self, _valor):
        return None

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        return None

    def rollback(self):
        return None


def _payload_semi(id_art: int, qty: Decimal) -> Dict[int, Dict[str, Any]]:
    return {id_art: {"semi": qty, "lineas": []}}


def _payload_semi_2da(
    id_art: int,
    qty_semi: Decimal,
    id_operario: int,
    id_turno: int,
    qty_2da: Decimal,
) -> Dict[int, Dict[str, Any]]:
    return {
        id_art: {
            "semi": qty_semi,
            "lineas": [(id_operario, id_turno, "2da", qty_2da)],
        }
    }


def _payload_2da_huerfano(id_art: int, id_operario: int, id_turno: int, qty: Decimal):
    return {
        id_art: {
            "semi": Decimal("0"),
            "lineas": [(id_operario, id_turno, "2da", qty)],
        }
    }


def _payload_lote_dos_articulos(
    art_ok: int,
    semi_ok: Decimal,
    art_fail: int,
    semi_fail: Decimal,
) -> Dict[int, Dict[str, Any]]:
    return {
        art_ok: {"semi": semi_ok, "lineas": []},
        art_fail: {"semi": semi_fail, "lineas": []},
    }


def _crear_turno(nombre: str = "Mañana", turno_id: Optional[int] = None) -> MprTurno:
    defaults = {
        "base_empresa": EMPRESA,
        "nombre": nombre,
        "hora_inicio": time(6, 0),
        "hora_fin": time(14, 0),
        "activo": True,
    }
    if turno_id is not None:
        turno, _ = MprTurno.objects.update_or_create(
            base_empresa=EMPRESA,
            id=turno_id,
            defaults=defaults,
        )
        return turno
    return MprTurno.objects.create(**defaults)


def _crear_parte_con_lineas(
    lineas: List[Tuple[int, int, int, Decimal]],
    *,
    fecha: date = FECHA,
    turno: Optional[MprTurno] = None,
) -> MprParte:
    """Crea parte con líneas (id_articulo, id_operario, id_mpr_turno implícito en turno, cantidad)."""
    turno = turno or _crear_turno()
    parte = MprParte.objects.create(
        base_empresa=EMPRESA,
        fecha_produccion=fecha,
        turno=turno,
        id_usuario=ID_USUARIO,
    )
    nombres = {ID_LUIS: "Luis", ID_MARIO: "Mario"}
    for id_art, id_op, _tid, cant in lineas:
        MprParteLinea.objects.create(
            parte=parte,
            id_articulo=id_art,
            id_operario=id_op,
            operario_nombre=nombres.get(id_op, f"Op {id_op}"),
            cantidad=cant,
        )
    return parte


def _fake_stock_pivot(saldos: Dict[int, float]) -> Dict[int, Dict[str, float]]:
    tipos = [
        TIPO_MPR_PRODUCCION,
        TIPO_MPR_SEMI_ELABORADO,
        TIPO_MPR_2DA_SELECCION,
        TIPO_MPR_SCRAP,
    ]
    pivot: Dict[int, Dict[str, float]] = {}
    for id_art, prod in saldos.items():
        pivot[id_art] = {t: 0.0 for t in tipos}
        pivot[id_art][TIPO_MPR_PRODUCCION] = prod
    return pivot


# ---------------------------------------------------------------------------
# Infraestructura DDL (PR1 — GREEN estructural)
# ---------------------------------------------------------------------------


class TestCcConsolidadoDdl(SimpleTestCase):
    """DDL 007 y registro en catalog.py (idempotente)."""

    def test_sql_007_existe_y_documenta_uk_fecha(self):
        app_path = Path(apps.get_app_config("mpr").path)
        sql_path = app_path / "sql" / "007_mpr_cc_borrador_consolidado.sql"
        self.assertTrue(sql_path.is_file(), f"Falta {sql_path}")
        content = sql_path.read_text(encoding="utf-8")
        self.assertIn("mpr_cc_borrador", content)
        self.assertIn("mpr_cc_borrador_linea", content)
        self.assertIn("uk_mpr_cc_borrador_fecha", content)
        self.assertIn("id_operario INT NOT NULL DEFAULT 0", content)
        self.assertIn("id_mpr_turno BIGINT NOT NULL DEFAULT 0", content)

    def test_baseline_auditoria_solo_select(self):
        docs_path = Path(settings.BASE_DIR) / "docs" / "mpr"
        sql_path = docs_path / "AUDITORIA_CC_CONSOLIDADO_BASELINE.sql"
        self.assertTrue(sql_path.is_file(), f"Falta {sql_path}")
        content = sql_path.read_text(encoding="utf-8").upper()
        self.assertIn("SELECT", content)
        self.assertNotIn("UPDATE ", content)
        self.assertNotIn("DELETE ", content)
        self.assertNotIn("INSERT ", content)

    @patch("core.services.legacy_mysql_schema.catalog.nombre_tabla_real")
    @patch("core.services.legacy_mysql_schema.catalog.indice_existe", return_value=False)
    def test_catalog_aplica_007_si_tabla_ausente(self, _mock_idx, mock_nombre):
        from core.services.legacy_mysql_schema.catalog import run_mpr_core_tables_mysql

        def _nombre(cursor, tabla):
            if tabla == "mpr_cc_borrador":
                return None
            if tabla == "mpr_transicion_lote":
                return "mpr_transicion_lote"
            if tabla == "mpr_clasificacion_borrador":
                return "mpr_clasificacion_borrador"
            return tabla

        mock_nombre.side_effect = _nombre
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        result = run_mpr_core_tables_mysql(conn)

        self.assertTrue(result["success"])
        statements = " ".join(
            str(c.args[0]).lower() for c in cursor.execute.call_args_list if c.args
        )
        self.assertIn("mpr_cc_borrador", statements)
        self.assertIn("idx_mpr_tl_fecha_art_dest", statements)

    @patch("core.services.legacy_mysql_schema.catalog.nombre_tabla_real")
    @patch("core.services.legacy_mysql_schema.catalog.indice_existe", return_value=True)
    def test_catalog_noop_007_si_tabla_presente(self, _mock_idx, mock_nombre):
        from core.services.legacy_mysql_schema.catalog import run_mpr_core_tables_mysql

        mock_nombre.return_value = "mpr_cc_borrador"
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        result = run_mpr_core_tables_mysql(conn)

        self.assertTrue(result["success"])
        statements = " ".join(
            str(c.args[0]).lower() for c in cursor.execute.call_args_list if c.args
        )
        self.assertNotIn("create table if not exists mpr_cc_borrador", statements)


# ---------------------------------------------------------------------------
# RED S1–S9 — confirmación atómica (PR2 GREEN)
# ---------------------------------------------------------------------------


class TestConfirmacionSaldo(TestCase):
    """Matriz §12.1 S1–S5, S7, S9 — ``confirmar_cc_consolidado``."""

    databases = {"default"}

    def setUp(self):
        MprParte.objects.filter(base_empresa=EMPRESA).delete()
        MprTurno.objects.filter(base_empresa=EMPRESA).delete()
        self.conexion_patcher = patch(
            "mpr.services_cc_consolidado.get_connection",
            side_effect=lambda _base: _ConexionCcFalsa(),
        )
        self.conexion_patcher.start()

    def tearDown(self):
        self.conexion_patcher.stop()

    @patch("mpr.services_cc_consolidado._saldo_produccion_articulo", create=True, return_value=Decimal("0"))
    @patch("mpr.services_cc_consolidado._transferir_cc_en_cursor", create=True)
    def test_s1_semi_120_prod_cero_ledger_sin_operario(self, mock_tx, mock_saldo):
        """S1: Prod=120 → Semi 120 → Prod 0, 1 fila ledger id_operario NULL."""
        _assert_modulo_cc_pendiente(_import_confirmar)
        confirmar = _import_confirmar()
        mock_saldo.side_effect = [Decimal("120"), Decimal("0")]
        mock_tx.return_value = True

        resultado = confirmar(
            EMPRESA,
            ID_USUARIO,
            FECHA,
            _payload_semi(ART_S1, Decimal("120")),
        )

        self.assertIn(ART_S1, resultado["ok"])
        self.assertEqual(resultado["errores"], [])
        mock_tx.assert_called()
        kwargs_list = [c.kwargs for c in mock_tx.call_args_list if c.kwargs]
        semi_calls = [
            k for k in kwargs_list if k.get("tipo_destino") == TIPO_MPR_SEMI_ELABORADO
        ]
        self.assertEqual(len(semi_calls), 1)
        self.assertIsNone(semi_calls[0].get("id_operario"))
        self.assertIsNone(semi_calls[0].get("id_mpr_turno"))

    @patch(
        "mpr.services_cc_consolidado._atribuible_2da_scrap",
        create=True,
        return_value=Decimal("20"),
    )
    @patch("mpr.services_cc_consolidado._nombre_operario_parte", return_value="Luis")
    @patch("mpr.services_cc_consolidado._celda_parte_existe", return_value=True)
    @patch("mpr.services_cc_consolidado._es_huerfano", return_value=False)
    @patch("mpr.services_cc_consolidado._saldo_produccion_articulo", create=True, return_value=Decimal("0"))
    @patch("mpr.services_cc_consolidado._transferir_cc_en_cursor", create=True)
    def test_s2_semi_100_2da_luis_20_prod_cero(
        self, mock_tx, mock_saldo, _mock_huerfano, _mock_celda, _mock_nombre,
        _mock_atribuible,
    ):
        """S2: Semi 100 + 2da Luis 20 → Prod 0; Semi sin op; 2da con op."""
        _assert_modulo_cc_pendiente(_import_confirmar)
        confirmar = _import_confirmar()
        mock_saldo.side_effect = [Decimal("120"), Decimal("0")]
        mock_tx.return_value = True

        resultado = confirmar(
            EMPRESA,
            ID_USUARIO,
            FECHA,
            _payload_semi_2da(ART_S2, Decimal("100"), ID_LUIS, TURNO_MANANA, Decimal("20")),
        )

        self.assertIn(ART_S2, resultado["ok"])
        kwargs_list = [c.kwargs for c in mock_tx.call_args_list if c.kwargs]
        semi = next(k for k in kwargs_list if k.get("tipo_destino") == TIPO_MPR_SEMI_ELABORADO)
        seg2da = next(k for k in kwargs_list if k.get("tipo_destino") == TIPO_MPR_2DA_SELECCION)
        self.assertIsNone(semi.get("id_operario"))
        self.assertEqual(seg2da.get("id_operario"), ID_LUIS)
        self.assertEqual(seg2da.get("id_mpr_turno"), TURNO_MANANA)

    @patch(
        "mpr.services_cc_consolidado._atribuible_2da_scrap",
        create=True,
        return_value=Decimal("45"),
    )
    @patch("mpr.services_cc_consolidado._celda_parte_existe", return_value=True)
    @patch("mpr.services_cc_consolidado._es_huerfano", return_value=False)
    @patch(
        "mpr.services_cc_consolidado._saldo_produccion_articulo",
        create=True,
        return_value=Decimal("100"),
    )
    @patch("mpr.services_cc_consolidado._transferir_cc_en_cursor", create=True)
    def test_exceso_2da_por_operario_rechaza_sin_transferir(
        self,
        mock_tx,
        mock_saldo,
        _mock_huerfano,
        _mock_celda,
        mock_atribuible,
    ):
        """50 de 2da exceden las 45 unidades atribuibles del parte colapsado."""
        confirmar = _import_confirmar()

        resultado = confirmar(
            EMPRESA,
            ID_USUARIO,
            FECHA,
            _payload_semi_2da(
                ART_S2,
                Decimal("0"),
                ID_LUIS,
                TURNO_MANANA,
                Decimal("50"),
            ),
        )

        self.assertNotIn(ART_S2, resultado["ok"])
        self.assertEqual(mock_saldo.return_value, Decimal("100"))
        self.assertIn(
            "La 2da/desperdicio supera lo fabricado por el operario en el parte.",
            [mensaje for _articulo, mensaje in resultado["errores"]],
        )
        mock_atribuible.assert_called_once_with(
            EMPRESA, FECHA, ART_S2, ID_LUIS, TURNO_MANANA
        )
        mock_tx.assert_not_called()

    @patch("mpr.services_cc_consolidado._contar_ledger_nuevos", create=True, return_value=0)
    @patch("mpr.services_cc_consolidado._transferir_cc_en_cursor", create=True)
    @patch("mpr.services_cc_consolidado._saldo_produccion_articulo", create=True, return_value=Decimal("120"))
    def test_s3_exceso_sobre_saldo_rechaza_sin_filas(self, mock_saldo, mock_tx, mock_cnt):
        """S3: Semi 100 + 2da 30 sobre Prod 120 → rechazo; cero filas nuevas."""
        _assert_modulo_cc_pendiente(_import_confirmar)
        confirmar = _import_confirmar()

        resultado = confirmar(
            EMPRESA,
            ID_USUARIO,
            FECHA,
            _payload_semi_2da(ART_S1, Decimal("100"), ID_LUIS, TURNO_MANANA, Decimal("30")),
        )

        self.assertNotIn(ART_S1, resultado.get("ok", []))
        self.assertTrue(resultado["errores"])
        mock_tx.assert_not_called()
        mock_cnt.assert_not_called()

    @patch("mpr.services_cc_consolidado._es_huerfano", create=True, return_value=True)
    @patch("mpr.services_cc_consolidado._saldo_produccion_articulo", create=True, return_value=Decimal("0"))
    @patch("mpr.services_cc_consolidado._transferir_cc_en_cursor", create=True)
    def test_s4_huerfano_semi_50_sin_2da(self, mock_tx, mock_saldo, _mock_h):
        """S4: Huérfano Prod=50, Semi 50 → OK sin 2da."""
        _assert_modulo_cc_pendiente(_import_confirmar)
        confirmar = _import_confirmar()
        mock_saldo.side_effect = [Decimal("50"), Decimal("0")]
        mock_tx.return_value = True

        resultado = confirmar(
            EMPRESA,
            ID_USUARIO,
            FECHA,
            _payload_semi(ART_HUERFANO, Decimal("50")),
        )

        self.assertIn(ART_HUERFANO, resultado["ok"])
        kwargs_list = [c.kwargs for c in mock_tx.call_args_list if c.kwargs]
        self.assertEqual(len(kwargs_list), 1)
        self.assertEqual(kwargs_list[0]["tipo_destino"], TIPO_MPR_SEMI_ELABORADO)

    @patch("mpr.services_cc_consolidado._es_huerfano", create=True, return_value=True)
    @patch("mpr.services_cc_consolidado._saldo_produccion_articulo", create=True, return_value=Decimal("50"))
    @patch("mpr.services_cc_consolidado._transferir_cc_en_cursor", create=True)
    def test_s5_huerfano_post_2da_rechazado(self, mock_tx, mock_saldo, _mock_h):
        """S5: Huérfano Prod=50, POST 2da 10 → rechazo; Prod 50."""
        _assert_modulo_cc_pendiente(_import_confirmar)
        confirmar = _import_confirmar()

        resultado = confirmar(
            EMPRESA,
            ID_USUARIO,
            FECHA,
            _payload_2da_huerfano(ART_HUERFANO, ID_LUIS, TURNO_MANANA, Decimal("10")),
        )

        self.assertNotIn(ART_HUERFANO, resultado.get("ok", []))
        self.assertTrue(resultado["errores"])
        mock_tx.assert_not_called()

    @patch(
        "mpr.services_cc_consolidado._atribuible_2da_scrap",
        create=True,
        return_value=Decimal("20"),
    )
    @patch("mpr.services_cc_consolidado._nombre_operario_parte", return_value="Luis")
    @patch("mpr.services_cc_consolidado._celda_parte_existe", return_value=True)
    @patch("mpr.services_cc_consolidado._es_huerfano", return_value=False)
    @patch("mpr.services_cc_consolidado._saldo_produccion_articulo", create=True, return_value=Decimal("120"))
    @patch("mpr.services_cc_consolidado._transferir_cc_en_cursor", create=True)
    def test_s7_fallo_2da_rollback_prod_intacto(
        self, mock_tx, mock_saldo, _mock_huerfano, _mock_celda, _mock_nombre,
        _mock_atribuible,
    ):
        """S7: Fallo inyectado en 2da tras Semi → rollback; Prod intacto."""
        _assert_modulo_cc_pendiente(_import_confirmar)
        confirmar = _import_confirmar()
        mock_saldo.return_value = Decimal("120")

        def _tx_side_effect(**kwargs):
            if kwargs.get("tipo_destino") == TIPO_MPR_2DA_SELECCION:
                raise RuntimeError("fallo simulado 2da")
            return True

        mock_tx.side_effect = _tx_side_effect

        resultado = confirmar(
            EMPRESA,
            ID_USUARIO,
            FECHA,
            _payload_semi_2da(ART_S1, Decimal("80"), ID_LUIS, TURNO_MANANA, Decimal("20")),
        )

        self.assertNotIn(ART_S1, resultado.get("ok", []))
        self.assertTrue(resultado["errores"])
        semi_calls = [
            c.kwargs
            for c in mock_tx.call_args_list
            if c.kwargs.get("tipo_destino") == TIPO_MPR_SEMI_ELABORADO
        ]
        self.assertEqual(len(semi_calls), 0, "Rollback: no debe persistir fila Semi")

    @patch("mpr.services_cc_consolidado._borrador_lineas_articulo", create=True)
    @patch("mpr.services_cc_consolidado._saldo_produccion_articulo", create=True)
    @patch("mpr.services_cc_consolidado._transferir_cc_en_cursor", create=True)
    def test_s9_parcial_articulo_1_ok_2_excede_borrador_2_intacto(
        self, mock_tx, mock_saldo, mock_borrador
    ):
        """S9: Artículo 1 OK; artículo 2 excede → parcial; borrador 2 intacto."""
        _assert_modulo_cc_pendiente(_import_confirmar)
        confirmar = _import_confirmar()
        mock_tx.return_value = True

        def _saldo(id_art, *_a, **_k):
            if id_art == ART_OK:
                return Decimal("50")
            if id_art == ART_EXCEDE:
                return Decimal("30")
            return Decimal("0")

        mock_saldo.side_effect = _saldo
        mock_borrador.return_value = [{"id_articulo": ART_EXCEDE, "cant_semi": Decimal("10")}]

        payload = _payload_lote_dos_articulos(ART_OK, Decimal("50"), ART_EXCEDE, Decimal("40"))
        resultado = confirmar(EMPRESA, ID_USUARIO, FECHA, payload)

        self.assertIn(ART_OK, resultado["ok"])
        self.assertNotIn(ART_EXCEDE, resultado.get("ok", []))
        errores_ids = [e[0] for e in resultado["errores"]]
        self.assertIn(ART_EXCEDE, errores_ids)
        mock_borrador.assert_called()


class TestGrillaSaldo(TestCase):
    """Matriz §12.1 S6, S8 — ``construir_bloques_cc_articulo``."""

    databases = {"default"}

    def setUp(self):
        MprParte.objects.filter(base_empresa=EMPRESA).delete()
        MprTurno.objects.filter(base_empresa=EMPRESA).delete()

    @patch("mpr.repositories.clasificacion_borrador.tiene_borrador", return_value=False)
    @patch("mpr.repositories.clasificacion_borrador.tiene_borrador_cc_consolidado", return_value=False)
    @patch(
        "mpr.repositories.transicion_lote.clasificado_segunda_scrap_por_celda_fecha",
        return_value={},
    )
    @patch("mpr.services._fetch_descripciones_articulo", return_value={ART_S6: ("A-6", "Artículo 6")})
    @patch("mpr.repositories.transicion_lote.semi_agregado_por_articulo_fecha", return_value={})
    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion", create=True)
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    def test_s6_parte_100_saldo_150_tope_150(
        self, mock_celdas, mock_pivot, _mock_semi, _mock_desc,
        _mock_clasificado, _mock_nuevo, _mock_viejo,
    ):
        """S6: Parte 100, saldo Prod 150 → tope/mostrar 150 (no 100)."""
        _assert_modulo_cc_pendiente(_import_bloques)
        bloques_fn = _import_bloques()
        mock_celdas.return_value = {
            (0, ART_S6, ID_LUIS, TURNO_MANANA): {
                "cantidad": Decimal("100"),
                "operario_nombre": "Luis",
                "turno_nombre": "Mañana",
            }
        }
        mock_pivot.return_value = _fake_stock_pivot({ART_S6: 150.0})

        resultado = bloques_fn(EMPRESA, FECHA)

        bloque = next(b for b in resultado["bloques"] if b["id_articulo"] == ART_S6)
        self.assertEqual(Decimal(str(bloque["saldo_produccion"])), Decimal("150"))
        self.assertEqual(Decimal(str(bloque["tope_confirmacion"])), Decimal("150"))

    @patch("mpr.repositories.clasificacion_borrador.tiene_borrador", return_value=False)
    @patch("mpr.repositories.clasificacion_borrador.tiene_borrador_cc_consolidado", return_value=False)
    @patch(
        "mpr.repositories.transicion_lote.clasificado_segunda_scrap_por_celda_fecha",
        return_value={},
    )
    @patch(
        "mpr.repositories.transicion_lote.semi_agregado_por_articulo_fecha",
        create=True,
    )
    @patch("mpr.services._fetch_descripciones_articulo", return_value={ART_S8: ("A-8", "Artículo 8")})
    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion", create=True)
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno", return_value={})
    def test_s8_historico_semi_60_prod_cero_muestra_sin_insert(
        self, mock_celdas, mock_pivot, _mock_desc, mock_semi,
        _mock_clasificado, _mock_nuevo, _mock_viejo,
    ):
        """S8: CC histórico Semi 60 con operario, Prod 0 → muestra 60; sin INSERT."""
        _assert_modulo_cc_pendiente(_import_bloques)
        bloques_fn = _import_bloques()
        mock_pivot.return_value = _fake_stock_pivot({ART_S8: 0.0})
        mock_semi.return_value = {ART_S8: Decimal("60")}

        resultado = bloques_fn(EMPRESA, FECHA, modo_roster=True)

        bloque = next(b for b in resultado["bloques"] if b["id_articulo"] == ART_S8)
        self.assertEqual(Decimal(str(bloque["semi_mostrar"])), Decimal("60"))
        self.assertTrue(bloque.get("solo_lectura"))
        mock_semi.assert_called_once_with(EMPRESA, FECHA, [ART_S8])


class TestParserCcConsolidado(SimpleTestCase):
    """C6 y normalización del centinela de borrador."""

    def test_c6_ignora_semi_legado_y_usa_clave_consolidada(self):
        from mpr.services_cc_consolidado import parsear_post_cc_consolidado

        payload = parsear_post_cc_consolidado(
            {
                "semi_10": "24",
                "semi_10_op_5_t_1_m_2": "999",
                "seg2da_10_op_5_t_1": "6",
            }
        )

        self.assertEqual(payload[10]["semi"], Decimal("24"))
        self.assertEqual(payload[10]["lineas"], [(5, 1, "2da", Decimal("6"))])

    def test_parser_convierte_docenas_y_descarta_ceros(self):
        from mpr.services_cc_consolidado import parsear_post_cc_consolidado

        payload = parsear_post_cc_consolidado(
            {
                "semi_11_docenas": "2",
                "semi_11_unidades": "3",
                "scrap_11_op_7_t_2_docenas": "1",
                "scrap_11_op_7_t_2_unidades": "0",
            }
        )

        self.assertEqual(payload[11]["semi"], Decimal("27"))
        self.assertEqual(payload[11]["lineas"], [(7, 2, "scrap", Decimal("12"))])

    def test_centinela_borrador_semi_se_normaliza_a_none(self):
        from mpr.repositories.clasificacion_borrador import normalizar_linea_cc_borrador

        linea = normalizar_linea_cc_borrador(
            {
                "id_articulo": "10",
                "id_operario": 0,
                "id_mpr_turno": "0",
                "cant_semi": "12",
            }
        )

        self.assertEqual(linea["id_articulo"], 10)
        self.assertIsNone(linea["id_operario"])
        self.assertIsNone(linea["id_mpr_turno"])
        self.assertEqual(linea["cant_semi"], Decimal("12"))


class TestGrillaBloqueo(SimpleTestCase):
    """B1–B6: grilla diaria consolidada y bloqueo dual del parte."""

    @patch("mpr.repositories.clasificacion_borrador.tiene_borrador", return_value=False)
    @patch("mpr.repositories.clasificacion_borrador.tiene_borrador_cc_consolidado", return_value=False)
    @patch(
        "mpr.repositories.transicion_lote.clasificado_segunda_scrap_por_celda_fecha",
        return_value={},
    )
    @patch("mpr.services._fetch_descripciones_articulo", return_value={ART_S1: ("A-1", "Artículo 1")})
    @patch("mpr.repositories.transicion_lote.semi_agregado_por_articulo_fecha", return_value={})
    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion")
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    def test_b1_b2_ignora_turno_y_colapsa_maquinas(
        self,
        mock_celdas,
        mock_stock,
        _mock_semi,
        _mock_desc,
        _mock_clasificado,
        _mock_nuevo,
        _mock_viejo,
    ):
        mock_celdas.return_value = {
            (10, ART_S1, ID_LUIS, TURNO_MANANA): {
                "cantidad": Decimal("12"),
                "operario_nombre": "Luis",
                "turno_nombre": "Mañana",
            },
            (20, ART_S1, ID_LUIS, TURNO_MANANA): {
                "cantidad": Decimal("18"),
                "operario_nombre": "Luis",
                "turno_nombre": "Mañana",
            },
        }
        mock_stock.return_value = _fake_stock_pivot({ART_S1: 30})

        resultado = _import_bloques()(EMPRESA, FECHA)

        mock_celdas.assert_called_once_with(EMPRESA, FECHA, None)
        self.assertFalse(resultado["requiere_fecha_turno"])
        self.assertEqual(len(resultado["bloques"]), 1)
        self.assertEqual(len(resultado["bloques"][0]["filas"]), 1)
        self.assertEqual(resultado["bloques"][0]["filas"][0]["fabricado"], Decimal("30"))

    @patch("mpr.repositories.clasificacion_borrador.tiene_borrador", return_value=False)
    @patch("mpr.repositories.clasificacion_borrador.tiene_borrador_cc_consolidado", return_value=False)
    @patch(
        "mpr.repositories.transicion_lote.clasificado_segunda_scrap_por_celda_fecha",
        return_value={(ART_S1, ID_LUIS, TURNO_MANANA): Decimal("5")},
    )
    @patch("mpr.services._fetch_descripciones_articulo", return_value={ART_S1: ("A-1", "Artículo 1")})
    @patch("mpr.repositories.transicion_lote.semi_agregado_por_articulo_fecha", return_value={})
    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion")
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    def test_b3_b4_solo_pendiente_oculta_saldo_cero_y_operario_confirmado(
        self,
        mock_celdas,
        mock_stock,
        _mock_semi,
        _mock_desc,
        _mock_clasificado,
        _mock_nuevo,
        _mock_viejo,
    ):
        mock_celdas.return_value = {
            (10, ART_S1, ID_LUIS, TURNO_MANANA): {
                "cantidad": Decimal("10"),
                "operario_nombre": "Luis",
                "turno_nombre": "Mañana",
            },
            (20, ART_S1, ID_MARIO, TURNO_MANANA): {
                "cantidad": Decimal("10"),
                "operario_nombre": "Mario",
                "turno_nombre": "Mañana",
            },
        }
        mock_stock.return_value = _fake_stock_pivot({ART_S1: 20})

        pendiente = _import_bloques()(EMPRESA, FECHA, solo_pendiente=True)

        self.assertEqual(
            [fila["id_operario"] for fila in pendiente["bloques"][0]["filas"]],
            [ID_MARIO],
        )
        self.assertEqual(pendiente["confirmadas_ocultas"], 1)

        mock_stock.return_value = _fake_stock_pivot({ART_S1: 0})
        sin_saldo = _import_bloques()(EMPRESA, FECHA, solo_pendiente=True)
        self.assertEqual(sin_saldo["bloques"], [])

    @patch("mpr.repositories.clasificacion_borrador.tiene_borrador", return_value=True)
    @patch("mpr.repositories.clasificacion_borrador.tiene_borrador_cc_consolidado", return_value=False)
    @patch(
        "mpr.repositories.transicion_lote.clasificado_segunda_scrap_por_celda_fecha",
        return_value={},
    )
    @patch("mpr.services._fetch_descripciones_articulo", return_value={})
    @patch("mpr.repositories.transicion_lote.semi_agregado_por_articulo_fecha", return_value={})
    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno", return_value={})
    def test_avisa_borrador_viejo_incompatible(
        self,
        _mock_celdas,
        _mock_stock,
        _mock_semi,
        _mock_desc,
        _mock_clasificado,
        _mock_nuevo,
        _mock_viejo,
    ):
        resultado = _import_bloques()(EMPRESA, FECHA)

        self.assertTrue(resultado["borrador_incompatible"])
        self.assertEqual(
            resultado["aviso_borrador"],
            "El borrador anterior no es compatible; volvé a cargar.",
        )

    @patch("mpr.repositories.transicion_lote.mysql_cursor")
    def test_b5_b6_query_dual_semi_nuevo_no_bloquea_e_historico_si(self, mock_ctx):
        from mpr.repositories.transicion_lote import turnos_con_control_calidad

        cursor = MagicMock()
        mock_ctx.return_value.__enter__.return_value = cursor
        mock_ctx.return_value.__exit__.return_value = False
        cursor.fetchall.return_value = [{"id_mpr_turno": TURNO_MANANA}]

        resultado = turnos_con_control_calidad(EMPRESA, FECHA)

        self.assertEqual(resultado, {TURNO_MANANA})
        sql = cursor.execute.call_args.args[0]
        self.assertIn("tipo_destino IN ('2daSeleccion', 'Scrap')", sql)
        self.assertIn("tipo_destino = 'SemiElaborado' AND id_operario IS NOT NULL", sql)
        self.assertIn("id_mpr_turno IS NOT NULL", sql)
        self.assertEqual(cursor.execute.call_args.args[1], [FECHA])


class TestBorradorCcConsolidado(SimpleTestCase):
    """B7 y repositorio 007: persistir borrador nunca mueve stock."""

    @patch("mpr.repositories.clasificacion_borrador.mysql_cursor")
    def test_b7_upsert_por_fecha_solo_escribe_tablas_borrador(self, mock_ctx):
        from mpr.repositories.clasificacion_borrador import upsert_borrador_cc_consolidado

        cursor = MagicMock()
        mock_ctx.return_value.__enter__.return_value = cursor
        mock_ctx.return_value.__exit__.return_value = False
        cursor.fetchone.return_value = (91,)

        upsert_borrador_cc_consolidado(
            EMPRESA,
            FECHA,
            ID_USUARIO,
            [
                {
                    "id_articulo": ART_S1,
                    "id_operario": None,
                    "id_mpr_turno": None,
                    "cant_semi": Decimal("12"),
                },
                {
                    "id_articulo": ART_S1,
                    "id_operario": ID_LUIS,
                    "id_mpr_turno": TURNO_MANANA,
                    "cant_2da": Decimal("3"),
                },
                {
                    "id_articulo": ART_S1,
                    "id_operario": ID_LUIS,
                    "id_mpr_turno": TURNO_MANANA,
                    "cant_scrap": Decimal("2"),
                },
            ],
        )

        sql_total = " ".join(str(call.args[0]) for call in cursor.execute.call_args_list)
        self.assertIn("mpr_cc_borrador", sql_total)
        self.assertIn("mpr_cc_borrador_linea", sql_total)
        self.assertNotIn("stock_deposito", sql_total)
        self.assertNotIn("mpr_transicion_lote", sql_total)
        inserts_linea = [
            call for call in cursor.execute.call_args_list
            if "INSERT INTO mpr_cc_borrador_linea" in str(call.args[0])
        ]
        self.assertEqual(len(inserts_linea), 2)
        self.assertEqual(inserts_linea[0].args[1][2:4], [0, 0])
        self.assertEqual(inserts_linea[1].args[1][5:7], [Decimal("3"), Decimal("2")])

    @patch("mpr.repositories.clasificacion_borrador.mysql_cursor")
    def test_listar_normaliza_centinela_y_borrar_solo_articulo(self, mock_ctx):
        from mpr.repositories.clasificacion_borrador import (
            eliminar_borrador_cc_articulo,
            listar_lineas_borrador_cc_consolidado,
        )

        cursor = MagicMock()
        mock_ctx.return_value.__enter__.return_value = cursor
        mock_ctx.return_value.__exit__.return_value = False
        cursor.fetchall.return_value = [
            {
                "id_articulo": ART_S1,
                "id_operario": 0,
                "id_mpr_turno": 0,
                "cant_semi": Decimal("8"),
                "cant_2da": Decimal("0"),
                "cant_scrap": Decimal("0"),
            }
        ]

        lineas = listar_lineas_borrador_cc_consolidado(EMPRESA, FECHA)
        eliminar_borrador_cc_articulo(EMPRESA, FECHA, ART_S1)

        self.assertIsNone(lineas[0]["id_operario"])
        self.assertIsNone(lineas[0]["id_mpr_turno"])
        delete_call = cursor.execute.call_args_list[-1]
        self.assertIn("l.id_articulo = %s", delete_call.args[0])
        self.assertEqual(delete_call.args[1], [str(FECHA), ART_S1])


class TestRendimientoCcConsolidado(SimpleTestCase):
    """B8: Semi NULL queda fuera y 2da atribuida sigue sumando."""

    @patch("mpr.repositories.transicion_lote.mysql_cursor")
    def test_b8_ignora_semi_null_y_suma_segunda(self, mock_ctx):
        from mpr.repositories.transicion_lote import sumar_clasificado_rendimiento_operario

        cursor = MagicMock()
        mock_ctx.return_value.__enter__.return_value = cursor
        mock_ctx.return_value.__exit__.return_value = False
        cursor.fetchall.return_value = [
            {
                "id_operario": ID_LUIS,
                "operario_nombre": "Luis",
                "tipo_destino": "2daSeleccion",
                "total": Decimal("20"),
            }
        ]

        resultado = sumar_clasificado_rendimiento_operario(EMPRESA, FECHA, FECHA)

        self.assertEqual(resultado[ID_LUIS]["semi"], Decimal("0"))
        self.assertEqual(resultado[ID_LUIS]["segunda"], Decimal("20"))
        self.assertIn("id_operario IS NOT NULL", cursor.execute.call_args.args[0])

    @patch("mpr.repositories.transicion_lote.mysql_cursor")
    def test_fabricado_sin_clasificacion_atribuible_devuelve_mapa_vacio(
        self, mock_ctx
    ):
        from mpr.repositories.transicion_lote import sumar_clasificado_rendimiento_operario

        cursor = MagicMock()
        mock_ctx.return_value.__enter__.return_value = cursor
        mock_ctx.return_value.__exit__.return_value = False
        cursor.fetchall.return_value = []

        resultado = sumar_clasificado_rendimiento_operario(EMPRESA, FECHA, FECHA)

        self.assertEqual(resultado, {})
        self.assertIn("id_operario IS NOT NULL", cursor.execute.call_args.args[0])

    @patch("mpr.repositories.transicion_lote.mysql_cursor")
    def test_semi_null_no_se_duplica_entre_operarios(self, mock_ctx):
        from mpr.repositories.transicion_lote import sumar_clasificado_rendimiento_operario

        cursor = MagicMock()
        mock_ctx.return_value.__enter__.return_value = cursor
        mock_ctx.return_value.__exit__.return_value = False
        cursor.fetchall.return_value = [
            {
                "id_operario": ID_LUIS,
                "operario_nombre": "Luis",
                "tipo_destino": "SemiElaborado",
                "total": Decimal("480"),
            }
        ]

        resultado = sumar_clasificado_rendimiento_operario(EMPRESA, FECHA, FECHA)

        self.assertEqual(resultado[ID_LUIS]["semi"], Decimal("480"))
        self.assertNotIn(ID_MARIO, resultado)
        self.assertIn("id_operario IS NOT NULL", cursor.execute.call_args.args[0])
