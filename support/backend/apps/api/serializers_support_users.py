from rest_framework import serializers
from apps.support_users.models import SupportUser, ChannelIdentity
from apps.api.serializers_cases import CompanyMinimalSerializer


class ChannelIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelIdentity
        fields = ("id", "channel_type", "external_id", "metadata", "created_at")


class SupportUserSerializer(serializers.ModelSerializer):
    company = CompanyMinimalSerializer(read_only=True)
    channel_identities = ChannelIdentitySerializer(many=True, read_only=True)

    class Meta:
        model = SupportUser
        fields = ("id", "company", "name", "language", "is_authorized", "channel_identities", "created_at", "updated_at")
