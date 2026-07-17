"""
Checkout mayorista (Fase P2): confirmación del carrito con alta de comprobante legacy.

Da de alta un PEDIDO (PED), PRESUPUESTO (PRE) o DEVOLUCIÓN (DEV) en MySQL AdministraNET
dentro de una única transacción (autocommit off + COMMIT/ROLLBACK). Escribe: comp_ped
(cabecera), stockp (renglones), cliente_datos_adicionales, percep_cli (percepciones IIBB
cuando la sucursal es agente de percepción — Fase P4) y actualiza
stock_deposito.saldo_pedido_cliente: en PED con validación de disponible, en DEV sin
validación (paridad legacy), en PRE no lo toca.

Percepciones IIBB (P4): configurable por implementación vía `sucursales.agente_percep`.
Si la sucursal es agente, para PED/PRE se calcula `total_percep` sobre el neto con
descuento y se insertan filas `percep_cli` (ver `mayorista_percepciones.py`). Si no es
agente, `total_percep = 0`. En DEV no aplica.

Mejoras sobre el PHP legacy:
- Numeración con SELECT ... FOR UPDATE en codmov y talonarios (evita duplicados).
- Validación de stock disponible en el commit (UPDATE condicional).
- Idempotencia por estado del carrito (Postgres).
- Precio recalculado con el motor único en el commit (autoridad, no confía en el carrito).

Fuera de alcance P2: factura electrónica/CAE (el pedido nace 'Pendiente'), medios de
pago/caja, percepciones IIBB (total_percep=0 por ahora) y devolución (DEV → P3).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

import MySQLdb
from django.utils import timezone

from core.mysql_pool import get_connection, get_mysql_pool
from core.utils.administranet_types import to_decimal_or_none, to_int_or_none, str_or_default
from ecom.models import EcomCart
from ecom.services.catalogo_producto import resolver_precio_articulo
from ecom.services.aprobacion_pedidos import aplicar_estado_inicial_checkout, evaluar_reglas
from ecom.services.ecom_config_mysql import aprobacion_pedidos_activa, pedidos_validan_stock
from ecom.services.mayorista_cart_service import recalcular_totales
from ecom.services.mayorista_credito import evaluar_autorizacion
from ecom.services.mayorista_percepciones import (
    PercepcionesSinConfig,
    calcular_percepciones,
)
from ecom.services.numero_a_letras import numero_a_letras
from ecom.services.pedido_cabecera_comercial import (
    PedidoCabeceraComercial,
    resolver_cabecera_comercial,
)

logger = logging.getLogger(__name__)

Q2 = Decimal("0.01")


def _q2(v: Any) -> Decimal:
    return (v if isinstance(v, Decimal) else Decimal(str(v))).quantize(Q2, rounding=ROUND_HALF_UP)


def _dec(v: Any, default: str = "0") -> Decimal:
    r = to_decimal_or_none(v)
    return r if r is not None else Decimal(default)


@dataclass
class CheckoutInput:
    tipo: str = EcomCart.TIPO_PEDIDO           # 'PED' | 'PRE' | 'DEV'
    id_punto_venta: Optional[int] = None
    forma_entrega: str = ""
    id_cliente_domicilio: Optional[int] = None
    id_ruta: Optional[int] = None
    observaciones: str = ""
    es_cliente: bool = False                    # alta por el propio cliente (autogestión)
    dias_entrega: int = 0
    dias_no_laborables: List[int] = field(default_factory=list)  # ISO weekday (1=lun..7=dom)
    # IIBB configurable por implementación: 'Si'/'No' (sucursal agente de percepción).
    # Si es None, el servicio lo resuelve desde la sucursal del usuario (paridad legacy).
    agente_percep: Optional[str] = None
    cod_mov_presupuesto_origen: Optional[int] = None
    enviar_mail_cliente: bool = True
    # Cabecera comercial (opcional; si no se envía, el resolver usa defaults del cliente)
    es_supervisor: bool = False
    fecha_pedido: Optional[date] = None
    fecha_entrega: Optional[date] = None
    vencimiento: Optional[date] = None
    id_condventa: Optional[int] = None
    cond_venta: Optional[str] = None
    lista_id: Optional[int] = None


def confirmar(
    cart: EcomCart,
    datos: CheckoutInput,
    *,
    id_usuario: int,
    cod_viajante: Optional[int] = None,
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Confirma el carrito dando de alta el comprobante. Devuelve (ok, error, result)."""
    tipo = (datos.tipo or EcomCart.TIPO_PEDIDO).upper()
    if tipo not in (EcomCart.TIPO_PEDIDO, EcomCart.TIPO_PRESUPUESTO, EcomCart.TIPO_DEVOLUCION):
        return False, "Tipo de comprobante no soportado.", None

    # Idempotencia: carrito ya confirmado → devolver resultado previo, sin reescribir.
    if cart.estado == EcomCart.ESTADO_CONFIRMADO and cart.codigo_movimiento:
        return True, None, _result_desde_cart(cart)

    items = list(cart.items.all())
    if not items:
        return False, "El carrito está vacío.", None

    pv = to_int_or_none(datos.id_punto_venta)
    if pv is None:
        return False, "Falta seleccionar el punto de venta.", None

    if not cart.idcliente:
        return False, "Falta seleccionar el cliente.", None

    cli = _fetch_cliente(cart.base_empresa, int(cart.idcliente))
    if not cli:
        return False, "Cliente no encontrado.", None

    cabecera, err_cab = resolver_cabecera_comercial(
        cart.base_empresa,
        int(cart.idcliente),
        es_supervisor=bool(datos.es_supervisor),
        fecha_pedido=datos.fecha_pedido,
        fecha_entrega=datos.fecha_entrega,
        vencimiento=datos.vencimiento,
        id_condventa=datos.id_condventa,
        lista_id=datos.lista_id,
        dias_entrega=int(datos.dias_entrega or 0),
        dias_no_laborables=datos.dias_no_laborables,
        tipo_comprobante=tipo,
    )
    if not cabecera:
        return False, err_cab or "Cabecera comercial inválida.", None

    # Fijar lista efectiva y recalcular precios (autoridad) antes de escribir.
    cart.lista_id = int(cabecera.lista_id)
    cart.save(update_fields=["lista_id", "updated_at"])
    desc_renglon = _dec(cli.get("descRenglon"), "0")
    if not _reprice_items(cart, items, desc_renglon):
        return False, "No se pudieron recalcular los precios con la lista seleccionada.", None
    recalcular_totales(cart)
    items = list(cart.items.all())

    extras = _fetch_articulo_extras(cart.base_empresa, [it.id_articulo for it in items])

    cod_mov: Optional[int] = None
    nro_comp: Optional[str] = None
    autorizacion = ""

    with get_connection(cart.base_empresa) as conn:
        try:
            conn.autocommit(False)
            cur = conn.cursor(MySQLdb.cursors.DictCursor)

            autorizacion, _dias = evaluar_autorizacion(
                cur,
                int(cart.idcliente),
                to_int_or_none(cli.get("credito_limite_dias")) or 0,
                es_cliente=datos.es_cliente,
            )

            # CodigoMovimiento (lock)
            cur.execute("SELECT CodigoMovimiento FROM codmov WHERE codigo = 1 FOR UPDATE")
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return False, "No se pudo obtener el código de movimiento.", None
            cod_mov = int(_dec(row.get("CodigoMovimiento"))) + 1
            cur.execute("UPDATE codmov SET CodigoMovimiento = %s WHERE codigo = 1", [cod_mov])

            # Numeración talonario (lock) — corrige el bug de concurrencia del PHP
            cur.execute(
                """
                SELECT Nro, PV FROM talonarios
                WHERE id_punto_venta = %s AND TipoComprobante = %s
                LIMIT 1 FOR UPDATE
                """,
                [pv, tipo],
            )
            tal = cur.fetchone()
            if not tal:
                conn.rollback()
                return False, "No hay talonario para el punto de venta y tipo de comprobante.", None
            nro = to_int_or_none(tal.get("Nro")) or 0
            pv_num = to_int_or_none(tal.get("PV")) or 0
            nro_comp = f"{pv_num:04d}-{nro:08d}"
            cur.execute(
                "UPDATE talonarios SET Nro = Nro + 1 WHERE id_punto_venta = %s AND TipoComprobante = %s",
                [pv, tipo],
            )

            hoy = cabecera.fecha_pedido
            fecha_entrega = cabecera.fecha_entrega

            # Percepciones IIBB (P4) — configurable por implementación (sucursal agente).
            #  - PED/PRE: si la sucursal es agente, calcula sobre el neto con descuento.
            #  - DEV: no aplica (total_percep = 0).
            percepciones = []
            total_percep = Decimal("0")
            if tipo in (EcomCart.TIPO_PEDIDO, EcomCart.TIPO_PRESUPUESTO):
                agente = datos.agente_percep
                if agente is None:
                    agente = _fetch_agente_percep(cur, id_usuario)
                try:
                    percepciones, total_percep = calcular_percepciones(
                        cur, int(cart.idcliente), _dec(cart.subtotal_neto), agente
                    )
                except PercepcionesSinConfig as exc:
                    conn.rollback()
                    return False, str(exc), None

            # cliente_datos_adicionales
            cur.execute(
                """
                INSERT INTO cliente_datos_adicionales
                    (fechaEntrega, id_deposito_despacho, Fentrega, origen_pedido,
                     TipoComprobante, id_cliente, CodigoMovimiento, id_cliente_domicilio, id_ruta)
                VALUES (%(fechaEntrega)s, %(id_dep)s, %(fentrega)s, 'Web',
                        %(tipo)s, %(id_cliente)s, %(cod_mov)s, %(id_dom)s, %(id_ruta)s)
                """,
                {
                    "fechaEntrega": fecha_entrega,
                    "id_dep": cart.id_deposito,
                    "fentrega": str_or_default(datos.forma_entrega, ""),
                    "tipo": tipo,
                    "id_cliente": int(cart.idcliente),
                    "cod_mov": cod_mov,
                    "id_dom": to_int_or_none(datos.id_cliente_domicilio),
                    "id_ruta": to_int_or_none(datos.id_ruta),
                },
            )

            # Cotización vigente (una lectura por transacción; paridad Principal.cotizacion).
            coti = _fetch_cotizacion_vigente(cur)
            coti_dolar = _dec(coti.get("ValorPesos"), "1")
            id_cotizacion = to_int_or_none(coti.get("id_cotizacion")) or 1

            # comp_ped (cabecera) — totales recalculados
            neto_gravado = _q2(_dec(cart.neto_gravado_21) + _dec(cart.neto_gravado_105))
            importe_venta = _q2(_dec(cart.total) + total_percep)
            cur.execute(_SQL_INSERT_COMP_PED, {
                "Fecha": hoy,
                "TipoComprobante": tipo,
                "NroComprobante": nro_comp,
                "NroCompBusq": nro,
                "Codigo": int(cart.idcliente),
                "CodigoMovimiento": cod_mov,
                "id_pv": pv,
                "CodSucursal": to_int_or_none(cli.get("id_sucursal")),
                "IdUsuario": id_usuario,
                "CodViajante": to_int_or_none(cod_viajante) or 0,
                "TipoPedido": "Ecom cliente" if datos.es_cliente else "Ecom vendedor",
                "Detalle": str_or_default(datos.observaciones, ""),
                "ImporteVenta": importe_venta,
                "ImporteVentaL": numero_a_letras(float(importe_venta)),
                "IVA1": _dec(cart.iva_21),
                "IVA2": _dec(cart.iva_105),
                "Exento": _dec(cart.exento),
                "SubTotal1": _dec(cart.neto_gravado_21),
                "SubTotal2": _dec(cart.neto_gravado_105),
                "SubTotalGral": neto_gravado,
                "PorDesc": _dec(cart.descuento_pie_pct),
                "SubTotalDesc": _dec(cart.subtotal_neto),
                "impuesto_interno_total": _dec(cart.impuesto_interno_total),
                "total_percep": total_percep,
                "CotiDolar": coti_dolar,
                "cod_mov_ped_orginal": cod_mov if tipo == EcomCart.TIPO_PEDIDO else 0,
                "Nro_Comp_PED_orginal": nro_comp if tipo == EcomCart.TIPO_PEDIDO else "",
                "autorizacion_sistema": autorizacion,
                "Vencimiento": cabecera.vencimiento,
                "FechaEntrega": fecha_entrega,
                "FormaEntrega": str_or_default(datos.forma_entrega, ""),
                "id_deposito_despacho": cart.id_deposito,
                "CondVenta": str_or_default(cabecera.cond_venta or datos.cond_venta or cli.get("condVenta"), ""),
                "id_condventa": to_int_or_none(cabecera.id_condventa),
                "fecha_control": timezone.localtime().strftime("%d/%m/%Y %H:%M:%S"),
            })

            # percep_cli — una fila por tipo de percepción (dentro de la transacción)
            for per in percepciones:
                cur.execute(_SQL_INSERT_PERCEP_CLI, {
                    "id_percep_cli_tipo": per.id_percep_cli_tipo,
                    "alicuota_percep_cli": per.alicuota,
                    "importe_percep_cli": per.importe,
                    "codigo_movimiento": cod_mov,
                    "id_cliente": int(cart.idcliente),
                    "tipo_comp": tipo,
                })

            # Renglones stockp (+ stock_deposito según tipo)
            #  - PED: reserva stock → incrementa saldo comprometido (con/sin validación según config).
            #  - DEV: incrementa saldo comprometido SIN validación (paridad legacy alta_devolucion).
            #  - PRE: no toca stock.
            validar_stock_ped = (
                tipo == EcomCart.TIPO_PEDIDO and pedidos_validan_stock(cart.base_empresa)
            )
            for orden, it in enumerate(items, start=1):
                cant = _dec(it.cantidad)
                if tipo == EcomCart.TIPO_PEDIDO:
                    if validar_stock_ped:
                        cur.execute(
                            """
                            UPDATE stock_deposito
                            SET saldo_pedido_cliente = COALESCE(saldo_pedido_cliente, 0) + %s
                            WHERE id_articulo = %s AND id_deposito = %s
                              AND (COALESCE(saldo, 0) - COALESCE(saldo_pedido_cliente, 0)) >= %s
                            """,
                            [cant, it.id_articulo, cart.id_deposito, cant],
                        )
                        if cur.rowcount == 0:
                            conn.rollback()
                            nombre = (it.descripcion or "").strip() or f"artículo {it.id_articulo}"
                            return False, f"Stock insuficiente: {nombre}.", None
                    else:
                        cur.execute(
                            """
                            UPDATE stock_deposito
                            SET saldo_pedido_cliente = COALESCE(saldo_pedido_cliente, 0) + %s
                            WHERE id_articulo = %s AND id_deposito = %s
                            """,
                            [cant, it.id_articulo, cart.id_deposito],
                        )
                elif tipo == EcomCart.TIPO_DEVOLUCION:
                    cur.execute(
                        """
                        UPDATE stock_deposito
                        SET saldo_pedido_cliente = COALESCE(saldo_pedido_cliente, 0) + %s
                        WHERE id_articulo = %s AND id_deposito = %s
                        """,
                        [cant, it.id_articulo, cart.id_deposito],
                    )

                saldo_renglon = _fetch_saldo_pedido_cliente(
                    cur, it.id_articulo, cart.id_deposito, tipo
                )
                cur.execute(_SQL_INSERT_STOCKP, _params_stockp(
                    it, orden, cart, tipo, nro_comp, cod_mov, cod_viajante,
                    id_usuario, cli, extras.get(it.id_articulo, {}),
                    cod_mov_presupuesto=datos.cod_mov_presupuesto_origen if tipo == EcomCart.TIPO_PEDIDO else None,
                    fecha_pedido=cabecera.fecha_pedido,
                    coti_dolar=coti_dolar,
                    id_cotizacion=id_cotizacion,
                    saldo=saldo_renglon,
                ))

            if (
                datos.cod_mov_presupuesto_origen
                and tipo == EcomCart.TIPO_PEDIDO
                and cod_mov is not None
            ):
                from ecom.services.presupuesto_a_pedido_service import (
                    finalizar_vinculo_presupuesto_pedido,
                )

                finalizar_vinculo_presupuesto_pedido(
                    cur, int(datos.cod_mov_presupuesto_origen), int(cod_mov)
                )

            if (
                tipo == EcomCart.TIPO_PEDIDO
                and cod_mov is not None
                and aprobacion_pedidos_activa(cart.base_empresa)
            ):
                requiere_aprob, reglas = evaluar_reglas(
                    cart.base_empresa,
                    cart,
                    cli,
                    autorizacion_sistema=autorizacion,
                    cursor=cur,
                    cod_mov_excluir=int(cod_mov),
                )
                aplicar_estado_inicial_checkout(
                    cur,
                    cart.base_empresa,
                    cod_mov=int(cod_mov),
                    cod_viajante=to_int_or_none(cod_viajante),
                    requiere=requiere_aprob,
                    reglas=reglas,
                )

            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.exception("Error en checkout mayorista (cart_id=%s)", cart.id)
            return False, "No se pudo confirmar el comprobante.", None
        finally:
            try:
                conn.autocommit(True)
            except Exception:
                pass

    # Persistir resultado en el carrito (idempotencia)
    cart.estado = EcomCart.ESTADO_CONFIRMADO
    cart.codigo_movimiento = cod_mov
    cart.nro_comprobante = nro_comp
    cart.autorizacion = autorizacion
    cart.confirmed_at = timezone.now()
    cart.save(update_fields=["estado", "codigo_movimiento", "nro_comprobante", "autorizacion", "confirmed_at", "updated_at"])

    if (
        datos.enviar_mail_cliente
        and tipo == EcomCart.TIPO_PEDIDO
        and cod_mov is not None
    ):
        from ecom.services.ecom_config_mysql import pedidos_envian_mail_confirmacion

        if pedidos_envian_mail_confirmacion(cart.base_empresa):
            _encolar_mail_comprobante_si_correo(
                cart.base_empresa,
                int(cod_mov),
                int(cart.idcliente),
                cli,
            )

    return True, None, _result_desde_cart(cart)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _encolar_mail_comprobante_si_correo(
    base_empresa: str,
    cod_mov: int,
    id_cliente: int,
    cli: Dict[str, Any],
) -> None:
    """Encola mail al cliente tras confirmar PED (no bloquea checkout)."""
    email = str(cli.get("Email") or cli.get("email") or "").strip()
    if not email or "@" not in email:
        return
    try:
        from ecom.services.comprobante_mail_async import encolar_comprobante_mail

        encolar_comprobante_mail(
            base_empresa=base_empresa,
            cod_mov=cod_mov,
            tipo_comp=0,
            to_email=email,
            idcliente=id_cliente,
        )
    except Exception:
        logger.exception("No se pudo encolar mail de comprobante cod_mov=%s", cod_mov)


