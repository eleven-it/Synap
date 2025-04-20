def usuario_y_permisos(request):
    user = getattr(request, "user", None)

    if not user or not getattr(user, "is_authenticated", False):
        return {
            "user": None,
            "permisos_usuario": []
        }

    permisos_rol = user.rol.permisos.values_list("codigo", flat=True) if user.rol else []
    permisos_extra = user.permisos_extra.values_list("codigo", flat=True)
    permisos = set(permisos_rol) | set(permisos_extra)

    return {
        "user": user,
        "permisos_usuario": permisos
    }
