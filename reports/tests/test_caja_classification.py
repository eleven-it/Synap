"""Tests clasificación caja compartida."""
from django.test import SimpleTestCase

from reports.services.executive_dashboard.caja_classification import (
    classify_movement,
    get_payment_method,
    is_movimiento_interno,
    medio_cobro_bucket,
)


class CajaClassificationTests(SimpleTestCase):
    def test_rec_es_cobranza(self):
        flujo, sub = classify_movement("REC", "Cobranza Efectivo", 100, 0)
        self.assertEqual(sub, "ingresos_cobranzas")

    def test_fa_es_venta(self):
        flujo, sub = classify_movement("FA", "Factura Contado TPV", 500, 0)
        self.assertEqual(sub, "ingresos_ventas")

    def test_op_proveedor(self):
        flujo, sub = classify_movement("OP", "Pago Efectivo", 0, 200, tipo_cp="Proveedor")
        self.assertEqual(sub, "egresos_proveedores")

    def test_cheq_cliente_es_cobranza(self):
        flujo, sub = classify_movement("CHEQ", "Cheque", 1000, 0, tipo_cp="Cliente")
        self.assertEqual(sub, "ingresos_cobranzas")

    def test_cheq_entrega_proveedor(self):
        flujo, sub = classify_movement("CHEQ", "Entrega Proveedor", 0, 500, tipo_cp="Proveedor")
        self.assertEqual(sub, "egresos_proveedores")

    def test_retiro_caja_mcaj(self):
        flujo, sub = classify_movement("MCAJ", "Retiro de Caja", 0, 100, tipo_cp="Mov Caja")
        self.assertEqual(sub, "egresos_otros")

    def test_movimiento_no_operativo(self):
        from reports.services.executive_dashboard.caja_classification import (
            is_movimiento_no_operativo,
        )

        self.assertTrue(is_movimiento_no_operativo("Transferencia de Fondos"))
        self.assertTrue(is_movimiento_no_operativo("Inversión en activo"))
        self.assertFalse(is_movimiento_no_operativo("Pago Efectivo"))

    def test_movimiento_interno(self):
        self.assertTrue(is_movimiento_interno("Cierre de Caja - Usuario de PV"))
        self.assertTrue(is_movimiento_interno("Transferencia de Fondos"))
        self.assertFalse(is_movimiento_interno("Cobranza Efectivo"))

    def test_medio_cobro_bucket(self):
        self.assertEqual(medio_cobro_bucket("Efectivo"), "efectivo")
        self.assertEqual(medio_cobro_bucket("Tarjeta"), "tarjeta")
        self.assertEqual(medio_cobro_bucket("Transferencia"), "transferencia")

    def test_get_payment_method_rec_efectivo(self):
        self.assertEqual(get_payment_method("REC", "Cobranza Efectivo"), "Efectivo")
