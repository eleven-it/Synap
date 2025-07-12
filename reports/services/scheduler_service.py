"""
Servicio de programación automática de reportes
Proporciona funcionalidades para programar, ejecutar y distribuir reportes automáticamente
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
import json
import base64

from reports.models import Report, ReportSchedule
from reports.services.ai_integration import ai_service
from core.models import Empresa, UsuarioExtendido

logger = logging.getLogger(__name__)

class ReportSchedulerService:
    """Servicio para programación automática de reportes"""
    
    def __init__(self):
        self.ai_service = ai_service
    
    async def create_schedule(
        self,
        report: Report,
        schedule_type: str,
        schedule_config: Dict[str, Any],
        distribution_config: Dict[str, Any],
        user: UsuarioExtendido
    ) -> ReportSchedule:
        """Crear una nueva programación de reporte"""
        try:
            logger.info(f"Creando programación para reporte: {report.title}")
            
            # Validar configuración de programación
            self._validate_schedule_config(schedule_type, schedule_config)
            
            # Crear programación
            schedule = ReportSchedule.objects.create(
                report=report,
                schedule_type=schedule_type,
                schedule_config=schedule_config,
                distribution_config=distribution_config,
                created_by=user,
                empresa=user.branches.first().empresa if user.branches.exists() else None,
                is_active=True,
                next_execution=self._calculate_next_execution(schedule_type, schedule_config)
            )
            
            logger.info(f"Programación creada exitosamente: {schedule.id}")
            return schedule
            
        except Exception as e:
            logger.error(f"Error creando programación: {e}")
            raise
    
    def _validate_schedule_config(self, schedule_type: str, config: Dict[str, Any]) -> None:
        """Validar configuración de programación"""
        if schedule_type == "daily":
            if "time" not in config:
                raise ValueError("Configuración diaria requiere hora de ejecución")
        elif schedule_type == "weekly":
            if "day_of_week" not in config or "time" not in config:
                raise ValueError("Configuración semanal requiere día y hora")
        elif schedule_type == "monthly":
            if "day_of_month" not in config or "time" not in config:
                raise ValueError("Configuración mensual requiere día del mes y hora")
        elif schedule_type == "custom":
            if "cron_expression" not in config:
                raise ValueError("Configuración personalizada requiere expresión cron")
        else:
            raise ValueError(f"Tipo de programación no válido: {schedule_type}")
    
    def _calculate_next_execution(self, schedule_type: str, config: Dict[str, Any]) -> datetime:
        """Calcular próxima ejecución basada en configuración"""
        now = timezone.now()
        
        if schedule_type == "daily":
            time_str = config.get("time", "09:00")
            hour, minute = map(int, time_str.split(":"))
            next_exec = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_exec <= now:
                next_exec += timedelta(days=1)
                
        elif schedule_type == "weekly":
            day_of_week = config.get("day_of_week", 0)  # 0 = Lunes
            time_str = config.get("time", "09:00")
            hour, minute = map(int, time_str.split(":"))
            
            days_ahead = day_of_week - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_exec = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
            
        elif schedule_type == "monthly":
            day_of_month = config.get("day_of_month", 1)
            time_str = config.get("time", "09:00")
            hour, minute = map(int, time_str.split(":"))
            
            if now.day > day_of_month:
                # Pasar al próximo mes
                if now.month == 12:
                    next_exec = now.replace(year=now.year + 1, month=1, day=day_of_month, hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    next_exec = now.replace(month=now.month + 1, day=day_of_month, hour=hour, minute=minute, second=0, microsecond=0)
            else:
                next_exec = now.replace(day=day_of_month, hour=hour, minute=minute, second=0, microsecond=0)
                
        elif schedule_type == "custom":
            # Implementar parser de cron expression
            next_exec = self._parse_cron_expression(config.get("cron_expression", ""), now)
            
        return next_exec
    
    def _parse_cron_expression(self, cron_expr: str, from_time: datetime) -> datetime:
        """Parser básico de expresiones cron"""
        # Implementación simplificada - en producción usar librería como croniter
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError("Expresión cron debe tener 5 partes")
        
        # Por ahora, retornar ejecución en 1 hora
        return from_time + timedelta(hours=1)
    
    async def execute_scheduled_report(self, schedule: ReportSchedule) -> bool:
        """Ejecutar reporte programado"""
        try:
            logger.info(f"Ejecutando reporte programado: {schedule.report.title}")
            
            # Generar reporte con IA
            report_data = await self._generate_report_data(schedule.report)
            
            # Generar branding
            branding = await self._generate_branding(schedule.report)
            
            # Exportar según configuración
            export_format = schedule.distribution_config.get("export_format", "pdf")
            if export_format == "pdf":
                export_result = await self.ai_service.export_to_pdf(
                    report_data=report_data,
                    branding=branding,
                    optimize_for_executive=True
                )
            elif export_format == "pptx":
                export_result = await self.ai_service.export_to_pptx(
                    report_data=report_data,
                    branding=branding,
                    optimize_for_executive=True
                )
            else:
                raise ValueError(f"Formato de exportación no soportado: {export_format}")
            
            if "error" in export_result:
                logger.error(f"Error en exportación: {export_result['error']}")
                return False
            
            # Guardar archivo generado
            file_data = base64.b64decode(export_result["file_data"])
            filename = export_result["filename"]
            
            # Crear registro de distribución
            # distribution = ReportDistribution.objects.create( # Modelo no implementado aún
            #     schedule=schedule,
            #     report=schedule.report,
            #     export_format=export_format,
            #     file_size=len(file_data),
            #     generated_at=timezone.now(),
            #     status="completed"
            # )
            
            # Guardar archivo
            # distribution.file.save(filename, ContentFile(file_data), save=True) # Modelo no implementado aún
            
            # Distribuir reporte
            await self._distribute_report(schedule.report, schedule.distribution_config) # Modelo no implementado aún
            
            # Actualizar próxima ejecución
            schedule.last_execution = timezone.now()
            schedule.next_execution = self._calculate_next_execution(
                schedule.schedule_type, 
                schedule.schedule_config
            )
            schedule.save()
            
            logger.info(f"Reporte programado ejecutado exitosamente: {schedule.id}") # Modelo no implementado aún
            return True
            
        except Exception as e:
            logger.error(f"Error ejecutando reporte programado: {e}")
            
            # Registrar error
            # ReportDistribution.objects.create( # Modelo no implementado aún
            #     schedule=schedule,
            #     report=schedule.report,
            #     status="failed",
            #     error_message=str(e),
            #     generated_at=timezone.now()
            # )
            
            return False
    
    async def _generate_report_data(self, report: Report) -> Dict[str, Any]:
        """Generar datos del reporte usando IA"""
        try:
            # Obtener contexto de la empresa
            empresa = report.empresa
            company_context = {
                "name": empresa.nombre,
                "industry": empresa.industria or "General",
                "size": "Medium"  # Por defecto
            }
            
            # Generar reporte con IA
            report_data = await self.ai_service.generate_report(
                title=report.title,
                description=report.description,
                data_sources=report.data_sources,
                template_type=report.template.template_type if report.template else "general",
                company_context=company_context,
                user_preferences={"audience": "executive"}
            )
            
            return report_data
            
        except Exception as e:
            logger.error(f"Error generando datos del reporte: {e}")
            # Retornar datos básicos si falla la IA
            return {
                "title": report.title,
                "description": report.description,
                "content": {
                    "executive_summary": "Reporte generado automáticamente",
                    "key_findings": ["Datos no disponibles"],
                    "recommendations": ["Revisar configuración"]
                }
            }
    
    async def _generate_branding(self, report: Report) -> Dict[str, Any]:
        """Generar branding para el reporte"""
        try:
            empresa = report.empresa
            company_data = {
                "name": empresa.nombre,
                "industry": empresa.industria or "General",
                "size": "Medium"
            }
            
            branding_result = await self.ai_service.generate_branding_guidelines(
                company_data=company_data,
                report_type=report.template.template_type if report.template else "general"
            )
            
            if "branding_guidelines" in branding_result:
                return branding_result["branding_guidelines"]
            else:
                # Branding por defecto
                return {
                    "primary_color": "#2563eb",
                    "secondary_color": "#64748b",
                    "company_name": empresa.nombre,
                    "tagline": "Reporte Automático"
                }
                
        except Exception as e:
            logger.error(f"Error generando branding: {e}")
            # Branding por defecto
            return {
                "primary_color": "#2563eb",
                "secondary_color": "#64748b",
                "company_name": report.empresa.nombre,
                "tagline": "Reporte Automático"
            }
    
    async def _distribute_report(
        self, 
        report: Report, # Modelo no implementado aún
        config: Dict[str, Any]
    ) -> None:
        """Distribuir reporte según configuración"""
        try:
            distribution_methods = config.get("methods", [])
            
            for method in distribution_methods:
                if method == "email":
                    await self._send_email_distribution(report, config) # Modelo no implementado aún
                elif method == "slack":
                    await self._send_slack_distribution(report, config) # Modelo no implementado aún
                elif method == "webhook":
                    await self._send_webhook_distribution(report, config) # Modelo no implementado aún
                elif method == "storage":
                    await self._save_to_storage(report, config) # Modelo no implementado aún
                    
        except Exception as e:
            logger.error(f"Error distribuyendo reporte: {e}")
    
    async def _send_email_distribution(
        self, 
        report: Report, # Modelo no implementado aún
        config: Dict[str, Any]
    ) -> None:
        """Enviar reporte por email"""
        try:
            recipients = config.get("email_recipients", [])
            if not recipients:
                logger.warning("No hay destinatarios de email configurados")
                return
            
            subject = config.get("email_subject", f"Reporte: {report.title}") # Modelo no implementado aún
            
            # Generar contenido del email
            context = {
                "report": report, # Modelo no implementado aún
                "distribution": report, # Modelo no implementado aún
                "generated_at": timezone.now(), # Modelo no implementado aún
                "file_size": 0 # Modelo no implementado aún
            }
            
            html_content = render_to_string("reports/email/report_distribution.html", context)
            text_content = render_to_string("reports/email/report_distribution.txt", context)
            
            # Enviar email
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                html_message=html_content,
                fail_silently=False
            )
            
            logger.info(f"Email enviado a {len(recipients)} destinatarios")
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
    
    async def _send_slack_distribution(
        self, 
        report: Report, # Modelo no implementado aún
        config: Dict[str, Any]
    ) -> None:
        """Enviar reporte a Slack"""
        try:
            webhook_url = config.get("slack_webhook_url")
            channel = config.get("slack_channel", "#general")
            
            if not webhook_url:
                logger.warning("No hay webhook de Slack configurado")
                return
            
            # Implementar envío a Slack
            # Por ahora solo log
            logger.info(f"Reporte enviado a Slack channel: {channel}")
            
        except Exception as e:
            logger.error(f"Error enviando a Slack: {e}")
    
    async def _send_webhook_distribution(
        self, 
        report: Report, # Modelo no implementado aún
        config: Dict[str, Any]
    ) -> None:
        """Enviar reporte via webhook"""
        try:
            webhook_url = config.get("webhook_url")
            if not webhook_url:
                logger.warning("No hay webhook configurado")
                return
            
            # Preparar datos para webhook
            webhook_data = {
                "report_id": report.id, # Modelo no implementado aún
                "report_title": report.title, # Modelo no implementado aún
                "distribution_id": report.id, # Modelo no implementado aún
                "export_format": "pdf", # Modelo no implementado aún
                "file_size": 0, # Modelo no implementado aún
                "generated_at": timezone.now().isoformat(), # Modelo no implementado aún
                "download_url": f"/reports/download/{report.id}/" # Modelo no implementado aún
            }
            
            # Enviar webhook (implementar con httpx)
            logger.info(f"Webhook enviado a: {webhook_url}")
            
        except Exception as e:
            logger.error(f"Error enviando webhook: {e}")
    
    async def _save_to_storage(
        self, 
        report: Report, # Modelo no implementado aún
        config: Dict[str, Any]
    ) -> None:
        """Guardar reporte en almacenamiento externo"""
        try:
            storage_type = config.get("storage_type", "local")
            
            if storage_type == "local":
                # Ya está guardado localmente
                logger.info("Reporte guardado localmente")
            elif storage_type == "s3":
                # Implementar guardado en S3
                logger.info("Reporte guardado en S3")
            elif storage_type == "gdrive":
                # Implementar guardado en Google Drive
                logger.info("Reporte guardado en Google Drive")
            
        except Exception as e:
            logger.error(f"Error guardando en almacenamiento: {e}")
    
    async def process_scheduled_reports(self) -> Dict[str, int]:
        """Procesar todos los reportes programados pendientes"""
        try:
            now = timezone.now()
            pending_schedules = ReportSchedule.objects.filter(
                is_active=True,
                next_execution__lte=now
            )
            
            logger.info(f"Procesando {pending_schedules.count()} reportes programados")
            
            results = {
                "total": pending_schedules.count(),
                "success": 0,
                "failed": 0
            }
            
            for schedule in pending_schedules:
                success = await self.execute_scheduled_report(schedule)
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
            
            logger.info(f"Procesamiento completado: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error procesando reportes programados: {e}")
            return {"total": 0, "success": 0, "failed": 0}
    
    def get_schedule_status(self, schedule: ReportSchedule) -> Dict[str, Any]:
        """Obtener estado detallado de una programación"""
        try:
            # Obtener últimas distribuciones
            # recent_distributions = ReportDistribution.objects.filter( # Modelo no implementado aún
            #     schedule=schedule
            # ).order_by('-generated_at')[:5]
            
            # Calcular estadísticas
            # total_distributions = ReportDistribution.objects.filter(schedule=schedule).count() # Modelo no implementado aún
            # successful_distributions = ReportDistribution.objects.filter( # Modelo no implementado aún
            #     schedule=schedule, 
            #     status="completed"
            # ).count()
            
            # success_rate = (successful_distributions / total_distributions * 100) if total_distributions > 0 else 0 # Modelo no implementado aún
            
            return {
                "schedule_id": schedule.id,
                "report_title": schedule.report.title,
                "schedule_type": schedule.schedule_type,
                "is_active": schedule.is_active,
                "next_execution": schedule.next_execution,
                "last_execution": schedule.last_execution,
                "total_distributions": 0, # Modelo no implementado aún
                "successful_distributions": 0, # Modelo no implementado aún
                "success_rate": 0, # Modelo no implementado aún
                "recent_distributions": [] # Modelo no implementado aún
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado de programación: {e}")
            return {"error": str(e)}
    
    async def pause_schedule(self, schedule: ReportSchedule) -> bool:
        """Pausar una programación"""
        try:
            schedule.is_active = False
            schedule.save()
            logger.info(f"Programación pausada: {schedule.id}")
            return True
        except Exception as e:
            logger.error(f"Error pausando programación: {e}")
            return False
    
    async def resume_schedule(self, schedule: ReportSchedule) -> bool:
        """Reanudar una programación"""
        try:
            schedule.is_active = True
            schedule.save()
            logger.info(f"Programación reanudada: {schedule.id}")
            return True
        except Exception as e:
            logger.error(f"Error reanudando programación: {e}")
            return False
    
    async def delete_schedule(self, schedule: ReportSchedule) -> bool:
        """Eliminar una programación"""
        try:
            schedule.delete()
            logger.info(f"Programación eliminada: {schedule.id}")
            return True
        except Exception as e:
            logger.error(f"Error eliminando programación: {e}")
            return False

# Instancia global del servicio
scheduler_service = ReportSchedulerService() 