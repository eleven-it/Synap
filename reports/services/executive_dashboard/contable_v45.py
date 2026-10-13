"""Gestión contable V45 basada en modCM_ContableDatos.bas."""
from __future__ import annotations
from datetime import timedelta

from .base import DashboardFilters, build_meta, round_money
from .resumen_v45 import _table_exists


CONTABLE_V45_KEYS = (
    "asientos", "total_debe", "total_haber", "diferencia",
    "desbalanceados", "manuales", "proceso", "resultado_contable",
    "impuestos_determinados", "impuestos_pagar", "impuestos_favor",
    "impuestos_vencidos", "periodos_abiertos", "ejercicios_abiertos",
)


def _scope(filters: DashboardFilters, alias: str = "a", grupo_contable: int | None = None) -> tuple[str, list[int]]:
    clauses = []
    values: list[int] = []
    if filters.sucursales_filtro:
        clauses.append(f"{alias}.id_sucursal IN ({','.join(['%s'] * len(filters.sucursales_filtro))})")
        values.extend(filters.sucursales_filtro)
    if grupo_contable is not None:
        clauses.append(f"{alias}.id_grupo_contable=%s")
        values.append(grupo_contable)
    return (" AND " + " AND ".join(clauses) if clauses else ""), values


def _period(filters: DashboardFilters) -> list[str]:
    return [filters.fecha_inicio_str, (filters.fecha_fin + timedelta(days=1)).isoformat()]


def _asientos(cursor, filters: DashboardFilters, grupo_contable: int | None) -> dict:
    scope, params = _scope(filters, grupo_contable=grupo_contable)
    cursor.execute(
        f"""SELECT COUNT(DISTINCT CONCAT(COALESCE(a.id_ejercicio,0),'-',COALESCE(a.nro_asiento,0))),
              COALESCE(SUM(a.debe_asiento),0),COALESCE(SUM(a.haber_asiento),0),
              COUNT(DISTINCT CASE WHEN UPPER(COALESCE(a.balanceado_asiento,'NO'))<>'SI'
                THEN CONCAT(COALESCE(a.id_ejercicio,0),'-',COALESCE(a.nro_asiento,0)) END),
              COUNT(DISTINCT CASE WHEN UPPER(COALESCE(a.tipo_asiento,''))='MANUAL'
                THEN CONCAT(COALESCE(a.id_ejercicio,0),'-',COALESCE(a.nro_asiento,0)) END),
              COUNT(DISTINCT CASE WHEN UPPER(COALESCE(a.tipo_asiento,''))='PROCESO'
                THEN CONCAT(COALESCE(a.id_ejercicio,0),'-',COALESCE(a.nro_asiento,0)) END)
            FROM cont_asiento a WHERE a.fecha_asiento >= %s AND a.fecha_asiento < %s
              AND a.anulado='No'{scope}""",
        _period(filters) + params,
    )
    row = cursor.fetchone() or (0,) * 6
    count, debit, credit, unbalanced, manual, process = row
    debit = round_money(debit)
    credit = round_money(credit)
    return {
        "asientos": int(count or 0), "total_debe": debit, "total_haber": credit,
        "diferencia": round_money(debit - credit),
        "desbalanceados": int(unbalanced or 0), "manuales": int(manual or 0),
        "proceso": int(process or 0),
    }


def _result(cursor, filters: DashboardFilters, grupo_contable: int | None) -> float | None:
    if not _table_exists(cursor, "cont_pc"):
        return None
    scope, params = _scope(filters, grupo_contable=grupo_contable)
    cursor.execute(
        f"""SELECT COALESCE(SUM(COALESCE(a.haber_asiento,0)-COALESCE(a.debe_asiento,0)),0)
            FROM cont_asiento a JOIN cont_pc p ON p.id_pc=a.id_pc
            WHERE a.fecha_asiento >= %s AND a.fecha_asiento < %s
              AND a.anulado='No' AND COALESCE(p.anulado,'No')='No'
              AND UPPER(COALESCE(p.tipo_cuenta_pc,'')) IN ('RESULTADO','GANANCIA','PERDIDA')
              {scope}""",
        _period(filters) + params,
    )
    row = cursor.fetchone()
    return round_money(row[0] if row else 0)


