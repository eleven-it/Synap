from django.test import TestCase
from unittest.mock import patch, MagicMock
from logistics.services.route_planning_service import RoutePlanningService
from logistics.services.notification_service import NotificationService
from logistics.services.integration_service import IntegrationService
from logistics.services.tracking_service import TrackingService
from logistics.services.weather_service import WeatherService
from logistics.models import DeliveryRoute, DeliveryStop, Vehicle, Driver
from core.models import Empresa
from sales.models import Client, SalesOrder
from datetime import date

class RoutePlanningServiceTest(TestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nombre='Test Company', razon_social='RS', identificador_fiscal='123', activa=True)
        self.vehicle = Vehicle.objects.create(company=self.company, license_plate='ABC123', type='Truck', capacity_kg=1000)
        self.driver = Driver.objects.create(company=self.company, name='Driver', document_number='DNI', phone='123')
        self.client = Client.objects.create(name='Client', type='person', document_number='C1', is_active=True)
        self.order = SalesOrder.objects.create(client=self.client, state='draft')
        self.stop = DeliveryStop.objects.create(route=None, sales_order=self.order, client=self.client, address='Street 1', scheduled_time=date.today(), state='pending')

    def test_plan_routes_basic(self):
        service = RoutePlanningService()
        routes = service.plan_routes()
        self.assertIsInstance(routes, list)

class NotificationServiceTest(TestCase):
    @patch('logistics.services.notification_service.send_mail')
    def test_send_notification_email(self, mock_send_mail):
        service = NotificationService()
        result = service.send_notification('delayed', {'stop_id': 1}, recipients=['test@example.com'], channels=['email'])
        self.assertIn('email', result['results'])

class IntegrationServiceTest(TestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nombre='Test Company', razon_social='RS', identificador_fiscal='123', activa=True)
        self.vehicle = Vehicle.objects.create(company=self.company, license_plate='ABC123', type='Truck', capacity_kg=1000)
        self.driver = Driver.objects.create(company=self.company, name='Driver', document_number='DNI', phone='123')
        self.client = Client.objects.create(name='Client', type='person', document_number='C1', is_active=True)
        self.order = SalesOrder.objects.create(client=self.client, state='draft')
        self.route = DeliveryRoute.objects.create(vehicle=self.vehicle, driver=self.driver, date=date.today(), state='planned')
        self.stop = DeliveryStop.objects.create(route=self.route, sales_order=self.order, client=self.client, address='Street 1', scheduled_time=date.today(), state='pending')

    def test_reserve_stock_for_delivery(self):
        service = IntegrationService()
        result = service.reserve_stock_for_delivery(self.stop)
        self.assertIn('success', result)

class TrackingServiceTest(TestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nombre='Test Company', razon_social='RS', identificador_fiscal='123', activa=True)
        self.driver = Driver.objects.create(company=self.company, name='Driver', document_number='DNI', phone='123')

    @patch('logistics.services.tracking_service.NotificationService')
    def test_update_driver_location(self, mock_notification):
        service = TrackingService()
        result = service.update_driver_location(self.driver, -34.6, -58.4)
        self.assertIsInstance(result, dict)

class WeatherServiceTest(TestCase):
    @patch('logistics.services.weather_service.requests.get')
    def test_get_current_weather(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'weather': 'ok'}
        service = WeatherService()
        result = service.get_current_weather(-34.6, -58.4)
        self.assertTrue(result is None or isinstance(result, dict)) 