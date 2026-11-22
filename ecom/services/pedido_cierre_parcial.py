"""Cierre explícito de la parte pendiente de un PED parcialmente remitido."""

from collections import defaultdict
from decimal import Decimal
import logging

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_decimal_or_none, to_int_or_none

logger = logging.getLogger(__name__)


def cerrar_pedido_parcial(base_empresa: str, cod_mov: int, motivo: str) -> dict:
    """Cierra el PED y libera solo su pendiente; deja intactos REM y facturas.

    Bloquea pedido y reservas durante la operación. Si un artículo del PED sale de
    varios depósitos, exige resolución manual: el remito no indica inequívocamente
    a qué renglón del pedido imputar la entrega.
    """
    cod = to_int_or_none(cod_mov)
    motivo = (motivo or "").strip()
    if cod is None or not motivo or len(motivo) > 500:
        return {"ok": False, "error": "Indicá el pedido y un motivo de hasta 500 caracteres."}
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        try:
            conn.autocommit(False)
            cur = conn.cursor()
            cur.execute(
                "SELECT Estado, Anulado FROM comp_ped "
                "WHERE CodigoMovimiento=%s AND TipoComprobante='PED' FOR UPDATE",
                [cod],
            )
            cab = cur.fetchone()
            if not cab or str(cab[1]).strip().lower() != "no":
                raise ValueError("Pedido inexistente o anulado.")
            if str(cab[0]).strip().lower() in ("cerrado", "facturado"):
                raise ValueError("El pedido ya está cerrado o facturado.")
            cur.execute(
                "SELECT IDArt, Salida, CodDeposito FROM stockp "
                "WHERE CodigoMovimiento=%s AND Anulado='No' FOR UPDATE",
                [cod],
            )
            renglones = cur.fetchall() or []
            if not renglones:
                raise ValueError("El pedido no tiene renglones activos.")
            pedidos = defaultdict(lambda: Decimal("0"))
            depositos = defaultdict(set)
            for id_art, salida, deposito in renglones:
                art, dep = to_int_or_none(id_art), to_int_or_none(deposito)
                cantidad = to_decimal_or_none(salida) or Decimal("0")
                if art is None or dep is None or dep <= 0 or cantidad <= 0:
                    raise ValueError("El pedido contiene un renglón sin artículo, depósito o cantidad válida.")
                pedidos[(art, dep)] += cantidad
                depositos[art].add(dep)
            if any(len(ids) > 1 for ids in depositos.values()):
                raise ValueError("Un artículo usa varios depósitos; el cierre requiere revisión manual.")

            cur.execute(
                "SELECT s.IDArt, SUM(ABS(COALESCE(s.Salida,0))) FROM stock s "
                "JOIN comp_ped rem ON rem.CodigoMovimiento=s.codmov_remito "
                "WHERE s.codmov_pedido=%s AND rem.TipoComprobante='REM' "
                "AND COALESCE(s.Anulado,'No')='No' AND COALESCE(rem.Anulado,'No')='No' "
                "GROUP BY s.IDArt",
                [cod],
            )
            entregado = {
                int(art): to_decimal_or_none(qty) or Decimal("0")
                for art, qty in (cur.fetchall() or [])
            }
            if any(art not in depositos for art in entregado):
                raise ValueError("El remito contiene artículos fuera del pedido; revisá los vínculos.")
            total_pedido = sum(pedidos.values(), Decimal("0"))
            total_entregado = sum(entregado.values(), Decimal("0"))
            if not total_entregado or total_entregado >= total_pedido:
                raise ValueError("El pedido debe tener una entrega parcial para poder cerrarlo.")
            pendientes = {}
            for (art, dep), qty in pedidos.items():
                recibido = entregado.get(art, Decimal("0"))
                if recibido > qty:
                    raise ValueError("La cantidad remitida supera la pedida; revisá el pedido.")
                restante = qty - recibido
                if restante:
                    pendientes[(art, dep)] = restante
            for (art, dep), qty in sorted(pendientes.items()):
                cur.execute(
                    "SELECT saldo_pedido_cliente FROM stock_deposito "
                    "WHERE id_articulo=%s AND id_deposito=%s FOR UPDATE",
                    [art, dep],
                )
                fila = cur.fetchone()
                reserva = to_decimal_or_none(fila[0]) if fila else None
                if reserva is None or reserva < qty:
                    raise ValueError("La reserva no alcanza para liberar el pendiente; revisá stock antes de cerrar.")
                cur.execute(
                    "UPDATE stock_deposito SET saldo_pedido_cliente=saldo_pedido_cliente-%s "
                    "WHERE id_articulo=%s AND id_deposito=%s",
                    [qty, art, dep],
                )
            cur.execute(
                "UPDATE stockp SET cantidad_pendiente=0 "
                "WHERE CodigoMovimiento=%s AND Anulado='No'",
                [cod],
            )
            cur.execute(
                "UPDATE comp_ped SET Estado='Cerrado', "
                "observacion_interna=TRIM(CONCAT(COALESCE(observacion_interna,''),%s)) "
                "WHERE CodigoMovimiento=%s",
                [f"\n[Cierre parcial Synap: {motivo}]", cod],
            )
            conn.commit()
            return {"ok": True, "pedido": cod, "entregado": str(total_entregado),
                    "liberado": str(sum(pendientes.values(), Decimal('0')))}
        except ValueError as exc:
            conn.rollback()
            return {"ok": False, "error": str(exc)}
        except Exception:
            conn.rollback()
            logger.exception("No se pudo cerrar parcialmente el pedido %s", cod)
            return {"ok": False, "error": "No se pudo cerrar el pedido. Revisá el registro del servidor."}
        finally:
            conn.autocommit(True)
