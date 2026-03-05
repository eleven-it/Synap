"""
Tests para legacy_db: validators, mappers, constantes y repositorios (sin BD cuando aplique).
"""
from datetime import date, timedelta

from django.test import TestCase

from legacy_db.validators import (
    PrecheckError,
    validar_cai_vigente,
    validar_obliga_oc_para_factura,
    tipo_factura_segun_idiva,
)
from legacy_db.mappers import proveedor_row_to_dto, sucursal_row_to_dto, dto_to_fact_temporalp_row
from legacy_db.repositories import PROVEEDOR_ORDER_COLUMNS


class PrecheckErrorTest(TestCase):
    """Códigos de error expuestos en API."""

    def test_codigos_definidos(self):
        self.assertEqual(PrecheckError.CAI_VENCIDO, "CAI_VENCIDO")
        self.assertEqual(PrecheckError.REQUIERE_OC, "REQUIERE_OC")
        self.assertEqual(PrecheckError.OP_BLOQUEADA, "OP_BLOQUEADA")
        self.assertEqual(PrecheckError.SIN_PROVEEDOR, "SIN_PROVEEDOR")


class ValidarCaiVigenteTest(TestCase):
    """Paridad VB6: FechaCAI >= fecha actual."""

    def test_none_ok(self):
        ok, err = validar_cai_vigente(None)
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_fecha_futura_ok(self):
        maniana = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        ok, err = validar_cai_vigente(maniana)
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_fecha_pasada_falla(self):
        ayer = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        ok, err = validar_cai_vigente(ayer)
        self.assertFalse(ok)
        self.assertEqual(err, PrecheckError.CAI_VENCIDO)

    def test_fecha_hoy_ok(self):
        hoy = date.today().strftime("%Y-%m-%d")
        ok, err = validar_cai_vigente(hoy)
        self.assertTrue(ok)
        self.assertIsNone(err)


class ValidarObligaOcTest(TestCase):
    """Paridad VB6: obliga_oc_carga_comp = 'Si' -> no puede factura sin OC."""

    def test_si_falla(self):
        ok, err = validar_obliga_oc_para_factura("Si")
        self.assertFalse(ok)
        self.assertEqual(err, PrecheckError.REQUIERE_OC)

    def test_no_ok(self):
        ok, err = validar_obliga_oc_para_factura("No")
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_none_o_vacio_ok(self):
        ok, _ = validar_obliga_oc_para_factura(None)
        self.assertTrue(ok)
        ok, _ = validar_obliga_oc_para_factura("")
        self.assertTrue(ok)


class TipoFacturaSegunIvaTest(TestCase):
    """FA/FB/FC según idIVA (paridad VB6)."""

    def test_ri_ricbu_fa(self):
        self.assertEqual(tipo_factura_segun_idiva(1), "FA")
        self.assertEqual(tipo_factura_segun_idiva(7), "FA")

    def test_rim_fb(self):
        self.assertEqual(tipo_factura_segun_idiva(6), "FB")

    def test_mon_ex_cf_fc(self):
        self.assertEqual(tipo_factura_segun_idiva(2), "FC")
        self.assertEqual(tipo_factura_segun_idiva(3), "FC")
        self.assertEqual(tipo_factura_segun_idiva(4), "FC")

    def test_none_fc(self):
        self.assertEqual(tipo_factura_segun_idiva(None), "FC")


class MappersTest(TestCase):
    """DTO <-> filas legacy con administranet_types."""

    def test_proveedor_row_to_dto(self):
        row = {
            "Codigo": 10,
            "Nombre": "Proveedor SA",
            "CUIT": "30-12345678-9",
            "idIVA": 1,
            "IVA": "RI",
            "FechaCAI": "2025-12-31",
            "obliga_oc_carga_comp": "No",
            "saldo": "1500.50",
        }
        dto = proveedor_row_to_dto(row)
        self.assertEqual(dto["Codigo"], 10)
        self.assertEqual(dto["Nombre"], "Proveedor SA")
        self.assertEqual(dto["idIVA"], 1)
        self.assertEqual(dto["obliga_oc_carga_comp"], "No")

    def test_sucursal_row_to_dto(self):
        row = {"id_sucursal": 1, "nombre_sucursal": "Casa central"}
        dto = sucursal_row_to_dto(row)
        self.assertEqual(dto["id_sucursal"], 1)
        self.assertEqual(dto["nombre_sucursal"], "Casa central")

    def test_dto_to_fact_temporalp_row(self):
        row = dto_to_fact_temporalp_row(100, 5, "No")
        self.assertEqual(row["Codigo"], 100)
        self.assertEqual(row["Codusuario"], 5)
        self.assertEqual(row["visualiza"], "No")


class RepositoriesWhitelistTest(TestCase):
    """Whitelist de ordenación para evitar inyección."""

    def test_order_columns_defined(self):
        self.assertIn("Nombre", PROVEEDOR_ORDER_COLUMNS)
        self.assertIn("Codigo", PROVEEDOR_ORDER_COLUMNS)
        self.assertIn("CUIT", PROVEEDOR_ORDER_COLUMNS)
        self.assertIn("saldo", PROVEEDOR_ORDER_COLUMNS)
