from rest_framework import serializers
from .models import AccountReceivable, CreditLimitLog, FinancialReport

class AccountReceivableSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountReceivable
        fields = '__all__'

class CreditLimitLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditLimitLog
        fields = '__all__'

class FinancialReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialReport
        fields = '__all__' 