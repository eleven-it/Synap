"""
Vistas DRF para configuración (Admin). Todas requieren IsAdmin.
"""
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from apps.api.permissions import IsAdmin
from apps.companies.models import Company
from apps.sla.models import SLAConfig
from apps.system_config.audit_utils import log_config_event
from apps.system_config.channel_tests import test_channel_config
from apps.system_config.ia_storage_tests import test_ia_config, test_storage_config
from apps.system_config.models import (
    BrandingConfig,
    ChannelConfig,
    ConfigStatus,
    IAConfig,
    NotificationsConfig,
    RAGConfig,
    SecurityConfig,
    StorageConfig,
)
from apps.system_config.serializers import (
    BrandingConfigSerializer,
    BrandingConfigWriteSerializer,
    ChannelConfigSerializer,
    ChannelConfigWriteSerializer,
    IAConfigSerializer,
    IAConfigWriteSerializer,
    NotificationsConfigSerializer,
    NotificationsConfigWriteSerializer,
    RAGConfigSerializer,
    RAGConfigWriteSerializer,
    SecurityConfigSerializer,
    SecurityConfigWriteSerializer,
    StorageConfigSerializer,
    StorageConfigWriteSerializer,
)
from apps.system_config.services import invalidate_config_cache

# --- Permisos comunes ---
ConfigPermission = [IsAuthenticated, IsAdmin]


# --- Canales ---

