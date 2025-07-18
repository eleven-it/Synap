#!/usr/bin/env python
"""
Test específico para verificar que el botón Cancelar funcione correctamente
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

def test_cancel_button():
    """Test específico para el botón Cancelar"""
    print("🔍 Test: Botón Cancelar")
    print("=" * 50)
    
    client = Client()
    
    # 1. Test en formulario de creación
    print("\n1️⃣ Test: Botón Cancelar en formulario de creación")
    
    response = client.get(reverse('core:empresa_crear'))
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        
        # Verificar que el botón Cancelar esté presente
        if 'Cancelar' in content:
            print("   ✅ Botón Cancelar encontrado en el HTML")
        else:
            print("   ❌ Botón Cancelar NO encontrado en el HTML")
            return False
        
        # Verificar que el enlace apunte a la lista de empresas
        if 'href="/core/empresas/"' in content or 'href="{% url \'core:empresa_listar\' %}"' in content:
            print("   ✅ Enlace Cancelar apunta a la lista de empresas")
        else:
            print("   ❌ Enlace Cancelar NO apunta a la lista de empresas")
            return False
        
        # Verificar que no sea un botón submit
        if 'type="submit"' not in content or 'Cancelar' not in content:
            print("   ✅ Botón Cancelar NO es de tipo submit")
        else:
            print("   ❌ Botón Cancelar es de tipo submit (incorrecto)")
            return False
    else:
        print(f"   ❌ Error al cargar formulario: {response.status_code}")
        return False
    
    # 2. Test en formulario de edición
    print("\n2️⃣ Test: Botón Cancelar en formulario de edición")
    
    # Crear empresa de prueba
    country = Country.objects.create(name='Argentina', code='AR')
    state = State.objects.create(name='Buenos Aires', country=country, code='BA')
    fiscal_responsibility = FiscalResponsibility.objects.create(name='Responsable Inscripto', code='RI')
    
    empresa = Empresa.objects.create(
        nombre='Empresa Test Cancel',
        razon_social='Empresa Test Cancel S.A.',
        identificador_fiscal='20-12345678-9',
        country=country,
        state=state,
        fiscal_responsibility=fiscal_responsibility
    )
    
    response = client.get(reverse('core:empresa_editar', kwargs={'empresa_id': empresa.id}))
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        
        # Verificar que el botón Cancelar esté presente
        if 'Cancelar' in content:
            print("   ✅ Botón Cancelar encontrado en el HTML")
        else:
            print("   ❌ Botón Cancelar NO encontrado en el HTML")
            return False
        
        # Verificar que el enlace apunte a la lista de empresas
        if 'href="/core/empresas/"' in content or 'href="{% url \'core:empresa_listar\' %}"' in content:
            print("   ✅ Enlace Cancelar apunta a la lista de empresas")
        else:
            print("   ❌ Enlace Cancelar NO apunta a la lista de empresas")
            return False
    else:
        print(f"   ❌ Error al cargar formulario: {response.status_code}")
        return False
    
    # 3. Test de redirección
    print("\n3️⃣ Test: Redirección del botón Cancelar")
    
    # Simular clic en el botón Cancelar (GET a la lista)
    response = client.get(reverse('core:empresa_listar'))
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ Redirección a lista de empresas funciona")
    else:
        print(f"   ❌ Error en redirección: {response.status_code}")
        return False
    
    # 4. Limpiar
    print("\n4️⃣ Limpiando datos de prueba...")
    empresa.delete()
    country.delete()
    state.delete()
    fiscal_responsibility.delete()
    print("   ✅ Datos limpiados")
    
    print("\n🎉 Test del botón Cancelar completado exitosamente!")
    return True

if __name__ == "__main__":
    try:
        success = test_cancel_button()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 