def _result_desde_cart(cart: EcomCart) -> Dict[str, Any]:
    return {
        "codigo_movimiento": cart.codigo_movimiento,
        "nro_comprobante": cart.nro_comprobante,
        "tipo": cart.tipo_comprobante,
        "autorizacion": cart.autorizacion,
        "total": float(cart.total),
        "subtotal_neto": float(cart.subtotal_neto),
    }


def _reprice_items(cart: EcomCart, items: List[Any], descuento_cliente: Decimal) -> bool:
    """Recalcula el precio de cada renglón con el motor (autoridad en el commit)."""
    for it in items:
        res = resolver_precio_articulo(
            cart.base_empresa,
            it.id_articulo,
            lista_id=cart.lista_id,
            codigo_cliente=cart.idcliente,
            descuento_cliente=descuento_cliente,
            iva_incluido=False,
        )
        if res is None:
            return False
        precio, row = res
        it.precio_unitario_neto = _dec(precio)
        it.alicuota_iva = _dec(row.get("alic_iva"), "21")
        it.impuesto_interno_pct = _dec(row.get("impuesto_interno"), "0")
        it.save(update_fields=["precio_unitario_neto", "alicuota_iva", "impuesto_interno_pct"])
    return True


def _fetch_cliente(base_empresa: str, codigo_cliente: int) -> Optional[Dict[str, Any]]:
    sql = """
        SELECT
            cliente.Codigo AS Codigo,
            cliente.id_sucursal AS id_sucursal,
            cliente.id_cv AS id_cv,
            cliente.Email AS Email,
            cliente.email AS email,
            cliente.saldo AS saldo,
            cliente.Credito AS Credito,
            cond_venta.Descripcion AS condVenta,
            cliente.credito_limite_dias AS credito_limite_dias,
            cliente.descuento_por_cli AS descRenglon
        FROM cliente
        LEFT JOIN cond_venta ON cond_venta.Codigo = cliente.id_cv
        WHERE cliente.Codigo = %s
        LIMIT 1
    """
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cur = conn.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(sql, [codigo_cliente])
        return cur.fetchone()


