"""Tests consulta clientes y formulario de mapeo."""

from unittest.mock import patch

from django.test import TestCase

from tiendanube_administranet.forms import CustomerMappingForm
from tiendanube_administranet.models import CustomerMapping
from tiendanube_administranet.services.customer_lookup import (
    adminet_customer_to_form_fields,
    nombre_completo_a_campos_tiendanube,
    tiendanube_customer_to_form_fields,
)


class CustomerLookupNormalizeTests(TestCase):
    def test_tiendanube_a_form_fields(self):
        data = tiendanube_customer_to_form_fields({
            'id': 42,
            'name': 'Juan Pérez',
            'email': 'j@t.com',
            'phone': '123',
            'identification': '20123456789',
            'addresses': [{'city': 'CABA', 'address': 'Calle 1'}],
        })
        self.assertEqual(data['tiendanube_id'], 42)
        self.assertEqual(data['tiendanube_email'], 'j@t.com')
        self.assertEqual(data['tiendanube_first_name'], 'Juan')
        self.assertEqual(data['tiendanube_last_name'], 'Pérez')

    def test_tiendanube_first_last_sin_name(self):
        data = tiendanube_customer_to_form_fields({
            'id': 7,
            'first_name': 'Yanina',
            'last_name': 'Ruiz',
            'email': 'y@t.com',
        })
        self.assertEqual(data['tiendanube_first_name'], 'Yanina')
        self.assertEqual(data['tiendanube_last_name'], 'Ruiz')

    def test_nombre_completo_a_campos_tiendanube(self):
        data = nombre_completo_a_campos_tiendanube('Yanina Ruiz')
        self.assertEqual(data['tiendanube_name'], 'Yanina Ruiz')
        self.assertEqual(data['tiendanube_first_name'], 'Yanina')
        self.assertEqual(data['tiendanube_last_name'], 'Ruiz')

    def test_display_name_fallback_adminet(self):
        mapping = CustomerMapping(
            adminet_nombre='Yanina Ruiz',
            tiendanube_email='y@t.com',
        )
        self.assertEqual(mapping.display_name, 'Yanina Ruiz')

    def test_adminet_a_form_fields(self):
        data = adminet_customer_to_form_fields({
            'Codigo': 99,
            'nombre_cliente': 'ACME',
            'Email': 'a@b.com',
            'CUIT': '30-1-9',
            'telefono': '456',
            'Calle': 'Falsa',
            'NroCalle': '123',
            'Dpto': '-',
        })
        self.assertEqual(data['adminet_codigo'], 99)
        self.assertEqual(data['adminet_nombre'], 'ACME')


class CustomerMappingFormCleanTests(TestCase):
    @patch('tiendanube_administranet.services.customer_lookup.enrich_cleaned_data_from_sources')
    def test_requiere_al_menos_un_id(self, mock_enrich):
        form = CustomerMappingForm(data={
            'sync_direction': 'tiendanube_to_adminet',
            'sync_status': 'pending',
            'workflow_estado': 'incompleto',
            'intentos_completar_datos': 0,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('indique al menos un id', str(form.non_field_errors()).lower())
        mock_enrich.assert_not_called()

    @patch('tiendanube_administranet.services.customer_mapping_validation.validate_customer_mapping_form')
    @patch('tiendanube_administranet.services.customer_lookup.enrich_cleaned_data_from_sources')
    def test_acepta_solo_tiendanube_id(self, mock_enrich, mock_validate):
        def _enrich(cleaned, **kwargs):
            cleaned['tiendanube_email'] = 'x@y.com'
            cleaned['tiendanube_name'] = 'Test'
            return cleaned
        mock_enrich.side_effect = _enrich
        form = CustomerMappingForm(data={
            'tiendanube_id': 100,
            'sync_direction': 'tiendanube_to_adminet',
            'sync_status': 'pending',
            'workflow_estado': 'incompleto',
            'intentos_completar_datos': 0,
        })
        form.is_valid()
        self.assertTrue(form.is_valid(), form.errors)
        mock_enrich.assert_called_once()
        mock_validate.assert_called_once()
