"""KPIs libro banco — Command Center gerencial (P1)."""
from __future__ import annotations

from typing import Any

from core.utils.administranet_types import str_or_default, to_int_or_none

from .base import DashboardFilters, build_meta, round_money


def _fecha_libro_expr(alias: str = "lb") -> str:
    return f"COALESCE({alias}.FechaMov, {alias}.Fecha)"


def _anulado_libro(alias: str = "lb") -> str:
    return f"COALESCE({alias}.Anulado, 'No') != 'Si'"


def _where_librobanco_period(filters: DashboardFilters) -> tuple[str, list]:
    fecha = _fecha_libro_expr("lb")
    conds = [
        _anulado_libro("lb"),
        "lb.CodCuenta IS NOT NULL",
        f"{fecha} >= %s",
        f"{fecha} <= %s",
    ]
    params: list = [filters.fecha_inicio_str, filters.fecha_fin_str]
    if filters.cod_sucursal is not None:
        conds.append("lb.CodSucursal = %s")
        params.append(filters.cod_sucursal)
    return " AND ".join(conds), params


def sum_saldo_banco(
    cursor,
    fecha_limite: str,
    *,
    antes_de: bool,
    cod_sucursal: int | None = None,
) -> float:
    """Suma último librobanco.Saldo por CodCuenta antes o hasta fecha_limite."""
    op = "<" if antes_de else "<="
    fecha = _fecha_libro_expr("lb")
    suc_sql = ""
    suc_params: list = []
    if cod_sucursal is not None:
        suc_sql = " AND CodSucursal = %s"
        suc_params = [cod_sucursal]
    anul = f"COALESCE(Anulado, 'No') != 'Si'"
    fecha_plain = "COALESCE(FechaMov, Fecha)"
    base_where = f"""
        {anul}
        AND CodCuenta IS NOT NULL
        AND {fecha_plain} {op} %s
        {suc_sql}
    """
    sql = f"""
        SELECT COALESCE(SUM(lb.Saldo), 0)
        FROM librobanco lb
        INNER JOIN (
            SELECT CodCuenta, MAX({fecha_plain}) AS max_fecha
            FROM librobanco
            WHERE {base_where}
            GROUP BY CodCuenta
        ) ult_f ON ult_f.CodCuenta = lb.CodCuenta
              AND {fecha} = ult_f.max_fecha
        INNER JOIN (
            SELECT CodCuenta, {fecha_plain} AS fecha_g, MAX(CodMov) AS max_mov
            FROM librobanco
            WHERE {base_where}
            GROUP BY CodCuenta, {fecha_plain}
        ) ult_m ON ult_m.CodCuenta = lb.CodCuenta
              AND ult_m.fecha_g = {fecha}
              AND ult_m.max_mov = lb.CodMov
        WHERE {anul}
    """
    params = (
        [fecha_limite] + suc_params + [fecha_limite] + suc_params
    )
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def _saldo_por_cuenta_map(
    cursor,
    fecha_limite: str,
    *,
    antes_de: bool,
    cod_sucursal: int | None,
) -> dict[int, float]:
    op = "<" if antes_de else "<="
    fecha = _fecha_libro_expr("lb")
    suc_sql = ""
    suc_params: list = []
    if cod_sucursal is not None:
        suc_sql = " AND CodSucursal = %s"
        suc_params = [cod_sucursal]
    anul = f"COALESCE(Anulado, 'No') != 'Si'"
    fecha_plain = "COALESCE(FechaMov, Fecha)"
    base_where = f"""
        {anul}
        AND CodCuenta IS NOT NULL
        AND {fecha_plain} {op} %s
        {suc_sql}
    """
    sql = f"""
        SELECT lb.CodCuenta, lb.Saldo
        FROM librobanco lb
        INNER JOIN (
            SELECT CodCuenta, MAX({fecha_plain}) AS max_fecha
            FROM librobanco
            WHERE {base_where}
            GROUP BY CodCuenta
        ) ult_f ON ult_f.CodCuenta = lb.CodCuenta
              AND {fecha} = ult_f.max_fecha
        INNER JOIN (
            SELECT CodCuenta, {fecha_plain} AS fecha_g, MAX(CodMov) AS max_mov
            FROM librobanco
            WHERE {base_where}
            GROUP BY CodCuenta, {fecha_plain}
        ) ult_m ON ult_m.CodCuenta = lb.CodCuenta
              AND ult_m.fecha_g = {fecha}
              AND ult_m.max_mov = lb.CodMov
        WHERE {anul}
    """
    params = [fecha_limite] + suc_params + [fecha_limite] + suc_params
    cursor.execute(sql, params)
    out: dict[int, float] = {}
    for cod, saldo in cursor.fetchall():
        cid = to_int_or_none(cod)
        if cid is not None:
            out[cid] = float(saldo or 0)
    return out


