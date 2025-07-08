"""
Vistas de administración para hooks del sistema Synap
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from core.models import ModuleConfig
from core.hook_manager import hook_manager
from core.hook_registry import hook_registry
from core.event_dispatcher import event_dispatcher
from core.event_listeners import event_listener_manager
from core.module_manager import module_manager


@login_required
def hook_dashboard(request):
    """Dashboard principal de hooks"""
    # Estadísticas generales
    hook_stats = hook_manager.get_hook_info()
    event_stats = event_dispatcher.get_event_statistics()
    listener_stats = event_listener_manager.get_listener_stats()
    
    # Módulos con hooks
    modules_with_hooks = []
    for module_name in module_manager.get_active_modules():
        try:
            hook_config = hook_manager.get_module_hooks(module_name)
            if hook_config:
                modules_with_hooks.append({
                    'name': module_name,
                    'hook_count': len(hook_config),
                    'hooks': list(hook_config.keys())
                })
        except:
            pass
    
    context = {
        'hook_stats': hook_stats,
        'event_stats': event_stats,
        'listener_stats': listener_stats,
        'modules_with_hooks': modules_with_hooks,
        'total_modules': len(modules_with_hooks)
    }
    
    return render(request, 'core/hook_dashboard.html', context)


@login_required
def hook_list(request):
    """Lista todos los hooks registrados"""
    # Obtener todos los hooks
    all_hooks = hook_manager.get_all_hooks()
    
    # Filtros
    search = request.GET.get('search', '')
    module_filter = request.GET.get('module', '')
    category_filter = request.GET.get('category', '')
    
    # Aplicar filtros
    filtered_hooks = []
    for hook_name, hook_info in all_hooks.items():
        # Filtro de búsqueda
        if search and search.lower() not in hook_name.lower() and search.lower() not in hook_info.get('description', '').lower():
            continue
        
        # Filtro de módulo
        if module_filter and module_filter not in hook_info.get('modules', []):
            continue
        
        # Filtro de categoría
        if category_filter:
            found_category = False
            for registration in hook_info.get('registrations', []):
                if registration.get('metadata', {}).get('category') == category_filter:
                    found_category = True
                    break
            if not found_category:
                continue
        
        filtered_hooks.append({
            'name': hook_name,
            'info': hook_info
        })
    
    # Ordenar por nombre
    filtered_hooks.sort(key=lambda x: x['name'])
    
    # Paginación
    paginator = Paginator(filtered_hooks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener módulos y categorías para filtros
    modules = list(set([module['name'] for module in module_manager.get_modules_summary()['modules']]))
    categories = ['sales', 'purchases', 'inventory', 'accounting', 'core']
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'module_filter': module_filter,
        'category_filter': category_filter,
        'modules': modules,
        'categories': categories,
        'total_hooks': len(all_hooks),
        'filtered_hooks': len(filtered_hooks)
    }
    
    return render(request, 'core/hook_list.html', context)


@login_required
def hook_detail(request, hook_name):
    """Detalle de un hook específico"""
    # Obtener información del hook
    hook_info = hook_manager.get_hook_info(hook_name)
    
    if not hook_info:
        messages.error(request, f'Hook "{hook_name}" no encontrado')
        return redirect('core:hook_list')
    
    # Obtener estadísticas de ejecución
    execution_stats = hook_manager.get_hook_execution_stats(hook_name)
    
    # Obtener dependencias
    dependencies = hook_registry.hook_dependencies.get(hook_name, [])
    
    # Obtener validadores
    validator = hook_registry.hook_validators.get(hook_name)
    
    context = {
        'hook_name': hook_name,
        'hook_info': hook_info,
        'execution_stats': execution_stats,
        'dependencies': dependencies,
        'validator': validator,
        'has_validator': validator is not None
    }
    
    return render(request, 'core/hook_detail.html', context)


@login_required
def event_list(request):
    """Lista todos los eventos del sistema"""
    # Obtener estadísticas de eventos
    event_stats = event_dispatcher.get_event_statistics()
    
    # Obtener eventos recientes
    recent_events = event_dispatcher.get_recent_events(50)
    
    # Filtros
    search = request.GET.get('search', '')
    priority_filter = request.GET.get('priority', '')
    
    # Aplicar filtros a eventos recientes
    filtered_events = []
    for event in recent_events:
        # Filtro de búsqueda
        if search and search.lower() not in event['name'].lower():
            continue
        
        # Filtro de prioridad
        if priority_filter and event.get('priority') != priority_filter:
            continue
        
        filtered_events.append(event)
    
    # Paginación
    paginator = Paginator(filtered_events, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Prioridades disponibles
    priorities = ['low', 'normal', 'high', 'critical']
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'priority_filter': priority_filter,
        'priorities': priorities,
        'event_stats': event_stats,
        'total_events': len(recent_events),
        'filtered_events': len(filtered_events)
    }
    
    return render(request, 'core/event_list.html', context)


@login_required
def event_detail(request, event_name):
    """Detalle de un evento específico"""
    # Obtener información del evento
    event_info = event_dispatcher.get_event_info(event_name)
    
    # Obtener listeners del evento
    listeners = event_listener_manager.get_listener_details(event_name)
    
    # Obtener hooks relacionados
    related_hooks = []
    for hook_name in hook_manager.hooks.keys():
        if event_name in hook_name or hook_name in event_name:
            related_hooks.append(hook_name)
    
    # Obtener eventos recientes de este tipo
    recent_events = []
    for event in event_dispatcher.get_recent_events(100):
        if event['name'] == event_name:
            recent_events.append(event)
    
    context = {
        'event_name': event_name,
        'event_info': event_info,
        'listeners': listeners,
        'related_hooks': related_hooks,
        'recent_events': recent_events[:10]  # Solo los 10 más recientes
    }
    
    return render(request, 'core/event_detail.html', context)


@login_required
def module_hooks(request, module_name):
    """Hooks de un módulo específico"""
    # Verificar que el módulo existe
    module = get_object_or_404(ModuleConfig, name=module_name)
    
    # Obtener hooks del módulo
    module_hooks = hook_registry.get_module_hooks(module_name)
    
    # Obtener configuración de hooks del módulo
    try:
        hook_config = hook_manager.get_module_hooks(module_name)
    except:
        hook_config = {}
    
    # Obtener estadísticas del módulo
    module_summary = hook_registry.get_module_hooks_summary(module_name)
    
    # Obtener listeners del módulo
    module_listeners = []
    for event_name, listeners in event_listener_manager.listeners.items():
        for listener in listeners:
            if listener.module_name == module_name:
                module_listeners.append({
                    'event_name': event_name,
                    'listener': listener.get_stats()
                })
    
    context = {
        'module': module,
        'module_hooks': module_hooks,
        'hook_config': hook_config,
        'module_summary': module_summary,
        'module_listeners': module_listeners
    }
    
    return render(request, 'core/module_hooks.html', context)


@login_required
def hook_validation(request):
    """Página de validación de hooks"""
    # Validar hooks
    validation_results = hook_manager.validate_hooks()
    
    # Agrupar resultados por tipo
    success_results = [r for r in validation_results if r['type'] == 'success']
    warning_results = [r for r in validation_results if r['type'] == 'warning']
    error_results = [r for r in validation_results if r['type'] == 'error']
    
    # Estadísticas de validación
    validation_stats = {
        'total': len(validation_results),
        'success': len(success_results),
        'warnings': len(warning_results),
        'errors': len(error_results)
    }
    
    context = {
        'validation_results': validation_results,
        'success_results': success_results,
        'warning_results': warning_results,
        'error_results': error_results,
        'validation_stats': validation_stats
    }
    
    return render(request, 'core/hook_validation.html', context)


@login_required
def reload_hooks(request):
    """Recarga todos los hooks"""
    if request.method == 'POST':
        try:
            # Recargar hooks
            hook_manager.reload_hooks()
            hook_registry.reload_registry()
            event_listener_manager.reload_listeners()
            
            messages.success(request, 'Hooks recargados exitosamente')
        except Exception as e:
            messages.error(request, f'Error al recargar hooks: {e}')
        
        return redirect('core:hook_dashboard')
    
    return render(request, 'core/reload_hooks.html')


@login_required
def test_hooks(request):
    """Página para probar hooks"""
    if request.method == 'POST':
        test_type = request.POST.get('test_type')
        
        try:
            if test_type == 'register_examples':
                from core.examples.hook_examples import register_hook_examples
                register_hook_examples()
                messages.success(request, 'Ejemplos de hooks registrados exitosamente')
            
            elif test_type == 'unregister_examples':
                from core.examples.hook_examples import unregister_hook_examples
                unregister_hook_examples()
                messages.success(request, 'Ejemplos de hooks desregistrados exitosamente')
            
            elif test_type == 'test_events':
                from core.examples.hook_examples import demonstrate_event_dispatching
                demonstrate_event_dispatching()
                messages.success(request, 'Eventos de prueba ejecutados exitosamente')
            
        except Exception as e:
            messages.error(request, f'Error en la prueba: {e}')
        
        return redirect('core:test_hooks')
    
    # Obtener información de hooks registrados
    hook_stats = hook_manager.get_hook_info()
    event_stats = event_dispatcher.get_event_statistics()
    
    context = {
        'hook_stats': hook_stats,
        'event_stats': event_stats
    }
    
    return render(request, 'core/test_hooks.html', context)


# APIs para AJAX
@login_required
def hook_stats_api(request):
    """API para obtener estadísticas de hooks"""
    hook_stats = hook_manager.get_hook_info()
    event_stats = event_dispatcher.get_event_statistics()
    listener_stats = event_listener_manager.get_listener_stats()
    
    return JsonResponse({
        'hook_stats': hook_stats,
        'event_stats': event_stats,
        'listener_stats': listener_stats
    })


@login_required
def hook_execution_api(request, hook_name):
    """API para ejecutar un hook específico"""
    if request.method == 'POST':
        try:
            # Obtener datos del request
            data = request.POST.get('data', {})
            
            # Ejecutar hook
            results = hook_manager.execute_hook(hook_name, data)
            
            return JsonResponse({
                'success': True,
                'results': results
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
def event_dispatch_api(request):
    """API para disparar un evento"""
    if request.method == 'POST':
        try:
            # Obtener datos del request
            event_name = request.POST.get('event_name')
            event_data = request.POST.get('event_data', {})
            source_module = request.POST.get('source_module')
            priority = request.POST.get('priority', 'normal')
            
            # Disparar evento
            event_dispatcher.dispatch_event(
                event_name,
                event_data,
                source_module=source_module,
                priority=priority
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Evento {event_name} disparado exitosamente'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}) 