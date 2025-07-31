from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from inventory.models import Product, ProductVariant, StockQuant, Location, Warehouse, StockMove
from sales.models import Client, SalesOrder, SalesOrderLine
from decimal import Decimal
from django.utils import timezone
from .models_synap import (
    TiendaNubeConfig, TiendaNubeSyncLog, TiendaNubeProductMapping,
    TiendaNubeCustomerMapping, TiendaNubeOrderMapping, TiendaNubeRestockRule,
    TiendaNubeRestockLog, TiendaNubeProductRestockPolicy
)

# Importar todos los modelos de Synap para mantener la funcionalidad completa
__all__ = [
    'TiendaNubeConfig',
    'TiendaNubeSyncLog', 
    'TiendaNubeProductMapping',
    'TiendaNubeCustomerMapping',
    'TiendaNubeOrderMapping',
    'TiendaNubeRestockRule',
    'TiendaNubeRestockLog',
    'TiendaNubeProductRestockPolicy',
]
