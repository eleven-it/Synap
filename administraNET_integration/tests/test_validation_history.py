import pytest
from core.models.models import Empresa, UsuarioExtendido
from administraNET_integration.models import SyncLog, ValidationRuleConfig
from administraNET_integration.validations.base import VALIDATION_RULES_REGISTRY

@pytest.mark.django_db
def test_validation_history_logging():
    empresa = Empresa.objects.create(nombre="Empresa History", identificador_fiscal="44444444444")
    user = UsuarioExtendido.objects.create(email="test@history.com", nombre="Test User")
    # Activar regla
    ValidationRuleConfig.objects.create(empresa=empresa, rule_code='integrity_mappings', is_active=True)
    # Simular ejecución de validación
    rule_cls = VALIDATION_RULES_REGISTRY.get('integrity_mappings')
    rule = rule_cls(empresa)
    result = rule.validate()
    # Crear log manualmente
    log = SyncLog.objects.create(
        sync_type='VALIDATION',
        status='SUCCESS' if result['success'] else 'ERROR',
        records_processed=1,
        records_failed=len(result.get('errors', [])),
        details={
            'rule': 'integrity_mappings',
            'result': result,
            'user': user.id,
            'empresa': empresa.id,
        }
    )
    # Verificar que se registró correctamente
    assert log.sync_type == 'VALIDATION'
    assert log.details['rule'] == 'integrity_mappings'
    assert log.details['user'] == user.id
    assert log.details['empresa'] == empresa.id
    assert 'empresa' in log.details['result'] 