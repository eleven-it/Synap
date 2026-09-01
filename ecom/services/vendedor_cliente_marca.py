"""CRUD MySQL de relaciones ``ecom_vendedor_cliente_marca`` (territorio comercial)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import str_or_default, to_int_or_none

logger = logging.getLogger(__name__)


class ConflictoMarcaCliente(Exception):
    """La marca ya está asignada a otro viajante para el mismo cliente y sucursal."""

    def __init__(self, message: str, dueno: Dict[str, Any]):
        super().__init__(message)
        self.message = message
        self.dueno = dueno


def _mensaje_tabla_ausente(exc: Exception) -> str:
    msg = str(exc)
    if "1146" in msg or "doesn't exist" in msg.lower():
        return (
            "Faltan las tablas ecom_vendedor_cliente_marca. "
            "Ejecutá la migración «E-com — relación Vendedor→Cliente→Sucursal→Marca» "
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


def _etiqueta_sucursal(calle: str, nro: str, id_dom: int) -> Tuple[str, str]:
    calle = (calle or "").strip()
    nro = (nro or "").strip()
    nombre_parts = [p for p in (calle, nro) if p and p != "-"]
    nombre = " ".join(nombre_parts).strip()
    etiqueta = nombre or f"Sucursal #{id_dom}"
    return nombre, etiqueta


def _domicilio_valido_cliente(
    base_empresa: str,
    id_cliente: int,
    id_cliente_domicilio: int,
) -> Tuple[bool, str]:
    """Verifica que el domicilio pertenezca al cliente y esté activo."""
    idc = to_int_or_none(id_cliente)
    idd = to_int_or_none(id_cliente_domicilio)
    if idc is None or idd is None or idd <= 0:
        return False, "Sucursal (id_cliente_domicilio) inválida."
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT 1
                    FROM cliente_domicilio
                    WHERE id_cliente_domicilio = %s
                      AND id_cliente = %s
                      AND COALESCE(anulado, 'No') = 'No'
                    LIMIT 1
                    """,
                    [idd, idc],
                )
                if cursor.fetchone():
                    return True, ""
                return False, "La sucursal no pertenece al cliente o está anulada."
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("_domicilio_valido_cliente: %s", e)
        return False, _mensaje_tabla_ausente(e)


