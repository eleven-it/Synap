"""
Vistas para validación y corrección de inconsistencias de datos.
"""

import json
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone

from ..models import TiendanubeConfig, AdministraNETConfig
from ..services.periodic_sync_service import PeriodicSyncService

logger = logging.getLogger(__name__)


class DataValidationView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista para validación de consistencia de datos.
    """
    template_name = 'tiendanube_administranet/validation/data_validation.html'
    permission_required = 'tiendanube_administranet.view_customermapping'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener configuraciones
        tiendanube_config = TiendanubeConfig.objects.first()
        adminet_config = AdministraNETConfig.objects.first()
        
        context['tiendanube_config'] = tiendanube_config
        context['adminet_config'] = adminet_config
        
        # Estadísticas básicas
        from ..models import CustomerMapping
        total_mappings = CustomerMapping.objects.filter(
            tiendanube_id__isnull=False,
            adminet_codigo__isnull=False
        ).count()
        
        context['stats'] = {
            'total_mappings': total_mappings,
            'has_configs': bool(tiendanube_config and adminet_config)
        }
        
        return context


class ValidateDataAjaxView(LoginRequiredMixin, View):
    """
    Vista AJAX para validar consistencia de datos.
    """
    permission_required = 'tiendanube_administranet.view_customermapping'
    
    def post(self, request, *args, **kwargs):
        """
        Ejecutar validación de consistencia de datos.
        """
        try:
            # Obtener configuraciones
            tiendanube_config = TiendanubeConfig.objects.first()
            adminet_config = AdministraNETConfig.objects.first()
            
            if not tiendanube_config or not adminet_config:
                return JsonResponse({
                    'success': False,
                    'message': 'Configuraciones de TiendaNube o AdministraNET no encontradas'
                })
            
            # Crear servicio de validación
            sync_service = PeriodicSyncService(tiendanube_config, adminet_config)
            
            # Ejecutar validación
            result = sync_service.validate_customer_data_consistency()
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Error en validación AJAX: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Error en validación: {str(e)}'
            })


class FixInconsistenciesAjaxView(LoginRequiredMixin, View):
    """
    Vista AJAX para corregir inconsistencias.
    """
    permission_required = 'tiendanube_administranet.change_customermapping'
    
    def post(self, request, *args, **kwargs):
        """
        Corregir inconsistencias de datos.
        """
        try:
            data = json.loads(request.body)
            inconsistencies = data.get('inconsistencies', [])
            prefer_tiendanube = data.get('prefer_tiendanube', True)
            
            if not inconsistencies:
                return JsonResponse({
                    'success': False,
                    'message': 'No se proporcionaron inconsistencias para corregir'
                })
            
            # Obtener configuraciones
            tiendanube_config = TiendanubeConfig.objects.first()
            adminet_config = AdministraNETConfig.objects.first()
            
            if not tiendanube_config or not adminet_config:
                return JsonResponse({
                    'success': False,
                    'message': 'Configuraciones de TiendaNube o AdministraNET no encontradas'
                })
            
            # Crear servicio de validación
            sync_service = PeriodicSyncService(tiendanube_config, adminet_config)
            
            # Corregir inconsistencias
            result = sync_service.fix_customer_inconsistencies(
                inconsistencies,
                prefer_tiendanube=prefer_tiendanube
            )
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Error corrigiendo inconsistencias: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Error corrigiendo inconsistencias: {str(e)}'
            })


class SyncUpdatesAjaxView(LoginRequiredMixin, View):
    """
    Vista AJAX para sincronización periódica de actualizaciones.
    """
    permission_required = 'tiendanube_administranet.change_customermapping'
    
    def post(self, request, *args, **kwargs):
        """
        Ejecutar sincronización periódica de actualizaciones.
        """
        try:
            data = json.loads(request.body)
            hours_back = data.get('hours_back', 24)
            
            # Obtener configuraciones
            tiendanube_config = TiendanubeConfig.objects.first()
            adminet_config = AdministraNETConfig.objects.first()
            
            if not tiendanube_config or not adminet_config:
                return JsonResponse({
                    'success': False,
                    'message': 'Configuraciones de TiendaNube o AdministraNET no encontradas'
                })
            
            # Crear servicio de sincronización
            sync_service = PeriodicSyncService(tiendanube_config, adminet_config)
            
            # Ejecutar sincronización
            result = sync_service.sync_customer_updates_from_tiendanube(hours_back=hours_back)
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Error en sincronización AJAX: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            })



