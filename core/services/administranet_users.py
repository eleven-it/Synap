"""
Servicio para gestión de usuarios en administraNET Gestión
Permite CRUD completo de usuarios directamente en MySQL de administraNET
"""
import logging
import MySQLdb
from django.conf import settings
from typing import Optional, Dict, List
from django.db import connections

logger = logging.getLogger(__name__)

# Clave de encriptación AES (debe coincidir con administraNET Gestión)
AES_KEY = 'a7v8xx2'


class AdministraNETUserService:
    """Servicio para gestión de usuarios en administraNET Gestión"""
    
    def __init__(self, server: str = None, port: str = None):
        """
        Inicializa el servicio de gestión de usuarios
        
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
    
    def listar_usuarios(self, base_empresa: str, id_empresa: int = None, busqueda: str = None, solo_activos: bool = True) -> List[Dict]:
        """
        Lista usuarios de una empresa
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_empresa: ID de la empresa (si no se proporciona, se obtiene desde base_empresa)
            busqueda: Texto de búsqueda (nombre, apellido o cod_usuario)
            solo_activos: Si True, solo muestra usuarios no dados de baja
            
        Returns:
            Lista de diccionarios con información de usuarios
        """
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
                else:
                    logger.error(f"No se encontró empresa con base_empresa: {base_empresa}")
                    cursor.close()
                    conn.close()
                    return []
            
            # Query similar a ABMUsuarios.frm
            query = """
                SELECT 
                    usuarios.id_usuario,
                    usuarios.cod_usuario,
                    usuarios.nombre_usuario,
                    usuarios.apellido_usuario,
                    usuarios.id_puesto,
                    usuarios.id_sucursal,
                    usuarios.id_empresa,
                    usuarios.id_punto_venta,
                    usuarios.id_deposito,
                    usuarios.id_caja,
                    usuarios.baja_usuario,
                    usuarios.tipo_busqueda_defecto,
                    usuarios.permiso_supervisor_venta,
                    usuarios.vendedor_web,
                    usuarios.zoom_reportes,
                    usuarios.color_formulario,
                    usuarios.tipo_boton,
                    usuarios.CodViajante,
                    usuarios.resol_principal,
                    usuarios.entrega_defecto,
                    usuarios.utiliza_reporte_local,
                    usuarios.utiliza_certificado_local,
                    usuarios.ruta_reporte_local,
                    usuarios.ruta_certificado_local,
                    usuarios.carpeta_documentos,
                    usuarios.fuente_nombre,
                    usuarios.fuente_tamano,
                    puestos.puesto AS nombre_puesto,
                    sucursales.nombre_sucursal,
                    viajantes.Nombre AS nombre_viajante,
                    datosempresa.Nombre AS nombre_empresa
                FROM usuarios
                LEFT JOIN puestos ON puestos.idpuesto = usuarios.id_puesto
                LEFT JOIN sucursales ON sucursales.id_sucursal = usuarios.id_sucursal
                LEFT JOIN viajantes ON viajantes.CodViajante = usuarios.CodViajante
                LEFT JOIN datosempresa ON datosempresa.id_empresa = usuarios.id_empresa
                WHERE usuarios.id_empresa = %s
            """
            
            params = [id_empresa]
            
            if solo_activos:
                query += " AND usuarios.baja_usuario <> 'Si'"
            
            if busqueda:
                query += " AND (usuarios.nombre_usuario LIKE %s OR usuarios.apellido_usuario LIKE %s OR usuarios.cod_usuario LIKE %s)"
                busqueda_pattern = f"%{busqueda}%"
                params.extend([busqueda_pattern, busqueda_pattern, busqueda_pattern])
            
            query += " ORDER BY usuarios.nombre_usuario"
            
            cursor.execute(query, params)
            
            usuarios = []
            for row in cursor.fetchall():
                usuarios.append({
                    'id_usuario': row[0],
                    'cod_usuario': row[1] or '',
                    'nombre_usuario': row[2] or '',
                    'apellido_usuario': row[3] or '',
                    'id_puesto': row[4],
                    'id_sucursal': row[5],
                    'id_empresa': row[6],
                    'id_punto_venta': row[7],
                    'id_deposito': row[8],
                    'id_caja': row[9],
                    'baja_usuario': row[10] or 'No',
                    'tipo_busqueda_defecto': row[11],
                    'permiso_supervisor_venta': row[12] or 'No',
                    'vendedor_web': row[13] or 'No',
                    'zoom_reportes': row[14],
                    'color_formulario': row[15] or '',
                    'tipo_boton': row[16] or '',
                    'CodViajante': row[17],
                    'resol_principal': row[18] or '',
                    'entrega_defecto': row[19] or '',
                    'utiliza_reporte_local': row[20] or 'No',
                    'utiliza_certificado_local': row[21] or 'No',
                    'ruta_reporte_local': row[22] or '',
                    'ruta_certificado_local': row[23] or '',
                    'carpeta_documentos': row[24] or '',
                    'fuente_nombre': row[25] or '',
                    'fuente_tamano': row[26],
                    'nombre_puesto': row[27] or '',
                    'nombre_sucursal': row[28] or '',
                    'nombre_viajante': row[29] or '' if len(row) > 29 else '',
                    'nombre_empresa': row[30] or '' if len(row) > 30 else '',
                })
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Obtenidos {len(usuarios)} usuarios de empresa {base_empresa}")
            return usuarios
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al listar usuarios de empresa {base_empresa}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado al listar usuarios: {e}", exc_info=True)
            return []
    
    def obtener_usuario(self, base_empresa: str, id_usuario: int) -> Optional[Dict]:
        """
        Obtiene un usuario por ID
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_usuario: ID del usuario
            
        Returns:
            Diccionario con información del usuario o None si no existe
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Query mejorado con manejo de NULLs y verificación de anulado
            cursor.execute("""
                SELECT 
                    usuarios.id_usuario,
                    usuarios.cod_usuario,
                    usuarios.nombre_usuario,
                    usuarios.apellido_usuario,
                    usuarios.id_puesto,
                    usuarios.id_sucursal,
                    usuarios.id_empresa,
                    usuarios.id_punto_venta,
                    usuarios.id_deposito,
                    usuarios.id_caja,
                    usuarios.baja_usuario,
                    usuarios.tipo_busqueda_defecto,
                    usuarios.permiso_supervisor_venta,
                    usuarios.vendedor_web,
                    usuarios.zoom_reportes,
                    usuarios.color_formulario,
                    usuarios.tipo_boton,
                    usuarios.CodViajante,
                    usuarios.resol_principal,
                    usuarios.entrega_defecto,
                    usuarios.utiliza_reporte_local,
                    usuarios.utiliza_certificado_local,
                    usuarios.ruta_reporte_local,
                    usuarios.ruta_certificado_local,
                    usuarios.carpeta_documentos,
                    usuarios.fuente_nombre,
                    usuarios.fuente_tamano,
                    COALESCE(NULLIF(puestos.puesto, ''), '') AS nombre_puesto,
                    COALESCE(NULLIF(sucursales.nombre_sucursal, ''), '') AS nombre_sucursal,
                    COALESCE(NULLIF(datosempresa.Nombre, ''), '') AS nombre_empresa
                FROM usuarios
                LEFT JOIN puestos ON puestos.idpuesto = usuarios.id_puesto 
                    AND (puestos.anulado IS NULL OR puestos.anulado <> 'Si')
                LEFT JOIN sucursales ON sucursales.id_sucursal = usuarios.id_sucursal 
                    AND (sucursales.anulado IS NULL OR sucursales.anulado <> 'Si')
                LEFT JOIN datosempresa ON datosempresa.id_empresa = usuarios.id_empresa
                WHERE usuarios.id_usuario = %s
            """, [id_usuario])
            
            row = cursor.fetchone()
            
            if row:
                # Log detallado para debug
                logger.info(f"=== DEBUG obtener_usuario ===")
                logger.info(f"Total columnas: {len(row)}")
                logger.info(f"Row completo: {row}")
                logger.info(f"nombre_empresa (índice 29): {row[29] if len(row) > 29 else 'N/A'}")
                logger.info(f"nombre_sucursal (índice 28): {row[28] if len(row) > 28 else 'N/A'}")
                logger.info(f"nombre_puesto (índice 27): {row[27] if len(row) > 27 else 'N/A'}")
                logger.info(f"baja_usuario (índice 10): {row[10] if len(row) > 10 else 'N/A'}")
                logger.info(f"id_empresa (índice 6): {row[6] if len(row) > 6 else 'N/A'}")
                logger.info(f"id_sucursal (índice 5): {row[5] if len(row) > 5 else 'N/A'}")
                logger.info(f"id_puesto (índice 4): {row[4] if len(row) > 4 else 'N/A'}")
                
                usuario_dict = {
                    'id_usuario': row[0],
                    'cod_usuario': row[1] or '',
                    'nombre_usuario': row[2] or '',
                    'apellido_usuario': row[3] or '',
                    'id_puesto': row[4],
                    'id_sucursal': row[5],
                    'id_empresa': row[6],
                    'id_punto_venta': row[7],
                    'id_deposito': row[8],
                    'id_caja': row[9],
                    'baja_usuario': row[10] if row[10] else 'No',
                    'tipo_busqueda_defecto': row[11],
                    'permiso_supervisor_venta': row[12] or 'No',
                    'vendedor_web': row[13] or 'No',
                    'zoom_reportes': row[14],
                    'color_formulario': row[15] or '',
                    'tipo_boton': row[16] or '',
                    'CodViajante': row[17],
                    'resol_principal': row[18] or '',
                    'entrega_defecto': row[19] or '',
                    'utiliza_reporte_local': row[20] or 'No',
                    'utiliza_certificado_local': row[21] or 'No',
                    'ruta_reporte_local': row[22] or '',
                    'ruta_certificado_local': row[23] or '',
                    'carpeta_documentos': row[24] or '',
                    'fuente_nombre': row[25] or '',
                    'fuente_tamano': row[26],
                    'nombre_puesto': (row[27] or '').strip() if row[27] else '',
                    'nombre_sucursal': (row[28] or '').strip() if row[28] else '',
                    'nombre_empresa': (row[29] or '').strip() if row[29] else '',
                }
                
                logger.info(f"Usuario dict creado: nombre_empresa='{usuario_dict['nombre_empresa']}', nombre_sucursal='{usuario_dict['nombre_sucursal']}', nombre_puesto='{usuario_dict['nombre_puesto']}'")
                
                cursor.close()
                conn.close()
                return usuario_dict
            
            cursor.close()
            conn.close()
            return None
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al obtener usuario {id_usuario} de empresa {base_empresa}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al obtener usuario: {e}", exc_info=True)
            return None
    
    def crear_usuario(self, base_empresa: str, id_empresa: int, datos_usuario: Dict) -> Optional[int]:
        """
        Crea un nuevo usuario en administraNET
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_empresa: ID de la empresa
            datos_usuario: Diccionario con los datos del usuario
            
        Returns:
            ID del usuario creado o None si falla
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Obtener el siguiente ID de usuario
            cursor.execute("SELECT MAX(id_usuario) FROM usuarios")
            max_id = cursor.fetchone()[0]
            nuevo_id = (max_id or 0) + 1
            
            # Asegurar que id_empresa esté en los datos
            datos_usuario['id_empresa'] = id_empresa
            
            # Encriptar contraseña con AES_ENCRYPT (igual que administraNET Gestión)
            password = datos_usuario.get('password', '')
            
            # Insertar usuario
            cursor.execute("""
                INSERT INTO usuarios (
                    id_usuario,
                    cod_usuario,
                    password_usuario,
                    nombre_usuario,
                    apellido_usuario,
                    id_puesto,
                    id_sucursal,
                    id_empresa,
                    id_punto_venta,
                    id_deposito,
                    id_caja,
                    baja_usuario,
                    tipo_busqueda_defecto,
                    permiso_supervisor_venta,
                    vendedor_web,
                    zoom_reportes,
                    color_formulario,
                    tipo_boton,
                    CodViajante,
                    resol_principal,
                    entrega_defecto,
                    utiliza_reporte_local,
                    utiliza_certificado_local,
                    ruta_reporte_local,
                    ruta_certificado_local,
                    carpeta_documentos,
                    fuente_nombre,
                    fuente_tamano
                ) VALUES (
                    %s, %s, AES_ENCRYPT(%s, %s), %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, [
                nuevo_id,
                datos_usuario.get('cod_usuario', '').lower().strip(),
                password,
                AES_KEY,
                datos_usuario.get('nombre_usuario', '').strip(),
                datos_usuario.get('apellido_usuario', '').strip(),
                datos_usuario.get('id_puesto'),
                datos_usuario.get('id_sucursal'),
                id_empresa,
                datos_usuario.get('id_punto_venta'),
                datos_usuario.get('id_deposito'),
                datos_usuario.get('id_caja'),
                datos_usuario.get('baja_usuario', 'No'),
                datos_usuario.get('tipo_busqueda_defecto', 0),
                datos_usuario.get('permiso_supervisor_venta', 'No'),
                datos_usuario.get('vendedor_web', 'No'),
                datos_usuario.get('zoom_reportes', 100),
                datos_usuario.get('color_formulario', ''),
                datos_usuario.get('tipo_boton', ''),
                datos_usuario.get('CodViajante'),
                datos_usuario.get('resol_principal', ''),
                datos_usuario.get('entrega_defecto', ''),
                datos_usuario.get('utiliza_reporte_local', 'No'),
                datos_usuario.get('utiliza_certificado_local', 'No'),
                datos_usuario.get('ruta_reporte_local', ''),
                datos_usuario.get('ruta_certificado_local', ''),
                datos_usuario.get('carpeta_documentos', ''),
                datos_usuario.get('fuente_nombre', ''),
                datos_usuario.get('fuente_tamano', 8.25),
            ])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Usuario creado: {datos_usuario.get('cod_usuario')} (ID: {nuevo_id})")
            return nuevo_id
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al crear usuario en empresa {base_empresa}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al crear usuario: {e}", exc_info=True)
            return None
    
    def actualizar_usuario(self, base_empresa: str, id_usuario: int, datos_usuario: Dict) -> bool:
        """
        Actualiza un usuario existente
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_usuario: ID del usuario a actualizar
            datos_usuario: Diccionario con los datos a actualizar
            
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Construir query de actualización dinámicamente
            campos = []
            valores = []
            
            # Campos que siempre se pueden actualizar
            campos_actualizables = [
                'cod_usuario', 'nombre_usuario', 'apellido_usuario',
                'id_puesto', 'id_sucursal', 'id_punto_venta', 'id_deposito',
                'id_caja', 'baja_usuario', 'tipo_busqueda_defecto',
                'permiso_supervisor_venta', 'vendedor_web', 'zoom_reportes',
                'color_formulario', 'tipo_boton', 'CodViajante',
                'resol_principal', 'entrega_defecto', 'utiliza_reporte_local',
                'utiliza_certificado_local', 'ruta_reporte_local',
                'ruta_certificado_local', 'carpeta_documentos',
                'fuente_nombre', 'fuente_tamano'
            ]
            
            for campo in campos_actualizables:
                if campo in datos_usuario:
                    if campo == 'cod_usuario':
                        campos.append(f"{campo} = %s")
                        valores.append(datos_usuario[campo].lower().strip())
                    else:
                        campos.append(f"{campo} = %s")
                        valores.append(datos_usuario[campo])
            
            # Manejar contraseña por separado (si se proporciona)
            if 'password' in datos_usuario and datos_usuario['password']:
                campos.append("password_usuario = AES_ENCRYPT(%s, %s)")
                valores.append(datos_usuario['password'])
                valores.append(AES_KEY)
            
            if not campos:
                cursor.close()
                conn.close()
                return False
            
            valores.append(id_usuario)
            
            query = f"UPDATE usuarios SET {', '.join(campos)} WHERE id_usuario = %s"
            
            cursor.execute(query, valores)
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Usuario actualizado: ID {id_usuario}")
            return True
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al actualizar usuario {id_usuario} en empresa {base_empresa}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al actualizar usuario: {e}", exc_info=True)
            return False
    
    def eliminar_usuario(self, base_empresa: str, id_usuario: int) -> bool:
        """
        Elimina (da de baja) un usuario
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_usuario: ID del usuario a eliminar
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            # No eliminar el usuario supervisor (id_usuario = 1)
            if id_usuario == 1:
                logger.warning("⚠️ No se puede eliminar el usuario Supervisor (ID: 1)")
                return False
            
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Marcar como dado de baja en lugar de eliminar físicamente
            cursor.execute("""
                UPDATE usuarios 
                SET baja_usuario = 'Si' 
                WHERE id_usuario = %s
            """, [id_usuario])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Usuario dado de baja: ID {id_usuario}")
            return True
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al eliminar usuario {id_usuario} de empresa {base_empresa}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al eliminar usuario: {e}", exc_info=True)
            return False
    
    def obtener_puestos(self, base_empresa: str) -> List[Dict]:
        """Obtiene lista de puestos disponibles"""
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            cursor.execute("SELECT idpuesto, puesto FROM puestos ORDER BY puesto")
            
            puestos = []
            for row in cursor.fetchall():
                puestos.append({
                    'id': row[0],
                    'nombre': row[1] or ''
                })
            
            cursor.close()
            conn.close()
            return puestos
            
        except Exception as e:
            logger.error(f"Error al obtener puestos: {e}")
            return []
    
    def obtener_sucursales(self, base_empresa: str) -> List[Dict]:
        """Obtiene lista de sucursales disponibles"""
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id_sucursal, nombre_sucursal FROM sucursales ORDER BY nombre_sucursal")
            
            sucursales = []
            for row in cursor.fetchall():
                sucursales.append({
                    'id': row[0],
                    'nombre': row[1] or ''
                })
            
            cursor.close()
            conn.close()
            return sucursales
            
        except Exception as e:
            logger.error(f"Error al obtener sucursales: {e}")
            return []

