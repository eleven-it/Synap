from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class ModuleConfig(models.Model):
    """
    Modelo para gestionar la configuración de módulos del sistema
    Permite activar/desactivar módulos y configurar sus dependencias
    """
    name = models.CharField(
        _('Module Name'), 
        max_length=50, 
        unique=True,
        help_text=_('Internal module identifier')
    )
    display_name = models.CharField(
        _('Display Name'), 
        max_length=100,
        help_text=_('Human-readable module name')
    )
    description = models.TextField(
        _('Description'), 
        blank=True,
        help_text=_('Module description')
    )
    version = models.CharField(
        _('Version'), 
        max_length=20, 
        default='1.0.0',
        help_text=_('Module version')
    )
    author = models.CharField(
        _('Author'), 
        max_length=100, 
        blank=True,
        help_text=_('Module author or development team')
    )
    
    # Estado del módulo
    is_active = models.BooleanField(
        _('Active'), 
        default=False,
        help_text=_('Whether the module is currently active')
    )
    is_required = models.BooleanField(
        _('Required'), 
        default=False,
        help_text=_('Whether the module is required for system operation')
    )
    is_core = models.BooleanField(
        _('Core Module'), 
        default=False,
        help_text=_('Whether this is a core system module')
    )
    
    # Dependencias
    dependencies = models.JSONField(
        _('Dependencies'), 
        default=list,
        help_text=_('List of required module dependencies')
    )
    optional_dependencies = models.JSONField(
        _('Optional Dependencies'), 
        default=list,
        help_text=_('List of optional module dependencies')
    )
    
    # Configuración
    settings = models.JSONField(
        _('Settings'), 
        default=dict,
        help_text=_('Module-specific configuration settings')
    )
    permissions = models.JSONField(
        _('Permissions'), 
        default=list,
        help_text=_('List of permissions provided by this module')
    )
    hooks = models.JSONField(
        _('Hooks'), 
        default=list,
        help_text=_('List of hooks provided by this module')
    )
    
    # Metadatos
    created_at = models.DateTimeField(
        _('Created at'), 
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('Updated at'), 
        auto_now=True
    )
    last_activated = models.DateTimeField(
        _('Last Activated'), 
        null=True, 
        blank=True
    )
    last_deactivated = models.DateTimeField(
        _('Last Deactivated'), 
        null=True, 
        blank=True
    )

    class Meta:
        verbose_name = _('Module Configuration')
        verbose_name_plural = _('Module Configurations')
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['is_core']),
            models.Index(fields=['is_required']),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.name})"

    def clean(self):
        """Validaciones del modelo"""
        from django.core.exceptions import ValidationError
        
        # Validar que el nombre sea válido
        if not self.name.isalnum() and not '_' in self.name:
            raise ValidationError(_('Module name must be alphanumeric with underscores only'))
        
        # Validar que las dependencias no sean circulares
        if self.name in self.dependencies:
            raise ValidationError(_('Module cannot depend on itself'))

    def save(self, *args, **kwargs):
        """Override save para actualizar timestamps de activación"""
        if self.pk:
            old_instance = ModuleConfig.objects.get(pk=self.pk)
            if not old_instance.is_active and self.is_active:
                self.last_activated = timezone.now()
            elif old_instance.is_active and not self.is_active:
                self.last_deactivated = timezone.now()
        elif self.is_active:
            self.last_activated = timezone.now()
        
        super().save(*args, **kwargs)

    @property
    def status_display(self):
        """Retorna el estado del módulo para mostrar"""
        if self.is_core:
            return _('Core')
        elif self.is_required:
            return _('Required')
        elif self.is_active:
            return _('Active')
        else:
            return _('Inactive')

    @property
    def can_be_activated(self):
        """Verifica si el módulo puede ser activado"""
        from core.module_manager import ModuleManager
        module_manager = ModuleManager()
        return module_manager.can_activate_module(self.name)

    @property
    def can_be_deactivated(self):
        """Verifica si el módulo puede ser desactivado"""
        from core.module_manager import ModuleManager
        module_manager = ModuleManager()
        return module_manager.can_deactivate_module(self.name)

    def get_dependency_tree(self):
        """Obtiene el árbol de dependencias del módulo"""
        from core.dependency_manager import DependencyManager
        dependency_manager = DependencyManager()
        return dependency_manager.get_dependency_tree(self.name)

    def get_dependents(self):
        """Obtiene los módulos que dependen de este"""
        from core.module_manager import ModuleManager
        module_manager = ModuleManager()
        return module_manager.get_module_dependents(self.name)

    def get_settings_schema(self):
        """Obtiene el esquema de configuración del módulo"""
        try:
            module = __import__(f'{self.name}.module_config', fromlist=['SETTINGS_SCHEMA'])
            return getattr(module, 'SETTINGS_SCHEMA', {})
        except ImportError:
            return {}

    def update_settings(self, new_settings):
        """Actualiza la configuración del módulo"""
        current_settings = self.settings.copy()
        current_settings.update(new_settings)
        self.settings = current_settings
        self.save(update_fields=['settings', 'updated_at']) 

    @classmethod
    def get_active_nav_modules(cls):
        """
        Devuelve los módulos activos que deben aparecer en la navegación principal (navbar)
        """
        return cls.objects.filter(is_active=True, is_core=False).order_by('display_name')

    @classmethod
    def get_nav_menu_items(cls):
        """
        Devuelve una lista de diccionarios con los items de menú para el navbar y dropdown,
        incluyendo submenús por cada módulo activo.
        """
        modules = cls.get_active_nav_modules()
        items = []
        for mod in modules:
            items.append({
                'name': mod.name,
                'display_name': mod.display_name,
                'url': f'/{mod.name}/',
                'submenu': mod.get_nav_submenu_items() if hasattr(mod, 'get_nav_submenu_items') else [],
            })
        return items

    def get_nav_submenu_items(self):
        """
        Devuelve los submenús para este módulo (puede ser extendido por cada app)
        """
        if self.name == 'tiendanube_administranet':
            return [
                {'label': 'Dashboard', 'url': '/tiendanube_administranet/'},
                {'label': 'Customer Mappings', 'url': '/tiendanube_administranet/customer-mappings/'},
                {'label': 'Product Mappings', 'url': '/tiendanube_administranet/product-mappings/'},
                {'label': 'Order Mappings', 'url': '/tiendanube_administranet/order-mappings/'},
                {'label': 'Sync History', 'url': '/tiendanube_administranet/sync-history/'},
            ]
        elif self.name == 'self_checkout':
            return [
                {'label': 'Selector de kiosco', 'url': '/self_checkout/'},
                {'label': 'Configuración autoservicios', 'url': '/self_checkout/config/'},
                {'label': 'Carritos pendientes', 'url': '/self_checkout/config/carritos-pendientes/'},
                {'label': 'Talonarios', 'url': '/self_checkout/talonarios/'},
            ]
        # Por defecto, un solo item principal
        return [{
            'label': self.display_name,
            'url': f'/{self.name}/',
        }] 