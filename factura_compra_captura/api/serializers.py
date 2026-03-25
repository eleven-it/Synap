from rest_framework import serializers

from factura_compra_captura.models import (
    DocumentoFuente,
    EventoAuditoriaInterno,
    ExpedienteFacturaCompra,
    LineaExpedienteCompra,
)
from factura_compra_captura.services import ExpedienteService, TransicionEstadoInvalida
from factura_compra_captura.services.transiciones_estado import listar_acciones_permitidas


class DocumentoFuenteSerializer(serializers.ModelSerializer):
    url_archivo = serializers.SerializerMethodField()

    class Meta:
        model = DocumentoFuente
        fields = [
            "id",
            "nombre_original",
            "mime_type",
            "tamano_bytes",
            "sha256_hex",
            "tipo_archivo",
            "estado_procesamiento",
            "ocr_intento",
            "ocr_error_codigo",
            "ocr_error_detalle",
            "resultado_ocr",
            "creado_en",
            "modificado_en",
            "url_archivo",
        ]
        read_only_fields = (
            "id",
            "nombre_original",
            "mime_type",
            "tamano_bytes",
            "sha256_hex",
            "tipo_archivo",
            "estado_procesamiento",
            "ocr_intento",
            "ocr_error_codigo",
            "ocr_error_detalle",
            "resultado_ocr",
            "creado_en",
            "modificado_en",
            "url_archivo",
        )

    def get_url_archivo(self, obj: DocumentoFuente):
        request = self.context.get("request")
        if obj.archivo and request:
            return request.build_absolute_uri(obj.archivo.url)
        if obj.archivo:
            return obj.archivo.url
        return None


class LineaExpedienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaExpedienteCompra
        fields = [
            "id",
            "orden",
            "id_art_legacy",
            "codgasto_legacy",
            "cantidad",
            "precio_unitario",
            "codigo_movimiento_oc",
            "codigo_movimiento_remito",
            "metadata",
        ]
        read_only_fields = ["id"]


class ExpedienteFacturaCompraSerializer(serializers.ModelSerializer):
    lineas = LineaExpedienteSerializer(many=True, read_only=True)
    documentos_fuente = DocumentoFuenteSerializer(many=True, read_only=True)
    acciones_permitidas = serializers.SerializerMethodField()

    class Meta:
        model = ExpedienteFacturaCompra
        fields = [
            "id",
            "empresa",
            "sucursal_codigo_legacy",
            "estado",
            "origen_datos",
            "codigo_proveedor_legacy",
            "metadata",
            "posting_status",
            "posting_attempt",
            "legacy_codigo_movimiento",
            "legacy_nro_comprobante",
            "rechazo_motivo",
            "creado_por",
            "creado_en",
            "modificado_en",
            "lineas",
            "documentos_fuente",
            "acciones_permitidas",
        ]
        read_only_fields = [
            "id",
            "estado",
            "posting_status",
            "posting_attempt",
            "legacy_codigo_movimiento",
            "legacy_nro_comprobante",
            "rechazo_motivo",
            "creado_por",
            "creado_en",
            "modificado_en",
            "lineas",
            "documentos_fuente",
            "acciones_permitidas",
        ]

    def get_acciones_permitidas(self, obj: ExpedienteFacturaCompra):
        return listar_acciones_permitidas(obj.estado)


class ExpedienteCreateSerializer(serializers.Serializer):
    empresa = serializers.IntegerField()
    origen_datos = serializers.ChoiceField(
        choices=ExpedienteFacturaCompra.OrigenDatos.choices,
        default=ExpedienteFacturaCompra.OrigenDatos.MANUAL,
        required=False,
    )
    metadata = serializers.JSONField(required=False, default=dict)

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        return ExpedienteService.crear(
            empresa_id=validated_data["empresa"],
            origen_datos=validated_data.get("origen_datos")
            or ExpedienteFacturaCompra.OrigenDatos.MANUAL,
            creado_por=user,
            metadata=validated_data.get("metadata") or {},
        )


class ExpedientePatchSerializer(serializers.Serializer):
    codigo_proveedor_legacy = serializers.IntegerField(required=False, allow_null=True)
    origen_datos = serializers.ChoiceField(
        choices=ExpedienteFacturaCompra.OrigenDatos.choices,
        required=False,
    )
    sucursal_codigo_legacy = serializers.IntegerField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False)
    lineas = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
    )
    posting_header = serializers.JSONField(
        required=False,
        help_text="Objeto cabecera hacia metadata.posting_v1.header (LegacyPostingCommand v1).",
    )
    posting_context = serializers.JSONField(
        required=False,
    )
    vales_codigos = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
    )

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        lineas = validated_data.pop("lineas", None)
        posting_header = validated_data.pop("posting_header", None)
        posting_context = validated_data.pop("posting_context", None)
        vales_codigos = validated_data.pop("vales_codigos", None)
        kw: dict = {
            "actor": user,
            "lineas": lineas,
            "posting_header": posting_header,
            "posting_context": posting_context,
            "vales_codigos": vales_codigos,
        }
        for key in (
            "codigo_proveedor_legacy",
            "origen_datos",
            "sucursal_codigo_legacy",
            "metadata",
        ):
            if key in validated_data:
                kw[key] = validated_data[key]
        try:
            return ExpedienteService.actualizar(instance, **kw)
        except TransicionEstadoInvalida as e:
            raise serializers.ValidationError(
                {"detail": str(e), "codigo": e.codigo}
            ) from e


class EventoAuditoriaSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()

    class Meta:
        model = EventoAuditoriaInterno
        fields = [
            "id",
            "tipo_evento",
            "payload",
            "actor_email",
            "creado_en",
        ]
        read_only_fields = fields

    def get_actor_email(self, obj: EventoAuditoriaInterno):
        if obj.actor_id and obj.actor:
            return getattr(obj.actor, "email", None)
        return None


class TransicionSerializer(serializers.Serializer):
    accion = serializers.CharField(max_length=64)
    motivo = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Obligatorio si accion=rechazar",
    )
    payload = serializers.JSONField(required=False, default=dict)

    def save(self, expediente, *, actor, request=None):
        accion = self.validated_data["accion"]
        payload = dict(self.validated_data.get("payload") or {})
        if self.validated_data.get("motivo") is not None:
            payload["motivo"] = self.validated_data["motivo"]
        try:
            return ExpedienteService.aplicar_transicion(
                expediente,
                accion,
                actor=actor,
                payload=payload,
                request=request,
            )
        except TransicionEstadoInvalida as e:
            raise serializers.ValidationError(
                {"detail": str(e), "codigo": e.codigo}
            ) from e
