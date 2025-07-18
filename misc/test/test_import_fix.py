#!/usr/bin/env python
"""
Test simple para verificar que la importación de Country esté funcionando
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

def test_import_fix():
    """Test simple para verificar la importación"""
    print("🔍 Test de importación de Country")
    print("=" * 50)
    
    # Test 1: Verificar que Country esté importado
    print("\n1️⃣ Test: Importación de Country")
    try:
        country = Country.objects.create(name='Argentina', code='AR')
        print(f"   ✅ Country creado exitosamente: {country.name} (ID: {country.id})")
        
        # Limpiar
        country.delete()
        print("   ✅ Country eliminado")
    except Exception as e:
        print(f"   ❌ Error con Country: {e}")
        return False
    
    # Test 2: Verificar que la página de crear empresa cargue
    print("\n2️⃣ Test: Página de crear empresa")
    try:
        client = Client()
        response = client.get(reverse('core:empresa_crear'))
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Página carga correctamente")
        else:
            print("   ❌ Página no carga")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 3: Verificar que la página de editar empresa cargue
    print("\n3️⃣ Test: Página de editar empresa")
    try:
        # Crear empresa de prueba
        country = Country.objects.create(name='Argentina', code='AR')
        state = State.objects.create(name='Buenos Aires', country=country, code='BA')
        fiscal_responsibility = FiscalResponsibility.objects.create(name='Responsable Inscripto', code='RI')
        
        empresa = Empresa.objects.create(
            nombre='Empresa Test Import',
            razon_social='Empresa Test Import S.A.',
            identificador_fiscal='20-12345678-9',
            country=country,
            state=state,
            fiscal_responsibility=fiscal_responsibility
        )
        
        response = client.get(reverse('core:empresa_editar', kwargs={'empresa_id': empresa.id}))
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Página carga correctamente")
        else:
            print("   ❌ Página no carga")
            
        # Limpiar
        empresa.delete()
        country.delete()
        state.delete()
        fiscal_responsibility.delete()
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n🎉 Test de importación completado exitosamente!")
    return True

if __name__ == "__main__":
    try:
        success = test_import_fix()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 