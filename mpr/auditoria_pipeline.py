# -*- coding: utf-8 -*-
"""Auditoría read-only del pipeline MPR diario: parte → CC → armado + mstock.

Uso vía ``manage.py auditar_pipeline_mpr``. No muta datos.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _ser(o: Any) -> Any:
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (datetime, date)):
        try:
            return o.isoformat(sep=" ", timespec="seconds")
        except TypeError:
            return o.isoformat()
    return o


def _f(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _i(v: Any) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def iter_fechas(desde: date, hasta: date) -> List[date]:
    if hasta < desde:
        raise ValueError("hasta < desde")
    out: List[date] = []
    d = desde
    while d <= hasta:
        out.append(d)
        d += timedelta(days=1)
    return out


def _fetchone(cursor) -> Dict[str, Any]:
    row = cursor.fetchone() or {}
    return dict(row) if not isinstance(row, dict) else row


def _fetchall(cursor) -> List[Dict[str, Any]]:
    rows = cursor.fetchall() or []
    return [dict(r) if not isinstance(r, dict) else r for r in rows]


def auditar_conexion(cursor) -> Dict[str, Any]:
    cursor.execute("SELECT @@hostname AS host, @@port AS port, DATABASE() AS db, NOW() AS ahora")
    return {k: _ser(v) for k, v in _fetchone(cursor).items()}


def auditar_parte_dia(cursor, fecha: date) -> Dict[str, Any]:
    cursor.execute(
        """
        SELECT COUNT(*) n_partes,
               SUM(CASE WHEN estado='aprobado' THEN 1 ELSE 0 END) n_aprobados,
               SUM(CASE WHEN estado<>'aprobado' THEN 1 ELSE 0 END) n_otros
        FROM mpr_parte
        WHERE fecha_produccion=%s
        """,
        [fecha],
    )
    cab = _fetchone(cursor)

    cursor.execute(
        """
        SELECT COUNT(*) n_lineas,
               COALESCE(SUM(pl.cantidad),0) qty,
               COUNT(DISTINCT pl.id_articulo) n_arts,
               COUNT(DISTINCT pl.id_operario) n_ops,
               COUNT(DISTINCT p.id_mpr_turno) n_turnos
        FROM mpr_parte_linea pl
        JOIN mpr_parte p ON p.id_mpr_parte=pl.id_mpr_parte
        WHERE p.fecha_produccion=%s AND p.estado='aprobado'
        """,
        [fecha],
    )
    lin = _fetchone(cursor)

    # OPP "de parte" reales suelen ir con detalle distinto a Transición MPR (CC).
    cursor.execute(
        """
        SELECT COUNT(*) n_opp,
               COALESCE(SUM(CASE WHEN anulado=0 OR anulado IS NULL THEN 1 ELSE 0 END),0) n_activos,
               COALESCE(SUM(CASE WHEN anulado=1 THEN 1 ELSE 0 END),0) n_anulados,
               COALESCE(SUM(
                 CASE WHEN (anulado=0 OR anulado IS NULL)
                      AND detalle LIKE 'Transición MPR%%' THEN 1 ELSE 0 END
               ),0) n_activos_transicion_cc,
               COALESCE(SUM(
                 CASE WHEN (anulado=0 OR anulado IS NULL)
                      AND (detalle IS NULL OR detalle NOT LIKE 'Transición MPR%%') THEN 1 ELSE 0 END
               ),0) n_activos_otros
        FROM movimiento_stock
        WHERE fecha=%s AND UPPER(TRIM(COALESCE(tipo_mov,'')))='OPP'
        """,
        [fecha],
    )
    opp = _fetchone(cursor)

    cursor.execute(
        """
        SELECT COUNT(*) n_lineas_cuerpo,
               COALESCE(SUM(c.Cantidad),0) qty_cuerpo,
               COUNT(DISTINCT c.CodigoMovimiento) n_mov
        FROM cuerpostock c
        JOIN movimiento_stock m ON m.codigo_movimiento=c.CodigoMovimiento
        WHERE m.fecha=%s AND UPPER(TRIM(COALESCE(m.tipo_mov,'')))='OPP'
          AND (m.anulado=0 OR m.anulado IS NULL)
          AND (m.detalle IS NULL OR m.detalle NOT LIKE 'Transición MPR%%')
        """,
        [fecha],
    )
    cuerpo = _fetchone(cursor)

    cursor.execute(
        """
        SELECT SUM(CASE WHEN COALESCE(movimiento_fisico_ok,0)=1 THEN 1 ELSE 0 END) ok_fisico,
               SUM(CASE WHEN COALESCE(movimiento_fisico_ok,0)=0 THEN 1 ELSE 0 END) sin_fisico
        FROM mpr_parte
        WHERE fecha_produccion=%s AND estado='aprobado'
        """,
        [fecha],
    )
    fisico = _fetchone(cursor)

    alertas: List[str] = []
    n_aprob = _i(cab.get("n_aprobados"))
    n_opp_otros = _i(opp.get("n_activos_otros"))
    if n_aprob > 0 and _i(fisico.get("sin_fisico")) > 0:
        alertas.append(f"partes_aprobados_sin_movimiento_fisico_ok={_i(fisico.get('sin_fisico'))}")
    if n_opp_otros > 0 and _f(cuerpo.get("qty_cuerpo")) <= 0:
        alertas.append("opp_no_transicion_sin_cuerpostock")

    return {
        "partes": {k: _ser(v) for k, v in cab.items()},
        "lineas_aprobadas": {k: _ser(v) for k, v in lin.items()},
        "mstock_opp": {k: _ser(v) for k, v in opp.items()},
        "cuerpostock_opp_no_transicion": {k: _ser(v) for k, v in cuerpo.items()},
        "movimiento_fisico": {k: _ser(v) for k, v in fisico.items()},
        "alertas": alertas,
    }


def auditar_cc_dia(cursor, fecha: date) -> Dict[str, Any]:
    cursor.execute(
        """
        SELECT COUNT(*) n,
               COALESCE(SUM(cantidad),0) qty,
               COALESCE(SUM(COALESCE(cantidad_extra,0)),0) qty_extra,
               COUNT(DISTINCT id_usuario) usuarios,
               COUNT(DISTINCT id_articulo) arts,
               COUNT(DISTINCT id_operario) ops
        FROM mpr_transicion_lote
        WHERE fecha_produccion=%s
        """,
        [fecha],
    )
    tot = _fetchone(cursor)

    cursor.execute(
        """
        SELECT COUNT(*) cc_n,
               SUM(ms.codigo_movimiento IS NULL) sin_ms,
               SUM(ms.codigo_movimiento IS NOT NULL AND ms.fecha<>%s) fecha_diff,
               SUM(
                 ms.codigo_movimiento IS NOT NULL
                 AND UPPER(TRIM(COALESCE(ms.tipo_mov,''))) NOT IN ('OPP','OPA','ARMADO')
               ) tipo_raro,
               SUM(ms.anulado=1) ms_anulado,
               SUM(
                 ms.codigo_movimiento IS NOT NULL
                 AND NOT EXISTS (
                   SELECT 1 FROM cuerpostock c WHERE c.CodigoMovimiento=t.codigo_movimiento
                 )
               ) sin_cuerpostock
        FROM mpr_transicion_lote t
        LEFT JOIN movimiento_stock ms ON ms.codigo_movimiento=t.codigo_movimiento
        WHERE t.fecha_produccion=%s
        """,
        [fecha, fecha],
    )
    join_ms = _fetchone(cursor)

    # fab vs cls art×op×turno
    cursor.execute(
        """
        SELECT pl.id_articulo, pl.id_operario, p.id_mpr_turno, SUM(pl.cantidad) fab
        FROM mpr_parte_linea pl
        JOIN mpr_parte p ON p.id_mpr_parte=pl.id_mpr_parte
        WHERE p.fecha_produccion=%s AND p.estado='aprobado'
        GROUP BY 1,2,3
        """,
        [fecha],
    )
    fab = {
        (_i(r["id_articulo"]), _i(r.get("id_operario")), _i(r["id_mpr_turno"])): _f(r["fab"])
        for r in _fetchall(cursor)
    }

    cursor.execute(
        """
        SELECT id_articulo, id_operario, id_mpr_turno,
               SUM(cantidad) cls,
               SUM(COALESCE(cantidad_extra,0)) extra
        FROM mpr_transicion_lote
        WHERE fecha_produccion=%s
        GROUP BY 1,2,3
        """,
        [fecha],
    )
    cls_rows = _fetchall(cursor)
    cls = {
        (_i(r["id_articulo"]), _i(r.get("id_operario")), _i(r["id_mpr_turno"])): _f(r["cls"])
        for r in cls_rows
    }
    extra_map = {
        (_i(r["id_articulo"]), _i(r.get("id_operario")), _i(r["id_mpr_turno"])): _f(r["extra"])
        for r in cls_rows
    }

    exceso = []
    for k, fval in fab.items():
        cval = cls.get(k, 0.0)
        if cval > fval + 0.01:
            exceso.append(
                {
                    "id_articulo": k[0],
                    "id_operario": k[1],
                    "id_mpr_turno": k[2],
                    "fabricado": round(fval, 2),
                    "clasificado": round(cval, 2),
                    "exceso": round(cval - fval, 2),
                    "cantidad_extra_ledger": round(extra_map.get(k, 0.0), 2),
                }
            )
    exceso.sort(key=lambda x: -x["exceso"])

    deficit = []
    for k, fval in fab.items():
        cval = cls.get(k, 0.0)
        if cval + 0.01 < fval:
            deficit.append(
                {
                    "id_articulo": k[0],
                    "id_operario": k[1],
                    "id_mpr_turno": k[2],
                    "fabricado": round(fval, 2),
                    "clasificado": round(cval, 2),
                    "faltante": round(fval - cval, 2),
                }
            )
    deficit.sort(key=lambda x: -x["faltante"])

    # CC sin parte (art×op×turno)
    huérfanos = []
    for k, cval in cls.items():
        if k not in fab and cval > 0.01:
            huérfanos.append(
                {
                    "id_articulo": k[0],
                    "id_operario": k[1],
                    "id_mpr_turno": k[2],
                    "clasificado": round(cval, 2),
                }
            )
    huérfanos.sort(key=lambda x: -x["clasificado"])

    # Duplicados de clave lógica (mismo art×op×turno×destino con varios registros)
    cursor.execute(
        """
        SELECT COUNT(*) AS n_grupos_dup FROM (
          SELECT id_articulo, id_operario, id_mpr_turno, tipo_destino
          FROM mpr_transicion_lote
          WHERE fecha_produccion=%s
          GROUP BY 1,2,3,4
          HAVING COUNT(*)>1
        ) x
        """,
        [fecha],
    )
    n_dups = _i(_fetchone(cursor).get("n_grupos_dup"))

    cursor.execute(
        """
        SELECT id_articulo, id_operario, id_mpr_turno, tipo_destino, COUNT(*) n,
               SUM(cantidad) qty
        FROM mpr_transicion_lote
        WHERE fecha_produccion=%s
        GROUP BY 1,2,3,4
        HAVING COUNT(*)>1
        ORDER BY n DESC
        LIMIT 40
        """,
        [fecha],
    )
    dups = [{k: _ser(v) for k, v in r.items()} for r in _fetchall(cursor)]

    alertas: List[str] = []
    if _i(join_ms.get("sin_ms")):
        alertas.append(f"cc_sin_mstock={_i(join_ms.get('sin_ms'))}")
    if _i(join_ms.get("fecha_diff")):
        alertas.append(f"cc_mstock_fecha_distinta={_i(join_ms.get('fecha_diff'))}")
    if _i(join_ms.get("sin_cuerpostock")):
        alertas.append(f"cc_mstock_sin_cuerpostock={_i(join_ms.get('sin_cuerpostock'))}")
    if exceso:
        alertas.append(f"cls_gt_fab_celdas={len(exceso)}")
    if huérfanos:
        alertas.append(f"cc_sin_parte_celdas={len(huérfanos)}")
    if n_dups:
        alertas.append(f"cc_dup_clave={n_dups}")

    return {
        "totales": {k: _ser(v) for k, v in tot.items()},
        "mstock_join": {k: _ser(v) for k, v in join_ms.items()},
        "celdas_parte": len(fab),
        "celdas_cc": len(cls),
        "eq": sum(1 for k in fab if abs(fab[k] - cls.get(k, 0)) < 0.01),
        "cls_gt_fab_n": len(exceso),
        "cls_gt_fab_pares": round(sum(x["exceso"] for x in exceso), 2),
        "cls_gt_fab_top": exceso[:25],
        "cls_lt_fab_n": len(deficit),
        "cls_lt_fab_pares": round(sum(x["faltante"] for x in deficit), 2),
        "cls_lt_fab_top": deficit[:25],
        "cc_sin_parte_n": len(huérfanos),
        "cc_sin_parte_top": huérfanos[:25],
        "delta_cls_fab": round(sum(cls.values()) - sum(fab.values()), 2),
        "dups_clave_n": n_dups,
        "dups_clave": dups,
        "alertas": alertas,
    }


def auditar_armado_dia(cursor, fecha: date) -> Dict[str, Any]:
    # Lotes por fecha_realizado (criterio operativo) o DATE(ejecutado_en) si fecha_realizado null
    cursor.execute(
        """
        SELECT COUNT(*) n_lotes,
               SUM(CASE WHEN estado='aprobado' THEN 1 ELSE 0 END) n_aprobados,
               SUM(CASE WHEN estado='borrador' THEN 1 ELSE 0 END) n_borrador,
               SUM(COALESCE(cantidad_items,0)) items,
               SUM(COALESCE(cantidad_exitosos,0)) exitosos,
               SUM(COALESCE(cantidad_fallidos,0)) fallidos
        FROM mpr_armado_lote
        WHERE COALESCE(fecha_realizado, DATE(ejecutado_en))=%s
        """,
        [fecha],
    )
    lotes = _fetchone(cursor)

    cursor.execute(
        """
        SELECT COUNT(*) n_mov,
               COALESCE(SUM(cantidad_packs),0) packs,
               COUNT(DISTINCT id_articulo_pack) n_packs,
               SUM(ms.codigo_movimiento IS NULL) sin_ms,
               SUM(ms.codigo_movimiento IS NOT NULL AND ms.fecha<>%s) fecha_diff,
               SUM(
                 ms.codigo_movimiento IS NOT NULL
                 AND UPPER(TRIM(COALESCE(ms.tipo_mov,''))) NOT IN ('OPA','ARMADO')
               ) tipo_raro,
               SUM(ms.anulado=1) ms_anulado
        FROM mpr_armado_surtido_movimiento a
        JOIN mpr_armado_lote l ON l.id_mpr_armado_lote=a.id_mpr_armado_lote
        LEFT JOIN movimiento_stock ms ON ms.codigo_movimiento=a.codigo_movimiento
        WHERE COALESCE(l.fecha_realizado, DATE(l.ejecutado_en))=%s
        """,
        [fecha, fecha],
    )
    mov = _fetchone(cursor)

    cursor.execute(
        """
        SELECT COUNT(*) n_lineas_cuerpo,
               COALESCE(SUM(ABS(c.Cantidad)),0) qty_abs,
               COUNT(DISTINCT c.CodigoMovimiento) n_mov
        FROM cuerpostock c
        JOIN movimiento_stock m ON m.codigo_movimiento=c.CodigoMovimiento
        WHERE m.fecha=%s
          AND UPPER(TRIM(COALESCE(m.tipo_mov,''))) IN ('OPA','ARMADO')
          AND (m.anulado=0 OR m.anulado IS NULL)
        """,
        [fecha],
    )
    cuerpo = _fetchone(cursor)

    cursor.execute(
        """
        SELECT COUNT(*) n_opa,
               COALESCE(SUM(CASE WHEN anulado=0 OR anulado IS NULL THEN 1 ELSE 0 END),0) n_activos
        FROM movimiento_stock
        WHERE fecha=%s AND UPPER(TRIM(COALESCE(tipo_mov,''))) IN ('OPA','ARMADO')
        """,
        [fecha],
    )
    opa = _fetchone(cursor)

    # Cuerpostock de los mstock referenciados por armado del día (aunque fecha mstock difiera)
    cursor.execute(
        """
        SELECT COUNT(*) n_mov_arm,
               SUM(
                 NOT EXISTS (
                   SELECT 1 FROM cuerpostock c WHERE c.CodigoMovimiento=a.codigo_movimiento
                 )
               ) sin_cuerpo
        FROM mpr_armado_surtido_movimiento a
        JOIN mpr_armado_lote l ON l.id_mpr_armado_lote=a.id_mpr_armado_lote
        WHERE COALESCE(l.fecha_realizado, DATE(l.ejecutado_en))=%s
        """,
        [fecha],
    )
    cuerpo_ref = _fetchone(cursor)

    alertas: List[str] = []
    if _i(lotes.get("n_aprobados")) > 0 and _i(mov.get("n_mov")) == 0:
        alertas.append("lotes_aprobados_sin_surtido_movimiento")
    if _i(mov.get("sin_ms")):
        alertas.append(f"armado_sin_mstock={_i(mov.get('sin_ms'))}")
    if _i(mov.get("fecha_diff")):
        alertas.append(f"armado_mstock_fecha_distinta={_i(mov.get('fecha_diff'))}")
    if _i(cuerpo_ref.get("sin_cuerpo")):
        alertas.append(f"armado_mstock_sin_cuerpostock={_i(cuerpo_ref.get('sin_cuerpo'))}")
    if _i(opa.get("n_activos")) > 0 and _f(cuerpo.get("qty_abs")) <= 0:
        alertas.append("opa_mstock_fecha_dia_sin_cuerpostock")

    return {
        "lotes": {k: _ser(v) for k, v in lotes.items()},
        "surtido_mov": {k: _ser(v) for k, v in mov.items()},
        "mstock_opa": {k: _ser(v) for k, v in opa.items()},
        "cuerpostock_opa_fecha_mstock": {k: _ser(v) for k, v in cuerpo.items()},
        "cuerpostock_por_ref_armado": {k: _ser(v) for k, v in cuerpo_ref.items()},
        "alertas": alertas,
    }


def auditar_dia(cursor, fecha: date) -> Dict[str, Any]:
    parte = auditar_parte_dia(cursor, fecha)
    cc = auditar_cc_dia(cursor, fecha)
    armado = auditar_armado_dia(cursor, fecha)

    alertas = list(parte.get("alertas") or []) + list(cc.get("alertas") or []) + list(
        armado.get("alertas") or []
    )
    severidad = "ok"
    if alertas:
        severidad = "alerta"
    if cc.get("cls_gt_fab_n") or _i((cc.get("mstock_join") or {}).get("sin_ms")):
        severidad = "critico" if cc.get("cls_gt_fab_n") else severidad

    return {
        "fecha": fecha.strftime("%d/%m/%Y"),
        "fecha_iso": fecha.isoformat(),
        "severidad": severidad,
        "parte": parte,
        "cc": cc,
        "armado": armado,
        "alertas": alertas,
        "resumen_dia": {
            "parte_pares": _f((parte.get("lineas_aprobadas") or {}).get("qty")),
            "cc_pares": _f((cc.get("totales") or {}).get("qty")),
            "delta_cls_fab": cc.get("delta_cls_fab"),
            "cls_gt_fab_n": cc.get("cls_gt_fab_n"),
            "armado_packs": _f((armado.get("surtido_mov") or {}).get("packs")),
            "armado_lotes": _i((armado.get("lotes") or {}).get("n_lotes")),
            "n_alertas": len(alertas),
        },
    }


def auditar_rango(
    cursor,
    base_empresa: str,
    desde: date,
    hasta: date,
) -> Dict[str, Any]:
    dias = [auditar_dia(cursor, f) for f in iter_fechas(desde, hasta)]
    resumen = {
        "dias": len(dias),
        "dias_con_parte": sum(
            1 for d in dias if _f(d["resumen_dia"]["parte_pares"]) > 0
        ),
        "dias_con_cc": sum(1 for d in dias if _f(d["resumen_dia"]["cc_pares"]) > 0),
        "dias_con_armado": sum(
            1 for d in dias if _i(d["resumen_dia"]["armado_lotes"]) > 0
        ),
        "dias_alerta": sum(1 for d in dias if d["severidad"] != "ok"),
        "dias_critico": sum(1 for d in dias if d["severidad"] == "critico"),
        "total_cls_gt_fab_celdas": sum(_i(d["cc"].get("cls_gt_fab_n")) for d in dias),
        "total_cls_gt_fab_pares": round(
            sum(_f(d["cc"].get("cls_gt_fab_pares")) for d in dias), 2
        ),
        "total_cc_sin_mstock": sum(
            _i((d["cc"].get("mstock_join") or {}).get("sin_ms")) for d in dias
        ),
        "total_cc_sin_cuerpostock": sum(
            _i((d["cc"].get("mstock_join") or {}).get("sin_cuerpostock")) for d in dias
        ),
        "total_armado_sin_mstock": sum(
            _i((d["armado"].get("surtido_mov") or {}).get("sin_ms")) for d in dias
        ),
    }
    return {
        "base_empresa": base_empresa,
        "desde": desde.strftime("%d/%m/%Y"),
        "hasta": hasta.strftime("%d/%m/%Y"),
        "conexion": auditar_conexion(cursor),
        "resumen": resumen,
        "dias": dias,
    }
