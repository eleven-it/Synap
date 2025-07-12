from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from core.models import Permiso


class Command(BaseCommand):
    help = 'Configurar permisos del módulo reports en la base de datos'

    def handle(self, *args, **options):
        """Configurar permisos de reports"""
        
        # Definir permisos del módulo reports
        permisos_reports = [
            ("reports.ver", "Ver reportes"),
            ("reports.crear", "Crear reportes personalizados"),
            ("reports.editar", "Editar reportes"),
            ("reports.eliminar", "Eliminar reportes"),
            ("reports.exportar", "Exportar reportes"),
            ("reports.programar", "Programar reportes automáticos"),
            ("reports.dashboard", "Acceso a dashboards"),
            ("reports.builder", "Usar constructor visual de reportes"),
            ("reports.templates", "Gestionar templates de reportes"),
            ("reports.components", "Gestionar componentes de reportes"),
            ("reports.schedules", "Gestionar programación de reportes"),
            ("reports.ai", "Usar funcionalidades de IA para reportes"),
        ]
        
        # Crear o actualizar permisos
        for codigo, nombre in permisos_reports:
            permiso, created = Permiso.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'descripcion': f'Permiso para {nombre.lower()}',
                    'modulo': 'reports',
                    'activo': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Permiso creado: {codigo} - {nombre}')
                )
            else:
                # Actualizar si ya existe
                if permiso.nombre != nombre or permiso.modulo != 'reports':
                    permiso.nombre = nombre
                    permiso.modulo = 'reports'
                    permiso.activo = True
                    permiso.save()
                    self.stdout.write(
                        self.style.WARNING(f'↻ Permiso actualizado: {codigo} - {nombre}')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Permiso ya existe: {codigo} - {nombre}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS('\n🎉 Permisos del módulo reports configurados correctamente!')
        ) 