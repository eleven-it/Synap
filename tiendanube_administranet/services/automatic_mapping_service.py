"""
Servicio de Mapeo Automático entre AdministraNET y Tiendanube.
Proporciona mapeos completos y actualizados para todos los modelos.
"""

import logging
from typing import Dict, List, Any, Optional
from django.utils import timezone
from django.utils.translation import gettext as _

from ..models import (
    ProductMapping, CustomerMapping, OrderMapping, ProductVariantMapping,
    TiendanubeConfig, AdministraNETConfig
)
from .intelligent_name_mapping_service import IntelligentNameMappingService

logger = logging.getLogger(__name__)


class AutomaticMappingService:
    """
    Servicio para mapeo automático completo entre AdministraNET y Tiendanube.
    Incluye todos los campos actualizados según la documentación oficial.
    """
    
    def __init__(self, tiendanube_config: TiendanubeConfig = None, adminet_config: AdministraNETConfig = None):
        self.tiendanube_config = tiendanube_config
        self.adminet_config = adminet_config
        self.intelligent_mapper = IntelligentNameMappingService(adminet_config)
    
    # ============================================================================
    # MAPEO DE PRODUCTOS
    # ============================================================================
    
    def map_tiendanube_to_adminet_product(self, tiendanube_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos de producto de Tiendanube a AdministraNET.
        Incluye todos los campos actualizados según la documentación.
        """
        try:
            # Mapeo básico de campos
            adminet_data = {
                # Campos principales
                'NombreArticulo': tiendanube_product.get('name', ''),
                'Detalle': tiendanube_product.get('description', ''),
                'Precio1V': float(tiendanube_product.get('price', 0)),
                'PrecioCosto': float(tiendanube_product.get('cost', 0)),
                'saldo_articulo': int(tiendanube_product.get('stock', 0)),
                'NroCodBarra': tiendanube_product.get('sku', ''),
                
                # Campos de configuración
                'ecommerce': 'Si' if tiendanube_product.get('published', True) else 'No',
                'disponible_vta': 'Si' if tiendanube_product.get('published', True) else 'No',
                'disponible_comp': 'Si',
                'Discontinuo': 'No',
                'detalle_web': tiendanube_product.get('description', ''),
                
                # Campos de marca y categoría (si están disponibles)
                'CodigoMarca': self._extract_brand_code(tiendanube_product.get('brand', '')),
                'CodigoRubro': self._extract_category_code(tiendanube_product.get('categories', [])),
                
                # Campos de configuración por defecto
                'Alicuota': 1,  # IVA 21%
                'AlicuotaIB': 1,  # IB por defecto
                'Moneda': 'ARS',
                'TipoIVA': 'Responsable Inscripto',
                'TipoIB': 'Responsable Inscripto',
                
                # Campos de stock
                'stock_max': float(tiendanube_product.get('stock', 0)) * 1.5,  # 50% más del stock actual
                'stock_min': max(1, float(tiendanube_product.get('stock', 0)) * 0.1),  # 10% del stock actual
                
                # Campos de precios adicionales (si están disponibles)
                'Precio2V': float(tiendanube_product.get('compare_at_price', 0)),
                'Precio3V': float(tiendanube_product.get('price', 0)) * 0.9,  # 10% descuento
                'Precio4V': float(tiendanube_product.get('price', 0)) * 0.8,  # 20% descuento
                'Precio5V': float(tiendanube_product.get('price', 0)) * 0.7,  # 30% descuento
                
                # Campos de configuración adicional
                'CodigoArticuloT': tiendanube_product.get('sku', ''),
                'CodigoProveedor': None,  # Se puede configurar manualmente
                'CodigoModelo': None,  # Se puede configurar manualmente
                'CodigoSubRubro': None,  # Se puede configurar manualmente
                
                # Campos de estado
                'promo_destacado': 'Si' if tiendanube_product.get('featured', False) else 'No',
                
                # Campos de fecha
                'fecha_alta': timezone.now(),
                'fecha_mod': timezone.now(),
            }
            
            # Limpiar campos None
            adminet_data = {k: v for k, v in adminet_data.items() if v is not None}
            
            logger.info(f"Mapeo Tiendanube → AdministraNET producto: {tiendanube_product.get('name', 'N/A')}")
            return adminet_data
            
        except Exception as e:
            logger.error(f"Error en mapeo Tiendanube → AdministraNET producto: {e}")
            raise
    
    def map_adminet_to_tiendanube_product(self, adminet_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos de producto de AdministraNET a Tiendanube.
        Incluye todos los campos actualizados según la documentación.
        """
        try:
            # Mapeo básico de campos
            tiendanube_data = {
                # Campos principales
                'name': adminet_product.get('NombreArticulo', ''),
                'description': adminet_product.get('Detalle', ''),
                'price': float(adminet_product.get('Precio1V', 0)),
                'cost': float(adminet_product.get('PrecioCosto', 0)),
                'stock': int(adminet_product.get('saldo_articulo', 0)),
                'sku': adminet_product.get('NroCodBarra', ''),
                
                # Campos de configuración
                'published': adminet_product.get('ecommerce') == 'Si',
                'handle': self._generate_handle(adminet_product.get('NombreArticulo', '')),
                'product_type': 'physical',
                'free_shipping': False,
                'featured': adminet_product.get('promo_destacado') == 'Si',
                
                # Campos de SEO
                'seo_title': adminet_product.get('NombreArticulo', ''),
                'seo_description': adminet_product.get('detalle_web', ''),
                
                # Campos de marca y categoría
                'brand': self._get_brand_name(adminet_product.get('CodigoMarca')),
                'categories': self._get_category_names(adminet_product.get('CodigoRubro')),
                
                # Campos de dimensiones (por defecto)
                'weight': 0.5,  # 500g por defecto
                'width': 10.0,  # 10cm por defecto
                'height': 10.0,  # 10cm por defecto
                'depth': 10.0,  # 10cm por defecto
                
                # Campos de precio comparativo
                'compare_at_price': float(adminet_product.get('Precio2V', 0)),
                
                # Campos de imágenes y videos (vacíos por defecto)
                'images': [],
                'videos': [],
                'tags': [],
                
                # Campos de fecha
                'created_at': adminet_product.get('fecha_alta'),
                'updated_at': adminet_product.get('fecha_mod'),
            }
            
            # Limpiar campos None
            tiendanube_data = {k: v for k, v in tiendanube_data.items() if v is not None}
            
            logger.info(f"Mapeo AdministraNET → Tiendanube producto: {adminet_product.get('NombreArticulo', 'N/A')}")
            return tiendanube_data
            
        except Exception as e:
            logger.error(f"Error en mapeo AdministraNET → Tiendanube producto: {e}")
            raise
    
    # ============================================================================
    # MAPEO DE CLIENTES
    # ============================================================================
    
    def map_tiendanube_to_adminet_customer(self, tiendanube_customer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos de cliente de Tiendanube a AdministraNET.
        Maneja clientes con datos mínimos (solo nombre, email, contraseña).
        """
        try:
            # Extraer información de dirección (datos de la cuenta)
            address = tiendanube_customer.get('address', {})
            tiendanube_address = address.get('street', '')
            
            # Parsear la dirección de Tiendanube a campos separados de AdministraNET
            calle, nro_calle, dpto = self._parse_tiendanube_address(tiendanube_address)
            
            # Determinar si los datos están completos
            datos_completos = self._check_customer_data_completeness(tiendanube_customer)
            
            adminet_data = {
                # Campos principales (siempre disponibles)
                'nombre_cliente': tiendanube_customer.get('name', ''),
                'Email': tiendanube_customer.get('email', ''),
                'CUIT': tiendanube_customer.get('document', ''),
                'telefono': tiendanube_customer.get('phone', ''),
                
                # Campos de dirección (datos de la cuenta)
                'Calle': calle,
                'NroCalle': nro_calle,
                'Dpto': dpto,
                
                # Campos de ubicación (usando mapeo inteligente)
                'IDDistrito': self.intelligent_mapper.get_district_id(address.get('city', '')),
                'CodProvincia': self.intelligent_mapper.get_province_code(address.get('province', '')),
                'IDDepartamento': self.intelligent_mapper.get_department_id(address.get('city', '')),
                
                # Campos de configuración
                'TipoCliente': self.intelligent_mapper.get_customer_type_id('Consumidor Final'),
                'CodViajante': self.intelligent_mapper.get_viajante_id(),
                'id_pais': self.intelligent_mapper.get_country_id(address.get('country', 'Argentina')),
                'Estado': 'Activo' if tiendanube_customer.get('active', True) else 'Inactivo',
                'tipo_doc': 'CUIT',
                'ListaPrecio': 'Lista 1',
                
                # Campos de fecha
                'FechaAlta': tiendanube_customer.get('created_at') or timezone.now(),
                'fecha_ultima_compra': None,
                
                # Campos adicionales
                'Credito': 0.0,
                'Descuento': 0.0,
                'Observaciones': self._generate_customer_observations(tiendanube_customer, datos_completos),
                'saldo': 0.0,
                'id_manual_cli': '',
                'nombre_fantasia': tiendanube_customer.get('name', ''),
                'cliente_ecommerce': 'Si',
                
                # Campos de workflow de datos incompletos
                'datos_completos': datos_completos,
                'fecha_registro_incompleto': None if datos_completos else timezone.now(),
                'intentos_completar_datos': 0,
                'workflow_estado': 'completo' if datos_completos else 'incompleto',
            }
            
            # Limpiar campos None
            adminet_data = {k: v for k, v in adminet_data.items() if v is not None}
            
            logger.info(f"Mapeo Tiendanube → AdministraNET cliente: {tiendanube_customer.get('email', 'N/A')} - Datos completos: {datos_completos}")
            return adminet_data
            
        except Exception as e:
            logger.error(f"Error en mapeo Tiendanube → AdministraNET cliente: {e}")
            raise
    
    def map_adminet_to_tiendanube_customer(self, adminet_customer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos de cliente de AdministraNET a Tiendanube.
        Incluye transformación de dirección: AdministraNET (3 campos) → Tiendanube (1 campo)
        """
        try:
            # Combinar campos de dirección de AdministraNET en un solo campo para Tiendanube
            tiendanube_address = self._combine_adminet_address(
                adminet_customer.get('Calle', ''),
                adminet_customer.get('NroCalle', ''),
                adminet_customer.get('Dpto', '')
            )
            
            tiendanube_data = {
                # Campos principales
                'name': adminet_customer.get('nombre_cliente', ''),
                'email': adminet_customer.get('Email', ''),
                'document': adminet_customer.get('CUIT', ''),
                'phone': adminet_customer.get('telefono', ''),
                
                # Campos de dirección
                'address': {
                    'street': tiendanube_address,
                    'city': self._get_department_name(adminet_customer.get('IDDepartamento')),
                    'province': self._get_province_name(adminet_customer.get('CodProvincia')),
                    'country': 'Argentina',  # Por defecto
                    'zip': '',  # Se puede configurar manualmente
                },
                
                # Campos de estado
                'active': adminet_customer.get('Estado') == 'Activo',
                
                # Campos de fecha
                'created_at': adminet_customer.get('FechaAlta'),
                'updated_at': adminet_customer.get('FechaMod'),
            }
            
            # Limpiar campos None
            tiendanube_data = {k: v for k, v in tiendanube_data.items() if v is not None}
            
            logger.info(f"Mapeo AdministraNET → Tiendanube cliente: {adminet_customer.get('Email', 'N/A')}")
            return tiendanube_data
            
        except Exception as e:
            logger.error(f"Error en mapeo AdministraNET → Tiendanube cliente: {e}")
            raise
    
    # ============================================================================
    # MAPEO DE PEDIDOS
    # ============================================================================
    
    def map_tiendanube_to_adminet_order(self, tiendanube_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos de pedido de Tiendanube a AdministraNET.
        Incluye manejo de direcciones de entrega y facturación.
        """
        try:
            # Extraer información del cliente
            customer = tiendanube_order.get('customer', {})
            
            # Extraer direcciones
            shipping_address = tiendanube_order.get('shipping_address', {})
            billing_address = tiendanube_order.get('billing_address', {})
            
            # Parsear direcciones
            shipping_calle, shipping_nro, shipping_dpto = self._parse_tiendanube_address(shipping_address.get('street', ''))
            billing_calle, billing_nro, billing_dpto = self._parse_tiendanube_address(billing_address.get('street', ''))
            
            adminet_data = {
                # Campos principales
                'numero_pedido': tiendanube_order.get('number', ''),
                'total': float(tiendanube_order.get('total', 0)),
                'estado': self._map_order_status(tiendanube_order.get('status', '')),
                
                # Campos del cliente
                'idcliente': self._get_customer_id_by_email(customer.get('email', '')),
                
                # Campos de pago y envío
                'metodo_pago': tiendanube_order.get('payment_method', ''),
                'observaciones': self._generate_order_observations(tiendanube_order, shipping_address, billing_address),
                
                # Dirección de entrega
                'direccion_entrega': self._combine_adminet_address(shipping_calle, shipping_nro, shipping_dpto),
                'calle_entrega': shipping_calle,
                'nro_calle_entrega': shipping_nro,
                'dpto_entrega': shipping_dpto,
                'ciudad_entrega': shipping_address.get('city', ''),
                'provincia_entrega': shipping_address.get('province', ''),
                'codigo_postal_entrega': shipping_address.get('zip', ''),
                
                # Dirección de facturación
                'direccion_facturacion': self._combine_adminet_address(billing_calle, billing_nro, billing_dpto),
                'calle_facturacion': billing_calle,
                'nro_calle_facturacion': billing_nro,
                'dpto_facturacion': billing_dpto,
                'ciudad_facturacion': billing_address.get('city', ''),
                'provincia_facturacion': billing_address.get('province', ''),
                'codigo_postal_facturacion': billing_address.get('zip', ''),
                
                # Campos de configuración por defecto
                'vendedor': 75,  # Vendedor por defecto
                'condicion_venta': 'Contado',
                'moneda': tiendanube_order.get('currency', 'ARS'),
                
                # Campos de fecha
                'fecha_pedido': tiendanube_order.get('created_at') or timezone.now(),
                'fecha_mod': timezone.now(),
            }
            
            # Limpiar campos None
            adminet_data = {k: v for k, v in adminet_data.items() if v is not None}
            
            logger.info(f"Mapeo Tiendanube → AdministraNET pedido: {tiendanube_order.get('number', 'N/A')}")
            return adminet_data
            
        except Exception as e:
            logger.error(f"Error en mapeo Tiendanube → AdministraNET pedido: {e}")
            raise
    
    def map_adminet_to_tiendanube_order(self, adminet_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos de pedido de AdministraNET a Tiendanube.
        Incluye todos los campos actualizados según la documentación.
        """
        try:
            tiendanube_data = {
                # Campos principales
                'number': adminet_order.get('numero_pedido', ''),
                'total': float(adminet_order.get('total', 0)),
                'status': self._map_adminet_order_status(adminet_order.get('estado', '')),
                
                # Campos del cliente
                'customer': {
                    'id': adminet_order.get('idcliente'),
                    'email': self._get_customer_email_by_id(adminet_order.get('idcliente')),
                    'name': self._get_customer_name_by_id(adminet_order.get('idcliente')),
                },
                
                # Campos de pago y envío
                'payment_method': adminet_order.get('metodo_pago', ''),
                'payment_status': 'paid',  # Por defecto
                'shipping_method': 'standard',  # Por defecto
                'notes': adminet_order.get('observaciones', ''),
                
                # Campos de dirección
                'shipping_address': self._parse_shipping_address(adminet_order.get('direccion', '')),
                'billing_address': self._parse_shipping_address(adminet_order.get('direccion', '')),
                
                # Campos de moneda
                'currency': adminet_order.get('moneda', 'ARS'),
                
                # Campos de fecha
                'created_at': adminet_order.get('fecha_pedido'),
                'updated_at': adminet_order.get('fecha_mod'),
            }
            
            # Limpiar campos None
            tiendanube_data = {k: v for k, v in tiendanube_data.items() if v is not None}
            
            logger.info(f"Mapeo AdministraNET → Tiendanube pedido: {adminet_order.get('numero_pedido', 'N/A')}")
            return tiendanube_data
            
        except Exception as e:
            logger.error(f"Error en mapeo AdministraNET → Tiendanube pedido: {e}")
            raise
    
    # ============================================================================
    # MAPEO DE VARIANTES
    # ============================================================================
    
    def map_tiendanube_to_adminet_variant(self, tiendanube_variant: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos de variante de Tiendanube a AdministraNET.
        Las variantes se tratan como productos separados en AdministraNET.
        """
        try:
            adminet_data = {
                # Campos principales
                'NombreArticulo': tiendanube_variant.get('name', ''),
                'Detalle': f"Variante: {tiendanube_variant.get('name', '')}",
                'Precio1V': float(tiendanube_variant.get('price', 0)),
                'PrecioCosto': float(tiendanube_variant.get('cost', 0)),
                'saldo_articulo': int(tiendanube_variant.get('stock', 0)),
                'NroCodBarra': tiendanube_variant.get('sku', ''),
                
                # Campos de configuración
                'ecommerce': 'Si',
                'disponible_vta': 'Si',
                'disponible_comp': 'Si',
                'Discontinuo': 'No',
                
                # Campos de configuración por defecto
                'Alicuota': 1,
                'AlicuotaIB': 1,
                'Moneda': 'ARS',
                'TipoIVA': 'Responsable Inscripto',
                'TipoIB': 'Responsable Inscripto',
                
                # Campos de stock
                'stock_max': float(tiendanube_variant.get('stock', 0)) * 1.5,
                'stock_min': max(1, float(tiendanube_variant.get('stock', 0)) * 0.1),
                
                # Campos de precios adicionales
                'Precio2V': float(tiendanube_variant.get('compare_at_price', 0)),
                'Precio3V': float(tiendanube_variant.get('price', 0)) * 0.9,
                'Precio4V': float(tiendanube_variant.get('price', 0)) * 0.8,
                'Precio5V': float(tiendanube_variant.get('price', 0)) * 0.7,
                
                # Campos de fecha
                'fecha_alta': timezone.now(),
                'fecha_mod': timezone.now(),
            }
            
            # Limpiar campos None
            adminet_data = {k: v for k, v in adminet_data.items() if v is not None}
            
            logger.info(f"Mapeo Tiendanube → AdministraNET variante: {tiendanube_variant.get('name', 'N/A')}")
            return adminet_data
            
        except Exception as e:
            logger.error(f"Error en mapeo Tiendanube → AdministraNET variante: {e}")
            raise
    
    def map_adminet_to_tiendanube_variant(self, adminet_variant: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos de variante de AdministraNET a Tiendanube.
        """
        try:
            tiendanube_data = {
                # Campos principales
                'name': adminet_variant.get('NombreArticulo', ''),
                'sku': adminet_variant.get('NroCodBarra', ''),
                'price': float(adminet_variant.get('Precio1V', 0)),
                'cost': float(adminet_variant.get('PrecioCosto', 0)),
                'stock': int(adminet_variant.get('saldo_articulo', 0)),
                
                # Campos de configuración
                'published': adminet_variant.get('ecommerce') == 'Si',
                'compare_at_price': float(adminet_variant.get('Precio2V', 0)),
                
                # Campos de dimensiones
                'weight': 0.5,
                'width': 10.0,
                'height': 10.0,
                'depth': 10.0,
                
                # Campos de opciones y valores
                'options': [],
                'values': {},
                'images': [],
                
                # Campos de fecha
                'created_at': adminet_variant.get('fecha_alta'),
                'updated_at': adminet_variant.get('fecha_mod'),
            }
            
            # Limpiar campos None
            tiendanube_data = {k: v for k, v in tiendanube_data.items() if v is not None}
            
            logger.info(f"Mapeo AdministraNET → Tiendanube variante: {adminet_variant.get('NombreArticulo', 'N/A')}")
            return tiendanube_data
            
        except Exception as e:
            logger.error(f"Error en mapeo AdministraNET → Tiendanube variante: {e}")
            raise
    
    # ============================================================================
    # MÉTODOS AUXILIARES
    # ============================================================================
    
    def _extract_brand_code(self, brand_name: str) -> Optional[int]:
        """Extraer código de marca desde el nombre."""
        # Implementar lógica de búsqueda en tabla de marcas
        return None
    
    def _extract_category_code(self, categories: List[str]) -> Optional[int]:
        """Extraer código de categoría desde la lista de categorías."""
        # Implementar lógica de búsqueda en tabla de rubros
        return None
    
    def _generate_handle(self, name: str) -> str:
        """Generar handle para Tiendanube desde el nombre."""
        if not name:
            return ''
        return name.lower().replace(' ', '-').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    
    def _get_brand_name(self, brand_code: int) -> str:
        """Obtener nombre de marca desde el código."""
        # Implementar consulta a tabla de marcas
        return ''
    
    def _get_category_names(self, category_code: int) -> List[str]:
        """Obtener nombres de categorías desde el código."""
        # Implementar consulta a tabla de rubros
        return []
    
    def _get_department_id(self, city_name: str) -> Optional[int]:
        """Obtener ID de departamento desde el nombre de ciudad."""
        # Implementar consulta a tabla de departamentos
        return None
    
    def _get_province_code(self, province_name: str) -> Optional[int]:
        """Obtener código de provincia desde el nombre."""
        # Implementar consulta a tabla de provincias
        return None
    
    def _get_department_name(self, department_id: int) -> str:
        """Obtener nombre de departamento desde el ID."""
        # Implementar consulta a tabla de departamentos
        return ''
    
    def _get_province_name(self, province_code: int) -> str:
        """Obtener nombre de provincia desde el código."""
        # Implementar consulta a tabla de provincias
        return ''
    
    def _get_customer_id_by_email(self, email: str) -> Optional[int]:
        """Obtener ID de cliente desde el email."""
        # Implementar consulta a tabla de clientes
        return None
    
    def _get_customer_email_by_id(self, customer_id: int) -> str:
        """Obtener email de cliente desde el ID."""
        # Implementar consulta a tabla de clientes
        return ''
    
    def _get_customer_name_by_id(self, customer_id: int) -> str:
        """Obtener nombre de cliente desde el ID."""
        # Implementar consulta a tabla de clientes
        return ''

    def _parse_tiendanube_address(self, address_string: str) -> tuple:
        """
        Parsea la dirección de Tiendanube y la separa en campos de AdministraNET.
        Maneja múltiples formatos de direcciones argentinas.
        Retorna: (calle, nro_calle, dpto)
        
        Ejemplos soportados:
        - "Av. Corrientes 1234"
        - "Calle de la Plata 500, Piso 3, Dpto A"
        - "San Martín 1234 bis"
        - "Belgrano 567, 2do piso"
        - "Rivadavia 890, Local 15"
        """
        if not address_string:
            return '', '', ''
        
        import re
        
        # Limpiar la dirección
        address = address_string.strip()
        
        # Primero, extraer información de departamento/piso
        dpto_info = self._extract_department_info(address)
        address = dpto_info['clean_address']
        dpto = dpto_info['department']
        
        # Luego, extraer calle y número
        street_info = self._extract_street_and_number(address)
        calle = street_info['street']
        nro_calle = street_info['number']
        
        return calle, nro_calle, dpto
    
    def _extract_department_info(self, address: str) -> dict:
        """Extrae información de departamento/piso de la dirección."""
        import re
        
        # Patrones para departamentos/pisos
        dpto_patterns = [
            r',?\s*(?:piso|p\.|pis\.)\s*(\d+)(?:\s*,?\s*(?:dpto|depto|dpt\.|apto|apt\.)\s*([a-zA-Z0-9]+))?',
            r',?\s*(?:dpto|depto|dpt\.|apto|apt\.)\s*([a-zA-Z0-9]+)',
            r',?\s*(?:local|l\.)\s*(\d+)',
            r',?\s*(\d+)\s*(?:piso|p\.)',
            r',?\s*(\d+)\s*(?:dpto|depto|dpt\.)',
            r',?\s*(\d+)\s*(?:local|l\.)',
            r',?\s*([a-zA-Z0-9]+)\s*(?:dpto|depto|dpt\.)',
            r',?\s*(?:piso|p\.|pis\.)\s*([a-zA-Z0-9]+)(?:\s*,?\s*(?:dpto|depto|dpt\.|apto|apt\.)\s*([a-zA-Z0-9]+))?',
            r',?\s*(?:dpto|depto|dpt\.|apto|apt\.)\s*(\d+)',
        ]
        
        dpto_match = None
        dpto_text = ''
        
        for pattern in dpto_patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                dpto_match = match
                dpto_text = match.group(0)
                break
        
        if dpto_match:
            # Remover el texto del departamento
            clean_address = address[:dpto_match.start()] + address[dpto_match.end():]
            clean_address = clean_address.strip()
            
            # Extraer información del departamento
            dpto_parts = []
            for group in dpto_match.groups():
                if group:
                    dpto_parts.append(group)
            
            if dpto_parts:
                department = ' '.join(dpto_parts)
            else:
                department = dpto_text.strip(' ,')
        else:
            clean_address = address
            department = ''
        
        return {
            'clean_address': clean_address,
            'department': department
        }
    
    def _extract_street_and_number(self, address: str) -> dict:
        """Extrae calle y número de la dirección."""
        import re
        
        # Patrones para números de calle
        number_patterns = [
            r'\b(\d+)\s*(?:bis|ter|quater)?\b',  # 1234, 1234 bis, 1234 ter
            r'\b(\d+[a-zA-Z])\b',  # 1234A, 1234B
            r'\b(\d+)\s*-\s*(\d+)\b',  # 1234-5678
        ]
        
        # Buscar el número
        number_match = None
        number_text = ''
        
        for pattern in number_patterns:
            match = re.search(pattern, address)
            if match:
                number_match = match
                number_text = match.group(0)
                break
        
        if number_match:
            # Separar calle y número
            street = address[:number_match.start()].strip()
            number = number_text
            
            # Limpiar la calle
            street = re.sub(r'[,\s]+$', '', street)
        else:
            street = address
            number = ''
        
        # Lógica especial para calles con números en el nombre
        if street and not number:
            street_parts = street.split()
            if len(street_parts) >= 3:
                # Verificar si el último elemento es un número
                last_part = street_parts[-1]
                if last_part.isdigit():
                    # Es un número de dirección
                    street = ' '.join(street_parts[:-1])
                    number = last_part
                elif len(street_parts) >= 4:
                    # Verificar patrones como "Av. 9 de Julio" o "Calle 25 de Mayo"
                    # Si hay un número en el medio, es parte del nombre
                    for i, part in enumerate(street_parts):
                        if part.isdigit() and i < len(street_parts) - 1:
                            # Es parte del nombre de la calle
                            continue
                        elif part.isdigit() and i == len(street_parts) - 1:
                            # Es un número de dirección al final
                            street = ' '.join(street_parts[:-1])
                            number = part
                            break
        
        return {
            'street': street.strip(),
            'number': number.strip()
        }

    def _combine_adminet_address(self, calle: str, nro_calle: str, dpto: str) -> str:
        """
        Combina los campos de dirección de AdministraNET en un solo string para Tiendanube.
        Formato: "Calle NroCalle Dpto"
        """
        parts = []
        if calle:
            parts.append(calle.strip())
        if nro_calle:
            parts.append(nro_calle.strip())
        if dpto:
            parts.append(dpto.strip())
        
        return ' '.join(parts)

    def _get_district_id(self, city_name: str) -> Optional[int]:
        """Obtener ID de distrito desde el nombre de ciudad."""
        # Implementar consulta a tabla distrito
        return 1  # Por defecto

    def _get_customer_type_id(self, type_name: str) -> Optional[int]:
        """Obtener ID de tipo de cliente desde el nombre."""
        # Implementar consulta a tabla tipo_cliente
        return 1  # Por defecto

    def _get_default_viajante_id(self) -> Optional[int]:
        """Obtener ID de viajante por defecto."""
        # Implementar consulta a tabla viajantes
        return 1  # Por defecto

    def _get_country_id(self, country_name: str) -> Optional[int]:
        """Obtener ID de país desde el nombre."""
        # Implementar consulta a tabla pais
        return 1  # Por defecto
    
    def _check_customer_data_completeness(self, tiendanube_customer: Dict[str, Any]) -> bool:
        """
        Verifica si el cliente tiene datos completos.
        Datos mínimos: nombre, email, contraseña
        Datos completos: nombre, email, teléfono, dirección completa
        """
        # Datos obligatorios mínimos
        has_name = bool(tiendanube_customer.get('name', '').strip())
        has_email = bool(tiendanube_customer.get('email', '').strip())
        
        # Datos adicionales que indican completitud
        has_phone = bool(tiendanube_customer.get('phone', '').strip())
        has_document = bool(tiendanube_customer.get('document', '').strip())
        
        # Verificar dirección completa
        address = tiendanube_customer.get('address', {})
        has_street = bool(address.get('street', '').strip())
        has_city = bool(address.get('city', '').strip())
        has_province = bool(address.get('province', '').strip())
        has_country = bool(address.get('country', '').strip())
        
        # Se considera completo si tiene datos mínimos + al menos teléfono o dirección
        datos_minimos = has_name and has_email
        datos_adicionales = has_phone or (has_street and has_city and has_province)
        
        return datos_minimos and datos_adicionales
    
    def _generate_customer_observations(self, tiendanube_customer: Dict[str, Any], datos_completos: bool) -> str:
        """
        Genera observaciones para el cliente basadas en su estado de datos.
        """
        observations = []
        
        # Información básica
        observations.append(f"Cliente sincronizado desde Tiendanube - ID: {tiendanube_customer.get('id', 'N/A')}")
        
        # Estado de datos
        if datos_completos:
            observations.append("Datos completos")
        else:
            observations.append("Datos incompletos - requiere completar información")
            
            # Indicar qué datos faltan
            missing_data = []
            if not tiendanube_customer.get('phone'):
                missing_data.append("teléfono")
            if not tiendanube_customer.get('document'):
                missing_data.append("documento")
            
            address = tiendanube_customer.get('address', {})
            if not address.get('street') or not address.get('city'):
                missing_data.append("dirección completa")
            
            if missing_data:
                observations.append(f"Datos faltantes: {', '.join(missing_data)}")
        
        # Fecha de sincronización
        observations.append(f"Sincronizado: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
        
        return " | ".join(observations)
    
    def _generate_order_observations(self, tiendanube_order: Dict[str, Any], shipping_address: Dict[str, Any], billing_address: Dict[str, Any]) -> str:
        """
        Genera observaciones para el pedido incluyendo información de direcciones.
        """
        observations = []
        
        # Información básica del pedido
        observations.append(f"Pedido sincronizado desde Tiendanube - Número: {tiendanube_order.get('number', 'N/A')}")
        observations.append(f"Cliente: {tiendanube_order.get('customer', {}).get('name', 'N/A')}")
        
        # Información de direcciones
        if shipping_address:
            shipping_info = f"Entrega: {shipping_address.get('street', '')}, {shipping_address.get('city', '')}, {shipping_address.get('province', '')}"
            observations.append(shipping_info)
        
        if billing_address:
            billing_info = f"Facturación: {billing_address.get('street', '')}, {billing_address.get('city', '')}, {billing_address.get('province', '')}"
            observations.append(billing_info)
        
        # Estado del pedido
        observations.append(f"Estado: {tiendanube_order.get('status', 'N/A')}")
        observations.append(f"Pago: {tiendanube_order.get('payment_status', 'N/A')}")
        
        # Notas originales
        if tiendanube_order.get('notes'):
            observations.append(f"Notas: {tiendanube_order.get('notes')}")
        
        # Fecha de sincronización
        observations.append(f"Sincronizado: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
        
        return " | ".join(observations)
    
    def _map_order_status(self, tiendanube_status: str) -> str:
        """Mapear estado de pedido de Tiendanube a AdministraNET."""
        status_mapping = {
            'open': 'Pendiente',
            'closed': 'Cerrado',
            'cancelled': 'Cancelado',
            'pending': 'Pendiente',
            'paid': 'Pagado',
            'shipped': 'Enviado',
            'delivered': 'Entregado',
        }
        return status_mapping.get(tiendanube_status.lower(), 'Pendiente')
    
    def _map_adminet_order_status(self, adminet_status: str) -> str:
        """Mapear estado de pedido de AdministraNET a Tiendanube."""
        status_mapping = {
            'pendiente': 'pending',
            'cerrado': 'closed',
            'cancelado': 'cancelled',
            'pagado': 'paid',
            'enviado': 'shipped',
            'entregado': 'delivered',
        }
        return status_mapping.get(adminet_status.lower(), 'pending')
    
    def _format_shipping_address(self, address: Dict[str, Any]) -> str:
        """Formatear dirección de envío para AdministraNET."""
        parts = []
        if address.get('street'):
            parts.append(address['street'])
        if address.get('city'):
            parts.append(address['city'])
        if address.get('province'):
            parts.append(address['province'])
        if address.get('zip'):
            parts.append(address['zip'])
        return ', '.join(parts)
    
    def _parse_shipping_address(self, address_string: str) -> Dict[str, Any]:
        """Parsear dirección de envío desde AdministraNET."""
        parts = address_string.split(',') if address_string else []
        return {
            'street': parts[0].strip() if len(parts) > 0 else '',
            'city': parts[1].strip() if len(parts) > 1 else '',
            'province': parts[2].strip() if len(parts) > 2 else '',
            'zip': parts[3].strip() if len(parts) > 3 else '',
            'country': 'Argentina',
        }
    
    # ============================================================================
    # MÉTODOS DE ACTUALIZACIÓN DE MAPPINGS
    # ============================================================================
    
    def update_product_mapping_from_tiendanube(self, mapping: ProductMapping, tiendanube_product: Dict[str, Any]):
        """Actualizar mapeo de producto con datos de Tiendanube."""
        try:
            # Actualizar campos de Tiendanube
            mapping.tiendanube_name = tiendanube_product.get('name', '')
            mapping.tiendanube_handle = tiendanube_product.get('handle', '')
            mapping.tiendanube_description = tiendanube_product.get('description', '')
            mapping.tiendanube_sku = tiendanube_product.get('sku', '')
            mapping.tiendanube_price = float(tiendanube_product.get('price', 0))
            mapping.tiendanube_compare_at_price = float(tiendanube_product.get('compare_at_price', 0))
            mapping.tiendanube_cost = float(tiendanube_product.get('cost', 0))
            mapping.tiendanube_stock = int(tiendanube_product.get('stock', 0))
            mapping.tiendanube_weight = float(tiendanube_product.get('weight', 0))
            mapping.tiendanube_width = float(tiendanube_product.get('width', 0))
            mapping.tiendanube_height = float(tiendanube_product.get('height', 0))
            mapping.tiendanube_depth = float(tiendanube_product.get('depth', 0))
            mapping.tiendanube_free_shipping = tiendanube_product.get('free_shipping', False)
            mapping.tiendanube_published = tiendanube_product.get('published', True)
            mapping.tiendanube_featured = tiendanube_product.get('featured', False)
            mapping.tiendanube_product_type = tiendanube_product.get('product_type', 'physical')
            mapping.tiendanube_brand = tiendanube_product.get('brand', '')
            mapping.tiendanube_categories = tiendanube_product.get('categories', [])
            mapping.tiendanube_tags = tiendanube_product.get('tags', [])
            mapping.tiendanube_images = tiendanube_product.get('images', [])
            mapping.tiendanube_videos = tiendanube_product.get('videos', [])
            mapping.tiendanube_seo_title = tiendanube_product.get('seo_title', '')
            mapping.tiendanube_seo_description = tiendanube_product.get('seo_description', '')
            mapping.tiendanube_created_at = tiendanube_product.get('created_at')
            mapping.tiendanube_updated_at = tiendanube_product.get('updated_at')
            
            mapping.save()
            logger.info(f"Mapeo de producto actualizado desde Tiendanube: {mapping.tiendanube_name}")
            
        except Exception as e:
            logger.error(f"Error actualizando mapeo de producto desde Tiendanube: {e}")
            raise
    
    def update_product_mapping_from_adminet(self, mapping: ProductMapping, adminet_product: Dict[str, Any]):
        """Actualizar mapeo de producto con datos de AdministraNET."""
        try:
            # Actualizar campos de AdministraNET
            mapping.adminet_id = adminet_product.get('IDArt')
            mapping.adminet_id_manual = adminet_product.get('id_manual', '')
            mapping.adminet_codigo_articulo = adminet_product.get('CodigoArticuloT', '')
            mapping.adminet_nombre = adminet_product.get('NombreArticulo', '')
            mapping.adminet_detalle = adminet_product.get('Detalle', '')
            mapping.adminet_precio_costo = float(adminet_product.get('PrecioCosto', 0))
            mapping.adminet_precio_1v = float(adminet_product.get('Precio1V', 0))
            mapping.adminet_precio_2v = float(adminet_product.get('Precio2V', 0))
            mapping.adminet_precio_3v = float(adminet_product.get('Precio3V', 0))
            mapping.adminet_precio_4v = float(adminet_product.get('Precio4V', 0))
            mapping.adminet_precio_5v = float(adminet_product.get('Precio5V', 0))
            mapping.adminet_stock = int(adminet_product.get('saldo_articulo', 0))
            mapping.adminet_stock_max = float(adminet_product.get('stock_max', 0))
            mapping.adminet_stock_min = float(adminet_product.get('stock_min', 0))
            mapping.adminet_codigo_barra = adminet_product.get('NroCodBarra', '')
            mapping.adminet_codigo_barra_f = adminet_product.get('NroCodBarraF', '')
            mapping.adminet_codigo_proveedor = adminet_product.get('CodigoProveedor')
            mapping.adminet_codigo_marca = adminet_product.get('CodigoMarca')
            mapping.adminet_codigo_modelo = adminet_product.get('CodigoModelo')
            mapping.adminet_codigo_rubro = adminet_product.get('CodigoRubro')
            mapping.adminet_codigo_subrubro = adminet_product.get('CodigoSubRubro')
            mapping.adminet_alicuota = adminet_product.get('Alicuota')
            mapping.adminet_alicuota_ib = adminet_product.get('AlicuotaIB')
            mapping.adminet_moneda = adminet_product.get('Moneda', '')
            mapping.adminet_tipo_iva = adminet_product.get('TipoIVA', '')
            mapping.adminet_tipo_ib = adminet_product.get('TipoIB', '')
            mapping.adminet_discontinuo = adminet_product.get('Discontinuo', '')
            mapping.adminet_ecommerce = adminet_product.get('ecommerce', '')
            mapping.adminet_detalle_web = adminet_product.get('detalle_web', '')
            mapping.adminet_disponible_venta = adminet_product.get('disponible_vta', '')
            mapping.adminet_disponible_compra = adminet_product.get('disponible_comp', '')
            mapping.adminet_promo_destacado = adminet_product.get('promo_destacado', '')
            mapping.adminet_fecha_alta = adminet_product.get('fecha_alta')
            mapping.adminet_fecha_mod = adminet_product.get('fecha_mod')
            
            mapping.save()
            logger.info(f"Mapeo de producto actualizado desde AdministraNET: {mapping.adminet_nombre}")
            
        except Exception as e:
            logger.error(f"Error actualizando mapeo de producto desde AdministraNET: {e}")
            raise 