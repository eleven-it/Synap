from rest_framework import serializers

from ia.models import AgentConversation, AgentDefinition, AgentMemoryItem, AgentMessage


class AgentDefinitionSerializer(serializers.ModelSerializer):
    provider_kind = serializers.CharField(source="default_provider.provider_kind", read_only=True)
    provider_name = serializers.CharField(source="default_provider.name", read_only=True)
    provider_is_configured = serializers.SerializerMethodField()
    provider_available_models = serializers.SerializerMethodField()

    class Meta:
        model = AgentDefinition
        fields = [
            "slug",
            "name",
            "description",
            "domain",
            "required_permission",
            "default_model_name",
            "tool_use_model_name",
            "memory_write_model_name",
            "fast_model_name",
            "supports_streaming",
            "supports_structured_output",
            "supports_parallel_tool_calls",
            "provider_kind",
            "provider_name",
            "provider_is_configured",
            "provider_available_models",
            "ui_config",
        ]

    def get_provider_is_configured(self, obj):
        provider = getattr(obj, "default_provider", None)
        return bool(provider and provider.is_configured)

    def get_provider_available_models(self, obj):
        provider = getattr(obj, "default_provider", None)
        return provider.available_models if provider else []


class ConversationCreateSerializer(serializers.Serializer):
    agent_slug = serializers.SlugField(max_length=120)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    channel = serializers.ChoiceField(
        choices=AgentConversation._meta.get_field("channel").choices,
        required=False,
        default="web",
    )
    metadata = serializers.JSONField(required=False)


class ConversationMessageCreateSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=5000)


class LearningExampleReviewSerializer(serializers.Serializer):
    """Revisión de un ejemplo capturado para el dataset de afinado."""

    action = serializers.ChoiceField(choices=["approve", "reject", "mark_exported"])
    notes = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    corrected_assistant_text = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50000,
        help_text="Si se informa junto con approve, sustituye la respuesta del asistente en el payload exportable.",
    )


class AgentMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentMessage
        fields = [
            "id",
            "role",
            "content",
            "structured_content",
            "metadata",
            "created_at",
        ]


class AgentConversationSerializer(serializers.ModelSerializer):
    agent = AgentDefinitionSerializer(read_only=True)
    messages = AgentMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AgentConversation
        fields = [
            "conversation_uuid",
            "title",
            "status",
            "channel",
            "metadata",
            "last_message_at",
            "created_at",
            "updated_at",
            "agent",
            "messages",
        ]


class AgentMemoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentMemoryItem
        fields = [
            "id",
            "scope",
            "memory_type",
            "sensitivity",
            "key",
            "content",
            "source_summary",
            "confidence",
            "is_confirmed",
            "created_at",
            "updated_at",
        ]
