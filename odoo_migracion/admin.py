from django.contrib import admin

from odoo_migracion.models import MigrationEntityMapping, MigrationJob, OdooConnection


@admin.register(OdooConnection)
class OdooConnectionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "base_empresa", "base_url", "activo", "api_key_expires_at")
    search_fields = ("nombre", "base_empresa", "base_url")


@admin.register(MigrationJob)
class MigrationJobAdmin(admin.ModelAdmin):
    list_display = ("dominio", "conexion", "estado", "total_procesados", "created_at")
    list_filter = ("estado", "dominio")


@admin.register(MigrationEntityMapping)
class MigrationEntityMappingAdmin(admin.ModelAdmin):
    list_display = ("entity_type", "adminet_id", "external_id", "odoo_model", "sync_state")
    search_fields = ("adminet_id", "external_id")
