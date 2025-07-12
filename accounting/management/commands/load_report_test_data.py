from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import datetime, timedelta
import random

from accounting.models import (
    ChartOfAccounts, Journal, JournalEntry, JournalEntryLine,
    Tax, TaxGroup, TaxLine, FiscalPosition, EntryStates, AccountTypes
)
from core.models import Empresa
from django.contrib.auth import get_user_model

Usuario = get_user_model()


class Command(BaseCommand):
    help = 'Cargar datos de prueba para reportes contables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa',
            type=str,
            help='Nombre de la empresa para cargar datos',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpiar datos existentes antes de cargar',
        )

    def handle(self, *args, **options):
        empresa_nombre = options['empresa']
        clear_data = options['clear']

        # Obtener empresa
        try:
            if empresa_nombre:
                empresa = Empresa.objects.get(nombre=empresa_nombre)
            else:
                empresa = Empresa.objects.first()
                if not empresa:
                    self.stdout.write(
                        self.style.ERROR('No se encontró ninguna empresa. Cree una empresa primero.')
                    )
                    return
        except Empresa.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'No se encontró la empresa: {empresa_nombre}')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Cargando datos de prueba para empresa: {empresa.nombre}')
        )

        # Obtener usuario activo
        try:
            usuario = Usuario.objects.filter(is_active=True).first()
            if not usuario:
                self.stdout.write(
                    self.style.ERROR('No se encontró ningún usuario activo.')
                )
                return
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error al obtener usuario: {e}')
            )
            return

        with transaction.atomic():
            if clear_data:
                self.stdout.write('Limpiando datos existentes...')
                # Limpiar datos de prueba (solo líneas y asientos, no cuentas ni diarios)
                JournalEntryLine.objects.filter(entry__empresa=empresa).delete()
                JournalEntry.objects.filter(empresa=empresa).delete()
                TaxLine.objects.filter(tax__empresa=empresa).delete()

            # Verificar que existan cuentas y diarios
            cuentas = ChartOfAccounts.objects.filter(empresa=empresa, is_active=True)
            if not cuentas.exists():
                self.stdout.write(
                    self.style.ERROR('No se encontraron cuentas activas. Ejecute primero load_accounting_data.')
                )
                return

            diarios = Journal.objects.filter(empresa=empresa, is_active=True)
            if not diarios.exists():
                self.stdout.write(
                    self.style.ERROR('No se encontraron diarios activos. Ejecute primero load_journal_data.')
                )
                return

            # Crear datos de prueba para reportes
            self.create_test_entries(empresa, usuario, cuentas, diarios)
            self.create_test_tax_lines(empresa, usuario)

        self.stdout.write(
            self.style.SUCCESS('Datos de prueba para reportes cargados exitosamente.')
        )

    def create_test_entries(self, empresa, usuario, cuentas, diarios):
        """Crear asientos de prueba para diferentes períodos"""
        self.stdout.write('Creando asientos de prueba...')

        # Obtener cuentas por tipo
        cuentas_activo = cuentas.filter(account_type=AccountTypes.ASSETS)
        cuentas_pasivo = cuentas.filter(account_type=AccountTypes.LIABILITIES)
        cuentas_patrimonio = cuentas.filter(account_type=AccountTypes.EQUITY)
        cuentas_ingreso = cuentas.filter(account_type=AccountTypes.INCOME)
        cuentas_gasto = cuentas.filter(account_type=AccountTypes.EXPENSES)

        # Crear asientos para diferentes meses
        meses_atras = [0, 1, 2, 3]  # Mes actual y 3 meses atrás
        
        for mes in meses_atras:
            fecha_base = timezone.now().date() - timedelta(days=30 * mes)
            
            # Asiento 1: Compra de mercancías
            if cuentas_activo.exists() and cuentas_pasivo.exists():
                self.create_entry(
                    empresa, usuario, diarios.first(),
                    fecha_base,
                    "Compra de mercancías",
                    [
                        (cuentas_activo.first(), Decimal('5000.00'), Decimal('0.00')),
                        (cuentas_pasivo.first(), Decimal('0.00'), Decimal('5000.00')),
                    ]
                )

            # Asiento 2: Venta de mercancías
            if cuentas_activo.exists() and cuentas_ingreso.exists():
                self.create_entry(
                    empresa, usuario, diarios.first(),
                    fecha_base + timedelta(days=5),
                    "Venta de mercancías",
                    [
                        (cuentas_activo.first(), Decimal('8000.00'), Decimal('0.00')),
                        (cuentas_ingreso.first(), Decimal('0.00'), Decimal('8000.00')),
                    ]
                )

            # Asiento 3: Pago de gastos
            if cuentas_activo.exists() and cuentas_gasto.exists():
                self.create_entry(
                    empresa, usuario, diarios.first(),
                    fecha_base + timedelta(days=10),
                    "Pago de gastos operativos",
                    [
                        (cuentas_gasto.first(), Decimal('2000.00'), Decimal('0.00')),
                        (cuentas_activo.first(), Decimal('0.00'), Decimal('2000.00')),
                    ]
                )

            # Asiento 4: Depósito en banco
            if cuentas_activo.count() >= 2:
                cuentas_banco = cuentas_activo.filter(name__icontains='banco').first()
                cuentas_caja = cuentas_activo.filter(name__icontains='caja').first()
                
                if cuentas_banco and cuentas_caja:
                    self.create_entry(
                        empresa, usuario, diarios.first(),
                        fecha_base + timedelta(days=15),
                        "Depósito en banco",
                        [
                            (cuentas_banco, Decimal('3000.00'), Decimal('0.00')),
                            (cuentas_caja, Decimal('0.00'), Decimal('3000.00')),
                        ]
                    )

            # Asiento 5: Préstamo bancario
            if cuentas_activo.exists() and cuentas_pasivo.exists():
                self.create_entry(
                    empresa, usuario, diarios.first(),
                    fecha_base + timedelta(days=20),
                    "Préstamo bancario",
                    [
                        (cuentas_activo.first(), Decimal('10000.00'), Decimal('0.00')),
                        (cuentas_pasivo.first(), Decimal('0.00'), Decimal('10000.00')),
                    ]
                )

    def create_entry(self, empresa, usuario, diario, fecha, descripcion, lineas):
        """Crear un asiento contable"""
        try:
            entry = JournalEntry.objects.create(
                empresa=empresa,
                journal=diario,
                number=f"TEST-{fecha.strftime('%Y%m%d')}-{random.randint(1000, 9999)}",
                date=fecha,
                reference=descripcion,
                narration=descripcion,
                state=EntryStates.POSTED,
                created_by=usuario
            )

            for cuenta, debe, haber in lineas:
                JournalEntryLine.objects.create(
                    entry=entry,
                    account=cuenta,
                    debit=debe,
                    credit=haber,
                    name=f"Línea de {descripcion}"
                )

            self.stdout.write(f'  ✓ Asiento creado: {descripcion} ({fecha})')

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'  ⚠ Error creando asiento: {e}')
            )

    def create_test_tax_lines(self, empresa, usuario):
        """Crear líneas de impuesto de prueba"""
        self.stdout.write('Creando líneas de impuesto de prueba...')

        # Obtener impuestos activos
        impuestos = Tax.objects.filter(empresa=empresa, is_active=True)
        if not impuestos.exists():
            self.stdout.write(
                self.style.WARNING('No se encontraron impuestos activos. Saltando líneas de impuesto.')
            )
            return

        # Crear líneas de impuesto para diferentes fechas
        for i in range(10):
            fecha = timezone.now().date() - timedelta(days=i * 3)
            impuesto = impuestos.first()
            
            try:
                base_amount = Decimal(random.uniform(100, 1000))
                tax_amount = base_amount * (impuesto.amount / Decimal('100'))
                total_amount = base_amount + tax_amount

                TaxLine.objects.create(
                    tax=impuesto,
                    base_amount=base_amount,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                    origin_model='test',
                    origin_id=i+1
                )

                self.stdout.write(f'  ✓ Línea de impuesto creada: {impuesto.name} ({fecha})')

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠ Error creando línea de impuesto: {e}')
                ) 