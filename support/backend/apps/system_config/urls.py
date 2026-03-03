"""URLs de configuración: /api/config/..."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.system_config.views import (
    BrandingConfigViewSet,
    ChannelConfigViewSet,
    IAConfigViewSet,
    NotificationsConfigViewSet,
    RAGConfigViewSet,
    SLAConfigViewSet,
    SecurityConfigViewSet,
    StorageConfigViewSet,
)

router = DefaultRouter()
router.register(r"channels", ChannelConfigViewSet, basename="config-channel")
router.register(r"sla", SLAConfigViewSet, basename="config-sla")

# Singleton-style: sin <pk> para GET/PATCH en la misma ruta
urlpatterns = [
    path("", include(router.urls)),
    path(
        "ia/",
        IAConfigViewSet.as_view({"get": "list", "patch": "partial_update"}),
        name="config-ia",
    ),
    path(
        "ia/test/",
        IAConfigViewSet.as_view({"post": "test_global"}),
        name="config-ia-test",
    ),
    path(
        "rag/",
        RAGConfigViewSet.as_view({"get": "list", "patch": "partial_update"}),
        name="config-rag",
    ),
    path(
        "rag/ingest/",
        RAGConfigViewSet.as_view({"post": "ingest"}),
        name="config-rag-ingest",
    ),
    path(
        "rag/reindex/",
        RAGConfigViewSet.as_view({"post": "reindex"}),
        name="config-rag-reindex",
    ),
    path(
        "storage/",
        StorageConfigViewSet.as_view({"get": "list", "patch": "partial_update"}),
        name="config-storage",
    ),
    path(
        "storage/test/",
        StorageConfigViewSet.as_view({"post": "test_storage"}),
        name="config-storage-test",
    ),
    path(
        "security/",
        SecurityConfigViewSet.as_view({"get": "list", "patch": "partial_update"}),
        name="config-security",
    ),
    path(
        "security/self-check/",
        SecurityConfigViewSet.as_view({"post": "self_check"}),
        name="config-security-self-check",
    ),
    path(
        "notifications/",
        NotificationsConfigViewSet.as_view({"get": "list", "patch": "partial_update"}),
        name="config-notifications",
    ),
    path(
        "branding/",
        BrandingConfigViewSet.as_view({"get": "list", "patch": "partial_update"}),
        name="config-branding",
    ),
]
