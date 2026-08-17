# -*- coding: utf-8 -*-
"""Servicio de match auditable cliente seed → AdministraNET."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone

from reports.models import MonthlyReportingClientMatch, MonthlyReportingClientMatchAudit


@dataclass(frozen=True)
class MatchActor:
    id_usuario: Optional[int] = None
    cod_usuario: str = ""
    nombre: str = ""


def resolve_client_identity(match: MonthlyReportingClientMatch, base_empresa: str = "") -> str:
    """Identidad estable para agregados: seed pendiente o anet matcheado."""
    if match.estado == MonthlyReportingClientMatch.Estado.MATCHED and match.anet_cliente_id:
        base = (base_empresa or match.base_empresa or "default").strip()
        return f"anet:{base}:{match.anet_cliente_id}"
    return f"seed:{match.seed_key}"


def match_to_aggregate_row(match: MonthlyReportingClientMatch, base_empresa: str = "") -> dict[str, Any]:
    """Metadatos de cliente para filas agregadas (pendientes visibles)."""
    return {
        "identity": resolve_client_identity(match, base_empresa),
        "seed_key": match.seed_key,
        "display_name": match.seed_customer_name,
        "match_estado": match.estado,
        "anet_cliente_id": match.anet_cliente_id,
        "pending": match.estado == MonthlyReportingClientMatch.Estado.PENDING,
    }


@transaction.atomic
def apply_client_match(
    match: MonthlyReportingClientMatch,
    *,
    anet_cliente_id: int,
    base_empresa: str,
    actor: Optional[MatchActor] = None,
) -> MonthlyReportingClientMatch:
    """Vincula cliente histórico a AdministraNET con auditoría JSON."""
    actor = actor or MatchActor()
    before = {
        "estado": match.estado,
        "anet_cliente_id": match.anet_cliente_id,
        "base_empresa": match.base_empresa,
    }
    match.estado = MonthlyReportingClientMatch.Estado.MATCHED
    match.anet_cliente_id = int(anet_cliente_id)
    match.base_empresa = str(base_empresa or "").strip()
    match.actor_id_usuario = actor.id_usuario
    match.actor_cod_usuario = actor.cod_usuario
    match.actor_nombre = actor.nombre
    match.save(
        update_fields=[
            "estado",
            "anet_cliente_id",
            "base_empresa",
            "actor_id_usuario",
            "actor_cod_usuario",
            "actor_nombre",
            "updated_at",
        ]
    )
    after = {
        "estado": match.estado,
        "anet_cliente_id": match.anet_cliente_id,
        "base_empresa": match.base_empresa,
    }
    MonthlyReportingClientMatchAudit.objects.create(
        match=match,
        before_json=before,
        after_json=after,
        actor_id_usuario=actor.id_usuario,
        actor_cod_usuario=actor.cod_usuario,
        actor_nombre=actor.nombre,
    )
    return match


def format_audit_fecha(audit: MonthlyReportingClientMatchAudit) -> str:
    """Fecha auditoría en formato dd/MM/yyyy para UI."""
    ts = audit.created_at or timezone.now()
    if timezone.is_aware(ts):
        ts = timezone.localtime(ts)
    return ts.strftime("%d/%m/%Y")


def format_match_updated_at(match: MonthlyReportingClientMatch) -> str:
    """Fecha última actualización del match en dd/MM/yyyy para UI."""
    ts = match.updated_at or timezone.now()
    if timezone.is_aware(ts):
        ts = timezone.localtime(ts)
    return ts.strftime("%d/%m/%Y")


@transaction.atomic
def undo_client_match(
    match: MonthlyReportingClientMatch,
    *,
    actor: Optional[MatchActor] = None,
) -> MonthlyReportingClientMatch:
    """Revoca vínculo seed→ANET dejando el cliente en pendiente."""
    actor = actor or MatchActor()
    before = {
        "estado": match.estado,
        "anet_cliente_id": match.anet_cliente_id,
        "base_empresa": match.base_empresa,
    }
    match.estado = MonthlyReportingClientMatch.Estado.PENDING
    match.anet_cliente_id = None
    match.base_empresa = ""
    match.actor_id_usuario = actor.id_usuario
    match.actor_cod_usuario = actor.cod_usuario
    match.actor_nombre = actor.nombre
    match.save(
        update_fields=[
            "estado",
            "anet_cliente_id",
            "base_empresa",
            "actor_id_usuario",
            "actor_cod_usuario",
            "actor_nombre",
            "updated_at",
        ]
    )
    after = {
        "estado": match.estado,
        "anet_cliente_id": match.anet_cliente_id,
        "base_empresa": match.base_empresa,
    }
    MonthlyReportingClientMatchAudit.objects.create(
        match=match,
        before_json=before,
        after_json=after,
        actor_id_usuario=actor.id_usuario,
        actor_cod_usuario=actor.cod_usuario,
        actor_nombre=actor.nombre,
    )
    return match
