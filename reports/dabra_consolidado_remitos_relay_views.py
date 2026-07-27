"""
Vistas GET relay — Informe DABRA consolidado remitos.

- GET preview JSON: /api/reports/dabra-consolidado-remitos/relay/
- GET export xlsx: /api/reports/dabra-consolidado-remitos/relay/export/
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from reports.permissions import DabraConsolidadoRemitosPermission
from reports.services.dabra_consolidado_remitos import get_dabra_consolidado_remitos
from reports.services.dabra_consolidado_remitos_export import exportar_dabra_xlsx

logger = logging.getLogger(__name__)


def _session_user(request: Request) -> Dict[str, Any]:
    return (getattr(request, "session", None) or {}).get("user") or {}


def _base_empresa(request: Request) -> Optional[str]:
    bu = _session_user(request).get("base_empresa")
    return str(bu).strip() if bu else None


def _parse_mes_anio(request: Request) -> tuple[Optional[int], Optional[int], Optional[str]]:
    mes_raw = request.query_params.get("mes")
    anio_raw = request.query_params.get("anio") or request.query_params.get("año")
    if mes_raw is None or mes_raw == "":
        return None, None, "Parámetro mes es obligatorio (1–12)."
    if anio_raw is None or anio_raw == "":
        return None, None, "Parámetro anio es obligatorio."
    try:
        mes = int(mes_raw)
        anio = int(anio_raw)
    except (TypeError, ValueError):
        return None, None, "Mes y año deben ser enteros válidos."
    if mes < 1 or mes > 12:
        return None, None, "Mes inválido (debe ser 1–12)."
    return mes, anio, None


class DabraConsolidadoRemitosRelayAPIView(APIView):
    """GET preview JSON del informe DABRA."""

    permission_classes = [DabraConsolidadoRemitosPermission]

    def get(self, request: Request) -> Response:
        base = _base_empresa(request)
        if not base:
            return Response(
                {"detail": "No se encontró base_empresa en la sesión."},
                status=400,
            )

        mes, anio, err = _parse_mes_anio(request)
        if err:
            return Response({"detail": err}, status=400)

        try:
            result = get_dabra_consolidado_remitos(base, mes=mes, anio=anio)
        except ValueError as ve:
            return Response({"detail": str(ve)}, status=400)
        except Exception:
            logger.exception("dabra_consolidado_remitos preview base=%s", base)
            return Response({"detail": "Error al ejecutar el informe DABRA."}, status=500)

        return Response(result)


class DabraConsolidadoRemitosExportAPIView(APIView):
    """GET export Excel; 409 si hay errores de validación Σ."""

    permission_classes = [DabraConsolidadoRemitosPermission]

    def get(self, request: Request):
        base = _base_empresa(request)
        if not base:
            return Response(
                {"detail": "No se encontró base_empresa en la sesión."},
                status=400,
            )

        mes, anio, err = _parse_mes_anio(request)
        if err:
            return Response({"detail": err}, status=400)

        try:
            result = get_dabra_consolidado_remitos(base, mes=mes, anio=anio)
        except ValueError as ve:
            return Response({"detail": str(ve)}, status=400)
        except Exception:
            logger.exception("dabra_consolidado_remitos export base=%s", base)
            return Response({"detail": "Error al generar el export DABRA."}, status=500)

        if result.get("errores"):
            return Response(
                {
                    "detail": "No se puede exportar: hay errores de validación de totales.",
                    "errores": result["errores"],
                },
                status=409,
            )

        return exportar_dabra_xlsx(result, mes=mes, anio=anio)
