"""
Recibo a cuenta (adelanto) por pedido Tiendanube pagado.

Paridad con ``json_recibo.php`` / ReciboCobro VB6: REC ``TipoRecibo='A Cuenta'``,
``recibo_factura`` con saldo a favor del cliente e ingreso en caja según medio.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict

from core.utils.administranet_types import to_int_or_none

from .order_payment import TiendanubeOrderPayment

logger = logging.getLogger(__name__)

MAX_CODMOV_RETRIES = 12


def _float(value: Decimal | float | int) -> float:
    return float(Decimal(str(value)))


def allocate_codigo_movimiento(cursor, max_retries: int = MAX_CODMOV_RETRIES) -> int:
    """Reserva ``CodigoMovimiento`` global (tabla ``codmov``)."""
    for _ in range(max_retries):
        cursor.execute(
            """
            SELECT CodigoMovimiento + 1 AS nuevo, CodigoMovimiento AS viejo
            FROM codmov WHERE codigo = 1
            """
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError('No existe fila codigo=1 en tabla codmov.')
        nuevo = int(row['nuevo'])
        viejo = int(row['viejo'])
        cursor.execute(
            """
            UPDATE codmov SET CodigoMovimiento = %s
            WHERE codigo = 1 AND CodigoMovimiento = %s
            """,
            (nuevo, viejo),
        )
        if cursor.rowcount == 1:
            return nuevo
    raise RuntimeError('No se pudo reservar CodigoMovimiento tras reintentos.')


def allocate_nro_recibo(cursor, punto_venta_id: int) -> tuple[str, int]:
    """Obtiene número REC desde ``talonarios`` (formato XXXX-XXXXXXXX)."""
    cursor.execute(
        """
        SELECT PV, Nro FROM talonarios
        WHERE id_punto_venta = %s AND TipoComprobante = 'REC'
        LIMIT 1
        """,
        (punto_venta_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError(f'Sin talonario REC para punto de venta {punto_venta_id}.')
    pv = str(row['PV']).zfill(4)
    nro = int(row['Nro'])
    nro_recibo = f'{pv}-{str(nro).zfill(8)}'
    cursor.execute(
        """
        UPDATE talonarios SET Nro = Nro + 1
        WHERE id_punto_venta = %s AND TipoComprobante = 'REC'
        """,
        (punto_venta_id,),
    )
    if cursor.rowcount != 1:
        raise RuntimeError('No se pudo incrementar talonario REC.')
    return nro_recibo, nro


def _load_usuario(cursor, user_id: int) -> Dict[str, Any]:
    cursor.execute(
        """
        SELECT id_usuario, id_sucursal, id_punto_venta, CodViajante,
               id_caja, id_caja_tarjeta, id_caja_cheque
        FROM usuarios WHERE id_usuario = %s LIMIT 1
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError(f'Usuario AdministraNET {user_id} no encontrado.')
    return row


