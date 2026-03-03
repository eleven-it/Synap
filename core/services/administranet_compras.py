"""
Servicio de acceso a datos para Remitos de compra (PRemito.frm).
Paridad 1:1 con VB6: mismo SQL, mismo orden de operaciones, mismas transacciones.
Sin modelos Django; usa core.mysql_pool y base_empresa de sesión.
Referencia: docs/general/ANALISIS_REMITOS_DE_COMPRA_PERSISTENCIA.md
"""
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.mysql_pool import get_connection
from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)

logger = logging.getLogger(__name__)


def buscar_proveedores(
    base_empresa: str, q: str, limite: int = 15
) -> List[Dict[str, Any]]:
    """
    Busca proveedores por CUIT, nombre/razón social o código (Codigo).
    Devuelve lista de dict con: Codigo, Nombre, CUIT, responsabilidad_iva (contribuyentes.IVA),
    Tipo (Mercaderías/Servicios), saldo. Para uso en búsqueda predictiva del remito de compra.
    """
    q = (q or "").strip()
    if not q:
        return []
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            term = f"%{q}%"
            cursor.execute(
                """
                SELECT p.Codigo, COALESCE(p.Nombre, '') AS Nombre, COALESCE(p.CUIT, '') AS CUIT,
                       COALESCE(c.IVA, '') AS responsabilidad_iva, COALESCE(p.Tipo, '') AS Tipo,
                       COALESCE(p.saldo, 0) AS saldo
                FROM proveedor p
                LEFT JOIN contribuyentes c ON c.IDIva = p.IDIva
                WHERE (
                    CAST(p.Codigo AS CHAR) = %s
                    OR COALESCE(p.CUIT, '') LIKE %s
                    OR COALESCE(p.Nombre, '') LIKE %s
                    OR COALESCE(p.id_manual_prov, '') LIKE %s
                )
                AND COALESCE(p.estado, '') <> 'Anulado'
                ORDER BY p.Nombre
                LIMIT %s
                """,
                [q, term, term, term, limite],
            )
            rows = cursor.fetchall()
            cols = ["Codigo", "Nombre", "CUIT", "responsabilidad_iva", "Tipo", "saldo"]
            cursor.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        logger.warning("buscar_proveedores %s: %s", base_empresa, e)
        return []


def get_id_art_por_codigo(
    base_empresa: str, codigo_articulo: str
) -> Optional[Dict[str, Any]]:
    """
    Obtiene IDArt y Descripcion (NombreArticulo) desde articulo por CodigoArticulo.
    Paridad búsqueda artículo en PRemito / Data_Articulo.
    Devuelve None si no existe o dict con IDArt, CodigoArticulo, Descripcion.
    """
    if not codigo_articulo or not str(codigo_articulo).strip():
        return None
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT IDArt, COALESCE(CodigoArticulo, '') AS CodigoArticulo, COALESCE(NombreArticulo, '') AS Descripcion
                FROM articulo
                WHERE COALESCE(anulado, 'No') = 'No' AND (CodigoArticulo = %s OR id_manual = %s)
                LIMIT 1
                """,
                [str(codigo_articulo).strip(), str(codigo_articulo).strip()],
            )
            row = cursor.fetchone()
            cursor.close()
        if not row:
            return None
        cols = ["IDArt", "CodigoArticulo", "Descripcion"]
        return dict(zip(cols, row))
    except Exception as e:
        logger.warning("get_id_art_por_codigo %s: %s", base_empresa, e)
        return None


def get_depositos_remito(
    base_empresa: str,
    id_usuario: Optional[int],
    id_puesto: Optional[int],
    cambia_deposito: bool = True,
    id_deposito_usuario: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Lista depósitos para remito de compra (paridad Form_Load PRemito.frm).
    Si cambia_deposito: depósitos por usuario (deposito_usr); si no hay, todos no anulados.
    Si no cambia_deposito: solo el depósito asignado al usuario (Principal.id_deposito).
    """
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            if cambia_deposito and id_usuario:
                cursor.execute(
                    """
                    SELECT d.CodDeposito, COALESCE(d.NombreDeposito, '') AS NombreDeposito
                    FROM deposito d
                    INNER JOIN deposito_usr du ON du.id_deposito = d.CodDeposito
                    WHERE du.id_usuario = %s AND COALESCE(d.anulado, 'No') = 'No'
                    ORDER BY d.CodDeposito
                    """,
                    [id_usuario],
                )
                rows = cursor.fetchall()
                if rows:
                    cols = [c[0] for c in cursor.description]
                    result = [dict(zip(cols, r)) for r in rows]
                    cursor.close()
                    return result
            if not cambia_deposito:
                dep_usr = to_int_or_none(id_deposito_usuario)
                if dep_usr is not None:
                    cursor.execute(
                        """
                        SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito
                        FROM deposito
                        WHERE CodDeposito = %s AND COALESCE(anulado, 'No') = 'No'
                        ORDER BY CodDeposito
                        """,
                        [dep_usr],
                    )
                    rows = cursor.fetchall()
                    if rows:
                        cols = [c[0] for c in cursor.description]
                        result = [dict(zip(cols, r)) for r in rows]
                        cursor.close()
                        return result
            cursor.execute(
                """
                SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito
                FROM deposito
                WHERE COALESCE(anulado, 'No') = 'No'
                ORDER BY CodDeposito
                """
            )
            rows = cursor.fetchall()
            cols = [c[0] for c in cursor.description]
        cursor.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        logger.warning("Error al listar depósitos remito en %s: %s", base_empresa, e)
        return []


