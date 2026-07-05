"""
Restricciones de catálogo por punto de venta (Fase P3, config en BD Postgres synap).

Reemplaza el baneo legacy hardcodeado (`lista_baneo_productos_fiscal/no_fiscal` en sesión,
aplicado según `punto_venta.cont`) por configuración genérica en `EcomCatalogoRestriccionPV`.
Se resuelven las exclusiones del PV activo y se inyectan a los filtros del catálogo
(`excluir_articulos`/`excluir_rubros`/`excluir_subrubros`), que `_construir_where_catalogo`
traduce a cláusulas `NOT IN`.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ecom.models import EcomCatalogoRestriccionPV

_TIPO_A_CLAVE = {
    EcomCatalogoRestriccionPV.TIPO_ARTICULO: "excluir_articulos",
    EcomCatalogoRestriccionPV.TIPO_RUBRO: "excluir_rubros",
    EcomCatalogoRestriccionPV.TIPO_SUBRUBRO: "excluir_subrubros",
    # 'categoria' no se filtra en el catálogo P0 (no se trae la categoría); reservado.
}


def restricciones_para_pv(base_empresa: str, id_punto_venta: Optional[int]) -> Dict[str, list]:
    """
    Devuelve las exclusiones activas del PV como dict listo para inyectar en filtros:
    {"excluir_articulos": [...], "excluir_rubros": [...], "excluir_subrubros": [...]}.
    Si no hay PV o no hay restricciones, devuelve {} (sin exclusiones).
    """
    if not base_empresa or id_punto_venta is None:
        return {}

    qs = EcomCatalogoRestriccionPV.objects.filter(
        base_empresa=base_empresa, id_punto_venta=id_punto_venta, activo=True
    ).values_list("tipo", "valor_id")

    out: Dict[str, list] = {}
    for tipo, valor_id in qs:
        clave = _TIPO_A_CLAVE.get(tipo)
        if clave is None:
            continue
        out.setdefault(clave, []).append(valor_id)
    return out


def aplicar_restricciones_a_filtros(
    filtros: Optional[Dict[str, Any]], base_empresa: str, id_punto_venta: Optional[int]
) -> Dict[str, Any]:
    """Combina las restricciones del PV con los filtros del catálogo (no muta el original)."""
    filtros = dict(filtros or {})
    restricciones = restricciones_para_pv(base_empresa, id_punto_venta)
    for clave, ids in restricciones.items():
        existentes = list(filtros.get(clave) or [])
        filtros[clave] = existentes + ids
    return filtros
