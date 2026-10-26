# -*- coding: utf-8 -*-
"""
Informe Pedidos pendientes (Producción): clon funcional extendido de BO vs Stock,
sin modificar bo-stock-facturacion.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.conf import settings

from reports.services.articulo_venta_sql import sql_excluir_tipo_art_gasto
from reports.services.query_runner import QueryResult, parse_fecha_bo_yyyymmdd
from reports.services.ventas_objetivos_bo_runner import _vo_sql_filtros_articulo

logger = logging.getLogger(__name__)

CRITERIO_BACKORDER = "backorder"
CRITERIO_SALDO_COMERCIAL = "saldo_comercial"
CRITERIO_EN_PREPARACION = "en_preparacion"
CRITERIO_SALDO_NO_ENTREGADO = "saldo_no_entregado"

CRITERIO_LABELS = {
    CRITERIO_BACKORDER: "Backorder (PED Pendiente, cantidad pedida)",
    CRITERIO_SALDO_COMERCIAL: "Saldo comercial MPR (cantidad pendiente, Pendiente/Parcial)",
    CRITERIO_EN_PREPARACION: "En preparación / Preparado (saldo pendiente)",
    CRITERIO_SALDO_NO_ENTREGADO: "Saldo no entregado (Pendiente, Parcial, En preparación, Preparado)",
}


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


def resolve_criterio_pendiente(raw: Optional[str]) -> str:
    c = (raw or CRITERIO_BACKORDER).strip().lower()
    if c not in CRITERIO_LABELS:
        return CRITERIO_BACKORDER
    return c


def criterio_estados_sql(criterio: str) -> Tuple[str, str]:
    """Devuelve (fragmento SQL IN (...), descripción)."""
    if criterio == CRITERIO_BACKORDER:
        return "('Pendiente')", CRITERIO_LABELS[criterio]
    if criterio == CRITERIO_EN_PREPARACION:
        return "('En preparación', 'Preparado')", CRITERIO_LABELS[criterio]
    if criterio == CRITERIO_SALDO_NO_ENTREGADO:
        return "('Pendiente', 'Parcial', 'En preparación', 'Preparado')", CRITERIO_LABELS[criterio]
    return "('Pendiente', 'Parcial')", CRITERIO_LABELS[CRITERIO_SALDO_COMERCIAL]


def qty_expression_for_criterio(criterio: str, tbl_stockp: str = "sp") -> str:
    if criterio == CRITERIO_BACKORDER:
        return f"{tbl_stockp}.Cantidad"
    return (
        f"COALESCE({tbl_stockp}.cantidad_pendiente, "
        f"{tbl_stockp}.Cantidad - COALESCE({tbl_stockp}.cantidad_entregada, 0))"
    )


def classify_depositos_columns(
    depositos: Sequence[Dict[str, Any]],
) -> Tuple[List[int], List[int], List[Dict[str, Any]]]:
    """
    Clasifica depósitos para columnas de stock.
    Returns: (ids_terminado, ids_produccion, otros_columnas[{key, id, nombre}])
    """
    terminado: List[int] = []
    produccion: List[int] = []
    otros: List[Dict[str, Any]] = []

    def _norm_tipo(val: Any) -> str:
        return (str(val or "").strip().lower().replace("ó", "o").replace("é", "e"))

    for dep in depositos:
        cod = dep.get("CodDeposito") or dep.get("id_deposito") or dep.get("cod_deposito")
        try:
            cod_int = int(cod)
        except (TypeError, ValueError):
            continue
        nombre = str(dep.get("NombreDeposito") or dep.get("nombre") or f"Dep {cod_int}").strip()
        suma = str(dep.get("suma_stock") or "Si").strip().upper() in ("SI", "S", "1", "YES")
        tipo = _norm_tipo(dep.get("tipo_mpr"))

        if tipo in ("terminado",):
            terminado.append(cod_int)
        elif tipo in ("produccion", "producción"):
            produccion.append(cod_int)
        elif suma:
            key = f"dep_{cod_int}"
            otros.append({"key": key, "id_deposito": cod_int, "nombre": nombre})

    return terminado, produccion, otros


def merge_mpr_into_articulos(
    articulos: List[Dict[str, Any]],
    mpr_filas: Sequence[Dict[str, Any]],
) -> None:
    mpr_by_id = {int(r["id_articulo"]): r for r in mpr_filas if r.get("id_articulo") is not None}
    for row in articulos:
        aid = row.get("id_art")
        mpr = mpr_by_id.get(aid) if aid is not None else None
        if not mpr:
            row.update(
                {
                    "mpr_demanda_pedido": None,
                    "mpr_stock_terminado": None,
                    "mpr_stock_reserva": None,
                    "mpr_cantidad_a_fabricar": None,
                    "mpr_brecha_vs_pendiente": None,
                }
            )
            continue
        demanda = float(mpr.get("cantidad_pedida_pedido") or 0)
        a_fab = float(mpr.get("cantidad_a_fabricar") or 0)
        pend = float(row.get("pendiente_qty") or 0)
        row["mpr_demanda_pedido"] = demanda
        row["mpr_stock_terminado"] = float(mpr.get("stock_terminado") or 0)
        row["mpr_stock_reserva"] = float(mpr.get("stock_reserva") or 0)
        row["mpr_cantidad_a_fabricar"] = a_fab
        row["mpr_brecha_vs_pendiente"] = round(pend - a_fab, 4) if pend or a_fab else 0.0


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

    criterio = resolve_criterio_pendiente(filters.get("criterio_pendiente"))
    solo_terminados = filters.get("solo_terminados")
    if solo_terminados is None:
        solo_terminados = True
    solo_terminados = bool(solo_terminados) if not isinstance(solo_terminados, str) else solo_terminados.lower() in (
        "1",
        "true",
        "si",
        "sí",
        "yes",
    )

    sucursales_ints, _pv = svc._parse_sucursales_pv(filters)
    clientes_excluidos = svc._parse_clientes_excluidos(filters)
    clientes_incluir = _as_int_list(filters.get("clientes_incluir") or filters.get("clientes_incluidos"))
    marcas_incluidos = _as_int_list(filters.get("marcas_incluidos"))
    marcas_excluidos = _as_int_list(filters.get("marcas_excluidos"))

    depositos_incluidos = filters.get("depositos_incluidos") or []
    if isinstance(depositos_incluidos, str):
        depositos_incluidos = [depositos_incluidos] if depositos_incluidos else []
    depositos_incluidos = [
        int(x) for x in depositos_incluidos if str(x).strip() and str(x).replace("-", "").isdigit()
    ]

    fecha_inicio_bo, fecha_fin_bo = parse_fecha_bo_yyyymmdd(fecha_inicio, fecha_fin)
    bo_estados_sql, criterio_desc = criterio_estados_sql(criterio)
    qty_sql = qty_expression_for_criterio(criterio)

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
                "COALESCE(suma_stock,'Si') AS suma_stock, tipo_mpr FROM deposito "
                "WHERE COALESCE(anulado,'No')='No' ORDER BY NombreDeposito"
            )
            for row in cursor.fetchall() or []:
                depositos_cfg.append(
                    {
                        "CodDeposito": row[0],
                        "NombreDeposito": row[1],
                        "suma_stock": row[2],
                        "tipo_mpr": row[3],
                    }
                )
        except Exception:
            pass

    ids_terminado, ids_produccion, otros_deps = classify_depositos_columns(depositos_cfg)

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

    tipo_terminado_sql = ""
    if solo_terminados:
        tipo_terminado_sql = " AND COALESCE(TRIM(a.tipo_art_fab), '') = 'Terminado'"

    params_bo: List[Any] = []
    params_bo.extend(suc_params)
    params_bo.extend([fecha_inicio_bo, fecha_fin_bo])
    if clientes_incluir:
        params_bo.extend(clientes_incluir)
    if clientes_excluidos:
        params_bo.extend(clientes_excluidos)
    params_bo.extend(filt_art_params)

    sql_pendiente = f"""
        SELECT
            sp.IDArt AS id_art,
            COALESCE(a.id_manual, '') AS codigo,
            COALESCE(a.NombreArticulo, '') AS articulo,
            COALESCE(m.NombreMarca, '') AS marca,
            COALESCE(r.NombreRubro, 'Sin Rubro') AS categoria,
            SUM({qty_sql}) AS pendiente_qty
        FROM stockp sp
        INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
        LEFT JOIN articulo a ON a.IDArt = sp.IDArt
        LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
        LEFT JOIN marca m ON m.CodMarca = a.CodigoMarca
        WHERE cp.TipoComprobante = 'PED'
          AND (sp.Comprobante = 'PED' OR sp.Comprobante IS NULL)
          AND cp.Anulado = 'No'
          AND (sp.anulado IS NULL OR sp.anulado = 'No')
          AND cp.Estado IN {bo_estados_sql}
          AND sp.CodigoMovimiento IS NOT NULL
          {suc_sql}
          AND sp.Fecha >= %s AND sp.Fecha <= %s
          {cliente_incl_sql}
          {cliente_excl_sql}
          {tipo_terminado_sql}
          AND {sql_excluir_tipo_art_gasto("a")}
          {filt_art_sql}
        GROUP BY sp.IDArt, a.id_manual, a.NombreArticulo, m.NombreMarca, r.NombreRubro
        HAVING pendiente_qty > 0
        ORDER BY pendiente_qty DESC
    """

    if criterio == CRITERIO_SALDO_COMERCIAL:
        try:
            from mpr.services import _sql_filtros_ped_demanda_comercial, _sql_qty_pendiente_comercial_stockp

            qty_mpr = _sql_qty_pendiente_comercial_stockp(cursor, "stockp")
            filt_com = _sql_filtros_ped_demanda_comercial(cursor, "comp_ped", "stockp")
            sql_pendiente = f"""
                SELECT
                    sp.IDArt AS id_art,
                    COALESCE(a.id_manual, '') AS codigo,
                    COALESCE(a.NombreArticulo, '') AS articulo,
                    COALESCE(m.NombreMarca, '') AS marca,
                    COALESCE(r.NombreRubro, 'Sin Rubro') AS categoria,
                    SUM({qty_mpr}) AS pendiente_qty
                FROM stockp sp
                INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                LEFT JOIN articulo a ON a.IDArt = sp.IDArt
                LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
                LEFT JOIN marca m ON m.CodMarca = a.CodigoMarca
                WHERE COALESCE(cp.Anulado, 'No') = 'No'
                  AND COALESCE(cp.TipoComprobante, '') = 'PED'
                  {filt_com}
                  AND {qty_mpr} > 0
                  {suc_sql}
                  AND cp.Fecha >= %s AND cp.Fecha <= %s
                  {cliente_incl_sql}
                  {cliente_excl_sql}
                  {tipo_terminado_sql}
                  AND {sql_excluir_tipo_art_gasto("a")}
                  {filt_art_sql}
                GROUP BY sp.IDArt, a.id_manual, a.NombreArticulo, m.NombreMarca, r.NombreRubro
                HAVING pendiente_qty > 0
                ORDER BY pendiente_qty DESC
            """
        except Exception as exc:
            logger.warning("Fallback criterio saldo_comercial: %s", exc)

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
                "codigo": row[1] or "",
                "articulo": row[2] or "",
                "marca": row[3] or "",
                "categoria": row[4] or "",
                "pendiente_qty": float(row[5] or 0),
                "stock_terminado": 0.0,
                "stock_produccion": 0.0,
                "stock_total": 0.0,
            }
        )

    if id_arts:
        ph = ",".join(["%s"] * len(id_arts))
        dep_filter = ""
        dep_params: List[Any] = list(id_arts)
        if depositos_incluidos:
            phd = ",".join(["%s"] * len(depositos_incluidos))
            dep_filter = f" AND sd.id_deposito IN ({phd})"
            dep_params.extend(depositos_incluidos)
        cursor.execute(
            f"""
            SELECT sd.id_articulo, sd.id_deposito, COALESCE(sd.saldo, 0)
            FROM stock_deposito sd
            WHERE sd.id_articulo IN ({ph})
            {dep_filter}
            """,
            dep_params,
        )
        saldo_map: Dict[Tuple[int, int], float] = {}
        for sid_art, sid_dep, saldo in cursor.fetchall() or []:
            saldo_map[(int(sid_art), int(sid_dep))] = float(saldo or 0)

        set_terminado = set(ids_terminado)
        set_produccion = set(ids_produccion)
        for art in articulos:
            aid = art["id_art"]
            st_term = sum(saldo_map.get((aid, d), 0.0) for d in set_terminado)
            st_prod = sum(saldo_map.get((aid, d), 0.0) for d in set_produccion)
            art["stock_terminado"] = st_term
            art["stock_produccion"] = st_prod
            total = st_term + st_prod
            for col in otros_deps:
                val = saldo_map.get((aid, col["id_deposito"]), 0.0)
                art[col["key"]] = val
                total += val
            art["stock_total"] = total

    try:
        from mpr.services import listar_demanda_pack_desde_pedidos

        fd = date.fromisoformat(str(fecha_inicio)[:10])
        fh = date.fromisoformat(str(fecha_fin)[:10])
        mpr_filas = listar_demanda_pack_desde_pedidos(
            base_empresa,
            limit=max(500, len(articulos) * 2),
            fecha_desde=fd,
            fecha_hasta=fh,
            marcas_incluidos=marcas_incluidos or None,
        )
    except Exception as exc:
        logger.warning("MPR demanda pack: %s", exc)
        mpr_filas = []

    merge_mpr_into_articulos(articulos, mpr_filas)

    total_pendiente = sum(a.get("pendiente_qty") or 0 for a in articulos)
    totals = {
        "total_articulos": len(articulos),
        "total_pendiente_qty": total_pendiente,
        "total_stock_terminado": sum(a.get("stock_terminado") or 0 for a in articulos),
        "total_stock_produccion": sum(a.get("stock_produccion") or 0 for a in articulos),
        "total_stock": sum(a.get("stock_total") or 0 for a in articulos),
    }

    columnas_stock = {
        "stock_terminado": {"label": "Stock terminado", "deposito_ids": ids_terminado},
        "stock_produccion": {"label": "Stock producción", "deposito_ids": ids_produccion},
        "otros": otros_deps,
    }

    notes = [
        f"Período pedidos: {svc._format_date(fecha_inicio)} a {svc._format_date(fecha_fin)}",
        f"Criterio de pendiente: {criterio_desc} (valor={criterio}).",
        "Stock terminado/producción según deposito.tipo_mpr; columnas adicionales = depósitos con suma_stock=Si.",
        "MPR: listar_demanda_pack_desde_pedidos (demanda/brecha pack en vivo).",
        f"Solo terminados (tipo_art_fab): {'Sí' if solo_terminados else 'No'}.",
    ]
    if clientes_incluir:
        notes.append(f"Clientes incluidos: {len(clientes_incluir)}.")
    if marcas_incluidos:
        notes.append(f"Marcas incluidas: {len(marcas_incluidos)}.")

    cursor.close()
    conn.close()

    return QueryResult(
        meta={
            **meta_base,
            "extra": {
                "articulos": articulos,
                "columnas_stock": columnas_stock,
                "criterio_pendiente": criterio,
            },
            "filters_applied": {
                "criterio_pendiente": criterio,
                "solo_terminados": solo_terminados,
                "clientes_incluir": clientes_incluir,
                "marcas_incluidos": marcas_incluidos,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
            },
        },
        data=articulos,
        totals=totals,
        notes=notes,
    )
