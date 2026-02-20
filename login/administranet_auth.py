"""
Servicio de autenticación con administraNET Gestión.
Usa el pool MySQL de core (origen único). Conexiones vía context manager.
"""
import logging
from django.conf import settings
from typing import Optional, Dict, List

from core.mysql_pool import get_connection as pool_get_connection

logger = logging.getLogger(__name__)

# Clave de encriptación AES (debe coincidir con administraNET Gestión)
AES_KEY = b'a7v8xx2'  # Clave usada en administraNET para AES_DECRYPT


class AdministraNETAuth:
    """Servicio para autenticación con administraNET Gestión"""

    def __init__(self, server: str = None, port: str = None, database: str = None):
        """
        Inicializa el servicio de autenticación.

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
        Context manager: obtiene una conexión del pool MySQL.
        Uso: with auth_service.get_connection(base_empresa) as connection: ...
        """
        db = (db_name or self.database).strip() or self.database
        return pool_get_connection(db)
    
    def get_empresas(self) -> List[Dict]:
        """
        Obtiene la lista de empresas disponibles desde la base 'empresas'.
        Usa el pool MySQL (core.mysql_pool).

        Returns:
            Lista de diccionarios con información de empresas
        """
        try:
            with pool_get_connection('empresas') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id_empresa, nombre_empresa, base_empresa
                    FROM empresas
                    ORDER BY nombre_empresa
                """)
                empresas = [
                    {
                        'id_empresa': row[0],
                        'nombre_empresa': row[1] if row[1] else '',
                        'base_empresa': row[2] if row[2] else '',
                    }
                    for row in cursor.fetchall()
                ]
                cursor.close()
            logger.info("Obtenidas %s empresas del servidor %s", len(empresas), self.server)
            return empresas
        except Exception as e:
            logger.error("Error al obtener empresas del servidor %s: %s", self.server, e)
            base_default = settings.DATABASES['mysql'].get('NAME', 'administranet')
            return [{
                'id_empresa': 1,
                'nombre_empresa': f'Local ({base_default})',
                'base_empresa': base_default,
            }]
    
    def validate_user(self, cod_usuario: str, password: str, base_empresa: str) -> Optional[Dict]:
        """
        Valida las credenciales del usuario contra la base de administraNET.
        Usa el pool MySQL (core.mysql_pool).

        Returns:
            Diccionario con datos del usuario si es válido, None en caso contrario.
        """
        try:
            with pool_get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'usuarios' AND COLUMN_NAME = 'idioma'
                """, [base_empresa])
                tiene_idioma = cursor.fetchone()[0] > 0

                if tiene_idioma:
                    cursor.execute("""
                        SELECT id_usuario, cod_usuario, nombre_usuario, apellido_usuario,
                               id_empresa, id_sucursal, id_puesto, id_punto_venta, id_deposito, id_caja,
                               tipo_busqueda_defecto, baja_usuario, idioma
                        FROM usuarios
                        WHERE baja_usuario = 'No' AND cod_usuario = %s
                          AND AES_DECRYPT(password_usuario, 'a7v8xx2') = %s
                    """, [cod_usuario.lower().strip(), password.strip()])
                else:
                    cursor.execute("""
                        SELECT id_usuario, cod_usuario, nombre_usuario, apellido_usuario,
                               id_empresa, id_sucursal, id_puesto, id_punto_venta, id_deposito, id_caja,
                               tipo_busqueda_defecto, baja_usuario
                        FROM usuarios
                        WHERE baja_usuario = 'No' AND cod_usuario = %s
                          AND AES_DECRYPT(password_usuario, 'a7v8xx2') = %s
                    """, [cod_usuario.lower().strip(), password.strip()])

                row = cursor.fetchone()
                if not row:
                    return None

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
                    'base_empresa': base_empresa,
                    'idioma': (row[12] if tiene_idioma else None) or 'es',
                }

                if user_dict['id_puesto']:
                    try:
                        cursor.execute(
                            "SELECT puesto FROM puestos WHERE idpuesto = %s AND anulado = 'No'",
                            [user_dict['id_puesto']],
                        )
                        puesto_row = cursor.fetchone()
                        user_dict['nombre_puesto'] = puesto_row[0] if puesto_row else None
                    except Exception as e:
                        logger.warning("No se pudo obtener nombre del puesto: %s", e)
                        user_dict['nombre_puesto'] = None
                else:
                    user_dict['nombre_puesto'] = None

                cursor.close()
                return user_dict

        except Exception as e:
            logger.warning("Error al validar usuario %s en empresa %s: %s", cod_usuario, base_empresa, e)
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
        Crea un registro de sesión en la base de datos (usa pool MySQL).
        Returns:
            Datos de la sesión creada (id_sesion puede ser None si no existe tabla sesion).
        """
        ip_address = ip_address or '127.0.0.1'
        fallback = {
            'id_sesion': None,
            'id_usuario': user_data.get('id_usuario'),
            'id_sucursal': user_data.get('id_sucursal'),
            'fechainicio': None,
            'ip': ip_address,
        }
        try:
            with pool_get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = 'sesion'
                """, [base_empresa])
                if cursor.fetchone()[0] == 0:
                    logger.warning("Tabla 'sesion' no existe en base %s", base_empresa)
                    return fallback

                cursor.execute("""
                    INSERT INTO sesion (id_usuario, id_sucursal, fechainicio, ip)
                    VALUES (%s, %s, NOW(), %s)
                """, [user_data['id_usuario'], user_data['id_sucursal'], ip_address])
                cursor.execute("SELECT LAST_INSERT_ID()")
                id_sesion = cursor.fetchone()[0]
                conn.commit()
                cursor.close()
                return {
                    'id_sesion': id_sesion,
                    'id_usuario': user_data['id_usuario'],
                    'id_sucursal': user_data['id_sucursal'],
                    'fechainicio': None,
                    'ip': ip_address,
                }
        except Exception as e:
            logger.warning("Error al crear sesión: %s", e, exc_info=True)
            return fallback

