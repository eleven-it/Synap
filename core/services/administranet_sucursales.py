"""
Servicio para gestión de sucursales en administraNET Gestión
Gestiona la tabla sucursales directamente en MySQL de administraNET
Basado en ABMSucursal.frm y CargaSucursal.frm

Usa core.mysql_pool.get_connection para participar de la conexión por request.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from django.conf import settings

from core.mysql_pool import get_connection

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

    def obtener_viajantes(self, base_empresa: str) -> List[Dict]:
        """
        Lista vendedores (viajantes) no anulados para desplegables.
        Paridad con Configuración.frm: DataViajante.RecordSource = "SELECT * FROM viajantes WHERE anulado = 'No' ORDER BY Nombre"
        Devuelve lista de dicts con CodViajante y Nombre.
        """
        try:
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT CodViajante, COALESCE(Nombre, '') AS Nombre
                    FROM viajantes
                    WHERE COALESCE(anulado, 'No') = 'No'
                    ORDER BY Nombre
                """)
                rows = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                result = []
                for row in rows:
                    d = dict(zip(column_names, row))
                    d['CodViajante'] = int(d['CodViajante']) if d.get('CodViajante') is not None else None
                    result.append(d)
                cursor.close()
                return result
        except Exception as e:
            logger.debug("No se pudo cargar viajantes (tabla puede no existir): %s", e)
            return []

    def listar_zonas(self, base_empresa: str) -> List[Dict]:
        """
        Lista zonas de envío no anuladas (erp_zona). Para desplegable en tipos de envío por sucursal.
        Paridad con CargaSucursal_Envio.frm: Data_Zonas.RecordSource = "SELECT * FROM erp_zona WHERE anulado = 'No' ORDER BY nombre_zona"
        """
        try:
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id_zona, COALESCE(nombre_zona, '') AS nombre_zona
                    FROM erp_zona
                    WHERE COALESCE(anulado, 'No') = 'No'
                    ORDER BY nombre_zona
                """)
                rows = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                result = [dict(zip(column_names, row)) for row in rows]
                for d in result:
                    if d.get('id_zona') is not None:
                        try:
                            d['id_zona'] = int(d['id_zona'])
                        except (ValueError, TypeError):
                            pass
                cursor.close()
                return result
        except Exception as e:
            logger.debug("No se pudo cargar zonas (tabla erp_zona puede no existir): %s", e)
            return []

    def _columnas_sucursal_envios(self, cursor) -> List[str]:
        """
        Devuelve las columnas FK a sucursal en sucursales_envios (id_sucusal y/o id_sucursal).
        Paridad AdministraNET: VB6 escribe en id_sucusal. Usa nombres exactos de la DB.
        Primero intenta con SELECT * LIMIT 1 y las claves del resultado (más fiable con algunos drivers).
        """
        found = []
        try:
            cursor.execute("SELECT * FROM sucursales_envios LIMIT 1")
            row = cursor.fetchone()
            cols = [desc[0] for desc in cursor.description] if cursor.description else []
            for c in cols:
                if c is None:
                    continue
                cstr = str(c).strip() if not isinstance(c, str) else c.strip()
                if cstr.lower() in ('id_sucursal', 'id_sucusal') and cstr not in found:
                    found.append(cstr)
        except Exception:
            pass
        if not found:
            try:
                cursor.execute("SHOW COLUMNS FROM sucursales_envios")
                for row in cursor.fetchall():
                    col = (row[0] or '').strip()
                    if isinstance(col, bytes):
                        col = col.decode('utf-8', errors='replace').strip()
                    if col and col.lower() in ('id_sucursal', 'id_sucusal') and col not in found:
                        found.append(col)
            except Exception:
                pass
        if not found:
            try:
                cursor.execute("SELECT * FROM sucursales_envios LIMIT 0")
                for col in (desc[0] for desc in cursor.description):
                    cstr = str(col).strip() if col else ''
                    if cstr and cstr.lower() in ('id_sucursal', 'id_sucusal') and cstr not in found:
                        found.append(cstr)
            except Exception:
                pass
        if not found:
            return ['id_sucusal']
        low = [c.lower() for c in found]
        if 'id_sucusal' in low and 'id_sucursal' in low:
            return [found[low.index('id_sucusal')], found[low.index('id_sucursal')]]
        if 'id_sucusal' in low:
            return [found[low.index('id_sucusal')]]
        return [found[low.index('id_sucursal')]]

    def _listar_tipos_envio_sucursal_con_where(self, cursor, where_clause: str, params: list) -> List[Dict]:
        """Ejecuta el SELECT con la cláusula WHERE indicada. params: lista de valores para %s."""
        query = """
            SELECT se.id_sucursales_envios, se.tipo_envio, se.id_zona,
                   se.porcentaje_descuento, se.tipo_recargo_envio, se.tipo_recargo_envio_monto,
                   se.monto_minimo_envio_gratis, se.anulado,
                   COALESCE(z.nombre_zona, '') AS nombre_zona
            FROM sucursales_envios se
            LEFT JOIN erp_zona z ON z.id_zona = se.id_zona
            """ + where_clause + """
            ORDER BY z.nombre_zona, se.id_sucursales_envios
        """
        cursor.execute(query, params)
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        result = []
        for row in rows:
            d = dict(zip(column_names, row))
            if d.get('id_sucursales_envios') is not None:
                try:
                    d['id_sucursales_envios'] = int(d['id_sucursales_envios'])
                except (ValueError, TypeError):
                    pass
            if d.get('id_zona') is not None:
                try:
                    d['id_zona'] = int(d['id_zona'])
                except (ValueError, TypeError):
                    pass
            result.append(d)
        return result

    def listar_tipos_envio_sucursal(self, base_empresa: str, id_sucursal: int) -> List[Dict]:
        """
        Lista tipos de cobro por envío solo de la sucursal indicada (branch en edición).
        Paridad: AdministraNET guarda el id de sucursal en id_sucusal. Filtramos por esa sucursal.
        Usa nombres de columna exactos de la DB y compara con int y con str por compatibilidad.
        """
        try:
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                columnas = self._columnas_sucursal_envios(cursor)
                id_val = id_sucursal
                # Escapar nombre de columna con backticks (MySQL)
                def q(c):
                    return "`" + c.replace("`", "``") + "`"
                if len(columnas) >= 2:
                    c1, c2 = columnas[0], columnas[1]
                    where = " WHERE (se." + q(c1) + " = %s OR se." + q(c2) + " = %s)"
                    result = self._listar_tipos_envio_sucursal_con_where(cursor, where, [id_val, id_val])
                else:
                    col = columnas[0]
                    where = " WHERE se." + q(col) + " = %s"
                    result = self._listar_tipos_envio_sucursal_con_where(cursor, where, [id_val])
                if not result:
                    # Intentar comparando como string (por si en la DB está como VARCHAR)
                    if len(columnas) >= 2:
                        where = " WHERE (se." + q(columnas[0]) + " = %s OR se." + q(columnas[1]) + " = %s)"
                        result = self._listar_tipos_envio_sucursal_con_where(cursor, where, [str(id_val), str(id_val)])
                    else:
                        where = " WHERE se." + q(columnas[0]) + " = %s"
                        result = self._listar_tipos_envio_sucursal_con_where(cursor, where, [str(id_val)])
                if not result:
                    # Diagnóstico: columna FK usada y valores de sucursal que sí tienen datos
                    try:
                        cursor.execute("SELECT * FROM sucursales_envios LIMIT 5")
                        sample = cursor.fetchall()
                        cols = [desc[0] for desc in cursor.description]
                        fk_used = columnas[0] if columnas else None
                        distinct_ids = []
                        if columnas:
                            qc = "`" + columnas[0].replace("`", "``") + "`"
                            cursor.execute("SELECT DISTINCT " + qc + " FROM sucursales_envios ORDER BY 1")
                            distinct_ids = [r[0] for r in cursor.fetchall()]
                        logger.info(
                            "Tipos envío: 0 filas para id_sucursal=%s. Columna FK usada: %s. En la tabla hay datos para sucursal(es): %s. Abra la sucursal con ese id (ej. /sucursales/<id>/editar/). Muestra: %s",
                            id_sucursal, fk_used, distinct_ids,
                            dict(zip(cols, sample[0])) if sample and cols else None,
                        )
                    except Exception as diag:
                        logger.debug("Diagnóstico tipos envío: %s", diag)
                cursor.close()
                return result
        except Exception as e:
            logger.warning("No se pudo listar tipos envío sucursal (base=%s, id_sucursal=%s): %s", base_empresa, id_sucursal, e)
            return []

    def crear_tipo_envio_sucursal(self, base_empresa: str, id_sucursal: int, datos: Dict) -> Optional[Dict]:
        """
        Crea un registro en sucursales_envios para la sucursal que se está editando.
        Paridad CargaSucursal_Envio.frm: rs.Fields!id_sucusal = id_sucursales_envios (id de sucursal).
        id_sucursal debe ser el branch_id de la URL (sucursal en edición). Se escribe en id_sucusal
        cuando existe, para compatibilidad con AdministraNET.
        """
        try:
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                columnas = self._columnas_sucursal_envios(cursor)
                col_suc = columnas[0]  # id_sucusal preferido (VB6)
                col_quoted = "`" + col_suc.replace("`", "``") + "`"
                cursor.execute("""
                    INSERT INTO sucursales_envios
                    (""" + col_quoted + """, tipo_envio, id_zona, porcentaje_descuento, tipo_recargo_envio, tipo_recargo_envio_monto, monto_minimo_envio_gratis, anulado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    id_sucursal,
                    (datos.get('tipo_envio') or '').strip() or None,
                    int(datos['id_zona']) if datos.get('id_zona') not in (None, '') else None,
                    self._float_or_zero(datos.get('porcentaje_descuento')),
                    (datos.get('tipo_recargo_envio') or '').strip() or None,
                    self._float_or_zero(datos.get('tipo_recargo_envio_monto')),
                    self._float_or_zero(datos.get('monto_minimo_envio_gratis')),
                    (datos.get('anulado') or 'No').strip() or 'No',
                ])
                conn.commit()
                pk = cursor.lastrowid
                cursor.close()
                return self._get_one_tipo_envio(base_empresa, pk) if pk else None
        except Exception as e:
            logger.exception("Error al crear tipo envío sucursal: %s", e)
            return None

    def actualizar_tipo_envio_sucursal(self, base_empresa: str, id_sucursales_envios: int, datos: Dict) -> bool:
        """
        Actualiza un registro de sucursales_envios. Paridad con CargaSucursal_Envio.frm (modificación).
        """
        try:
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sucursales_envios SET
                        tipo_envio = COALESCE(%s, tipo_envio),
                        id_zona = COALESCE(%s, id_zona),
                        porcentaje_descuento = %s,
                        tipo_recargo_envio = COALESCE(%s, tipo_recargo_envio),
                        tipo_recargo_envio_monto = %s,
                        monto_minimo_envio_gratis = %s,
                        anulado = COALESCE(%s, anulado)
                    WHERE id_sucursales_envios = %s
                """, [
                    (datos.get('tipo_envio') or '').strip() or None,
                    int(datos['id_zona']) if datos.get('id_zona') not in (None, '') else None,
                    self._float_or_zero(datos.get('porcentaje_descuento')),
                    (datos.get('tipo_recargo_envio') or '').strip() or None,
                    self._float_or_zero(datos.get('tipo_recargo_envio_monto')),
                    self._float_or_zero(datos.get('monto_minimo_envio_gratis')),
                    (datos.get('anulado') or 'No').strip() or 'No',
                    id_sucursales_envios,
                ])
                conn.commit()
                cursor.close()
                return True
        except Exception as e:
            logger.exception("Error al actualizar tipo envío sucursal: %s", e)
            return False

    def eliminar_tipo_envio_sucursal(self, base_empresa: str, id_sucursales_envios: int) -> bool:
        """Elimina un registro de sucursales_envios. Paridad con ABM_Sucursal_Envio (eliminar)."""
        try:
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sucursales_envios WHERE id_sucursales_envios = %s", [id_sucursales_envios])
                conn.commit()
                cursor.close()
                return True
        except Exception as e:
            logger.exception("Error al eliminar tipo envío sucursal: %s", e)
            return False

    def tipo_envio_pertenece_a_sucursal(
        self, base_empresa: str, id_sucursales_envios: int, id_sucursal: int
    ) -> bool:
        """Evita IDOR: el registro sucursales_envios debe corresponder a la sucursal de la URL."""
        d = self._get_one_tipo_envio(base_empresa, id_sucursales_envios)
        if not d:
            return False
        for key in ('id_sucursal', 'id_sucusal'):
            if key in d and d.get(key) is not None:
                try:
                    return int(d[key]) == int(id_sucursal)
                except (TypeError, ValueError):
                    continue
        return False

    def _float_or_zero(self, v) -> float:
        if v is None or (isinstance(v, str) and not v.strip()):
            return 0.0
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

    def _get_one_tipo_envio(self, base_empresa: str, id_sucursales_envios: int) -> Optional[Dict]:
        """Devuelve un registro de sucursales_envios con nombre_zona."""
        try:
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                columnas = self._columnas_sucursal_envios(cursor)
                col_suc = columnas[0]
                col_quoted = "`" + col_suc.replace("`", "``") + "`"
                cursor.execute("""
                    SELECT se.id_sucursales_envios, se.""" + col_quoted + """, se.tipo_envio, se.id_zona,
                           se.porcentaje_descuento, se.tipo_recargo_envio, se.tipo_recargo_envio_monto,
                           se.monto_minimo_envio_gratis, se.anulado,
                           COALESCE(z.nombre_zona, '') AS nombre_zona
                    FROM sucursales_envios se
                    LEFT JOIN erp_zona z ON z.id_zona = se.id_zona
                    WHERE se.id_sucursales_envios = %s
                """, [id_sucursales_envios])
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    return None
                column_names = [desc[0] for desc in cursor.description]
                d = dict(zip(column_names, row))
                if d.get('id_sucursales_envios') is not None:
                    d['id_sucursales_envios'] = int(d['id_sucursales_envios'])
                if d.get('id_zona') is not None:
                    d['id_zona'] = int(d['id_zona'])
                cursor.close()
                return d
        except Exception as e:
            logger.debug("_get_one_tipo_envio: %s", e)
            return None

    def listar_sucursales(self, base_empresa: str, busqueda: str = None) -> List[Dict]:
        """
        Lista todas las sucursales de la empresa, con búsqueda opcional
        Basado en ABMSucursal.frm - Consulta_Busqueda()
        """
        try:
            with get_connection(base_empresa) as conn:
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
            with get_connection(base_empresa) as conn:
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
                # Nombre del artículo de facturación de envío (si existe id_articulo_fact_envio)
                id_art = sucursal_dict.get('id_articulo_fact_envio')
                if id_art:
                    try:
                        cursor.execute(
                            "SELECT COALESCE(NombreArticulo, '') FROM articulo WHERE IDArt = %s LIMIT 1",
                            [id_art]
                        )
                        art_row = cursor.fetchone()
                        sucursal_dict['articulo_fact_envio_nombre'] = (art_row[0] or '').strip() if art_row else ''
                    except Exception:
                        sucursal_dict['articulo_fact_envio_nombre'] = ''
                else:
                    sucursal_dict['articulo_fact_envio_nombre'] = ''

                cursor.close()

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
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()

                # Obtener id_empresa de la base de datos activa (solo hay una empresa por base)
                cursor.execute("SELECT id_empresa FROM datosempresa LIMIT 1")
                empresa_row = cursor.fetchone()
                if not empresa_row:
                    logger.error(f"No se encontró empresa en {base_empresa}")
                    cursor.close()
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

                logger.info(f"✅ Sucursal creada exitosamente en {base_empresa}")
                return True

        except Exception as e:
            logger.error(f"Error al crear sucursal: {e}")
            return False
    
    def actualizar_sucursal(self, base_empresa: str, id_sucursal: int, datos_sucursal: Dict) -> bool:
        """
        Actualiza una sucursal existente
        Basado en CargaSucursal.frm - Aceptar_Click() cuando modificacion = "Si"
        """
        try:
            with get_connection(base_empresa) as conn:
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

                # Campos opcionales (COT, Geolocalización, Envíos) como en CargaSucursal.frm
                id_articulo = datos_sucursal.get('id_articulo_fact_envio')
                try:
                    id_articulo = int(id_articulo) if id_articulo not in (None, '') else None
                except (ValueError, TypeError):
                    id_articulo = None
                extras = {
                'cot_clave_acceso': (datos_sucursal.get('cot_clave_acceso') or '').strip() or None,
                'cot_kg_limite': datos_sucursal.get('cot_kg_limite'),
                'cot_monto_limite': datos_sucursal.get('cot_monto_limite'),
                'cot_cantidad_operaciones': datos_sucursal.get('cot_cantidad_operaciones'),
                'geo_latitud': (datos_sucursal.get('geo_latitud') or '').strip() or None,
                'geo_longitud': (datos_sucursal.get('geo_longitud') or '').strip() or None,
                'geo_api_key': (datos_sucursal.get('geo_api_key') or '').strip() or None,
                'geo_api_key_javascript': (datos_sucursal.get('geo_api_key_javascript') or '').strip() or None,
                'activa_calculo_envios': 'Si' if datos_sucursal.get('activa_calculo_envios') in (True, 'Si', 'on', '1') else 'No',
                'id_articulo_fact_envio': id_articulo,
                }
                try:
                    cursor.execute("""
                        UPDATE sucursales SET
                            cot_clave_acceso = COALESCE(%s, cot_clave_acceso),
                        cot_kg_limite = COALESCE(%s, cot_kg_limite),
                        cot_monto_limite = COALESCE(%s, cot_monto_limite),
                        cot_cantidad_operaciones = COALESCE(%s, cot_cantidad_operaciones),
                        geo_latitud = COALESCE(%s, geo_latitud),
                        geo_longitud = COALESCE(%s, geo_longitud),
                        geo_api_key = COALESCE(%s, geo_api_key),
                        geo_api_key_javascript = COALESCE(%s, geo_api_key_javascript),
                        activa_calculo_envios = %s,
                        id_articulo_fact_envio = COALESCE(%s, id_articulo_fact_envio)
                        WHERE id_sucursal = %s
                    """, [
                        extras['cot_clave_acceso'], extras['cot_kg_limite'], extras['cot_monto_limite'],
                        extras['cot_cantidad_operaciones'], extras['geo_latitud'], extras['geo_longitud'],
                        extras['geo_api_key'], extras['geo_api_key_javascript'], extras['activa_calculo_envios'],
                        extras['id_articulo_fact_envio'], id_sucursal,
                    ])
                    conn.commit()
                except Exception as ext:
                    logger.debug("Campos COT/geo/envíos no actualizados (pueden no existir en la tabla): %s", ext)
                    conn.rollback()

                # Configuración Sucursal (Opciones Generales, Agente, Impresoras, DNF - tab Configuración en AdministraNET)
                config = {
                'vendedor_defecto': datos_sucursal.get('vendedor_defecto'),
                'limite_consulta': datos_sucursal.get('limite_consulta'),
                'ruta_reporte_servidor': (datos_sucursal.get('ruta_reporte_servidor') or '').strip() or None,
                'ruta_reporte_comprobante': (datos_sucursal.get('ruta_reporte_comprobante') or '').strip() or None,
                'cant_renglon_venta': datos_sucursal.get('cant_renglon_venta'),
                'salida_sin_stock': datos_sucursal.get('salida_sin_stock', 'No') == 'Si' and 'Si' or 'No',
                'dias_venc_presup': datos_sucursal.get('dias_venc_presup'),
                'dias_venc_pedido': datos_sucursal.get('dias_venc_pedido'),
                'tipo_calculo_precios_impuesto_venta': (datos_sucursal.get('tipo_calculo_precios_impuesto_venta') or '').strip() or None,
                'lim_redondeo_tpv': datos_sucursal.get('lim_redondeo_tpv'),
                'agente_retib': datos_sucursal.get('agente_retib', 'No') == 'Si' and 'Si' or 'No',
                'agente_retg': datos_sucursal.get('agente_retg', 'No') == 'Si' and 'Si' or 'No',
                'agente_reti': datos_sucursal.get('agente_reti', 'No') == 'Si' and 'Si' or 'No',
                'agente_percep': datos_sucursal.get('agente_percep', 'No') == 'Si' and 'Si' or 'No',
                'agente_percep_resol_afip_5329_iva': datos_sucursal.get('agente_percep_resol_afip_5329_iva', 'No') == 'Si' and 'Si' or 'No',
                'tipo_impresora': (datos_sucursal.get('tipo_impresora') or '').strip() or None,
                'nombre_impresora': (datos_sucursal.get('nombre_impresora') or '').strip() or None,
                'puerto_impresora': (datos_sucursal.get('puerto_impresora') or '').strip() or None,
                'doble_imp_etiqueta': datos_sucursal.get('doble_imp_etiqueta', 'No') == 'Si' and 'Si' or 'No',
                'dnf_vta': datos_sucursal.get('dnf_vta', 'No') == 'Si' and 'Si' or 'No',
                'dnf_tipo': (datos_sucursal.get('dnf_tipo') or '').strip() or None,
                'dnf_texto': (datos_sucursal.get('dnf_texto') or '').strip() or None,
                'dnf_texto2': (datos_sucursal.get('dnf_texto2') or '').strip() or None,
                'dnf_texto3': (datos_sucursal.get('dnf_texto3') or '').strip() or None,
                }
                try:
                    cursor.execute("""
                        UPDATE sucursales SET
                            limite_consulta = COALESCE(%s, limite_consulta),
                        ruta_reporte_servidor = COALESCE(%s, ruta_reporte_servidor),
                        ruta_reporte_comprobante = COALESCE(%s, ruta_reporte_comprobante),
                        cant_renglon_venta = COALESCE(%s, cant_renglon_venta),
                        salida_sin_stock = %s,
                        dias_venc_presup = COALESCE(%s, dias_venc_presup),
                        dias_venc_pedido = COALESCE(%s, dias_venc_pedido),
                        tipo_calculo_precios_impuesto_venta = COALESCE(%s, tipo_calculo_precios_impuesto_venta),
                        lim_redondeo_tpv = COALESCE(%s, lim_redondeo_tpv),
                        vendedor_defecto = COALESCE(%s, vendedor_defecto),
                        agente_retib = %s,
                        agente_retg = %s,
                        agente_reti = %s,
                        agente_percep = %s,
                        agente_percep_resol_afip_5329_iva = %s,
                            tipo_impresora = COALESCE(%s, tipo_impresora),
                            nombre_impresora = COALESCE(%s, nombre_impresora),
                            puerto_impresora = COALESCE(%s, puerto_impresora),
                            doble_imp_etiqueta = %s,
                            dnf_vta = %s,
                            dnf_tipo = COALESCE(%s, dnf_tipo),
                            dnf_texto = COALESCE(%s, dnf_texto),
                            dnf_texto2 = COALESCE(%s, dnf_texto2),
                            dnf_texto3 = COALESCE(%s, dnf_texto3)
                        WHERE id_sucursal = %s
                    """, [
                        config['limite_consulta'], config['ruta_reporte_servidor'], config['ruta_reporte_comprobante'],
                    config['cant_renglon_venta'], config['salida_sin_stock'], config['dias_venc_presup'],
                    config['dias_venc_pedido'], config['tipo_calculo_precios_impuesto_venta'], config['lim_redondeo_tpv'],
                    config['vendedor_defecto'], config['agente_retib'], config['agente_retg'], config['agente_reti'],
                    config['agente_percep'], config['agente_percep_resol_afip_5329_iva'],
                    config['tipo_impresora'], config['nombre_impresora'], config['puerto_impresora'],
                    config['doble_imp_etiqueta'], config['dnf_vta'], config['dnf_tipo'],
                    config['dnf_texto'], config['dnf_texto2'], config['dnf_texto3'], id_sucursal,
                    ])
                    conn.commit()
                except Exception as ext2:
                    logger.debug("Campos configuración sucursal no actualizados (pueden no existir): %s", ext2)
                    conn.rollback()

                cursor.close()

                logger.info("✅ Sucursal %s actualizada exitosamente en %s", id_sucursal, base_empresa)
                return True

        except Exception as e:
            logger.error("Error al actualizar sucursal %s: %s", id_sucursal, e)
            return False

    def toggle_anulado_sucursal(self, base_empresa: str, id_sucursal: int) -> Optional[bool]:
        """
        Alterna el estado Anulado de una sucursal (Si <-> No).
        Como en AdministraNET: las sucursales no se eliminan, solo se desactivan.
        Returns: True si quedó activa, False si quedó anulada, None si error.
        """
        try:
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT anulado FROM sucursales WHERE id_sucursal = %s",
                    [id_sucursal],
                )
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    return None
                actual = (row[0] or "").strip().lower()
                nuevo = "No" if actual == "si" else "Si"
                cursor.execute(
                    "UPDATE sucursales SET anulado = %s WHERE id_sucursal = %s",
                    [nuevo, id_sucursal],
                )
                conn.commit()
                cursor.close()
                logger.info("✅ Sucursal %s: anulado %s -> %s en %s", id_sucursal, actual, nuevo, base_empresa)
                return nuevo.lower() != "si"
        except Exception as e:
            logger.error("Error al alternar anulado sucursal %s: %s", id_sucursal, e)
            return None

    def eliminar_sucursal(self, base_empresa: str, id_sucursal: int) -> bool:
        """
        Marca la sucursal como anulada (Anulado='Si'). No se elimina físicamente.
        Preferir toggle_anulado_sucursal para alternar estado desde la lista.
        """
        result = self.toggle_anulado_sucursal(base_empresa, id_sucursal)
        if result is None:
            return False
        # Si estaba activa, ahora está anulada
        return not result

