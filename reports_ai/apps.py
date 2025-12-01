"""
Configuración de la aplicación Reports AI
"""
from django.apps import AppConfig
# Función dummy para mantener compatibilidad - no se usa internacionalización
def _(s): return s


class ReportsAiConfig(AppConfig):
    """Configuración del módulo de Reportes AI"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reports_ai'
    verbose_name = _('Reportes AI Administranet')
    
    # Configuración del módulo para el sistema de gestión de módulos
    module_config = {
        'name': 'reports_ai',
        'display_name': 'Reports AI (CrewAI)',
        'icon': 'fas fa-brain',
        'color': 'purple',
        'order': 90,
    }
    
    def ready(self):
        """Inicialización cuando Django está listo"""
        try:
            # Importar signals si los hay
            # import reports_ai.signals
            
            # Registrar hooks del módulo
            self._register_hooks()
            
        except ImportError:
            pass
    
    def _register_hooks(self):
        """Registra los hooks del módulo en el sistema"""
        try:
            from core.hook_registry import hook_registry
            
            # Registrar hooks definidos en module_registry
            hooks = [
                'reports_ai.pre_report_generate',
                'reports_ai.post_report_generate',
                'reports_ai.report_error',
                'reports_ai.agent_invoked',
                'reports_ai.validation_failed',
                'reports_ai.hallucination_detected',
            ]
            
            for hook_name in hooks:
                hook_registry.register_hook(hook_name, self.name)
                
        except Exception as e:
            # Si falla el registro de hooks, continuar (puede ser durante migración)
            pass