def _count_pendiente_conciliar(cursor, filters: DashboardFilters) -> int:
    fecha = _fecha_libro_expr("lb")
    conds = [
        _anulado_libro("lb"),
        f"{fecha} <= %s",
        "(lb.conciliado IS NULL OR lb.conciliado NOT IN ('Si', 'si'))",
    ]
    params: list = [filters.fecha_fin_str]
    if filters.cod_sucursal is not None:
        conds.append("lb.CodSucursal = %s")
        params.append(filters.cod_sucursal)
    sql = f"SELECT COUNT(*) FROM librobanco lb WHERE {' AND '.join(conds)}"
    try:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def fetch_tesoreria_banco_resumen(cursor, filters: DashboardFilters) -> dict[str, Any]:
    where_period, params_period = _where_librobanco_period(filters)
    fecha = _fecha_libro_expr("lb")

    saldo_inicial = sum_saldo_banco(
        cursor, filters.fecha_inicio_str, antes_de=True, cod_sucursal=filters.cod_sucursal
    )
    saldo_final = sum_saldo_banco(
        cursor, filters.fecha_fin_str, antes_de=False, cod_sucursal=filters.cod_sucursal
    )

    sql_flujos = f"""
        SELECT
            COALESCE(SUM(COALESCE(lb.Credito, 0)), 0),
            COALESCE(SUM(COALESCE(lb.Debito, 0)), 0)
        FROM librobanco lb
        WHERE {where_period}
    """
    cursor.execute(sql_flujos, params_period)
    row = cursor.fetchone() or (0, 0)
    creditos_periodo = float(row[0] or 0)
    debitos_periodo = float(row[1] or 0)

    saldo_ini_map = _saldo_por_cuenta_map(
        cursor, filters.fecha_inicio_str, antes_de=True, cod_sucursal=filters.cod_sucursal
    )
    saldo_fin_map = _saldo_por_cuenta_map(
        cursor, filters.fecha_fin_str, antes_de=False, cod_sucursal=filters.cod_sucursal
    )

    sql_por_cuenta = f"""
        SELECT
            lb.CodCuenta,
            COALESCE(SUM(COALESCE(lb.Credito, 0)), 0),
            COALESCE(SUM(COALESCE(lb.Debito, 0)), 0)
        FROM librobanco lb
        WHERE {where_period}
        GROUP BY lb.CodCuenta
    """
    cursor.execute(sql_por_cuenta, params_period)
    flujos_map: dict[int, tuple[float, float]] = {}
    for cod, cred, deb in cursor.fetchall():
        cid = to_int_or_none(cod)
        if cid is not None:
            flujos_map[cid] = (float(cred or 0), float(deb or 0))

    cod_cuentas = sorted(set(saldo_ini_map) | set(saldo_fin_map) | set(flujos_map))
    cuenta_meta: dict[int, tuple[str | None, str | None]] = {}
    if cod_cuentas:
        placeholders = ",".join(["%s"] * len(cod_cuentas))
        sql_meta = f"""
            SELECT cb.CodCuenta, cb.NroCuenta, b.Nombre
            FROM cuenta_banco cb
            LEFT JOIN banco b ON b.CodBanco = cb.CodBanco
            WHERE cb.CodCuenta IN ({placeholders})
        """
        try:
            cursor.execute(sql_meta, cod_cuentas)
            for cod, nro, nombre in cursor.fetchall():
                cid = to_int_or_none(cod)
                if cid is not None:
                    cuenta_meta[cid] = (nro, nombre)
        except Exception:
            pass

    por_cuenta_banco: list[dict[str, Any]] = []
    for cod in cod_cuentas:
        cred, deb = flujos_map.get(cod, (0.0, 0.0))
        nro, banco_nombre = cuenta_meta.get(cod, (None, None))
        por_cuenta_banco.append(
            {
                "cod_cuenta": cod,
                "nro_cuenta": str_or_default(nro, "-") if nro else None,
                "banco_nombre": str_or_default(banco_nombre, "-") if banco_nombre else None,
                "saldo_inicial": round_money(saldo_ini_map.get(cod, 0.0)),
                "saldo_final": round_money(saldo_fin_map.get(cod, 0.0)),
                "creditos": round_money(cred),
                "debitos": round_money(debit),
            }
        )
    por_cuenta_banco.sort(key=lambda x: abs(x["saldo_final"]), reverse=True)

    pendiente_conciliar = _count_pendiente_conciliar(cursor, filters)

    notas = [
        "Libro banco (librobanco): independiente de saldos de caja; no sumar con tesorería caja.",
        "Saldos: último librobanco.Saldo por CodCuenta (fecha COALESCE(FechaMov, Fecha)).",
        "Créditos/débitos del período excluyen movimientos Anulado='Si'.",
        f"Movimientos pendientes de conciliar al {filters.fecha_fin_str}: {pendiente_conciliar}.",
    ]

    return {
        "saldo_banco_inicial": round_money(saldo_inicial),
        "saldo_banco_final": round_money(saldo_final),
        "creditos_periodo": round_money(creditos_periodo),
        "debitos_periodo": round_money(debitos_periodo),
        "por_cuenta_banco": por_cuenta_banco,
        "pendiente_conciliar": pendiente_conciliar,
        "disponible": True,
        "meta": build_meta(filters, notas_semanticas=notas),
    }
