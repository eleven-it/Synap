from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.translation import gettext as _
from core.models.models import Empresa
from administraNET_integration.models import ValidationRuleConfig, SyncLog
from administraNET_integration.validations.base import VALIDATION_RULES_REGISTRY
from core.constantes_permisos import CAN_MANAGE_INTEGRATIONS
from core.utils.permissions import CorePermissionRequiredMixin
import logging

logger = logging.getLogger(__name__)

class AdminetValidationView(CorePermissionRequiredMixin, TemplateView):
    template_name = 'administraNET_integration/validation.html'
    permission_required = CAN_MANAGE_INTEGRATIONS

    def get_empresa(self):
        empresa_id = self.request.GET.get('empresa_id') or self.request.POST.get('empresa_id')
        if empresa_id:
            return get_object_or_404(Empresa, id=empresa_id)
        # Fallback: empresa activa del usuario
        if hasattr(self.request.user, 'empresa_activa') and self.request.user.empresa_activa:
            return self.request.user.empresa_activa
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self.get_empresa()
        context['empresa'] = empresa
        context['resultados'] = []
        context['reglas_activas'] = []
        if not empresa:
            messages.error(self.request, _("No tienes permisos o la empresa no existe."))
            return context
        reglas_activas = ValidationRuleConfig.objects.filter(empresa=empresa, is_active=True)
        context['reglas_activas'] = reglas_activas
        # Si se ejecutan validaciones (POST o GET ?run=1)
        if self.request.method == 'POST' or self.request.GET.get('run') == '1':
            resultados = []
            for config in reglas_activas:
                rule_cls = VALIDATION_RULES_REGISTRY.get(config.rule_code)
                if not rule_cls:
                    continue
                rule = rule_cls(empresa)
                try:
                    resultado = rule.validate()
                    resultados.append({
                        'code': config.rule_code,
                        'label': getattr(rule_cls, 'label', config.rule_code),
                        'description': getattr(rule_cls, 'description', ''),
                        'success': resultado.get('success', False),
                        'errors': resultado.get('errors', []),
                        'warnings': resultado.get('warnings', []),
                        'details': resultado.get('details', {}),
                    })
                    # Auditoría
                    logger.info(f"[VALIDATION] Usuario {self.request.user} ejecutó regla {config.rule_code} para empresa {empresa.id} - Resultado: {resultado}")
                    SyncLog.objects.create(
                        sync_type='VALIDATION',
                        status='SUCCESS' if resultado.get('success') else 'ERROR',
                        records_processed=1,
                        records_failed=len(resultado.get('errors', [])),
                        details={
                            'rule': config.rule_code,
                            'result': resultado,
                            'user': self.request.user.id,
                            'empresa': empresa.id,
                        }
                    )
                except Exception as e:
                    resultados.append({
                        'code': config.rule_code,
                        'label': getattr(rule_cls, 'label', config.rule_code),
                        'description': getattr(rule_cls, 'description', ''),
                        'success': False,
                        'errors': [str(e)],
                        'warnings': [],
                        'details': {},
                    })
                    logger.error(f"[VALIDATION] Error ejecutando regla {config.rule_code} para empresa {empresa.id}: {e}")
            context['resultados'] = resultados
        return context

    def post(self, request, *args, **kwargs):
        # Permite ejecutar validaciones vía POST
        return self.render_to_response(self.get_context_data()) 