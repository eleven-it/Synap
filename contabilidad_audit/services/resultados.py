"""Contratos y helpers de resultados de auditoría contable."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Protocol

from django.utils import timezone


@dataclass
class Diferencia:
    id_pc: Optional[int] = None
    cod_pc: Optional[str] = None
    id_ejercicio: Optional[int] = None
    id_periodo: Optional[int] = None
    codigo_movimiento: Optional[str] = None
    nro_asiento: Optional[int] = None
    valor_esperado: Optional[Decimal] = None
    valor_actual: Optional[Decimal] = None
    delta: Optional[Decimal] = None
    referencia_hallazgo: str = ""
    detalle: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditResult:
    check_id: str
    titulo: str
    severidad: str
    ok: bool
    total_evaluado: int
    total_diferencias: int
    diferencias: list[Diferencia]
    resumen: dict[str, Any]
    config_hash: str
    corrida_id: str
    fecha_corrida: str
    error: Optional[str] = None


class Filtros(Protocol):
    base_empresa: str
    id_ejercicio: int
    id_periodo: Optional[int]
    fecha_desde: Optional[str]
    fecha_hasta: Optional[str]


class Check(Protocol):
    check_id: str
    titulo: str
    severidad: str

    def __call__(
        self,
        base_empresa: str,
        filtros: dict,
        politica: dict,
        contexto: "CorridaContexto",
    ) -> AuditResult: ...


@dataclass
class CorridaContexto:
    """Contexto compartido por corrida: un cursor MySQL y metadatos Postgres."""

    cursor: Any
    corrida_id: str
    config_hash: str
    fecha_corrida: datetime = field(default_factory=timezone.now)


def formatear_fecha_corrida(fecha: datetime) -> str:
    """Formato dd/MM/yyyy HH:mm para UI."""
    local = timezone.localtime(fecha) if timezone.is_aware(fecha) else fecha
    return local.strftime("%d/%m/%Y %H:%M")


def construir_audit_result(
    *,
    check_id: str,
    titulo: str,
    severidad: str,
    ok: bool,
    total_evaluado: int,
    diferencias: list[Diferencia],
    resumen: Optional[dict[str, Any]],
    contexto: CorridaContexto,
    error: Optional[str] = None,
    compensaciones_centavo: Optional[list[dict[str, Any]]] = None,
) -> AuditResult:
    """Arma AuditResult estándar contando diferencias reportables."""
    resumen_final = dict(resumen or {})
    if compensaciones_centavo:
        resumen_final["compensaciones_centavo"] = compensaciones_centavo
    total_diferencias = len(diferencias)
    return AuditResult(
        check_id=check_id,
        titulo=titulo,
        severidad=severidad,
        ok=ok and not error,
        total_evaluado=total_evaluado,
        total_diferencias=total_diferencias,
        diferencias=diferencias,
        resumen=resumen_final,
        config_hash=contexto.config_hash,
        corrida_id=contexto.corrida_id,
        fecha_corrida=formatear_fecha_corrida(contexto.fecha_corrida),
        error=error,
    )


def audit_result_error(
    *,
    check_id: str,
    titulo: str,
    severidad: str,
    contexto: CorridaContexto,
    mensaje: str,
) -> AuditResult:
    return construir_audit_result(
        check_id=check_id,
        titulo=titulo,
        severidad=severidad,
        ok=False,
        total_evaluado=0,
        diferencias=[],
        resumen={"error": mensaje},
        contexto=contexto,
        error=mensaje,
    )
