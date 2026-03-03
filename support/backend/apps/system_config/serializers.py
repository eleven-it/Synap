"""
Serializers de configuración: GET con campos sensibles enmascarados;
PATCH: si secreto viene vacío/null no se reemplaza.
"""
from rest_framework import serializers

from apps.companies.models import Company
from apps.system_config.crypto_utils import decrypt_json, encrypt_json, mask_secret
from apps.system_config.models import (
    BrandingConfig,
    ChannelConfig,
    ChannelType,
    ConfigStatus,
    IAConfig,
    NotificationsConfig,
    RAGConfig,
    SecurityConfig,
    StorageConfig,
)


# --- Canales ---

class ChannelConfigSerializer(serializers.ModelSerializer):
    """GET: config enmascarada (config_masked). PATCH: solo actualizar si valor no vacío."""
    config_masked = serializers.SerializerMethodField()
    company_id = serializers.PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        source="company",
        read_only=True,
    )

    class Meta:
        model = ChannelConfig
        fields = [
            "id",
            "company_id",
            "channel_type",
            "display_name",
            "status",
            "config_masked",
            "last_check_at",
            "last_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_check_at", "last_error", "created_at", "updated_at"]

    def get_config_masked(self, obj):
        if not obj.config_encrypted_json:
            return {}
        data = decrypt_json(obj.config_encrypted_json)
        if not data:
            return {}
        out = {}
        for k, v in data.items():
            if k in ("token", "access_token", "api_key", "app_secret", "password", "secret", "verify_token"):
                out[k] = mask_secret(str(v) if v else None)
            else:
                out[k] = v
        return out


class ChannelConfigWriteSerializer(serializers.ModelSerializer):
    """Para POST/PATCH: acepta config dict; cifra y guarda. Campos vacíos no reemplazan secretos."""
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        required=False,
        allow_null=True,
        source="company",
    )
    config = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = ChannelConfig
        fields = [
            "id",
            "company_id",
            "channel_type",
            "display_name",
            "status",
            "config",
        ]

    def _merge_encrypted(self, instance, new_config: dict | None):
        if new_config is None:
            return
        current = decrypt_json(instance.config_encrypted_json) or {}
        for k, v in new_config.items():
            if v is None or (isinstance(v, str) and not v.strip()):
                continue
            current[k] = v
        instance.config_encrypted_json = encrypt_json(current)

    def create(self, validated_data):
        config = validated_data.pop("config", None)
        validated_data.setdefault("status", ConfigStatus.DRAFT)
        obj = super().create(validated_data)
        if config:
            self._merge_encrypted(obj, config)
            obj.save(update_fields=["config_encrypted_json"])
        return obj

    def update(self, instance, validated_data):
        config = validated_data.pop("config", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if config is not None:
            self._merge_encrypted(instance, config)
        instance.save()
        return instance


# --- IA ---

class IAConfigSerializer(serializers.ModelSerializer):
    api_key_masked = serializers.SerializerMethodField()
    company_id = serializers.PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        source="company",
        read_only=True,
    )

    class Meta:
        model = IAConfig
        fields = [
            "id",
            "company_id",
            "provider",
            "model",
            "api_key_masked",
            "limits_json",
            "prompt_version_id",
            "status",
            "last_check_at",
            "last_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_check_at", "last_error", "created_at", "updated_at"]

    def get_api_key_masked(self, obj):
        if not obj.api_key_encrypted:
            return "****"
        dec = decrypt_json(obj.api_key_encrypted)
        if isinstance(dec, dict) and "api_key" in dec:
            return mask_secret(dec["api_key"])
        return mask_secret(dec if isinstance(dec, str) else None)


class IAConfigWriteSerializer(serializers.ModelSerializer):
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        required=False,
        allow_null=True,
        source="company",
    )
    api_key = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = IAConfig
        fields = [
            "id",
            "company_id",
            "provider",
            "model",
            "api_key",
            "limits_json",
            "prompt_version_id",
            "status",
        ]

    def update(self, instance, validated_data):
        api_key = validated_data.pop("api_key", None)
        if api_key is not None and isinstance(api_key, str) and api_key.strip():
            instance.api_key_encrypted = encrypt_json({"api_key": api_key.strip()})
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def create(self, validated_data):
        api_key = validated_data.pop("api_key", None)
        validated_data.setdefault("status", ConfigStatus.DRAFT)
        obj = super().create(validated_data)
        if api_key and str(api_key).strip():
            obj.api_key_encrypted = encrypt_json({"api_key": str(api_key).strip()})
            obj.save(update_fields=["api_key_encrypted"])
        return obj


# --- RAG ---

class RAGConfigSerializer(serializers.ModelSerializer):
    company_id = serializers.PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        source="company",
        read_only=True,
    )
    sources_enabled = serializers.JSONField(source="sources_enabled_json", required=False)

    class Meta:
        model = RAGConfig
        fields = [
            "id",
            "company_id",
            "top_k",
            "sources_enabled",
            "cache_ttl_seconds",
            "status",
            "last_ingest_at",
            "last_error",
            "created_at",
            "updated_at",
        ]


class RAGConfigWriteSerializer(serializers.ModelSerializer):
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        required=False,
        allow_null=True,
        source="company",
    )
    sources_enabled = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = RAGConfig
        fields = [
            "id",
            "company_id",
            "top_k",
            "sources_enabled",
            "cache_ttl_seconds",
            "status",
        ]

    def create(self, validated_data):
        sources = validated_data.pop("sources_enabled", None)
        if sources is not None:
            validated_data["sources_enabled_json"] = sources
        return super().create(validated_data)

    def update(self, instance, validated_data):
        sources = validated_data.pop("sources_enabled", None)
        if sources is not None:
            instance.sources_enabled_json = sources
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance


