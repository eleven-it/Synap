from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import uuid

# --- CONSTANTES ---
class AccountTypes:
    """Tipos de cuenta contable"""
    ASSETS = 'assets'           # Activos
    LIABILITIES = 'liabilities' # Pasivos
    EQUITY = 'equity'          # Patrimonio Neto
    INCOME = 'income'          # Ingresos
    EXPENSES = 'expenses'      # Gastos
    
    CHOICES = [
        (ASSETS, _('Assets')),
        (LIABILITIES, _('Liabilities')),
        (EQUITY, _('Equity')),
        (INCOME, _('Income')),
        (EXPENSES, _('Expenses')),
    ]

class JournalTypes:
    """Tipos de diario contable"""
    SALE = 'sale'              # Ventas
    PURCHASE = 'purchase'      # Compras
    CASH = 'cash'              # Caja
    BANK = 'bank'              # Banco
    MISCELLANEOUS = 'misc'     # Varios
    
    CHOICES = [
        (SALE, _('Sales')),
        (PURCHASE, _('Purchase')),
        (CASH, _('Cash')),
        (BANK, _('Bank')),
        (MISCELLANEOUS, _('Miscellaneous')),
    ]

class EntryStates:
    """Estados de los asientos contables"""
    DRAFT = 'draft'            # Borrador
    POSTED = 'posted'          # Publicado
    CANCELLED = 'cancelled'    # Cancelado
    
    CHOICES = [
        (DRAFT, _('Draft')),
        (POSTED, _('Posted')),
        (CANCELLED, _('Cancelled')),
    ]

# --- MODELOS DE CONTABILIDAD ---

class ChartOfAccounts(models.Model):
    """Plan de cuentas contables"""
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='chart_of_accounts')
    name = models.CharField(_('Name'), max_length=255)
    code = models.CharField(_('Code'), max_length=20, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    account_type = models.CharField(_('Account Type'), max_length=20, choices=AccountTypes.CHOICES)
    is_active = models.BooleanField(_('Active'), default=True)
    is_reconcilable = models.BooleanField(_('Reconcilable'), default=False)
    allow_reconciliation = models.BooleanField(_('Allow Reconciliation'), default=False)
    deprecated = models.BooleanField(_('Deprecated'), default=False)
    
    # Campos para cuentas de impuestos
    is_tax_account = models.BooleanField(_('Tax Account'), default=False)
    tax_type = models.CharField(_('Tax Type'), max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Chart of Accounts')
        verbose_name_plural = _('Chart of Accounts')
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        if self.parent and self.parent.account_type != self.account_type:
            raise ValidationError(_('Child account must have the same type as parent account.'))

    def get_balance(self, date=None):
        """Obtener saldo de la cuenta hasta una fecha"""
        return get_account_balance(self, date)

class Journal(models.Model):
    """Diario contable"""
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='journals')
    name = models.CharField(_('Name'), max_length=255)
    code = models.CharField(_('Code'), max_length=10, unique=True)
    journal_type = models.CharField(_('Journal Type'), max_length=10, choices=JournalTypes.CHOICES)
    default_account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, null=True, blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    sequence_id = models.IntegerField(_('Sequence ID'), default=1)
    
    # Configuración de impuestos
    tax_account = models.ForeignKey(
        ChartOfAccounts, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name='tax_journals',
        limit_choices_to={'is_tax_account': True}
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Journal')
        verbose_name_plural = _('Journals')
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

class JournalEntry(models.Model):
    """Asiento contable"""
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='journal_entries')
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT, related_name='entries')
    number = models.CharField(_('Entry Number'), max_length=32, unique=True)
    date = models.DateField(_('Entry Date'))
    reference = models.CharField(_('Reference'), max_length=255, blank=True)
    narration = models.TextField(_('Narration'), blank=True)
    state = models.CharField(_('State'), max_length=20, choices=EntryStates.CHOICES, default=EntryStates.DRAFT)
    
    # Campos de auditoría
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='entries_created')
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='entries_posted')
    posted_at = models.DateTimeField(_('Posted At'), null=True, blank=True)
    
    # Campos de origen (para integración con otros módulos)
    origin_model = models.CharField(_('Origin Model'), max_length=50, blank=True)
    origin_id = models.IntegerField(_('Origin ID'), null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Journal Entry')
        verbose_name_plural = _('Journal Entries')
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.number} - {self.date}"

    def clean(self):
        if self.state == EntryStates.POSTED and not self.posted_by:
            raise ValidationError(_('Posted entries must have a posted_by user.'))

    def post(self, user):
        """Publicar el asiento contable"""
        if self.state != EntryStates.DRAFT:
            raise ValidationError(_('Only draft entries can be posted.'))
        
        # Validar que el asiento esté balanceado
        total_debit = sum(line.debit for line in self.lines.all())
        total_credit = sum(line.credit for line in self.lines.all())
        
        if abs(total_debit - total_credit) > Decimal('0.01'):
            raise ValidationError(_('Journal entry must be balanced before posting.'))
        
        self.state = EntryStates.POSTED
        self.posted_by = user
        self.posted_at = timezone.now()
        self.save()

    def cancel(self, user):
        """Cancelar el asiento contable"""
        if self.state != EntryStates.POSTED:
            raise ValidationError(_('Only posted entries can be cancelled.'))
        
        self.state = EntryStates.CANCELLED
        self.save()

