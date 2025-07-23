from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    # Vehicle
    path('vehicles/', views.VehicleListView.as_view(), name='vehicle_list'),
    path('vehicles/create/', views.VehicleCreateView.as_view(), name='vehicle_create'),
    path('vehicles/<int:pk>/', views.VehicleDetailView.as_view(), name='vehicle_detail'),
    path('vehicles/<int:pk>/edit/', views.VehicleUpdateView.as_view(), name='vehicle_edit'),
    path('vehicles/<int:pk>/delete/', views.VehicleDeleteView.as_view(), name='vehicle_delete'),

    # Driver
    path('drivers/', views.DriverListView.as_view(), name='driver_list'),
    path('drivers/create/', views.DriverCreateView.as_view(), name='driver_create'),
    path('drivers/<int:pk>/', views.DriverDetailView.as_view(), name='driver_detail'),
    path('drivers/<int:pk>/edit/', views.DriverUpdateView.as_view(), name='driver_edit'),
    path('drivers/<int:pk>/delete/', views.DriverDeleteView.as_view(), name='driver_delete'),

    # DeliveryRoute
    path('deliveryroutes/', views.DeliveryRouteListView.as_view(), name='deliveryroute_list'),
    path('deliveryroutes/create/', views.DeliveryRouteCreateView.as_view(), name='deliveryroute_create'),
    path('deliveryroutes/<int:pk>/', views.DeliveryRouteDetailView.as_view(), name='deliveryroute_detail'),
    path('deliveryroutes/<int:pk>/edit/', views.DeliveryRouteUpdateView.as_view(), name='deliveryroute_edit'),
    path('deliveryroutes/<int:pk>/delete/', views.DeliveryRouteDeleteView.as_view(), name='deliveryroute_delete'),
    path('deliveryroutes/plan/', views.RoutePlanningView.as_view(), name='deliveryroute_plan'),

    # DeliveryStop
    path('deliverystops/', views.DeliveryStopListView.as_view(), name='deliverystop_list'),
    path('deliverystops/create/', views.DeliveryStopCreateView.as_view(), name='deliverystop_create'),
    path('deliverystops/<int:pk>/', views.DeliveryStopDetailView.as_view(), name='deliverystop_detail'),
    path('deliverystops/<int:pk>/edit/', views.DeliveryStopUpdateView.as_view(), name='deliverystop_edit'),
    path('deliverystops/<int:pk>/delete/', views.DeliveryStopDeleteView.as_view(), name='deliverystop_delete'),

    # DeliveryEvent
    path('deliveryevents/', views.DeliveryEventListView.as_view(), name='deliveryevent_list'),
    path('deliveryevents/create/', views.DeliveryEventCreateView.as_view(), name='deliveryevent_create'),
    path('deliveryevents/<int:pk>/', views.DeliveryEventDetailView.as_view(), name='deliveryevent_detail'),
    path('deliveryevents/<int:pk>/edit/', views.DeliveryEventUpdateView.as_view(), name='deliveryevent_edit'),
    path('deliveryevents/<int:pk>/delete/', views.DeliveryEventDeleteView.as_view(), name='deliveryevent_delete'),
    path('tracking/realtime/', views.RealTimeTrackingView.as_view(), name='tracking_realtime'),
    path('geofences/add/', views.GeofenceCreateView.as_view(), name='geofence_add'),
    path('geofences/<int:pk>/edit/', views.GeofenceUpdateView.as_view(), name='geofence_edit'),
    path('dashboard/', views.DashboardLogisticsView.as_view(), name='dashboard'),
    path('notifications/config/', views.NotificationConfigUpdateView.as_view(), name='notification_config'),
    path('track/', views.CustomerTrackingView.as_view(), name='customer_tracking'),
    path('simulator/', views.LogisticsSimulatorView.as_view(), name='simulator'),
    path('config/', views.LogisticsConfigView.as_view(), name='config'),
    path('notifications/', views.NotificationConfigListView.as_view(), name='notification_config_list'),
    path('notifications/create/', views.NotificationConfigCreateView.as_view(), name='notification_config_create'),
    path('notifications/<int:pk>/edit/', views.NotificationConfigUpdateView.as_view(), name='notification_config_update'),
    path('notifications/<int:pk>/delete/', views.NotificationConfigDeleteView.as_view(), name='notification_config_delete'),
    path('notifications/test/', views.NotificationTestView.as_view(), name='notification_test'),
    path('integration/', views.IntegrationDashboardView.as_view(), name='integration_dashboard'),
    path('integration/stock/<int:pk>/', views.StockReservationView.as_view(), name='stock_reservation'),
    path('integration/costs/<int:pk>/', views.LogisticsCostsView.as_view(), name='logistics_costs'),
    path('integration/invoices/', views.InvoiceManagementView.as_view(), name='invoice_management'),
    path('integration/settings/<int:pk>/', views.IntegrationSettingsView.as_view(), name='integration_settings'),
] 