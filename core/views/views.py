from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from core.decorators import tiene_permiso
from core.models import UsuarioExtendido, Permiso, Rol
from django.contrib import messages
from core.utils import permisos_contextuales
from django.core.paginator import Paginator
from core.constantes_permisos import PERMISOS_POR_MODULO
from django_project.firebase_config import get_firebase_app
import logging
from django.utils.translation import gettext_lazy as _
import firebase_admin
from firebase_admin import firestore, auth
from core.models.models import Empresa
from django import forms
from core.models import Branch
from core.utils.utils import require_empresa_activa
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

@csrf_protect
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

    # Agrupar permisos por módulo según PERMISOS_POR_MODULO
    modulos_permisos = {}
    codigos_usados = set()

    for modulo, lista_codigos in PERMISOS_POR_MODULO.items():
        codigos = [c for c, _ in lista_codigos]
        permisos_modulo = todos_permisos.filter(codigo__in=codigos)
        modulos_permisos[modulo] = permisos_modulo
        codigos_usados.update(codigos)

    permisos_restantes = todos_permisos.exclude(codigo__in=codigos_usados)
    if permisos_restantes.exists():
        modulos_permisos["Otros"] = permisos_restantes

    # 🔄 Actualización (roles + permisos + Firestore)
    if request.method == "POST":
        db = firestore.client()

        for usuario in usuarios:
            # ✅ Asignar múltiples roles
            roles_ids = request.POST.getlist(f"roles_{usuario.uid}")
            roles_objs = Rol.objects.filter(id__in=roles_ids)
            usuario.roles.set(roles_objs)
            nombres_roles = [r.nombre for r in roles_objs]

            # ✅ Asignar permisos adicionales
            permisos_ids = request.POST.getlist(f"perm_{usuario.uid}")
            usuario.permisos_extra.set(permisos_ids)

            usuario.save()

            # 🔁 Sincronizar Firestore
            try:
                doc_ref = db.collection("usuarios").document(usuario.uid)
                doc = doc_ref.get()
                if doc.exists:
                    doc_ref.update({"roles": nombres_roles})
                else:
                    doc_ref.set({
                        "email": usuario.email,
                        "nombre": usuario.nombre,
                        "idioma": usuario.idioma or "es",
                        "roles": nombres_roles
                    })
                logger.info(f"📡 Firestore actualizado para {usuario.email}")
            except Exception as e:
                logger.warning(f"⚠️ Error al sincronizar con Firestore para {usuario.email}: {e}")

        messages.success(request, _("✅ Changes saved successfully."))
        return redirect("core:usuarios")

    # 🔽 Render final
    context.update({
        "usuarios": page_obj,
        "roles": roles,
        "modulos_permisos": modulos_permisos,
        "q": q,
        "rol_filter": rol_filter,
    })
    return render(request, "core/usuarios_admin.html", context)


@tiene_permiso("usuarios.ver")
def listar_permisos(request):
    permisos = Permiso.objects.all()
    return render(request, "core/permisos_list.html", {"permisos": permisos})

@csrf_protect
@tiene_permiso("administrar.usuarios")
def crear_usuario_view(request):
    if not request.user.tiene_permiso("administrar.usuarios"):
        messages.error(request, _("You do not have permission to create users."))
        return redirect("core:usuarios")

    context = permisos_contextuales(request, "usuarios.crear", roles_permitidos=["Administrador"])

    if not context.get("puede_usuarios_crear") and not context.get("rol_permitido"):
        return render(request, "core/403.html", context, status=403)

    roles = Rol.objects.all()

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        nombre = request.POST.get("nombre", "").strip()
        idioma = request.POST.get("idioma", "es")
        password = request.POST.get("password", "")
        confirmar = request.POST.get("confirmar", "")
        roles_ids = request.POST.getlist("roles")

        if not email or not password or not confirmar or not nombre:
            messages.error(request, _("All fields are required."))
            return render(request, "core/usuarios_form.html", {"roles": roles})

        if password != confirmar:
            messages.error(request, _("Passwords do not match."))
            return render(request, "core/usuarios_form.html", {"roles": roles})

        # ⚠️ Verificar si el usuario ya existe localmente
        if UsuarioExtendido.objects.filter(email=email).exists():
            messages.error(request, _("A user with that email already exists in the database."))
            return render(request, "core/usuarios_form.html", {"roles": roles})

        # 1. Crear en Firebase Auth
        try:
            firebase_user = auth.create_user(email=email, password=password, display_name=nombre)
            uid = firebase_user.uid
        except auth.EmailAlreadyExistsError:
            messages.error(request, _("That email is already registered in Firebase."))
            return render(request, "core/usuarios_form.html", {"roles": roles})
        except Exception as e:
            messages.error(request, _("Error creating user in Firebase: %(error)s") % {'error': e})
            return render(request, "core/usuarios_form.html", {"roles": roles})

        # 2. Crear en DB local
        usuario = UsuarioExtendido.objects.create(
            uid=uid,
            email=email,
            nombre=nombre,
            idioma=idioma,
        )
        if roles_ids:
            usuario.roles.set(roles_ids)

        # 3. Crear en Firestore
        try:
            firestore.client().collection("usuarios").document(uid).set({
                "email": email,
                "nombre": nombre,
                "idioma": idioma,
                "roles": [Rol.objects.get(id=r).nombre for r in roles_ids]
            })
        except Exception as e:
            messages.warning(request, _("User created locally, but not synced with Firebase: %(error)s") % {'error': e})

        messages.success(request, _("✅ User %(email)s created successfully.") % {'email': email})
        return redirect("core:usuarios")

    return render(request, "core/usuarios_form.html", {
        "roles": roles
    })


