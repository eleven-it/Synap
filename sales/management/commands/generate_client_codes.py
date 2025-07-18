from django.core.management.base import BaseCommand
from sales.models import Client
from django.db.models import Max


class Command(BaseCommand):
    help = 'Genera códigos para clientes que no tienen código asignado'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué códigos se generarían sin aplicarlos',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Obtener clientes sin código
        clients_without_code = Client.objects.filter(code__isnull=True) | Client.objects.filter(code='')
        
        if not clients_without_code.exists():
            self.stdout.write(
                self.style.SUCCESS('Todos los clientes ya tienen códigos asignados.')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(
                f'Encontrados {clients_without_code.count()} clientes sin código.'
            )
        )
        
        if dry_run:
            self.stdout.write('Modo DRY RUN - No se aplicarán cambios:')
            self.stdout.write('')
        
        # Buscar el último código global
        last_code = Client.objects.filter(code__startswith='CLI-').aggregate(
            max_code=Max('code')
        )['max_code']
        if last_code:
            try:
                last_number = int(last_code.split('-')[-1])
                next_number = last_number + 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            next_number = 1
        
        updated_count = 0
        
        for client in clients_without_code:
            new_code = f'CLI-{next_number}'
            
            if dry_run:
                self.stdout.write(
                    f'  {client.name} -> {new_code}'
                )
            else:
                client.code = new_code
                client.save(update_fields=['code'])
                self.stdout.write(
                    f'  ✓ {client.name} -> {new_code}'
                )
                updated_count += 1
            
            next_number += 1
        
        if dry_run:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(
                    f'Se generarían {updated_count} códigos (modo DRY RUN)'
                )
            )
        else:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    f'Se generaron {updated_count} códigos exitosamente.'
                )
            ) 