# --- Storage ---

class StorageConfigSerializer(serializers.ModelSerializer):
    access_key_masked = serializers.SerializerMethodField()
    allowed_content_types = serializers.JSONField(
        source="allowed_content_types_json",
        required=False,
    )

    class Meta:
        model = StorageConfig
        fields = [
            "id",
            "endpoint",
            "bucket",
            "region",
            "force_path_style",
            "access_key_masked",
            "max_size_bytes",
            "allowed_content_types",
            "retention_days",
            "status",
            "last_check_at",
            "last_error",
            "created_at",
            "updated_at",
        ]

    def get_access_key_masked(self, obj):
        if obj.access_key_masked:
            return mask_secret(obj.access_key_masked) if len(obj.access_key_masked) > 4 else "****"
        data = decrypt_json(obj.secret_encrypted) if obj.secret_encrypted else None
        if data and isinstance(data, dict) and data.get("access_key"):
            return mask_secret(data["access_key"])
        return "****"


class StorageConfigWriteSerializer(serializers.ModelSerializer):
    access_key = serializers.CharField(required=False, allow_blank=True, write_only=True)
    secret = serializers.CharField(required=False, allow_blank=True, write_only=True)
    allowed_content_types = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = StorageConfig
        fields = [
            "id",
            "endpoint",
            "bucket",
            "region",
            "force_path_style",
            "access_key",
            "secret",
            "max_size_bytes",
            "allowed_content_types",
            "retention_days",
            "status",
        ]

    def update(self, instance, validated_data):
        access_key = validated_data.pop("access_key", None)
        secret = validated_data.pop("secret", None)
        allowed = validated_data.pop("allowed_content_types", None)
        if allowed is not None:
            instance.allowed_content_types_json = allowed
        creds = decrypt_json(instance.secret_encrypted) or {}
        if isinstance(access_key, str) and access_key.strip():
            creds["access_key"] = access_key.strip()
            instance.access_key_masked = mask_secret(access_key.strip())
        if isinstance(secret, str) and secret.strip():
            creds["secret"] = secret.strip()
        if creds:
            instance.secret_encrypted = encrypt_json(creds)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def create(self, validated_data):
        access_key = validated_data.pop("access_key", None)
        secret = validated_data.pop("secret", None)
        allowed = validated_data.pop("allowed_content_types", None)
        if allowed is not None:
            validated_data["allowed_content_types_json"] = allowed
        validated_data.setdefault("status", ConfigStatus.DRAFT)
        obj = super().create(validated_data)
        creds = {}
        if isinstance(access_key, str) and access_key.strip():
            creds["access_key"] = access_key.strip()
            obj.access_key_masked = mask_secret(access_key.strip())
        if isinstance(secret, str) and secret.strip():
            creds["secret"] = secret.strip()
        if creds:
            obj.secret_encrypted = encrypt_json(creds)
        obj.save(update_fields=["access_key_masked", "secret_encrypted"])
        return obj


# --- Security ---

class SecurityConfigSerializer(serializers.ModelSerializer):
    rate_limits = serializers.JSONField(source="rate_limits_json", required=False)

    class Meta:
        model = SecurityConfig
        fields = [
            "id",
            "rate_limits",
            "anti_spam_enabled",
            "pii_warning_enabled",
            "created_at",
            "updated_at",
        ]


class SecurityConfigWriteSerializer(serializers.ModelSerializer):
    rate_limits = serializers.JSONField(source="rate_limits_json", required=False)

    class Meta:
        model = SecurityConfig
        fields = ["id", "rate_limits", "anti_spam_enabled", "pii_warning_enabled"]


# --- Notifications ---

class NotificationsConfigSerializer(serializers.ModelSerializer):
    escalation_emails = serializers.JSONField(
        source="escalation_emails_json",
        required=False,
    )

    class Meta:
        model = NotificationsConfig
        fields = [
            "id",
            "escalation_emails",
            "sla_warning_message_template",
            "sla_breach_message_template",
            "internal_alert_channel",
            "created_at",
            "updated_at",
        ]


class NotificationsConfigWriteSerializer(serializers.ModelSerializer):
    escalation_emails = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = NotificationsConfig
        fields = [
            "id",
            "escalation_emails",
            "sla_warning_message_template",
            "sla_breach_message_template",
            "internal_alert_channel",
        ]

    def update(self, instance, validated_data):
        emails = validated_data.pop("escalation_emails", None)
        if emails is not None:
            instance.escalation_emails_json = emails
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def create(self, validated_data):
        emails = validated_data.pop("escalation_emails", None)
        if emails is not None:
            validated_data["escalation_emails_json"] = emails
        return super().create(validated_data)


# --- Branding ---

class BrandingConfigSerializer(serializers.ModelSerializer):
    company_id = serializers.PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        source="company",
        read_only=True,
    )

    class Meta:
        model = BrandingConfig
        fields = [
            "id",
            "company_id",
            "assistant_name",
            "welcome_message",
            "default_language",
            "created_at",
            "updated_at",
        ]


class BrandingConfigWriteSerializer(serializers.ModelSerializer):
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(),
        required=False,
        allow_null=True,
        source="company",
    )

    class Meta:
        model = BrandingConfig
        fields = ["id", "company_id", "assistant_name", "welcome_message", "default_language"]
