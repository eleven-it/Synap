# core/management/commands/crear_usuario.py
# Firebase deshabilitado para instalación mínima de Reportes

from django.core.management.base import BaseCommand
# Firebase deshabilitado para instalación mínima de Reportes
# from firebase_admin import auth, firestore
from core.models import UsuarioExtendido, Rol
from django.db import transaction
import getpass

class Command(BaseCommand):
    help = "Crea un usuario (Firebase deshabilitado - usar autenticación administraNET)"

    def handle(self, *args, **options):
        self.stderr.write(self.style.ERROR("❌ Este comando requiere Firebase, que está deshabilitado en la instalación mínima de Reportes."))
        self.stderr.write("💡 Para crear usuarios, usa la autenticación de administraNET Gestión directamente.")
        return
        
        # Código deshabilitado - Firebase no está disponible
        # self.stdout.write(self.style.SUCCESS("=== Crear nuevo usuario ==="))
        # 
        # email = input("📧 Email: ").strip().lower()
        # nombre = input("👤 Nombre: ").strip()
        # idioma = input("🌐 Idioma [es]: ").strip() or "es"
        # password = getpass.getpass("🔑 Contraseña: ")
        # confirm = getpass.getpass("🔒 Confirmar contraseña: ")
        # 
        # if password != confirm:
        #     self.stderr.write("❌ Las contraseñas no coinciden.")
        #     return
        # 
        # roles = Rol.objects.all()
        # if not roles.exists():
        #     self.stderr.write("⚠️ No hay roles cargados.")
        #     return
        # 
        # self.stdout.write("\n📋 Roles disponibles:")
        # for rol in roles:
        #     self.stdout.write(f" [{rol.id}] {rol.nombre}")
        # seleccion = input("\nIDs de roles (ej: 1,2): ").strip()
        # roles_ids = [int(i) for i in seleccion.split(",") if i.isdigit()]
        # 
        # # Crear en Firebase
        # try:
        #     firebase_user = auth.create_user(email=email, password=password, display_name=nombre)
        #     uid = firebase_user.uid
        #     self.stdout.write(self.style.SUCCESS(f"✅ Firebase UID: {uid}"))
        # except Exception as e:
        #     self.stderr.write(f"❌ Error en Firebase: {e}")
        #     return
        # 
        # # Crear en base local
        # try:
        #     with transaction.atomic():
        #         usuario = UsuarioExtendido.objects.create(
        #             uid=uid,
        #             email=email,
        #             nombre=nombre,
        #             idioma=idioma,
        #             username=email,
        #             password=""
        #         )
        #         usuario.roles.set(roles_ids)
        #         usuario.save()
        # 
        #         firestore.client().collection("usuarios").document(uid).set({
        #             "email": email,
        #             "nombre": nombre,
        #             "idioma": idioma,
        #             "roles": list(usuario.roles.values_list("nombre", flat=True)),
        #         })
        # 
        #         self.stdout.write(self.style.SUCCESS(f"✅ Usuario '{email}' creado y sincronizado."))
        # except Exception as e:
        #     self.stderr.write(f"⚠️ Falló creación local: {e}")
