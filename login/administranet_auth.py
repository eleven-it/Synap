"""
Servicio de autenticación con administraNET Gestión
Reemplaza Firebase con conexión directa a MySQL de administraNET
"""
import logging
import MySQLdb
from django.db import connections
from django.conf import settings
from typing import Optional, Dict, List
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import hashlib

logger = logging.getLogger(__name__)

# Clave de encriptación AES (debe coincidir con administraNET Gestión)
AES_KEY = b'a7v8xx2'  # Clave usada en administraNET para AES_DECRYPT

# Timeout de conexión MySQL (segundos) - evita que requests se cuelguen si MySQL es inaccesible
MYSQL_CONNECT_TIMEOUT = 5


class AdministraNETAuth:
    """Servicio para autenticación con administraNET Gestión"""
    
    def __init__(self, server: str = None, port: str = None, database: str = None):
        """
        Inicializa el servicio de autenticación
        
        Args:
            server: Nombre del servidor MySQL (host/IP). Si no se proporciona, usa DB_HOST del .env
            port: Puerto MySQL. Si no se proporciona, usa DB_PORT del .env
            database: Nombre de la base de datos. Si no se proporciona, usa DB_NAME del .env
        """
        mysql_config = settings.DATABASES['mysql']
        self.server = server or mysql_config['HOST']
        self.port = port or mysql_config['PORT']
        self.database = database or mysql_config['NAME']
        self.user = mysql_config['USER']
        self.password = mysql_config['PASSWORD']
    
    def get_connection(self, db_name: str = None):
        """
        Obtiene una conexión a la base de datos MySQL de administraNET
        
        Args:
            db_name: Nombre de la base de datos específica (ej: 'empresas' o nombre de empresa)
        """
        db_name = db_name or self.database
        
        # Usar la conexión MySQL configurada en settings
        connection = connections['mysql']
        
        # Si necesitamos cambiar de base de datos, ejecutamos USE
        if db_name and db_name != self.database:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"USE `{db_name}`")
            except Exception as e:
                logger.error(f"Error al cambiar a base de datos {db_name}: {e}")
                raise
        
        return connection
    
    def get_empresas(self) -> List[Dict]:
        """
        Obtiene la lista de empresas disponibles desde la base 'empresas'
        Similar a como lo hace administraNET Gestión: conecta directamente a la base 'empresas'
        del servidor configurado.
        
        Returns:
            Lista de diccionarios con información de empresas
        """
        try:
            # Conectar directamente a la base 'empresas' como lo hace administraNET Gestión
            # ConnectionString: "SERVER=...;DATABASE=empresas;UID=administranet;PWD=a7v8xx0805;CHARSET=latin1"
            conn = MySQLdb.connect(
                host=self.server,
                port=int(self.port),
                user=self.user,
                passwd=self.password,
                db='empresas',  # Base de datos donde están las empresas
                charset='latin1',
                connect_timeout=MYSQL_CONNECT_TIMEOUT,
            )
            
            cursor = conn.cursor()
            
            # Query igual a administraNET: SELECT * FROM empresas
            cursor.execute("""
                SELECT 
                    id_empresa,
                    nombre_empresa,
                    base_empresa
                FROM empresas
                ORDER BY nombre_empresa
            """)
            
            empresas = []
            for row in cursor.fetchall():
                empresas.append({
                    'id_empresa': row[0],
                    'nombre_empresa': row[1] if row[1] else '',
                    'base_empresa': row[2] if row[2] else ''
                })
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Obtenidas {len(empresas)} empresas del servidor {self.server}")
            return empresas
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al obtener empresas del servidor {self.server}: {e}")
            # Fallback para entorno local: si no existe la base 'empresas', ofrecer la base del .env
            # (ej. solo se restauró 'administranet' y no existe la base empresas)
            try:
                base_default = settings.DATABASES['mysql'].get('NAME', 'administranet')
                return [{
                    'id_empresa': 1,
                    'nombre_empresa': f'Local ({base_default})',
                    'base_empresa': base_default,
                }]
            except Exception:
                return []
        except Exception as e:
            logger.error(f"Error inesperado al obtener empresas: {e}", exc_info=True)
            try:
                base_default = settings.DATABASES['mysql'].get('NAME', 'administranet')
                return [{
                    'id_empresa': 1,
                    'nombre_empresa': f'Local ({base_default})',
                    'base_empresa': base_default,
                }]
            except Exception:
                return []
    
    def validate_user(self, cod_usuario: str, password: str, base_empresa: str) -> Optional[Dict]:
        """
        Valida las credenciales del usuario contra la base de administraNET
        Similar a como lo hace administraNET Gestión: conecta a la base específica de la empresa
        
        Args:
            cod_usuario: Código de usuario (nombre de usuario)
            password: Contraseña en texto plano
            base_empresa: Nombre de la base de datos de la empresa
            
        Returns:
            Diccionario con datos del usuario si es válido, None en caso contrario
        """
        try:
            # Conectar directamente a la base de la empresa como lo hace administraNET Gestión
            conn = MySQLdb.connect(
                host=self.server,
                port=int(self.port),
                user=self.user,
                passwd=self.password,
                db=base_empresa,  # Base de datos específica de la empresa
                charset='latin1',
                connect_timeout=MYSQL_CONNECT_TIMEOUT,
            )
            
            cursor = conn.cursor()
            
            # Primero verificar si existe la columna 'idioma'
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'usuarios' 
                AND COLUMN_NAME = 'idioma'
            """, [base_empresa])
            
            tiene_idioma = cursor.fetchone()[0] > 0
            
            # Query igual a administraNET Gestión: AES_DECRYPT con la clave 'a7v8xx2'
            # Adaptamos la query según si tiene columna idioma o no
            if tiene_idioma:
                cursor.execute("""
                    SELECT 
                        id_usuario,
                        cod_usuario,
                        nombre_usuario,
                        apellido_usuario,
                        id_empresa,
                        id_sucursal,
                        id_puesto,
                        id_punto_venta,
                        id_deposito,
                        id_caja,
                        tipo_busqueda_defecto,
                        baja_usuario,
                        idioma
                    FROM usuarios 
                    WHERE baja_usuario = 'No' 
                    AND cod_usuario = %s 
                    AND AES_DECRYPT(password_usuario, 'a7v8xx2') = %s
                """, [cod_usuario.lower().strip(), password.strip()])
            else:
                # Query sin columna idioma (para bases antiguas)
                cursor.execute("""
                    SELECT 
                        id_usuario,
                        cod_usuario,
                        nombre_usuario,
                        apellido_usuario,
                        id_empresa,
                        id_sucursal,
                        id_puesto,
                        id_punto_venta,
                        id_deposito,
                        id_caja,
                        tipo_busqueda_defecto,
                        baja_usuario
                    FROM usuarios 
                    WHERE baja_usuario = 'No' 
                    AND cod_usuario = %s 
                    AND AES_DECRYPT(password_usuario, 'a7v8xx2') = %s
                """, [cod_usuario.lower().strip(), password.strip()])
            
            row = cursor.fetchone()
            
            if row:
                # Construir diccionario según si tiene idioma o no
                user_dict = {
                    'id_usuario': row[0],
                    'cod_usuario': row[1],
                    'nombre_usuario': row[2] if row[2] else '',
                    'apellido_usuario': row[3] if row[3] else '',
                    'id_empresa': row[4],
                    'id_sucursal': row[5],
                    'id_puesto': row[6],
                    'id_punto_venta': row[7],
                    'id_deposito': row[8],
                    'id_caja': row[9],
                    'tipo_busqueda_defecto': row[10],
                    'baja_usuario': row[11],
                    'base_empresa': base_empresa
                }
                
                # Agregar idioma si existe
                if tiene_idioma:
                    user_dict['idioma'] = row[12] or 'es'
                else:
                    user_dict['idioma'] = 'es'  # Valor por defecto
                
                # Obtener nombre del puesto desde la tabla puestos (antes de cerrar la conexión)
                if user_dict['id_puesto']:
                    try:
                        cursor.execute("""
                            SELECT puesto 
                            FROM puestos 
                            WHERE idpuesto = %s AND anulado = 'No'
                        """, [user_dict['id_puesto']])
                        puesto_row = cursor.fetchone()
                        if puesto_row:
                            user_dict['nombre_puesto'] = puesto_row[0]
                        else:
                            user_dict['nombre_puesto'] = None
                    except Exception as e:
                        logger.warning(f"No se pudo obtener nombre del puesto: {e}")
                        user_dict['nombre_puesto'] = None
                else:
                    user_dict['nombre_puesto'] = None
                
                cursor.close()
                conn.close()
                return user_dict
            
            cursor.close()
            conn.close()
            
            return None
                
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al validar usuario {cod_usuario} en empresa {base_empresa}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al validar usuario: {e}", exc_info=True)
            return None
    
    def get_servidores(self) -> List[Dict]:
        """
        Obtiene la lista de servidores desde el archivo conexion.txt o configuración
        
        Returns:
            Lista de servidores disponibles
        """
        # Por ahora retornamos el servidor configurado en settings
        # En el futuro se puede leer de conexion.txt o base de datos
        return [{
            'host': self.server,
            'port': self.port,
            'descripcion': f'Servidor {self.server}',
            'default': True
        }]
    
    def create_session(self, user_data: Dict, base_empresa: str, ip_address: str = None) -> Dict:
        """
        Crea un registro de sesión en la base de datos
        Similar a como lo hace administraNET Gestión
        
        Args:
            user_data: Datos del usuario validado
            base_empresa: Base de datos de la empresa
            ip_address: Dirección IP del cliente (opcional)
            
        Returns:
            Datos de la sesión creada
        """
        try:
            # Conectar directamente a la base de la empresa
            conn = MySQLdb.connect(
                host=self.server,
                port=int(self.port),
                user=self.user,
                passwd=self.password,
                db=base_empresa,
                charset='latin1',
                connect_timeout=MYSQL_CONNECT_TIMEOUT,
            )
            
            ip_address = ip_address or '127.0.0.1'
            
            cursor = conn.cursor()
            
            # Verificar si existe tabla sesion
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = 'sesion'
            """, [base_empresa])
            
            table_exists = cursor.fetchone()[0] > 0
            
            if table_exists:
                # Insertar sesión (igual que administraNET Gestión)
                cursor.execute("""
                    INSERT INTO sesion (id_usuario, id_sucursal, fechainicio, ip)
                    VALUES (%s, %s, NOW(), %s)
                """, [user_data['id_usuario'], user_data['id_sucursal'], ip_address])
                
                # Obtener ID de sesión
                cursor.execute("SELECT LAST_INSERT_ID() as idsession")
                id_sesion = cursor.fetchone()[0]
                
                conn.commit()
                cursor.close()
                conn.close()
                
                return {
                    'id_sesion': id_sesion,
                    'id_usuario': user_data['id_usuario'],
                    'id_sucursal': user_data['id_sucursal'],
                    'fechainicio': None,
                    'ip': ip_address
                }
            else:
                logger.warning(f"Tabla 'sesion' no existe en base {base_empresa}")
                cursor.close()
                conn.close()
                return {
                    'id_sesion': None,
                    'id_usuario': user_data['id_usuario'],
                    'id_sucursal': user_data['id_sucursal'],
                    'fechainicio': None,
                    'ip': ip_address
                }
                
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al crear sesión: {e}", exc_info=True)
            return {
                'id_sesion': None,
                'id_usuario': user_data.get('id_usuario'),
                'id_sucursal': user_data.get('id_sucursal'),
                'fechainicio': None,
                'ip': ip_address or '127.0.0.1'
            }
        except Exception as e:
            logger.error(f"Error inesperado al crear sesión: {e}", exc_info=True)
            return {
                'id_sesion': None,
                'id_usuario': user_data.get('id_usuario'),
                'id_sucursal': user_data.get('id_sucursal'),
                'fechainicio': None,
                'ip': ip_address or '127.0.0.1'
            }