def buscar_dueno_marca_cliente(
    base_empresa: str,
    id_cliente: int,
    cod_marca: int,
    id_cliente_domicilio: int,
) -> Optional[Dict[str, Any]]:
    """Fila activa dueña de (cliente, sucursal, marca), o None."""
    idc = to_int_or_none(id_cliente)
    cm = to_int_or_none(cod_marca)
    idd = to_int_or_none(id_cliente_domicilio)
    if idc is None or cm is None or idd is None:
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
                        t.id_cliente_domicilio,
                        t.CodMarca,
                        COALESCE(v.Nombre, '') AS nombre_viajante
                    FROM ecom_vendedor_cliente_marca t
                    LEFT JOIN viajantes v ON v.CodViajante = t.CodViajante
                    WHERE t.id_cliente = %s
                      AND t.id_cliente_domicilio = %s
                      AND t.CodMarca = %s
                      AND COALESCE(t.anulado, 'No') = 'No'
                    LIMIT 1
                    """,
                    [idc, idd, cm],
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return {
                    "id": int(row[0]),
                    "CodViajante": int(row[1]),
                    "id_cliente": int(row[2]),
                    "id_cliente_domicilio": int(row[3]),
                    "CodMarca": int(row[4]),
                    "nombre_viajante": (row[5] or "").strip(),
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
    id_cliente_domicilio: Optional[int] = None,
    solo_activas: bool = True,
    limit: int = 5000,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Lista relaciones con nombres de viajante / cliente / sucursal / marca."""
    lim = max(1, min(int(limit), 20000))
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
    idd = to_int_or_none(id_cliente_domicilio)
    if idd is not None:
        where.append("t.id_cliente_domicilio = %s")
        params.append(idd)
    params.append(lim)
    sql = f"""
        SELECT
            t.id,
            t.CodViajante,
            COALESCE(v.Nombre, '') AS nombre_viajante,
            t.id_cliente,
            COALESCE(c.nombre_cliente, '') AS nombre_cliente,
            t.id_cliente_domicilio,
            COALESCE(cd.Calle, '') AS calle_sucursal,
            COALESCE(cd.NroCalle, '') AS nro_sucursal,
            t.CodMarca,
            COALESCE(m.NombreMarca, '') AS nombre_marca,
            COALESCE(t.anulado, 'No') AS anulado,
            DATE_FORMAT(t.fecha_alta, '%%d/%%m/%%Y') AS fecha_alta
        FROM ecom_vendedor_cliente_marca t
        LEFT JOIN viajantes v ON v.CodViajante = t.CodViajante
        LEFT JOIN cliente c ON c.Codigo = t.id_cliente
        LEFT JOIN cliente_domicilio cd ON cd.id_cliente_domicilio = t.id_cliente_domicilio
        LEFT JOIN marca m ON m.CodMarca = t.CodMarca
        WHERE {' AND '.join(where)}
        ORDER BY v.Nombre ASC, c.nombre_cliente ASC, cd.Calle ASC, m.NombreMarca ASC
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
                    id_dom = int(r[5] or 0)
                    nombre_suc, etiqueta_suc = _etiqueta_sucursal(r[6], r[7], id_dom)
                    rows.append(
                        {
                            "id": int(r[0]),
                            "CodViajante": int(r[1]),
                            "nombre_viajante": (r[2] or "").strip(),
                            "id_cliente": int(r[3]),
                            "nombre_cliente": (r[4] or "").strip(),
                            "id_cliente_domicilio": id_dom,
                            "nombre_sucursal": nombre_suc,
                            "etiqueta_sucursal": etiqueta_suc,
                            "CodMarca": int(r[8]),
                            "nombre_marca": (r[9] or "").strip(),
                            "anulado": (r[10] or "No").strip(),
                            "fecha_alta": r[11] or "",
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
    id_cliente_domicilio: int,
    *,
    usuario_mod: str = "-",
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Crea relación activa. Si (cliente, sucursal, marca) ya tiene dueño distinto → ConflictoMarcaCliente.
    Si el mismo viajante ya la tiene → idempotente (devuelve la fila).
    """
    cv = to_int_or_none(cod_viajante)
    idc = to_int_or_none(id_cliente)
    cm = to_int_or_none(cod_marca)
    idd = to_int_or_none(id_cliente_domicilio)
    if cv is None or idc is None or cm is None or idd is None or idd <= 0:
        return False, "Faltan CodViajante, id_cliente, id_cliente_domicilio (>0) o CodMarca válidos.", None
    um = (usuario_mod or "-")[:60]

    ok_dom, err_dom = _domicilio_valido_cliente(base_empresa, idc, idd)
    if not ok_dom:
        return False, err_dom, None

    dueno = buscar_dueno_marca_cliente(base_empresa, idc, cm, idd)
    if dueno:
        if int(dueno["CodViajante"]) == cv:
            return True, "La relación ya existía.", dueno
        nombre = dueno.get("nombre_viajante") or f"cod {dueno['CodViajante']}"
        raise ConflictoMarcaCliente(
            f"La marca ya está asignada a {nombre} para este cliente y sucursal.",
            {
                "CodViajante": dueno["CodViajante"],
                "nombre_viajante": dueno.get("nombre_viajante") or "",
                "id": dueno.get("id"),
                "id_cliente_domicilio": dueno.get("id_cliente_domicilio"),
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
                        (CodViajante, id_cliente, id_cliente_domicilio, CodMarca, anulado, usuario_mod)
                    VALUES (%s, %s, %s, %s, 'No', %s)
                    """,
                    [cv, idc, idd, cm, um],
                )
                new_id = int(cursor.lastrowid)
                conn.commit()
                return (
                    True,
                    "Relación creada.",
                    {
                        "id": new_id,
                        "CodViajante": cv,
                        "id_cliente": idc,
                        "id_cliente_domicilio": idd,
                        "CodMarca": cm,
                    },
                )
            except Exception as e:
                conn.rollback()
                dueno2 = buscar_dueno_marca_cliente(base_empresa, idc, cm, idd)
                if dueno2 and int(dueno2["CodViajante"]) != cv:
                    nombre = dueno2.get("nombre_viajante") or f"cod {dueno2['CodViajante']}"
                    raise ConflictoMarcaCliente(
                        f"La marca ya está asignada a {nombre} para este cliente y sucursal.",
                        {
                            "CodViajante": dueno2["CodViajante"],
                            "nombre_viajante": dueno2.get("nombre_viajante") or "",
                            "id": dueno2.get("id"),
                            "id_cliente_domicilio": dueno2.get("id_cliente_domicilio"),
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


def _normalizar_enteros_positivos(valores: List[Any]) -> List[int]:
    """Enteros únicos positivos, preservando el orden de primera aparición."""
    vistos: set[int] = set()
    resultado: List[int] = []
    for raw in valores or []:
        n = to_int_or_none(raw)
        if n is None or n <= 0 or n in vistos:
            continue
        vistos.add(n)
        resultado.append(n)
    return resultado


def _normalizar_ids_domicilio(ids_cliente_domicilio: List[Any]) -> List[int]:
    """Ids de sucursal únicos positivos, preservando el orden de primera aparición."""
    return _normalizar_enteros_positivos(ids_cliente_domicilio)


def crear_ternas_lote(
    base_empresa: str,
    cod_viajante: int,
    id_cliente: int,
    cod_marca: int,
    ids_cliente_domicilio: List[Any],
    *,
    usuario_mod: str = "-",
    cod_marcas: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Crea relaciones en lote (mismo vendedor y cliente × cada sucursal × cada marca).
    No aborta ante el primer conflicto; devuelve resumen por categoría.
    ``cod_marcas`` tiene prioridad sobre ``cod_marca`` (compat. una sola marca).
    """
    ids_norm = _normalizar_ids_domicilio(ids_cliente_domicilio)
    marcas_norm = _normalizar_enteros_positivos(
        cod_marcas if cod_marcas is not None else [cod_marca]
    )
    vacio: Dict[str, Any] = {
        "creadas": [],
        "ya_existian": [],
        "conflictos": [],
        "errores": [],
        "n_creadas": 0,
        "n_ya_existian": 0,
        "n_conflictos": 0,
        "n_errores": 0,
    }
    if not ids_norm or not marcas_norm:
        return vacio

    creadas: List[Dict[str, Any]] = []
    ya_existian: List[Dict[str, Any]] = []
    conflictos: List[Dict[str, Any]] = []
    errores: List[Dict[str, Any]] = []

    for cm in marcas_norm:
        for idd in ids_norm:
            try:
                ok, msg, terna = crear_terna(
                    base_empresa,
                    cod_viajante,
                    id_cliente,
                    cm,
                    idd,
                    usuario_mod=usuario_mod,
                )
                if ok:
                    msg_lower = (msg or "").lower()
                    if "ya existía" in msg_lower or "ya existia" in msg_lower:
                        if terna:
                            ya_existian.append(terna)
                    elif terna:
                        creadas.append(terna)
                else:
                    errores.append(
                        {
                            "id_cliente_domicilio": idd,
                            "CodMarca": cm,
                            "error": msg,
                        }
                    )
            except ConflictoMarcaCliente as exc:
                conflictos.append(
                    {
                        "id_cliente_domicilio": idd,
                        "CodMarca": cm,
                        "error": exc.message,
                        "dueno": exc.dueno,
                    }
                )

    return {
        "creadas": creadas,
        "ya_existian": ya_existian,
        "conflictos": conflictos,
        "errores": errores,
        "n_creadas": len(creadas),
        "n_ya_existian": len(ya_existian),
        "n_conflictos": len(conflictos),
        "n_errores": len(errores),
    }


def anular_terna(
    base_empresa: str,
    id_terna: int,
    *,
    usuario_mod: str = "-",
) -> Tuple[bool, str]:
    """Soft-delete: anulado = Si (libera unique activo)."""
    tid = to_int_or_none(id_terna)
    if tid is None:
        return False, "Id de relación inválido."
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
                    return False, "Relación no encontrada o ya anulada."
                return True, "Relación anulada."
            except Exception as e:
                conn.rollback()
                logger.exception("anular_terna: %s", e)
                return False, _mensaje_tabla_ausente(e)
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("anular_terna: %s", e)
        return False, _mensaje_tabla_ausente(e)


def anular_ternas_lote(
    base_empresa: str,
    ids_terna: List[Any],
    *,
    usuario_mod: str = "-",
) -> Dict[str, Any]:
    """Soft-delete en lote: ``anulado = Si`` para cada id activo. No aborta a medias."""
    ids_norm = _normalizar_enteros_positivos(ids_terna)
    vacio: Dict[str, Any] = {
        "n_solicitadas": 0,
        "n_anuladas": 0,
        "n_omitidas": 0,
        "ids_anuladas": [],
    }
    if not ids_norm:
        return vacio
    um = (usuario_mod or "-")[:60]
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                placeholders = ",".join(["%s"] * len(ids_norm))
                cursor.execute(
                    f"""
                    SELECT id
                    FROM ecom_vendedor_cliente_marca
                    WHERE id IN ({placeholders})
                      AND COALESCE(anulado, 'No') = 'No'
                    """,
                    ids_norm,
                )
                ids_activas = [int(r[0]) for r in cursor.fetchall()]
                if ids_activas:
                    ph_upd = ",".join(["%s"] * len(ids_activas))
                    cursor.execute(
                        f"""
                        UPDATE ecom_vendedor_cliente_marca
                        SET anulado = 'Si', usuario_mod = %s
                        WHERE id IN ({ph_upd})
                          AND COALESCE(anulado, 'No') = 'No'
                        """,
                        [um, *ids_activas],
                    )
                conn.commit()
                return {
                    "n_solicitadas": len(ids_norm),
                    "n_anuladas": len(ids_activas),
                    "n_omitidas": len(ids_norm) - len(ids_activas),
                    "ids_anuladas": ids_activas,
                }
            except Exception as e:
                conn.rollback()
                logger.exception("anular_ternas_lote: %s", e)
                return {
                    **vacio,
                    "n_solicitadas": len(ids_norm),
                    "error": _mensaje_tabla_ausente(e),
                }
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("anular_ternas_lote: %s", e)
        return {
            **vacio,
            "n_solicitadas": len(ids_norm),
            "error": _mensaje_tabla_ausente(e),
        }


def buscar_sucursales_cliente(
    base_empresa: str,
    id_cliente: int,
    q: str = "",
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """Domicilios activos del cliente para predictivo de config (sin filtrar por relación)."""
    idc = to_int_or_none(id_cliente)
    if idc is None:
        return []
    lim = max(1, min(int(limit), 100))
    where = [
        "cm.id_cliente = %s",
        "COALESCE(cm.anulado, 'No') = 'No'",
    ]
    params: List[Any] = [idc]
    q = (q or "").strip()
    if q:
        # Coincide id (exacto o parcial como texto), calle o nro — no devolver el listado completo.
        where.append(
            "("
            "CAST(cm.id_cliente_domicilio AS CHAR) LIKE %s "
            "OR cm.Calle LIKE %s "
            "OR cm.NroCalle LIKE %s "
            "OR CONCAT(COALESCE(cm.Calle,''), ' ', COALESCE(cm.NroCalle,'')) LIKE %s"
            ")"
        )
        like = f"%{q}%"
        params.extend([like, like, like, like])
    params.append(lim)
    sql = f"""
        SELECT
            cm.id_cliente_domicilio,
            COALESCE(cm.Calle, '') AS calle,
            COALESCE(cm.NroCalle, '') AS nro
        FROM cliente_domicilio AS cm
        WHERE {' AND '.join(where)}
        ORDER BY cm.Calle ASC, cm.NroCalle ASC
        LIMIT %s
    """
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                out = []
                for r in cursor.fetchall():
                    id_dom = int(r[0])
                    nombre, etiqueta = _etiqueta_sucursal(r[1], r[2], id_dom)
                    out.append(
                        {
                            "id_cliente_domicilio": id_dom,
                            "nombre": nombre,
                            "etiqueta": etiqueta,
                        }
                    )
                return out
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("buscar_sucursales_cliente: %s", e)
        return []


def sucursales_asignadas_viajante_cliente(
    base_empresa: str,
    cod_viajante: int,
    id_cliente: int,
) -> List[int]:
    """Ids de sucursal con al menos una relación activa para (viajante, cliente)."""
    cv = to_int_or_none(cod_viajante)
    idc = to_int_or_none(id_cliente)
    if cv is None or idc is None:
        return []
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT DISTINCT id_cliente_domicilio
                    FROM ecom_vendedor_cliente_marca
                    WHERE CodViajante = %s
                      AND id_cliente = %s
                      AND COALESCE(anulado, 'No') = 'No'
                      AND COALESCE(id_cliente_domicilio, 0) > 0
                    ORDER BY id_cliente_domicilio ASC
                    """,
                    [cv, idc],
                )
                return [int(r[0]) for r in cursor.fetchall() if r and r[0] is not None]
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("sucursales_asignadas_viajante_cliente: %s", e)
        return []


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
