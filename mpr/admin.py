from django.contrib import admin

from mpr.models import (
    MprArmadoSurtidoLinea,
    MprArmadoSurtidoMovimiento,
    MprArticuloArmadoSurtido,
)


class MprArmadoSurtidoLineaInline(admin.TabularInline):
    model = MprArmadoSurtidoLinea
    extra = 0
    readonly_fields = (
        "id_articulo_componente",
        "codigo_articulo",
        "descripcion_articulo",
        "cantidad_por_pack",
        "cantidad_total",
    )


@admin.register(MprArticuloArmadoSurtido)
class MprArticuloArmadoSurtidoAdmin(admin.ModelAdmin):
    list_display = ("base_empresa", "id_articulo", "activo", "creado_en")
    list_filter = ("base_empresa", "activo")
    search_fields = ("base_empresa", "id_articulo")


@admin.register(MprArmadoSurtidoMovimiento)
class MprArmadoSurtidoMovimientoAdmin(admin.ModelAdmin):
    list_display = (
        "creado_en",
        "base_empresa",
        "codigo_movimiento",
        "id_articulo_pack",
        "cantidad_packs",
    )
    list_filter = ("base_empresa",)
    inlines = [MprArmadoSurtidoLineaInline]
    readonly_fields = ("creado_en",)
