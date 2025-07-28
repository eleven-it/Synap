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
from .models_adminet import (
    TiendaNubeCondVentaMap, TiendaNubeAdminetConfig
)

# Dejar solo la configuración y utilidades generales aquí
