from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings

from core.decorators import tiene_permiso
from core.utils import permisos_contextuales
from tiendanube.models import Product, TiendaNubeConfig, TiendaNubeSyncLog, TiendaNubeProductMapping
from tiendanube.services import TiendaNubeService
from .serializers import (
    ProductSerializer, TiendaNubeConfigSerializer, 
    TiendaNubeSyncLogSerializer, SyncStatusSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@tiene_permiso("inventory.")
def tiendanube_sync_status(request):
    """Obtiene el estado de sincronización con TiendaNube"""
    try:
        # Get the first available configuration
        config = TiendaNubeConfig.objects.first()
        if not config:
            return Response(
                {'error': 'No TiendaNube configuration found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = TiendaNubeService(config)
        status_data = service.get_sync_status()
        
        serializer = SyncStatusSerializer(status_data)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'error': f'Error obteniendo estado de sincronización: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@tiene_permiso("inventory.")
def tiendanube_sync_products(request):
    """Sincroniza productos nuevos y pendientes con TiendaNube"""
    try:
        limit = request.data.get('limit', 100)
        offset = request.data.get('offset', 0)
        config = TiendaNubeConfig.objects.first()
        if not config:
            return Response({'error': 'No TiendaNube configuration found'}, status=status.HTTP_400_BAD_REQUEST)
        service = TiendaNubeService(config)
        # Sincronizar productos nuevos (sin tiendanube_id)
        success_new, failed_new = service.sync_products_from_tiendanube(limit=limit, offset=offset)
        # Sincronizar productos pendientes (mapping pending)
        pendientes = TiendaNubeProductMapping.objects.filter(sync_status='pending', sync_enabled=True)
        success_pending = 0
        failed_pending = 0
        for mapping in pendientes:
            ok, msg = service.sync_product_update(mapping.product)
            if ok:
                success_pending += 1
            else:
                failed_pending += 1
        total_success = success_new + success_pending
        total_failed = failed_new + failed_pending
        return Response({
            'success': True,
            'message': f'Sincronización completada: {total_success} exitosos, {total_failed} fallidos (Nuevos: {success_new}/{failed_new}, Pendientes: {success_pending}/{failed_pending})',
            'data': {
                'success_new': success_new,
                'failed_new': failed_new,
                'success_pending': success_pending,
                'failed_pending': failed_pending,
                'total_success': total_success,
                'total_failed': total_failed
            }
        })
    except Exception as e:
        return Response({'error': f'Error en sincronización: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@tiene_permiso("inventory.")
def tiendanube_sync_stock(request):
    """Sincroniza stock hacia TiendaNube"""
    try:
        product_id = request.data.get('product_id')
        
        # Get the first available configuration
        config = TiendaNubeConfig.objects.first()
        if not config:
            return Response(
                {'error': 'No TiendaNube configuration found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = TiendaNubeService(config)
        
        if product_id:
            product = get_object_or_404(Product, id=product_id)
            success, failed = service.sync_stock_to_tiendanube(product=product)
        else:
            success, failed = service.sync_stock_to_tiendanube()
        
        return Response({
            'success': True,
            'message': f'Stock sincronizado: {success} exitosos, {failed} fallidos',
            'data': {
                'success_count': success,
                'failed_count': failed,
                'total_processed': success + failed
            }
        })
        
    except Exception as e:
        return Response(
            {'error': f'Error sincronizando stock: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@tiene_permiso("inventory.")
def tiendanube_products(request):
    """Lista productos sincronizados con TiendaNube"""
    try:
        # Parámetros de filtrado
        synced_only = request.GET.get('synced_only', 'false').lower() == 'true'
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        # Construir queryset
        if synced_only:
            products = Product.objects.filter(tiendanube_id__isnull=False)
        else:
            products = Product.objects.all()
        
        # Aplicar paginación
        products = products[offset:offset + limit]
        
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'error': f'Error obteniendo productos: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@tiene_permiso("inventory.")
def tiendanube_sync_logs(request):
    """Obtiene logs de sincronización"""
    try:
        limit = int(request.GET.get('limit', 20))
        
        # Get the first available configuration
        config = TiendaNubeConfig.objects.first()
        if not config:
            return Response(
                {'error': 'No TiendaNube configuration found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = TiendaNubeService(config)
        logs = service.get_recent_logs(limit=limit)
        
        serializer = TiendaNubeSyncLogSerializer(logs, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'error': f'Error obteniendo logs: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@tiene_permiso("inventory.")
def tiendanube_test_connection(request):
    """Prueba la conexión con TiendaNube"""
    try:
        # Get the first available configuration
        config = TiendaNubeConfig.objects.first()
        if not config:
            return Response(
                {'error': 'No TiendaNube configuration found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = TiendaNubeService(config)
        success, message = service.test_connection()
        
        return Response({
            'success': success,
            'message': message,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response(
            {'error': f'Error probando conexión: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@tiene_permiso("inventory.")
def tiendanube_create_webhook(request):
    """Crea webhook en TiendaNube"""
    try:
        webhook_url = request.data.get('webhook_url')
        
        if not webhook_url:
            return Response(
                {'error': 'webhook_url es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the first available configuration
        config = TiendaNubeConfig.objects.first()
        if not config:
            return Response(
                {'error': 'No TiendaNube configuration found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = TiendaNubeService(config)
        response = service.create_webhook(webhook_url)
        
        return Response({
            'success': True,
            'message': 'Webhook creado exitosamente',
            'data': response
        })
        
    except Exception as e:
        return Response(
            {'error': f'Error creando webhook: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@tiene_permiso("inventory.")
def tiendanube_config(request):
    """Obtiene o actualiza la configuración de TiendaNube"""
    try:
        config = TiendaNubeConfig.objects.first()
        
        if request.method == 'GET':
            if config:
                serializer = TiendaNubeConfigSerializer(config)
                return Response(serializer.data)
            else:
                return Response({'configured': False})
        
        elif request.method == 'PUT':
            if config:
                serializer = TiendaNubeConfigSerializer(config, data=request.data, partial=True)
            else:
                serializer = TiendaNubeConfigSerializer(data=request.data)
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
    except Exception as e:
        return Response(
            {'error': f'Error con configuración: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@tiene_permiso("inventory.")
def tiendanube_create_config_from_env(request):
    """Crea configuración desde variables de entorno"""
    try:
        # Verificar si ya existe configuración
        if TiendaNubeConfig.objects.exists():
            return Response(
                {'error': 'Ya existe una configuración de TiendaNube'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener valores de variables de entorno
        store_id = getattr(settings, 'TIENDANUBE_STORE_ID', '')
        access_token = getattr(settings, 'TIENDANUBE_ACCESS_TOKEN', '')
        webhook_secret = getattr(settings, 'TIENDANUBE_WEBHOOK_SECRET', '')
        api_url = getattr(settings, 'TIENDANUBE_API_URL', 'https://api.tiendanube.com/v1')
        auto_sync = getattr(settings, 'TIENDANUBE_AUTO_SYNC', True)
        sync_interval = getattr(settings, 'TIENDANUBE_SYNC_INTERVAL', 30)
        
        # Verificar que tenemos los datos mínimos
        if not store_id or not access_token:
            return Response(
                {'error': 'Variables de entorno TIENDANUBE_STORE_ID y TIENDANUBE_ACCESS_TOKEN son requeridas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear configuración
        config = TiendaNubeConfig.objects.create(
            store_id=store_id,
            access_token=access_token,
            webhook_secret=webhook_secret,
            api_url=api_url,
            auto_sync=auto_sync,
            sync_interval=sync_interval
        )
        
        serializer = TiendaNubeConfigSerializer(config)
        return Response({
            'success': True,
            'message': f'Configuración creada exitosamente para store: {store_id}',
            'data': serializer.data
        })
        
    except Exception as e:
        return Response(
            {'error': f'Error creando configuración: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@tiene_permiso("inventory.")
def tiendanube_webhook_handler(request):
    """Maneja webhooks de TiendaNube"""
    try:
        # Verificar que es un webhook válido de TiendaNube
        event_type = request.headers.get('X-Tiendanube-Event')
        store_id = request.headers.get('X-Tiendanube-Store')
        
        if not event_type or not store_id:
            return Response(
                {'error': 'Headers de TiendaNube no encontrados'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que la configuración coincide
        config = TiendaNubeConfig.objects.filter(store_id=store_id).first()
        if not config:
            return Response(
                {'error': 'Configuración no encontrada para esta tienda'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Procesar webhook
        service = TiendaNubeService(config)
        success, message = service.handle_webhook(request.data)
        
        if success:
            return Response({'success': True, 'message': message})
        else:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
    except Exception as e:
        return Response(
            {'error': f'Error procesando webhook: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@tiene_permiso("inventory.")
def tiendanube_dashboard_data(request):
    """Obtiene datos para el dashboard de TiendaNube"""
    try:
        # Get configuration
        config = TiendaNubeConfig.objects.first()
        if not config:
            return Response({
                'configured': False,
                'message': 'No TiendaNube configuration found'
            })
        
        service = TiendaNubeService(config)
        sync_status = service.get_sync_status()
        
        # Get additional statistics
        total_products = Product.objects.count()
        products_with_tn = Product.objects.filter(tiendanube_id__isnull=False).count()
        
        # Get recent stock movements
        from ..models import StockMove
        recent_moves = StockMove.objects.filter(
            product__tiendanube_id__isnull=False
        ).order_by('-timestamp')[:10]
        
        # Get products with low stock
        from ..models import StockQuant
        low_stock_products = StockQuant.objects.filter(
            product__tiendanube_id__isnull=False,
            quantity__lte=10
        ).select_related('product', 'location')[:10]
        
        # Prepare response data
        dashboard_data = {
            'configured': True,
            'sync_status': sync_status,
            'statistics': {
                'total_products': total_products,
                'products_with_tiendanube': products_with_tn,
                'sync_percentage': (products_with_tn / total_products * 100) if total_products > 0 else 0
            },
            'recent_moves': [
                {
                    'product_name': move.product.name,
                    'quantity': move.quantity,
                    'timestamp': move.timestamp,
                    'move_type': move.move_type
                }
                for move in recent_moves
            ],
            'low_stock_products': [
                {
                    'product_name': quant.product.name,
                    'location_name': quant.location.name,
                    'quantity': quant.quantity
                }
                for quant in low_stock_products
            ]
        }
        
        return Response(dashboard_data)
        
    except Exception as e:
        return Response(
            {'error': f'Error obteniendo datos del dashboard: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 