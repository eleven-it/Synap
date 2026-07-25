# -*- coding: utf-8 -*-
"""Hub Kanban: columna Finanzas y CTAs gateadas (REQ-HUB-02/11)."""

import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from ecom.services.pedidos_hub_pipeline import (
    _columna_ped_mysql,
    _pedidos_mysql,
    columnas_hub_visibles,
)


class TestColumnaCreditoFinanzas(unittest.TestCase):
    def test_pendiente_finanzas_columna_dedicada(self):
        col = _columna_ped_mysql(
            "No",
            "No Autorizado",
            "Pendiente",
            estado_aprobacion_comercial="-",
            aprobacion_activa=True,
            credito_activo=True,
            estado_credito_finanzas="pendiente",
        )
        self.assertEqual(col, "credito_finanzas")

    def test_credito_on_no_mezcla_por_autorizar(self):
        col = _columna_ped_mysql(
            "No",
            "No Autorizado",
            "Pendiente",
            estado_aprobacion_comercial="-",
            aprobacion_activa=True,
            credito_activo=True,
            estado_credito_finanzas="pendiente",
        )
        self.assertNotEqual(col, "por_autorizar")

    def test_ambos_pendientes_prioriza_columna_finanzas(self):
        col = _columna_ped_mysql(
            "No",
            "No Autorizado",
            "Pendiente",
            estado_aprobacion_comercial="pendiente",
            aprobacion_activa=True,
            credito_activo=True,
            estado_credito_finanzas="pendiente",
        )
        self.assertEqual(col, "credito_finanzas")

    def test_comercial_pendiente_sin_credito_va_por_autorizar(self):
        col = _columna_ped_mysql(
            "No",
            "Autorizado",
            "Pendiente",
            estado_aprobacion_comercial="pendiente",
            aprobacion_activa=True,
            credito_activo=True,
            estado_credito_finanzas="-",
        )
        self.assertEqual(col, "por_autorizar")

    def test_flag_credito_off_sin_columna_finanzas(self):
        cols = columnas_hub_visibles(aprobacion_activa=True, credito_activo=False)
        self.assertNotIn("credito_finanzas", cols)

    def test_flag_credito_on_incluye_columna_finanzas(self):
        cols = columnas_hub_visibles(aprobacion_activa=True, credito_activo=True)
        self.assertIn("credito_finanzas", cols)

    def test_meta_finanzas_habilita_cta_segun_permiso(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "CodigoMovimiento": 9001,
                "NroComprobante": "0001-00009001",
                "fecha": "25/07/2026",
                "Estado": "Pendiente",
                "Anulado": "No",
                "autorizacion": "No Autorizado",
                "estado_aprobacion_comercial": "pendiente",
                "estado_credito_finanzas": "pendiente",
                "CodViajante": 1,
                "id_cliente": 10,
                "nombre_cliente": "Cliente crédito",
                "ImporteVenta": 100,
                "total_calc": 100,
                "id_cliente_domicilio": None,
                "calle_domicilio": "",
                "nro_domicilio": "",
            }
        ]

        @contextmanager
        def fake_mysql_cursor(*_args, **_kwargs):
            yield cursor

        with patch(
            "ecom.services.pedidos_hub_pipeline.mysql_cursor",
            side_effect=fake_mysql_cursor,
        ), patch(
            "ecom.services.pedidos_hub_pipeline._nombres_viajantes",
            return_value={},
        ), patch(
            "ecom.services.credito_pedidos.aprobacion.credito_pedidos_activo",
            return_value=True,
        ):
            con_permiso = _pedidos_mysql(
                "empresa_test",
                {
                    "todos_clientes": "Si",
                    "synap_permisos": ["finance.credito.aprobar"],
                },
                aprobacion_on=True,
                credito_on=True,
            )
            sin_permiso = _pedidos_mysql(
                "empresa_test",
                {"todos_clientes": "Si", "synap_permisos": []},
                aprobacion_on=True,
                credito_on=True,
            )

        self.assertEqual(con_permiso[0]["columna"], "credito_finanzas")
        self.assertTrue(con_permiso[0]["meta"]["puede_aprobar_credito"])
        self.assertTrue(con_permiso[0]["meta"]["pendiente_comercial"])
        self.assertTrue(con_permiso[0]["meta"]["pendiente_credito_finanzas"])
        self.assertFalse(sin_permiso[0]["meta"]["puede_aprobar_credito"])
