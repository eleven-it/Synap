"""
Repositorios: único punto de lectura/escritura parametrizada sobre tablas MySQL administraNET.
Todas las funciones usan parámetros (nunca concatenación) y core.utils.administranet_types.
Reciben base_empresa o conn según uso en transacción.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_connection
from core.utils.administranet_types import to_int_or_none

logger = logging.getLogger(__name__)

# Whitelist columnas para ordenar listado proveedores (evitar inyección)
PROVEEDOR_ORDER_COLUMNS = {"Nombre": "p.Nombre", "Codigo": "p.Codigo", "CUIT": "p.CUIT", "IVA": "c.IVA", "saldo": "p.saldo"}


def listar_sucursales(
    base_empresa: str,
    solo_id_sucursal: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Lista sucursales. Si solo_id_sucursal está definido, filtra por esa sucursal.
    Paridad con CargaComprobantesP Inicial (DataSucursal).
    """
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            if solo_id_sucursal is not None:
                cursor.execute(
                    "SELECT * FROM sucursales WHERE id_sucursal = %s ORDER BY nombre_sucursal",
                    [to_int_or_none(solo_id_sucursal)],
                )
            else:
                cursor.execute("SELECT * FROM sucursales ORDER BY nombre_sucursal")
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description] if cursor.description else []
            cursor.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        logger.warning("listar_sucursales %s: %s", base_empresa, e)
        return []


def buscar_proveedores_paginado(
    base_empresa: str,
    q: str,
    tipo_busqueda: str,
    id_sucursal: Optional[int],
    ver_proveedor_todas_sucursales: bool,
    limit: int,
    offset: int = 0,
    order_by: str = "Nombre",
    orden: str = "asc",
) -> List[Dict[str, Any]]:
    """
    Búsqueda de proveedores con filtros parametrizados, paginación y orden.
    Paridad con Consulta_Busqueda (SQL-003); order_by solo permite columnas whitelist.
    """
    q = (q or "").strip()
    col_order = PROVEEDOR_ORDER_COLUMNS.get(order_by, "p.Nombre")
    dir_order = "ASC" if (orden or "").lower() == "asc" else "DESC"
    comodin1, comodin2 = "%", "%"
    if tipo_busqueda == "Comienza con":
        comodin2 = "%"
        comodin1 = ""
    elif tipo_busqueda == "Finaliza con":
        comodin1 = "%"
        comodin2 = ""
    term = f"{comodin1}{q}{comodin2}"

    params: List[Any] = [term, term, term, term]
    where_extra = " AND p.Codigo <> 1 AND p.Codigo <> 2 AND COALESCE(p.estado, '') = 'Activo' "
    if not ver_proveedor_todas_sucursales and id_sucursal is not None:
        where_extra += " AND p.id_sucursal = %s "
        params.append(to_int_or_none(id_sucursal))
    params.extend([limit, offset])

    sql = f"""
        SELECT p.obliga_oc_carga_comp, p.cod_ret_iva, p.id_cc, p.CodCatRet, p.CodCatRetG, p.Tipo,
               p.NroCAI, p.FechaCAI, p.CUIT, p.Codigo, p.Nombre, p.idIVA, c.IVA AS IVA, p.saldo
        FROM proveedor p
        INNER JOIN contribuyentes c ON c.idIVA = p.idIVA
        WHERE (p.Codigo LIKE %s OR p.Nombre LIKE %s OR p.CUIT LIKE %s OR COALESCE(p.id_manual_prov, '') LIKE %s)
        {where_extra}
        ORDER BY {col_order} {dir_order}
        LIMIT %s OFFSET %s
    """
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description] if cursor.description else []
            cursor.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception as e:
        logger.warning("buscar_proveedores_paginado %s: %s", base_empresa, e)
        return []


def count_proveedores(
    base_empresa: str,
    q: str,
    tipo_busqueda: str,
    id_sucursal: Optional[int],
    ver_proveedor_todas_sucursales: bool,
) -> int:
    """
    Total de proveedores con los mismos filtros que buscar_proveedores_paginado.
    Reemplazo de SQL_CALC_FOUND_ROWS con COUNT(*) parametrizado.
    """
    q = (q or "").strip()
    comodin1, comodin2 = "%", "%"
    if tipo_busqueda == "Comienza con":
        comodin2 = "%"
        comodin1 = ""
    elif tipo_busqueda == "Finaliza con":
        comodin1 = "%"
        comodin2 = ""
    term = f"{comodin1}{q}{comodin2}"
    params: List[Any] = [term, term, term, term]
    where_extra = " AND p.Codigo <> 1 AND p.Codigo <> 2 AND COALESCE(p.estado, '') = 'Activo' "
    if not ver_proveedor_todas_sucursales and id_sucursal is not None:
        where_extra += " AND p.id_sucursal = %s "
        params.append(to_int_or_none(id_sucursal))

    sql = f"""
        SELECT COUNT(*)
        FROM proveedor p
        INNER JOIN contribuyentes c ON c.idIVA = p.idIVA
        WHERE (p.Codigo LIKE %s OR p.Nombre LIKE %s OR p.CUIT LIKE %s OR COALESCE(p.id_manual_prov, '') LIKE %s)
        {where_extra}
    """
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            cursor.close()
        return int(row[0]) if row else 0
    except Exception as e:
        logger.warning("count_proveedores %s: %s", base_empresa, e)
        return 0


