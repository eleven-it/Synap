"""
Factories en memoria (sin MySQL) para datos de prueba del calculador de precios.
"""

from dataclasses import dataclass
from decimal import Decimal

import factory

from ecom.models import EcomMigrationCheckpoint


@dataclass
class ArticuloStub:
    """Valores mínimos tipo fila articulo para tests (no es modelo Django)."""

    precio_base_lista: Decimal = Decimal(
        "1000.00"
    )  # neto ya elegido para la lista activa
    lista_activa_id: int = 1
    alicuota_iva: Decimal = Decimal("21")
    impuesto_interno_pct: Decimal = Decimal("0")
    tipo_articulo: str = "normal"


@dataclass
class ClienteStub:
    tipo_cliente: str | None = "minorista"
    descuento_asignado_pct: Decimal = Decimal("0")
    cod_cliente: int = 1


@dataclass
class ListaPrecioStub:
    """Entidad lógica lista 1..5 u oficial (id 6)."""

    id: int = 1
    etiqueta: str = "Lista 1"


class ArticuloFactory(factory.Factory):
    class Meta:
        model = ArticuloStub

    precio_base_lista = Decimal("1000.00")
    lista_activa_id = 1
    alicuota_iva = Decimal("21")
    impuesto_interno_pct = Decimal("0")


class ClienteFactory(factory.Factory):
    class Meta:
        model = ClienteStub

    tipo_cliente = "minorista"
    descuento_asignado_pct = Decimal("0")


class ListaPrecioFactory(factory.Factory):
    class Meta:
        model = ListaPrecioStub

    id = factory.Sequence(lambda n: (n % 6) + 1)
    etiqueta = factory.LazyAttribute(
        lambda o: "Lista Oficial" if o.id == 6 else f"Lista {o.id}"
    )


class EcomMigrationCheckpointFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EcomMigrationCheckpoint

    module_slug = factory.Sequence(lambda n: f"modulo-{n}")
    notes = ""
