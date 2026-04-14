import requests
import logging
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from ..models import TiendanubeConfig, ProductMapping, ProductCategoryMapping, ProductVariantMapping
from .tiendanube_service import NUVEMSHOP_API_VERSION

logger = logging.getLogger(__name__)


class TiendanubeProductService:
    """
    Servicio completo para manejar productos y variantes de Tiendanube.
    Basado en la documentación oficial de Tiendanube API.
    """
    
    def __init__(self, config: TiendanubeConfig):
        self.config = config
        self.base_url = (
            f"https://api.tiendanube.com/{NUVEMSHOP_API_VERSION}/{config.store_id}"
        )
        self.headers = {
            'Authentication': f'bearer {config.access_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'AdministraNET (soporte@administranet.com.ar)'
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Probar conexión con Tiendanube."""
        try:
            response = requests.get(f"{self.base_url}/products", params={"limit": 1}, headers=self.headers)
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Conexión exitosa con Tiendanube',
                    'store_info': response.json()
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

    # ============================================================================
    # PRODUCTOS
    # ============================================================================

    def get_products(self, limit: int = 50, offset: int = 0, **filters) -> Dict[str, Any]:
        """
        Obtener lista de productos de Tiendanube con filtros avanzados.
        
        Args:
            limit: Número máximo de productos a obtener
            offset: Número de productos a saltar
            **filters: Filtros adicionales (name, sku, handle, etc.)
        """
        try:
            url = f"{self.base_url}/products"
            params = {'limit': limit, 'offset': offset}
            
            # Agregar filtros adicionales
            for key, value in filters.items():
                if value:
                    params[key] = value
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                products = response.json()
                return {
                    'success': True,
                    'products': products,
                    'total': len(products),
                    'has_more': len(products) == limit
                }
            elif response.status_code == 404:
                return {
                    'success': True,
                    'products': [],
                    'total': 0,
                    'has_more': False,
                    'message': 'No se encontraron productos'
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
        """
        Crear producto en Tiendanube.
        
        Args:
            product_data: Datos del producto según documentación de Tiendanube
        """
        try:
            url = f"{self.base_url}/products"
            
            # Validar datos requeridos
            validation_result = self._validate_product_data(product_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'message': 'Datos de producto inválidos',
                    'errors': validation_result['errors']
                }
            
            response = requests.post(url, headers=self.headers, json=product_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Producto creado exitosamente en Tiendanube: {result.get('id')}")
                return {
                    'success': True,
                    'product': result,
                    'message': 'Producto creado exitosamente'
                }
            else:
                logger.error(f"Error creando producto en Tiendanube: {response.status_code} - {response.text}")
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
        """
        Actualizar producto en Tiendanube.
        
        Args:
            product_id: ID del producto en Tiendanube
            product_data: Datos actualizados del producto
        """
        try:
            url = f"{self.base_url}/products/{product_id}"
            
            # Validar datos
            validation_result = self._validate_product_data(product_data, is_update=True)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'message': 'Datos de producto inválidos',
                    'errors': validation_result['errors']
                }
            
            response = requests.put(url, headers=self.headers, json=product_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Producto actualizado exitosamente en Tiendanube: {product_id}")
                return {
                    'success': True,
                    'product': result,
                    'message': 'Producto actualizado exitosamente'
                }
            else:
                logger.error(f"Error actualizando producto en Tiendanube: {response.status_code} - {response.text}")
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
            
            if response.status_code in [200, 204]:
                logger.info(f"Producto eliminado exitosamente de Tiendanube: {product_id}")
                return {
                    'success': True,
                    'message': 'Producto eliminado exitosamente'
                }
            else:
                logger.error(f"Error eliminando producto de Tiendanube: {response.status_code} - {response.text}")
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

    def search_products(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """Buscar productos en Tiendanube."""
        try:
            url = f"{self.base_url}/products"
            params = {
                'q': query,
                'limit': limit
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                products = response.json()
                return {
                    'success': True,
                    'products': products,
                    'total': len(products),
                    'query': query
                }
            else:
                return {
                    'success': False,
                    'message': f'Error buscando productos: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error searching products in Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error buscando productos: {str(e)}'
            }

    # ============================================================================
    # VARIANTES
    # ============================================================================

    def get_product_variants(self, product_id: int) -> Dict[str, Any]:
        """Obtener variantes de un producto de Tiendanube."""
        try:
            url = f"{self.base_url}/products/{product_id}/variants"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                variants = response.json()
                return {
                    'success': True,
                    'variants': variants,
                    'total': len(variants)
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo variantes: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting product variants from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo variantes: {str(e)}'
            }

    def get_variant(self, product_id: int, variant_id: int) -> Dict[str, Any]:
        """Obtener variante específica de un producto."""
        try:
            url = f"{self.base_url}/products/{product_id}/variants/{variant_id}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'variant': response.json()
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo variante: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting variant from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo variante: {str(e)}'
            }

    def create_variant(self, product_id: int, variant_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crear variante de producto en Tiendanube.
        
        Args:
            product_id: ID del producto padre
            variant_data: Datos de la variante
        """
        try:
            url = f"{self.base_url}/products/{product_id}/variants"
            
            # Validar datos de variante
            validation_result = self._validate_variant_data(variant_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'message': 'Datos de variante inválidos',
                    'errors': validation_result['errors']
                }
            
            response = requests.post(url, headers=self.headers, json=variant_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Variante creada exitosamente en Tiendanube: {result.get('id')}")
                return {
                    'success': True,
                    'variant': result,
                    'message': 'Variante creada exitosamente'
                }
            else:
                logger.error(f"Error creando variante en Tiendanube: {response.status_code} - {response.text}")
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

    def update_variant(self, product_id: int, variant_id: int, variant_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar variante de producto en Tiendanube.
        
        Args:
            product_id: ID del producto padre
            variant_id: ID de la variante
            variant_data: Datos actualizados de la variante
        """
        try:
            url = f"{self.base_url}/products/{product_id}/variants/{variant_id}"
            
            # Validar datos
            validation_result = self._validate_variant_data(variant_data, is_update=True)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'message': 'Datos de variante inválidos',
                    'errors': validation_result['errors']
                }
            
            response = requests.put(url, headers=self.headers, json=variant_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Variante actualizada exitosamente en Tiendanube: {variant_id}")
                return {
                    'success': True,
                    'variant': result,
                    'message': 'Variante actualizada exitosamente'
                }
            else:
                logger.error(f"Error actualizando variante en Tiendanube: {response.status_code} - {response.text}")
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

    def delete_variant(self, product_id: int, variant_id: int) -> Dict[str, Any]:
        """Eliminar variante de producto de Tiendanube."""
        try:
            url = f"{self.base_url}/products/{product_id}/variants/{variant_id}"
            response = requests.delete(url, headers=self.headers)
            
            if response.status_code in [200, 204]:
                logger.info(f"Variante eliminada exitosamente de Tiendanube: {variant_id}")
                return {
                    'success': True,
                    'message': 'Variante eliminada exitosamente'
                }
            else:
                logger.error(f"Error eliminando variante de Tiendanube: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'message': f'Error eliminando variante: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error deleting variant from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error eliminando variante: {str(e)}'
            }

    # ============================================================================
    # STOCK
    # ============================================================================

    def update_product_stock(self, product_id: int, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar stock de un producto en Tiendanube.
        
        Args:
            product_id: ID del producto
            stock_data: Datos del stock {'stock': cantidad}
        """
        try:
            url = f"{self.base_url}/products/{product_id}/stock"
            response = requests.put(url, headers=self.headers, json=stock_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Stock actualizado exitosamente para producto: {product_id}")
                return {
                    'success': True,
                    'result': result,
                    'message': 'Stock actualizado exitosamente'
                }
            else:
                logger.error(f"Error actualizando stock de producto: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'message': f'Error actualizando stock: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error updating product stock in Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error actualizando stock: {str(e)}'
            }

    def update_variant_stock(self, product_id: int, variant_id: int, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar stock de una variante en Tiendanube.
        
        Args:
            product_id: ID del producto padre
            variant_id: ID de la variante
            stock_data: Datos del stock {'stock': cantidad}
        """
        try:
            url = f"{self.base_url}/products/{product_id}/variants/{variant_id}/stock"
            response = requests.put(url, headers=self.headers, json=stock_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Stock actualizado exitosamente para variante: {variant_id}")
                return {
                    'success': True,
                    'result': result,
                    'message': 'Stock actualizado exitosamente'
                }
            else:
                logger.error(f"Error actualizando stock de variante: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'message': f'Error actualizando stock: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error updating variant stock in Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error actualizando stock: {str(e)}'
            }

    # ============================================================================
    # CATEGORÍAS
    # ============================================================================

    def get_categories(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Obtener categorías de productos de Tiendanube."""
        try:
            url = f"{self.base_url}/categories"
            params = {'limit': limit, 'offset': offset}
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                categories = response.json()
                return {
                    'success': True,
                    'categories': categories,
                    'total': len(categories)
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

    def get_category(self, category_id: int) -> Dict[str, Any]:
        """Obtener categoría específica de Tiendanube."""
        try:
            url = f"{self.base_url}/categories/{category_id}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'category': response.json()
                }
            else:
                return {
                    'success': False,
                    'message': f'Error obteniendo categoría: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error getting category from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo categoría: {str(e)}'
            }

    def create_category(self, category_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear categoría en Tiendanube."""
        try:
            url = f"{self.base_url}/categories"
            response = requests.post(url, headers=self.headers, json=category_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"Categoría creada exitosamente en Tiendanube: {result.get('id')}")
                return {
                    'success': True,
                    'category': result,
                    'message': 'Categoría creada exitosamente'
                }
            else:
                logger.error(f"Error creando categoría en Tiendanube: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'message': f'Error creando categoría: {response.status_code}',
                    'error': response.text
                }
        except Exception as e:
            logger.error(f"Error creating category in Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error creando categoría: {str(e)}'
            }

    # ============================================================================
    # VALIDACIONES
    # ============================================================================

    def _validate_product_data(self, product_data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
        """
        Validar datos de producto según documentación de Tiendanube.
        
        Args:
            product_data: Datos del producto a validar
            is_update: Si es una actualización (algunos campos pueden ser opcionales)
        """
        errors = []
        warnings = []
        
        # Campos requeridos
        if not is_update:
            # Verificar nombre (puede ser un objeto con idiomas)
            name = product_data.get('name')
            if not name:
                errors.append("El nombre del producto es obligatorio")
            elif isinstance(name, dict):
                if not any(name.values()):
                    errors.append("El nombre del producto debe tener al menos un idioma")
            elif not isinstance(name, str):
                errors.append("El nombre del producto debe ser una cadena válida")
            
            # Verificar SKU en variantes
            variants = product_data.get('variants', [])
            if not variants:
                errors.append("El producto debe tener al menos una variante")
            else:
                for i, variant in enumerate(variants):
                    if not variant.get('sku'):
                        errors.append(f"La variante {i+1} debe tener un SKU")
        
        # Validar longitud de campos
        name = product_data.get('name')
        if name:
            if isinstance(name, dict):
                for lang, text in name.items():
                    if text and len(text) > 255:
                        errors.append(f"El nombre del producto en {lang} no puede exceder 255 caracteres")
            elif isinstance(name, str) and len(name) > 255:
                errors.append("El nombre del producto no puede exceder 255 caracteres")
        
        if product_data.get('sku') and len(product_data['sku']) > 100:
            errors.append("El SKU del producto no puede exceder 100 caracteres")
        
        handle = product_data.get('handle')
        if handle:
            if isinstance(handle, dict):
                for lang, text in handle.items():
                    if text and len(text) > 255:
                        errors.append(f"El handle del producto en {lang} no puede exceder 255 caracteres")
            elif isinstance(handle, str) and len(handle) > 255:
                errors.append("El handle del producto no puede exceder 255 caracteres")
        
        # Validar precio
        if product_data.get('price') is not None:
            try:
                price = float(product_data['price'])
                if price < 0:
                    errors.append("El precio del producto no puede ser negativo")
                elif price > 999999.99:
                    errors.append("El precio del producto no puede exceder 999,999.99")
            except (ValueError, TypeError):
                errors.append("El precio del producto debe ser un número válido")
        
        # Validar stock
        if product_data.get('stock') is not None:
            try:
                stock = int(product_data['stock'])
                if stock < 0:
                    errors.append("El stock del producto no puede ser negativo")
            except (ValueError, TypeError):
                errors.append("El stock del producto debe ser un número entero válido")
        
        # Validar dimensiones
        for dimension in ['weight', 'width', 'height', 'depth']:
            if product_data.get(dimension) is not None:
                try:
                    value = float(product_data[dimension])
                    if value < 0:
                        errors.append(f"La {dimension} del producto no puede ser negativa")
                except (ValueError, TypeError):
                    errors.append(f"La {dimension} del producto debe ser un número válido")
        
        # Validar variantes si existen
        if product_data.get('variants'):
            if not isinstance(product_data['variants'], list):
                errors.append("Las variantes deben ser una lista")
            else:
                for i, variant in enumerate(product_data['variants']):
                    if not isinstance(variant, dict):
                        errors.append(f"La variante {i+1} debe ser un objeto válido")
                        continue
                    
                    if not variant.get('sku'):
                        errors.append(f"La variante {i+1} debe tener un SKU válido")
                    
                    if variant.get('price') is not None:
                        try:
                            price = float(variant['price'])
                            if price < 0:
                                errors.append(f"El precio de la variante {i+1} no puede ser negativo")
                        except (ValueError, TypeError):
                            errors.append(f"El precio de la variante {i+1} debe ser un número válido")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def _validate_variant_data(self, variant_data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
        """
        Validar datos de variante según documentación de Tiendanube.
        
        Args:
            variant_data: Datos de la variante a validar
            is_update: Si es una actualización
        """
        errors = []
        warnings = []
        
        # Campos requeridos
        if not is_update:
            if not variant_data.get('sku'):
                errors.append("El SKU de la variante es obligatorio")
        
        # Validar longitud de campos
        if variant_data.get('name') and len(variant_data['name']) > 255:
            errors.append("El nombre de la variante no puede exceder 255 caracteres")
        
        if variant_data.get('sku') and len(variant_data['sku']) > 100:
            errors.append("El SKU de la variante no puede exceder 100 caracteres")
        
        # Validar precio
        if variant_data.get('price') is not None:
            try:
                price = float(variant_data['price'])
                if price < 0:
                    errors.append("El precio de la variante no puede ser negativo")
                elif price > 999999.99:
                    errors.append("El precio de la variante no puede exceder 999,999.99")
            except (ValueError, TypeError):
                errors.append("El precio de la variante debe ser un número válido")
        
        # Validar stock
        if variant_data.get('stock') is not None:
            try:
                stock = int(variant_data['stock'])
                if stock < 0:
                    errors.append("El stock de la variante no puede ser negativo")
            except (ValueError, TypeError):
                errors.append("El stock de la variante debe ser un número entero válido")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    # ============================================================================
    # UTILIDADES
    # ============================================================================

    def get_product_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de productos de Tiendanube."""
        try:
            # Obtener todos los productos para calcular estadísticas
            result = self.get_products(limit=1000, offset=0)
            
            if not result['success']:
                return result
            
            products = result['products']
            
            # Calcular estadísticas
            total_products = len(products)
            published_products = len([p for p in products if p.get('published', False)])
            products_with_variants = len([p for p in products if p.get('variants')])
            total_variants = sum(len(p.get('variants', [])) for p in products)
            
            # Calcular precios promedio
            prices = []
            for product in products:
                if product.get('price'):
                    prices.append(float(product['price']))
                elif product.get('variants'):
                    for variant in product['variants']:
                        if variant.get('price'):
                            prices.append(float(variant['price']))
            
            avg_price = sum(prices) / len(prices) if prices else 0
            
            return {
                'success': True,
                'statistics': {
                    'total_products': total_products,
                    'published_products': published_products,
                    'products_with_variants': products_with_variants,
                    'total_variants': total_variants,
                    'average_price': round(avg_price, 2),
                    'unpublished_products': total_products - published_products
                }
            }
        except Exception as e:
            logger.error(f"Error getting product statistics from Tiendanube: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo estadísticas: {str(e)}'
            }

    def sync_product_to_tiendanube(self, product_mapping: ProductMapping) -> Dict[str, Any]:
        """
        Sincronizar producto desde AdministraNET a Tiendanube.
        
        Args:
            product_mapping: Mapeo del producto a sincronizar
        """
        try:
            # Construir datos del producto para Tiendanube
            product_data = {
                'name': product_mapping.tiendanube_name or product_mapping.adminet_nombre,
                'description': product_mapping.tiendanube_description or product_mapping.adminet_descripcion or '',
                'sku': product_mapping.tiendanube_sku,
                'handle': product_mapping.tiendanube_handle,
                'published': product_mapping.tiendanube_published,
                'product_type': product_mapping.tiendanube_product_type,
            }
            
            # Agregar precio si está habilitado
            if product_mapping.sync_price and product_mapping.tiendanube_price:
                product_data['price'] = float(product_mapping.tiendanube_price)
            
            # Agregar stock si está habilitado
            if product_mapping.sync_stock and product_mapping.tiendanube_stock is not None:
                product_data['stock'] = int(product_mapping.tiendanube_stock)
            
            # Agregar dimensiones
            if product_mapping.tiendanube_weight:
                product_data['weight'] = float(product_mapping.tiendanube_weight)
            if product_mapping.tiendanube_width:
                product_data['width'] = float(product_mapping.tiendanube_width)
            if product_mapping.tiendanube_height:
                product_data['height'] = float(product_mapping.tiendanube_height)
            if product_mapping.tiendanube_depth:
                product_data['depth'] = float(product_mapping.tiendanube_depth)
            
            # Agregar imágenes si están habilitadas
            if product_mapping.sync_images and product_mapping.tiendanube_images:
                product_data['images'] = product_mapping.tiendanube_images
            
            # Crear o actualizar producto
            if product_mapping.tiendanube_id:
                result = self.update_product(product_mapping.tiendanube_id, product_data)
            else:
                result = self.create_product(product_data)
                if result['success']:
                    # Actualizar el mapping con el ID de Tiendanube
                    product_mapping.tiendanube_id = result['product']['id']
                    product_mapping.save()
            
            # Actualizar estado de sincronización
            if result['success']:
                product_mapping.sync_status = ProductMapping.SyncStatus.SYNCED
                product_mapping.error_message = ''
            else:
                product_mapping.sync_status = ProductMapping.SyncStatus.ERROR
                product_mapping.error_message = result.get('message', 'Error desconocido')
            
            product_mapping.save()
            
            return result
            
        except Exception as e:
            logger.error(f"Error syncing product to Tiendanube: {e}")
            product_mapping.sync_status = ProductMapping.SyncStatus.ERROR
            product_mapping.error_message = str(e)
            product_mapping.save()
            
            return {
                'success': False,
                'message': f'Error sincronizando producto: {str(e)}'
            }

    def sync_variant_to_tiendanube(self, variant_mapping: ProductVariantMapping) -> Dict[str, Any]:
        """
        Sincronizar variante desde AdministraNET a Tiendanube.
        
        Args:
            variant_mapping: Mapeo de la variante a sincronizar
        """
        try:
            if not variant_mapping.product_mapping.tiendanube_id:
                return {
                    'success': False,
                    'message': 'El producto padre debe estar sincronizado primero'
                }
            
            # Construir datos de la variante para Tiendanube
            variant_data = {
                'name': variant_mapping.tiendanube_name or variant_mapping.adminet_nombre,
                'sku': variant_mapping.tiendanube_sku,
                'published': variant_mapping.tiendanube_published,
            }
            
            # Agregar precio si está habilitado
            if variant_mapping.sync_price and variant_mapping.tiendanube_price:
                variant_data['price'] = float(variant_mapping.tiendanube_price)
            
            # Agregar stock si está habilitado
            if variant_mapping.sync_stock and variant_mapping.tiendanube_stock is not None:
                variant_data['stock'] = int(variant_mapping.tiendanube_stock)
            
            # Agregar dimensiones
            if variant_mapping.tiendanube_weight:
                variant_data['weight'] = float(variant_mapping.tiendanube_weight)
            if variant_mapping.tiendanube_width:
                variant_data['width'] = float(variant_mapping.tiendanube_width)
            if variant_mapping.tiendanube_height:
                variant_data['height'] = float(variant_mapping.tiendanube_height)
            if variant_mapping.tiendanube_depth:
                variant_data['depth'] = float(variant_mapping.tiendanube_depth)
            
            # Crear o actualizar variante
            if variant_mapping.tiendanube_variant_id:
                result = self.update_variant(
                    variant_mapping.product_mapping.tiendanube_id,
                    variant_mapping.tiendanube_variant_id,
                    variant_data
                )
            else:
                result = self.create_variant(
                    variant_mapping.product_mapping.tiendanube_id,
                    variant_data
                )
                if result['success']:
                    # Actualizar el mapping con el ID de Tiendanube
                    variant_mapping.tiendanube_variant_id = result['variant']['id']
                    variant_mapping.save()
            
            # Actualizar estado de sincronización
            if result['success']:
                variant_mapping.sync_status = ProductVariantMapping.SyncStatus.SYNCED
                variant_mapping.error_message = ''
            else:
                variant_mapping.sync_status = ProductVariantMapping.SyncStatus.ERROR
                variant_mapping.error_message = result.get('message', 'Error desconocido')
            
            variant_mapping.save()
            
            return result
            
        except Exception as e:
            logger.error(f"Error syncing variant to Tiendanube: {e}")
            variant_mapping.sync_status = ProductVariantMapping.SyncStatus.ERROR
            variant_mapping.error_message = str(e)
            variant_mapping.save()
            
            return {
                'success': False,
                'message': f'Error sincronizando variante: {str(e)}'
            } 