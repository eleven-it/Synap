"""
Tests del checkout mayorista (Fase P2).

La escritura legacy MySQL se simula con un cursor/conn falsos (FakeConn/FakeCursor):
no se toca ninguna base real. El carrito vive en Postgres (test DB Django).
"""

from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from ecom.models import EcomCart, EcomCartItem
from ecom.services import mayorista_checkout_service as checkout_svc
from ecom.services.mayorista_checkout_service import CheckoutInput
from ecom.services.pedido_cabecera_comercial import PedidoCabeceraComercial


class FakeCursor:
    def __init__(self, state):
        self.state = state
        self.executed = []
        self._last = None
        self._last_all = []
        self.rowcount = 1

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        low = " ".join(sql.split()).lower()
        if "from cuentacliente" in low:
            self._last = {"ultimaf": self.state.get("ultimaf")}
        elif "from codmov" in low:
            self._last = {"CodigoMovimiento": self.state.get("codmov", 1000)}
        elif "from talonarios" in low:
            self._last = self.state.get("talonario", {"Nro": 57, "PV": 3})
        elif "from usuarios" in low:
            self._last = {"agente_percep": self.state.get("agente_percep", "No")}
        elif "from cotizacion" in low:
            self._last = self.state.get(
                "cotizacion",
                {"ValorPesos": Decimal("1200"), "id_cotizacion": 1},
            )
        elif "from stock_deposito" in low and "saldo_pedido_cliente" in low:
            self._last = {
                "saldo": self.state.get("saldo_pedido_cliente", Decimal("2")),
            }
        elif "from percep_cli_param" in low:
            self._last_all = list(self.state.get("percep_param", []))
        elif "from percep_cli_tipo" in low:
            id_tipo = params[0] if params else None
            self._last = (self.state.get("percep_tipos", {}) or {}).get(int(id_tipo)) if id_tipo is not None else None
        elif "insert into percep_cli" in low:
            self.state["percep_count"] = self.state.get("percep_count", 0) + 1
            self.state.setdefault("percep_rows", []).append(params)
        elif low.startswith("update stock_deposito"):
            self.rowcount = self.state.get("stock_rowcount", 1)
        elif "insert into stockp" in low:
            if self.state.get("raise_on_stockp"):
                raise RuntimeError("fallo simulado en stockp")
            self.state["stockp_count"] = self.state.get("stockp_count", 0) + 1
            self.state.setdefault("stockp_params", []).append(params)
        elif "insert into comp_ped" in low:
            self.state["comp_ped_count"] = self.state.get("comp_ped_count", 0) + 1
            self.state["comp_ped_params"] = params
        elif "update comp_ped" in low and "estado_aprobacion_comercial" in low:
            self.state["aprobacion_update"] = params
        elif "insert into ecom_aprobacion_evento" in low:
            self.state["aprobacion_evento_count"] = self.state.get("aprobacion_evento_count", 0) + 1
            self.state["aprobacion_evento_params"] = params
        elif "from comp_ped" in low and "codigo =" in low:
            self._last = None
        else:
            self.rowcount = 1

    def fetchone(self):
        return self._last

    def fetchall(self):
        return self._last_all

    def close(self):
        pass


class FakeConn:
    def __init__(self, state):
        self.state = state
        self.committed = False
        self.rolled_back = False
        self.cur = None

    def autocommit(self, _v):
        pass

    def cursor(self, *args, **kwargs):
        self.cur = FakeCursor(self.state)
        return self.cur

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def _make_get_connection(conn):
    @contextmanager
    def _cm(_base):
        yield conn
    return _cm


