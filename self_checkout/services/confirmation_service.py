"""
ConfirmationService: transacción atómica de confirmación final.
Flujo: codmov → talonarios → cuentacliente → stock_deposito → stock → audit_log.

Estados carrito: borrador → pago_pendiente → pago_aprobado → confirmado
(draft → awaiting_payment → paid → confirmed)

Idempotente por cart_id: reintento no duplica comprobante.
Revalida stock al inicio (UPDATE condicional).
Rollback completo si falla un paso.
Trazabilidad: audit_log con correlation_id.
"""
import logging
import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

from self_checkout.db import get_mysql_connection
from self_checkout.fe_config import is_fe_configured
from self_checkout.fe_sync import get_ultimo_autorizado_afip
from .stock_service import StockService
from .invoice_service import InvoiceService
from .tpv_payment_validation import evaluar_suma_medios_pago

logger = logging.getLogger(__name__)


def _lookup_tarjeta_ids_tc_comprobante(cursor, nombre_tarjeta: str, nombre_plan: str) -> Tuple[int, Optional[Decimal]]:
    """
    AdministraNET exige id_tc (FK lógica a tarjetas_credito.idTC) e id_tc_plan (tc_plan.Id_tc_plan)
    en INSERT tc_comprobante; el TPV los copia desde tc_temp/data_tarjeta_temp.
    Self-checkout arma la fila desde strings → resolvemos por nombre con fallback seguro.
    """
    nom_tc = (nombre_tarjeta or '').strip() or 'Mercado Pago'
    nom_plan = (nombre_plan or '').strip() or nom_tc

    def _fetch_scalar(sql: str, params: tuple) -> Optional[float]:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        if not row or row[0] is None:
            return None
        return float(row[0])

    id_tc = _fetch_scalar(
        """
        SELECT idTC FROM tarjetas_credito
        WHERE Anulado = 'No' AND LOWER(TRIM(nombre)) = LOWER(TRIM(%s))
        LIMIT 1
        """,
        (nom_tc,),
    )
    if id_tc is None and 'mercado' in nom_tc.lower():
        id_tc = _fetch_scalar(
            """
            SELECT idTC FROM tarjetas_credito
            WHERE Anulado = 'No' AND LOWER(TRIM(nombre)) LIKE %s
            ORDER BY idTC LIMIT 1
            """,
            ('%mercado%',),
        )
    if id_tc is None:
        id_tc = _fetch_scalar(
            "SELECT MIN(idTC) FROM tarjetas_credito WHERE Anulado = 'No'",
            (),
        )
    if id_tc is None:
        id_tc = 1.0

    id_tc_i = int(id_tc)

    id_tc_plan = _fetch_scalar(
        """
        SELECT Id_tc_plan FROM tc_plan
        WHERE idTC = %s AND anulado = 'No'
          AND LOWER(TRIM(nombre_tc_plan)) = LOWER(TRIM(%s))
        ORDER BY Id_tc_plan LIMIT 1
        """,
        (id_tc_i, nom_plan),
    )
    if id_tc_plan is None:
        id_tc_plan = _fetch_scalar(
            """
            SELECT MIN(Id_tc_plan) FROM tc_plan
            WHERE idTC = %s AND anulado = 'No'
            """,
            (id_tc_i,),
        )

    plan_dec = Decimal(str(id_tc_plan)).quantize(Decimal('1')) if id_tc_plan is not None else None
    return id_tc_i, plan_dec


