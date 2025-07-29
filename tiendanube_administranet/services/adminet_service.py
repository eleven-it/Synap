"""
Servicio para interactuar con la base de datos de AdministraNET.
"""

import mysql.connector
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.utils import timezone
from ..models import AdministraNETConfig

logger = logging.getLogger(__name__)


class AdministraNETService:
    """
    Servicio para interactuar con la base de datos MySQL de AdministraNET.
    """
    
    def __init__(self, config: AdministraNETConfig):
        self.config = config
        self.connection = None
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Obtener parámetros de conexión."""
        return {
            'host': self.config.host,
            'port': self.config.port,
            'database': self.config.database,
            'user': self.config.user,
            'password': self.config.password,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'autocommit': True
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Probar conexión con AdministraNET."""
        try:
            connection_params = self.get_connection_params()
            connection = mysql.connector.connect(**connection_params)
            
            if connection.is_connected():
                cursor = connection.cursor()
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                cursor.close()
                connection.close()
                
                return {
                    'success': True,
                    'message': 'Conexión exitosa con AdministraNET',
                    'version': version[0] if version else 'Unknown'
                }
            else:
                return {
                    'success': False,
                    'message': 'No se pudo establecer conexión con AdministraNET'
                }
        except Exception as e:
            logger.error(f"Error testing AdministraNET connection: {e}")
            return {
                'success': False,
                'message': f'Error de conexión: {str(e)}'
            }
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
        """Ejecutar consulta SQL."""
        try:
            if not self.connection or not self.connection.is_connected():
                connection_params = self.get_connection_params()
                self.connection = mysql.connector.connect(**connection_params)
            
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                cursor.close()
                return {
                    'success': True,
                    'results': results,
                    'count': len(results)
                }
            else:
                self.connection.commit()
                cursor.close()
                return {
                    'success': True,
                    'affected_rows': cursor.rowcount,
                    'message': 'Consulta ejecutada exitosamente'
                }
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {
                'success': False,
                'message': f'Error ejecutando consulta: {str(e)}'
            }
    
    def get_customers(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Obtener lista de clientes de AdministraNET."""
        query = """
        SELECT 
            codigo,
            nombre,
            documento,
            telefono,
            direccion,
            email,
            fecha_alta,
            activo
        FROM clientes 
        WHERE activo = 1
        ORDER BY nombre
        LIMIT %s OFFSET %s
        """
        return self.execute_query(query, (limit, offset))

    def get_customer(self, customer_code: int) -> Dict[str, Any]:
        """Obtener cliente específico de AdministraNET."""
        query = """
        SELECT 
            codigo,
            nombre,
            documento,
            telefono,
            direccion,
            email,
            fecha_alta,
            activo
        FROM clientes 
        WHERE codigo = %s AND activo = 1
        """
        result = self.execute_query(query, (customer_code,))
        if result['success'] and result['results']:
            return {
                'success': True,
                'customer': result['results'][0]
            }
        return {
            'success': False,
            'message': 'Cliente no encontrado'
        }
    
    def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear nuevo cliente en AdministraNET."""
        query = """
        INSERT INTO clientes (
            nombre, documento, telefono, direccion, email, fecha_alta, activo
        ) VALUES (%s, %s, %s, %s, %s, NOW(), 1)
        """
        params = (
            customer_data.get('nombre'),
            customer_data.get('documento'),
            customer_data.get('telefono'),
            customer_data.get('direccion'),
            customer_data.get('email')
        )
        result = self.execute_query(query, params)
        
        if result['success']:
            # Obtener el ID del cliente creado
            cursor = self.connection.cursor()
            cursor.execute("SELECT LAST_INSERT_ID()")
            new_id = cursor.fetchone()[0]
            cursor.close()
            
            return {
                'success': True,
                'message': 'Cliente creado exitosamente',
                'customer_id': new_id
            }
        else:
            return result
    
    def update_customer(self, customer_code: int, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Actualizar cliente existente en AdministraNET."""
        query = """
        UPDATE clientes SET
            nombre = %s,
            documento = %s,
            telefono = %s,
            direccion = %s,
            email = %s
        WHERE codigo = %s
        """
        params = (
            customer_data.get('nombre'),
            customer_data.get('documento'),
            customer_data.get('telefono'),
            customer_data.get('direccion'),
            customer_data.get('email'),
            customer_code
        )
        return self.execute_query(query, params)

    # ============================================================================
    # PRODUCTOS
    # ============================================================================

    def get_products(self, limit: int = 50, offset: int = 0, **filters) -> Dict[str, Any]:
        """
        Obtener lista de productos de AdministraNET.
        
        Args:
            limit: Número máximo de productos a obtener
            offset: Número de productos a saltar
            **filters: Filtros adicionales
        """
        try:
            # Construir consulta base
            query = """
            SELECT 
                IDArt,
                id_manual,
                CodigoArticulo,
                CodigoArticuloT,
                NombreArticulo,
                Detalle,
                PrecioCosto,
                Precio1V,
                Precio2V,
                Precio3V,
                Precio4V,
                Precio5V,
                saldo_articulo,
                stock_max,
                stock_min,
                NroCodBarra,
                NroCodBarraF,
                CodigoProveedor,
                CodigoMarca,
                CodigoModelo,
                CodigoRubro,
                CodigoSubRubro,
                Alicuota,
                AlicuotaIB,
                Moneda,
                TipoIVA,
                TipoIB,
                Discontinuo,
                ecommerce,
                detalle_web,
                disponible_vta,
                disponible_comp,
                fecha_alta,
                fecha_mod
            FROM articulo
            WHERE 1=1
            """
            
            params = []
            
            # Agregar filtros
            if filters.get('ecommerce'):
                query += " AND ecommerce = %s"
                params.append(filters['ecommerce'])
            
            if filters.get('discontinuo'):
                query += " AND Discontinuo = %s"
                params.append(filters['discontinuo'])
            
            if filters.get('disponible_vta'):
                query += " AND disponible_vta = %s"
                params.append(filters['disponible_vta'])
            
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query += " AND (NombreArticulo LIKE %s OR CodigoArticuloT LIKE %s)"
                params.extend([search_term, search_term])
            
            # Agregar ordenamiento y límites
            query += " ORDER BY NombreArticulo LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            return self.execute_query(query, tuple(params))
            
        except Exception as e:
            logger.error(f"Error getting products from AdministraNET: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo productos: {str(e)}'
            }

    def get_product(self, product_id: int) -> Dict[str, Any]:
        """
        Obtener un producto específico por ID.
        
        Args:
            product_id: ID del producto en AdministraNET
        """
        query = """
        SELECT 
            IDArt,
            id_manual,
            CodigoArticulo,
            CodigoArticuloT,
            NombreArticulo,
            Detalle,
            PrecioCosto,
            Precio1V,
            Precio2V,
            Precio3V,
            Precio4V,
            Precio5V,
            saldo_articulo,
            stock_max,
            stock_min,
            NroCodBarra,
            NroCodBarraF,
            CodigoProveedor,
            CodigoMarca,
            CodigoModelo,
            CodigoRubro,
            CodigoSubRubro,
            Alicuota,
            AlicuotaIB,
            Moneda,
            TipoIVA,
            TipoIB,
            Discontinuo,
            ecommerce,
            detalle_web,
            disponible_vta,
            disponible_comp,
            fecha_alta,
            fecha_mod
        FROM articulo 
        WHERE IDArt = %s
        """
        return self.execute_query(query, (product_id,))

    def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crear un nuevo producto en AdministraNET.
        
        Args:
            product_data: Datos del producto a crear
        """
        try:
            # Preparar campos para inserción
            fields = [
                'id_manual', 'CodigoArticulo', 'CodigoArticuloT', 'NombreArticulo',
                'Detalle', 'PrecioCosto', 'Precio1V', 'Precio2V', 'Precio3V', 'Precio4V', 'Precio5V',
                'saldo_articulo', 'stock_max', 'stock_min', 'NroCodBarra', 'NroCodBarraF',
                'CodigoProveedor', 'CodigoMarca', 'CodigoModelo', 'CodigoRubro', 'CodigoSubRubro',
                'Alicuota', 'AlicuotaIB', 'Moneda', 'TipoIVA', 'TipoIB', 'Discontinuo',
                'ecommerce', 'detalle_web', 'disponible_vta', 'disponible_comp'
            ]
            
            # Filtrar solo los campos que existen en product_data
            available_fields = [field for field in fields if field in product_data]
            placeholders = ', '.join(['%s'] * len(available_fields))
            field_names = ', '.join(available_fields)
            
            query = f"""
            INSERT INTO articulo ({field_names}, fecha_alta, fecha_mod)
            VALUES ({placeholders}, NOW(), NOW())
            """
            
            values = [product_data[field] for field in available_fields]
            
            result = self.execute_query(query, tuple(values))
            
            if result['success']:
                # Obtener el ID del producto creado
                cursor = self.connection.cursor()
                cursor.execute("SELECT LAST_INSERT_ID()")
                new_id = cursor.fetchone()[0]
                cursor.close()
                
                return {
                    'success': True,
                    'message': 'Producto creado exitosamente',
                    'product_id': new_id
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error creating product in AdministraNET: {e}")
            return {
                'success': False,
                'message': f'Error creando producto: {str(e)}'
            }

    def update_product(self, product_id: int, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar un producto existente en AdministraNET.
        
        Args:
            product_id: ID del producto a actualizar
            product_data: Datos del producto a actualizar
        """
        try:
            # Preparar campos para actualización
            fields = [
                'id_manual', 'CodigoArticulo', 'CodigoArticuloT', 'NombreArticulo',
                'Detalle', 'PrecioCosto', 'Precio1V', 'Precio2V', 'Precio3V', 'Precio4V', 'Precio5V',
                'saldo_articulo', 'stock_max', 'stock_min', 'NroCodBarra', 'NroCodBarraF',
                'CodigoProveedor', 'CodigoMarca', 'CodigoModelo', 'CodigoRubro', 'CodigoSubRubro',
                'Alicuota', 'AlicuotaIB', 'Moneda', 'TipoIVA', 'TipoIB', 'Discontinuo',
                'ecommerce', 'detalle_web', 'disponible_vta', 'disponible_comp'
            ]
            
            # Filtrar solo los campos que existen en product_data
            available_fields = [field for field in fields if field in product_data]
            
            if not available_fields:
                return {
                    'success': False,
                    'message': 'No hay campos válidos para actualizar'
                }
            
            # Construir query de actualización
            set_clause = ', '.join([f"{field} = %s" for field in available_fields])
            query = f"""
            UPDATE articulo 
            SET {set_clause}, fecha_mod = NOW()
            WHERE IDArt = %s
            """
            
            values = [product_data[field] for field in available_fields]
            values.append(product_id)
            
            result = self.execute_query(query, tuple(values))
            
            if result['success']:
                return {
                    'success': True,
                    'message': 'Producto actualizado exitosamente',
                    'affected_rows': result.get('affected_rows', 0)
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error updating product in AdministraNET: {e}")
            return {
                'success': False,
                'message': f'Error actualizando producto: {str(e)}'
            }

    def delete_product(self, product_id: int) -> Dict[str, Any]:
        """
        Eliminar un producto de AdministraNET.
        
        Args:
            product_id: ID del producto a eliminar
        """
        query = "DELETE FROM articulo WHERE IDArt = %s"
        return self.execute_query(query, (product_id,))

    def update_product_stock(self, product_id: int, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar stock de un producto.
        
        Args:
            product_id: ID del producto
            stock_data: Datos de stock (saldo_articulo, stock_max, stock_min)
        """
        try:
            fields = ['saldo_articulo', 'stock_max', 'stock_min']
            available_fields = [field for field in fields if field in stock_data]
            
            if not available_fields:
                return {
                    'success': False,
                    'message': 'No hay datos de stock válidos'
                }
            
            set_clause = ', '.join([f"{field} = %s" for field in available_fields])
            query = f"""
            UPDATE articulo 
            SET {set_clause}, fecha_mod = NOW()
            WHERE IDArt = %s
            """
            
            values = [stock_data[field] for field in available_fields]
            values.append(product_id)
            
            return self.execute_query(query, tuple(values))
            
        except Exception as e:
            logger.error(f"Error updating product stock in AdministraNET: {e}")
            return {
                'success': False,
                'message': f'Error actualizando stock: {str(e)}'
            }

    def search_products(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """
        Buscar productos por nombre o código.
        
        Args:
            query: Término de búsqueda
            limit: Número máximo de resultados
        """
        search_term = f"%{query}%"
        sql_query = """
        SELECT 
            IDArt,
            CodigoArticuloT,
            NombreArticulo,
            Precio1V,
            saldo_articulo,
            ecommerce,
            disponible_vta
        FROM articulo 
        WHERE NombreArticulo LIKE %s OR CodigoArticuloT LIKE %s
        ORDER BY NombreArticulo
        LIMIT %s
        """
        return self.execute_query(sql_query, (search_term, search_term, limit))

    def get_product_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de productos."""
        try:
            queries = {
                'total_products': "SELECT COUNT(*) as total FROM articulo",
                'ecommerce_products': "SELECT COUNT(*) as total FROM articulo WHERE ecommerce = 'Si'",
                'active_products': "SELECT COUNT(*) as total FROM articulo WHERE disponible_vta = 'Si'",
                'discontinued_products': "SELECT COUNT(*) as total FROM articulo WHERE Discontinuo = 'Si'",
                'low_stock': "SELECT COUNT(*) as total FROM articulo WHERE saldo_articulo <= stock_min AND stock_min > 0"
            }
            
            stats = {}
            for key, query in queries.items():
                result = self.execute_query(query)
                if result['success'] and result['results']:
                    stats[key] = result['results'][0]['total']
                else:
                    stats[key] = 0
            
            return {
                'success': True,
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Error getting product statistics: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo estadísticas: {str(e)}'
            }
    
    def get_orders(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Obtener lista de órdenes de AdministraNET."""
        query = """
        SELECT 
            o.numero,
            o.fecha,
            o.cliente_codigo,
            c.nombre as cliente_nombre,
            o.total,
            o.estado,
            o.fecha_creacion
        FROM ordenes o
        JOIN clientes c ON o.cliente_codigo = c.codigo
        ORDER BY o.fecha_creacion DESC
        LIMIT %s OFFSET %s
        """
        return self.execute_query(query, (limit, offset))
    
    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear nueva orden en AdministraNET."""
        try:
            # Crear la orden principal
            order_query = """
            INSERT INTO ordenes (
                numero, fecha, cliente_codigo, total, estado, fecha_creacion
            ) VALUES (%s, %s, %s, %s, %s, NOW())
            """
            order_params = (
                order_data.get('numero'),
                order_data.get('fecha'),
                order_data.get('cliente_codigo'),
                order_data.get('total'),
                order_data.get('estado', 'pendiente')
            )
            
            result = self.execute_query(order_query, order_params)
            if not result['success']:
                return result
            
            # Crear las líneas de la orden
            order_lines = order_data.get('lineas', [])
            for line in order_lines:
                line_query = """
                INSERT INTO orden_lineas (
                    orden_numero, producto_codigo, cantidad, precio_unitario, subtotal
                ) VALUES (%s, %s, %s, %s, %s)
                """
                line_params = (
                    order_data.get('numero'),
                    line.get('producto_codigo'),
                    line.get('cantidad'),
                    line.get('precio_unitario'),
                    line.get('subtotal')
                )
                self.execute_query(line_query, line_params)
            
            return {
                'success': True,
                'message': 'Orden creada exitosamente'
            }
        except Exception as e:
            logger.error(f"Error creating order in AdministraNET: {e}")
            return {
                'success': False,
                'message': f'Error creando orden: {str(e)}'
            }
    
    def _create_order_line(self, order_number: str, line_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear línea de orden en AdministraNET."""
        query = """
        INSERT INTO orden_lineas (
            orden_numero, producto_codigo, cantidad, precio_unitario, subtotal
        ) VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            order_number,
            line_data.get('producto_codigo'),
            line_data.get('cantidad'),
            line_data.get('precio_unitario'),
            line_data.get('subtotal')
        )
        return self.execute_query(query, params)
    
    def update_order_status(self, order_number: str, status: str) -> Dict[str, Any]:
        """Actualizar estado de una orden en AdministraNET."""
        query = """
        UPDATE ordenes SET
            estado = %s,
            fecha_modificacion = NOW()
        WHERE numero = %s
        """
        return self.execute_query(query, (status, order_number))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de AdministraNET."""
        try:
            stats = {}
            
            # Total de clientes
            result = self.execute_query("SELECT COUNT(*) as total FROM clientes WHERE activo = 1")
            if result['success']:
                stats['total_customers'] = result['results'][0]['total']
            
            # Total de productos
            result = self.execute_query("SELECT COUNT(*) as total FROM productos WHERE activo = 1")
            if result['success']:
                stats['total_products'] = result['results'][0]['total']
            
            # Total de órdenes
            result = self.execute_query("SELECT COUNT(*) as total FROM ordenes")
            if result['success']:
                stats['total_orders'] = result['results'][0]['total']
            
            # Ventas del mes actual
            result = self.execute_query("""
                SELECT SUM(total) as total_ventas 
                FROM ordenes 
                WHERE MONTH(fecha) = MONTH(NOW()) 
                AND YEAR(fecha) = YEAR(NOW())
                AND estado = 'pagado'
            """)
            if result['success']:
                stats['monthly_sales'] = result['results'][0]['total_ventas'] or 0
            
            return {
                'success': True,
                'statistics': stats
            }
        except Exception as e:
            logger.error(f"Error getting statistics from AdministraNET: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo estadísticas: {str(e)}'
            }
    
    def close_connection(self):
        """Cerrar conexión con la base de datos."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.connection = None 