"""
Servicio para gestión de empresas en administraNET Gestión
Gestiona la tabla DatosEmpresa directamente en MySQL de administraNET
Basado en Empresa.frm
"""
import logging
import MySQLdb
from django.conf import settings
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AdministraNETEmpresaService:
    """Servicio para gestión de empresas en administraNET Gestión"""
    
    def __init__(self, server: str = None, port: str = None):
        """
        Inicializa el servicio de gestión de empresas
        
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
    
    def obtener_empresa(self, base_empresa: str) -> Optional[Dict]:
        """
        Obtiene los datos de la empresa desde la tabla DatosEmpresa
        Similar a Recupera_Datos() de Empresa.frm
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            
        Returns:
            Diccionario con información de la empresa o None si no existe
        """
        try:
            logger.info(f"🔍 Intentando obtener empresa de base_empresa: {base_empresa}")
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Verificar si la tabla existe
            cursor.execute("SHOW TABLES LIKE 'DatosEmpresa'")
            table_exists = cursor.fetchone()
            if not table_exists:
                logger.error(f"❌ La tabla 'DatosEmpresa' no existe en la base de datos '{base_empresa}'")
                cursor.close()
                conn.close()
                return None
            
            cursor.execute("""
                SELECT 
                    id_empresa,
                    Nombre,
                    Domicilio,
                    CodProvincia,
                    CodDepartamento,
                    Pais,
                    id_pais,
                    Telefono,
                    Email,
                    Fax,
                    Timbrado,
                    CUIT,
                    Establecimiento,
                    IngBrutos,
                    InicioAct,
                    IDIva,
                    cod_postal,
                    whatsapp,
                    facebook_messenger,
                    twitter,
                    direccion_web,
                    url_ecommerce_cliente,
                    url_ecommerce_vendedor,
                    observaciones,
                    rubro_canal,
                    actividad
                FROM DatosEmpresa
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            logger.info(f"📊 Resultado de consulta: {row is not None} filas encontradas")
            
            if row:
                # Obtener nombres de columnas ANTES de cerrar el cursor
                column_names = [desc[0] for desc in cursor.description]
                
                # Crear diccionario
                empresa_dict = dict(zip(column_names, row))
                
                # Asegurar que CodProvincia y CodDepartamento sean enteros o None
                if empresa_dict.get('CodProvincia') is not None:
                    try:
                        empresa_dict['CodProvincia'] = int(empresa_dict['CodProvincia'])
                    except (ValueError, TypeError):
                        empresa_dict['CodProvincia'] = None
                
                if empresa_dict.get('CodDepartamento') is not None:
                    try:
                        empresa_dict['CodDepartamento'] = int(empresa_dict['CodDepartamento'])
                    except (ValueError, TypeError):
                        empresa_dict['CodDepartamento'] = None
                
                # Asegurar que id_pais sea entero
                if empresa_dict.get('id_pais') is not None:
                    try:
                        empresa_dict['id_pais'] = int(empresa_dict['id_pais'])
                    except (ValueError, TypeError):
                        empresa_dict['id_pais'] = 1
                
                # Convertir fecha a string si existe (formato YYYY-MM-DD para input type="date")
                inicio_act_raw = empresa_dict.get('InicioAct')
                logger.info(f"📅 InicioAct raw value: {inicio_act_raw} (type: {type(inicio_act_raw)})")
                
                if inicio_act_raw:
                    if isinstance(inicio_act_raw, datetime):
                        empresa_dict['InicioAct'] = inicio_act_raw.strftime('%Y-%m-%d')
                        logger.info(f"📅 InicioAct convertido desde datetime: {empresa_dict['InicioAct']}")
                    elif isinstance(inicio_act_raw, str):
                        # Ya está en formato string, verificar formato
                        if len(inicio_act_raw) == 10 and inicio_act_raw.count('-') == 2:
                            # Formato YYYY-MM-DD, mantenerlo
                            empresa_dict['InicioAct'] = inicio_act_raw
                            logger.info(f"📅 InicioAct ya en formato correcto: {empresa_dict['InicioAct']}")
                        else:
                            # Intentar convertir de otros formatos
                            try:
                                fecha_obj = datetime.strptime(inicio_act_raw, '%d/%m/%Y')
                                empresa_dict['InicioAct'] = fecha_obj.strftime('%Y-%m-%d')
                                logger.info(f"📅 InicioAct convertido desde dd/mm/yyyy: {empresa_dict['InicioAct']}")
                            except Exception as e:
                                logger.warning(f"⚠️ No se pudo convertir fecha InicioAct: {inicio_act_raw}, error: {e}")
                                empresa_dict['InicioAct'] = ''
                    else:
                        # Intentar convertir usando str() y luego parsear
                        try:
                            fecha_str = str(inicio_act_raw)
                            if len(fecha_str) >= 10:
                                # Intentar parsear como fecha MySQL (YYYY-MM-DD)
                                fecha_obj = datetime.strptime(fecha_str[:10], '%Y-%m-%d')
                                empresa_dict['InicioAct'] = fecha_obj.strftime('%Y-%m-%d')
                                logger.info(f"📅 InicioAct convertido desde objeto: {empresa_dict['InicioAct']}")
                            else:
                                empresa_dict['InicioAct'] = ''
                        except Exception as e:
                            logger.warning(f"⚠️ No se pudo convertir fecha InicioAct desde objeto: {inicio_act_raw}, error: {e}")
                            empresa_dict['InicioAct'] = ''
                else:
                    # Si es None o vacío, dejar como string vacío para el input date
                    empresa_dict['InicioAct'] = ''
                    logger.info(f"📅 InicioAct es None o vacío, se establece como string vacío")
                
                # Manejar valores por defecto para rubro_canal y actividad según Empresa.frm
                rubro_canal_raw = empresa_dict.get('rubro_canal')
                actividad_raw = empresa_dict.get('actividad')
                
                logger.info(f"📋 rubro_canal raw: {rubro_canal_raw}, actividad raw: {actividad_raw}")
                
                if rubro_canal_raw == '-' or not rubro_canal_raw:
                    empresa_dict['rubro_canal'] = 'Venta minorista'
                    logger.info(f"📋 rubro_canal establecido a valor por defecto: Venta minorista")
                else:
                    empresa_dict['rubro_canal'] = str(rubro_canal_raw).strip()
                    logger.info(f"📋 rubro_canal mantenido: {empresa_dict['rubro_canal']}")
                
                if actividad_raw == '-' or not actividad_raw:
                    empresa_dict['actividad'] = 'Drugstore / Minimarket / Kioscos'
                    logger.info(f"📋 actividad establecida a valor por defecto: Drugstore / Minimarket / Kioscos")
                else:
                    empresa_dict['actividad'] = str(actividad_raw).strip()
                    logger.info(f"📋 actividad mantenida: {empresa_dict['actividad']}")
                
                logger.info(f"✅ Empresa obtenida de {base_empresa} - CodProvincia: {empresa_dict.get('CodProvincia')}, CodDepartamento: {empresa_dict.get('CodDepartamento')}, InicioAct: {empresa_dict.get('InicioAct')}, rubro_canal: {empresa_dict.get('rubro_canal')}, actividad: {empresa_dict.get('actividad')}")
                cursor.close()
                conn.close()
                return empresa_dict
            
            return None
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al obtener empresa de {base_empresa}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al obtener empresa: {e}", exc_info=True)
            return None
    
    def guardar_empresa(self, base_empresa: str, datos_empresa: Dict) -> bool:
        """
        Guarda o actualiza los datos de la empresa en DatosEmpresa
        Similar a Guardar() de Empresa.frm
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            datos_empresa: Diccionario con los datos de la empresa
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Verificar si existe un registro
            cursor.execute("SELECT id_empresa FROM DatosEmpresa LIMIT 1")
            existe = cursor.fetchone()
            
            # Preparar valores para CUIT según país
            cuit_valor = datos_empresa.get('CUIT', '')
            if datos_empresa.get('id_pais') == 1:  # Argentina
                # Si viene con formato con guiones, mantenerlo
                cuit_valor = datos_empresa.get('CUIT', '')
            else:
                # Para otros países, usar campo sin máscara
                cuit_valor = datos_empresa.get('CUIT', '')
            
            if existe:
                # Actualizar registro existente
                cursor.execute("""
                    UPDATE DatosEmpresa SET
                        Nombre = %s,
                        Domicilio = %s,
                        CodProvincia = %s,
                        CodDepartamento = %s,
                        Pais = %s,
                        id_pais = %s,
                        Telefono = %s,
                        Email = %s,
                        Fax = %s,
                        Timbrado = %s,
                        CUIT = %s,
                        Establecimiento = %s,
                        IngBrutos = %s,
                        InicioAct = %s,
                        IDIva = %s,
                        cod_postal = %s,
                        whatsapp = %s,
                        facebook_messenger = %s,
                        twitter = %s,
                        direccion_web = %s,
                        url_ecommerce_cliente = %s,
                        url_ecommerce_vendedor = %s,
                        observaciones = %s,
                        rubro_canal = %s,
                        actividad = %s
                    WHERE id_empresa = %s
                """, [
                    datos_empresa.get('Nombre', ''),
                    datos_empresa.get('Domicilio', ''),
                    datos_empresa.get('CodProvincia'),
                    datos_empresa.get('CodDepartamento'),
                    datos_empresa.get('Pais', ''),
                    datos_empresa.get('id_pais', 1),
                    datos_empresa.get('Telefono', ''),
                    datos_empresa.get('Email', ''),
                    datos_empresa.get('Fax', ''),
                    datos_empresa.get('Timbrado', ''),
                    cuit_valor,
                    datos_empresa.get('Establecimiento', ''),
                    datos_empresa.get('IngBrutos', ''),
                    datos_empresa.get('InicioAct') or None,
                    datos_empresa.get('IDIva'),
                    datos_empresa.get('cod_postal', ''),
                    datos_empresa.get('whatsapp', '-'),
                    datos_empresa.get('facebook_messenger', '-'),
                    datos_empresa.get('twitter', '-'),
                    datos_empresa.get('direccion_web', '-'),
                    datos_empresa.get('url_ecommerce_cliente', '-'),
                    datos_empresa.get('url_ecommerce_vendedor', '-'),
                    datos_empresa.get('observaciones', ''),
                    datos_empresa.get('rubro_canal', 'Venta minorista') or 'Venta minorista',
                    datos_empresa.get('actividad', 'Drugstore / Minimarket / Kioscos') or 'Drugstore / Minimarket / Kioscos',
                    existe[0]
                ])
            else:
                # Crear nuevo registro
                cursor.execute("""
                    INSERT INTO DatosEmpresa (
                        Nombre, Domicilio, CodProvincia, CodDepartamento, Pais, id_pais,
                        Telefono, Email, Fax, Timbrado, CUIT, Establecimiento, IngBrutos,
                        InicioAct, IDIva, cod_postal, whatsapp, facebook_messenger, twitter,
                        direccion_web, url_ecommerce_cliente, url_ecommerce_vendedor,
                        observaciones, rubro_canal, actividad
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, [
                    datos_empresa.get('Nombre', ''),
                    datos_empresa.get('Domicilio', ''),
                    datos_empresa.get('CodProvincia'),
                    datos_empresa.get('CodDepartamento'),
                    datos_empresa.get('Pais', ''),
                    datos_empresa.get('id_pais', 1),
                    datos_empresa.get('Telefono', ''),
                    datos_empresa.get('Email', ''),
                    datos_empresa.get('Fax', ''),
                    datos_empresa.get('Timbrado', ''),
                    cuit_valor,
                    datos_empresa.get('Establecimiento', ''),
                    datos_empresa.get('IngBrutos', ''),
                    datos_empresa.get('InicioAct') or None,
                    datos_empresa.get('IDIva'),
                    datos_empresa.get('cod_postal', ''),
                    datos_empresa.get('whatsapp', '-'),
                    datos_empresa.get('facebook_messenger', '-'),
                    datos_empresa.get('twitter', '-'),
                    datos_empresa.get('direccion_web', '-'),
                    datos_empresa.get('url_ecommerce_cliente', '-'),
                    datos_empresa.get('url_ecommerce_vendedor', '-'),
                    datos_empresa.get('observaciones', ''),
                    datos_empresa.get('rubro_canal', 'Venta minorista') or 'Venta minorista',
                    datos_empresa.get('actividad', 'Drugstore / Minimarket / Kioscos') or 'Drugstore / Minimarket / Kioscos',
                ])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Empresa guardada en {base_empresa}")
            return True
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al guardar empresa en {base_empresa}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al guardar empresa: {e}", exc_info=True)
            return False
    
    def obtener_paises(self, base_empresa: str) -> List[Dict]:
        """
        Obtiene lista de países disponibles
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id_pais, nombre FROM pais ORDER BY nombre")
            
            paises = []
            for row in cursor.fetchall():
                paises.append({
                    'id': row[0],
                    'nombre': row[1] or ''
                })
            
            cursor.close()
            conn.close()
            return paises
            
        except Exception as e:
            logger.error(f"Error al obtener países: {e}")
            return []
    
    def obtener_provincias(self, base_empresa: str, id_pais: int = None) -> List[Dict]:
        """
        Obtiene lista de provincias disponibles, filtradas por país si se proporciona
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            if id_pais:
                cursor.execute("SELECT CodProvincia, Provincia FROM Provincia WHERE id_pais = %s ORDER BY Provincia", [id_pais])
            else:
                cursor.execute("SELECT CodProvincia, Provincia FROM Provincia ORDER BY Provincia")
            
            provincias = []
            for row in cursor.fetchall():
                provincias.append({
                    'id': int(row[0]) if row[0] is not None else None,
                    'nombre': row[1] or ''
                })
            
            cursor.close()
            conn.close()
            return provincias
            
        except Exception as e:
            logger.error(f"Error al obtener provincias: {e}")
            return []
    
    def obtener_departamentos(self, base_empresa: str, cod_provincia: int = None) -> List[Dict]:
        """
        Obtiene lista de departamentos disponibles, filtrados por provincia si se proporciona
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            if cod_provincia:
                cursor.execute("""
                    SELECT IDDepartamento, NombreDepartamento 
                    FROM Departamento 
                    WHERE CodProvincia = %s OR idDepartamento = 1
                    ORDER BY NombreDepartamento
                """, [cod_provincia])
            else:
                cursor.execute("SELECT IDDepartamento, NombreDepartamento FROM Departamento ORDER BY NombreDepartamento")
            
            departamentos = []
            for row in cursor.fetchall():
                departamentos.append({
                    'id': int(row[0]) if row[0] is not None else None,
                    'nombre': row[1] or ''
                })
            
            cursor.close()
            conn.close()
            return departamentos
            
        except Exception as e:
            logger.error(f"Error al obtener departamentos: {e}")
            return []
    
    def obtener_valores_rubro_canal(self, base_empresa: str) -> List[str]:
        """
        Obtiene los valores únicos de rubro_canal desde la base de datos
        para poblar el dropdown. Si no hay valores en la DB, retorna valores por defecto.
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Obtener valores únicos de rubro_canal
            cursor.execute("""
                SELECT DISTINCT rubro_canal 
                FROM DatosEmpresa 
                WHERE rubro_canal IS NOT NULL 
                AND rubro_canal != '-' 
                AND rubro_canal != ''
                ORDER BY rubro_canal
            """)
            resultados = cursor.fetchall()
            valores = [r[0] for r in resultados if r[0]]
            
            cursor.close()
            conn.close()
            
            # Si no hay valores en la DB, usar valores por defecto
            if not valores:
                valores = [
                    'Venta minorista',
                    'Venta mayorista',
                    'Distribuidor',
                    'Distribuidor mayorista',
                    'Fabricante',
                ]
            
            logger.info(f"📋 Valores rubro_canal obtenidos: {valores}")
            return valores
            
        except Exception as e:
            logger.error(f"Error al obtener valores de rubro_canal: {e}")
            # Retornar valores por defecto en caso de error
            return [
                'Venta minorista',
                'Venta mayorista',
                'Distribuidor',
                'Distribuidor mayorista',
                'Fabricante',
            ]
    
    def obtener_valores_actividad(self, base_empresa: str) -> List[str]:
        """
        Obtiene los valores únicos de actividad desde la base de datos
        para poblar el dropdown. Si no hay valores en la DB, retorna valores por defecto.
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Obtener valores únicos de actividad
            cursor.execute("""
                SELECT DISTINCT actividad 
                FROM DatosEmpresa 
                WHERE actividad IS NOT NULL 
                AND actividad != '-' 
                AND actividad != ''
                ORDER BY actividad
            """)
            resultados = cursor.fetchall()
            valores = [r[0] for r in resultados if r[0]]
            
            cursor.close()
            conn.close()
            
            # Si no hay valores en la DB, usar valores por defecto
            if not valores:
                valores = [
                    'Drugstore / Minimarket / Kioscos',
                    'Supermercado',
                    'Farmacia',
                    'Perfumería',
                    'Belleza y cuidado personal',
                    'Otros',
                ]
            
            logger.info(f"📋 Valores actividad obtenidos: {valores}")
            return valores
            
        except Exception as e:
            logger.error(f"Error al obtener valores de actividad: {e}")
            # Retornar valores por defecto en caso de error
            return [
                'Drugstore / Minimarket / Kioscos',
                'Supermercado',
                'Farmacia',
                'Perfumería',
                'Belleza y cuidado personal',
                'Otros',
            ]
    
    def obtener_contribuyentes(self, base_empresa: str, id_pais: int = None) -> List[Dict]:
        """
        Obtiene lista de contribuyentes (condiciones IVA) disponibles
        Si se proporciona id_pais, filtra según el país
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            cursor.execute("SELECT IDIva, Iva, Abreviado FROM Contribuyentes ORDER BY IDIva")
            
            contribuyentes = []
            for row in cursor.fetchall():
                contribuyentes.append({
                    'id': row[0],
                    'nombre': row[1] or '',
                    'abreviado': row[2] or ''
                })
            
            cursor.close()
            conn.close()
            return contribuyentes
            
        except Exception as e:
            logger.error(f"Error al obtener contribuyentes: {e}")
            return []

