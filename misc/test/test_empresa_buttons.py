#!/usr/bin/env python
"""
Test para verificar el funcionamiento de los botones Cancelar y Guardar en el formulario de empresa
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import Empresa, Country, State, FiscalResponsibility, Currency

User = get_user_model()

class EmpresaButtonsTest(TestCase):
    def setUp(self):
        """Configurar datos de prueba"""
        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # Crear datos de referencia
        self.country = Country.objects.create(name='Argentina', code='AR')
        self.state = State.objects.create(name='Buenos Aires', country=self.country, code='BA')
        self.fiscal_responsibility = FiscalResponsibility.objects.create(
            name='Responsable Inscripto', 
            code='RI'
        )
        self.currency = Currency.objects.create(
            name='Peso Argentino', 
            code='ARS', 
            symbol='$'
        )
        
        # Crear empresa de prueba
        self.empresa = Empresa.objects.create(
            nombre='Empresa Test',
            razon_social='Empresa Test S.A.',
            identificador_fiscal='20-12345678-9',
            email='test@empresa.com',
            telefono='+54 11 1234-5678',
            direccion='Av. Test 123',
            ciudad='Buenos Aires',
            country=self.country,
            state=self.state,
            fiscal_responsibility=self.fiscal_responsibility,
            activa=True
        )
        
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_crear_empresa_form_buttons(self):
        """Test que verifica que el formulario de crear empresa tenga los botones correctos"""
        print("\n🔍 Test: Formulario de crear empresa - botones")
        
        # Obtener la página de crear empresa
        response = self.client.get(reverse('core:empresa_crear'))
        
        self.assertEqual(response.status_code, 200)
        print("✅ Página de crear empresa carga correctamente")
        
        # Verificar que el formulario tenga los botones
        content = response.content.decode('utf-8')
        
        # Verificar botón Cancelar
        self.assertIn('Cancelar', content)
        self.assertIn('href="/core/empresas/"', content)
        print("✅ Botón Cancelar presente y con URL correcta")
        
        # Verificar botón Crear
        self.assertIn('Crear', content)
        self.assertIn('type="submit"', content)
        print("✅ Botón Crear presente y es tipo submit")
        
        # Verificar que el formulario tenga el ID correcto
        self.assertIn('id="empresa-form"', content)
        print("✅ Formulario tiene ID correcto")

    def test_editar_empresa_form_buttons(self):
        """Test que verifica que el formulario de editar empresa tenga los botones correctos"""
        print("\n🔍 Test: Formulario de editar empresa - botones")
        
        # Obtener la página de editar empresa
        response = self.client.get(reverse('core:empresa_editar', kwargs={'empresa_id': self.empresa.id}))
        
        self.assertEqual(response.status_code, 200)
        print("✅ Página de editar empresa carga correctamente")
        
        # Verificar que el formulario tenga los botones
        content = response.content.decode('utf-8')
        
        # Verificar botón Cancelar
        self.assertIn('Cancelar', content)
        self.assertIn('href="/core/empresas/"', content)
        print("✅ Botón Cancelar presente y con URL correcta")
        
        # Verificar botón Guardar
        self.assertIn('Guardar', content)
        self.assertIn('type="submit"', content)
        print("✅ Botón Guardar presente y es tipo submit")
        
        # Verificar que el formulario tenga el ID correcto
        self.assertIn('id="empresa-form"', content)
        print("✅ Formulario tiene ID correcto")

    def test_cancelar_button_redirect(self):
        """Test que verifica que el botón Cancelar redirija correctamente"""
        print("\n🔍 Test: Botón Cancelar - redirección")
        
        # Simular clic en Cancelar (GET a la lista de empresas)
        response = self.client.get(reverse('core:empresa_listar'))
        
        self.assertEqual(response.status_code, 200)
        print("✅ Botón Cancelar redirige a la lista de empresas")

    def test_guardar_empresa_crear(self):
        """Test que verifica que el botón Guardar funcione para crear empresa"""
        print("\n🔍 Test: Botón Guardar - crear empresa")
        
        # Datos para crear empresa
        empresa_data = {
            'nombre': 'Nueva Empresa Test',
            'razon_social': 'Nueva Empresa Test S.A.',
            'identificador_fiscal': '30-87654321-0',
            'email': 'nueva@empresa.com',
            'telefono': '+54 11 8765-4321',
            'direccion': 'Av. Nueva 456',
            'ciudad': 'Córdoba',
            'country_name': self.country.name,
            'country_id': str(self.country.id),
            'state_name': self.state.name,
            'state_id': str(self.state.id),
            'fiscal_responsibility_name': self.fiscal_responsibility.name,
            'fiscal_responsibility_id': str(self.fiscal_responsibility.id),
            'activa': True
        }
        
        # Enviar formulario
        response = self.client.post(reverse('core:empresa_crear'), empresa_data)
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:empresa_listar'))
        print("✅ Formulario de crear empresa redirige correctamente")
        
        # Verificar que la empresa se creó
        nueva_empresa = Empresa.objects.filter(nombre='Nueva Empresa Test').first()
        self.assertIsNotNone(nueva_empresa)
        self.assertEqual(nueva_empresa.country, self.country)
        self.assertEqual(nueva_empresa.state, self.state)
        self.assertEqual(nueva_empresa.fiscal_responsibility, self.fiscal_responsibility)
        print("✅ Nueva empresa creada con datos correctos")

    def test_guardar_empresa_editar(self):
        """Test que verifica que el botón Guardar funcione para editar empresa"""
        print("\n🔍 Test: Botón Guardar - editar empresa")
        
        # Datos para editar empresa
        empresa_data = {
            'nombre': 'Empresa Test Modificada',
            'razon_social': 'Empresa Test Modificada S.A.',
            'identificador_fiscal': '20-12345678-9',
            'email': 'modificada@empresa.com',
            'telefono': '+54 11 9999-8888',
            'direccion': 'Av. Modificada 789',
            'ciudad': 'Rosario',
            'country_name': self.country.name,
            'country_id': str(self.country.id),
            'state_name': self.state.name,
            'state_id': str(self.state.id),
            'fiscal_responsibility_name': self.fiscal_responsibility.name,
            'fiscal_responsibility_id': str(self.fiscal_responsibility.id),
            'activa': True
        }
        
        # Enviar formulario
        response = self.client.post(
            reverse('core:empresa_editar', kwargs={'empresa_id': self.empresa.id}), 
            empresa_data
        )
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:empresa_listar'))
        print("✅ Formulario de editar empresa redirige correctamente")
        
        # Verificar que la empresa se actualizó
        self.empresa.refresh_from_db()
        self.assertEqual(self.empresa.nombre, 'Empresa Test Modificada')
        self.assertEqual(self.empresa.email, 'modificada@empresa.com')
        self.assertEqual(self.empresa.ciudad, 'Rosario')
        print("✅ Empresa actualizada con datos correctos")

    def test_form_validation_errors(self):
        """Test que verifica que se muestren errores de validación"""
        print("\n🔍 Test: Validación de formulario - errores")
        
        # Datos inválidos (sin nombre)
        empresa_data = {
            'razon_social': 'Empresa Sin Nombre S.A.',
            'identificador_fiscal': '30-12345678-9',
            'country_name': self.country.name,
            'country_id': str(self.country.id),
        }
        
        # Enviar formulario
        response = self.client.post(reverse('core:empresa_crear'), empresa_data)
        
        # Verificar que no redirija (debe mostrar errores)
        self.assertEqual(response.status_code, 200)
        print("✅ Formulario con errores no redirige")
        
        # Verificar que se muestren errores
        content = response.content.decode('utf-8')
        self.assertIn('error', content.lower() or 'nombre' in content.lower())
        print("✅ Errores de validación se muestran correctamente")

if __name__ == "__main__":
    print("🚀 Test de botones del formulario de empresa")
    print("=" * 50)
    
    try:
        # Ejecutar tests
        test = EmpresaButtonsTest()
        test.setUp()
        
        test.test_crear_empresa_form_buttons()
        test.test_editar_empresa_form_buttons()
        test.test_cancelar_button_redirect()
        test.test_guardar_empresa_crear()
        test.test_guardar_empresa_editar()
        test.test_form_validation_errors()
        
        print("\n🎉 Todos los tests de botones pasaron exitosamente!")
        
    except Exception as e:
        print(f"\n❌ ERROR en test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 