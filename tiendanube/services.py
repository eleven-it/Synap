import requests
import logging
import json
import datetime
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from core.models import Contact
from .models import TiendaNubeConfig, TiendaNubeProductMapping, TiendaNubeCustomerMapping, TiendaNubeOrderMapping, TiendaNubeSyncLog
from inventory.models import Product, ProductVariant, StockQuant, Location, Warehouse
from sales.models import Client, SalesOrder, SalesOrderLine
from core.models import Empresa, Branch, SystemConfiguration

logger = logging.getLogger(__name__)

def get_site_url():
    """Obtiene la URL del sitio desde la configuración del sistema"""
    try:
        # Busca la configuración activa con clave 'main.site.url' o 'site.url'
        config = SystemConfiguration.objects.filter(key__in=['main.site.url', 'site.url'], is_active=True).first()
        if config and config.value:
            return config.value.rstrip('/')
        # Fallback a settings
        return getattr(settings, 'SITE_URL', '').rstrip('/')
    except:
        return getattr(settings, 'SITE_URL', '').rstrip('/')

class TiendaNubeValidationError(Exception):
    """Excepción personalizada para errores de validación de Tiendanube"""
    pass

class TiendaNubeService:
    """
    Service for full integration with TiendaNube API.
    Handles authentication, product/variant CRUD, stock sync, orders, customers, webhooks, and logging.
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
                "User-Agent": "administranet_tiendanube - tiendanube@administranet.com.ar"
            }
        else:
            self.BASE_URL = "https://api.tiendanube.com/2025-03"
            self.headers = {
                "Content-Type": "application/json",
                "User-Agent": "administranet_tiendanube - tiendanube@administranet.com.ar"
            }

    def validate_product_data(self, product, operation_type="create"):
        """
        Valida los datos del producto antes de sincronizar con Tiendanube.
        
        Args:
            product: Producto de Synap a validar
            operation_type: "create" o "update"
            
        Returns:
            dict: Datos validados del producto
            list: Lista de errores de validación
        """
        errors = []
        warnings = []
        
        # Log de inicio de validación
        logger.info(f"🔍 Iniciando validación de producto {product.sku} para operación: {operation_type}")
        
        # Validar campos obligatorios según documentación de Tiendanube
        if not product.name or len(product.name.strip()) == 0:
            errors.append("El nombre del producto es obligatorio")
        elif len(product.name) > 255:
            errors.append("El nombre del producto no puede exceder 255 caracteres")
        
        if not product.sku or len(product.sku.strip()) == 0:
            errors.append("El SKU del producto es obligatorio")
        elif len(product.sku) > 100:
            errors.append("El SKU del producto no puede exceder 100 caracteres")
        
        # Validar precio
        if not product.price or product.price <= 0:
            errors.append("El precio del producto debe ser mayor a 0")
        elif product.price > 999999.99:
            errors.append("El precio del producto no puede exceder 999,999.99")
        
        # Validar descripción
        if product.description and len(product.description) > 1000:
            warnings.append("La descripción del producto es muy larga (máximo 1000 caracteres recomendado)")
        
        # Validar handle (URL slug)
        if product.handle and len(product.handle) > 255:
            errors.append("El handle del producto no puede exceder 255 caracteres")
        
        # Validar variantes si existen
        tiene_variantes = hasattr(product, 'variants') and product.variants.exists()
        if tiene_variantes:
            logger.info(f"📦 Producto {product.sku} tiene {product.variants.count()} variantes")
            for i, variante in enumerate(product.variants.all()):
                if not variante.sku or len(variante.sku.strip()) == 0:
                    errors.append(f"La variante {i+1} debe tener un SKU válido")
                if not variante.price or variante.price <= 0:
                    errors.append(f"La variante {i+1} debe tener un precio mayor a 0")
                if variante.price > 999999.99:
                    errors.append(f"El precio de la variante {i+1} no puede exceder 999,999.99")
        
        # Validar imágenes
        if hasattr(product, 'images') and product.images.exists():
            logger.info(f"🖼️ Producto {product.sku} tiene {product.images.count()} imágenes")
            for i, img in enumerate(product.images.all()):
                if not img.image:
                    warnings.append(f"La imagen {i+1} no tiene archivo válido")
        
        # Validar empresa y sucursal
        if not product.empresa:
            errors.append("El producto debe estar asociado a una empresa")
        if not product.branch:
            errors.append("El producto debe estar asociado a una sucursal")
        
        # Validar moneda
        if not product.price_currency:
            warnings.append("El producto no tiene moneda configurada, se usará la moneda por defecto")
        
        # Construir datos del producto para Tiendanube
        product_data = {
            "name": product.name.strip(),
            "description": product.description.strip() if product.description else "",
            "sku": product.sku.strip(),
            "handle": product.handle.strip() if product.handle else None,
            "published": product.is_published,
        }
        
        # Agregar precio según tipo de producto
        if tiene_variantes:
            variants_list = []
            for variante in product.variants.all():
                variant_data = {
                    "name": variante.name if hasattr(variante, 'name') else f"{product.name} - {variante.sku}",
                    "sku": variante.sku.strip(),
                    "price": float(variante.price),
                }
                variants_list.append(variant_data)
            product_data["variants"] = variants_list
            logger.info(f"💰 Producto con variantes - {len(variants_list)} variantes configuradas")
        else:
            product_data["price"] = float(product.price)
            logger.info(f"💰 Producto simple - Precio: ${product.price}")
        
        # Agregar imágenes
        images = []
        site_url = get_site_url()
        if hasattr(product, 'images') and product.images.exists():
            for img in product.images.all():
                if img.image:
                    if site_url:
                        image_url = site_url + img.image.url
                    else:
                        image_url = img.image.url
                    images.append({"src": image_url})
            
            if images:
                product_data["images"] = images
                logger.info(f"🖼️ {len(images)} imágenes configuradas para el producto")
        
        # Log de resultado de validación
        if errors:
            logger.error(f"❌ Validación fallida para producto {product.sku}: {errors}")
        elif warnings:
            logger.warning(f"⚠️ Validación exitosa con advertencias para producto {product.sku}: {warnings}")
        else:
            logger.info(f"✅ Validación exitosa para producto {product.sku}")
        
        return product_data, errors, warnings

    def log_api_response(self, operation, url, request_data, response, product_sku=None):
        """
        Registra detalladamente las respuestas de la API de Tiendanube.
        
        Args:
            operation: Tipo de operación (create, update, delete, etc.)
            url: URL de la API
            request_data: Datos enviados a la API
            response: Respuesta de la API
            product_sku: SKU del producto (opcional)
        """
        log_data = {
            "operation": operation,
            "url": url,
            "product_sku": product_sku,
            "request_data": request_data,
            "response_status": response.status_code,
            "response_headers": dict(response.headers),
            "timestamp": timezone.now().isoformat()
        }
        
        try:
            response_json = response.json()
            log_data["response_data"] = response_json
        except:
            log_data["response_text"] = response.text
        
        # Log detallado según el status code
        if response.status_code in [200, 201]:
            logger.info(f"✅ API {operation} exitosa para producto {product_sku}")
            logger.debug(f"📊 Respuesta API: {json.dumps(log_data, indent=2)}")
        elif response.status_code == 400:
            logger.error(f"❌ Error 400 - Datos inválidos en {operation} para producto {product_sku}")
            logger.error(f"📊 Detalles del error: {json.dumps(log_data, indent=2)}")
        elif response.status_code == 401:
            logger.error(f"❌ Error 401 - No autorizado en {operation} para producto {product_sku}")
            logger.error(f"🔑 Verificar token de acceso")
        elif response.status_code == 403:
            logger.error(f"❌ Error 403 - Prohibido en {operation} para producto {product_sku}")
            logger.error(f"🚫 Verificar permisos de la aplicación")
        elif response.status_code == 404:
            logger.error(f"❌ Error 404 - No encontrado en {operation} para producto {product_sku}")
        elif response.status_code >= 500:
            logger.error(f"❌ Error del servidor ({response.status_code}) en {operation} para producto {product_sku}")
            logger.error(f"🛠️ Error del servidor de Tiendanube: {json.dumps(log_data, indent=2)}")
        else:
            logger.warning(f"⚠️ Respuesta inesperada ({response.status_code}) en {operation} para producto {product_sku}")
            logger.warning(f"📊 Respuesta completa: {json.dumps(log_data, indent=2)}")
        
        # Guardar en base de datos
        try:
            TiendaNubeSyncLog.objects.create(
                config=self.config,
                sync_type='product',
                status='success' if response.status_code in [200, 201] else 'error',
                message=f"API {operation} - Status: {response.status_code}",
                details=log_data
            )
        except Exception as e:
            logger.error(f"Error guardando log en base de datos: {str(e)}")

    # ----------------------
    # Sync Status & Dashboard
    # ----------------------
    def get_sync_status(self):
        """Get current sync status and statistics."""
        total_products = Product.objects.count()
        synced_products = TiendaNubeProductMapping.objects.filter(sync_status='synced').count()
        pending_products = TiendaNubeProductMapping.objects.filter(sync_status='pending').count()
        error_products = TiendaNubeProductMapping.objects.filter(sync_status='error').count()
        
        total_customers = Client.objects.count()
        synced_customers = TiendaNubeCustomerMapping.objects.filter(sync_status='synced').count()
        
        total_orders = SalesOrder.objects.filter(origin='Tiendanube').count()
        synced_orders = TiendaNubeOrderMapping.objects.filter(sync_status='synced').count()
        
        sync_percentage = (synced_products / total_products * 100) if total_products > 0 else 0.0
        last_sync = self.config.last_sync if self.config else None
        sync_interval = self.config.sync_interval if self.config else None
        next_sync = None
        if last_sync and sync_interval:
            next_sync = last_sync + datetime.timedelta(minutes=sync_interval)
        
        return {
            'configured': bool(self.config and self.config.is_configured),
            'auto_sync': self.config.auto_sync if self.config else False,
            'last_sync': last_sync,
            'next_sync': next_sync,
            'sync_interval': sync_interval,
            'total_products': total_products,
            'synced_products': synced_products,
            'pending_products': pending_products,
            'error_products': error_products,
            'sync_percentage': sync_percentage,
            'total_customers': total_customers,
            'synced_customers': synced_customers,
            'total_orders': total_orders,
            'synced_orders': synced_orders,
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
    # Order Sync Methods
    # ----------------------
    def sync_orders_from_tiendanube(self, limit=50, offset=0):
        """Sincroniza pedidos desde Tiendanube hacia Synap."""
        success_count = 0
        failed_count = 0
        errors = []
        
        try:
            # Obtener pedidos de Tiendanube (solo pagados o confirmados)
            params = {
                'limit': limit,
                'offset': offset,
                'status': 'paid,confirmed'  # Solo pedidos pagados o confirmados
            }
            
            response = requests.get(f"{self.BASE_URL}/orders", headers=self.headers, params=params)
            
            if response.status_code != 200:
                self.log_sync('order', 'error', f"Error obteniendo pedidos: {response.status_code}")
                return 0, 1
            
            orders_data = response.json()
            
            for order_data in orders_data:
                try:
                    with transaction.atomic():
                        # Verificar si ya existe el pedido
                        if TiendaNubeOrderMapping.objects.filter(tiendanube_order_id=order_data['id']).exists():
                            continue  # Ya existe, saltar
                        
                        # Buscar o crear cliente
                        customer = self._get_or_create_customer_from_order(order_data)
                        if not customer:
                            failed_count += 1
                            errors.append(f"Error creando cliente para pedido {order_data['id']}")
                            continue
                        
                        # Crear orden de venta
                        sales_order = self._create_sales_order_from_tiendanube(order_data, customer)
                        if not sales_order:
                            failed_count += 1
                            errors.append(f"Error creando orden de venta para pedido {order_data['id']}")
                            continue
                        
                        # Crear mapping
                        TiendaNubeOrderMapping.objects.create(
                            sales_order=sales_order,
                            tiendanube_order_id=order_data['id'],
                            tiendanube_order_number=order_data.get('number', ''),
                            order_source="Tiendanube",
                            payment_method=order_data.get('payment_method', ''),
                            payment_amount=Decimal(str(order_data.get('total', 0))),
                            sync_status=TiendaNubeOrderMapping.SyncStatus.SYNCED
                        )
                        
                        success_count += 1
                        
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Error procesando pedido {order_data.get('id', 'unknown')}: {str(e)}")
                    logger.error(f"Error procesando pedido Tiendanube: {str(e)}")
            
            status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
            self.log_sync('order', status, f'Sincronizados: {success_count}, Fallidos: {failed_count}', {"errors": errors})
            
        except Exception as e:
            self.log_sync('order', 'error', f"Error general en sincronización de pedidos: {str(e)}")
            return 0, 1
        
        return success_count, failed_count

    def _get_or_create_customer_from_order(self, order_data):
        """Obtener o crear cliente desde datos de pedido de Tiendanube."""
        customer_data = order_data.get('customer', {})
        email = customer_data.get('email', '')
        document = customer_data.get('document', '')
        
        # Buscar cliente existente por email o documento
        if email:
            try:
                customer = Client.objects.get(email=email)
                # --- Contact universal ---
                contact = Contact.objects.filter(email=email).first()
                if not contact and document:
                    contact = Contact.objects.filter(notes__icontains=document).first()
                if not contact:
                    contact = Contact.objects.create(
                        name=customer_data.get('name', 'Cliente Tiendanube'),
                        email=email,
                        phone=customer_data.get('phone', ''),
                        address=customer_data.get('address', ''),
                        city=customer_data.get('city', ''),
                        state=customer_data.get('state', ''),
                        country=customer_data.get('country', 'Argentina'),
                        notes=document
                    )
                # Agregar tag tiendanube si no existe
                if contact and 'tiendanube' not in (contact.tags or '').lower():
                    current_tags = contact.tags or ''
                    contact.tags = f"{current_tags},tiendanube".strip(',')
                    contact.save()
                if not customer.has_contact(contact, relationship_type='primary'):
                    customer.add_contact_relationship(contact, relationship_type='primary')
                return customer
            except Client.DoesNotExist:
                pass
        
        if document:
            try:
                customer = Client.objects.get(document_number=document)
                contact = Contact.objects.filter(notes__icontains=document).first()
                if not contact and email:
                    contact = Contact.objects.filter(email=email).first()
                if not contact:
                    contact = Contact.objects.create(
                        name=customer_data.get('name', 'Cliente Tiendanube'),
                        email=email,
                        phone=customer_data.get('phone', ''),
                        address=customer_data.get('address', ''),
                        city=customer_data.get('city', ''),
                        state=customer_data.get('state', ''),
                        country=customer_data.get('country', 'Argentina'),
                        notes=document
                    )
                # Agregar tag tiendanube si no existe
                if contact and 'tiendanube' not in (contact.tags or '').lower():
                    current_tags = contact.tags or ''
                    contact.tags = f"{current_tags},tiendanube".strip(',')
                    contact.save()
                if not customer.has_contact(contact, relationship_type='primary'):
                    customer.add_contact_relationship(contact, relationship_type='primary')
                return customer
            except Client.DoesNotExist:
                pass
        
        # Crear nuevo cliente
        try:
            customer = Client.objects.create(
                name=customer_data.get('name', 'Cliente Tiendanube'),
                email=email,
                document_number=document,
                type='individual' if not document else 'company',
                credit_limit=Decimal('0.00')
            )
            # --- Contact universal ---
            contact = None
            if email:
                contact = Contact.objects.filter(email=email).first()
            if not contact and document:
                contact = Contact.objects.filter(notes__icontains=document).first()
            if not contact:
                contact = Contact.objects.create(
                    name=customer_data.get('name', 'Cliente Tiendanube'),
                    email=email,
                    phone=customer_data.get('phone', ''),
                    address=customer_data.get('address', ''),
                    city=customer_data.get('city', ''),
                    state=customer_data.get('state', ''),
                    country=customer_data.get('country', 'Argentina'),
                    notes=document,
                    tags='tiendanube'  # Nuevo cliente con tag tiendanube
                )
            else:
                # Contact existente - agregar tag tiendanube
                if 'tiendanube' not in (contact.tags or '').lower():
                    current_tags = contact.tags or ''
                    contact.tags = f"{current_tags},tiendanube".strip(',')
                    contact.save()
            if not customer.has_contact(contact, relationship_type='primary'):
                customer.add_contact_relationship(contact, relationship_type='primary')
            # Crear mapping del cliente
            TiendaNubeCustomerMapping.objects.create(
                client=customer,
                tiendanube_id=customer_data.get('id'),
                tiendanube_email=email,
                tiendanube_document=document,
                sync_status=TiendaNubeCustomerMapping.SyncStatus.SYNCED
            )
            
            return customer
            
        except Exception as e:
            logger.error(f"Error creando cliente: {str(e)}")
            return None

    def _create_sales_order_from_tiendanube(self, order_data, customer):
        """Crear orden de venta desde datos de pedido de Tiendanube."""
        try:
            # Obtener configuración necesaria
            branch = Branch.objects.first()  # Usar primera sucursal o configurar
            if not branch:
                return None
            
            # Crear orden de venta
            sales_order = SalesOrder.objects.create(
                order_date=datetime.datetime.fromisoformat(order_data['created_at'].replace('Z', '+00:00')).date(),
                currency='ARS',  # Configurar según necesidad
                client=customer,
                branch=branch,
                payment_term_id=1,  # Configurar según necesidad
                price_list_id=1,    # Configurar según necesidad
                seller_id=1,        # Configurar según necesidad
                state=SalesOrderStates.CONFIRMED,
                origin="Tiendanube",
                external_id=str(order_data['id']),
                total=Decimal(str(order_data.get('total', 0)))
            )
            
            # Crear líneas de orden
            for item in order_data.get('products', []):
                try:
                    # Buscar producto por SKU
                    product = Product.objects.filter(sku=item.get('sku')).first()
                    if not product:
                        logger.warning(f"Producto no encontrado: {item.get('sku')}")
                        continue
                    
                    # Usar primera variante o crear una
                    product_variant = product.variants.first()
                    if not product_variant:
                        product_variant = ProductVariant.objects.create(
                            product=product,
                            sku=item.get('sku'),
                            price=Decimal(str(item.get('price', 0)))
                        )
                    
                    # Crear línea de orden
                    SalesOrderLine.objects.create(
                        sales_order=sales_order,
                        product_variant=product_variant,
                        quantity=Decimal(str(item.get('quantity', 1))),
                        unit_price=Decimal(str(item.get('price', 0))),
                        discount=Decimal('0.00'),
                        subtotal=Decimal(str(item.get('price', 0))) * Decimal(str(item.get('quantity', 1))),
                        state='confirmed'
                    )
                    
                except Exception as e:
                    logger.error(f"Error creando línea de orden: {str(e)}")
                    continue
            
            return sales_order
            
        except Exception as e:
            logger.error(f"Error creando orden de venta: {str(e)}")
            return None

    # ----------------------
    # Customer Sync Methods
    # ----------------------
    def sync_customers_from_tiendanube(self, limit=100, offset=0):
        """Sincroniza clientes desde Tiendanube hacia Synap."""
        success_count = 0
        failed_count = 0
        errors = []
        
        try:
            params = {'limit': limit, 'offset': offset}
            response = requests.get(f"{self.BASE_URL}/customers", headers=self.headers, params=params)
            
            if response.status_code != 200:
                self.log_sync('customer', 'error', f"Error obteniendo clientes: {response.status_code}")
                return 0, 1
            
            customers_data = response.json()
            
            for customer_data in customers_data:
                try:
                    with transaction.atomic():
                        # Verificar si ya existe el mapping
                        if TiendaNubeCustomerMapping.objects.filter(tiendanube_id=customer_data['id']).exists():
                            continue
                        
                        # Buscar cliente existente por email
                        email = customer_data.get('email', '')
                        existing_customer = None
                        
                        if email:
                            try:
                                existing_customer = Client.objects.get(email=email)
                            except Client.DoesNotExist:
                                pass
                        
                        # Si no existe, crear nuevo cliente
                        if not existing_customer:
                            existing_customer = Client.objects.create(
                                name=customer_data.get('name', 'Cliente Tiendanube'),
                                email=email,
                                document_number=customer_data.get('document', ''),
                                type='individual' if not customer_data.get('document') else 'company',
                                credit_limit=Decimal('0.00')
                            )
                        # --- Contact universal ---
                        contact = None
                        # Buscar Contact por email o documento
                        if email:
                            contact = Contact.objects.filter(email=email).first()
                        if not contact and customer_data.get('document', ''):
                            contact = Contact.objects.filter(notes__icontains=customer_data.get('document', '')).first()
                        if not contact:
                            contact = Contact.objects.create(
                                name=customer_data.get('name', 'Cliente Tiendanube'),
                                email=email,
                                phone=customer_data.get('phone', ''),
                                address=customer_data.get('address', ''),
                                city=customer_data.get('city', ''),
                                state=customer_data.get('state', ''),
                                country=customer_data.get('country', 'Argentina'),
                                notes=customer_data.get('document', ''),
                                tags='tiendanube'  # Nuevo contacto con tag tiendanube
                            )
                        else:
                            # Contact existente - agregar tag tiendanube si no existe
                            if 'tiendanube' not in (contact.tags or '').lower():
                                current_tags = contact.tags or ''
                                contact.tags = f"{current_tags},tiendanube".strip(',')
                                contact.save()
                        # Vincular como contacto primario si no existe relación
                        if not existing_customer.has_contact(contact, relationship_type='primary'):
                            existing_customer.add_contact_relationship(contact, relationship_type='primary')
                        # Crear mapping
                        TiendaNubeCustomerMapping.objects.create(
                            client=existing_customer,
                            tiendanube_id=customer_data['id'],
                            tiendanube_email=email,
                            tiendanube_document=customer_data.get('document', ''),
                            sync_status=TiendaNubeCustomerMapping.SyncStatus.SYNCED
                        )
                        
                        success_count += 1
                        
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Error procesando cliente {customer_data.get('id', 'unknown')}: {str(e)}")
            
            status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
            self.log_sync('customer', status, f'Sincronizados: {success_count}, Fallidos: {failed_count}', {"errors": errors})
            
        except Exception as e:
            self.log_sync('customer', 'error', f"Error general en sincronización de clientes: {str(e)}")
            return 0, 1
        
        return success_count, failed_count

    def sync_customer_to_tiendanube(self, client):
        """Sincroniza cliente desde Synap hacia Tiendanube (solo clientes con tag tiendanube)."""
        try:
            # Verificar que el cliente tenga tag tiendanube
            primary_contact = client.get_primary_contact_object()
            if not primary_contact or 'tiendanube' not in (primary_contact.tags or '').lower():
                return True, "Cliente no marcado para sincronización con Tiendanube"
            
            # Verificar si ya existe mapping
            mapping, created = TiendaNubeCustomerMapping.objects.get_or_create(
                client=client,
                defaults={'sync_status': TiendaNubeCustomerMapping.SyncStatus.PENDING}
            )
            
            if not created and mapping.sync_status == TiendaNubeCustomerMapping.SyncStatus.SYNCED:
                return True, "Cliente ya sincronizado"
            
            # --- Obtener datos del Contact primario ---
            if primary_contact:
                # Usar datos del Contact primario
                customer_data = {
                    'name': primary_contact.display_name,
                    'email': primary_contact.email or client.email,
                    'document': primary_contact.notes or client.document_number or '',
                    'phone': primary_contact.phone or client.phone or '',
                    'address': primary_contact.full_address or client.get_full_address() or '',
                }
            else:
                # Usar datos del cliente (fallback)
                customer_data = {
                    'name': client.name,
                    'email': client.email,
                    'document': client.document_number or '',
                    'phone': client.phone or '',
                    'address': client.get_full_address() or '',
                }
            
            if created:
                # Crear nuevo cliente en Tiendanube
                response = requests.post(f"{self.BASE_URL}/customers", headers=self.headers, json=customer_data)
            else:
                # Actualizar cliente existente
                response = requests.put(f"{self.BASE_URL}/customers/{mapping.tiendanube_id}", headers=self.headers, json=customer_data)
            
            if response.status_code in [200, 201]:
                customer_response = response.json()
                mapping.tiendanube_id = customer_response['id']
                mapping.tiendanube_email = customer_data['email']
                mapping.tiendanube_document = customer_data['document']
                mapping.sync_status = TiendaNubeCustomerMapping.SyncStatus.SYNCED
                mapping.save()
                
                self.log_sync('customer', 'success', f'Cliente {client.name} sincronizado exitosamente')
                return True, "Cliente sincronizado exitosamente"
            else:
                mapping.sync_status = TiendaNubeCustomerMapping.SyncStatus.ERROR
                mapping.error_message = f"Error {response.status_code}: {response.text}"
                mapping.save()
                
                self.log_sync('customer', 'error', f'Error sincronizando cliente {client.name}: {response.text}')
                return False, f"Error {response.status_code}: {response.text}"
                
        except Exception as e:
            self.log_sync('customer', 'error', f'Error sincronizando cliente {client.name}: {str(e)}')
            return False, str(e)

    def sync_all_customers_to_tiendanube(self, limit=100, offset=0):
        """Sincroniza todos los clientes con tag tiendanube hacia Tiendanube."""
        success_count = 0
        failed_count = 0
        errors = []
        
        try:
            # Obtener clientes que tienen contactos con tag tiendanube
            contacts_with_tiendanube = Contact.objects.filter(
                tags__icontains='tiendanube',
                is_active=True
            )
            
            # Obtener clientes relacionados con estos contactos
            client_ids = set()
            for contact in contacts_with_tiendanube:
                for relationship in contact.relationships.filter(
                    content_type__model='client',
                    is_active=True
                ):
                    client_ids.add(relationship.object_id)
            
            # Sincronizar clientes
            clients = Client.objects.filter(id__in=list(client_ids)[offset:offset+limit])
            
            for client in clients:
                try:
                    success, message = self.sync_customer_to_tiendanube(client)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"Error sincronizando {client.name}: {message}")
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Error procesando {client.name}: {str(e)}")
            
            status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
            self.log_sync('customer', status, f'Sincronizados: {success_count}, Fallidos: {failed_count}', {"errors": errors})
            
        except Exception as e:
            self.log_sync('customer', 'error', f"Error general en sincronización de clientes: {str(e)}")
            return 0, 1
        
        return success_count, failed_count

    # ----------------------
    # Stock Management Methods
    # ----------------------
    def sync_stock_to_tiendanube(self, product=None):
        """Sincroniza stock desde Synap hacia Tiendanube (solo productos con tag tiendanube)."""
        success_count = 0
        failed_count = 0
        
        try:
            if product:
                # Verificar que el producto tenga tag tiendanube
                if not product.tags or 'tiendanube' not in product.tags.lower():
                    logger.info(f"Producto {product.sku} no tiene tag tiendanube, saltando sincronización de stock")
                    return 0, 0
                
                # Sincronizar producto específico
                success, error = self._sync_single_product_stock(product)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            else:
                # Sincronizar solo productos con tag tiendanube y mapeados
                mappings = TiendaNubeProductMapping.objects.filter(
                    sync_enabled=True,
                    sync_stock=True,
                    product__tags__icontains='tiendanube'  # Solo productos con tag tiendanube
                )
                
                for mapping in mappings:
                    success, error = self._sync_single_product_stock(mapping.product)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
            
            status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
            self.log_sync('stock', status, f'Sincronizados: {success_count}, Fallidos: {failed_count}')
            return success_count, failed_count
            
        except Exception as e:
            self.log_sync('stock', 'error', f"Error general en sincronización de stock: {str(e)}")
            return 0, 1

    def _sync_single_product_stock(self, product):
        """Sincroniza stock de un producto específico (solo si tiene tag tiendanube)."""
        try:
            # Verificar que el producto tenga tag tiendanube
            if not product.tags or 'tiendanube' not in product.tags.lower():
                logger.info(f"[STOCK] Producto {product.sku} no tiene tag tiendanube, no sincronizar")
                return True, "Producto no tiene tag tiendanube, no sincronizar"
            
            mapping = TiendaNubeProductMapping.objects.get(product=product)
            
            # Obtener stock disponible en el almacén de Tiendanube
            tiendanube_warehouse = self.config.tiendanube_warehouse if self.config else None
            if not tiendanube_warehouse:
                logger.error(f"[STOCK] No hay almacén de Tiendanube configurado para producto {product.sku}")
                return False, "No hay almacén de Tiendanube configurado"
            
            # Calcular stock disponible
            stock_quants = StockQuant.objects.filter(
                product=product,
                location__warehouse=tiendanube_warehouse
            )
            available_stock = sum(quant.available_quantity for quant in stock_quants)
            logger.info(f"[STOCK] Stock calculado para {product.sku}: {available_stock} unidades en almacén {tiendanube_warehouse}")
            
            # Actualizar stock en Tiendanube
            if mapping.tiendanube_variant_id:
                # Producto con variantes
                stock_data = {
                    'stock': int(available_stock)
                }
                url = f"{self.BASE_URL}/products/{mapping.tiendanube_id}/variants/{mapping.tiendanube_variant_id}/stock"
                logger.info(f"[STOCK] Enviando stock a variante: URL={url} DATA={stock_data}")
                response = requests.put(
                    url,
                    headers=self.headers,
                    json=stock_data
                )
                self.log_api_response("update_variant_stock", url, stock_data, response, product.sku)
            else:
                # Producto simple
                stock_data = {
                    'stock': int(available_stock)
                }
                url = f"{self.BASE_URL}/products/{mapping.tiendanube_id}/stock"
                logger.info(f"[STOCK] Enviando stock a producto simple: URL={url} DATA={stock_data}")
                response = requests.put(
                    url,
                    headers=self.headers,
                    json=stock_data
                )
                self.log_api_response("update_product_stock", url, stock_data, response, product.sku)
            
            if response.status_code in [200, 201]:
                logger.info(f"[STOCK] Stock actualizado correctamente para {product.sku} (status {response.status_code})")
                return True, None
            else:
                logger.error(f"[STOCK] Error actualizando stock para {product.sku}: {response.status_code} - {response.text}")
                return False, f"Error {response.status_code}: {response.text}"
        except TiendaNubeProductMapping.DoesNotExist:
            logger.error(f"[STOCK] Producto {product.sku} no tiene mapping con Tiendanube para stock")
            return False, "No mapping"
        except Exception as e:
            logger.error(f"[STOCK] Error general sincronizando stock para {product.sku}: {str(e)}")
            return False, str(e)

    # ----------------------
    # Restock Management Methods
    # ----------------------
    def check_and_restock_products(self):
        """Verifica stock y ejecuta reabastecimiento automático (solo productos con tag tiendanube)."""
        success_count = 0
        failed_count = 0
        
        try:
            # Obtener productos que necesitan reabastecimiento
            products_to_restock = self._get_products_needing_restock()
            
            for product, current_stock in products_to_restock:
                try:
                    success = self._execute_restock_for_product(product, current_stock)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error en reabastecimiento de {product.sku}: {str(e)}")
            
            status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
            self.log_sync('restock', status, f'Reabastecidos: {success_count}, Fallidos: {failed_count}')
            return success_count, failed_count
            
        except Exception as e:
            self.log_sync('restock', 'error', f"Error general en reabastecimiento: {str(e)}")
            return 0, 1

    def _get_products_needing_restock(self):
        """Obtiene productos que necesitan reabastecimiento (solo productos con tag tiendanube)."""
        products_needing_restock = []
        
        # Obtener almacén de Tiendanube
        tiendanube_warehouse = self.config.tiendanube_warehouse if self.config else None
        if not tiendanube_warehouse:
            return products_needing_restock
        
        # Obtener solo productos mapeados con Tiendanube que tengan tag tiendanube
        mappings = TiendaNubeProductMapping.objects.filter(
            sync_enabled=True,
            restock_enabled=True,
            product__tags__icontains='tiendanube'  # Solo productos con tag tiendanube
        )
        
        for mapping in mappings:
            product = mapping.product
            
            # Calcular stock actual en almacén de Tiendanube
            stock_quants = StockQuant.objects.filter(
                product=product,
                location__warehouse=tiendanube_warehouse
            )
            current_stock = sum(quant.available_quantity for quant in stock_quants)
            
            # Obtener umbral de reabastecimiento
            threshold = mapping.restock_threshold or self.config.restock_threshold
            
            if current_stock <= threshold:
                products_needing_restock.append((product, current_stock))
        
        return products_needing_restock

    def sync_all_stock_to_tiendanube(self, limit=100, offset=0):
        """Sincroniza stock de todos los productos con tag tiendanube hacia Tiendanube."""
        success_count = 0
        failed_count = 0
        errors = []
        
        try:
            # Obtener productos con tag tiendanube
            products_with_tiendanube = Product.objects.filter(
                tags__icontains='tiendanube',
                is_published=True  # Solo productos publicados
            )[offset:offset+limit]
            
            for product in products_with_tiendanube:
                try:
                    # Verificar si tiene mapping
                    mapping = TiendaNubeProductMapping.objects.filter(product=product).first()
                    
                    if mapping:
                        # Sincronizar stock de producto existente
                        success, error = self._sync_single_product_stock(product)
                        if success:
                            success_count += 1
                        else:
                            failed_count += 1
                            errors.append(f"Error sincronizando stock de {product.sku}: {error}")
                    else:
                        # Producto con tag tiendanube pero sin mapping - crear mapping primero
                        logger.info(f"Producto {product.sku} tiene tag tiendanube pero no mapping, creando...")
                        
                        # Crear producto en Tiendanube primero
                        tiene_variantes = hasattr(product, 'variants') and product.variants.exists()
                        product_data = {
                            "name": product.name,
                            "description": product.description,
                            "sku": product.sku,
                            "handle": product.handle,
                            "published": product.is_published,
                        }
                        if tiene_variantes:
                            variants_list = []
                            for variante in product.variants.all():
                                variants_list.append({
                                    "name": variante.name,
                                    "sku": variante.sku,
                                    "price": float(variante.price),
                                })
                            product_data["variants"] = variants_list
                        else:
                            product_data["price"] = float(product.price)
                        
                        # Agregar imágenes
                        images = []
                        site_url = get_site_url()
                        for img in product.images.all():
                            if site_url:
                                image_url = site_url + img.image.url
                            else:
                                image_url = img.image.url
                            images.append({"src": image_url})
                        
                        if images:
                            product_data["images"] = images
                        
                        response = self.create_product(product_data)
                        
                        if response:
                            # Crear mapping
                            mapping = TiendaNubeProductMapping.objects.create(
                                product=product,
                                tiendanube_id=response['id'],
                                tiendanube_handle=response.get('handle', ''),
                                sync_status=TiendaNubeProductMapping.SyncStatus.SYNCED,
                                sync_enabled=True,
                                sync_stock=True  # Habilitar sincronización de stock
                            )
                            # Actualizar producto con tiendanube_id
                            product.tiendanube_id = response['id']
                            product.tiendanube_url = response.get('permalink', '')
                            product.save(update_fields=['tiendanube_id', 'tiendanube_url'])
                            
                            # Ahora sincronizar stock
                            success, error = self._sync_single_product_stock(product)
                            if success:
                                success_count += 1
                            else:
                                failed_count += 1
                                errors.append(f"Error sincronizando stock de {product.sku}: {error}")
                        else:
                            failed_count += 1
                            errors.append(f"Error creando producto {product.sku} en Tiendanube")
                            
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Error procesando producto {product.sku}: {str(e)}")
            
            status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
            self.log_sync('stock', status, f'Sincronizados: {success_count}, Fallidos: {failed_count}', {"errors": errors})
            
        except Exception as e:
            self.log_sync('stock', 'error', f"Error general en sincronización de stock: {str(e)}")
            return 0, 1
        
        return success_count, failed_count

    def _execute_restock_for_product(self, product, current_stock):
        """Ejecuta reabastecimiento para un producto específico."""
        try:
            # Obtener regla de reabastecimiento
            rule = self._get_restock_rule_for_product(product)
            if not rule:
                return False
            
            # Calcular cantidad a reabastecer
            restock_quantity = self._get_restock_quantity(product, rule)
            
            # Ejecutar acción según tipo de regla
            if rule.action_type == TiendaNubeRestockRule.ActionType.TRANSFER:
                return self._execute_transfer_restock(product, rule, restock_quantity)
            elif rule.action_type == TiendaNubeRestockRule.ActionType.PURCHASE:
                return self._execute_purchase_restock(product, rule, restock_quantity)
            elif rule.action_type == TiendaNubeRestockRule.ActionType.NOTIFICATION:
                return self._execute_notification_restock(product, rule, restock_quantity)
            
            return False
            
        except Exception as e:
            logger.error(f"Error ejecutando reabastecimiento para {product.sku}: {str(e)}")
            return False

    def _get_restock_rule_for_product(self, product):
        """Obtiene regla de reabastecimiento para un producto."""
        # Buscar regla específica para el producto
        rule = TiendaNubeRestockRule.objects.filter(
            product=product,
            is_active=True
        ).first()
        
        if rule:
            return rule
        
        # Buscar regla por categoría
        if product.category:
            rule = TiendaNubeRestockRule.objects.filter(
                category=product.category,
                is_active=True
            ).first()
            
            if rule:
                return rule
        
        # Buscar regla global
        rule = TiendaNubeRestockRule.objects.filter(
            rule_type=TiendaNubeRestockRule.RuleType.GLOBAL,
            is_active=True
        ).first()
        
        return rule

    def _get_restock_quantity(self, product, rule):
        """Obtiene cantidad de reabastecimiento para un producto."""
        mapping = TiendaNubeProductMapping.objects.get(product=product)
        
        # Usar cantidad específica del producto si está configurada
        if mapping.restock_quantity:
            return mapping.restock_quantity
        
        # Usar cantidad de la regla
        return rule.restock_quantity

    def _execute_transfer_restock(self, product, rule, quantity):
        """Ejecuta transferencia interna de reabastecimiento."""
        try:
            with transaction.atomic():
                # Crear movimiento de stock
                source_location = Location.objects.filter(
                    warehouse=rule.source_warehouse,
                    is_active=True
                ).first()
                
                destination_location = Location.objects.filter(
                    warehouse=rule.destination_warehouse,
                    is_active=True
                ).first()
                
                if not source_location or not destination_location:
                    return False
                
                stock_move = StockMove.objects.create(
                    empresa=product.empresa,
                    branch=product.branch,
                    product=product,
                    location_from=source_location,
                    location_to=destination_location,
                    quantity=quantity,
                    move_type='internal_transfer',
                    reference='Tiendanube Restock',
                    state='confirmed'
                )
                
                # Crear log de reabastecimiento
                TiendaNubeRestockLog.objects.create(
                    product=product,
                    rule=rule,
                    action_type=TiendaNubeRestockLog.ActionType.TRANSFER,
                    status=TiendaNubeRestockLog.Status.COMPLETED,
                    quantity_requested=quantity,
                    quantity_processed=quantity,
                    stock_move=stock_move,
                    message=f"Transferencia automática de {source_location.name} a {destination_location.name}"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Error en transferencia de reabastecimiento: {str(e)}")
            return False

    def _execute_purchase_restock(self, product, rule, quantity):
        """Ejecuta orden de compra de reabastecimiento."""
        try:
            # TODO: Implementar creación de orden de compra
            # Por ahora, solo crear log de notificación
            TiendaNubeRestockLog.objects.create(
                product=product,
                rule=rule,
                action_type=TiendaNubeRestockLog.ActionType.PURCHASE,
                status=TiendaNubeRestockLog.Status.PENDING,
                quantity_requested=quantity,
                message="Orden de compra de reabastecimiento pendiente de implementación"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error en orden de compra de reabastecimiento: {str(e)}")
            return False

    def _execute_notification_restock(self, product, rule, quantity):
        """Ejecuta notificación de reabastecimiento."""
        try:
            TiendaNubeRestockLog.objects.create(
                product=product,
                rule=rule,
                action_type=TiendaNubeRestockLog.ActionType.NOTIFICATION,
                status=TiendaNubeRestockLog.Status.COMPLETED,
                quantity_requested=quantity,
                message=f"Notificación de reabastecimiento enviada para {product.sku}"
            )
            
            # TODO: Implementar envío de notificaciones por email
            return True
            
        except Exception as e:
            logger.error(f"Error en notificación de reabastecimiento: {str(e)}")
            return False

    # ----------------------
    # Product Sync Methods (Enhanced)
    # ----------------------
    def sync_products_from_tiendanube(self, limit=100, offset=0):
        """Sincroniza productos locales pendientes hacia TiendaNube (solo productos con tag tiendanube)."""
        from .models import TiendaNubeProductMapping
        success_count = 0
        failed_count = 0
        errors = []
        
        logger.info(f"🚀 Iniciando sincronización de productos hacia Tiendanube (limit: {limit}, offset: {offset})")
        
        # Filtrar solo productos con tag tiendanube
        productos_pendientes = Product.objects.filter(
            tiendanube_id__isnull=True,
            tags__icontains='tiendanube'
        ).all()[offset:offset+limit]
        
        logger.info(f"📦 Encontrados {productos_pendientes.count()} productos pendientes de sincronización")
        
        for producto in productos_pendientes:
            try:
                logger.info(f"🔄 Procesando producto: {producto.sku} - {producto.name}")
                
                # Validar datos del producto antes de sincronizar
                product_data, validation_errors, validation_warnings = self.validate_product_data(producto, "create")
                
                if validation_errors:
                    error_msg = f"Error de validación en producto {producto.sku}: {', '.join(validation_errors)}"
                    logger.error(f"❌ {error_msg}")
                    errors.append(error_msg)
                    failed_count += 1
                    continue
                
                if validation_warnings:
                    logger.warning(f"⚠️ Advertencias en producto {producto.sku}: {', '.join(validation_warnings)}")
                
                # Crear producto en Tiendanube
                response = self.create_product(product_data)
                
                if response:
                    # Crear mapping
                    TiendaNubeProductMapping.objects.create(
                        product=producto,
                        tiendanube_id=response['id'],
                        tiendanube_handle=response.get('handle', ''),
                        sync_status=TiendaNubeProductMapping.SyncStatus.SYNCED,
                        sync_enabled=True
                    )
                    # Actualizar producto con tiendanube_id
                    producto.tiendanube_id = response['id']
                    producto.tiendanube_url = response.get('permalink', '')
                    producto.save(update_fields=['tiendanube_id', 'tiendanube_url'])
                    
                    logger.info(f"✅ Producto {producto.sku} sincronizado exitosamente (TN ID: {response['id']})")
                    success_count += 1
                else:
                    error_msg = f"Error creando producto {producto.sku} en Tiendanube"
                    logger.error(f"❌ {error_msg}")
                    errors.append(error_msg)
                    failed_count += 1
                    
            except Exception as e:
                error_msg = f"Error procesando producto {producto.sku}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)
                failed_count += 1
        
        status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
        self.log_sync('product', status, f'Sincronizados: {success_count}, Fallidos: {failed_count}', {"errors": errors})
        
        logger.info(f"🏁 Sincronización completada: {success_count} exitosos, {failed_count} fallidos")
        return success_count, failed_count

    def sync_all_products_to_tiendanube(self, limit=100, offset=0):
        """Sincroniza todos los productos con tag tiendanube hacia Tiendanube."""
        success_count = 0
        failed_count = 0
        errors = []
        
        logger.info(f"🚀 Iniciando sincronización completa de productos hacia Tiendanube (limit: {limit}, offset: {offset})")
        
        try:
            # Obtener productos con tag tiendanube
            products_with_tiendanube = Product.objects.filter(
                tags__icontains='tiendanube',
                is_published=True  # Solo productos publicados
            )[offset:offset+limit]
            
            logger.info(f"📦 Encontrados {products_with_tiendanube.count()} productos con tag tiendanube")
            
            for producto in products_with_tiendanube:
                try:
                    logger.info(f"🔄 Procesando producto: {producto.sku} - {producto.name}")
                    
                    # Verificar si ya tiene mapping
                    mapping = TiendaNubeProductMapping.objects.filter(product=producto).first()
                    
                    if mapping:
                        # Actualizar producto existente
                        logger.info(f"🔄 Actualizando producto existente: {producto.sku} (TN ID: {mapping.tiendanube_id})")
                        
                        # Validar datos del producto antes de actualizar
                        product_data, validation_errors, validation_warnings = self.validate_product_data(producto, "update")
                        
                        if validation_errors:
                            error_msg = f"Error de validación en producto {producto.sku}: {', '.join(validation_errors)}"
                            logger.error(f"❌ {error_msg}")
                            errors.append(error_msg)
                            failed_count += 1
                            continue
                        
                        if validation_warnings:
                            logger.warning(f"⚠️ Advertencias en producto {producto.sku}: {', '.join(validation_warnings)}")
                        
                        success = self.sync_product_update(producto)
                        if success:
                            success_count += 1
                            logger.info(f"✅ Producto {producto.sku} actualizado exitosamente")
                        else:
                            failed_count += 1
                            errors.append(f"Error actualizando producto {producto.sku}")
                            logger.error(f"❌ Error actualizando producto {producto.sku}")
                    else:
                        # Crear nuevo producto en Tiendanube
                        logger.info(f"🆕 Creando nuevo producto: {producto.sku}")
                        
                        # Validar datos del producto antes de crear
                        product_data, validation_errors, validation_warnings = self.validate_product_data(producto, "create")
                        
                        if validation_errors:
                            error_msg = f"Error de validación en producto {producto.sku}: {', '.join(validation_errors)}"
                            logger.error(f"❌ {error_msg}")
                            errors.append(error_msg)
                            failed_count += 1
                            continue
                        
                        if validation_warnings:
                            logger.warning(f"⚠️ Advertencias en producto {producto.sku}: {', '.join(validation_warnings)}")
                        
                        response = self.create_product(product_data)
                        
                        if response:
                            # Crear mapping
                            TiendaNubeProductMapping.objects.create(
                                product=producto,
                                tiendanube_id=response['id'],
                                tiendanube_handle=response.get('handle', ''),
                                sync_status=TiendaNubeProductMapping.SyncStatus.SYNCED,
                                sync_enabled=True
                            )
                            # Actualizar producto con tiendanube_id
                            producto.tiendanube_id = response['id']
                            producto.tiendanube_url = response.get('permalink', '')
                            producto.save(update_fields=['tiendanube_id', 'tiendanube_url'])
                            
                            logger.info(f"✅ Producto {producto.sku} creado exitosamente (TN ID: {response['id']})")
                            success_count += 1
                        else:
                            failed_count += 1
                            errors.append(f"Error creando producto {producto.sku} en Tiendanube")
                            logger.error(f"❌ Error creando producto {producto.sku} en Tiendanube")
                            
                except Exception as e:
                    error_msg = f"Error procesando producto {producto.sku}: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    errors.append(error_msg)
                    failed_count += 1
            
            status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
            self.log_sync('product', status, f'Sincronizados: {success_count}, Fallidos: {failed_count}', {"errors": errors})
            
        except Exception as e:
            error_msg = f"Error general en sincronización de productos: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.log_sync('product', 'error', error_msg)
            return 0, 1
        
        logger.info(f"🏁 Sincronización completa finalizada: {success_count} exitosos, {failed_count} fallidos")
        return success_count, failed_count

    def sync_pending_products_to_tiendanube(self):
        """Sincroniza productos pendientes con tag tiendanube hacia Tiendanube."""
        success_count = 0
        failed_count = 0
        errors = []
        
        try:
            # Obtener productos con tag tiendanube que necesitan sincronización
            products_to_sync = Product.objects.filter(
                tags__icontains='tiendanube',
                is_published=True
            ).exclude(
                tiendanubeproductmapping__sync_status=TiendaNubeProductMapping.SyncStatus.SYNCED
            )
            
            logger.info(f"🔄 Sincronizando {products_to_sync.count()} productos pendientes...")
            
            for product in products_to_sync:
                try:
                    # Verificar si ya tiene mapping
                    mapping = TiendaNubeProductMapping.objects.filter(product=product).first()
                    
                    if mapping:
                        # Producto ya existe en Tiendanube, actualizar
                        success = self.sync_product_update(product)
                        if success:
                            success_count += 1
                        else:
                            failed_count += 1
                            errors.append(f"Error actualizando producto {product.sku}")
                    else:
                        # Producto nuevo, crear en Tiendanube
                        product_data, validation_errors, validation_warnings = self.validate_product_data(product, "create")
                        
                        if validation_errors:
                            failed_count += 1
                            errors.append(f"Error de validación en {product.sku}: {', '.join(validation_errors)}")
                            continue
                        
                        response = self.create_product(product_data)
                        
                        if response:
                            # Crear mapping
                            TiendaNubeProductMapping.objects.create(
                                product=product,
                                tiendanube_id=response['id'],
                                tiendanube_handle=response.get('handle', ''),
                                sync_status=TiendaNubeProductMapping.SyncStatus.SYNCED,
                                sync_enabled=True
                            )
                            # Actualizar producto con tiendanube_id
                            product.tiendanube_id = response['id']
                            product.tiendanube_url = response.get('permalink', '')
                            product.save(update_fields=['tiendanube_id', 'tiendanube_url'])
                            
                            logger.info(f"✅ Producto {product.sku} sincronizado exitosamente (TN ID: {response['id']})")
                            success_count += 1
                        else:
                            error_msg = f"Error creando producto {product.sku} en Tiendanube"
                            logger.error(f"❌ {error_msg}")
                            errors.append(error_msg)
                            failed_count += 1
                            
                except Exception as e:
                    error_msg = f"Error procesando producto {product.sku}: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    errors.append(error_msg)
                    failed_count += 1
            
            status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
            self.log_sync('product', status, f'Sincronizados: {success_count}, Fallidos: {failed_count}', {"errors": errors})
            
        except Exception as e:
            error_msg = f"Error general en sincronización de productos pendientes: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.log_sync('product', 'error', error_msg)
            return 0, 1
        
        logger.info(f"🏁 Sincronización de productos pendientes finalizada: {success_count} exitosos, {failed_count} fallidos")
        return success_count, failed_count

    def sync_product_update(self, producto):
        """Sync product update to Tiendanube (solo productos con tag tiendanube)."""
        try:
            # Verificar que el producto tenga tag tiendanube
            if not producto.tags or 'tiendanube' not in producto.tags.lower():
                logger.info(f"ℹ️ Producto {producto.sku} no tiene tag tiendanube, saltando actualización")
                return True  # No es un producto de Tiendanube, no sincronizar
            
            mapping = TiendaNubeProductMapping.objects.get(product=producto)
            
            logger.info(f"🔄 Actualizando producto {producto.sku} (TN ID: {mapping.tiendanube_id})")
            
            # Validar datos del producto antes de actualizar
            product_data, validation_errors, validation_warnings = self.validate_product_data(producto, "update")
            
            if validation_errors:
                logger.error(f"❌ Error de validación en producto {producto.sku}: {', '.join(validation_errors)}")
                return False
            
            if validation_warnings:
                logger.warning(f"⚠️ Advertencias en producto {producto.sku}: {', '.join(validation_warnings)}")
            
            response = self.update_product(mapping.tiendanube_id, product_data)
            
            if response:
                # Actualizar precio usando endpoint de variantes
                price_success = self.update_product_price(producto)
                mapping.sync_status = TiendaNubeProductMapping.SyncStatus.SYNCED if price_success else TiendaNubeProductMapping.SyncStatus.ERROR
                mapping.error_message = "" if price_success else "Error actualizando precio"
                mapping.save()
                if price_success:
                    logger.info(f"✅ Producto {producto.sku} actualizado exitosamente en Tiendanube (incluyendo precio)")
                else:
                    logger.error(f"❌ Producto {producto.sku} actualizado pero error en precio en Tiendanube")
                return price_success
            else:
                mapping.sync_status = TiendaNubeProductMapping.SyncStatus.ERROR
                mapping.error_message = "Error updating product"
                mapping.save()
                logger.error(f"❌ Error actualizando producto {producto.sku} en Tiendanube")
                return False
                
        except TiendaNubeProductMapping.DoesNotExist:
            logger.error(f"❌ Producto {producto.sku} no tiene mapping con Tiendanube")
            return False
        except Exception as e:
            logger.error(f"❌ Error actualizando producto {producto.sku}: {str(e)}")
            return False

    def update_product_price(self, producto):
        """
        Actualiza el precio del producto en Tiendanube usando el endpoint de variantes.
        Si el producto no tiene variantes, crea una variante si es necesario.
        """
        try:
            mapping = TiendaNubeProductMapping.objects.get(product=producto)
            product_id = mapping.tiendanube_id
            logger.info(f"🔄 Actualizando precio para producto {producto.sku} (TN ID: {product_id})")

            # Obtener variantes desde Tiendanube
            url_variants = f"{self.BASE_URL}/products/{product_id}/variants"
            response = requests.get(url_variants, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"❌ No se pudieron obtener variantes para producto {producto.sku}: {response.text}")
                return False
            variants = response.json()

            if not variants:
                # Producto simple sin variantes, crear variante
                logger.info(f"ℹ️ Producto {producto.sku} no tiene variantes en Tiendanube, creando variante...")
                variant_data = {
                    "name": producto.name,
                    "sku": producto.sku,
                    "price": float(producto.price),
                }
                url_create_variant = f"{self.BASE_URL}/products/{product_id}/variants"
                resp_create = requests.post(url_create_variant, headers=self.headers, json=variant_data)
                self.log_api_response("create_variant", url_create_variant, variant_data, resp_create, producto.sku)
                if resp_create.status_code in [200, 201]:
                    logger.info(f"✅ Variante creada y precio actualizado para producto {producto.sku}")
                    return True
                else:
                    logger.error(f"❌ Error creando variante para producto {producto.sku}: {resp_create.text}")
                    return False
            else:
                # Actualizar precio de cada variante
                for variant in variants:
                    variant_id = variant['id']
                    price_data = {"price": float(producto.price)}
                    url_update = f"{self.BASE_URL}/products/{product_id}/variants/{variant_id}"
                    resp_update = requests.put(url_update, headers=self.headers, json=price_data)
                    self.log_api_response("update_variant_price", url_update, price_data, resp_update, producto.sku)
                    if resp_update.status_code in [200, 201]:
                        logger.info(f"✅ Precio actualizado para variante {variant_id} de producto {producto.sku}")
                    else:
                        logger.error(f"❌ Error actualizando precio de variante {variant_id} para producto {producto.sku}: {resp_update.text}")
                        return False
                return True
        except TiendaNubeProductMapping.DoesNotExist:
            logger.error(f"❌ Producto {producto.sku} no tiene mapping con Tiendanube para actualizar precio")
            return False
        except Exception as e:
            logger.error(f"❌ Error actualizando precio en Tiendanube para producto {producto.sku}: {str(e)}")
            return False

    # ----------------------
    # Webhook Methods (Enhanced)
    # ----------------------
    def create_webhook(self, webhook_url):
        """Create a webhook in TiendaNube."""
        try:
            webhook_data = {
                "url": webhook_url,
                "events": [
                    "product/created",
                    "product/updated",
                    "product/deleted",
                    "order/created",
                    "order/updated",
                    "order/cancelled",
                    "customer/created",
                    "customer/updated"
                ]
            }
            
            response = requests.post(f"{self.BASE_URL}/webhooks", headers=self.headers, json=webhook_data)
            
            if response.status_code in [200, 201]:
                webhook_response = response.json()
                return webhook_response
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
                
        except Exception as e:
            raise Exception(f"Failed to create webhook: {str(e)}")

    def handle_webhook(self, webhook_data):
        """Handle incoming webhook from TiendaNube."""
        try:
            webhook_type = webhook_data.get('type')
            webhook_id = webhook_data.get('id')
            
            # Log the webhook
            self.log_sync('webhook', 'success', f'Webhook {webhook_type} received', webhook_data)
            
            # Process based on webhook type
            if webhook_type == 'product/created':
                self._handle_product_webhook(webhook_data, 'created')
            elif webhook_type == 'product/updated':
                self._handle_product_webhook(webhook_data, 'updated')
            elif webhook_type == 'order/created':
                self._handle_order_webhook(webhook_data, 'created')
            elif webhook_type == 'order/updated':
                self._handle_order_webhook(webhook_data, 'updated')
            elif webhook_type == 'customer/created':
                self._handle_customer_webhook(webhook_data, 'created')
            elif webhook_type == 'customer/updated':
                self._handle_customer_webhook(webhook_data, 'updated')
            
            return True
            
        except Exception as e:
            self.log_sync('webhook', 'error', f'Error processing webhook: {str(e)}', webhook_data)
            return False

    def _handle_product_webhook(self, webhook_data, action):
        """Handle product webhook events."""
        try:
            product_data = webhook_data.get('data', {})
            tiendanube_id = product_data.get('id')
            
            if action == 'created':
                # Crear producto en Synap
                self._create_product_from_tiendanube(product_data)
            elif action == 'updated':
                # Actualizar producto en Synap
                self._update_product_from_tiendanube(product_data)
                
        except Exception as e:
            logger.error(f"Error handling product webhook: {str(e)}")

    def _handle_order_webhook(self, webhook_data, action):
        """Handle order webhook events."""
        try:
            order_data = webhook_data.get('data', {})
            
            if action == 'created':
                # Sincronizar pedido desde Tiendanube
                self.sync_orders_from_tiendanube(limit=1)
            elif action == 'updated':
                # Actualizar pedido existente
                self._update_order_from_tiendanube(order_data)
                
        except Exception as e:
            logger.error(f"Error handling order webhook: {str(e)}")

    def _handle_customer_webhook(self, webhook_data, action):
        """Handle customer webhook events."""
        try:
            customer_data = webhook_data.get('data', {})
            
            if action == 'created':
                # Crear cliente en Synap
                self._create_customer_from_tiendanube(customer_data)
            elif action == 'updated':
                # Actualizar cliente en Synap
                self._update_customer_from_tiendanube(customer_data)
                
        except Exception as e:
            logger.error(f"Error handling customer webhook: {str(e)}")

    # ----------------------
    # Webhook Handler Methods
    # ----------------------
    def _create_product_from_tiendanube(self, product_data):
        """Crear producto en Synap desde datos de Tiendanube."""
        try:
            # Verificar si ya existe el producto
            tiendanube_id = product_data.get('id')
            if TiendaNubeProductMapping.objects.filter(tiendanube_id=tiendanube_id).exists():
                return
            
            # Crear producto básico
            product = Product.objects.create(
                name=product_data.get('name', 'Producto Tiendanube'),
                sku=product_data.get('sku', f"TN_{tiendanube_id}"),
                description=product_data.get('description', ''),
                price=Decimal(str(product_data.get('price', 0))),
                is_published=product_data.get('published', True),
                tiendanube_id=tiendanube_id,
                tiendanube_url=product_data.get('permalink', ''),
                tags='tiendanube',  # Nuevo producto con tag tiendanube
                # Usar primera empresa y sucursal disponibles
                empresa=Empresa.objects.first(),
                branch=Branch.objects.first()
            )
            
            # Crear mapping
            TiendaNubeProductMapping.objects.create(
                product=product,
                tiendanube_id=tiendanube_id,
                tiendanube_handle=product_data.get('handle', ''),
                sync_status=TiendaNubeProductMapping.SyncStatus.SYNCED,
                sync_enabled=True
            )
            
            logger.info(f"Producto creado desde Tiendanube: {product.sku}")
            
        except Exception as e:
            logger.error(f"Error creando producto desde Tiendanube: {str(e)}")

    def _update_product_from_tiendanube(self, product_data):
        """Actualizar producto en Synap desde datos de Tiendanube."""
        try:
            tiendanube_id = product_data.get('id')
            mapping = TiendaNubeProductMapping.objects.get(tiendanube_id=tiendanube_id)
            product = mapping.product
            
            # Actualizar campos básicos
            product.name = product_data.get('name', product.name)
            product.description = product_data.get('description', product.description)
            product.price = Decimal(str(product_data.get('price', product.price)))
            product.is_published = product_data.get('published', product.is_published)
            product.tiendanube_url = product_data.get('permalink', product.tiendanube_url)
            
            # Agregar tag tiendanube si no existe
            if not product.tags or 'tiendanube' not in product.tags.lower():
                current_tags = product.tags or ''
                product.tags = f"{current_tags},tiendanube".strip(',')
            
            product.save()
            
            # Actualizar mapping
            mapping.sync_status = TiendaNubeProductMapping.SyncStatus.SYNCED
            mapping.save()
            
            logger.info(f"Producto actualizado desde Tiendanube: {product.sku}")
            
        except TiendaNubeProductMapping.DoesNotExist:
            logger.warning(f"Producto no encontrado para actualización: {product_data.get('id')}")
        except Exception as e:
            logger.error(f"Error actualizando producto desde Tiendanube: {str(e)}")

    def _update_order_from_tiendanube(self, order_data):
        """Actualizar pedido en Synap desde datos de Tiendanube."""
        try:
            tiendanube_id = order_data.get('id')
            mapping = TiendaNubeOrderMapping.objects.get(tiendanube_order_id=tiendanube_id)
            sales_order = mapping.sales_order
            
            # Actualizar estado del pedido según estado en Tiendanube
            tiendanube_status = order_data.get('status', '')
            if tiendanube_status == 'cancelled':
                sales_order.state = SalesOrderStates.CANCELLED
            elif tiendanube_status == 'paid':
                sales_order.state = SalesOrderStates.CONFIRMED
            elif tiendanube_status == 'shipped':
                sales_order.state = SalesOrderStates.DELIVERED
            
            sales_order.save()
            
            # Actualizar mapping
            mapping.sync_status = TiendaNubeOrderMapping.SyncStatus.SYNCED
            mapping.save()
            
            logger.info(f"Pedido actualizado desde Tiendanube: {sales_order.number}")
            
        except TiendaNubeOrderMapping.DoesNotExist:
            logger.warning(f"Pedido no encontrado para actualización: {order_data.get('id')}")
        except Exception as e:
            logger.error(f"Error actualizando pedido desde Tiendanube: {str(e)}")

    def _create_customer_from_tiendanube(self, customer_data):
        """Crear cliente en Synap desde datos de Tiendanube."""
        try:
            tiendanube_id = customer_data.get('id')
            if TiendaNubeCustomerMapping.objects.filter(tiendanube_id=tiendanube_id).exists():
                return
            
            # Crear cliente
            customer = Client.objects.create(
                name=customer_data.get('name', 'Cliente Tiendanube'),
                email=customer_data.get('email', ''),
                document_number=customer_data.get('document', ''),
                type='individual' if not customer_data.get('document') else 'company',
                credit_limit=Decimal('0.00')
            )
            # --- Contact universal ---
            contact = None
            email = customer_data.get('email', '')
            document = customer_data.get('document', '')
            if email:
                contact = Contact.objects.filter(email=email).first()
            if not contact and document:
                contact = Contact.objects.filter(notes__icontains=document).first()
            if not contact:
                contact = Contact.objects.create(
                    name=customer_data.get('name', 'Cliente Tiendanube'),
                    email=email,
                    phone=customer_data.get('phone', ''),
                    address=customer_data.get('address', ''),
                    city=customer_data.get('city', ''),
                    state=customer_data.get('state', ''),
                    country=customer_data.get('country', 'Argentina'),
                    notes=document,
                    tags='tiendanube'  # Nuevo contacto con tag tiendanube
                )
            else:
                # Contact existente - agregar tag tiendanube si no existe
                if 'tiendanube' not in (contact.tags or '').lower():
                    current_tags = contact.tags or ''
                    contact.tags = f"{current_tags},tiendanube".strip(',')
                    contact.save()
            if not customer.has_contact(contact, relationship_type='primary'):
                customer.add_contact_relationship(contact, relationship_type='primary')
            # Crear mapping
            TiendaNubeCustomerMapping.objects.create(
                client=customer,
                tiendanube_id=tiendanube_id,
                tiendanube_email=email,
                tiendanube_document=customer_data.get('document', ''),
                sync_status=TiendaNubeCustomerMapping.SyncStatus.SYNCED
            )
            
            logger.info(f"Cliente creado desde Tiendanube: {customer.name}")
            
        except Exception as e:
            logger.error(f"Error creando cliente desde Tiendanube: {str(e)}")

    def _update_customer_from_tiendanube(self, customer_data):
        """Actualizar cliente en Synap desde datos de Tiendanube."""
        try:
            tiendanube_id = customer_data.get('id')
            mapping = TiendaNubeCustomerMapping.objects.get(tiendanube_id=tiendanube_id)
            customer = mapping.client
            
            # Actualizar campos básicos del cliente
            customer.name = customer_data.get('name', customer.name)
            customer.email = customer_data.get('email', customer.email)
            customer.document_number = customer_data.get('document', customer.document_number)
            customer.save()
            
            # --- Actualizar Contact primario ---
            primary_contact = customer.get_primary_contact_object()
            if primary_contact:
                # Actualizar Contact existente
                primary_contact.name = customer_data.get('name', primary_contact.name)
                primary_contact.email = customer_data.get('email', primary_contact.email)
                primary_contact.phone = customer_data.get('phone', primary_contact.phone)
                primary_contact.address = customer_data.get('address', primary_contact.address)
                primary_contact.notes = customer_data.get('document', primary_contact.notes)
                # Agregar tag tiendanube si no existe
                if 'tiendanube' not in (primary_contact.tags or '').lower():
                    current_tags = primary_contact.tags or ''
                    primary_contact.tags = f"{current_tags},tiendanube".strip(',')
                primary_contact.save()
            else:
                # Crear nuevo Contact si no existe
                contact = Contact.objects.create(
                    name=customer_data.get('name', 'Cliente Tiendanube'),
                    email=customer_data.get('email', ''),
                    phone=customer_data.get('phone', ''),
                    address=customer_data.get('address', ''),
                    notes=customer_data.get('document', ''),
                    tags='tiendanube'  # Nuevo contacto con tag tiendanube
                )
                customer.add_contact_relationship(contact, relationship_type='primary')
            
            # Actualizar mapping
            mapping.sync_status = TiendaNubeCustomerMapping.SyncStatus.SYNCED
            mapping.save()
            
            logger.info(f"Cliente actualizado desde Tiendanube: {customer.name}")
            
        except TiendaNubeCustomerMapping.DoesNotExist:
            logger.warning(f"Cliente no encontrado para actualización: {customer_data.get('id')}")
        except Exception as e:
            logger.error(f"Error actualizando cliente desde Tiendanube: {str(e)}")

    # ----------------------
    # Utility Methods
    # ----------------------
    def get_recent_logs(self, limit=20):
        """Get recent sync logs."""
        return TiendaNubeSyncLog.objects.all()[:limit]

    def log_sync(self, sync_type, status, message, details=None):
        """Log sync operation."""
        try:
            log = TiendaNubeSyncLog.objects.create(
                config=self.config,
                sync_type=sync_type,
                status=status,
                message=message,
                details=details or {}
            )
            
            # Update last sync time for config
            if self.config and status == 'success':
                self.config.last_sync = timezone.now()
                self.config.save(update_fields=['last_sync'])
            
            return log
        except Exception as e:
            logger.error(f"Error logging sync: {str(e)}")

    def get_products(self, params=None):
        """Get products from TiendaNube."""
        url = f"{self.BASE_URL}/products"
        response = requests.get(url, headers=self.headers, params=params)
        return self.handle_response(response)

    def create_product(self, product_data):
        """Create product in Tiendanube with detailed validation and logging."""
        url = f"{self.BASE_URL}/products"
        
        # Log de inicio de creación
        product_sku = product_data.get('sku', 'Unknown')
        logger.info(f"🚀 Iniciando creación de producto {product_sku} en Tiendanube")
        logger.debug(f"📤 Datos a enviar: {json.dumps(product_data, indent=2)}")
        
        try:
            response = requests.post(url, headers=self.headers, json=product_data)
            
            # Log detallado de la respuesta
            self.log_api_response("create", url, product_data, response, product_sku)
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"✅ Producto {product_sku} creado exitosamente en Tiendanube (ID: {result.get('id')})")
                return result
            else:
                logger.error(f"❌ Error creando producto {product_sku} en Tiendanube")
                return None
                
        except Exception as e:
            logger.error(f"❌ Excepción creando producto {product_sku}: {str(e)}")
            return None

    def update_product(self, tiendanube_id, product_data):
        """Update product in Tiendanube with detailed validation and logging."""
        url = f"{self.BASE_URL}/products/{tiendanube_id}"
        
        # Log de inicio de actualización
        product_sku = product_data.get('sku', 'Unknown')
        logger.info(f"🔄 Iniciando actualización de producto {product_sku} (TN ID: {tiendanube_id})")
        logger.debug(f"📤 Datos a enviar: {json.dumps(product_data, indent=2)}")
        
        try:
            response = requests.put(url, headers=self.headers, json=product_data)
            
            # Log detallado de la respuesta
            self.log_api_response("update", url, product_data, response, product_sku)
            
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"✅ Producto {product_sku} actualizado exitosamente en Tiendanube")
                return result
            else:
                logger.error(f"❌ Error actualizando producto {product_sku} en Tiendanube")
                return None
                
        except Exception as e:
            logger.error(f"❌ Excepción actualizando producto {product_sku}: {str(e)}")
            return None

    def delete_product(self, tiendanube_id):
        """Delete product from TiendaNube."""
        url = f"{self.BASE_URL}/products/{tiendanube_id}"
        response = requests.delete(url, headers=self.headers)
        return self.handle_response(response)

    def get_variants(self, product_id):
        """Get product variants from TiendaNube."""
        url = f"{self.BASE_URL}/products/{product_id}/variants"
        response = requests.get(url, headers=self.headers)
        return self.handle_response(response)

    def update_variant_stock(self, variant_id, stock):
        """Update variant stock in TiendaNube."""
        url = f"{self.BASE_URL}/variants/{variant_id}/stock"
        data = {"stock": stock}
        response = requests.put(url, headers=self.headers, json=data)
        return self.handle_response(response)

    def sync_stock(self, product_id, stock_data):
        """Sync stock for a product."""
        url = f"{self.BASE_URL}/products/{product_id}/stock"
        response = requests.put(url, headers=self.headers, json=stock_data)
        return self.handle_response(response)

    def sync_price(self, product_id, price_data):
        """Sync price for a product."""
        url = f"{self.BASE_URL}/products/{product_id}/price"
        response = requests.put(url, headers=self.headers, json=price_data)
        return self.handle_response(response)

    def get_orders(self, params=None):
        """Get orders from TiendaNube."""
        url = f"{self.BASE_URL}/orders"
        response = requests.get(url, headers=self.headers, params=params)
        return self.handle_response(response)

    def update_order_status(self, order_id, status):
        """Update order status in TiendaNube."""
        url = f"{self.BASE_URL}/orders/{order_id}"
        data = {"status": status}
        response = requests.put(url, headers=self.headers, json=data)
        return self.handle_response(response)

    def register_webhook(self, webhook_data):
        """Register webhook with TiendaNube."""
        url = f"{self.BASE_URL}/webhooks"
        response = requests.post(url, headers=self.headers, json=webhook_data)
        return self.handle_response(response)

    def delete_webhook(self, webhook_id):
        """Delete webhook from TiendaNube."""
        url = f"{self.BASE_URL}/webhooks/{webhook_id}"
        response = requests.delete(url, headers=self.headers)
        return self.handle_response(response)

    def handle_error(self, response):
        """Handle API error response."""
        try:
            error_data = response.json()
            return f"Error {response.status_code}: {error_data.get('error', response.text)}"
        except:
            return f"Error {response.status_code}: {response.text}"

    def get_headers(self):
        """Get API headers."""
        return self.headers

    def get_base_url(self):
        """Get API base URL."""
        return self.BASE_URL

    def handle_response(self, response):
        """Handle API response with detailed logging."""
        if response.status_code in [200, 201]:
            try:
                return response.json()
            except:
                return {"success": True, "message": response.text}
        else:
            logger.error(f"API Error: {response.status_code} - {response.text}")
            return None 