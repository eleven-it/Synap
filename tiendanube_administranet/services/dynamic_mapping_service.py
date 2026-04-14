"""
Servicio para manejar mapeos dinámicos de campos entre Tiendanube y AdministraNET.
"""

import logging
from typing import Dict, List, Any, Optional
from django.utils.translation import gettext as _

from ..models import FieldMappingConfig

logger = logging.getLogger(__name__)


class DynamicMappingService:
    """
    Servicio para manejar mapeos dinámicos de campos.
    Permite configurar y aplicar mapeos sin modificar código.
    """
    
    def __init__(self):
        self._cache = {}
    
    def get_field_mappings(self, mapping_type: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Obtener todos los mapeos de campos para un tipo específico.
        Retorna un diccionario con campos de AdministraNET y Tiendanube.
        """
        cache_key = f"mappings_{mapping_type}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Obtener campos de AdministraNET
        adminet_fields = FieldMappingConfig.get_mappings_for_type(
            mapping_type, 
            'adminet'
        )
        
        # Obtener campos de Tiendanube
        tiendanube_fields = FieldMappingConfig.get_mappings_for_type(
            mapping_type, 
            'tiendanube'
        )
        
        # Crear mapeos
        mappings = {
            'adminet_fields': [],
            'tiendanube_fields': [],
            'mappings': []
        }
        
        # Procesar campos de AdministraNET
        for field in adminet_fields:
            field_info = {
                'name': field.field_name,
                'display_name': field.field_display_name,
                'description': field.field_description,
                'is_mappable': field.is_mappable,
                'is_required': field.is_required,
                'is_primary_key': field.is_primary_key,
                'mapped_to': field.mapped_to_field,
                'mapping_notes': field.mapping_notes,
                'transformation_type': field.transformation_type,
                'display_order': field.display_order,
            }
            mappings['adminet_fields'].append(field_info)
        
        # Procesar campos de Tiendanube
        for field in tiendanube_fields:
            field_info = {
                'name': field.field_name,
                'display_name': field.field_display_name,
                'description': field.field_description,
                'is_mappable': field.is_mappable,
                'is_required': field.is_required,
                'is_primary_key': field.is_primary_key,
                'mapped_to': field.mapped_to_field,
                'mapping_notes': field.mapping_notes,
                'transformation_type': field.transformation_type,
                'display_order': field.display_order,
            }
            mappings['tiendanube_fields'].append(field_info)
        
        # Crear mapeos cruzados
        for adminet_field in mappings['adminet_fields']:
            if adminet_field['mapped_to']:
                # Buscar el campo de Tiendanube correspondiente
                tiendanube_field = next(
                    (f for f in mappings['tiendanube_fields'] 
                     if f['name'] == adminet_field['mapped_to']), 
                    None
                )
                
                if tiendanube_field:
                    mappings['mappings'].append({
                        'adminet_field': adminet_field,
                        'tiendanube_field': tiendanube_field,
                        'is_mappable': adminet_field['is_mappable'] and tiendanube_field['is_mappable']
                    })
        
        # Cachear resultado
        self._cache[cache_key] = mappings
        
        return mappings
    
    def get_mappable_fields(self, mapping_type: str) -> List[Dict[str, Any]]:
        """
        Obtener solo los campos que son mapeables.
        """
        mappings = self.get_field_mappings(mapping_type)
        return [m for m in mappings['mappings'] if m['is_mappable']]
    
    def get_field_by_name(self, mapping_type: str, field_name: str, field_type: str = None) -> Optional[Dict[str, Any]]:
        """
        Obtener información de un campo específico por nombre.
        """
        mappings = self.get_field_mappings(mapping_type)
        
        if field_type == 'adminet':
            fields = mappings['adminet_fields']
        elif field_type == 'tiendanube':
            fields = mappings['tiendanube_fields']
        else:
            # Buscar en ambos
            fields = mappings['adminet_fields'] + mappings['tiendanube_fields']
        
        return next((f for f in fields if f['name'] == field_name), None)
    
    def clear_cache(self):
        """Limpiar el cache de mapeos."""
        self._cache.clear()
    
    def refresh_mappings(self, mapping_type: str = None):
        """Refrescar los mapeos del cache."""
        if mapping_type:
            cache_key = f"mappings_{mapping_type}"
            if cache_key in self._cache:
                del self._cache[cache_key]
        else:
            self.clear_cache()


class FieldMappingInitializer:
    """
    Clase para inicializar los mapeos de campos por defecto.
    """
    
    @classmethod
    def initialize_customer_mappings(cls):
        """Inicializar mapeos de clientes."""
        mappings = [
            # Campos de AdministraNET
            {
                'mapping_type': 'customer',
                'field_type': 'adminet',
                'field_name': 'Codigo',
                'field_display_name': 'Código',
                'field_description': 'Customer ID (Primary Key)',
                'is_mappable': True,
                'is_required': True,
                'is_primary_key': True,
                'mapped_to_field': 'id',
                'mapping_notes': 'Primary key mapping',
                'transformation_type': 'direct',
                'display_order': 1,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'adminet',
                'field_name': 'nombre_cliente',
                'field_display_name': 'Nombre Cliente',
                'field_description': 'Customer Name',
                'is_mappable': True,
                'is_required': True,
                'mapped_to_field': 'name',
                'mapping_notes': 'Direct name mapping',
                'transformation_type': 'direct',
                'display_order': 2,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'adminet',
                'field_name': 'Email',
                'field_display_name': 'Email',
                'field_description': 'Customer Email',
                'is_mappable': True,
                'is_required': True,
                'mapped_to_field': 'email',
                'mapping_notes': 'Direct email mapping',
                'transformation_type': 'direct',
                'display_order': 3,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'adminet',
                'field_name': 'CUIT',
                'field_display_name': 'CUIT',
                'field_description': 'Tax ID/Document',
                'is_mappable': True,
                'is_required': False,
                'mapped_to_field': 'document',
                'mapping_notes': 'Tax document mapping',
                'transformation_type': 'direct',
                'display_order': 4,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'adminet',
                'field_name': 'telefono',
                'field_display_name': 'Teléfono',
                'field_description': 'Phone Number',
                'is_mappable': True,
                'is_required': False,
                'mapped_to_field': 'phone',
                'mapping_notes': 'Direct phone mapping',
                'transformation_type': 'direct',
                'display_order': 5,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'adminet',
                'field_name': 'Calle',
                'field_display_name': 'Calle',
                'field_description': 'Street Name',
                'is_mappable': True,
                'is_required': False,
                'mapped_to_field': 'address.street',
                'mapping_notes': 'Part of address parsing',
                'transformation_type': 'address_parse',
                'display_order': 6,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'adminet',
                'field_name': 'NroCalle',
                'field_display_name': 'Número Calle',
                'field_description': 'Street Number',
                'is_mappable': True,
                'is_required': False,
                'mapped_to_field': 'address.street',
                'mapping_notes': 'Part of address parsing',
                'transformation_type': 'address_parse',
                'display_order': 7,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'adminet',
                'field_name': 'Dpto',
                'field_display_name': 'Departamento',
                'field_description': 'Department/Apartment',
                'is_mappable': True,
                'is_required': False,
                'mapped_to_field': 'address.street',
                'mapping_notes': 'Part of address parsing',
                'transformation_type': 'address_parse',
                'display_order': 8,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'adminet',
                'field_name': 'IDDepartamento',
                'field_display_name': 'ID Departamento',
                'field_description': 'City/Department (FK)',
                'is_mappable': True,
                'is_required': False,
                'mapped_to_field': 'address.city',
                'mapping_notes': 'City mapping with name resolution',
                'transformation_type': 'name_mapping',
                'display_order': 9,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'adminet',
                'field_name': 'CodProvincia',
                'field_display_name': 'Código Provincia',
                'field_description': 'Province Code (FK)',
                'is_mappable': True,
                'is_required': False,
                'mapped_to_field': 'address.province',
                'mapping_notes': 'Province mapping with name resolution',
                'transformation_type': 'name_mapping',
                'display_order': 10,
            },
            
            # Campos de Tiendanube
            {
                'mapping_type': 'customer',
                'field_type': 'tiendanube',
                'field_name': 'id',
                'field_display_name': 'ID',
                'field_description': 'Customer ID (Primary Key)',
                'is_mappable': True,
                'is_required': True,
                'is_primary_key': True,
                'mapped_to_field': 'Codigo',
                'mapping_notes': 'Primary key mapping',
                'transformation_type': 'direct',
                'display_order': 1,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'tiendanube',
                'field_name': 'name',
                'field_display_name': 'Name',
                'field_description': 'Customer Name',
                'is_mappable': True,
                'is_required': True,
                'mapped_to_field': 'nombre_cliente',
                'mapping_notes': 'Direct name mapping',
                'transformation_type': 'direct',
                'display_order': 2,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'tiendanube',
                'field_name': 'email',
                'field_display_name': 'Email',
                'field_description': 'Customer Email',
                'is_mappable': True,
                'is_required': True,
                'mapped_to_field': 'Email',
                'mapping_notes': 'Direct email mapping',
                'transformation_type': 'direct',
                'display_order': 3,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'tiendanube',
                'field_name': 'document',
                'field_display_name': 'Document',
                'field_description': 'Tax ID/Document',
                'is_mappable': True,
                'is_required': False,
                'mapped_to_field': 'CUIT',
                'mapping_notes': 'Tax document mapping',
                'transformation_type': 'direct',
                'display_order': 4,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'tiendanube',
                'field_name': 'phone',
                'field_display_name': 'Phone',
                'field_description': 'Phone Number',
                'is_mappable': True,
                'is_required': False,
                'mapped_to_field': 'telefono',
                'mapping_notes': 'Direct phone mapping',
                'transformation_type': 'direct',
                'display_order': 5,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'tiendanube',
                'field_name': 'address.street',
                'field_display_name': 'Address Street',
                'field_description': 'Calle y número (incluidos)',
                'is_mappable': True,
                'is_required': False,
                'mapped_to_field': 'Calle',
                'mapping_notes': 'Combines Calle, NroCalle, and Dpto',
                'transformation_type': 'address_parse',
                'display_order': 6,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'tiendanube',
                'field_name': 'address.city',
                'field_display_name': 'Address City',
                'field_description': 'City',
                'is_mappable': True,
                'is_required': False,
                'mapped_to_field': 'IDDepartamento',
                'mapping_notes': 'City mapping with name resolution',
                'transformation_type': 'name_mapping',
                'display_order': 7,
            },
            {
                'mapping_type': 'customer',
                'field_type': 'tiendanube',
                'field_name': 'address.province',
                'field_display_name': 'Address Province',
                'field_description': 'Province/State',
                'is_mappable': True,
                'is_required': False,
                'mapped_to_field': 'CodProvincia',
                'mapping_notes': 'Province mapping with name resolution',
                'transformation_type': 'name_mapping',
                'display_order': 8,
            },
        ]
        
        for mapping_data in mappings:
            FieldMappingConfig.objects.get_or_create(
                mapping_type=mapping_data['mapping_type'],
                field_type=mapping_data['field_type'],
                field_name=mapping_data['field_name'],
                defaults=mapping_data
            )
        
        logger.info(f"Initialized {len(mappings)} customer field mappings")
    
    @classmethod
    def initialize_all_mappings(cls):
        """Inicializar todos los mapeos."""
        cls.initialize_customer_mappings()
        # Agregar otros tipos de mapeo aquí
        logger.info("All field mappings initialized") 