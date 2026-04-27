from __future__ import annotations

from django import forms
from django.db.models import Q

from ia.models import AgentDefinition, LlmProviderConfig
from ia.services.provider_presets import (
    apply_provider_preset,
    get_provider_models,
    get_recommended_model,
)


class LlmProviderConfigForm(forms.ModelForm):
    api_key_plain = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
        label="API key",
        help_text="Ingresar solo si querés crear o reemplazar la clave actual.",
    )
    available_models_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Modelos disponibles",
        help_text="Uno por línea. Estos modelos se podrán elegir luego por agente.",
    )

    class Meta:
        model = LlmProviderConfig
        fields = [
            "name",
            "provider_kind",
            "base_url",
            "organization_id",
            "is_active",
            "supports_structured_output",
            "supports_tool_use",
            "supports_streaming",
            "supports_vision",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_widget_classes()
        if self.instance and self.instance.pk:
            self.fields["available_models_text"].initial = "\n".join(self.instance.available_models or [])

    def _apply_widget_classes(self):
        base_class = "w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "rounded border-slate-300 text-violet-600 focus:ring-violet-500")
            else:
                widget.attrs.setdefault("class", base_class)

    def clean_available_models_text(self):
        raw = self.cleaned_data.get("available_models_text", "")
        models = [line.strip() for line in raw.splitlines() if line.strip()]
        if len(models) > 50:
            raise forms.ValidationError("No se permiten más de 50 modelos por proveedor.")
        return models

    def save(self, commit=True):
        instance = super().save(commit=False)
        apply_provider_preset(instance)
        instance.available_models = self.cleaned_data.get("available_models_text", [])
        api_key_plain = (self.cleaned_data.get("api_key_plain") or "").strip()
        if api_key_plain:
            instance.set_api_key(api_key_plain)
        if commit:
            instance.save()
        return instance


class AgentDefinitionConfigForm(forms.ModelForm):
    class Meta:
        model = AgentDefinition
        fields = [
            "name",
            "description",
            "required_permission",
            "default_provider",
            "fallback_provider",
            "default_model_name",
            "tool_use_model_name",
            "memory_write_model_name",
            "fast_model_name",
            "fallback_model_name",
            "reasoning_profile",
            "max_input_tokens",
            "max_output_tokens",
            "supports_structured_output",
            "supports_parallel_tool_calls",
            "supports_streaming",
            "supports_vision",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_providers = LlmProviderConfig.objects.filter(is_active=True)
        selected_ids = []
        if self.instance and self.instance.default_provider_id:
            selected_ids.append(self.instance.default_provider_id)
        if self.instance and self.instance.fallback_provider_id:
            selected_ids.append(self.instance.fallback_provider_id)
        if selected_ids:
            active_providers = LlmProviderConfig.objects.filter(
                Q(is_active=True) | Q(id__in=selected_ids)
            )
        active_providers = active_providers.order_by("name")
        self.fields["default_provider"].queryset = active_providers
        self.fields["fallback_provider"].queryset = active_providers
        self._apply_widget_classes()

    def _apply_widget_classes(self):
        base_class = "w-full rounded-xl border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "rounded border-slate-300 text-violet-600 focus:ring-violet-500")
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", base_class)
                widget.attrs.setdefault("rows", 3)
            else:
                widget.attrs.setdefault("class", base_class)


class AgentQuickSetupForm(forms.Form):
    default_provider = forms.ModelChoiceField(
        queryset=LlmProviderConfig.objects.none(),
        label="Proveedor",
        empty_label=None,
    )
    api_key_plain = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
        label="API key",
        help_text="Solo se usa para crear o reemplazar la clave del proveedor seleccionado.",
    )
    selected_model_name = forms.ChoiceField(
        choices=(),
        label="Modelo",
    )

    def __init__(self, *args, agent: AgentDefinition, **kwargs):
        self.agent = agent
        super().__init__(*args, **kwargs)
        self._apply_widget_classes()

        providers = LlmProviderConfig.objects.filter(is_active=True).order_by("name")
        if self.agent.default_provider_id:
            providers = LlmProviderConfig.objects.filter(Q(is_active=True) | Q(id=self.agent.default_provider_id)).order_by("name")
        self.fields["default_provider"].queryset = providers

        selected_provider = self._resolve_selected_provider()
        self._configure_model_choices(selected_provider)

        if not self.is_bound:
            if self.agent.default_provider_id:
                self.fields["default_provider"].initial = self.agent.default_provider_id
            if self.agent.default_model_name:
                self.fields["selected_model_name"].initial = self.agent.default_model_name
            elif selected_provider:
                self.fields["selected_model_name"].initial = get_recommended_model(selected_provider)

    def _apply_widget_classes(self):
        base_class = "w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", base_class)

    def _resolve_selected_provider(self):
        if self.is_bound:
            provider_id = self.data.get(self.add_prefix("default_provider")) or self.data.get("default_provider")
            try:
                return LlmProviderConfig.objects.get(pk=int(provider_id))
            except (TypeError, ValueError, LlmProviderConfig.DoesNotExist):
                return self.agent.default_provider
        return self.agent.default_provider

    def _configure_model_choices(self, provider):
        model_choices = [("", "Seleccionar modelo")]
        models = get_provider_models(provider)
        model_choices.extend((model, model) for model in models)
        self.fields["selected_model_name"].choices = model_choices

    def clean(self):
        cleaned = super().clean()
        provider = cleaned.get("default_provider")
        selected_model = cleaned.get("selected_model_name")
        available_models = [value for value, _label in self.fields["selected_model_name"].choices if value]
        if provider and not provider.is_configured and not (cleaned.get("api_key_plain") or "").strip():
            self.add_error("api_key_plain", "Ingresá la API key para dejar operativo el agente.")
        if selected_model and available_models and selected_model not in available_models:
            self.add_error("selected_model_name", "Seleccioná un modelo válido del proveedor.")
        if provider and not available_models:
            self.add_error("selected_model_name", "El proveedor no tiene modelos disponibles. Cargá o sincronizá sus modelos.")
        return cleaned

    def save(self):
        provider = self.cleaned_data["default_provider"]
        api_key_plain = (self.cleaned_data.get("api_key_plain") or "").strip()
        if api_key_plain:
            provider.set_api_key(api_key_plain)
        apply_provider_preset(provider)
        provider.save()

        selected_model = self.cleaned_data["selected_model_name"]
        self.agent.default_provider = provider
        self.agent.default_model_name = selected_model
        self.agent.tool_use_model_name = selected_model
        self.agent.memory_write_model_name = selected_model
        self.agent.fast_model_name = selected_model
        self.agent.fallback_provider = self.agent.fallback_provider or provider
        self.agent.fallback_model_name = self.agent.fallback_model_name or selected_model
        self.agent.reasoning_profile = self.agent.reasoning_profile or "balanced"
        self.agent.supports_structured_output = provider.supports_structured_output
        self.agent.supports_parallel_tool_calls = False
        self.agent.supports_streaming = provider.supports_streaming
        self.agent.supports_vision = provider.supports_vision
        self.agent.max_input_tokens = self.agent.max_input_tokens or 16000
        self.agent.max_output_tokens = self.agent.max_output_tokens or 4000
        self.agent.is_active = True
        config = dict(self.agent.config or {})
        config["temperature"] = config.get("temperature", 0.2)
        config["auto_configured"] = True
        self.agent.config = config
        self.agent.save()
        return self.agent


class AgentConversationStartForm(forms.Form):
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Escribí tu consulta..."}),
        max_length=5000,
        label="Mensaje inicial",
    )
