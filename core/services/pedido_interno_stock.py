"""Pedidos internos PEDI compatibles con Pedido_Interno.frm de administraNET."""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool, mysql_cursor
from core.services.administranet_stock import get_depositos
from core.services.stock_presentaciones import (
    PresentacionInvalida, datos_presentacion_articulo, factor_presentacion,
)

logger = logging.getLogger(__name__)


def obtener_presentaciones_pedido_interno(base_empresa: str, id_articulo: int) -> Dict[str, Any]:
    """Factores de lectura del PEDI, calculados con la misma regla de escritura."""
    with mysql_cursor(base_empresa) as cursor:
        datos = datos_presentacion_articulo(cursor, id_articulo)
    resultado = {"unidades_display": None, "unidades_bulto": None}
    for tipo, campo in (("Display", "unidades_display"), ("Bulto", "unidades_bulto")):
        try:
            resultado[campo] = str(factor_presentacion(
                tipo, datos["unidades_display"], datos["multiplicador_comp"],
                datos["displays_bulto"], usa_lote=datos["lote"],
                usa_serie=datos["serie"],
            ))
        except PresentacionInvalida:
            pass
    return resultado


def listar_pedidos_internos(base_empresa: str, limite: int = 50) -> List[Dict[str, Any]]:
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        cursor.execute(
            """SELECT cp.CodigoMovimiento,cp.NroComprobante,cp.Fecha,cp.Estado,
                      cp.tipo_pedido_interno,ms.deposito_origen,ms.deposito_destino,
                      COALESCE(SUM(sp.Cantidad),0) AS cantidad,
                      COALESCE(SUM(CASE WHEN UPPER(COALESCE(sp.tipo_unidad,''))='DISPLAY'
                        AND COALESCE(sp.cantidad_dividir,0)>0
                        THEN sp.Cantidad/sp.cantidad_dividir ELSE 0 END),0) AS displays,
                      COALESCE(SUM(CASE WHEN LEFT(UPPER(COALESCE(sp.tipo_unidad,'')),5)='BULTO'
                        AND COALESCE(sp.cantidad_dividir,0)>0
                        THEN sp.Cantidad/sp.cantidad_dividir ELSE 0 END),0) AS bultos,
                      COALESCE(SUM(sp.cantidad_pendiente),0) AS pendiente
               FROM comp_ped cp
               LEFT JOIN movimiento_stock ms ON ms.codigo_movimiento=cp.CodigoMovimiento
                 AND ms.tipo_comprobante='PEDI' AND UPPER(COALESCE(ms.anulado,'No'))<>'SI'
               LEFT JOIN stockp sp ON sp.CodigoMovimiento=cp.CodigoMovimiento
                 AND UPPER(COALESCE(sp.Anulado,'No'))<>'SI'
               WHERE cp.TipoComprobante='PEDI' AND UPPER(COALESCE(cp.Anulado,'No'))<>'SI'
               GROUP BY cp.CodigoMovimiento,cp.NroComprobante,cp.Fecha,cp.Estado,
                        cp.tipo_pedido_interno,ms.deposito_origen,ms.deposito_destino
               ORDER BY cp.CodigoMovimiento DESC LIMIT %s""", [limite])
        return [dict(row) for row in cursor.fetchall()]


