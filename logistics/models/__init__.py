# Solo importar los nuevos modelos adicionales
from .logistics_config import LogisticsConfig
from .notification_config import NotificationConfig
from .geofence import Geofence
from .driver_location import DriverLocation, DriverLocationHistory
from .tracking_config import TrackingConfig
from .vehicle import Vehicle
from .driver import Driver
from .delivery_route import DeliveryRoute
from .delivery_stop import DeliveryStop
from .delivery_event import DeliveryEvent

__all__ = [
    'LogisticsConfig',
    'NotificationConfig', 
    'Geofence',
    'DriverLocation',
    'DriverLocationHistory',
    'TrackingConfig',
    'Vehicle',
    'Driver',
    'DeliveryRoute',
    'DeliveryStop',
    'DeliveryEvent',
] 