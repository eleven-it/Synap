def usuario_y_permisos(request):
    user = request.session.get("user", {})
    return {
        "user": user,
        "permisos_usuario": user.get("permisos", [])
    }
