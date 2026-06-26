"""
Vistas product views — tiendanube_administranet.
"""

import logging
import requests
import uuid
import json
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import models
from django.db.models import Q, Count
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView, RedirectView, View
from django.views.generic.edit import FormView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import gettext as _, gettext_lazy as _
from django.core.paginator import Paginator

from ..models import (
    TiendanubeConfig, AdministraNETConfig, CustomerMapping,
    SyncLog, ProductMapping, ProductVariantMapping, ProductCategoryMapping,
    OrderMapping, WebhookConfig, WebhookEvent, WebhookDeliveryLog
)
from ..services.automatic_mapping_service import AutomaticMappingService
from ..services.product_comparison import (
    filas_comparacion_producto,
    resumen_comparacion_producto,
)
from ..services.product_pricing import (
    precios_finales_desde_product_mapping,
    precios_finales_tiendanube_mapping,
)
from ..services.product_service import TiendanubeProductService
from ..services.sync_service import TiendanubeAdministraNETSyncService
from ..forms import (
    TiendanubeConfigForm, AdministraNETConfigForm,
    CustomerMappingForm, CustomerMappingFilterForm,
    ProductMappingForm, ProductVariantMappingForm, ProductCategoryMappingForm,
    OrderMappingForm, WebhookConfigForm, WebhookEventFilterForm
)
from ..mixins import TiendanubeAdministranetLoginMixin
from ..mysql import resolve_mysql_base_empresa
from ..services.tiendanube_service import NUVEMSHOP_API_VERSION

DEFAULT_TIENDANUBE_API_URL = f'https://api.tiendanube.com/{NUVEMSHOP_API_VERSION}'

logger = logging.getLogger(__name__)

