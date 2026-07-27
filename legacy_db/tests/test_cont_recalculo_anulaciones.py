"""Tests REC-19: reparación de anulaciones incompletas (plan + apply, mocks)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

from django.test import TestCase, override_settings

from contabilidad_audit.models import PREFIJOS_CUENTA_DEFAULT, PlanCorreccion
from contabilidad_audit.services.politicas import calcular_config_hash
from legacy_db.services.cont_recalculo_service import (
    CHECK_ANULACION,
    MARCA_ANUL_REGEN,
    MARCA_REGEN,
    CorreccionContableError,
    _aplicar_item_anulacion,
    _evaluar_problemas_anulacion_cm,
    _filtrar_items_aplicables,
    _plan_reparacion_anulaciones,
    _reconstruir_renglones_comprobante_anulado,
    apply,
    calcular_data_fingerprint,
)


def _politica_base() -> dict:
    return {
        "tratamiento_anulados": "incluir_neutralizado",
        "politica_centavo": "diario_manda",
        "prefijos_cuenta": dict(PREFIJOS_CUENTA_DEFAULT),
        "ejercicios_cerrados": "no_tocar",
        "alcance_recompute": "ejercicio_seleccionado",
        "tolerancia_decimal": Decimal("0.005"),
    }


def _item_marcador(cm: str = "12345") -> dict:
    return {
        "tabla": "cuentaproveedor",
        "clave": {"codigo_movimiento_original": cm, "codigo_movimiento_anul": cm},
        "accion": "insert_marcador",
        "valor_anterior": None,
        "valor_nuevo": {
            "CodigoMovimiento": "0",
            "codigo_movimiento_anul": cm,
            "Detalle": "Anulacion - FA - 1",
            "Anulado": "No",
            "TipoComprobante": "FA",
            "NroComprobante": "1",
            "Fecha": "2025-01-15",
            "CodSucursal": 1,
        },
        "delta": "0",
        "check_id": CHECK_ANULACION,
        "excluido": False,
        "bloqueado": False,
    }


def _item_marcar_original(cm: str = "12345") -> dict:
    return {
        "tabla": "cont_asiento",
        "clave": {"codigo_movimiento": cm},
        "accion": "marcar_original_anulado",
        "valor_anterior": "No",
        "valor_nuevo": "Si",
        "delta": "0",
        "check_id": CHECK_ANULACION,
        "excluido": False,
        "bloqueado": False,
    }


def _item_contra(cm: str = "12345") -> dict:
    return {
        "tabla": "cont_asiento",
        "clave": {"codigo_movimiento_original": cm},
        "accion": "insert_contra_asiento",
        "valor_anterior": None,
        "valor_nuevo": {
            "codigo_movimiento_original": cm,
            "id_concepto_asiento": 4,
            "desc_concepto_asiento": "Anulación-Compra",
            "id_ejercicio": 1,
            "fecha_asiento": date(2025, 1, 15),
            "desc_asiento": "Anulación - FA - 1",
            "desc_renglon_asiento": MARCA_ANUL_REGEN,
            "renglones_preview": [
                {
                    "id_pc": 10,
                    "debe_asiento": "0.00",
                    "haber_asiento": "100.00",
                    "desc_renglon_asiento": MARCA_ANUL_REGEN,
                    "desc_concepto_asiento": "Anulación-Compra",
                    "id_concepto_asiento": 4,
                },
                {
                    "id_pc": 20,
                    "debe_asiento": "100.00",
                    "haber_asiento": "0.00",
                    "desc_renglon_asiento": MARCA_ANUL_REGEN,
                    "desc_concepto_asiento": "Anulación-Compra",
                    "id_concepto_asiento": 4,
                },
            ],
        },
        "delta": "0",
        "check_id": CHECK_ANULACION,
        "excluido": False,
        "bloqueado": False,
    }


def _item_contra_regenerar(cm: str = "9001") -> dict:
    return {
        "tabla": "cont_asiento",
        "clave": {"codigo_movimiento_original": cm},
        "accion": "insert_contra_asiento",
        "valor_anterior": None,
        "valor_nuevo": {
            "codigo_movimiento_original": cm,
            "id_concepto_asiento": 4,
            "desc_concepto_asiento": "Anulación-Compra",
            "id_ejercicio": 1,
            "fecha_asiento": date(2025, 4, 1),
            "desc_asiento": "Compra - Nro Comp. A-9001",
            "desc_renglon_asiento": MARCA_ANUL_REGEN,
            "regenerar_original": True,
            "renglones_original_preview": [
                {
                    "id_pc": 10,
                    "debe_asiento": "200.00",
                    "haber_asiento": "0.00",
                    "id_concepto_asiento": 3,
                    "desc_concepto_asiento": "Compra",
                },
                {
                    "id_pc": 20,
                    "debe_asiento": "0.00",
                    "haber_asiento": "200.00",
                    "id_concepto_asiento": 3,
                    "desc_concepto_asiento": "Compra",
                },
            ],
            "renglones_preview": [
                {
                    "id_pc": 10,
                    "debe_asiento": "0.00",
                    "haber_asiento": "200.00",
                    "desc_renglon_asiento": MARCA_ANUL_REGEN,
                    "desc_concepto_asiento": "Anulación-Compra",
                    "id_concepto_asiento": 4,
                },
                {
                    "id_pc": 20,
                    "debe_asiento": "200.00",
                    "haber_asiento": "0.00",
                    "desc_renglon_asiento": MARCA_ANUL_REGEN,
                    "desc_concepto_asiento": "Anulación-Compra",
                    "id_concepto_asiento": 4,
                },
            ],
        },
        "delta": "0",
        "check_id": CHECK_ANULACION,
        "excluido": False,
        "bloqueado": False,
    }


def _item_bloqueado(cm: str = "999") -> dict:
    return {
        "tabla": "cont_asiento",
        "clave": {"codigo_movimiento_original": cm},
        "accion": "bloqueado",
        "valor_anterior": None,
        "valor_nuevo": None,
        "delta": "0",
        "check_id": CHECK_ANULACION,
        "excluido": True,
        "bloqueado": True,
        "motivo_bloqueo": "contra_no_invierte_original",
    }


def _crear_plan(items: list[dict], base_empresa: str = "test_empresa") -> PlanCorreccion:
    politica = _politica_base()
    from django.utils import timezone

    ahora = timezone.now()
    aplicables = _filtrar_items_aplicables(items)
    fp = calcular_data_fingerprint(aplicables)
    return PlanCorreccion.objects.create(
        base_empresa=base_empresa,
        alcance={"id_ejercicio": 1},
        config_hash=calcular_config_hash(politica),
        data_fingerprint=fp,
        plan={"items": items, "items_anulacion": [i for i in items if i.get("check_id") == CHECK_ANULACION]},
        estado="propuesto",
        creado_por="tester",
        creado_en=ahora,
        expira_en=ahora + timedelta(minutes=30),
    )


class EvaluarProblemasAnulacionTestCase(TestCase):
    def test_falta_marcador_y_contra(self):
        cur = MagicMock()
        # marcador cnt=0; pendientes=0 total>0 (ya anulado); orig_tot; contra None
        cur.fetchone.side_effect = [
            {"TipoComprobante": "FA", "TipoOP": ""},
            {"cnt": 0},
            {"pendientes": 0, "total": 2},
            {"codigo_movimiento": "1", "d": Decimal("100"), "h": Decimal("100")},
            None,
        ]
        problemas, _ = _evaluar_problemas_anulacion_cm(cur, 1)
        self.assertIn("falta_marcador_cuentaproveedor_cm0", problemas)
        self.assertIn("falta_contra_asiento", problemas)
        self.assertNotIn("asiento_original_no_anulado", problemas)

    def test_op_egreso_sin_marcador_no_reporta_falta(self):
        cur = MagicMock()
        cur.fetchone.side_effect = [
            {"cnt": 0},
            {"pendientes": 0, "total": 2},
            {"codigo_movimiento": "1", "d": Decimal("100"), "h": Decimal("100")},
            {"codigo_movimiento": "2", "d": Decimal("100"), "h": Decimal("100")},
        ]
        problemas, _ = _evaluar_problemas_anulacion_cm(
            cur, 1, tipo_comprobante="OP", tipo_op="Egreso"
        )
        self.assertNotIn("falta_marcador_cuentaproveedor_cm0", problemas)
        self.assertEqual(problemas, [])

    def test_sin_renglones_no_marca_original(self):
        cur = MagicMock()
        cur.fetchone.side_effect = [
            {"TipoComprobante": "FA", "TipoOP": ""},
            {"cnt": 1},
            {"pendientes": 0, "total": 0},
            None,
            None,
        ]
        problemas, _ = _evaluar_problemas_anulacion_cm(cur, 1)
        self.assertNotIn("asiento_original_no_anulado", problemas)
        self.assertIn("falta_contra_asiento", problemas)

    def test_contra_no_invierte(self):
        cur = MagicMock()
        cur.fetchone.side_effect = [
            {"TipoComprobante": "FA", "TipoOP": ""},
            {"cnt": 1},
            {"pendientes": 0, "total": 2},
            {"codigo_movimiento": "1", "d": Decimal("100"), "h": Decimal("50")},
            {"codigo_movimiento": "2", "d": Decimal("10"), "h": Decimal("100")},
        ]
        problemas, _ = _evaluar_problemas_anulacion_cm(cur, 1)
        self.assertIn("contra_no_invierte_original", problemas)


class PlanReparacionAnulacionesTestCase(TestCase):
    def test_plan_marca_falta_marcador(self):
        repo = MagicMock()
        cur = MagicMock()
        repo.cur.return_value = cur
        repo.ejercicio_por_fecha.return_value = {"id_ejercicio": 1}
        repo.ejercicios_cerrados.return_value = set()

        cur.fetchall.side_effect = [
            [
                {
                    "CodigoMovimiento": Decimal("12345"),
                    "TipoComprobante": "FA",
                    "NroComprobante": "A-1",
                    "Fecha": date(2025, 1, 15),
                    "CodSucursal": 1,
                    "Codigo": 5,
                    "ImporteCompra": Decimal("100"),
                    "ImportePago": None,
                    "TipoOP": "",
                }
            ],
        ]
        # _evaluar: sin marcador, sin pendientes, con contra OK
        cur.fetchone.side_effect = [
            {"cnt": 0},
            {"pendientes": 0, "total": 2},
            {"codigo_movimiento": "12345", "d": Decimal("100"), "h": Decimal("100")},
            {"codigo_movimiento": "99", "d": Decimal("100"), "h": Decimal("100")},
        ]

        items = _plan_reparacion_anulaciones(
            MagicMock(),
            repo,
            _politica_base(),
            {"id_ejercicio": 1},
        )
        acciones = [i["accion"] for i in items]
        self.assertIn("insert_marcador", acciones)
        self.assertTrue(all(i["check_id"] == CHECK_ANULACION for i in items))

    def test_plan_marca_falta_contra(self):
        repo = MagicMock()
        cur = MagicMock()
        repo.cur.return_value = cur
        repo.ejercicio_por_fecha.return_value = {"id_ejercicio": 1}
        repo.nro_asiento_ejercicio.return_value = 50

        cur.fetchall.side_effect = [
            [
                {
                    "CodigoMovimiento": Decimal("55"),
                    "TipoComprobante": "OP",
                    "NroComprobante": "OP-1",
                    "Fecha": date(2025, 2, 1),
                    "CodSucursal": 1,
                    "Codigo": 1,
                    "ImporteCompra": None,
                    "ImportePago": Decimal("50"),
                    "TipoOP": "Imputacion",
                }
            ],
            [
                {
                    "id_pc": 10,
                    "id_ejercicio": 1,
                    "debe_asiento": Decimal("50"),
                    "haber_asiento": Decimal("0"),
                    "desc_renglon_asiento": "x",
                    "desc_concepto_asiento": "Pago",
                    "desc_asiento": "OP",
                    "fecha_asiento": date(2025, 2, 1),
                },
                {
                    "id_pc": 20,
                    "id_ejercicio": 1,
                    "debe_asiento": Decimal("0"),
                    "haber_asiento": Decimal("50"),
                    "desc_renglon_asiento": "y",
                    "desc_concepto_asiento": "Pago",
                    "desc_asiento": "OP",
                    "fecha_asiento": date(2025, 2, 1),
                },
            ],
        ]
        cur.fetchone.side_effect = [
            {"cnt": 1},
            {"pendientes": 0, "total": 2},
            {"codigo_movimiento": "55", "d": Decimal("50"), "h": Decimal("50")},
            None,
        ]

        items = _plan_reparacion_anulaciones(
            MagicMock(), repo, _politica_base(), {"id_ejercicio": 1}
        )
        contra = [i for i in items if i["accion"] == "insert_contra_asiento"]
        self.assertEqual(len(contra), 1)
        self.assertEqual(contra[0]["valor_nuevo"]["id_concepto_asiento"], 8)
        self.assertEqual(
            contra[0]["valor_nuevo"]["renglones_preview"][0]["desc_renglon_asiento"],
            MARCA_ANUL_REGEN,
        )

    @patch("legacy_db.services.cont_recalculo_service._reconstruir_renglones_comprobante_anulado")
    def test_plan_falta_contra_sin_asiento_reconstruye(self, mock_recon):
        repo = MagicMock()
        cur = MagicMock()
        repo.cur.return_value = cur
        repo.ejercicio_por_fecha.return_value = {"id_ejercicio": 1}
        repo.nro_asiento_ejercicio.return_value = 50

        cur.fetchall.side_effect = [
            [
                {
                    "CodigoMovimiento": Decimal("9001"),
                    "TipoComprobante": "FA",
                    "NroComprobante": "A-9001",
                    "Fecha": date(2025, 4, 1),
                    "CodSucursal": 1,
                    "Codigo": 5,
                    "ImporteCompra": Decimal("200"),
                    "ImportePago": None,
                    "TipoOP": "",
                }
            ],
            [],  # sin renglones cont_asiento
        ]
        cur.fetchone.side_effect = [
            {"cnt": 1},
            {"pendientes": 0, "total": 0},
            None,
            None,
            {
                "CodigoMovimiento": Decimal("9001"),
                "TipoComprobante": "FA",
                "Anulado": "Si",
                "ImporteCompra": Decimal("200"),
            },
        ]
        mock_recon.return_value = (
            [
                {"id_pc": 10, "debe_asiento": "200.00", "haber_asiento": "0.00"},
                {"id_pc": 20, "debe_asiento": "0.00", "haber_asiento": "200.00"},
            ],
            {
                "id_ejercicio": 1,
                "fecha_asiento": date(2025, 4, 1),
                "desc_asiento": "Compra - Nro Comp. A-9001",
                "concepto": 3,
                "desc_concepto": "Compra",
            },
        )

        items = _plan_reparacion_anulaciones(
            MagicMock(), repo, _politica_base(), {"id_ejercicio": 1}
        )
        contra = [i for i in items if i["accion"] == "insert_contra_asiento"]
        self.assertEqual(len(contra), 1)
        vn = contra[0]["valor_nuevo"]
        self.assertTrue(vn.get("regenerar_original"))
        self.assertEqual(len(vn.get("renglones_original_preview") or []), 2)
        self.assertEqual(len(vn.get("renglones_preview") or []), 2)
        self.assertEqual(
            vn["renglones_preview"][0]["debe_asiento"],
            vn["renglones_original_preview"][0]["haber_asiento"],
        )
        self.assertTrue(contra[0]["detalle"].get("reconstruido_desde_comprobante"))
        mock_recon.assert_called_once()

    def test_contra_no_invierte_queda_bloqueado(self):
        repo = MagicMock()
        cur = MagicMock()
        repo.cur.return_value = cur
        repo.ejercicio_por_fecha.return_value = {"id_ejercicio": 1}

        cur.fetchall.return_value = [
            {
                "CodigoMovimiento": Decimal("77"),
                "TipoComprobante": "FA",
                "NroComprobante": "X",
                "Fecha": date(2025, 3, 1),
                "CodSucursal": 1,
                "Codigo": 1,
                "ImporteCompra": Decimal("10"),
                "ImportePago": None,
                "TipoOP": "",
            }
        ]
        cur.fetchone.side_effect = [
            {"cnt": 1},
            {"pendientes": 0, "total": 2},
            {"codigo_movimiento": "77", "d": Decimal("100"), "h": Decimal("100")},
            {"codigo_movimiento": "88", "d": Decimal("1"), "h": Decimal("2")},
        ]

        items = _plan_reparacion_anulaciones(
            MagicMock(), repo, _politica_base(), {"id_ejercicio": 1}
        )
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["bloqueado"])
        self.assertTrue(items[0]["excluido"])
        self.assertEqual(items[0]["motivo_bloqueo"], "contra_no_invierte_original")
        self.assertEqual(_filtrar_items_aplicables(items), [])


class ApplyAnulacionTestCase(TestCase):
    def test_aplicar_insert_marcador(self):
        cur = MagicMock()
        dict_cur = MagicMock()
        dict_cur.fetchone.side_effect = [
            None,  # no existe marcador
            {
                "Fecha": date(2025, 1, 15),
                "FechaRegistro": date(2025, 1, 15),
                "TipoComprobante": "FA",
                "NroComprobante": "1",
                "NroCompBusq": 1,
                "Codigo": 5,
                "CodSucursal": 1,
                "IdUsuario": 1,
                "ImporteCompra": Decimal("100"),
                "ImportePago": None,
            },
            {"nid": 999},  # max id + 1
        ]
        repo = MagicMock()
        n = _aplicar_item_anulacion(
            cur, dict_cur, repo, _item_marcador(), {}, "L1", "tester", date(2025, 7, 25)
        )
        self.assertEqual(n, 1)
        sqls = [c[0][0].strip().upper() for c in cur.execute.call_args_list]
        self.assertTrue(any(s.startswith("INSERT INTO CUENTAPROVEEDOR") for s in sqls))

    def test_aplicar_marcar_original(self):
        cur = MagicMock()
        cur.rowcount = 2
        dict_cur = MagicMock()
        dict_cur.fetchone.return_value = {"cnt": 2}
        repo = MagicMock()
        n = _aplicar_item_anulacion(
            cur, dict_cur, repo, _item_marcar_original(), {}, "L1", "tester", date(2025, 7, 25)
        )
        self.assertEqual(n, 2)
        sqls = [c[0][0] for c in cur.execute.call_args_list]
        self.assertTrue(any("anulado" in s.lower() and "update" in s.lower() for s in sqls))

    def test_aplicar_insert_contra(self):
        cur = MagicMock()
        dict_cur = MagicMock()
        # existe? no; then codmov reserve; nro reserve; saldo reads
        cur.fetchone.side_effect = [
            (1000,),  # codmov
            (50,),  # nro_asiento
            (Decimal("0"),),  # saldo pc 10
            (Decimal("0"),),  # saldo pc 20
        ]
        dict_cur.fetchone.return_value = None
        repo = MagicMock()
        repo.saldo_pc.return_value = "Deudor"
        n = _aplicar_item_anulacion(
            cur,
            dict_cur,
            repo,
            _item_contra(),
            {},
            "L1",
            "tester",
            date(2025, 7, 25),
        )
        self.assertGreaterEqual(n, 1)
        inserts = [
            c[0][0]
            for c in cur.execute.call_args_list
            if "INSERT INTO cont_asiento" in c[0][0]
        ]
        self.assertGreaterEqual(len(inserts), 2)
        # marca en parámetros
        params_flat = []
        for c in cur.execute.call_args_list:
            if c[0] and "INSERT INTO cont_asiento" in c[0][0]:
                params_flat.extend(list(c[0][1]))
        self.assertTrue(any(MARCA_ANUL_REGEN in str(p) for p in params_flat))

    def test_aplicar_insert_contra_regenera_original(self):
        cur = MagicMock()
        dict_cur = MagicMock()
        dict_cur.fetchone.side_effect = [
            None,  # contra no existe
            None,  # asiento original no existe
        ]
        cur.fetchone.side_effect = [
            (50,),  # nro_asiento original
            (Decimal("0"),),
            (Decimal("0"),),
            (1000,),  # codmov contra
            (51,),  # nro_asiento contra
            (Decimal("0"),),
            (Decimal("0"),),
        ]
        repo = MagicMock()
        repo.saldo_pc.return_value = "Deudor"
        n = _aplicar_item_anulacion(
            cur,
            dict_cur,
            repo,
            _item_contra_regenerar(),
            {},
            "L1",
            "tester",
            date(2025, 7, 25),
        )
        self.assertGreaterEqual(n, 4)
        inserts = [
            c[0][0]
            for c in cur.execute.call_args_list
            if "INSERT INTO cont_asiento" in c[0][0]
        ]
        self.assertEqual(len(inserts), 4)
        params_por_insert = [
            list(c[0][1])
            for c in cur.execute.call_args_list
            if c[0] and "INSERT INTO cont_asiento" in c[0][0]
        ]
        anulados = [p[-1] for p in params_por_insert]
        self.assertEqual(anulados[:2], ["Si", "Si"])
        self.assertEqual(anulados[2:], ["No", "No"])
        marcas = [p[9] for p in params_por_insert]
        self.assertEqual(marcas[:2], [MARCA_REGEN, MARCA_REGEN])
        self.assertTrue(all(MARCA_ANUL_REGEN in m for m in marcas[2:]))

    def test_aplicar_bloqueado_no_hace_nada(self):
        cur = MagicMock()
        n = _aplicar_item_anulacion(
            cur, MagicMock(), MagicMock(), _item_bloqueado(), {}, "L1", "t", date(2025, 1, 1)
        )
        self.assertEqual(n, 0)
        cur.execute.assert_not_called()

    def test_filtrar_excluye_bloqueados(self):
        items = [_item_bloqueado(), _item_marcador("111")]
        aplicables = _filtrar_items_aplicables(items)
        self.assertEqual(len(aplicables), 1)
        self.assertEqual(aplicables[0]["accion"], "insert_marcador")

    @override_settings(ENVIRONMENT="development")
    def test_apply_rechaza_sin_permiso(self):
        plan = _crear_plan([_item_marcador()])
        with self.assertRaises(CorreccionContableError) as ctx:
            apply(plan.base_empresa, str(plan.dry_run_id), "tester", tiene_permiso_corregir=False)
        self.assertIn("permiso", str(ctx.exception).lower())
