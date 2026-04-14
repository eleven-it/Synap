"""
Vistas para la configuración dinámica de mapeos de campos.
"""

from django.views.generic import TemplateView, ListView, UpdateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext as _

from ..models import FieldMappingConfig
from ..services.dynamic_mapping_service import DynamicMappingService, FieldMappingInitializer


class DynamicMappingConfigurationView(LoginRequiredMixin, TemplateView):
    """
    Vista principal para configurar mapeos dinámicos de campos.
    """
    template_name = 'tiendanube_administranet/dynamic_mapping_configuration.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener el tipo de mapeo desde la URL
        mapping_type = self.kwargs.get('mapping_type', 'customer')
        
        # Inicializar el servicio
        mapping_service = DynamicMappingService()
        
        # Obtener los mapeos
        mappings = mapping_service.get_field_mappings(mapping_type)
        
        context.update({
            'mapping_type': mapping_type,
            'mapping_type_display': dict(FieldMappingConfig.MappingType.choices)[mapping_type],
            'mappings': mappings,
            'mappable_fields': mapping_service.get_mappable_fields(mapping_type),
            'adminet_fields': mappings['adminet_fields'],
            'tiendanube_fields': mappings['tiendanube_fields'],
        })
        
        return context


class FieldMappingListView(LoginRequiredMixin, ListView):
    """
    Vista para listar todas las configuraciones de mapeo de campos.
    """
    model = FieldMappingConfig
    template_name = 'tiendanube_administranet/field_mapping_list.html'
    context_object_name = 'field_mappings'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        mapping_type = self.request.GET.get('mapping_type')
        field_type = self.request.GET.get('field_type')
        is_active = self.request.GET.get('is_active')
        
        if mapping_type:
            queryset = queryset.filter(mapping_type=mapping_type)
        if field_type:
            queryset = queryset.filter(field_type=field_type)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active == 'true')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'mapping_types': FieldMappingConfig.MappingType.choices,
            'field_types': FieldMappingConfig.FieldType.choices,
        })
        return context


class FieldMappingUpdateView(LoginRequiredMixin, UpdateView):
    """
    Vista para editar una configuración de mapeo de campo.
    """
    model = FieldMappingConfig
    template_name = 'tiendanube_administranet/field_mapping_form.html'
    fields = [
        'field_display_name', 'field_description', 'is_mappable', 
        'is_required', 'is_primary_key', 'mapped_to_field', 
        'mapping_notes', 'transformation_type', 'transformation_config',
        'is_active', 'display_order'
    ]
    success_url = reverse_lazy('tiendanube_administranet:field_mapping_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'mapping_types': FieldMappingConfig.MappingType.choices,
            'field_types': FieldMappingConfig.FieldType.choices,
            'transformation_types': [
                ('direct', 'Direct Mapping'),
                ('address_parse', 'Address Parsing'),
                ('name_mapping', 'Name Mapping'),
                ('custom', 'Custom Transformation'),
            ]
        })
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Field mapping configuration updated successfully.'))
        return super().form_valid(form)


class FieldMappingCreateView(LoginRequiredMixin, CreateView):
    """
    Vista para crear una nueva configuración de mapeo de campo.
    """
    model = FieldMappingConfig
    template_name = 'tiendanube_administranet/field_mapping_form.html'
    fields = [
        'mapping_type', 'field_type', 'field_name', 'field_display_name',
        'field_description', 'is_mappable', 'is_required', 'is_primary_key',
        'mapped_to_field', 'mapping_notes', 'transformation_type',
        'transformation_config', 'is_active', 'display_order'
    ]
    success_url = reverse_lazy('tiendanube_administranet:field_mapping_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'mapping_types': FieldMappingConfig.MappingType.choices,
            'field_types': FieldMappingConfig.FieldType.choices,
            'transformation_types': [
                ('direct', 'Direct Mapping'),
                ('address_parse', 'Address Parsing'),
                ('name_mapping', 'Name Mapping'),
                ('custom', 'Custom Transformation'),
            ]
        })
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Field mapping configuration created successfully.'))
        return super().form_valid(form)


def initialize_mappings_view(request):
    """
    Vista para inicializar los mapeos por defecto.
    """
    if request.method == 'POST':
        try:
            FieldMappingInitializer.initialize_all_mappings()
            messages.success(request, _('Field mappings initialized successfully.'))
        except Exception as e:
            messages.error(request, f'Error initializing mappings: {str(e)}')
        
        return redirect('tiendanube_administranet:field_mapping_list')
    
    return render(request, 'tiendanube_administranet/initialize_mappings.html')


def get_mappings_api(request, mapping_type):
    """
    API para obtener mapeos en formato JSON.
    """
    try:
        mapping_service = DynamicMappingService()
        mappings = mapping_service.get_field_mappings(mapping_type)
        
        return JsonResponse({
            'success': True,
            'mapping_type': mapping_type,
            'data': mappings
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def refresh_mappings_cache(request):
    """
    Vista para refrescar el cache de mapeos.
    """
    if request.method == 'POST':
        try:
            mapping_service = DynamicMappingService()
            mapping_type = request.POST.get('mapping_type')
            
            if mapping_type:
                mapping_service.refresh_mappings(mapping_type)
                messages.success(request, f'Cache refreshed for {mapping_type} mappings.')
            else:
                mapping_service.clear_cache()
                messages.success(request, 'All mapping caches cleared.')
                
        except Exception as e:
            messages.error(request, f'Error refreshing cache: {str(e)}')
        
        return redirect('tiendanube_administranet:field_mapping_list')
    
    return render(request, 'tiendanube_administranet/refresh_cache.html') 