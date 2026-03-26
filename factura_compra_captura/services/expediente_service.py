from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest

from factura_compra_captura.models import (
    EventoAuditoriaInterno,
    ExpedienteFacturaCompra,
    LineaExpedienteCompra,
)
from factura_compra_captura.services.duplicate_detection import DuplicateDetectionService
from factura_compra_captura.services.fiscal_invoice_validation import (
    FiscalInvoiceValidationService,
    resolve_base_empresa_for_compras,
    tipo_factura_desde_expediente_metadata,
)
from factura_compra_captura.services.proveedor_legacy_service import (
    buscar_proveedor_por_cuit,
    crear_proveedor_desde_borrador,
)
from factura_compra_captura.services.transiciones_estado import (
    TransicionEstadoInvalida,
    obtener_estado_destino,
    validar_precondiciones,
)
from factura_compra_captura.services.proveedor_resolution_service import (
    resolver_proveedor_desde_legacy_o_padron,
)
from factura_compra_posting.legacy_posting_command_v1 import (
    PostingValidationError,
    validate_posting_command,
)
from factura_compra_posting.mapper_v1 import map_expediente_to_command_v1
from factura_compra_posting.stub_adapter import get_posting_adapter
from factura_compra_posting.structured_log import log_factura_compra_event

logger = logging.getLogger(__name__)


def _solo_digitos_cuit(s: str) -> str:
    return "".join(ch for ch in str(s or "") if ch.isdigit())


def _cuit_11_digitos_para_resolver(expediente: ExpedienteFacturaCompra) -> str | None:
    """
    CUIT para búsqueda en AdministraNET: primero metadata.proveedor_synap,
    si no, último documento con OCR completado (campos_cabecera).
    """
    md = expediente.metadata or {}
    ps = md.get("proveedor_synap") or {}
    c = _solo_digitos_cuit(str(ps.get("cuit") or ""))
    if len(c) == 11:
        return c
    from factura_compra_captura.models import DocumentoFuente

    doc = (
        expediente.documentos_fuente.filter(
            estado_procesamiento=DocumentoFuente.EstadoProcesamiento.COMPLETADO,
        )
        .order_by("-creado_en")
        .first()
    )
    if not doc:
        return None
    cab = (doc.resultado_ocr or {}).get("campos_cabecera") or {}
    c = _solo_digitos_cuit(str(cab.get("proveedor_cuit_texto") or ""))
    if len(c) == 11:
        return c
    return None


