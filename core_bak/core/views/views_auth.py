from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

def redireccionar_segun_rol(request):
    user = getattr(request, "user", None)

    print("🧭 Redireccionador activado para:", request.path)

    if not user or not getattr(user, "is_authenticated", False):
        print("🔐 Usuario no autenticado, redirigiendo a login...")
        return redirect(f"/login/?next={request.path}")

    if user.roles.filter(nombre__iexact="administrador").exists():
        print("✅ Usuario con rol Administrador — acceso permitido")
        return None  # permite continuar
    else:
        print("⛔ Usuario autenticado, pero sin rol de administrador")
        raise PermissionDenied()