@permission_required('tiendanube_administranet.view_productmapping')
def product_list(request):
    """Vista para listar productos mapeados."""
    try:
        # Obtener filtros
        search = request.GET.get('search', '')
        status = request.GET.get('status', '')
        sync_enabled = request.GET.get('sync_enabled', '')
        
        # Query base
        products = ProductMapping.objects.all()
        
        # Aplicar filtros
        if search:
            products = products.filter(
                Q(tiendanube_name__icontains=search) |
                Q(adminet_nombre__icontains=search) |
                Q(tiendanube_sku__icontains=search) |
                Q(adminet_codigo_articulo__icontains=search)
            )
        
        if status:
            products = products.filter(sync_status=status)
        
        if sync_enabled:
            products = products.filter(sync_enabled=sync_enabled == 'true')
        
        # Ordenar
        products = products.order_by('-created_at')
        
        # Paginación
        paginator = Paginator(products, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Estadísticas
        stats = {
            'total': ProductMapping.objects.count(),
            'synced': ProductMapping.objects.filter(sync_status=ProductMapping.SyncStatus.SYNCED).count(),
            'pending': ProductMapping.objects.filter(sync_status=ProductMapping.SyncStatus.PENDING).count(),
            'error': ProductMapping.objects.filter(sync_status=ProductMapping.SyncStatus.ERROR).count(),
        }
        
        context = {
            'page_obj': page_obj,
            'stats': stats,
            'search': search,
            'status': status,
            'sync_enabled': sync_enabled,
        }
        
        return render(request, 'tiendanube_administranet/products/product_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in product_list: {e}")
        # Usar contexto para pasar el error en lugar de messages
        context = {
            'error_message': f'Error cargando productos: {str(e)}',
            'page_obj': [],
            'stats': {'total': 0, 'synced': 0, 'pending': 0, 'error': 0},
            'search': '',
            'status': '',
            'sync_enabled': '',
        }
        return render(request, 'tiendanube_administranet/products/product_list.html', context)


@login_required
@permission_required('tiendanube_administranet.add_productmapping')
def product_create(request):
    """Vista para crear nuevo mapeo de producto."""
    if request.method == 'POST':
        form = ProductMappingForm(request.POST)
        if form.is_valid():
            try:
                product = form.save()
                messages.success(request, 'Producto creado exitosamente.')
                return redirect('tiendanube_administranet:product_detail', product_id=product.id)
            except Exception as e:
                logger.error(f"Error creating product: {e}")
                messages.error(request, f'Error creando producto: {str(e)}')
    else:
        form = ProductMappingForm()
    
    context = {
        'form': form,
        'title': 'Crear Producto',
        'action': 'Crear'
    }
    return render(request, 'tiendanube_administranet/products/product_form.html', context)


@login_required
@permission_required('tiendanube_administranet.view_productmapping')
def product_detail(request, product_id):
    """Vista para ver detalles de un producto."""
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        variants = ProductVariantMapping.objects.filter(product_mapping=product)
        tn_fetch_error = None

        # Refrescar snapshot TN desde la API (precio/stock/handle viven en variante).
        if product.tiendanube_id:
            tn_config = TiendanubeConfig.objects.filter(is_active=True).first()
            if tn_config:
                tn_result = TiendanubeProductService(tn_config).get_product(
                    int(product.tiendanube_id)
                )
                if tn_result.get('success'):
                    adminet_config = AdministraNETConfig.objects.filter(
                        is_active=True
                    ).first()
                    mapper = AutomaticMappingService(
                        tiendanube_config=tn_config,
                        adminet_config=adminet_config,
                    )
                    mapper.update_product_mapping_from_tiendanube(
                        product, tn_result['product']
                    )
                    product.refresh_from_db()
                else:
                    tn_fetch_error = tn_result.get(
                        'message', 'No se pudo consultar Tiendanube'
                    )
            else:
                tn_fetch_error = 'No hay configuración activa de Tiendanube'

        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        filas_comparacion = filas_comparacion_producto(product, config=adminet_config)

        context = {
            'product': product,
            'variants': variants,
            'tn_fetch_error': tn_fetch_error,
            'filas_comparacion': filas_comparacion,
            'resumen_comparacion': resumen_comparacion_producto(filas_comparacion),
        }
        return render(request, 'tiendanube_administranet/products/product_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in product_detail: {e}")
        messages.error(request, f'Error cargando producto: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.change_productmapping')
def product_edit(request, product_id):
    """Vista para editar un producto."""
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        
        if request.method == 'POST':
            form = ProductMappingForm(request.POST, instance=product)
            if form.is_valid():
                form.save()
                messages.success(request, 'Producto actualizado exitosamente.')
                return redirect('tiendanube_administranet:product_detail', product_id=product.id)
        else:
            form = ProductMappingForm(instance=product)
        
        context = {
            'form': form,
            'product': product,
            'title': 'Editar Producto',
            'action': 'Actualizar'
        }
        return render(request, 'tiendanube_administranet/products/product_form.html', context)
        
    except Exception as e:
        logger.error(f"Error in product_edit: {e}")
        messages.error(request, f'Error editando producto: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.delete_productmapping')
def product_delete(request, product_id):
    """Vista para eliminar un producto."""
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        
        if request.method == 'POST':
            product.delete()
            messages.success(request, 'Producto eliminado exitosamente.')
            return redirect('tiendanube_administranet:product_list')
        
        context = {
            'product': product,
        }
        return render(request, 'tiendanube_administranet/products/product_confirm_delete.html', context)
        
    except Exception as e:
        logger.error(f"Error in product_delete: {e}")
        messages.error(request, f'Error eliminando producto: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.change_productmapping')
def product_sync(request, product_id):
    """Vista AJAX para sincronizar un producto específico."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        
        # Obtener configuraciones
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config or not adminet_config:
            return JsonResponse({
                'success': False,
                'error': 'Configuraciones de Tiendanube o AdministraNET no encontradas'
            })
        
        # Crear servicio de sincronización
        from ..services.sync_service import TiendanubeAdministraNETSyncService
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        
        # Determinar dirección de sincronización
        sync_direction = request.POST.get('direction', 'both')
        
        if sync_direction == 'to_adminet' or sync_direction == 'both':
            # Sincronizar desde Tiendanube hacia AdministraNET
            if product.tiendanube_id:
                result = sync_service.sync_products_from_tiendanube()
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'El producto no tiene ID de Tiendanube para sincronizar'
                })
        
        elif sync_direction == 'from_adminet':
            # Sincronizar desde AdministraNET hacia Tiendanube
            if product.adminet_id:
                result = sync_service.sync_products_from_adminet()
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'El producto no tiene ID de AdministraNET para sincronizar'
                })
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in product_sync: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error en sincronización: {str(e)}'
        })


@login_required
@permission_required('tiendanube_administranet.change_productmapping')
def product_sync_all(request):
    """Vista AJAX para sincronizar todos los productos."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        # Obtener configuraciones
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config or not adminet_config:
            return JsonResponse({
                'success': False,
                'error': 'Configuraciones de Tiendanube o AdministraNET no encontradas'
            })
        
        # Crear servicio de sincronización
        from ..services.sync_service import TiendanubeAdministraNETSyncService
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        
        # Determinar dirección de sincronización
        sync_direction = request.POST.get('direction', 'both')
        
        if sync_direction == 'to_adminet' or sync_direction == 'both':
            result = sync_service.sync_products_from_tiendanube()
        elif sync_direction == 'from_adminet':
            result = sync_service.sync_products_from_adminet()
        else:
            return JsonResponse({
                'success': False,
                'error': 'Dirección de sincronización no válida'
            })
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in product_sync_all: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error en sincronización: {str(e)}'
        })


@login_required
@permission_required('tiendanube_administranet.add_productmapping')
def product_import_from_tiendanube(request):
    """Vista AJAX para importar productos desde Tiendanube."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        # Obtener configuración de Tiendanube
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if not tiendanube_config:
            return JsonResponse({
                'success': False,
                'error': 'Configuración de Tiendanube no encontrada'
            })
        
        # Crear servicio de productos
        from ..services.product_service import TiendanubeProductService
        product_service = TiendanubeProductService(tiendanube_config)
        
        # Obtener productos de Tiendanube
        result = product_service.get_products(limit=100)
        
        if not result['success']:
            return JsonResponse(result)
        
        products = result['products']
        imported_count = 0
        error_count = 0
        
        for product_data in products:
            try:
                # Verificar si ya existe
                existing = ProductMapping.objects.filter(tiendanube_id=product_data['id']).first()
                if existing:
                    continue
                
                # Crear nuevo mapeo
                ProductMapping.objects.create(
                    tiendanube_id=product_data['id'],
                    tiendanube_name=product_data.get('name', ''),
                    tiendanube_sku=product_data.get('sku', ''),
                    tiendanube_price=float(product_data.get('price', 0)),
                    tiendanube_stock=int(product_data.get('stock', 0)),
                    tiendanube_config=tiendanube_config,
                    sync_status=ProductMapping.SyncStatus.PENDING
                )
                imported_count += 1
                
            except Exception as e:
                logger.error(f"Error importing product {product_data.get('id')}: {e}")
                error_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Importación completada: {imported_count} productos importados, {error_count} errores',
            'imported_count': imported_count,
            'error_count': error_count
        })
        
    except Exception as e:
        logger.error(f"Error in product_import_from_tiendanube: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error en importación: {str(e)}'
        })


# ============================================================================
# VISTAS DE VARIANTES
# ============================================================================

@login_required
@permission_required('tiendanube_administranet.view_productvariantmapping')
def variant_list(request, product_id):
    """Vista para listar variantes de un producto."""
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        variants = ProductVariantMapping.objects.filter(product_mapping=product).order_by('-created_at')
        
        context = {
            'product': product,
            'variants': variants,
        }
        return render(request, 'tiendanube_administranet/products/variant_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in variant_list: {e}")
        messages.error(request, f'Error cargando variantes: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.add_productvariantmapping')
def variant_create(request, product_id):
    """Vista para crear nueva variante."""
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        
        if request.method == 'POST':
            form = ProductVariantMappingForm(request.POST)
            if form.is_valid():
                variant = form.save(commit=False)
                variant.product_mapping = product
                variant.save()
                messages.success(request, 'Variante creada exitosamente.')
                return redirect('tiendanube_administranet:variant_list', product_id=product.id)
        else:
            form = ProductVariantMappingForm()
        
        context = {
            'form': form,
            'product': product,
            'title': 'Crear Variante',
            'action': 'Crear'
        }
        return render(request, 'tiendanube_administranet/products/variant_form.html', context)
        
    except Exception as e:
        logger.error(f"Error in variant_create: {e}")
        messages.error(request, f'Error creando variante: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.change_productvariantmapping')
def variant_edit(request, variant_id):
    """Vista para editar una variante."""
    try:
        variant = get_object_or_404(ProductVariantMapping, id=variant_id)
        
        if request.method == 'POST':
            form = ProductVariantMappingForm(request.POST, instance=variant)
            if form.is_valid():
                form.save()
                messages.success(request, 'Variante actualizada exitosamente.')
                return redirect('tiendanube_administranet:variant_list', product_id=variant.product_mapping.id)
        else:
            form = ProductVariantMappingForm(instance=variant)
        
        context = {
            'form': form,
            'variant': variant,
            'product': variant.product_mapping,
            'title': 'Editar Variante',
            'action': 'Actualizar'
        }
        return render(request, 'tiendanube_administranet/products/variant_form.html', context)
        
    except Exception as e:
        logger.error(f"Error in variant_edit: {e}")
        messages.error(request, f'Error editando variante: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.delete_productvariantmapping')
def variant_delete(request, variant_id):
    """Vista para eliminar una variante."""
    try:
        variant = get_object_or_404(ProductVariantMapping, id=variant_id)
        product_id = variant.product_mapping.id
        
        if request.method == 'POST':
            variant.delete()
            messages.success(request, 'Variante eliminada exitosamente.')
            return redirect('tiendanube_administranet:variant_list', product_id=product_id)
        
        context = {
            'variant': variant,
            'product': variant.product_mapping,
        }
        return render(request, 'tiendanube_administranet/products/variant_confirm_delete.html', context)
        
    except Exception as e:
        logger.error(f"Error in variant_delete: {e}")
        messages.error(request, f'Error eliminando variante: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.change_productvariantmapping')
def variant_sync(request, variant_id):
    """Vista AJAX para sincronizar una variante específica."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        variant = get_object_or_404(ProductVariantMapping, id=variant_id)
        
        # Obtener configuraciones
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config or not adminet_config:
            return JsonResponse({
                'success': False,
                'error': 'Configuraciones de Tiendanube o AdministraNET no encontradas'
            })
        
        # Crear servicio de sincronización
        from ..services.sync_service import TiendanubeAdministraNETSyncService
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        
        # Sincronizar variantes del producto
        result = sync_service.sync_product_variants_from_tiendanube(variant.product_mapping)
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in variant_sync: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error en sincronización: {str(e)}'
        })


