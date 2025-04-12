from firebase_admin import firestore
from core.models import UsuarioExtendido, Rol

def sincronizar_usuario_desde_firestore(decoded_token):
    uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    nombre = decoded_token.get("nombre", "")

    # Leer tipo_usuario desde Firestore
    db = firestore.client()
    doc_ref = db.collection("usuarios").document(uid)
    doc = doc_ref.get()

    tipo_usuario = ""
    if doc.exists:
        tipo_usuario = doc.to_dict().get("tipo_usuario", "")

    # Buscar o crear rol
    rol, _ = Rol.objects.get_or_create(nombre=tipo_usuario or "sin_rol")

    # Crear usuario extendido
    usuario, _ = UsuarioExtendido.objects.get_or_create(uid=uid, defaults={
        "email": email,
        "nombre": nombre,
        "rol": rol,
    })

    # Actualizar rol si fue asignado después
    if usuario.rol != rol:
        usuario.rol = rol
        usuario.save()

    return usuario
