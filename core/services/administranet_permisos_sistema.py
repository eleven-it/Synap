"""
Servicio para gestión de permisos del sistema en administraNET Gestión
Gestiona la tabla permisos_sistema que asigna permisos a puestos
"""
import logging
import MySQLdb
from django.conf import settings
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class AdministraNETPermisosSistemaService:
    """Servicio para gestión de permisos del sistema por puesto en administraNET Gestión"""
    
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
    
    def obtener_permisos_puesto(self, base_empresa: str, id_puesto: int) -> Optional[Dict]:
        """
        Obtiene los permisos del sistema para un puesto específico
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_puesto: ID del puesto
            
        Returns:
            Diccionario con todos los permisos del puesto o None si no existe
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM permisos_sistema WHERE IDPuesto = %s LIMIT 1
            """, [id_puesto])
            
            row = cursor.fetchone()
            
            if row:
                # Obtener nombres de columnas
                column_names = [desc[0] for desc in cursor.description]
                
                # Crear diccionario con todos los permisos
                permisos = dict(zip(column_names, row))
                
                cursor.close()
                conn.close()
                
                return permisos
            
            cursor.close()
            conn.close()
            
            # Si no existe, retornar None (la vista manejará los valores por defecto)
            return None
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al obtener permisos del puesto {id_puesto} en empresa {base_empresa}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al obtener permisos del puesto: {e}", exc_info=True)
            return None
    
    def _get_permisos_por_defecto(self) -> Dict:
        """
        Retorna un diccionario con valores por defecto para todos los permisos
        Basado en la estructura de permisos_sistema
        """
        return {
            'IDPuesto': None,
            'Mod_Precio_Fact': 'Si',
            'cambia_cv': 'Si',
            'actualiza_abm_art': 'Si',
            'mod_lista_de_precio': 'Si',
            'cambia_deposito': 'Si',
            'cambia_caja': 'Si',
            'cambia_sucursal': 'Si',
            'cambia_talonario': 'Si',
            'mod_descuento_pie': 'Si',
            'mod_descuento_renglon': 'Si',
            'mod_precio_pedido': 'No',
            'visualizar_comprobantes': 'Si',
            'anular_comprobantes': 'Si',
            'reimprimir_comprobantes': 'Si',
            'actualiza_lista_compra': 'Si',
            'lista_compra_venta_defecto': 'Si',
            'imprime_cheques': 'No',
            'modifica_pedido_presupuesto': 'Si',
            'modifica_factura_pedido': 'Si',
            'modifica_remito_pedido': 'Si',
            'acceso_pv': 'Si',
            'acceso_comp_ventas_talonario': 'Si',
            'carga_comp_venta': 'Todos',
            'modifica_oc_presupuesto': 'Si',
            'modifica_factura_oc': 'Si',
            'modifica_remito_oc': 'Si',
            'modifica_remitoc_facturac': 'Si',
            'ver_cliente_sucursal': 'Si',
            'ver_proveedor_sucursal': 'Si',
            'carga_comp_cobranza': 'Todos',
            'carga_comp_ped': 'Todos',
            'id_refmovstock': 1,
            'acceso_ref_movstock': 'Todos',
            'acceso_motivo_movstock': 'Todos',
            'genera_fact_rem': 'No',
            'factura_importe_cero': 'No',
            'calcula_precio_oficial': 'No',
            'autoriza_documentos': 'No',
            'cont_prev_asiento': 'No',
            'cont_acceso_contabilidad': 'Si',
            'medio_cobro_pend': 'Normal',
            'pre_ped_otro_cliente': 'No',
            'login_supervisor_credito': 'Si',
            'selec_pv': 'No',
            'cambia_cv_abmcliente': 'Si',
            'cambia_lp_abmcliente': 'Si',
            'modifica_comp_talonario': 'Si',
            'visualiza_aviso': 'No',
            'obliga_cambvendedor': 'No',
            'caja_opciones_total': 'No',
            'obliga_selecpv': 'No',
            'obliga_selecTipoDevol': 'No',
            'popup_mensajeria': 'No',
            'traslada_detalle': 'No',
            'desc_int_cv': 'No',
            'secuencia_tpv_cant': 'No',
            'selec_item_total_ped_rem': 'No',
            'modif_prec_remito_fact': 'No',
            'remite_factura_art': 'No',
            'limita_pendientes_ped_max': 'No',
            'Habilita_selecpv_consultacomp': 'No',
            'selec_ejer_per_cont': 'No',
            'precio_final_fa': 'No',
            'selec_DatosAdicionales': 'No',
            'utiliza_lista_oficial': 'No',
            'lim_desc_renglon': 0,
            'lim_desc_pie': 0,
            'filtra_art_proveedor': 'No',
            'mov_stock_utiliza_cbarra': 'No',
            'plantillas': 'No',
            'art_precios_negativos': 'No',
            'recuerda_ruta_zona': 'No',
            'visualiza_clientes_todos_web': 'No',
            'pedido_web': 'No',
            'remito_web': 'No',
            'ver_informes_gerencia_web': 'No',
            'oe_ultima_etapa': 'No',
            'impresion_oe': 'No',
            'genera_edita_oe': 'No',
            'serie_cod_barra': 'No',
            'fiscal_cambio': 'No',
            'fiscal_codigo_linea_comp': 'No',
            'abmcli_mod_desc': 'No',
            'abmcli_mod_vendedor': 'No',
            'bloquea_oc': 'No',
            'oe_deposito_origenxarticulo': 'No',
            'ajuste_cta_cte': 'No',
            'informes_vendedor': 'No',
            'nc_ruta_cerrada': 'No',
            'mod_fecha_venta': 'No',
            'mod_item_pre_ped': 'No',
            'reporte_pedido': 'Formal',
        }
    
    def guardar_permisos_puesto(self, base_empresa: str, id_puesto: int, permisos: Dict) -> bool:
        """
        Guarda o actualiza los permisos del sistema para un puesto
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_puesto: ID del puesto
            permisos: Diccionario con los permisos a guardar
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Verificar si ya existe un registro para este puesto
            cursor.execute("SELECT id_permisos_sistema FROM permisos_sistema WHERE IDPuesto = %s LIMIT 1", [id_puesto])
            existe = cursor.fetchone()
            
            # Preparar campos y valores para INSERT o UPDATE
            permisos['IDPuesto'] = id_puesto
            
            # Obtener todos los campos de la tabla (excepto id_permisos_sistema que es auto-increment)
            cursor.execute("SHOW COLUMNS FROM permisos_sistema")
            columnas = [row[0] for row in cursor.fetchall() if row[0] != 'id_permisos_sistema']
            
            if existe:
                # UPDATE
                campos_update = []
                valores_update = []
                
                for campo in columnas:
                    if campo in permisos:
                        campos_update.append(f"{campo} = %s")
                        valores_update.append(permisos[campo])
                
                valores_update.append(id_puesto)
                
                query = f"UPDATE permisos_sistema SET {', '.join(campos_update)} WHERE IDPuesto = %s"
                cursor.execute(query, valores_update)
            else:
                # INSERT
                campos_insert = []
                valores_insert = []
                placeholders = []
                
                for campo in columnas:
                    if campo in permisos:
                        campos_insert.append(campo)
                        valores_insert.append(permisos[campo])
                        placeholders.append('%s')
                
                query = f"INSERT INTO permisos_sistema ({', '.join(campos_insert)}) VALUES ({', '.join(placeholders)})"
                cursor.execute(query, valores_insert)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Permisos guardados para puesto {id_puesto}")
            return True
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al guardar permisos del puesto {id_puesto} en empresa {base_empresa}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al guardar permisos del puesto: {e}", exc_info=True)
            return False
    
    def obtener_puesto(self, base_empresa: str, id_puesto: int) -> Optional[Dict]:
        """
        Obtiene información de un puesto específico
        
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
    
    def heredar_permisos_desde_puesto(self, base_empresa: str, id_puesto_destino: int, id_puesto_origen: int) -> bool:
        """
        Hereda todos los permisos del sistema desde un puesto origen a un puesto destino
        Basado en Alta_Configuracion_Tablas_Puesto_Base de CargaPuesto.frm
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_puesto_destino: ID del puesto destino (nuevo puesto)
            id_puesto_origen: ID del puesto origen (puesto base)
            
        Returns:
            True si se heredaron correctamente, False en caso contrario
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Copiar permisos del sistema desde el puesto origen
            cursor.execute("""
                INSERT INTO permiso_sistema_puesto (id_permiso_sistema, key_permiso, valor_permiso, id_puesto) 
                SELECT id_permiso_sistema, key_permiso, valor_permiso, %s
                FROM permiso_sistema_puesto 
                WHERE id_puesto = %s
            """, [id_puesto_destino, id_puesto_origen])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Permisos del sistema heredados desde puesto {id_puesto_origen} a puesto {id_puesto_destino}")
            return True
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al heredar permisos del sistema desde puesto {id_puesto_origen} a puesto {id_puesto_destino}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al heredar permisos del sistema: {e}", exc_info=True)
            return False

