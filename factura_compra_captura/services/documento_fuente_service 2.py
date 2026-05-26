from __future__ import annotations

from typing import BinaryIO

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from factura_compra_captura.models import DocumentoFuente, ExpedienteFacturaCompra
from factura_compra_captura.ocr.jobs import programar_ocr_documento
from factura_compra_captura.services.expediente_service import ExpedienteService
from factura_compra_captura.services.transiciones_estado import TransicionEstadoInvalida


class DocumentoValidacionError(ValueError):
    def __init__(self, mensaje: str, codigo: str):
        self.codigo = codigo
        super().__init__(mensaje)


def _mime_permitidos() -> set[str]:
    raw = getattr(
        settings,
        "FACTURA_COMPRA_DOCUMENTO_MIME_PERMITIDOS",
        ("image/jpeg", "image/png", "application/pdf"),
    )
    return {x.lower().strip() for x in raw}


def _max_bytes() -> int:
    return int(
        getattr(settings, "FACTURA_COMPRA_DOCUMENTO_MAX_BYTES", 15 * 1024 * 1024)
    )


def validar_archivo(upload: UploadedFile) -> tuple[str, str]:
    """Devuelve (mime_normalizado, tipo imagen|pdf)."""
    mime = (upload.content_type or "").split(";")[0].strip().lower()
    if mime not in _mime_permitidos():
        raise DocumentoValidacionError(
            f"Tipo de archivo no permitido: {mime or 'desconocido'}",
            codigo="mime_no_permitido",
        )
    size = getattr(upload, "size", None) or _contar_tamano(upload)
    if size > _max_bytes():
        raise DocumentoValidacionError(
            f"El archivo supera el tamaño máximo permitido ({_max_bytes()} bytes).",
            codigo="tamano_excedido",
        )
    if mime == "application/pdf":
        tipo = DocumentoFuente.TipoArchivo.PDF
    else:
        tipo = DocumentoFuente.TipoArchivo.IMAGEN
    return mime, tipo


def _contar_tamano(upload: BinaryIO) -> int:
    pos = upload.tell() if hasattr(upload, "tell") else None
    upload.seek(0)
    n = 0
    while True:
        chunk = upload.read(65536)
        if not chunk:
            break
        n += len(chunk)
    if pos is not None:
        upload.seek(pos)
    else:
        upload.seek(0)
    return n


@transaction.atomic
def crear_documento_desde_upload(
    expediente: ExpedienteFacturaCompra,
    upload: UploadedFile,
    *,
    actor=None,
) -> DocumentoFuente:
    if hasattr(upload, "seek"):
        upload.seek(0)
    if expediente.estado not in (
        ExpedienteFacturaCompra.Estado.BORRADOR,
        ExpedienteFacturaCompra.Estado.OCR_COMPLETADO,
    ):
        raise TransicionEstadoInvalida(
            "Solo se pueden adjuntar documentos en borrador o tras OCR previo (nueva captura).",
            codigo="captura_estado_invalido",
        )
    mime, tipo = validar_archivo(upload)
    if expediente.estado == ExpedienteFacturaCompra.Estado.OCR_COMPLETADO:
        expediente.estado = ExpedienteFacturaCompra.Estado.BORRADOR
        expediente.save(update_fields=["estado", "modificado_en"])

    doc = DocumentoFuente(
        expediente=expediente,
        nombre_original=getattr(upload, "name", "") or "",
        mime_type=mime,
        tamano_bytes=getattr(upload, "size", None) or 0,
        tipo_archivo=tipo,
        estado_procesamiento=DocumentoFuente.EstadoProcesamiento.PENDIENTE,
    )
    doc.archivo.save(upload.name, upload, save=False)
    doc.save()

    if not doc.tamano_bytes and doc.archivo:
        doc.tamano_bytes = doc.archivo.size
    doc.sha256_hex = doc.calcular_sha256()
    doc.save(update_fields=["tamano_bytes", "sha256_hex", "modificado_en"])

    ExpedienteService._registrar_evento(
        expediente,
        actor=actor,
        tipo="documento_subido",
        payload={
            "documento_fuente_id": doc.pk,
            "mime_type": mime,
            "tamano_bytes": doc.tamano_bytes,
        },
    )

    programar_ocr_documento(doc.pk)
    doc.refresh_from_db()
    return doc


@transaction.atomic
def reintentar_ocr(documento: DocumentoFuente, *, actor=None) -> DocumentoFuente:
    if documento.estado_procesamiento not in (
        DocumentoFuente.EstadoProcesamiento.FALLIDO,
        DocumentoFuente.EstadoProcesamiento.PENDIENTE,
        DocumentoFuente.EstadoProcesamiento.PROCESANDO,
    ):
        raise TransicionEstadoInvalida(
            "Solo se reintenta OCR en documentos pendientes o con fallo.",
            codigo="reintento_ocr_invalido",
        )
    documento.estado_procesamiento = DocumentoFuente.EstadoProcesamiento.PENDIENTE
    documento.ocr_error_codigo = ""
    documento.ocr_error_detalle = ""
    documento.save(
        update_fields=[
            "estado_procesamiento",
            "ocr_error_codigo",
            "ocr_error_detalle",
            "modificado_en",
        ]
    )
    ExpedienteService._registrar_evento(
        documento.expediente,
        actor=actor,
        tipo="ocr_reintento_solicitado",
        payload={"documento_fuente_id": documento.pk},
    )
    programar_ocr_documento(documento.pk)
    documento.refresh_from_db()
    return documento
