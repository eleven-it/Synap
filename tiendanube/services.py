from .models import (
    TiendaNubeConfig, TiendaNubeSyncLog, TiendaNubeProductMapping,
    TiendaNubeCustomerMapping, TiendaNubeOrderMapping, TiendaNubeRestockRule,
    TiendaNubeRestockLog
)
from inventory.models import Product, ProductVariant, StockQuant, Location, Warehouse, StockMove
from sales.models import Client, SalesOrder, SalesOrderLine, SalesOrderStates
from core.models import SystemConfiguration, Branch, Empresa
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import logging
import requests
import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

User = get_user_model()
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
                return customer
            except Client.DoesNotExist:
                pass
        
        if document:
            try:
                customer = Client.objects.get(document_number=document)
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
        """Sincroniza cliente desde Synap hacia Tiendanube."""
        try:
            # Verificar si ya existe mapping
            mapping, created = TiendaNubeCustomerMapping.objects.get_or_create(
                client=client,
                defaults={'sync_status': TiendaNubeCustomerMapping.SyncStatus.PENDING}
            )
            
            if not created and mapping.sync_status == TiendaNubeCustomerMapping.SyncStatus.SYNCED:
                return True, "Cliente ya sincronizado"
            
            # Preparar datos del cliente
            customer_data = {
                'name': client.name,
                'email': client.email,
                'document': client.document_number or '',
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
                mapping.tiendanube_email = client.email
                mapping.tiendanube_document = client.document_number or ''
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

    # ----------------------
    # Stock Management Methods
    # ----------------------
    def sync_stock_to_tiendanube(self, product=None):
        """Sincroniza stock desde Synap hacia Tiendanube."""
        success_count = 0
        failed_count = 0
        
        try:
            if product:
                # Sincronizar producto específico
                success, error = self._sync_single_product_stock(product)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            else:
                # Sincronizar todos los productos mapeados
                mappings = TiendaNubeProductMapping.objects.filter(
                    sync_enabled=True,
                    sync_stock=True
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
        """Sincroniza stock de un producto específico."""
        try:
            mapping = TiendaNubeProductMapping.objects.get(product=product)
            
            # Obtener stock disponible en el almacén de Tiendanube
            tiendanube_warehouse = self.config.tiendanube_warehouse if self.config else None
            if not tiendanube_warehouse:
                return False, "No hay almacén de Tiendanube configurado"
            
            # Calcular stock disponible
            stock_quants = StockQuant.objects.filter(
                product=product,
                location__warehouse=tiendanube_warehouse
            )
            
            available_stock = sum(quant.available_quantity for quant in stock_quants)
            
            # Actualizar stock en Tiendanube
            if mapping.tiendanube_variant_id:
                # Producto con variantes
                stock_data = {
                    'stock': int(available_stock)
                }
                response = requests.put(
                    f"{self.BASE_URL}/products/{mapping.tiendanube_id}/variants/{mapping.tiendanube_variant_id}/stock",
                    headers=self.headers,
                    json=stock_data
                )
            else:
                # Producto simple
                stock_data = {
                    'stock': int(available_stock)
                }
                response = requests.put(
                    f"{self.BASE_URL}/products/{mapping.tiendanube_id}/stock",
                    headers=self.headers,
                    json=stock_data
                )
            
            if response.status_code == 200:
                mapping.sync_status = TiendaNubeProductMapping.SyncStatus.SYNCED
                mapping.save()
                return True, None
            else:
                mapping.sync_status = TiendaNubeProductMapping.SyncStatus.ERROR
                mapping.error_message = f"Error {response.status_code}: {response.text}"
                mapping.save()
                return False, f"Error {response.status_code}: {response.text}"
                
        except TiendaNubeProductMapping.DoesNotExist:
            return False, "Producto no mapeado con Tiendanube"
        except Exception as e:
            return False, str(e)

    # ----------------------
    # Restock Management Methods
    # ----------------------
    def check_and_restock_products(self):
        """Verifica stock y ejecuta reabastecimiento automático."""
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
        """Obtiene productos que necesitan reabastecimiento."""
        products_needing_restock = []
        
        # Obtener almacén de Tiendanube
        tiendanube_warehouse = self.config.tiendanube_warehouse if self.config else None
        if not tiendanube_warehouse:
            return products_needing_restock
        
        # Obtener todos los productos mapeados con Tiendanube
        mappings = TiendaNubeProductMapping.objects.filter(
            sync_enabled=True,
            restock_enabled=True
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
        """Sincroniza productos locales pendientes hacia TiendaNube."""
        from .models import TiendaNubeProductMapping
        success_count = 0
        failed_count = 0
        errors = []
        productos_pendientes = Product.objects.filter(tiendanube_id__isnull=True).all()[offset:offset+limit]
        for producto in productos_pendientes:
            try:
                tiene_variantes = hasattr(producto, 'variants') and producto.variants.exists()
                product_data = {
                    "name": producto.name,
                    "description": producto.description,
                    "sku": producto.sku,
                    "handle": producto.handle,
                    "published": producto.is_published,
                }
                if tiene_variantes:
                    variants_list = []
                    for variante in producto.variants.all():
                        variants_list.append({
                            "name": variante.name,
                            "sku": variante.sku,
                            "price": float(variante.price),
                        })
                    product_data["variants"] = variants_list
                else:
                    product_data["price"] = float(producto.price)
                # --- NUEVA LÓGICA DE IMÁGENES ---
                images = []
                site_url = get_site_url()
                for img in producto.images.all():
                    if site_url:
                        image_url = site_url + img.image.url
                    else:
                        image_url = img.image.url
                    try:
                        resp = requests.head(image_url, timeout=5)
                        if resp.status_code == 200:
                            images.append({"src": image_url})
                        else:
                            logger.warning(f"Imagen no accesible (status {resp.status_code}): {image_url}")
                    except Exception as e:
                        logger.warning(f"Error accediendo a la imagen: {image_url} - {str(e)}")
                if images:
                    product_data["images"] = images
                # --- FIN NUEVA LÓGICA DE IMÁGENES ---
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
                    msg = f"Error creando producto {producto.sku}: {response}"
                    producto.tiendanube_id = None
                    producto.tiendanube_url = ""
                    producto.save()
                    failed_count += 1
                    errors.append(msg)
            except Exception as e:
                msg = f"Excepción creando producto {producto.sku}: {str(e)}"
                failed_count += 1
                errors.append(msg)
        status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'error')
        self.log_sync('product', status, f'Sincronizados: {success_count}, Fallidos: {failed_count}', {"errors": errors})
        return success_count, failed_count

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
            
            # Crear mapping
            TiendaNubeCustomerMapping.objects.create(
                client=customer,
                tiendanube_id=tiendanube_id,
                tiendanube_email=customer.email,
                tiendanube_document=customer.document_number,
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
            
            # Actualizar campos básicos
            customer.name = customer_data.get('name', customer.name)
            customer.email = customer_data.get('email', customer.email)
            customer.document_number = customer_data.get('document', customer.document_number)
            customer.save()
            
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
        """Create product in TiendaNube."""
        url = f"{self.BASE_URL}/products"
        response = requests.post(url, headers=self.headers, json=product_data)
        return self.handle_response(response)

    def update_product(self, tiendanube_id, product_data):
        """Update product in TiendaNube."""
        url = f"{self.BASE_URL}/products/{tiendanube_id}"
        response = requests.put(url, headers=self.headers, json=product_data)
        return self.handle_response(response)

    def sync_product_update(self, producto):
        """Sync product update to TiendaNube."""
        try:
            mapping = TiendaNubeProductMapping.objects.get(product=producto)
            
            product_data = {
                "name": producto.name,
                "description": producto.description,
                "published": producto.is_published,
            }
            
            if not producto.variants.exists():
                product_data["price"] = float(producto.price)
            
            # Sync images
            images = []
            site_url = get_site_url()
            for img in producto.images.all():
                if site_url:
                    image_url = site_url + img.image.url
                else:
                    image_url = img.image.url
                images.append({"src": image_url})
            
            if images:
                product_data["images"] = images
            
            response = self.update_product(mapping.tiendanube_id, product_data)
            
            if response:
                mapping.sync_status = TiendaNubeProductMapping.SyncStatus.SYNCED
                mapping.error_message = ""
                mapping.save()
                return True
            else:
                mapping.sync_status = TiendaNubeProductMapping.SyncStatus.ERROR
                mapping.error_message = "Error updating product"
                mapping.save()
                return False
                
        except TiendaNubeProductMapping.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error syncing product update: {str(e)}")
            return False

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
        """Handle API response."""
        if response.status_code in [200, 201]:
            try:
                return response.json()
            except:
                return response.text
        else:
            error_msg = self.handle_error(response)
            logger.error(f"API Error: {error_msg}")
            return None 