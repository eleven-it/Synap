"""
Agregados del panel «Resumen ejecutivo (ventas)»: solo facturación en ``cuentacliente``.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

_TIPOS_FA_FM = ("FA", "FB", "FC", "FE", "FM")
_TIPOS_NC = ("NCA", "NCB", "NCC", "NCE", "NCM")
_TIPOS_TODOS = _TIPOS_FA_FM + _TIPOS_NC

_STOCK_TIPO_COMP = (
    "Venta",
    "Venta TPV",
    "Devol - Cliente",
    "ND Anul NC",
)


def _net_line_sql(alias: str = "cc") -> str:
    return f"""CASE
        WHEN {alias}.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
            THEN COALESCE({alias}.SubtotalDesc, 0)
        WHEN {alias}.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
            THEN -COALESCE({alias}.SubtotalDesc, 0)
        ELSE 0
    END"""


def _base_cc_where(alias: str = "cc") -> Tuple[str, List[Any]]:
    """Condiciones comunes sobre cuentacliente (sin filtro de fecha)."""
    ph = ",".join(["%s"] * len(_TIPOS_TODOS))
    w = (
        f"{alias}.Anulado = 'No' AND {alias}.CodigoMovimiento <> 0 "
        f"AND {alias}.TipoComprobante IN ({ph})"
    )
    return w, list(_TIPOS_TODOS)


def _ventas_netas_dia(cursor, dia: date) -> float:
    base_w, base_p = _base_cc_where("cc")
    sql = f"""
        SELECT SUM({_net_line_sql('cc')}) AS v
        FROM cuentacliente cc
        WHERE cc.Fecha = %s AND {base_w}
    """
    params: List[Any] = [dia] + base_p
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def _tickets_dia(cursor, dia: date) -> int:
    ph = ",".join(["%s"] * len(_TIPOS_FA_FM))
    base_w, base_p = _base_cc_where("cc")
    sql = f"""
        SELECT COUNT(*) AS c
        FROM cuentacliente cc
        WHERE cc.Fecha = %s AND {base_w}
        AND cc.TipoComprobante IN ({ph})
    """
    params: List[Any] = [dia] + base_p + list(_TIPOS_FA_FM)
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def _unidades_dia(cursor, dia: date) -> float:
    base_w, base_p = _base_cc_where("cc")
    ph_tc = ",".join(["%s"] * len(_STOCK_TIPO_COMP))
    sql = f"""
        SELECT SUM(
            CASE
                WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
                    THEN COALESCE(st.Cantidad, 0)
                WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
                    THEN -COALESCE(st.Cantidad, 0)
                ELSE 0
            END
        ) AS u
        FROM stock st
        INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
        WHERE cc.Fecha = %s
          AND {base_w}
          AND st.Anulado = 'No'
          AND st.TipoComp IN ({ph_tc})
    """
    params = [dia] + base_p + list(_STOCK_TIPO_COMP)
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def _serie_horaria(cursor, dia: date) -> List[Dict[str, Any]]:
    base_w, base_p = _base_cc_where("cc")
    sql = f"""
        SELECT HOUR(cc.FechaControl) AS hora, SUM({_net_line_sql('cc')}) AS ventas_netas
        FROM cuentacliente cc
        WHERE cc.Fecha = %s AND {base_w}
        GROUP BY HOUR(cc.FechaControl)
        ORDER BY hora
    """
    params = [dia] + base_p
    cursor.execute(sql, params)
    by_h = {int(r[0]): float(r[1] or 0) for r in cursor.fetchall() if r[0] is not None}
    out = []
    for h in range(24):
        out.append({"hora": h, "ventas_netas": round(by_h.get(h, 0.0), 2)})
    return out


def _serie_7_dias(cursor, fecha_fin: date) -> List[Dict[str, Any]]:
    fecha_ini = fecha_fin - timedelta(days=6)
    base_w, base_p = _base_cc_where("cc")
    sql = f"""
        SELECT cc.Fecha AS dia, SUM({_net_line_sql('cc')}) AS ventas_netas
        FROM cuentacliente cc
        WHERE cc.Fecha >= %s AND cc.Fecha <= %s AND {base_w}
        GROUP BY cc.Fecha
        ORDER BY cc.Fecha
    """
    params = [fecha_ini, fecha_fin] + base_p
    cursor.execute(sql, params)
    raw = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}
    out = []
    d = fecha_ini
    while d <= fecha_fin:
        out.append({"fecha": d.isoformat(), "ventas_netas": round(raw.get(d, 0.0), 2)})
        d += timedelta(days=1)
    return out


def _split_canal(
    cursor,
    dia: date,
    mayorista_ids: Sequence[int],
    minorista_ids: Sequence[int],
) -> Dict[str, float]:
    base_w, base_p = _base_cc_where("cc")
    net = _net_line_sql("cc")

    def _sum_for_pvs(pvs: Sequence[int]) -> float:
        if not pvs:
            return 0.0
        ph = ",".join(["%s"] * len(pvs))
        sql = f"""
            SELECT SUM({net}) AS v
            FROM cuentacliente cc
            WHERE cc.Fecha = %s AND {base_w} AND cc.id_pv IN ({ph})
        """
        params = [dia] + base_p + list(pvs)
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return float(row[0] or 0) if row else 0.0

    m_may = _sum_for_pvs(mayorista_ids)
    m_min = _sum_for_pvs(minorista_ids)
    total_dia = _ventas_netas_dia(cursor, dia)
    asignado = m_may + m_min
    sin_asignar = max(0.0, total_dia - asignado)
    return {
        "mayorista": round(m_may, 2),
        "minorista": round(m_min, 2),
        "sin_asignar": round(sin_asignar, 2),
    }


def _pct_change(actual: float, anterior: float) -> Optional[float]:
    if anterior == 0:
        return None
    return round((actual - anterior) / anterior * 100.0, 2)


def run_executive_summary(
    cursor,
    fecha_referencia: date,
    mayorista_ids: Sequence[int],
    minorista_ids: Sequence[int],
) -> Dict[str, Any]:
    """
    Calcula payload del panel ejecutivo. ``cursor`` sobre MySQL empresa.
    """
    hoy = fecha_referencia
    ayer = hoy - timedelta(days=1)
    semana_pasada = hoy - timedelta(days=7)

    v_hoy = _ventas_netas_dia(cursor, hoy)
    v_ayer = _ventas_netas_dia(cursor, ayer)
    v_sem = _ventas_netas_dia(cursor, semana_pasada)

    tickets = _tickets_dia(cursor, hoy)
    ticket_prom = (v_hoy / tickets) if tickets else None

    unidades = _unidades_dia(cursor, hoy)

    split = _split_canal(cursor, hoy, mayorista_ids, minorista_ids)

    return {
        "fecha_referencia": hoy.isoformat(),
        "kpis": {
            "ventas_netas_dia": round(v_hoy, 2),
            "pct_vs_ayer": _pct_change(v_hoy, v_ayer),
            "pct_vs_misma_semana_anterior": _pct_change(v_hoy, v_sem),
            "tickets": tickets,
            "ticket_promedio": round(ticket_prom, 2) if ticket_prom is not None else None,
            "unidades_vendidas": round(unidades, 4),
            "ventas_ayer_monto": round(v_ayer, 2),
            "ventas_misma_semana_anterior_monto": round(v_sem, 2),
        },
        "split_mayorista_minorista": split,
        "serie_horaria": _serie_horaria(cursor, hoy),
        "serie_7_dias": _serie_7_dias(cursor, hoy),
        "meta": {
            "definicion": "executive-sales-v1",
            "hora_eje": "FechaControl",
            "dia_contable": "Fecha",
        },
    }


def fetch_puntos_venta_activos(cursor) -> List[Dict[str, Any]]:
    """Lista PV no anulados (mismo criterio que filtros API)."""
    cursor.execute(
        """
        SELECT id_punto_venta, nro_punto_venta, id_sucursal
        FROM punto_venta
        WHERE anulado = 'No' OR anulado IS NULL
        ORDER BY nro_punto_venta, id_punto_venta
        """
    )
    cols = [d[0] for d in cursor.description]
    out = []
    for row in cursor.fetchall():
        r = dict(zip(cols, row))
        id_pv = int(r["id_punto_venta"])
        nro = r.get("nro_punto_venta")
        label = f"PV {nro}" if nro is not None else f"PV {id_pv}"
        out.append(
            {
                "id_pv": id_pv,
                "label": label,
                "nro_punto_venta": nro,
                "id_sucursal": r.get("id_sucursal"),
            }
        )
    return out
