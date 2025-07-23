from django.shortcuts import render
from django.conf import settings
from django.db.models import Sum, Q
from django.http import JsonResponse
from ..models import StockQuant, Product, Warehouse, Location, Branch
from tiendanube.models import TiendaNubeConfig
from core.decorators import tiene_permiso
from core.utils import permisos_contextuales

@tiene_permiso("inventory.ver_dashboard")
def stock_dashboard(request):
    """
    Dashboard de stock con filtrado inteligente por sucursal
    - Por defecto muestra stock de la sucursal activa del usuario
    - Permite consultar stock de otras sucursales
    - Incluye filtros avanzados por producto, ubicación y almacén
    """
    context = permisos_contextuales(request, "inventory.ver_dashboard")
    if not context.get("puede_inventory_ver_dashboard"):
        return render(request, "core/403.html", context, status=403)

    # Obtener empresa y sucursal activa del usuario
    empresa = request.user.empresa_activa
    branch_activa = request.user.branch_activa
    
    if not empresa:
        return render(request, "core/403.html", context, status=403)
    
    # Obtener parámetros de filtrado
    branch_id = request.GET.get('branch')
    product_id = request.GET.get('product')
    warehouse_id = request.GET.get('warehouse')
    location_id = request.GET.get('location')
    show_all_branches = request.GET.get('show_all_branches', 'false').lower() == 'true'
    
    # Construir queryset base
    quants = StockQuant.objects.select_related(
        'product', 'location', 'location__warehouse', 'branch'
    ).filter(product__empresa=empresa, quantity__gt=0)
    
    # Aplicar filtros
    if branch_id:
        # Filtro específico por sucursal
        quants = quants.filter(branch_id=branch_id)
    elif not show_all_branches and branch_activa:
        # Por defecto, mostrar solo la sucursal activa
        quants = quants.filter(branch=branch_activa)
    
    if product_id:
        quants = quants.filter(product_id=product_id)
    
    if warehouse_id:
        quants = quants.filter(location__warehouse_id=warehouse_id)
    
    if location_id:
        quants = quants.filter(location_id=location_id)
    
    # Ordenar resultados
    quants = quants.order_by('product__sku', 'location__name')
    
    # Calcular estadísticas
    total_products = quants.values('product').distinct().count()
    total_locations = quants.values('location').distinct().count()
    total_warehouses = quants.values('location__warehouse').distinct().count()
    
    # Calcular stock total disponible
    stock_stats = quants.aggregate(
        total_quantity=Sum('quantity'),
        total_reserved=Sum('reserved_quantity')
    )
    
    # Obtener datos para filtros
    branches = Branch.objects.filter(empresa=empresa, active=True).order_by('name')
    products = Product.objects.filter(empresa=empresa).order_by('name')
    warehouses = Warehouse.objects.filter(empresa=empresa, is_active=True).order_by('name')
    locations = Location.objects.filter(empresa=empresa, is_active=True).order_by('name')
    
    # Preparar contexto
    context.update({
        "quants": quants,
        "total_products": total_products,
        "total_locations": total_locations,
        "total_warehouses": total_warehouses,
        "total_quantity": stock_stats['total_quantity'] or 0,
        "total_reserved": stock_stats['total_reserved'] or 0,
        "total_available": (stock_stats['total_quantity'] or 0) - (stock_stats['total_reserved'] or 0),
        
        # Filtros disponibles
        "branches": branches,
        "products": products,
        "warehouses": warehouses,
        "locations": locations,
        
        # Estado de filtros actuales
        "current_branch_id": branch_id,
        "current_product_id": product_id,
        "current_warehouse_id": warehouse_id,
        "current_location_id": location_id,
        "show_all_branches": show_all_branches,
        "branch_activa": branch_activa,
        
        # Información para el usuario
        "filtered_by_branch": branch_id or (not show_all_branches and branch_activa),
        "current_branch_name": branch_activa.name if branch_activa else None,
    })
    
    return render(request, "inventory/stock_dashboard.html", context)

@tiene_permiso("inventory.ver_dashboard")
def stock_dashboard_api(request):
    """
    API endpoint para obtener datos del dashboard de stock
    Útil para actualizaciones AJAX y filtros dinámicos
    """
    if not request.user.empresa_activa:
        return JsonResponse({'error': 'No company active'}, status=403)
    
    empresa = request.user.empresa_activa
    branch_activa = request.user.branch_activa
    
    # Obtener parámetros
    branch_id = request.GET.get('branch')
    product_id = request.GET.get('product')
    warehouse_id = request.GET.get('warehouse')
    location_id = request.GET.get('location')
    show_all_branches = request.GET.get('show_all_branches', 'false').lower() == 'true'
    
    # Construir queryset
    quants = StockQuant.objects.select_related(
        'product', 'location', 'location__warehouse', 'branch'
    ).filter(product__empresa=empresa, quantity__gt=0)
    
    # Aplicar filtros
    if branch_id:
        quants = quants.filter(branch_id=branch_id)
    elif not show_all_branches and branch_activa:
        quants = quants.filter(branch=branch_activa)
    
    if product_id:
        quants = quants.filter(product_id=product_id)
    if warehouse_id:
        quants = quants.filter(location__warehouse_id=warehouse_id)
    if location_id:
        quants = quants.filter(location_id=location_id)
    
    # Preparar datos para respuesta JSON
    stock_data = []
    for quant in quants[:100]:  # Limitar a 100 registros para performance
        stock_data.append({
            'id': quant.id,
            'product_sku': quant.product.sku,
            'product_name': quant.product.name,
            'location_name': quant.location.name,
            'warehouse_name': quant.location.warehouse.name if quant.location.warehouse else '',
            'branch_name': quant.branch.name,
            'quantity': float(quant.quantity),
            'reserved_quantity': float(quant.reserved_quantity),
            'available_quantity': float(quant.available_quantity),
            'last_updated': quant.last_updated.isoformat() if quant.last_updated else None,
        })
    
    # Estadísticas
    stats = quants.aggregate(
        total_quantity=Sum('quantity'),
        total_reserved=Sum('reserved_quantity')
    )
    
    return JsonResponse({
        'stock_data': stock_data,
        'statistics': {
            'total_products': quants.values('product').distinct().count(),
            'total_locations': quants.values('location').distinct().count(),
            'total_quantity': float(stats['total_quantity'] or 0),
            'total_reserved': float(stats['total_reserved'] or 0),
            'total_available': float((stats['total_quantity'] or 0) - (stats['total_reserved'] or 0)),
        },
        'filters_applied': {
            'branch_id': branch_id,
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'location_id': location_id,
            'show_all_branches': show_all_branches,
        }
    })

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