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
            
            # Query alineado con CargaUsuario.frm: incluye pv, pvc, tipo_busq y cajas de cobranza/rendición
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
                    usuarios.pv,
                    usuarios.pvc,
                    usuarios.tipo_busq,
                    usuarios.id_caja_cheque,
                    usuarios.id_caja_tarjeta,
                    usuarios.id_punto_ventac,
                    usuarios.id_caja_cheque_deposito,
                    usuarios.id_caja_deposito,
                    usuarios.id_caja_tarjeta_deposito,
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
                    COALESCE(NULLIF(viajantes.Nombre, ''), '') AS nombre_viajante,
                    COALESCE(NULLIF(datosempresa.Nombre, ''), '') AS nombre_empresa
                FROM usuarios
                LEFT JOIN puestos ON puestos.idpuesto = usuarios.id_puesto
                    AND (puestos.anulado IS NULL OR puestos.anulado <> 'Si')
                LEFT JOIN sucursales ON sucursales.id_sucursal = usuarios.id_sucursal
                    AND (sucursales.anulado IS NULL OR sucursales.anulado <> 'Si')
                LEFT JOIN viajantes ON viajantes.CodViajante = usuarios.CodViajante
                LEFT JOIN datosempresa ON datosempresa.id_empresa = usuarios.id_empresa
                WHERE usuarios.id_usuario = %s
            """, [id_usuario])
            
            row = cursor.fetchone()
            
            if row:
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
                    'pv': row[10],
                    'pvc': row[11],
                    'tipo_busq': (row[12] or '').strip() if row[12] else '',
                    'id_caja_cheque': row[13],
                    'id_caja_tarjeta': row[14],
                    'id_punto_ventac': row[15],
                    'id_caja_cheque_deposito': row[16],
                    'id_caja_deposito': row[17],
                    'id_caja_tarjeta_deposito': row[18],
                    'baja_usuario': row[19] if row[19] else 'No',
                    'tipo_busqueda_defecto': row[20],
                    'permiso_supervisor_venta': row[21] or 'No',
                    'vendedor_web': row[22] or 'No',
                    'zoom_reportes': row[23],
                    'color_formulario': row[24] or '',
                    'tipo_boton': row[25] or '',
                    'CodViajante': row[26],
                    'resol_principal': row[27] or '',
                    'entrega_defecto': row[28] or '',
                    'utiliza_reporte_local': row[29] or 'No',
                    'utiliza_certificado_local': row[30] or 'No',
                    'ruta_reporte_local': row[31] or '',
                    'ruta_certificado_local': row[32] or '',
                    'carpeta_documentos': row[33] or '',
                    'fuente_nombre': row[34] or '',
                    'fuente_tamano': row[35],
                    'nombre_puesto': (row[36] or '').strip() if row[36] else '',
                    'nombre_sucursal': (row[37] or '').strip() if row[37] else '',
                    'nombre_viajante': (row[38] or '').strip() if row[38] else '',
                    'nombre_empresa': (row[39] or '').strip() if row[39] else '',
                }
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
            
            # id_sucursal es NOT NULL en tabla usuarios (paridad CargaUsuario.frm): si no viene, usar primera sucursal activa
            id_sucursal = datos_usuario.get('id_sucursal')
            if id_sucursal is None:
                cursor.execute("""
                    SELECT id_sucursal FROM sucursales
                    WHERE (anulado IS NULL OR anulado <> 'Si')
                    ORDER BY id_sucursal LIMIT 1
                """)
                row_suc = cursor.fetchone()
                id_sucursal = row_suc[0] if row_suc else None
                datos_usuario['id_sucursal'] = id_sucursal
            if id_sucursal is None:
                logger.error("No hay sucursales activas en la base; no se puede crear usuario sin id_sucursal.")
                cursor.close()
                conn.close()
                return None
            
            # Encriptar contraseña con AES_ENCRYPT (igual que administraNET Gestión)
            password = datos_usuario.get('password', '')
            
            # Insertar usuario (columnas alineadas con CargaUsuario.frm)
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
                    pv,
                    pvc,
                    tipo_busq,
                    id_caja_cheque,
                    id_caja_tarjeta,
                    id_punto_ventac,
                    id_caja_cheque_deposito,
                    id_caja_deposito,
                    id_caja_tarjeta_deposito,
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
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, [
                nuevo_id,
                datos_usuario.get('cod_usuario', '').lower().strip(),
                password,
                AES_KEY,
                datos_usuario.get('nombre_usuario', '').strip(),
                datos_usuario.get('apellido_usuario', '').strip(),
                datos_usuario.get('id_puesto'),
                datos_usuario.get('id_sucursal') or id_sucursal,
                id_empresa,
                datos_usuario.get('id_punto_venta'),
                datos_usuario.get('id_deposito'),
                datos_usuario.get('id_caja'),
                datos_usuario.get('pv'),
                datos_usuario.get('pvc'),
                (datos_usuario.get('tipo_busq') or '').strip() or None,
                datos_usuario.get('id_caja_cheque'),
                datos_usuario.get('id_caja_tarjeta'),
                datos_usuario.get('id_punto_ventac'),
                datos_usuario.get('id_caja_cheque_deposito'),
                datos_usuario.get('id_caja_deposito'),
                datos_usuario.get('id_caja_tarjeta_deposito'),
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
            
            # Campos actualizables (alineados con CargaUsuario.frm)
            campos_actualizables = [
                'cod_usuario', 'nombre_usuario', 'apellido_usuario',
                'id_puesto', 'id_sucursal', 'id_punto_venta', 'id_deposito',
                'id_caja', 'pv', 'pvc', 'tipo_busq',
                'id_caja_cheque', 'id_caja_tarjeta', 'id_punto_ventac',
                'id_caja_cheque_deposito', 'id_caja_deposito', 'id_caja_tarjeta_deposito',
                'baja_usuario', 'tipo_busqueda_defecto',
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
            
            # Solo puestos no anulados (paridad AdministraNET: listados activos)
            cursor.execute("""
                SELECT idpuesto, puesto FROM puestos
                WHERE (anulado IS NULL OR anulado <> 'Si')
                ORDER BY puesto
            """)
            
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
            
            # Solo sucursales no anuladas (paridad AdministraNET: listados activos)
            cursor.execute("""
                SELECT id_sucursal, nombre_sucursal FROM sucursales
                WHERE (anulado IS NULL OR anulado <> 'Si')
                ORDER BY nombre_sucursal
            """)
            
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

    def obtener_depositos(self, base_empresa: str) -> List[Dict]:
        """Lista depósitos no anulados para desplegables (paridad CargaUsuario.frm)."""
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT CodDeposito, NombreDeposito FROM deposito
                WHERE (anulado IS NULL OR anulado <> 'Si')
                ORDER BY NombreDeposito
            """)
            out = [{'id': row[0], 'nombre': (row[1] or '').strip() or f'Depósito {row[0]}'} for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return out
        except Exception as e:
            logger.debug("No se pudo cargar depósitos: %s", e)
            return []

    def obtener_cajas_abm(self, base_empresa: str, id_sucursal: int = None) -> List[Dict]:
        """Lista todas las cajas (caja_abm) no anuladas. Preferir obtener_cajas_abm_por_tipo para formulario usuario."""
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            q = """
                SELECT id_caja, COALESCE(NULLIF(nombre_caja, ''), tipo_caja) AS nombre, tipo_caja
                FROM caja_abm
                WHERE (anulado IS NULL OR anulado <> 'Si')
            """
            params = []
            if id_sucursal is not None:
                q += " AND (id_sucursal IS NULL OR id_sucursal = %s)"
                params.append(id_sucursal)
            q += " ORDER BY nombre_caja, id_caja"
            cursor.execute(q, params)
            out = [{'id': row[0], 'nombre': (row[1] or row[2] or '').strip() or f'Caja {row[0]}'} for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return out
        except Exception as e:
            logger.debug("No se pudo cargar cajas: %s", e)
            return []

    def obtener_cajas_abm_por_tipo(
        self, base_empresa: str, tipos_caja: List[str], id_sucursal: int = None
    ) -> List[Dict]:
        """
        Lista cajas (caja_abm) no anuladas filtradas por tipo_caja.
        Paridad con CargaUsuario.frm: cada combo usa un RecordSource con tipos concretos.
        tipos_caja: ej. ['Acumulativa', 'Punto de Venta', 'Fondo Fijo'] para efectivo.
        """
        if not tipos_caja:
            return []
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            placeholders = ", ".join(["%s"] * len(tipos_caja))
            q = f"""
                SELECT id_caja, COALESCE(NULLIF(nombre_caja, ''), tipo_caja) AS nombre, tipo_caja
                FROM caja_abm
                WHERE (anulado IS NULL OR anulado <> 'Si') AND tipo_caja IN ({placeholders})
            """
            params = list(tipos_caja)
            if id_sucursal is not None:
                q += " AND (id_sucursal IS NULL OR id_sucursal = %s)"
                params.append(id_sucursal)
            q += " ORDER BY nombre_caja, id_caja"
            cursor.execute(q, params)
            out = [{'id': row[0], 'nombre': (row[1] or row[2] or '').strip() or f'Caja {row[0]}'} for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return out
        except Exception as e:
            logger.debug("No se pudo cargar cajas por tipo %s: %s", tipos_caja, e)
            return []

    def obtener_cajas_usuario_formulario(
        self, base_empresa: str, id_sucursal: int = None
    ) -> Dict[str, List[Dict]]:
        """
        Devuelve las 6 listas de cajas para el formulario usuario, alineadas a CargaUsuario.frm:
        - data_caja / Caja_Deposito: efectivo (Acumulativa, Punto de Venta, Fondo Fijo)
        - data_caja_cheque: Cheque
        - data_caja_cheque_deposito: Acumulativa Cheque
        - data_caja_tarjeta / Caja_Tarjeta_Deposito: Tarjeta, Acumulativa Tarjeta
        """
        tipos_efectivo = ['Acumulativa', 'Punto de Venta', 'Fondo Fijo']
        cajas_efectivo = self.obtener_cajas_abm_por_tipo(base_empresa, tipos_efectivo, id_sucursal)
        cajas_cheque_cobranza = self.obtener_cajas_abm_por_tipo(base_empresa, ['Cheque'], id_sucursal)
        cajas_cheque_rendicion = self.obtener_cajas_abm_por_tipo(
            base_empresa, ['Acumulativa Cheque'], id_sucursal
        )
        cajas_tarjeta = self.obtener_cajas_abm_por_tipo(
            base_empresa, ['Tarjeta', 'Acumulativa Tarjeta'], id_sucursal
        )
        return {
            'cajas_efectivo_cobranza': cajas_efectivo,
            'cajas_efectivo_rendicion': cajas_efectivo,
            'cajas_cheque_cobranza': cajas_cheque_cobranza,
            'cajas_cheque_rendicion': cajas_cheque_rendicion,
            'cajas_tarjeta_cobranza': cajas_tarjeta,
            'cajas_tarjeta_rendicion': cajas_tarjeta,
        }

    def obtener_puntos_venta(self, base_empresa: str, id_sucursal: int = None) -> List[Dict]:
        """Lista puntos de venta para desplegables (paridad CargaUsuario.frm)."""
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            q = "SELECT id_punto_venta, nro_punto_venta FROM punto_venta WHERE 1=1"
            params = []
            if id_sucursal is not None:
                q += " AND (id_sucursal IS NULL OR id_sucursal = %s)"
                params.append(id_sucursal)
            q += " ORDER BY nro_punto_venta, id_punto_venta"
            cursor.execute(q, params)
            out = [{'id': row[0], 'nombre': f"PV {row[1] or row[0]}"} for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return out
        except Exception as e:
            logger.debug("No se pudo cargar puntos de venta: %s", e)
            return []