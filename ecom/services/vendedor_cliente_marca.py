"""CRUD MySQL de ternas ``ecom_vendedor_cliente_marca`` (territorio comercial)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import str_or_default, to_int_or_none

logger = logging.getLogger(__name__)


class ConflictoMarcaCliente(Exception):
    """La marca ya está asignada a otro viajante para el mismo cliente."""

    def __init__(self, message: str, dueno: Dict[str, Any]):
        super().__init__(message)
        self.message = message
        self.dueno = dueno


def _mensaje_tabla_ausente(exc: Exception) -> str:
    msg = str(exc)
    if "1146" in msg or "doesn't exist" in msg.lower():
        return (
            "Faltan las tablas ecom_vendedor_cliente_marca. "
            "Ejecutá la migración «E-com — terna Vendedor→Cliente→Marca» "
            "en Archivo → Migración esquema MySQL."
        )
    return msg


def _usuario_mod(sess_user: Optional[Dict[str, Any]]) -> str:
    if not sess_user:
        return "-"
    raw = str_or_default(
        sess_user.get("cod_usuario") or sess_user.get("nombre_usuario"),
        "-",
    )
    return (raw or "-")[:60]


def buscar_dueno_marca_cliente(
    base_empresa: str,
    id_cliente: int,
    cod_marca: int,
) -> Optional[Dict[str, Any]]:
    """Fila activa dueña de (cliente, marca), o None."""
    idc = to_int_or_none(id_cliente)
    cm = to_int_or_none(cod_marca)
    if idc is None or cm is None:
        return None
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT
                        t.id,
                        t.CodViajante,
                        t.id_cliente,
                        t.CodMarca,
                        COALESCE(v.Nombre, '') AS nombre_viajante
                    FROM ecom_vendedor_cliente_marca t
                    LEFT JOIN viajantes v ON v.CodViajante = t.CodViajante
                    WHERE t.id_cliente = %s
                      AND t.CodMarca = %s
                      AND COALESCE(t.anulado, 'No') = 'No'
                    LIMIT 1
                    """,
                    [idc, cm],
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return {
                    "id": int(row[0]),
                    "CodViajante": int(row[1]),
                    "id_cliente": int(row[2]),
                    "CodMarca": int(row[3]),
                    "nombre_viajante": (row[4] or "").strip(),
                }
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("buscar_dueno_marca_cliente: %s", e)
        return None


def listar_ternas(
    base_empresa: str,
    *,
    cod_viajante: Optional[int] = None,
    id_cliente: Optional[int] = None,
    solo_activas: bool = True,
    limit: int = 200,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Lista ternas con nombres de viajante / cliente / marca."""
    lim = max(1, min(int(limit), 500))
    where = ["1=1"]
    params: List[Any] = []
    if solo_activas:
        where.append("COALESCE(t.anulado, 'No') = 'No'")
    cv = to_int_or_none(cod_viajante)
    if cv is not None:
        where.append("t.CodViajante = %s")
        params.append(cv)
    idc = to_int_or_none(id_cliente)
    if idc is not None:
        where.append("t.id_cliente = %s")
        params.append(idc)
    params.append(lim)
    sql = f"""
        SELECT
            t.id,
            t.CodViajante,
            COALESCE(v.Nombre, '') AS nombre_viajante,
            t.id_cliente,
            COALESCE(c.nombre_cliente, '') AS nombre_cliente,
            t.CodMarca,
            COALESCE(m.NombreMarca, '') AS nombre_marca,
            COALESCE(t.anulado, 'No') AS anulado,
            DATE_FORMAT(t.fecha_alta, '%%d/%%m/%%Y') AS fecha_alta
        FROM ecom_vendedor_cliente_marca t
        LEFT JOIN viajantes v ON v.CodViajante = t.CodViajante
        LEFT JOIN cliente c ON c.Codigo = t.id_cliente
        LEFT JOIN marca m ON m.CodMarca = t.CodMarca
        WHERE {' AND '.join(where)}
        ORDER BY v.Nombre ASC, c.nombre_cliente ASC, m.NombreMarca ASC
        LIMIT %s
    """
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                rows = []
                for r in cursor.fetchall():
                    rows.append(
                        {
                            "id": int(r[0]),
                            "CodViajante": int(r[1]),
                            "nombre_viajante": (r[2] or "").strip(),
                            "id_cliente": int(r[3]),
                            "nombre_cliente": (r[4] or "").strip(),
                            "CodMarca": int(r[5]),
                            "nombre_marca": (r[6] or "").strip(),
                            "anulado": (r[7] or "No").strip(),
                            "fecha_alta": r[8] or "",
                        }
                    )
                return True, "", rows
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("listar_ternas: %s", e)
        return False, _mensaje_tabla_ausente(e), []


def crear_terna(
    base_empresa: str,
    cod_viajante: int,
    id_cliente: int,
    cod_marca: int,
    *,
    usuario_mod: str = "-",
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Crea terna activa. Si (cliente, marca) ya tiene dueño distinto → ConflictoMarcaCliente.
    Si el mismo viajante ya la tiene → idempotente (devuelve la fila).
    """
    cv = to_int_or_none(cod_viajante)
    idc = to_int_or_none(id_cliente)
    cm = to_int_or_none(cod_marca)
    if cv is None or idc is None or cm is None:
        return False, "Faltan CodViajante, id_cliente o CodMarca válidos.", None
    um = (usuario_mod or "-")[:60]

    dueno = buscar_dueno_marca_cliente(base_empresa, idc, cm)
    if dueno:
        if int(dueno["CodViajante"]) == cv:
            return True, "La terna ya existía.", dueno
        nombre = dueno.get("nombre_viajante") or f"cod {dueno['CodViajante']}"
        raise ConflictoMarcaCliente(
            f"La marca ya está asignada a {nombre} para este cliente.",
            {
                "CodViajante": dueno["CodViajante"],
                "nombre_viajante": dueno.get("nombre_viajante") or "",
                "id": dueno.get("id"),
            },
        )

    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO ecom_vendedor_cliente_marca
                        (CodViajante, id_cliente, CodMarca, anulado, usuario_mod)
                    VALUES (%s, %s, %s, 'No', %s)
                    """,
                    [cv, idc, cm, um],
                )
                new_id = int(cursor.lastrowid)
                conn.commit()
                return (
                    True,
                    "Terna creada.",
                    {
                        "id": new_id,
                        "CodViajante": cv,
                        "id_cliente": idc,
                        "CodMarca": cm,
                    },
                )
            except Exception as e:
                conn.rollback()
                # Carrera: unique
                dueno2 = buscar_dueno_marca_cliente(base_empresa, idc, cm)
                if dueno2 and int(dueno2["CodViajante"]) != cv:
                    nombre = dueno2.get("nombre_viajante") or f"cod {dueno2['CodViajante']}"
                    raise ConflictoMarcaCliente(
                        f"La marca ya está asignada a {nombre} para este cliente.",
                        {
                            "CodViajante": dueno2["CodViajante"],
                            "nombre_viajante": dueno2.get("nombre_viajante") or "",
                            "id": dueno2.get("id"),
                        },
                    ) from e
                logger.exception("crear_terna: %s", e)
                return False, _mensaje_tabla_ausente(e), None
            finally:
                cursor.close()
    except ConflictoMarcaCliente:
        raise
    except Exception as e:
        logger.exception("crear_terna: %s", e)
        return False, _mensaje_tabla_ausente(e), None


def anular_terna(
    base_empresa: str,
    id_terna: int,
    *,
    usuario_mod: str = "-",
) -> Tuple[bool, str]:
    """Soft-delete: anulado = Si (libera unique activo)."""
    tid = to_int_or_none(id_terna)
    if tid is None:
        return False, "Id de terna inválido."
    um = (usuario_mod or "-")[:60]
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    UPDATE ecom_vendedor_cliente_marca
                    SET anulado = 'Si', usuario_mod = %s
                    WHERE id = %s AND COALESCE(anulado, 'No') = 'No'
                    """,
                    [um, tid],
                )
                affected = cursor.rowcount
                conn.commit()
                if affected < 1:
                    return False, "Terna no encontrada o ya anulada."
                return True, "Terna anulada."
            except Exception as e:
                conn.rollback()
                logger.exception("anular_terna: %s", e)
                return False, _mensaje_tabla_ausente(e)
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("anular_terna: %s", e)
        return False, _mensaje_tabla_ausente(e)


