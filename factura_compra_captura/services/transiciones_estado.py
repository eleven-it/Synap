"""
Matriz (estado_actual, accion) -> estado_destino.
Alineado conceptualmente a docs/compras/domain_model.md §5.
"""

from __future__ import annotations

from typing import Any

from factura_compra_captura.models import ExpedienteFacturaCompra


class TransicionEstadoInvalida(ValueError):
    """Transición no permitida o precondiciones incumplidas."""

    def __init__(self, mensaje: str, codigo: str | None = None):
        self.codigo = codigo
        super().__init__(mensaje)


# (estado_origen, accion) -> estado_destino
_TRANSICIONES: dict[tuple[str, str], str] = {
    (ExpedienteFacturaCompra.Estado.BORRADOR, "marcar_ocr_completado"): ExpedienteFacturaCompra.Estado.OCR_COMPLETADO,
    (ExpedienteFacturaCompra.Estado.BORRADOR, "enviar_revision"): ExpedienteFacturaCompra.Estado.EN_REVISION,
    (ExpedienteFacturaCompra.Estado.OCR_COMPLETADO, "enviar_revision"): ExpedienteFacturaCompra.Estado.EN_REVISION,
    (ExpedienteFacturaCompra.Estado.EN_REVISION, "marcar_listo_para_aprobar"): ExpedienteFacturaCompra.Estado.LISTO_PARA_APROBAR,
    (ExpedienteFacturaCompra.Estado.EN_REVISION, "solicitar_aprobacion"): ExpedienteFacturaCompra.Estado.APROBACION_SOLICITADA,
    (ExpedienteFacturaCompra.Estado.LISTO_PARA_APROBAR, "solicitar_aprobacion"): ExpedienteFacturaCompra.Estado.APROBACION_SOLICITADA,
    (ExpedienteFacturaCompra.Estado.EN_REVISION, "rechazar"): ExpedienteFacturaCompra.Estado.RECHAZADO,
    (ExpedienteFacturaCompra.Estado.LISTO_PARA_APROBAR, "rechazar"): ExpedienteFacturaCompra.Estado.RECHAZADO,
    (ExpedienteFacturaCompra.Estado.APROBACION_SOLICITADA, "simular_posting_exitoso"): ExpedienteFacturaCompra.Estado.APROBADO,
}


def obtener_estado_destino(estado_actual: str, accion: str) -> str | None:
    return _TRANSICIONES.get((estado_actual, accion))


def validar_precondiciones(
    expediente: ExpedienteFacturaCompra,
    accion: str,
    payload: dict[str, Any] | None = None,
) -> None:
    payload = payload or {}
    if accion == "enviar_revision":
        if expediente.codigo_proveedor_legacy is None:
            raise TransicionEstadoInvalida(
                "Se requiere codigo_proveedor_legacy para enviar a revisión.",
                codigo="proveedor_requerido",
            )
        lineas = list(expediente.lineas.all())
        if not lineas:
            raise TransicionEstadoInvalida(
                "Se requiere al menos una línea.",
                codigo="lineas_requeridas",
            )
        for ln in lineas:
            if ln.id_art_legacy is None:
                raise TransicionEstadoInvalida(
                    "Cada línea debe tener id_art_legacy antes de enviar a revisión.",
                    codigo="linea_sin_articulo",
                )
            if ln.cantidad is None or ln.cantidad <= 0:
                raise TransicionEstadoInvalida(
                    "Cada línea debe tener cantidad mayor a cero.",
                    codigo="linea_cantidad_invalida",
                )
    if accion == "rechazar":
        motivo = (payload.get("motivo") or "").strip()
        if not motivo:
            raise TransicionEstadoInvalida(
                "El motivo de rechazo es obligatorio.",
                codigo="motivo_rechazo_requerido",
            )


def listar_acciones_permitidas(estado_actual: str) -> list[str]:
    return [a for (e, a) in _TRANSICIONES if e == estado_actual]
