"""
Modelo troncal para responsabilidades fiscales oficiales por país
Centraliza la gestión de tipos de contribuyentes según la legislación de cada país
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator
from .models import Country


class FiscalResponsibility(models.Model):
    """
    Responsabilidades fiscales oficiales por país
    Define los tipos de contribuyentes según la legislación fiscal de cada país
    """
    
    # Tipos de responsabilidad por país
    RESPONSIBILITY_TYPES = {
        'AR': {  # Argentina (AFIP)
            'RI': 'Responsable Inscripto',
            'RM': 'Responsable Monotributista', 
            'CF': 'Consumidor Final',
            'EX': 'Exento',
            'NR': 'No Responsable',
            'RNI': 'Responsable No Inscripto',
            'SR': 'Sujeto a Retención',
            'SP': 'Sujeto a Percepción',
            'RIVA': 'Responsable IVA Agropecuario',
            'PCE': 'Pequeño Contribuyente Eventual',
        },
        'CL': {  # Chile (SII)
            'RPG': 'Régimen Pro Pyme General',
            'RPT': 'Régimen Pro Pyme Transparente',
            'RG': 'Régimen General (Artículo 14 A)',
            'RRP': 'Régimen de Renta Presunta',
            'RRA': 'Régimen de Renta Atribuida',
            'CSC': 'Contribuyente de Segunda Categoría',
            'EX': 'Exento',
        },
        'UY': {  # Uruguay (DGI)
            'RG': 'Régimen General',
            'RM': 'Régimen de Monotributo',
            'RPE': 'Régimen de Pequeños Empresarios',
            'EX': 'Exento',
            'CF': 'Consumidor Final',
        },
        'PY': {  # Paraguay (SET)
            'RG': 'Régimen General',
            'RM': 'Régimen de Microempresa',
            'RPE': 'Régimen de Pequeños Empresarios',
            'EX': 'Exento',
            'CF': 'Consumidor Final',
        },
        'BR': {  # Brasil (Receita Federal)
            'PJ': 'Pessoa Jurídica',
            'PF': 'Pessoa Física',
            'MEI': 'Microempreendedor Individual',
            'SN': 'Simples Nacional',
            'LP': 'Lucro Presumido',
            'LR': 'Lucro Real',
            'EX': 'Isento',
        },
        'US': {  # USA (IRS)
            'IND': 'Individual',
            'CORP': 'Corporation',
            'LLC': 'Limited Liability Company',
            'PART': 'Partnership',
            'S_CORP': 'S Corporation',
            'TRUST': 'Trust',
            'ESTATE': 'Estate',
            'NON_PROFIT': 'Non-Profit Organization',
            'EXEMPT': 'Tax Exempt',
        },
        'ES': {  # España (AEAT)
            'RG': 'Régimen General',
            'RA': 'Régimen de Autónomos',
            'RS': 'Régimen Simplificado',
            'RE': 'Régimen Especial',
            'EX': 'Exento',
            'CF': 'Consumidor Final',
        }
    }
    
    name = models.CharField(
        max_length=100,
        verbose_name=_("Nombre"),
        help_text=_("Nombre oficial de la responsabilidad fiscal")
    )
    
    code = models.CharField(
        max_length=10,
        verbose_name=_("Código"),
        help_text=_("Código oficial de la responsabilidad fiscal"),
        validators=[MinLengthValidator(2)]
    )
    
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        verbose_name=_("País"),
        help_text=_("País al que pertenece esta responsabilidad fiscal")
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Descripción"),
        help_text=_("Descripción detallada de la responsabilidad fiscal")
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Activo"),
        help_text=_("Indica si esta responsabilidad fiscal está activa")
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Fecha de creación")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Fecha de actualización")
    )
    
    class Meta:
        verbose_name = _("Responsabilidad Fiscal")
        verbose_name_plural = _("Responsabilidades Fiscales")
        unique_together = ['code', 'country']
        ordering = ['country', 'name']
        db_table = 'core_fiscal_responsibility'
    
    def __str__(self):
        return f"{self.name} ({self.country.name})"
    
    def get_localized_name(self):
        """Retorna el nombre en el idioma del usuario"""
        return self.name
    
    @classmethod
    def get_by_country(cls, country_code):
        """Obtiene las responsabilidades fiscales activas de un país"""
        return cls.objects.filter(
            country__code=country_code,
            is_active=True
        ).order_by('name')
    
    @classmethod
    def get_by_country_name(cls, country_name):
        """Obtiene las responsabilidades fiscales activas de un país por nombre"""
        return cls.objects.filter(
            country__name__iexact=country_name,
            is_active=True
        ).order_by('name')
    
    @classmethod
    def populate_official_responsibilities(cls):
        """Pobla las responsabilidades fiscales oficiales de todos los países"""
        from django.db import transaction
        
        with transaction.atomic():
            for country_code, responsibilities in cls.RESPONSIBILITY_TYPES.items():
                try:
                    country = Country.objects.get(code=country_code)
                    
                    for code, name in responsibilities.items():
                        cls.objects.get_or_create(
                            code=code,
                            country=country,
                            defaults={
                                'name': name,
                                'description': f'Responsabilidad fiscal oficial de {country.name}',
                                'is_active': True
                            }
                        )
                        
                except Country.DoesNotExist:
                    print(f"País {country_code} no encontrado en la base de datos")
                    continue 