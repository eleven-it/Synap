from rest_framework import viewsets
from .models import AccountReceivable, CreditLimitLog, FinancialReport
from .serializers import AccountReceivableSerializer, CreditLimitLogSerializer, FinancialReportSerializer

class AccountReceivableViewSet(viewsets.ModelViewSet):
    queryset = AccountReceivable.objects.all()
    serializer_class = AccountReceivableSerializer

class CreditLimitLogViewSet(viewsets.ModelViewSet):
    queryset = CreditLimitLog.objects.all()
    serializer_class = CreditLimitLogSerializer

class FinancialReportViewSet(viewsets.ModelViewSet):
    queryset = FinancialReport.objects.all()
    serializer_class = FinancialReportSerializer 