def _load_cliente_saldo(cursor, codigo_cliente: int) -> float:
    cursor.execute(
        'SELECT COALESCE(saldo, 0) AS saldo FROM cliente WHERE Codigo = %s LIMIT 1',
        (codigo_cliente,),
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError(f'Cliente {codigo_cliente} no encontrado.')
    return float(row['saldo'] or 0)


def _insert_caja_ingreso(
    cursor,
    *,
    tipo: str,
    tipo_comprobante: str,
    nro_comprobante: str,
    nro_comp_busq: int,
    ingreso: float,
    codigo_movimiento: int,
    codigo_cliente: int,
    id_caja: int,
    id_usuario: int,
    cod_sucursal: int,
    detalle: str,
) -> None:
    cursor.execute(
        'SELECT saldo FROM caja_saldo WHERE id_caja = %s LIMIT 1',
        (id_caja,),
    )
    caja_row = cursor.fetchone()
    saldo_caja = float(caja_row['saldo'] if caja_row else 0) + ingreso

    cursor.execute(
        """
        INSERT INTO caja (
            Fecha, tipo_comprobante, Tipo, nro_comprobante, nro_comp_busq,
            egreso, id_usuario, cod_sucursal, Moneda, ingreso, Detalle,
            Codigo_Movimiento, Codigo_Cliente, codigo_prov, tipo_cp, anulado,
            Saldo, id_caja_abm_origen
        ) VALUES (
            %s, %s, %s, %s, %s,
            0, %s, %s, 'Pesos', %s, %s,
            %s, %s, 1, 'Cliente', 'No',
            %s, %s
        )
        """,
        (
            date.today(),
            tipo_comprobante,
            tipo,
            nro_comprobante,
            nro_comp_busq,
            id_usuario,
            cod_sucursal,
            ingreso,
            detalle[:500] if detalle else '',
            codigo_movimiento,
            codigo_cliente,
            saldo_caja,
            id_caja,
        ),
    )
    if caja_row:
        cursor.execute(
            """
            UPDATE caja_saldo SET saldo = %s, id_usuario = %s, cod_sucursal = %s
            WHERE id_caja = %s
            """,
            (saldo_caja, id_usuario, cod_sucursal, id_caja),
        )


def registrar_adelanto_tiendanube(
    cursor,
    *,
    codigo_cliente: int,
    payment: TiendanubeOrderPayment,
    punto_venta_id: int,
    user_id: int,
    cod_viajante: int,
    pedido_nro: str,
    pedido_codmov: int,
    tiendanube_order_id: str,
) -> Dict[str, Any]:
    """
    Registra REC a cuenta + saldo a favor (``recibo_factura``) + caja.

    Debe ejecutarse dentro de la misma transacción MySQL que el alta del pedido.
    """
    total = payment.total
    if total <= 0:
        raise ValueError('Importe de adelanto inválido (total <= 0).')

    usuario = _load_usuario(cursor, user_id)
    cod_sucursal = int(usuario['id_sucursal'] or 1)
    id_pv = to_int_or_none(usuario.get('id_punto_venta')) or punto_venta_id
    cod_mov_rec = allocate_codigo_movimiento(cursor)
    nro_recibo, nro_comp_busq = allocate_nro_recibo(cursor, id_pv)

    saldo_cliente = _load_cliente_saldo(cursor, codigo_cliente)
    total_f = _float(total)
    saldo_cliente_nuevo = saldo_cliente - total_f

    total_efectivo = total_f if payment.medio_adminet == 'efectivo' else 0.0
    total_tarjeta = total_f if payment.medio_adminet == 'tarjeta' else 0.0
    total_transferencia = total_f if payment.medio_adminet == 'transferencia' else 0.0
    total_pago_rec = total_f

    detalle_rec = (
        f'TN #{tiendanube_order_id} PED {pedido_nro} '
        f'{payment.method_label} {payment.gateway_id or ""}'.strip()
    )

    cursor.execute(
        """
        INSERT INTO cuentacliente (
            Fecha, TipoComprobante, NroComprobante, NroCompBusq, id_pv,
            TipoREC, ImporteVentaL, Detalle, anulado, ReciboMov,
            ImporteCobro, ImporteVenta, CondVenta, idUsuario, codSucursal,
            Codigo, CodigoMovimiento, TipoRecibo, CotiDolar,
            ReciboPesos, ReciboDolar, TotalPago, TotalEfectivoP, TotalEfectivoD,
            TotalCheque, TotalImputacionRec, NetoImputacionRec, TotalPagoRec,
            TotalRecibo, TotalDescRec, TotalRetencion, Total_Tarjeta, Total_MC,
            Total_Ingreso, CodViajante, Saldo
        ) VALUES (
            %s, 'REC', %s, %s, %s,
            'Sistema', '-', 'TN-WEB', 'No', 0,
            %s, NULL, '-', %s, %s,
            %s, %s, 'A Cuenta', 1,
            %s, 0, %s, %s, 0,
            0, 0, 0, %s,
            %s, 0, 0, %s, 0,
            %s, %s, %s
        )
        """,
        (
            date.today(),
            nro_recibo,
            nro_comp_busq,
            id_pv,
            total_f,
            user_id,
            cod_sucursal,
            codigo_cliente,
            cod_mov_rec,
            total_efectivo,
            total_pago_rec,
            total_efectivo,
            total_pago_rec,
            total_f,
            total_tarjeta,
            total_f,
            cod_viajante or 0,
            saldo_cliente_nuevo,
        ),
    )

    cursor.execute(
        """
        UPDATE cliente SET saldo = %s WHERE Codigo = %s
        """,
        (saldo_cliente_nuevo, codigo_cliente),
    )

    cursor.execute(
        """
        INSERT INTO recibo_factura (
            Fecha, TipoComprobante, Importe, cancelado, Saldo, ImporteNC,
            NroComprobante, estado, CodigoMovimiento, Codigo, Imp, anulado,
            Modificado, Tipo, CodViajante
        ) VALUES (
            %s, 'REC', %s, 0, %s, %s,
            %s, 'N/Canc', %s, %s, 'No', 'No',
            'No', 'Cliente', %s
        )
        """,
        (
            date.today(),
            total_f,
            total_f,
            total_f,
            nro_recibo,
            cod_mov_rec,
            codigo_cliente,
            cod_viajante or 0,
        ),
    )

    cursor.execute(
        """
        INSERT INTO recibo_factura_par (
            cancelado, CanceladoActual, Saldo, estado, Imp, ReciboMov, Recibo,
            Fecha, TipoComprobante, Importe, NroComprobante, CodigoMovimiento,
            Codigo, ImporteNC, anulado, Modificado, seleccionado
        ) VALUES (
            0, 0, %s, 'N/Canc', 'Si', %s, %s,
            %s, 'REC', %s, %s, %s,
            %s, %s, 'No', 'No', 'No'
        )
        """,
        (
            total_f,
            cod_mov_rec,
            nro_recibo,
            date.today(),
            total_f,
            nro_recibo,
            cod_mov_rec,
            codigo_cliente,
            total_f,
        ),
    )

    id_caja_efectivo = to_int_or_none(usuario.get('id_caja'))
    id_caja_tarjeta = to_int_or_none(usuario.get('id_caja_tarjeta'))
    ref_pago = payment.gateway_id or nro_recibo

    if payment.medio_adminet == 'efectivo' and id_caja_efectivo:
        _insert_caja_ingreso(
            cursor,
            tipo='Cobranza Efectivo',
            tipo_comprobante='REC',
            nro_comprobante=nro_recibo,
            nro_comp_busq=nro_comp_busq,
            ingreso=total_f,
            codigo_movimiento=cod_mov_rec,
            codigo_cliente=codigo_cliente,
            id_caja=id_caja_efectivo,
            id_usuario=user_id,
            cod_sucursal=cod_sucursal,
            detalle=detalle_rec,
        )
    elif payment.medio_adminet == 'transferencia' and id_caja_efectivo:
        _insert_caja_ingreso(
            cursor,
            tipo='Transferencia',
            tipo_comprobante='REC',
            nro_comprobante=ref_pago[:50],
            nro_comp_busq=nro_comp_busq,
            ingreso=total_f,
            codigo_movimiento=cod_mov_rec,
            codigo_cliente=codigo_cliente,
            id_caja=id_caja_efectivo,
            id_usuario=user_id,
            cod_sucursal=cod_sucursal,
            detalle=detalle_rec,
        )
    elif id_caja_tarjeta:
        _insert_caja_ingreso(
            cursor,
            tipo='Tarjeta',
            tipo_comprobante='REC',
            nro_comprobante=ref_pago[:50],
            nro_comp_busq=nro_comp_busq,
            ingreso=total_f,
            codigo_movimiento=cod_mov_rec,
            codigo_cliente=codigo_cliente,
            id_caja=id_caja_tarjeta,
            id_usuario=user_id,
            cod_sucursal=cod_sucursal,
            detalle=detalle_rec,
        )
    elif id_caja_efectivo:
        logger.warning(
            'Sin caja tarjeta para usuario %s; adelanto TN ingresa en caja efectivo.',
            user_id,
        )
        _insert_caja_ingreso(
            cursor,
            tipo='Cobranza Efectivo',
            tipo_comprobante='REC',
            nro_comprobante=nro_recibo,
            nro_comp_busq=nro_comp_busq,
            ingreso=total_f,
            codigo_movimiento=cod_mov_rec,
            codigo_cliente=codigo_cliente,
            id_caja=id_caja_efectivo,
            id_usuario=user_id,
            cod_sucursal=cod_sucursal,
            detalle=detalle_rec,
        )
    else:
        logger.warning(
            'Usuario %s sin cajas configuradas; REC TN sin movimiento de caja.',
            user_id,
        )

    return {
        'codigo_movimiento_rec': cod_mov_rec,
        'nro_recibo': nro_recibo,
        'saldo_cliente_nuevo': saldo_cliente_nuevo,
        'pedido_codmov': pedido_codmov,
        'medio_adminet': payment.medio_adminet,
    }