@tiene_permiso("permisos.eliminar")
def eliminar_permiso(request, permiso_id):
    permiso = get_object_or_404(Permiso, id=permiso_id)
    permiso.delete()
    messages.success(request, _("Permission deleted."))
    return redirect("core:listar_permisos")


def error_403_view(request, exception=None):
    return render(request, "core/403.html", status=403)


def dashboard_view(request):
    usuario = request.user
    if not isinstance(usuario, UsuarioExtendido):
        return redirect("login:login")

    print("🧠 Usuario:", usuario.email)
    print("🧠 UID:", usuario.uid)
    print("🧠 ROLES:", [r.nombre for r in usuario.roles.all()])

    context = permisos_contextuales(request, "*", debug=True)
    return render(request, "core/dashboard.html", context)


@tiene_permiso("usuarios.perfil")
def perfil_view(request):
    user_data = request.session.get("user")
    if not user_data:
        return redirect("login:login")

    try:
        usuario = UsuarioExtendido.objects.get(uid=user_data["uid"])
    except UsuarioExtendido.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect("login:login")

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        idioma = request.POST.get("idioma", "es")
        nueva = request.POST.get("nueva_password", "")
        confirmar = request.POST.get("confirmar_password", "")

        if nombre:
            usuario.nombre = nombre
        if idioma in ["es", "en", "pt"]:
            usuario.idioma = idioma

        if nueva:
            if nueva == confirmar:
                try:
                    auth.update_user(uid=usuario.uid, password=nueva)
                    messages.success(request, "Contraseña actualizada correctamente.")
                except Exception as e:
                    messages.error(request, f"Error al cambiar la contraseña: {e}")
            else:
                messages.error(request, "Las contraseñas no coinciden.")

        usuario.save()
        request.session["user"]["nombre"] = usuario.nombre
        request.session["user"]["idioma"] = usuario.idioma
        messages.success(request, "Cambios guardados correctamente.")
        return redirect("core:perfil")

    return render(request, "core/perfil.html", {"user": user_data})


@tiene_permiso("usuarios.historial")
def historial_view(request):
    return render(request, "core/historial.html", {"user": request.session["user"]})

# Antes de usar auth o firestore, asegúrate de inicializar Firebase:
get_firebase_app()

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = [
            'nombre', 'identificador_fiscal', 'email', 'telefono', 'direccion',
            'pais', 'ciudad', 'logo', 'activa'
        ]
        widgets = {
            'activa': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

# Vista para crear una nueva empresa
def empresa_crear_view(request):
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES)
        if form.is_valid():
            empresa = form.save()
            return redirect('core:empresa_listar')
    else:
        form = EmpresaForm()
    return render(request, 'core/system_config/empresa_form.html', {'form': form, 'empresa': None})