class JournalEntryLine(models.Model):
    """Línea de asiento contable"""
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, related_name='entry_lines')
    partner = models.ForeignKey('sales.Client', on_delete=models.PROTECT, null=True, blank=True)
    debit = models.DecimalField(_('Debit'), max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(_('Credit'), max_digits=15, decimal_places=2, default=0)
    amount_currency = models.DecimalField(_('Amount Currency'), max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.ForeignKey('core.Currency', on_delete=models.PROTECT, null=True, blank=True)
    name = models.CharField(_('Description'), max_length=255, blank=True)
    
    # Campos para impuestos
    tax_line = models.ForeignKey('TaxLine', on_delete=models.SET_NULL, null=True, blank=True, related_name='entry_lines')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Journal Entry Line')
        verbose_name_plural = _('Journal Entry Lines')
        ordering = ['id']

    def __str__(self):
        return f"{self.entry.number} - {self.account.code} - {self.debit}/{self.credit}"

    def clean(self):
        if self.debit > 0 and self.credit > 0:
            raise ValidationError(_('A line cannot have both debit and credit amounts.'))
        
        if self.debit == 0 and self.credit == 0:
            raise ValidationError(_('A line must have either debit or credit amount.'))

# --- MODELOS DE IMPUESTOS ---

class TaxGroup(models.Model):
    """Grupo de impuestos (ej: IVA, Impuestos Internos)"""
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='tax_groups')
    name = models.CharField(_('Name'), max_length=100)
    code = models.CharField(_('Code'), max_length=20, unique=True)
    description = models.TextField(_('Description'), blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    
    # Configuración contable
    account_id = models.ForeignKey(
        ChartOfAccounts, 
        on_delete=models.PROTECT, 
        related_name='tax_groups_sales',
        verbose_name=_('Sales Account')
    )
    refund_account_id = models.ForeignKey(
        ChartOfAccounts, 
        on_delete=models.PROTECT, 
        related_name='tax_groups_purchases',
        verbose_name=_('Purchase Account'),
        null=True, 
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Tax Group')
        verbose_name_plural = _('Tax Groups')
        ordering = ['name']

    def __str__(self):
        return self.name

class Tax(models.Model):
    """Impuesto individual"""
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='taxes')
    name = models.CharField(_('Name'), max_length=100)
    code = models.CharField(_('Code'), max_length=20, unique=True)
    description = models.TextField(_('Description'), blank=True)
    
    # Configuración del impuesto
    amount = models.DecimalField(_('Amount'), max_digits=10, decimal_places=4, default=0)
    amount_type = models.CharField(_('Amount Type'), max_length=20, choices=[
        ('percent', _('Percentage')),
        ('fixed', _('Fixed Amount')),
        ('group', _('Group of Taxes')),
        ('code', _('Python Code')),
    ], default='percent')
    
    # Configuración de aplicación
    price_include = models.BooleanField(_('Included in Price'), default=False)
    include_base_amount = models.BooleanField(_('Include Base Amount'), default=True)
    is_base_affected = models.BooleanField(_('Base Affected'), default=True)
    
    # Configuración contable
    account_id = models.ForeignKey(
        ChartOfAccounts, 
        on_delete=models.PROTECT, 
        related_name='taxes_sales',
        verbose_name=_('Sales Account')
    )
    refund_account_id = models.ForeignKey(
        ChartOfAccounts, 
        on_delete=models.PROTECT, 
        related_name='taxes_purchases',
        verbose_name=_('Purchase Account'),
        null=True, 
        blank=True
    )
    
    # Configuración de grupo
    tax_group = models.ForeignKey(TaxGroup, on_delete=models.PROTECT, related_name='taxes')
    sequence = models.IntegerField(_('Sequence'), default=10)
    
    # Configuración avanzada
    python_compute = models.TextField(_('Python Compute Code'), blank=True)
    python_applicable = models.TextField(_('Python Applicable Code'), blank=True)
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Tax')
        verbose_name_plural = _('Taxes')
        ordering = ['tax_group', 'sequence', 'name']

    def __str__(self):
        return f"{self.name} ({self.amount}%)"

    def compute_amount(self, base_amount, price_unit, quantity=1, product=None, partner=None):
        """Calcular el monto del impuesto"""
        if self.amount_type == 'percent':
            return base_amount * (self.amount / Decimal('100'))
        elif self.amount_type == 'fixed':
            return self.amount * quantity
        elif self.amount_type == 'group':
            # Implementar cálculo de grupo de impuestos
            return Decimal('0')
        elif self.amount_type == 'code':
            # Ejecutar código Python personalizado
            return self._execute_python_compute(base_amount, price_unit, quantity, product, partner)
        return Decimal('0')

    def _execute_python_compute(self, base_amount, price_unit, quantity, product, partner):
        """Ejecutar código Python para cálculo personalizado"""
        if not self.python_compute:
            return Decimal('0')
        
        # Crear contexto para el código Python
        context = {
            'base_amount': base_amount,
            'price_unit': price_unit,
            'quantity': quantity,
            'product': product,
            'partner': partner,
            'tax': self,
            'result': Decimal('0')
        }
        
        try:
            exec(self.python_compute, context)
            return context.get('result', Decimal('0'))
        except Exception as e:
            # Log del error
            print(f"Error executing tax compute code: {e}")
            return Decimal('0')

    def is_applicable(self, product=None, partner=None, date=None):
        """Verificar si el impuesto es aplicable"""
        if not self.is_active:
            return False
        
        if self.python_applicable:
            return self._execute_python_applicable(product, partner, date)
        
        return True

    def _execute_python_applicable(self, product, partner, date):
        """Ejecutar código Python para verificar aplicabilidad"""
        context = {
            'product': product,
            'partner': partner,
            'date': date,
            'tax': self,
            'result': True
        }
        
        try:
            exec(self.python_applicable, context)
            return context.get('result', True)
        except Exception as e:
            print(f"Error executing tax applicable code: {e}")
            return True

class TaxLine(models.Model):
    """Línea de impuesto en documentos (facturas, pedidos, etc.)"""
    tax = models.ForeignKey(Tax, on_delete=models.PROTECT, related_name='tax_lines')
    base_amount = models.DecimalField(_('Base Amount'), max_digits=15, decimal_places=2)
    tax_amount = models.DecimalField(_('Tax Amount'), max_digits=15, decimal_places=2)
    total_amount = models.DecimalField(_('Total Amount'), max_digits=15, decimal_places=2)
    
    # Campos de origen
    origin_model = models.CharField(_('Origin Model'), max_length=50)
    origin_id = models.IntegerField(_('Origin ID'))
    origin_line_id = models.IntegerField(_('Origin Line ID'), null=True, blank=True)
    
    # Campos de auditoría
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Tax Line')
        verbose_name_plural = _('Tax Lines')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tax.name} - {self.tax_amount}"

# --- MODELOS DE CONFIGURACIÓN FISCAL ---

class FiscalPosition(models.Model):
    """Posición fiscal (para diferentes jurisdicciones)"""
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='fiscal_positions')
    name = models.CharField(_('Name'), max_length=100)
    code = models.CharField(_('Code'), max_length=20, unique=True)
    description = models.TextField(_('Description'), blank=True)
    
    # Configuración de aplicación
    country_id = models.CharField(_('Country'), max_length=2, blank=True)
    state_id = models.CharField(_('State/Province'), max_length=64, blank=True)
    zip_from = models.CharField(_('Zip From'), max_length=24, blank=True)
    zip_to = models.CharField(_('Zip To'), max_length=24, blank=True)
    
    # Configuración de impuestos
    tax_ids = models.ManyToManyField(Tax, through='FiscalPositionTax', related_name='fiscal_positions', through_fields=('fiscal_position', 'tax_src_id'))
    
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Fiscal Position')
        verbose_name_plural = _('Fiscal Positions')
        ordering = ['name']

    def __str__(self):
        return self.name

