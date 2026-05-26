"""
Ejecución del pipeline OCR sobre un DocumentoFuente persistido.
No bloquea el expediente ante fallo: solo marca documento y deja expediente en borrador.
"""

from __future__ import annotations

import logging
import os
import tempfile

from django.core.files.storage import default_storage
from django.db import transaction

from factura_compra_captura.models import DocumentoFuente, ExpedienteFacturaCompra
from factura_compra_captura.ocr.base import OcrAdapterError
from factura_compra_captura.ocr.factory import get_ocr_adapter
from factura_compra_captura.services.expediente_service import ExpedienteService

logger = logging.getLogger(__name__)


def _resolver_ruta_local(doc: DocumentoFuente) -> tuple[str, bool]:
    """
    Devuelve (ruta, debe_borrar_temp).
    Compatible con FileSystemStorage (.path) y storages remotos (temporal).
    """
    f = doc.archivo
    try:
        name = f.name
        if default_storage.exists(name):
            path = default_storage.path(name)
            return path, False
    except Exception:
        pass
    try:
        path_real = f.path
        return path_real, False
    except Exception:
        pass
    suf = os.path.splitext(doc.nombre_original or "")[1] or ".bin"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suf)
    with doc.archivo.open("rb") as src:
        for chunk in iter(lambda: src.read(65536), b""):
            tmp.write(chunk)
    tmp.close()
    return tmp.name, True


@transaction.atomic
def ejecutar_pipeline_ocr(documento_fuente_id: int) -> None:
    doc = (
        DocumentoFuente.objects.select_for_update()
        .select_related("expediente")
        .get(pk=documento_fuente_id)
    )
    if doc.estado_procesamiento == DocumentoFuente.EstadoProcesamiento.COMPLETADO:
        logger.info("OCR omitido: documento %s ya completado.", documento_fuente_id)
        return

    doc.ocr_intento += 1
    doc.estado_procesamiento = DocumentoFuente.EstadoProcesamiento.PROCESANDO
    doc.ocr_error_codigo = ""
    doc.ocr_error_detalle = ""
    doc.save(
        update_fields=[
            "ocr_intento",
            "estado_procesamiento",
            "ocr_error_codigo",
            "ocr_error_detalle",
            "modificado_en",
        ]
    )

    ruta, borrar_temp = _resolver_ruta_local(doc)
    resultado = None
    try:
        adapter = get_ocr_adapter()
        resultado = adapter.extract(ruta_archivo=ruta, mime_type=doc.mime_type or "")
    except OcrAdapterError as e:
        _marcar_fallo(doc, codigo=e.codigo, detalle=str(e))
        resultado = None
    except Exception as e:
        logger.exception("OCR inesperado documento=%s", documento_fuente_id)
        _marcar_fallo(doc, codigo="ocr_excepcion", detalle=str(e))
        resultado = None
    finally:
        if borrar_temp and ruta and os.path.isfile(ruta):
            try:
                os.unlink(ruta)
            except OSError:
                pass

    if resultado is None:
        return

    doc.resultado_ocr = {
        "texto_plano": resultado.texto_plano,
        "confianza_global": resultado.confianza_global,
        "campos_cabecera": resultado.campos_cabecera,
        "lineas_sugeridas": resultado.lineas_sugeridas,
        "raw": resultado.raw,
    }
    doc.estado_procesamiento = DocumentoFuente.EstadoProcesamiento.COMPLETADO
    doc.save(
        update_fields=["resultado_ocr", "estado_procesamiento", "modificado_en"]
    )

    exp = doc.expediente
    if exp.estado == ExpedienteFacturaCompra.Estado.BORRADOR:
        exp.estado = ExpedienteFacturaCompra.Estado.OCR_COMPLETADO
        meta = dict(exp.metadata or {})
        meta["ocr_ultimo_documento_id"] = doc.pk
        meta["ocr_confianza_global"] = resultado.confianza_global
        exp.metadata = meta
        exp.save(update_fields=["estado", "metadata", "modificado_en"])
        ExpedienteService._registrar_evento(
            exp,
            actor=None,
            tipo="ocr_completado",
            payload={"documento_fuente_id": doc.pk},
        )


def _marcar_fallo(doc: DocumentoFuente, *, codigo: str, detalle: str) -> None:
    doc.estado_procesamiento = DocumentoFuente.EstadoProcesamiento.FALLIDO
    doc.ocr_error_codigo = codigo[:64]
    doc.ocr_error_detalle = detalle[:4000]
    doc.save(
        update_fields=[
            "estado_procesamiento",
            "ocr_error_codigo",
            "ocr_error_detalle",
            "modificado_en",
        ]
    )
    exp = doc.expediente
    meta = dict(exp.metadata or {})
    meta["ocr_ultimo_error"] = {"codigo": codigo, "documento_id": doc.pk}
    exp.metadata = meta
    exp.save(update_fields=["metadata", "modificado_en"])
    ExpedienteService._registrar_evento(
        exp,
        actor=None,
        tipo="ocr_fallido",
        payload={"documento_fuente_id": doc.pk, "codigo": codigo},
    )
