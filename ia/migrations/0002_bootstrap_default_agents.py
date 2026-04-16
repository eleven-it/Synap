from django.db import migrations


def bootstrap_default_agents(apps, schema_editor):
    LlmProviderConfig = apps.get_model("ia", "LlmProviderConfig")
    AgentDefinition = apps.get_model("ia", "AgentDefinition")

    openai_provider, _ = LlmProviderConfig.objects.get_or_create(
        name="OpenAI",
        defaults={
            "provider_kind": "openai",
            "api_key_env_var": "OPENAI_API_KEY",
            "supports_structured_output": True,
            "supports_tool_use": True,
            "supports_streaming": True,
            "supports_vision": True,
            "metadata": {"recommended_for": ["tool_use", "structured_output", "reasoning"]},
        },
    )
    anthropic_provider, _ = LlmProviderConfig.objects.get_or_create(
        name="Anthropic",
        defaults={
            "provider_kind": "anthropic",
            "api_key_env_var": "ANTHROPIC_API_KEY",
            "supports_structured_output": True,
            "supports_tool_use": True,
            "supports_streaming": True,
            "supports_vision": True,
            "metadata": {"recommended_for": ["synthesis", "analysis", "long_context"]},
        },
    )
    openai_compatible_provider, _ = LlmProviderConfig.objects.get_or_create(
        name="OpenAI-Compatible",
        defaults={
            "provider_kind": "openai_compatible",
            "api_key_env_var": "OPENAI_COMPATIBLE_API_KEY",
            "supports_structured_output": True,
            "supports_tool_use": True,
            "supports_streaming": True,
            "supports_vision": False,
            "metadata": {"recommended_for": ["self_hosted", "gateways", "local_inference"]},
        },
    )
    local_provider, _ = LlmProviderConfig.objects.get_or_create(
        name="Local",
        defaults={
            "provider_kind": "local",
            "api_key_env_var": "",
            "supports_structured_output": False,
            "supports_tool_use": False,
            "supports_streaming": False,
            "supports_vision": False,
            "metadata": {"recommended_for": ["classification", "tagging", "cheap_tasks"]},
        },
    )

    AgentDefinition.objects.get_or_create(
        empresa=None,
        slug="asistente-reportes",
        defaults={
            "name": "Asistente de Reportes",
            "description": "Asistente personal persistente para consultas gerenciales y operativas.",
            "domain": "reportes",
            "required_permission": "ia.reportes",
            "is_active": True,
            "is_system": True,
            "default_provider_id": openai_provider.id,
            "fallback_provider_id": anthropic_provider.id,
            "default_model_name": "configurar-modelo-principal",
            "tool_use_model_name": "configurar-modelo-tool-use",
            "memory_write_model_name": "configurar-modelo-memoria",
            "fast_model_name": "configurar-modelo-rapido",
            "fallback_model_name": "configurar-modelo-fallback",
            "reasoning_profile": "high_accuracy",
            "supports_structured_output": True,
            "supports_parallel_tool_calls": False,
            "supports_streaming": True,
            "supports_vision": False,
            "memory_policy": {
                "enabled": True,
                "requires_governance": True,
                "default_scope": "user",
                "allow_types": ["profile", "episodic", "semantic", "working"],
            },
            "ui_config": {
                "surface": "conversation_first",
                "mobile_first": True,
                "supports_pwa": True,
            },
            "config": {
                "recommended_provider_order": [
                    openai_provider.name,
                    anthropic_provider.name,
                    openai_compatible_provider.name,
                    local_provider.name,
                ],
                "bootstrap_mode": True,
            },
            "system_prompt": "Asistente de Reportes seguro, persistente y gobernado por permisos.",
            "soul_summary": "Analista operativo y gerencial con memoria persistente y herramientas seguras.",
        },
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("ia", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(bootstrap_default_agents, noop_reverse),
    ]
