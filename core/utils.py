from core.models import UsuarioExtendido, Rol
from firebase_admin import firestore

def sincronizar_usuario_desde_firestore(decoded_token):
    """
    Sincroniza un usuario de Firebase con el modelo UsuarioExtendido.
    Si el usuario no existe, lo crea; si existe, lo actualiza parcialmente.
    """
    uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    nombre = decoded_token.get("name", "")

    firestore_db = firestore.client()
    doc_ref = firestore_db.collection("usuarios").document(uid)
    doc = doc_ref.get()

    tipo_usuario = ""
    idioma = "es"

    if doc.exists:
        data = doc.to_dict()
        tipo_usuario = data.get("tipo_usuario", "")
        idioma = data.get("idioma", "es")

    usuario, creado = UsuarioExtendido.objects.get_or_create(uid=uid, defaults={
        "email": email,
        "nombre": nombre,
        "idioma": idioma
    })

    # Actualizar info si ya existía
    if not creado:
        usuario.email = email or usuario.email
        usuario.nombre = nombre or usuario.nombre
        usuario.idioma = idioma or usuario.idioma

    # Intentar asignar rol automáticamente si coincide con tipo_usuario
    if tipo_usuario:
        try:
            rol = Rol.objects.get(nombre__iexact=tipo_usuario)
            usuario.rol = rol
        except Rol.DoesNotExist:
            pass

    usuario.save()
    return usuario
