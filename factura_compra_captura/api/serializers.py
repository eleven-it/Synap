from rest_framework import serializers

from core.utils.django_user_fk import usuario_extendido_para_fk

from factura_compra_captura.models import (
    DocumentoFuente,
    EventoAuditoriaInterno,
    ExpedienteFacturaCompra,
    LineaExpedienteCompra,
)
from factura_compra_captura.services import ExpedienteService, TransicionEstadoInvalida
from factura_compra_captura.services.revision_engine_context import (
    build_revision_engine_context_for_ui,
)
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
    revision_engine_context = serializers.SerializerMethodField()

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
            "revision_engine_context",
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
            "revision_engine_context",
        ]

    def get_acciones_permitidas(self, obj: ExpedienteFacturaCompra):
        return listar_acciones_permitidas(obj.estado)

    def get_revision_engine_context(self, obj: ExpedienteFacturaCompra):
        docs = list(obj.documentos_fuente.all())
        if not docs:
            return None
        last = max(docs, key=lambda d: (d.creado_en, d.pk))
        raw = (last.resultado_ocr or {}).get("raw") or {}
        de = raw.get("document_engine_v1")
        af = (obj.metadata or {}).get("analyst_feedback")
        return build_revision_engine_context_for_ui(de, analyst_feedback_persisted=af)


class ExpedienteCreateSerializer(serializers.Serializer):
    empresa = serializers.IntegerField(required=False)
    origen_datos = serializers.ChoiceField(
        choices=ExpedienteFacturaCompra.OrigenDatos.choices,
        default=ExpedienteFacturaCompra.OrigenDatos.MANUAL,
        required=False,
    )
    metadata = serializers.JSONField(required=False, default=dict)

    def _resolver_empresa_id_desde_sesion(self, request) -> int | None:
        if request is None:
            return None
        from factura_compra_captura.session_empresa import empresa_synap_id_desde_sesion

        return empresa_synap_id_desde_sesion(request)

    def validate(self, attrs):
        request = self.context.get("request")
        empresa_id = attrs.get("empresa")
        if empresa_id is None:
            empresa_id = self._resolver_empresa_id_desde_sesion(request)
            if empresa_id is None:
                raise serializers.ValidationError(
                    {
                        "empresa": (
                            "No se pudo resolver la empresa activa desde sesión. "
                            "Inicie sesión nuevamente o envíe 'empresa'."
                        ),
                        "codigo": "empresa_no_resuelta",
                    }
                )
            attrs["empresa"] = empresa_id
        from core.models import Empresa

        if not Empresa.objects.filter(pk=empresa_id).exists():
            raise serializers.ValidationError(
                {
                    "empresa": f"Empresa {empresa_id} inexistente.",
                    "codigo": "empresa_invalida",
                }
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = usuario_extendido_para_fk(
            getattr(request, "user", None) if request else None
        )
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
    analyst_feedback_append = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
    )

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = usuario_extendido_para_fk(
            getattr(request, "user", None) if request else None
        )
        lineas = validated_data.pop("lineas", None)
        posting_header = validated_data.pop("posting_header", None)
        posting_context = validated_data.pop("posting_context", None)
        vales_codigos = validated_data.pop("vales_codigos", None)
        analyst_feedback_append = validated_data.pop("analyst_feedback_append", None)
        kw: dict = {
            "actor": user,
            "lineas": lineas,
            "posting_header": posting_header,
            "posting_context": posting_context,
            "vales_codigos": vales_codigos,
            "analyst_feedback_append": analyst_feedback_append,
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


class ResolverProveedorSerializer(serializers.Serializer):
    cuit = serializers.CharField(max_length=16)
    razon_social = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
