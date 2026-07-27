"""Tests del servicio de eliminación de asientos contables."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from legacy_db.services.cont_eliminacion_asientos_service import (
    CHECK_ID_ELIMINACION,
    EliminacionAsientosError,
    eliminar_asientos,
    listar_asientos,
    preview_eliminacion,
)


class ListarAsientosTestCase(SimpleTestCase):
    def test_listar_exige_id_ejercicio(self):
        with self.assertRaises(EliminacionAsientosError):
            listar_asientos("empresa_test", {})

    @patch("legacy_db.services.cont_eliminacion_asientos_service.get_mysql_pool")
    def test_listar_mock_cursor_agrupado(self, mock_pool):
        conn = MagicMock()
        mock_pool.return_value.get_connection.return_value.__enter__.return_value = conn
        cur = MagicMock()
        conn.cursor.return_value = cur

        cur.fetchone.return_value = {"total": 1}
        cur.fetchall.return_value = [
            {
                "id_ejercicio": 1,
                "nro_asiento": 79,
                "fecha_asiento": "2024-03-15",
                "id_concepto_asiento": 3,
                "desc_concepto_asiento": "Compra",
                "codigo_movimiento": "1001",
                "desc_asiento": "Factura test",
                "cant_lineas": 2,
                "total_debe": "100.00",
                "total_haber": "100.00",
                "anulado": "No",
                "tipo_comprobante": "FA",
                "origen": "proveedor",
            }
        ]

        resultado = listar_asientos("empresa_test", {"id_ejercicio": 1, "page": 1})
        self.assertEqual(resultado["total"], 1)
        self.assertEqual(resultado["page_size"], 500)
        self.assertEqual(len(resultado["items"]), 1)
        self.assertEqual(resultado["items"][0]["nro_asiento"], 79)
        self.assertEqual(resultado["items"][0]["fecha_asiento"], "15/03/2024")
        sql_ejecutados = " ".join(str(c) for c in cur.execute.call_args_list)
        self.assertIn("GROUP BY", sql_ejecutados)
        self.assertIn("LIMIT", sql_ejecutados.upper())


class PreviewEliminacionTestCase(SimpleTestCase):
    @patch("legacy_db.services.cont_eliminacion_asientos_service.get_mysql_pool")
    def test_preview_cuenta_renglones(self, mock_pool):
        conn = MagicMock()
        mock_pool.return_value.get_connection.return_value.__enter__.return_value = conn
        dict_cur = MagicMock()
        conn.cursor.return_value = dict_cur

        dict_cur.fetchone.return_value = {
            "total_renglones": 2,
            "cuentas_impactadas": 2,
            "periodos_impactados": 2,
            "asientos_con_renglones_anulados": 0,
        }
        dict_cur.fetchall.return_value = [
            {
                "id_ejercicio": 1,
                "nro_asiento": 79,
            },
        ]

        payload = preview_eliminacion(
            "empresa_test",
            [{"id_ejercicio": 1, "nro_asiento": 79}],
        )
        self.assertEqual(payload["asientos_solicitados"], 1)
        self.assertEqual(payload["total_renglones"], 2)
        self.assertEqual(payload["cuentas_impactadas"], 2)


class EliminarAsientosTestCase(SimpleTestCase):
    def test_eliminar_sin_permiso_lanza(self):
        with self.assertRaises(EliminacionAsientosError) as ctx:
            eliminar_asientos(
                "empresa_test",
                [{"id_ejercicio": 1, "nro_asiento": 79}],
                "auditor",
                tiene_permiso_corregir=False,
            )
        self.assertIn("permiso", str(ctx.exception).lower())

    @patch("legacy_db.services.cont_eliminacion_asientos_service._insertar_log_detalle")
    @patch("legacy_db.services.cont_eliminacion_asientos_service.get_mysql_pool")
    def test_eliminar_mock_delete_update_log(self, mock_pool, mock_log):
        conn_tx = MagicMock()
        mock_pool.return_value.get_connection.return_value.__enter__.return_value = conn_tx

        dict_cur = MagicMock()
        cur = MagicMock()
        conn_tx.cursor.side_effect = [cur, dict_cur]

        dict_cur.fetchall.return_value = [
            {
                "id_ejercicio": 1,
                "nro_asiento": 79,
                "id_pc": 10,
                "id_periodo": 5,
                "fecha_asiento": "2024-03-15",
                "codigo_movimiento": "1001",
                "debe_asiento": "100.00",
                "haber_asiento": "0.00",
                "anulado": "No",
                "id_concepto_asiento": 3,
                "desc_concepto_asiento": "Compra",
                "desc_asiento": "Test",
                "desc_renglon_asiento": "R1",
                "saldo_asiento": "0",
            }
        ]
        dict_cur.fetchone.side_effect = [
            {"saldo_teorico": "0.00"},
            {"saldo_teorico": "0.00"},
        ]
        cur.fetchone.side_effect = [None, (1,)]
        cur.rowcount = 1

        resultado = eliminar_asientos(
            "empresa_test",
            [{"id_ejercicio": 1, "nro_asiento": 79}],
            "auditor",
            tiene_permiso_corregir=True,
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["asientos_eliminados"], 1)
        self.assertEqual(resultado["backups"], {})
        self.assertNotIn("backup_efimero", resultado)
        self.assertIn("lote_id", resultado)

        sql_ejecutados = [str(c[0][0]) for c in cur.execute.call_args_list]
        self.assertTrue(any("DELETE FROM cont_asiento" in s for s in sql_ejecutados))
        self.assertTrue(
            any(
                "INSERT INTO cont_ejercicio_saldo_cta" in s or "UPDATE cont_ejercicio_saldo_cta" in s
                for s in sql_ejecutados
            )
        )
        self.assertTrue(any("cont_audit_correccion_lote" in s for s in sql_ejecutados))
        insert_lote = next(c for c in cur.execute.call_args_list if "cont_audit_correccion_lote" in str(c[0][0]))
        self.assertEqual(insert_lote[0][1][-1], "{}")
        mock_log.assert_called()
        args_log = mock_log.call_args[0]
        item_log = args_log[2]
        self.assertEqual(item_log["check_id"], CHECK_ID_ELIMINACION)
        # Una sola conexión de trabajo (sin fase backup).
        self.assertEqual(mock_pool.return_value.get_connection.call_count, 1)

    @patch("legacy_db.services.cont_eliminacion_asientos_service._insertar_log_detalle")
    @patch("legacy_db.services.cont_eliminacion_asientos_service.get_mysql_pool")
    def test_eliminar_fallo_hace_rollback(self, mock_pool, mock_log):
        conn_tx = MagicMock()
        mock_pool.return_value.get_connection.return_value.__enter__.return_value = conn_tx

        dict_cur = MagicMock()
        cur = MagicMock()
        conn_tx.cursor.side_effect = [cur, dict_cur]
        dict_cur.fetchall.side_effect = EliminacionAsientosError("Asiento inexistente")

        with self.assertRaises(EliminacionAsientosError):
            eliminar_asientos(
                "empresa_test",
                [{"id_ejercicio": 1, "nro_asiento": 79}],
                "auditor",
                tiene_permiso_corregir=True,
            )

        conn_tx.rollback.assert_called()
        mock_log.assert_not_called()

    @patch("legacy_db.services.cont_eliminacion_asientos_service._insertar_log_detalle")
    @patch("legacy_db.services.cont_eliminacion_asientos_service.get_mysql_pool")
    def test_eliminar_emite_callbacks_progreso(self, mock_pool, mock_log):
        conn_tx = MagicMock()
        mock_pool.return_value.get_connection.return_value.__enter__.return_value = conn_tx

        dict_cur = MagicMock()
        cur = MagicMock()
        conn_tx.cursor.side_effect = [cur, dict_cur]

        dict_cur.fetchall.return_value = [
            {
                "id_ejercicio": 1,
                "nro_asiento": 79,
                "id_pc": 10,
                "id_periodo": 5,
                "fecha_asiento": "2024-03-15",
                "codigo_movimiento": "1001",
                "debe_asiento": "100.00",
                "haber_asiento": "0.00",
                "anulado": "No",
                "id_concepto_asiento": 3,
                "desc_concepto_asiento": "Compra",
                "desc_asiento": "Test",
                "desc_renglon_asiento": "R1",
                "saldo_asiento": "0",
            }
        ]
        dict_cur.fetchone.side_effect = [{"saldo_teorico": "0.00"}, {"saldo_teorico": "0.00"}]
        cur.fetchone.side_effect = [None, (1,)]
        cur.rowcount = 1

        eventos: list[dict] = []

        eliminar_asientos(
            "empresa_test",
            [{"id_ejercicio": 1, "nro_asiento": 79}],
            "auditor",
            tiene_permiso_corregir=True,
            on_progress=eventos.append,
        )

        fases = [e.get("phase") for e in eventos if e.get("type") == "progress"]
        self.assertNotIn("backup", fases)
        self.assertIn("prepare", fases)
        self.assertIn("delete", fases)
        self.assertIn("recalc", fases)
        self.assertEqual(fases[0], "prepare")
        recalc_evts = [e for e in eventos if e.get("type") == "progress" and e.get("phase") == "recalc"]
        self.assertGreaterEqual(len(recalc_evts), 1)
        self.assertEqual(recalc_evts[0]["current"], 0)
        self.assertGreaterEqual(recalc_evts[-1]["current"], 1)
        self.assertEqual(recalc_evts[-1]["total"], recalc_evts[0]["total"])
        sql_ejecutados = [str(c[0][0]) for c in cur.execute.call_args_list]
        self.assertTrue(any("DELETE FROM cont_asiento" in s and "IN (" in s for s in sql_ejecutados))
