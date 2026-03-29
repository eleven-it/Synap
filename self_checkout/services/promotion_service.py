"""
Servicio de promociones por artículo (réplica lógica administraNET VB6).
Obtener_Promo_Articulo: vigencia + lista; tipos: Monto fijo, Importe descuento, Cantidad, Cantidad - Unidad, Cantidad - Intervalo.
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any

from self_checkout.db import mysql_cursor

logger = logging.getLogger(__name__)

# id_lista: 0 = lista oficial, 1..5 = listas 1 a 5 (como VB6)
LISTA_COLUMNS = [
    'promocion_listaoficial', 'promocion_lista1', 'promocion_lista2',
    'promocion_lista3', 'promocion_lista4', 'promocion_lista5',
]


def promocion_desde_fila_articulo(
    row: Optional[Dict[str, Any]],
    id_lista: int,
    fecha: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Evalúa promoción vigente a partir de columnas de `articulo` ya cargadas (sin SELECT extra).
    `row` debe incluir las claves que devolvía el SELECT de obtener_promocion_articulo.
    """
    if fecha is None:
        fecha = date.today()
    out: Dict[str, Any] = {
        'aplica': False,
        'promocion': 'No',
        'promocion_tipo': '',
        'promocion_por': Decimal('0'),
        'promocion_cant': Decimal('0'),
    }
    id_lista = max(0, min(5, int(id_lista)))
    if not row or (row.get('promocion') or '').strip() != 'Si':
        return out
    col_lista = LISTA_COLUMNS[id_lista]
    if (row.get(col_lista) or '').strip() != 'Si':
        return out
    vigencia_desde = row.get('vigencia_desde')
    vigencia_hasta = row.get('vigencia_hasta')
    if vigencia_desde and hasattr(vigencia_desde, 'date'):
        vigencia_desde = vigencia_desde.date() if hasattr(vigencia_desde, 'date') else vigencia_desde
    if vigencia_hasta and hasattr(vigencia_hasta, 'date'):
        vigencia_hasta = vigencia_hasta.date() if hasattr(vigencia_hasta, 'date') else vigencia_hasta
    if vigencia_desde and fecha < vigencia_desde:
        return out
    if vigencia_hasta and fecha > vigencia_hasta:
        return out
    out['aplica'] = True
    out['promocion'] = 'Si'
    out['promocion_tipo'] = (row.get('promocion_tipo') or '').strip()
    try:
        out['promocion_por'] = Decimal(str(row.get('promocion_por') or 0))
    except Exception:
        out['promocion_por'] = Decimal('0')
    try:
        out['promocion_cant'] = Decimal(str(row.get('promocion_cant') or 0))
    except Exception:
        out['promocion_cant'] = Decimal('0')
    return out


def obtener_promocion_articulo(
    base_empresa: str,
    id_articulo: int,
    id_lista: int,
    fecha: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Comprueba si el artículo tiene promoción vigente para la lista dada.
    Returns: {
        'aplica': bool,
        'promocion': 'Si'|'No',
        'promocion_tipo': str or '',
        'promocion_por': Decimal|float,
        'promocion_cant': Decimal|float,
    }
    """
    sin_promo = {
        'aplica': False,
        'promocion': 'No',
        'promocion_tipo': '',
        'promocion_por': Decimal('0'),
        'promocion_cant': Decimal('0'),
    }
    with mysql_cursor(base_empresa, dict_cursor=True) as c:
        try:
            c.execute("""
                SELECT a.promocion,
                       COALESCE(a.promocion_vigencia_desde, '1900-01-01') AS vigencia_desde,
                       COALESCE(a.promocion_vigencia_hasta, '2099-12-31') AS vigencia_hasta,
                       COALESCE(a.promocion_tipo, '') AS promocion_tipo,
                       COALESCE(a.promocion_por, 0) AS promocion_por,
                       COALESCE(a.promocion_cant, 0) AS promocion_cant,
                       a.promocion_listaoficial, a.promocion_lista1, a.promocion_lista2,
                       a.promocion_lista3, a.promocion_lista4, a.promocion_lista5
                FROM articulo a
                WHERE a.IDArt = %s
                LIMIT 1
            """, [id_articulo])
            row = c.fetchone()
        except Exception as e:
            if 'Unknown column' in str(e):
                return sin_promo
            raise
    return promocion_desde_fila_articulo(row, id_lista, fecha)


def aplicar_precio_promocion(
    precio_base: Decimal,
    alicuota_iva: Decimal,
    cantidad: Decimal,
    promo: Dict[str, Any],
) -> tuple:
    """
    Dado precio base (neto), alícuota IVA, cantidad y resultado de obtener_promocion_articulo,
    devuelve (precio_unitario_final, porcentaje_descuento, promocion_por, promocion_tipo, promocion_cant).
    - Monto fijo: precio_unitario = promocion_por (neto); porcentaje_descuento = 0.
    - Importe descuento: precio_unitario = precio_base; porcentaje_descuento = promocion_por.
    - Cantidad: si cantidad >= promocion_cant entonces porcentaje_descuento = promocion_por, sino 0; precio = precio_base.
    """
    pct_desc = Decimal('0')
    precio_final = precio_base
    if not promo.get('aplica'):
        return precio_final, pct_desc, Decimal('0'), '', Decimal('0')
    tipo = promo.get('promocion_tipo') or ''
    por = promo.get('promocion_por') or Decimal('0')
    cant_min = promo.get('promocion_cant') or Decimal('0')
    if tipo == 'Monto fijo':
        # VB6: PrecioVentaxU_CALC = promocion_por / valor_alicuota (precio con IVA / (1+iva))
        try:
            alic = float(alicuota_iva or 0)
            valor_alicuota = 1 + (alic / 100.0)
            precio_final = Decimal(str(float(por) / valor_alicuota))
        except (TypeError, ZeroDivisionError):
            precio_final = por
        return precio_final, Decimal('0'), por, tipo, cant_min
    if tipo == 'Importe descuento':
        return precio_base, por, por, tipo, cant_min
    if tipo in ('Cantidad', 'Cantidad - Unidad', 'Cantidad - Intervalo'):
        if cantidad >= cant_min and cant_min is not None:
            pct_desc = por
        return precio_base, pct_desc, por, tipo, cant_min
    return precio_base, pct_desc, por, tipo, cant_min
