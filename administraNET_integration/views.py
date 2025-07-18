from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def dashboard(request):
    """Vista principal del dashboard de integración administraNET."""
    return render(request, 'administraNET_integration/dashboard.html')

def config_view(request):
    """Vista de configuración de la integración."""
    return render(request, 'administraNET_integration/config_view.html')

def test_connection(request):
    """Vista para probar la conexión con administraNET."""
    return render(request, 'administraNET_integration/test_connection.html')

def table_mappings(request):
    """Vista de listado de mapeos de tablas."""
    return render(request, 'administraNET_integration/table_mappings.html')

def table_mapping_create(request):
    """Vista para crear un mapeo de tabla."""
    return render(request, 'administraNET_integration/table_mapping_create.html')

def table_mapping_edit(request, pk):
    """Vista para editar un mapeo de tabla."""
    return render(request, 'administraNET_integration/table_mapping_edit.html', {'pk': pk})

def table_mapping_delete(request, pk):
    """Vista para eliminar un mapeo de tabla."""
    return render(request, 'administraNET_integration/table_mapping_delete.html', {'pk': pk})

def sync_logs(request):
    """Vista de logs de sincronización."""
    return render(request, 'administraNET_integration/sync_logs.html')

def sync_log_detail(request, pk):
    """Vista de detalle de log de sincronización."""
    return render(request, 'administraNET_integration/sync_log_detail.html', {'pk': pk})

def manual_sync(request):
    """Vista para ejecutar sincronización manual."""
    return render(request, 'administraNET_integration/manual_sync.html')

def toggle_integration(request):
    """Vista para activar/desactivar integración."""
    return render(request, 'administraNET_integration/toggle_integration.html')

def sync_webhook(request):
    """Vista para recibir webhooks de sincronización."""
    return HttpResponse('Webhook recibido', status=200)
