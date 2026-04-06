"""
Relay de filtros para estadísticas (paridad relay-filtros-estadisticas.php).
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.mysql_pool import get_mysql_pool


def _build_sql(tabla: str, usa_id_manual: bool, arr_vend_cargo: List[int]) -> str:
    t = (tabla or "").strip().lower()
    if t == "cliente":
        if usa_id_manual:
            return (
                "SELECT cliente.id_manual_cli AS valor, "
                "CONCAT(cliente.nombre_cliente,' (cod:',cliente.id_manual_cli,')') AS texto "
                "FROM cliente WHERE cliente.Estado='Activo' ORDER BY texto ASC"
            )
        return (
            "SELECT cliente.Codigo AS valor, "
            "CONCAT(cliente.nombre_cliente,' (cod:',cliente.Codigo,')') AS texto "
            "FROM cliente WHERE cliente.Estado='Activo' ORDER BY texto ASC"
        )
    if t == "tipocliente":
        return (
            "SELECT tipo_cliente.IDTipoCliente AS valor, "
            "CONCAT(tipo_cliente.NombreTipoCliente,' (cod:',tipo_cliente.IDTipoCliente,')') AS texto "
            "FROM tipo_cliente WHERE tipo_cliente.Anulado='No' ORDER BY texto ASC"
        )
    if t == "articulo":
        if usa_id_manual:
            return (
                "SELECT articulo.id_manual AS valor, "
                "CONCAT(articulo.NombreArticulo,' (cod:',articulo.id_manual,')') AS texto "
                "FROM articulo WHERE articulo.Discontinuo='No' AND articulo.id_manual<>'' ORDER BY texto ASC"
            )
        return (
            "SELECT articulo.IDArt AS valor, "
            "CONCAT(articulo.NombreArticulo,' (cod:',articulo.IDArt,')') AS texto "
            "FROM articulo WHERE articulo.Discontinuo='No' ORDER BY texto ASC"
        )
    if t == "vendedor":
        extra = ""
        if arr_vend_cargo:
            lista = ",".join(str(int(x)) for x in arr_vend_cargo)
            extra = f" AND viajantes.CodViajante IN ({lista})"
        return (
            "SELECT viajantes.CodViajante AS valor, "
            "CONCAT(viajantes.Nombre,' (cod:',viajantes.CodViajante,')') AS texto "
            "FROM viajantes WHERE viajantes.Anulado='No'"
            f"{extra} ORDER BY texto ASC"
        )
    if t == "proveedor":
        return (
            "SELECT proveedor.Codigo AS valor, "
            "CONCAT(proveedor.Nombre,' (cod:',proveedor.Codigo,')') AS texto "
            "FROM proveedor WHERE proveedor.Estado='Activo' AND proveedor.Tipo='Mercaderias' ORDER BY texto ASC"
        )
    if t == "zona":
        return (
            "SELECT erp_zona.id_zona AS valor, "
            "CONCAT(erp_zona.nombre_zona,' (cod:',erp_zona.id_zona,')') AS texto "
            "FROM erp_zona WHERE erp_zona.anulado='No' ORDER BY texto ASC"
        )
    if t == "categoria":
        return (
            "SELECT rubro_categoria.id_categoria AS valor, "
            "CONCAT(rubro_categoria.nombre_categoria,' (cod:',rubro_categoria.id_categoria,')') AS texto "
            "FROM rubro_categoria WHERE rubro_categoria.anulado='No' ORDER BY texto ASC"
        )
    if t == "rubro":
        return (
            "SELECT rubro.CodigoRubro AS valor, "
            "CONCAT(rubro.NombreRubro,' (cod:',rubro.CodigoRubro,')') AS texto "
            "FROM rubro WHERE rubro.anulado='No' ORDER BY texto ASC"
        )
    if t == "subrubro":
        return (
            "SELECT subrubro.IDSubRubro AS valor, "
            "CONCAT(subrubro.NombreSubRubro,' (ru: ',rubro.NombreRubro,' - cod: ', subrubro.IDSubRubro ,')') AS texto "
            "FROM subrubro LEFT JOIN rubro ON rubro.CodigoRubro = subrubro.CodigoRubro "
            "WHERE subrubro.anulado='No' ORDER BY texto ASC"
        )
    if t == "usuario":
        return (
            "SELECT usuarios.id_usuario AS valor, "
            "CONCAT(usuarios.cod_usuario,' (cod: ', usuarios.id_usuario ,')') AS texto "
            "FROM usuarios WHERE usuarios.baja_usuario='No' ORDER BY texto ASC"
        )
    return ""


def listado_filtros_estadisticas(
    *,
    base_empresa: str,
    tabla: str,
    usa_id_manual: bool,
    arr_vend_cargo: List[int] | None = None,
) -> List[Dict[str, str]]:
    sql = _build_sql(tabla, usa_id_manual=usa_id_manual, arr_vend_cargo=arr_vend_cargo or [])
    if not sql:
        return []
    pool = get_mysql_pool()
    out: List[Dict[str, str]] = []
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        c.execute(sql)
        for valor, texto in c.fetchall():
            out.append({"label": str(texto), "value": f"{valor}|{texto}"})
    return out

