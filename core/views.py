from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from core.decorators import tiene_permiso
from core.models import UsuarioExtendido, Permiso, Rol
from django.contrib import messages


@csrf_exempt
@tiene_permiso("administrar_usuarios")
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


@tiene_permiso("administrar_usuarios")
def listar_permisos(request):
    permisos = Permiso.objects.all()
    return render(request, "core/permisos_list.html", {"permisos": permisos})


@tiene_permiso("administrar_usuarios")
def crear_permiso(request):
    if request.method == "POST":
        codigo = request.POST.get("codigo")
        nombre = request.POST.get("nombre")
        if codigo and nombre:
            Permiso.objects.create(codigo=codigo, nombre=nombre)
            messages.success(request, "Permiso creado exitosamente.")
            return redirect("core:listar_permisos")
    return render(request, "core/permisos_form.html")


@tiene_permiso("administrar_usuarios")
def eliminar_permiso(request, permiso_id):
    permiso = get_object_or_404(Permiso, id=permiso_id)
    permiso.delete()
    messages.success(request, "Permiso eliminado.")
    return redirect("core:listar_permisos")


def error_403_view(request, exception=None):
    return render(request, "core/403.html", status=403)