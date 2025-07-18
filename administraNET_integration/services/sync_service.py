import logging
from django.utils import timezone
from django.db import transaction
from django.apps import apps
from .connection_service import AdministraNETConnectionService
from administraNET_integration.models import ValidationRuleConfig
from administraNET_integration.validations.base import VALIDATION_RULES_REGISTRY
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


class AdministraNETSyncService:
    """
    Servicio para sincronizar datos entre administraNET y Synap
    """
    
    def __init__(self, config):
        """
        Inicializar servicio con configuración
        
        Args:
            config: Instancia de AdministraNETConfig
        """
        self.config = config
        self.connection_service = AdministraNETConnectionService(config)
    
    def sync_all(self, sync_log):
        """
        Sincronización completa de todos los datos
        
        Args:
            sync_log: Instancia de SyncLog para registrar progreso
            
        Returns:
            dict: Resultado de la sincronización
        """
        log_closed = False
        try:
            # Obtener empresa desde la configuración
            empresa = getattr(self.config, 'empresa', None)
            if empresa:
                # Ejecutar validaciones custom activas antes de sincronizar
                reglas_activas = ValidationRuleConfig.objects.filter(empresa=empresa, is_active=True)
                errores_criticos = []
                for config in reglas_activas:
                    rule_cls = VALIDATION_RULES_REGISTRY.get(config.rule_code)
                    if not rule_cls:
                        continue
                    rule = rule_cls(empresa)
                    resultado = rule.validate()
                    if not resultado.get('success', False):
                        errores_criticos.extend(resultado.get('errors', []))
                if errores_criticos:
                    error_msg = f"Sincronización bloqueada por errores de validación: {errores_criticos}"
                    logger.error(error_msg)
                    sync_log.mark_completed(success=False, error_message=error_msg)
                    log_closed = True
                    # Notificación por email
                    if empresa.email:
                        try:
                            send_mail(
                                subject='[Synap] Error de validación en sincronización',
                                message=f'Se detectaron errores críticos de validación en la sincronización de AdministraNET para la empresa {empresa.nombre}:\n' + '\n'.join(errores_criticos),
                                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@synap.com'),
                                recipient_list=[empresa.email],
                                fail_silently=True,
                            )
                        except Exception as e:
                            logger.error(f"Error enviando notificación de validación: {e}")
                    return {
                        'success': False,
                        'error': error_msg,
                        'validation_errors': errores_criticos
                    }
            sync_log.status = 'RUNNING'
            sync_log.save()
            
            total_processed = 0
            total_created = 0
            total_updated = 0
            total_failed = 0
            
            # Sincronizar productos
            result = self.sync_products(sync_log)
            total_processed += result.get('processed', 0)
            total_created += result.get('created', 0)
            total_updated += result.get('updated', 0)
            total_failed += result.get('failed', 0)
            
            # Sincronizar stock
            result = self.sync_stock(sync_log)
            total_processed += result.get('processed', 0)
            total_created += result.get('created', 0)
            total_updated += result.get('updated', 0)
            total_failed += result.get('failed', 0)
            
            # Sincronizar clientes
            result = self.sync_customers(sync_log)
            total_processed += result.get('processed', 0)
            total_created += result.get('created', 0)
            total_updated += result.get('updated', 0)
            total_failed += result.get('failed', 0)
            
            # Sincronizar pedidos
            result = self.sync_orders(sync_log)
            total_processed += result.get('processed', 0)
            total_created += result.get('created', 0)
            total_updated += result.get('updated', 0)
            total_failed += result.get('failed', 0)
            
            # Actualizar log
            sync_log.records_processed = total_processed
            sync_log.records_created = total_created
            sync_log.records_updated = total_updated
            sync_log.records_failed = total_failed
            sync_log.mark_completed(success=True)
            log_closed = True
            
            # Actualizar configuración
            self.config.last_sync = timezone.now()
            self.config.save()
            
            return {
                'success': True,
                'processed': total_processed,
                'created': total_created,
                'updated': total_updated,
                'failed': total_failed
            }
            
        except Exception as e:
            error_msg = f"Error en sincronización completa: {str(e)}"
            logger.error(error_msg)
            if not log_closed:
                sync_log.mark_completed(success=False, error_message=error_msg)
                log_closed = True
            return {
                'success': False,
                'error': error_msg
            }
        finally:
            # Si por alguna razón no se cerró el log, cerrarlo aquí
            if not log_closed:
                try:
                    sync_log.mark_completed(success=False, error_message='[finally] Sincronización cerrada por error inesperado.')
                except Exception as ex:
                    logger.critical(f"[finally] No se pudo cerrar SyncLog: {ex}")
    
    def sync_products(self, sync_log):
        """
        Sincronizar productos desde administraNET
        
        Args:
            sync_log: Instancia de SyncLog
            
        Returns:
            dict: Resultado de la sincronización
        """
        try:
            # Obtener mapeo de productos
            mapping = self._get_mapping('PRODUCTS')
            if not mapping:
                return {'success': False, 'error': 'No hay mapeo configurado para productos'}
            
            # Obtener datos de administraNET
            admin_data = self.connection_service.get_table_data(
                mapping.administraNET_table
            )
            
            processed = 0
            created = 0
            updated = 0
            failed = 0
            
            # Obtener modelo de Synap
            synap_model = self._get_synap_model(mapping.synap_model)
            
            # Obtener empresa y branch por defecto
            from core.models import Empresa, Branch
            empresa = Empresa.objects.first()
            branch = Branch.objects.first()
            
            if not empresa or not branch:
                return {'success': False, 'error': 'No se encontró empresa o branch por defecto'}
            
            for admin_record in admin_data:
                try:
                    processed += 1
                    
                    # Mapear campos
                    synap_data = self._map_fields(admin_record, mapping.field_mappings, synap_model)
                    
                    if synap_data is None:
                        failed += 1
                        continue

                    # Mapear unidad de medida desde administraNET
                    admin_uom_id = admin_record.get('id_unimed')
                    if admin_uom_id:
                        # Mapeo de unidades de medida de administraNET a Synap
                        uom_mapping = {
                            1.0: 'un',    # Unidad
                            3.0: 'kg',    # Kilogramo
                        }
                        
                        uom_code = uom_mapping.get(float(admin_uom_id))
                        if uom_code:
                            from core.models import UnitOfMeasure
                            uom = UnitOfMeasure.objects.filter(code=uom_code).first()
                            if uom:
                                synap_data['uom'] = uom
                            else:
                                logger.warning(f"Unidad de medida no encontrada: {uom_code}")
                        else:
                            logger.warning(f"Unidad de medida no mapeada: {admin_uom_id}")

                    # Agregar campos requeridos
                    synap_data['empresa'] = empresa
                    synap_data['branch'] = branch
                    # Asignar la moneda de la empresa al producto
                    if hasattr(empresa, 'currency') and empresa.currency:
                        synap_data['price_currency'] = empresa.currency
                    
                    # Asegurar que el SKU no esté vacío
                    if not synap_data.get('sku'):
                        synap_data['sku'] = f"SKU_{admin_record.get('CodigoArticuloT', f'PROD_{processed}')}"
                    
                    # Buscar producto existente por SKU
                    existing_product = synap_model.objects.filter(
                        sku=synap_data.get('sku')
                    ).first()
                    
                    if existing_product:
                        # Actualizar producto existente
                        for field, value in synap_data.items():
                            if hasattr(existing_product, field) and field not in ['empresa', 'branch']:
                                setattr(existing_product, field, value)
                        # Asegurar que la moneda esté actualizada
                        if hasattr(empresa, 'currency') and empresa.currency:
                            existing_product.price_currency = empresa.currency
                        existing_product.save()
                        updated += 1
                        logger.info(f"Producto actualizado: {synap_data.get('sku')}")
                    else:
                        # Crear nuevo producto
                        synap_model.objects.create(**synap_data)
                        created += 1
                        logger.info(f"Producto creado: {synap_data.get('sku')}")
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"Error procesando producto: {e}")
                    logger.error(f"Datos del producto: {admin_record}")
            
            return {
                'success': True,
                'processed': processed,
                'created': created,
                'updated': updated,
                'failed': failed
            }
            
        except Exception as e:
            error_msg = f"Error sincronizando productos: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def sync_stock(self, sync_log):
        """
        Sincronizar stock desde administraNET
        
        Args:
            sync_log: Instancia de SyncLog
            
        Returns:
            dict: Resultado de la sincronización
        """
        try:
            # Obtener mapeo de stock
            mapping = self._get_mapping('STOCK')
            if not mapping:
                return {'success': False, 'error': 'No hay mapeo configurado para stock'}
            
            # Obtener datos de stock por depósito usando la tabla configurada
            query = f"""
                SELECT 
                    sd.id_articulo,
                    sd.id_deposito,
                    sd.saldo as cantidad,
                    sd.saldo_pedido_cliente as cantidad_reservada,
                    a.CodigoArticuloT as producto_codigo,
                    d.NombreDeposito as deposito_nombre
                FROM stock_deposito sd
                JOIN articulo a ON sd.id_articulo = a.IDArt
                JOIN deposito d ON sd.id_deposito = d.CodDeposito
            """
            
            admin_data = self.connection_service.execute_query(query)
            
            # Verificar si la consulta fue exitosa
            if not admin_data.get('success'):
                return {'success': False, 'error': f'Error en consulta SQL: {admin_data.get("error")}'}
            
            # Obtener los datos de la respuesta
            stock_records = admin_data.get('data', [])
            
            processed = 0
            created = 0
            updated = 0
            failed = 0
            
            # Obtener modelos de Synap
            product_model = self._get_synap_model('inventory.product')
            warehouse_model = self._get_synap_model('inventory.warehouse')
            location_model = self._get_synap_model('inventory.location')
            stock_model = self._get_synap_model('inventory.stockquant')
            
            # Obtener empresa y branch por defecto
            from core.models import Empresa, Branch
            empresa = Empresa.objects.first()
            branch = Branch.objects.first()
            
            if not empresa or not branch:
                return {'success': False, 'error': 'No se encontró empresa o branch por defecto'}
            
            for admin_record in stock_records:
                try:
                    processed += 1
                    
                    # Buscar producto en Synap por SKU (no por code)
                    product = product_model.objects.filter(
                        sku=admin_record.get('producto_codigo')
                    ).first()
                    
                    if not product:
                        logger.warning(f"Producto no encontrado: {admin_record.get('producto_codigo')}")
                        failed += 1
                        continue
                    
                    # Buscar o crear warehouse
                    warehouse, warehouse_created = warehouse_model.objects.get_or_create(
                        empresa=empresa,
                        branch=branch,
                        name=admin_record.get('deposito_nombre'),
                        defaults={
                            'code': f"ALM-{admin_record.get('id_deposito', '001')}",
                            'is_active': True
                        }
                    )
                    
                    if warehouse_created:
                        logger.info(f"Almacén creado: {warehouse.name}")
                    
                    # Buscar o crear location
                    location, location_created = location_model.objects.get_or_create(
                        empresa=empresa,
                        branch=branch,
                        warehouse=warehouse,
                        name='Default',
                        defaults={
                            'is_active': True,
                            'allow_operations': True
                        }
                    )
                    
                    if location_created:
                        logger.info(f"Ubicación creada: {location.name} en {warehouse.name}")
                    
                    # Actualizar o crear stock
                    stock, stock_created = stock_model.objects.get_or_create(
                        empresa=empresa,
                        branch=branch,
                        product=product,
                        location=location,
                        defaults={
                            'quantity': admin_record.get('cantidad', 0),
                            'reserved_quantity': admin_record.get('cantidad_reservada', 0)
                        }
                    )
                    
                    if not stock_created:
                        # Actualizar stock existente
                        stock.quantity = admin_record.get('cantidad', 0)
                        stock.reserved_quantity = admin_record.get('cantidad_reservada', 0)
                        stock.save()
                        updated += 1
                        logger.info(f"Stock actualizado: {product.sku} en {location.name}")
                    else:
                        created += 1
                        logger.info(f"Stock creado: {product.sku} en {location.name}")
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"Error procesando stock: {e}")
                    logger.error(f"Datos del stock: {admin_record}")
            
            return {
                'success': True,
                'processed': processed,
                'created': created,
                'updated': updated,
                'failed': failed
            }
            
        except Exception as e:
            error_msg = f"Error sincronizando stock: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def sync_customers(self, sync_log):
        """
        Sincronizar clientes desde administraNET
        
        Args:
            sync_log: Instancia de SyncLog
            
        Returns:
            dict: Resultado de la sincronización
        """
        try:
            # Obtener mapeo de clientes
            mapping = self._get_mapping('CUSTOMERS')
            if not mapping:
                return {'success': False, 'error': 'No hay mapeo configurado para clientes'}
            
            # Obtener datos de clientes
            admin_data = self.connection_service.get_table_data(
                mapping.administraNET_table
            )
            
            processed = 0
            created = 0
            updated = 0
            failed = 0
            
            # Obtener modelo de Synap
            synap_model = self._get_synap_model(mapping.synap_model)
            
            for admin_record in admin_data:
                try:
                    processed += 1
                    
                    # Mapear campos
                    synap_data = self._map_fields(admin_record, mapping.field_mappings, synap_model)
                    
                    if synap_data is None:
                        failed += 1
                        continue

                    # Buscar cliente existente o crear nuevo
                    existing_customer = synap_model.objects.filter(
                        code=synap_data.get('code')
                    ).first()
                    
                    if existing_customer:
                        # Actualizar cliente existente
                        for field, value in synap_data.items():
                            if hasattr(existing_customer, field):
                                setattr(existing_customer, field, value)
                        existing_customer.save()
                        updated += 1
                    else:
                        # Crear nuevo cliente
                        synap_model.objects.create(**synap_data)
                        created += 1
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"Error procesando cliente: {e}")
            
            return {
                'success': True,
                'processed': processed,
                'created': created,
                'updated': updated,
                'failed': failed
            }
            
        except Exception as e:
            error_msg = f"Error sincronizando clientes: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def sync_orders(self, sync_log):
        """
        Sincronizar pedidos desde administraNET
        
        Args:
            sync_log: Instancia of SyncLog
            
        Returns:
            dict: Resultado de la sincronización
        """
        try:
            # Obtener mapeo de pedidos
            mapping = self._get_mapping('ORDERS')
            if not mapping:
                return {'success': False, 'error': 'No hay mapeo configurado para pedidos'}
            
            # Obtener datos de pedidos
            query = """
                SELECT 
                    p.id,
                    p.fecha,
                    p.cliente_id,
                    p.estado,
                    pd.articulo_id,
                    pd.cantidad,
                    pd.precio_unitario,
                    c.codigo as cliente_codigo,
                    a.codigo as producto_codigo
                FROM pedidos p
                JOIN pedidos_detalle pd ON p.id = pd.pedido_id
                JOIN clientes c ON p.cliente_id = c.id
                JOIN articulos a ON pd.articulo_id = a.id
                WHERE p.fecha >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """
            
            admin_data = self.connection_service.execute_query(query)
            
            processed = 0
            created = 0
            updated = 0
            failed = 0
            
            # Obtener modelos de Synap
            order_model = self._get_synap_model('sales.order')
            order_item_model = self._get_synap_model('sales.orderitem')
            customer_model = self._get_synap_model('sales.customer')
            product_model = self._get_synap_model('inventory.product')
            
            # Agrupar por pedido
            orders_dict = {}
            for record in admin_data:
                order_id = record['id']
                if order_id not in orders_dict:
                    orders_dict[order_id] = {
                        'order_data': record,
                        'items': []
                    }
                orders_dict[order_id]['items'].append(record)
            
            for order_id, order_info in orders_dict.items():
                try:
                    processed += 1
                    
                    order_data = order_info['order_data']
                    
                    # Buscar cliente
                    customer = customer_model.objects.filter(
                        code=order_data['cliente_codigo']
                    ).first()
                    
                    if not customer:
                        failed += 1
                        continue
                    
                    # Buscar o crear pedido
                    order, created_flag = order_model.objects.get_or_create(
                        external_id=f"admin_{order_id}",
                        defaults={
                            'customer': customer,
                            'date': order_data['fecha'],
                            'status': self._map_order_status(order_data['estado'])
                        }
                    )
                    
                    if not created_flag:
                        updated += 1
                    else:
                        created += 1
                    
                    # Procesar items del pedido
                    for item_data in order_info['items']:
                        product = product_model.objects.filter(
                            code=item_data['producto_codigo']
                        ).first()
                        
                        if product:
                            order_item_model.objects.get_or_create(
                                order=order,
                                product=product,
                                defaults={
                                    'quantity': item_data['cantidad'],
                                    'unit_price': item_data['precio_unitario']
                                }
                            )
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"Error procesando pedido {order_id}: {e}")
            
            return {
                'success': True,
                'processed': processed,
                'created': created,
                'updated': updated,
                'failed': failed
            }
            
        except Exception as e:
            error_msg = f"Error sincronizando pedidos: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def sync_by_type(self, sync_type, sync_log):
        """
        Sincronizar por tipo específico
        
        Args:
            sync_type (str): Tipo de sincronización
            sync_log: Instancia de SyncLog
            
        Returns:
            dict: Resultado de la sincronización
        """
        if sync_type == 'PRODUCTS':
            return self.sync_products(sync_log)
        elif sync_type == 'STOCK':
            return self.sync_stock(sync_log)
        elif sync_type == 'CUSTOMERS':
            return self.sync_customers(sync_log)
        elif sync_type == 'ORDERS':
            return self.sync_orders(sync_log)
        else:
            return {
                'success': False,
                'error': f'Tipo de sincronización no válido: {sync_type}'
            }
    
    def _get_mapping(self, mapping_type):
        """
        Obtener mapeo por tipo
        
        Args:
            mapping_type (str): Tipo de mapeo
            
        Returns:
            TableMapping: Instancia del mapeo o None
        """
        from ..models import TableMapping
        
        return TableMapping.objects.filter(
            mapping_type=mapping_type,
            is_active=True
        ).first()
    
    def _get_synap_model(self, model_path):
        """
        Obtener modelo de Synap por ruta
        
        Args:
            model_path (str): Ruta del modelo (app.model)
            
        Returns:
            Model: Clase del modelo
        """
        app_label, model_name = model_path.split('.')
        return apps.get_model(app_label, model_name)
    
    def _map_fields(self, admin_record, field_mappings, synap_model=None):
        """
        Mapear campos de administraNET a Synap
        
        Args:
            admin_record (dict): Registro de administraNET
            field_mappings (dict): Mapeo de campos
            synap_model: Modelo de Synap para validar campos
            
        Returns:
            dict: Datos mapeados para Synap
        """
        synap_data = {}
        
        for admin_field, synap_field in field_mappings.items():
            if admin_field in admin_record:
                value = admin_record[admin_field]
                # Manejar valores nulos para campos requeridos
                if value is None or value == '':
                    if synap_field == 'price':
                        value = 0.0  # Precio por defecto
                    elif synap_field == 'cost_price':
                        value = 0.0  # Precio de costo por defecto
                    elif synap_field == 'name':
                        value = f"Producto {admin_record.get('CodigoArticuloT', 'Sin código')}"  # Nombre por defecto
                    elif synap_field == 'description':
                        value = "Sin descripción"  # Descripción por defecto
                    elif synap_field == 'sku':
                        value = admin_record.get('CodigoArticuloT', 'SKU_DEFAULT')  # SKU por defecto
                
                synap_data[synap_field] = value
                
                # Transformaciones especiales
                if synap_field == 'is_active' and isinstance(value, str):
                    synap_data[synap_field] = value.lower() in ['activo', 'true', '1', 'yes', 'sí']
        
        # Agregar campos requeridos por defecto según el modelo
        if synap_model:
            if 'branch_id' not in synap_data and 'branch_id' in [f.name for f in synap_model._meta.fields]:
                synap_data['branch_id'] = 1  # Sucursal por defecto
            
            if 'empresa_id' not in synap_data and 'empresa_id' in [f.name for f in synap_model._meta.fields]:
                synap_data['empresa_id'] = 1  # Empresa por defecto
            
            # Campo empresa requerido para el modelo Client
            if 'empresa' not in synap_data and 'empresa' in [f.name for f in synap_model._meta.fields]:
                from django.apps import apps
                Empresa = apps.get_model('core', 'Empresa')
                try:
                    empresa = Empresa.objects.first()
                    if empresa:
                        synap_data['empresa'] = empresa
                    else:
                        # Si no hay empresa, crear una por defecto
                        empresa = Empresa.objects.create(
                            name='Empresa por defecto',
                            tax_id='00-00000000-0',
                            is_active=True
                        )
                        synap_data['empresa'] = empresa
                except Exception as e:
                    logger.error(f"Error obteniendo empresa: {e}")
                    return None
        
        return synap_data
    
    def _map_order_status(self, admin_status):
        """
        Mapear estado de pedido de administraNET a Synap
        
        Args:
            admin_status (str): Estado en administraNET
            
        Returns:
            str: Estado en Synap
        """
        status_mapping = {
            'PENDIENTE': 'pending',
            'CONFIRMADO': 'confirmed',
            'ENVIADO': 'shipped',
            'ENTREGADO': 'delivered',
            'CANCELADO': 'cancelled',
        }
        
        return status_mapping.get(admin_status.upper(), 'pending') 