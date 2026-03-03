"""
Utilidades para gestión de permisos del sistema.
Funciones reutilizables para crear y sincronizar permisos entre PostgreSQL y MySQL.
"""
import logging
from core.models import Permiso

logger = logging.getLogger(__name__)
