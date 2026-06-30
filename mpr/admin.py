from django.contrib import admin

from mpr.models import (
    MprArmadoLote,
    MprArmadoSurtidoLinea,
    MprArmadoSurtidoMovimiento,
    MprArticuloArmadoSurtido,
    MprImputacionArmado,
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


@admin.register(MprArmadoLote)
class MprArmadoLoteAdmin(admin.ModelAdmin):
    list_display = (
        "ejecutado_en",
        "base_empresa",
        "modo",
        "id_operario",
        "id_usuario",
        "cantidad_items",
        "cantidad_exitosos",
        "cantidad_fallidos",
    )
    list_filter = ("base_empresa", "modo", "ejecutado_en")
    readonly_fields = ("id", "ejecutado_en")
    search_fields = ("id", "base_empresa")


@admin.register(MprArmadoSurtidoMovimiento)
class MprArmadoSurtidoMovimientoAdmin(admin.ModelAdmin):
    list_display = (
        "creado_en",
        "base_empresa",
        "codigo_movimiento",
        "id_articulo_pack",
        "cantidad_packs",
        "modo",
        "estado_imputacion",
    )
    list_filter = ("base_empresa", "modo", "estado_imputacion")
    inlines = [MprArmadoSurtidoLineaInline]
    readonly_fields = ("creado_en",)


@admin.register(MprImputacionArmado)
class MprImputacionArmadoAdmin(admin.ModelAdmin):
    list_display = (
        "imputado_en",
        "base_empresa",
        "codigo_movimiento",
        "id_articulo_pack",
        "cantidad",
        "codigo_movimiento_pedido",
        "origen_regla",
        "id_usuario_supervisor",
    )
    list_filter = ("base_empresa", "origen_regla", "imputado_en")
    readonly_fields = ("imputado_en",)
    search_fields = ("codigo_movimiento", "codigo_movimiento_pedido")
