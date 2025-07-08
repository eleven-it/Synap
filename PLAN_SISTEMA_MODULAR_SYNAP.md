# Plan de Sistema Modular Desacoplado para Synap

## 1. Visión General

### Objetivo
Implementar un sistema modular que permita:
- **Activación/Desactivación dinámica** de módulos sin afectar el core
- **Extensibilidad** para nuevos módulos futuros
- **Desacoplamiento** entre módulos y funcionalidades
- **Gestión centralizada** de dependencias y configuraciones
- **Escalabilidad** para sistemas multi-tenant

### Arquitectura Propuesta
```
Synap Core (Base)
├── Módulos Base (Siempre activos)
│   ├── core (Entidades fundamentales)
│   ├── login (Autenticación)
│   └── dashboard (Panel principal)
├── Módulos Opcionales (Activables/Desactivables)
│   ├── sales (Ventas)
│   ├── purchases (Compras)
│   ├── inventory (Inventario)
│   ├── accounting (Contabilidad)
│   └── tiendanube (Integración)
└── Módulos Futuros (Extensibles)
    ├── hr (Recursos Humanos)
    ├── manufacturing (Manufactura)
    ├── crm (Gestión de Relaciones)
    └── analytics (Analíticas)
```

## 2. Estructura del Sistema Modular

### 2.1 Core System (Módulo Base)
**Ubicación**: `core/`
**Estado**: Siempre activo
**Responsabilidades**:
- Entidades fundamentales (Empresa, Usuario, Rol, Permiso)
- Sistema de autenticación y autorización
- Gestión de contactos universales
- Configuración del sistema
- Middleware base
- Utilidades comunes

### 2.2 Módulos Opcionales

#### 2.2.1 Sales Module
**Ubicación**: `sales/`
**Dependencias**: `core`, `inventory` (opcional)
**Funcionalidades**:
- Gestión de clientes
- Órdenes de venta
- Facturación
- Gestión de pagos
- Reportes de ventas

#### 2.2.2 Purchases Module
**Ubicación**: `purchases/`
**Dependencias**: `core`, `inventory` (opcional)
**Funcionalidades**:
- Gestión de proveedores
- Órdenes de compra
- Recepción de mercancías
- Gestión de pagos a proveedores
- Reportes de compras

#### 2.2.3 Inventory Module
**Ubicación**: `inventory/`
**Dependencias**: `core`
**Funcionalidades**:
- Gestión de productos
- Control de stock
- Movimientos de inventario
- Ubicaciones y almacenes
- Reportes de inventario

#### 2.2.4 Accounting Module
**Ubicación**: `accounting/`
**Dependencias**: `core`, `sales` (opcional), `purchases` (opcional)
**Funcionalidades**:
- Plan de cuentas
- Asientos contables
- Impuestos y retenciones
- Estados financieros
- Reportes contables

#### 2.2.5 TiendaNube Integration
**Ubicación**: `tiendanube/`
**Dependencias**: `core`, `inventory`, `sales`
**Funcionalidades**:
- Sincronización de productos
- Sincronización de órdenes
- Gestión de inventario
- Reportes de e-commerce

## 3. Implementación del Sistema de Módulos

### 3.1 Gestión de Configuración de Módulos

#### 3.1.1 Modelo de Configuración
```python
# core/models/module_config.py
class ModuleConfig(models.Model):
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=20, default='1.0.0')
    is_active = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    dependencies = models.JSONField(default=list)
    settings = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Module Configuration'
        verbose_name_plural = 'Module Configurations'
```

