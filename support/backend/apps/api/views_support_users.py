"""API usuarios de soporte y canales."""
from django.urls import path
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.support_users.models import SupportUser
from apps.api.permissions import IsAdmin
from .serializers_support_users import SupportUserSerializer


class SupportUserListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = SupportUserSerializer
    queryset = SupportUser.objects.select_related("company").prefetch_related("channel_identities")
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["company"]


class SupportUserDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = SupportUserSerializer
    queryset = SupportUser.objects.select_related("company").prefetch_related("channel_identities")


urlpatterns = [
    path("", SupportUserListCreateView.as_view(), name="support-user-list"),
    path("<int:pk>/", SupportUserDetailView.as_view(), name="support-user-detail"),
]