class ConfirmationService:
    def __init__(self, base_empresa: str):
        self.base_empresa = base_empresa
        self.stock_service = StockService(base_empresa)

    def confirm(self, cart_id: int, **kwargs) -> Tuple[bool, Optional[str], Optional[dict]]:
        """Alias de confirmar (compatible con spec)."""
        return self.confirmar(cart_id=cart_id, **kwargs)

    def confirmar(
        self,
        cart_id: int,
        id_cliente: int = 1,
        email: str = '',
        tipo_comprobante: str = 'FB',
        cuit: Optional[str] = None,
        id_usuario: Optional[int] = None,
        cod_viajante: Optional[int] = None,
        tpv_importe_efectivo: Optional[float] = None,
        tpv_pago_efectivo: Optional[float] = None,
        tpv_cambio_efectivo: Optional[float] = None,
        tpv_importe_tarjeta: Optional[float] = None,
        tpv_tarjeta_nombre: Optional[str] = None,
        tpv_plan_nombre: Optional[str] = None,
        tpv_cuotas: Optional[int] = None,
        tpv_nro_tarjeta: Optional[str] = None,
        tpv_nro_cupon: Optional[str] = None,
        tpv_nro_lote: Optional[str] = None,
        tpv_intereses: Optional[float] = None,
        tpv_valor_cuota: Optional[float] = None,
        tpv_importe_parcial: Optional[float] = None,
    ) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Ejecuta la transacción atómica de confirmación.
        Idempotente: si cart ya está confirmado, retorna resultado existente sin duplicar.
        id_usuario: usuario logueado (session['user']['id_usuario']); si None se usa 0 (kiosk sin usuario).
        No se confirma ninguna venta sin CAE/CAEA: si FE falla, se hace rollback completo (stock y numeraciones no se afectan).
        Returns: (ok, error_msg, result) - result tiene codigo_movimiento, id_cuentacliente, nro_comprobante
        """
        id_usuario_final = int(id_usuario) if id_usuario is not None else 0
        correlation_id = str(uuid.uuid4())
        with get_mysql_connection(self.base_empresa) as conn:
            try:
                conn.autocommit(False)
                cursor = conn.cursor()

                # 0. Idempotencia: si ya confirmado, retornar sin duplicar
                cursor.execute("""
                    SELECT estado, codigo_movimiento, id_cuentacliente, tipo_comprobante
                    FROM self_checkout_cart WHERE id = %s
                """, [cart_id])
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return False, 'Carrito no encontrado', None
                estado_actual, cod_mov, id_cc, tipo_comp = row[0], row[1], row[2], row[3]
                if estado_actual == 'confirmado' and cod_mov and id_cc:
                    cursor.execute(
                        "SELECT NroComprobante FROM cuentacliente WHERE id_cuentacliente = %s", [id_cc]
                    )
                    nro_row = cursor.fetchone()
                    nro_comp = nro_row[0] if nro_row else str(cod_mov)
                    cursor.execute(
                        "SELECT id_punto_venta, total, subtotal FROM self_checkout_cart WHERE id = %s",
                        [cart_id],
                    )
                    cart_row = cursor.fetchone()
                    id_pv = cart_row[0] if cart_row else 1
                    tot = cart_row[1] if cart_row else 0
                    sub = cart_row[2] if cart_row else 0
                    conn.rollback()
                    logger.info('CONFIRM_IDEMPOTENT: cart_id=%s correlation_id=%s', cart_id, correlation_id)
                    return True, None, {
                        'codigo_movimiento': cod_mov,
                        'id_cuentacliente': id_cc,
                        'nro_comprobante': nro_comp,
                        'tipo_comprobante': tipo_comp or tipo_comprobante,
                        'id_punto_venta': id_pv,
                        'total': tot,
                        'subtotal': sub,
                    }

                # 1. Obtener carrito y validar estado (pago_aprobado)
                try:
                    cursor.execute("""
                        SELECT id_sucursal, id_punto_venta, id_deposito, total, subtotal, kiosk_id,
                               COALESCE(monto_descuento_voucher, 0)
                        FROM self_checkout_cart
                        WHERE id = %s AND estado = 'pago_aprobado'
                    """, [cart_id])
                except Exception:
                    cursor.execute("""
                        SELECT id_sucursal, id_punto_venta, id_deposito, total, subtotal, kiosk_id
                        FROM self_checkout_cart
                        WHERE id = %s AND estado = 'pago_aprobado'
                    """, [cart_id])
                cart = cursor.fetchone()
                if not cart:
                    conn.rollback()
                    return False, 'Carrito no encontrado o no está en pago aprobado', None

                id_sucursal, id_punto_venta, id_deposito, total, subtotal = cart[0], cart[1], cart[2], cart[3], cart[4]
                kiosk_id = cart[5]
                monto_descuento_voucher = float(cart[6]) if len(cart) > 6 and cart[6] is not None else 0.0

                # 2. Obtener ítems con todos los campos necesarios para stock (réplica TPV VB6), incl. promoción y series
                try:
                    cursor.execute("""
                        SELECT id_articulo, cantidad, importe_total, importe_iva,
                               precio_unitario, COALESCE(alicuota_iva, 0), COALESCE(orden, 0),
                               COALESCE(codigo_articulo, ''), COALESCE(descripcion, ''),
                               COALESCE(porcentaje_descuento, 0),
                               COALESCE(NULLIF(TRIM(promocion), ''), 'No'),
                               COALESCE(promocion_por, 0), COALESCE(promocion_tipo, ''), COALESCE(promocion_cant, 0),
                               id, COALESCE(NULLIF(TRIM(serie), ''), 'No'), COALESCE(desc_serie, '')
                        FROM self_checkout_cart_item WHERE cart_id = %s
                    """, [cart_id])
                except Exception:
                    try:
                        cursor.execute("""
                            SELECT id_articulo, cantidad, importe_total, importe_iva,
                                   precio_unitario, COALESCE(alicuota_iva, 0), COALESCE(orden, 0),
                                   COALESCE(codigo_articulo, ''), COALESCE(descripcion, ''),
                                   COALESCE(porcentaje_descuento, 0)
                            FROM self_checkout_cart_item WHERE cart_id = %s
                        """, [cart_id])
                    except Exception:
                        cursor.execute("""
                            SELECT id_articulo, cantidad, importe_total, importe_iva,
                                   precio_unitario, COALESCE(alicuota_iva, 0), COALESCE(orden, 0),
                                   COALESCE(codigo_articulo, ''), COALESCE(descripcion, '')
                            FROM self_checkout_cart_item WHERE cart_id = %s
                        """, [cart_id])
                items = cursor.fetchall()

                if not items:
                    conn.rollback()
                    return False, 'Carrito vacío', None

                # 3. Revalidar stock: DISPONIBLE con UPDATE condicional (dentro de transacción)
                for row in items:
                    id_art, cant = row[0], row[1]
                    cursor.execute("""
                        UPDATE stock_deposito
                        SET saldo = saldo - %s
                        WHERE id_articulo = %s AND id_deposito = %s
                          AND (COALESCE(saldo, 0) - COALESCE(saldo_pedido_cliente, 0)) >= %s
                    """, [float(cant), id_art, id_deposito, float(cant)])
                    if cursor.rowcount == 0:
                        conn.rollback()
                        disp = self.stock_service.get_disponible(id_art, id_deposito)
                        logger.warning(
                            'STOCK_INSUFFICIENT al confirmar: cart_id=%s id_articulo=%s cantidad=%s disponible=%s',
                            cart_id, id_art, float(cant), float(disp),
                        )
                        return False, f'Stock insuficiente artículo {id_art}. Disponible: {disp}', None

                # 4. Obtener CodigoMovimiento (codmov) — VB6: +2 si activ_contabilidad, +1 si no (TPV.frm 8465-8470)
                cursor.execute("SELECT CodigoMovimiento FROM codmov WHERE codigo = 1 FOR UPDATE")
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return False, 'Error en codmov', None
                incremento = 1
                try:
                    cursor.execute("SELECT activ_contabilidad FROM configuracion LIMIT 1")
                    rcfg = cursor.fetchone()
                    if rcfg and (rcfg[0] or '').strip() == 'Si':
                        incremento = 2
                except Exception:
                    pass
                contador = row[0] + incremento
                cursor.execute("UPDATE codmov SET CodigoMovimiento = %s WHERE codigo = 1", [contador])

                # 5. Obtener y reservar NroComprobante (talonarios)
                # Igual que VB6 TPV: talonarios.Nro = próximo número a usar (no "último usado").
                # RecuperaLastCMP + 1 = próximo AFIP; validamos talonarios.Nro = próximo AFIP; luego Nro = Nro + 1.
                cursor.execute("""
                    SELECT Nro FROM talonarios
                    WHERE id_punto_venta = %s AND TipoComprobante = %s
                    LIMIT 1 FOR UPDATE
                """, [id_punto_venta, tipo_comprobante])
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return False, 'Talonario no configurado', None
                nro_actual = row[0] or 0
                # VB6: próximo a usar = talonarios.Nro (no Nro+1)
                proximo_local = nro_actual

                if is_fe_configured(self.base_empresa):
                    ultimo_afip, err_afip = get_ultimo_autorizado_afip(
                        self.base_empresa, id_punto_venta, tipo_comprobante
                    )
                    if err_afip is None and ultimo_afip is not None:
                        proximo_afip = ultimo_afip + 1
                        if proximo_local != proximo_afip:
                            conn.rollback()
                            # Sincronizar: poner talonarios.Nro = ARCA próximo (como en VB6)
                            return False, (
                                'No coincide el Nro. de talonario con el de ARCA. '
                                'Talonario próximo: %s, ARCA próximo: %s. Sincronice numeración en administraNET: '
                                'en la tabla talonarios (PV y tipo de este comprobante) poner Nro = %s (valor ARCA próximo). '
                                'Ver docs/sync_talonario_arca.sql.'
                            ) % (proximo_local, proximo_afip, proximo_afip), None
                    # Si AFIP no respondió (err_afip), seguimos con talonario; la solicitud de CAE fallará luego si hay desfase.

                nro_comp = str(proximo_local).zfill(8)
                # VB6: después de usar Nro, guardar próximo = Nro + 1
                cursor.execute("""
                    UPDATE talonarios SET Nro = Nro + 1
                    WHERE id_punto_venta = %s AND TipoComprobante = %s
                """, [id_punto_venta, tipo_comprobante])

                # 5b. Vendedor: si se pasó cod_viajante (TPV selección en pantalla), usarlo; si no, del kiosco
                if cod_viajante is None:
                    try:
                        cursor.execute(
                            "SELECT cod_viajante FROM self_checkout_kiosk WHERE kiosk_id = %s",
                            [kiosk_id],
                        )
                        row_v = cursor.fetchone()
                        if row_v and row_v[0] is not None:
                            cod_viajante = row_v[0]
                    except Exception:
                        pass

                # 5c. Saldo cliente (TPV VB6: rs_cuentacliente.Fields!Saldo) — para paridad con TPV
                saldo_cliente = 0.0
                try:
                    cursor.execute(
                        "SELECT COALESCE(saldo, 0) FROM cliente WHERE codigo = %s",
                        [id_cliente],
                    )
                    row_s = cursor.fetchone()
                    if row_s is not None:
                        saldo_cliente = float(row_s[0] or 0)
                except Exception:
                    pass

                # 5d. Total costo comprobante (TPV: Obtener_Total_Costo_Comprobante_Temporal) — suma costo×cant por ítem
                total_costo_comp = 0.0
                try:
                    for it in items:
                        cursor.execute(
                            "SELECT COALESCE(PrecioCosto, 0) FROM articulo WHERE IDArt = %s",
                            [it[0]],
                        )
                        r = cursor.fetchone()
                        costo_u = float(r[0] or 0) if r else 0
                        total_costo_comp += costo_u * float(it[1] or 0)
                except Exception:
                    pass

                # Totales IVA/subtotales para cuentacliente (alineado TPV: Iva1, Subtotal1, SubtotalGral, PorDesc1, etc.)
                total_f = float(total or 0)
                subtotal_f = float(subtotal or 0)
                pordesc1_f = monto_descuento_voucher
                impdesc1_f = subtotal_f * (pordesc1_f / 100.0) if pordesc1_f else 0.0
                subtotal_desc_f = subtotal_f - impdesc1_f  # debe coincidir con total_f si el único descuento es al pie
                iva1_f = total_f - subtotal_desc_f  # IVA implícito en total (neto con descuento al pie)
                iva2_f = 0.0
                alicuota1_f = 21.0  # por defecto; TPV usa Alic1 del formulario
                alicuota2_f = 0.0
                exento_f = 0.0
                subtotal1_f = subtotal_f
                subtotal2_f = 0.0
                subtotal_gral_f = total_f
                impdesc2_f = 0.0
                subtotaldesc1_f = subtotal_desc_f
                subtotaldesc2_f = 0.0

                # 6. INSERT cuentacliente — todos los campos que graba TPV VB6 (TPV.frm ~8985-9454)
                # Medios de cobro TPV: soporta pago único o mixto (efectivo + tarjeta + intereses). Si no envía ninguno, default = tarjeta = total.
                if tpv_importe_efectivo is None and tpv_importe_tarjeta is None:
                    tpv_imp_efectivo = 0.0
                    tpv_imp_tarjeta = total_f
                else:
                    ok_sum, err_sum = evaluar_suma_medios_pago(
                        total_f, tpv_importe_efectivo, tpv_importe_tarjeta, tpv_intereses
                    )
                    if not ok_sum:
                        conn.rollback()
                        return False, err_sum, None
                    tpv_imp_efectivo = float(tpv_importe_efectivo) if tpv_importe_efectivo is not None else 0.0
                    tpv_imp_tarjeta = float(tpv_importe_tarjeta) if tpv_importe_tarjeta is not None else 0.0
                tpv_imp_cheque = 0.0
                tpv_imp_ctacte = 0.0
                tpv_pago_ef = float(tpv_pago_efectivo) if tpv_pago_efectivo is not None else None
                tpv_cambio_ef = float(tpv_cambio_efectivo) if tpv_cambio_efectivo is not None else None
                fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                fecha_date = datetime.now().strftime('%Y-%m-%d')
                cursor.execute("""
                    INSERT INTO cuentacliente (
                        CodigoMovimiento, NroComprobante, NroCompBusq, TipoComprobante, Fecha,
                        Codigo, CodSucursal, id_pv, ReciboMov, ImporteVenta, ImporteVentaL, ImporteCobro,
                        Saldo, Iva1, Iva2, Alicuota1, alicuota2, Exento, anulado,
                        Subtotal1, Subtotal2, SubtotalGral, PorDesc1, ImpDesc1, ImpDesc2,
                        SubTotalDesc1, SubTotalDesc2, SubtotalDesc,
                        idUsuario, TipoFactura, Detalle,
                        CondVenta, id_condventa, Vencimiento, Vencido, Estado,
                        tpv_comp, tpv_importe_efectivo, tpv_importe_tarjeta, tpv_importe_cheque, tpv_importe_ctacte,
                        tpv_pago_efectivo, tpv_cambio_efectivo,
                        tpv_mail_ocasional, codViajante, id_vendedor_asistente,
                        impuesto_interno_total, total_percep, id_deposito_despacho, CotiDolar, total_costo
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, NULL, NULL,
                        %s, %s, %s, %s, %s, %s, 'No',
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, 'Sistema', '',
                        'Contado', 1, %s, 'No', 'Canc',
                        'Si', %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, 0,
                        0, 0, %s, 0, %s
                    )
                """, [
                    contador, nro_comp, nro_comp, tipo_comprobante, fecha,
                    id_cliente, id_sucursal, id_punto_venta, total_f,
                    saldo_cliente, iva1_f, iva2_f, alicuota1_f, alicuota2_f, exento_f,
                    subtotal1_f, subtotal2_f, subtotal_gral_f, pordesc1_f, impdesc1_f, impdesc2_f,
                    subtotaldesc1_f, subtotaldesc2_f, subtotal_desc_f,
                    id_usuario_final,
                    fecha_date,
                    tpv_imp_efectivo, tpv_imp_tarjeta, tpv_imp_cheque, tpv_imp_ctacte,
                    tpv_pago_ef if tpv_pago_ef is not None else 0.0,
                    tpv_cambio_ef if tpv_cambio_ef is not None else 0.0,
                    email or None, cod_viajante,
                    id_deposito, total_costo_comp,
                ])
                id_cuentacliente = cursor.lastrowid

                # 7. INSERT stock por cada ítem — persistencia fiel al TPV VB6 (TPV.frm ~9652-9905)
                # Todos los campos que el TPV asigna para que administraNET y procesos downstream no se rompan.
                nro_comprobante_stock = f"{id_punto_venta:04d}-{nro_comp}"
                id_usuario_stock = id_usuario_final  # Usuario logueado (session) o 0 si kiosk sin usuario
                for item in items:
                    (id_art, cant, imp_total, imp_iva, precio_unitario, alicuota_iva, orden_item,
                     codigo_articulo_item, descripcion_item, pordesc_item) = (
                        item[0], float(item[1]), float(item[2] or 0), float(item[3] or 0),
                        float(item[4] or 0), float(item[5] or 0), int(item[6] or 0),
                        (item[7] or ""), (item[8] or ""), float(item[9] or 0) if len(item) > 9 else 0.0,
                    )
                    promocion_stock = (item[10] or 'No') if len(item) > 10 else 'No'
                    promocion_por_stock = float(item[11] or 0) if len(item) > 11 else 0.0
                    promocion_tipo_stock = (item[12] or '') if len(item) > 12 else ''
                    promocion_cant_stock = float(item[13] or 0) if len(item) > 13 else 0.0
                    cart_item_id = item[14] if len(item) > 14 else None
                    serie_item = ((item[15] or '').strip() == 'Si') if len(item) > 15 else False
                    desc_serie_item = (item[16] or '') if len(item) > 16 else ''
                    cursor.execute(
                        "SELECT saldo FROM stock_deposito WHERE id_articulo = %s AND id_deposito = %s",
                        [id_art, id_deposito],
                    )
                    saldo_row = cursor.fetchone()
                    saldo_stock = float(saldo_row[0]) if saldo_row and saldo_row[0] is not None else 0.0
                    # Articulo: todos los campos que el TPV usa en stock. imp_alicuota_iva/imp_alicuota_iibb = porcentajes (21, 3.5).
                    # En administraNET articulo.Alicuota puede ser id -> iva; el porcentaje está en iva.Alicuota.
                    try:
                        cursor.execute("""
                            SELECT a.id_manual, a.NombreArticulo, COALESCE(a.PrecioCosto, 0),
                                   COALESCE(a.Alicuota, 0), COALESCE(a.AlicuotaIB, 0),
                                   COALESCE(NULLIF(TRIM(a.tipoIVA), ''), 'Gravado'),
                                   COALESCE(a.CodLaboratorio, 0), COALESCE(NULLIF(TRIM(a.Lote), ''), 'No'),
                                   COALESCE(iva.Alicuota, a.Alicuota, 0)
                            FROM articulo a
                            LEFT JOIN iva ON iva.id = a.Alicuota
                            WHERE a.IDArt = %s
                        """, [id_art])
                        art_row = cursor.fetchone()
                    except Exception:
                        cursor.execute("""
                            SELECT id_manual, NombreArticulo, COALESCE(PrecioCosto, 0), COALESCE(Alicuota, 0),
                                   COALESCE(AlicuotaIB, 0), COALESCE(NULLIF(TRIM(tipoIVA), ''), 'Gravado'),
                                   COALESCE(CodLaboratorio, 0), COALESCE(NULLIF(TRIM(Lote), ''), 'No'),
                                   COALESCE(Alicuota, 0)
                            FROM articulo WHERE IDArt = %s
                        """, [id_art])
                        art_row = cursor.fetchone()
                    if not art_row:
                        art_row = ("", "", 0.0, 0.0, 0.0, "Gravado", 0, "No", 0.0)
                    if len(art_row) < 9:
                        art_row = tuple(list(art_row) + [float(art_row[3] or 0)])
                    (id_manual, nombre_art, precio_costo, alicuota_art, alicuota_ib_art,
                     tipo_iva_art, cod_lab, lote_art, alic_iva_pct) = art_row
                    id_manual = id_manual or ""
                    nombre_art = nombre_art or descripcion_item or ""
                    precio_costo = float(precio_costo or 0)
                    alicuota_art = float(alicuota_art or 0)
                    alicuota_ib_art = float(alicuota_ib_art or 0)
                    tipo_iva_art = (tipo_iva_art or "Gravado").strip() or "Gravado"
                    cod_lab = int(cod_lab or 0)
                    codigo_art = (codigo_articulo_item or id_manual).strip()
                    desc_art = (descripcion_item or nombre_art).strip()
                    cant_f = float(cant)
                    if cant_f <= 0:
                        cant_f = 1.0
                    # Orígenes TPV VB6: renglón (data_renglon_tpv). Kiosk: cart_item + articulo.
                    # Neto/bruto: importe_total del ítem = total con IVA (bruto); neto = total - importe_iva.
                    imp_iva_f = imp_iva or 0.0
                    precio_bruto_r = imp_total or 0.0  # total renglón con IVA (TPV: PrecioBrutoxR)
                    precio_neto_r = precio_bruto_r - imp_iva_f  # neto renglón (TPV: PrecioNetoxR)
                    precio_iva_u = imp_iva_f / cant_f if cant_f else 0.0
                    precio_neto_u = precio_neto_r / cant_f if cant_f else 0.0
                    precio_bruto_u = precio_bruto_r / cant_f if cant_f else 0.0
                    precio_venta_u = precio_unitario or precio_neto_u  # precio venta unitario (neto)
                    precio_venta_r = precio_neto_r  # venta total = neto (TPV: PrecioVentaxR = neto)
                    precio_costo_r = precio_costo * cant_f
                    alic_iva = alicuota_iva or alicuota_art
                    # imp_alicuota_iva e imp_alicuota_iibb = porcentajes (21, 3.5), no importes. Origen: iva.Alicuota / articulo.Alicuota, articulo.AlicuotaIB
                    imp_alic_iva = float(alic_iva_pct) if alic_iva_pct is not None else (alic_iva or 0.0)
                    imp_alic_iibb = float(alicuota_ib_art or 0.0)
                    pordesc = pordesc_item  # TPV: data_renglon_tpv.Pordesc (descuento por renglón)
                    neto_antes_desc = cant_f * float(precio_unitario or 0)
                    imp_desc = neto_antes_desc * (pordesc / 100.0) if pordesc else 0.0  # TPV: Impdesc
                    # Comprobante = TipoFactura (FA/FB); NroComprobante = PV-Nro; anulado = 'No'; idUsuario = 0 (kiosk)
                    serie_stock = 'Si' if serie_item else 'No'
                    desc_serie_stock = (desc_serie_item or '')[:500] if serie_item else ''
                    params_stock = [
                        contador, id_art, cant_f, cant_f, id_deposito,
                        fecha_date, codigo_art, desc_art,
                        precio_venta_u, precio_costo, precio_iva_u, precio_bruto_u, precio_neto_u,
                        imp_desc, pordesc,
                        precio_venta_r, precio_costo_r, imp_iva_f, precio_bruto_r, precio_neto_r,
                        alic_iva, alicuota_ib_art, imp_alic_iva, imp_alic_iibb,
                        saldo_stock, orden_item, cod_viajante, cod_lab, desc_art,
                        tipo_comprobante, nro_comprobante_stock,
                        id_cliente, id_sucursal, id_usuario_stock, tipo_iva_art,
                        promocion_stock, promocion_por_stock, promocion_tipo_stock, promocion_cant_stock,
                        id_manual,
                    ]
                    try:
                        cursor.execute("""
                            INSERT INTO stock (
                                CodigoMovimiento, IDArt, Cantidad, Entrada, Salida, CodDeposito,
                                Fecha, CodigoArticulo, Descripcion,
                                PrecioVentaxU, PrecioCostoxU, PrecioIVAxU, PrecioBrutoxU, PrecioNetoxU,
                                Impdesc, Pordesc,
                                PrecioVentaxR, PrecioCostoxR, PrecioIVAxR, PrecioBrutoxR, PrecioNetoxR,
                                Alicuota, AlicuotaIB, imp_alicuota_iva, imp_alicuota_iibb,
                                Saldo, orden, CodViajante, CodLaboratorio, Detalle,
                                TipoComp, Comprobante, NroComprobante, anulado,
                                Tipo, CodigoCP, codSucursal, idUsuario, TipoIVA,
                                Lista_Precio, promocion, promocion_por, promocion_tipo, promocion_cant,
                                impuesto_interno, impuesto_interno_subtotal,
                                tipo_unidad, cantidad_unidad_display, cantidad_dividir,
                                multiplicador_vta, multiplicador_comp, visualiza_ensamble, id_manual,
                                serie, desc_serie
                            ) VALUES (
                                %s, %s, %s, 0, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s, %s, %s,
                                %s, %s,
                                %s, %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s, %s, %s,
                                'Venta Self Checkout', %s, %s, 'No',
                                'Cliente', %s, %s, %s, %s,
                                1, %s, %s, %s, %s,
                                0, 0,
                                'Unidad', 1, 1,
                                1, 1, 'No', %s,
                                %s, %s
                            )
                        """, params_stock + [serie_stock, desc_serie_stock])
                    except Exception as e_stock:
                        if 'Unknown column' in str(e_stock) and 'serie' in str(e_stock).lower():
                            cursor.execute("""
                                INSERT INTO stock (
                                    CodigoMovimiento, IDArt, Cantidad, Entrada, Salida, CodDeposito,
                                    Fecha, CodigoArticulo, Descripcion,
                                    PrecioVentaxU, PrecioCostoxU, PrecioIVAxU, PrecioBrutoxU, PrecioNetoxU,
                                    Impdesc, Pordesc,
                                    PrecioVentaxR, PrecioCostoxR, PrecioIVAxR, PrecioBrutoxR, PrecioNetoxR,
                                    Alicuota, AlicuotaIB, imp_alicuota_iva, imp_alicuota_iibb,
                                    Saldo, orden, CodViajante, CodLaboratorio, Detalle,
                                    TipoComp, Comprobante, NroComprobante, anulado,
                                    Tipo, CodigoCP, codSucursal, idUsuario, TipoIVA,
                                    Lista_Precio, promocion, promocion_por, promocion_tipo, promocion_cant,
                                    impuesto_interno, impuesto_interno_subtotal,
                                    tipo_unidad, cantidad_unidad_display, cantidad_dividir,
                                    multiplicador_vta, multiplicador_comp, visualiza_ensamble, id_manual
                                ) VALUES (
                                    %s, %s, %s, 0, %s, %s,
                                    %s, %s, %s,
                                    %s, %s, %s, %s, %s,
                                    %s, %s,
                                    %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s,
                                    'Venta Self Checkout', %s, %s, 'No',
                                    'Cliente', %s, %s, %s, %s,
                                    1, %s, %s, %s, %s,
                                    0, 0,
                                    'Unidad', 1, 1,
                                    1, 1, 'No', %s
                                )
                            """, params_stock)
                        else:
                            raise
                    id_stock = cursor.lastrowid
                    # GuardarSerie (TPV VB6): serie_movimiento + serie_entrada.disponible = 'No'
                    if serie_item and cart_item_id and id_stock:
                        try:
                            cursor.execute("""
                                SELECT id_serie_entrada, nro_serie, desc_serie, vto_serie
                                FROM self_checkout_cart_item_serie WHERE cart_item_id = %s ORDER BY id
                            """, [cart_item_id])
                            series_rows = cursor.fetchall()
                        except Exception:
                            series_rows = []
                        for srow in series_rows:
                            id_se = srow[0]
                            nro_s = (srow[1] or '') if len(srow) > 1 else ''
                            desc_s = (srow[2] or '') if len(srow) > 2 else ''
                            vto_s = srow[3] if len(srow) > 3 else None
                            fecha_serie = datetime.now().strftime('%Y-%m-%d')
                            try:
                                cursor.execute("""
                                    INSERT INTO serie_movimiento (
                                        anulado, codigo_mov_vta, desc_serie, fecha, id_articulo,
                                        nro_serie, tipo_comprobante, vto_serie, id_serie_entrada, tipo_comp_desc,
                                        id_cliente, comprobante, nro_comprobante, modificado, id_stock, id_deposito
                                    ) VALUES (
                                        'No', %s, %s, %s, %s, %s, %s, %s, %s, 'Factura Venta',
                                        %s, %s, %s, 'No', %s, %s
                                    )
                                """, [
                                    contador, desc_s, fecha_serie, id_art, nro_s, tipo_comprobante, vto_s, id_se,
                                    id_cliente, tipo_comprobante, nro_comp, id_stock, id_deposito,
                                ])
                            except Exception as e_serie:
                                if "doesn't exist" in str(e_serie):
                                    break
                                raise
                        if series_rows:
                            ids_se = [r[0] for r in series_rows]
                            placeholders = ','.join(['%s'] * len(ids_se))
                            try:
                                cursor.execute(
                                    "UPDATE serie_entrada SET disponible = 'No' WHERE id_serie_entrada IN (" + placeholders + ")",
                                    ids_se,
                                )
                            except Exception as e_up:
                                if "doesn't exist" in str(e_up):
                                    pass
                                else:
                                    raise

                # 7b. INSERT resumen_venta_cv — paridad literal con TPV VB6 Guardar_resumen_venta_cv (Factura TPV)
                # TPV.frm ~10311-10314: Comprobante = 'Factura TPV', Total_Efectivo, Total_CtaCte, Total_Tarjeta, Total_Cheque
                try:
                    cursor.execute("""
                        INSERT INTO resumen_venta_cv (
                            Fecha, id_cliente, codigo_movimiento, tipo_comp, Comprobante, importe_neto, nro_comprobante,
                            importe_iva_1, importe_iva_2, importe_percep, importe_impuesto_interno, Importe_Interes,
                            importe_exento, importe_total, Total_Efectivo, Total_CtaCte, Total_Tarjeta, Total_Cheque
                        ) VALUES (
                            %s, %s, %s, %s, 'Factura TPV', %s, %s, %s, %s, 0, 0, 0, %s, %s, %s, 0, %s, 0
                        )
                    """, [
                        fecha_date, id_cliente, contador, tipo_comprobante, subtotal_desc_f, nro_comp,
                        iva1_f, iva2_f, exento_f, total_f, tpv_imp_efectivo, tpv_imp_tarjeta,
                    ])
                except Exception as e_rv:
                    if "doesn't exist" in str(e_rv) or "Unknown column" in str(e_rv):
                        logger.warning("resumen_venta_cv no insertado (tabla/columnas pueden no existir): %s", e_rv)
                    else:
                        raise

                # 7c. INSERT tc_comprobante — paridad TPV VB6 cuando hay tarjeta (TPV.frm 10054-10081)
                # Registra detalle: tarjeta, plan, cuotas, nro tarjeta, nro cupón, nro lote, intereses, valor cuota, importe parcial
                if tpv_imp_tarjeta > 0:
                    try:
                        nom_tc = (tpv_tarjeta_nombre or 'Tarjeta').strip() or 'Mercado Pago'
                        nom_plan = (tpv_plan_nombre or 'Plan').strip() or 'Mercado Pago'
                        id_tc_ins, id_tc_plan_ins = _lookup_tarjeta_ids_tc_comprobante(cursor, nom_tc, nom_plan)
                        cuotas_val = int(tpv_cuotas) if tpv_cuotas is not None else 1
                        interes_val = float(tpv_intereses) if tpv_intereses is not None else 0.0
                        imp_con_interes = tpv_imp_tarjeta + interes_val
                        valor_cuota_val = float(tpv_valor_cuota) if tpv_valor_cuota is not None and tpv_valor_cuota > 0 else (imp_con_interes / cuotas_val if cuotas_val > 0 else tpv_imp_tarjeta)
                        imp_parcial_val = float(tpv_importe_parcial) if tpv_importe_parcial is not None else 0.0
                        nro_tarjeta_val = (tpv_nro_tarjeta or '').strip() or '0'
                        nro_cupon_val = (tpv_nro_cupon or '').strip() or '0'
                        nro_lote_val = (tpv_nro_lote or '').strip() or '0'
                        cursor.execute(
                            """
                            INSERT INTO tc_comprobante (
                                nombre_tc_comprobante, nombre_plan_tc_comprobante,
                                id_tc, id_tc_plan,
                                cuotas_tc_comprobante, interes_tc_comprobante, descuento_tc_comprobante,
                                nro_tarjeta_tc_comprobante, nro_cupon_tc_comprobante, nro_lote_tc,
                                importe_tc_comprobante, importe_cuota, importe_con_interes,
                                codigo_movimiento
                            ) VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            [
                                nom_tc, nom_plan, id_tc_ins, id_tc_plan_ins,
                                cuotas_val, round(interes_val, 2),
                                nro_tarjeta_val, nro_cupon_val, nro_lote_val,
                                round(tpv_imp_tarjeta, 2), round(valor_cuota_val, 2), round(imp_con_interes, 2),
                                contador,
                            ],
                        )
                    except Exception as e_tc:
                        if "doesn't exist" in str(e_tc) or "Unknown column" in str(e_tc):
                            # Fallback: schema puede no tener todas las columnas
                            try:
                                nom_fb = (tpv_tarjeta_nombre or 'Mercado Pago').strip() or 'Mercado Pago'
                                nom_plan_fb = (tpv_plan_nombre or 'Mercado Pago').strip() or 'Mercado Pago'
                                id_tc_fb, id_tc_plan_fb = _lookup_tarjeta_ids_tc_comprobante(cursor, nom_fb, nom_plan_fb)
                                cursor.execute(
                                    """
                                    INSERT INTO tc_comprobante (
                                        nombre_tc_comprobante, nombre_plan_tc_comprobante,
                                        id_tc, id_tc_plan,
                                        importe_tc_comprobante, importe_cuota, importe_con_interes,
                                        codigo_movimiento
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                    """,
                                    [
                                        nom_fb, nom_plan_fb, id_tc_fb, id_tc_plan_fb,
                                        round(tpv_imp_tarjeta, 2), round(tpv_imp_tarjeta, 2), round(tpv_imp_tarjeta, 2),
                                        contador,
                                    ],
                                )
                            except Exception as e_tc2:
                                logger.warning("tc_comprobante no insertado: %s", e_tc2)
                        else:
                            raise

                # 8. UPDATE carrito
                cursor.execute("""
                    UPDATE self_checkout_cart SET
                        estado = 'confirmado',
                        codigo_movimiento = %s,
                        id_cuentacliente = %s,
                        tipo_comprobante = %s,
                        id_cliente = %s,
                        email = %s,
                        confirmed_at = NOW()
                    WHERE id = %s
                """, [contador, id_cuentacliente, tipo_comprobante, id_cliente, email or None, cart_id])

                # 9. Audit log (trazabilidad con correlation_id)
                detalle = json.dumps({
                    'correlation_id': correlation_id,
                    'cart_id': cart_id,
                    'codigo_movimiento': contador,
                    'nro_comprobante': nro_comp,
                    'id_cuentacliente': id_cuentacliente,
                })
                cursor.execute("""
                    SELECT kiosk_id, id_sucursal, id_punto_venta FROM self_checkout_cart WHERE id = %s
                """, [cart_id])
                krow = cursor.fetchone()
                kiosk_id, ids, idpv = krow[0], krow[1], krow[2]
                cursor.execute("""
                    INSERT INTO self_checkout_audit_log (kiosk_id, id_sucursal, id_punto_venta, cart_id, accion, detalle)
                    VALUES (%s, %s, %s, %s, 'confirmado', %s)
                """, [kiosk_id, ids, idpv, cart_id, detalle])

                # FE: si está configurado, obtener CAE/CAEA antes de commit. Si falla → no finalizar venta.
                result = {
                    'codigo_movimiento': contador,
                    'id_cuentacliente': id_cuentacliente,
                    'nro_comprobante': nro_comp,
                    'tipo_comprobante': tipo_comprobante,
                    'id_punto_venta': id_punto_venta,
                    'total': total,
                    'subtotal': subtotal,
                }
                if is_fe_configured(self.base_empresa):
                    inv_svc = InvoiceService(self.base_empresa)
                    estado_fe, cae, vto_cae, err_detail = inv_svc.emitir_fe(
                        cart_id=cart_id,
                        id_cuentacliente=id_cuentacliente,
                        codigo_movimiento=contador,
                        tipo_comprobante=tipo_comprobante,
                        nro_comprobante=nro_comp,
                        id_punto_venta=id_punto_venta,
                        total=Decimal(str(total or 0)),
                        subtotal=Decimal(str(subtotal or 0)),
                        id_cliente=id_cliente,
                        cuit=cuit,
                    )
                    if estado_fe == 'failed':
                        conn.rollback()
                        msg = (err_detail or {}).get('msg', 'No se pudo obtener CAE/CAEA') if isinstance(err_detail, dict) else 'No se pudo obtener CAE/CAEA'
                        logger.warning('FE failed antes de commit: cart_id=%s %s', cart_id, msg)
                        return False, msg, None
                    else:
                        fe_reg = 'CAE' if estado_fe == 'issued_cae' else ('CAEA' if estado_fe in ('issued_caea_pending', 'sent') else None)
                        fe_comp = 'Si'
                        fe_transmitido = 'Si' if estado_fe in ('issued_cae', 'sent') else 'No'
                        vto_sql = vto_cae if vto_cae else None
                        cursor.execute("""
                            UPDATE cuentacliente SET
                                fe_cae = COALESCE(%s, fe_cae),
                                fe_vto_cae = COALESCE(%s, fe_vto_cae),
                                fe_comp = %s,
                                fe_transmitido = %s,
                                fe_regimen_tipo = COALESCE(%s, fe_regimen_tipo)
                            WHERE id_cuentacliente = %s
                        """, [cae, vto_sql, fe_comp, fe_transmitido, fe_reg, id_cuentacliente])
                        result['estado_fe'] = estado_fe
                        result['cae'] = cae
                        result['vto_cae'] = vto_cae
                        result['fe_regimen'] = fe_reg

                # Caja dentro de transacción (paridad administraNET: si falla → rollback completo)
                try:
                    from mercadopago.services.payment_service import (
                        get_config_for_kiosk,
                        write_caja_ingreso_with_cursor,
                    )
                    config = get_config_for_kiosk(self.base_empresa, kiosk_id or '')
                    if config and config.id_caja_abm and id_sucursal is not None:
                        id_caja = config.id_caja_abm
                        id_usr = getattr(config, 'id_usuario_autoservicio', None) or id_usuario_final
                        cod_vend = getattr(config, 'cod_vendedor_autoservicio', None)
                        nro_comp_str = nro_comp
                        if tpv_imp_efectivo > 0:
                            write_caja_ingreso_with_cursor(
                                cursor, id_caja, contador, tpv_imp_efectivo, id_sucursal,
                                tipo='Factura Contado TPV', nro_comprobante=nro_comp_str,
                                codigo_cliente=id_cliente, tipo_comprobante=tipo_comprobante,
                                id_usuario=id_usr if id_usr else None, cod_vendedor=cod_vend,
                            )
                        if tpv_imp_tarjeta > 0:
                            write_caja_ingreso_with_cursor(
                                cursor, id_caja, contador, tpv_imp_tarjeta, id_sucursal,
                                tipo='Tarjeta', nro_comprobante=nro_comp_str,
                                codigo_cliente=id_cliente, tipo_comprobante=tipo_comprobante,
                                id_usuario=id_usr if id_usr else None, cod_vendedor=cod_vend,
                            )
                except Exception as e_caja:
                    conn.rollback()
                    logger.warning('Caja (write_caja_ingreso) falló en transacción: %s', e_caja)
                    return False, 'Error al registrar movimiento de caja', None

                conn.commit()
                # Marcar voucher usado (programa de descuentos, como TPV VB6)
                try:
                    from .voucher_service import marcar_voucher_usado
                    with mysql_cursor(self.base_empresa, dict_cursor=True) as c2:
                        c2.execute("SELECT id_sp_cupon FROM self_checkout_cart WHERE id = %s", [cart_id])
                        r = c2.fetchone()
                        if r and r.get('id_sp_cupon'):
                            marcar_voucher_usado(self.base_empresa, int(r['id_sp_cupon']))
                except Exception as e2:
                    logger.debug("voucher_usado no aplicado (tabla/columna puede no existir): %s", e2)
                return True, None, result
            except Exception as e:
                conn.rollback()
                logger.exception('Error en confirmación')
                return False, str(e), None
            finally:
                conn.autocommit(True)
