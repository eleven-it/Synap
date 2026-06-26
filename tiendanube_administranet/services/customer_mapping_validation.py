"""Validaciones de mapeo cliente Tienda Nube ↔ AdministraNET."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from ..models import AdministraNETConfig, CustomerMapping, TiendanubeConfig


def validate_tiendanube_customer_exists(
    tiendanube_config: Optional['TiendanubeConfig'],
    tiendanube_id: Optional[int],
) -> None:
    if not tiendanube_id:
        return
    if not tiendanube_config:
        raise ValidationError(
            _('No hay configuración Tiendanube activa para validar el ID.')
        )
    from .tiendanube_service import TiendanubeService

    result = TiendanubeService(tiendanube_config).get_customer(int(tiendanube_id))
    if not result.get('success'):
        raise ValidationError(
            _('El cliente Tienda Nube con ID %(id)s no existe o no es accesible.')
            % {'id': tiendanube_id}
        )


def validate_adminet_customer_exists(
    adminet_config: Optional['AdministraNETConfig'],
    adminet_codigo: Optional[int],
    base_empresa: Optional[str] = None,
) -> None:
    if not adminet_codigo:
        return
    if not adminet_config:
        raise ValidationError(
            _('No hay configuración AdministraNET activa para validar el código.')
        )
    from .adminet_service import AdministraNETService

    be = (base_empresa or adminet_config.database or '').strip()
    service = AdministraNETService(adminet_config, base_empresa=be)
    result = service.get_customer(int(adminet_codigo))
    if not result.get('success'):
        raise ValidationError(
            _('El cliente AdministraNET con código %(cod)s no existe.')
            % {'cod': adminet_codigo}
        )


def validate_adminet_codigo_unique_mapping(
    adminet_codigo: Optional[int],
    exclude_mapping_id: Optional[int] = None,
) -> None:
    if not adminet_codigo:
        return
    from ..models import CustomerMapping

    qs = CustomerMapping.objects.filter(adminet_codigo=adminet_codigo)
    if exclude_mapping_id:
        qs = qs.exclude(pk=exclude_mapping_id)
    if qs.exists():
        raise ValidationError(
            _('El código AdministraNET %(cod)s ya está vinculado a otro mapeo.')
            % {'cod': adminet_codigo}
        )


def validate_customer_mapping_form(
    cleaned_data: dict,
    instance: Optional['CustomerMapping'] = None,
    base_empresa: Optional[str] = None,
) -> None:
    """Validación cruzada para CustomerMappingForm (errores por campo)."""
    from ..models import AdministraNETConfig, TiendanubeConfig

    tn_id = cleaned_data.get('tiendanube_id')
    adminet_codigo = cleaned_data.get('adminet_codigo')
    tn_cfg = TiendanubeConfig.objects.filter(is_active=True).first()
    an_cfg = AdministraNETConfig.objects.filter(is_active=True).first()
    exclude_id = instance.pk if instance and instance.pk else None
    errors: dict = {}

    for validator, field, args in (
        (validate_tiendanube_customer_exists, 'tiendanube_id', (tn_cfg, tn_id)),
        (validate_adminet_customer_exists, 'adminet_codigo', (an_cfg, adminet_codigo, base_empresa)),
    ):
        try:
            validator(*args)
        except ValidationError as exc:
            errors.setdefault(field, []).extend(exc.messages)

    try:
        validate_adminet_codigo_unique_mapping(adminet_codigo, exclude_id)
    except ValidationError as exc:
        errors.setdefault('adminet_codigo', []).extend(exc.messages)

    if tn_id and adminet_codigo and tn_cfg and an_cfg and 'adminet_codigo' not in errors:
        from .adminet_service import AdministraNETService
        from .tiendanube_service import TiendanubeService

        tn = TiendanubeService(tn_cfg).get_customer(int(tn_id)).get('customer') or {}
        be = (base_empresa or an_cfg.database or '').strip()
        an = AdministraNETService(an_cfg, base_empresa=be).get_customer(
            int(adminet_codigo)
        ).get('customer') or {}
        tn_email = (tn.get('email') or '').strip().lower()
        an_email = (an.get('Email') or '').strip().lower()
        if tn_email and an_email and tn_email != an_email:
            errors.setdefault('__all__', []).append(
                _('Los emails no coinciden: Tienda Nube (%(tn)s) vs AdministraNET (%(an)s). '
                  'Revise el vínculo antes de guardar.')
                % {'tn': tn_email, 'an': an_email}
            )

    if errors:
        raise ValidationError(errors)
