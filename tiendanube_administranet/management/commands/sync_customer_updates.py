"""
Comando para sincronización periódica de actualizaciones de clientes.
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from tiendanube_administranet.services.periodic_sync_service import PeriodicSyncService
from tiendanube_administranet.models import TiendanubeConfig, AdministraNETConfig

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza actualizaciones de clientes desde TiendaNube hacia AdministraNET.'

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=24,
                            help='Horas hacia atrás para buscar clientes modificados (default: 24).')
        parser.add_argument('--validate', action='store_true',
                            help='Solo validar consistencia de datos sin sincronizar.')
        parser.add_argument('--fix', action='store_true',
                            help='Corregir inconsistencias encontradas.')
        parser.add_argument('--prefer-tiendanube', action='store_true',
                            help='Usar datos de TiendaNube como fuente de verdad al corregir.')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🔄 Iniciando sincronización periódica de clientes..."))
        self.stdout.write(f"   📊 Horas hacia atrás: {options['hours']}")
        self.stdout.write(f"   📊 Validar: {options['validate']}")
        self.stdout.write(f"   📊 Corregir: {options['fix']}")
        self.stdout.write(f"   📊 Preferir TiendaNube: {options['prefer_tiendanube']}")

        try:
            # Obtener configuraciones
            tiendanube_config = TiendanubeConfig.objects.first()
            if not tiendanube_config:
                raise CommandError("❌ No se encontró configuración de TiendaNube. Por favor, configúrela primero.")
            
            adminet_config = AdministraNETConfig.objects.first()
            if not adminet_config:
                raise CommandError("❌ No se encontró configuración de AdministraNET. Por favor, configúrela primero.")
            
            self.stdout.write(self.style.SUCCESS(f"✅ Configuración TiendaNube: {tiendanube_config.store_id}"))
            self.stdout.write(self.style.SUCCESS(f"✅ Configuración AdministraNET: {adminet_config.host}:{adminet_config.port}/{adminet_config.database}"))

            # Crear servicio de sincronización periódica
            sync_service = PeriodicSyncService(tiendanube_config, adminet_config)

            if options['validate']:
                # Solo validar consistencia
                self.stdout.write("🔍 Validando consistencia de datos...")
                result = sync_service.validate_customer_data_consistency()
                
                if result['success']:
                    self.stdout.write(self.style.SUCCESS("✅ Validación completada!"))
                    self.stdout.write(f"   📈 Total verificados: {result['total_checked']}")
                    self.stdout.write(f"   ❌ Inconsistencias: {result['inconsistency_count']}")
                    
                    if result['inconsistencies']:
                        self.stdout.write("\n📋 Inconsistencias encontradas:")
                        for i, inconsistency in enumerate(result['inconsistencies'][:10], 1):  # Mostrar solo las primeras 10
                            self.stdout.write(f"   {i}. Cliente {inconsistency.get('tiendanube_id')} (Adminet: {inconsistency.get('adminet_codigo')})")
                            if 'inconsistencies' in inconsistency:
                                for field_issue in inconsistency['inconsistencies']:
                                    self.stdout.write(f"      - {field_issue['field']}: TiendaNube='{field_issue['tiendanube']}' vs Adminet='{field_issue['adminet']}'")
                            else:
                                self.stdout.write(f"      - {inconsistency.get('issue', 'Error desconocido')}")
                        
                        if len(result['inconsistencies']) > 10:
                            self.stdout.write(f"   ... y {len(result['inconsistencies']) - 10} más")
                else:
                    raise CommandError(f"❌ Error en validación: {result['message']}")
            
            elif options['fix']:
                # Corregir inconsistencias
                self.stdout.write("🔧 Corrigiendo inconsistencias...")
                
                # Primero validar para obtener inconsistencias
                validation_result = sync_service.validate_customer_data_consistency()
                if not validation_result['success']:
                    raise CommandError(f"❌ Error validando datos: {validation_result['message']}")
                
                if validation_result['inconsistency_count'] == 0:
                    self.stdout.write(self.style.SUCCESS("✅ No se encontraron inconsistencias para corregir"))
                    return
                
                # Corregir inconsistencias
                fix_result = sync_service.fix_customer_inconsistencies(
                    validation_result['inconsistencies'],
                    prefer_tiendanube=options['prefer_tiendanube']
                )
                
                if fix_result['success']:
                    self.stdout.write(self.style.SUCCESS("✅ Corrección completada!"))
                    self.stdout.write(f"   ✅ Corregidas: {fix_result['fixed_count']}")
                    self.stdout.write(f"   ❌ Fallidas: {fix_result['failed_count']}")
                    
                    if fix_result['errors']:
                        self.stdout.write("\n❌ Errores durante la corrección:")
                        for error in fix_result['errors'][:5]:  # Mostrar solo los primeros 5 errores
                            self.stdout.write(f"   - {error}")
                        if len(fix_result['errors']) > 5:
                            self.stdout.write(f"   ... y {len(fix_result['errors']) - 5} más")
                else:
                    raise CommandError(f"❌ Error en corrección: {fix_result['message']}")
            
            else:
                # Sincronización normal
                result = sync_service.sync_customer_updates_from_tiendanube(hours_back=options['hours'])

                if result['success']:
                    self.stdout.write(self.style.SUCCESS("✅ Sincronización completada exitosamente!"))
                    self.stdout.write(f"   📈 Total procesados: {result['total_processed']}")
                    self.stdout.write(f"   ✅ Exitosos: {result['successful']}")
                    self.stdout.write(f"   ❌ Fallidos: {result['failed']}")
                    self.stdout.write(f"   ⏭️  Omitidos: {result['skipped']}")
                    self.stdout.write(f"   📋 Log ID: {result['sync_log_id']}")
                else:
                    raise CommandError(f"❌ Error ejecutando sincronización: {result['message']}")

        except CommandError as e:
            self.stderr.write(self.style.ERROR(str(e)))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error inesperado durante la sincronización: {e}"))



