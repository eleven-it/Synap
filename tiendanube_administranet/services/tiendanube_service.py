import requests
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from ..models import TiendanubeConfig

logger = logging.getLogger(__name__)


class TiendanubeService:
    """
    Servicio para interactuar con la API de Tiendanube.
    """
    
    def __init__(self, config: TiendanubeConfig):
        self.config = config
        # Usar la versión 2025-03 de la API según documentación oficial
        self.base_url = f"https://api.tiendanube.com/2025-03/{config.store_id}"
        self.headers = {
            'Authentication': f'bearer {config.access_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'AdministraNET (soporte@administranet.com.ar)'
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Probar conexión con Tiendanube."""
        try:
            # Usar endpoint correcto según documentación 2025-03
            url = f"{self.base_url}/products"
            params = {'limit': 1}
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Conexión exitosa con Tiendanube',
                    'store_info': {'status': 'connected', 'store_id': self.config.store_id}
                }
            else:
                return {
                    'success': False,
                    'message': f'Error de conexión: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error testing Tiendanube connection: {e}")
            return {
                'success': False,
                'message': f'Error de conexión: {str(e)}'
            }
    
    def get_customers(self, limit: int = 50, offset: int = 0, **filters) -> Dict[str, Any]:
        """
        Obtener lista de clientes de Tiendanube con filtros avanzados.
        
        Args:
            limit: Número máximo de clientes a obtener
            offset: Número de clientes a saltar
            **filters: Filtros adicionales (email, name, document, etc.)
        """
        try:
            url = f"{self.base_url}/customers"
            params = {'limit': limit, 'offset': offset}
            
            # Agregar filtros adicionales
            for key, value in filters.items():
                if value:
                    params[key] = value
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                customers = response.json()
                return {
                    'success': True,
                    'customers': customers,
                    'total': len(customers),
                    'has_more': len(customers) == limit
                }
            elif response.status_code == 404:
                return {
                    'success': True,
                    'customers': [],
                    'total': 0,
                    'has_more': False,
                    'message': 'No se encontraron clientes'
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo clientes: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting customers from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo clientes: {str(e)}'
            }
    
    def get_customer(self, customer_id: int) -> Dict[str, Any]:
        """Obtener cliente específico de Tiendanube."""
        try:
            url = f"{self.base_url}/customers/{customer_id}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'customer': response.json()
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo cliente: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting customer from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo cliente: {str(e)}'
            }
    
    def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear nuevo cliente en Tiendanube."""
        try:
            url = f"{self.base_url}/customers"
            response = requests.post(url, headers=self.headers, json=customer_data)
            
            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'customer': response.json(),
                    'message': 'Cliente creado exitosamente'
                }
            else:
                return {
                    'success': False,
                    'message': f'Error creando cliente: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error creating customer in Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error creando cliente: {str(e)}'
            }
    
    def update_customer(self, customer_id: int, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Actualizar cliente existente en Tiendanube."""
        try:
            url = f"{self.base_url}/customers/{customer_id}"
            response = requests.put(url, headers=self.headers, json=customer_data)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'customer': response.json(),
                    'message': 'Cliente actualizado exitosamente'
                }
            else:
                return {
                    'success': False,
                    'message': f'Error actualizando cliente: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error updating customer in Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error actualizando cliente: {str(e)}'
            }
    
    def delete_customer(self, customer_id: int) -> Dict[str, Any]:
        """Eliminar cliente de Tiendanube."""
        try:
            url = f"{self.base_url}/customers/{customer_id}"
            response = requests.delete(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Cliente eliminado exitosamente'
                }
            else:
                return {
                    'success': False,
                    'message': f'Error eliminando cliente: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error deleting customer from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error eliminando cliente: {str(e)}'
            }

    def search_customers(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """
        Buscar clientes por email, nombre o documento.
        
        Args:
            query: Término de búsqueda
            limit: Número máximo de resultados
        """
        try:
            url = f"{self.base_url}/customers"
            params = {
                'limit': limit,
                'q': query
            }
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                customers = response.json()
                return {
                    'success': True,
                    'customers': customers,
                    'total': len(customers),
                    'query': query
                }
            else:
                return {
                    'success': False,
                    'message': f'Error buscando clientes: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error searching customers in Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error buscando clientes: {str(e)}'
            }

    def get_customer_orders(self, customer_id: int, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Obtener órdenes de un cliente específico.
        
        Args:
            customer_id: ID del cliente
            limit: Número máximo de órdenes
            offset: Número de órdenes a saltar
        """
        try:
            url = f"{self.base_url}/{self.config.store_id}/customers/{customer_id}/orders"
            params = {'limit': limit, 'offset': offset}
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                orders = response.json()
                return {
                    'success': True,
                    'orders': orders,
                    'total': len(orders),
                    'customer_id': customer_id
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo órdenes del cliente: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting customer orders from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo órdenes del cliente: {str(e)}'
            }

    def validate_customer_data(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validar datos del cliente según la documentación de Tiendanube.
        
        Args:
            customer_data: Datos del cliente a validar
        """
        errors = []
        warnings = []
        
        # Validaciones requeridas
        if not customer_data.get('email'):
            errors.append('El email es obligatorio')
        
        if not customer_data.get('name') and not (customer_data.get('first_name') or customer_data.get('last_name')):
            errors.append('El nombre es obligatorio (name o first_name + last_name)')
        
        # Validaciones de formato
        email = customer_data.get('email', '')
        if email and '@' not in email:
            errors.append('El email debe tener un formato válido')
        
        # Validaciones de longitud
        if customer_data.get('name') and len(customer_data['name']) > 255:
            errors.append('El nombre no puede exceder 255 caracteres')
        
        if customer_data.get('first_name') and len(customer_data['first_name']) > 100:
            errors.append('El nombre no puede exceder 100 caracteres')
        
        if customer_data.get('last_name') and len(customer_data['last_name']) > 100:
            errors.append('El apellido no puede exceder 100 caracteres')
        
        if customer_data.get('document') and len(customer_data['document']) > 50:
            errors.append('El documento no puede exceder 50 caracteres')
        
        if customer_data.get('phone') and len(customer_data['phone']) > 50:
            errors.append('El teléfono no puede exceder 50 caracteres')
        
        # Advertencias
        if not customer_data.get('phone'):
            warnings.append('Se recomienda incluir un número de teléfono')
        
        if not customer_data.get('address'):
            warnings.append('Se recomienda incluir una dirección')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def get_customer_statistics(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de clientes.
        """
        try:
            # Obtener todos los clientes para calcular estadísticas
            result = self.get_customers(limit=1000, offset=0)
            
            if not result['success']:
                return result
            
            customers = result['customers']
            
            # Calcular estadísticas
            total_customers = len(customers)
            verified_customers = len([c for c in customers if c.get('verified_email', False)])
            marketing_customers = len([c for c in customers if c.get('accepts_marketing', False)])
            
            # Calcular total gastado
            total_spent = sum(float(c.get('total_spent', 0)) for c in customers)
            
            # Clientes con órdenes
            customers_with_orders = len([c for c in customers if c.get('orders_count', 0) > 0])
            
            # Top clientes por gasto
            top_customers = sorted(
                customers, 
                key=lambda x: float(x.get('total_spent', 0)), 
                reverse=True
            )[:10]
            
            return {
                'success': True,
                'statistics': {
                    'total_customers': total_customers,
                    'verified_customers': verified_customers,
                    'marketing_customers': marketing_customers,
                    'customers_with_orders': customers_with_orders,
                    'total_spent': total_spent,
                    'average_spent': total_spent / total_customers if total_customers > 0 else 0,
                    'verification_rate': (verified_customers / total_customers * 100) if total_customers > 0 else 0,
                    'marketing_rate': (marketing_customers / total_customers * 100) if total_customers > 0 else 0,
                    'top_customers': top_customers
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting customer statistics from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo estadísticas de clientes: {str(e)}'
            }
    
    def get_products(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Obtener lista de productos de Tiendanube."""
        try:
            url = f"{self.base_url}/products"
            params = {'limit': limit, 'offset': offset}
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'products': response.json(),
                    'total': len(response.json())
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo productos: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting products from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo productos: {str(e)}'
            }
    
    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Obtener producto específico de Tiendanube."""
        try:
            url = f"{self.base_url}/products/{product_id}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'product': response.json()
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo producto: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting product from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo producto: {str(e)}'
            }
    
    def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear nuevo producto en Tiendanube."""
        try:
            # Validar SKU antes de crear
            if 'variants' in product_data and product_data['variants']:
                for variant in product_data['variants']:
                    if variant.get('sku'):
                        # Verificar si el SKU ya existe
                        sku_check = self.check_sku_exists(variant['sku'])
                        if not sku_check['success']:
                            return {
                                'success': False,
                                'message': f'Error verificando SKU: {sku_check["message"]}'
                            }
                        if sku_check['exists']:
                            return {
                                'success': False,
                                'message': f'El SKU {variant["sku"]} ya existe en TiendaNube'
                            }
            
            url = f"{self.base_url}/products"
            response = requests.post(url, headers=self.headers, json=product_data)
            
            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'product': response.json(),
                    'message': 'Producto creado exitosamente'
                }
            else:
                return {
                    'success': False,
                    'message': f'Error creando producto: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error creating product in Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error creando producto: {str(e)}'
            }
    
    def update_product(self, product_id: int, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Actualizar producto existente en Tiendanube."""
        try:
            # Validar SKUs antes de actualizar
            if 'variants' in product_data and product_data['variants']:
                for variant in product_data['variants']:
                    if variant.get('sku'):
                        # Verificar si el SKU ya existe en otro producto
                        sku_check = self.check_sku_exists(variant['sku'], exclude_product_id=product_id)
                        if not sku_check['success']:
                            return {
                                'success': False,
                                'message': f'Error verificando SKU: {sku_check["message"]}'
                            }
                        if sku_check['exists']:
                            return {
                                'success': False,
                                'message': f'El SKU {variant["sku"]} ya existe en otro producto'
                            }
            
            url = f"{self.base_url}/products/{product_id}"
            response = requests.put(url, headers=self.headers, json=product_data)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'product': response.json(),
                    'message': 'Producto actualizado exitosamente'
                }
            else:
                return {
                    'success': False,
                    'message': f'Error actualizando producto: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error updating product in Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error actualizando producto: {str(e)}'
            }
    
    def delete_product(self, product_id: int) -> Dict[str, Any]:
        """Eliminar producto de Tiendanube."""
        try:
            url = f"{self.base_url}/products/{product_id}"
            response = requests.delete(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Producto eliminado exitosamente'
                }
            else:
                return {
                    'success': False,
                    'message': f'Error eliminando producto: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error deleting product from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error eliminando producto: {str(e)}'
            }
    
    def get_orders(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Obtener lista de órdenes de Tiendanube."""
        try:
            url = f"{self.base_url}/orders"
            params = {'limit': limit, 'offset': offset}
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'orders': response.json(),
                    'total': len(response.json())
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo órdenes: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting orders from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo órdenes: {str(e)}'
            }
    
    def get_order(self, order_id: int) -> Dict[str, Any]:
        """Obtener orden específica de Tiendanube."""
        try:
            url = f"{self.base_url}/orders/{order_id}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'order': response.json()
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo orden: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting order from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo orden: {str(e)}'
            }
    
    def update_order(self, order_id: int, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Actualizar orden existente en Tiendanube."""
        try:
            url = f"{self.base_url}/orders/{order_id}"
            response = requests.put(url, headers=self.headers, json=order_data)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'order': response.json(),
                    'message': 'Orden actualizada exitosamente'
                }
            else:
                return {
                    'success': False,
                    'message': f'Error actualizando orden: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error updating order in Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error actualizando orden: {str(e)}'
            }
    
    def get_categories(self) -> Dict[str, Any]:
        """Obtener categorías de Tiendanube."""
        try:
            url = f"{self.base_url}/categories"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'categories': response.json()
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo categorías: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting categories from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo categorías: {str(e)}'
            }
    
    def get_payment_methods(self) -> Dict[str, Any]:
        """Obtener métodos de pago de Tiendanube."""
        try:
            url = f"{self.base_url}/payment_methods"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'payment_methods': response.json()
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo métodos de pago: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting payment methods from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo métodos de pago: {str(e)}'
            }
    
    def get_shipping_methods(self) -> Dict[str, Any]:
        """Obtener métodos de envío de Tiendanube."""
        try:
            url = f"{self.base_url}/shipping_methods"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'shipping_methods': response.json()
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo métodos de envío: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting shipping methods from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo métodos de envío: {str(e)}'
            }
    
    def get_store_info(self) -> Dict[str, Any]:
        """Obtener información de la tienda."""
        try:
            url = f"{self.base_url}/store"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'store_info': response.json()
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo información de la tienda: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting store info from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo información de la tienda: {str(e)}'
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de la tienda."""
        try:
            url = f"{self.base_url}/statistics"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'statistics': response.json()
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo estadísticas: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting statistics from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo estadísticas: {str(e)}'
            }
    
    def check_sku_exists(self, sku: str, exclude_product_id: int = None) -> Dict[str, Any]:
        """
        Verificar si un SKU ya existe en TiendaNube.
        
        Args:
            sku: SKU a verificar
            exclude_product_id: ID del producto a excluir de la búsqueda (para actualizaciones)
            
        Returns:
            Dict con success, exists y message
        """
        try:
            # Buscar productos con el SKU específico
            url = f"{self.base_url}/products"
            params = {'per_page': 200}  # Obtener todos los productos
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                products = response.json()
                
                for product in products:
                    # Excluir el producto actual si se especifica
                    if exclude_product_id and product.get('id') == exclude_product_id:
                        continue
                    
                    # Verificar variantes del producto
                    variants = product.get('variants', [])
                    for variant in variants:
                        if variant.get('sku') == sku:
                            return {
                                'success': True,
                                'exists': True,
                                'message': f'SKU {sku} encontrado en producto {product.get("id")}',
                                'product_id': product.get('id'),
                                'variant_id': variant.get('id')
                            }
                
                return {
                    'success': True,
                    'exists': False,
                    'message': f'SKU {sku} no encontrado'
                }
            else:
                return {
                    'success': False,
                    'exists': False,
                    'message': f'Error obteniendo productos: {response.status_code}'
                }
        except Exception as e:
            logger.error(f"Error checking SKU existence: {e}")
            return {
                'success': False,
                'exists': False,
                'message': f'Error verificando SKU: {str(e)}'
            }
    
    def update_variant(self, product_id: int, variant_id: int, variant_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar una variante específica de un producto.
        Este es el método correcto para actualizar stock, precio y SKU.
        
        Args:
            product_id: ID del producto
            variant_id: ID de la variante
            variant_data: Datos de la variante a actualizar
            
        Returns:
            Dict con el resultado de la actualización
        """
        try:
            # Validar SKU antes de actualizar
            if variant_data.get('sku'):
                sku_check = self.check_sku_exists(variant_data['sku'], exclude_product_id=product_id)
                if not sku_check['success']:
                    return {
                        'success': False,
                        'message': f'Error verificando SKU: {sku_check["message"]}'
                    }
                if sku_check['exists']:
                    return {
                        'success': False,
                        'message': f'El SKU {variant_data["sku"]} ya existe en otro producto'
                    }
            
            url = f"{self.base_url}/products/{product_id}/variants/{variant_id}"
            response = requests.put(url, headers=self.headers, json=variant_data)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'variant': response.json(),
                    'message': 'Variante actualizada exitosamente'
                }
            else:
                return {
                    'success': False,
                    'message': f'Error actualizando variante: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error updating variant in Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error actualizando variante: {str(e)}'
            }
    
    def create_variant(self, product_id: int, variant_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crear una nueva variante para un producto.
        
        Args:
            product_id: ID del producto
            variant_data: Datos de la variante a crear
            
        Returns:
            Dict con el resultado de la creación
        """
        try:
            # Validar SKU antes de crear
            if variant_data.get('sku'):
                sku_check = self.check_sku_exists(variant_data['sku'])
                if not sku_check['success']:
                    return {
                        'success': False,
                        'message': f'Error verificando SKU: {sku_check["message"]}'
                    }
                if sku_check['exists']:
                    return {
                        'success': False,
                        'message': f'El SKU {variant_data["sku"]} ya existe'
                    }
            
            url = f"{self.base_url}/products/{product_id}/variants"
            response = requests.post(url, headers=self.headers, json=variant_data)
            
            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'variant': response.json(),
                    'message': 'Variante creada exitosamente'
                }
            else:
                return {
                    'success': False,
                    'message': f'Error creando variante: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error creating variant in Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error creando variante: {str(e)}'
            } 