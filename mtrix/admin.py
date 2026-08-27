from django.contrib import admin

from mtrix.models import MtrixArtifact, MtrixConfig, MtrixJob


@admin.register(MtrixConfig)
class MtrixConfigAdmin(admin.ModelAdmin):
    list_display = ("base_empresa", "cnpj_fornecedor", "programador_activo", "updated_at")


@admin.register(MtrixJob)
class MtrixJobAdmin(admin.ModelAdmin):
    list_display = ("id", "base_empresa", "status", "origen", "created_at")
    readonly_fields = ("id", "created_at")


@admin.register(MtrixArtifact)
class MtrixArtifactAdmin(admin.ModelAdmin):
    list_display = ("filename", "tipo", "job", "sftp_status", "size_bytes")