#### 3.1.2 Configuración de Módulos
```python
# core/module_registry.py
MODULE_CONFIGS = {
    'sales': {
        'name': 'sales',
        'display_name': 'Sales Management',
        'description': 'Complete sales management system',
        'version': '1.0.0',
        'is_required': False,
        'dependencies': ['core'],
        'optional_dependencies': ['inventory'],
        'settings': {
            'enable_quotes': True,
            'enable_discounts': True,
            'tax_calculation': 'automatic',
        }
    },
    'purchases': {
        'name': 'purchases',
        'display_name': 'Purchase Management',
        'description': 'Complete purchase management system',
        'version': '1.0.0',
        'is_required': False,
        'dependencies': ['core'],
        'optional_dependencies': ['inventory'],
        'settings': {
            'enable_approvals': True,
            'enable_ratings': True,
        }
    },
    'inventory': {
        'name': 'inventory',
        'display_name': 'Inventory Management',
        'description': 'Complete inventory management system',
        'version': '1.0.0',
        'is_required': False,
        'dependencies': ['core'],
        'settings': {
            'enable_locations': True,
            'enable_lots': False,
            'enable_serial_numbers': False,
        }
    },
    'accounting': {
        'name': 'accounting',
        'display_name': 'Accounting System',
        'description': 'Complete accounting system',
        'version': '1.0.0',
        'is_required': False,
        'dependencies': ['core'],
        'optional_dependencies': ['sales', 'purchases'],
        'settings': {
            'currency': 'ARS',
            'fiscal_year_start': '01-01',
            'enable_tax_management': True,
        }
    },
    'tiendanube': {
        'name': 'tiendanube',
        'display_name': 'TiendaNube Integration',
        'description': 'E-commerce integration with TiendaNube',
        'version': '1.0.0',
        'is_required': False,
        'dependencies': ['core', 'inventory', 'sales'],
        'settings': {
            'sync_products': True,
            'sync_orders': True,
            'sync_inventory': True,
        }
    }
}
```

### 3.2 Sistema de Registro de Módulos

#### 3.2.1 Registry Manager
```python
# core/module_manager.py
class ModuleManager:
    """Gestor central de módulos del sistema"""
    
    def __init__(self):
        self.modules = {}
        self.active_modules = set()
        self.load_modules()
    
    def load_modules(self):
        """Carga la configuración de módulos desde la base de datos"""
        from .models import ModuleConfig
        
        for config in ModuleConfig.objects.filter(is_active=True):
            self.active_modules.add(config.name)
    
    def is_module_active(self, module_name):
        """Verifica si un módulo está activo"""
        return module_name in self.active_modules
    
    def get_active_modules(self):
        """Retorna la lista de módulos activos"""
        return list(self.active_modules)
    
    def activate_module(self, module_name):
        """Activa un módulo"""
        if self.can_activate_module(module_name):
            from .models import ModuleConfig
            config = ModuleConfig.objects.get(name=module_name)
            config.is_active = True
            config.save()
            self.active_modules.add(module_name)
            return True
        return False
    
    def deactivate_module(self, module_name):
        """Desactiva un módulo"""
        if self.can_deactivate_module(module_name):
            from .models import ModuleConfig
            config = ModuleConfig.objects.get(name=module_name)
            config.is_active = False
            config.save()
            self.active_modules.discard(module_name)
            return True
        return False
    
    def can_activate_module(self, module_name):
        """Verifica si se puede activar un módulo"""
        if module_name not in MODULE_CONFIGS:
            return False
        
        config = MODULE_CONFIGS[module_name]
        dependencies = config.get('dependencies', [])
        
        for dep in dependencies:
            if not self.is_module_active(dep):
                return False
        
        return True
    
    def can_deactivate_module(self, module_name):
        """Verifica si se puede desactivar un módulo"""
        # Verificar si otros módulos dependen de este
        for module, config in MODULE_CONFIGS.items():
            if module != module_name and self.is_module_active(module):
                dependencies = config.get('dependencies', [])
                if module_name in dependencies:
                    return False
        
        return True
    
    def get_module_dependencies(self, module_name):
        """Obtiene las dependencias de un módulo"""
        if module_name in MODULE_CONFIGS:
            return MODULE_CONFIGS[module_name].get('dependencies', [])
        return []
    
    def get_module_dependents(self, module_name):
        """Obtiene los módulos que dependen de este"""
        dependents = []
        for module, config in MODULE_CONFIGS.items():
            dependencies = config.get('dependencies', [])
            if module_name in dependencies:
                dependents.append(module)
        return dependents
```