class ChannelConfigViewSet(ModelViewSet):
    permission_classes = ConfigPermission
    queryset = ChannelConfig.objects.all()
    serializer_class = ChannelConfigSerializer
    filterset_fields = ["company_id", "channel_type", "status"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ChannelConfigWriteSerializer
        return ChannelConfigSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        serializer.save()
        log_config_event(
            "config.updated",
            area="channels",
            object_id=serializer.instance.id,
            scope="company" if serializer.instance.company_id else "global",
            company_id=serializer.instance.company_id,
            actor_id=getattr(self.request.user, "id", None),
        )
        invalidate_config_cache("channel", serializer.instance.company_id)

    def perform_update(self, serializer):
        serializer.save()
        log_config_event(
            "config.updated",
            area="channels",
            object_id=serializer.instance.id,
            scope="company" if serializer.instance.company_id else "global",
            company_id=serializer.instance.company_id,
            actor_id=getattr(self.request.user, "id", None),
        )
        invalidate_config_cache("channel", serializer.instance.company_id)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        channel = self.get_object()
        result = test_channel_config(channel)
        log_config_event(
            "config.tested",
            area="channels",
            object_id=channel.id,
            scope="company" if channel.company_id else "global",
            company_id=channel.company_id,
            actor_id=getattr(request.user, "id", None),
            payload=result,
        )
        return Response(result)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        channel = self.get_object()
        channel.status = ConfigStatus.ACTIVE
        channel.save(update_fields=["status"])
        invalidate_config_cache("channel", channel.company_id)
        log_config_event(
            "config.activated",
            area="channels",
            object_id=channel.id,
            scope="company" if channel.company_id else "global",
            company_id=channel.company_id,
            actor_id=getattr(request.user, "id", None),
        )
        return Response({"success": True, "message": "Canal activado"})

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        channel = self.get_object()
        channel.status = ConfigStatus.DISABLED
        channel.save(update_fields=["status"])
        invalidate_config_cache("channel", channel.company_id)
        log_config_event(
            "config.deactivated",
            area="channels",
            object_id=channel.id,
            scope="company" if channel.company_id else "global",
            company_id=channel.company_id,
            actor_id=getattr(request.user, "id", None),
        )
        return Response({"success": True, "message": "Canal desactivado"})


# --- IA (singleton por scope: global o company_id) ---

class IAConfigViewSet(GenericViewSet):
    permission_classes = ConfigPermission
    queryset = IAConfig.objects.all()
    serializer_class = IAConfigSerializer

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return IAConfigWriteSerializer
        return IAConfigSerializer

    def list(self, request, *args, **kwargs):
        company_id = request.query_params.get("company_id")
        if company_id:
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                company_id = None
        else:
            company_id = None
        qs = IAConfig.objects.filter(company_id=company_id)
        instance = qs.first()
        if not instance:
            return Response([])
        serializer = self.get_serializer(instance)
        return Response([serializer.data])

    def _get_ia_instance(self, request):
        company_id = request.data.get("company_id") or request.query_params.get("company_id")
        if company_id is not None:
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                company_id = None
        qs = IAConfig.objects.filter(company_id=company_id)
        instance = qs.first()
        if not instance:
            instance = IAConfig.objects.create(company_id=company_id)
        return instance

    def partial_update(self, request, pk=None):
        instance = self._get_ia_instance(request) if pk is None else self.get_object()
        serializer = IAConfigWriteSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_config_event(
            "config.updated",
            area="ia",
            object_id=instance.id,
            scope="company" if instance.company_id else "global",
            company_id=instance.company_id,
            actor_id=getattr(request.user, "id", None),
        )
        invalidate_config_cache("ia", instance.company_id)
        return Response(IAConfigSerializer(instance).data)

    @action(detail=False, methods=["post"], url_path="test")
    def test_global(self, request):
        company_id = request.data.get("company_id") or request.query_params.get("company_id")
        if company_id is not None:
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                company_id = None
        qs = IAConfig.objects.filter(company_id=company_id)
        instance = qs.first()
        if not instance:
            return Response(
                {"success": False, "message": "No hay configuración IA para este ámbito"},
                status=status.HTTP_404_NOT_FOUND,
            )
        result = test_ia_config(instance)
        log_config_event(
            "config.tested",
            area="ia",
            object_id=instance.id,
            scope="company" if company_id else "global",
            company_id=company_id,
            actor_id=getattr(request.user, "id", None),
            payload=result,
        )
        return Response(result)


# --- RAG ---

class RAGConfigViewSet(GenericViewSet):
    permission_classes = ConfigPermission
    queryset = RAGConfig.objects.all()
    serializer_class = RAGConfigSerializer

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return RAGConfigWriteSerializer
        return RAGConfigSerializer

    def list(self, request, *args, **kwargs):
        company_id = request.query_params.get("company_id")
        if company_id:
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                company_id = None
        qs = RAGConfig.objects.filter(company_id=company_id)
        instance = qs.first()
        if not instance:
            return Response([])
        return Response([RAGConfigSerializer(instance).data])

    def _get_rag_instance(self, request):
        company_id = request.data.get("company_id") or request.query_params.get("company_id")
        if company_id is not None:
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                company_id = None
        qs = RAGConfig.objects.filter(company_id=company_id)
        instance = qs.first()
        if not instance:
            instance = RAGConfig.objects.create(company_id=company_id)
        return instance

    def partial_update(self, request, pk=None):
        instance = self._get_rag_instance(request) if pk is None else self.get_object()
        serializer = RAGConfigWriteSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_config_event(
            "config.updated",
            area="rag",
            object_id=instance.id,
            scope="company" if instance.company_id else "global",
            company_id=instance.company_id,
            actor_id=getattr(request.user, "id", None),
        )
        invalidate_config_cache("rag", instance.company_id)
        return Response(RAGConfigSerializer(instance).data)

    @action(detail=False, methods=["post"], url_path="ingest")
    def ingest(self, request):
        from apps.knowledge.services import KnowledgeIngestionService
        items = request.data.get("items") or []
        if not items:
            return Response(
                {"message": "items (lista) requerido", "created": 0, "updated": 0},
                status=status.HTTP_400_BAD_REQUEST,
            )
        svc = KnowledgeIngestionService()
        company_id = request.data.get("company_id")
        source_type = (request.data.get("source_type") or "manual")[:32]
        created, updated = svc.create_or_update_chunks(
            items=items,
            company_id=company_id,
            source_type=source_type,
        )
        return Response({"created": created, "updated": updated, "message": f"Ingesta: {created} creados, {updated} actualizados."})

    @action(detail=False, methods=["post"], url_path="reindex")
    def reindex(self, request):
        return Response(
            {"message": "Reindexación bajo demanda: encolar tarea Celery o ejecutar comando. (Stub OK)"},
            status=status.HTTP_200_OK,
        )


# --- Storage (singleton global) ---

class StorageConfigViewSet(GenericViewSet):
    permission_classes = ConfigPermission
    queryset = StorageConfig.objects.all()
    serializer_class = StorageConfigSerializer

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return StorageConfigWriteSerializer
        return StorageConfigSerializer

    def list(self, request, *args, **kwargs):
        instance = StorageConfig.objects.first()
        if not instance:
            return Response([])
        return Response([StorageConfigSerializer(instance).data])

    def partial_update(self, request, pk=None):
        instance = StorageConfig.objects.first()
        if not instance:
            instance = StorageConfig.objects.create()
        serializer = StorageConfigWriteSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_config_event(
            "config.updated",
            area="storage",
            object_id=instance.id,
            scope="global",
            actor_id=getattr(request.user, "id", None),
        )
        invalidate_config_cache("storage", None)
        return Response(StorageConfigSerializer(instance).data)

    @action(detail=False, methods=["post"], url_path="test")
    def test_storage(self, request):
        instance = StorageConfig.objects.first()
        if not instance:
            return Response(
                {"success": False, "message": "No hay configuración de storage"},
                status=status.HTTP_404_NOT_FOUND,
            )
        result = test_storage_config(instance)
        log_config_event(
            "config.tested",
            area="storage",
            object_id=instance.id,
            scope="global",
            actor_id=getattr(request.user, "id", None),
            payload=result,
        )
        return Response(result)


# --- Security ---

class SecurityConfigViewSet(GenericViewSet):
    permission_classes = ConfigPermission
    queryset = SecurityConfig.objects.all()
    serializer_class = SecurityConfigSerializer

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return SecurityConfigWriteSerializer
        return SecurityConfigSerializer

    def list(self, request, *args, **kwargs):
        instance = SecurityConfig.objects.first()
        if not instance:
            return Response([])
        return Response([SecurityConfigSerializer(instance).data])

    def partial_update(self, request, pk=None):
        instance = SecurityConfig.objects.first()
        if not instance:
            instance = SecurityConfig.objects.create()
        serializer = SecurityConfigWriteSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_config_event(
            "config.updated",
            area="security",
            object_id=instance.id,
            scope="global",
            actor_id=getattr(request.user, "id", None),
        )
        invalidate_config_cache("security", None)
        return Response(SecurityConfigSerializer(instance).data)

    @action(detail=False, methods=["post"], url_path="self-check")
    def self_check(self, request):
        checklist = {
            "rate_limits_configured": False,
            "anti_spam_enabled": False,
            "pii_warning_enabled": False,
        }
        instance = SecurityConfig.objects.first()
        if instance:
            checklist["rate_limits_configured"] = bool(instance.rate_limits_json)
            checklist["anti_spam_enabled"] = instance.anti_spam_enabled
            checklist["pii_warning_enabled"] = instance.pii_warning_enabled
        return Response({"checklist": checklist, "message": "Self-check completado"})


# --- Notifications ---

class NotificationsConfigViewSet(GenericViewSet):
    permission_classes = ConfigPermission
    queryset = NotificationsConfig.objects.all()
    serializer_class = NotificationsConfigSerializer

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return NotificationsConfigWriteSerializer
        return NotificationsConfigSerializer

    def list(self, request, *args, **kwargs):
        instance = NotificationsConfig.objects.first()
        if not instance:
            return Response([])
        return Response([NotificationsConfigSerializer(instance).data])

    def partial_update(self, request, pk=None):
        instance = NotificationsConfig.objects.first()
        if not instance:
            instance = NotificationsConfig.objects.create()
        serializer = NotificationsConfigWriteSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_config_event(
            "config.updated",
            area="notifications",
            object_id=instance.id,
            scope="global",
            actor_id=getattr(request.user, "id", None),
        )
        return Response(NotificationsConfigSerializer(instance).data)


# --- Branding ---

class BrandingConfigViewSet(GenericViewSet):
    permission_classes = ConfigPermission
    queryset = BrandingConfig.objects.all()
    serializer_class = BrandingConfigSerializer

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return BrandingConfigWriteSerializer
        return BrandingConfigSerializer

    def list(self, request, *args, **kwargs):
        company_id = request.query_params.get("company_id")
        if company_id:
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                company_id = None
        qs = BrandingConfig.objects.filter(company_id=company_id)
        instance = qs.first()
        if not instance:
            return Response([])
        return Response([BrandingConfigSerializer(instance).data])

    def partial_update(self, request, pk=None):
        company_id = request.data.get("company_id") or request.query_params.get("company_id")
        if company_id is not None:
            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                company_id = None
        qs = BrandingConfig.objects.filter(company_id=company_id)
        instance = qs.first()
        if not instance:
            serializer = BrandingConfigWriteSerializer(data={**request.data, "company_id": company_id})
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
        else:
            serializer = BrandingConfigWriteSerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        log_config_event(
            "config.updated",
            area="branding",
            object_id=instance.id,
            scope="company" if instance.company_id else "global",
            company_id=instance.company_id,
            actor_id=getattr(request.user, "id", None),
        )
        invalidate_config_cache("branding", instance.company_id)
        return Response(BrandingConfigSerializer(instance).data)


# --- SLA (CRUD modelo existente) ---

class SLAConfigSerializer(serializers.ModelSerializer):
    company_id = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all(), source="company")

    class Meta:
        model = SLAConfig
        fields = ("id", "company_id", "case_type", "response_time_minutes", "warning_pct", "created_at", "updated_at")


class SLAConfigViewSet(ModelViewSet):
    permission_classes = ConfigPermission
    queryset = SLAConfig.objects.all()
    serializer_class = SLAConfigSerializer
    filterset_fields = ["company_id"]
