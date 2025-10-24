# import uuid
# from django.core.management.base import BaseCommand
# from core.models import UsuarioExtendido, Rol
# from firebase_admin import firestore
# from django.db import connection
# from pathlib import Path
# import getpass
# from firebase_admin import auth

# class Command(BaseCommand):
#     help = "Administra usuarios: asignar roles, crear o eliminar, sincronizando con Firebase"

#     def handle(self, *args, **kwargs):
#         while True:
#             print("\n📋 Opciones:")
#             print("1. Listar y editar usuarios")
#             print("2. Crear nuevo usuario")
#             print("3. Eliminar usuario")
#             print("0. Salir")

#             opcion = input("Selecciona una opción: ").strip()

#             if opcion == "1":
#                 self.editar_usuarios()
#             elif opcion == "2":
#                 self.crear_usuario()
#             elif opcion == "3":
#                 self.eliminar_usuario()
#             elif opcion == "0":
#                 print("👋 Finalizado.")
#                 break
#             else:
#                 print("❌ Opción inválida.")

#     def editar_usuarios(self):
#         usuarios = UsuarioExtendido.objects.all().order_by("email")
#         print("\nUsuarios disponibles:")
#         for i, u in enumerate(usuarios, 1):
#             estado = "Inactivo" if hasattr(u, "activo") and not u.activo else "Activo"
#             print(f"{i}. {u.email} — {', '.join([r.nombre for r in u.roles.all()]) or 'Sin rol'} — {estado}")
#         print("0. Volver")

#         try:
#             index = int(input("\nSelecciona el número de usuario a editar: "))
#             if index == 0:
#                 return
#             usuario = usuarios[index - 1]
#         except (ValueError, IndexError):
#             print("❌ Índice inválido.")
#             return

#         print("\nOpciones de rol (podés seleccionar múltiples, separados por coma):")
#         roles = Rol.objects.all()
#         for i, r in enumerate(roles, 1):
#             print(f"{i}. {r.nombre}")

#         entrada = input("\nSelecciona los números de roles (ej. 1,3): ").strip()
#         if not entrada:
#             print("↪️ Sin cambios de rol.")
#             return

#         try:
#             indices = [int(x.strip()) for x in entrada.split(",")]
#             roles_seleccionados = [roles[i - 1] for i in indices if 1 <= i <= len(roles)]
#             usuario.roles.set(roles_seleccionados)
#         except Exception as e:
#             print(f"❌ Error al asignar roles: {e}")
#             return

#         usuario.save()

#         # Sincronizar con Firebase
#         try:
#             db = firestore.client()
#             doc_ref = db.collection("usuarios").document(usuario.uid)
#             doc_ref.set({
#                 "tipo_usuario": [r.nombre for r in roles_seleccionados] or firestore.DELETE_FIELD
#             }, merge=True)
#             print("✅ Sincronizado con Firebase")
#         except Exception as e:
#             print(f"⚠️ Error al sincronizar con Firebase: {e}")

#         print(f"➡️ Usuario actualizado: {usuario.email} → {', '.join([r.nombre for r in usuario.roles.all()]) or 'Sin rol'}")

#     def crear_usuario(self):
#         print("\n📨 Crear nuevo usuario:")
#         email = input("Email: ").strip()
#         nombre = input("Nombre completo: ").strip()
#         idioma = input("Idioma [es/en/pt] (default es): ").strip() or "es"

#         password = getpass.getpass("Contraseña: ").strip()
#         confirm = getpass.getpass("Confirmar contraseña: ").strip()

#         if not password or password != confirm:
#             print("❌ Las contraseñas no coinciden o están vacías.")
#             return

#         try:
#             firebase_user = auth.create_user(email=email, password=password, display_name=nombre)
#             uid = firebase_user.uid
#             print(f"✅ Usuario creado en Firebase Auth. UID: {uid}")
#         except auth.EmailAlreadyExistsError:
#             print("❌ Ese email ya está registrado en Firebase Auth.")
#             return
#         except Exception as e:
#             print(f"❌ Error al crear usuario en Firebase Auth: {e}")
#             return

#         roles = Rol.objects.all()
#         print("\nRoles disponibles:")
#         for i, r in enumerate(roles, 1):
#             print(f"{i}. {r.nombre}")

#         entrada = input("Selecciona los números de roles (ej. 1,2): ").strip()
#         try:
#             indices = [int(x.strip()) for x in entrada.split(",")]
#             roles_seleccionados = [roles[i - 1] for i in indices if 1 <= i <= len(roles)]
#         except Exception:
#             print("❌ Error en selección de roles.")
#             return

#         usuario = UsuarioExtendido.objects.create(
#             uid=uid,
#             email=email,
#             nombre=nombre,
#             idioma=idioma,
#         )
#         usuario.roles.set(roles_seleccionados)

