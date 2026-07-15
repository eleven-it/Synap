"""
Relays de precios mayoristapp: lista de precios y promociones (paridad PHP).

Fuentes: ``relay-lista-precio.php``, ``relay-promociones.php``, ``control.php`` (armado de sesión).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none

# Normalización de ``$objCliente->listaPrecio`` → sufijo columna ``articulo.promocion_*`` y ``articulo_promo_intervalo.*``
_PROMO_LISTA_ARTICULO: Dict[str, str] = {
    "listaoficial": "promocion_listaoficial",
    "lista1": "promocion_lista1",
    "lista2": "promocion_lista2",
    "lista3": "promocion_lista3",
    "lista4": "promocion_lista4",
    "lista5": "promocion_lista5",
}

# Tabla ``articulo_promo_intervalo`` solo tiene lista1..lista5 (sin oficial en schema documentado).
_INTERVALO_LISTA_COL: Dict[str, str] = {
    "lista1": "lista1",
    "lista2": "lista2",
    "lista3": "lista3",
    "lista4": "lista4",
    "lista5": "lista5",
}


def _normalizar_clave_lista_precio(raw: Optional[str]) -> Optional[str]:
    if raw is None or str(raw).strip() == "":
        return None
    return str(raw).replace(" ", "").lower()


def columna_promocion_articulo(lista_precio_cliente: Optional[str]) -> Optional[str]:
    """Mapea texto tipo ``Lista 1`` / ``Lista Oficial`` a columna ``articulo.promocion_*``."""
    key = _normalizar_clave_lista_precio(lista_precio_cliente)
    if not key:
        return None
    return _PROMO_LISTA_ARTICULO.get(key)


def condiciones_venta_relay_json(
    base_empresa: str,
    *,
    id_condicion_cliente: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Catálogo ``cond_venta`` para desplegables de cabecera comercial.

    Columnas legacy confirmadas: ``Codigo``, ``Descripcion``, ``Dias``.
    """
    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    cli_cv = to_int_or_none(id_condicion_cliente)
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT Codigo, COALESCE(Descripcion, '') AS Descripcion, COALESCE(Dias, 0) AS Dias
            FROM cond_venta
            WHERE COALESCE(anulado, 'No') <> 'Si'
            ORDER BY Codigo
            """
        )
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            item = _json_safe(dict(zip(cols, row)))
            item["selected"] = cli_cv is not None and int(item.get("Codigo") or 0) == cli_cv
            out.append(item)
    return out


def lista_precio_relay_json(
    base_empresa: str,
    *,
    cod_lista_precio_cliente: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Paridad ``relay-lista-precio.php``: listas 1..5 con ``name`` = texto + nombre descriptivo,
    ``selected`` según cliente o lista por defecto de ``configuracion``.
    """
    pool = get_mysql_pool()
    lista_defecto_num = 1
    desc = {1: "Lista 1", 2: "Lista 2", 3: "Lista 3", 4: "Lista 4", 5: "Lista 5"}
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT lista_precio_web,
                   desc_util1, desc_util2, desc_util3, desc_util4, desc_util5
            FROM configuracion
            WHERE id_configuracion = 1
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if row:
            lista_defecto_num = to_int_or_none(row[0]) or 1
            if lista_defecto_num < 1 or lista_defecto_num > 5:
                lista_defecto_num = 1
            for i in range(1, 6):
                d = row[i]
                if d is not None and str(d).strip():
                    desc[i] = str(d).strip()

    lista_defecto_texto = f"Lista {lista_defecto_num}"
    out: List[Dict[str, Any]] = []
    cli = to_int_or_none(cod_lista_precio_cliente)
    for i in range(1, 6):
        texto = f"Lista {i}"
        nombre = desc.get(i, texto)
        name = f"{texto} {nombre}".strip()
        selected = False
        if cli is not None:
            if cli == i and 1 <= cli <= 5:
                selected = True
        else:
            if texto == lista_defecto_texto:
                selected = True
        out.append({"id": i, "name": name, "selected": selected})
    return out


