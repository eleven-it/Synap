"""
Vistas para la administración de módulos del sistema
"""

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, UpdateView, DetailView
from django.views import View
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.db import transaction

from core.models import ModuleConfig
from core.module_manager import module_manager
from core.dependency_manager import dependency_manager
from core.menu_manager import menu_manager


class ModuleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista para listar y gestionar módulos"""
    model = ModuleConfig
    template_name = 'core/module_list.html'
    context_object_name = 'modules'
    permission_required = 'core.change_moduleconfig'
    
    def get_queryset(self):
        return ModuleConfig.objects.all().order_by('is_core', 'is_required', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Agregar información adicional para cada módulo
        for module in context['modules']:
            module.can_activate = module_manager.can_activate_module(module.name)
            module.can_deactivate = module_manager.can_deactivate_module(module.name)
            module.dependencies = module_manager.get_module_dependencies(module.name)
            module.dependents = module_manager.get_module_dependents(module.name)
            module.missing_dependencies = module_manager._get_missing_dependencies(module.name)
        
        # Resumen del sistema
        context['summary'] = module_manager.get_modules_summary()
        context['module_summary'] = module_manager.get_modules_summary()
        
        # Variable para mostrar la tarjeta especial solo a administradores
        user = self.request.user
        context['is_admin_user'] = user.is_superuser or user.groups.filter(name__iexact='administrador').exists()
        
        return context


class ModuleDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Vista para mostrar detalles de un módulo"""
    model = ModuleConfig
    template_name = 'core/module_detail.html'
    context_object_name = 'module'
    permission_required = 'core.view_moduleconfig'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Información del módulo
        module_name = self.object.name
        context['module_status'] = module_manager.get_module_status(module_name)
        context['dependency_tree'] = dependency_manager.get_dependency_tree(module_name)
        context['impact_analysis'] = dependency_manager.get_impact_analysis(module_name)
        
        # Información de menú
        context['menu_items'] = menu_manager.get_module_menu_items(module_name, self.request.user)
        context['menu_validation'] = menu_manager.validate_menu_config(module_name)
        
        return context


class ModuleToggleView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para activar/desactivar módulos"""
    permission_required = 'core.change_moduleconfig'
    
    def post(self, request, module_name):
        action = request.POST.get('action')
        
        if action == 'activate':
            success, message = module_manager.activate_module(module_name, user=request.user)
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        
        elif action == 'deactivate':
            success, message = module_manager.deactivate_module(module_name, user=request.user)
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        
        else:
            messages.error(request, _('Invalid action specified.'))
        
        return redirect('core:module_list')


class ModuleBulkActionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para acciones masivas en módulos"""
    permission_required = 'core.change_moduleconfig'
    
    def post(self, request):
        action = request.POST.get('action')
        modules = request.POST.getlist('modules')
        
        if not modules:
            messages.error(request, _('No modules selected.'))
            return redirect('core:module_list')
        
        if action == 'activate':
            self.activate_modules(request, modules)
        elif action == 'deactivate':
            self.deactivate_modules(request, modules)
        else:
            messages.error(request, _('Invalid action specified.'))
        
        return redirect('core:module_list')
    
    def activate_modules(self, request, modules):
        """Activa múltiples módulos"""
        success_count = 0
        error_count = 0
        
        # Obtener orden de activación
        activation_order = dependency_manager.get_activation_order(modules)
        
        for module in activation_order:
            if module in modules:
                success, message = module_manager.activate_module(module, user=request.user)
                if success:
                    success_count += 1
                else:
                    error_count += 1
        
        if success_count > 0:
            messages.success(request, f'{success_count} modules activated successfully.')
        if error_count > 0:
            messages.error(request, f'{error_count} modules could not be activated.')
    
    def deactivate_modules(self, request, modules):
        """Desactiva múltiples módulos"""
        success_count = 0
        error_count = 0
        
        # Obtener orden de desactivación
        deactivation_order = dependency_manager.get_deactivation_order(modules)
        
        for module in deactivation_order:
            if module in modules:
                success, message = module_manager.deactivate_module(module, user=request.user)
                if success:
                    success_count += 1
                else:
                    error_count += 1
        
        if success_count > 0:
            messages.success(request, f'{success_count} modules deactivated successfully.')
        if error_count > 0:
            messages.error(request, f'{error_count} modules could not be deactivated.')


