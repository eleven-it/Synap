"""
Servicio para gestión de empresas en administraNET Gestión
Gestiona la tabla DatosEmpresa directamente en MySQL de administraNET
Basado en Empresa.frm. Usa el pool MySQL del proyecto (mismo origen que login).
Tipos: ver core.utils.administranet_types (validación y normalización como AdministraNET).
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

import MySQLdb
from django.conf import settings

from core.mysql_pool import get_connection as pool_get_connection
from core.utils.administranet_types import to_int_or_none, to_date_or_none, str_or_default

logger = logging.getLogger(__name__)


def _nombre_tabla_empresa(cursor) -> Optional[str]:
    """
    Resuelve el nombre real de la tabla de datos de empresa (puede variar en mayúsculas/minúsculas).
    Devuelve el nombre tal como está en el servidor o None si no existe.
    """
    return _nombre_tabla(cursor, "datosempresa")


def _nombre_tabla(cursor, nombre_lower: str) -> Optional[str]:
    """
    Resuelve el nombre real de una tabla (puede variar en mayúsculas/minúsculas en MySQL).
    Alineado con AdministraNET: Empresa.frm usa pais, Provincia, Departamento, Contribuyentes.
    Devuelve el nombre tal como está en el servidor o None si no existe.
    """
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall():
        nombre = (row[0] or "").strip()
        if nombre.lower() == nombre_lower:
            return nombre
    return None


# Claves que esperan templates y formularios (capitalización AdministraNET/VB6)
_CLAVES_EMPRESA = (
    "id_empresa", "Nombre", "Domicilio", "CodProvincia", "CodDepartamento", "Pais", "id_pais",
    "Telefono", "Email", "Fax", "Timbrado", "CUIT", "Establecimiento", "IngBrutos", "InicioAct",
    "IDIva", "cod_postal", "whatsapp", "facebook_messenger", "twitter", "direccion_web",
    "url_ecommerce_cliente", "url_ecommerce_vendedor", "observaciones", "rubro_canal", "actividad",
)


def _normalizar_claves_empresa(d: Dict) -> None:
    """Asegura claves con capitalización esperada; MySQL puede devolver nombres en minúsculas."""
    by_lower = {k.lower(): k for k in d}
    for canon in _CLAVES_EMPRESA:
        if canon not in d and canon.lower() in by_lower:
            d[canon] = d.get(by_lower[canon.lower()])


class AdministraNETEmpresaService:
    """Servicio para gestión de empresas en administraNET Gestión"""
    
    def __init__(self, server: str = None, port: str = None):
        """
        Inicializa el servicio de gestión de empresas.
        Las conexiones se obtienen del pool MySQL del proyecto.
        """
        mysql_config = settings.DATABASES['mysql']
        self.server = server or mysql_config['HOST']
        self.port = port or mysql_config['PORT']
        self.user = mysql_config['USER']
        self.password = mysql_config['PASSWORD']
    
    def _get_connection(self, db_name: str):
        """Conexión directa MySQL (para guardar y otros métodos que requieren transacción explícita)."""
        return MySQLdb.connect(
            host=self.server,
            port=int(self.port),
            user=self.user,
            passwd=self.password,
            db=db_name,
            charset='latin1',
        )
    
    def obtener_empresa(self, base_empresa: str) -> Optional[Dict]:
        """
        Obtiene los datos de la empresa desde la tabla DatosEmpresa.
        Usa el pool MySQL (mismo que login). Tolera variación de mayúsculas en el nombre de la tabla.
        Similar a Recupera_Datos() de Empresa.frm. Siempre lee el registro actual (sin caché);
        los cambios hechos desde AdministraNET se reflejan en la siguiente carga.
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa (misma que en AdministraNET)
            
        Returns:
            Diccionario con información de la empresa o None si no existe
        """
        try:
            logger.info("Intentando obtener empresa de base_empresa: %s", base_empresa)
            with pool_get_connection(base_empresa.strip()) as conn:
                cursor = conn.cursor()
                tabla = _nombre_tabla_empresa(cursor)
                if not tabla:
                    logger.error("No existe tabla DatosEmpresa en la base '%s'", base_empresa)
                    return None
                # SELECT * para no depender del esquema exacto (bases antiguas pueden tener menos columnas)
                cursor.execute(f"SELECT * FROM `{tabla}` WHERE id_empresa = 1 LIMIT 1")
                row = cursor.fetchone()
                if not row:
                    cursor.execute(f"SELECT * FROM `{tabla}` LIMIT 1")
                    row = cursor.fetchone()
                logger.info("Resultado de consulta: %s filas (tabla %s)", "1" if row else "0", tabla)
                
                if row:
                    column_names = [desc[0] for desc in cursor.description]
                    empresa_dict = dict(zip(column_names, row))
                    _normalizar_claves_empresa(empresa_dict)

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
                    if empresa_dict.get('id_pais') is not None:
                        try:
                            empresa_dict['id_pais'] = int(empresa_dict['id_pais'])
                        except (ValueError, TypeError):
                            empresa_dict['id_pais'] = 1
                    
                    inicio_act_raw = empresa_dict.get('InicioAct')
                    if inicio_act_raw:
                        if isinstance(inicio_act_raw, datetime):
                            empresa_dict['InicioAct'] = inicio_act_raw.strftime('%Y-%m-%d')
                        elif isinstance(inicio_act_raw, str) and len(inicio_act_raw) == 10 and inicio_act_raw.count('-') == 2:
                            empresa_dict['InicioAct'] = inicio_act_raw
                        else:
                            try:
                                if isinstance(inicio_act_raw, str):
                                    fecha_obj = datetime.strptime(inicio_act_raw[:10].replace('/', '-'), '%d-%m-%Y' if '/' in str(inicio_act_raw)[:10] else '%Y-%m-%d')
                                else:
                                    fecha_obj = datetime.strptime(str(inicio_act_raw)[:10], '%Y-%m-%d')
                                empresa_dict['InicioAct'] = fecha_obj.strftime('%Y-%m-%d')
                            except Exception:
                                empresa_dict['InicioAct'] = ''
                    else:
                        empresa_dict['InicioAct'] = ''
                    
                    rubro_canal_raw = empresa_dict.get('rubro_canal')
                    actividad_raw = empresa_dict.get('actividad')
                    empresa_dict['rubro_canal'] = ('Venta minorista' if (rubro_canal_raw == '-' or not rubro_canal_raw) else str(rubro_canal_raw).strip())
                    empresa_dict['actividad'] = ('Drugstore / Minimarket / Kioscos' if (actividad_raw == '-' or not actividad_raw) else str(actividad_raw).strip())
                    
                    return empresa_dict
                return None
            
        except Exception as e:
            logger.error("Error al obtener empresa de %s: %s", base_empresa, e, exc_info=True)
            return None
    
    def guardar_empresa(self, base_empresa: str, datos_empresa: Dict) -> bool:
        """
        Guarda o actualiza los datos de la empresa en DatosEmpresa.
        Alineado con Empresa.frm (Guardar): mismos campos y tipos que AdministraNET.
        Schema: INT (CodProvincia, CodDepartamento, id_pais, IDIva), DATE (InicioAct), VARCHAR/MEDIUMTEXT.
        Usa el nombre real de la tabla (resolución mayúsculas/minúsculas) e id_empresa = 1.
        """
        base = (base_empresa or '').strip()
        if not base:
            logger.error("guardar_empresa: base_empresa vacío")
            return False
        try:
            with pool_get_connection(base) as conn:
                cursor = conn.cursor()
                # Verificar que la conexión es a la base de la sesión (no a otra DB)
                cursor.execute("SELECT DATABASE()")
                db_actual = (cursor.fetchone() or (None,))[0]
                if db_actual != base:
                    logger.error(
                        "guardar_empresa: conexión apunta a DB distinta: esperado=%r, actual=%r",
                        base,
                        db_actual,
                    )
                    return False
                logger.info("guardar_empresa: escribiendo en base %s (session base_empresa)", base)
                tabla = _nombre_tabla_empresa(cursor)
                if not tabla:
                    logger.error("No existe tabla DatosEmpresa en la base '%s'", base)
                    return False

                # Normalizar tipos (core.utils.administranet_types)
                cod_prov = to_int_or_none(datos_empresa.get('CodProvincia'))
                cod_dpto = to_int_or_none(datos_empresa.get('CodDepartamento'))
                id_pais = to_int_or_none(datos_empresa.get('id_pais')) or 1
                id_iva = to_int_or_none(datos_empresa.get('IDIva'))
                inicio_act = to_date_or_none(datos_empresa.get('InicioAct'))

                cuit_valor = str_or_default(datos_empresa.get('CUIT'))
                nombre = str_or_default(datos_empresa.get('Nombre'))
                domicilio = str_or_default(datos_empresa.get('Domicilio'))
                pais = str_or_default(datos_empresa.get('Pais'))
                telefono = str_or_default(datos_empresa.get('Telefono'))
                email = str_or_default(datos_empresa.get('Email'))
                fax = str_or_default(datos_empresa.get('Fax'))
                timbrado = str_or_default(datos_empresa.get('Timbrado'))
                establecimiento = str_or_default(datos_empresa.get('Establecimiento'))
                ing_brutos = str_or_default(datos_empresa.get('IngBrutos'))
                cod_postal = str_or_default(datos_empresa.get('cod_postal'))
                whatsapp = str_or_default(datos_empresa.get('whatsapp'), '-')
                facebook_messenger = str_or_default(datos_empresa.get('facebook_messenger'), '-')
                twitter = str_or_default(datos_empresa.get('twitter'), '-')
                direccion_web = str_or_default(datos_empresa.get('direccion_web'), '-')
                url_ecom_cli = str_or_default(datos_empresa.get('url_ecommerce_cliente'), '-')
                url_ecom_vend = str_or_default(datos_empresa.get('url_ecommerce_vendedor'), '-')
                observaciones = str_or_default(datos_empresa.get('observaciones'))
                # Como en Empresa.frm: rubro_canal y actividad son texto; vacío se guarda como '' (compatible con VB6)
                rubro_canal_raw = (datos_empresa.get('rubro_canal') or '').strip()
                actividad_raw = (datos_empresa.get('actividad') or '').strip()
                rubro_canal = rubro_canal_raw if rubro_canal_raw else '-'
                actividad = actividad_raw if actividad_raw else '-'

                params = [
                    nombre, domicilio, cod_prov, cod_dpto, pais, id_pais,
                    telefono, email, fax, timbrado, cuit_valor, establecimiento, ing_brutos,
                    inicio_act, id_iva, cod_postal, whatsapp, facebook_messenger, twitter,
                    direccion_web, url_ecom_cli, url_ecom_vend, observaciones, rubro_canal, actividad,
                ]
                update_sql = f"""
                    UPDATE `{tabla}` SET
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
                    WHERE id_empresa = 1
                """
                insert_sql = f"""
                    INSERT INTO `{tabla}` (
                        id_empresa, Nombre, Domicilio, CodProvincia, CodDepartamento, Pais, id_pais,
                        Telefono, Email, Fax, Timbrado, CUIT, Establecimiento, IngBrutos,
                        InicioAct, IDIva, cod_postal, whatsapp, facebook_messenger, twitter,
                        direccion_web, url_ecommerce_cliente, url_ecommerce_vendedor,
                        observaciones, rubro_canal, actividad
                    ) VALUES (
                        1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """

                cursor.execute(f"SELECT id_empresa FROM `{tabla}` WHERE id_empresa = 1 LIMIT 1")
                existe = cursor.fetchone()

                if existe:
                    cursor.execute(update_sql, params)
                else:
                    cursor.execute(insert_sql, params)

                # Sincronizar datosempresa2 si existe (Empresa.frm en VB6 puede usar esta tabla, línea 1743)
                tabla2 = _nombre_tabla(cursor, "datosempresa2")
                if tabla2:
                    try:
                        cursor.execute(f"SELECT id_empresa FROM `{tabla2}` WHERE id_empresa = 1 LIMIT 1")
                        if cursor.fetchone():
                            cursor.execute(update_sql.replace(f"`{tabla}`", f"`{tabla2}`"), params)
                            logger.info("✅ Sincronizado también en %s", tabla2)
                    except MySQLdb.Error as e2:
                        logger.warning("No se pudo actualizar %s (se guardó en %s): %s", tabla2, tabla, e2)

                conn.commit()
            logger.info("✅ Empresa guardada en %s (tabla %s)", base, tabla)
            return True
        except MySQLdb.Error as e:
            logger.error("Error MySQL al guardar empresa en %s: %s", base, e)
            return False
        except Exception as e:
            logger.error("Error inesperado al guardar empresa: %s", e, exc_info=True)
            return False
    
    def obtener_paises(self, base_empresa: str) -> List[Dict]:
        """
        Obtiene lista de países disponibles desde la base de la empresa.
        Alineado con Empresa.frm: SELECT * FROM pais ORDER BY nombre.
        Tolera variación de mayúsculas en el nombre de la tabla.
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            tabla = _nombre_tabla(cursor, "pais")
            if not tabla:
                logger.warning("No existe tabla pais en la base '%s'", base_empresa)
                cursor.close()
                conn.close()
                return []
            cursor.execute(f"SELECT id_pais, nombre FROM {tabla} ORDER BY nombre")
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
        Obtiene lista de provincias disponibles, filtradas por país si se proporciona.
        Alineado con Empresa.frm: Provincia WHERE id_pais = ... ORDER BY Provincia.
        Tolera variación de mayúsculas en el nombre de la tabla.
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            tabla = _nombre_tabla(cursor, "provincia")
            if not tabla:
                logger.warning("No existe tabla Provincia en la base '%s'", base_empresa)
                cursor.close()
                conn.close()
                return []
            if id_pais:
                cursor.execute(f"SELECT CodProvincia, Provincia FROM {tabla} WHERE id_pais = %s ORDER BY Provincia", [id_pais])
            else:
                cursor.execute(f"SELECT CodProvincia, Provincia FROM {tabla} ORDER BY Provincia")
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
        Obtiene lista de departamentos disponibles, filtrados por provincia si se proporciona.
        Alineado con Empresa.frm: Departamento filtrado por CodProvincia, ORDER BY NombreDepartamento.
        Tolera variación de mayúsculas en el nombre de la tabla.
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            tabla = _nombre_tabla(cursor, "departamento")
            if not tabla:
                logger.warning("No existe tabla Departamento en la base '%s'", base_empresa)
                cursor.close()
                conn.close()
                return []
            if cod_provincia:
                cursor.execute(f"""
                    SELECT IDDepartamento, NombreDepartamento
                    FROM {tabla}
                    WHERE CodProvincia = %s OR idDepartamento = 1
                    ORDER BY NombreDepartamento
                """, [cod_provincia])
            else:
                cursor.execute(f"SELECT IDDepartamento, NombreDepartamento FROM {tabla} ORDER BY NombreDepartamento")
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
        Obtiene todas las opciones para el dropdown Rubro/Canal: valores por defecto
        más todos los valores distintos que existan en DatosEmpresa (sin filtrar por
        NULL/'-'/vacío), para que se muestren todas las opciones que hay en la DB.
        """
        default_rubro = [
            'Venta minorista',
            'Venta mayorista',
            'Distribuidor',
            'Distribuidor mayorista',
            'Fabricante',
        ]
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            tabla = _nombre_tabla_empresa(cursor)
            if not tabla:
                cursor.close()
                conn.close()
                return default_rubro
            cursor.execute(f"""
                SELECT DISTINCT rubro_canal
                FROM {tabla}
                ORDER BY rubro_canal
            """)
            resultados = cursor.fetchall()
            cursor.close()
            conn.close()
            # Incluir todo valor presente en la DB (strip, excluir solo vacíos)
            desde_db = []
            for r in resultados:
                val = (r[0] or '').strip()
                if val and val != '-':
                    desde_db.append(val)
            # Unir: primero los por defecto, luego los de la DB que no estén ya
            seen = {v for v in default_rubro}
            valores = list(default_rubro)
            for v in sorted(set(desde_db)):
                if v not in seen:
                    seen.add(v)
                    valores.append(v)
            logger.info(f"📋 Valores rubro_canal obtenidos: {len(valores)} (por defecto + DB)")
            return valores
        except Exception as e:
            logger.error(f"Error al obtener valores de rubro_canal: {e}")
            return default_rubro
    
    def obtener_valores_actividad(self, base_empresa: str) -> List[str]:
        """
        Obtiene todas las opciones para el dropdown Actividad: valores por defecto
        más todos los valores distintos que existan en DatosEmpresa (sin filtrar por
        NULL/'-'/vacío), para que se muestren todas las opciones que hay en la DB.
        """
        default_actividad = [
            'Drugstore / Minimarket / Kioscos',
            'Supermercado',
            'Farmacia',
            'Perfumería',
            'Belleza y cuidado personal',
            'Otros',
        ]
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            tabla = _nombre_tabla_empresa(cursor)
            if not tabla:
                cursor.close()
                conn.close()
                return default_actividad
            cursor.execute(f"""
                SELECT DISTINCT actividad
                FROM {tabla}
                ORDER BY actividad
            """)
            resultados = cursor.fetchall()
            cursor.close()
            conn.close()
            # Incluir todo valor presente en la DB (strip, excluir solo vacíos)
            desde_db = []
            for r in resultados:
                val = (r[0] or '').strip()
                if val and val != '-':
                    desde_db.append(val)
            # Unir: primero los por defecto, luego los de la DB que no estén ya
            seen = {v for v in default_actividad}
            valores = list(default_actividad)
            for v in sorted(set(desde_db)):
                if v not in seen:
                    seen.add(v)
                    valores.append(v)
            logger.info(f"📋 Valores actividad obtenidos: {len(valores)} (por defecto + DB)")
            return valores
        except Exception as e:
            logger.error(f"Error al obtener valores de actividad: {e}")
            return default_actividad
    
    def obtener_contribuyentes(self, base_empresa: str, id_pais: int = None) -> List[Dict]:
        """
        Obtiene lista de contribuyentes (condiciones IVA) disponibles desde la base de la empresa.
        Alineado con Empresa.frm: SELECT * FROM Contribuyentes (combo Iva).
        Tolera variación de mayúsculas en el nombre de la tabla.
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            tabla = _nombre_tabla(cursor, "contribuyentes")
            if not tabla:
                logger.warning("No existe tabla Contribuyentes en la base '%s'", base_empresa)
                cursor.close()
                conn.close()
                return []
            cursor.execute(f"SELECT IDIva, Iva, Abreviado FROM {tabla} ORDER BY IDIva")
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

