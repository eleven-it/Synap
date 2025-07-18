#!/usr/bin/env python3
import os
import django
import sys
from datetime import timedelta
from django.utils import timezone

# Configuración de Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from administraNET_integration.models import SyncLog
from django.db import transaction
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('watchdog_synclog')

# Tiempo máximo permitido en RUNNING (minutos)
MAX_RUNNING_MINUTES = 30

def main():
    now = timezone.now()
    threshold = now - timedelta(minutes=MAX_RUNNING_MINUTES)
    stuck_logs = SyncLog.objects.filter(status='RUNNING', started_at__lt=threshold)
    count = stuck_logs.count()
    if count == 0:
        logger.info('No hay SyncLogs atascados en RUNNING.')
        return
    for log in stuck_logs:
        with transaction.atomic():
            log.status = 'FAILED'
            log.error_message = '[WATCHDOG] Sincronización marcada como FAILED por exceder tiempo máximo en RUNNING.'
            log.completed_at = now
            log.save()
            logger.warning(f'SyncLog {log.id} ({log.sync_type}) marcado como FAILED (iniciado: {log.started_at})')
    logger.info(f'Total de SyncLogs marcados como FAILED: {count}')

if __name__ == '__main__':
    main() 