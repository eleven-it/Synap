from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.apps import apps
from decimal import Decimal
from core.models import Empresa, Branch, UsuarioExtendido
from sales.models import POSTerminal, PriceList, Client

User = get_user_model()

class Command(BaseCommand):
    help = 'Configurar datos de prueba para el TPV (Terminal de Punto de Venta)'

    def handle(self, *args, **options):
        self.stdout.write("🚀 Configurando datos de prueba para el TPV...")
        
        with transaction.atomic():
            # Obtener empresa
            empresa = Empresa.objects.first()
            if not empresa:
                self.stdout.write(self.style.ERROR("❌ No se encontró empresa. Ejecute primero setup_core_data"))
                return
            
            self.stdout.write(f"🏢 Usando empresa: {empresa.name}")
            
            # Obtener sucursal
            branch = Branch.objects.filter(empresa=empresa).first()
            if not branch:
                self.stdout.write(self.style.ERROR("❌ No se encontró sucursal. Ejecute primero setup_core_data"))
                return
            
            self.stdout.write(f"🏪 Usando sucursal: {branch.name}")
            
            # Obtener usuario
            user = User.objects.filter(is_staff=True).first()
            if not user:
                self.stdout.write(self.style.ERROR("❌ No se encontró usuario. Ejecute primero setup_core_data"))
                return
            
            # Crear o obtener UsuarioExtendido
            user_extended, created = UsuarioExtendido.objects.get_or_create(
                uid=user.uid if hasattr(user, 'uid') else str(user.id),
                defaults={
                    'email': user.email,
                    'nombre': getattr(user, 'nombre', None) or getattr(user, 'username', None) or user.email,
                    'default_branch': branch
                }
            )
            
            if created:
                self.stdout.write(f"👤 UsuarioExtendido creado: {user_extended.email}")
            else:
                self.stdout.write(f"👤 UsuarioExtendido existente: {user_extended.email}")
            
            # Crear terminal de punto de venta
            terminal, created = POSTerminal.objects.get_or_create(
                branch=branch,
                code='TPV001',
                defaults={
                    'name': 'Terminal Principal',
                    'is_active': True,
                    'barcode_scanner': True,
                    'scale_integration': False
                }
            )
            
            if created:
                self.stdout.write(f"💻 Terminal creado: {terminal.name}")
            else:
                self.stdout.write(f"💻 Terminal existente: {terminal.name}")
            
            # Crear lista de precios
            price_list, created = PriceList.objects.get_or_create(
                name='Lista de Precios General',
                defaults={
                    'currency': 'ARS',
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f"💰 Lista de precios creada: {price_list.name}")
            else:
                self.stdout.write(f"💰 Lista de precios existente: {price_list.name}")
            
            # Crear cliente ocasional
            client, created = Client.objects.get_or_create(
                name='Cliente Ocasional',
                defaults={
                    'type': 'individual',
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f"👥 Cliente ocasional creado: {client.name}")
            else:
                self.stdout.write(f"👥 Cliente ocasional existente: {client.name}")
            
            # Crear cuentas contables básicas si el módulo accounting está disponible
            if apps.is_installed('accounting'):
                from accounting.models import ChartOfAccounts
                
                self.stdout.write("📊 Configurando cuentas contables básicas...")
                
                # Cuenta de ventas
                sales_account, created = ChartOfAccounts.objects.get_or_create(
                    empresa=empresa,
                    code='4001-TPV',
                    defaults={
                        'name': 'Ventas de Mercaderías TPV',
                        'account_type': 'income',
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(f"  ✅ Cuenta de ventas creada: {sales_account.code} - {sales_account.name}")
                else:
                    self.stdout.write(f"  ℹ️  Cuenta de ventas existente: {sales_account.code} - {sales_account.name}")
                
                # Cuenta de caja
                cash_account, created = ChartOfAccounts.objects.get_or_create(
                    empresa=empresa,
                    code='1101-TPV',
                    defaults={
                        'name': 'Caja TPV',
                        'account_type': 'assets',
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(f"  ✅ Cuenta de caja creada: {cash_account.code} - {cash_account.name}")
                else:
                    self.stdout.write(f"  ℹ️  Cuenta de caja existente: {cash_account.code} - {cash_account.name}")
                
                # Cuenta de IVA
                vat_account, created = ChartOfAccounts.objects.get_or_create(
                    empresa=empresa,
                    code='2101-TPV',
                    defaults={
                        'name': 'IVA Responsable Inscripto TPV',
                        'account_type': 'liabilities',
                        'is_active': True,
                        'is_tax_account': True,
                        'tax_type': 'vat'
                    }
                )
                if created:
                    self.stdout.write(f"  ✅ Cuenta de IVA creada: {vat_account.code} - {vat_account.name}")
                else:
                    self.stdout.write(f"  ℹ️  Cuenta de IVA existente: {vat_account.code} - {vat_account.name}")
                
                # Cuenta de costo de ventas
                cogs_account, created = ChartOfAccounts.objects.get_or_create(
                    empresa=empresa,
                    code='5101-TPV',
                    defaults={
                        'name': 'Costo de Ventas TPV',
                        'account_type': 'expenses',
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(f"  ✅ Cuenta de costo de ventas creada: {cogs_account.code} - {cogs_account.name}")
                else:
                    self.stdout.write(f"  ℹ️  Cuenta de costo de ventas existente: {cogs_account.code} - {cogs_account.name}")
                
                self.stdout.write("✅ Cuentas contables básicas configuradas")
            else:
                self.stdout.write("⚠️  Módulo de contabilidad no disponible - saltando configuración de cuentas")
            
            self.stdout.write(self.style.SUCCESS("🎉 Configuración del TPV completada exitosamente!"))
            self.stdout.write("📋 Resumen de configuración:")
            self.stdout.write(f"  • Terminal: {terminal.name} ({terminal.code})")
            self.stdout.write(f"  • Lista de precios: {price_list.name}")
            self.stdout.write(f"  • Cliente ocasional: {client.name}")
            if apps.is_installed('accounting'):
                self.stdout.write(f"  • Cuentas contables: 4 cuentas básicas creadas")
            self.stdout.write("")
            self.stdout.write("🚀 El TPV está listo para usar. Ejecute 'python test_tpv_functionality.py' para verificar la funcionalidad.") 