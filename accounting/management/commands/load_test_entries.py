from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta
import random

from accounting.models import JournalEntry, JournalEntryLine, Journal, ChartOfAccounts, EntryStates
from core.models import Empresa
from core.models.models import UsuarioExtendido


class Command(BaseCommand):
    help = 'Cargar datos de prueba para asientos contables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company',
            type=str,
            help='Nombre de la empresa para la cual crear los asientos',
        )
        parser.add_argument(
            '--entries',
            type=int,
            default=50,
            help='Número de asientos a crear (default: 50)',
        )

    def handle(self, *args, **options):
        company_name = options['company']
        num_entries = options['entries']

        try:
            # Obtener la empresa
            if company_name:
                empresa = Empresa.objects.get(name=company_name)
            else:
                empresa = Empresa.objects.first()
                if not empresa:
                    self.stdout.write(
                        self.style.ERROR('No se encontró ninguna empresa. Crea una empresa primero.')
                    )
                    return

            self.stdout.write(f'Creando {num_entries} asientos para la empresa: {empresa.nombre}')

            # Obtener diarios y cuentas disponibles
            journals = Journal.objects.filter(empresa=empresa, is_active=True)
            if not journals.exists():
                self.stdout.write(
                    self.style.ERROR('No se encontraron diarios activos. Crea diarios primero.')
                )
                return

            accounts = ChartOfAccounts.objects.filter(empresa=empresa, is_active=True)
            if not accounts.exists():
                self.stdout.write(
                    self.style.ERROR('No se encontraron cuentas activas. Crea cuentas primero.')
                )
                return

            # Buscar usuario activo relacionado a la empresa, o cualquier usuario activo
            user = None
            try:
                # Si hay relación M2M entre empresa y usuario, usarla (ajusta si tu modelo lo permite)
                if hasattr(empresa, 'usuarios') and empresa.usuarios.exists():
                    user = empresa.usuarios.filter(is_active=True).first()
                if not user:
                    user = UsuarioExtendido.objects.filter(is_active=True).first()
            except Exception:
                user = UsuarioExtendido.objects.filter(is_active=True).first()
            if not user:
                self.stdout.write(
                    self.style.ERROR('No se encontró ningún usuario activo. Crea un usuario primero.')
                )
                return

            # Tipos de asientos de ejemplo
            entry_templates = [
                {
                    'name': 'Venta de mercancías',
                    'narration': 'Venta de productos terminados',
                    'lines': [
                        {'account_type': 'assets', 'debit': 0, 'credit': 0, 'description': 'Caja'},
                        {'account_type': 'income', 'debit': 0, 'credit': 0, 'description': 'Ventas'},
                    ]
                },
                {
                    'name': 'Compra de mercancías',
                    'narration': 'Compra de materias primas',
                    'lines': [
                        {'account_type': 'assets', 'debit': 0, 'credit': 0, 'description': 'Inventario'},
                        {'account_type': 'liabilities', 'debit': 0, 'credit': 0, 'description': 'Proveedores'},
                    ]
                },
                {
                    'name': 'Pago de servicios',
                    'narration': 'Pago de servicios públicos',
                    'lines': [
                        {'account_type': 'expenses', 'debit': 0, 'credit': 0, 'description': 'Servicios'},
                        {'account_type': 'assets', 'debit': 0, 'credit': 0, 'description': 'Banco'},
                    ]
                },
                {
                    'name': 'Depreciación de activos',
                    'narration': 'Depreciación mensual de equipos',
                    'lines': [
                        {'account_type': 'expenses', 'debit': 0, 'credit': 0, 'description': 'Depreciación'},
                        {'account_type': 'assets', 'debit': 0, 'credit': 0, 'description': 'Depreciación Acumulada'},
                    ]
                },
                {
                    'name': 'Pago de nómina',
                    'narration': 'Pago de salarios del personal',
                    'lines': [
                        {'account_type': 'expenses', 'debit': 0, 'credit': 0, 'description': 'Gastos de Personal'},
                        {'account_type': 'liabilities', 'debit': 0, 'credit': 0, 'description': 'Impuestos por Pagar'},
                        {'account_type': 'assets', 'debit': 0, 'credit': 0, 'description': 'Banco'},
                    ]
                },
            ]

            entries_created = 0
            entries_updated = 0

            with transaction.atomic():
                for i in range(num_entries):
                    # Seleccionar template aleatorio
                    template = random.choice(entry_templates)
                    
                    # Generar número de asiento único
                    entry_number = f"JE{timezone.now().year}{str(i+1).zfill(4)}"
                    
                    # Verificar si ya existe
                    if JournalEntry.objects.filter(empresa=empresa, number=entry_number).exists():
                        entries_updated += 1
                        continue

                    # Generar fecha aleatoria en los últimos 6 meses
                    days_ago = random.randint(0, 180)
                    entry_date = date.today() - timedelta(days=days_ago)
                    
                    # Seleccionar diario aleatorio
                    journal = random.choice(journals)
                    
                    # Crear asiento
                    entry = JournalEntry.objects.create(
                        empresa=empresa,
                        journal=journal,
                        number=entry_number,
                        date=entry_date,
                        reference=f"Ref-{entry_number}",
                        narration=template['narration'],
                        state=random.choice([EntryStates.DRAFT, EntryStates.POSTED]),
                        created_by=user,
                    )

                    # Crear líneas del asiento
                    total_amount = Decimal(random.randint(1000, 50000))
                    
                    for j, line_template in enumerate(template['lines']):
                        # Buscar cuenta del tipo especificado
                        account_type = line_template['account_type']
                        available_accounts = accounts.filter(account_type=account_type)
                        
                        if not available_accounts.exists():
                            # Si no hay cuentas del tipo específico, usar cualquier cuenta
                            available_accounts = accounts
                        
                        account = random.choice(available_accounts)
                        
                        # Calcular montos
                        if j == 0:  # Primera línea
                            if line_template['debit'] > 0:
                                debit_amount = total_amount
                                credit_amount = 0
                            elif line_template['credit'] > 0:
                                debit_amount = 0
                                credit_amount = total_amount
                            else:
                                # Determinar si es débito o crédito basado en el tipo de cuenta
                                if account_type in ['assets', 'expenses']:
                                    debit_amount = total_amount
                                    credit_amount = 0
                                else:
                                    debit_amount = 0
                                    credit_amount = total_amount
                        else:  # Líneas adicionales
                            if j == len(template['lines']) - 1:  # Última línea
                                # Balancear el asiento
                                previous_debit = sum(line.debit for line in entry.lines.all())
                                previous_credit = sum(line.credit for line in entry.lines.all())
                                
                                if previous_debit > previous_credit:
                                    debit_amount = 0
                                    credit_amount = previous_debit - previous_credit
                                else:
                                    debit_amount = previous_credit - previous_debit
                                    credit_amount = 0
                            else:
                                # Línea intermedia
                                line_amount = total_amount / len(template['lines'])
                                if account_type in ['assets', 'expenses']:
                                    debit_amount = line_amount
                                    credit_amount = 0
                                else:
                                    debit_amount = 0
                                    credit_amount = line_amount

                        # Crear línea
                        JournalEntryLine.objects.create(
                            entry=entry,
                            account=account,
                            debit=debit_amount,
                            credit=credit_amount,
                            name=line_template['description'],
                        )

                    # Si el asiento está publicado, asignar posted_by
                    if entry.state == EntryStates.POSTED:
                        entry.posted_by = user
                        entry.posted_at = entry.created_at
                        entry.save()

                    entries_created += 1

                    if (i + 1) % 10 == 0:
                        self.stdout.write(f'Progreso: {i + 1}/{num_entries} asientos creados')

            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Completado: {entries_created} asientos creados, {entries_updated} actualizados'
                )
            )
            
            # Mostrar estadísticas
            total_entries = JournalEntry.objects.filter(empresa=empresa).count()
            draft_entries = JournalEntry.objects.filter(empresa=empresa, state=EntryStates.DRAFT).count()
            posted_entries = JournalEntry.objects.filter(empresa=empresa, state=EntryStates.POSTED).count()
            
            self.stdout.write(f'\n📊 Estadísticas:')
            self.stdout.write(f'   • Total de asientos: {total_entries}')
            self.stdout.write(f'   • Borradores: {draft_entries}')
            self.stdout.write(f'   • Publicados: {posted_entries}')

        except Empresa.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'No se encontró la empresa: {company_name}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error al crear asientos: {str(e)}')
            ) 