def promociones_relay_payload(
    base_empresa: str,
    *,
    lista_precio_cliente: Optional[str] = None,
    id_categoria: Optional[int] = None,
    id_rubro: Optional[int] = None,
    id_subrubro: Optional[int] = None,
    id_marca: Optional[int] = None,
    id_modelo: Optional[int] = None,
    fecha_ref: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Paridad lógica ``relay-promociones.php`` (respuesta JSON en Synap; el PHP armaba HTML).

    Incluye artículos en promoción vigente y mapa de intervalos por cantidad desde
    ``articulo_promo_intervalo`` (misma regla de lista que el PHP cuando hay cliente).
    """
    hoy = fecha_ref or date.today()
    hoy_s = hoy.strftime("%Y-%m-%d")
    col_promo = columna_promocion_articulo(lista_precio_cliente)
    col_intervalo = _INTERVALO_LISTA_COL.get(_normalizar_clave_lista_precio(lista_precio_cliente) or "")

    where_extra: List[str] = []
    params_art: List[Any] = [hoy_s, hoy_s]

    if col_promo:
        where_extra.append(f"articulo.{col_promo} = %s")
        params_art.append("Si")

    if id_categoria is not None:
        where_extra.append("rubro.id_categoria = %s")
        params_art.append(id_categoria)
    if id_rubro is not None:
        where_extra.append("articulo.CodigoRubro = %s")
        params_art.append(id_rubro)
    if id_subrubro is not None:
        where_extra.append("articulo.IDSubRubro = %s")
        params_art.append(id_subrubro)
    if id_marca is not None:
        where_extra.append("articulo.CodigoMarca = %s")
        params_art.append(id_marca)
    if id_modelo is not None:
        where_extra.append("articulo.CodigoModelo = %s")
        params_art.append(id_modelo)

    filtro = ""
    if where_extra:
        filtro = " AND " + " AND ".join(where_extra)

    sql_art = f"""
        SELECT
            articulo.id_manual,
            articulo.tipo_art,
            articulo.Alicuota,
            articulo.AlicuotaIB,
            marca.NombreMarca AS Marca,
            modelo.NombreModelo AS Modelo,
            articulo.IDArt,
            articulo.IDSubRubro,
            articulo.CodigoSubRubro,
            articulo.CodigoRubro,
            articulo.CodigoArticuloT,
            articulo.NombreArticulo,
            iva.Alicuota AS Alic,
            cat.nombre_categoria AS NombCategoria,
            rubro.NombreRubro AS NombRub,
            subrubro.NombreSubRubro AS NombSubRub,
            articulo.promocion,
            articulo.promocion_por,
            articulo.promocion_cant,
            articulo.promocion_alcance,
            articulo.promocion_tipo,
            DATE_FORMAT(articulo.promocion_vigencia_desde, '%%d/%%m/%%Y') AS promocion_vigencia_desde,
            DATE_FORMAT(articulo.promocion_vigencia_hasta, '%%d/%%m/%%Y') AS promocion_vigencia_hasta
        FROM articulo
        LEFT JOIN iva ON articulo.Alicuota = iva.id
        LEFT JOIN subrubro ON subrubro.IDSubRubro = articulo.IDSubRubro
        LEFT JOIN rubro ON rubro.CodigoRubro = articulo.CodigoRubro
        LEFT JOIN rubro_categoria AS cat ON cat.id_categoria = rubro.id_categoria
        LEFT JOIN modelo ON modelo.CodModelo = articulo.CodigoModelo
        LEFT JOIN marca ON marca.CodMarca = articulo.CodigoMarca
        WHERE articulo.Discontinuo = 'No'
          AND articulo.ecommerce = 'Si'
          AND articulo.promocion = 'Si'
          AND articulo.promocion_vigencia_desde <= %s
          AND articulo.promocion_vigencia_hasta >= %s
          {filtro}
        ORDER BY articulo.promocion_por DESC,
                 cat.nombre_categoria,
                 rubro.NombreRubro,
                 subrubro.NombreSubRubro,
                 articulo.NombreArticulo
    """

    pool = get_mysql_pool()
    articulos: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql_art, params_art)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            articulos.append(_json_safe(dict(zip(cols, row))))

    intervalos_por_articulo: Dict[str, List[Dict[str, Any]]] = {}
    params_pi: List[Any] = [hoy_s, hoy_s]
    wh_pi = "ai.anulado = 'No' AND ai.vigencia_desde <= %s AND ai.vigencia_hasta >= %s"
    if col_intervalo:
        wh_pi += f" AND ai.{col_intervalo} = %s"
        params_pi.append("Si")

    sql_pi = f"""
        SELECT
            ai.id_articulo,
            ai.desde_cantidad,
            ai.hasta_cantidad,
            ai.monto_descuento
        FROM articulo_promo_intervalo AS ai
        WHERE {wh_pi}
    """
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql_pi, params_pi)
        cols_pi = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            item = _json_safe(dict(zip(cols_pi, row)))
            iid = item.get("id_articulo")
            if iid is None:
                continue
            key = str(int(iid))
            intervalos_por_articulo.setdefault(key, []).append(item)

    return {
        "articulos": articulos,
        "intervalos_por_articulo": intervalos_por_articulo,
        "filtro_lista_precio": col_promo,
        "fecha_consulta": hoy_s,
    }


def parse_query_promociones(query_params) -> Tuple[Dict[str, Optional[int]], Optional[str]]:
    """Query GET relay-promociones (categoria, rubro, subrubro, marca, modelo)."""
    lista_cli = None
    raw_lista = query_params.get("listaPrecio") or query_params.get("lista_precio_cliente")
    if raw_lista:
        lista_cli = str(raw_lista)
    filtros = {
        "id_categoria": to_int_or_none(query_params.get("categoria")),
        "id_rubro": to_int_or_none(query_params.get("rubro")),
        "id_subrubro": to_int_or_none(query_params.get("subrubro")),
        "id_marca": to_int_or_none(query_params.get("marca")),
        "id_modelo": to_int_or_none(query_params.get("modelo")),
    }
    return filtros, lista_cli


def _json_safe(item: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in list(item.items()):
        if isinstance(v, (date, datetime)):
            item[k] = v.isoformat() if isinstance(v, date) else v.date().isoformat()
        elif isinstance(v, Decimal):
            item[k] = float(v)
        elif isinstance(v, bytes):
            item[k] = v.decode("utf-8", errors="replace")
    return item