def _fetch_agente_percep(cur, id_usuario: int) -> str:
    """Resuelve `sucursales.agente_percep` de la sucursal del usuario (paridad `control.php`).

    Usa el cursor de la transacción abierta. Devuelve 'Si'/'No' (default 'No').
    """
    cur.execute(
        """
        SELECT sucursales.agente_percep AS agente_percep
        FROM usuarios
        LEFT JOIN sucursales ON sucursales.id_sucursal = usuarios.id_sucursal
        WHERE usuarios.id_usuario = %s
        LIMIT 1
        """,
        [int(id_usuario)],
    )
    row = cur.fetchone() or {}
    return str_or_default(row.get("agente_percep") if isinstance(row, dict) else None, "No") or "No"


def _fetch_articulo_extras(base_empresa: str, ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """PrecioCosto/CodLaboratorio/tipo_art y alícuotas (id IVA/IIBB) por artículo para stockp."""
    ids = [i for i in {int(x) for x in ids if x is not None}]
    if not ids:
        return {}
    placeholders = ",".join(["%s"] * len(ids))
    sql = f"""
        SELECT
            articulo.IDArt,
            articulo.PrecioCosto,
            articulo.CodLaboratorio,
            articulo.tipo_art,
            articulo.Alicuota,
            articulo.AlicuotaIB,
            activ_iibb.alicuota AS iibb_pct
        FROM articulo
        LEFT JOIN activ_iibb ON activ_iibb.id = articulo.AlicuotaIB
        WHERE articulo.IDArt IN ({placeholders})
    """
    out: Dict[int, Dict[str, Any]] = {}
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cur = conn.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(sql, ids)
        for r in cur.fetchall():
            out[int(r["IDArt"])] = r
    return out


def _fetch_cotizacion_vigente(cur) -> Dict[str, Any]:
    """Cotización vigente (ValorPesos / id_cotizacion) dentro de la transacción."""
    cur.execute(
        "SELECT ValorPesos, id_cotizacion FROM cotizacion ORDER BY id_cotizacion LIMIT 1"
    )
    row = cur.fetchone() or {}
    return row if isinstance(row, dict) else {}


def _fetch_saldo_pedido_cliente(
    cur,
    id_articulo: int,
    id_deposito: int,
    tipo: str,
) -> Decimal:
    """Saldo comprometido tras el UPDATE de reserva (PED/DEV); 0 en PRE o sin fila."""
    if tipo not in (EcomCart.TIPO_PEDIDO, EcomCart.TIPO_DEVOLUCION):
        return Decimal("0")
    cur.execute(
        """
        SELECT COALESCE(saldo_pedido_cliente, 0) AS saldo
        FROM stock_deposito
        WHERE id_articulo = %s AND id_deposito = %s
        LIMIT 1
        """,
        [id_articulo, id_deposito],
    )
    row = cur.fetchone() or {}
    if not isinstance(row, dict) or row.get("saldo") is None:
        return Decimal("0")
    return _dec(row.get("saldo"))


def _calcular_fecha_entrega(
    dias_entrega: int,
    dias_no_laborables: List[int],
    *,
    fecha_base: Optional[date] = None,
) -> date:
    """Suma días de entrega y evita un día no laborable (paridad legacy)."""
    base = (fecha_base or date.today()) + timedelta(days=int(dias_entrega or 0))
    no_lab = {int(d) for d in (dias_no_laborables or [])}
    if base.isoweekday() in no_lab:
        base = base + timedelta(days=1)
    return base


def _params_stockp(
    it: Any, orden: int, cart: EcomCart, tipo: str, nro_comp: str, cod_mov: int,
    cod_viajante: Optional[int], id_usuario: int, cli: Dict[str, Any], extra: Dict[str, Any],
    *,
    cod_mov_presupuesto: Optional[int] = None,
    fecha_pedido: Optional[date] = None,
    coti_dolar: Decimal = Decimal("1"),
    id_cotizacion: int = 1,
    saldo: Decimal = Decimal("0"),
) -> Dict[str, Any]:
    cant = _dec(it.cantidad)
    pu = _dec(it.precio_unitario_neto)
    desc = _dec(it.porcentaje_descuento)
    alic_pct = _dec(it.alicuota_iva)
    id_alic_iva = to_int_or_none(extra.get("Alicuota")) or 0
    id_alic_iibb = to_int_or_none(extra.get("AlicuotaIB")) or 0
    iibb_pct = _dec(extra.get("iibb_pct"), "0")
    neto_u = _q2(pu * (Decimal("100") - desc) / Decimal("100"))
    iva_u = _q2(neto_u * alic_pct / Decimal("100"))
    bruto_u = _q2(neto_u + iva_u)
    costo_u = _dec(extra.get("PrecioCosto"), "0")
    tipo_comp_texto = {
        EcomCart.TIPO_PEDIDO: "Pedido",
        EcomCart.TIPO_PRESUPUESTO: "Presupuesto",
        EcomCart.TIPO_DEVOLUCION: "Devolucion",
    }.get(tipo, "Pedido")
    tipo_iva = "Exento" if alic_pct == 0 else "Gravado"
    tipo_unidad = str_or_default(getattr(it, "tipo_unidad", None), "Unidad")
    cant_div = _dec(getattr(it, "cantidad_dividir", None), "1")
    if cant_div <= 0:
        cant_div = Decimal("1")
    promocion = str_or_default(it.promocion, "No") or "No"
    promocion_tipo = ""
    promocion_cant = 0
    promocion_por = Decimal("0")
    if promocion == "Si":
        promocion_tipo = str_or_default(it.promocion_tipo, "")
        promocion_cant = to_int_or_none(it.promocion_cant) or 0
        promocion_por = _dec(it.promocion_por)
    return {
        "IDArt": it.id_articulo,
        "CodigoArticulo": str_or_default(it.codigo, ""),
        "Descripcion": str_or_default(it.descripcion, ""),
        "id_manual": str_or_default(it.id_manual, ""),
        "CodigoMovimiento": cod_mov,
        "Fecha": fecha_pedido or date.today(),
        "Salida": cant,
        "Cantidad": cant,
        "Alicuota": id_alic_iva,
        "AlicuotaIB": id_alic_iibb,
        "imp_alicuota_iva": alic_pct,
        "imp_alicuota_iibb": iibb_pct,
        "saldo": _dec(saldo),
        "coti_dolar": _dec(coti_dolar),
        "id_cotizacion": id_cotizacion,
        "PrecioVentaxU": pu,
        "PrecioNetoxU": neto_u,
        "PrecioIVAxU": iva_u,
        "PrecioBrutoxU": bruto_u,
        "PrecioCostoxU": costo_u,
        "PrecioVentaxR": _q2(pu * cant),
        "PrecioNetoxR": _dec(it.neto),
        "PrecioIVAxR": _dec(it.iva),
        "PrecioBrutoxR": _q2(_dec(it.neto) + _dec(it.iva)),
        "PrecioCostoxR": _q2(costo_u * cant),
        "PorDesc": desc,
        "ImpDesc": _q2(pu * cant - _dec(it.neto)),
        "impuesto_interno": _dec(it.impuesto_interno_pct),
        "impuesto_interno_subtotal": _q2(_dec(it.neto) * _dec(it.impuesto_interno_pct) / Decimal("100")),
        "TipoIVA": tipo_iva,
        "CodigoCP": int(cart.idcliente),
        "TipoComp": tipo_comp_texto,
        "Comprobante": tipo,
        "NroComprobante": nro_comp,
        "CodDeposito": cart.id_deposito,
        "CodSucursal": to_int_or_none(cli.get("id_sucursal")),
        "idusuario": id_usuario,
        "CodViajante": to_int_or_none(cod_viajante) or 0,
        "CodLaboratorio": to_int_or_none(extra.get("CodLaboratorio")),
        "lista_precio": cart.lista_id,
        "tipo_art": str_or_default(extra.get("tipo_art"), ""),
        "Orden": orden,
        "cantidad_entregada": cant,
        "cantidad_pendiente": cant,
        "cantidad_pendiente_opt": cant,
        "cantidad_fab_pendiente_opt": cant,
        "promocion": promocion,
        "promocion_por": promocion_por,
        "promocion_tipo": promocion_tipo,
        "promocion_cant": promocion_cant,
        "tipo_unidad": tipo_unidad,
        "cantidad_dividir": cant_div,
        "cantidad_unidad_display": cant_div,
        "codmov_presupuesto": cod_mov_presupuesto or 0,
        "NroPresupuesto": "",
    }


_SQL_INSERT_COMP_PED = """
    INSERT INTO comp_ped SET
        Fecha = %(Fecha)s,
        TipoComprobante = %(TipoComprobante)s,
        NroComprobante = %(NroComprobante)s,
        NroCompBusq = %(NroCompBusq)s,
        Codigo = %(Codigo)s,
        CodigoMovimiento = %(CodigoMovimiento)s,
        id_pv = %(id_pv)s,
        CodSucursal = %(CodSucursal)s,
        IdUsuario = %(IdUsuario)s,
        CodViajante = %(CodViajante)s,
        TipoPedido = %(TipoPedido)s,
        Detalle = %(Detalle)s,
        ImporteVenta = %(ImporteVenta)s,
        IVA1 = %(IVA1)s,
        IVA2 = %(IVA2)s,
        Alicuota1 = 21,
        Alicuota2 = 10.5,
        Exento = %(Exento)s,
        SubTotal1 = %(SubTotal1)s,
        SubTotal2 = %(SubTotal2)s,
        SubTotalGral = %(SubTotalGral)s,
        PorDesc1 = %(PorDesc)s,
        PorDesc2 = %(PorDesc)s,
        ImpDesc1 = 0,
        ImpDesc2 = 0,
        SubTotalDesc1 = %(SubTotal1)s,
        SubTotalDesc2 = %(SubTotal2)s,
        SubtotalDesc = %(SubTotalDesc)s,
        impuesto_interno_total = %(impuesto_interno_total)s,
        total_percep = %(total_percep)s,
        CotiDolar = %(CotiDolar)s,
        ImporteVentaL = %(ImporteVentaL)s,
        cod_mov_ped_orginal = %(cod_mov_ped_orginal)s,
        Nro_Comp_PED_orginal = %(Nro_Comp_PED_orginal)s,
        autorizacion_sistema = %(autorizacion_sistema)s,
        Estado = 'Pendiente',
        Anulado = 'No',
        Vencimiento = %(Vencimiento)s,
        FechaEntrega = %(FechaEntrega)s,
        FormaEntrega = %(FormaEntrega)s,
        id_deposito_despacho = %(id_deposito_despacho)s,
        CondVenta = %(CondVenta)s,
        id_condventa = %(id_condventa)s,
        fecha_control = %(fecha_control)s
"""


_SQL_INSERT_PERCEP_CLI = """
    INSERT INTO percep_cli SET
        id_percep_cli_tipo = %(id_percep_cli_tipo)s,
        alicuota_percep_cli = %(alicuota_percep_cli)s,
        importe_percep_cli = %(importe_percep_cli)s,
        codigo_movimiento = %(codigo_movimiento)s,
        id_cliente = %(id_cliente)s,
        tipo_comp = %(tipo_comp)s,
        anulado = 'No'
"""


_SQL_INSERT_STOCKP = """
    INSERT INTO stockp SET
        IDArt = %(IDArt)s,
        CodigoArticulo = %(CodigoArticulo)s,
        Descripcion = %(Descripcion)s,
        id_manual = %(id_manual)s,
        CodigoMovimiento = %(CodigoMovimiento)s,
        Fecha = %(Fecha)s,
        Salida = %(Salida)s,
        Cantidad = %(Cantidad)s,
        saldo = %(saldo)s,
        Alicuota = %(Alicuota)s,
        AlicuotaIB = %(AlicuotaIB)s,
        imp_alicuota_iva = %(imp_alicuota_iva)s,
        imp_alicuota_iibb = %(imp_alicuota_iibb)s,
        coti_dolar = %(coti_dolar)s,
        id_cotizacion = %(id_cotizacion)s,
        PrecioVentaxU = %(PrecioVentaxU)s,
        PrecioNetoxU = %(PrecioNetoxU)s,
        PrecioIVAxU = %(PrecioIVAxU)s,
        PrecioBrutoxU = %(PrecioBrutoxU)s,
        PrecioCostoxU = %(PrecioCostoxU)s,
        PrecioVentaxR = %(PrecioVentaxR)s,
        PrecioNetoxR = %(PrecioNetoxR)s,
        PrecioIVAxR = %(PrecioIVAxR)s,
        PrecioBrutoxR = %(PrecioBrutoxR)s,
        PrecioCostoxR = %(PrecioCostoxR)s,
        PorDesc = %(PorDesc)s,
        ImpDesc = %(ImpDesc)s,
        impuesto_interno = %(impuesto_interno)s,
        impuesto_interno_subtotal = %(impuesto_interno_subtotal)s,
        TipoIVA = %(TipoIVA)s,
        CodigoCP = %(CodigoCP)s,
        Tipo = 'Cliente',
        TipoComp = %(TipoComp)s,
        Comprobante = %(Comprobante)s,
        Anulado = 'No',
        NroComprobante = %(NroComprobante)s,
        CodDeposito = %(CodDeposito)s,
        CodSucursal = %(CodSucursal)s,
        idusuario = %(idusuario)s,
        CodViajante = %(CodViajante)s,
        CodLaboratorio = %(CodLaboratorio)s,
        lista_precio = %(lista_precio)s,
        tipo_art = %(tipo_art)s,
        Orden = %(Orden)s,
        cantidad_entregada = %(cantidad_entregada)s,
        cantidad_pendiente = %(cantidad_pendiente)s,
        cantidad_pendiente_opt = %(cantidad_pendiente_opt)s,
        cantidad_fab_pendiente_opt = %(cantidad_fab_pendiente_opt)s,
        promocion = %(promocion)s,
        promocion_por = %(promocion_por)s,
        promocion_tipo = %(promocion_tipo)s,
        promocion_cant = %(promocion_cant)s,
        tipo_unidad = %(tipo_unidad)s,
        cantidad_dividir = %(cantidad_dividir)s,
        cantidad_unidad_display = %(cantidad_unidad_display)s,
        codmov_presupuesto = %(codmov_presupuesto)s,
        NroPresupuesto = %(NroPresupuesto)s
"""