### 3.3 Middleware de Módulos

#### 3.3.1 Module Middleware
```python
# core/middleware/module_middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from core.module_manager import ModuleManager

class ModuleMiddleware:
    """Middleware para verificar acceso a módulos activos"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.module_manager = ModuleManager()
    
    def __call__(self, request):
        # Verificar si la URL pertenece a un módulo inactivo
        path = request.path_info.lstrip('/')
        
        for module_name in MODULE_CONFIGS.keys():
            if path.startswith(f'{module_name}/') and not self.module_manager.is_module_active(module_name):
                messages.error(request, f'El módulo {module_name} no está activo.')
                return redirect('core:dashboard')
        
        response = self.get_response(request)
        return response
```

### 3.4 Gestión de URLs Dinámicas

#### 3.4.1 URL Registry
```python
# core/url_registry.py
class URLRegistry:
    """Registro dinámico de URLs por módulo"""
    
    def __init__(self):
        self.module_urls = {}
        self.load_module_urls()
    
    def load_module_urls(self):
        """Carga las URLs de los módulos activos"""
        from core.module_manager import ModuleManager
        module_manager = ModuleManager()
        
        for module_name in module_manager.get_active_modules():
            try:
                module_urls = self.get_module_urls(module_name)
                self.module_urls[module_name] = module_urls
            except ImportError:
                # Módulo no tiene URLs definidas
                pass
    
    def get_module_urls(self, module_name):
        """Obtiene las URLs de un módulo específico"""
        try:
            module = __import__(f'{module_name}.urls', fromlist=['urlpatterns'])
            return module.urlpatterns
        except ImportError:
            return []
    
    def get_all_urls(self):
        """Obtiene todas las URLs de módulos activos"""
        urls = []
        for module_urls in self.module_urls.values():
            urls.extend(module_urls)
        return urls
```

#### 3.4.2 URLs Dinámicas
```python
# django_project/urls.py
from django.contrib import admin
from django.urls import path, include
from core.url_registry import URLRegistry

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('login/', include('login.urls')),
    path('dashboard/', include('dashboard.urls')),
]

# Agregar URLs de módulos activos dinámicamente
url_registry = URLRegistry()
for module_name, module_urls in url_registry.module_urls.items():
    urlpatterns.append(path(f'{module_name}/', include(f'{module_name}.urls')))
```

### 3.5 Gestión de Menús Dinámicos

#### 3.5.1 Menu Manager
```python
# core/menu_manager.py
class MenuManager:
    """Gestor de menús dinámicos por módulo"""
    
    def __init__(self):
        self.module_menus = {}
        self.load_module_menus()
    
    def load_module_menus(self):
        """Carga los menús de los módulos activos"""
        from core.module_manager import ModuleManager
        module_manager = ModuleManager()
        
        for module_name in module_manager.get_active_modules():
            try:
                menu_config = self.get_module_menu(module_name)
                self.module_menus[module_name] = menu_config
            except ImportError:
                pass
    
    def get_module_menu(self, module_name):
        """Obtiene la configuración de menú de un módulo"""
        try:
            module = __import__(f'{module_name}.menu_config', fromlist=['MENU_CONFIG'])
            return module.MENU_CONFIG
        except ImportError:
            return {}
    
    def get_user_menu(self, user):
        """Obtiene el menú completo para un usuario"""
        menu = []
        
        # Menú base (siempre disponible)
        menu.extend(self.get_base_menu(user))
        
        # Menús de módulos activos
        for module_name, menu_config in self.module_menus.items():
            if self.user_has_module_access(user, module_name):
                menu.extend(self.filter_menu_by_permissions(menu_config, user))
        
        return menu
    
    def user_has_module_access(self, user, module_name):
        """Verifica si el usuario tiene acceso al módulo"""
        # Verificar permisos específicos del módulo
        return user.tiene_permiso_modulo(module_name)
    
    def filter_menu_by_permissions(self, menu_config, user):
        """Filtra el menú según los permisos del usuario"""
        filtered_menu = []
        
        for item in menu_config:
            if 'permission' in item:
                if user.tiene_permiso(item['permission']):
                    filtered_menu.append(item)
            else:
                filtered_menu.append(item)
        
        return filtered_menu
```

