from django.contrib import admin

from contabilidad_audit.models import (
    AprobacionREI,
    CorridaAuditoria,
    HistorialPoliticaAuditoria,
    PlanCorreccion,
    PoliticaAuditoriaContable,
)

admin.site.register(PoliticaAuditoriaContable)
admin.site.register(HistorialPoliticaAuditoria)
admin.site.register(CorridaAuditoria)
admin.site.register(PlanCorreccion)
admin.site.register(AprobacionREI)