class FiscalPositionTax(models.Model):
    """Mapeo de impuestos en posiciones fiscales"""
    fiscal_position = models.ForeignKey(FiscalPosition, on_delete=models.CASCADE, related_name='tax_mappings')
    tax_src_id = models.ForeignKey(Tax, on_delete=models.CASCADE, related_name='fiscal_position_src', verbose_name=_('Source Tax'))
    tax_dest_id = models.ForeignKey(Tax, on_delete=models.CASCADE, related_name='fiscal_position_dest', verbose_name=_('Destination Tax'))
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Fiscal Position Tax')
        verbose_name_plural = _('Fiscal Position Taxes')
        unique_together = ('fiscal_position', 'tax_src_id')

    def __str__(self):
        return f"{self.fiscal_position.name} - {self.tax_src_id.name} → {self.tax_dest_id.name}"


class FiscalYear(models.Model):
    """Año fiscal"""
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='fiscal_years')
    name = models.CharField(_('Name'), max_length=100)
    code = models.CharField(_('Code'), max_length=20, unique=True)
    description = models.TextField(_('Description'), blank=True)
    date_from = models.DateField(_('Start Date'))
    date_to = models.DateField(_('End Date'))
    is_active = models.BooleanField(_('Active'), default=True)
    is_closed = models.BooleanField(_('Closed'), default=False)
    period_length = models.IntegerField(_('Period Length (months)'), default=1)
    auto_create_periods = models.BooleanField(_('Auto Create Periods'), default=True)
    allow_negative_cash = models.BooleanField(_('Allow Negative Cash'), default=False)
    allow_negative_equity = models.BooleanField(_('Allow Negative Equity'), default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Fiscal Year')
        verbose_name_plural = _('Fiscal Years')
        ordering = ['-date_from']

    def __str__(self):
        return f"{self.name} ({self.date_from} - {self.date_to})"

    def clean(self):
        if self.date_from and self.date_to and self.date_from >= self.date_to:
            raise ValidationError(_('Start date must be before end date.'))

    def close(self, user):
        """Cerrar el año fiscal"""
        if self.is_closed:
            raise ValidationError(_('Fiscal year is already closed.'))
        # Verificar que todos los períodos estén cerrados
        open_periods = self.periods.filter(is_closed=False)
        if open_periods.exists():
            raise ValidationError(_('Cannot close fiscal year with open periods.'))
        self.is_closed = True
        self.save()

    def reopen(self, user):
        """Reabrir el año fiscal"""
        if not self.is_closed:
            raise ValidationError(_('Fiscal year is not closed.'))
        self.is_closed = False
        self.save()

    @property
    def is_current(self):
        """Verificar si es el año fiscal actual"""
        today = timezone.now().date()
        return self.date_from <= today <= self.date_to


class AccountingPeriod(models.Model):
    """Período contable"""
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='periods')
    name = models.CharField(_('Name'), max_length=100)
    code = models.CharField(_('Code'), max_length=20)
    description = models.TextField(_('Description'), blank=True)
    date_from = models.DateField(_('Start Date'))
    date_to = models.DateField(_('End Date'))
    is_active = models.BooleanField(_('Active'), default=True)
    is_closed = models.BooleanField(_('Closed'), default=False)
    is_adjustment = models.BooleanField(_('Adjustment Period'), default=False)
    sequence = models.IntegerField(_('Sequence'), default=0)
    allow_entries = models.BooleanField(_('Allow Entries'), default=True)
    allow_adjustments = models.BooleanField(_('Allow Adjustments'), default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Accounting Period')
        verbose_name_plural = _('Accounting Periods')
        ordering = ['fiscal_year', 'sequence', 'date_from']
        unique_together = ('fiscal_year', 'code')

    def __str__(self):
        return f"{self.name} ({self.date_from} - {self.date_to})"

    def clean(self):
        if self.date_from and self.date_to and self.date_from >= self.date_to:
            raise ValidationError(_('Start date must be before end date.'))
        
        if self.fiscal_year:
            if self.date_from < self.fiscal_year.date_from or self.date_to > self.fiscal_year.date_to:
                raise ValidationError(_('Period dates must be within fiscal year dates.'))

    def close(self, user):
        """Cerrar el período contable"""
        if self.is_closed:
            raise ValidationError(_('Accounting period is already closed.'))
        
        # Verificar que no haya asientos pendientes
        pending_entries = JournalEntry.objects.filter(
            empresa=self.fiscal_year.empresa,
            date__gte=self.date_from,
            date__lte=self.date_to,
            state=EntryStates.DRAFT
        )
        
        if pending_entries.exists():
            raise ValidationError(_('Cannot close period with pending entries.'))
        
        self.is_closed = True
        self.save()

    def reopen(self, user):
        """Reabrir el período contable"""
        if not self.is_closed:
            raise ValidationError(_('Accounting period is not closed.'))
        
        # Verificar que el año fiscal no esté cerrado
        if self.fiscal_year.is_closed:
            raise ValidationError(_('Cannot reopen period in a closed fiscal year.'))
        
        self.is_closed = False
        self.save()

    @property
    def entries_count(self):
        """Número de asientos en el período"""
        return JournalEntry.objects.filter(
            empresa=self.fiscal_year.empresa,
            date__gte=self.date_from,
            date__lte=self.date_to,
            state=EntryStates.POSTED
        ).count()

    @property
    def total_debits(self):
        """Total de débitos en el período"""
        from django.db.models import Sum
        result = JournalEntryLine.objects.filter(
            entry__empresa=self.fiscal_year.empresa,
            entry__date__gte=self.date_from,
            entry__date__lte=self.date_to,
            entry__state=EntryStates.POSTED
        ).aggregate(total=Sum('debit'))
        return result['total'] or 0

    @property
    def total_credits(self):
        """Total de créditos en el período"""
        from django.db.models import Sum
        result = JournalEntryLine.objects.filter(
            entry__empresa=self.fiscal_year.empresa,
            entry__date__gte=self.date_from,
            entry__date__lte=self.date_to,
            entry__state=EntryStates.POSTED
        ).aggregate(total=Sum('credit'))
        return result['total'] or 0

    @property
    def balance(self):
        """Balance del período (débitos - créditos)"""
        return self.total_debits - self.total_credits

    @property
    def duration_days(self):
        """Duración del período en días"""
        return (self.date_to - self.date_from).days + 1


def get_account_balance(account, date=None):
    """Obtener saldo de una cuenta hasta una fecha específica"""
    from decimal import Decimal
    
    if not date:
        date = timezone.now().date()
    
    # Obtener todas las líneas de asientos publicados hasta la fecha
    lines = JournalEntryLine.objects.filter(
        account=account,
        entry__state=EntryStates.POSTED,
        entry__date__lte=date
    )
    
    # Calcular saldo
    total_debit = sum(line.debit for line in lines)
    total_credit = sum(line.credit for line in lines)
    
    return total_debit - total_credit 