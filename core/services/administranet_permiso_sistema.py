"""
Servicio para gestión de permisos del sistema en administraNET Gestión
Gestiona la tabla permiso_sistema que define los permisos disponibles
"""
import logging
import MySQLdb
from django.conf import settings
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class AdministraNETPermisoSistemaService:
    """Servicio para gestión de permisos del sistema en administraNET Gestión"""
    
    def __init__(self, server: str = None, port: str = None):
        """
        Inicializa el servicio de gestión de permisos del sistema
        
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
    
    def listar_permisos(self, base_empresa: str, busqueda: str = None, grupo: str = None, id_puesto: int = None) -> List[Dict]:
        """
        Lista permisos del sistema de una empresa con valores guardados
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            busqueda: Texto de búsqueda (nombre o key del permiso)
            grupo: Filtrar por grupo_permiso
            id_puesto: ID del puesto para filtrar valores específicos (opcional)
            
        Returns:
            Lista de diccionarios con información de permisos, incluyendo valor guardado
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Consulta con LEFT JOIN para obtener el valor guardado del puesto específico o el más reciente
            if id_puesto:
                # Filtrar por puesto específico
                query = """
                    SELECT 
                        ps.id_permiso_sistema,
                        ps.key_permiso,
                        ps.nombre_permiso,
                        ps.detalle_permiso,
                        ps.grupo_permiso,
                        ps.tipo_permiso,
                        ps.default_permiso,
                        ps.detalle_valor_permiso,
                        COALESCE(psp.valor_permiso, ps.default_permiso) as valor_guardado
                    FROM permiso_sistema ps
                    LEFT JOIN permiso_sistema_puesto psp 
                        ON ps.id_permiso_sistema = psp.id_permiso_sistema 
                        AND psp.id_puesto = %s
                    WHERE 1=1
                """
                params = [id_puesto]
            else:
                # Obtener el valor más reciente de cualquier puesto
                query = """
                    SELECT 
                        ps.id_permiso_sistema,
                        ps.key_permiso,
                        ps.nombre_permiso,
                        ps.detalle_permiso,
                        ps.grupo_permiso,
                        ps.tipo_permiso,
                        ps.default_permiso,
                        ps.detalle_valor_permiso,
                        COALESCE(psp.valor_permiso, ps.default_permiso) as valor_guardado
                    FROM permiso_sistema ps
                    LEFT JOIN (
                        SELECT psp1.id_permiso_sistema, psp1.valor_permiso
                        FROM permiso_sistema_puesto psp1
                        INNER JOIN (
                            SELECT id_permiso_sistema, MAX(id_permiso_sistema_puesto) as max_id
                            FROM permiso_sistema_puesto
                            GROUP BY id_permiso_sistema
                        ) psp2 ON psp1.id_permiso_sistema = psp2.id_permiso_sistema 
                               AND psp1.id_permiso_sistema_puesto = psp2.max_id
                    ) psp ON ps.id_permiso_sistema = psp.id_permiso_sistema
                    WHERE 1=1
                """
                params = []
            
            if busqueda:
                query += " AND (ps.nombre_permiso LIKE %s OR ps.key_permiso LIKE %s OR ps.detalle_permiso LIKE %s)"
                busqueda_param = f"%{busqueda}%"
                params.extend([busqueda_param, busqueda_param, busqueda_param])
            
            if grupo:
                query += " AND ps.grupo_permiso = %s"
                params.append(grupo)
            
            query += " ORDER BY ps.grupo_permiso, ps.nombre_permiso"
            
            cursor.execute(query, params)
            
            # Obtener nombres de columnas
            column_names = [desc[0] for desc in cursor.description]
            
            permisos = []
            for row in cursor.fetchall():
                permiso_dict = dict(zip(column_names, row))
                permisos.append(permiso_dict)
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Obtenidos {len(permisos)} permisos del sistema de empresa {base_empresa}")
            return permisos
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al listar permisos del sistema de empresa {base_empresa}: {e}")
            # Si falla el JOIN (por ejemplo, si ROW_NUMBER no está disponible), usar consulta simple
            try:
                conn = self._get_connection(base_empresa)
                cursor = conn.cursor()
                
                query = "SELECT * FROM permiso_sistema WHERE 1=1"
                params = []
                
                if busqueda:
                    query += " AND (nombre_permiso LIKE %s OR key_permiso LIKE %s OR detalle_permiso LIKE %s)"
                    busqueda_param = f"%{busqueda}%"
                    params.extend([busqueda_param, busqueda_param, busqueda_param])
                
                if grupo:
                    query += " AND grupo_permiso = %s"
                    params.append(grupo)
                
                query += " ORDER BY grupo_permiso, nombre_permiso"
                
                cursor.execute(query, params)
                column_names = [desc[0] for desc in cursor.description]
                
                permisos = []
                for row in cursor.fetchall():
                    permiso_dict = dict(zip(column_names, row))
                    # Agregar valor_guardado como default_permiso si no se pudo obtener
                    permiso_dict['valor_guardado'] = permiso_dict.get('default_permiso', '')
                    permisos.append(permiso_dict)
                
                cursor.close()
                conn.close()
                
                logger.info(f"✅ Obtenidos {len(permisos)} permisos del sistema de empresa {base_empresa} (sin JOIN)")
                return permisos
            except Exception as e2:
                logger.error(f"Error inesperado al listar permisos del sistema: {e2}", exc_info=True)
                return []
        except Exception as e:
            logger.error(f"Error inesperado al listar permisos del sistema: {e}", exc_info=True)
            return []
    
    def obtener_permiso(self, base_empresa: str, id_permiso_sistema: int) -> Optional[Dict]:
        """
        Obtiene un permiso del sistema específico
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_permiso_sistema: ID del permiso
            
        Returns:
            Diccionario con información del permiso o None si no existe
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM permiso_sistema WHERE id_permiso_sistema = %s", [id_permiso_sistema])
            row = cursor.fetchone()
            
            if row:
                column_names = [desc[0] for desc in cursor.description]
                permiso_dict = dict(zip(column_names, row))
                
                cursor.close()
                conn.close()
                
                return permiso_dict
            
            cursor.close()
            conn.close()
            
            return None
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al obtener permiso {id_permiso_sistema} de empresa {base_empresa}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al obtener permiso: {e}", exc_info=True)
            return None
    
    def crear_permiso(self, base_empresa: str, datos_permiso: Dict) -> Optional[int]:
        """
        Crea un nuevo permiso del sistema
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            datos_permiso: Diccionario con los datos del permiso
            
        Returns:
            ID del permiso creado o None si hubo error
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Verificar si ya existe un permiso con el mismo key_permiso
            cursor.execute("SELECT id_permiso_sistema FROM permiso_sistema WHERE key_permiso = %s", 
                         [datos_permiso.get('key_permiso', '').strip()])
            if cursor.fetchone():
                cursor.close()
                conn.close()
                logger.warning(f"Ya existe un permiso con key_permiso '{datos_permiso.get('key_permiso')}'")
                return None
            
            cursor.execute("""
                INSERT INTO permiso_sistema (
                    key_permiso,
                    nombre_permiso,
                    detalle_permiso,
                    grupo_permiso,
                    tipo_permiso,
                    default_permiso,
                    detalle_valor_permiso
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [
                datos_permiso.get('key_permiso', '').strip(),
                datos_permiso.get('nombre_permiso', '').strip(),
                datos_permiso.get('detalle_permiso', '').strip(),
                datos_permiso.get('grupo_permiso', 'Generales').strip(),
                datos_permiso.get('tipo_permiso', 'Si-No').strip(),
                datos_permiso.get('default_permiso', 'No').strip(),
                datos_permiso.get('detalle_valor_permiso', 'Si-No').strip(),
            ])
            
            nuevo_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Permiso del sistema creado con ID {nuevo_id}")
            return nuevo_id
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al crear permiso del sistema en empresa {base_empresa}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al crear permiso del sistema: {e}", exc_info=True)
            return None
    
    def actualizar_permiso(self, base_empresa: str, id_permiso_sistema: int, datos_permiso: Dict) -> bool:
        """
        Actualiza un permiso del sistema existente
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_permiso_sistema: ID del permiso a actualizar
            datos_permiso: Diccionario con los datos a actualizar
            
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Verificar si existe
            cursor.execute("SELECT id_permiso_sistema FROM permiso_sistema WHERE id_permiso_sistema = %s", 
                         [id_permiso_sistema])
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                logger.warning(f"Permiso {id_permiso_sistema} no existe")
                return False
            
            # Verificar si otro permiso tiene el mismo key_permiso (si se está cambiando)
            if 'key_permiso' in datos_permiso:
                cursor.execute("SELECT id_permiso_sistema FROM permiso_sistema WHERE key_permiso = %s AND id_permiso_sistema != %s", 
                             [datos_permiso['key_permiso'].strip(), id_permiso_sistema])
                if cursor.fetchone():
                    cursor.close()
                    conn.close()
                    logger.warning(f"Ya existe otro permiso con key_permiso '{datos_permiso['key_permiso']}'")
                    return False
            
            # Construir UPDATE dinámicamente
            campos_update = []
            valores_update = []
            
            campos_permitidos = ['nombre_permiso', 'detalle_permiso', 'grupo_permiso', 
                               'tipo_permiso', 'default_permiso', 'detalle_valor_permiso', 'key_permiso']
            
            for campo in campos_permitidos:
                if campo in datos_permiso:
                    campos_update.append(f"{campo} = %s")
                    valores_update.append(datos_permiso[campo].strip() if isinstance(datos_permiso[campo], str) else datos_permiso[campo])
            
            if not campos_update:
                cursor.close()
                conn.close()
                return False
            
            valores_update.append(id_permiso_sistema)
            
            query = f"UPDATE permiso_sistema SET {', '.join(campos_update)} WHERE id_permiso_sistema = %s"
            cursor.execute(query, valores_update)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Permiso del sistema {id_permiso_sistema} actualizado")
            return True
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al actualizar permiso {id_permiso_sistema} en empresa {base_empresa}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al actualizar permiso del sistema: {e}", exc_info=True)
            return False
    
    def eliminar_permiso(self, base_empresa: str, id_permiso_sistema: int) -> bool:
        """
        Elimina un permiso del sistema
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_permiso_sistema: ID del permiso a eliminar
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Verificar si existe
            cursor.execute("SELECT id_permiso_sistema FROM permiso_sistema WHERE id_permiso_sistema = %s", 
                         [id_permiso_sistema])
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                logger.warning(f"Permiso {id_permiso_sistema} no existe")
                return False
            
            # Verificar si hay asignaciones en permiso_sistema_puesto
            cursor.execute("SELECT COUNT(*) FROM permiso_sistema_puesto WHERE id_permiso_sistema = %s", 
                         [id_permiso_sistema])
            count = cursor.fetchone()[0]
            
            if count > 0:
                # Eliminar primero las asignaciones
                cursor.execute("DELETE FROM permiso_sistema_puesto WHERE id_permiso_sistema = %s", 
                             [id_permiso_sistema])
            
            # Eliminar el permiso
            cursor.execute("DELETE FROM permiso_sistema WHERE id_permiso_sistema = %s", 
                         [id_permiso_sistema])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Permiso del sistema {id_permiso_sistema} eliminado")
            return True
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al eliminar permiso {id_permiso_sistema} de empresa {base_empresa}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al eliminar permiso del sistema: {e}", exc_info=True)
            return False
    
    def obtener_grupos(self, base_empresa: str) -> List[str]:
        """
        Obtiene la lista de grupos de permisos únicos
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            
        Returns:
            Lista de nombres de grupos únicos
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT grupo_permiso FROM permiso_sistema WHERE grupo_permiso IS NOT NULL ORDER BY grupo_permiso")
            grupos = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return grupos
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al obtener grupos de permisos de empresa {base_empresa}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado al obtener grupos: {e}", exc_info=True)
            return []
    
    def actualizar_valor_permiso(self, base_empresa: str, id_permiso_sistema: int, nuevo_valor: str, id_puesto: int = None) -> bool:
        """
        Actualiza el valor de un permiso en permiso_sistema_puesto.
        Si no existe un registro, lo crea. Si id_puesto es None, actualiza todos los registros del permiso.
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_permiso_sistema: ID del permiso a actualizar
            nuevo_valor: Nuevo valor a asignar ('Si' o 'No')
            id_puesto: ID del puesto (opcional, si es None actualiza todos)
            
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Obtener key_permiso del permiso
            cursor.execute("SELECT key_permiso FROM permiso_sistema WHERE id_permiso_sistema = %s", [id_permiso_sistema])
            row = cursor.fetchone()
            if not row:
                cursor.close()
                conn.close()
                logger.warning(f"Permiso {id_permiso_sistema} no existe")
                return False
            
            key_permiso = row[0]
            
            if id_puesto:
                # Actualizar o crear registro específico para un puesto
                cursor.execute("""
                    SELECT id_permiso_sistema_puesto FROM permiso_sistema_puesto 
                    WHERE id_permiso_sistema = %s AND id_puesto = %s
                """, [id_permiso_sistema, id_puesto])
                
                existe = cursor.fetchone()
                
                if existe:
                    # Actualizar existente
                    cursor.execute("""
                        UPDATE permiso_sistema_puesto 
                        SET valor_permiso = %s 
                        WHERE id_permiso_sistema = %s AND id_puesto = %s
                    """, [nuevo_valor, id_permiso_sistema, id_puesto])
                else:
                    # Crear nuevo
                    cursor.execute("""
                        INSERT INTO permiso_sistema_puesto 
                        (id_permiso_sistema, key_permiso, valor_permiso, id_puesto) 
                        VALUES (%s, %s, %s, %s)
                    """, [id_permiso_sistema, key_permiso, nuevo_valor, id_puesto])
            else:
                # Actualizar todos los registros del permiso
                cursor.execute("""
                    UPDATE permiso_sistema_puesto 
                    SET valor_permiso = %s 
                    WHERE id_permiso_sistema = %s
                """, [nuevo_valor, id_permiso_sistema])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Valor del permiso {id_permiso_sistema} actualizado a '{nuevo_valor}'")
            return True
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al actualizar valor del permiso {id_permiso_sistema} en empresa {base_empresa}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al actualizar valor del permiso: {e}", exc_info=True)
            return False

