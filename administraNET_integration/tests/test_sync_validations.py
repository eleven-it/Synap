import pytest
from core.models.models import Empresa
from administraNET_integration.models import AdministraNETConfig, SyncLog, ValidationRuleConfig
from administraNET_integration.services.sync_service import AdministraNETSyncService
from unittest.mock import patch

@pytest.mark.django_db
def test_sync_blocked_by_validation_error():
    empresa = Empresa.objects.create(nombre="Empresa Sync", identificador_fiscal="22222222222", email="test@empresa.com")
    config = AdministraNETConfig.objects.create(
        host="localhost", port=3306, database_name="testdb", username="user", password="pass", is_active=True
    )
    # Simular relación empresa-config
    config.empresa = empresa
    config.save()
    # Activar regla que siempre falla
    ValidationRuleConfig.objects.create(empresa=empresa, rule_code='integrity_mappings', is_active=True)
    sync_log = SyncLog.objects.create(sync_type='FULL', status='PENDING')
    # Mockear la validación para forzar error
    with patch('administraNET_integration.validations.integrity_mappings.IntegrityMappingsValidationRule.validate') as mock_validate:
        mock_validate.return_value = {'success': False, 'errors': ['Error crítico de prueba'], 'warnings': [], 'details': {}}
        service = AdministraNETSyncService(config)
        result = service.sync_all(sync_log)
        assert not result['success']
        assert 'validation_errors' in result
        assert 'Error crítico de prueba' in result['validation_errors']
        sync_log.refresh_from_db()
        assert sync_log.status == 'ERROR'
        assert 'Error crítico de prueba' in sync_log.error_message 