"""API agentes (usuarios backoffice con rol)."""
from django.urls import path
from django.contrib.auth import get_user_model
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers

from apps.agents.models import AgentProfile
from apps.api.permissions import IsAgentOrAdmin

User = get_user_model()


class AgentSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    def get_role(self, obj):
        try:
            return obj.agent_profile.role
        except AgentProfile.DoesNotExist:
            return None

    class Meta:
        model = User
        fields = ("id", "username", "email", "role")


class AgentListView(ListAPIView):
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]
    serializer_class = AgentSerializer
    queryset = User.objects.filter(agent_profile__isnull=False).select_related("agent_profile")


urlpatterns = [
    path("", AgentListView.as_view(), name="agent-list"),
]
