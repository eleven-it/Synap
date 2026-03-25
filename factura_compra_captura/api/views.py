import logging

from django.shortcuts import get_object_or_404
from rest_framework import status

from core.utils.django_user_fk import usuario_extendido_para_fk
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from factura_compra_captura.api.throttles import ComprasDocumentUploadThrottle
from factura_compra_captura.api.permissions import (
    DocumentoExpedientePermission,
    ExpedienteAprobarPermission,
    ExpedienteDetailPatchPermission,
    ExpedienteEventosPermission,
    ExpedienteListCreatePermission,
    ExpedienteResolverProveedorPermission,
    ExpedienteTransicionPermission,
)
from factura_compra_captura.api.serializers import (
    DocumentoFuenteSerializer,
    EventoAuditoriaSerializer,
    ExpedienteCreateSerializer,
    ExpedienteFacturaCompraSerializer,
    ExpedientePatchSerializer,
    ResolverProveedorSerializer,
    TransicionSerializer,
)
from factura_compra_captura.models import (
    DocumentoFuente,
    EventoAuditoriaInterno,
    ExpedienteFacturaCompra,
)
from factura_compra_captura.services import ExpedienteService, TransicionEstadoInvalida
from factura_compra_captura.services.documento_fuente_service import (
    DocumentoValidacionError,
    crear_documento_desde_upload,
    reintentar_ocr,
)
from factura_compra_captura.services.fiscal_invoice_validation import (
    resolve_base_empresa_for_compras,
)
from factura_compra_captura.services.proveedor_resolution_service import (
    resolver_proveedor_desde_legacy_o_padron,
)

logger = logging.getLogger(__name__)


def _actor_api(request):
    return usuario_extendido_para_fk(getattr(request, "user", None))


def _qs_expediente_con_nidos():
    return (
        ExpedienteFacturaCompra.objects.select_related("empresa", "creado_por")
        .prefetch_related("lineas", "documentos_fuente")
    )


class ExpedienteListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, ExpedienteListCreatePermission]

    def get(self, request):
        qs = _qs_expediente_con_nidos()
        estado = request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        empresa_id = request.query_params.get("empresa")
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        data = ExpedienteFacturaCompraSerializer(
            qs.order_by("-creado_en"),
            many=True,
            context={"request": request},
        ).data
        return Response(data)

    def post(self, request):
        ser = ExpedienteCreateSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        exp = ser.save()
        out = ExpedienteFacturaCompraSerializer(
            _qs_expediente_con_nidos().get(pk=exp.pk),
            context={"request": request},
        )
        return Response(out.data, status=status.HTTP_201_CREATED)


class ExpedienteDetailPatchAPIView(APIView):
    permission_classes = [IsAuthenticated, ExpedienteDetailPatchPermission]

    def get(self, request, pk):
        exp = get_object_or_404(_qs_expediente_con_nidos(), pk=pk)
        try:
            exp = ExpedienteService.asegurar_codigo_proveedor_desde_cuit_si_falta(
                exp, request
            )
        except Exception:
            logger.exception(
                "asegurar_codigo_proveedor_desde_cuit_si_falta en GET expediente"
            )
        exp = _qs_expediente_con_nidos().get(pk=exp.pk)
        return Response(
            ExpedienteFacturaCompraSerializer(
                exp, context={"request": request}
            ).data
        )

    def patch(self, request, pk):
        exp = get_object_or_404(ExpedienteFacturaCompra.objects.all(), pk=pk)
        ser = ExpedientePatchSerializer(
            data=request.data, partial=True, context={"request": request}
        )
        ser.is_valid(raise_exception=True)
        exp = ser.update(exp, ser.validated_data)
        exp = _qs_expediente_con_nidos().get(pk=exp.pk)
        return Response(
            ExpedienteFacturaCompraSerializer(
                exp, context={"request": request}
            ).data
        )


class ExpedienteTransicionAPIView(APIView):
    permission_classes = [IsAuthenticated, ExpedienteTransicionPermission]

    def post(self, request, pk):
        exp = get_object_or_404(ExpedienteFacturaCompra.objects.all(), pk=pk)
        ser = TransicionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        exp = ser.save(
            exp,
            actor=_actor_api(request),
            request=request,
        )
        exp = _qs_expediente_con_nidos().get(pk=exp.pk)
        return Response(
            ExpedienteFacturaCompraSerializer(
                exp, context={"request": request}
            ).data
        )


class ExpedienteAprobarAPIView(APIView):
    """
    POST: aprueba expediente en estado aprobación_solicitada (posting stub / fake).
    """

    permission_classes = [IsAuthenticated, ExpedienteAprobarPermission]

    def post(self, request, pk):
        exp = get_object_or_404(ExpedienteFacturaCompra.objects.all(), pk=pk)
        try:
            exp = ExpedienteService.aprobar_expediente_con_stub(
                exp,
                actor=_actor_api(request),
                request=request,
            )
        except TransicionEstadoInvalida as e:
            return Response(
                {"detail": str(e), "codigo": e.codigo},
                status=status.HTTP_400_BAD_REQUEST,
            )
        exp = _qs_expediente_con_nidos().get(pk=exp.pk)
        return Response(
            ExpedienteFacturaCompraSerializer(
                exp, context={"request": request}
            ).data
        )


