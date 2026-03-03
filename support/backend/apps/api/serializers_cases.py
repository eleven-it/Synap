"""Serializers para casos y timeline."""
from rest_framework import serializers
from apps.cases.models import Case, Message, CaseStatus, CaseSummary
from apps.companies.models import Company


class CompanyMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ("id", "synap_id", "prefix", "language", "is_active")


class AgentMinimalSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


class CaseListSerializer(serializers.ModelSerializer):
    company = CompanyMinimalSerializer(read_only=True)
    assigned_to = serializers.SerializerMethodField()

    def get_assigned_to(self, obj):
        if not obj.assigned_to_id:
            return None
        u = obj.assigned_to
        return {"id": u.id, "username": u.username}

    class Meta:
        model = Case
        fields = (
            "id", "number_display", "status", "company",
            "assigned_to", "sla_started_at", "sla_due_at", "sla_paused_since",
            "sla_warning_sent_at", "sla_breached_at",
            "created_at", "updated_at",
        )


class CaseDetailSerializer(CaseListSerializer):
    class Meta(CaseListSerializer.Meta):
        fields = CaseListSerializer.Meta.fields


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "channel_type", "sender_type", "content", "direction", "created_at")


class CaseSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseSummary
        fields = ("id", "summary_text", "model_version", "created_at")


class CasePatchSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=CaseStatus.choices, required=False)
    assigned_to_id = serializers.IntegerField(required=False, allow_null=True)