#         try:
#             db = firestore.client()
#             doc_ref = db.collection("usuarios").document(uid)
#             doc_ref.set({
#                 "email": email,
#                 "nombre": nombre,
#                 "idioma": idioma,
#                 "tipo_usuario": [r.nombre for r in roles_seleccionados]
#             })
#             print("✅ Usuario sincronizado con Firestore.")
#         except Exception as e:
#             print(f"⚠️ Usuario creado localmente, pero falló la sincronización con Firestore: {e}")

#         path = Path("ultimo_usuario_creado.txt")
#         path.write_text(f"{usuario.email} → {uid}\n", encoding="utf-8")
#         print(f"📝 UID guardado en {path.resolve()}")

#     def eliminar_usuario(self):
#         usuarios = UsuarioExtendido.objects.all().order_by("email")
#         print("\nUsuarios disponibles:")
#         for i, u in enumerate(usuarios, 1):
#             print(f"{i}. {u.email} — {', '.join([r.nombre for r in u.roles.all()]) or 'Sin rol'}")
#         print("0. Volver")

#         try:
#             index = int(input("\nSelecciona el número de usuario a eliminar: "))
#             if index == 0:
#                 return
#             usuario = usuarios[index - 1]
#         except (ValueError, IndexError):
#             print("❌ Índice inválido.")
#             return

#         tiene_datos_asociados = self._tiene_relaciones(usuario)

#         if tiene_datos_asociados:
#             print("⚠️ El usuario tiene movimientos asociados.")
#             if hasattr(usuario, "activo"):
#                 usuario.activo = False
#                 usuario.save()
#                 print("🛑 Usuario marcado como inactivo.")
#             else:
#                 print("❌ El modelo no tiene campo 'activo'. No se puede desactivar.")
#             return

#         confirm = input(f"¿Confirmás eliminar a {usuario.email}? [s/N]: ").strip().lower()
#         if confirm == "s":
#             try:
#                 usuario.delete()
#                 db = firestore.client()
#                 db.collection("usuarios").document(usuario.uid).delete()
#                 print("🗑️ Usuario eliminado en DB y Firebase.")
#             except Exception as e:
#                 print(f"⚠️ Error al eliminar en Firebase: {e}")
#         else:
#             print("↪️ Cancelado.")

#     def _tiene_relaciones(self, usuario):
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 SELECT COUNT(*) FROM information_schema.constraint_column_usage
#                 WHERE table_name != 'core_usuarioextendido'
#                 AND column_name = 'uid'
#             """)
#             row = cursor.fetchone()
#             return row[0] > 0

import uuid
from django.core.management.base import BaseCommand
from core.models import UsuarioExtendido, Rol
from firebase_admin import firestore, auth
from django.db import connection, transaction
from pathlib import Path
import getpass

