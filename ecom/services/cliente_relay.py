"""
Relays clientes mayoristapp (paridad ``relay-clientes.php`` — búsqueda y sesión).

SQL parametrizado; filtros por vendedor alineados a ``buscarCliente`` en PHP.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none

from ecom.services.vendedor_asignacion_sql import where_vendedor_cliente


def _si_no(val: Any, default: str = "No") -> str:
    if val is None:
        return default
    s = str(val).strip().lower()
    if s in ("si", "sí", "yes", "1", "true"):
        return "Si"
    return "No"


def cod_viajante_desde_sesion_usuario(sess_user: Dict[str, Any]) -> Optional[int]:
    """``CodViajante`` del vendedor logueado (Synap suele usar ``id_vendedor_usr``)."""
    return to_int_or_none(
        sess_user.get("id_vendedor_usr")
        or sess_user.get("CodViajante")
        or sess_user.get("cod_viajante")
    )


def vendedor_a_cargo_desde_sesion(sess_user: Dict[str, Any]) -> List[int]:
    raw = sess_user.get("vendedor_a_cargo")
    if raw is None:
        return []
    if isinstance(raw, str):
        # posible JSON o lista separada por comas
        raw = raw.strip()
        if raw.startswith("["):
            try:
                import json

                raw = json.loads(raw)
            except Exception:
                return []
        else:
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            out = []
            for p in parts:
                n = to_int_or_none(p)
                if n is not None:
                    out.append(n)
            return out
    if isinstance(raw, (list, tuple)):
        out = []
        for x in raw:
            n = to_int_or_none(x)
            if n is not None:
                out.append(n)
        return out
    return []


def _where_viajante(
    sess_user: Dict[str, Any],
    base_empresa: str = "",
) -> tuple[str, List[Any]]:
    """
    Restricción ``CodViajante`` como en PHP (``todos_clientes``, supervisor, ``vendedor_a_cargo``).

    Si ``configuracion_ecom.ecom_fuente_vendedor_cliente`` = ``tabla``, usa
    ``vendedores_clientes_asignacion`` (sin sincronizar con ``cliente.CodViajante``).
    """
    if base_empresa:
        return where_vendedor_cliente(base_empresa, sess_user)
    return where_vendedor_cliente("", sess_user)


def _patron_texto_busqueda(patron: str) -> tuple[Optional[str], List[Any]]:
    """
    Paridad PHP: palabras con ``\\w+``; varias palabras unidas con ``%`` para un único LIKE ``%…%``.
    """
    s = (patron or "").strip()
    if not s:
        return None, []
    words = re.findall(r"\w+", s, flags=re.UNICODE)
    if not words:
        return None, []
    lista = words[0] if len(words) == 1 else "%".join(words)
    p = f"%{lista}%"
    return p, [p, p]


def cliente_accesible_para_sesion(
    base_empresa: str,
    codigo_cliente: int,
    sess_user: Dict[str, Any],
) -> bool:
    """
    True si el cliente existe y cumple los mismos filtros de vendedor que la búsqueda.
    """
    rows, err = buscar_clientes_relay(
        base_empresa,
        modo_busqueda="codigo",
        patron_texto="",
        codigo_cliente=str(codigo_cliente),
        sess_user=sess_user,
        limit=1,
    )
    if err:
        return False
    return len(rows) > 0


def buscar_clientes_relay(
    base_empresa: str,
    *,
    modo_busqueda: str,
    patron_texto: str,
    codigo_cliente: str,
    sess_user: Dict[str, Any],
    limit: int = 10,
) -> tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Devuelve ``(filas, error)``. Si error, filas vacías.

    ``modo_busqueda``: ``codigo`` | ``texto`` (paridad ``claseBusqueda`` / ``modoBus``).
    """
    modo = (modo_busqueda or "").strip().lower()
    usa_manual = _si_no(sess_user.get("usa_id_manual"), "No")

    cod_txt = (codigo_cliente or "").strip()
    pat = (patron_texto or "").strip()

    if modo == "codigo":
        if not cod_txt:
            return [], "ingrese_busqueda"
    elif modo == "texto":
        if not pat:
            return [], "ingrese_busqueda"
    else:
        return [], "modo_invalido"

    where_extra: List[str] = []
    params: List[Any] = []

    if modo == "codigo":
        cod_int = to_int_or_none(cod_txt)
        if cod_int is None:
            return [], "codigo_invalido"
        where_extra.append("cliente.Codigo = %s")
        params.append(cod_int)
    elif modo == "texto":
        p_tuple = _patron_texto_busqueda(pat)
        if p_tuple[0] is None:
            return [], "patron_vacio"
        p_like, p_params = p_tuple
        if usa_manual == "Si":
            where_extra.append(
                "(cliente.nombre_cliente LIKE %s OR cliente.id_manual_cli LIKE %s)"
            )
            params.extend(p_params)
        else:
            where_extra.append(
                "(cliente.nombre_cliente LIKE %s OR CAST(cliente.Codigo AS CHAR) LIKE %s)"
            )
            params.extend(p_params)

    w_viaj, p_viaj = _where_viajante(sess_user, base_empresa)
    params.extend(p_viaj)

    lim = max(1, min(int(limit), 50))

    where_sql = " AND ".join(where_extra)
    sql = f"""
        SELECT
            cliente.nombre_cliente AS nombre_cliente,
            cliente.Codigo AS codigo,
            cliente.Estado AS estado,
            cliente.saldo AS saldo,
            cliente.telefono AS telefono,
            cliente.ListaPrecio AS lista_precio,
            cliente.Email AS email,
            cliente.EmailContacto AS email_contacto,
            cliente.id_manual_cli AS id_manual_cli,
            cliente.CodViajante AS cod_viajante,
            Tipo_Cliente.NombreTipoCliente AS nombre_tipo_cliente,
            Contribuyentes.Abreviado AS condicion_iva
        FROM cliente
        LEFT JOIN tipo_cliente AS Tipo_Cliente ON cliente.TipoCliente = Tipo_Cliente.IDTipoCliente
        LEFT JOIN contribuyentes ON contribuyentes.IDIva = cliente.IDIva
        WHERE cliente.Codigo <> 1
          AND cliente.Estado = 'Activo'
          AND {where_sql}
          {w_viaj}
        ORDER BY cliente.nombre_cliente
        LIMIT %s
    """
    params.append(lim)

    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            item = dict(zip(cols, row))
            out.append(_json_safe_row(item))
    return out, None


