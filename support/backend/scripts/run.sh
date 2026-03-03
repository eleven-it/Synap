#!/bin/sh
# Migrar y arrancar servidor (desarrollo).
set -e
cd "$(dirname "$0")/.."
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.local}"
python manage.py migrate --noinput
python manage.py runserver 0.0.0.0:8000
