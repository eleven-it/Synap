"""Consulta y normalización de clientes Tienda Nube / AdministraNET para mapeos."""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from core.utils.administranet_types import str_or_default

if TYPE_CHECKING:
    from ..models import CustomerMapping


def tiendanube_customer_preview(customer: Dict[str, Any]) -> Dict[str, Any]:
    """Resumen para UI a partir de respuesta API Tienda Nube."""
    addr = (customer.get('addresses') or [{}])[0] if customer.get('addresses') else {}
    if not addr and isinstance(customer.get('default_address'), dict):
        addr = customer['default_address']
    name = str_or_default(customer.get('name'), '').strip()
    first = str_or_default(customer.get('first_name'), '').strip()
    last = str_or_default(customer.get('last_name'), '').strip()
    if not name and (first or last):
        name = f'{first} {last}'.strip()
    return {
        'id': customer.get('id'),
        'name': name or '-',
        'email': str_or_default(customer.get('email'), '-'),
        'document': str_or_default(
            customer.get('identification') or customer.get('document'), '-'
        ),
        'phone': str_or_default(customer.get('phone'), '-'),
        'city': str_or_default(addr.get('city'), '-'),
    }


def adminet_customer_preview(customer: Dict[str, Any]) -> Dict[str, Any]:
    """Resumen para UI a partir de fila MySQL cliente."""
    return {
        'id': customer.get('Codigo'),
        'name': str_or_default(customer.get('nombre_cliente'), '-'),
        'email': str_or_default(customer.get('Email'), '-'),
        'document': str_or_default(customer.get('CUIT'), '-'),
        'phone': str_or_default(customer.get('telefono'), '-'),
        'city': str_or_default(customer.get('IDDepartamento'), '-'),
    }


def nombre_completo_a_campos_tiendanube(nombre: str) -> Dict[str, str]:
    """Descompone un nombre completo en tiendanube_name, first_name y last_name."""
    name = str_or_default(nombre, '').strip()
    if not name:
        return {
            'tiendanube_name': '',
            'tiendanube_first_name': '',
            'tiendanube_last_name': '',
        }
    parts = name.split(None, 1)
    return {
        'tiendanube_name': name,
        'tiendanube_first_name': parts[0],
        'tiendanube_last_name': parts[1] if len(parts) > 1 else '',
    }


def tiendanube_customer_to_form_fields(customer: Dict[str, Any]) -> Dict[str, Any]:
    """Campos CustomerMapping desde cliente Tienda Nube."""
    addr = (customer.get('addresses') or [{}])[0] if customer.get('addresses') else {}
    if not addr and isinstance(customer.get('default_address'), dict):
        addr = customer['default_address']
    name = str_or_default(customer.get('name'), '').strip()
    first = str_or_default(customer.get('first_name'), '').strip()
    last = str_or_default(customer.get('last_name'), '').strip()
    if name and not first and not last:
        parts = name.split(None, 1)
        first = parts[0] if parts else ''
        last = parts[1] if len(parts) > 1 else ''
    street = str_or_default(addr.get('address') or addr.get('street'), '')
    return {
        'tiendanube_id': customer.get('id'),
        'tiendanube_email': str_or_default(customer.get('email'), ''),
        'tiendanube_name': name,
        'tiendanube_first_name': first,
        'tiendanube_last_name': last,
        'tiendanube_document': str_or_default(
            customer.get('identification') or customer.get('document'), ''
        ),
        'tiendanube_phone': str_or_default(customer.get('phone'), ''),
        'tiendanube_address': street,
        'tiendanube_city': str_or_default(addr.get('city'), ''),
        'tiendanube_state': str_or_default(addr.get('province') or addr.get('state'), ''),
        'tiendanube_country': str_or_default(addr.get('country'), ''),
        'tiendanube_postal_code': str_or_default(addr.get('zipcode') or addr.get('zip'), ''),
    }


def adminet_customer_to_form_fields(customer: Dict[str, Any]) -> Dict[str, Any]:
    """Campos CustomerMapping desde cliente AdministraNET."""
    calle = str_or_default(customer.get('Calle'), '')
    nro = str_or_default(customer.get('NroCalle'), '')
    dpto = str_or_default(customer.get('Dpto'), '')
    direccion = ', '.join(p for p in (calle, nro, dpto) if p and p != '-')
    return {
        'adminet_codigo': customer.get('Codigo'),
        'adminet_nombre': str_or_default(customer.get('nombre_cliente'), ''),
        'adminet_email': str_or_default(customer.get('Email'), ''),
        'adminet_documento': str_or_default(customer.get('CUIT'), ''),
        'adminet_telefono': str_or_default(customer.get('telefono'), ''),
        'adminet_calle': calle,
        'adminet_nro_calle': nro,
        'adminet_dpto': dpto,
        'adminet_direccion': direccion,
        'adminet_cuit': str_or_default(customer.get('CUIT'), ''),
        'adminet_nombre_fantasia': str_or_default(customer.get('nombre_fantasia'), ''),
        'adminet_estado': str_or_default(customer.get('Estado'), ''),
    }


def enrich_cleaned_data_from_sources(
    cleaned_data: dict,
    *,
    base_empresa: Optional[str] = None,
    instance: Optional['CustomerMapping'] = None,
) -> dict:
    """
    Completa cleaned_data consultando Tienda Nube y/o AdministraNET según IDs indicados.
    """
    from ..models import AdministraNETConfig, TiendanubeConfig
    from .adminet_service import AdministraNETService
    from .tiendanube_service import TiendanubeService

    tn_id = cleaned_data.get('tiendanube_id')
    adminet_codigo = cleaned_data.get('adminet_codigo')

    if tn_id:
        tn_cfg = TiendanubeConfig.objects.filter(is_active=True).first()
        if not tn_cfg:
            raise ValueError('tn_config')
        tn_result = TiendanubeService(tn_cfg).get_customer(int(tn_id))
        if not tn_result.get('success'):
            raise ValueError('tn_not_found')
        for key, value in tiendanube_customer_to_form_fields(
            tn_result['customer']
        ).items():
            if value not in (None, '') or not cleaned_data.get(key):
                cleaned_data[key] = value

    if adminet_codigo:
        an_cfg = AdministraNETConfig.objects.filter(is_active=True).first()
        if not an_cfg:
            raise ValueError('an_config')
        be = (base_empresa or an_cfg.database or '').strip()
        an_result = AdministraNETService(an_cfg, base_empresa=be).get_customer(
            int(adminet_codigo)
        )
        if not an_result.get('success'):
            raise ValueError('an_not_found')
        for key, value in adminet_customer_to_form_fields(
            an_result['customer']
        ).items():
            if value not in (None, '') or not cleaned_data.get(key):
                cleaned_data[key] = value

    if not cleaned_data.get('tiendanube_email') and cleaned_data.get('adminet_email'):
        cleaned_data['tiendanube_email'] = cleaned_data['adminet_email']

    return cleaned_data
