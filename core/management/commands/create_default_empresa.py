from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Empresa, Branch


class Command(BaseCommand):
    help = 'Crea una empresa y sucursal por defecto para staging'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-nombre',
            type=str,
            default='Empresa Staging',
            help='Nombre de la empresa a crear',
        )
        parser.add_argument(
            '--empresa-identificador',
            type=str,
            default='STAGING-001',
            help='Identificador fiscal de la empresa',
        )
        parser.add_argument(
            '--branch-nombre',
            type=str,
            default='Sucursal Principal',
            help='Nombre de la sucursal a crear',
        )
        parser.add_argument(
            '--branch-codigo',
            type=str,
            default='STAGING-BRANCH-001',
            help='Código interno de la sucursal',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecuta sin hacer cambios reales en la base de datos',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        empresa_nombre = options['empresa_nombre']
        empresa_identificador = options['empresa_identificador']
        branch_nombre = options['branch_nombre']
        branch_codigo = options['branch_codigo']

        self.stdout.write(
            self.style.SUCCESS('🚀 Creando empresa y sucursal por defecto...')
        )

        # Verificar si ya existe una empresa
        existing_empresa = Empresa.objects.first()
        if existing_empresa:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Ya existe una empresa: {existing_empresa.nombre} (ID: {existing_empresa.id})')
            )
            
            existing_branch = Branch.objects.filter(empresa=existing_empresa).first()
            if existing_branch:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Ya existe una sucursal: {existing_branch.name} (ID: {existing_branch.id})')
                )
                self.stdout.write(
                    self.style.SUCCESS('✅ Usando empresa y sucursal existentes')
                )
                return
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  La empresa no tiene sucursales, creando una nueva...')
                )
                empresa = existing_empresa
        else:
            self.stdout.write(f'📝 Creando nueva empresa: {empresa_nombre}')
            empresa = None

        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 MODO DRY-RUN: No se harán cambios reales en la base de datos')
            )
            self.stdout.write(f'   📋 Se crearían:')
            if not empresa:
                self.stdout.write(f'      - Empresa: {empresa_nombre} ({empresa_identificador})')
            self.stdout.write(f'      - Sucursal: {branch_nombre} ({branch_codigo})')
            return

        try:
            with transaction.atomic():
                # Crear empresa si no existe
                if not empresa:
                    empresa = Empresa.objects.create(
                        nombre=empresa_nombre,
                        identificador_fiscal=empresa_identificador,
                        email='admin@staging.synap.com',
                        telefono='+54 11 1234-5678',
                        direccion='Av. Staging 123',
                        pais='Argentina',
                        ciudad='Buenos Aires',
                        activa=True
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Empresa creada: {empresa.nombre} (ID: {empresa.id})')
                    )

                # Crear sucursal
                branch = Branch.objects.create(
                    empresa=empresa,
                    name=branch_nombre,
                    code=branch_codigo,
                    address='Av. Staging 123, Piso 1',
                    city='Buenos Aires',
                    state='Buenos Aires',
                    country='Argentina',
                    phone='+54 11 1234-5678',
                    email='branch@staging.synap.com',
                    active=True
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Sucursal creada: {branch.name} (ID: {branch.id})')
                )

            self.stdout.write(
                self.style.SUCCESS('🎉 Empresa y sucursal creadas exitosamente')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al crear empresa y sucursal: {e}')
            )
            if not dry_run:
                self.stdout.write(
                    self.style.ERROR('🔄 Los cambios han sido revertidos debido al error')
                )

        # Mostrar resumen final
        self.stdout.write('\n📋 RESUMEN FINAL:')
        self.stdout.write(f'   🏢 Empresa: {empresa.nombre} (ID: {empresa.id})')
        self.stdout.write(f'   🏪 Sucursal: {branch.name} (ID: {branch.id})')
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS('✅ Ahora puedes ejecutar initialize_empresa_branch')
            )
        else:
            self.stdout.write(
                self.style.WARNING('🔍 Ejecuta sin --dry-run para crear la empresa y sucursal')
            ) 