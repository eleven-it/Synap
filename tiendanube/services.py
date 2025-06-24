import requests
from .models import TiendaNubeConfig, TiendaNubeSyncLog, TiendaNubeProductMapping
from inventory.models import Product
import logging
from django.conf import settings
from core.models import SystemConfiguration

# Configurar logger
logger = logging.getLogger(__name__)

def get_site_url():
    # Busca la configuración activa con clave 'main.site.url' o 'site.url'
    config = SystemConfiguration.objects.filter(key__in=['main.site.url', 'site.url'], is_active=True).first()
    if config and config.value:
        return config.value.rstrip('/')
    # Fallback a settings
    return getattr(settings, 'SITE_URL', '').rstrip('/')

class TiendaNubeService:
    """
    Service for full integration with TiendaNube API.
    Handles authentication, product/variant CRUD, stock sync, orders, webhooks, and logging.
    """
    BASE_URL = "https://api.tiendanube.com/v1"

    def __init__(self, config=None):
        self.config = config
        self.store_id = None
        if config and hasattr(config, 'store_id') and config.store_id:
            self.store_id = str(config.store_id)
        if config:
            # Usar la nueva URL base recomendada por la documentación
            self.BASE_URL = f"https://api.tiendanube.com/2025-03/{self.store_id}" if self.store_id else "https://api.tiendanube.com/2025-03"
            self.headers = {
                "Content-Type": "application/json",
                "Authentication": f"bearer {config.access_token}",
                "User-Agent": "Synap (https://synap.com.ar)"
            }
        else:
            self.BASE_URL = "https://api.tiendanube.com/2025-03"
            self.headers = {
                "Content-Type": "application/json",
                "User-Agent": "Synap (https://synap.com.ar)"
            }

    # ----------------------
    # Sync Status & Dashboard
    # ----------------------
    def get_sync_status(self):
        """Get current sync status and statistics."""
        # Obtener datos reales
        total_products = Product.objects.count()
        synced_products = Product.objects.filter(tiendanube_id__isnull=False).count()
        pending_products = total_products - synced_products
        error_products = 0  # Aquí podrías contar productos con errores de sync si tienes ese dato
        sync_percentage = (synced_products / total_products * 100) if total_products > 0 else 0.0
        return {
            'configured': bool(self.config and self.config.is_configured),
            'auto_sync': self.config.auto_sync if self.config else False,
            'last_sync': self.config.last_sync if self.config else None,
            'total_products': total_products,
            'synced_products': synced_products,
            'pending_products': pending_products,
            'error_products': error_products,
            'sync_percentage': sync_percentage
        }

    def test_connection(self):
        """Test real de conexión a la API de TiendaNube usando el token configurado."""
        try:
            if not self.config:
                return False, "No configuration found"
            url = f"{self.BASE_URL}/products?limit=1"
            
            # Log detallado de la petición de prueba
            logger.info(f"=== PRUEBA DE CONEXIÓN TIENDANUBE ===")
            logger.info(f"URL: {url}")
            logger.info(f"Headers: {self.headers}")
            logger.info(f"Config Store ID: {self.config.store_id}")
            if self.config.access_token:
                token_preview = f"{self.config.access_token[:10]}...{self.config.access_token[-10:]}"
            else:
                token_preview = 'None'
            logger.info(f"Config Access Token: {token_preview}")
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            # Log de la respuesta de prueba
            logger.info(f"=== RESPUESTA PRUEBA DE CONEXIÓN ===")
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Response Headers: {dict(response.headers)}")
            logger.info(f"Response Text: {response.text}")
            
            if response.status_code == 200:
                return True, "Conexión exitosa: token válido y acceso a la tienda confirmado."
            elif response.status_code == 401:
                return False, "Token inválido o sin permisos. Verifica el token de acceso de TiendaNube."
            else:
                return False, f"Error {response.status_code}: {response.text}"
        except Exception as e:
            logger.error(f"=== ERROR EN PRUEBA DE CONEXIÓN ===")
            logger.error(f"Exception: {str(e)}")
            return False, f"Error de conexión: {str(e)}"

    # ----------------------
    # Product Sync Methods
    # ----------------------
    def sync_products_from_tiendanube(self, limit=100, offset=0):
        """Sincroniza productos locales pendientes hacia TiendaNube."""
        from .models import TiendaNubeProductMapping
        success_count = 0
        failed_count = 0
        errors = []
        productos_pendientes = Product.objects.filter(tiendanube_id__isnull=True).all()[offset:offset+limit]
        for producto in productos_pendientes:
            try:
                product_data = {
                    "name": producto.name,
                    "description": producto.description,
                    "price": float(producto.price),
                    "sku": producto.sku,
                    "handle": producto.handle,
                    "published": producto.is_published,
                }
                if producto.image:
                    site_url = get_site_url()
                    if site_url:
                        image_url = site_url + producto.image.url
                    else:
                        image_url = producto.image.url
                    product_data["images"] = [{"src": image_url}]
                response = self.create_product(product_data)
                if response and response.get("id"):
                    tiendanube_id = response["id"]
                    producto.tiendanube_id = tiendanube_id
                    producto.tiendanube_url = response.get("permalink", "")
                    producto.save()
                    mapping, created = TiendaNubeProductMapping.objects.get_or_create(product=producto, defaults={
                        "tiendanube_id": tiendanube_id,
                        "tiendanube_handle": producto.handle,
                        "sync_status": TiendaNubeProductMapping.SyncStatus.SYNCED,
                        "sync_enabled": True
                    })
                    if not created:
                        mapping.tiendanube_id = tiendanube_id
                        mapping.tiendanube_handle = producto.handle
                        mapping.sync_status = TiendaNubeProductMapping.SyncStatus.SYNCED
                        mapping.error_message = ""
                        mapping.save()
                    success_count += 1
                else:
                    # Error en la creación: NO crear mapeo si no hay ID
                    msg = f"Error creando producto {producto.sku}: {response}"
                    producto.tiendanube_id = None
                    producto.tiendanube_url = ""
                    producto.save()
                    # Opcional: guardar el error en un campo del producto si lo deseas
                    failed_count += 1
                    errors.append(msg)
            except Exception as e:
                msg = f"Excepción creando producto {producto.sku}: {str(e)}"
                failed_count += 1
                errors.append(msg)
        status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
        self.log_sync('products_from_tiendanube', status, f'Sincronizados: {success_count}, Fallidos: {failed_count}', {"errors": errors})
        return success_count, failed_count

    def sync_stock_to_tiendanube(self, product=None):
        """Sync stock from local database to TiendaNube."""
        # TODO: Implement actual stock sync
        success_count = 0
        failed_count = 0
        
        try:
            if product:
                # Sync specific product
                pass
            else:
                # Sync all products
                pass
            
            self.log_sync('stock_to_tiendanube', 'success', f'Synced stock for {success_count} products')
            return success_count, failed_count
        except Exception as e:
            self.log_sync('stock_to_tiendanube', 'error', str(e))
            return 0, 1

    # ----------------------
    # Webhook Methods
    # ----------------------
    def create_webhook(self, webhook_url):
        """Create a webhook in TiendaNube."""
        # TODO: Implement actual webhook creation
        try:
            # Placeholder implementation
            return {'webhook_id': 'temp_id', 'url': webhook_url}
        except Exception as e:
            raise Exception(f"Failed to create webhook: {str(e)}")

    def handle_webhook(self, webhook_data):
        """Handle incoming webhook from TiendaNube."""
        # TODO: Implement webhook handling
        try:
            webhook_type = webhook_data.get('type')
            webhook_id = webhook_data.get('id')
            
            # Log the webhook
            self.log_sync('webhook_received', 'success', f'Webhook {webhook_type} received', webhook_data)
            
            # Process based on webhook type
            if webhook_type == 'product/created':
                # Handle product creation
                pass
            elif webhook_type == 'product/updated':
                # Handle product update
                pass
            elif webhook_type == 'order/created':
                # Handle order creation
                pass
            elif webhook_type == 'order/updated':
                # Handle order update
                pass
            
            return True, "Webhook processed successfully"
        except Exception as e:
            self.log_sync('webhook_received', 'error', str(e), webhook_data)
            return False, f"Error processing webhook: {str(e)}"

    # ----------------------
    # Logs & Utilities
    # ----------------------
    def get_recent_logs(self, limit=20):
        """Get recent sync logs."""
        return TiendaNubeSyncLog.objects.all().order_by('-started_at')[:limit]

    def log_sync(self, sync_type, status, message, details=None):
        """Log a sync operation to database."""
        try:
            TiendaNubeSyncLog.objects.create(
                sync_type=sync_type,
                status=status,
                message=message,
                details=details or {},
                config=self.config
            )
        except Exception as e:
            # Fallback logging if database fails
            print(f"Sync log error: {e}")

    # ----------------------
    # Product Methods
    # ----------------------
    def get_products(self, params=None):
        """Fetch all products from TiendaNube."""
        # TODO: Implement API call
        pass

    def create_product(self, product_data):
        """Crea un producto en TiendaNube vía API REST."""
        url = f"{self.BASE_URL}/products"
        
        # Log detallado de la petición
        logger.info(f"=== PETICIÓN A TIENDANUBE ===")
        logger.info(f"URL: {url}")
        logger.info(f"Headers: {self.headers}")
        logger.info(f"Product Data: {product_data}")
        logger.info(f"Config Store ID: {self.config.store_id if self.config else 'None'}")
        if self.config and self.config.access_token:
            token_preview = f"{self.config.access_token[:10]}...{self.config.access_token[-10:]}"
        else:
            token_preview = 'None'
        logger.info(f"Config Access Token: {token_preview}")
        
        try:
            response = requests.post(url, json=product_data, headers=self.headers, timeout=15)
            
            # Log de la respuesta
            logger.info(f"=== RESPUESTA DE TIENDANUBE ===")
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Response Headers: {dict(response.headers)}")
            logger.info(f"Response Text: {response.text}")
            
            if response.status_code in (200, 201):
                return response.json()
            else:
                return {"error": response.status_code, "message": response.text}
        except Exception as e:
            logger.error(f"=== ERROR EN PETICIÓN ===")
            logger.error(f"Exception: {str(e)}")
            return {"error": "exception", "message": str(e)}

    def update_product(self, tiendanube_id, product_data):
        """Update a product in TiendaNube."""
        # TODO: Implement API call
        pass

    def delete_product(self, tiendanube_id):
        """Delete a product from TiendaNube."""
        # TODO: Implement API call
        pass

    # ----------------------
    # Variant Methods
    # ----------------------
    def get_variants(self, product_id):
        """Fetch all variants for a product."""
        # TODO: Implement API call
        pass

    def update_variant_stock(self, variant_id, stock):
        """Update stock for a variant."""
        # TODO: Implement API call
        pass

    # ----------------------
    # Stock Sync
    # ----------------------
    def sync_stock(self, product_id, stock_data):
        """Sync stock for a product or variant."""
        # TODO: Implement API call
        pass

    # ----------------------
    # Price Sync
    # ----------------------
    def sync_price(self, product_id, price_data):
        """Sync price for a product or variant."""
        # TODO: Implement API call
        pass

    # ----------------------
    # Orders
    # ----------------------
    def get_orders(self, params=None):
        """Fetch orders from TiendaNube."""
        # TODO: Implement API call
        pass

    def update_order_status(self, order_id, status):
        """Update the status of an order."""
        # TODO: Implement API call
        pass

    # ----------------------
    # Webhooks
    # ----------------------
    def register_webhook(self, webhook_data):
        """Register a webhook in TiendaNube."""
        # TODO: Implement API call
        pass

    def delete_webhook(self, webhook_id):
        """Delete a webhook from TiendaNube."""
        # TODO: Implement API call
        pass

    # ----------------------
    # Error Handling
    # ----------------------
    def handle_error(self, response):
        """Handle API errors and raise exceptions or log as needed."""
        # TODO: Implement error handling
        pass

    # ----------------------
    # Additional Utilities
    # ----------------------
    def get_headers(self):
        """Return the headers for API requests."""
        return self.headers

    def get_base_url(self):
        """Return the base URL for API requests."""
        return self.BASE_URL 