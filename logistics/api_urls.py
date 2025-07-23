from django.urls import path
from logistics.api import views as api_views

app_name = 'logistics_api'

urlpatterns = [
    # Weather API endpoints
    path('weather/current/', api_views.weather_current, name='weather_current'),
    path('weather/forecast/', api_views.weather_forecast, name='weather_forecast'),
    path('weather/route/<int:route_id>/impact/', api_views.weather_route_impact, name='weather_route_impact'),
    path('weather/suitability/', api_views.weather_delivery_suitability, name='weather_delivery_suitability'),
    path('weather/config/status/', api_views.weather_config_status, name='weather_config_status'),
    
    # Notification API endpoints
    path('notifications/test/', api_views.test_notification, name='test_notification'),
    path('notifications/config/', api_views.notification_config_list, name='notification_config_list'),
    path('notifications/config/create/', api_views.notification_config_create, name='notification_config_create'),
    path('notifications/config/<int:config_id>/update/', api_views.notification_config_update, name='notification_config_update'),
    path('notifications/config/<int:config_id>/delete/', api_views.notification_config_delete, name='notification_config_delete'),
] 