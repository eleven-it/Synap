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
    
    def get_customers(self, limit: int = 50, offset: int = 0, **filters) -> Dict[str, Any]:
        """
        Obtener lista de clientes de AdministraNET.
        
        Args:
            limit: Número máximo de clientes a obtener
            offset: Número de clientes a saltar
            **filters: Filtros adicionales (ej: search, estado)
        
        Returns:
            Dict con success, results y count
        """
        try:
            # Query con nombres de campos correctos según estructura real de BD
            query = """
            SELECT 
                Codigo,
                nombre_cliente,
                nombre_fantasia,
                CUIT,
                tipo_doc,
                telefono,
                Email,
                EmailContacto,
                Calle,
                NroCalle,
                Dpto,
                IDDistrito,
                CodProvincia,
                IDDepartamento,
                NombreContacto,
                TelefonoContacto,
                CelularContacto,
                IDIva,
                Credito,
                Descuento,
                CodViajante,
                Observaciones,
                ListaPrecio,
                FechaAlta,
                Estado,
                NroIngBrutos,
                NroAgenteRetencion,
                saldo
            FROM cliente
            WHERE 1=1
            """
            
            params = []
            
            # Agregar filtros opcionales
            if filters.get('estado'):
                query += " AND Estado = %s"
                params.append(filters['estado'])
            else:
                # Por defecto, solo clientes activos
                query += " AND Estado = 'Activo'"
            
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query += " AND (nombre_cliente LIKE %s OR nombre_fantasia LIKE %s OR CUIT LIKE %s OR Email LIKE %s)"
                params.extend([search_term, search_term, search_term, search_term])
            
            # Ordenamiento y límites
            query += " ORDER BY nombre_cliente LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            result = self.execute_query(query, tuple(params))
            
            if result['success']:
                return {
                    'success': True,
                    'data': result['results'],
                    'total': result['count']
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error getting customers from AdministraNET: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo clientes: {str(e)}'
            }

    def get_customer(self, customer_code: int) -> Dict[str, Any]:
        """
        Obtener cliente específico de AdministraNET por código.
        
        Args:
            customer_code: Código del cliente en AdministraNET
        
        Returns:
            Dict con success y customer data
        """
        query = """
        SELECT 
            Codigo,
            nombre_cliente,
            nombre_fantasia,
            CUIT,
            tipo_doc,
            telefono,
            Email,
            EmailContacto,
            Calle,
            NroCalle,
            Dpto,
            IDDistrito,
            CodProvincia,
            IDDepartamento,
            NombreContacto,
            TelefonoContacto,
            CelularContacto,
            IDIva,
            Credito,
            Descuento,
            CodViajante,
            Observaciones,
            ListaPrecio,
            FechaAlta,
            Estado,
            NroIngBrutos,
            NroAgenteRetencion,
            saldo,
            TipoCliente,
            Fax
        FROM cliente 
        WHERE Codigo = %s
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
        """
        Crear nuevo cliente en AdministraNET.
        
        Args:
            customer_data: Diccionario con datos del cliente
                - nombre_cliente (requerido)
                - CUIT (opcional)
                - Email (opcional)
                - telefono (opcional)
                - Calle (opcional)
                - NroCalle (opcional)
                - etc.
        
        Returns:
            Dict con success, message y customer_id
        """
        try:
            # Campos básicos requeridos y opcionales
            fields = [
                'nombre_cliente', 'nombre_fantasia', 'CUIT', 'tipo_doc',
                'telefono', 'Email', 'EmailContacto',
                'Calle', 'NroCalle', 'Dpto',
                'IDDistrito', 'CodProvincia', 'IDDepartamento',
                'NombreContacto', 'TelefonoContacto', 'CelularContacto',
                'IDIva', 'Credito', 'Descuento', 'CodViajante',
                'Observaciones', 'ListaPrecio', 'TipoCliente',
                'NroIngBrutos', 'NroAgenteRetencion'
            ]
            
            # Filtrar solo los campos que existen en customer_data
            available_fields = [field for field in fields if field in customer_data]
            
            if not available_fields:
                return {
                    'success': False,
                    'message': 'No hay datos válidos para crear el cliente'
                }
            
            # Construir query dinámicamente
            placeholders = ', '.join(['%s'] * len(available_fields))
            field_names = ', '.join(available_fields)
            
            query = f"""
            INSERT INTO cliente ({field_names}, FechaAlta, Estado)
            VALUES ({placeholders}, NOW(), 'Activo')
            """
            
            values = [customer_data[field] for field in available_fields]
            
            result = self.execute_query(query, tuple(values))
            
            if result['success']:
                # Obtener el ID del cliente creado
                cursor = self.connection.cursor()
                cursor.execute("SELECT LAST_INSERT_ID()")
                new_id = cursor.fetchone()[0]
                cursor.close()
                
                return {
                    'success': True,
                    'message': 'Cliente creado exitosamente en AdministraNET',
                    'customer_id': new_id,
                    'codigo': new_id
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error creating customer in AdministraNET: {e}")
            return {
                'success': False,
                'message': f'Error creando cliente: {str(e)}'
            }
    
    def update_customer(self, customer_code: int, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar cliente existente en AdministraNET.
        
        Args:
            customer_code: Código del cliente a actualizar
            customer_data: Diccionario con campos a actualizar
        
        Returns:
            Dict con success y message
        """
        try:
            # Campos que se pueden actualizar
            fields = [
                'nombre_cliente', 'nombre_fantasia', 'CUIT', 'tipo_doc',
                'telefono', 'Email', 'EmailContacto',
                'Calle', 'NroCalle', 'Dpto',
                'IDDistrito', 'CodProvincia', 'IDDepartamento',
                'NombreContacto', 'TelefonoContacto', 'CelularContacto',
                'IDIva', 'Credito', 'Descuento', 'CodViajante',
                'Observaciones', 'ListaPrecio', 'TipoCliente',
                'NroIngBrutos', 'NroAgenteRetencion', 'Estado', 'Fax'
            ]
            
            # Filtrar solo los campos que existen en customer_data
            available_fields = [field for field in fields if field in customer_data]
            
            if not available_fields:
                return {
                    'success': False,
                    'message': 'No hay campos válidos para actualizar'
                }
            
            # Construir query de actualización
            set_clause = ', '.join([f"{field} = %s" for field in available_fields])
            query = f"""
            UPDATE cliente 
            SET {set_clause}
            WHERE Codigo = %s
            """
            
            values = [customer_data[field] for field in available_fields]
            values.append(customer_code)
            
            result = self.execute_query(query, tuple(values))
            
            if result['success']:
                return {
                    'success': True,
                    'message': 'Cliente actualizado exitosamente en AdministraNET',
                    'affected_rows': result.get('affected_rows', 0)
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error updating customer in AdministraNET: {e}")
            return {
                'success': False,
                'message': f'Error actualizando cliente: {str(e)}'
            }

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

    def get_stock_by_deposito(self, product_id: int, deposito_id: int) -> Dict[str, Any]:
        """
        Obtener stock de un producto en un depósito específico.
        
        Args:
            product_id: ID del producto
            deposito_id: ID del depósito
            
        Returns:
            Dict con el stock del producto en el depósito
        """
        try:
            query = """
            SELECT 
                sd.id_stock_deposito,
                sd.id_articulo,
                sd.id_deposito,
                sd.saldo,
                sd.saldo_pedido_cliente,
                sd.saldo_pedido_proveedor,
                d.NombreDeposito as nombre_deposito,
                a.NombreArticulo
            FROM stock_deposito sd
            LEFT JOIN deposito d ON sd.id_deposito = d.CodDeposito
            LEFT JOIN articulo a ON sd.id_articulo = a.IDArt
            WHERE sd.id_articulo = %s AND sd.id_deposito = %s
            """
            
            result = self.execute_query(query, (product_id, deposito_id))
            
            if result['success'] and result['results']:
                stock_data = result['results'][0]
                return {
                    'success': True,
                    'stock': float(stock_data.get('saldo', 0)),
                    'stock_pedido_cliente': float(stock_data.get('saldo_pedido_cliente', 0)),
                    'stock_pedido_proveedor': float(stock_data.get('saldo_pedido_proveedor', 0)),
                    'nombre_deposito': stock_data.get('nombre_deposito', ''),
                    'nombre_articulo': stock_data.get('NombreArticulo', ''),
                    'data': stock_data
                }
            else:
                return {
                    'success': True,
                    'stock': 0,
                    'stock_pedido_cliente': 0,
                    'stock_pedido_proveedor': 0,
                    'message': 'No se encontró stock para este producto en el depósito especificado'
                }
                
        except Exception as e:
            logger.error(f"Error getting stock by deposito: {e}")
            return {
                'success': False,
                'stock': 0,
                'message': f'Error obteniendo stock por depósito: {str(e)}'
            }
    
    def get_products_with_stock_by_deposito(self, deposito_id: int, limit: int = 100, **filters) -> Dict[str, Any]:
        """
        Obtener productos con su stock de un depósito específico.
        
        Args:
            deposito_id: ID del depósito
            limit: Número máximo de productos
            **filters: Filtros adicionales (ecommerce, disponible_vta, etc.)
            
        Returns:
            Dict con la lista de productos y su stock del depósito
        """
        try:
            # Construir consulta base con JOIN a stock_deposito
            query = """
            SELECT 
                a.IDArt,
                a.id_manual,
                a.CodigoArticulo,
                a.CodigoArticuloT,
                a.NombreArticulo,
                a.Detalle,
                a.PrecioCosto,
                a.Precio1V,
                a.Precio2V,
                a.Precio3V,
                a.Precio4V,
                a.Precio5V,
                a.saldo_articulo,
                a.stock_max,
                a.stock_min,
                a.NroCodBarra,
                a.NroCodBarraF,
                a.CodigoProveedor,
                a.CodigoMarca,
                a.CodigoModelo,
                a.CodigoRubro,
                a.CodigoSubRubro,
                a.Alicuota,
                a.AlicuotaIB,
                a.Moneda,
                a.TipoIVA,
                a.TipoIB,
                a.Discontinuo,
                a.ecommerce,
                a.detalle_web,
                a.disponible_vta,
                a.disponible_comp,
                a.fecha_alta,
                a.fecha_mod,
                COALESCE(sd.saldo, 0) as stock_deposito,
                COALESCE(sd.saldo_pedido_cliente, 0) as stock_pedido_cliente,
                COALESCE(sd.saldo_pedido_proveedor, 0) as stock_pedido_proveedor
            FROM articulo a
            LEFT JOIN stock_deposito sd ON a.IDArt = sd.id_articulo AND sd.id_deposito = %s
            WHERE 1=1
            """
            
            params = [deposito_id]
            
            # Agregar filtros
            if filters.get('ecommerce'):
                query += " AND a.ecommerce = %s"
                params.append(filters['ecommerce'])
            
            if filters.get('discontinuo'):
                query += " AND a.Discontinuo = %s"
                params.append(filters['discontinuo'])
            
            if filters.get('disponible_vta'):
                query += " AND a.disponible_vta = %s"
                params.append(filters['disponible_vta'])
            
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query += " AND (a.NombreArticulo LIKE %s OR a.CodigoArticuloT LIKE %s)"
                params.extend([search_term, search_term])
            
            # Ordenamiento y límites
            query += " ORDER BY a.NombreArticulo LIMIT %s"
            params.append(limit)
            
            result = self.execute_query(query, tuple(params))
            
            if result['success']:
                return {
                    'success': True,
                    'results': result['results'],
                    'count': result['count']
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error getting products with stock by deposito: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo productos con stock por depósito: {str(e)}'
            }
    
    def get_depositos(self) -> Dict[str, Any]:
        """
        Obtener lista de depósitos disponibles.
        
        Returns:
            Dict con la lista de depósitos
        """
        try:
            query = """
            SELECT 
                CodDeposito as id,
                NombreDeposito as nombre,
                Descripcion as descripcion,
                anulado
            FROM deposito
            WHERE anulado IS NULL OR anulado = '' OR anulado = 'No'
            ORDER BY NombreDeposito
            """
            
            result = self.execute_query(query, ())
            
            if result['success']:
                return {
                    'success': True,
                    'depositos': result['results'],
                    'count': len(result['results'])
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error getting depositos: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo depósitos: {str(e)}'
            }
    
    def get_next_codigo_movimiento(self) -> Dict[str, Any]:
        """
        Obtener el próximo código de movimiento disponible.
        
        Returns:
            Dict con el próximo código de movimiento
        """
        try:
            query = """
            SELECT COALESCE(MAX(CodigoMovimiento), 0) + 1 as next_codigo
            FROM comp_ped
            """
            
            result = self.execute_query(query, ())
            
            if result['success'] and result['results']:
                next_codigo = int(result['results'][0].get('next_codigo', 1))
                return {
                    'success': True,
                    'codigo_movimiento': next_codigo
                }
            else:
                return {
                    'success': False,
                    'message': 'Error obteniendo próximo código de movimiento'
                }
                
        except Exception as e:
            logger.error(f"Error getting next codigo_movimiento: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo código de movimiento: {str(e)}'
            }
    
    def get_next_nro_comprobante(self, tipo_comp: str = 'PED', sucursal: int = 1) -> Dict[str, Any]:
        """
        Obtener el próximo número de comprobante.
        
        Args:
            tipo_comp: Tipo de comprobante (PED, FA, FB, etc.)
            sucursal: Código de sucursal
            
        Returns:
            Dict con el próximo número de comprobante en formato XXXX-XXXXXXXX
        """
        try:
            query = """
            SELECT COALESCE(MAX(CAST(SUBSTRING_INDEX(NroComprobante, '-', -1) AS UNSIGNED)), 0) + 1 as next_number
            FROM comp_ped
            WHERE TipoComprobante = %s
            AND NroComprobante LIKE %s
            """
            
            sucursal_str = str(sucursal).zfill(4)
            pattern = f"{sucursal_str}-%"
            
            result = self.execute_query(query, (tipo_comp, pattern))
            
            if result['success'] and result['results']:
                next_number = int(result['results'][0].get('next_number', 1))
                nro_comprobante = f"{sucursal_str}-{str(next_number).zfill(8)}"
                
                return {
                    'success': True,
                    'nro_comprobante': nro_comprobante,
                    'sucursal': sucursal,
                    'numero': next_number
                }
            else:
                return {
                    'success': False,
                    'message': 'Error obteniendo próximo número de comprobante'
                }
                
        except Exception as e:
            logger.error(f"Error getting next nro_comprobante: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo número de comprobante: {str(e)}'
            }

    def create_order_from_tiendanube(self, order_data: Dict[str, Any], deposito_id: int = 1, 
                                     user_id: int = 1, sucursal_id: int = 1) -> Dict[str, Any]:
        """
        Crear pedido en AdministraNET desde orden de TiendaNube.
        
        Args:
            order_data: Datos de la orden de TiendaNube
            deposito_id: ID del depósito de despacho
            user_id: ID del usuario del sistema
            sucursal_id: ID de la sucursal
            
        Returns:
            Dict con el resultado de la creación
        """
        try:
            import json
            from datetime import datetime, timedelta
            from decimal import Decimal
            
            # 1. Obtener próximo código de movimiento
            codigo_result = self.get_next_codigo_movimiento()
            if not codigo_result['success']:
                return codigo_result
            
            codigo_movimiento = codigo_result['codigo_movimiento']
            
            # 2. Obtener próximo número de comprobante
            nro_result = self.get_next_nro_comprobante('PED', sucursal_id)
            if not nro_result['success']:
                return nro_result
            
            nro_comprobante = nro_result['nro_comprobante']
            
            # 3. Extraer datos de la orden
            customer = order_data.get('customer', {})
            shipping = order_data.get('shipping_address', {})
            shipping_method = order_data.get('shipping', {})
            payment = order_data.get('payment', {})
            products = order_data.get('products', [])
            
            # 4. Calcular totales
            subtotal = Decimal(str(order_data.get('subtotal', 0)))
            total = Decimal(str(order_data.get('total', 0)))
            discount = Decimal(str(order_data.get('discount', 0)))
            shipping_cost = Decimal(str(order_data.get('shipping_cost', 0)))
            
            # Calcular IVA (asumiendo IVA 21% en Argentina)
            iva_21 = total * Decimal('0.21') / Decimal('1.21')
            subtotal_sin_iva = total - iva_21
            
            # 5. Determinar forma de entrega
            if shipping_method.get('type') == 'pickup':
                forma_entrega = "Retira cliente mostrador"
            else:
                forma_entrega = "Envía por despacho"
            
            # 6. Preparar JSON con información completa
            info_ped_eco = json.dumps({
                'tiendanube': {
                    'order_id': str(order_data.get('id', '')),
                    'order_number': order_data.get('number', 0),
                    'created_at': order_data.get('created_at', ''),
                    'updated_at': order_data.get('updated_at', '')
                },
                'shipping': {
                    'address': f"{shipping.get('address', '')} {shipping.get('number', '')}",
                    'floor': shipping.get('floor', ''),
                    'locality': shipping.get('locality', ''),
                    'city': shipping.get('city', ''),
                    'province': shipping.get('province', ''),
                    'zipcode': shipping.get('zipcode', ''),
                    'country': shipping.get('country', 'AR'),
                    'phone': shipping.get('phone', ''),
                    'carrier': shipping_method.get('carrier', ''),
                    'method': shipping_method.get('name', ''),
                    'tracking_number': shipping_method.get('tracking_number', ''),
                    'tracking_url': shipping_method.get('tracking_url', ''),
                    'cost': float(shipping_cost)
                },
                'customer': {
                    'name': customer.get('name', ''),
                    'email': customer.get('email', ''),
                    'phone': customer.get('phone', ''),
                    'identification': customer.get('identification', '')
                },
                'payment': {
                    'method': payment.get('name', ''),
                    'status': order_data.get('payment_status', '')
                }
            }, ensure_ascii=False)
            
            # 7. Fecha de entrega estimada (7 días por defecto)
            fecha_entrega = datetime.now() + timedelta(days=7)
            if shipping_method.get('estimated_delivery_date'):
                try:
                    fecha_entrega = datetime.fromisoformat(shipping_method['estimated_delivery_date'].replace('Z', '+00:00'))
                except:
                    pass
            
            # 8. Insertar cabecera del pedido
            insert_comp_ped = """
            INSERT INTO comp_ped (
                Fecha, TipoComprobante, NroComprobante, CodigoMovimiento,
                Estado, Codigo, ImporteVenta, SubtotalGral,
                Subtotal1, Subtotal2, IVA1, IVA2,
                Alicuota1, Alicuota2, Exento,
                PorDesc1, ImpDesc1, SubTotalDesc1, SubTotalDesc2, SubtotalDesc,
                id_condventa, CondVenta, CodViajante,
                idUsuario, codSucursal, id_deposito_despacho,
                FechaEntrega, FormaEntrega, operador_logistico,
                autorizacion_sistema, anulado,
                id_tiendanube, ped_eco, info_ped_eco, estado_pago_ecom,
                Vencimiento, TipoPedido, id_pv
            ) VALUES (
                NOW(), 'PED', %s, %s,
                'Pendiente', %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                'Autorizado', 'No',
                %s, %s, %s, %s,
                %s, 'Automatico', %s
            )
            """
            
            # Cliente ID (debe existir o crearse antes)
            cliente_id = order_data.get('adminet_customer_id', 1)  # Default genérico
            
            # Condición de venta (1 = Contado por defecto)
            id_condventa = 1
            cond_venta = "Contado"
            
            # Vendedor (0 = Sin vendedor / venta online)
            cod_viajante = 0
            
            params = (
                nro_comprobante, codigo_movimiento,
                cliente_id, float(total), float(subtotal),
                float(subtotal_sin_iva), Decimal(0), float(iva_21), Decimal(0),
                Decimal(21.0), Decimal(0), Decimal(0),
                float(discount), float(discount), Decimal(0), Decimal(0), float(subtotal - discount),
                id_condventa, cond_venta, cod_viajante,
                user_id, sucursal_id, deposito_id,
                fecha_entrega.strftime('%Y-%m-%d'), forma_entrega, shipping_method.get('carrier', ''),
                str(order_data.get('id', '')), order_data.get('number', 0), info_ped_eco, 
                order_data.get('payment_status', ''),
                fecha_entrega.strftime('%Y-%m-%d'), sucursal_id
            )
            
            result = self.execute_query(insert_comp_ped, params)
            
            if not result['success']:
                return {
                    'success': False,
                    'message': f'Error insertando cabecera del pedido: {result.get("message", "")}'
                }
            
            # 9. Insertar items del pedido
            for index, product in enumerate(products, 1):
                insert_stockp = """
                INSERT INTO stockp (
                    Fecha, CodigoArticulo, Descripcion, Cantidad,
                    cantidad_entregada, cantidad_pendiente,
                    PrecioVentaxU, PrecioCostoxU, PrecioNetoxU, PrecioBrutoxU, PrecioIVAxU,
                    Alicuota, Pordesc, Impdesc,
                    PrecioVentaxR, PrecioCostoxR, PrecioNetoxR, PrecioBrutoxR, PrecioIVAxR,
                    CodigoMovimiento, CodDeposito, IDArt,
                    Salida, Saldo, orden, codSucursal
                ) VALUES (
                    NOW(), %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s
                )
                """
                
                cantidad = Decimal(str(product.get('quantity', 1)))
                precio_unitario = Decimal(str(product.get('price', 0)))
                precio_total = cantidad * precio_unitario
                
                # Calcular IVA del producto
                iva_producto = precio_unitario * Decimal('0.21') / Decimal('1.21')
                precio_sin_iva = precio_unitario - iva_producto
                precio_total_sin_iva = precio_total - (iva_producto * cantidad)
                
                # ID del artículo (debe mapearse)
                id_art = product.get('adminet_product_id', 0)
                sku = product.get('sku', '')
                
                params_item = (
                    sku, product.get('name', ''), float(cantidad),
                    float(cantidad), float(cantidad),
                    float(precio_unitario), float(precio_sin_iva), float(precio_sin_iva), 
                    float(precio_unitario), float(iva_producto),
                    Decimal(21.0), Decimal(0), Decimal(0),
                    float(precio_total), float(precio_total_sin_iva), float(precio_total_sin_iva),
                    float(precio_total), float(iva_producto * cantidad),
                    codigo_movimiento, deposito_id, id_art,
                    float(cantidad), float(cantidad), index, sucursal_id
                )
                
                result_item = self.execute_query(insert_stockp, params_item)
                
                if not result_item['success']:
                    logger.error(f"Error insertando item {index}: {result_item.get('message', '')}")
                
                # 10. Actualizar stock comprometido
                if id_art > 0:
                    update_stock = """
                    UPDATE stock_deposito 
                    SET saldo_pedido_cliente = saldo_pedido_cliente + %s
                    WHERE id_articulo = %s AND id_deposito = %s
                    """
                    
                    self.execute_query(update_stock, (float(cantidad), id_art, deposito_id))
            
            logger.info(f"Pedido creado exitosamente: {nro_comprobante} (CodigoMovimiento: {codigo_movimiento})")
            
            return {
                'success': True,
                'codigo_movimiento': codigo_movimiento,
                'nro_comprobante': nro_comprobante,
                'message': f'Pedido creado exitosamente: {nro_comprobante}'
            }
            
        except Exception as e:
            logger.error(f"Error creating order from TiendaNube: {e}")
            return {
                'success': False,
                'message': f'Error creando pedido: {str(e)}'
            }

    def get_tiendanube_orders_with_changes(self, hours: int = 24) -> Dict[str, Any]:
        """
        Obtener pedidos de TiendaNube que han sido modificados recientemente.
        
        Args:
            hours: Horas hacia atrás para buscar cambios
            
        Returns:
            Dict con la lista de pedidos modificados
        """
        try:
            query = """
            SELECT 
                CodigoMovimiento,
                NroComprobante,
                Fecha,
                Estado,
                anulado,
                Codigo as CodCliente,
                ImporteVenta,
                id_tiendanube,
                ped_eco,
                info_ped_eco,
                FechaEntrega,
                FormaEntrega,
                operador_logistico,
                fecha_hora_entrega,
                entregado,
                motivo_no_entrega,
                fecha_control
            FROM comp_ped
            WHERE id_tiendanube IS NOT NULL
            AND id_tiendanube != ''
            AND fecha_control >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            ORDER BY fecha_control DESC
            """
            
            result = self.execute_query(query, (hours,))
            
            if result['success']:
                return {
                    'success': True,
                    'orders': result['results'],
                    'count': len(result['results'])
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error getting TiendaNube orders with changes: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo pedidos modificados: {str(e)}'
            }
    
    def get_order_by_tiendanube_id(self, tiendanube_id: str) -> Dict[str, Any]:
        """
        Obtener un pedido por su ID de TiendaNube.
        
        Args:
            tiendanube_id: ID de la orden en TiendaNube
            
        Returns:
            Dict con los datos del pedido
        """
        try:
            query = """
            SELECT 
                CodigoMovimiento,
                NroComprobante,
                Fecha,
                Estado,
                anulado,
                Codigo as CodCliente,
                ImporteVenta,
                id_tiendanube,
                ped_eco,
                info_ped_eco,
                FechaEntrega,
                FormaEntrega,
                operador_logistico,
                fecha_hora_entrega,
                entregado
            FROM comp_ped
            WHERE id_tiendanube = %s
            """
            
            result = self.execute_query(query, (tiendanube_id,))
            
            if result['success'] and result['results']:
                return {
                    'success': True,
                    'order': result['results'][0]
                }
            else:
                return {
                    'success': False,
                    'message': f'Pedido no encontrado para TiendaNube ID: {tiendanube_id}'
                }
                
        except Exception as e:
            logger.error(f"Error getting order by TiendaNube ID: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo pedido: {str(e)}'
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
        """
        Obtener estadísticas generales de AdministraNET.
        
        Returns:
            Dict con estadísticas de clientes, productos, órdenes, etc.
        """
        try:
            stats = {}
            
            # Total de clientes activos
            result = self.execute_query("SELECT COUNT(*) as total FROM cliente WHERE Estado = 'Activo'")
            if result['success'] and result['results']:
                stats['total_customers'] = result['results'][0]['total']
            else:
                stats['total_customers'] = 0
            
            # Total de productos disponibles para venta
            result = self.execute_query("SELECT COUNT(*) as total FROM articulo WHERE disponible_vta = 'Si'")
            if result['success'] and result['results']:
                stats['total_products'] = result['results'][0]['total']
            else:
                stats['total_products'] = 0
            
            # Total de artículos (incluyendo no disponibles)
            result = self.execute_query("SELECT COUNT(*) as total FROM articulo")
            if result['success'] and result['results']:
                stats['total_articles'] = result['results'][0]['total']
            else:
                stats['total_articles'] = 0
            
            # Productos para ecommerce
            result = self.execute_query("SELECT COUNT(*) as total FROM articulo WHERE ecommerce = 'Si'")
            if result['success'] and result['results']:
                stats['ecommerce_products'] = result['results'][0]['total']
            else:
                stats['ecommerce_products'] = 0
            
            # Clientes con saldo pendiente
            result = self.execute_query("SELECT COUNT(*) as total FROM cliente WHERE saldo > 0 AND Estado = 'Activo'")
            if result['success'] and result['results']:
                stats['customers_with_balance'] = result['results'][0]['total']
            else:
                stats['customers_with_balance'] = 0
            
            # Saldo total de clientes
            result = self.execute_query("SELECT SUM(saldo) as total_saldo FROM cliente WHERE Estado = 'Activo'")
            if result['success'] and result['results'] and result['results'][0]['total_saldo']:
                stats['total_customer_balance'] = float(result['results'][0]['total_saldo'])
            else:
                stats['total_customer_balance'] = 0.0
            
            return {
                'success': True,
                'statistics': stats
            }
        except Exception as e:
            logger.error(f"Error getting statistics from AdministraNET: {e}")
            return {
                'success': False,
                'message': f'Error obteniendo estadísticas: {str(e)}',
                'statistics': {}
            }
    
    def close_connection(self):
        """Cerrar conexión con la base de datos."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.connection = None
    
    # ============================================================================
    # MÉTODOS ADICIONALES PARA CLIENTES
    # ============================================================================
    
    def search_customers(self, search_term: str, limit: int = 50) -> Dict[str, Any]:
        """
        Buscar clientes por nombre, CUIT, email o teléfono.
        
        Args:
            search_term: Término de búsqueda
            limit: Número máximo de resultados
        
        Returns:
            Dict con resultados de la búsqueda
        """
        try:
            search_pattern = f"%{search_term}%"
            query = """
            SELECT 
                Codigo,
                nombre_cliente,
                nombre_fantasia,
                CUIT,
                Email,
                telefono,
                Estado,
                saldo
            FROM cliente
            WHERE (nombre_cliente LIKE %s 
                OR nombre_fantasia LIKE %s 
                OR CUIT LIKE %s 
                OR Email LIKE %s 
                OR telefono LIKE %s)
            AND Estado = 'Activo'
            ORDER BY nombre_cliente
            LIMIT %s
            """
            
            result = self.execute_query(query, (
                search_pattern, search_pattern, search_pattern, 
                search_pattern, search_pattern, limit
            ))
            
            if result['success']:
                return {
                    'success': True,
                    'customers': result['results'],
                    'count': len(result['results'])
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error searching customers: {e}")
            return {
                'success': False,
                'message': f'Error buscando clientes: {str(e)}'
            }
    
    def get_customer_by_cuit(self, cuit: str) -> Dict[str, Any]:
        """
        Obtener cliente por CUIT.
        
        Args:
            cuit: CUIT del cliente
        
        Returns:
            Dict con datos del cliente
        """
        query = """
        SELECT 
            Codigo,
            nombre_cliente,
            nombre_fantasia,
            CUIT,
            tipo_doc,
            telefono,
            Email,
            Estado
        FROM cliente
        WHERE CUIT = %s
        LIMIT 1
        """
        
        result = self.execute_query(query, (cuit,))
        if result['success'] and result['results']:
            return {
                'success': True,
                'customer': result['results'][0]
            }
        return {
            'success': False,
            'message': 'Cliente no encontrado'
        }
    
    def get_customer_by_email(self, email: str) -> Dict[str, Any]:
        """
        Obtener cliente por email.
        
        Args:
            email: Email del cliente
        
        Returns:
            Dict con datos del cliente
        """
        query = """
        SELECT 
            Codigo,
            nombre_cliente,
            nombre_fantasia,
            CUIT,
            Email,
            telefono,
            Estado
        FROM cliente
        WHERE Email = %s OR EmailContacto = %s
        LIMIT 1
        """
        
        result = self.execute_query(query, (email, email))
        if result['success'] and result['results']:
            return {
                'success': True,
                'customer': result['results'][0]
            }
        return {
            'success': False,
            'message': 'Cliente no encontrado'
        }
    
    def get_customer_count(self, estado: str = 'Activo') -> Dict[str, Any]:
        """
        Obtener conteo de clientes por estado.
        
        Args:
            estado: Estado del cliente (Activo, Inactivo, etc.)
        
        Returns:
            Dict con el conteo
        """
        try:
            if estado:
                query = "SELECT COUNT(*) as total FROM cliente WHERE Estado = %s"
                result = self.execute_query(query, (estado,))
            else:
                query = "SELECT COUNT(*) as total FROM cliente"
                result = self.execute_query(query)
            
            if result['success'] and result['results']:
                return {
                    'success': True,
                    'count': result['results'][0]['total']
                }
            else:
                return {
                    'success': False,
                    'message': 'Error obteniendo conteo',
                    'count': 0
                }
        except Exception as e:
            logger.error(f"Error getting customer count: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'count': 0
            } 