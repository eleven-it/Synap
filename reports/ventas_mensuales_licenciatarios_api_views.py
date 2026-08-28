# -*- coding: utf-8 -*-
"""API staff — match cliente seed ↔ AdministraNET (informe licenciatarios)."""
from __future__ import annotations

import logging
from typing import Any, Optional

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import str_or_default, to_int_or_none
from core.utils.permissions import user_has_full_access, user_has_permission

from reports.models import MonthlyReportingClientMatch
from reports.permissions import OperationalReportsPermission
from reports.services.monthly_reporting_client_match_service import (
    MatchActor,
    apply_client_match,
    format_audit_fecha,
    format_match_updated_at,
    undo_client_match,
)
from reports.services.monthly_reporting_superart_service import (
    get_active_catalog_version,
    list_qa_pending,
    resolve_superart_genero,
)
from reports.services.ventas_mensuales_licenciatarios_query import search_anet_clients

logger = logging.getLogger(__name__)

PERM_CLASIFICAR_SUPERART = "reports.licenciatarios_clasificar_superart"


def _can_clasificar_superart(user) -> bool:
    """Supervisor (puesto/usuario) o permiso dedicado de clasificación SuperArt."""
    return user_has_permission(user, PERM_CLASIFICAR_SUPERART)


def _base_empresa_request(request) -> str:
    session = getattr(request, "session", None)
    session_user = session.get("user", {}) if session else {}
    return str_or_default(session_user.get("base_empresa"), "").strip()


def _match_actor(request) -> MatchActor:
    session = getattr(request, "session", None)
    session_user = session.get("user", {}) if session else {}
    user = getattr(request, "user", None)
    return MatchActor(
        id_usuario=to_int_or_none(session_user.get("id_usuario")),
        cod_usuario=str_or_default(getattr(user, "cod_usuario", session_user.get("cod_usuario")), ""),
        nombre=str_or_default(session_user.get("nombre") or getattr(user, "nombre", None), ""),
    )


def serialize_client_match(match: MonthlyReportingClientMatch) -> dict[str, Any]:
    """Payload JSON para listado/panel de match."""
    audits = [
        {
            "fecha": format_audit_fecha(audit),
            "before": audit.before_json,
            "after": audit.after_json,
            "actor_cod_usuario": audit.actor_cod_usuario,
            "actor_nombre": audit.actor_nombre,
        }
        for audit in match.audits.order_by("-created_at")[:5]
    ]
    return {
        "id": match.id,
        "seed_key": match.seed_key,
        "seed_customer_code": match.seed_customer_code,
        "seed_customer_name": match.seed_customer_name,
        "seed_city": match.seed_city,
        "estado": match.estado,
        "anet_cliente_id": match.anet_cliente_id,
        "base_empresa": match.base_empresa,
        "updated_at_display": format_match_updated_at(match),
        "pending": match.estado == MonthlyReportingClientMatch.Estado.PENDING,
        "audits": audits,
    }


class LicenciatariosClientMatchesListAPIView(APIView):
    """GET listado de matches pendientes/matcheados."""

    permission_classes = [OperationalReportsPermission]

    def get(self, request, *args, **kwargs):
        can_edit = user_has_full_access(request.user)
        estado = str_or_default(request.query_params.get("estado"), "").strip().lower()
        qs = MonthlyReportingClientMatch.objects.all().order_by("seed_customer_name")
        if estado in {"pending", "matched"}:
            qs = qs.filter(estado=estado)
        matches = [serialize_client_match(m) for m in qs[:500]]
        pending_count = MonthlyReportingClientMatch.objects.filter(
            estado=MonthlyReportingClientMatch.Estado.PENDING
        ).count()
        return Response(
            {
                "matches": matches,
                "pending_count": pending_count,
                "can_edit": can_edit,
            }
        )


