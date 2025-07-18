from django.urls import path
from . import views

app_name = 'adminet_api'

urlpatterns = [
    # Endpoints existentes...
    
    # Nuevos endpoints para mapeo
    path('table-fields/', views.get_adminet_table_fields, name='table_fields'),
    path('model-fields/', views.get_synap_model_fields, name='model_fields'),
    path('preset-mapping/', views.get_preset_mapping, name='preset_mapping'),
    path('mapping-types/', views.get_available_mapping_types, name='mapping_types'),
] 