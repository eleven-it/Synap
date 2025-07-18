#!/usr/bin/env python
"""
Test específico para debuggear el problema de edición del país
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from core.models import Empresa, Country, State, FiscalResponsibility
from core.models.currency import Currency

def test_edit_debug():
    """Test específico para debuggear la edición"""
    print("🔍 Debug: Test de edición de país")
    print("=" * 50)
    
    client = Client()
    
    # 1. Crear datos de prueba
    print("\n1️⃣ Creando datos de prueba...")
    
    # Crear países
    country1 = Country.objects.create(name='Argentina', code='AR')
    country2 = Country.objects.create(name='Brasil', code='BR')
    print(f"   ✅ País 1: {country1.name} (ID: {country1.id})")
    print(f"   ✅ País 2: {country2.name} (ID: {country2.id})")
    
    # Crear otros datos necesarios
    state = State.objects.create(name='Buenos Aires', country=country1, code='BA')
    fiscal_responsibility = FiscalResponsibility.objects.create(name='Responsable Inscripto', code='RI')
    currency = Currency.objects.create(name='Peso Argentino', code='ARS', symbol='$')
    
    # 2. Crear empresa con país 1
    print("\n2️⃣ Creando empresa con país 1...")
    
    empresa_data = {
        'nombre': 'Empresa Debug Test',
        'razon_social': 'Empresa Debug Test S.A.',
        'identificador_fiscal': '20-12345678-9',
        'email': 'debug@test.com',
        'telefono': '+54 11 1234-5678',
        'direccion': 'Calle Debug 123',
        'country_name': country1.name,
        'country_id': str(country1.id),
        'state_id': str(state.id),
        'fiscal_responsibility_id': str(fiscal_responsibility.id),
        'currency_id': str(currency.id),
        'ciudad': 'Buenos Aires',
        'activa': True
    }
    
    response = client.post(reverse('core:empresa_crear'), empresa_data, follow=True)
    print(f"   Status: {response.status_code}")
    
    empresa = Empresa.objects.filter(nombre='Empresa Debug Test').first()
    if empresa:
        print(f"   ✅ Empresa creada: {empresa.nombre} (ID: {empresa.id})")
        print(f"   ✅ País inicial: {empresa.country.name} (ID: {empresa.country.id})")
        assert empresa.country.id == country1.id, f"País inicial incorrecto: esperado {country1.id}, obtenido {empresa.country.id}"
    else:
        print("   ❌ Empresa no creada")
        return False
    
    # 3. Intentar editar para cambiar a país 2
    print("\n3️⃣ Editando empresa para cambiar a país 2...")
    
    empresa_data_edit = {
        'nombre': 'Empresa Debug Test - Editada',
        'razon_social': 'Empresa Debug Test Editada S.A.',
        'identificador_fiscal': '20-87654321-0',
        'email': 'editado@debug.com',
        'telefono': '+54 11 8765-4321',
        'direccion': 'Calle Editada 456',
        'country_name': country2.name,  # Cambiar a país 2
        'country_id': str(country2.id),  # ID del país 2
        'state_id': str(state.id),
        'fiscal_responsibility_id': str(fiscal_responsibility.id),
        'currency_id': str(currency.id),
        'ciudad': 'Córdoba',
        'activa': True
    }
    
    print(f"   📋 Datos a enviar:")
    print(f"      - country_name: {empresa_data_edit['country_name']}")
    print(f"      - country_id: {empresa_data_edit['country_id']}")
    print(f"      - País esperado: {country2.name} (ID: {country2.id})")
    
    response = client.post(reverse('core:empresa_editar', kwargs={'empresa_id': empresa.id}), empresa_data_edit, follow=True)
    print(f"   Status: {response.status_code}")
    
    # 4. Verificar el resultado
    print("\n4️⃣ Verificando resultado...")
    
    empresa.refresh_from_db()
    print(f"   📊 Estado final:")
    print(f"      - Nombre: {empresa.nombre}")
    print(f"      - País actual: {empresa.country.name if empresa.country else 'None'} (ID: {empresa.country.id if empresa.country else 'None'})")
    print(f"      - País esperado: {country2.name} (ID: {country2.id})")
    
    if empresa.country and empresa.country.id == country2.id:
        print("   ✅ País cambiado correctamente!")
    else:
        print("   ❌ País NO cambió correctamente")
        print(f"      - Esperado: {country2.id}")
        print(f"      - Obtenido: {empresa.country.id if empresa.country else 'None'}")
        
        # Debug adicional
        print("\n🔍 Debug adicional:")
        print(f"      - Datos POST enviados: {empresa_data_edit}")
        print(f"      - Formulario válido: {response.status_code == 200}")
        
        # Verificar si hay errores en la respuesta
        if hasattr(response, 'context') and response.context:
            form = response.context.get('form')
            if form and form.errors:
                print(f"      - Errores del formulario: {form.errors}")
    
    # 5. Limpiar
    print("\n5️⃣ Limpiando datos de prueba...")
    empresa.delete()
    country1.delete()
    country2.delete()
    state.delete()
    fiscal_responsibility.delete()
    currency.delete()
    print("   ✅ Datos limpiados")
    
    print("\n🎉 Test de debug completado!")
    return True

if __name__ == "__main__":
    try:
        success = test_edit_debug()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 