class ExpedienteEventosAPIView(APIView):
    permission_classes = [IsAuthenticated, ExpedienteEventosPermission]

    def get(self, request, pk):
        get_object_or_404(ExpedienteFacturaCompra.objects.all(), pk=pk)
        qs = EventoAuditoriaInterno.objects.filter(expediente_id=pk).order_by(
            "creado_en"
        )
        return Response(
            EventoAuditoriaSerializer(qs, many=True).data,
        )


class ExpedienteResolverProveedorAPIView(APIView):
    permission_classes = [IsAuthenticated, ExpedienteResolverProveedorPermission]

    def post(self, request, pk):
        exp = get_object_or_404(ExpedienteFacturaCompra.objects.all(), pk=pk)
        ser = ResolverProveedorSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cuit = ser.validated_data["cuit"]
        razon_social = ser.validated_data.get("razon_social") or ""
        base_empresa = resolve_base_empresa_for_compras(exp, request)
        if not base_empresa:
            return Response(
                {
                    "detail": (
                        "No se pudo determinar la base empresa AdministraNET "
                        "(sesión o FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID)."
                    ),
                    "codigo": "base_empresa_requerida",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            out = resolver_proveedor_desde_legacy_o_padron(
                base_empresa=base_empresa,
                cuit=cuit,
                razon_social_borrador=razon_social,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e), "codigo": "proveedor_cuit_invalido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        md = dict(exp.metadata or {})
        md["proveedor_synap"] = out.proveedor_synap
        exp.metadata = md
        if out.codigo_proveedor_legacy:
            exp.codigo_proveedor_legacy = out.codigo_proveedor_legacy
        exp.save(update_fields=["metadata", "codigo_proveedor_legacy", "modificado_en"])
        exp.refresh_from_db()
        resp_data: dict = {
            "detail": out.detail,
            "codigo_proveedor_legacy": out.codigo_proveedor_legacy,
            "proveedor_synap": out.proveedor_synap,
        }
        if out.codigo_proveedor_legacy and exp.estado in (
            ExpedienteFacturaCompra.Estado.BORRADOR,
            ExpedienteFacturaCompra.Estado.OCR_COMPLETADO,
        ):
            try:
                exp_tr = (
                    ExpedienteFacturaCompra.objects.select_related("empresa")
                    .prefetch_related("lineas")
                    .get(pk=exp.pk)
                )
                exp_tr = ExpedienteService.aplicar_transicion(
                    exp_tr,
                    "enviar_revision",
                    actor=_actor_api(request),
                    request=request,
                )
                resp_data["enviar_revision"] = {
                    "realizado": True,
                    "estado": exp_tr.estado,
                }
            except TransicionEstadoInvalida as e:
                resp_data["enviar_revision"] = {
                    "realizado": False,
                    "codigo": e.codigo,
                    "detail": str(e),
                }
        return Response(resp_data)


class DocumentoFuenteListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, DocumentoExpedientePermission]
    throttle_classes = [ComprasDocumentUploadThrottle]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, expediente_pk):
        get_object_or_404(ExpedienteFacturaCompra.objects.all(), pk=expediente_pk)
        qs = DocumentoFuente.objects.filter(expediente_id=expediente_pk).order_by(
            "creado_en"
        )
        return Response(
            DocumentoFuenteSerializer(
                qs, many=True, context={"request": request}
            ).data
        )

    def post(self, request, expediente_pk):
        exp = get_object_or_404(ExpedienteFacturaCompra.objects.all(), pk=expediente_pk)
        upload = request.FILES.get("archivo")
        if not upload:
            return Response(
                {"detail": "Campo multipart 'archivo' requerido.", "codigo": "archivo_requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            doc = crear_documento_desde_upload(
                exp,
                upload,
                actor=_actor_api(request),
            )
        except DocumentoValidacionError as e:
            return Response(
                {"detail": str(e), "codigo": e.codigo},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TransicionEstadoInvalida as e:
            return Response(
                {"detail": str(e), "codigo": e.codigo},
                status=status.HTTP_400_BAD_REQUEST,
            )
        out = DocumentoFuenteSerializer(doc, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)


class DocumentoFuenteDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, DocumentoExpedientePermission]

    def get(self, request, expediente_pk, pk):
        doc = get_object_or_404(
            DocumentoFuente.objects.filter(expediente_id=expediente_pk), pk=pk
        )
        return Response(
            DocumentoFuenteSerializer(doc, context={"request": request}).data
        )


class DocumentoFuenteReintentarOcrAPIView(APIView):
    permission_classes = [IsAuthenticated, DocumentoExpedientePermission]

    def post(self, request, expediente_pk, pk):
        doc = get_object_or_404(
            DocumentoFuente.objects.filter(expediente_id=expediente_pk), pk=pk
        )
        try:
            doc = reintentar_ocr(
                doc,
                actor=_actor_api(request),
            )
        except TransicionEstadoInvalida as e:
            return Response(
                {"detail": str(e), "codigo": e.codigo},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            DocumentoFuenteSerializer(doc, context={"request": request}).data
        )
