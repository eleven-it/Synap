# -*- coding: utf-8 -*-
"""
Informe Pedidos pendientes (Producción): pendientes por artículo alineado al legacy
PEDIDOS PENDIENTES - VENDEDOR / MARCA. Sin modificar bo-stock-facturacion.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

from reports.services.articulo_venta_sql import sql_excluir_tipo_art_gasto
from reports.services.pedidos_pendientes_produccion_calcs import (
    aggregate_totals,
    build_busqueda_sql,
    build_pv_sql,
    build_viajante_sql,
    classify_depositos_stock_columns,
    enrich_articulo_row,
    sql_unidad_base_group_by_suffix,
    sql_unidad_base_join,
    sql_unidad_base_select,
)
from reports.services.query_runner import QueryResult, parse_fecha_bo_yyyymmdd
from reports.services.ventas_objetivos_bo_runner import _vo_sql_filtros_articulo

logger = logging.getLogger(__name__)

CRITERIO_BACKORDER = "backorder"

IMPORTE_PENDIENTE_NOTA = (
    "Importe neto sin IVA ni descuento de cabecera (proporcional PrecioNetoxR por línea pendiente)."
)

PPP_FOOTER_NOTA = (
    "Stock actual global: depósitos activos con Suma stock=Si. Disponible = max(0, terminado − pendiente). "
    "Backorder = pendiente sin cobertura de terminado. Producción se muestra aparte. "
    "Importe neto sin IVA ni descuento de cabecera."
)


def _as_int_list(raw: Any) -> List[int]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw] if raw.strip() else []
    if not isinstance(raw, (list, tuple)):
        return []
    out: List[int] = []
    for item in raw:
        try:
            out.append(int(str(item).strip()))
        except (TypeError, ValueError):
            continue
    return out


def run_pedidos_pendientes_produccion(report, payload: Dict, user) -> QueryResult:
    from reports.services.query_runner import QueryRunnerService

    svc = QueryRunnerService(user)
    meta_base = {
        "slug": report.slug,
        "name": report.name,
        "category": report.category,
        "version": report.version,
    }
    filters = payload.get("filters") or {}
    base_empresa = filters.get("base_empresa")
    fecha_inicio, fecha_fin = svc._resolve_period_dates(filters)
    if not fecha_inicio or not fecha_fin:
        return QueryResult(
            meta=meta_base,
            data=[],
            totals={},
            notes=["Debe indicar fecha de inicio y fin (o un período predefinido)."],
        )
    if not base_empresa:
        base_empresa = getattr(user, "base_empresa", None)
    if not base_empresa:
        base_empresa = getattr(settings, "DEFAULT_BASE_EMPRESA", None)
    if not base_empresa:
        return QueryResult(
            meta=meta_base,
            data=[],
            totals={},
            notes=["No se pudo determinar la base de datos de la empresa."],
        )

    sucursales_ints, puntos_venta_ints = svc._parse_sucursales_pv(filters)
    clientes_excluidos = svc._parse_clientes_excluidos(filters)
    clientes_incluir = _as_int_list(filters.get("clientes_incluir") or filters.get("clientes_incluidos"))
    marcas_incluidos = _as_int_list(filters.get("marcas_incluidos"))
    marcas_excluidos = _as_int_list(filters.get("marcas_excluidos"))
    vendedores_incluir = _as_int_list(filters.get("vendedores_incluir"))
    vendedores_excluidos = _as_int_list(svc._parse_vendedores_excluidos(filters))
    if vendedores_incluir:
        vendedores_excluidos = [v for v in vendedores_excluidos if v not in set(vendedores_incluir)]
    busqueda = filters.get("busqueda") or filters.get("busqueda_libre")

    fecha_inicio_bo, fecha_fin_bo = parse_fecha_bo_yyyymmdd(fecha_inicio, fecha_fin)
    bo_estados_sql = "('Pendiente')"
    qty_sql = "sp.Cantidad"

    import MySQLdb

    mysql_config = settings.DATABASES["mysql"]
    try:
        conn = MySQLdb.connect(
            host=mysql_config["HOST"],
            port=int(mysql_config["PORT"]),
            user=mysql_config["USER"],
            passwd=mysql_config["PASSWORD"],
            db=base_empresa,
            charset="latin1",
        )
        cursor = conn.cursor()
    except Exception as exc:
        logger.error("Pedidos pendientes producción: error MySQL %s", exc)
        return QueryResult(meta=meta_base, data=[], totals={}, notes=[f"Error de conexión: {exc}"])

    try:
        from mpr.services import listar_depositos_config

        depositos_cfg = listar_depositos_config(base_empresa)
    except Exception as exc:
        logger.warning("No se pudo listar depósitos MPR: %s", exc)
        depositos_cfg = []
        try:
            cursor.execute(
                "SELECT CodDeposito, COALESCE(NombreDeposito,'') AS NombreDeposito, "
                "COALESCE(suma_stock,'Si') AS suma_stock, COALESCE(anulado,'No') AS anulado, tipo_mpr "
                "FROM deposito WHERE COALESCE(anulado,'No')='No' ORDER BY NombreDeposito"
            )
            for row in cursor.fetchall() or []:
                depositos_cfg.append(
                    {
                        "CodDeposito": row[0],
                        "NombreDeposito": row[1],
                        "suma_stock": row[2],
                        "anulado": row[3],
                        "tipo_mpr": row[4],
                    }
                )
        except Exception:
            pass

    ids_terminado, ids_produccion = classify_depositos_stock_columns(depositos_cfg)

    filt_art_sql, filt_art_params = _vo_sql_filtros_articulo(
        "a",
        marcas_incluidos=marcas_incluidos or None,
        marcas_excluidos=marcas_excluidos or None,
    )

    cliente_incl_sql = ""
    cliente_excl_sql = ""
    if clientes_incluir:
        ph = ",".join(["%s"] * len(clientes_incluir))
        cliente_incl_sql = f" AND cp.Codigo IN ({ph})"
    if clientes_excluidos:
        ph = ",".join(["%s"] * len(clientes_excluidos))
        cliente_excl_sql = f" AND cp.Codigo NOT IN ({ph})"

    suc_sql = ""
    suc_params: List[Any] = []
    if sucursales_ints:
        ph = ",".join(["%s"] * len(sucursales_ints))
        suc_sql = f" AND cp.CodSucursal IN ({ph})"
        suc_params = list(sucursales_ints)

    pv_sql, pv_params = build_pv_sql(puntos_venta_ints)
    viaj_sql, viaj_params = build_viajante_sql(vendedores_incluir, vendedores_excluidos)
    busq_sql, busq_params = build_busqueda_sql(busqueda)

    importe_expr = (
        f"SUM({qty_sql} * COALESCE(sp.PrecioNetoxR / NULLIF(ABS(sp.Cantidad), 0), 0))"
    )

    params_bo: List[Any] = []
    params_bo.extend(suc_params)
    params_bo.extend(pv_params)
    params_bo.extend(viaj_params)
    params_bo.extend([fecha_inicio_bo, fecha_fin_bo])
    if clientes_incluir:
        params_bo.extend(clientes_incluir)
    if clientes_excluidos:
        params_bo.extend(clientes_excluidos)
    params_bo.extend(busq_params)
    params_bo.extend(filt_art_params)

    sql_pendiente = f"""
        SELECT
            sp.IDArt AS id_art,
            COALESCE(a.id_manual, '') AS cod_manual,
            COALESCE(a.NombreArticulo, '') AS articulo,
            COALESCE(m.NombreMarca, '') AS marca,
            {sql_unidad_base_select()},
            SUM({qty_sql}) AS pendiente_qty,
            {importe_expr} AS importe_pendiente
        FROM stockp sp
        INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
        LEFT JOIN articulo a ON a.IDArt = sp.IDArt
        LEFT JOIN marca m ON m.CodMarca = a.CodigoMarca
        {sql_unidad_base_join()}
        WHERE cp.TipoComprobante = 'PED'
          AND (sp.Comprobante = 'PED' OR sp.Comprobante IS NULL)
          AND cp.Anulado = 'No'
          AND (sp.anulado IS NULL OR sp.anulado = 'No')
          AND cp.Estado IN {bo_estados_sql}
          AND sp.CodigoMovimiento IS NOT NULL
          {suc_sql}
          {pv_sql}
          {viaj_sql}
          AND sp.Fecha >= %s AND sp.Fecha <= %s
          {cliente_incl_sql}
          {cliente_excl_sql}
          {busq_sql}
          AND {sql_excluir_tipo_art_gasto("a")}
          {filt_art_sql}
        GROUP BY sp.IDArt, a.id_manual, a.NombreArticulo, m.NombreMarca{sql_unidad_base_group_by_suffix()}
        HAVING pendiente_qty > 0
        ORDER BY pendiente_qty DESC
    """

    cursor.execute(sql_pendiente, params_bo)
    rows = cursor.fetchall()
    articulos: List[Dict[str, Any]] = []
    id_arts: List[int] = []
    for row in rows:
        id_art = int(row[0])
        id_arts.append(id_art)
        articulos.append(
            {
                "id_art": id_art,
                "codigo": id_art,
                "cod_manual": row[1] or "",
                "articulo": row[2] or "",
                "marca": row[3] or "",
                "unidad_base": row[4] or "",
                "pendiente_qty": float(row[5] or 0),
                "importe_pendiente": round(float(row[6] or 0), 2),
                "stock_terminado": 0.0,
                "stock_produccion": 0.0,
            }
        )

    reserva_map: Dict[int, float] = {}
    if id_arts:
        ph = ",".join(["%s"] * len(id_arts))
        cursor.execute(
            f"SELECT IDArt, COALESCE(stock_reserva, 0) FROM articulo WHERE IDArt IN ({ph})",
            id_arts,
        )
        for aid, res in cursor.fetchall() or []:
            reserva_map[int(aid)] = float(res or 0)

        dep_ids = list(set(ids_terminado) | set(ids_produccion))
        saldo_map: Dict[Tuple[int, int], float] = {}
        if dep_ids:
            ph_art = ",".join(["%s"] * len(id_arts))
            ph_dep = ",".join(["%s"] * len(dep_ids))
            cursor.execute(
                f"""
                SELECT sd.id_articulo, sd.id_deposito, COALESCE(sd.saldo, 0)
                FROM stock_deposito sd
                INNER JOIN deposito d ON d.CodDeposito = sd.id_deposito
                  AND COALESCE(d.anulado, 'No') = 'No'
                  AND COALESCE(d.suma_stock, 'Si') = 'Si'
                WHERE sd.id_articulo IN ({ph_art})
                  AND sd.id_deposito IN ({ph_dep})
                """,
                id_arts + dep_ids,
            )
            for sid_art, sid_dep, saldo in cursor.fetchall() or []:
                saldo_map[(int(sid_art), int(sid_dep))] = float(saldo or 0)

        set_terminado = set(ids_terminado)
        set_produccion = set(ids_produccion)
        for art in articulos:
            aid = art["id_art"]
            art["stock_terminado"] = sum(saldo_map.get((aid, d), 0.0) for d in set_terminado)
            art["stock_produccion"] = sum(saldo_map.get((aid, d), 0.0) for d in set_produccion)
            enrich_articulo_row(art, reserva_map.get(aid, 0.0))

    totals = aggregate_totals(articulos)

    notes = [
        f"Período pedidos (sp.Fecha): {svc._format_date(fecha_inicio)} a {svc._format_date(fecha_fin)}",
        "Pendiente: PED en estado Pendiente, cantidad = stockp.Cantidad (backorder).",
        "Stock terminado/producción: depósitos activos con suma_stock=Si y tipo_mpr Terminado/Producción.",
        "MPR: P_ped = pendiente del informe; a fabricar = max(0, P_ped + reserva − stock terminado); "
        "brecha = pendiente − a fabricar (misma base de líneas que el informe).",
        IMPORTE_PENDIENTE_NOTA,
        f"Filas: {totals.get('row_count', 0)}.",
    ]
    if clientes_incluir:
        notes.append(f"Clientes incluidos: {len(clientes_incluir)}.")
    if marcas_incluidos:
        notes.append(f"Marcas incluidas: {len(marcas_incluidos)}.")
    if vendedores_incluir:
        notes.append(f"Vendedores incluidos (cp.CodViajante): {len(vendedores_incluir)}.")
    if busqueda:
        notes.append(f"Búsqueda libre: «{str(busqueda)[:80]}».")

    cursor.close()
    conn.close()

    return QueryResult(
        meta={
            **meta_base,
            "extra": {
                "articulos": articulos,
                "importe_pendiente_field": "PrecioNetoxR proporcional",
                "footer_nota": PPP_FOOTER_NOTA,
            },
            "filters_applied": {
                "clientes_incluir": clientes_incluir,
                "marcas_incluidos": marcas_incluidos,
                "vendedores_incluir": vendedores_incluir,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "busqueda": busqueda,
            },
        },
        data=articulos,
        totals=totals,
        notes=notes,
    )