class ModuleSettingsView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para configurar módulos"""
    model = ModuleConfig
    template_name = 'core/module_settings.html'
    fields = ['settings']
    permission_required = 'core.change_moduleconfig'
    
    def get_success_url(self):
        return reverse('core:module_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener esquema de configuración del módulo
        context['settings_schema'] = self.object.get_settings_schema()
        
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Module settings updated successfully.'))
        return super().form_valid(form)


class ModuleDependencyView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para mostrar dependencias de módulos"""
    permission_required = 'core.view_moduleconfig'
    
    def get(self, request):
        context = {
            'dependency_graph': dependency_manager.get_dependency_graph(),
            'circular_dependencies': dependency_manager.get_circular_dependencies(),
            'modules': ModuleConfig.objects.all()
        }
        return render(request, 'core/module_dependencies.html', context)


class ModuleValidationView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para validar módulos"""
    permission_required = 'core.view_moduleconfig'
    
    def get(self, request):
        validation_results = {
            'dependencies': self.validate_dependencies(),
            'menus': self.validate_menus(),
            'modules': self.validate_modules()
        }
        
        return render(request, 'core/module_validation.html', {
            'validation_results': validation_results
        })
    
    def validate_dependencies(self):
        """Valida las dependencias de todos los módulos"""
        results = []
        
        # Verificar dependencias circulares
        if dependency_manager.check_circular_dependencies():
            results.append({
                'type': 'error',
                'message': 'Circular dependencies detected',
                'details': dependency_manager.get_circular_dependencies()
            })
        else:
            results.append({
                'type': 'success',
                'message': 'No circular dependencies found'
            })
        
        # Validar dependencias individuales
        for module_name in module_manager.get_all_modules():
            is_valid, message = dependency_manager.validate_dependencies(module_name)
            results.append({
                'type': 'success' if is_valid else 'error',
                'module': module_name,
                'message': message
            })
        
        return results
    
    def validate_menus(self):
        """Valida las configuraciones de menú"""
        results = []
        
        for module_name in module_manager.get_active_modules():
            is_valid, message = menu_manager.validate_menu_config(module_name)
            results.append({
                'type': 'success' if is_valid else 'error',
                'module': module_name,
                'message': message
            })
        
        return results
    
    def validate_modules(self):
        """Valida la configuración general de módulos"""
        results = []
        
        # Verificar módulos activos
        active_modules = module_manager.get_active_modules()
        
        for module_name in active_modules:
            missing_deps = dependency_manager.get_missing_dependencies(
                module_name, active_modules
            )
            
            if missing_deps:
                results.append({
                    'type': 'warning',
                    'module': module_name,
                    'message': f'Missing dependencies: {", ".join(missing_deps)}'
                })
            else:
                results.append({
                    'type': 'success',
                    'module': module_name,
                    'message': 'All dependencies satisfied'
                })
        
        return results


class ModuleAPIView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista API para gestión de módulos"""
    permission_required = 'core.change_moduleconfig'
    
    def get(self, request):
        """Obtiene información de módulos"""
        action = request.GET.get('action')
        
        if action == 'list':
            return self.get_module_list()
        elif action == 'status':
            return self.get_module_status()
        elif action == 'dependencies':
            return self.get_dependencies()
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
    
    def post(self, request):
        """Ejecuta acciones en módulos"""
        action = request.POST.get('action')
        
        if action == 'activate':
            return self.activate_module(request)
        elif action == 'deactivate':
            return self.deactivate_module(request)
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
    
    def get_module_list(self):
        """Obtiene lista de módulos"""
        modules = []
        for module in ModuleConfig.objects.all():
            modules.append({
                'name': module.name,
                'display_name': module.display_name,
                'is_active': module.is_active,
                'is_core': module.is_core,
                'is_required': module.is_required,
                'can_activate': module_manager.can_activate_module(module.name),
                'can_deactivate': module_manager.can_deactivate_module(module.name),
            })
        
        return JsonResponse({'modules': modules})
    
    def get_module_status(self):
        """Obtiene estado de módulos"""
        summary = module_manager.get_modules_summary()
        return JsonResponse(summary)
    
    def get_dependencies(self):
        """Obtiene información de dependencias"""
        module_name = self.request.GET.get('module')
        if not module_name:
            return JsonResponse({'error': 'Module name required'}, status=400)
        
        dependency_tree = dependency_manager.get_dependency_tree(module_name)
        return JsonResponse({'dependencies': dependency_tree})
    
    def activate_module(self, request):
        """Activa un módulo"""
        module_name = request.POST.get('module')
        if not module_name:
            return JsonResponse({'error': 'Module name required'}, status=400)
        
        success, message = module_manager.activate_module(module_name, user=request.user)
        return JsonResponse({
            'success': success,
            'message': message
        })
    
    def deactivate_module(self, request):
        """Desactiva un módulo"""
        module_name = request.POST.get('module')
        if not module_name:
            return JsonResponse({'error': 'Module name required'}, status=400)
        
        success, message = module_manager.deactivate_module(module_name, user=request.user)
        return JsonResponse({
            'success': success,
            'message': message
        }) 