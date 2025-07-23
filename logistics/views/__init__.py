from .dashboard import DashboardLogisticsView
from .simulator import LogisticsSimulatorView
from .config import LogisticsConfigView
from .notification_config import (
    NotificationConfigListView,
    NotificationConfigCreateView,
    NotificationConfigUpdateView,
    NotificationConfigDeleteView,
    NotificationTestView
)
# Importar vistas CRUD de cada archivo correspondiente
from .vehicle import VehicleListView, VehicleDetailView, VehicleCreateView, VehicleUpdateView, VehicleDeleteView
from .driver import DriverListView, DriverDetailView, DriverCreateView, DriverUpdateView, DriverDeleteView
from .delivery_route import DeliveryRouteListView, DeliveryRouteDetailView, DeliveryRouteCreateView, DeliveryRouteUpdateView, DeliveryRouteDeleteView, RoutePlanningView
from .delivery_stop import DeliveryStopListView, DeliveryStopDetailView, DeliveryStopCreateView, DeliveryStopUpdateView, DeliveryStopDeleteView
from .delivery_event import DeliveryEventListView, DeliveryEventDetailView, DeliveryEventCreateView, DeliveryEventUpdateView, DeliveryEventDeleteView 
from .tracking import RealTimeTrackingView 
from .geofence import GeofenceCreateView, GeofenceUpdateView 
from .integration import IntegrationDashboardView, StockReservationView, LogisticsCostsView, InvoiceManagementView, IntegrationSettingsView 
from .customer_tracking import CustomerTrackingView 