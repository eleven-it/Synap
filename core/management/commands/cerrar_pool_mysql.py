"""Cierra todas las conexiones MySQL del pool del proceso actual.

Útil antes de un restore/mantenimiento de AdministraNET, o cuando se detectan
conexiones Sleep ociosas dejadas por workers de Synap.

Uso:
    docker exec Synap_app python manage.py cerrar_pool_mysql
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from core.mysql_pool import MySQLConnectionPool, get_mysql_pool


class Command(BaseCommand):
    help = "Cierra todas las conexiones del pool MySQL de este proceso Synap."

    def handle(self, *args, **options):
        # Asegura que el pool exista (registra atexit) y luego cierra todos.
        try:
            get_mysql_pool()
        except Exception as exc:
            self.stderr.write(self.style.WARNING(f"No se pudo inicializar el pool: {exc}"))
        n = MySQLConnectionPool.close_all_pools()
        self.stdout.write(
            self.style.SUCCESS(
                f"Pool MySQL cerrado ({n} pool(s) en este proceso). "
                "Si hay workers Gunicorn/uWSGI, reinicialos o esperá POOL_IDLE_SECONDS "
                "para que liberen sus Sleep, o usá KILL en MySQL para conexiones ajenas."
            )
        )