## 4. Configuración de Módulos

### 4.1 Estructura de Módulo
```
module_name/
├── __init__.py
├── apps.py
├── urls.py
├── menu_config.py
├── module_config.py
├── models/
├── views/
├── templates/
├── static/
├── migrations/
├── tests/
└── requirements.txt
```

### 4.2 Configuración de Módulo
```python
# sales/module_config.py
MODULE_CONFIG = {
    'name': 'sales',
    'display_name': 'Sales Management',
    'description': 'Complete sales management system',
    'version': '1.0.0',
    'author': 'Synap Team',
    'dependencies': ['core'],
    'optional_dependencies': ['inventory'],
    'settings_schema': {
        'enable_quotes': {
            'type': 'boolean',
            'default': True,
            'label': 'Enable Quotes',
            'description': 'Allow creation of sales quotes'
        },
        'enable_discounts': {
            'type': 'boolean',
            'default': True,
            'label': 'Enable Discounts',
            'description': 'Allow discounts on sales orders'
        },
        'tax_calculation': {
            'type': 'choice',
            'choices': ['automatic', 'manual'],
            'default': 'automatic',
            'label': 'Tax Calculation',
            'description': 'How to calculate taxes'
        }
    },
    'permissions': [
        'sales.view_client',
        'sales.add_client',
        'sales.change_client',
        'sales.delete_client',
        'sales.view_order',
        'sales.add_order',
        'sales.change_order',
        'sales.delete_order',
        'sales.view_invoice',
        'sales.add_invoice',
        'sales.change_invoice',
        'sales.delete_invoice',
    ],
    'hooks': [
        'sales.pre_order_create',
        'sales.post_order_create',
        'sales.pre_invoice_create',
        'sales.post_invoice_create',
    ]
}
```

### 4.3 Configuración de Menú
```python
# sales/menu_config.py
MENU_CONFIG = [
    {
        'name': 'sales',
        'label': 'Sales',
        'icon': 'fas fa-shopping-cart',
        'permission': 'sales.view_client',
        'children': [
            {
                'name': 'clients',
                'label': 'Clients',
                'url': 'sales:client_list',
                'permission': 'sales.view_client',
                'icon': 'fas fa-users'
            },
            {
                'name': 'orders',
                'label': 'Orders',
                'url': 'sales:order_list',
                'permission': 'sales.view_order',
                'icon': 'fas fa-file-invoice'
            },
            {
                'name': 'invoices',
                'label': 'Invoices',
                'url': 'sales:invoice_list',
                'permission': 'sales.view_invoice',
                'icon': 'fas fa-receipt'
            },
            {
                'name': 'reports',
                'label': 'Reports',
                'url': 'sales:reports_dashboard',
                'permission': 'sales.view_report',
                'icon': 'fas fa-chart-bar'
            }
        ]
    }
]
```

## 5. Sistema de Hooks y Eventos

### 5.1 Hook Manager
```python
# core/hook_manager.py
class HookManager:
    """Gestor de hooks y eventos entre módulos"""
    
    def __init__(self):
        self.hooks = {}
        self.load_hooks()
    
    def load_hooks(self):
        """Carga los hooks de los módulos activos"""
        from core.module_manager import ModuleManager
        module_manager = ModuleManager()
        
        for module_name in module_manager.get_active_modules():
            try:
                hooks = self.get_module_hooks(module_name)
                for hook_name, hook_func in hooks.items():
                    if hook_name not in self.hooks:
                        self.hooks[hook_name] = []
                    self.hooks[hook_name].append(hook_func)
            except ImportError:
                pass
    
    def get_module_hooks(self, module_name):
        """Obtiene los hooks de un módulo"""
        try:
            module = __import__(f'{module_name}.hooks', fromlist=['HOOKS'])
            return module.HOOKS
        except ImportError:
            return {}
    
    def execute_hook(self, hook_name, *args, **kwargs):
        """Ejecuta un hook específico"""
        if hook_name in self.hooks:
            results = []
            for hook_func in self.hooks[hook_name]:
                try:
                    result = hook_func(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    # Log error but continue
                    print(f"Error executing hook {hook_name}: {e}")
            return results
        return []
    
    def register_hook(self, hook_name, hook_func):
        """Registra un hook manualmente"""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        self.hooks[hook_name].append(hook_func)
```

