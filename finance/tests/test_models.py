from django.test import TestCase
from finance.models import AccountReceivable, CreditLimitLog, FinancialReport
from core.models import Empresa
from sales.models import Client, SalesOrder, Invoice
from datetime import date

class AccountReceivableModelTest(TestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nombre='Test Company', razon_social='Test RS', identificador_fiscal='200', activa=True)
        self.client = Client.objects.create(name='Client AR', type='person', document_number='C200', is_active=True)
        self.ar = AccountReceivable.objects.create(company=self.company, client=self.client, document_type='invoice', document_number='INV001', date=date.today(), due_date=date.today(), amount=1000, balance=1000, state='open')

    def test_ar_str(self):
        self.assertIn('INV001', str(self.ar))

class CreditLimitLogModelTest(TestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nombre='Test Company', razon_social='Test RS', identificador_fiscal='201', activa=True)
        self.client = Client.objects.create(name='Client CL', type='person', document_number='C201', is_active=True)
        self.log = CreditLimitLog.objects.create(client=self.client, old_limit=500, new_limit=1000, changed_by='admin', changed_at=date.today())

    def test_log_str(self):
        self.assertIn('admin', str(self.log))

class FinancialReportModelTest(TestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nombre='Test Company', razon_social='Test RS', identificador_fiscal='202', activa=True)
        self.report = FinancialReport.objects.create(company=self.company, report_type='balance', period_start=date.today(), period_end=date.today(), created_at=date.today())

    def test_report_str(self):
        self.assertIn('balance', str(self.report)) 