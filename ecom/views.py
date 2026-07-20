from pathlib import Path

from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect

from ecom.services.mayoristapp_relays import mayoristapp_relay_inventory_dict
from ecom.services.migration_info import build_migration_info_dict


def manual_usuario_view(request):
    """Manual de usuario Ventas (HTML estático). Solo requiere sesión activa."""
    if "user" not in request.session or not request.session.get("user"):
        return redirect("login:login")
    manual_path = (
        Path(__file__).resolve().parent
        / "static"
        / "ecom"
        / "manuales"
        / "manual_usuario_ventas.html"
    )
    if not manual_path.is_file():
        raise Http404("Manual de usuario Ventas no encontrado.")
    return FileResponse(
        manual_path.open("rb"),
        content_type="text/html; charset=utf-8",
    )


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
