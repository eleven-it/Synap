"""
Opciones de presentación / embalaje (Unidad, Display, Bulto, Pallet) para catálogo y carrito.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.mysql_pool import get_mysql_pool
from core.services.administranet_stock import get_config_unidad_bulto_display
from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none


def _si(val: Any) -> bool:
    return str_or_default(val, "No").strip().lower() in ("si", "sí", "1", "true")


def _fetch_utiliza_embalaje(base_empresa: str) -> bool:
    pool = get_mysql_pool()
    try:
        with pool.get_connection(base_empresa) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COALESCE(utiliza_embalaje, 'No') FROM configuracion LIMIT 1"
            )
            row = cur.fetchone()
            return _si(row[0] if row else "No")
    except Exception:
        return False


def _fetch_articulo_prov(base_empresa: str, id_articulo: int) -> Dict[str, Any]:
    """Embalaje del proveedor del artículo (columnas legacy pueden variar por base)."""
    sql = """
        SELECT
            ap.cantidad_uni,
            ap.cantidad_unidad_display,
            ap.cantidad_display_bulto,
            ap.cantidad_bulto_pallet
        FROM articulo_prov ap
        INNER JOIN articulo a ON a.CodigoProveedor = ap.codProveedor AND a.IDArt = %s
        WHERE ap.IDArt = %s
        LIMIT 1
    """
    pool = get_mysql_pool()
    try:
        with pool.get_connection(base_empresa) as conn:
            cur = conn.cursor()
            cur.execute(sql, [id_articulo, id_articulo])
            row = cur.fetchone()
            if not row:
                return {}
            cols = [d[0] for d in cur.description] if cur.description else []
            return dict(zip(cols, row))
    except Exception:
        return {}


def multiplicador_presentacion(tipo_unidad: str, prov: Dict[str, Any]) -> Decimal:
    """Cantidad en unidad base por una unidad de la presentación elegida."""
    t = (tipo_unidad or "Unidad").strip().lower()
    cud = to_decimal_or_none(prov.get("cantidad_unidad_display")) or Decimal("1")
    cdb = to_decimal_or_none(prov.get("cantidad_display_bulto")) or Decimal("1")
    cbp = to_decimal_or_none(prov.get("cantidad_bulto_pallet")) or Decimal("1")
    if t == "display":
        return max(cud, Decimal("1"))
    if t == "bulto":
        return max(cud * cdb, Decimal("1"))
    if t == "pallet":
        return max(cud * cdb * cbp, Decimal("1"))
    return Decimal("1")


def opciones_presentacion_articulo(
    base_empresa: str,
    id_articulo: int,
) -> Dict[str, Any]:
    """Devuelve opciones de embalaje para UI y cálculo de cantidad base."""
    cfg = get_config_unidad_bulto_display(base_empresa)
    embalaje = _fetch_utiliza_embalaje(base_empresa)
    prov = _fetch_articulo_prov(base_empresa, id_articulo)
    cud = to_decimal_or_none(prov.get("cantidad_unidad_display")) or Decimal("0")
    cdb = to_decimal_or_none(prov.get("cantidad_display_bulto")) or Decimal("0")
    cbp = to_decimal_or_none(prov.get("cantidad_bulto_pallet")) or Decimal("0")

    opciones: List[Dict[str, Any]] = [
        {"tipo": "Unidad", "etiqueta": "Unidad", "multiplicador": 1},
    ]
    if _si(cfg.get("utiliza_display")) and cud > 0:
        opciones.append(
            {
                "tipo": "Display",
                "etiqueta": f"Display ({int(cud)} u.)",
                "multiplicador": float(cud),
            }
        )
    if _si(cfg.get("utiliza_bulto_cerrado")) and cud > 0 and cdb > 0:
        mult_b = float(cud * cdb)
        opciones.append(
            {
                "tipo": "Bulto",
                "etiqueta": f"Bulto ({int(mult_b)} u.)",
                "multiplicador": mult_b,
            }
        )
    if embalaje and cud > 0 and cdb > 0 and cbp > 0:
        mult_p = float(cud * cdb * cbp)
        opciones.append(
            {
                "tipo": "Pallet",
                "etiqueta": f"Pallet ({int(mult_p)} u.)",
                "multiplicador": mult_p,
            }
        )

    defecto = str_or_default(cfg.get("tipo_unidad_defecto"), "Unidad")
    tipos = {o["tipo"] for o in opciones}
    if defecto not in tipos:
        defecto = "Unidad"

    return {
        "mostrar_embalaje": len(opciones) > 1,
        "tipo_unidad_defecto": defecto,
        "opciones": opciones,
    }


def cantidad_base_desde_ui(
    cantidad_ui: Any,
    tipo_unidad: str,
    prov: Optional[Dict[str, Any]] = None,
    *,
    multiplicador: Optional[Any] = None,
) -> Decimal:
    """Convierte cantidad ingresada en UI a unidades base (stockp.Salida)."""
    q = to_decimal_or_none(cantidad_ui) or Decimal("0")
    if multiplicador is not None:
        m = to_decimal_or_none(multiplicador) or Decimal("1")
    elif prov:
        m = multiplicador_presentacion(tipo_unidad, prov)
    else:
        m = Decimal("1")
    return q * m
