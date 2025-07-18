from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import UsuarioExtendido

PERMISSIONS = [
    # (codename, name)
    ("access_adminet_module", "Can access administraNET integration module"),
    ("edit_adminet_mappings", "Can edit administraNET mappings"),
    ("view_adminet_logs", "Can view administraNET logs and error reports"),
    ("run_adminet_sync", "Can execute administraNET synchronizations"),
    ("configure_adminet_sync", "Can configure administraNET sync intervals and advanced settings"),
]

class Command(BaseCommand):
    help = "Inicializa el grupo y permisos para la integración administraNET."

    def handle(self, *args, **options):
        # Crear grupo
        group, created = Group.objects.get_or_create(name="administraNET")
        if created:
            self.stdout.write(self.style.SUCCESS("Grupo 'administraNET' creado."))
        else:
            self.stdout.write("Grupo 'administraNET' ya existe.")

        # Crear permisos custom
        content_type = ContentType.objects.get_for_model(Group)  # Asociar a Group para centralizar
        created_perms = []
        for codename, name in PERMISSIONS:
            perm, perm_created = Permission.objects.get_or_create(
                codename=codename,
                content_type=content_type,
                defaults={"name": name}
            )
            if perm_created:
                created_perms.append(codename)
            group.permissions.add(perm)
        self.stdout.write(self.style.SUCCESS(f"Permisos asignados al grupo 'administraNET': {[p[0] for p in PERMISSIONS]}"))
        if created_perms:
            self.stdout.write(self.style.SUCCESS(f"Permisos creados: {created_perms}"))
        else:
            self.stdout.write("Todos los permisos ya existían.")

        # Asignar permisos al superusuario extendido
        superusers = UsuarioExtendido.objects.filter(is_superuser=True)
        for user in superusers:
            for codename, _ in PERMISSIONS:
                perm = Permission.objects.get(codename=codename)
                user.user_permissions.add(perm)
            self.stdout.write(self.style.SUCCESS(f"Permisos asignados al superusuario: {user.username}"))

        self.stdout.write(self.style.SUCCESS("Inicialización de permisos administraNET completada."))
        self.stdout.write("Permisos definidos:")
        for codename, name in PERMISSIONS:
            self.stdout.write(f"- {codename}: {name}") 