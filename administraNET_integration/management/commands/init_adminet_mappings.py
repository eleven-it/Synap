from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from administraNET_integration.models import TableMapping
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = _('Inicializar mapeos predefinidos para la integración con administraNET')

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help=_('Forzar recreación de mapeos existentes'),
        )
        parser.add_argument(
            '--type',
            type=str,
            help=_('Inicializar solo un tipo específico de mapeo'),
        )

    def handle(self, *args, **options):
        force = options['force']
        mapping_type = options['type']
        
        self.stdout.write(
            self.style.SUCCESS(_('Iniciando inicialización de mapeos predefinidos...'))
        )
        
        # Obtener tipos de mapeo disponibles
        available_types = list(TableMapping.get_preset_mappings().keys())
        
        if mapping_type:
            if mapping_type not in available_types:
                self.stdout.write(
                    self.style.ERROR(
                        _('Tipo de mapeo no válido: %(type)s. Tipos disponibles: %(available)s') % {
                            'type': mapping_type,
                            'available': ', '.join(available_types)
                        }
                    )
                )
                return
            types_to_process = [mapping_type]
        else:
            types_to_process = available_types
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for mapping_type in types_to_process:
            try:
                # Verificar si ya existe
                existing = TableMapping.objects.filter(mapping_type=mapping_type).first()
                
                if existing and not force:
                    self.stdout.write(
                        self.style.WARNING(
                            _('Mapeo %(type)s ya existe. Usar --force para recrear.') % {
                                'type': mapping_type
                            }
                        )
                    )
                    skipped_count += 1
                    continue
                
                if existing and force:
                    # Actualizar mapeo existente
                    existing.update_from_preset()
                    self.stdout.write(
                        self.style.SUCCESS(
                            _('Mapeo %(type)s actualizado desde predefinido.') % {
                                'type': mapping_type
                            }
                        )
                    )
                    updated_count += 1
                else:
                    # Crear nuevo mapeo
                    mapping = TableMapping.create_preset_mapping(mapping_type)
                    self.stdout.write(
                        self.style.SUCCESS(
                            _('Mapeo %(type)s creado exitosamente.') % {
                                'type': mapping_type
                            }
                        )
                    )
                    created_count += 1
                
                # Mostrar detalles del mapeo
                preset = TableMapping.get_preset_mappings()[mapping_type]
                self.stdout.write(
                    f"  Tabla: {preset['table']} → Modelo: {preset['model']}"
                )
                self.stdout.write(
                    f"  Campos mapeados: {len(preset['fields'])}"
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        _('Error creando mapeo %(type)s: %(error)s') % {
                            'type': mapping_type,
                            'error': str(e)
                        }
                    )
                )
                logger.error(f"Error inicializando mapeo {mapping_type}: {e}")
        
        # Resumen final
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(_('Resumen de inicialización:'))
        )
        self.stdout.write(f"  Creados: {created_count}")
        self.stdout.write(f"  Actualizados: {updated_count}")
        self.stdout.write(f"  Omitidos: {skipped_count}")
        self.stdout.write(f"  Total procesados: {len(types_to_process)}")
        
        if created_count > 0 or updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    _('Mapeos predefinidos inicializados correctamente.')
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    _('No se crearon nuevos mapeos. Usar --force para recrear existentes.')
                )
            ) 