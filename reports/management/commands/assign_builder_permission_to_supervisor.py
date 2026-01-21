from django.core.management.base import BaseCommand
from core.models import Rol, Permiso, UsuarioExtendido


class Command(BaseCommand):
    help = "Asigna el permiso reports.builder al rol Supervisor o al usuario Supervisor"

    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            action='store_true',
            help='Asignar permiso al rol Supervisor',
        )
        parser.add_argument(
            '--user',
            action='store_true',
            help='Asignar permiso directamente al usuario Supervisor',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Asignar permiso tanto al rol como al usuario Supervisor',
        )
        parser.add_argument(
            '--list-users',
            action='store_true',
            help='Listar todos los usuarios disponibles para identificar el Supervisor',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email específico del usuario al que asignar el permiso',
        )

    def handle(self, *args, **options):
        # Listar usuarios si se solicita
        if options.get('list_users'):
            self.stdout.write(self.style.SUCCESS("\n📋 Usuarios disponibles:\n"))
            usuarios = UsuarioExtendido.objects.filter(is_active=True).order_by('email')
            for usuario in usuarios:
                roles = ", ".join([r.nombre for r in usuario.roles.filter(activo=True)])
                tiene_permiso = usuario.permisos_extra.filter(codigo="reports.builder").exists()
                permiso_status = "✅" if tiene_permiso else "❌"
                self.stdout.write(f"  {permiso_status} {usuario.email} (nombre: {usuario.nombre or 'N/A'}, roles: {roles or 'Ninguno'})")
            self.stdout.write("")
            return
        
        # Obtener o crear el permiso reports.builder
        permiso, created = Permiso.objects.get_or_create(
            codigo="reports.builder",
            defaults={
                "nombre": "Usar constructor visual de reportes",
                "descripcion": "Permite usar el Report Builder para crear y editar reportes declarativos",
                "activo": True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ Permiso 'reports.builder' creado"))
        else:
            self.stdout.write(f"ℹ️  Permiso 'reports.builder' ya existe")
        
        # Activar el permiso si estaba inactivo
        if not permiso.activo:
            permiso.activo = True
            permiso.save()
            self.stdout.write(self.style.SUCCESS(f"✅ Permiso 'reports.builder' activado"))

        assigned = False
        
        # Asignar a usuario específico por email
        if options.get('email'):
            try:
                usuario = UsuarioExtendido.objects.filter(email__iexact=options['email']).first()
                if usuario:
                    if permiso not in usuario.permisos_extra.all():
                        usuario.permisos_extra.add(permiso)
                        self.stdout.write(self.style.SUCCESS(
                            f"✅ Permiso 'reports.builder' asignado al usuario '{usuario.email}'"
                        ))
                        assigned = True
                    else:
                        self.stdout.write(f"ℹ️  El usuario '{usuario.email}' ya tiene el permiso 'reports.builder'")
                else:
                    self.stdout.write(self.style.ERROR(f"❌ No se encontró usuario con email '{options['email']}'"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error asignando permiso: {e}"))

        # Asignar al rol Supervisor
        if options.get('role') or options.get('all'):
            try:
                rol_supervisor = Rol.objects.filter(nombre__iexact="supervisor", activo=True).first()
                if rol_supervisor:
                    if permiso not in rol_supervisor.permisos.all():
                        rol_supervisor.permisos.add(permiso)
                        self.stdout.write(self.style.SUCCESS(f"✅ Permiso 'reports.builder' asignado al rol 'Supervisor'"))
                        assigned = True
                    else:
                        self.stdout.write(f"ℹ️  El rol 'Supervisor' ya tiene el permiso 'reports.builder'")
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️  No se encontró el rol 'Supervisor' activo"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error asignando permiso al rol: {e}"))

        # Asignar directamente al usuario Supervisor
        if options.get('user') or options.get('all'):
            try:
                # Buscar usuario por email o nombre que contenga "supervisor"
                usuario_supervisor = UsuarioExtendido.objects.filter(
                    email__icontains="supervisor"
                ).first()
                
                if not usuario_supervisor:
                    # Intentar buscar por nombre
                    usuario_supervisor = UsuarioExtendido.objects.filter(
                        nombre__icontains="supervisor"
                    ).first()
                
                if usuario_supervisor:
                    if permiso not in usuario_supervisor.permisos_extra.all():
                        usuario_supervisor.permisos_extra.add(permiso)
                        self.stdout.write(self.style.SUCCESS(
                            f"✅ Permiso 'reports.builder' asignado directamente al usuario '{usuario_supervisor.email}' (nombre: {usuario_supervisor.nombre})"
                        ))
                        assigned = True
                    else:
                        self.stdout.write(f"ℹ️  El usuario '{usuario_supervisor.email}' ya tiene el permiso 'reports.builder'")
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️  No se encontró usuario Supervisor (buscado por email o nombre que contenga 'supervisor')"))
                    self.stdout.write(self.style.WARNING(f"   Usa --list-users para ver todos los usuarios disponibles"))
                    self.stdout.write(self.style.WARNING(f"   O usa --email <email> para asignar a un usuario específico"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error asignando permiso al usuario: {e}"))

        # Si no se especificó ninguna opción, asignar a ambos por defecto
        if not (options.get('role') or options.get('user') or options.get('all')):
            self.stdout.write(self.style.WARNING("⚠️  No se especificó opción. Usando --all por defecto"))
            # Asignar al rol
            try:
                rol_supervisor = Rol.objects.filter(nombre__iexact="supervisor", activo=True).first()
                if rol_supervisor:
                    if permiso not in rol_supervisor.permisos.all():
                        rol_supervisor.permisos.add(permiso)
                        self.stdout.write(self.style.SUCCESS(f"✅ Permiso 'reports.builder' asignado al rol 'Supervisor'"))
                        assigned = True
                    else:
                        self.stdout.write(f"ℹ️  El rol 'Supervisor' ya tiene el permiso 'reports.builder'")
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️  No se encontró el rol 'Supervisor' activo"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error asignando permiso al rol: {e}"))
            
            # Asignar al usuario
            try:
                usuario_supervisor = UsuarioExtendido.objects.filter(
                    email__icontains="supervisor"
                ).first()
                
                if not usuario_supervisor:
                    usuario_supervisor = UsuarioExtendido.objects.filter(
                        nombre__icontains="supervisor"
                    ).first()
                
                if usuario_supervisor:
                    if permiso not in usuario_supervisor.permisos_extra.all():
                        usuario_supervisor.permisos_extra.add(permiso)
                        self.stdout.write(self.style.SUCCESS(
                            f"✅ Permiso 'reports.builder' asignado directamente al usuario '{usuario_supervisor.email}' (nombre: {usuario_supervisor.nombre})"
                        ))
                        assigned = True
                    else:
                        self.stdout.write(f"ℹ️  El usuario '{usuario_supervisor.email}' ya tiene el permiso 'reports.builder'")
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️  No se encontró usuario Supervisor (buscado por email o nombre que contenga 'supervisor')"))
                    self.stdout.write(self.style.WARNING(f"   Usa --list-users para ver todos los usuarios disponibles"))
                    self.stdout.write(self.style.WARNING(f"   O usa --email <email> para asignar a un usuario específico"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error asignando permiso al usuario: {e}"))

        if assigned:
            self.stdout.write(self.style.SUCCESS("\n✅ Permiso asignado correctamente. El usuario Supervisor ahora puede acceder al Report Builder."))
            self.stdout.write(self.style.WARNING("⚠️  Nota: Si el usuario ya estaba logueado, debe cerrar sesión y volver a iniciar sesión para que los cambios surtan efecto."))
        else:
            self.stdout.write(self.style.WARNING("\n⚠️  No se pudo asignar el permiso. Verifica que el rol o usuario Supervisor exista."))

