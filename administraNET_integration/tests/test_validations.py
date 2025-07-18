import pytest
from django.contrib.auth import get_user_model
from core.models.models import Empresa
from administraNET_integration.models import ValidationRuleConfig
from administraNET_integration.validations.base import VALIDATION_RULES_REGISTRY
from administraNET_integration.validations.integrity_mappings import IntegrityMappingsValidationRule
from administraNET_integration.validations.stock_consistency import StockConsistencyValidationRule

@pytest.mark.django_db
def test_integrity_mappings_validation_rule():
    empresa = Empresa.objects.create(nombre="Test SA", identificador_fiscal="12345678901")
    # No hay mapeos, debe fallar
    rule = IntegrityMappingsValidationRule(empresa)
    result = rule.validate()
    assert not result['success']
    assert any('Falta mapeo activo' in e for e in result['errors'])

@pytest.mark.django_db
def test_stock_consistency_validation_rule():
    empresa = Empresa.objects.create(nombre="Test Stock", identificador_fiscal="98765432109")
    # No hay stock negativo, debe pasar
    rule = StockConsistencyValidationRule(empresa)
    result = rule.validate()
    assert result['success']

@pytest.mark.django_db
def test_validation_rule_config_activation():
    empresa = Empresa.objects.create(nombre="Test Config", identificador_fiscal="11111111111")
    # Activar/desactivar regla
    config = ValidationRuleConfig.objects.create(empresa=empresa, rule_code='integrity_mappings', is_active=True)
    assert config.is_active
    config.is_active = False
    config.save()
    config.refresh_from_db()
    assert not config.is_active 