"""
Servicio para gestión de puestos en administraNET Gestión
Gestiona la tabla puestos que son equivalentes a roles
"""
import logging
import MySQLdb
from django.conf import settings
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class CreacionPuestoBloqueadaError(Exception):
    """
    Se intentó crear un puesto desde Synap mientras la creación está bloqueada.

    Los puestos (``puestos.idpuesto``) son el ancla fija de AdministraNET; Synap no
    debe crearlos. Ver ``settings.SYNAP_BLOQUEAR_CREAR_PUESTOS`` y
    openspec/changes/permisos-roles-synap-independientes/design.md.
    """
    pass


class AdministraNETPuestosService:
    """Servicio para gestión de puestos (roles) en administraNET Gestión"""
    
    def __init__(self, server: str = None, port: str = None):
        """
        Inicializa el servicio de gestión de puestos
        
        Args:
            server: Nombre del servidor MySQL (host/IP). Si no se proporciona, usa DB_HOST del .env
            port: Puerto MySQL. Si no se proporciona, usa DB_PORT del .env
        """
        mysql_config = settings.DATABASES['mysql']
        self.server = server or mysql_config['HOST']
        self.port = port or mysql_config['PORT']
        self.user = mysql_config['USER']
        self.password = mysql_config['PASSWORD']
    
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
    
    def listar_puestos(self, base_empresa: str, busqueda: str = None) -> List[Dict]:
        """
        Lista puestos de una empresa
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            busqueda: Texto de búsqueda (nombre del puesto)
            
        Returns:
            Lista de diccionarios con información de puestos
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            query = "SELECT idpuesto, puesto FROM puestos WHERE 1=1"
            params = []
            
            if busqueda:
                query += " AND puesto LIKE %s"
                params.append(f"%{busqueda}%")
            
            query += " ORDER BY puesto"
            
            cursor.execute(query, params)
            
            puestos = []
            for row in cursor.fetchall():
                puestos.append({
                    'id': row[0],
                    'nombre': row[1] or ''
                })
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Obtenidos {len(puestos)} puestos de empresa {base_empresa}")
            return puestos
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al listar puestos de empresa {base_empresa}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado al listar puestos: {e}", exc_info=True)
            return []
    
    def obtener_puesto(self, base_empresa: str, id_puesto: int) -> Optional[Dict]:
        """
        Obtiene un puesto específico
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_puesto: ID del puesto
            
        Returns:
            Diccionario con información del puesto o None si no existe
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            cursor.execute("SELECT idpuesto, puesto FROM puestos WHERE idpuesto = %s", [id_puesto])
            row = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'nombre': row[1] or ''
                }
            
            return None
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al obtener puesto {id_puesto} de empresa {base_empresa}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al obtener puesto: {e}", exc_info=True)
            return None
    
    def crear_puesto(self, base_empresa: str, nombre: str) -> Optional[int]:
        """
        Crea un nuevo puesto
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            nombre: Nombre del puesto
            
        Returns:
            ID del puesto creado o None si hubo error

        Raises:
            CreacionPuestoBloqueadaError: si ``settings.SYNAP_BLOQUEAR_CREAR_PUESTOS`` está activo.
        """
        if getattr(settings, "SYNAP_BLOQUEAR_CREAR_PUESTOS", True):
            logger.warning(
                "Creación de puesto bloqueada (SYNAP_BLOQUEAR_CREAR_PUESTOS). "
                "Los puestos se crean en AdministraNET; en Synap se gestionan roles/permisos. "
                "Intento en empresa %s con nombre '%s'.",
                base_empresa, nombre,
            )
            raise CreacionPuestoBloqueadaError(
                "La creación de puestos está deshabilitada en Synap. "
                "Cree el puesto en AdministraNET y luego asigne sus permisos en "
                "«Permisos por puesto»."
            )
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Verificar si ya existe un puesto con el mismo nombre
            cursor.execute("SELECT idpuesto FROM puestos WHERE puesto = %s", [nombre.strip()])
            if cursor.fetchone():
                cursor.close()
                conn.close()
                logger.warning(f"Ya existe un puesto con nombre '{nombre}'")
                return None
            
            # Obtener el siguiente ID
            cursor.execute("SELECT MAX(idpuesto) FROM puestos")
            max_id = cursor.fetchone()[0]
            nuevo_id = (max_id or 0) + 1
            
            cursor.execute("INSERT INTO puestos (idpuesto, puesto) VALUES (%s, %s)", [nuevo_id, nombre.strip()])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Puesto creado con ID {nuevo_id}")
            return nuevo_id
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al crear puesto en empresa {base_empresa}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al crear puesto: {e}", exc_info=True)
            return None
    
    def actualizar_puesto(self, base_empresa: str, id_puesto: int, nombre: str) -> bool:
        """
        Actualiza un puesto existente
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_puesto: ID del puesto a actualizar
            nombre: Nuevo nombre del puesto
            
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Verificar si existe
            cursor.execute("SELECT idpuesto FROM puestos WHERE idpuesto = %s", [id_puesto])
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                logger.warning(f"Puesto {id_puesto} no existe")
                return False
            
            # Verificar si otro puesto tiene el mismo nombre
            cursor.execute("SELECT idpuesto FROM puestos WHERE puesto = %s AND idpuesto != %s", 
                         [nombre.strip(), id_puesto])
            if cursor.fetchone():
                cursor.close()
                conn.close()
                logger.warning(f"Ya existe otro puesto con nombre '{nombre}'")
                return False
            
            cursor.execute("UPDATE puestos SET puesto = %s WHERE idpuesto = %s", [nombre.strip(), id_puesto])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Puesto {id_puesto} actualizado")
            return True
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al actualizar puesto {id_puesto} en empresa {base_empresa}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al actualizar puesto: {e}", exc_info=True)
            return False
    
    def eliminar_puesto(self, base_empresa: str, id_puesto: int) -> bool:
        """
        Elimina un puesto (solo si no tiene usuarios asociados)
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_puesto: ID del puesto a eliminar
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Verificar si tiene usuarios asociados
            cursor.execute("SELECT COUNT(*) FROM usuarios WHERE id_puesto = %s", [id_puesto])
            count_usuarios = cursor.fetchone()[0]
            
            if count_usuarios > 0:
                cursor.close()
                conn.close()
                logger.warning(f"No se puede eliminar puesto {id_puesto}: tiene {count_usuarios} usuarios asociados")
                return False
            
            # Eliminar primero los permisos del menú
            cursor.execute("DELETE FROM permisos WHERE IDpuesto = %s", [str(id_puesto)])
            
            # Eliminar el puesto
            cursor.execute("DELETE FROM puestos WHERE idpuesto = %s", [id_puesto])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Puesto {id_puesto} eliminado")
            return True
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al eliminar puesto {id_puesto} de empresa {base_empresa}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al eliminar puesto: {e}", exc_info=True)
            return False
    
    def tiene_usuarios_asociados(self, base_empresa: str, id_puesto: int) -> bool:
        """
        Verifica si un puesto tiene usuarios asociados
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_puesto: ID del puesto
            
        Returns:
            True si tiene usuarios asociados, False en caso contrario
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM usuarios WHERE id_puesto = %s", [id_puesto])
            count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return count > 0
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al verificar usuarios del puesto {id_puesto}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al verificar usuarios: {e}", exc_info=True)
            return False