### 5.2 Ejemplo de Hooks
```python
# sales/hooks.py
from core.models import Contact

def pre_order_create(sender, order, **kwargs):
    """Hook ejecutado antes de crear una orden"""
    # Verificar límite de crédito del cliente
    if order.client.credit_limit and order.total > order.client.credit_limit:
        raise ValidationError("Order exceeds client credit limit")

def post_order_create(sender, order, **kwargs):
    """Hook ejecutado después de crear una orden"""
    # Crear contacto automáticamente si no existe
    if not order.client.get_contacts():
        contact = Contact.objects.create(
            name=order.client.name,
            email=order.client.email,
            phone=order.client.phone
        )
        order.client.add_contact_relationship(contact, 'primary')

HOOKS = {
    'sales.pre_order_create': pre_order_create,
    'sales.post_order_create': post_order_create,
}
```

## 6. Gestión de Dependencias

### 6.1 Dependency Manager
```python
# core/dependency_manager.py
class DependencyManager:
    """Gestor de dependencias entre módulos"""
    
    def __init__(self):
        self.dependencies = {}
        self.load_dependencies()
    
    def load_dependencies(self):
        """Carga las dependencias de todos los módulos"""
        for module_name, config in MODULE_CONFIGS.items():
            self.dependencies[module_name] = {
                'required': config.get('dependencies', []),
                'optional': config.get('optional_dependencies', [])
            }
    
    def get_dependency_tree(self, module_name):
        """Obtiene el árbol de dependencias de un módulo"""
        tree = {'module': module_name, 'dependencies': []}
        
        if module_name in self.dependencies:
            for dep in self.dependencies[module_name]['required']:
                tree['dependencies'].append(self.get_dependency_tree(dep))
        
        return tree
    
    def get_activation_order(self, modules_to_activate):
        """Obtiene el orden correcto para activar módulos"""
        order = []
        visited = set()
        
        def visit(module):
            if module in visited:
                return
            visited.add(module)
            
            if module in self.dependencies:
                for dep in self.dependencies[module]['required']:
                    visit(dep)
            
            order.append(module)
        
        for module in modules_to_activate:
            visit(module)
        
        return order
    
    def check_circular_dependencies(self):
        """Verifica dependencias circulares"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(module):
            visited.add(module)
            rec_stack.add(module)
            
            if module in self.dependencies:
                for dep in self.dependencies[module]['required']:
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True
            
            rec_stack.remove(module)
            return False
        
        for module in MODULE_CONFIGS.keys():
            if module not in visited:
                if has_cycle(module):
                    return True
        
        return False
```

## 7. Interfaz de Administración

### 7.1 Vista de Administración de Módulos
```python
# core/views/module_admin.py
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, UpdateView
from django.contrib import messages
from django.shortcuts import redirect
from core.models import ModuleConfig
from core.module_manager import ModuleManager

class ModuleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ModuleConfig
    template_name = 'core/module_list.html'
    permission_required = 'core.change_moduleconfig'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        module_manager = ModuleManager()
        
        for module in context['object_list']:
            module.can_activate = module_manager.can_activate_module(module.name)
            module.can_deactivate = module_manager.can_deactivate_module(module.name)
            module.dependencies = module_manager.get_module_dependencies(module.name)
            module.dependents = module_manager.get_module_dependents(module.name)
        
        return context

class ModuleToggleView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'core.change_moduleconfig'
    
    def post(self, request, module_name):
        action = request.POST.get('action')
        module_manager = ModuleManager()
        
        if action == 'activate':
            if module_manager.activate_module(module_name):
                messages.success(request, f'Módulo {module_name} activado correctamente.')
            else:
                messages.error(request, f'No se pudo activar el módulo {module_name}.')
        
        elif action == 'deactivate':
            if module_manager.deactivate_module(module_name):
                messages.success(request, f'Módulo {module_name} desactivado correctamente.')
            else:
                messages.error(request, f'No se pudo desactivar el módulo {module_name}.')
        
        return redirect('core:module_list')
```

