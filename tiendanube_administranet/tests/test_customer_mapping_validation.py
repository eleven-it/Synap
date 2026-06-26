"""Tests validación mapeo cliente y anti-duplicado AdministraNET."""

from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tiendanube_administranet.services.adminet_service import AdministraNETService
from tiendanube_administranet.services.customer_mapping_validation import (
    validate_adminet_codigo_unique_mapping,
)


class AdminetDuplicateCustomerTests(SimpleTestCase):
    def test_rechaza_email_duplicado(self):
        svc = AdministraNETService.__new__(AdministraNETService)
        svc.get_customer_by_email = MagicMock(
            return_value={'success': True, 'customer': {'Codigo': 42}}
        )
        svc.get_customer_by_cuit = MagicMock(return_value={'success': False})
        result = svc._reject_duplicate_adminet_customer({'Email': 'a@b.com'})
        self.assertFalse(result['success'])
        self.assertIn('42', result['message'])


class AdminetCodigoUniqueMappingTests(SimpleTestCase):
    @patch('tiendanube_administranet.models.CustomerMapping')
    def test_codigo_ya_mapeado(self, mock_model):
        mock_model.objects.filter.return_value.exists.return_value = True
        with self.assertRaises(ValidationError):
            validate_adminet_codigo_unique_mapping(100, exclude_mapping_id=None)
