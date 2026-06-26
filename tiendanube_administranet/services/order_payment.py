"""Extracción de datos de pago desde órdenes Tiendanube (API / webhooks)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional


@dataclass
class TiendanubeOrderPayment:
    """Pago normalizado de una orden TN ya cobrada."""

    payment_status: str
    method_label: str
    gateway: Optional[str] = None
    gateway_id: Optional[str] = None
    gateway_name: Optional[str] = None
    gateway_method: Optional[str] = None
    credit_card_company: Optional[str] = None
    installments: Optional[int] = None
    paid_at: Optional[str] = None
    total: Decimal = Decimal('0')
    medio_adminet: str = 'tarjeta'
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_info_ped_eco_fragment(self) -> Dict[str, Any]:
        return {
            'payment_status': self.payment_status,
            'method': self.method_label,
            'gateway': self.gateway,
            'gateway_id': self.gateway_id,
            'gateway_name': self.gateway_name,
            'gateway_method': self.gateway_method,
            'credit_card_company': self.credit_card_company,
            'installments': self.installments,
            'paid_at': self.paid_at,
            'total': float(self.total),
            'medio_adminet': self.medio_adminet,
        }


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0')


def _normalize_medio(
    *,
    gateway_method: str,
    method_label: str,
    gateway_name: str,
) -> str:
    blob = f'{gateway_method} {method_label} {gateway_name}'.lower()
    if any(k in blob for k in ('transfer', 'wire', 'transferencia', 'banco', 'bank')):
        return 'transferencia'
    if any(k in blob for k in ('cash', 'efectivo', 'contra reembolso', 'cod')):
        return 'efectivo'
    if any(k in blob for k in (
        'card', 'tarjeta', 'credit', 'debit', 'mercadopago', 'mercado pago',
        'mp', 'modo', 'paypal', 'stripe', 'gateway',
    )):
        return 'tarjeta'
    return 'tarjeta'


def parse_tiendanube_order_payment(order: Dict[str, Any]) -> TiendanubeOrderPayment:
    """
    Normaliza campos de pago de la orden TN.

    Fuentes (API Order): ``payment_status``, ``payment_details``, ``gateway``,
    ``gateway_id``, ``gateway_name``, ``paid_at``, ``total``.
    """
    payment_details = order.get('payment_details') or {}
    if not isinstance(payment_details, dict):
        payment_details = {}

    nested_payment = order.get('payment') or {}
    if not isinstance(nested_payment, dict):
        nested_payment = {}

    gateway_name = str(
        order.get('gateway_name')
        or nested_payment.get('name')
        or ''
    ).strip()
    gateway_id = str(order.get('gateway_id') or '').strip() or None
    gateway = str(order.get('gateway') or '').strip() or None
    gateway_method = str(order.get('gateway_method') or '').strip() or None

    method_label = str(
        payment_details.get('method')
        or nested_payment.get('method')
        or nested_payment.get('name')
        or gateway_name
        or gateway_method
        or 'Tiendanube'
    ).strip()

    installments_raw = payment_details.get('installments')
    installments: Optional[int] = None
    if installments_raw is not None:
        try:
            installments = int(installments_raw)
        except (TypeError, ValueError):
            installments = None

    payment_status = str(order.get('payment_status') or 'pending').lower()
    total = _to_decimal(order.get('total'))

    medio = _normalize_medio(
        gateway_method=gateway_method or '',
        method_label=method_label,
        gateway_name=gateway_name,
    )

    return TiendanubeOrderPayment(
        payment_status=payment_status,
        method_label=method_label,
        gateway=gateway,
        gateway_id=gateway_id,
        gateway_name=gateway_name or None,
        gateway_method=gateway_method,
        credit_card_company=payment_details.get('credit_card_company'),
        installments=installments,
        paid_at=order.get('paid_at'),
        total=total,
        medio_adminet=medio,
        raw={
            'payment_details': payment_details,
            'payment': nested_payment,
            'gateway': gateway,
            'gateway_id': gateway_id,
            'gateway_name': gateway_name,
            'gateway_method': gateway_method,
        },
    )


def pago_confirmado(payment: TiendanubeOrderPayment) -> bool:
    return payment.payment_status in ('paid', 'authorized', 'partially_paid')
