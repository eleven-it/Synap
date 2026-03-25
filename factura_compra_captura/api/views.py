from django.shortcuts import get_object_or_404
from rest_framework import status
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
    ExpedienteTransicionPermission,
)
from factura_compra_captura.api.serializers import (
    DocumentoFuenteSerializer,
    EventoAuditoriaSerializer,
    ExpedienteCreateSerializer,
    ExpedienteFacturaCompraSerializer,
    ExpedientePatchSerializer,
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
            actor=request.user if request.user.is_authenticated else None,
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
                actor=request.user if request.user.is_authenticated else None,
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
                actor=request.user if request.user.is_authenticated else None,
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
                actor=request.user if request.user.is_authenticated else None,
            )
        except TransicionEstadoInvalida as e:
            return Response(
                {"detail": str(e), "codigo": e.codigo},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            DocumentoFuenteSerializer(doc, context={"request": request}).data
        )
