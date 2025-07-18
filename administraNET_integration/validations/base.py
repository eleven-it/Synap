from abc import ABC, abstractmethod
from django.utils.translation import gettext_lazy as _

class BaseValidationRule(ABC):
    """
    Clase base para todas las reglas de validación custom de integración AdministraNET.
    Cada subclase debe definir un código único y un método validate.
    """
    code = None  # Código único de la regla (ej: 'unique_product_sku')
    label = None  # Nombre legible de la regla
    description = None  # Descripción corta para mostrar en UI

    def __init__(self, empresa):
        self.empresa = empresa

    @abstractmethod
    def validate(self, context=None):
        """
        Ejecuta la validación. Debe devolver un diccionario con el resultado:
        {
            'success': bool,
            'errors': [str],
            'warnings': [str],
            'details': dict
        }
        """
        pass

# Registro automático de reglas
VALIDATION_RULES_REGISTRY = {}

def register_validation_rule(cls):
    if cls.code:
        VALIDATION_RULES_REGISTRY[cls.code] = cls
    return cls 