def cliente_accesible_por_sesion(
    base_empresa: str,
    codigo_cliente: int,
    sess_user: Dict[str, Any],
) -> bool:
    """
    El cliente existe, está activo y cumple restricción de vendedor (paridad búsqueda).
    """
    cod_int = to_int_or_none(codigo_cliente)
    if cod_int is None or cod_int == 1:
        return False
    w_viaj, p_viaj = _where_viajante(sess_user, base_empresa)
    params: List[Any] = [cod_int]
    params.extend(p_viaj)
    sql = f"""
        SELECT 1
        FROM cliente
        WHERE cliente.Codigo = %s
          AND cliente.Estado = 'Activo'
          {w_viaj}
        LIMIT 1
    """
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchone() is not None


def _json_safe_row(item: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in list(item.items()):
        if isinstance(v, Decimal):
            item[k] = float(v)
        elif isinstance(v, bytes):
            item[k] = v.decode("utf-8", errors="replace")
    return item


# Paridad ``seleccionarComprobante`` en PHP (rutas relativas al portal mayorista).
MAYORISTAPP_FORMULARIO_COMPROBANTE: Dict[int, tuple[str, str]] = {
    0: ("pedido", "alta_pedido.php"),
    1: ("remitoSistema", "lista-facturas-sin-stock.php"),
    2: ("remitoTalonario", "lista-facturas-sin-stock.php"),
    3: ("presupuesto", "alta_presupuesto.php"),
    4: ("recibo", "recibo/alta_recibo.php"),
    5: ("devolucion", "alta-devolucion.php"),
}
