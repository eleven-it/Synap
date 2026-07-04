from django.contrib import admin

from ecom.models import EcomCatalogoRestriccionPV


@admin.register(EcomCatalogoRestriccionPV)
class EcomCatalogoRestriccionPVAdmin(admin.ModelAdmin):
    list_display = ("base_empresa", "id_punto_venta", "tipo", "valor_id", "activo", "updated_at")
    list_filter = ("base_empresa", "tipo", "activo")
    search_fields = ("base_empresa", "id_punto_venta", "valor_id", "nota")
    list_editable = ("activo",)
    ordering = ("base_empresa", "id_punto_venta", "tipo", "valor_id")
