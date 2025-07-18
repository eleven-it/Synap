from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.db.models import Q
from administraNET_integration.models import SyncLog
from core.models.models import Empresa, UsuarioExtendido
from core.constantes_permisos import CAN_MANAGE_INTEGRATIONS

@login_required
def validation_history(request):
    if not request.user.tiene_permiso(CAN_MANAGE_INTEGRATIONS):
        return render(request, 'administraNET_integration/validation_history.html', {'logs': [], 'empresas': [], 'filtros': {}})

    empresas = Empresa.objects.all().order_by('nombre')
    logs = SyncLog.objects.filter(sync_type='VALIDATION').order_by('-started_at')

    # Filtros
    empresa_id = request.GET.get('empresa')
    usuario_id = request.GET.get('usuario')
    estado = request.GET.get('estado')
    regla = request.GET.get('regla')
    fecha = request.GET.get('fecha')

    if empresa_id:
        # No existe details__empresa, así que filtrar por empresa si el modelo lo permite, si no, omitir
        pass
    if usuario_id:
        # No existe details__user, así que filtrar por initiated_by si aplica
        logs = logs.filter(initiated_by_id=int(usuario_id))
    if estado:
        logs = logs.filter(status=estado)
    if regla:
        # No existe details__rule, así que omitir o buscar en error_details si es relevante
        logs = logs.filter(error_details__icontains=regla)
    if fecha:
        logs = logs.filter(started_at__date=fecha)

    # Obtener usuarios únicos de los logs
    usuarios_ids = logs.values_list('initiated_by_id', flat=True).distinct()
    usuarios = UsuarioExtendido.objects.filter(id__in=usuarios_ids)

    # Obtener reglas únicas (de error_details si es relevante)
    reglas = []  # No se puede obtener reglas únicas directamente

    return render(request, 'administraNET_integration/validation_history.html', {
        'logs': logs[:100],
        'empresas': empresas,
        'usuarios': usuarios,
        'reglas': reglas,
        'filtros': {
            'empresa': empresa_id,
            'usuario': usuario_id,
            'estado': estado,
            'regla': regla,
            'fecha': fecha,
        }
    }) 