class CheckoutTestBase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._credito_flag_patcher = patch.object(
            checkout_svc, "credito_pedidos_activo", return_value=False
        )
        cls._aprobacion_flag_patcher = patch.object(
            checkout_svc, "aprobacion_pedidos_activa", return_value=False
        )
        cls._mail_confirm_patcher = patch(
            "ecom.services.ecom_config_mysql.pedidos_envian_mail_confirmacion",
            return_value=False,
        )
        cls._credito_flag_patcher.start()
        cls._aprobacion_flag_patcher.start()
        cls._mail_confirm_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls._mail_confirm_patcher.stop()
        cls._aprobacion_flag_patcher.stop()
        cls._credito_flag_patcher.stop()
        super().tearDownClass()

    def _cart(self, tipo="PED", items=((1, "2", "100", "21"),)):
        cart = EcomCart.objects.create(
            base_empresa="emp1", id_usuario=5, idcliente=10, lista_id=2,
            id_deposito=1, iva_incluido=True, tipo_comprobante=tipo,
        )
        for idx, (idart, cant, precio, alic) in enumerate(items, start=1):
            EcomCartItem.objects.create(
                cart=cart, id_articulo=idart, codigo=f"C{idart}", descripcion=f"Art {idart}",
                cantidad=Decimal(cant), precio_unitario_neto=Decimal(precio),
                alicuota_iva=Decimal(alic), orden=idx,
            )
        return cart

    def _cli(self, credito_limite_dias=0):
        return {
            "Codigo": 10, "id_sucursal": 1, "id_cv": 3, "condVenta": "CTA CTE",
            "credito_limite_dias": credito_limite_dias, "descRenglon": 0,
        }

    def _cabecera(self, lista_id=2):
        fp = date(2026, 7, 5)
        return PedidoCabeceraComercial(
            fecha_pedido=fp,
            fecha_entrega=fp + timedelta(days=2),
            vencimiento=fp + timedelta(days=15),
            id_condventa=3,
            cond_venta="CTA CTE",
            lista_id=lista_id,
        )

    def _articulo_extras(self):
        return {
            1: {
                "IDArt": 1,
                "PrecioCosto": 50,
                "CodLaboratorio": 2,
                "tipo_art": "N",
                "Alicuota": 1,
                "AlicuotaIB": 2,
                "iibb_pct": Decimal("3.50"),
            },
            2: {
                "IDArt": 2,
                "PrecioCosto": 30,
                "CodLaboratorio": 2,
                "tipo_art": "N",
                "Alicuota": 1,
                "AlicuotaIB": 2,
                "iibb_pct": Decimal("3.50"),
            },
        }

    def _patch_all(self, conn, cli=None, alic="21", cabecera=None):
        row = {"alic_iva": alic, "impuesto_interno": "0"}
        cab = cabecera or self._cabecera()
        return [
            patch.object(checkout_svc, "get_connection", _make_get_connection(conn)),
            patch.object(checkout_svc, "_fetch_cliente", return_value=cli or self._cli()),
            patch.object(
                checkout_svc, "_fetch_articulo_extras",
                return_value=self._articulo_extras(),
            ),
            patch.object(checkout_svc, "resolver_precio_articulo",
                         side_effect=lambda base, idart, **kw: (Decimal("100"), row)),
            patch.object(
                checkout_svc,
                "resolver_cabecera_comercial",
                return_value=(cab, None),
            ),
            patch.object(checkout_svc, "pedidos_validan_stock", return_value=True),
        ]

    @contextmanager
    def _with_patches(self, conn, **kwargs):
        patches = self._patch_all(conn, **kwargs)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            yield


