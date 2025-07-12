"""
Comando para ejecutar reportes programados automáticamente
"""

import asyncio
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from reports.services.scheduler_service import scheduler_service

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Ejecutar reportes programados que están pendientes de ejecución'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué reportes se ejecutarían sin ejecutarlos realmente'
        )
        parser.add_argument(
            '--schedule-id',
            type=int,
            help='Ejecutar solo un reporte programado específico'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar ejecución incluso si no está programado'
        )
    
    def handle(self, *args, **options):
        """Manejar la ejecución del comando"""
        try:
            self.stdout.write(
                self.style.SUCCESS('🚀 Iniciando procesamiento de reportes programados...')
            )
            
            # Ejecutar en modo asíncrono
            results = asyncio.run(self._process_scheduled_reports(options))
            
            # Mostrar resultados
            self._display_results(results, options)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error ejecutando reportes programados: {e}')
            )
            logger.error(f"Error en comando run_scheduled_reports: {e}")
    
    async def _process_scheduled_reports(self, options):
        """Procesar reportes programados"""
        if options['dry_run']:
            return await self._dry_run_scheduled_reports(options)
        else:
            return await scheduler_service.process_scheduled_reports()
    
    async def _dry_run_scheduled_reports(self, options):
        """Simular ejecución de reportes programados"""
        from reports.models import ReportSchedule
        
        now = timezone.now()
        
        if options['schedule_id']:
            # Solo un reporte específico
            schedules = ReportSchedule.objects.filter(
                id=options['schedule_id'],
                is_active=True
            )
        else:
            # Todos los reportes pendientes
            schedules = ReportSchedule.objects.filter(
                is_active=True,
                next_execution__lte=now
            )
        
        self.stdout.write(f"📋 Reportes que se ejecutarían: {schedules.count()}")
        
        for schedule in schedules:
            self.stdout.write(
                f"  • {schedule.report.title} (ID: {schedule.id})"
            )
            self.stdout.write(
                f"    - Tipo: {schedule.schedule_type}"
            )
            self.stdout.write(
                f"    - Próxima ejecución: {schedule.next_execution}"
            )
            self.stdout.write(
                f"    - Formato: {schedule.distribution_config.get('export_format', 'pdf')}"
            )
            self.stdout.write("")
        
        return {
            "total": schedules.count(),
            "success": 0,
            "failed": 0,
            "dry_run": True
        }
    
    def _display_results(self, results, options):
        """Mostrar resultados del procesamiento"""
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('🔍 Modo dry-run - No se ejecutaron reportes')
            )
            return
        
        total = results.get('total', 0)
        success = results.get('success', 0)
        failed = results.get('failed', 0)
        
        self.stdout.write("")
        self.stdout.write("📊 Resultados del procesamiento:")
        self.stdout.write(f"  • Total de reportes procesados: {total}")
        self.stdout.write(f"  • Exitosos: {success}")
        self.stdout.write(f"  • Fallidos: {failed}")
        
        if total > 0:
            success_rate = (success / total) * 100
            self.stdout.write(f"  • Tasa de éxito: {success_rate:.1f}%")
            
            if success > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {success} reportes ejecutados exitosamente")
                )
            
            if failed > 0:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ {failed} reportes fallaron")
                )
        else:
            self.stdout.write(
                self.style.WARNING("ℹ️ No hay reportes programados pendientes")
            )
        
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS('🎉 Procesamiento de reportes programados completado')
        ) 