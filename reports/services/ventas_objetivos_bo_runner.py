# -*- coding: utf-8 -*-
"""
Informe Objetivos de ventas por vendedor (jerárquico vendedor → cliente).

Misma temporalidad dual que bo-stock-facturacion. Ver SPEC_INFORME_OBJETIVOS_VENTAS_BO.md.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

from django.conf import settings

from reports.models import ReportDefinition
from reports.services.connection_pool import get_mysql_pool
from reports.services.objetivos_ventas_contract import (
    calcular_falta,
    calcular_total_facturacion_remitos,
)
from reports.services.query_runner import QueryResult, QueryRunnerService, parse_fecha_bo_yyyymmdd

logger = logging.getLogger(__name__)

_TIPOS_FAC_NC = (
    "FA",
    "FB",
    "FC",
    "FE",
    "FM",
    "NCA",
    "NCB",
    "NCC",
    "NCE",
    "NCM",
)
_STOCK_TIPO_COMP_VENTAS = (
    "Venta",
    "Venta TPV",
    "Devol - Cliente",
    "ND Anul NC",
)

FAC_LIMIT = 5000

# Misma convención que `bo-stock-facturacion` / VB6 Info_Stock (0–6).
_LISTA_PRECIO_LABELS = (
    "Costo",
    "Lista Oficial",
    "Lista 1",
    "Lista 2",
    "Lista 3",
    "Lista 4",
    "Lista 5",
)


def _label_lista_precio(cod: int) -> str:
    if 0 <= cod < len(_LISTA_PRECIO_LABELS):
        return _LISTA_PRECIO_LABELS[cod]
    return f"Lista ({cod})"


def _norm_yyyy_mm_dd(s: str) -> str:
    s = (s or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s[:10] if len(s) >= 10 else s


def _parse_date_for_overlap(s: str):
    s2 = _norm_yyyy_mm_dd(s)
    return datetime.strptime(s2, "%Y-%m-%d").date()


def run_ventas_objetivos_vs_bo(report: ReportDefinition, payload: Dict, user) -> QueryResult:
    svc = QueryRunnerService(user)
    filters = payload.get("filters", {}) or {}
    fecha_inicio, fecha_fin = svc._resolve_period_dates(filters)
    if not fecha_inicio or not fecha_fin:
        return QueryResult(
            meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
            data=[],
            totals={},
            notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
        )

    fi_fac_raw = filters.get("fecha_inicio_facturacion")
    ff_fac_raw = filters.get("fecha_fin_facturacion")
    fi_fac = str(fi_fac_raw).strip() if fi_fac_raw else ""
    ff_fac = str(ff_fac_raw).strip() if ff_fac_raw else ""
    if not fi_fac or not ff_fac:
        fi_fac, ff_fac = fecha_inicio, fecha_fin

    base_empresa = filters.get("base_empresa")
    if not base_empresa and hasattr(user, "base_empresa"):
        base_empresa = getattr(user, "base_empresa", None)
    if not base_empresa:
        base_empresa = getattr(settings, "DEFAULT_BASE_EMPRESA", None)
    if not base_empresa:
        return QueryResult(
            meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
            data=[],
            totals={},
            notes=["No se pudo determinar la base de datos de la empresa."],
        )

    sucursales = filters.get("sucursales", [])
    if isinstance(sucursales, str):
        sucursales = [sucursales] if sucursales else []
    elif not isinstance(sucursales, list):
        sucursales = []
    sucursales_ints: List[int] = []
    for s in sucursales:
        try:
            sucursales_ints.append(int(s))
        except (TypeError, ValueError):
            pass

    depositos_incluidos = filters.get("depositos_incluidos", [])
    if isinstance(depositos_incluidos, str):
        depositos_incluidos = [depositos_incluidos] if depositos_incluidos else []
    elif not isinstance(depositos_incluidos, list):
        depositos_incluidos = []
    depositos_incluidos = [
        int(x) for x in depositos_incluidos if str(x).strip() and str(x).replace("-", "").isdigit()
    ]

    clientes_excluidos = svc._parse_clientes_excluidos(filters)
    vendedores_excluidos = svc._parse_vendedores_excluidos(filters)

    lista_precio = filters.get("lista_precio")
    if lista_precio is None:
        lista_precio = 2
    try:
        lista_precio = int(lista_precio)
    except (TypeError, ValueError):
        lista_precio = 2
    if lista_precio not in range(0, 7):
        lista_precio = 2

    fecha_inicio_bo, fecha_fin_bo = parse_fecha_bo_yyyymmdd(fecha_inicio, fecha_fin)
    fi_fac_sql = _norm_yyyy_mm_dd(fi_fac)
    ff_fac_sql = _norm_yyyy_mm_dd(ff_fac)
    d_fac_ini = _parse_date_for_overlap(fi_fac)
    d_fac_fin = _parse_date_for_overlap(ff_fac)

    sd_where_excl = ""
    if depositos_incluidos:
        sd_where_excl = " WHERE id_deposito IN (" + ",".join(str(d) for d in depositos_incluidos) + ")"
    clientes_excl_bo = ""
    reservado_excl_clause = ""
    reservado_viaj_clause = ""
    if clientes_excluidos:
        clientes_excl_bo = " AND cp.Codigo NOT IN (" + ",".join(str(c) for c in clientes_excluidos) + ")"
        reservado_excl_clause = " AND cp_res.Codigo NOT IN (" + ",".join(str(c) for c in clientes_excluidos) + ")"
    if vendedores_excluidos:
        reservado_viaj_clause = " AND cl_res.CodViajante NOT IN (" + ",".join(str(x) for x in vendedores_excluidos) + ")"
    suc_bo_ph = ""
    if sucursales_ints:
        suc_bo_ph = " AND cp.CodSucursal IN (" + ",".join(["%s"] * len(sucursales_ints)) + ")"
    suc_res_inner = ""
    if sucursales_ints:
        suc_res_inner = " AND cp_res.CodSucursal IN (" + ",".join(str(x) for x in sucursales_ints) + ")"
    bo_estados = "('Pendiente')"

    obj_viaj_extra = ""
    if vendedores_excluidos:
        obj_viaj_extra = (
            " AND v.Codigo IN (SELECT cjx.Codigo FROM cliente cjx WHERE cjx.CodViajante NOT IN ("
            + ",".join(str(x) for x in vendedores_excluidos)
            + "))"
        )

    viaj_bo = ""
    if vendedores_excluidos:
        phvb = ",".join(["%s"] * len(vendedores_excluidos))
        viaj_bo = f" AND cl_bo.CodViajante NOT IN ({phvb})"

    notes: List[str] = []
    try:
        pool = get_mysql_pool()
        with pool.get_connection(str(base_empresa).strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SET SESSION max_execution_time = 90000")
            except Exception:
                pass

            # --- Facturación por cliente ---
            where_fac_cli = [
                "cc.Fecha >= %s",
                "cc.Fecha <= %s",
                "cc.Anulado = 'No'",
                "cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM')",
            ]
            params_fac_cli: List[Any] = [fi_fac_sql, ff_fac_sql]
            if sucursales_ints:
                phs = ",".join(["%s"] * len(sucursales_ints))
                where_fac_cli.append(f"cc.CodSucursal IN ({phs})")
                params_fac_cli.extend(sucursales_ints)
            if clientes_excluidos:
                ph = ",".join(["%s"] * len(clientes_excluidos))
                where_fac_cli.append(f"cc.Codigo NOT IN ({ph})")
                params_fac_cli.extend(clientes_excluidos)
            if vendedores_excluidos:
                phv = ",".join(["%s"] * len(vendedores_excluidos))
                where_fac_cli.append(f"cl.CodViajante NOT IN ({phv})")
                params_fac_cli.extend(vendedores_excluidos)
            where_fac_cli_s = " AND ".join(where_fac_cli)
            params_fac_cli.append(FAC_LIMIT)
            sql_fac_cli = f"""
                SELECT
                    cl.Codigo AS id_cliente,
                    COALESCE(MAX(cl.nombre_cliente), '') AS nombre_cliente,
                    SUM(CASE WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') THEN COALESCE(cc.SubtotalDesc, 0) ELSE 0 END)
                        - SUM(CASE WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') THEN COALESCE(cc.SubtotalDesc, 0) ELSE 0 END) AS sub_total,
                    COALESCE(MAX(cl.CodViajante), 0) AS cod_viajante,
                    COALESCE(MAX(v.Nombre), '') AS nombre_vendedor
                FROM cuentacliente cc
                INNER JOIN cliente cl ON cl.Codigo = cc.Codigo
                LEFT JOIN viajantes v ON v.CodViajante = cl.CodViajante
                WHERE {where_fac_cli_s}
                GROUP BY cl.Codigo
                ORDER BY sub_total DESC
                LIMIT %s
            """
            cursor.execute(sql_fac_cli, params_fac_cli)
            fac_rows = cursor.fetchall()
            fact_map: Dict[int, Dict[str, Any]] = {}
            for r in fac_rows:
                cid = int(r[0])
                fact_map[cid] = {
                    "nombre_cliente": (r[1] or "").strip(),
                    "facturacion": float(r[2] or 0),
                    "cod_viajante": int(r[3] or 0),
                    "nombre_vendedor": (r[4] or "").strip(),
                }

            # --- Remitos por cliente ---
            where_remitos = [
                "cp.Fecha >= %s",
                "cp.Fecha <= %s",
                "cp.TipoComprobante = 'REM'",
                "cp.Anulado = 'No'",
                "cp.Estado = 'Pendiente'",
            ]
            params_rem: List[Any] = [fi_fac_sql, ff_fac_sql]
            if sucursales_ints:
                phs = ",".join(["%s"] * len(sucursales_ints))
                where_remitos.append(f"cp.CodSucursal IN ({phs})")
                params_rem.extend(sucursales_ints)
            if clientes_excluidos:
                ph = ",".join(["%s"] * len(clientes_excluidos))
                where_remitos.append(f"cp.Codigo NOT IN ({ph})")
                params_rem.extend(clientes_excluidos)
            if vendedores_excluidos:
                phv = ",".join(["%s"] * len(vendedores_excluidos))
                where_remitos.append(f"cl_rem.CodViajante NOT IN ({phv})")
                params_rem.extend(vendedores_excluidos)
            sql_rem_cli = f"""
                SELECT cp.Codigo, SUM(COALESCE(cp.SubtotalDesc, 0))
                FROM comp_ped cp
                INNER JOIN cliente cl_rem ON cl_rem.Codigo = cp.Codigo
                WHERE {" AND ".join(where_remitos)}
                GROUP BY cp.Codigo
            """
            cursor.execute(sql_rem_cli, params_rem)
            rem_map: Dict[int, float] = {}
            for r in cursor.fetchall():
                rem_map[int(r[0])] = float(r[1] or 0)

            # --- Unidades vendidas (stock + cuentacliente) ---
            ph_tc = ",".join(["%s"] * len(_TIPOS_FAC_NC))
            ph_st = ",".join(["%s"] * len(_STOCK_TIPO_COMP_VENTAS))
            where_uni = [
                "cc.Fecha >= %s",
                "cc.Fecha <= %s",
                "cc.Anulado = 'No'",
                "cc.CodigoMovimiento <> 0",
                f"cc.TipoComprobante IN ({ph_tc})",
                "st.Anulado = %s",
                f"st.TipoComp IN ({ph_st})",
            ]
            params_uni: List[Any] = [fi_fac_sql, ff_fac_sql] + list(_TIPOS_FAC_NC) + ["No"] + list(_STOCK_TIPO_COMP_VENTAS)
            if sucursales_ints:
                phs = ",".join(["%s"] * len(sucursales_ints))
                where_uni.append(f"cc.CodSucursal IN ({phs})")
                params_uni.extend(sucursales_ints)
            if clientes_excluidos:
                ph = ",".join(["%s"] * len(clientes_excluidos))
                where_uni.append(f"cc.Codigo NOT IN ({ph})")
                params_uni.extend(clientes_excluidos)
            if vendedores_excluidos:
                phv = ",".join(["%s"] * len(vendedores_excluidos))
                where_uni.append(f"cl_uni.CodViajante NOT IN ({phv})")
                params_uni.extend(vendedores_excluidos)
            sql_uni = f"""
                SELECT cc.Codigo,
                    SUM(CASE
                        WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') THEN COALESCE(st.Cantidad, 0)
                        WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') THEN -COALESCE(st.Cantidad, 0)
                        ELSE 0
                    END) AS unidades
                FROM stock st
                INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
                INNER JOIN cliente cl_uni ON cl_uni.Codigo = cc.Codigo
                WHERE {" AND ".join(where_uni)}
                GROUP BY cc.Codigo
            """
            cursor.execute(sql_uni, params_uni)
            uni_map: Dict[int, float] = {}
            for r in cursor.fetchall():
                uni_map[int(r[0])] = float(r[1] or 0)

            # --- Objetivos (solape con rango facturación) ---
            objetivos_map: Dict[int, Decimal] = {}
            try:
                sql_obj = """
                    SELECT v1.Codigo, v1.objetivo
                    FROM viajantes_objetivos_ventas v1
                    INNER JOIN (
                        SELECT v.Codigo, MAX(v.id) AS max_id
                        FROM viajantes_objetivos_ventas v
                        LEFT JOIN viajantes_objetivos_periodo p ON p.id = v.id_periodo
                        WHERE (
                            (v.id_periodo IS NULL AND v.fecha_desde <= %s AND v.fecha_hasta >= %s)
                            OR (
                                v.id_periodo IS NOT NULL
                                AND p.id IS NOT NULL
                                AND COALESCE(p.anulado, 'No') = 'No'
                                AND p.fecha_desde <= %s AND p.fecha_hasta >= %s
                            )
                        )""" + obj_viaj_extra + """
                        GROUP BY v.Codigo
                    ) x ON x.Codigo = v1.Codigo AND x.max_id = v1.id
                """
                ff = d_fac_fin.isoformat()
                fi = d_fac_ini.isoformat()
                cursor.execute(sql_obj, [ff, fi, ff, fi])
                for r in cursor.fetchall():
                    objetivos_map[int(r[0])] = Decimal(str(r[1] or 0))
            except Exception as ex:
                logger.warning("Objetivos ventas: tabla o consulta no disponible: %s", ex)
                notes.append("No se pudieron leer objetivos (¿tabla viajantes_objetivos_ventas creada?).")

            # --- BO por cliente y artículo (misma lógica que BO agregado + prorrateo) ---
            sql_bo_by_client = f"""
                SELECT
                    cp.Codigo AS cod_cliente,
                    sp.IDArt AS id_art,
                    SUM(sp.Cantidad) AS bo_qty,
                    SUM(sp.PrecioNetoxR) AS bo_importe,
                    COALESCE(sd.stock_total, 0) AS stock_actual,
                    COALESCE(reservado_sub.reservado, 0) AS stock_reservado,
                    GREATEST(0, COALESCE(sd.stock_total, 0) - COALESCE(reservado_sub.reservado, 0)) AS disponible,
                    GREATEST(0, COALESCE(oc_pendiente_sub.oc_pendiente, 0)) AS oc_pendiente
                FROM stockp sp
                INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                INNER JOIN cliente cl_bo ON cl_bo.Codigo = cp.Codigo
                LEFT JOIN articulo a ON a.IDArt = sp.IDArt
                LEFT JOIN (
                    SELECT id_articulo, SUM(saldo) AS stock_total
                    FROM stock_deposito{sd_where_excl}
                    GROUP BY id_articulo
                ) sd ON sd.id_articulo = sp.IDArt
                LEFT JOIN (
                    SELECT sp_oc.IDArt AS id_articulo,
                        SUM(COALESCE(sp_oc.cantidad_pendiente, sp_oc.Cantidad - COALESCE(sp_oc.cantidad_entregada, 0))) AS oc_pendiente
                    FROM stockp sp_oc
                    INNER JOIN cuentaproveedor cp_oc ON cp_oc.CodigoMovimiento = sp_oc.CodigoMovimiento
                    WHERE cp_oc.TipoComprobante = 'OC'
                        AND (sp_oc.Comprobante = 'OC' OR sp_oc.Comprobante IS NULL)
                        AND cp_oc.Estado = 'Pendiente'
                        AND cp_oc.Anulado = 'No'
                        AND (sp_oc.anulado IS NULL OR sp_oc.anulado = 'No')
                        AND (COALESCE(sp_oc.cantidad_pendiente, sp_oc.Cantidad - COALESCE(sp_oc.cantidad_entregada, 0)) > 0)
                    GROUP BY sp_oc.IDArt
                ) oc_pendiente_sub ON oc_pendiente_sub.id_articulo = sp.IDArt
                LEFT JOIN (
                    SELECT sp_res.IDArt AS id_articulo,
                        SUM(COALESCE(sp_res.cantidad_pendiente, sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0))) AS reservado
                    FROM stockp sp_res
                    INNER JOIN comp_ped cp_res ON cp_res.CodigoMovimiento = sp_res.CodigoMovimiento
                    INNER JOIN cliente cl_res ON cl_res.Codigo = cp_res.Codigo
                    WHERE cp_res.TipoComprobante = 'PED'
                        AND (sp_res.Comprobante = 'PED' OR sp_res.Comprobante IS NULL)
                        AND cp_res.Anulado = 'No'
                        AND (sp_res.anulado IS NULL OR sp_res.anulado = 'No')
                        AND cp_res.Estado IN ('En preparación', 'Preparado')
                        AND (COALESCE(sp_res.cantidad_pendiente, sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0)) > 0){suc_res_inner}{reservado_excl_clause}{reservado_viaj_clause}
                    GROUP BY sp_res.IDArt
                ) reservado_sub ON reservado_sub.id_articulo = sp.IDArt
                WHERE cp.TipoComprobante = 'PED'
                    AND (sp.Comprobante = 'PED' OR sp.Comprobante IS NULL)
                    AND cp.Anulado = 'No'
                    AND (sp.anulado IS NULL OR sp.anulado = 'No')
                    AND cp.Estado IN {bo_estados}
                    AND sp.CodigoMovimiento IS NOT NULL
                    {suc_bo_ph}{viaj_bo}
                    AND sp.Fecha >= %s AND sp.Fecha <= %s{clientes_excl_bo}
                    AND (a.IDArt IS NULL OR a.tipo_art IS NULL OR a.tipo_art <> 'Gasto')
                GROUP BY cp.Codigo, sp.IDArt, sd.stock_total, oc_pendiente_sub.oc_pendiente, reservado_sub.reservado
                HAVING bo_qty > 0
            """
            _bo_params: List[Any] = []
            if sucursales_ints:
                _bo_params.extend(sucursales_ints)
            if vendedores_excluidos:
                _bo_params.extend(vendedores_excluidos)
            _bo_params.extend([fecha_inicio_bo, fecha_fin_bo])
            cursor.execute(sql_bo_by_client, _bo_params)
            bo_cli_agg: Dict[int, Dict[str, float]] = defaultdict(
                lambda: {"bo_total": 0.0, "con_stock": 0.0, "con_ingreso": 0.0, "sin_stock": 0.0}
            )
            for row in cursor.fetchall():
                cod_c = int(row[0])
                bo_qty = float(row[2] or 0)
                bo_importe = float(row[3] or 0)
                stock_actual = float(row[4] or 0)
                stock_reservado = float(row[5] or 0)
                disponible = float(row[6] or 0)
                oc_pendiente = float(row[7] or 0)
                faltante_reservado = max(0.0, stock_reservado - stock_actual)
                oc_para_reservado = min(oc_pendiente, faltante_reservado)
                oc_restante_bo = max(0.0, oc_pendiente - oc_para_reservado)
                con_stock_qty = min(bo_qty, disponible)
                rest = bo_qty - con_stock_qty
                con_ingreso_qty = min(rest, oc_restante_bo)
                sin_stock_qty = rest - con_ingreso_qty
                if bo_qty > 0:
                    csi = bo_importe * (con_stock_qty / bo_qty)
                    cii = bo_importe * (con_ingreso_qty / bo_qty)
                    ssi = bo_importe * (sin_stock_qty / bo_qty)
                else:
                    csi = cii = ssi = 0.0
                a = bo_cli_agg[cod_c]
                a["bo_total"] += bo_importe
                a["con_stock"] += csi
                a["con_ingreso"] += cii
                a["sin_stock"] += ssi

            all_ids = sorted(
                set(fact_map.keys())
                | set(rem_map.keys())
                | set(uni_map.keys())
                | set(bo_cli_agg.keys())
                | set(objetivos_map.keys())
            )
            master: Dict[int, Dict[str, Any]] = {}
            if all_ids:
                ph = ",".join(["%s"] * len(all_ids))
                cursor.execute(
                    f"""
                    SELECT cl.Codigo, COALESCE(cl.nombre_cliente, ''), COALESCE(cl.CodViajante, 0), COALESCE(v.Nombre, '')
                    FROM cliente cl
                    LEFT JOIN viajantes v ON v.CodViajante = cl.CodViajante
                    WHERE cl.Codigo IN ({ph})
                    """,
                    all_ids,
                )
                for r in cursor.fetchall():
                    master[int(r[0])] = {
                        "nombre_cliente": (r[1] or "").strip(),
                        "cod_viajante": int(r[2] or 0),
                        "nombre_vendedor": (r[3] or "").strip(),
                    }

            rows_out: List[Dict[str, Any]] = []
            for cid in all_ids:
                m = master.get(cid)
                if not m or m["cod_viajante"] == 0:
                    continue
                nom_c = m["nombre_cliente"]
                cv = m["cod_viajante"]
                if vendedores_excluidos and cv in vendedores_excluidos:
                    continue
                nv = m["nombre_vendedor"]
                fm = fact_map.get(cid)

                fac = float(fm["facturacion"]) if fm else 0.0
                rem = rem_map.get(cid, 0.0)
                uni = uni_map.get(cid, 0.0)
                bo = bo_cli_agg.get(cid, {"bo_total": 0.0, "con_stock": 0.0, "con_ingreso": 0.0, "sin_stock": 0.0})
                obj = float(objetivos_map.get(cid, Decimal("0")))
                total_fr = float(calcular_total_facturacion_remitos(fac, rem))
                falta = float(calcular_falta(obj, fac, rem))

                rows_out.append(
                    {
                        "codigo_cliente": cid,
                        "nombre_cliente": nom_c,
                        "cod_viajante": cv,
                        "nombre_vendedor": nv,
                        "objetivo": obj,
                        "facturacion": fac,
                        "remitos": rem,
                        "total": total_fr,
                        "falta": falta,
                        "cantidades_vendidas": uni,
                        "backorder_total": bo["bo_total"],
                        "bo_con_stock": bo["con_stock"],
                        "bo_con_ingreso": bo["con_ingreso"],
                        "bo_sin_stock": bo["sin_stock"],
                    }
                )

            rows_out.sort(
                key=lambda r: (
                    int(r.get("cod_viajante") or 0),
                    int(r.get("codigo_cliente") or 0),
                )
            )

            # Árbol vendedor → clientes
            grupos: Dict[int, Dict[str, Any]] = {}
            for row in rows_out:
                cv = row["cod_viajante"]
                if cv not in grupos:
                    grupos[cv] = {
                        "tipo": "vendedor",
                        "cod_viajante": cv,
                        "nombre_vendedor": row["nombre_vendedor"] or f"Vendedor {cv}",
                        "children": [],
                        "objetivo": 0.0,
                        "facturacion": 0.0,
                        "remitos": 0.0,
                        "total": 0.0,
                        "falta": 0.0,
                        "cantidades_vendidas": 0.0,
                        "backorder_total": 0.0,
                        "bo_con_stock": 0.0,
                        "bo_con_ingreso": 0.0,
                        "bo_sin_stock": 0.0,
                    }
                g = grupos[cv]
                ch = {**row, "tipo": "cliente"}
                g["children"].append(ch)
                for k in (
                    "objetivo",
                    "facturacion",
                    "remitos",
                    "total",
                    "falta",
                    "cantidades_vendidas",
                    "backorder_total",
                    "bo_con_stock",
                    "bo_con_ingreso",
                    "bo_sin_stock",
                ):
                    g[k] = float(g.get(k, 0) or 0) + float(row.get(k, 0) or 0)

            for g in grupos.values():
                g["children"].sort(
                    key=lambda x: (
                        int(x.get("codigo_cliente") or 0),
                        (x.get("nombre_cliente") or "").upper(),
                    )
                )

            arbol = sorted(grupos.values(), key=lambda x: int(x.get("cod_viajante") or 0))

            tot = {
                "objetivo": sum(float(x["objetivo"]) for x in rows_out),
                "facturacion": sum(float(x["facturacion"]) for x in rows_out),
                "remitos": sum(float(x["remitos"]) for x in rows_out),
                "total": sum(float(x["total"]) for x in rows_out),
                "falta": sum(float(x["falta"]) for x in rows_out),
                "cantidades_vendidas": sum(float(x["cantidades_vendidas"]) for x in rows_out),
                "backorder_total": sum(float(x["backorder_total"]) for x in rows_out),
                "bo_con_stock": sum(float(x["bo_con_stock"]) for x in rows_out),
                "bo_con_ingreso": sum(float(x["bo_con_ingreso"]) for x in rows_out),
                "bo_sin_stock": sum(float(x["bo_sin_stock"]) for x in rows_out),
                "total_clientes": len(rows_out),
                "total_vendedores": len(arbol),
            }

            filters_applied = {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "fecha_inicio_facturacion": fi_fac_sql,
                "fecha_fin_facturacion": ff_fac_sql,
                "fecha_inicio_bo": fecha_inicio_bo,
                "fecha_fin_bo": fecha_fin_bo,
                "sucursales": sucursales_ints,
                "depositos_incluidos": depositos_incluidos,
                "clientes_excluidos": clientes_excluidos,
                "vendedores_excluidos": vendedores_excluidos,
                "lista_precio": lista_precio,
                "lista_precio_label": _label_lista_precio(lista_precio),
            }
            notes.insert(
                0,
                f"Facturación/remitos: {fi_fac_sql} a {ff_fac_sql}. Backorder: {fecha_inicio_bo} a {fecha_fin_bo}.",
            )
            notes.append(f"Clientes en grilla: {len(rows_out)} (facturación top {FAC_LIMIT} + otros con movimiento/objetivo).")

            extra = {
                "tabs": {
                    "objetivos_jerarquia": arbol,
                    "objetivos_filas": rows_out,
                },
            }
            cursor.close()

        return QueryResult(
            meta={
                "slug": report.slug,
                "name": report.name,
                "category": report.category,
                "version": report.version,
                "extra": extra,
                "filters_applied": filters_applied,
            },
            data=rows_out,
            totals=tot,
            notes=notes,
        )
    except Exception as e:
        logger.exception("ventas_objetivos_vs_bo: %s", e)
        return QueryResult(
            meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
            data=[],
            totals={},
            notes=[f"Error al ejecutar el informe: {e}"],
        )