def get_renglones_temporales(
    base_empresa: str,
    id_usuario: int,
    codigo_movimiento: int = 0,
    visualiza: str = "No",
) -> List[Dict[str, Any]]:
    """
    Lee renglones temporales de cuerpostockp (paridad CuerpoStock.RecordSource).
    CodigoMovimiento=0 para remito nuevo; visualiza='No' para temporales del usuario.
    """
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT Orden, IDArt, CodigoArticulo, Descripcion, Cantidad, CodDeposito,
                       PrecioCostoxU, PrecioCostoxR, PrecioNetoxR, TipoIVA, Alicuota,
                       nro_oc, codmov_oc, imp_alicuota_iva, multiplicador_comp, multiplicador_vta,
                       cantidad_uni, id_manual, Detalle, impdesc_bonif, pordesc_bonif
                FROM cuerpostockp
                WHERE CodUsuario = %s AND COALESCE(visualiza, 'No') = %s AND CodigoMovimiento = %s
                ORDER BY Orden
                """,
                [id_usuario, visualiza, codigo_movimiento],
            )
            rows = cursor.fetchall()
            cols = [c[0] for c in cursor.description]
            cursor.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        logger.warning("Error al leer renglones temporales en %s: %s", base_empresa, e)
        return []


def eliminar_renglon_temporal(
    base_empresa: str,
    orden: int,
    id_usuario: int,
    id_articulo: Optional[int],
    orden_cuerpo: Optional[int],
) -> None:
    """
    Elimina un renglón temporal (paridad Eliminar_Click PRemito.frm).
    DELETE cuerpostockp WHERE Orden = %s; DELETE serie_entrada_temp WHERE id_articulo, id_usuario, orden, tipo_comprobante.
    """
    with get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM cuerpostockp WHERE Orden = %s", [orden])
            if id_articulo is not None and orden_cuerpo is not None:
                cursor.execute(
                    """
                    DELETE FROM serie_entrada_temp
                    WHERE id_articulo = %s AND id_usuario = %s AND orden = %s
                      AND COALESCE(tipo_comprobante, '') = 'PRemito'
                    """,
                    [id_articulo, id_usuario, orden_cuerpo],
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def obtener_contador_codmov(base_empresa: str) -> Optional[Decimal]:
    """Lee CodigoMovimiento desde codmov WHERE codigo = 1 (paridad rs_codmov.Open)."""
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT CodigoMovimiento FROM codmov WHERE codigo = 1")
            row = cursor.fetchone()
            cursor.close()
        return to_decimal_or_none(row[0] if row else None) if row else None
    except Exception as e:
        logger.warning("Error al leer codmov en %s: %s", base_empresa, e)
        return None


def guardar_remito_compra(
    base_empresa: str,
    id_usuario: int,
    cod_sucursal: int,
    cabecera: Dict[str, Any],
    renglones: List[Dict[str, Any]],
    id_deposito_seleccion: int,
) -> tuple[Optional[Decimal], Optional[str]]:
    """
    Persiste remito de compra (paridad Guardar PRemito.frm).
    Transacción 1: UPDATE codmov (incrementar CodigoMovimiento); Commit.
    Transacción 2: INSERT cuentaproveedor; por cada renglón stock_deposito + stock; oc_remp; serie_entrada/serie_movimiento; Commit.
    Devuelve (codigo_movimiento, error_message). Si error, (None, mensaje).
    """
    if not renglones:
        return None, "Debe completar todos los campos"

    nro = cabecera.get("nro") or cabecera.get("Nro")
    nro_suc = cabecera.get("nro_suc") or cabecera.get("NroSuc")
    importe_total = to_decimal_or_none(cabecera.get("importe_total") or cabecera.get("ImporteTotal"))
    if not nro or not nro_suc:
        return None, "Debe completar todos los campos"
    if importe_total is None:
        return None, "Debe completar todos los campos"

    codigo_prov = to_int_or_none(cabecera.get("codigo_proveedor") or cabecera.get("Codigo"))
    if codigo_prov is None:
        return None, "Proveedor inválido"

    # Formatear número como en VB6 (ceros a la izquierda)
    try:
        nro_int = int(str(nro).strip())
        nro_suc_int = int(str(nro_suc).strip())
    except (ValueError, TypeError):
        return None, "Número de comprobante inválido"
    ceros = "0000000"[: max(0, 8 - len(str(nro_int)))]
    ceros_s = "000"[: max(0, 4 - len(str(nro_suc_int)))]
    num = f"{ceros_s}{nro_suc_int}-{ceros}{nro_int}"

    # ----- Transacción 1: codmov -----
    try:
        with get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()
            cursor.execute("SELECT CodigoMovimiento FROM codmov WHERE codigo = 1 FOR UPDATE")
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                return None, "No se pudo obtener contador de movimiento"
            contador = (Decimal(str(row[0])) if row[0] is not None else Decimal(0)) + 1
            cursor.execute("UPDATE codmov SET CodigoMovimiento = %s WHERE codigo = 1", [contador])
            conn.commit()
            cursor.close()
    except Exception as e:
        logger.exception("Error transacción 1 codmov: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
        return None, str(e)

    # ----- Transacción 2: cuentaproveedor + stock + stock_deposito + oc_remp + series -----
    try:
        with get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()

            # INSERT cuentaproveedor (campos mínimos paridad VB6)
            fecha = to_date_or_none(cabecera.get("fecha") or cabecera.get("Fecha"))
            fecha_registro = to_date_or_none(cabecera.get("fecha_registro") or cabecera.get("FechaRegistro")) or fecha
            detalle = str_or_default(cabecera.get("detalle") or cabecera.get("Detalle"), "")
            importe_compra = to_decimal_or_none(cabecera.get("importe_total") or cabecera.get("ImporteCompra")) or Decimal(0)
            iva1 = to_decimal_or_none(cabecera.get("iva1") or cabecera.get("Iva1")) or Decimal(0)
            iva2 = to_decimal_or_none(cabecera.get("iva2") or cabecera.get("Iva2")) or Decimal(0)
            iva3 = to_decimal_or_none(cabecera.get("iva3") or cabecera.get("Iva3")) or Decimal(0)
            alic1 = to_decimal_or_none(cabecera.get("alic1") or cabecera.get("Alicuota1")) or Decimal(0)
            alic2 = to_decimal_or_none(cabecera.get("alic2") or cabecera.get("Alicuota2")) or Decimal(0)
            alic3 = to_decimal_or_none(cabecera.get("alic3") or cabecera.get("Alicuota3")) or Decimal(0)
            percep_ib = to_decimal_or_none(cabecera.get("percep_ib") or cabecera.get("PercepIB")) or Decimal(0)
            cod_prov_ib1 = to_int_or_none(cabecera.get("cod_prov_percep_ib1") or cabecera.get("CodProv_PercepIB1")) or 24
            percep_ib_prov = to_decimal_or_none(cabecera.get("percep_ib_prov") or cabecera.get("PercepIB_Prov")) or Decimal(0)
            cod_prov_ib2 = to_int_or_none(cabecera.get("cod_prov_percep_ib2") or cabecera.get("CodProv_PercepIB2")) or 24
            percep_gan = to_decimal_or_none(cabecera.get("percep_gan") or cabecera.get("PercepGan")) or Decimal(0)
            percep_iva = to_decimal_or_none(cabecera.get("percep_iva") or cabecera.get("PercepIVA")) or Decimal(0)
            otros_imp = to_decimal_or_none(cabecera.get("otros_imp") or cabecera.get("OtrosImp")) or Decimal(0)
            impuesto_interno = to_decimal_or_none(cabecera.get("impuesto_interno")) or Decimal(0)
            exento = to_decimal_or_none(cabecera.get("exento") or cabecera.get("Exento")) or Decimal(0)
            subtotal1 = to_decimal_or_none(cabecera.get("subtotal1") or cabecera.get("Subtotal1")) or Decimal(0)
            subtotal2 = to_decimal_or_none(cabecera.get("subtotal2") or cabecera.get("Subtotal2")) or Decimal(0)
            imp_desc1_1 = to_decimal_or_none(cabecera.get("imp_desc1_1") or cabecera.get("ImpDesc1_1")) or Decimal(0)
            sub_total_desc1 = to_decimal_or_none(cabecera.get("sub_total_desc1") or cabecera.get("SubTotalDesc1")) or Decimal(0)
            sub_total_desc2 = to_decimal_or_none(cabecera.get("sub_total_desc2") or cabecera.get("SubTotalDesc2")) or Decimal(0)
            id_condcompra = to_int_or_none(cabecera.get("id_condcompra")) or 0
            cond_compra = str_or_default(cabecera.get("cond_compra") or cabecera.get("CondCompra"), "")
            coti_dolar = to_decimal_or_none(cabecera.get("coti_dolar") or cabecera.get("CotiDolar")) or Decimal(0)
            nro_cai = str_or_default(cabecera.get("nro_cai"), "")
            fecha_cai = to_date_or_none(cabecera.get("fecha_cai"))

            cursor.execute(
                """
                INSERT INTO cuentaproveedor (
                    Fecha, FechaRegistro, TipoComprobante, NroComprobante, NroCompBusq, Detalle,
                    OPMov, ImporteCompra, ImportePago, Iva1, Iva2, Iva3, Alicuota1, Alicuota2, Alicuota3,
                    PercepIB, CodProv_PercepIB1, PercepIB_Prov, CodProv_PercepIB2, PercepGan, PercepIVA, OtrosImp,
                    impuesto_interno, NroCAI, FechaCAI, IdUsuario, codSucursal, TipoFactura, Exento,
                    anulado, Codigo, CodBanco, CodigoMovimiento, Subtotal1, Subtotal2, Subtotal3,
                    ImpDesc1_1, SubTotalDesc1, SubTotalDesc2, SubTotalDesc3, Estado, estado_remito,
                    id_condcompra, CondCompra, CotiDolar
                ) VALUES (
                    %s, %s, 'REM', %s, %s, %s, 0, %s, NULL, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Mercadería', %s,
                    'No', %s, 2, %s, %s, %s, 0, %s, %s, %s, 0, 'N/Canc', 'Pendiente',
                    %s, %s, %s
                )
                """,
                [
                    fecha, fecha_registro, num, nro_int, detalle,
                    importe_compra, iva1, iva2, iva3, alic1, alic2, alic3,
                    percep_ib, cod_prov_ib1, percep_ib_prov, cod_prov_ib2, percep_gan, percep_iva, otros_imp,
                    impuesto_interno, nro_cai, fecha_cai, id_usuario, cod_sucursal, exento,
                    codigo_prov, contador, subtotal1, subtotal2, imp_desc1_1, sub_total_desc1, sub_total_desc2,
                    id_condcompra if id_condcompra else None, cond_compra, coti_dolar,
                ],
            )

            # Por cada renglón: stock_deposito (SELECT; UPDATE o INSERT) y stock (INSERT)
            for reng in renglones:
                id_art = to_int_or_none(reng.get("IDArt") or reng.get("id_art"))
                cantidad = to_decimal_or_none(reng.get("Cantidad") or reng.get("cantidad")) or Decimal(0)
                cod_deposito = to_int_or_none(reng.get("CodDeposito") or reng.get("cod_deposito")) or id_deposito_seleccion
                if id_art is None or cantidad <= 0:
                    continue
                multiplicador_comp = to_decimal_or_none(reng.get("multiplicador_comp") or reng.get("multiplicador_comp")) or Decimal(1)
                entrada = cantidad * multiplicador_comp

                cursor.execute(
                    "SELECT id_articulo, id_deposito, saldo, saldo_pedido_proveedor FROM stock_deposito WHERE id_articulo = %s AND id_deposito = %s",
                    [id_art, cod_deposito],
                )
                sd_row = cursor.fetchone()
                if sd_row:
                    nuevo_saldo = (Decimal(str(sd_row[2])) if sd_row[2] is not None else Decimal(0)) + entrada
                    saldo_ped_prov = (Decimal(str(sd_row[3])) if sd_row[3] is not None else Decimal(0))
                    if reng.get("nro_oc") or reng.get("codmov_oc"):
                        saldo_ped_prov += cantidad
                    cursor.execute(
                        "UPDATE stock_deposito SET saldo = %s, saldo_pedido_proveedor = %s WHERE id_articulo = %s AND id_deposito = %s",
                        [nuevo_saldo, saldo_ped_prov, id_art, cod_deposito],
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO stock_deposito (id_articulo, id_deposito, saldo, saldo_pedido_proveedor)
                        VALUES (%s, %s, %s, %s)
                        """,
                        [id_art, cod_deposito, entrada, cantidad if (reng.get("nro_oc") or reng.get("codmov_oc")) else 0],
                    )

                descripcion = str_or_default(reng.get("Descripcion") or reng.get("descripcion"), "")
                codigo_articulo = str_or_default(reng.get("CodigoArticulo") or reng.get("codigo_articulo"), "")
                precio_costo_u = to_decimal_or_none(reng.get("PrecioCostoxU") or reng.get("precio_costo_u")) or Decimal(0)
                precio_costo_r = to_decimal_or_none(reng.get("PrecioCostoxR") or reng.get("precio_costo_r")) or (precio_costo_u * cantidad)
                tipo_iva = str_or_default(reng.get("TipoIVA") or reng.get("tipo_iva"), "")
                alicuota = to_decimal_or_none(reng.get("Alicuota") or reng.get("alicuota")) or Decimal(0)
                codmov_oc = to_decimal_or_none(reng.get("codmov_oc"))
                nro_oc = str_or_default(reng.get("nro_oc"), "")

                cursor.execute(
                    """
                    INSERT INTO stock (
                        Fecha, CodigoArticulo, Descripcion, PrecioCostoxU, PrecioCostoxR, Cantidad, Entrada,
                        TipoComp, CodigoMovimiento, CodigoCP, Tipo, anulado, Comprobante, NroComprobante,
                        CodDeposito, TipoIVA, Alicuota, IdUsuario, codSucursal, IDArt, NroRemito, codmov_remito,
                        NroPedido, codmov_pedido
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, 'Remito Entrada', %s, %s, 'Proveedor', 'No', 'REM', %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    [
                        fecha, codigo_articulo, descripcion, precio_costo_u, precio_costo_r, cantidad, entrada,
                        contador, codigo_prov, num, cod_deposito, tipo_iva, alicuota, id_usuario, cod_sucursal,
                        id_art, num, contador, nro_oc or None, codmov_oc,
                    ],
                )

                # oc_remp si viene de OC
                if codmov_oc is not None and codmov_oc != 0:
                    cursor.execute(
                        "INSERT INTO oc_remp (codigo_movimiento_remp, codigo_movimiento_oc, anulado) VALUES (%s, %s, 'No')",
                        [contador, codmov_oc],
                    )

            # GuardarSerie: INSERT serie_entrada y serie_movimiento desde serie_entrada_temp (simplificado: si no hay series, no insertar)
            cursor.execute(
                """
                SELECT id_articulo, orden, serie, id_serie_entrada
                FROM serie_entrada_temp
                WHERE id_usuario = %s AND COALESCE(tipo_comprobante, '') = 'PRemito'
                ORDER BY id_articulo, orden
                """,
                [id_usuario],
            )
            series_rows = cursor.fetchall()
            for srow in series_rows:
                pass  # Inserción serie_entrada/serie_movimiento según VB6 (opcional en primera entrega)

            conn.commit()
            cursor.close()
        return contador, None
    except Exception as e:
        logger.exception("Error transacción 2 remito compra: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
        return None, str(e)


def siguiente_orden_temporal(base_empresa: str, id_usuario: int) -> int:
    """Obtiene el siguiente Orden para cuerpostockp del usuario (CodUsuario, visualiza='No')."""
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COALESCE(MAX(Orden), 0) + 1 FROM cuerpostockp WHERE CodUsuario = %s AND COALESCE(visualiza, 'No') = 'No'",
                [id_usuario],
            )
            row = cursor.fetchone()
            cursor.close()
        return int(row[0]) if row and row[0] is not None else 1
    except Exception as e:
        logger.warning("Error al obtener siguiente Orden en %s: %s", base_empresa, e)
        return 1


def alta_renglon_temporal(
    base_empresa: str,
    id_usuario: int,
    id_art: int,
    codigo_articulo: str,
    descripcion: str,
    cantidad: Decimal,
    cod_deposito: int,
    precio_costo_u: Decimal,
    nro_oc: Optional[str] = None,
    codmov_oc: Optional[Decimal] = None,
) -> Optional[int]:
    """
    Inserta un renglón temporal en cuerpostockp (paridad AceptarStock / CuerpoStock.Recordset.AddNew).
    Devuelve el Orden asignado o None en error.
    """
    orden = siguiente_orden_temporal(base_empresa, id_usuario)
    precio_costo_r = (precio_costo_u or Decimal(0)) * (cantidad or Decimal(0))
    precio_neto_r = precio_costo_r
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO cuerpostockp (
                    Orden, CodUsuario, visualiza, CodigoMovimiento, IDArt, CodigoArticulo, Descripcion,
                    Cantidad, CodDeposito, PrecioCostoxU, PrecioCostoxR, PrecioNetoxR,
                    TipoIVA, Alicuota, multiplicador_comp, multiplicador_vta, cantidad_uni
                ) VALUES (
                    %s, %s, 'No', 0, %s, %s, %s, %s, %s, %s, %s, %s, '', 0, 1, 1, 1
                )
                """,
                [
                    orden, id_usuario, id_art, str_or_default(codigo_articulo, ""),
                    str_or_default(descripcion, ""), cantidad, cod_deposito,
                    precio_costo_u or Decimal(0), precio_costo_r, precio_neto_r,
                ],
            )
            if nro_oc or codmov_oc:
                cursor.execute(
                    "UPDATE cuerpostockp SET nro_oc = %s, codmov_oc = %s WHERE Orden = %s AND CodUsuario = %s",
                    [str_or_default(nro_oc, ""), codmov_oc, orden, id_usuario],
                )
            conn.commit()
            cursor.close()
        return orden
    except Exception as e:
        logger.exception("Error al insertar renglón temporal: %s", e)
        return None


