from rest_framework import serializers
from apps.companies.models import Company
from apps.sla.models import SLAConfig


class SLAConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLAConfig
        fields = ("id", "case_type", "response_time_minutes", "warning_pct")


class CompanySerializer(serializers.ModelSerializer):
    sla_configs = SLAConfigSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        fields = ("id", "synap_id", "prefix", "language", "is_active", "sla_configs", "created_at", "updated_at")
