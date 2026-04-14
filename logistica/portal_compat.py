"""
Contrato futuro — Portal de cliente (solo preparación, sin rutas HTTP).

La trazabilidad operativa vive en MySQL ``comp_ped`` y se refleja en el informe
``/reports/dashboard/comprobantes-rutas/``. El portal podrá reutilizar la misma
lectura sin duplicar negocio.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class EntregaTrazabilidadCliente:
    """Vista estable para exposición futura al cliente B2B (solo lectura)."""

    cod_mov_remito: Optional[int]
    nro_remito: Optional[str]
    entregado_raw: Optional[str]
    estado_entrega_etiqueta: str
    fecha_hora_entrega: Optional[str]
    motivo_no_entrega: Optional[str]
    detalle_no_entrega: Optional[str]
    nombre_usuario_registro: Optional[str]


def entrega_desde_detalle_remito(data: Dict[str, Any]) -> EntregaTrazabilidadCliente:
    """
    Normaliza el dict devuelto por ``obtener_detalle_remito`` (claves legado
    mezcladas). No accede a BD.
    """
    from logistica.services.lista_comprobantes_rutas import estado_entrega_label

    cod = data.get("codMovRemito") or data.get("cod_mov_remito")
    nro = data.get("nroRemito") or data.get("nro_remito")
    ent = data.get("entregado")
    motivo = data.get("motivo_no_entrega")
    detalle = data.get("detalle_no_entrega")
    fh = data.get("fechaHoraEntregaB") or data.get("fecha_hora_entrega_fmt")
    nu = data.get("nombreUsuarioNoEntrega") or data.get("nombre_usuario_entrega")

    try:
        cod_i = int(cod) if cod is not None else None
    except (TypeError, ValueError):
        cod_i = None

    return EntregaTrazabilidadCliente(
        cod_mov_remito=cod_i,
        nro_remito=str(nro).strip() if nro is not None else None,
        entregado_raw=str(ent).strip() if ent is not None else None,
        estado_entrega_etiqueta=estado_entrega_label(ent, data.get("id_usuario_no_entrega")),
        fecha_hora_entrega=str(fh).strip() if fh else None,
        motivo_no_entrega=str(motivo).strip() if motivo not in (None, "") else None,
        detalle_no_entrega=str(detalle).strip() if detalle not in (None, "") else None,
        nombre_usuario_registro=str(nu).strip() if nu not in (None, "") else None,
    )
