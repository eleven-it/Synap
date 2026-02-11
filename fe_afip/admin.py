from django.contrib import admin
from .models import AFIPConfig, CAEACode


@admin.register(CAEACode)
class CAEACodeAdmin(admin.ModelAdmin):
    list_display = ("base_empresa", "periodo", "orden", "vencimiento", "source", "requested_at")
    list_filter = ("base_empresa", "source")
    search_fields = ("base_empresa", "periodo", "codigo")
    readonly_fields = ("requested_at",)


@admin.register(AFIPConfig)
class AFIPConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "base_empresa", "modo_homologacion", "activo", "updated_at")
    list_filter = ("modo_homologacion", "activo")
    search_fields = ("name", "base_empresa")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "base_empresa", "activo")}),
        (
            "Credenciales AFIP",
            {
                "fields": ("cert_path", "key_path", "cuit"),
                "description": "Rutas a archivos en el servidor. No guardar claves en la base.",
            },
        ),
        (
            "Modo",
            {
                "fields": ("modo_homologacion", "cache_dir"),
                "description": "Homologación = pruebas AFIP. Producción = ambiente real.",
            },
        ),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )
