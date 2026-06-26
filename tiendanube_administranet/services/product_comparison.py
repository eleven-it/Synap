"""Filas comparativas AdministraNET ↔ Tiendanube para detalle de producto."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .product_pricing import precios_finales_desde_product_mapping, precios_finales_tiendanube_mapping
from .tiendanube_product_fields import _texto_localizado_tiendanube


def _fmt_money(value: Any) -> str:
    try:
        return f'${float(value):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return '—'


def _fmt_int(value: Any) -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return '—'


def _fmt_bool_si_no(value: Any) -> str:
    if value in (True, 'Si', 'Sí', 'si', 'sí', 'Yes', 'yes', 1, '1'):
        return 'Sí'
    if value in (False, 'No', 'no', 'No', 0, '0', None, ''):
        return 'No'
    return str(value or '—')


def _norm_handle(value: Any) -> str:
    if not value:
        return ''
    if isinstance(value, dict):
        return _texto_localizado_tiendanube(value)
    text = str(value).strip()
    if text.startswith('{') and "'es'" in text:
        try:
            import ast

            parsed = ast.literal_eval(text)
            if isinstance(parsed, dict):
                return _texto_localizado_tiendanube(parsed)
        except (SyntaxError, ValueError):
            pass
    return text


def _match_estado(
    tn_value: Any,
    adminet_value: Any,
    *,
    comparable: bool = True,
    numeric: bool = False,
    tolerance: float = 0.02,
) -> str:
    """``ok`` | ``diff`` | ``info`` (sin comparación)."""
    if not comparable:
        return 'info'
    if tn_value in (None, '', '—') and adminet_value in (None, '', '—'):
        return 'info'
    if numeric:
        try:
            tn_num = float(tn_value)
            an_num = float(adminet_value)
            if abs(tn_num - an_num) <= tolerance:
                return 'ok'
            return 'diff'
        except (TypeError, ValueError):
            return 'info'
    tn_text = str(tn_value or '').strip().lower()
    an_text = str(adminet_value or '').strip().lower()
    if tn_text == an_text:
        return 'ok'
    return 'diff'


def filas_comparacion_producto(
    mapping: Any,
    config: Any = None,
) -> List[Dict[str, Any]]:
    """Construye filas alineadas para tabla comparativa en detalle de producto."""
    precios_an = precios_finales_desde_product_mapping(mapping, config=config)
    precios_tn = precios_finales_tiendanube_mapping(mapping)

    tn_nombre = mapping.tiendanube_name or '—'
    an_nombre = mapping.adminet_nombre or '—'
    tn_sku = mapping.tiendanube_sku or '—'
    an_barra = mapping.adminet_codigo_barra or '—'
    tn_stock = mapping.tiendanube_stock
    an_stock = mapping.adminet_stock
    tn_pub = _fmt_bool_si_no(mapping.tiendanube_published)
    an_ecom = _fmt_bool_si_no(mapping.adminet_ecommerce)

    filas: List[Dict[str, Any]] = [
        {
            'grupo': 'identificacion',
            'label': 'ID',
            'tn': str(mapping.tiendanube_id or '—'),
            'adminet': str(mapping.adminet_id or '—'),
            'estado': 'info',
            'comparable': False,
        },
        {
            'grupo': 'catalogo',
            'label': 'Nombre',
            'tn': tn_nombre,
            'adminet': an_nombre,
            'estado': _match_estado(tn_nombre, an_nombre, comparable=True),
            'comparable': True,
        },
        {
            'grupo': 'catalogo',
            'label': 'SKU / Código de barra',
            'tn': tn_sku,
            'adminet': an_barra,
            'estado': _match_estado(tn_sku, an_barra, comparable=True),
            'comparable': True,
        },
        {
            'grupo': 'catalogo',
            'label': 'Código de artículo',
            'tn': '—',
            'adminet': mapping.adminet_codigo_articulo or '—',
            'estado': 'info',
            'comparable': False,
        },
        {
            'grupo': 'catalogo',
            'label': 'Handle (URL Tiendanube)',
            'tn': _norm_handle(mapping.tiendanube_handle) or '—',
            'adminet': '—',
            'estado': 'info',
            'comparable': False,
        },
        {
            'grupo': 'precios',
            'label': 'Precio de venta (final)',
            'tn': _fmt_money(precios_tn['precio_venta']),
            'adminet': _fmt_money(precios_an['precio_venta']),
            'tn_raw': precios_tn['precio_venta'],
            'adminet_raw': precios_an['precio_venta'],
            'adminet_hint': precios_an['lista_label'],
            'estado': _match_estado(
                precios_tn['precio_venta'],
                precios_an['precio_venta'],
                numeric=True,
            ),
            'comparable': True,
        },
        {
            'grupo': 'precios',
            'label': 'Costo (final)',
            'tn': _fmt_money(precios_tn['costo']),
            'adminet': _fmt_money(precios_an['costo']),
            'tn_raw': precios_tn['costo'],
            'adminet_raw': precios_an['costo'],
            'estado': _match_estado(
                precios_tn['costo'],
                precios_an['costo'],
                numeric=True,
            ),
            'comparable': True,
        },
        {
            'grupo': 'precios',
            'label': 'Stock',
            'tn': _fmt_int(tn_stock),
            'adminet': _fmt_int(an_stock),
            'estado': _match_estado(tn_stock, an_stock, numeric=True, tolerance=0),
            'comparable': True,
        },
        {
            'grupo': 'estado',
            'label': 'Publicado / E-commerce',
            'tn': tn_pub,
            'adminet': an_ecom,
            'estado': _match_estado(tn_pub, an_ecom, comparable=True),
            'comparable': True,
        },
        {
            'grupo': 'estado',
            'label': 'Destacado (Tiendanube)',
            'tn': _fmt_bool_si_no(mapping.tiendanube_featured),
            'adminet': _fmt_bool_si_no(mapping.adminet_promo_destacado),
            'estado': _match_estado(
                mapping.tiendanube_featured,
                mapping.adminet_promo_destacado,
                comparable=True,
            ),
            'comparable': True,
        },
        {
            'grupo': 'estado',
            'label': 'Tipo de producto',
            'tn': mapping.tiendanube_product_type or '—',
            'adminet': '—',
            'estado': 'info',
            'comparable': False,
        },
        {
            'grupo': 'estado',
            'label': 'Peso',
            'tn': f'{mapping.tiendanube_weight or 0} kg',
            'adminet': '—',
            'estado': 'info',
            'comparable': False,
        },
    ]
    return filas


def resumen_comparacion_producto(filas: List[Dict[str, Any]]) -> Dict[str, int]:
    comparables = [f for f in filas if f.get('comparable')]
    ok = sum(1 for f in comparables if f.get('estado') == 'ok')
    diff = sum(1 for f in comparables if f.get('estado') == 'diff')
    return {'coinciden': ok, 'diferencias': diff, 'total_comparables': len(comparables)}
