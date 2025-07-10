from django.core.management.base import BaseCommand
from core.models import UsuarioExtendido, Branch

class Command(BaseCommand):
    help = 'Asigna todas las sucursales existentes a los usuarios con rol administrador.'

    def handle(self, *args, **options):
        admins = UsuarioExtendido.objects.filter(roles__nombre__iexact="administrador", is_active=True).distinct()
        sucursales = Branch.objects.all()
        for admin in admins:
            admin.branches.add(*sucursales)
            if not admin.default_branch and sucursales.exists():
                admin.default_branch = sucursales.first()
                admin.save(update_fields=["default_branch"])
        self.stdout.write(self.style.SUCCESS(f"Asignadas {sucursales.count()} sucursales a {admins.count()} administradores.")) 