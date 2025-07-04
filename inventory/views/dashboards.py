from django.shortcuts import render
from django.conf import settings
from ..models import StockQuant
from tiendanube.models import TiendaNubeConfig
from core.decorators import tiene_permiso
from core.utils import permisos_contextuales

@tiene_permiso("inventory.ver_dashboard")
def stock_dashboard(request):
    context = permisos_contextuales(request, "inventory.ver_dashboard")
    if not context.get("puede_inventory_ver_dashboard"):
        return render(request, "core/403.html", context, status=403)

    quants = StockQuant.objects.select_related('product', 'location').order_by('product__sku', 'location__name')
    context["quants"] = quants
    # Calcular la cantidad de locations únicos
    total_locations = quants.values_list('location_id', flat=True).distinct().count()
    context["total_locations"] = total_locations
    return render(request, "inventory/stock_dashboard.html", context)

@tiene_permiso("inventory.ver_dashboard")
def test_app_architecture(request):
    """Vista de prueba para verificar la nueva arquitectura de apps"""
    context = permisos_contextuales(request, "inventory.ver_dashboard")
    if not context.get("puede_inventory_ver_dashboard"):
        return render(request, "core/403.html", context, status=403)
    
    return render(request, "inventory/test_app.html", context)

@tiene_permiso("inventory.ver_dashboard")
def simple_test(request):
    """Vista de prueba simple para verificar el template base"""
    context = permisos_contextuales(request, "inventory.ver_dashboard")
    if not context.get("puede_inventory_ver_dashboard"):
        return render(request, "core/403.html", context, status=403)
    
    return render(request, "inventory/simple_test.html", context)

@tiene_permiso("inventory.config_tiendanube")
def tiendanube_dashboard(request):
    """TiendaNube integration dashboard"""
    context = permisos_contextuales(request, "inventory.config_tiendanube")
    if not context.get("puede_inventory_config_tiendanube"):
        return render(request, "core/403.html", context, status=403)
    
    # Get TiendaNube config
    config = TiendaNubeConfig.objects.first()
    
    # If no config, check environment variables
    if not config:
        store_id = getattr(settings, 'TIENDANUBE_STORE_ID', '')
        access_token = getattr(settings, 'TIENDANUBE_ACCESS_TOKEN', '')
        
        if store_id and access_token:
            context["env_configured"] = True
            context["store_id"] = store_id
            context["api_url"] = getattr(settings, 'TIENDANUBE_API_URL', 'https://api.tiendanube.com/v1')
            context["auto_sync"] = getattr(settings, 'TIENDANUBE_AUTO_SYNC', True)
            context["sync_interval"] = getattr(settings, 'TIENDANUBE_SYNC_INTERVAL', 30)
        else:
            context["env_configured"] = False
    else:
        context["env_configured"] = True
        context["store_id"] = config.store_id
        context["api_url"] = config.api_url
        context["auto_sync"] = config.auto_sync
        context["sync_interval"] = config.sync_interval
    
    context["tiendanube_config"] = config
    context["is_configured"] = config.is_configured if config else False
    
    return render(request, "inventory/tiendanube_dashboard.html", context) 