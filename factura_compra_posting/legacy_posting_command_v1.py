"""
Implementación congelada LegacyPostingCommand v1 (subconjunto ejecutable).

Normativa: docs/compras/posting_contract.md y ADR-0006.
Cualquier cambio de forma o semántica obligatoria → versión v2 explícita.

Este módulo modela solo los campos necesarios para validaciones V-* de Fase 3–4
y el mapper desde ExpedienteFacturaCompra; el adapter legacy futuro puede
enriquecer filas hasta el shape completo del contrato sin relajar estas reglas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID


class PostingValidationError(ValueError):
    """Error de validación del comando antes de tocar MySQL legacy."""

    def __init__(self, message: str, *, code: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class PostingContextV1:
    """Subconjunto mínimo de PostingContext (posting_contract §1.2)."""

    id_usuario_legacy: int
    id_vendedor_usuario: int
    cod_sucursal: int
    fecha_servidor: date
    duplicate_check_includes_fm: bool = False


@dataclass(frozen=True)
class PostingHeaderV1:
    """Subconjunto mínimo de PostingHeader (posting_contract §1.3)."""

    codigo_proveedor: int
    fecha_comprobante: date
    importe_total: Decimal
    nro_comprobante_formateado: str
    tipo_factura: str
    tipo_factura_cabecera: str
    origen: str
    id_cond_compra: int
    cond_compra_dias: str


@dataclass(frozen=True)
class StockLineCommandV1:
    """Línea de stock — campos exigidos por validaciones cruzadas con origen / lote."""

    orden: int
    id_art: int
    cantidad: Decimal
    codigo_movimiento_oc: Optional[int] = None
    codigo_movimiento_remito: Optional[int] = None
    requiere_lote: bool = False
    cod_lote: Optional[str] = None
    vto_lote: Optional[date] = None


@dataclass(frozen=True)
class LegacyPostingCommandV1:
    idempotency_key: str
    expediente_id: UUID
    synap_empresa_id: int
    context: PostingContextV1
    header: PostingHeaderV1
    lines: tuple[StockLineCommandV1, ...]
    vales_codigos: tuple[int, ...] = ()


def validate_posting_command(cmd: LegacyPostingCommandV1) -> None:
    """
    Validaciones alineadas a posting_tests.md (UT-CMD) y posting_contract.
    Lanza PostingValidationError con code=V-xx.
    """
    # V-01
    if not cmd.lines:
        raise PostingValidationError(
            "Se requiere al menos una línea de stock.",
            code="V-01",
        )
    # V-02
    if cmd.header.importe_total is None or cmd.header.importe_total <= 0:
        raise PostingValidationError(
            "importe_total debe ser mayor a cero.",
            code="V-02",
        )
    if cmd.header.codigo_proveedor <= 0:
        raise PostingValidationError(
            "codigo_proveedor debe ser mayor a cero.",
            code="V-08",
        )
    if not (cmd.header.nro_comprobante_formateado or "").strip():
        raise PostingValidationError(
            "nro_comprobante_formateado es obligatorio.",
            code="V-HDR-NRO",
        )
    if cmd.header.tipo_factura not in ("FA", "FB", "FC", "FM"):
        raise PostingValidationError(
            "tipo_factura debe ser FA, FB, FC o FM.",
            code="V-HDR-LETRA",
        )
    origen = (cmd.header.origen or "").strip().upper()
    # V-04
    if origen == "REMITO":
        for ln in cmd.lines:
            if ln.codigo_movimiento_remito is None:
                raise PostingValidationError(
                    "Origen REMITO: cada línea debe indicar codigo_movimiento_remito.",
                    code="V-04",
                )
    # V-05
    if origen == "OC":
        for ln in cmd.lines:
            if ln.codigo_movimiento_oc is None:
                raise PostingValidationError(
                    "Origen OC: cada línea debe indicar codigo_movimiento_oc.",
                    code="V-05",
                )
    # V-06
    if origen == "VALE":
        if not cmd.vales_codigos:
            raise PostingValidationError(
                "Origen VALE: se requiere al menos un código de movimiento vale.",
                code="V-06",
            )
    # V-09
    for ln in cmd.lines:
        if ln.requiere_lote and not (ln.cod_lote or "").strip():
            raise PostingValidationError(
                f"Línea {ln.orden}: artículo con lote obligatorio sin cod_lote.",
                code="V-09",
            )
    # V-07 artículo
    for ln in cmd.lines:
        if ln.id_art <= 0:
            raise PostingValidationError(
                f"Línea {ln.orden}: id_art inválido.",
                code="V-07",
            )
    # Cantidad por línea
    for ln in cmd.lines:
        if ln.cantidad is None or ln.cantidad <= 0:
            raise PostingValidationError(
                f"Línea {ln.orden}: cantidad debe ser mayor a cero.",
                code="V-01b",
            )
    # UT-CMD-09 simplificado: contado (días 0) vs crédito
    dias = (cmd.header.cond_compra_dias or "").strip()
    if dias == "0":
        if cmd.header.importe_total <= 0:
            raise PostingValidationError(
                "Factura contado: importe_total inválido.",
                code="V-09-CONTADO",
            )
