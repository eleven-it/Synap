"""Conciliación de ventas por marca con el KPI de cabecera (paridad VB6)."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .base import DashboardFilters, comparison_filters, round_money
from .comercial_v45 import _scope as _sales_scope
from .resumen_v45 import _CREDIT_TYPES, _DEBIT_TYPES, _period, _sales_amount, _table_exists


_NC = "'NCA','NCB','NCC','NCE','NCM'"
_ND = "'NDA','NDB','NDC','NDE','NDM'"
_FA = "'FA','FB','FC','FE','FM'"
_STOCK_TYPES = "'Venta','Venta TPV','Devol - Cliente','ND Anul NC'"


def _money(value) -> Decimal:
    return Decimal(str(value or 0))


def _has_id_marca(cursor) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema=DATABASE() AND table_name='cuentacliente' "
        "AND column_name='id_marca'"
    )
    row = cursor.fetchone()
    return bool(row and row[0])


def _stock_exists(alias: str) -> str:
    # Repite el predicado del detalle VB6 para distinguir notas sin renglones.
    return (
        "EXISTS (SELECT 1 FROM stock sx WHERE sx.CodigoMovimiento=" + alias + ".CodigoMovimiento "
        "AND sx.CodigoMovimiento<>0 AND sx.Anulado='No' "
        "AND COALESCE(sx.visualiza_ensamble,'No')<>'Si' "
        f"AND sx.TipoComp IN ({_STOCK_TYPES}) "
        "AND sx.Fecha >= %s AND sx.Fecha < %s)"
    )


def _period_rows(cursor, filters: DashboardFilters, gross: bool) -> dict:
    period = _period(filters)
    scope, scope_params = _sales_scope("cc", filters)
    amount = (
        "COALESCE(st.PrecioNetoxR,0)+COALESCE(st.PrecioIVAxR,0)+"
        "COALESCE(st.ImpIB,0)+COALESCE(st.impuesto_interno_subtotal,0)"
        if gross else "COALESCE(st.PrecioNetoxR,0)"
    )
    cursor.execute(
        "SELECT COALESCE(a.CodigoMarca,0),COALESCE(MAX(m.NombreMarca),''),"
        f"COALESCE(SUM(CASE WHEN st.TipoComp='Devol - Cliente' THEN -({amount}) "
        f"ELSE ({amount}) END),0),COALESCE(SUM(ABS(COALESCE(st.Cantidad,0))),0) "
        "FROM stock st JOIN cuentacliente cc ON cc.CodigoMovimiento=st.CodigoMovimiento "
        "JOIN articulo a ON a.IDArt=st.IDArt LEFT JOIN marca m ON m.CodMarca=a.CodigoMarca "
        "WHERE st.Fecha >= %s AND st.Fecha < %s AND st.CodigoMovimiento<>0 "
        "AND st.Anulado='No' AND COALESCE(st.visualiza_ensamble,'No')<>'Si' "
        f"AND st.TipoComp IN ({_STOCK_TYPES}) "
        "AND cc.CodigoMovimiento<>0 AND cc.Anulado='No' "
        f"AND cc.TipoComprobante IN ({_CREDIT_TYPES},{_DEBIT_TYPES}){scope} "
        "GROUP BY a.CodigoMarca",
        period + scope_params,
    )
    by_brand = defaultdict(lambda: {"nombre": "", "neto": Decimal(0), "nc": Decimal(0),
                                  "nd": Decimal(0), "cantidad": Decimal(0)})
    for brand, name, net, quantity in cursor.fetchall() or []:
        item = by_brand[int(brand or 0)]
        item["nombre"] = name or item["nombre"]
        item["neto"] += _money(net)
        item["cantidad"] += _money(quantity)

    # NC/ND de cabecera asignadas a marca y sin renglones de stock.
    no_stock = _stock_exists("cc")
    credit = "COALESCE(cc.ImporteCobro,0)" if gross else "COALESCE(cc.SubtotalDesc,0)"
    debit = "COALESCE(cc.ImporteVenta,0)" if gross else "COALESCE(cc.SubtotalDesc,0)"
    cursor.execute(
        "SELECT COALESCE(cc.id_marca,0),COALESCE(MAX(m.NombreMarca),''),"
        f"COALESCE(SUM(CASE WHEN cc.TipoComprobante IN ({_NC}) THEN {credit} ELSE 0 END),0),"
        f"COALESCE(SUM(CASE WHEN cc.TipoComprobante IN ({_ND}) THEN {debit} ELSE 0 END),0),"
        "COUNT(*) FROM cuentacliente cc LEFT JOIN marca m ON m.CodMarca=cc.id_marca "
        "WHERE cc.Fecha >= %s AND cc.Fecha < %s AND cc.CodigoMovimiento<>0 "
        f"AND cc.Anulado='No' AND cc.TipoComprobante IN ({_NC},{_ND}){scope} "
        f"AND NOT {no_stock} GROUP BY cc.id_marca",
        period + scope_params + period,
    )
    unassigned_nc = Decimal(0)
    unassigned_nd = Decimal(0)
    for brand, name, nc, nd, _count in cursor.fetchall() or []:
        brand = int(brand or 0)
        if brand:
            item = by_brand[brand]
            item["nombre"] = name or item["nombre"]
            item["nc"] += _money(nc)
            item["nd"] += _money(nd)
        else:
            unassigned_nc += _money(nc)
            unassigned_nd += _money(nd)

    cursor.execute(
        f"SELECT COALESCE(SUM({_sales_amount(gross)}),0),"
        f"COALESCE(SUM(CASE WHEN cc.TipoComprobante IN ({_FA}) "
        f"AND NOT {no_stock} THEN {debit} ELSE 0 END),0) "
        "FROM cuentacliente cc WHERE cc.Fecha >= %s AND cc.Fecha < %s "
        "AND cc.CodigoMovimiento<>0 AND cc.Anulado='No' "
        f"AND cc.TipoComprobante IN ({_CREDIT_TYPES},{_DEBIT_TYPES}){scope}",
        period + period + scope_params,
    )
    kpi, invoices_without_lines = cursor.fetchone() or (0, 0)
    kpi = _money(kpi)
    invoices_without_lines = _money(invoices_without_lines)
    brands = []
    for brand, item in by_brand.items():
        amount_brand = item["neto"] - item["nc"] + item["nd"]
        if not (item["neto"] or item["nc"] or item["nd"]):
            continue
        brands.append({"etiqueta": item["nombre"] or ("Sin marca" if not brand else f"Marca {brand}"),
                       "id_marca": brand, "neto": round_money(item["neto"]),
                       "nc": round_money(item["nc"]), "nd": round_money(item["nd"]),
                       "importe": round_money(amount_brand),
                       "cantidad": float(item["cantidad"]), "tipo_fila": "marca"})
    brands.sort(key=lambda row: (-row["importe"], row["etiqueta"], row["id_marca"]))
    subtotal = sum((_money(row["importe"]) for row in brands), Decimal(0))
    # El cliente suma los importes visibles a dos decimales; cerrar también en centavos.
    discounts = (
        _money(round_money(kpi)) - subtotal
        + _money(round_money(unassigned_nc)) - _money(round_money(unassigned_nd))
        - _money(round_money(invoices_without_lines))
    )
    adjustments = [
        ("NC sin marca asignada", -unassigned_nc),
        ("ND sin marca asignada", unassigned_nd),
        ("Facturas sin artículos", invoices_without_lines),
        ("Descuentos / ajustes al pie", discounts),
    ]
    for label, value in adjustments:
        brands.append({"etiqueta": label, "importe": round_money(value),
                       "cantidad": 0, "tipo_fila": "conciliacion"})
    return {"filas": brands, "kpi": round_money(kpi), "subtotal_marcas": round_money(subtotal),
            "nc_sin_marca": round_money(unassigned_nc),
            "nd_sin_marca": round_money(unassigned_nd),
            "facturas_sin_articulos": round_money(invoices_without_lines),
            "descuentos_ajustes_pie": round_money(discounts),
            "cantidad_marcas": len(brands) - len(adjustments)}


def list_ventas_marca_conciliada(cursor, filters: DashboardFilters, *, gross=False,
                                  compare=False) -> dict:
    required = ("stock", "cuentacliente", "articulo", "marca")
    missing = [name for name in required if not _table_exists(cursor, name)]
    if missing:
        return {"disponible": False, "motivo": "tablas_faltantes",
                "tablas_faltantes": missing, "filas": []}
    if not _has_id_marca(cursor):
        return {"disponible": False, "motivo": "campo_id_marca_faltante", "filas": []}
    current = _period_rows(cursor, filters, gross)
    prior_filters = comparison_filters(filters) if compare else None
    previous = _period_rows(cursor, prior_filters, gross) if prior_filters else None
    def key(row):
        return (row["tipo_fila"], row.get("id_marca", row["etiqueta"]))

    previous_by_key = {key(row): row for row in previous["filas"]} if previous else {}
    rows = []
    current_keys = {key(row) for row in current["filas"]}
    for row in current["filas"] + ([r for r in previous["filas"] if key(r) not in current_keys]
                                    if previous else []):
        is_current = key(row) in current_keys
        actual = row["importe"] if is_current else 0
        prev = previous_by_key.get(key(row), {}).get("importe", 0)
        visible = row if is_current else {**row, "neto": 0, "nc": 0, "nd": 0,
                                          "cantidad": 0}
        rows.append({**visible, "importe": actual, "anterior": prev,
                     "variacion": round_money(actual - prev),
                     "variacion_pct": round((actual - prev) / abs(prev) * 100, 2) if prev else None})
    total = round_money(sum((_money(row["importe"]) for row in rows), Decimal(0)))
    if abs(total - current["kpi"]) > 0.01:
        raise ValueError("La conciliación por marca no coincide con el KPI de ventas netas")
    return {"indicador": "ventas", "dimension": "marca", "filas": rows,
            "total_importe": current["kpi"],
            "total_anterior": previous["kpi"] if previous else 0,
            "total_cantidad": sum(row.get("cantidad", 0) for row in current["filas"]
                                  if row.get("tipo_fila") == "marca"),
            "periodo": {"inicio": filters.fecha_inicio_str, "fin": filters.fecha_fin_str},
            "comparacion": ({"inicio": prior_filters.fecha_inicio_str,
                             "fin": prior_filters.fecha_fin_str} if prior_filters else None),
            "conciliacion": {key: value for key, value in current.items() if key != "filas"},
            "nota": "Marcas con NC/ND asignadas; notas sin marca, facturas sin artículos y ajustes al pie concilian con Ventas netas.",
            "truncado": False}
