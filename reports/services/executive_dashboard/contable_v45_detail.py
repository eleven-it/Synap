"""Aperturas de Gestión contable V45 con alcance declarado."""
from __future__ import annotations

from .base import DashboardFilters, build_paginated_response
from .contable_v45 import _period, _scope
from .resumen_v45 import _table_exists


CONTABLE_V45_VIEWS = frozenset({"asientos", "impuestos", "periodos", "ejercicios"})


def _source(filters, view, group):
    if view == "asientos":
        scope, values = _scope(filters, grupo_contable=group)
        return (
            "SELECT DATE_FORMAT(a.fecha_asiento,'%%Y-%%m-%%d') fecha,"
            "a.id_ejercicio ejercicio,a.nro_asiento asiento,"
            "COALESCE(a.tipo_asiento,'') tipo,COALESCE(pc.cod_pc,'') codigo_cuenta,"
            "COALESCE(pc.descrip_pc,'') detalle,a.codigo_movimiento movimiento,"
            "a.id_sucursal sucursal,a.id_grupo_contable grupo,"
            "COALESCE(a.debe_asiento,0) debe,COALESCE(a.haber_asiento,0) haber,"
            "COALESCE(a.haber_asiento,0) importe "
            "FROM cont_asiento a LEFT JOIN cont_pc pc ON pc.id_pc=a.id_pc "
            f"WHERE a.fecha_asiento >= %s AND a.fecha_asiento < %s AND a.anulado='No'{scope}",
            _period(filters) + values,
            "fecha DESC,ejercicio DESC,asiento DESC",
        )
    if view == "impuestos":
        return (
            "SELECT d.id_impuesto_detalle identificador,d.id_impuesto impuesto,"
            "d.fecdesde_impdetalle desde,d.fechasta_impdetalle hasta,"
            "d.vencimiento_impdetalle vencimiento,COALESCE(d.Tipo_saldo,'') tipo_saldo,"
            "COALESCE(d.estado_impdetalle,'') estado,COALESCE(d.detalle_impdetalle,'') detalle,"
            "COALESCE(d.importe_impdetalle,0) importe "
            "FROM impuesto_detalle d WHERE UPPER(COALESCE(d.anulado,'NO'))<>'SI' "
            "AND d.fechasta_impdetalle >= %s AND d.fechasta_impdetalle < %s",
            _period(filters), "hasta DESC,identificador DESC",
        )
    if view == "periodos":
        return (
            "SELECT p.id_periodo identificador,p.id_ejercicio ejercicio,"
            "p.fecdesde_periodo desde,p.fechasta_periodo hasta,"
            "COALESCE(p.descripcion_periodo,'') detalle,COALESCE(p.cerrado,'') cerrado,"
            "0 importe FROM cont_periodo p WHERE UPPER(COALESCE(p.cerrado,'NO'))<>'SI' "
            "AND p.fecdesde_periodo <= %s AND p.fechasta_periodo >= %s",
            [filters.fecha_fin_str, filters.fecha_inicio_str], "desde DESC,identificador DESC",
        )
    return (
        "SELECT e.id_ejercicio identificador,e.fecdesde_ejercicio desde,"
        "e.fechasta_ejercicio hasta,COALESCE(e.descripcion_ejercicio,'') detalle,"
        "COALESCE(e.cerrado,'') cerrado,0 importe "
        "FROM cont_ejercicio e WHERE UPPER(COALESCE(e.cerrado,'NO'))<>'SI' "
        "AND e.fecdesde_ejercicio <= %s AND e.fechasta_ejercicio >= %s",
        [filters.fecha_fin_str, filters.fecha_inicio_str], "desde DESC,identificador DESC",
    )


def list_contable_v45_detail(cursor, filters: DashboardFilters, *, view: str,
                             grupo_contable: int | None = None) -> dict:
    if view not in CONTABLE_V45_VIEWS:
        raise ValueError("Vista contable inválida")
    table = {"asientos": "cont_asiento", "impuestos": "impuesto_detalle",
             "periodos": "cont_periodo", "ejercicios": "cont_ejercicio"}[view]
    if not _table_exists(cursor, table):
        return {"disponible": False, "motivo": "tabla_faltante", "tabla": table, "filas": []}
    source, params, order = _source(filters, view, grupo_contable)
    search = ""
    if filters.busqueda:
        search = " WHERE CAST(q.detalle AS CHAR) LIKE %s"
        params += [f"%{filters.busqueda}%"]
    cursor.execute(f"SELECT COUNT(*),COALESCE(SUM(q.importe),0) FROM ({source}) q{search}", params)
    total = cursor.fetchone() or (0, 0)
    cursor.execute(
        f"SELECT * FROM ({source}) q{search} ORDER BY {order} LIMIT %s OFFSET %s",
        params + [filters.limit, filters.offset],
    )
    keys = [col[0] for col in cursor.description]
    rows = [dict(zip(keys, row)) for row in cursor.fetchall() or []]
    payload = build_paginated_response(filters, rows, int(total[0] or 0), total[1])
    payload["vista"] = view
    payload["alcance"] = "general" if view != "asientos" else "asiento histórico"
    return payload
