from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.models import Rol, Permiso
from core.decorators import tiene_permiso
from django.utils.translation import gettext_lazy as _

@login_required
@tiene_permiso("usuarios.roles.ver")
def listar_roles_view(request):
    roles = Rol.objects.prefetch_related("permisos").all()
    return render(request, "core/roles_listar.html", {"roles": roles})

@login_required
@tiene_permiso("usuarios.roles.editar")
def crear_editar_rol_view(request, rol_id=None):
    if rol_id:
        rol = get_object_or_404(Rol, id=rol_id)
    else:
        rol = None

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        descripcion = request.POST.get("descripcion", "").strip()
        permisos_ids = request.POST.getlist("permisos")

        if not nombre:
            messages.error(request, _("Role name is required."))
        elif not permisos_ids:
            messages.error(request, _("You must select at least one permission."))
        else:
            if rol:
                rol.nombre = nombre
                rol.descripcion = descripcion
                rol.save()
                messages.success(request, _("Role updated successfully."))
            else:
                rol = Rol.objects.create(nombre=nombre, descripcion=descripcion)
                messages.success(request, _("Role created successfully."))

            permisos = Permiso.objects.filter(id__in=permisos_ids)
            rol.permisos.set(permisos)
            return redirect("core:listar_roles")

    permisos = Permiso.objects.all().order_by("codigo")
    permisos_por_modulo = {}
    for permiso in permisos:
        modulo = permiso.codigo.split(".")[0] if "." in permiso.codigo else "Otros"
        permisos_por_modulo.setdefault(modulo, []).append(permiso)

    return render(
        request,
        "core/roles_form.html",
        {
            "rol": rol,
            "permisos_por_modulo": permisos_por_modulo,
        },
    )

def eliminar_rol_view(request, rol_id):
    rol = get_object_or_404(Rol, id=rol_id)
    if rol.nombre.lower() == "administrador":
        messages.error(request, _("Cannot delete the Administrator role."))
    else:
        rol.delete()
        messages.success(request, _("Role '%(name)s' deleted successfully.") % {'name': rol.nombre})
    return redirect("core:listar_roles")
