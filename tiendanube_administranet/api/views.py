"""
Vistas de API para la integración Tiendanube-AdministraNET.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from ..models import (
    TiendanubeConfig, AdministraNETConfig, CustomerMapping, 
    SyncLog, ProductMapping, OrderMapping
)
from ..services.sync_service import TiendanubeAdministraNETSyncService
from .serializers import (
    TiendanubeConfigSerializer, AdministraNETConfigSerializer,
    CustomerMappingSerializer, SyncLogSerializer,
    ProductMappingSerializer, OrderMappingSerializer
)

logger = logging.getLogger(__name__)


class TiendanubeConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet para configuraciones de Tiendanube.
    """
    queryset = TiendanubeConfig.objects.all()
    serializer_class = TiendanubeConfigSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar por configuración activa si se solicita."""
        queryset = super().get_queryset()
        active_only = self.request.query_params.get('active_only', 'false').lower() == 'true'
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Probar conexión con Tiendanube."""
        config = self.get_object()
        
        try:
            from ..services.tiendanube_service import TiendanubeService
            service = TiendanubeService(config)
            result = service.test_connection()
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Error probando conexión Tiendanube: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdministraNETConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet para configuraciones de AdministraNET.
    """
    queryset = AdministraNETConfig.objects.all()
    serializer_class = AdministraNETConfigSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar por configuración activa si se solicita."""
        queryset = super().get_queryset()
        active_only = self.request.query_params.get('active_only', 'false').lower() == 'true'
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Probar conexión con AdministraNET."""
        config = self.get_object()
        
        try:
            from ..services.adminet_service import AdministraNETService
            service = AdministraNETService(config)
            result = service.test_connection()
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Error probando conexión AdministraNET: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomerMappingViewSet(viewsets.ModelViewSet):
    """
    ViewSet para mapeos de clientes.
    """
    queryset = CustomerMapping.objects.all()
    serializer_class = CustomerMappingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Aplicar filtros de búsqueda."""
        queryset = super().get_queryset()
        
        # Filtros
        search = self.request.query_params.get('search')
        sync_status = self.request.query_params.get('sync_status')
        sync_direction = self.request.query_params.get('sync_direction')
        sync_enabled = self.request.query_params.get('sync_enabled')
        
        if search:
            queryset = queryset.filter(
                tiendanube_email__icontains=search
            ) | queryset.filter(
                tiendanube_name__icontains=search
            ) | queryset.filter(
                adminet_nombre__icontains=search
            )
        
        if sync_status:
            queryset = queryset.filter(sync_status=sync_status)
        
        if sync_direction:
            queryset = queryset.filter(sync_direction=sync_direction)
        
        if sync_enabled is not None:
            sync_enabled_bool = sync_enabled.lower() == 'true'
            queryset = queryset.filter(sync_enabled=sync_enabled_bool)
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Sincronizar un mapeo específico."""
        mapping = self.get_object()
        
        try:
            sync_service = TiendanubeAdministraNETSyncService()
            
            direction = request.data.get('direction', 'auto')
            
            if direction == 'to_tiendanube':
                success, message = sync_service.sync_customer_to_tiendanube(mapping)
            elif direction == 'to_adminet':
                success, message = sync_service.sync_customer_to_adminet(mapping)
            else:
                # Sincronización automática
                if mapping.sync_direction == 'tiendanube_to_adminet':
                    success, message = sync_service.sync_customer_to_adminet(mapping)
                elif mapping.sync_direction == 'adminet_to_tiendanube':
                    success, message = sync_service.sync_customer_to_tiendanube(mapping)
                else:
                    # Bidireccional
                    success1, message1 = sync_service.sync_customer_to_adminet(mapping)
                    success2, message2 = sync_service.sync_customer_to_tiendanube(mapping)
                    success = success1 and success2
                    message = f"Adminet: {message1}, Tiendanube: {message2}"
            
            return Response({
                'success': success,
                'message': message,
                'mapping_id': mapping.id
            })
            
        except Exception as e:
            logger.error(f"Error sincronizando mapeo {mapping.id}: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def bulk_sync(self, request):
        """Sincronización masiva de mapeos."""
        try:
            mapping_ids = request.data.get('mapping_ids', [])
            direction = request.data.get('direction', 'auto')
            
            if not mapping_ids:
                return Response({
                    'success': False,
                    'error': 'No se proporcionaron IDs de mapeos'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            sync_service = TiendanubeAdministraNETSyncService()
            results = []
            
            for mapping_id in mapping_ids:
                try:
                    mapping = CustomerMapping.objects.get(id=mapping_id)
                    
                    if direction == 'to_tiendanube':
                        success, message = sync_service.sync_customer_to_tiendanube(mapping)
                    elif direction == 'to_adminet':
                        success, message = sync_service.sync_customer_to_adminet(mapping)
                    else:
                        # Sincronización automática
                        if mapping.sync_direction == 'tiendanube_to_adminet':
                            success, message = sync_service.sync_customer_to_adminet(mapping)
                        elif mapping.sync_direction == 'adminet_to_tiendanube':
                            success, message = sync_service.sync_customer_to_tiendanube(mapping)
                        else:
                            # Bidireccional
                            success1, message1 = sync_service.sync_customer_to_adminet(mapping)
                            success2, message2 = sync_service.sync_customer_to_tiendanube(mapping)
                            success = success1 and success2
                            message = f"Adminet: {message1}, Tiendanube: {message2}"
                    
                    results.append({
                        'mapping_id': mapping_id,
                        'success': success,
                        'message': message
                    })
                    
                except CustomerMapping.DoesNotExist:
                    results.append({
                        'mapping_id': mapping_id,
                        'success': False,
                        'message': 'Mapeo no encontrado'
                    })
                except Exception as e:
                    results.append({
                        'mapping_id': mapping_id,
                        'success': False,
                        'message': str(e)
                    })
            
            success_count = sum(1 for r in results if r['success'])
            failed_count = len(results) - success_count
            
            return Response({
                'success': True,
                'results': results,
                'summary': {
                    'total': len(results),
                    'success': success_count,
                    'failed': failed_count
                }
            })
            
        except Exception as e:
            logger.error(f"Error en sincronización masiva: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para logs de sincronización (solo lectura).
    """
    queryset = SyncLog.objects.all()
    serializer_class = SyncLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Aplicar filtros de búsqueda."""
        queryset = super().get_queryset()
        
        # Filtros
        sync_type = self.request.query_params.get('sync_type')
        status_filter = self.request.query_params.get('status')
        platform = self.request.query_params.get('platform')
        mapping_id = self.request.query_params.get('mapping_id')
        
        if sync_type:
            queryset = queryset.filter(sync_type=sync_type)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if platform:
            queryset = queryset.filter(platform=platform)
        
        if mapping_id:
            queryset = queryset.filter(mapping_id=mapping_id)
        
        return queryset.order_by('-started_at')


class StatisticsView(APIView):
    """
    Vista para obtener estadísticas de sincronización.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Obtener estadísticas actualizadas."""
        try:
            sync_service = TiendanubeAdministraNETSyncService()
            statistics = sync_service.get_sync_statistics()
            
            return Response({
                'success': True,
                'statistics': statistics,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncFromTiendanubeView(APIView):
    """
    Vista para sincronizar clientes desde Tiendanube.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Ejecutar sincronización desde Tiendanube."""
        try:
            limit = int(request.data.get('limit', 100))
            offset = int(request.data.get('offset', 0))
            
            sync_service = TiendanubeAdministraNETSyncService()
            success_count, failed_count = sync_service.sync_customers_from_tiendanube(limit, offset)
            
            return Response({
                'success': True,
                'message': f'Sincronizados {success_count} clientes, {failed_count} fallidos',
                'success_count': success_count,
                'failed_count': failed_count,
                'total_processed': success_count + failed_count,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error en sincronización desde Tiendanube: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncFromAdminetView(APIView):
    """
    Vista para sincronizar clientes desde AdministraNET.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Ejecutar sincronización desde AdministraNET."""
        try:
            limit = int(request.data.get('limit', 100))
            offset = int(request.data.get('offset', 0))
            
            sync_service = TiendanubeAdministraNETSyncService()
            success_count, failed_count = sync_service.sync_customers_from_adminet(limit, offset)
            
            return Response({
                'success': True,
                'message': f'Sincronizados {success_count} clientes, {failed_count} fallidos',
                'success_count': success_count,
                'failed_count': failed_count,
                'total_processed': success_count + failed_count,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error en sincronización desde AdministraNET: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestConnectionsView(APIView):
    """
    Vista para probar conexiones con ambas plataformas.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Probar conexiones con ambas plataformas."""
        try:
            sync_service = TiendanubeAdministraNETSyncService()
            result = sync_service.test_connections()
            
            return Response({
                'success': True,
                'connections': result,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error probando conexiones: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 