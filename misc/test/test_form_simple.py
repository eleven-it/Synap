#!/usr/bin/env python
"""
Test simple para verificar el formulario de empresa y ver logs
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

def test_form_simple():
    """Test simple para verificar el formulario"""
    print("🔍 Test simple del formulario de empresa")
    print("=" * 50)
    
    client = Client()
    
    # Crear datos de prueba
    print("\n1️⃣ Creando datos de prueba...")
    country = Country.objects.create(name='Argentina', code='AR')
    state = State.objects.create(name='Buenos Aires', country=country, code='BA')
    fiscal_responsibility = FiscalResponsibility.objects.create(name='Responsable Inscripto', code='RI')
    
    print(f"   ✅ País creado: {country.name} (ID: {country.id})")
    print(f"   ✅ Provincia creada: {state.name} (ID: {state.id})")
    print(f"   ✅ Responsabilidad creada: {fiscal_responsibility.name} (ID: {fiscal_responsibility.id})")
    
    # Test 1: GET a crear empresa
    print("\n2️⃣ Test: GET /core/empresas/crear/")
    try:
        response = client.get(reverse('core:empresa_crear'))
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Página carga correctamente")
        else:
            print("   ❌ Página no carga")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: POST a crear empresa
    print("\n3️⃣ Test: POST /core/empresas/crear/")
    try:
        empresa_data = {
            'nombre': 'Empresa Test Simple',
            'razon_social': 'Empresa Test Simple S.A.',
            'identificador_fiscal': '30-12345678-9',
            'email': 'test@empresa.com',
            'telefono': '+54 11 1234-5678',
            'direccion': 'Av. Test 123',
            'ciudad': 'Buenos Aires',
            'country_name': country.name,
            'country_id': str(country.id),
            'state_name': state.name,
            'state_id': str(state.id),
            'fiscal_responsibility_name': fiscal_responsibility.name,
            'fiscal_responsibility_id': str(fiscal_responsibility.id),
            'activa': True
        }
        
        print(f"   📋 Enviando datos: {empresa_data}")
        response = client.post(reverse('core:empresa_crear'), empresa_data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 302:
            print("   ✅ Redirección exitosa (empresa creada)")
            # Verificar que la empresa se creó
            empresa = Empresa.objects.filter(nombre='Empresa Test Simple').first()
            if empresa:
                print(f"   ✅ Empresa creada en BD: {empresa.id}")
                print(f"   📋 Datos de la empresa:")
                print(f"      - Nombre: {empresa.nombre}")
                print(f"      - País: {empresa.country.name if empresa.country else 'None'}")
                print(f"      - Provincia: {empresa.state.name if empresa.state else 'None'}")
                print(f"      - Responsabilidad: {empresa.fiscal_responsibility.name if empresa.fiscal_responsibility else 'None'}")
            else:
                print("   ❌ Empresa no encontrada en BD")
        elif response.status_code == 200:
            print("   ⚠️  Página devuelta (posible error de validación)")
            content = response.content.decode('utf-8')
            if 'error' in content.lower():
                print("   ❌ Errores de validación detectados")
            else:
                print("   ✅ Sin errores aparentes")
        else:
            print(f"   ❌ Status inesperado: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Verificar lista de empresas
    print("\n4️⃣ Test: GET /core/empresas/")
    try:
        response = client.get(reverse('core:empresa_listar'))
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Lista de empresas carga correctamente")
            empresas = Empresa.objects.all()
            print(f"   📊 Total de empresas en BD: {empresas.count()}")
            for emp in empresas:
                print(f"      - {emp.nombre} (ID: {emp.id})")
        else:
            print("   ❌ Lista de empresas no carga")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Limpiar datos de prueba
    print("\n5️⃣ Limpiando datos de prueba...")
    try:
        Empresa.objects.filter(nombre__icontains='Test Simple').delete()
        print("   ✅ Empresas de prueba eliminadas")
    except Exception as e:
        print(f"   ❌ Error limpiando: {e}")
    
    print("\n🎉 Test completado!")

if __name__ == "__main__":
    try:
        test_form_simple()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 