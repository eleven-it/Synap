#!/usr/bin/env python
"""
Script simple para probar la creación de empresa con país
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from core.models import Empresa, Country, State, FiscalResponsibility
from core.models.currency import Currency

def test_simple_empresa():
    print("🧪 PRUEBA SIMPLE DE CREACIÓN DE EMPRESA")
    print("=" * 50)
    
    # Crear cliente de prueba
    client = Client()
    
    # Crear usuario de prueba
    User = get_user_model()
    user = User.objects.create_user(
        email='test@test.com',
        password='testpass123',
        nombre='Usuario Test'
    )
    
    # Autenticar usuario
    client.force_login(user)
    
    # Buscar datos de prueba
    country = Country.objects.filter(name__icontains='argentina').first()
    state = State.objects.filter(name__icontains='mendoza').first()
    fiscal_responsibility = FiscalResponsibility.objects.filter(name__icontains='inscripto').first()
    
    print(f"📊 Datos encontrados:")
    print(f"   - País: {country.name if country else 'No encontrado'} (ID: {country.id if country else 'N/A'})")
    print(f"   - Provincia: {state.name if state else 'No encontrado'} (ID: {state.id if state else 'N/A'})")
    print(f"   - Responsabilidad: {fiscal_responsibility.name if fiscal_responsibility else 'No encontrado'} (ID: {fiscal_responsibility.id if fiscal_responsibility else 'N/A'})")
    
    if not country or not state or not fiscal_responsibility:
        print("❌ Faltan datos de prueba. No se puede continuar.")
        return
    
    # Datos para crear empresa
    empresa_data = {
        'nombre': 'Empresa Test Simple',
        'razon_social': 'Empresa Test Simple S.A.',
        'identificador_fiscal': '20-12345678-9',
        'email': 'test@empresa.com',
        'telefono': '+54 11 1234-5678',
        'direccion': 'Calle Test 123',
        'country_name': country.name,
        'country_id': str(country.id),
        'state_id': str(state.id),
        'fiscal_responsibility_id': str(fiscal_responsibility.id),
        'ciudad': 'Buenos Aires',
        'activa': True
    }
    
    # Eliminar empresa de prueba si existe
    Empresa.objects.filter(nombre='Empresa Test Simple').delete()
    
    print(f"\n📝 Creando empresa con datos:")
    for key, value in empresa_data.items():
        print(f"   - {key}: {value}")
    
    # Crear empresa
    response = client.post('/core/empresas/nueva/', empresa_data, follow=True)
    
    print(f"\n📊 Resultado:")
    print(f"   - Status: {response.status_code}")
    
    # Verificar empresa creada
    empresa = Empresa.objects.filter(nombre='Empresa Test Simple').first()
    if empresa:
        print(f"   - Empresa creada: {empresa.nombre} (ID: {empresa.id})")
        print(f"   - País (FK): {empresa.country.name if empresa.country else 'None'} (ID: {empresa.country.id if empresa.country else 'None'})")
        print(f"   - País legacy: {empresa.pais}")
        print(f"   - Provincia: {empresa.state}")
        print(f"   - Responsabilidad: {empresa.fiscal_responsibility}")
        
        # Verificar que el país se asignó correctamente
        if empresa.country is not None:
            print("✅ ÉXITO: El país se asignó correctamente")
            assert empresa.country.id == country.id, f"ID de país incorrecto: esperado {country.id}, obtenido {empresa.country.id}"
        else:
            print("❌ ERROR: El país no se asignó")
            assert False, "El país no se asignó correctamente"
    else:
        print("❌ ERROR: La empresa no se creó")
        assert False, "La empresa no se creó"
    
    # Limpiar
    if empresa:
        empresa.delete()
    user.delete()
    
    print("\n🎉 Prueba completada exitosamente!")

if __name__ == "__main__":
    try:
        test_simple_empresa()
    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        print(traceback.format_exc())
        sys.exit(1) 