# ============================================================================
# VISTAS DE CATEGORÍAS
# ============================================================================

@login_required
@permission_required('tiendanube_administranet.view_productcategorymapping')
def category_list(request):
    """Vista para listar categorías mapeadas."""
    try:
        categories = ProductCategoryMapping.objects.all().order_by('-created_at')
        
        # Paginación
        paginator = Paginator(categories, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
        }
        return render(request, 'tiendanube_administranet/products/category_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in category_list: {e}")
        messages.error(request, f'Error cargando categorías: {str(e)}')
        return redirect('tiendanube_administranet:dashboard')


@login_required
@permission_required('tiendanube_administranet.add_productcategorymapping')
def category_import_from_tiendanube(request):
    """Vista AJAX para importar categorías desde Tiendanube."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        # Obtener configuración de Tiendanube
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if not tiendanube_config:
            return JsonResponse({
                'success': False,
                'error': 'Configuración de Tiendanube no encontrada'
            })
        
        # Crear servicio de productos
        from ..services.product_service import TiendanubeProductService
        product_service = TiendanubeProductService(tiendanube_config)
        
        # Obtener categorías de Tiendanube
        result = product_service.get_categories()
        
        if not result['success']:
            return JsonResponse(result)
        
        categories = result['categories']
        imported_count = 0
        error_count = 0
        
        for category_data in categories:
            try:
                # Verificar si ya existe
                existing = ProductCategoryMapping.objects.filter(tiendanube_id=category_data['id']).first()
                if existing:
                    continue
                
                # Crear nuevo mapeo
                ProductCategoryMapping.objects.create(
                    tiendanube_id=category_data['id'],
                    tiendanube_name=category_data.get('name', ''),
                    tiendanube_handle=category_data.get('handle', ''),
                    tiendanube_description=category_data.get('description', ''),
                    tiendanube_parent_id=category_data.get('parent_id'),
                    tiendanube_image=category_data.get('image', ''),
                    sync_status=ProductCategoryMapping.SyncStatus.PENDING
                )
                imported_count += 1
                
            except Exception as e:
                logger.error(f"Error importing category {category_data.get('id')}: {e}")
                error_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Importación completada: {imported_count} categorías importadas, {error_count} errores',
            'imported_count': imported_count,
            'error_count': error_count
        })
        
    except Exception as e:
        logger.error(f"Error in category_import_from_tiendanube: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error en importación: {str(e)}'
        })


# ============================================================================
# APIs
# ============================================================================

@login_required
@permission_required('tiendanube_administranet.view_productmapping')
def api_products(request):
    """API para obtener productos."""
    try:
        products = ProductMapping.objects.all()
        
        # Filtros
        search = request.GET.get('search', '')
        if search:
            products = products.filter(
                Q(tiendanube_name__icontains=search) |
                Q(adminet_nombre__icontains=search)
            )
        
        # Serializar
        data = []
        for product in products[:50]:  # Límite de 50
            data.append({
                'id': product.id,
                'tiendanube_id': product.tiendanube_id,
                'tiendanube_name': product.tiendanube_name,
                'tiendanube_sku': product.tiendanube_sku,
                'tiendanube_price': float(product.tiendanube_price) if product.tiendanube_price else 0,
                'tiendanube_stock': product.tiendanube_stock,
                'adminet_id': product.adminet_id,
                'adminet_nombre': product.adminet_nombre,
                'adminet_codigo_articulo': product.adminet_codigo_articulo,
                'sync_status': product.sync_status,
                'sync_enabled': product.sync_enabled,
                'last_synced': product.last_synced.isoformat() if product.last_synced else None,
            })
        
        return JsonResponse({
            'success': True,
            'products': data,
            'total': len(data)
        })
        
    except Exception as e:
        logger.error(f"Error in api_products: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@permission_required('tiendanube_administranet.view_productmapping')
def api_product_detail(request, product_id):
    """API para obtener detalles de un producto."""
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        precios_adminet = precios_finales_desde_product_mapping(
            product, config=adminet_config
        )
        precios_tn = precios_finales_tiendanube_mapping(product)

        data = {
            'id': product.id,
            'tiendanube_id': product.tiendanube_id,
            'tiendanube_name': product.tiendanube_name,
            'tiendanube_handle': product.tiendanube_handle,
            'tiendanube_description': product.tiendanube_description,
            'tiendanube_sku': product.tiendanube_sku,
            'tiendanube_price': precios_tn['precio_venta'],
            'tiendanube_compare_at_price': float(product.tiendanube_compare_at_price) if product.tiendanube_compare_at_price else 0,
            'tiendanube_cost': precios_tn['costo'],
            'tiendanube_precio_venta_final': precios_tn['precio_venta'],
            'tiendanube_costo_final': precios_tn['costo'],
            'tiendanube_stock': product.tiendanube_stock,
            'tiendanube_weight': float(product.tiendanube_weight) if product.tiendanube_weight else 0,
            'tiendanube_width': float(product.tiendanube_width) if product.tiendanube_width else 0,
            'tiendanube_height': float(product.tiendanube_height) if product.tiendanube_height else 0,
            'tiendanube_depth': float(product.tiendanube_depth) if product.tiendanube_depth else 0,
            'tiendanube_free_shipping': product.tiendanube_free_shipping,
            'tiendanube_published': product.tiendanube_published,
            'tiendanube_featured': product.tiendanube_featured,
            'tiendanube_product_type': product.tiendanube_product_type,
            'tiendanube_categories': product.tiendanube_categories,
            'tiendanube_images': product.tiendanube_images,
            'tiendanube_videos': product.tiendanube_videos,
            'tiendanube_seo_title': product.tiendanube_seo_title,
            'tiendanube_seo_description': product.tiendanube_seo_description,
            'tiendanube_created_at': product.tiendanube_created_at.isoformat() if product.tiendanube_created_at else None,
            'tiendanube_updated_at': product.tiendanube_updated_at.isoformat() if product.tiendanube_updated_at else None,
            'adminet_id': product.adminet_id,
            'adminet_id_manual': product.adminet_id_manual,
            'adminet_codigo_articulo': product.adminet_codigo_articulo,
            'adminet_nombre': product.adminet_nombre,
            'adminet_detalle': product.adminet_detalle,
            'adminet_precio_costo': float(product.adminet_precio_costo) if product.adminet_precio_costo else 0,
            'adminet_precio_1v': float(product.adminet_precio_1v) if product.adminet_precio_1v else 0,
            'adminet_precio_venta_final': precios_adminet['precio_venta'],
            'adminet_costo_final': precios_adminet['costo'],
            'adminet_lista_precio_label': precios_adminet['lista_label'],
            'adminet_stock': product.adminet_stock,
            'adminet_codigo_barra': product.adminet_codigo_barra,
            'adminet_ecommerce': product.adminet_ecommerce,
            'adminet_disponible_venta': product.adminet_disponible_venta,
            'sync_status': product.sync_status,
            'sync_enabled': product.sync_enabled,
            'sync_price': product.sync_price,
            'sync_stock': product.sync_stock,
            'sync_description': product.sync_description,
            'sync_images': product.sync_images,
            'error_message': product.error_message,
            'last_synced': product.last_synced.isoformat() if product.last_synced else None,
            'created_at': product.created_at.isoformat(),
            'updated_at': product.updated_at.isoformat(),
        }
        
        return JsonResponse({
            'success': True,
            'product': data
        })
        
    except Exception as e:
        logger.error(f"Error in api_product_detail: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@permission_required('tiendanube_administranet.change_productmapping')
def api_product_sync(request, product_id):
    """API para sincronizar un producto."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        
        # Obtener configuraciones
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config or not adminet_config:
            return JsonResponse({
                'success': False,
                'error': 'Configuraciones de Tiendanube o AdministraNET no encontradas'
            })
        
        # Crear servicio de sincronización
        from ..services.sync_service import TiendanubeAdministraNETSyncService
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        
        # Sincronizar
        sync_direction = request.POST.get('direction', 'both')
        
        if sync_direction == 'to_adminet' or sync_direction == 'both':
            result = sync_service.sync_products_from_tiendanube()
        elif sync_direction == 'from_adminet':
            result = sync_service.sync_products_from_adminet()
        else:
            return JsonResponse({
                'success': False,
                'error': 'Dirección de sincronización no válida'
            })
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in api_product_sync: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# =============================================================================
# TIENDANUBE CONFIGURATION VIEWS
# =============================================================================

