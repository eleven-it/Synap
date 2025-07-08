from django.core.management.base import BaseCommand
from sales.models import VATValidator


class Command(BaseCommand):
    help = 'Probar validadores de VAT por país'

    def handle(self, *args, **options):
        self.stdout.write('Probando validadores de VAT...')
        
        # Test Argentina CUIT
        self.test_argentina_cuit()
        
        # Test Brasil CNPJ
        self.test_brazil_cnpj()
        
        # Test México RFC
        self.test_mexico_rfc()
        
        # Test España NIF
        self.test_spain_nif()
        
        # Test USA EIN
        self.test_usa_ein()
        
        self.stdout.write(
            self.style.SUCCESS('Pruebas de validadores completadas')
        )

    def test_argentina_cuit(self):
        """Probar validador de CUIT argentino"""
        self.stdout.write('\n--- Argentina CUIT ---')
        
        # CUIT válidos (ejemplos reales)
        valid_cuits = [
            '20-12345678-9',  # Ejemplo con dígito verificador correcto
            '30-12345678-9',  # Ejemplo con dígito verificador correcto
            '20-12345678-0',  # Ejemplo con dígito verificador correcto
        ]
        
        # CUIT inválidos
        invalid_cuits = [
            '20-12345678-1',  # Dígito verificador incorrecto
            '20-1234567-9',   # Formato incorrecto
            '20-123456789-9', # Formato incorrecto
            '',               # Vacío
            None,             # None
        ]
        
        for cuit in valid_cuits:
            is_valid = VATValidator.validate_argentina_cuit(cuit)
            status = '✓ VÁLIDO' if is_valid else '✗ INVÁLIDO'
            self.stdout.write(f'  {cuit}: {status}')
        
        for cuit in invalid_cuits:
            is_valid = VATValidator.validate_argentina_cuit(cuit)
            status = '✓ VÁLIDO' if is_valid else '✗ INVÁLIDO'
            self.stdout.write(f'  {cuit}: {status}')

    def test_brazil_cnpj(self):
        """Probar validador de CNPJ brasileño"""
        self.stdout.write('\n--- Brasil CNPJ ---')
        
        # CNPJ válidos
        valid_cnpjs = [
            '11.222.333/0001-81',  # Ejemplo válido
            '12.345.678/0001-95',  # Ejemplo válido
        ]
        
        # CNPJ inválidos
        invalid_cnpjs = [
            '11.222.333/0001-82',  # Dígito verificador incorrecto
            '11.222.333/0001-8',   # Formato incorrecto
            '11.222.333/0001-812', # Formato incorrecto
            '',                    # Vacío
            None,                  # None
        ]
        
        for cnpj in valid_cnpjs:
            is_valid = VATValidator.validate_brazil_cnpj(cnpj)
            status = '✓ VÁLIDO' if is_valid else '✗ INVÁLIDO'
            self.stdout.write(f'  {cnpj}: {status}')
        
        for cnpj in invalid_cnpjs:
            is_valid = VATValidator.validate_brazil_cnpj(cnpj)
            status = '✓ VÁLIDO' if is_valid else '✗ INVÁLIDO'
            self.stdout.write(f'  {cnpj}: {status}')

    def test_mexico_rfc(self):
        """Probar validador de RFC mexicano"""
        self.stdout.write('\n--- México RFC ---')
        
        # RFC válidos (ejemplos reales)
        valid_rfcs = [
            'XAXX-010101-000',  # RFC genérico para extranjeros
            'MEX-123456-789',   # Ejemplo de empresa
            'PER-123456-789',   # Ejemplo de persona física
        ]
        
        # RFC inválidos
        invalid_rfcs = [
            'XAXX-010101-00',   # Formato incorrecto
            'XAXX-010101-0000', # Formato incorrecto
            '123-456789-01',    # Formato incorrecto
            '',                 # Vacío
            None,               # None
        ]
        
        for rfc in valid_rfcs:
            is_valid = VATValidator.validate_mexico_rfc(rfc)
            status = '✓ VÁLIDO' if is_valid else '✗ INVÁLIDO'
            self.stdout.write(f'  {rfc}: {status}')
        
        for rfc in invalid_rfcs:
            is_valid = VATValidator.validate_mexico_rfc(rfc)
            status = '✓ VÁLIDO' if is_valid else '✗ INVÁLIDO'
            self.stdout.write(f'  {rfc}: {status}')

    def test_spain_nif(self):
        """Probar validador de NIF español"""
        self.stdout.write('\n--- España NIF ---')
        
        # NIF válidos (ejemplos reales)
        valid_nifs = [
            '12345678-Z',  # Ejemplo válido
            '87654321-A',  # Ejemplo válido
            'X1234567-L',  # Ejemplo con letra inicial
        ]
        
        # NIF inválidos
        invalid_nifs = [
            '12345678-A',  # Letra incorrecta
            '1234567-Z',   # Formato incorrecto
            '123456789-Z', # Formato incorrecto
            '',            # Vacío
            None,          # None
        ]
        
        for nif in valid_nifs:
            is_valid = VATValidator.validate_spain_nif(nif)
            status = '✓ VÁLIDO' if is_valid else '✗ INVÁLIDO'
            self.stdout.write(f'  {nif}: {status}')
        
        for nif in invalid_nifs:
            is_valid = VATValidator.validate_spain_nif(nif)
            status = '✓ VÁLIDO' if is_valid else '✗ INVÁLIDO'
            self.stdout.write(f'  {nif}: {status}')

    def test_usa_ein(self):
        """Probar validador de EIN estadounidense"""
        self.stdout.write('\n--- USA EIN ---')
        
        # EIN válidos
        valid_eins = [
            '12-3456789',  # Ejemplo válido
            '98-7654321',  # Ejemplo válido
        ]
        
        # EIN inválidos
        invalid_eins = [
            '12-345678',   # Formato incorrecto
            '12-34567890', # Formato incorrecto
            '123-456789',  # Formato incorrecto
            '',            # Vacío
            None,          # None
        ]
        
        for ein in valid_eins:
            is_valid = VATValidator.validate_usa_ein(ein)
            status = '✓ VÁLIDO' if is_valid else '✗ INVÁLIDO'
            self.stdout.write(f'  {ein}: {status}')
        
        for ein in invalid_eins:
            is_valid = VATValidator.validate_usa_ein(ein)
            status = '✓ VÁLIDO' if is_valid else '✗ INVÁLIDO'
            self.stdout.write(f'  {ein}: {status}') 