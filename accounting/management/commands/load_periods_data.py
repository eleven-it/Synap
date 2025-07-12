from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from core.models import Empresa
from django.contrib.auth import get_user_model

User = get_user_model()
from accounting.models import FiscalYear, AccountingPeriod


class Command(BaseCommand):
    help = 'Cargar datos de prueba para períodos contables y años fiscales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID de la empresa para cargar datos',
        )
        parser.add_argument(
            '--empresa-nombre',
            type=str,
            help='Nombre de la empresa para cargar datos',
        )
        parser.add_argument(
            '--years',
            type=int,
            default=3,
            help='Número de años fiscales a crear (default: 3)',
        )

    def handle(self, *args, **options):
        empresa_id = options.get('empresa_id')
        empresa_nombre = options.get('empresa_nombre')
        years = options.get('years')

        # Obtener empresa
        if empresa_id:
            try:
                empresa = Empresa.objects.get(id=empresa_id)
            except Empresa.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Empresa con ID {empresa_id} no encontrada')
                )
                return
        elif empresa_nombre:
            try:
                empresa = Empresa.objects.get(nombre=empresa_nombre)
            except Empresa.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Empresa "{empresa_nombre}" no encontrada')
                )
                return
        else:
            # Usar primera empresa disponible
            empresa = Empresa.objects.first()
            if not empresa:
                self.stdout.write(
                    self.style.ERROR('No hay empresas configuradas')
                )
                return

        # Obtener usuario para crear los registros
        user = User.objects.filter(is_active=True).first()
        if not user:
            self.stdout.write(
                self.style.ERROR('No hay usuarios activos disponibles')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Cargando datos de períodos para: {empresa.nombre}')
        )

        with transaction.atomic():
            # Crear años fiscales
            self._create_fiscal_years(empresa, user, years)

        self.stdout.write(
            self.style.SUCCESS('Datos de períodos contables cargados exitosamente')
        )

    def _create_fiscal_years(self, empresa, user, years):
        """Crear años fiscales con períodos"""
        current_year = timezone.now().year
        
        for i in range(years):
            year = current_year - 1 + i  # Empezar desde el año anterior
            
            # Crear año fiscal
            fiscal_year = FiscalYear.objects.create(
                empresa=empresa,
                name=f'Año Fiscal {year}',
                code=f'FY{year}',
                description=f'Año fiscal {year} - Período contable principal',
                date_from=date(year, 1, 1),
                date_to=date(year, 12, 31),
                is_active=True,
                period_length=1,  # Períodos mensuales
                auto_create_periods=True,
                allow_negative_cash=False,
                allow_negative_equity=False,
                created_by=user
            )
            
            self.stdout.write(f'  ✓ Creado año fiscal: {fiscal_year.name}')
            
            # Los períodos se crean automáticamente por el modelo
            periods_count = fiscal_year.periods.count()
            self.stdout.write(f'    ✓ Creados {periods_count} períodos automáticamente')

        # No crear períodos de ajuste ni apertura automáticamente (mejor práctica internacional)

    def _create_sample_entries(self, fiscal_year, user):
        """Crear algunos asientos de ejemplo para los períodos"""
        from accounting.models import Journal, JournalEntry, JournalEntryLine, ChartOfAccounts
        
        # Obtener diario y cuentas
        journal = Journal.objects.filter(empresa=fiscal_year.empresa, is_active=True).first()
        if not journal:
            return
        
        accounts = ChartOfAccounts.objects.filter(empresa=fiscal_year.empresa, is_active=True)[:5]
        if len(accounts) < 2:
            return
        
        # Crear algunos asientos de ejemplo
        for i, period in enumerate(fiscal_year.periods.filter(is_adjustment=False)[:3]):
            entry = JournalEntry.objects.create(
                empresa=fiscal_year.empresa,
                journal=journal,
                number=f'ENT-{fiscal_year.code}-{period.code}-{i+1:03d}',
                date=period.date_from + timedelta(days=15),
                reference=f'Asiento de ejemplo {i+1}',
                narration=f'Asiento de prueba para el período {period.name}',
                state='posted',
                created_by=user,
                posted_by=user,
                posted_at=timezone.now()
            )
            
            # Crear líneas del asiento
            JournalEntryLine.objects.create(
                entry=entry,
                account=accounts[0],
                debit=1000.00,
                name=f'Débito de ejemplo {i+1}'
            )
            
            JournalEntryLine.objects.create(
                entry=entry,
                account=accounts[1],
                credit=1000.00,
                name=f'Crédito de ejemplo {i+1}'
            )
            
            self.stdout.write(f'    ✓ Creado asiento de ejemplo: {entry.number}') 