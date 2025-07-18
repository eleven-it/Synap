from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Empresa, Contact
from sales.models import Client
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class Command(BaseCommand):
    help = 'Test the contacts system by creating sample data'

    def handle(self, *args, **options):
        self.stdout.write('🧪 Testing contacts system...')
        
        # Crear empresa de prueba si no existe
        empresa, created = Empresa.objects.get_or_create(
            name="Test Company",
            defaults={
                'identificador_fiscal': '12345678',
                'email': 'test@company.com'
            }
        )
        
        if created:
            self.stdout.write(f'✅ Created test company: {empresa.name}')
        
        # Crear contactos de prueba
        contacts_data = [
            {
                'name': 'Juan Pérez',
                'email': 'juan.perez@example.com',
                'phone': '+54 11 1234-5678',
                'position': 'Gerente de Administración',
                'company_name': 'Empresa ABC',
                'type': 'person'
            },
            {
                'name': 'María González',
                'email': 'maria.gonzalez@example.com',
                'phone': '+54 11 2345-6789',
                'position': 'Responsable de Compras',
                'company_name': 'Empresa ABC',
                'type': 'person'
            },
            {
                'name': 'Carlos Rodríguez',
                'email': 'carlos.rodriguez@example.com',
                'phone': '+54 11 3456-7890',
                'position': 'Técnico de Sistemas',
                'company_name': 'Empresa ABC',
                'type': 'person'
            },
            {
                'name': 'Ana Martínez',
                'email': 'ana.martinez@example.com',
                'phone': '+54 11 4567-8901',
                'position': 'Contadora',
                'company_name': 'Empresa ABC',
                'type': 'person'
            }
        ]
        
        created_contacts = []
        for contact_data in contacts_data:
            contact, created = Contact.objects.get_or_create(
                email=contact_data['email'],
                defaults={
                    'name': contact_data['name'],
                    'phone': contact_data['phone'],
                    'position': contact_data['position'],
                    'company_name': contact_data['company_name'],
                    'type': contact_data['type'],
                    'empresa': empresa
                }
            )
            
            if created:
                created_contacts.append(contact)
                self.stdout.write(f'✅ Created contact: {contact.display_name}')
            else:
                self.stdout.write(f'ℹ️  Contact already exists: {contact.display_name}')
        
        # Crear cliente de prueba
        client, created = Client.objects.get_or_create(
            name='Empresa ABC',
            defaults={
                'type': 'company',
                'tax_id': '30-12345678-9',
                'email': 'info@empresaabc.com',
                'phone': '+54 11 1234-5678',
                'empresa': empresa
            }
        )
        
        if created:
            self.stdout.write(f'✅ Created test client: {client.name}')
        
        # Agregar contactos al cliente
        relationship_types = ['primary', 'billing', 'technical', 'decision_maker']
        
        for i, contact in enumerate(created_contacts):
            relationship_type = relationship_types[i % len(relationship_types)]
            
            if not client.has_contact(contact, relationship_type):
                relationship = client.add_contact(contact, relationship_type)
                self.stdout.write(f'✅ Added {contact.display_name} as {relationship_type} to {client.name}')
            else:
                self.stdout.write(f'ℹ️  {contact.display_name} already has {relationship_type} relationship with {client.name}')
        
        # Mostrar estadísticas
        total_contacts = Contact.objects.count()
        total_clients = Client.objects.count()
        total_relationships = client.contact_relationships.count()
        
        self.stdout.write('\n📊 Statistics:')
        self.stdout.write(f'   Total contacts: {total_contacts}')
        self.stdout.write(f'   Total clients: {total_clients}')
        self.stdout.write(f'   Relationships for {client.name}: {total_relationships}')
        
        # Mostrar contactos del cliente
        self.stdout.write(f'\n👥 Contacts for {client.name}:')
        for relationship in client.get_contacts():
            self.stdout.write(f'   • {relationship.contact.display_name} ({relationship.get_relationship_type_display()})')
        
        self.stdout.write('\n🎉 Contacts system test completed successfully!')
        self.stdout.write('You can now test the wizard at: /sales/clients/wizard/step4/{client_id}/') 