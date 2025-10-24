# coding: utf-8
from django.db import models
from core.models import Empresa
from sales.models import Client, SalesOrder, Invoice

class AccountReceivable(models.Model):
    company = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='accounts_receivable')
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='accounts_receivable')
    document_type = models.CharField(max_length=32, choices=[
        ('invoice', 'Invoice'),
        ('credit_note', 'Credit Note'),
        ('debit_note', 'Debit Note'),
        ('payment', 'Payment'),
        ('advance', 'Advance'),
        ('adjustment', 'Adjustment'),
    ])
    document_number = models.CharField(max_length=32)
    date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    state = models.CharField(max_length=32, choices=[
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ], default='open')
    related_invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.document_type} {self.document_number} - {self.client}"

class CreditLimitLog(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='credit_limit_logs')
    old_limit = models.DecimalField(max_digits=12, decimal_places=2)
    new_limit = models.DecimalField(max_digits=12, decimal_places=2)
    changed_by = models.ForeignKey('core.UsuarioExtendido', on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)

    def __str__(self):
        return f"Credit limit change for {self.client} at {self.changed_at}"

class FinancialReport(models.Model):
    company = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='financial_reports')
    name = models.CharField(max_length=128)
    report_type = models.CharField(max_length=32, choices=[
        ('aging', 'Aging'),
        ('balance', 'Balance'),
        ('sales', 'Sales'),
        ('collections', 'Collections'),
        ('custom', 'Custom'),
    ])
    parameters = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey('core.UsuarioExtendido', on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='financial_reports/', null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.report_type}) - {self.generated_at}"


class FinancialEntry(models.Model):
    """
    Tabla intermedia para consolidar entradas financieras de administraNET.
    Consolida ventas y compras de diferentes tablas en un modelo uniforme.
    """
    idempotency_key = models.CharField(max_length=128, unique=True)
    source_table = models.CharField(max_length=64)
    entry_type = models.CharField(
        max_length=10,
        choices=[
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
        ]
    )
    date = models.DateField()
    currency = models.CharField(max_length=8, default='ARS')
    net_amount = models.DecimalField(max_digits=14, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    cost_center = models.CharField(max_length=64, null=True, blank=True)
    counterparty_id = models.CharField(max_length=64, null=True, blank=True)
    source_id = models.CharField(max_length=64)
    source_updated_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['entry_type', 'date']),
            models.Index(fields=['source_updated_at']),
        ]
        verbose_name = 'Financial Entry'
        verbose_name_plural = 'Financial Entries'

    def __str__(self):
        return f"{self.entry_type} {self.source_id}" 