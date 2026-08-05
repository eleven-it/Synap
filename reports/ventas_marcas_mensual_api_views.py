"""
API preset SuperArt «Hombre» — ventas-marcas-mensual.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permissions import user_has_full_access

from .permissions import OperationalReportsPermission
from .services.ventas_marcas_mensual_preset import (
    preset_hombre_payload,
    set_preset_hombre,
)


class VentasMarcasMensualPresetAPIView(APIView):
    """GET estado del preset; PATCH (supervisor) persiste id_manuales."""

    permission_classes = [OperationalReportsPermission]

    def get(self, request, *args, **kwargs):
        can_edit = user_has_full_access(request.user)
        return Response(preset_hombre_payload(can_edit=can_edit))

    def patch(self, request, *args, **kwargs):
        if not user_has_full_access(request.user):
            return Response(
                {
                    "detail": (
                        "Solo el usuario supervisor puede configurar "
                        "el preset SuperArt «Hombre»."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if "id_manuales" not in request.data:
            return Response(
                {"detail": "Se requiere la lista «id_manuales»."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            stored = set_preset_hombre(
                request.data.get("id_manuales"),
                user=request.user,
                label=request.data.get("label"),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payload = preset_hombre_payload(can_edit=True)
        payload["preset_hombre"] = stored
        payload["message"] = "Preset «Hombre» actualizado."
        return Response(payload)
