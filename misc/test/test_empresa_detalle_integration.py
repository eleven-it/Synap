#!/usr/bin/env python3
"""
Test de integración para el template empresa_detail.html
Verifica que funcione correctamente para crear y editar empresas
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from core.models import Empresa, Country, State, FiscalResponsibility, Currency

User = get_user_model()

class EmpresaDetailIntegrationTest(TestCase):
    
    def setUp(self):
        """Configurar datos de prueba"""
        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # Crear datos de referencia
        self.country = Country.objects.create(
            name='Argentina',
            code='AR',
            active=True
        )
        
        self.state = State.objects.create(
            name='Buenos Aires',
            code='BA',
            country=self.country,
            active=True
        )
        
        self.fiscal_responsibility = FiscalResponsibility.objects.create(
            name='Responsable Inscripto',
            code='RI',
            active=True
        )
        
        self.currency = Currency.objects.create(
            name='Peso Argentino',
            code='ARS',
            symbol='$',
            active=True
        )
        
        # Crear empresa de prueba
        self.empresa = Empresa.objects.create(
            nombre='Empresa Test',
            razon_social='Empresa Test S.A.',
            identificador_fiscal='20-12345678-9',
            country=self.country,
            state=self.state,
            fiscal_responsibility=self.fiscal_responsibility,
            currency=self.currency,
            email='test@empresa.com',
            telefono='123456789',
            activa=True
        )
        
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_crear_empresa_form(self):
        """Test: Verificar que el formulario de crear empresa se renderiza correctamente"""
        print("\n🔍 Test: Formulario de crear empresa")
        
        # Acceder a la URL de crear empresa
        url = reverse('core:empresa_nueva')
        response = self.client.get(url)
        
        # Verificar que la respuesta es exitosa
        self.assertEqual(response.status_code, 200)
        print(f"✅ Status code: {response.status_code}")
        
        # Verificar que el template se renderiza
        self.assertTemplateUsed(response, 'core/system_config/empresa_detail.html')
        print("✅ Template correcto")
        
        # Verificar que está en modo creación
        self.assertTrue(response.context['modo_creacion'])
        print("✅ Modo creación activado")
        
        # Verificar que no hay empresa en el contexto
        self.assertIsNone(response.context['empresa'])
        print("✅ Sin empresa en contexto")
        
        # Verificar que los botones están presentes
        content = response.content.decode()
        self.assertIn('Crear empresa', content)
        self.assertIn('Cancelar', content)
        print("✅ Botones presentes")
    
    def test_editar_empresa_form(self):
        """Test: Verificar que el formulario de editar empresa se renderiza correctamente"""
        print("\n🔍 Test: Formulario de editar empresa")
        
        # Acceder a la URL de editar empresa
        url = reverse('core:empresa_detalle', kwargs={'empresa_id': self.empresa.id})
        response = self.client.get(url)
        
        # Verificar que la respuesta es exitosa
        self.assertEqual(response.status_code, 200)
        print(f"✅ Status code: {response.status_code}")
        
        # Verificar que el template se renderiza
        self.assertTemplateUsed(response, 'core/system_config/empresa_detail.html')
        print("✅ Template correcto")
        
        # Verificar que está en modo edición
        self.assertFalse(response.context['modo_creacion'])
        print("✅ Modo edición activado")
        
        # Verificar que la empresa está en el contexto
        self.assertEqual(response.context['empresa'], self.empresa)
        print("✅ Empresa en contexto")
        
        # Verificar que los campos tienen los valores correctos
        content = response.content.decode()
        self.assertIn(self.empresa.nombre, content)
        self.assertIn(self.empresa.razon_social, content)
        self.assertIn(self.empresa.identificador_fiscal, content)
        print("✅ Campos con valores correctos")
        
        # Verificar que los botones están presentes
        self.assertIn('Guardar cambios', content)
        self.assertIn('Cancelar', content)
        print("✅ Botones presentes")
    
    def test_crear_empresa_post(self):
        """Test: Verificar que se puede crear una empresa via POST"""
        print("\n🔍 Test: Crear empresa via POST")
        
        # Datos para crear empresa
        data = {
            'nombre': 'Nueva Empresa',
            'razon_social': 'Nueva Empresa S.A.',
            'identificador_fiscal': '30-98765432-1',
            'pais_id': self.country.id,
            'state_id': self.state.id,
            'fiscal_responsibility_id': self.fiscal_responsibility.id,
            'currency_id': self.currency.id,
            'email': 'nueva@empresa.com',
            'telefono': '987654321',
            'ciudad': 'CABA',
            'direccion': 'Av. Corrientes 123',
        }
        
        # Enviar POST
        url = reverse('core:empresa_nueva')
        response = self.client.post(url, data)
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        print(f"✅ Status code: {response.status_code}")
        
        # Verificar que redirige a la lista
        self.assertRedirects(response, reverse('core:empresa_listar'))
        print("✅ Redirección correcta")
        
        # Verificar que la empresa se creó
        empresa_creada = Empresa.objects.filter(nombre='Nueva Empresa').first()
        self.assertIsNotNone(empresa_creada)
        print(f"✅ Empresa creada: {empresa_creada.nombre}")
        
        # Verificar que los datos se guardaron correctamente
        self.assertEqual(empresa_creada.razon_social, 'Nueva Empresa S.A.')
        self.assertEqual(empresa_creada.identificador_fiscal, '30-98765432-1')
        self.assertEqual(empresa_creada.country, self.country)
        print("✅ Datos guardados correctamente")
    
    def test_editar_empresa_post(self):
        """Test: Verificar que se puede editar una empresa via POST"""
        print("\n🔍 Test: Editar empresa via POST")
        
        # Datos para editar empresa
        data = {
            'nombre': 'Empresa Modificada',
            'razon_social': 'Empresa Modificada S.A.',
            'identificador_fiscal': '20-12345678-9',
            'pais_id': self.country.id,
            'state_id': self.state.id,
            'fiscal_responsibility_id': self.fiscal_responsibility.id,
            'currency_id': self.currency.id,
            'email': 'modificada@empresa.com',
            'telefono': '111222333',
            'ciudad': 'La Plata',
            'direccion': 'Calle 7 1234',
        }
        
        # Enviar POST
        url = reverse('core:empresa_detalle', kwargs={'empresa_id': self.empresa.id})
        response = self.client.post(url, data)
        
        # Verificar redirección
        self.assertEqual(response.status_code, 302)
        print(f"✅ Status code: {response.status_code}")
        
        # Verificar que redirige a la lista
        self.assertRedirects(response, reverse('core:empresa_listar'))
        print("✅ Redirección correcta")
        
        # Recargar la empresa desde la base de datos
        self.empresa.refresh_from_db()
        
        # Verificar que los datos se actualizaron
        self.assertEqual(self.empresa.nombre, 'Empresa Modificada')
        self.assertEqual(self.empresa.razon_social, 'Empresa Modificada S.A.')
        self.assertEqual(self.empresa.email, 'modificada@empresa.com')
        self.assertEqual(self.empresa.ciudad, 'La Plata')
        print("✅ Datos actualizados correctamente")
    
    def test_cancelar_button(self):
        """Test: Verificar que el botón cancelar funciona correctamente"""
        print("\n🔍 Test: Botón cancelar")
        
        # Acceder al formulario
        url = reverse('core:empresa_nueva')
        response = self.client.get(url)
        
        # Verificar que el botón cancelar está presente y apunta a la lista
        content = response.content.decode()
        self.assertIn('href="/core/empresas/"', content)
        print("✅ Botón cancelar presente y con URL correcta")
        
        # Verificar que el botón cancelar es un enlace (no un botón submit)
        self.assertIn('<a href="/core/empresas/" class="btn-secondary">', content)
        print("✅ Botón cancelar es un enlace")
    
    def test_validation_errors(self):
        """Test: Verificar que se muestran errores de validación"""
        print("\n🔍 Test: Errores de validación")
        
        # Datos incompletos
        data = {
            'nombre': '',  # Campo obligatorio vacío
            'razon_social': 'Test',
            'identificador_fiscal': '',  # Campo obligatorio vacío
        }
        
        # Enviar POST
        url = reverse('core:empresa_nueva')
        response = self.client.post(url, data)
        
        # Verificar que no hay redirección (se queda en el formulario)
        self.assertEqual(response.status_code, 200)
        print(f"✅ Status code: {response.status_code}")
        
        # Verificar que hay error en el contexto
        self.assertIsNotNone(response.context.get('error'))
        print(f"✅ Error en contexto: {response.context['error']}")
        
        # Verificar que el error se muestra en el template
        content = response.content.decode()
        self.assertIn('Faltan campos obligatorios', content)
        print("✅ Error mostrado en template")

if __name__ == '__main__':
    print("🚀 Iniciando tests de integración para empresa_detail.html")
    print("=" * 60)
    
    # Ejecutar tests
    import unittest
    unittest.main(argv=[''], exit=False, verbosity=2) 