class ExpedienteService:
    @staticmethod
    def _merge_proveedor_metadata(
        expediente: ExpedienteFacturaCompra,
        *,
        patch: dict[str, Any],
    ) -> None:
        md = dict(expediente.metadata or {})
        proveedor_synap = dict(md.get("proveedor_synap") or {})
        proveedor_synap.update(patch)
        md["proveedor_synap"] = proveedor_synap
        expediente.metadata = md

    @staticmethod
    def _asegurar_proveedor_legacy(
        expediente: ExpedienteFacturaCompra,
        *,
        base_empresa: str,
    ) -> None:
        if expediente.codigo_proveedor_legacy:
            return
        proveedor_md = dict((expediente.metadata or {}).get("proveedor_synap") or {})
        cuit = str(proveedor_md.get("cuit") or "").strip()
        if not cuit:
            raise TransicionEstadoInvalida(
                "Falta CUIT del proveedor para aprobación.",
                codigo="proveedor_cuit_requerido",
            )
        existente = buscar_proveedor_por_cuit(base_empresa, cuit)
        if existente:
            expediente.codigo_proveedor_legacy = existente.codigo
            ExpedienteService._merge_proveedor_metadata(
                expediente,
                patch={
                    "modo": "legacy_vinculado",
                    "razon_social": existente.nombre,
                    "origen": "administranet",
                },
            )
            expediente.save(update_fields=["codigo_proveedor_legacy", "metadata"])
            return
        creado = crear_proveedor_desde_borrador(
            base_empresa=base_empresa,
            cuit=cuit,
            razon_social=str(proveedor_md.get("razon_social") or ""),
            tipo_factura_sugerida=str(proveedor_md.get("tipo_factura_sugerida") or ""),
        )
        expediente.codigo_proveedor_legacy = creado.codigo
        ExpedienteService._merge_proveedor_metadata(
            expediente,
            patch={
                "modo": "legacy_vinculado",
                "razon_social": creado.nombre,
                "origen": "alta_legacy_pre_posting",
            },
        )
        expediente.save(update_fields=["codigo_proveedor_legacy", "metadata"])

    @staticmethod
    @transaction.atomic
    def crear(
        *,
        empresa_id: int,
        origen_datos: str = ExpedienteFacturaCompra.OrigenDatos.MANUAL,
        creado_por=None,
        metadata: dict | None = None,
    ) -> ExpedienteFacturaCompra:
        exp = ExpedienteFacturaCompra.objects.create(
            empresa_id=empresa_id,
            origen_datos=origen_datos,
            creado_por=creado_por,
            metadata=metadata or {},
        )
        ExpedienteService._registrar_evento(
            exp,
            actor=creado_por,
            tipo="expediente_creado",
            payload={"estado": exp.estado},
        )
        return exp

    @staticmethod
    @transaction.atomic
    def asegurar_codigo_proveedor_desde_cuit_si_falta(
        expediente: ExpedienteFacturaCompra,
        request: HttpRequest | None,
    ) -> ExpedienteFacturaCompra:
        """
        Si aún no hay código legacy y hay CUIT (metadata u OCR), busca en AdministraNET
        y persiste el mismo resultado que POST /resolver-proveedor/.
        """
        if expediente.codigo_proveedor_legacy is not None:
            return expediente
        cuit = _cuit_11_digitos_para_resolver(expediente)
        if not cuit:
            return expediente
        base_empresa = resolve_base_empresa_for_compras(expediente, request)
        if not base_empresa:
            return expediente
        md = dict(expediente.metadata or {})
        ps = md.get("proveedor_synap") or {}
        razon = str(ps.get("razon_social") or "").strip()
        try:
            out = resolver_proveedor_desde_legacy_o_padron(
                base_empresa=base_empresa,
                cuit=cuit,
                razon_social_borrador=razon,
                tipo_factura_borrador=tipo_factura_desde_expediente_metadata(
                    expediente.metadata
                ),
            )
        except ValueError:
            return expediente
        except Exception as e:
            logger.warning(
                "asegurar_codigo_proveedor_desde_cuit_si_falta expediente=%s: %s",
                expediente.pk,
                e,
            )
            return expediente
        md = dict(expediente.metadata or {})
        md["proveedor_synap"] = out.proveedor_synap
        expediente.metadata = md
        fields = ["metadata", "modificado_en"]
        if out.codigo_proveedor_legacy is not None:
            expediente.codigo_proveedor_legacy = out.codigo_proveedor_legacy
            fields.append("codigo_proveedor_legacy")
        expediente.save(update_fields=fields)
        return expediente

    @staticmethod
    @transaction.atomic
    def actualizar(
        expediente: ExpedienteFacturaCompra,
        *,
        actor=None,
        codigo_proveedor_legacy: int | None = None,
        origen_datos: str | None = None,
        sucursal_codigo_legacy: int | None = None,
        metadata: dict | None = None,
        lineas: list[dict[str, Any]] | None = None,
        posting_header: dict[str, Any] | None = None,
        posting_context: dict[str, Any] | None = None,
        vales_codigos: list[int] | None = None,
        analyst_feedback_append: list[dict[str, Any]] | None = None,
    ) -> ExpedienteFacturaCompra:
        if expediente.estado not in (
            ExpedienteFacturaCompra.Estado.BORRADOR,
            ExpedienteFacturaCompra.Estado.OCR_COMPLETADO,
            ExpedienteFacturaCompra.Estado.EN_REVISION,
        ):
            raise TransicionEstadoInvalida(
                "No se puede editar el expediente en el estado actual.",
                codigo="edicion_no_permitida",
            )
        if codigo_proveedor_legacy is not None:
            expediente.codigo_proveedor_legacy = codigo_proveedor_legacy
        if origen_datos is not None:
            expediente.origen_datos = origen_datos
        if sucursal_codigo_legacy is not None:
            expediente.sucursal_codigo_legacy = sucursal_codigo_legacy
        if analyst_feedback_append:
            from factura_compra_captura.services.supplier_template_engine import (
                append_analyst_correction,
            )

            md = dict(expediente.metadata or {})
            fb = md.get("analyst_feedback")
            for c in analyst_feedback_append:
                if not isinstance(c, dict):
                    continue
                campo = str(c.get("campo") or "").strip()
                if not campo:
                    continue
                fb = append_analyst_correction(
                    fb,
                    campo=campo[:200],
                    valor_anterior=c.get("valor_anterior"),
                    valor_nuevo=c.get("valor_nuevo"),
                )
            md["analyst_feedback"] = fb
            expediente.metadata = md
        if metadata is not None:
            md = dict(expediente.metadata or {})
            md.update(metadata)
            expediente.metadata = md
        if (
            posting_header is not None
            or posting_context is not None
            or vales_codigos is not None
        ):
            md = dict(expediente.metadata or {})
            pv = dict(md.get("posting_v1") or {})
            if posting_header is not None and isinstance(posting_header, dict):
                h = dict(pv.get("header") or {})
                h.update(posting_header)
                pv["header"] = h
            if posting_context is not None and isinstance(posting_context, dict):
                ctx = dict(pv.get("context") or {})
                ctx.update(posting_context)
                pv["context"] = ctx
            if vales_codigos is not None:
                pv["vales_codigos"] = list(vales_codigos)
            md["posting_v1"] = pv
            expediente.metadata = md
        expediente.save()
        if lineas is not None:
            expediente.lineas.all().delete()
            for row in lineas:
                LineaExpedienteCompra.objects.create(
                    expediente=expediente,
                    orden=int(row["orden"]),
                    id_art_legacy=row.get("id_art_legacy"),
                    codgasto_legacy=row.get("codgasto_legacy"),
                    cantidad=Decimal(str(row.get("cantidad", 0))),
                    precio_unitario=Decimal(str(row.get("precio_unitario", 0))),
                    codigo_movimiento_oc=row.get("codigo_movimiento_oc"),
                    codigo_movimiento_remito=row.get("codigo_movimiento_remito"),
                    metadata=row.get("metadata") or {},
                )
        ExpedienteService._registrar_evento(
            expediente,
            actor=actor,
            tipo="expediente_actualizado",
            payload={"campos": True, "lineas": lineas is not None},
        )
        return expediente

    @staticmethod
    @transaction.atomic
    def aprobar_expediente_con_stub(
        expediente: ExpedienteFacturaCompra,
        *,
        actor=None,
        base_empresa: str | None = None,
        request: HttpRequest | None = None,
    ) -> ExpedienteFacturaCompra:
        """
        Transición a aprobado con posting fake/noop según settings.
        Valida LegacyPostingCommandV1 antes de invocar el adapter.
        Duplicados y fiscal (AFIP) se evalúan antes de preflight del adapter.
        """
        if expediente.estado != ExpedienteFacturaCompra.Estado.APROBACION_SOLICITADA:
            raise TransicionEstadoInvalida(
                "Solo se aprueba desde estado aprobación solicitada.",
                codigo="aprobacion_estado_invalido",
            )
        expediente = ExpedienteFacturaCompra.objects.select_for_update().get(
            pk=expediente.pk
        )
        if expediente.estado != ExpedienteFacturaCompra.Estado.APROBACION_SOLICITADA:
            raise TransicionEstadoInvalida(
                "El expediente ya no está en aprobación solicitada.",
                codigo="aprobacion_estado_invalido",
            )
        backend = getattr(
            settings, "FACTURA_COMPRA_POSTING_BACKEND", "fake"
        )
        if backend == "noop":
            raise TransicionEstadoInvalida(
                "Posting simulado no disponible con FACTURA_COMPRA_POSTING_BACKEND=noop.",
                codigo="posting_noop",
            )
        adapter = get_posting_adapter()
        nuevo = expediente.posting_attempt + 1
        key = f"{expediente.id}:{nuevo}"
        be = (base_empresa or "").strip() or None
        if be is None:
            be = resolve_base_empresa_for_compras(expediente, request)
        ExpedienteService._asegurar_proveedor_legacy(expediente, base_empresa=be)
        expediente.refresh_from_db(fields=["codigo_proveedor_legacy", "metadata"])
        cmd = map_expediente_to_command_v1(
            expediente,
            idempotency_key=key,
        )
        try:
            validate_posting_command(cmd)
        except PostingValidationError as e:
            raise TransicionEstadoInvalida(
                str(e),
                codigo=e.code,
            ) from e

        dup = DuplicateDetectionService.check_for_approval(
            expediente,
            cmd,
            exclude_expediente_id=expediente.id,
        )
        if dup.blocking:
            raise TransicionEstadoInvalida(
                "Ya existe un expediente con el mismo comprobante para este proveedor.",
                codigo="duplicate_factura_synap",
            )

        fiscal = FiscalInvoiceValidationService.validate_for_approval(
            expediente,
            cmd,
            base_empresa=be,
        )
        if fiscal.blocking:
            codigo = (
                fiscal.reason_codes[0]
                if fiscal.reason_codes
                else "fiscal_afip_invalid"
            )
            msg = (
                fiscal.details.get("afip_error")
                or fiscal.details.get("detail")
                or "Validación fiscal no superada."
            )
            raise TransicionEstadoInvalida(str(msg), codigo=codigo)

        pre = adapter.preflight(cmd)
        if not pre.ok:
            raise TransicionEstadoInvalida(
                pre.message or "Preflight de posting no superado.",
                codigo=pre.code or "preflight_fallo",
            )
        resultado = adapter.execute(cmd)
        estado_anterior = expediente.estado
        expediente.estado = ExpedienteFacturaCompra.Estado.APROBADO
        expediente.legacy_codigo_movimiento = resultado.codigo_movimiento
        expediente.legacy_nro_comprobante = resultado.nro_comprobante
        expediente.posting_status = ExpedienteFacturaCompra.PostingStatus.POSTED
        expediente.posting_attempt = nuevo
        expediente.idempotency_key_last = key
        expediente.save()
        ExpedienteService._registrar_evento(
            expediente,
            actor=actor,
            tipo="aprobacion_posting_stub",
            payload={
                "estado_anterior": estado_anterior,
                "codigo_movimiento": resultado.codigo_movimiento,
                "nro_comprobante": resultado.nro_comprobante,
                "warnings": list(resultado.warnings),
            },
        )
        log_factura_compra_event(
            logger,
            "aprobacion_stub_ok",
            expediente_id=str(expediente.id),
            codigo_movimiento=resultado.codigo_movimiento,
            extra={"nro_comprobante": resultado.nro_comprobante},
        )
        return expediente

    @staticmethod
    @transaction.atomic
    def aplicar_transicion(
        expediente: ExpedienteFacturaCompra,
        accion: str,
        *,
        actor=None,
        payload: dict[str, Any] | None = None,
        request: HttpRequest | None = None,
    ) -> ExpedienteFacturaCompra:
        payload = payload or {}
        if accion == "simular_posting_exitoso":
            validar_precondiciones(expediente, accion, payload)
            ExpedienteService.aprobar_expediente_con_stub(
                expediente,
                actor=actor,
                request=request,
            )
            expediente.refresh_from_db()
            ExpedienteService._registrar_evento(
                expediente,
                actor=actor,
                tipo="transicion_estado",
                payload={
                    "accion": accion,
                    "estado_anterior": ExpedienteFacturaCompra.Estado.APROBACION_SOLICITADA,
                    "estado_nuevo": expediente.estado,
                },
            )
            return expediente

        destino = obtener_estado_destino(expediente.estado, accion)
        if destino is None:
            raise TransicionEstadoInvalida(
                f'Transición no permitida: estado={expediente.estado!r} acción={accion!r}',
                codigo="transicion_invalida",
            )
        validar_precondiciones(expediente, accion, payload)
        estado_anterior = expediente.estado
        if accion == "rechazar":
            expediente.rechazo_motivo = (payload.get("motivo") or "").strip()
        expediente.estado = destino
        expediente.save()
        ExpedienteService._registrar_evento(
            expediente,
            actor=actor,
            tipo="transicion_estado",
            payload={
                "accion": accion,
                "estado_anterior": estado_anterior,
                "estado_nuevo": destino,
            },
        )
        return expediente

    @staticmethod
    def _registrar_evento(expediente, *, actor, tipo: str, payload: dict):
        EventoAuditoriaInterno.objects.create(
            expediente=expediente,
            actor=actor,
            tipo_evento=tipo,
            payload=payload,
        )