def check_lock_op_proveedor(
    base_empresa: str,
    codigo_proveedor: int,
    id_usuario_actual: int,
) -> Optional[Dict[str, Any]]:
    """
    Comprueba si otro usuario tiene bloqueada la OP para este proveedor (fact_temporalp).
    Paridad con SQL-006. Devuelve None si no hay bloqueo, o dict con codigo_usuario del que bloquea.
    """
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ft.Codigo, ft.Codusuario, u.cod_usuario AS codigo_usuario
                FROM fact_temporalp ft
                INNER JOIN usuarios u ON u.id_usuario = ft.Codusuario
                WHERE ft.Codigo = %s AND COALESCE(ft.visualiza, '') = 'No' AND ft.Codusuario <> %s
                LIMIT 1
                """,
                [to_int_or_none(codigo_proveedor), to_int_or_none(id_usuario_actual)],
            )
            row = cursor.fetchone()
            cursor.close()
        if not row:
            return None
        return {"Codigo": row[0], "Codusuario": row[1], "codigo_usuario": row[2]}
    except Exception as e:
        logger.warning("check_lock_op_proveedor %s: %s", base_empresa, e)
        return None


def acquire_lock_op_proveedor(
    conn: Any,
    codigo_proveedor: int,
    id_usuario: int,
    cod_usuario: str,
) -> None:
    """
    Toma el lock de OP para el proveedor (INSERT en fact_temporalp).
    Debe llamarse dentro de la misma transacción que la OP.
    Semántica VB6: visualiza = 'No'.
    """
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO fact_temporalp (Codigo, Codusuario, visualiza) VALUES (%s, %s, %s)",
            [to_int_or_none(codigo_proveedor), to_int_or_none(id_usuario), "No"],
        )
    finally:
        cursor.close()


def release_lock_op_proveedor(conn: Any, codigo_proveedor: int, id_usuario: int) -> None:
    """
    Libera el lock de OP para el proveedor (DELETE en fact_temporalp).
    Debe llamarse al cerrar/cancelar la OP, dentro de la misma transacción si aplica.
    """
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM fact_temporalp WHERE Codigo = %s AND Codusuario = %s",
            [to_int_or_none(codigo_proveedor), to_int_or_none(id_usuario)],
        )
    finally:
        cursor.close()


def listar_op_factura_para_imputar(
    base_empresa: str,
    codigo_proveedor: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Devuelve (comprobantes_a_cuenta, facturas_para_imputar) para keyAsignaPag.
    Paridad con SQL-008 y SQL-009. Solo lectura.
    """
    cod = to_int_or_none(codigo_proveedor)
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM op_factura
                WHERE Codigo = %s AND COALESCE(Estado, '') = 'N/Canc' AND COALESCE(Saldo, 0) <> 0
                  AND TipoComprobante IN ('OP', 'NC', 'AJC', 'INIC') AND COALESCE(Anulado, '') = 'No'
                ORDER BY NroComprobante
                """,
                [cod],
            )
            rows_cuenta = cursor.fetchall()
            cols = [d[0] for d in cursor.description] if cursor.description else []
            a_cuenta = [dict(zip(cols, r)) for r in rows_cuenta]

            cursor.execute(
                """
                SELECT * FROM op_factura
                WHERE Codigo = %s AND COALESCE(Estado, '') = 'N/Canc' AND COALESCE(Saldo, 0) <> 0
                  AND TipoComprobante IN ('FA', 'FB', 'FC', 'FM', 'ND', 'AJD', 'INID') AND COALESCE(Anulado, '') = 'No'
                ORDER BY NroComprobante
                """,
                [cod],
            )
            rows_fact = cursor.fetchall()
            cols = [d[0] for d in cursor.description] if cursor.description else []
            facturas = [dict(zip(cols, r)) for r in rows_fact]
            cursor.close()
        return (a_cuenta, facturas)
    except Exception as e:
        logger.warning("listar_op_factura_para_imputar %s: %s", base_empresa, e)
        return ([], [])


def hay_facturas_para_op_por_imputacion(
    base_empresa: str,
    codigo_proveedor: int,
) -> bool:
    """
    Paridad con keyPorimp: existe al menos un registro en op_factura para imputar (SQL-007).
    """
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 1 FROM op_factura
                WHERE Codigo = %s AND COALESCE(Estado, '') = 'N/Canc'
                  AND TipoComprobante IN ('FA','FB','FC','FM','ND','INIC','INID','AJD','AJC')
                  AND COALESCE(Anulado, '') = 'No'
                LIMIT 1
                """,
                [to_int_or_none(codigo_proveedor)],
            )
            row = cursor.fetchone()
            cursor.close()
        return row is not None
    except Exception as e:
        logger.warning("hay_facturas_para_op_por_imputacion %s: %s", base_empresa, e)
        return False


def hay_descuentos_para_nc_descuento(
    base_empresa: str,
    codigo_proveedor: int,
) -> bool:
    """
    Paridad con keyNCDesR (SQL-005): existe descuento_op_nc con Computado='No' e importe>0.
    """
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 1 FROM descuento_op_nc
                WHERE CodProveedor = %s AND COALESCE(Computado, '') = 'No' AND COALESCE(importe, 0) > 0
                LIMIT 1
                """,
                [to_int_or_none(codigo_proveedor)],
            )
            row = cursor.fetchone()
            cursor.close()
        return row is not None
    except Exception as e:
        logger.warning("hay_descuentos_para_nc_descuento %s: %s", base_empresa, e)
        return False
