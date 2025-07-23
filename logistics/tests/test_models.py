from django.test import TestCase
from logistics.models import Vehicle, Driver, DeliveryRoute, DeliveryStop, DeliveryEvent
from core.models import Empresa, Branch, UsuarioExtendido
from sales.models import SalesOrder, Client
from datetime import date

class VehicleModelTest(TestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nombre='Test Company', razon_social='Test RS', identificador_fiscal='123', activa=True)
        self.vehicle = Vehicle.objects.create(company=self.company, license_plate='ABC123', type='Truck', capacity_kg=1000)

    def test_vehicle_str(self):
        self.assertIn('ABC123', str(self.vehicle))

class DriverModelTest(TestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nombre='Test Company', razon_social='Test RS', identificador_fiscal='124', activa=True)
        self.driver = Driver.objects.create(company=self.company, name='John Doe', document_number='DNI123', phone='123456')

    def test_driver_str(self):
        self.assertIn('John Doe', str(self.driver))

class DeliveryRouteModelTest(TestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nombre='Test Company', razon_social='Test RS', identificador_fiscal='125', activa=True)
        self.branch = Branch.objects.create(empresa=self.company, name='Main Branch')
        self.vehicle = Vehicle.objects.create(company=self.company, license_plate='DEF456', type='Van', capacity_kg=500)
        self.driver = Driver.objects.create(company=self.company, name='Jane Smith', document_number='DNI124', phone='654321')
        self.route = DeliveryRoute.objects.create(company=self.company, branch=self.branch, vehicle=self.vehicle, driver=self.driver, date=date.today(), state='planned')

    def test_route_str(self):
        self.assertIn('planned', str(self.route))

class DeliveryStopModelTest(TestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nombre='Test Company', razon_social='Test RS', identificador_fiscal='126', activa=True)
        self.branch = Branch.objects.create(empresa=self.company, name='Branch 2')
        self.vehicle = Vehicle.objects.create(company=self.company, license_plate='GHI789', type='Car', capacity_kg=300)
        self.driver = Driver.objects.create(company=self.company, name='Alice', document_number='DNI125', phone='789123')
        self.route = DeliveryRoute.objects.create(company=self.company, branch=self.branch, vehicle=self.vehicle, driver=self.driver, date=date.today(), state='planned')
        self.client = Client.objects.create(name='Client 1', type='person', document_number='C123', is_active=True)
        self.stop = DeliveryStop.objects.create(route=self.route, order=None, client=self.client, address='Street 123', state='pending')

    def test_stop_str(self):
        self.assertIn('pending', str(self.stop))

class DeliveryEventModelTest(TestCase):
    def setUp(self):
        self.company = Empresa.objects.create(nombre='Test Company', razon_social='Test RS', identificador_fiscal='127', activa=True)
        self.branch = Branch.objects.create(empresa=self.company, name='Branch 3')
        self.vehicle = Vehicle.objects.create(company=self.company, license_plate='JKL012', type='Bike', capacity_kg=50)
        self.driver = Driver.objects.create(company=self.company, name='Bob', document_number='DNI126', phone='321987')
        self.route = DeliveryRoute.objects.create(company=self.company, branch=self.branch, vehicle=self.vehicle, driver=self.driver, date=date.today(), state='planned')
        self.client = Client.objects.create(name='Client 2', type='person', document_number='C124', is_active=True)
        self.stop = DeliveryStop.objects.create(route=self.route, order=None, client=self.client, address='Street 456', state='pending')
        self.event = DeliveryEvent.objects.create(stop=self.stop, event_type='arrived', timestamp=date.today(), notes='Arrived at stop')

    def test_event_str(self):
        self.assertIn('arrived', str(self.event)) 