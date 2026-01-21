"""
Servicio para gestión de sucursales en administraNET Gestión
Gestiona la tabla sucursales directamente en MySQL de administraNET
Basado en ABMSucursal.frm y CargaSucursal.frm
"""
import logging
import MySQLdb
from django.conf import settings
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AdministraNETSucursalesService:
    """Servicio para gestión de sucursales en administraNET Gestión"""
    
    def __init__(self, server: str = None, port: str = None):
        """
        Inicializa el servicio de gestión de sucursales
        
        Args:
            server: Nombre del servidor MySQL (host/IP). Si no se proporciona, usa DB_HOST del .env
            port: Puerto MySQL. Si no se proporciona, usa DB_PORT del .env
        """
        mysql_config = settings.DATABASES['mysql']
        self.server = server or mysql_config['HOST']
        self.port = port or mysql_config['PORT']
        self.user = mysql_config['USER']
        self.password = mysql_config['PASSWORD']
    
    def _get_connection(self, base_empresa: str):
        """Obtiene conexión a la base de datos MySQL"""
        return MySQLdb.connect(
            host=self.server,
            port=int(self.port),
            user=self.user,
            passwd=self.password,
            db=base_empresa,
            charset='utf8mb4'
        )
    
    def listar_sucursales(self, base_empresa: str, busqueda: str = None) -> List[Dict]:
        """
        Lista todas las sucursales de la empresa, con búsqueda opcional
        Basado en ABMSucursal.frm - Consulta_Busqueda()
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Construir consulta base con JOINs para obtener nombre de empresa y provincia
            # Nota: id_pais puede no existir en todas las versiones de la tabla sucursales
            # Si no existe, se obtiene desde provincia o datosempresa
            query = """
                SELECT 
                    s.id_sucursal,
                    s.nombre_sucursal,
                    s.desc_sucursal,
                    s.id_provincia,
                    s.domicilio_sucursal,
                    s.telefono_sucursal,
                    s.email_sucursal,
                    s.nro_estab_sucursal,
                    s.id_empresa,
                    COALESCE(s.id_pais, p.id_pais, e.id_pais, 1) as id_pais,
                    s.cod_postal,
                    s.anulado,
                    p.provincia as nomb_provincia,
                    e.Nombre as nomb_empresa
                FROM sucursales s
                LEFT JOIN provincia p ON p.codprovincia = s.id_provincia
                LEFT JOIN datosempresa e ON e.id_empresa = s.id_empresa
                WHERE 1=1
            """
            params = []
            
            # Agregar filtro de búsqueda si existe
            if busqueda:
                query += """
                    AND (
                        s.nombre_sucursal LIKE %s OR
                        p.provincia LIKE %s OR
                        e.Nombre LIKE %s OR
                        s.desc_sucursal LIKE %s
                    )
                """
                busqueda_pattern = f"%{busqueda}%"
                params = [busqueda_pattern, busqueda_pattern, busqueda_pattern, busqueda_pattern]
            
            query += " ORDER BY s.nombre_sucursal"
            
            cursor.execute(query, params)
            column_names = [desc[0] for desc in cursor.description]
            
            sucursales = []
            for row in cursor.fetchall():
                sucursal_dict = dict(zip(column_names, row))
                
                # Asegurar que id_provincia e id_pais sean enteros o None
                if sucursal_dict.get('id_provincia') is not None:
                    try:
                        sucursal_dict['id_provincia'] = int(sucursal_dict['id_provincia'])
                    except (ValueError, TypeError):
                        sucursal_dict['id_provincia'] = None
                
                if sucursal_dict.get('id_pais') is not None:
                    try:
                        sucursal_dict['id_pais'] = int(sucursal_dict['id_pais'])
                    except (ValueError, TypeError):
                        sucursal_dict['id_pais'] = None
                
                # Convertir anulado a booleano
                sucursal_dict['activa'] = sucursal_dict.get('anulado', 'No').lower() != 'si'
                
                sucursales.append(sucursal_dict)
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ {len(sucursales)} sucursales encontradas en {base_empresa}")
            return sucursales
            
        except Exception as e:
            logger.error(f"Error al listar sucursales: {e}")
            return []
    
    def obtener_sucursal(self, base_empresa: str, id_sucursal: int) -> Optional[Dict]:
        """
        Obtiene una sucursal por su ID
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    s.*,
                    COALESCE(s.id_pais, p.id_pais, e.id_pais, 1) as id_pais,
                    p.provincia as nomb_provincia,
                    e.Nombre as nomb_empresa
                FROM sucursales s
                LEFT JOIN provincia p ON p.codprovincia = s.id_provincia
                LEFT JOIN datosempresa e ON e.id_empresa = s.id_empresa
                WHERE s.id_sucursal = %s
            """, [id_sucursal])
            
            column_names = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            
            if not row:
                cursor.close()
                conn.close()
                return None
            
            sucursal_dict = dict(zip(column_names, row))
            
            # Asegurar que id_provincia e id_pais sean enteros o None
            if sucursal_dict.get('id_provincia') is not None:
                try:
                    sucursal_dict['id_provincia'] = int(sucursal_dict['id_provincia'])
                except (ValueError, TypeError):
                    sucursal_dict['id_provincia'] = None
            
            if sucursal_dict.get('id_pais') is not None:
                try:
                    sucursal_dict['id_pais'] = int(sucursal_dict['id_pais'])
                except (ValueError, TypeError):
                    sucursal_dict['id_pais'] = None
            
            # Convertir anulado a booleano
            sucursal_dict['activa'] = sucursal_dict.get('anulado', 'No').lower() != 'si'
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Sucursal {id_sucursal} obtenida de {base_empresa}")
            return sucursal_dict
            
        except Exception as e:
            logger.error(f"Error al obtener sucursal {id_sucursal}: {e}")
            return None
    
    def crear_sucursal(self, base_empresa: str, datos_sucursal: Dict) -> bool:
        """
        Crea una nueva sucursal
        Basado en CargaSucursal.frm - Aceptar_Click() cuando modificacion = "No"
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Obtener id_empresa de la base de datos activa (solo hay una empresa por base)
            cursor.execute("SELECT id_empresa FROM datosempresa LIMIT 1")
            empresa_row = cursor.fetchone()
            if not empresa_row:
                logger.error(f"No se encontró empresa en {base_empresa}")
                cursor.close()
                conn.close()
                return False
            
            id_empresa = empresa_row[0]
            
            # Insertar nueva sucursal
            cursor.execute("""
                INSERT INTO sucursales (
                    nombre_sucursal, desc_sucursal, id_provincia, id_pais,
                    domicilio_sucursal, telefono_sucursal, email_sucursal,
                    nro_estab_sucursal, id_empresa, anulado, cod_postal,
                    limite_consulta, ruta_reporte_servidor, ruta_reporte_comprobante,
                    cant_renglon_venta
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, [
                datos_sucursal.get('nombre_sucursal', ''),
                datos_sucursal.get('desc_sucursal', ''),
                datos_sucursal.get('id_provincia'),
                datos_sucursal.get('id_pais'),
                datos_sucursal.get('domicilio_sucursal', ''),
                datos_sucursal.get('telefono_sucursal', ''),
                datos_sucursal.get('email_sucursal', ''),
                datos_sucursal.get('nro_estab_sucursal', ''),
                id_empresa,
                'Si' if not datos_sucursal.get('activa', True) else 'No',
                datos_sucursal.get('cod_postal', ''),
                500,  # limite_consulta por defecto
                'C:\\administraNET\\Informes',  # ruta_reporte_servidor por defecto
                'C:\\administraNET\\Informes',  # ruta_reporte_comprobante por defecto
                20,  # cant_renglon_venta por defecto
            ])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Sucursal creada exitosamente en {base_empresa}")
            return True
            
        except Exception as e:
            logger.error(f"Error al crear sucursal: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return False
    
    def actualizar_sucursal(self, base_empresa: str, id_sucursal: int, datos_sucursal: Dict) -> bool:
        """
        Actualiza una sucursal existente
        Basado en CargaSucursal.frm - Aceptar_Click() cuando modificacion = "Si"
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Verificar si existe la columna id_pais en la tabla sucursales
            cursor.execute("SHOW COLUMNS FROM sucursales LIKE 'id_pais'")
            tiene_id_pais = cursor.fetchone() is not None
            
            # Obtener id_pais desde datosempresa si no se proporciona
            id_pais = datos_sucursal.get('id_pais')
            if not id_pais:
                cursor.execute("SELECT id_pais FROM datosempresa LIMIT 1")
                empresa_pais = cursor.fetchone()
                id_pais = empresa_pais[0] if empresa_pais else 1
            
            # Construir query según si existe id_pais o no
            if tiene_id_pais:
                cursor.execute("""
                    UPDATE sucursales SET
                        nombre_sucursal = %s,
                        desc_sucursal = %s,
                        id_provincia = %s,
                        id_pais = %s,
                        domicilio_sucursal = %s,
                        telefono_sucursal = %s,
                        email_sucursal = %s,
                        nro_estab_sucursal = %s,
                        anulado = %s,
                        cod_postal = %s
                    WHERE id_sucursal = %s
                """, [
                    datos_sucursal.get('nombre_sucursal', ''),
                    datos_sucursal.get('desc_sucursal', ''),
                    datos_sucursal.get('id_provincia'),
                    id_pais,
                    datos_sucursal.get('domicilio_sucursal', ''),
                    datos_sucursal.get('telefono_sucursal', ''),
                    datos_sucursal.get('email_sucursal', ''),
                    datos_sucursal.get('nro_estab_sucursal', ''),
                    'Si' if not datos_sucursal.get('activa', True) else 'No',
                    datos_sucursal.get('cod_postal', ''),
                    id_sucursal,
                ])
            else:
                # Si no existe id_pais, no lo incluimos en el UPDATE
                cursor.execute("""
                    UPDATE sucursales SET
                        nombre_sucursal = %s,
                        desc_sucursal = %s,
                        id_provincia = %s,
                        domicilio_sucursal = %s,
                        telefono_sucursal = %s,
                        email_sucursal = %s,
                        nro_estab_sucursal = %s,
                        anulado = %s,
                        cod_postal = %s
                    WHERE id_sucursal = %s
                """, [
                    datos_sucursal.get('nombre_sucursal', ''),
                    datos_sucursal.get('desc_sucursal', ''),
                    datos_sucursal.get('id_provincia'),
                    datos_sucursal.get('domicilio_sucursal', ''),
                    datos_sucursal.get('telefono_sucursal', ''),
                    datos_sucursal.get('email_sucursal', ''),
                    datos_sucursal.get('nro_estab_sucursal', ''),
                    'Si' if not datos_sucursal.get('activa', True) else 'No',
                    datos_sucursal.get('cod_postal', ''),
                    id_sucursal,
                ])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Sucursal {id_sucursal} actualizada exitosamente en {base_empresa}")
            return True
            
        except Exception as e:
            logger.error(f"Error al actualizar sucursal {id_sucursal}: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return False
    
    def eliminar_sucursal(self, base_empresa: str, id_sucursal: int) -> bool:
        """
        Elimina una sucursal (marca como anulada o elimina físicamente)
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Primero verificar si tiene usuarios asociados o movimientos
            # Por ahora, solo marcamos como anulado
            cursor.execute("""
                UPDATE sucursales SET anulado = 'Si'
                WHERE id_sucursal = %s
            """, [id_sucursal])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Sucursal {id_sucursal} marcada como anulada en {base_empresa}")
            return True
            
        except Exception as e:
            logger.error(f"Error al eliminar sucursal {id_sucursal}: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return False