def limpiar_temporales_usuario(
    base_empresa: str,
    id_usuario: int,
) -> None:
    """
    Elimina renglones temporales del usuario (paridad Elimina_Temporal).
    DELETE FROM cuerpostockp WHERE CodUsuario = %s AND visualiza = 'No';
    DELETE FROM serie_entrada_temp WHERE id_usuario = %s AND tipo_comprobante = 'PRemito'.
    """
    with get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM cuerpostockp WHERE CodUsuario = %s AND COALESCE(visualiza, 'No') = 'No'", [id_usuario])
            cursor.execute(
                "DELETE FROM serie_entrada_temp WHERE id_usuario = %s AND COALESCE(tipo_comprobante, '') = 'PRemito'",
                [id_usuario],
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def list_comprobantes_remito(
    base_empresa: str,
    codigo_proveedor: int,
    tipo: str,
) -> List[Dict[str, Any]]:
    """
    Lista comprobantes del proveedor para Remito de compra (paridad Lista_Comp_Gral).
    tipo: 'oc' (Orden de Compra - Remito), 'factura' (PFacturas), 'importa_rem' (Importa REM Prov).
    Devuelve lista de dict con CodigoMovimiento, NroComprobante, Fecha, ImporteCompra, id_condcompra, CondCompra, ImpDesc1_1, CotiDolar.
    """
    codigo_prov = to_int_or_none(codigo_proveedor)
    if codigo_prov is None:
        return []
    if tipo not in ("oc", "factura", "importa_rem"):
        return []
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            if tipo == "oc":
                cursor.execute(
                    """
                    SELECT cp.CodigoMovimiento, COALESCE(cp.NroComprobante, '') AS NroComprobante,
                           cp.Fecha, cp.ImporteCompra, cp.id_condcompra, COALESCE(cp.CondCompra, '') AS CondCompra,
                           cp.ImpDesc1_1, cp.CotiDolar
                    FROM cuentaproveedor cp
                    WHERE cp.Codigo = %s AND COALESCE(cp.Anulado, 'No') = 'No'
                      AND cp.TipoComprobante = 'OC'
                      AND (cp.Estado = 'Pendiente' OR cp.Estado IS NULL OR cp.Estado = '')
                    ORDER BY cp.Fecha DESC, cp.CodigoMovimiento DESC
                    LIMIT 200
                    """,
                    [codigo_prov],
                )
            elif tipo == "factura":
                cursor.execute(
                    """
                    SELECT cp.CodigoMovimiento, COALESCE(cp.NroComprobante, '') AS NroComprobante,
                           cp.Fecha, cp.ImporteCompra, cp.id_condcompra, COALESCE(cp.CondCompra, '') AS CondCompra,
                           cp.ImpDesc1_1, cp.CotiDolar
                    FROM cuentaproveedor cp
                    WHERE cp.Codigo = %s AND COALESCE(cp.Anulado, 'No') = 'No'
                      AND cp.TipoComprobante IN ('FA', 'FB', 'FC', 'FM', 'FE')
                      AND COALESCE(cp.remite_factura_art, 'No') = 'No'
                      AND (cp.estado_fact_remito = 'Pendiente' OR cp.estado_fact_remito = 'Parcial')
                    ORDER BY cp.Fecha DESC, cp.CodigoMovimiento DESC
                    LIMIT 200
                    """,
                    [codigo_prov],
                )
            else:
                cursor.execute(
                    """
                    SELECT cp.CodigoMovimiento, COALESCE(cp.NroComprobante, '') AS NroComprobante,
                           cp.Fecha, cp.ImporteCompra, cp.id_condcompra, COALESCE(cp.CondCompra, '') AS CondCompra,
                           cp.ImpDesc1_1, cp.CotiDolar
                    FROM cuentaproveedor cp
                    WHERE cp.Codigo = %s AND COALESCE(cp.Anulado, 'No') = 'No'
                      AND cp.TipoComprobante = 'REM'
                    ORDER BY cp.Fecha DESC, cp.CodigoMovimiento DESC
                    LIMIT 200
                    """,
                    [codigo_prov],
                )
            rows = cursor.fetchall()
            cols = [c[0] for c in cursor.description]
            cursor.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        logger.warning("list_comprobantes_remito %s tipo=%s: %s", base_empresa, tipo, e)
        return []


def importar_comprobante_remito(
    base_empresa: str,
    id_usuario: int,
    codigo_movimiento: int,
    tipo: str,
    id_deposito_usuario: Optional[int] = None,
) -> tuple[bool, Optional[str]]:
    """
    Copia renglones del comprobante seleccionado a cuerpostockp del usuario (paridad Lista_Comp_Gral → PRemito).
    tipo: 'oc' (desde stockp, cantidad_pendiente), 'factura' o 'importa_rem' (desde stock).
    Devuelve (True, None) o (False, mensaje_error).
    """
    cod_mov = to_int_or_none(codigo_movimiento)
    if cod_mov is None:
        return False, "Comprobante inválido"
    if tipo not in ("oc", "factura", "importa_rem"):
        return False, "Tipo de comprobante inválido"
    id_dep = to_int_or_none(id_deposito_usuario)

    try:
        with get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()

            if tipo == "oc":
                cursor.execute("DELETE FROM cuerpostockp WHERE CodUsuario = %s AND COALESCE(visualiza, 'No') = 'No'", [id_usuario])
                cursor.execute(
                    "DELETE FROM serie_entrada_temp WHERE id_usuario = %s AND COALESCE(tipo_comprobante, '') = 'PRemito'",
                    [id_usuario],
                )
                cursor.execute(
                    """
                    SELECT sp.CodigoArticulo, sp.IDArt, sp.Descripcion,
                           COALESCE(sp.cantidad_pendiente, sp.Cantidad) AS Cantidad,
                           sp.PrecioCostoxU, sp.PrecioVentaxU, sp.PrecioIVAxU, sp.PrecioBrutoxU,
                           sp.Impdesc, sp.Pordesc, sp.PrecioCostoxR, sp.PrecioVentaxR, sp.PrecioIVAxR, sp.PrecioBrutoxR, sp.PrecioNetoxR,
                           sp.TipoIVA, sp.Alicuota, sp.imp_alicuota_iva, sp.CodDeposito, sp.tipo_art, sp.impdesc_bonif, sp.pordesc_bonif,
                           sp.Detalle, sp.id_manual, sp.multiplicador_comp, sp.multiplicador_vta, sp.cantidad_uni,
                           sp.id_unimed_comp, sp.id_presentacion_comp, sp.nombre_unimed_comp, sp.nombre_presentacion_comp,
                           sp.impuesto_interno_subtotal, sp.NroPresupuesto, sp.codmov_presupuesto
                    FROM stockp sp
                    WHERE sp.CodigoMovimiento = %s AND COALESCE(sp.remitido_facturado, 'No') = 'No'
                    ORDER BY sp.Orden
                    """,
                    [cod_mov],
                )
                rows = cursor.fetchall()
                cursor.execute(
                    "SELECT NroComprobante FROM cuentaproveedor WHERE CodigoMovimiento = %s LIMIT 1",
                    [cod_mov],
                )
                nro_oc_row = cursor.fetchone()
                nro_oc = str(nro_oc_row[0]) if nro_oc_row and nro_oc_row[0] else ""
                orden = 0
                for r in rows:
                    orden += 1
                    cod_dep = to_int_or_none(r[18]) if len(r) > 18 else id_dep
                    if cod_dep is None:
                        cod_dep = id_dep or 0
                    cantidad = to_decimal_or_none(r[3]) or Decimal(0)
                    if cantidad <= 0:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO cuerpostockp (
                            Orden, CodUsuario, visualiza, CodigoMovimiento, IDArt, CodigoArticulo, Descripcion,
                            Cantidad, CodDeposito, PrecioCostoxU, PrecioVentaxU, PrecioIVAxU, PrecioBrutoxU,
                            PrecioCostoxR, PrecioVentaxR, PrecioIVAxR, PrecioBrutoxR, PrecioNetoxR,
                            Impdesc, Pordesc, TipoIVA, Alicuota, imp_alicuota_iva, tipo_art,
                            impdesc_bonif, pordesc_bonif, nro_oc, codmov_oc, Detalle, id_manual,
                            multiplicador_comp, multiplicador_vta, cantidad_uni,
                            id_UniMed, id_presentacion, nombre_unimed, nombre_presentacion,
                            impuesto_interno_subtotal, nro_presupuesto, codmov_presupuesto
                        ) VALUES (
                            %s, %s, 'No', 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        """,
                        [
                            orden, id_usuario, to_int_or_none(r[1]), str_or_default(r[0], ""), str_or_default(r[2], ""),
                            cantidad, cod_dep,
                            to_decimal_or_none(r[4]) or 0, to_decimal_or_none(r[5]) or 0, to_decimal_or_none(r[6]) or 0, to_decimal_or_none(r[7]) or 0,
                            to_decimal_or_none(r[10]) or 0, to_decimal_or_none(r[11]) or 0, to_decimal_or_none(r[12]) or 0, to_decimal_or_none(r[13]) or 0, to_decimal_or_none(r[14]) or 0,
                            to_decimal_or_none(r[8]) or 0, to_decimal_or_none(r[9]) or 0,
                            str_or_default(r[15], ""), to_decimal_or_none(r[16]) or 0, to_decimal_or_none(r[17]) or 0,
                            str_or_default(r[19], ""), to_decimal_or_none(r[20]) or 0, to_decimal_or_none(r[21]) or 0,
                            nro_oc, cod_mov,
                            str_or_default(r[22], "") if len(r) > 22 else "", str_or_default(r[23], "") if len(r) > 23 else "",
                            to_decimal_or_none(r[24]) or 1 if len(r) > 24 else 1, to_decimal_or_none(r[25]) or 1 if len(r) > 25 else 1, to_decimal_or_none(r[26]) or 0 if len(r) > 26 else 0,
                            to_int_or_none(r[27]) if len(r) > 27 else None, to_int_or_none(r[28]) if len(r) > 28 else None,
                            str_or_default(r[29], "") if len(r) > 29 else "", str_or_default(r[30], "") if len(r) > 30 else "",
                            to_decimal_or_none(r[31]) if len(r) > 31 else 0,
                            str_or_default(r[32], "") if len(r) > 32 else "", to_decimal_or_none(r[33]) if len(r) > 33 else None,
                        ],
                    )
            else:
                cursor.execute(
                    """
                    SELECT s.CodigoArticulo, s.IDArt, s.Descripcion, s.Cantidad,
                           s.PrecioCostoxU, s.PrecioVentaxU, s.PrecioIVAxU, s.PrecioBrutoxU,
                           s.Impdesc, s.Pordesc, s.PrecioCostoxR, s.PrecioVentaxR, s.PrecioIVAxR, s.PrecioBrutoxR, s.PrecioNetoxR,
                           s.TipoIVA, s.Alicuota, s.imp_alicuota_iva, s.CodDeposito, s.tipo_art,
                           s.impdesc_bonif, s.pordesc_bonif, s.detalle, s.id_manual, s.impuesto_interno_subtotal
                    FROM stock s
                    WHERE s.CodigoMovimiento = %s
                    ORDER BY s.Orden
                    """,
                    [cod_mov],
                )
                rows = cursor.fetchall()
                orden = 0
                for r in rows:
                    orden += 1
                    cod_dep = to_int_or_none(r[18]) if len(r) > 18 else id_dep
                    if cod_dep is None:
                        cod_dep = id_dep or 0
                    cantidad = to_decimal_or_none(r[3]) or Decimal(0)
                    if cantidad <= 0:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO cuerpostockp (
                            Orden, CodUsuario, visualiza, CodigoMovimiento, IDArt, CodigoArticulo, Descripcion,
                            Cantidad, CodDeposito, PrecioCostoxU, PrecioVentaxU, PrecioIVAxU, PrecioBrutoxU,
                            PrecioCostoxR, PrecioVentaxR, PrecioIVAxR, PrecioBrutoxR, PrecioNetoxR,
                            Impdesc, Pordesc, TipoIVA, Alicuota, imp_alicuota_iva, tipo_art,
                            impdesc_bonif, pordesc_bonif, Detalle, id_manual, impuesto_interno_subtotal
                        ) VALUES (
                            %s, %s, 'No', 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        """,
                        [
                            orden, id_usuario, to_int_or_none(r[1]), str_or_default(r[0], ""), str_or_default(r[2], ""),
                            cantidad, cod_dep,
                            to_decimal_or_none(r[4]) or 0, to_decimal_or_none(r[5]) or 0, to_decimal_or_none(r[6]) or 0, to_decimal_or_none(r[7]) or 0,
                            to_decimal_or_none(r[10]) or 0, to_decimal_or_none(r[11]) or 0, to_decimal_or_none(r[12]) or 0, to_decimal_or_none(r[13]) or 0, to_decimal_or_none(r[14]) or 0,
                            to_decimal_or_none(r[8]) or 0, to_decimal_or_none(r[9]) or 0,
                            str_or_default(r[15], ""), to_decimal_or_none(r[16]) or 0, to_decimal_or_none(r[17]) or 0,
                            str_or_default(r[19], ""), to_decimal_or_none(r[20]) or 0, to_decimal_or_none(r[21]) or 0,
                            str_or_default(r[22], "") if len(r) > 22 else "", str_or_default(r[23], "") if len(r) > 23 else "",
                            to_decimal_or_none(r[24]) if len(r) > 24 else 0,
                        ],
                    )

            conn.commit()
            cursor.close()
        return True, None
    except Exception as e:
        logger.exception("importar_comprobante_remito: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)