def _tax(cursor, filters: DashboardFilters) -> dict:
    if not _table_exists(cursor, "impuesto_detalle"):
        return {key: None for key in (
            "impuestos_determinados", "impuestos_pagar", "impuestos_favor", "impuestos_vencidos",
        )}
    cursor.execute(
        """SELECT COALESCE(SUM(importe_impdetalle),0),
              COALESCE(SUM(CASE WHEN UPPER(TRIM(COALESCE(Tipo_saldo,'')))='A PAGAR'
                AND UPPER(TRIM(COALESCE(estado_impdetalle,'')))='N/CANC'
                THEN COALESCE(importe_impdetalle,0) ELSE 0 END),0),
              COALESCE(SUM(CASE WHEN UPPER(TRIM(COALESCE(Tipo_saldo,'')))='A FAVOR'
                AND UPPER(TRIM(COALESCE(estado_impdetalle,'')))='N/CANC'
                THEN COALESCE(importe_impdetalle,0) ELSE 0 END),0)
            FROM impuesto_detalle WHERE UPPER(COALESCE(anulado,'NO'))<>'SI'
              AND fechasta_impdetalle >= %s AND fechasta_impdetalle < %s""",
        _period(filters),
    )
    determined, payable, favorable = cursor.fetchone() or (0, 0, 0)
    cursor.execute(
        """SELECT COALESCE(SUM(importe_impdetalle),0)
            FROM impuesto_detalle WHERE UPPER(COALESCE(anulado,'NO'))<>'SI'
              AND UPPER(TRIM(COALESCE(Tipo_saldo,'')))='A PAGAR'
              AND UPPER(TRIM(COALESCE(estado_impdetalle,'')))='N/CANC'
              AND vencimiento_impdetalle < %s""",
        [(filters.fecha_fin + timedelta(days=1)).isoformat()],
    )
    row = cursor.fetchone()
    return {
        "impuestos_determinados": round_money(determined),
        "impuestos_pagar": round_money(payable),
        "impuestos_favor": round_money(favorable),
        "impuestos_vencidos": round_money(row[0] if row else 0),
    }


def _open_periods(cursor, filters: DashboardFilters, *, exercise: bool) -> int | None:
    if exercise:
        table, first, last = "cont_ejercicio", "fecdesde_ejercicio", "fechasta_ejercicio"
    else:
        table, first, last = "cont_periodo", "fecdesde_periodo", "fechasta_periodo"
    if not _table_exists(cursor, table):
        return None
    cursor.execute(
        f"""SELECT COUNT(*) FROM {table} WHERE UPPER(COALESCE(cerrado,'NO'))<>'SI'
          AND {first} <= %s AND {last} >= %s""",
        [filters.fecha_fin_str, filters.fecha_inicio_str],
    )
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def _series(cursor, filters: DashboardFilters, grupo_contable: int | None) -> dict:
    days = (filters.fecha_fin - filters.fecha_inicio).days + 1
    if days <= 45:
        bucket, expression = "dia", "DATE_FORMAT(a.fecha_asiento,'%%Y-%%m-%%d')"
    elif days <= 200:
        bucket, expression = "semana", "DATE_FORMAT(DATE_SUB(a.fecha_asiento,INTERVAL WEEKDAY(a.fecha_asiento) DAY),'%%Y-%%m-%%d')"
    else:
        bucket, expression = "mes", "DATE_FORMAT(a.fecha_asiento,'%%Y-%%m-01')"
    scope, params = _scope(filters, grupo_contable=grupo_contable)
    cursor.execute(
        f"""SELECT {expression},COALESCE(SUM(a.debe_asiento),0),
          COALESCE(SUM(a.haber_asiento),0) FROM cont_asiento a
          WHERE a.fecha_asiento >= %s AND a.fecha_asiento < %s
            AND a.anulado='No'{scope}
          GROUP BY {expression} ORDER BY {expression}""",
        _period(filters) + params,
    )
    return {
        "agrupacion": bucket,
        "filas": [
            {"fecha": str(day), "debe": round_money(debit), "haber": round_money(credit)}
            for day, debit, credit in cursor.fetchall() or []
        ],
    }


def fetch_contable_v45(cursor, filters: DashboardFilters, *, grupo_contable: int | None = None) -> dict:
    if not _table_exists(cursor, "cont_asiento"):
        return {"disponible": False, "motivo": "sin_cont_asiento", "kpis": {}}
    values = {
        **_asientos(cursor, filters, grupo_contable),
        "resultado_contable": _result(cursor, filters, grupo_contable),
        **_tax(cursor, filters),
        "periodos_abiertos": _open_periods(cursor, filters, exercise=False),
        "ejercicios_abiertos": _open_periods(cursor, filters, exercise=True),
    }
    return {
        "kpis": values,
        "serie_asientos": _series(cursor, filters, grupo_contable),
        "alcance": {
            "asientos": "sucursal y grupo contable" if filters.sucursales_filtro or grupo_contable else "general",
            "impuestos_y_periodos": "general",
        },
        "disponible": True,
        "meta": build_meta(filters, fuente="modCM_ContableDatos.bas/V45"),
    }
