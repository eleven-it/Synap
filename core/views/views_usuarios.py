# core/views_usuarios.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_protect
from core.models import UsuarioExtendido, Permiso, Rol
from core.decorators import tiene_permiso
from core.constantes_permisos import PERMISOS_POR_MODULO
from core.utils import permisos_contextuales
from firebase_admin import firestore, auth
from django.views.generic.edit import CreateView
from django.contrib.auth.hashers import make_password
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from ..forms import UsuarioCreateForm
import logging

logger = logging.getLogger(__name__)


@tiene_permiso("administrar.usuarios")
def usuarios_admin_view(request):
    context = permisos_contextuales(request, "usuarios.ver", roles_permitidos=["Administrador"], debug=True)
    if not context.get("puede_usuarios_ver") and not context.get("rol_permitido"):
        return render(request, "core/403.html", context, status=403)

    q = request.GET.get("q", "")
    rol_filter = request.GET.get("rol_filter", "")
    usuarios = UsuarioExtendido.objects.all().prefetch_related("roles", "permisos_extra")

    if q:
        usuarios = usuarios.filter(nombre__icontains=q) | usuarios.filter(email__icontains=q)
    if rol_filter:
        usuarios = usuarios.filter(roles__id=rol_filter)

    usuarios = usuarios.order_by("email")
    paginator = Paginator(usuarios, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    roles = Rol.objects.all().order_by("nombre")
    todos_permisos = Permiso.objects.all().order_by("nombre")

    modulos_permisos = {}
    usados = set()
    for modulo, lista in PERMISOS_POR_MODULO.items():
        codigos = [c for c, _ in lista]
        modulos_permisos[modulo] = todos_permisos.filter(codigo__in=codigos)
        usados.update(codigos)

    restantes = todos_permisos.exclude(codigo__in=usados)
    if restantes.exists():
        modulos_permisos["Otros"] = restantes

    if request.method == "POST":
        for usuario in usuarios:
            # Roles
            roles_ids = request.POST.getlist(f"roles_{usuario.uid}")
            usuario.roles.set(roles_ids)

            # Permisos extra
            permisos_ids = request.POST.getlist(f"perm_{usuario.uid}")
            usuario.permisos_extra.set(permisos_ids)

            usuario.save()

            # 🔁 Sync roles to Firebase
            try:
                firestore.client().collection("usuarios").document(usuario.uid).set({
                    "roles": list(usuario.roles.values_list("nombre", flat=True))
                }, merge=True)
            except Exception as e:
                messages.warning(request, f"⚠️ Error al sincronizar {usuario.email} con Firebase: {e}")

        messages.success(request, "✅ Cambios guardados exitosamente.")
        return redirect("core:usuarios")

    context.update({
        "usuarios": page_obj,
        "roles": roles,
        "modulos_permisos": modulos_permisos,
        "q": q,
        "rol_filter": rol_filter,
    })
    return render(request, "core/usuarios_admin.html", context)


@tiene_permiso("administrar.usuarios")
@csrf_protect
def crear_usuario_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        nombre = request.POST.get("nombre", "").strip()
        idioma = request.POST.get("idioma", "es")
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirmar_password", "")
        roles_ids = request.POST.getlist("roles")

        if not email or not password or not confirm:
            messages.error(request, "Completa todos los campos obligatorios.")
            return redirect("core:usuarios")

        if password != confirm:
            messages.error(request, "Las contraseñas no coinciden.")
            return redirect("core:usuarios")

        try:
            firebase_user = auth.create_user(email=email, password=password, display_name=nombre)
            uid = firebase_user.uid
        except Exception as e:
            messages.error(request, f"Error al crear usuario en Firebase: {e}")
            return redirect("core:usuarios")

        usuario = UsuarioExtendido.objects.create(
            uid=uid,
            email=email,
            nombre=nombre,
            idioma=idioma
        )
        usuario.roles.set(roles_ids)
        usuario.save()

        try:
            firestore.client().collection("usuarios").document(uid).set({
                "email": email,
                "nombre": nombre,
                "idioma": idioma,
                "roles": list(usuario.roles.values_list("nombre", flat=True))
            })
        except Exception as e:
            messages.warning(request, f"Usuario creado localmente, pero falló la sincronización: {e}")

        messages.success(request, "✅ Usuario creado correctamente.")
        return redirect("core:usuarios")

    return redirect("core:usuarios")


class UsuarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = UsuarioExtendido
    form_class = UsuarioCreateForm
    template_name = 'core/usuarios_crear_form.html'
    permission_required = 'core.add_usuarioextendido'

    def form_valid(self, form):
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        nombre = form.cleaned_data['nombre']

        logger.info(f"Intentando crear usuario en Firebase con email: {email}, nombre: {nombre}")

        try:
            # Paso 1: Crear usuario solo con email y contraseña
            firebase_user = auth.create_user(
                email=email,
                password=password,
            )
            uid = firebase_user.uid

            # Paso 2: Actualizar el nombre (displayName)
            auth.update_user(uid, display_name=nombre)

        except auth.EmailAlreadyExistsError:
            form.add_error('email', 'Este correo electrónico ya está registrado en Firebase.')
            return self.form_invalid(form)
        except Exception as e:
            error_message = f"Error inesperado al crear usuario en Firebase: {e}"
            if hasattr(e, 'http_response'):
                try:
                    error_data = e.http_response.json()
                    error_message += f" | Detalles: {error_data.get('error', {}).get('message', 'Sin detalles')}"
                except:
                    pass
            logger.error(error_message)
            messages.error(self.request, error_message)
            return self.form_invalid(form)

        self.object = form.save(commit=False)
        self.object.uid = uid
        self.object.nombre = nombre
        self.object.username = email
        self.object.password = '' 
        self.object.save()
        
        messages.success(self.request, f"Usuario {email} creado exitosamente.")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('core:usuarios')
