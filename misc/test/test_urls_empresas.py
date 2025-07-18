#!/usr/bin/env python3
"""
Test rápido para verificar que las URLs de empresas funcionan
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from core.models import Empresa, Country, State, FiscalResponsibility, Currency

class EmpresaURLsTest(TestCase):
    
    def setUp(self):
        """Configurar datos de prueba"""
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
    
    def test_empresa_listar_url(self):
        """Test: URL de listar empresas"""
        print("\n🔍 Test: URL empresa_listar")
        try:
            url = reverse('core:empresa_listar')
            print(f"✅ URL generada: {url}")
            self.assertEqual(url, '/core/empresas/')
        except NoReverseMatch as e:
            print(f"❌ Error: {e}")
            self.fail(f"URL empresa_listar no encontrada: {e}")
    
    def test_empresa_nueva_url(self):
        """Test: URL de crear empresa"""
        print("\n🔍 Test: URL empresa_nueva")
        try:
            url = reverse('core:empresa_nueva')
            print(f"✅ URL generada: {url}")
            self.assertEqual(url, '/core/empresas/nueva/')
        except NoReverseMatch as e:
            print(f"❌ Error: {e}")
            self.fail(f"URL empresa_nueva no encontrada: {e}")
    
    def test_empresa_detalle_url(self):
        """Test: URL de editar empresa"""
        print("\n🔍 Test: URL empresa_detalle")
        try:
            url = reverse('core:empresa_detalle', kwargs={'empresa_id': self.empresa.id})
            print(f"✅ URL generada: {url}")
            self.assertEqual(url, f'/core/empresas/{self.empresa.id}/detalle/')
        except NoReverseMatch as e:
            print(f"❌ Error: {e}")
            self.fail(f"URL empresa_detalle no encontrada: {e}")
    
    def test_empresa_eliminar_url(self):
        """Test: URL de eliminar empresa"""
        print("\n🔍 Test: URL empresa_eliminar")
        try:
            url = reverse('core:empresa_eliminar', kwargs={'empresa_id': self.empresa.id})
            print(f"✅ URL generada: {url}")
            self.assertEqual(url, f'/core/empresas/{self.empresa.id}/eliminar/')
        except NoReverseMatch as e:
            print(f"❌ Error: {e}")
            self.fail(f"URL empresa_eliminar no encontrada: {e}")
    
    def test_branch_list_url(self):
        """Test: URL de listar sucursales"""
        print("\n🔍 Test: URL branch_list")
        try:
            url = reverse('core:branch_list', kwargs={'empresa_id': self.empresa.id})
            print(f"✅ URL generada: {url}")
            self.assertEqual(url, f'/core/empresas/{self.empresa.id}/sucursales/')
        except NoReverseMatch as e:
            print(f"❌ Error: {e}")
            self.fail(f"URL branch_list no encontrada: {e}")
    
    def test_branch_create_url(self):
        """Test: URL de crear sucursal"""
        print("\n🔍 Test: URL branch_create")
        try:
            url = reverse('core:branch_create', kwargs={'empresa_id': self.empresa.id})
            print(f"✅ URL generada: {url}")
            self.assertEqual(url, f'/core/empresas/{self.empresa.id}/sucursales/nueva/')
        except NoReverseMatch as e:
            print(f"❌ Error: {e}")
            self.fail(f"URL branch_create no encontrada: {e}")
    
    def test_cambiar_empresa_branch_url(self):
        """Test: URL de cambiar empresa/branch"""
        print("\n🔍 Test: URL cambiar_empresa_branch")
        try:
            url = reverse('core:cambiar_empresa_branch')
            print(f"✅ URL generada: {url}")
            self.assertEqual(url, '/core/cambiar-empresa-branch/')
        except NoReverseMatch as e:
            print(f"❌ Error: {e}")
            self.fail(f"URL cambiar_empresa_branch no encontrada: {e}")

if __name__ == '__main__':
    print("🚀 Iniciando tests de URLs de empresas")
    print("=" * 50)
    
    # Ejecutar tests
    import unittest
    unittest.main(argv=[''], exit=False, verbosity=2) 