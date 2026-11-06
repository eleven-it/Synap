"""
Settings mínimos para tests unitarios de reportes en CI/VM sin Postgres/MySQL.

Uso:
  DJANGO_SETTINGS_MODULE=django_project.settings_test_reports python manage.py test ...
"""

try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    pass

from .settings import *  # noqa: F401,F403

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
    "mysql": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}
