import pytest
from django.core import mail
from core.models.models import Empresa
from administraNET_integration.models import AdministraNETConfig, ValidationRuleConfig
from administraNET_integration.services.sync_service import AdministraNETSyncService
from unittest.mock import patch

@pytest.mark.django_db
def test_email_notification_on_validation_failure():
    empresa = Empresa.objects.create(nombre="Empresa Notif", identificador_fiscal="33333333333", email="test@notif.com")
    config = AdministraNETConfig.objects.create(
        host="localhost", port=3306, database_name="testdb", username="user", password="pass", is_active=True
    )
    # Simular relación empresa-config
    config.empresa = empresa
    config.save()
    # Activar regla que falla
    ValidationRuleConfig.objects.create(empresa=empresa, rule_code='integrity_mappings', is_active=True)
    sync_log = SyncLog.objects.create(sync_type='FULL', status='PENDING')
    # Mockear validación para forzar error
    with patch('administraNET_integration.validations.integrity_mappings.IntegrityMappingsValidationRule.validate') as mock_validate:
        mock_validate.return_value = {'success': False, 'errors': ['Error de notificación'], 'warnings': [], 'details': {}}
        service = AdministraNETSyncService(config)
        service.sync_all(sync_log)
        # Verificar que se envió email
        assert len(mail.outbox) == 1
        assert 'Error de validación en sincronización' in mail.outbox[0].subject
        assert 'test@notif.com' in mail.outbox[0].to
        assert 'Error de notificación' in mail.outbox[0].body 