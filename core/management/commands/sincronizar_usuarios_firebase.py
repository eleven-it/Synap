from django.core.management.base import BaseCommand
from core.models import UsuarioExtendido, Rol
from firebase_admin import firestore


class Command(BaseCommand):
    help = "Sincroniza usuarios desde Firebase a la base local, incluyendo múltiples roles."

    def handle(self, *args, **kwargs):
        db = firestore.client()
        usuarios_ref = db.collection("usuarios")
        docs = usuarios_ref.stream()

        uids_en_firebase = set()
        print("\n📥 Sincronizando usuarios desde Firebase...\n")

        for doc in docs:
            data = doc.to_dict()
            uid = doc.id
            email = data.get("email")
            nombre = data.get("nombre", "")
            idioma = data.get("idioma", "es")
            roles_lista = data.get("roles", [])

            if not email:
                print(f"⚠️ Usuario {uid} omitido (sin email)")
                continue

            usuario, creado = UsuarioExtendido.objects.get_or_create(uid=uid, defaults={
                "email": email,
                "nombre": nombre,
                "idioma": idioma,
                "username": email.split("@")[0],  # Necesario si es modelo de usuario
            })

            usuario.email = email
            usuario.nombre = nombre or usuario.nombre
            usuario.idioma = idioma or "es"

            # 🔄 Limpiar y asignar roles
            usuario.roles.clear()
            is_admin = False
            for nombre_rol in roles_lista:
                try:
                    rol = Rol.objects.get(nombre__iexact=nombre_rol)
                    usuario.roles.add(rol)
                    if rol.nombre.lower() == "administrador":
                        is_admin = True
                except Rol.DoesNotExist:
                    print(f"⚠️ Rol '{nombre_rol}' no existe para {email}")

            # 🔐 Flags administrativos
            usuario.is_superuser = is_admin
            usuario.is_staff = is_admin

            usuario.save()
            uids_en_firebase.add(uid)

            estado = "🆕 Creado" if creado else "✅ Actualizado"
            print(f"{estado}: {email} ({uid})")

        # 🧹 Verificar huérfanos
        print("\n🔍 Verificando usuarios huérfanos en la base local...\n")
        uids_local = set(UsuarioExtendido.objects.values_list("uid", flat=True))
        uids_faltantes = uids_local - uids_en_firebase

        for uid in uids_faltantes:
            try:
                usuario = UsuarioExtendido.objects.get(uid=uid)
            except UsuarioExtendido.DoesNotExist:
                continue

            print(f"❓ Usuario local sin coincidencia en Firebase: {usuario.email} ({uid})")
            print("   ¿Qué deseas hacer?")
            print("   [1] Eliminar de la base de datos")
            print("   [2] Marcar como inactivo (requiere campo `activo` en modelo)")
            print("   [3] Saltar")
            opcion = input("   Ingresá tu elección [1/2/3]: ").strip()

            if opcion == "1":
                usuario.delete()
                print(f"   🗑️ Eliminado: {usuario.email}")
            elif opcion == "2":
                if hasattr(usuario, "activo"):
                    usuario.activo = False
                    usuario.save()
                    print(f"   📴 Marcado como inactivo: {usuario.email}")
                else:
                    print("   ⚠️ El modelo no tiene campo 'activo'. Acción omitida.")
            else:
                print("   ↪️ Saltado.")

        print("\n✅ Sincronización completada.")