@require_empresa_activa(lambda request, empresa_id, *a, **k: get_object_or_404(Empresa, id=empresa_id))
def empresa_editar_view(request, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            return redirect('core:empresa_listar')
    else:
        form = EmpresaForm(instance=empresa)
    return render(request, 'core/system_config/empresa_form.html', {'form': form, 'empresa': empresa})

def empresa_listar_view(request):
    empresas = Empresa.objects.all().order_by('nombre')
    return render(request, 'core/system_config/empresa_list.html', {'empresas': empresas})

def empresa_eliminar_view(request, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    # Aquí se agregarán chequeos de dependencias en el futuro
    tiene_dependencias = False  # Por ahora, siempre False
    if request.method == 'POST':
        if tiene_dependencias or empresa.activa:
            empresa.activa = False
            empresa.save()
            messages.success(request, _('Company deactivated successfully.'))
        else:
            empresa.delete()
            messages.success(request, _('Company deleted successfully.'))
        return redirect('core:empresa_listar')
    return render(request, 'core/system_config/empresa_confirm_delete.html', {'empresa': empresa, 'tiene_dependencias': tiene_dependencias})

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = [
            'empresa', 'name', 'code', 'address', 'city', 'state', 'country', 'phone', 'email', 'active'
        ]
        widgets = {
            'active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

@require_empresa_activa(lambda request, empresa_id, *a, **k: get_object_or_404(Empresa, id=empresa_id))
def branch_list_view(request, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    branches = empresa.branches.all().order_by('name')
    return render(request, 'core/system_config/branch_list.html', {'empresa': empresa, 'branches': branches})

@require_empresa_activa(lambda request, empresa_id, *a, **k: get_object_or_404(Empresa, id=empresa_id))
def branch_create_view(request, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save(commit=False)
            branch.empresa = empresa
            branch.save()
            return redirect('core:branch_list', empresa_id=empresa.id)
    else:
        form = BranchForm(initial={'empresa': empresa})
    return render(request, 'core/system_config/branch_form.html', {'form': form, 'empresa': empresa, 'branch': None})

@require_empresa_activa(lambda request, empresa_id, branch_id, *a, **k: get_object_or_404(Empresa, id=empresa_id))
def branch_edit_view(request, empresa_id, branch_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    branch = get_object_or_404(Branch, id=branch_id, empresa=empresa)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            return redirect('core:branch_list', empresa_id=empresa.id)
    else:
        form = BranchForm(instance=branch)
    return render(request, 'core/system_config/branch_form.html', {'form': form, 'empresa': empresa, 'branch': branch})

@require_empresa_activa(lambda request, empresa_id, branch_id, *a, **k: get_object_or_404(Empresa, id=empresa_id))
def branch_delete_view(request, empresa_id, branch_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    branch = get_object_or_404(Branch, id=branch_id, empresa=empresa)
    if request.method == 'POST':
        if branch.active:
            branch.active = False
            branch.save()
            messages.success(request, _('Branch deactivated successfully.'))
        else:
            branch.delete()
            messages.success(request, _('Branch deleted successfully.'))
        return redirect('core:branch_list', empresa_id=empresa.id)
    return render(request, 'core/system_config/branch_confirm_delete.html', {'empresa': empresa, 'branch': branch})

@require_POST
def cambiar_empresa_branch(request):
    user = request.user
    empresa_id = request.POST.get('empresa_id')
    branch_id = request.POST.get('branch_id')
    next_url = request.META.get('HTTP_REFERER', '/')

    # Validar empresa
    try:
        empresa = Empresa.objects.get(id=empresa_id, activa=True)
    except Empresa.DoesNotExist:
        messages.error(request, _(u"Empresa inválida."))
        return redirect(next_url)

    # Validar sucursal
    try:
        branch = Branch.objects.get(id=branch_id, empresa=empresa, active=True)
    except Branch.DoesNotExist:
        messages.error(request, _(u"Sucursal inválida."))
        return redirect(next_url)

    # Validar permisos (solo admin puede cambiar a cualquier empresa/sucursal)
    if not user.is_admin():
        if empresa != getattr(user, 'empresa_activa', None) or branch != getattr(user, 'branch_activa', None):
            messages.error(request, _(u"No tienes permiso para cambiar de empresa o sucursal."))
            return redirect(next_url)

    # Actualizar sesión
    request.session['empresa_activa_id'] = empresa.id
    request.session['branch_activa_id'] = branch.id
    # Si el modelo de usuario tiene campos, actualizarlos también
    if hasattr(user, 'empresa_activa'):
        user.empresa_activa = empresa
        user.save(update_fields=['empresa_activa'])
    if hasattr(user, 'branch_activa'):
        user.branch_activa = branch
        user.save(update_fields=['branch_activa'])
    messages.success(request, _(u"Empresa y sucursal cambiadas correctamente."))
    return redirect(next_url)