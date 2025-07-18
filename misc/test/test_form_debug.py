#!/usr/bin/env python
"""
Test simple para debug del formulario de empresa
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

def test_form_debug():
    """Test simple para verificar el formulario"""
    print("🔍 Test de debug del formulario de empresa")
    print("=" * 50)
    
    client = Client()
    
    # Test 1: Verificar que la página de crear empresa cargue
    print("\n1️⃣ Test: Página de crear empresa")
    try:
        response = client.get(reverse('core:empresa_crear'))
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Página carga correctamente")
            content = response.content.decode('utf-8')
            
            # Verificar elementos del formulario
            checks = [
                ('id="empresa-form"', 'Formulario con ID correcto'),
                ('method="post"', 'Método POST'),
                ('action=', 'URL de acción'),
                ('type="submit"', 'Botón submit'),
                ('Cancelar', 'Botón cancelar'),
                ('Crear', 'Botón crear'),
            ]
            
            for check, description in checks:
                if check in content:
                    print(f"   ✅ {description}")
                else:
                    print(f"   ❌ {description}")
        else:
            print("   ❌ Página no carga")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Verificar que la página de editar empresa cargue
    print("\n2️⃣ Test: Página de editar empresa")
    try:
        # Crear empresa de prueba
        country = Country.objects.create(name='Argentina', code='AR')
        state = State.objects.create(name='Buenos Aires', country=country, code='BA')
        fiscal_responsibility = FiscalResponsibility.objects.create(name='Responsable Inscripto', code='RI')
        
        empresa = Empresa.objects.create(
            nombre='Empresa Test',
            razon_social='Empresa Test S.A.',
            identificador_fiscal='20-12345678-9',
            country=country,
            state=state,
            fiscal_responsibility=fiscal_responsibility
        )
        
        response = client.get(reverse('core:empresa_editar', kwargs={'empresa_id': empresa.id}))
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Página carga correctamente")
            content = response.content.decode('utf-8')
            
            # Verificar elementos del formulario
            checks = [
                ('id="empresa-form"', 'Formulario con ID correcto'),
                ('method="post"', 'Método POST'),
                ('action=', 'URL de acción'),
                ('type="submit"', 'Botón submit'),
                ('Cancelar', 'Botón cancelar'),
                ('Guardar', 'Botón guardar'),
            ]
            
            for check, description in checks:
                if check in content:
                    print(f"   ✅ {description}")
                else:
                    print(f"   ❌ {description}")
        else:
            print("   ❌ Página no carga")
            
        # Limpiar
        empresa.delete()
        country.delete()
        state.delete()
        fiscal_responsibility.delete()
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Verificar URLs
    print("\n3️⃣ Test: URLs")
    urls_to_test = [
        ('core:empresa_listar', 'Lista de empresas'),
        ('core:empresa_crear', 'Crear empresa'),
    ]
    
    for url_name, description in urls_to_test:
        try:
            url = reverse(url_name)
            print(f"   ✅ {description}: {url}")
        except Exception as e:
            print(f"   ❌ {description}: {e}")
    
    print("\n🎉 Test de debug completado!")

if __name__ == "__main__":
    try:
        test_form_debug()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 