def crear_pedido_interno(base_empresa: str, id_usuario: int, id_puesto: Optional[int],
                         id_pv: int, datos: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Crea encabezado, stockp y movimiento auxiliar bajo un único COMMIT."""
    try:
        tipo = str(datos.get("tipo") or "").strip()
        if tipo not in ("A deposito", "A compras"):
            raise ValueError("El tipo debe ser A depósito o A compras.")
        if not datos.get("deposito_origen") or (tipo == "A deposito" and not datos.get("deposito_destino")):
            raise ValueError("Seleccione los depósitos del pedido interno.")
        origen = int(datos["deposito_origen"])
        destino = int(datos["deposito_destino"]) if tipo == "A deposito" else origen
        if origen <= 0 or destino <= 0 or (tipo == "A deposito" and origen == destino):
            raise ValueError("Seleccione depósitos de origen y destino diferentes.")
        permitidos = {int(d["CodDeposito"]) for d in get_depositos(base_empresa, id_puesto)}
        if origen not in permitidos or destino not in permitidos:
            raise ValueError("No tiene acceso a uno de los depósitos seleccionados.")
        fecha = date.fromisoformat(str(datos.get("fecha") or date.today().isoformat()))
        renglones = datos.get("renglones")
        if not isinstance(renglones, list) or not renglones or len(renglones) > 200:
            raise ValueError("Agregue entre 1 y 200 artículos al pedido.")
        detalle = str(datos.get("detalle") or "").strip()[:2000]
        id_pv = int(id_pv or 1)
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()
            try:
                # Se bloquean los mismos numeradores que utiliza VB6.
                cursor.execute("SELECT CodigoMovimiento FROM codmov WHERE codigo=1 FOR UPDATE")
                row = cursor.fetchone()
                if not row:
                    raise ValueError("No existe el numerador de movimientos.")
                codigo = int(Decimal(str(row[0]))) + 1
                cursor.execute("UPDATE codmov SET CodigoMovimiento=%s WHERE codigo=1", [codigo])
                cursor.execute(
                    """SELECT Orden,Nro FROM talonarios WHERE TipoComprobante='PEDI'
                       AND id_punto_venta=%s AND COALESCE(anulado,'No')='No'
                       FOR UPDATE""", [id_pv])
                talonario = cursor.fetchone()
                if not talonario:
                    raise ValueError("No existe talonario PEDI para el punto de venta del usuario.")
                numero = int(talonario[1] or 0) + 1
                cursor.execute("UPDATE talonarios SET Nro=%s WHERE Orden=%s", [numero, talonario[0]])
                nro = f"{id_pv:04d}-{numero:08d}"
                cursor.execute(
                    """INSERT INTO comp_ped
                       (Fecha,TipoComprobante,CodSucursal,IdUsuario,Codigo,
                        NroComprobante,NroCompBusq,id_pv,Detalle,Anulado,
                        CodigoMovimiento,Estado,CodViajante,tipo_pedido_interno,fecha_control)
                       VALUES (%s,'PEDI',%s,%s,1,%s,%s,%s,%s,'No',%s,
                               'Pendiente',1,%s,DATE_FORMAT(NOW(),'%%d/%%m/%%Y/ %%H:%%i:%%s'))""",
                    [fecha, int(datos.get("cod_sucursal") or 1), id_usuario,
                     nro, numero, id_pv, detalle or None, codigo, tipo])
                for orden, item in enumerate(renglones, 1):
                    id_art = int(item.get("id_articulo"))
                    cursor.execute(
                        """SELECT IDArt,CodigoArticuloT,NombreArticulo,id_manual,
                                  PrecioCosto,TipoIVA,Alicuota,CodLaboratorio,
                                  IFNULL(serie,'No')
                           FROM articulo WHERE IDArt=%s""", [id_art])
                    articulo = cursor.fetchone()
                    if not articulo:
                        raise ValueError(f"Artículo {id_art} no encontrado.")
                    presentacion = datos_presentacion_articulo(cursor, id_art)
                    unidad = str(item.get("tipo_unidad") or "Unidad").strip().title()
                    factor = factor_presentacion(
                        unidad, presentacion["unidades_display"],
                        presentacion["multiplicador_comp"], presentacion["displays_bulto"],
                        usa_lote=presentacion["lote"], usa_serie=presentacion["serie"])
                    cantidad = Decimal(str(item.get("cantidad")))
                    if not cantidad.is_finite() or cantidad <= 0:
                        raise ValueError(f"Renglón {orden}: cantidad inválida.")
                    unidades = cantidad * factor
                    costo = Decimal(str(articulo[4] or 0))
                    cursor.execute(
                        """INSERT INTO stockp
                           (Fecha,CodigoArticulo,Descripcion,PrecioCostoxU,PrecioCostoxR,
                            Cantidad,cantidad_pendiente,cantidad_entregada,Entrada,Salida,
                            Orden,CodigoMovimiento,CodDeposito,IDArt,Detalle,id_manual,
                            CodSucursal,IdUsuario,TipoIVA,Alicuota,Tipo,TipoComp,Anulado,
                            Comprobante,NroComprobante,CodigoCP,CodLaboratorio,
                            tipo_unidad,cantidad_unidad_display,multiplicador_comp,
                            cantidad_dividir,serie)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,0,0,0,%s,%s,%s,%s,%s,%s,
                                   %s,%s,%s,%s,'Pedido Interno',%s,'No','PEDI',%s,1,%s,
                                   %s,%s,%s,%s,%s)""",
                        [fecha, articulo[1] or str(articulo[0]), articulo[2], costo,
                         costo * unidades, unidades, unidades, orden, codigo, origen,
                         id_art, detalle, articulo[3], int(datos.get("cod_sucursal") or 1),
                         id_usuario, articulo[5], articulo[6], tipo, nro, articulo[7] or 1,
                         unidad, presentacion["unidades_display"] or 1,
                         presentacion["multiplicador_comp"] or presentacion["displays_bulto"] or 1,
                         factor,
                         articulo[8]])
                cursor.execute(
                    """INSERT INTO movimiento_stock
                       (Fecha,motivo_movimiento,Detalle,deposito_origen,
                        deposito_destino,codigo_movimiento,nro_comprobante,
                        nro_comprobante_busq,id_sucursal,id_usuario,id_pv,
                        tipo_comprobante,Estado,Anulado)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PEDI','Pendiente','No')""",
                    [fecha, f"Pedido interno - {tipo}", detalle, origen, destino,
                     codigo, nro, numero, int(datos.get("cod_sucursal") or 1),
                     id_usuario, id_pv])
                conn.commit()
                return True, {"codigo_movimiento": codigo, "nro_comprobante": nro}
            except Exception:
                conn.rollback()
                raise
    except (ValueError, TypeError, InvalidOperation, PresentacionInvalida) as exc:
        return False, {"error": str(exc)}
    except Exception as exc:
        logger.exception("No se pudo crear el pedido interno")
        return False, {"error": str(exc)}