class Command(BaseCommand):
    help = "Administra usuarios: asignar roles, crear o eliminar, sincronizando con Firebase"

    def handle(self, *args, **kwargs):
        while True:
            print("\n📋 Opciones:")
            print("1. Listar y editar usuarios")
            print("2. Crear nuevo usuario")
            print("3. Eliminar usuario")
            print("0. Salir")

            opcion = input("Selecciona una opción: ").strip()

            if opcion == "1":
                self.editar_usuarios()
            elif opcion == "2":
                self.crear_usuario()
            elif opcion == "3":
                self.eliminar_usuario()
            elif opcion == "0":
                print("👋 Finalizado.")
                break
            else:
                print("❌ Opción inválida.")

    def editar_usuarios(self):
        usuarios = UsuarioExtendido.objects.all().order_by("email")
        print("\nUsuarios disponibles:")
        for i, u in enumerate(usuarios, 1):
            estado = "Inactivo" if hasattr(u, "activo") and not u.activo else "Activo"
            print(f"{i}. {u.email} — {', '.join([r.nombre for r in u.roles.all()]) or 'Sin rol'} — {estado}")
        print("0. Volver")

        try:
            index = int(input("\nSelecciona el número de usuario a editar: "))
            if index == 0:
                return
            usuario = usuarios[index - 1]
        except (ValueError, IndexError):
            print("❌ Índice inválido.")
            return

        print("\nOpciones de rol (podés seleccionar múltiples, separados por coma):")
        roles = Rol.objects.all()
        for i, r in enumerate(roles, 1):
            print(f"{i}. {r.nombre}")

        entrada = input("\nSelecciona los números de roles (ej. 1,3): ").strip()
        if not entrada:
            print("↪️ Sin cambios de rol.")
            return

        try:
            indices = [int(x.strip()) for x in entrada.split(",")]
            roles_seleccionados = [roles[i - 1] for i in indices if 1 <= i <= len(roles)]
            usuario.roles.set(roles_seleccionados)
            usuario.save()

            # Sincronizar con Firebase
            firestore.client().collection("usuarios").document(usuario.uid).set({
                "roles": [r.nombre for r in roles_seleccionados] or firestore.DELETE_FIELD
            }, merge=True)

            print("✅ Usuario actualizado y sincronizado con Firebase.")
        except Exception as e:
            print(f"❌ Error al asignar roles o sincronizar: {e}")

    def crear_usuario(self):
        print("\n📨 Crear nuevo usuario:")
        email = input("📧 Email: ").strip().lower()
        nombre = input("👤 Nombre completo: ").strip()
        idioma = input("🌐 Idioma [es/en/pt] (default es): ").strip() or "es"

        if UsuarioExtendido.objects.filter(email=email).exists():
            print("⚠️ Ya existe un usuario local con ese email.")
            return

        password = getpass.getpass("🔑 Contraseña: ").strip()
        confirm = getpass.getpass("🔒 Confirmar contraseña: ").strip()

        if not password or password != confirm:
            print("❌ Las contraseñas no coinciden o están vacías.")
            return

        # Crear en Firebase
        try:
            firebase_user = auth.create_user(email=email, password=password, display_name=nombre)
            uid = firebase_user.uid
            print(f"✅ Usuario creado en Firebase Auth. UID: {uid}")
        except auth.EmailAlreadyExistsError:
            print("❌ Ese email ya está registrado en Firebase.")
            return
        except Exception as e:
            print(f"❌ Error al crear usuario en Firebase: {e}")
            return

        # Selección de roles
        roles = Rol.objects.all()
        if not roles.exists():
            print("⚠️ No hay roles definidos.")
            return

        print("\n📋 Roles disponibles:")
        for i, r in enumerate(roles, 1):
            print(f"{i}. {r.nombre}")

        entrada = input("Selecciona los números de roles (ej. 1,2): ").strip()
        try:
            indices = [int(x.strip()) for x in entrada.split(",")]
            roles_seleccionados = [roles[i - 1] for i in indices if 1 <= i <= len(roles)]
        except Exception:
            print("❌ Error en la selección de roles.")
            return

        # Crear en base local
        try:
            with transaction.atomic():
                usuario = UsuarioExtendido.objects.create(
                    uid=uid,
                    email=email,
                    nombre=nombre,
                    idioma=idioma
                )
                usuario.set_unusable_password()  # No se guarda contraseña localmente (usa Firebase)
                usuario.roles.set(roles_seleccionados)
                usuario.save()

                firestore.client().collection("usuarios").document(uid).set({
                    "email": email,
                    "nombre": nombre,
                    "idioma": idioma,
                    "roles": [r.nombre for r in roles_seleccionados]
                })

                print("✅ Usuario creado localmente y sincronizado con Firestore.")
                Path("ultimo_usuario_creado.txt").write_text(f"{usuario.email} → {uid}\n", encoding="utf-8")
        except Exception as e:
            print(f"⚠️ Error al crear en base local o sincronizar con Firestore: {e}")
            print("⚠️ El usuario fue creado en Firebase pero no en la base local.")

    def eliminar_usuario(self):
        usuarios = UsuarioExtendido.objects.all().order_by("email")
        print("\nUsuarios disponibles:")
        for i, u in enumerate(usuarios, 1):
            print(f"{i}. {u.email} — {', '.join([r.nombre for r in u.roles.all()]) or 'Sin rol'}")
        print("0. Volver")

        try:
            index = int(input("\nSelecciona el número de usuario a eliminar: "))
            if index == 0:
                return
            usuario = usuarios[index - 1]
        except (ValueError, IndexError):
            print("❌ Índice inválido.")
            return

        tiene_datos_asociados = self._tiene_relaciones(usuario)

        if tiene_datos_asociados:
            print("⚠️ El usuario tiene movimientos asociados.")
            if hasattr(usuario, "activo"):
                usuario.activo = False
                usuario.save()
                print("🛑 Usuario marcado como inactivo.")
            else:
                print("❌ El modelo no tiene campo 'activo'. No se puede desactivar.")
            return

        confirm = input(f"¿Confirmás eliminar a {usuario.email}? [s/N]: ").strip().lower()
        if confirm == "s":
            try:
                usuario.delete()
                firestore.client().collection("usuarios").document(usuario.uid).delete()
                print("🗑️ Usuario eliminado de la base local y Firebase.")
            except Exception as e:
                print(f"⚠️ Error al eliminar en Firebase: {e}")
        else:
            print("↪️ Cancelado.")

    def _tiene_relaciones(self, usuario):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.constraint_column_usage
                WHERE table_name != 'core_usuarioextendido'
                AND column_name = 'uid'
            """)
            row = cursor.fetchone()
            return row[0] > 0
