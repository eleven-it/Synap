"""
Servicio para validar la integridad entre puestos asignados a usuarios y sus permisos
Verifica que los permisos del sistema y del menú estén correctamente asignados al puesto
"""
import logging
import MySQLdb
from django.conf import settings
from typing import Dict, List, Optional, Tuple
from core.services.administranet_permisos_sistema import AdministraNETPermisosSistemaService
from core.services.administranet_permisos_menu import AdministraNETPermisosMenuService

logger = logging.getLogger(__name__)


class AdministraNETValidacionPuestosService:
    """Servicio para validar integridad de puestos y permisos"""
    
    def __init__(self, server: str = None, port: str = None):
        """
        Inicializa el servicio de validación
        
        Args:
            server: Nombre del servidor MySQL (host/IP). Si no se proporciona, usa DB_HOST del .env
            port: Puerto MySQL. Si no se proporciona, usa DB_PORT del .env
        """
        mysql_config = settings.DATABASES['mysql']
        self.server = server or mysql_config['HOST']
        self.port = port or mysql_config['PORT']
        self.user = mysql_config['USER']
        self.password = mysql_config['PASSWORD']
        self.permisos_sistema_service = AdministraNETPermisosSistemaService(server, port)
        self.permisos_menu_service = AdministraNETPermisosMenuService(server, port)
    
    def _get_connection(self, db_name: str):
        """
        Establece una conexión directa a MySQLdb
        """
        return MySQLdb.connect(
            host=self.server,
            port=int(self.port),
            user=self.user,
            passwd=self.password,
            db=db_name,
            charset='latin1'
        )
    
    def validar_integridad_puesto(self, base_empresa: str, id_puesto: int) -> Dict:
        """
        Valida la integridad de un puesto específico
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_puesto: ID del puesto a validar
            
        Returns:
            Diccionario con el resultado de la validación:
            {
                'valido': bool,
                'errores': List[str],
                'advertencias': List[str],
                'tiene_permisos_sistema': bool,
                'tiene_permisos_menu': bool,
                'cantidad_permisos_menu': int,
                'cantidad_permisos_sistema': int
            }
        """
        resultado = {
            'valido': True,
            'errores': [],
            'advertencias': [],
            'tiene_permisos_sistema': False,
            'tiene_permisos_menu': False,
            'cantidad_permisos_menu': 0,
            'cantidad_permisos_sistema': 0
        }
        
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Verificar que el puesto existe
            cursor.execute("SELECT idpuesto, puesto FROM puestos WHERE idpuesto = %s", [id_puesto])
            puesto_row = cursor.fetchone()
            
            if not puesto_row:
                resultado['valido'] = False
                resultado['errores'].append(f"El puesto con ID {id_puesto} no existe")
                cursor.close()
                conn.close()
                return resultado
            
            nombre_puesto = puesto_row[1] or f"Puesto {id_puesto}"
            
            # Verificar permisos del sistema (tabla permisos_sistema)
            cursor.execute("SELECT COUNT(*) FROM permisos_sistema WHERE IDPuesto = %s", [id_puesto])
            count_permisos_sistema = cursor.fetchone()[0]
            resultado['cantidad_permisos_sistema'] = count_permisos_sistema
            resultado['tiene_permisos_sistema'] = count_permisos_sistema > 0
            
            if count_permisos_sistema == 0:
                resultado['advertencias'].append(f"El puesto '{nombre_puesto}' no tiene permisos del sistema asignados (tabla permisos_sistema)")
            
            # Verificar permisos del menú (tabla permisos)
            cursor.execute("SELECT COUNT(*) FROM permisos WHERE IDpuesto = %s AND Permiso = '1'", [str(id_puesto)])
            count_permisos_menu = cursor.fetchone()[0]
            resultado['cantidad_permisos_menu'] = count_permisos_menu
            resultado['tiene_permisos_menu'] = count_permisos_menu > 0
            
            if count_permisos_menu == 0:
                resultado['advertencias'].append(f"El puesto '{nombre_puesto}' no tiene permisos del menú asignados (tabla permisos)")
            
            # Verificar permisos del sistema por puesto (tabla permiso_sistema_puesto)
            cursor.execute("SELECT COUNT(*) FROM permiso_sistema_puesto WHERE id_puesto = %s", [id_puesto])
            count_permiso_sistema_puesto = cursor.fetchone()[0]
            
            if count_permiso_sistema_puesto == 0:
                resultado['advertencias'].append(f"El puesto '{nombre_puesto}' no tiene valores personalizados de permisos del sistema (tabla permiso_sistema_puesto)")
            
            # Si no tiene ningún tipo de permiso, es un error crítico
            if not resultado['tiene_permisos_sistema'] and not resultado['tiene_permisos_menu']:
                resultado['valido'] = False
                resultado['errores'].append(f"El puesto '{nombre_puesto}' no tiene ningún permiso asignado")
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Validación del puesto {id_puesto} ({nombre_puesto}): {len(resultado['errores'])} errores, {len(resultado['advertencias'])} advertencias")
            return resultado
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al validar puesto {id_puesto} en empresa {base_empresa}: {e}")
            resultado['valido'] = False
            resultado['errores'].append(f"Error al validar el puesto: {str(e)}")
            return resultado
        except Exception as e:
            logger.error(f"Error inesperado al validar puesto: {e}", exc_info=True)
            resultado['valido'] = False
            resultado['errores'].append(f"Error inesperado: {str(e)}")
            return resultado
    
    def validar_integridad_usuario(self, base_empresa: str, id_usuario: int) -> Dict:
        """
        Valida la integridad del puesto asignado a un usuario específico
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_usuario: ID del usuario a validar
            
        Returns:
            Diccionario con el resultado de la validación incluyendo datos del usuario
            {
                'valido': bool,
                'errores': List[str],
                'advertencias': List[str],
                'usuario': Dict con datos del usuario,
                'puesto': Dict con datos del puesto y validación
            }
        """
        resultado = {
            'valido': True,
            'errores': [],
            'advertencias': [],
            'usuario': None,
            'puesto': None
        }
        
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Obtener datos del usuario
            cursor.execute("""
                SELECT id_usuario, cod_usuario, nombre_usuario, apellido_usuario, id_puesto
                FROM usuarios WHERE id_usuario = %s
            """, [id_usuario])
            
            usuario_row = cursor.fetchone()
            
            if not usuario_row:
                resultado['valido'] = False
                resultado['errores'].append(f"El usuario con ID {id_usuario} no existe")
                cursor.close()
                conn.close()
                return resultado
            
            resultado['usuario'] = {
                'id_usuario': usuario_row[0],
                'cod_usuario': usuario_row[1] or '',
                'nombre_usuario': usuario_row[2] or '',
                'apellido_usuario': usuario_row[3] or '',
                'id_puesto': usuario_row[4]
            }
            
            id_puesto = usuario_row[4]
            
            if not id_puesto:
                resultado['valido'] = False
                resultado['errores'].append(f"El usuario '{usuario_row[1]}' no tiene un puesto asignado")
                cursor.close()
                conn.close()
                return resultado
            
            # Validar el puesto del usuario
            validacion_puesto = self.validar_integridad_puesto(base_empresa, id_puesto)
            resultado['puesto'] = validacion_puesto
            
            # Combinar errores y advertencias
            resultado['errores'].extend(validacion_puesto['errores'])
            resultado['advertencias'].extend(validacion_puesto['advertencias'])
            resultado['valido'] = validacion_puesto['valido']
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Validación del usuario {id_usuario}: {len(resultado['errores'])} errores, {len(resultado['advertencias'])} advertencias")
            return resultado
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al validar usuario {id_usuario} en empresa {base_empresa}: {e}")
            resultado['valido'] = False
            resultado['errores'].append(f"Error al validar el usuario: {str(e)}")
            return resultado
        except Exception as e:
            logger.error(f"Error inesperado al validar usuario: {e}", exc_info=True)
            resultado['valido'] = False
            resultado['errores'].append(f"Error inesperado: {str(e)}")
            return resultado
    
    def validar_todos_los_usuarios(self, base_empresa: str, id_empresa: int = None) -> Dict:
        """
        Valida la integridad de todos los usuarios de una empresa
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_empresa: ID de la empresa (opcional)
            
        Returns:
            Diccionario con resumen de validaciones:
            {
                'total_usuarios': int,
                'usuarios_validos': int,
                'usuarios_invalidos': int,
                'usuarios_sin_puesto': int,
                'detalles': List[Dict] con detalles de cada usuario
            }
        """
        resultado = {
            'total_usuarios': 0,
            'usuarios_validos': 0,
            'usuarios_invalidos': 0,
            'usuarios_sin_puesto': 0,
            'detalles': []
        }
        
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Obtener id_empresa si no se proporciona
            if not id_empresa:
                conn_empresas = self._get_connection('empresas')
                cursor_empresas = conn_empresas.cursor()
                cursor_empresas.execute("SELECT id_empresa FROM empresas WHERE base_empresa = %s LIMIT 1", [base_empresa])
                row_empresa = cursor_empresas.fetchone()
                cursor_empresas.close()
                conn_empresas.close()
                
                if row_empresa:
                    id_empresa = row_empresa[0]
            
            # Obtener todos los usuarios activos
            query = "SELECT id_usuario, cod_usuario, nombre_usuario, apellido_usuario, id_puesto FROM usuarios WHERE baja_usuario <> 'Si'"
            params = []
            
            if id_empresa:
                query += " AND id_empresa = %s"
                params.append(id_empresa)
            
            cursor.execute(query, params)
            
            usuarios = cursor.fetchall()
            resultado['total_usuarios'] = len(usuarios)
            
            for usuario_row in usuarios:
                id_usuario = usuario_row[0]
                id_puesto = usuario_row[4]
                
                detalle = {
                    'id_usuario': id_usuario,
                    'cod_usuario': usuario_row[1] or '',
                    'nombre_completo': f"{usuario_row[2] or ''} {usuario_row[3] or ''}".strip(),
                    'id_puesto': id_puesto,
                    'valido': False,
                    'errores': [],
                    'advertencias': []
                }
                
                if not id_puesto:
                    resultado['usuarios_sin_puesto'] += 1
                    detalle['errores'].append("Usuario sin puesto asignado")
                else:
                    validacion = self.validar_integridad_puesto(base_empresa, id_puesto)
                    detalle['valido'] = validacion['valido']
                    detalle['errores'] = validacion['errores']
                    detalle['advertencias'] = validacion['advertencias']
                    
                    if validacion['valido']:
                        resultado['usuarios_validos'] += 1
                    else:
                        resultado['usuarios_invalidos'] += 1
                
                resultado['detalles'].append(detalle)
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Validación completa: {resultado['usuarios_validos']} válidos, {resultado['usuarios_invalidos']} inválidos, {resultado['usuarios_sin_puesto']} sin puesto")
            return resultado
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al validar usuarios de empresa {base_empresa}: {e}")
            return resultado
        except Exception as e:
            logger.error(f"Error inesperado al validar usuarios: {e}", exc_info=True)
            return resultado
    
    def validar_integridad_empresa_sucursal(self, base_empresa: str, id_usuario: int, id_empresa: int = None, id_sucursal: int = None) -> Dict:
        """
        Valida la integridad de empresa y sucursal asignados a un usuario
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_usuario: ID del usuario a validar
            id_empresa: ID de la empresa del usuario (opcional, se obtiene del usuario si no se proporciona)
            id_sucursal: ID de la sucursal del usuario (opcional, se obtiene del usuario si no se proporciona)
            
        Returns:
            Diccionario con el resultado de la validación:
            {
                'valido': bool,
                'errores': List[str],
                'advertencias': List[str],
                'empresa_existe': bool,
                'sucursal_existe': bool,
                'sucursal_pertenece_empresa': bool,
                'nombre_empresa': str,
                'nombre_sucursal': str
            }
        """
        resultado = {
            'valido': True,
            'errores': [],
            'advertencias': [],
            'empresa_existe': False,
            'sucursal_existe': False,
            'sucursal_pertenece_empresa': False,
            'nombre_empresa': '',
            'nombre_sucursal': ''
        }
        
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Obtener id_empresa e id_sucursal del usuario si no se proporcionan
            if not id_empresa or not id_sucursal:
                cursor.execute("""
                    SELECT id_empresa, id_sucursal
                    FROM usuarios WHERE id_usuario = %s
                """, [id_usuario])
                
                usuario_row = cursor.fetchone()
                if usuario_row:
                    if not id_empresa:
                        id_empresa = usuario_row[0]
                    if not id_sucursal:
                        id_sucursal = usuario_row[1]
            
            # Validar empresa
            if id_empresa and id_empresa > 0:
                cursor.execute("SELECT id_empresa, Nombre FROM datosempresa WHERE id_empresa = %s", [id_empresa])
                empresa_row = cursor.fetchone()
                
                if empresa_row:
                    resultado['empresa_existe'] = True
                    resultado['nombre_empresa'] = empresa_row[1] or f"Empresa {id_empresa}"
                else:
                    resultado['valido'] = False
                    resultado['errores'].append(f"La empresa con ID {id_empresa} no existe en la base de datos")
            else:
                resultado['advertencias'].append("El usuario no tiene empresa asignada (id_empresa = 0 o NULL)")
            
            # Validar sucursal
            if id_sucursal and id_sucursal > 0:
                cursor.execute("""
                    SELECT s.id_sucursal, s.nombre_sucursal, s.id_empresa, s.anulado
                    FROM sucursales s
                    WHERE s.id_sucursal = %s
                """, [id_sucursal])
                
                sucursal_row = cursor.fetchone()
                
                if sucursal_row:
                    resultado['sucursal_existe'] = True
                    resultado['nombre_sucursal'] = sucursal_row[1] or f"Sucursal {id_sucursal}"
                    
                    # Verificar que la sucursal pertenezca a la empresa del usuario
                    if id_empresa and id_empresa > 0:
                        if sucursal_row[2] == id_empresa:
                            resultado['sucursal_pertenece_empresa'] = True
                        else:
                            resultado['valido'] = False
                            resultado['errores'].append(
                                f"La sucursal '{resultado['nombre_sucursal']}' (ID: {id_sucursal}) "
                                f"pertenece a la empresa {sucursal_row[2]}, pero el usuario está asignado a la empresa {id_empresa}"
                            )
                    
                    # Verificar si la sucursal está anulada
                    if sucursal_row[3] and sucursal_row[3].lower() == 'si':
                        resultado['advertencias'].append(f"La sucursal '{resultado['nombre_sucursal']}' está anulada")
                else:
                    resultado['valido'] = False
                    resultado['errores'].append(f"La sucursal con ID {id_sucursal} no existe en la base de datos")
            else:
                resultado['advertencias'].append("El usuario no tiene sucursal asignada (id_sucursal = 0 o NULL)")
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Validación empresa/sucursal del usuario {id_usuario}: {len(resultado['errores'])} errores, {len(resultado['advertencias'])} advertencias")
            return resultado
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al validar empresa/sucursal del usuario {id_usuario} en empresa {base_empresa}: {e}")
            resultado['valido'] = False
            resultado['errores'].append(f"Error al validar empresa/sucursal: {str(e)}")
            return resultado
        except Exception as e:
            logger.error(f"Error inesperado al validar empresa/sucursal: {e}", exc_info=True)
            resultado['valido'] = False
            resultado['errores'].append(f"Error inesperado: {str(e)}")
            return resultado

