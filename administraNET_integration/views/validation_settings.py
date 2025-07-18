from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from core.models.models import Empresa
from administraNET_integration.models import ValidationRuleConfig
from administraNET_integration.validations.base import VALIDATION_RULES_REGISTRY
from core.constantes_permisos import CAN_MANAGE_INTEGRATIONS

@login_required
def validation_settings(request, empresa_id):
    # Protección por permisos del core
    if not request.user.tiene_permiso(CAN_MANAGE_INTEGRATIONS):
        messages.error(request, _("No tienes permisos para gestionar validaciones de integración."))
        return redirect('core:dashboard')

    empresa = get_object_or_404(Empresa, id=empresa_id)
    reglas = []
    for code, rule_cls in VALIDATION_RULES_REGISTRY.items():
        config, _ = ValidationRuleConfig.objects.get_or_create(
            empresa=empresa, rule_code=code,
            defaults={'is_active': True}
        )
        reglas.append({
            'code': code,
            'label': getattr(rule_cls, 'label', code),
            'description': getattr(rule_cls, 'description', ''),
            'is_active': config.is_active,
            'config_id': config.id,
        })

    if request.method == 'POST':
        for code in VALIDATION_RULES_REGISTRY.keys():
            is_active = request.POST.get(f'active_{code}') == 'on'
            ValidationRuleConfig.objects.filter(empresa=empresa, rule_code=code).update(is_active=is_active)
        messages.success(request, _("Configuración de validaciones actualizada correctamente."))
        return redirect('adminet:validation_settings', empresa_id=empresa.id)

    return render(request, 'administraNET_integration/validation_settings.html', {
        'empresa': empresa,
        'reglas': reglas,
    }) 