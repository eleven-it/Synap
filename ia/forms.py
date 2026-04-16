from __future__ import annotations

from django import forms
from django.db.models import Q

from ia.models import AgentDefinition, LlmProviderConfig


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


class AgentConversationStartForm(forms.Form):
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Escribí tu consulta..."}),
        max_length=5000,
        label="Mensaje inicial",
    )