def buscar_clientes_activos(
    base_empresa: str,
    q: str = "",
    limit: int = 30,
) -> List[Dict[str, Any]]:
    q = (q or "").strip()
    lim = max(1, min(int(limit), 100))
    where = ["cliente.Estado = 'Activo'", "cliente.Codigo <> 1"]
    params: List[Any] = []
    if q:
        qi = to_int_or_none(q)
        if qi is not None:
            where.append(
                "(cliente.Codigo = %s OR cliente.nombre_cliente LIKE %s OR cliente.id_manual_cli LIKE %s)"
            )
            params.extend([qi, f"%{q}%", f"%{q}%"])
        else:
            where.append(
                "(cliente.nombre_cliente LIKE %s OR cliente.id_manual_cli LIKE %s)"
            )
            params.extend([f"%{q}%", f"%{q}%"])
    params.append(lim)
    sql = f"""
        SELECT cliente.Codigo, COALESCE(cliente.nombre_cliente, '') AS nombre
        FROM cliente
        WHERE {' AND '.join(where)}
        ORDER BY cliente.nombre_cliente ASC
        LIMIT %s
    """
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                return [
                    {
                        "id_cliente": int(r[0]),
                        "nombre": (r[1] or "").strip(),
                        "etiqueta": f"{(r[1] or '').strip()} (cod: {int(r[0])})",
                    }
                    for r in cursor.fetchall()
                ]
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("buscar_clientes_activos: %s", e)
        return []


def buscar_marcas_activas(
    base_empresa: str,
    q: str = "",
    limit: int = 30,
) -> List[Dict[str, Any]]:
    q = (q or "").strip()
    lim = max(1, min(int(limit), 100))
    where = ["COALESCE(marca.anulado, 'No') = 'No'"]
    params: List[Any] = []
    if q:
        qi = to_int_or_none(q)
        if qi is not None:
            where.append("(marca.CodMarca = %s OR marca.NombreMarca LIKE %s)")
            params.extend([qi, f"%{q}%"])
        else:
            where.append("marca.NombreMarca LIKE %s")
            params.append(f"%{q}%")
    params.append(lim)
    sql = f"""
        SELECT marca.CodMarca, COALESCE(marca.NombreMarca, '') AS nombre
        FROM marca
        WHERE {' AND '.join(where)}
        ORDER BY marca.NombreMarca ASC
        LIMIT %s
    """
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                return [
                    {
                        "CodMarca": int(r[0]),
                        "nombre": (r[1] or "").strip(),
                        "etiqueta": f"{(r[1] or '').strip()} (cod: {int(r[0])})",
                    }
                    for r in cursor.fetchall()
                ]
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("buscar_marcas_activas: %s", e)
        return []