### 7.2 Template de Administración
```html
<!-- core/templates/core/module_list.html -->
{% extends "core/core_app_base.html" %}
{% load i18n %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <div class="mb-6">
        <h1 class="text-3xl font-bold text-gray-900">{% trans "Module Management" %}</h1>
        <p class="text-gray-600">{% trans "Activate or deactivate system modules" %}</p>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {% for module in object_list %}
        <div class="bg-white rounded-lg shadow-md p-6">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold text-gray-900">{{ module.display_name }}</h3>
                <span class="px-2 py-1 text-xs rounded-full {% if module.is_active %}bg-green-100 text-green-800{% else %}bg-red-100 text-red-800{% endif %}">
                    {% if module.is_active %}{% trans "Active" %}{% else %}{% trans "Inactive" %}{% endif %}
                </span>
            </div>
            
            <p class="text-gray-600 text-sm mb-4">{{ module.description }}</p>
            
            {% if module.dependencies %}
            <div class="mb-4">
                <h4 class="text-sm font-medium text-gray-700 mb-2">{% trans "Dependencies" %}</h4>
                <div class="flex flex-wrap gap-1">
                    {% for dep in module.dependencies %}
                    <span class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">{{ dep }}</span>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
            
            <div class="flex space-x-2">
                {% if module.is_active %}
                    {% if module.can_deactivate %}
                    <form method="post" action="{% url 'core:module_toggle' module.name %}">
                        {% csrf_token %}
                        <input type="hidden" name="action" value="deactivate">
                        <button type="submit" class="btn-danger text-sm">
                            {% trans "Deactivate" %}
                        </button>
                    </form>
                    {% else %}
                    <button disabled class="btn-secondary text-sm opacity-50">
                        {% trans "Cannot Deactivate" %}
                    </button>
                    {% endif %}
                {% else %}
                    {% if module.can_activate %}
                    <form method="post" action="{% url 'core:module_toggle' module.name %}">
                        {% csrf_token %}
                        <input type="hidden" name="action" value="activate">
                        <button type="submit" class="btn-primary text-sm">
                            {% trans "Activate" %}
                        </button>
                    </form>
                    {% else %}
                    <button disabled class="btn-secondary text-sm opacity-50">
                        {% trans "Cannot Activate" %}
                    </button>
                    {% endif %}
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

## 8. Migración y Configuración

### 8.1 Comando de Migración
```python
# core/management/commands/setup_modules.py
from django.core.management.base import BaseCommand
from core.models import ModuleConfig
from core.module_manager import ModuleManager

class Command(BaseCommand):
    help = 'Setup and configure system modules'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--activate',
            nargs='+',
            help='Modules to activate'
        )
        parser.add_argument(
            '--deactivate',
            nargs='+',
            help='Modules to deactivate'
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all module configurations'
        )
    
    def handle(self, *args, **options):
        if options['reset']:
            self.reset_modules()
        
        if options['activate']:
            self.activate_modules(options['activate'])
        
        if options['deactivate']:
            self.deactivate_modules(options['deactivate'])
        
        self.stdout.write(
            self.style.SUCCESS('Module configuration completed successfully')
        )
    
    def reset_modules(self):
        """Resetea la configuración de módulos"""
        ModuleConfig.objects.all().delete()
        
        for module_name, config in MODULE_CONFIGS.items():
            ModuleConfig.objects.create(
                name=module_name,
                display_name=config['display_name'],
                description=config['description'],
                version=config['version'],
                is_active=config.get('is_required', False),
                is_required=config.get('is_required', False),
                dependencies=config.get('dependencies', []),
                settings=config.get('settings', {})
            )
    
    def activate_modules(self, modules):
        """Activa módulos específicos"""
        module_manager = ModuleManager()
        
        for module in modules:
            if module_manager.activate_module(module):
                self.stdout.write(f'Module {module} activated')
            else:
                self.stdout.write(
                    self.style.ERROR(f'Could not activate module {module}')
                )
    
    def deactivate_modules(self, modules):
        """Desactiva módulos específicos"""
        module_manager = ModuleManager()
        
        for module in modules:
            if module_manager.deactivate_module(module):
                self.stdout.write(f'Module {module} deactivated')
            else:
                self.stdout.write(
                    self.style.ERROR(f'Could not deactivate module {module}')
                )
