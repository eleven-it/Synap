from django.http import JsonResponse

from ecom.services.mayoristapp_relays import mayoristapp_relay_inventory_dict
from ecom.services.migration_info import build_migration_info_dict


def health(_request):
    """Smoke check para despliegue y monitoreo."""
    return JsonResponse({"status": "ok", "app": "ecom"})


def migration_info(_request):
    """Metadatos alineados a la ingeniería inversa (tests de paridad)."""
    return JsonResponse(build_migration_info_dict())


def mayoristapp_relay_inventory(_request):
    """
    Inventario de archivos relay bajo mayoristapp/ (Fase A — trazabilidad).
    Ver docs/ecom/MAYORISTAPP_RELAYS.md y ecom.services.mayoristapp_relays.
    """
    return JsonResponse(mayoristapp_relay_inventory_dict())
