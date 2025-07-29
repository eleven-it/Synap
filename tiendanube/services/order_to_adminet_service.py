import logging
from .connection_service import MySQLConnectionService
from tiendanube.models_adminet import TiendaNubeAdminetConfig, TiendaNubeCondVentaMap, TiendaNubeClienteMap

logger = logging.getLogger(__name__)

class OrderToAdminetService:
    """
    Servicio para guardar pedidos de Tiendanube directamente en administraNET (MySQL).
    """
    def __init__(self, mysql_config=None, tn_service=None):
        if mysql_config is None:
            config_obj = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
            if not config_obj:
                raise Exception("No hay configuración activa de conexión a administraNET.")
            mysql_config = {
                'host': config_obj.host,
                'port': config_obj.port,
                'database': config_obj.database,
                'user': config_obj.user,
                'password': config_obj.password,
            }
        self.mysql_service = MySQLConnectionService(mysql_config)
        self.tn_service = tn_service

    def save_order(self, tiendanube_order_data):
        """
        Guarda un pedido de Tiendanube en administraNET.
        - Verifica/crea cliente
        - Inserta pedido con estado 'Preparado', vendedor 75, mapeo de condición de venta
        - Inserta líneas de pedido
        - Guarda id_tiendanube para trazabilidad
        """
        # 1. Verificar/crear cliente
        cliente_id = self._get_or_create_cliente(tiendanube_order_data)
        # 2. Mapear condición de venta
        cond_venta = self._map_cond_venta(tiendanube_order_data)
        # 3. Insertar pedido
        pedido_id = self._insert_pedido(tiendanube_order_data, cliente_id, cond_venta)
        # 4. Insertar líneas de pedido
        self._insert_pedido_lineas(pedido_id, tiendanube_order_data)
        # 5. Log y retorno
        logger.info(f"Pedido Tiendanube {tiendanube_order_data.get('id')} guardado en administraNET con ID {pedido_id}")
        return pedido_id

    def _get_or_create_cliente(self, order_data):
        """
        Verifica si el cliente existe en administraNET (MySQL) por email o documento.
        Si no existe, lo crea con los datos mínimos requeridos.
        Retorna el ID del cliente.
        """
        # Extraer datos relevantes del pedido de Tiendanube
        cliente_data = order_data.get('customer', {})
        email = cliente_data.get('email', '').strip().lower()
        documento = cliente_data.get('identification', '').strip()
        nombre = cliente_data.get('name', '').strip() or cliente_data.get('full_name', '').strip()
        telefono = cliente_data.get('phone', '').strip() if cliente_data.get('phone') else ''
        direccion = cliente_data.get('address', {}).get('street', '').strip() if cliente_data.get('address') else ''
        ciudad = cliente_data.get('address', {}).get('city', '').strip() if cliente_data.get('address') else ''
        provincia = cliente_data.get('address', {}).get('province', '').strip() if cliente_data.get('address') else ''
        codigo_postal = cliente_data.get('address', {}).get('zip', '').strip() if cliente_data.get('address') else ''
        
        # 1. Primero verificar si existe un mapeo de cliente
        if email:
            mapeo_cliente = TiendaNubeClienteMap.objects.filter(
                tiendanube_email=email, 
                activo=True
            ).first()
            
            if mapeo_cliente:
                logger.info(f"Cliente encontrado por mapeo: {mapeo_cliente.adminet_codigo} ({email})")
                return mapeo_cliente.adminet_codigo
        
        # 2. Buscar cliente por email o documento
        query = """
            SELECT codigo FROM cliente
            WHERE LOWER(email) = %s OR (cuit <> '' AND cuit = %s)
            LIMIT 1
        """
        params = (email, documento)
        result = self.mysql_service.execute_query(query, params, fetch_one=True)
        if result and result.get('codigo'):
            logger.info(f"Cliente encontrado en administraNET: {result['codigo']} ({email or documento})")
            return result['codigo']
        
        # 3. Si no existe, crear cliente
        insert_query = """
            INSERT INTO cliente (nombre_cliente, email, cuit, fecha_alta)
            VALUES (%s, %s, %s, NOW())
        """
        insert_params = (nombre, email, documento)
        self.mysql_service.execute_query(insert_query, insert_params, commit=True)
        # Obtener el ID del nuevo cliente
        id_query = "SELECT LAST_INSERT_ID() AS codigo"
        new_id = self.mysql_service.execute_query(id_query, fetch_one=True)
        logger.info(f"Cliente creado en administraNET: {new_id['codigo']} ({email or documento})")
        return new_id['codigo']

    def _map_cond_venta(self, order_data):
        """
        Mapea la condición de venta usando el CRUD de mapeo y retorna el código adminet correspondiente.
        """
        payment_method = order_data.get('payment_method', '').strip()
        mapeo = TiendaNubeCondVentaMap.objects.filter(payment_method=payment_method, activo=True).first()
        if mapeo:
            logger.info(f"Condición de venta Tiendanube '{payment_method}' mapeada a adminet código {mapeo.adminet_codigo}")
            return mapeo.adminet_codigo
        logger.warning(f"No se encontró mapeo para condición de venta '{payment_method}', usando código por defecto 1")
        return 1  # Código por defecto (ajustar según necesidad)

    def _insert_pedido(self, order_data, cliente_id, cond_venta):
        """
        Inserta el pedido en comp_ped con estado 'Preparado', vendedor 75, id_tiendanube, etc.
        Retorna el ID del pedido.
        """
        id_tiendanube = order_data.get('id')
        fecha = order_data.get('created_at') or order_data.get('date')
        total = order_data.get('total', 0)
        observaciones = order_data.get('note', '')
        # Datos logísticos
        direccion = order_data.get('shipping_address', {}).get('street', '')
        ciudad = order_data.get('shipping_address', {}).get('city', '')
        provincia = order_data.get('shipping_address', {}).get('province', '')
        codigo_postal = order_data.get('shipping_address', {}).get('zip', '')
        # Insertar pedido
        insert_query = """
            INSERT INTO comp_ped (idcliente, fecha, total, estado, id_tiendanube, vendedor, cond_venta, observaciones, direccion, ciudad, provincia, codigopostal)
            VALUES (%s, %s, %s, 'Preparado', %s, 75, %s, %s, %s, %s, %s, %s)
        """
        params = (cliente_id, fecha, total, id_tiendanube, cond_venta, observaciones, direccion, ciudad, provincia, codigo_postal)
        self.mysql_service.execute_query(insert_query, params, commit=True)
        # Obtener el ID del nuevo pedido
        id_query = "SELECT LAST_INSERT_ID() AS idpedido"
        new_id = self.mysql_service.execute_query(id_query, fetch_one=True)
        logger.info(f"Pedido insertado en comp_ped: {new_id['idpedido']} (id_tiendanube={id_tiendanube})")
        return new_id['idpedido']

    def _insert_pedido_lineas(self, pedido_id, order_data):
        """
        Inserta las líneas de pedido en la tabla cuerpostockpe o equivalente.
        """
        lineas = order_data.get('items', [])
        for item in lineas:
            producto_id = item.get('product_id')
            nombre = item.get('name', '')
            cantidad = item.get('quantity', 1)
            precio_unitario = item.get('price', 0)
            total = item.get('total', precio_unitario * cantidad)
            insert_query = """
                INSERT INTO cuerpostockpe (idpedido, producto_id, nombre, cantidad, precio_unitario, total)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (pedido_id, producto_id, nombre, cantidad, precio_unitario, total)
            self.mysql_service.execute_query(insert_query, params, commit=True)
            logger.info(f"Línea de pedido insertada: pedido {pedido_id}, producto {producto_id}, cantidad {cantidad}") 