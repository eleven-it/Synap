"""
Detección de cambios para re-sincronización incremental AdministraNET ↔ Tiendanube.

- Productos: ``articulo.fecha_mod`` vs snapshot en ``ProductMapping.adminet_fecha_mod``;
  stock por comparación de unidades (``stock_deposito`` no tiene fecha);
  precios por comparación de valores publicables en TN.
- Clientes Adminet→TN: sin ``fecha_mod`` en ``cliente``; comparación de campos relevantes.
- Clientes TN→Adminet: ``updated_at`` de TN vs ``CustomerMapping.tiendanube_updated_at``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.utils.administranet_types import str_or_default, to_int_or_none

from ..models import CustomerMapping, ProductMapping
from .product_pricing import precios_tiendanube_desde_articulo
from .product_stock import stock_unidades_articulo_deposito


def to_aware_dt(value: Any) -> Optional[datetime]:
    """Normaliza fecha/hora a datetime con zona horaria."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        dt = parse_datetime(str(value))
        if dt is None:
            return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def adminet_fecha_modificado(
    fecha_mod: Any,
    referencia: Any,
) -> bool:
    """
    True si ``fecha_mod`` del origen es posterior al snapshot guardado en el mapeo.
    """
    mod = to_aware_dt(fecha_mod)
    if mod is None:
        return False
    ref = to_aware_dt(referencia)
    if ref is None:
        return True
    return mod > ref


def _decimal_distinto(a: Any, b: Any, places: int = 2) -> bool:
    if a is None and b is None:
        return False
    if a is None or b is None:
        return True
    return round(float(a), places) != round(float(b), places)


def _stock_actual_adminet(
    adminet_product: Dict[str, Any],
    deposito_id: Optional[int],
) -> Optional[int]:
    if deposito_id and 'stock_deposito' in adminet_product:
        return int(stock_unidades_articulo_deposito(adminet_product, deposito_id))
    if adminet_product.get('saldo_articulo') is not None:
        return int(adminet_product.get('saldo_articulo', 0))
    return None


def _precios_distintos(
    mapping: ProductMapping,
    adminet_product: Dict[str, Any],
    config: Any = None,
) -> bool:
    if not mapping.sync_price:
        return False
    precios = precios_tiendanube_desde_articulo(adminet_product, config=config)
    if _decimal_distinto(mapping.tiendanube_price, precios['price']):
        return True
    if _decimal_distinto(mapping.tiendanube_cost, precios['cost']):
        return True
    return False


def producto_requiere_sync_adminet_a_tn(
    mapping: ProductMapping,
    adminet_product: Dict[str, Any],
    deposito_id: Optional[int],
    *,
    force: bool = False,
    config: Any = None,
) -> Tuple[bool, str]:
    """
    Indica si un producto ya vinculado debe volver a publicarse en Tiendanube.
    """
    if force:
        return True, 'forzado'
    if not mapping.sync_enabled:
        return False, 'sync deshabilitado'
    if mapping.sync_status != ProductMapping.SyncStatus.SYNCED:
        return True, f'estado {mapping.sync_status}'
    if not mapping.tiendanube_id:
        return True, 'sin tiendanube_id'

    motivos = []
    if adminet_fecha_modificado(
        adminet_product.get('fecha_mod'),
        mapping.adminet_fecha_mod,
    ):
        motivos.append('fecha_mod articulo')

    if mapping.sync_stock:
        nuevo_stock = _stock_actual_adminet(adminet_product, deposito_id)
        if nuevo_stock is not None and (
            mapping.adminet_stock is None
            or int(mapping.adminet_stock) != int(nuevo_stock)
        ):
            motivos.append('stock deposito')

    if _precios_distintos(mapping, adminet_product, config=config):
        motivos.append('precio/costo')

    if motivos:
        return True, ', '.join(motivos)
    return False, 'sin cambios'


def _email_adminet_normalizado(customer: Dict[str, Any]) -> str:
    email = str_or_default(customer.get('Email'), '').strip()
    if email and email != '-':
        return email
    codigo = customer.get('Codigo')
    return f'adminet_{codigo or 0}@noemail.local'


def _texto_normalizado(value: Any) -> str:
    return str_or_default(value, '').strip()


CUSTOMER_ADMINET_SYNC_FIELDS = (
    ('adminet_nombre', 'nombre_cliente'),
    ('adminet_cuit', 'CUIT'),
    ('adminet_telefono', 'telefono'),
    ('adminet_calle', 'Calle'),
    ('adminet_nro_calle', 'NroCalle'),
    ('adminet_cliente_ecommerce', 'cliente_ecommerce'),
)


def cliente_adminet_cambio(
    mapping: CustomerMapping,
    customer: Dict[str, Any],
) -> bool:
    """True si los datos del cliente en AdministraNET difieren del snapshot del mapeo."""
    email_mapeo = _texto_normalizado(mapping.adminet_email)
    email_origen = _email_adminet_normalizado(customer)
    if email_mapeo != email_origen:
        return True

    for m_attr, c_key in CUSTOMER_ADMINET_SYNC_FIELDS:
        m_val = _texto_normalizado(getattr(mapping, m_attr, None))
        c_val = _texto_normalizado(customer.get(c_key))
        if m_val != c_val:
            return True

    id_tn = to_int_or_none(customer.get('id_tiendanube'))
    map_tn = to_int_or_none(mapping.tiendanube_id)
    if id_tn and map_tn and id_tn != map_tn:
        return True
    if id_tn and not map_tn:
        return True
    return False


def cliente_tn_modificado(
    tn_customer: Dict[str, Any],
    mapping: CustomerMapping,
) -> bool:
    """True si el cliente en Tiendanube fue modificado después del último sync."""
    if mapping.sync_status != CustomerMapping.SyncStatus.SYNCED:
        return True
    updated = to_aware_dt(tn_customer.get('updated_at'))
    ref = to_aware_dt(mapping.tiendanube_updated_at)
    if updated is None:
        return ref is None
    if ref is None:
        return True
    return updated > ref


def actualizar_snapshot_cliente_adminet(
    mapping: CustomerMapping,
    customer: Dict[str, Any],
) -> None:
    """Persiste en el mapeo los campos de AdministraNET usados para detectar cambios."""
    mapping.adminet_nombre = _texto_normalizado(customer.get('nombre_cliente'))
    mapping.adminet_email = _email_adminet_normalizado(customer)
    mapping.adminet_cuit = _texto_normalizado(customer.get('CUIT'))
    mapping.adminet_telefono = _texto_normalizado(customer.get('telefono'))
    mapping.adminet_calle = _texto_normalizado(customer.get('Calle'))
    mapping.adminet_nro_calle = _texto_normalizado(customer.get('NroCalle'))
    mapping.adminet_cliente_ecommerce = _texto_normalizado(customer.get('cliente_ecommerce'))
    mapping.adminet_cliente_ecommerce = mapping.adminet_cliente_ecommerce or 'Si'


def actualizar_snapshot_cliente_tiendanube(
    mapping: CustomerMapping,
    tn_customer: Dict[str, Any],
) -> None:
    """Persiste ``updated_at`` y datos TN relevantes tras sync exitoso."""
    mapping.tiendanube_updated_at = to_aware_dt(tn_customer.get('updated_at'))