class LicenciatariosClientMatchDetailAPIView(APIView):
    """PATCH apply/undo match auditable."""

    permission_classes = [OperationalReportsPermission]

    def patch(self, request, match_id: int, *args, **kwargs):
        if not user_has_full_access(request.user):
            return Response(
                {
                    "detail": (
                        "Solo usuarios con alcance global autorizado pueden "
                        "vincular o desvincular clientes históricos."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        match = get_object_or_404(MonthlyReportingClientMatch, pk=match_id)
        action = str_or_default(request.data.get("action"), "apply").strip().lower()
        actor = _match_actor(request)

        if action == "undo":
            if match.estado != MonthlyReportingClientMatch.Estado.MATCHED:
                return Response(
                    {"detail": "Solo se puede desvincular un cliente ya matcheado."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            undo_client_match(match, actor=actor)
            match.refresh_from_db()
            payload = serialize_client_match(match)
            payload["message"] = "Vínculo revocado; cliente en pendiente."
            return Response(payload)

        anet_id = to_int_or_none(request.data.get("anet_cliente_id"))
        if anet_id is None:
            return Response(
                {"detail": "Se requiere «anet_cliente_id» para vincular."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        base_empresa = str_or_default(
            request.data.get("base_empresa") or _base_empresa_request(request),
            "",
        ).strip()
        if not base_empresa:
            return Response(
                {"detail": "Falta base_empresa en sesión o en el cuerpo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            apply_client_match(
                match,
                anet_cliente_id=anet_id,
                base_empresa=base_empresa,
                actor=actor,
            )
        except Exception as exc:
            logger.exception("apply_client_match: %s", exc)
            return Response(
                {"detail": "No se pudo guardar el vínculo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        match.refresh_from_db()
        payload = serialize_client_match(match)
        payload["message"] = "Cliente histórico vinculado a AdministraNET."
        return Response(payload)


def _format_qa_datetime(dt) -> str:
    if not dt:
        return ""
    return dt.strftime("%d/%m/%Y %H:%M")


def serialize_qa_pending(pending) -> dict[str, Any]:
    return {
        "superart": pending.superart,
        "occurrence_count": pending.occurrence_count,
        "sample_json": pending.sample_json or {},
        "first_seen_at": pending.first_seen_at.isoformat() if pending.first_seen_at else "",
        "last_seen_at": pending.last_seen_at.isoformat() if pending.last_seen_at else "",
        "first_seen_display": _format_qa_datetime(pending.first_seen_at),
        "last_seen_display": _format_qa_datetime(pending.last_seen_at),
    }


class LicenciatariosSuperArtQAListAPIView(APIView):
    """GET pendientes SuperArt · POST clasificar uno (men/women)."""

    permission_classes = [OperationalReportsPermission]

    def get(self, request, *args, **kwargs):
        can_edit = _can_clasificar_superart(request.user)
        active = get_active_catalog_version()
        pending = [serialize_qa_pending(p) for p in list_qa_pending()[:500]]
        return Response(
            {
                "pending": pending,
                "pending_count": len(pending),
                "can_edit": can_edit,
                "catalog_version": active.version if active else None,
            }
        )

    def post(self, request, *args, **kwargs):
        if not _can_clasificar_superart(request.user):
            return Response(
                {
                    "detail": (
                        "Se requiere el permiso "
                        f"«{PERM_CLASIFICAR_SUPERART}» "
                        "(puesto Supervisor o asignación explícita) para "
                        "clasificar SuperArt desconocidos."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        superart = str_or_default(request.data.get("superart"), "").strip()
        genero = str_or_default(request.data.get("genero"), "").strip().lower()
        if not superart:
            return Response(
                {"detail": "Se requiere «superart»."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        actor = _match_actor(request)
        try:
            entry = resolve_superart_genero(
                superart,
                genero,
                actor_id_usuario=actor.id_usuario,
                actor_cod_usuario=actor.cod_usuario,
                actor_nombre=actor.nombre,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("resolve_superart_genero: %s", exc)
            return Response(
                {"detail": "No se pudo clasificar el SuperArt."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pending_count = list_qa_pending().count()
        payload = {
            **entry,
            "message": f"SuperArt «{entry['superart']}» clasificado como {entry['genero']}.",
            "pending_count": pending_count,
        }
        return Response(payload)


class LicenciatariosSuperArtQABulkAPIView(APIView):
    """POST clasificación masiva [{superart, genero}, …]."""

    permission_classes = [OperationalReportsPermission]

    def post(self, request, *args, **kwargs):
        if not _can_clasificar_superart(request.user):
            return Response(
                {
                    "detail": (
                        "Se requiere el permiso "
                        f"«{PERM_CLASIFICAR_SUPERART}» "
                        "(puesto Supervisor o asignación explícita) para "
                        "clasificar SuperArt desconocidos."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        items = request.data.get("items")
        if not isinstance(items, list) or not items:
            return Response(
                {"detail": "Se requiere «items» con al menos un SuperArt."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        actor = _match_actor(request)
        resolved = []
        errors = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append({"index": idx, "detail": "Ítem inválido."})
                continue
            superart = str_or_default(item.get("superart"), "").strip()
            genero = str_or_default(item.get("genero"), "").strip().lower()
            try:
                entry = resolve_superart_genero(
                    superart,
                    genero,
                    actor_id_usuario=actor.id_usuario,
                    actor_cod_usuario=actor.cod_usuario,
                    actor_nombre=actor.nombre,
                )
                resolved.append(entry)
            except ValueError as exc:
                errors.append({"index": idx, "superart": superart, "detail": str(exc)})
            except Exception as exc:
                logger.exception("resolve_superart_genero bulk idx=%s: %s", idx, exc)
                errors.append(
                    {"index": idx, "superart": superart, "detail": "Error al clasificar."}
                )
        pending_count = list_qa_pending().count()
        return Response(
            {
                "resolved": resolved,
                "errors": errors,
                "pending_count": pending_count,
                "message": f"{len(resolved)} SuperArt(s) clasificado(s).",
            }
        )


class LicenciatariosAnetClientsAPIView(APIView):
    """GET búsqueda RO de clientes AdministraNET (?q=)."""

    permission_classes = [OperationalReportsPermission]

    def get(self, request, *args, **kwargs):
        base = _base_empresa_request(request)
        if not base:
            return Response(
                {"detail": "Falta base_empresa en la sesión."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        q = str_or_default(request.query_params.get("q"), "")
        if len(q.strip()) < 2:
            return Response({"results": []})
        try:
            results = search_anet_clients(base, q)
            return Response({"results": results})
        except Exception as exc:
            logger.exception("search_anet_clients: %s", exc)
            return Response(
                {"detail": "Error al buscar clientes AdministraNET."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
