from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from core.models import UsuarioExtendido, Rol, Permiso
from core.decorators import permiso_requerido

@csrf_exempt
@permiso_requerido("admin_usuarios")
def usuarios_admin_view(request):
    if request.method == "POST":
        for usuario in UsuarioExtendido.objects.all():
            # Asignar nuevo rol
            rol_id = request.POST.get(f"rol_{usuario.uid}")
            if rol_id:
                try:
                    usuario.rol = Rol.objects.get(id=rol_id)
                except Rol.DoesNotExist:
                    usuario.rol = None
            else:
                usuario.rol = None

            # Permisos extra
            permisos_ids = request.POST.getlist(f"perm_{usuario.uid}")
            usuario.permisos_extra.set(permisos_ids)
            usuario.save()
        return redirect("core:usuarios")

    context = {
        "usuarios": UsuarioExtendido.objects.select_related("rol").prefetch_related("permisos_extra"),
        "roles": Rol.objects.all(),
        "permisos": Permiso.objects.all()
    }
    return render(request, "core/usuarios_admin.html", context)

def error_403_view(request, exception=None):
    return render(request, "core/403.html", status=403)
