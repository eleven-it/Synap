from django.contrib import admin

from factura_compra_captura.models import (
    DocumentoFuente,
    EventoAuditoriaInterno,
    ExpedienteFacturaCompra,
    LineaExpedienteCompra,
)


class LineaExpedienteInline(admin.TabularInline):
    model = LineaExpedienteCompra
    extra = 0


class DocumentoFuenteInline(admin.TabularInline):
    model = DocumentoFuente
    extra = 0
    readonly_fields = (
        "archivo",
        "mime_type",
        "tamano_bytes",
        "sha256_hex",
        "estado_procesamiento",
        "ocr_intento",
        "ocr_error_codigo",
    )


@admin.register(ExpedienteFacturaCompra)
class ExpedienteFacturaCompraAdmin(admin.ModelAdmin):
    list_display = ("id", "empresa", "estado", "origen_datos", "creado_en")
    list_filter = ("estado", "origen_datos")
    search_fields = ("id",)
    inlines = [DocumentoFuenteInline, LineaExpedienteInline]


@admin.register(EventoAuditoriaInterno)
class EventoAuditoriaInternoAdmin(admin.ModelAdmin):
    list_display = ("expediente", "tipo_evento", "creado_en")
    list_filter = ("tipo_evento",)
