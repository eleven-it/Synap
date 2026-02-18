#!/usr/bin/env python
"""Script de administración del proyecto Support (Django)."""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Está instalado en el entorno?"
        ) from exc
    execute_from_command_line(sys.argv)
