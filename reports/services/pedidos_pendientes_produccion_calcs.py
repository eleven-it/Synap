# -*- coding: utf-8 -*-
"""Cálculos puros para pedidos-pendientes-produccion (testeables sin MySQL)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple


def compute_disponible_backorder(pendiente_qty: float, stock_terminado: float) -> Tuple[float, float]:
    """Disponible = stock terminado − pendiente; backorder = max(pendiente − terminado, 0)."""
    pend = float(pendiente_qty or 0)
    term = float(stock_terminado or 0)
    disponible = round(term - pend, 4)
    backorder = round(max(pend - term, 0.0), 4)
    return disponible, backorder


def compute_mpr_pack_fields(
    pendiente_qty: float,
    stock_terminado: float,
    stock_reserva: float,
) -> Dict[str, float]:
    """
    Misma fórmula que MPR pack (listar_demanda_pack_desde_pedidos) pero P_ped = pendiente del informe
    y S = solo stock en depósitos terminado con suma_stock (columna stock_terminado del informe).
    """
    p_ped = float(pendiente_qty or 0)
    st = float(stock_terminado or 0)
    reserva = float(stock_reserva or 0) if stock_reserva is not None else 0.0
    a_fab = max(0.0, p_ped + reserva - st)
    brecha = round(p_ped - a_fab, 4)
    return {
        "mpr_demanda_pedido": round(p_ped, 4),
        "mpr_stock_terminado": round(st, 4),
        "mpr_stock_reserva": round(reserva, 4),
        "mpr_cantidad_a_fabricar": round(a_fab, 4),
        "mpr_brecha_vs_pendiente": brecha,
    }


def enrich_articulo_row(row: Dict[str, Any], stock_reserva: float = 0.0) -> None:
    pend = float(row.get("pendiente_qty") or 0)
    term = float(row.get("stock_terminado") or 0)
    disp, bo = compute_disponible_backorder(pend, term)
    row["disponible"] = disp
    row["backorder"] = bo
    mpr = compute_mpr_pack_fields(pend, term, stock_reserva)
    row.update(mpr)


def build_viajante_sql(
    vendedores_incluir: Sequence[int],
    vendedores_excluidos: Sequence[int],
) -> Tuple[str, List[int]]:
    """Filtro por comp_ped.CodViajante (vendedor del pedido)."""
    incluir = [int(v) for v in vendedores_incluir if v is not None]
    excluir = [int(v) for v in vendedores_excluidos if v is not None]
    if incluir:
        ph = ",".join(["%s"] * len(incluir))
        return f" AND cp.CodViajante IN ({ph})", list(incluir)
    if excluir:
        ph = ",".join(["%s"] * len(excluir))
        return f" AND cp.CodViajante NOT IN ({ph})", list(excluir)
    return "", []


def build_pv_sql(puntos_venta: Sequence[int]) -> Tuple[str, List[int]]:
    if not puntos_venta:
        return "", []
    ph = ",".join(["%s"] * len(puntos_venta))
    return f" AND cp.id_pv IN ({ph})", list(puntos_venta)


def build_busqueda_sql(busqueda: Optional[str]) -> Tuple[str, List[Any]]:
    q = (busqueda or "").strip()
    if not q:
        return "", []
    like = f"%{q}%"
    clause = (
        " AND (CAST(sp.IDArt AS CHAR) LIKE %s OR COALESCE(a.id_manual,'') LIKE %s "
        "OR COALESCE(a.NombreArticulo,'') LIKE %s OR COALESCE(m.NombreMarca,'') LIKE %s)"
    )
    return clause, [like, like, like, like]


def deposito_suma_stock(dep: Dict[str, Any]) -> bool:
    return str(dep.get("suma_stock") or "Si").strip().upper() in ("SI", "S", "1", "YES")


def deposito_activo(dep: Dict[str, Any]) -> bool:
    return str(dep.get("anulado") or dep.get("Anulado") or "No").strip().lower() != "si"


def classify_depositos_stock_columns(
    depositos: Sequence[Dict[str, Any]],
) -> Tuple[List[int], List[int]]:
    """Solo depósitos activos con suma_stock=Si; terminado vs producción por tipo_mpr."""
    terminado: List[int] = []
    produccion: List[int] = []

    def _norm_tipo(val: Any) -> str:
        return (str(val or "").strip().lower().replace("ó", "o").replace("é", "e"))

    for dep in depositos:
        if not deposito_activo(dep) or not deposito_suma_stock(dep):
            continue
        cod = dep.get("CodDeposito") or dep.get("id_deposito") or dep.get("cod_deposito")
        try:
            cod_int = int(cod)
        except (TypeError, ValueError):
            continue
        tipo = _norm_tipo(dep.get("tipo_mpr"))
        if tipo in ("terminado",):
            terminado.append(cod_int)
        elif tipo in ("produccion", "producción"):
            produccion.append(cod_int)
    return terminado, produccion


def aggregate_totals(articulos: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    def _sum(key: str) -> float:
        return round(sum(float(a.get(key) or 0) for a in articulos), 4)

    articulos_con_backorder = sum(1 for a in articulos if float(a.get("backorder") or 0) > 0)

    return {
        "row_count": len(articulos),
        "total_articulos": len(articulos),
        "articulos_con_backorder": articulos_con_backorder,
        "total_pendiente_qty": _sum("pendiente_qty"),
        "total_stock_terminado": _sum("stock_terminado"),
        "total_stock_produccion": _sum("stock_produccion"),
        "total_disponible": _sum("disponible"),
        "total_backorder": _sum("backorder"),
        "total_importe_pendiente": round(_sum("importe_pendiente"), 2),
        "total_mpr_demanda_pedido": _sum("mpr_demanda_pedido"),
        "total_mpr_cantidad_a_fabricar": _sum("mpr_cantidad_a_fabricar"),
    }


def sql_unidad_base_join() -> str:
    """JOIN unidmed vía articulo.id_unimed (paridad ventas marcas / licenciatarios)."""
    return "LEFT JOIN unidmed um ON um.id_unimed = a.id_unimed"


def sql_unidad_base_select() -> str:
    return "COALESCE(um.nombre_unimed, '') AS unidad_base"


def sql_unidad_base_group_by_suffix() -> str:
    return ", COALESCE(um.nombre_unimed, '')"