class TestCheckoutPedido(CheckoutTestBase):
    def test_alta_pedido_ok(self):
        state = {"codmov": 1000, "talonario": {"Nro": 57, "PV": 3}}
        conn = FakeConn(state)
        cart = self._cart(tipo="PED")
        with self._with_patches(conn):
            ok, err, result = checkout_svc.confirmar(cart, CheckoutInput(tipo="PED", id_punto_venta=3), id_usuario=5)
        self.assertTrue(ok, err)
        self.assertIsNone(err)
        self.assertEqual(result["codigo_movimiento"], 1001)
        self.assertEqual(result["nro_comprobante"], "0003-00000057")
        self.assertTrue(conn.committed)
        self.assertEqual(state.get("comp_ped_count"), 1)
        self.assertEqual(state.get("stockp_count"), 1)
        cart.refresh_from_db()
        self.assertEqual(cart.estado, EcomCart.ESTADO_CONFIRMADO)
        self.assertEqual(cart.codigo_movimiento, 1001)
        # total: neto 200 + iva 42 = 242
        self.assertEqual(cart.total, Decimal("242.00"))

    def test_persiste_cabecera_en_comp_ped(self):
        state = {"codmov": 1000, "talonario": {"Nro": 57, "PV": 3}}
        conn = FakeConn(state)
        cart = self._cart(tipo="PED")
        cab = self._cabecera(lista_id=4)
        with self._with_patches(conn, cabecera=cab):
            ok, err, _ = checkout_svc.confirmar(
                cart,
                CheckoutInput(
                    tipo="PED",
                    id_punto_venta=3,
                    fecha_pedido=cab.fecha_pedido,
                    lista_id=4,
                ),
                id_usuario=5,
            )
        self.assertTrue(ok, err)
        params = state.get("comp_ped_params") or {}
        self.assertEqual(params.get("Fecha"), cab.fecha_pedido)
        self.assertEqual(params.get("Vencimiento"), cab.vencimiento)
        self.assertEqual(params.get("FechaEntrega"), cab.fecha_entrega)
        self.assertEqual(params.get("id_condventa"), cab.id_condventa)
        cart.refresh_from_db()
        self.assertEqual(cart.lista_id, 4)

    def test_paridad_comp_ped_y_stockp(self):
        """Paridad AdministraNET: totales cabecera, alícuotas id/% y saldo en renglón."""
        state = {
            "codmov": 1000,
            "talonario": {"Nro": 24, "PV": 1},
            "cotizacion": {"ValorPesos": Decimal("1180.50"), "id_cotizacion": 1},
            "saldo_pedido_cliente": Decimal("5"),
        }
        conn = FakeConn(state)
        cart = self._cart(tipo="PED")
        with self._with_patches(conn):
            ok, err, _ = checkout_svc.confirmar(
                cart, CheckoutInput(tipo="PED", id_punto_venta=1), id_usuario=5
            )
        self.assertTrue(ok, err)
        comp = state.get("comp_ped_params") or {}
        # neto 200 + iva 42 = 242 (ImporteVenta bruto con IVA)
        self.assertEqual(comp.get("ImporteVenta"), Decimal("242.00"))
        self.assertEqual(comp.get("SubTotalDesc"), Decimal("200.00"))
        self.assertEqual(comp.get("CotiDolar"), Decimal("1180.50"))
        self.assertTrue(comp.get("ImporteVentaL"))
        self.assertIn("PESOS", comp.get("ImporteVentaL", ""))
        self.assertEqual(comp.get("cod_mov_ped_orginal"), 1001)
        self.assertEqual(comp.get("Nro_Comp_PED_orginal"), "0001-00000024")
        self.assertRegex(comp.get("fecha_control", ""), r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$")

        stockp = (state.get("stockp_params") or [])[0]
        self.assertEqual(stockp.get("Alicuota"), 1)
        self.assertEqual(stockp.get("imp_alicuota_iva"), Decimal("21"))
        self.assertEqual(stockp.get("AlicuotaIB"), 2)
        self.assertEqual(stockp.get("imp_alicuota_iibb"), Decimal("3.50"))
        self.assertEqual(stockp.get("saldo"), Decimal("5"))
        self.assertEqual(stockp.get("coti_dolar"), Decimal("1180.50"))
        self.assertEqual(stockp.get("id_cotizacion"), 1)
        self.assertEqual(stockp.get("cantidad_pendiente_opt"), Decimal("2"))
        self.assertEqual(stockp.get("cantidad_fab_pendiente_opt"), Decimal("2"))
        self.assertEqual(stockp.get("promocion"), "No")
        self.assertEqual(stockp.get("promocion_tipo"), "")
        self.assertEqual(stockp.get("promocion_cant"), 0)

    def test_actualiza_stock_deposito_en_pedido(self):
        conn = FakeConn({"codmov": 1000})
        cart = self._cart(tipo="PED")
        with self._with_patches(conn):
            checkout_svc.confirmar(cart, CheckoutInput(tipo="PED", id_punto_venta=3), id_usuario=5)
        sqls = " ".join(s.lower() for s, _ in conn.cur.executed)
        self.assertIn("update stock_deposito", sqls)
        self.assertIn("for update", sqls)  # numeración segura

    def test_stock_insuficiente_rollback(self):
        conn = FakeConn({"codmov": 1000, "stock_rowcount": 0})
        cart = self._cart(tipo="PED")
        with self._with_patches(conn):
            ok, err, result = checkout_svc.confirmar(cart, CheckoutInput(tipo="PED", id_punto_venta=3), id_usuario=5)
        self.assertFalse(ok)
        self.assertIn("Stock insuficiente", err)
        self.assertTrue(conn.rolled_back)
        cart.refresh_from_db()
        self.assertEqual(cart.estado, EcomCart.ESTADO_BORRADOR)

    def test_rollback_ante_fallo_en_renglon(self):
        conn = FakeConn({"codmov": 1000, "raise_on_stockp": True})
        cart = self._cart(tipo="PED")
        with self._with_patches(conn):
            ok, err, result = checkout_svc.confirmar(cart, CheckoutInput(tipo="PED", id_punto_venta=3), id_usuario=5)
        self.assertFalse(ok)
        self.assertTrue(conn.rolled_back)
        cart.refresh_from_db()
        self.assertEqual(cart.estado, EcomCart.ESTADO_BORRADOR)
        self.assertIsNone(cart.codigo_movimiento)


class TestCheckoutPresupuesto(CheckoutTestBase):
    def test_alta_presupuesto_no_toca_stock(self):
        conn = FakeConn({"codmov": 2000, "talonario": {"Nro": 10, "PV": 1}})
        cart = self._cart(tipo="PRE")
        with self._with_patches(conn):
            ok, err, result = checkout_svc.confirmar(cart, CheckoutInput(tipo="PRE", id_punto_venta=1), id_usuario=5)
        self.assertTrue(ok, err)
        self.assertEqual(result["codigo_movimiento"], 2001)
        sqls = " ".join(s.lower() for s, _ in conn.cur.executed)
        self.assertNotIn("update stock_deposito", sqls)
        self.assertEqual(state_stockp := conn.state.get("stockp_count"), 1)


class TestCheckoutDevolucion(CheckoutTestBase):
    def test_alta_devolucion_ok(self):
        conn = FakeConn({"codmov": 3000, "talonario": {"Nro": 20, "PV": 2}})
        cart = self._cart(tipo="DEV")
        with self._with_patches(conn):
            ok, err, result = checkout_svc.confirmar(cart, CheckoutInput(tipo="DEV", id_punto_venta=2), id_usuario=5)
        self.assertTrue(ok, err)
        self.assertEqual(result["codigo_movimiento"], 3001)
        self.assertEqual(result["nro_comprobante"], "0002-00000020")
        self.assertEqual(conn.state.get("comp_ped_count"), 1)
        self.assertEqual(conn.state.get("stockp_count"), 1)
        cart.refresh_from_db()
        self.assertEqual(cart.estado, EcomCart.ESTADO_CONFIRMADO)

    def test_devolucion_incrementa_stock_sin_validar_disponible(self):
        # stock_rowcount 0 (no habría disponible): DEV NO valida → igual confirma.
        conn = FakeConn({"codmov": 3000, "stock_rowcount": 0})
        cart = self._cart(tipo="DEV")
        with self._with_patches(conn):
            ok, err, result = checkout_svc.confirmar(cart, CheckoutInput(tipo="DEV", id_punto_venta=2), id_usuario=5)
        self.assertTrue(ok, err)
        sqls = [" ".join(s.split()).lower() for s, _ in conn.cur.executed]
        upd = [s for s in sqls if s.startswith("update stock_deposito")]
        self.assertEqual(len(upd), 1)
        # el UPDATE de DEV NO lleva condición de disponible
        self.assertNotIn("saldo, 0) - coalesce(saldo_pedido_cliente", upd[0])
        self.assertNotIn(">=", upd[0])


class TestCheckoutValidaciones(CheckoutTestBase):
    def test_carrito_vacio(self):
        cart = EcomCart.objects.create(base_empresa="emp1", id_usuario=5, idcliente=10, lista_id=2, id_deposito=1)
        ok, err, _ = checkout_svc.confirmar(cart, CheckoutInput(tipo="PED", id_punto_venta=3), id_usuario=5)
        self.assertFalse(ok)
        self.assertIn("vacío", err)

    def test_sin_punto_de_venta(self):
        cart = self._cart(tipo="PED")
        ok, err, _ = checkout_svc.confirmar(cart, CheckoutInput(tipo="PED", id_punto_venta=None), id_usuario=5)
        self.assertFalse(ok)
        self.assertIn("punto de venta", err)

    def test_idempotencia(self):
        cart = self._cart(tipo="PED")
        cart.estado = EcomCart.ESTADO_CONFIRMADO
        cart.codigo_movimiento = 999
        cart.nro_comprobante = "0003-00000001"
        cart.save()
        called = {"n": 0}

        def _boom(_b):
            called["n"] += 1
            raise AssertionError("no debe abrir conexión")

        with patch.object(checkout_svc, "get_connection", _boom):
            ok, err, result = checkout_svc.confirmar(cart, CheckoutInput(tipo="PED", id_punto_venta=3), id_usuario=5)
        self.assertTrue(ok)
        self.assertEqual(result["codigo_movimiento"], 999)
        self.assertEqual(called["n"], 0)


class TestCheckoutAutorizacion(CheckoutTestBase):
    def test_cliente_al_dia_autorizado(self):
        conn = FakeConn({"codmov": 1000, "ultimaf": None})
        cart = self._cart(tipo="PED")
        with self._with_patches(conn, cli=self._cli(credito_limite_dias=30)):
            ok, err, result = checkout_svc.confirmar(cart, CheckoutInput(tipo="PED", id_punto_venta=3), id_usuario=5)
        self.assertTrue(ok, err)
        self.assertEqual(result["autorizacion"], "Autorizado")

    def test_cliente_con_exceso_no_autorizado(self):
        vieja = date.today() - timedelta(days=45)
        conn = FakeConn({"codmov": 1000, "ultimaf": vieja})
        cart = self._cart(tipo="PED")
        with self._with_patches(conn, cli=self._cli(credito_limite_dias=30)):
            ok, err, result = checkout_svc.confirmar(cart, CheckoutInput(tipo="PED", id_punto_venta=3), id_usuario=5)
        self.assertTrue(ok, err)
        self.assertEqual(result["autorizacion"], "No Autorizado")

    def test_alta_por_cliente_no_autorizado(self):
        conn = FakeConn({"codmov": 1000, "ultimaf": None})
        cart = self._cart(tipo="PED")
        with self._with_patches(conn):
            ok, err, result = checkout_svc.confirmar(
                cart, CheckoutInput(tipo="PED", id_punto_venta=3, es_cliente=True), id_usuario=5
            )
        self.assertTrue(ok, err)
        self.assertEqual(result["autorizacion"], "No Autorizado")


class TestCheckoutPercepcionesIIBB(CheckoutTestBase):
    """REQ-CHK-009: percepciones IIBB configurables por sucursal (agente de percepción)."""

    def test_sucursal_no_agente_sin_percepciones(self):
        state = {"codmov": 1000, "agente_percep": "No"}
        conn = FakeConn(state)
        cart = self._cart(tipo="PED")
        with self._with_patches(conn):
            ok, err, _ = checkout_svc.confirmar(cart, CheckoutInput(tipo="PED", id_punto_venta=3), id_usuario=5)
        self.assertTrue(ok, err)
        self.assertIsNone(state.get("percep_count"))
        self.assertEqual(state["comp_ped_params"]["total_percep"], Decimal("0"))

    def test_sucursal_agente_calcula_e_inserta(self):
        state = {
            "codmov": 1000,
            "agente_percep": "Si",
            "percep_param": [{"id_percep_cli_tipo": 7}],
            "percep_tipos": {7: {
                "id_percep_cli_tipo": 7, "nombre_percep_cli_tipo": "IIBB CABA",
                "alicuota_percep_cli_tipo": "3", "cod_afip": 1,
            }},
        }
        conn = FakeConn(state)
        cart = self._cart(tipo="PED")  # neto 2*100 = 200
        with self._with_patches(conn):
            ok, err, _ = checkout_svc.confirmar(cart, CheckoutInput(tipo="PED", id_punto_venta=3), id_usuario=5)
        self.assertTrue(ok, err)
        self.assertTrue(conn.committed)
        self.assertEqual(state.get("percep_count"), 1)
        # base 200 * 3% = 6; ImporteVenta = 242 + 6 = 248
        self.assertEqual(state["comp_ped_params"]["total_percep"], Decimal("6.00"))
        self.assertEqual(state["comp_ped_params"]["ImporteVenta"], Decimal("248.00"))
        row = state["percep_rows"][0]
        self.assertEqual(row["importe_percep_cli"], Decimal("6.00"))
        self.assertEqual(row["alicuota_percep_cli"], Decimal("3"))
        self.assertEqual(row["tipo_comp"], "PED")
        self.assertEqual(row["id_percep_cli_tipo"], 7)

    def test_agente_override_por_checkout_input(self):
        state = {
            "codmov": 1000,
            "agente_percep": "No",  # la sucursal dice No...
            "percep_param": [{"id_percep_cli_tipo": 7}],
            "percep_tipos": {7: {"id_percep_cli_tipo": 7, "nombre_percep_cli_tipo": "IIBB",
                                 "alicuota_percep_cli_tipo": "2.5", "cod_afip": 1}},
        }
        conn = FakeConn(state)
        cart = self._cart(tipo="PRE")
        # ...pero la sesión fuerza 'Si' (override)
        with self._with_patches(conn):
            ok, err, _ = checkout_svc.confirmar(
                cart, CheckoutInput(tipo="PRE", id_punto_venta=3, agente_percep="Si"), id_usuario=5
            )
        self.assertTrue(ok, err)
        self.assertEqual(state.get("percep_count"), 1)
        self.assertEqual(state["comp_ped_params"]["total_percep"], Decimal("5.00"))  # 200 * 2.5%

    def test_agente_sin_config_cliente_bloquea(self):
        state = {"codmov": 1000, "agente_percep": "Si", "percep_param": []}
        conn = FakeConn(state)
        cart = self._cart(tipo="PED")
        with self._with_patches(conn):
            ok, err, result = checkout_svc.confirmar(cart, CheckoutInput(tipo="PED", id_punto_venta=3), id_usuario=5)
        self.assertFalse(ok)
        self.assertIn("percepciones", err.lower())
        self.assertTrue(conn.rolled_back)
        self.assertIsNone(result)
        cart.refresh_from_db()
        self.assertEqual(cart.estado, EcomCart.ESTADO_BORRADOR)

    def test_devolucion_no_calcula_percepciones(self):
        state = {"codmov": 1000, "agente_percep": "Si", "percep_param": [{"id_percep_cli_tipo": 7}],
                 "percep_tipos": {7: {"id_percep_cli_tipo": 7, "alicuota_percep_cli_tipo": "3"}}}
        conn = FakeConn(state)
        cart = self._cart(tipo="DEV")
        with self._with_patches(conn):
            ok, err, _ = checkout_svc.confirmar(cart, CheckoutInput(tipo="DEV", id_punto_venta=3), id_usuario=5)
        self.assertTrue(ok, err)
        self.assertIsNone(state.get("percep_count"))
        self.assertEqual(state["comp_ped_params"]["total_percep"], Decimal("0"))


class TestCheckoutAprobacionComercial(CheckoutTestBase):
    @patch.object(checkout_svc, "aprobacion_pedidos_activa", return_value=False)
    def test_flag_off_sin_hook_aprobacion(self, _flag):
        state = {"codmov": 1000, "talonario": {"Nro": 57, "PV": 3}}
        conn = FakeConn(state)
        cart = self._cart(tipo="PED")
        with self._with_patches(conn):
            ok, err, _ = checkout_svc.confirmar(
                cart, CheckoutInput(tipo="PED", id_punto_venta=3), id_usuario=5
            )
        self.assertTrue(ok, err)
        self.assertIsNone(state.get("aprobacion_update"))
        self.assertIsNone(state.get("aprobacion_evento_count"))

    @patch("ecom.services.aprobacion_pedidos.aprobacion_pedidos_activa", return_value=True)
    @patch.object(checkout_svc, "aprobacion_pedidos_activa", return_value=True)
    @patch.object(checkout_svc, "evaluar_reglas", return_value=(True, ["monto"]))
    def test_flag_on_setea_pendiente(self, _eval, _flag_checkout, _flag_aprob):
        state = {"codmov": 1000, "talonario": {"Nro": 57, "PV": 3}}
        conn = FakeConn(state)
        cart = self._cart(tipo="PED")
        with self._with_patches(conn):
            ok, err, _ = checkout_svc.confirmar(
                cart,
                CheckoutInput(tipo="PED", id_punto_venta=3),
                id_usuario=5,
                cod_viajante=42,
            )
        self.assertTrue(ok, err)
        self.assertEqual(state.get("aprobacion_update"), ("pendiente", 1001))
        self.assertEqual(state.get("aprobacion_evento_count"), 1)


class TestCalcularFechaEntrega(TestCase):
    """REQ-CHK-008: fecha de entrega = hoy + días, saltando un día no laborable (paridad legacy)."""

    def test_suma_dias_sin_dias_no_laborables(self):
        esperado = date.today() + timedelta(days=2)
        self.assertEqual(checkout_svc._calcular_fecha_entrega(2, []), esperado)

    def test_dia_habil_no_se_corre(self):
        base = date.today() + timedelta(days=3)
        # Marcamos como no laborable un weekday distinto al de `base` → no debe correrse.
        otro_weekday = (base.isoweekday() % 7) + 1
        self.assertEqual(checkout_svc._calcular_fecha_entrega(3, [otro_weekday]), base)

    def test_salta_dia_no_laborable(self):
        base = date.today() + timedelta(days=2)
        # El weekday resultante es no laborable → corre un día.
        resultado = checkout_svc._calcular_fecha_entrega(2, [base.isoweekday()])
        self.assertEqual(resultado, base + timedelta(days=1))

    def test_cero_dias_entrega(self):
        self.assertEqual(checkout_svc._calcular_fecha_entrega(0, []), date.today())
