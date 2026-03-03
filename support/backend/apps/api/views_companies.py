"""API empresas: CRUD."""
from django.urls import path
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated

from apps.companies.models import Company
from apps.api.permissions import IsAdmin
from .serializers_companies import CompanySerializer


class CompanyListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = CompanySerializer
    queryset = Company.objects.all()


class CompanyDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = CompanySerializer
    queryset = Company.objects.all()


urlpatterns = [
    path("", CompanyListCreateView.as_view(), name="company-list"),
    path("<int:pk>/", CompanyDetailView.as_view(), name="company-detail"),
]