```

### 8.2 Configuración Inicial
```bash
# Comando para configurar módulos inicialmente
python manage.py setup_modules --reset

# Activar módulos específicos
python manage.py setup_modules --activate sales inventory purchases

# Desactivar módulos
python manage.py setup_modules --deactivate tiendanube
```

## 9. Plan de Implementación

### Fase 1: Core System (Semana 1-2)
1. **Implementar sistema de configuración de módulos**
   - Modelo ModuleConfig
   - ModuleManager
   - Registry de módulos

2. **Crear middleware de módulos**
   - ModuleMiddleware
   - Verificación de acceso

3. **Implementar gestión de URLs dinámicas**
   - URLRegistry
   - Carga dinámica de URLs

### Fase 2: Gestión de Menús (Semana 3)
1. **Implementar MenuManager**
   - Carga dinámica de menús
   - Filtrado por permisos

2. **Crear interfaz de administración**
   - Vistas de gestión de módulos
   - Templates de administración

### Fase 3: Sistema de Hooks (Semana 4)
1. **Implementar HookManager**
   - Sistema de eventos
   - Registro de hooks

2. **Crear hooks de ejemplo**
   - Hooks para sales
   - Hooks para purchases

### Fase 4: Migración y Testing (Semana 5)
1. **Crear comandos de migración**
   - setup_modules
   - Verificación de dependencias

2. **Testing completo**
   - Tests unitarios
   - Tests de integración

### Fase 5: Documentación y Optimización (Semana 6)
1. **Documentación**
   - Manual de desarrollador
   - Guía de migración

2. **Optimización**
   - Cache de módulos
   - Performance tuning

## 10. Beneficios del Sistema Modular

### 10.1 Para Desarrolladores
- **Desacoplamiento**: Módulos independientes
- **Reutilización**: Componentes compartidos
- **Escalabilidad**: Fácil agregar nuevos módulos
- **Mantenibilidad**: Código organizado y modular

### 10.2 Para Administradores
- **Flexibilidad**: Activar solo módulos necesarios
- **Performance**: Reducir carga del sistema
- **Costos**: Pagar solo por funcionalidades usadas
- **Personalización**: Configurar según necesidades

### 10.3 Para Usuarios Finales
- **Simplicidad**: Interfaz limpia y enfocada
- **Rendimiento**: Sistema más rápido
- **Experiencia**: Solo ver funcionalidades relevantes
- **Escalabilidad**: Crecer con el negocio

## 11. Consideraciones Futuras

### 11.1 Nuevos Módulos Potenciales
- **HR Module**: Gestión de recursos humanos
- **Manufacturing**: Control de producción
- **CRM**: Gestión de relaciones con clientes
- **Analytics**: Reportes avanzados y dashboards
- **API Gateway**: Integración con sistemas externos
- **Mobile App**: Aplicación móvil nativa

### 11.2 Mejoras Futuras
- **Plugin System**: Módulos de terceros
- **Marketplace**: Tienda de módulos
- **Multi-tenant**: Soporte para múltiples empresas
- **Microservices**: Arquitectura distribuida
- **Cloud Native**: Despliegue en la nube

Este plan proporciona una base sólida para un sistema modular desacoplado que permitirá a Synap crecer de manera sostenible y adaptarse a las necesidades cambiantes del mercado. 