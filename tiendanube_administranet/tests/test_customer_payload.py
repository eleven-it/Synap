"""Tests normalización payload cliente AdministraNET."""

from django.test import SimpleTestCase

from tiendanube_administranet.services.customer_payload import normalize_adminet_customer_payload


class CustomerPayloadTests(SimpleTestCase):
    def test_normaliza_int_y_varchar(self):
        data = normalize_adminet_customer_payload({
            'nombre_cliente': 'Juan',
            'CodProvincia': '5',
            'Email': '',
            'id_tiendanube': '99',
        })
        self.assertEqual(data['CodProvincia'], 5)
        self.assertEqual(data['id_tiendanube'], 99)
        self.assertEqual(data['Email'], '-')

    def test_lista_precio_permance_varchar(self):
        data = normalize_adminet_customer_payload({'ListaPrecio': 'Lista 1'})
        self.assertEqual(data['ListaPrecio'], 'Lista 1')
