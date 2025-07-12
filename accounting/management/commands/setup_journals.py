from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from accounting.models import Journal, ChartOfAccounts
from core.models import Empresa


class Command(BaseCommand):
    help = _('Carga datos de prueba para diarios contables')

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help=_('ID de la empresa para la cual crear los diarios'),
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help=_('Eliminar todos los diarios existentes antes de crear nuevos'),
        )

    def handle(self, *args, **options):
        company_id = options['company_id']
        clear_existing = options['clear']

        try:
            # Obtener la empresa
            if company_id:
                company = Empresa.objects.get(id=company_id)
            else:
                # Usar la primera empresa disponible
                company = Empresa.objects.first()
                if not company:
                    self.stdout.write(
                        self.style.ERROR(_('No se encontró ninguna empresa. Crea una empresa primero.'))
                    )
                    return

            self.stdout.write(_('Configurando diarios para la empresa: {nombre}').format(nombre=company.nombre))

            # Eliminar diarios existentes si se solicita
            if clear_existing:
                Journal.objects.filter(empresa=company).delete()
                self.stdout.write(_('Diarios existentes eliminados.'))

            # Obtener cuentas por defecto
            cash_account = ChartOfAccounts.objects.filter(
                empresa=company,
                code__startswith='1100',  # Caja y bancos
                is_active=True
            ).first()

            bank_account = ChartOfAccounts.objects.filter(
                empresa=company,
                code__startswith='1110',  # Bancos
                is_active=True
            ).first()

            sales_account = ChartOfAccounts.objects.filter(
                empresa=company,
                code__startswith='4100',  # Ventas
                is_active=True
            ).first()

            purchases_account = ChartOfAccounts.objects.filter(
                empresa=company,
                code__startswith='6000',  # Compras
                is_active=True
            ).first()

            # Datos de diarios por defecto (códigos <= 10 caracteres)
            journals_data = [
                {
                    'code': 'VENTAS',
                    'name': _('Diario de Ventas'),
                    'journal_type': 'sale',
                    'default_account': sales_account,
                    'is_active': True,
                },
                {
                    'code': 'COMPRAS',
                    'name': _('Diario de Compras'),
                    'journal_type': 'purchase',
                    'default_account': purchases_account,
                    'is_active': True,
                },
                {
                    'code': 'CAJA',
                    'name': _('Diario de Caja'),
                    'journal_type': 'cash',
                    'default_account': cash_account,
                    'is_active': True,
                },
                {
                    'code': 'BANCO',
                    'name': _('Diario de Banco'),
                    'journal_type': 'bank',
                    'default_account': bank_account,
                    'is_active': True,
                },
                {
                    'code': 'MISC',
                    'name': _('Diario Misceláneo'),
                    'journal_type': 'misc',
                    'default_account': None,
                    'is_active': True,
                },
                {
                    'code': 'AJUSTES',
                    'name': _('Diario de Ajustes'),
                    'journal_type': 'misc',
                    'default_account': None,
                    'is_active': True,
                },
                {
                    'code': 'NOMINA',
                    'name': _('Diario de Nómina'),
                    'journal_type': 'misc',
                    'default_account': None,
                    'is_active': True,
                },
                {
                    'code': 'GASTOS',
                    'name': _('Diario de Gastos'),
                    'journal_type': 'misc',
                    'default_account': None,
                    'is_active': True,
                }
            ]

            created_count = 0
            updated_count = 0

            with transaction.atomic():
                for journal_data in journals_data:
                    # Verificar si el diario ya existe
                    journal, created = Journal.objects.get_or_create(
                        code=journal_data['code'],
                        empresa=company,
                        defaults={
                            'name': journal_data['name'],
                            'journal_type': journal_data['journal_type'],
                            'default_account': journal_data['default_account'],
                            'is_active': journal_data['is_active']
                        }
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(_('✓ Diario creado: {name} ({code})').format(name=journal.name, code=journal.code))
                        )
                    else:
                        # Actualizar diario existente
                        journal.name = journal_data['name']
                        journal.journal_type = journal_data['journal_type']
                        journal.default_account = journal_data['default_account']
                        journal.is_active = journal_data['is_active']
                        journal.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.WARNING(_('↻ Diario actualizado: {name} ({code})').format(name=journal.name, code=journal.code))
                        )

            # Resumen
            total_journals = Journal.objects.filter(empresa=company).count()
            
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS(_('RESUMEN DE DIARIOS')))
            self.stdout.write('='*50)
            self.stdout.write(_('Empresa: {nombre}').format(nombre=company.nombre))
            self.stdout.write(_('Diarios creados: {count}').format(count=created_count))
            self.stdout.write(_('Diarios actualizados: {count}').format(count=updated_count))
            self.stdout.write(_('Total de diarios: {count}').format(count=total_journals))
            
            # Mostrar lista de diarios
            self.stdout.write('\n' + _('Diarios disponibles:'))
            for journal in Journal.objects.filter(empresa=company).order_by('code'):
                status = '✓' if journal.is_active else '✗'
                self.stdout.write(f'  {status} {journal.code} - {journal.name} ({journal.get_journal_type_display()})')

            self.stdout.write(
                self.style.SUCCESS(_('\n✓ Configuración de diarios completada para {nombre}').format(nombre=company.nombre))
            )

        except Empresa.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(_('No se encontró la empresa con ID {id}').format(id=company_id))
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(_('Error al configurar diarios: {error}').format(error=str(e)))
            ) 