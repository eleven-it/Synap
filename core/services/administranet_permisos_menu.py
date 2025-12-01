"""
Servicio para gestión de permisos del menú en administraNET Gestión
Gestiona la tabla permisos que asigna permisos del menú a puestos
Basado en la estructura jerárquica del menú de ABMPuesto.frm
"""
import logging
import MySQLdb
from django.conf import settings
from typing import Optional, Dict, List, Set

logger = logging.getLogger(__name__)


class AdministraNETPermisosMenuService:
    """Servicio para gestión de permisos del menú por puesto en administraNET Gestión"""
    
    def __init__(self, server: str = None, port: str = None):
        """
        Inicializa el servicio de gestión de permisos del menú
        
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
    
    def obtener_estructura_menu(self) -> Dict:
        """
        Obtiene la estructura completa del menú jerárquico
        Basado en la función Alta_Permisos() de ABMPuesto.frm
        
        Returns:
            Diccionario con la estructura jerárquica del menú
        """
        return {
            'keyArchivo': {
                'nombre': 'Archivo',
                'hijos': {
                    'keyPar': {
                        'nombre': 'Empresa',
                        'hijos': {
                            'keyEmpresa': {'nombre': 'Datos'},
                            'keySucursal': {'nombre': 'Sucursal'},
                            'keyNuevoUsuario': {'nombre': 'Administración de usuarios'},
                            'keyPuesto': {
                                'nombre': 'Puestos',
                                'hijos': {
                                    'keyPuestoMenu': {'nombre': 'Permisos en menu'},
                                    'keyPuestoSistema': {'nombre': 'Permisos en sistema'},
                                }
                            },
                            'keyAdmSesiones': {'nombre': 'Administrador de sesiones'},
                        }
                    },
                    'keyTabla': {
                        'nombre': 'Entidades',
                        'hijos': {
                            'keyCliente': {'nombre': 'Cliente'},
                            'keyProveedor': {'nombre': 'Proveedor'},
                            'keyABMBanco': {'nombre': 'Banco'},
                            'keyViajantes': {'nombre': 'Vendedor'},
                            'keyLaboratorio': {'nombre': 'Laboratorio'},
                            'keyDeposito': {'nombre': 'Depositos'},
                        }
                    },
                    'keyArticulos': {
                        'nombre': 'Productos',
                        'hijos': {
                            'keyRubros': {'nombre': 'Rubro'},
                            'keySubRubros': {'nombre': 'SubRubro'},
                            'keyABMRubroCategoria': {'nombre': 'Categoria rubro'},
                            'keyABMArticulo': {'nombre': 'Articulo'},
                            'keyPresArticulo': {'nombre': 'Presentación de artículo'},
                            'keyArticuloCE': {'nombre': 'Campos especiales'},
                            'keyModelo': {'nombre': 'Marca y modelo'},
                            'keyUM': {'nombre': 'Unidades de medida'},
                            'keyAsigProvArt': {'nombre': 'Asignación de proveedores a artículo'},
                            'keyCambioPrecio': {'nombre': 'Actualización de precios'},
                            'keyCambioDescuento': {'nombre': 'Actualización de descuentos de venta'},
                            'keyConsulta_Avanzada_Articulo': {'nombre': 'Consulta avanzanda de artículos'},
                            'keyDescuento_Proveedor': {'nombre': 'Descuento de proveedor'},
                            'keyDescuento_Proveedor_Act': {'nombre': 'Actualización de descuentos de proveedor'},
                            'keyActualizacion_Datos_Art': {'nombre': 'Actualización masiva de datos de artículo'},
                            'keyRprecios': {'nombre': 'Reglas de precios'},
                            'keyAsigArtTipo': {'nombre': 'Asignación de artículos a tipo de cliente'},
                            'keyDesarmeArt': {'nombre': 'Armado / Desarmado de artículos'},
                            'keyPrograma_Descuentos': {'nombre': 'Programa de descuentos y voucher'},
                            'keyConsulta_Precios': {'nombre': 'Consulta de precios'},
                        }
                    },
                    'keyVariable': {
                        'nombre': 'Variables',
                        'hijos': {
                            'keyImpositiva': {
                                'nombre': 'Impositivas',
                                'hijos': {
                                    'keyImpuesto': {'nombre': 'Impuesto'},
                                    'keyImpuestos': {'nombre': 'Alícuota IVA'},
                                    'keyIngBrutos': {'nombre': 'Alícuota ingresos brutos'},
                                    'keyRet': {
                                        'nombre': 'Retenciones',
                                        'hijos': {
                                            'keyTipoRetPro': {
                                                'nombre': 'Proveedor',
                                                'hijos': {
                                                    'keyTipoRetProI': {'nombre': 'Ingresos Brutos'},
                                                    'keyTipoRetProG': {'nombre': 'Ganancias'},
                                                    'keyTipoRetProIVA': {'nombre': 'IVA'},
                                                }
                                            },
                                            'keyTipoRetCli': {'nombre': 'Cliente'},
                                        }
                                    },
                                    'KeyPercep': {
                                        'nombre': 'Percepciones',
                                        'hijos': {
                                            'keyPerPro': {'nombre': 'Proveedor'},
                                            'keyPerCli': {
                                                'nombre': 'Cliente',
                                                'hijos': {
                                                    'keyTipoPerc': {'nombre': 'Percepciones'},
                                                    'keyTipoPercTipo': {'nombre': 'Tipo de Percepciones'},
                                                }
                                            },
                                        }
                                    },
                                    'keyImpuestoInterno': {'nombre': 'Impuestos internos'},
                                    'keyABMPeriodos': {'nombre': 'Año y periodos de vencimiento fiscal'},
                                    'keyConfCompElect': {'nombre': 'Configuración de Factura electrónica (C.A.E.A)'},
                                }
                            },
                            'keyAdministrativa': {
                                'nombre': 'Administrativas',
                                'hijos': {
                                    'keyPV': {'nombre': 'Puntos de venta y talonario de cobro'},
                                    'keyTalon': {'nombre': 'Talonarios'},
                                    'keyCondVenta': {'nombre': 'Condición venta/compra'},
                                    'keyCotizacion': {'nombre': 'Cotización dólar'},
                                    'keyGastos_Grupo': {'nombre': 'Grupo de gasto'},
                                    'keyGastos': {'nombre': 'Gastos'},
                                    'keyDescRec': {'nombre': 'Descuentos recibos / orden de pago'},
                                    'keyABMCajas': {'nombre': 'Cajas'},
                                    'keyABMTarjetasCredito': {'nombre': 'Tarjetas de crédito / débito / billeteras virtuales'},
                                    'keyABMPlanes_TarjetasCredito': {'nombre': 'Planes de tarjetas de crédito / débito / billeteras virtuales'},
                                    'KeyABMref_movstock': {'nombre': 'Referencia de movimiento de stock'},
                                    'keyABMTransporte': {'nombre': 'Transporte'},
                                    'keyTipoMedioCP': {'nombre': 'Tipo de medio de cobro / pago'},
                                    'keyMedioCP': {'nombre': 'Medio de cobro / pago'},
                                    'keyIngreso': {'nombre': 'Ingreso'},
                                    'keyDeuda': {'nombre': 'Deuda'},
                                }
                            },
                            'keyGeneral': {
                                'nombre': 'Generales',
                                'hijos': {
                                    'keyTC': {'nombre': 'Tipos de cliente'},
                                    'keyDep': {'nombre': 'País / Provincia / Departamento / distrito'},
                                    'keyZona': {'nombre': 'Zonas'},
                                    'keyConfImpFiscal': {'nombre': 'Configuración de impresoras fiscales'},
                                    'keyConfiguracion_Carga_Bascula': {'nombre': 'Configuración de báscula'},
                                }
                            },
                            'keyBancarias': {
                                'nombre': 'Bancarias',
                                'hijos': {
                                    'keyGastoB': {'nombre': 'Gastos bancarios'},
                                    'keyChequeras': {'nombre': 'Cuenta bancaria y chequera'},
                                }
                            },
                            'keyEcommerce': {
                                'nombre': 'Ecommerce',
                                'hijos': {
                                    'keyEcom_Plantilla_Caract': {'nombre': 'Plantilla de característica de artículo'},
                                }
                            },
                        }
                    },
                    'keyProceso': {
                        'nombre': 'Procesos',
                        'hijos': {
                            'keyAnulComp': {'nombre': 'Anulacion de numeración de comprobantes'},
                            'keyAnulCheq': {'nombre': 'Liquidación de comisiones'},
                        }
                    },
                    'keyExportacion': {
                        'nombre': 'Exportaciones',
                        'hijos': {
                            'keyExSIAP': {'nombre': 'Sistemas externos'},
                        }
                    },
                    'keyConf': {'nombre': 'Configuración'},
                    'keySalir': {'nombre': 'Salir'},
                }
            },
            'keyAdministracion': {
                'nombre': 'Gestión',
                'hijos': {
                    'keyVentas': {
                        'nombre': 'Ventas',
                        'hijos': {
                            'keyPre': {'nombre': 'Presupuesto'},
                            'keyPed': {'nombre': 'Pedido'},
                            'keyFacturacion': {'nombre': 'Facturación'},
                            'keyPuntoVenta': {'nombre': 'Punto de Venta'},
                            'keyNC-ND': {'nombre': 'Nota de Crédito / Nota de Débito'},
                            'keyCtaCte-Cli': {'nombre': 'Cuenta Corriente'},
                            'keyConsultaVentas': {'nombre': 'Consultas y Anulaciones'},
                            'keyProcFiscal': {'nombre': 'Procesos fiscales'},
                            'keyAdmCompElect': {'nombre': 'Administración de comprobantes electrónicos'},
                            'keyInformesVentas': {'nombre': 'Informes'},
                        }
                    },
                    'keyCobranza': {
                        'nombre': 'Cobranzas',
                        'hijos': {
                            'keyCob': {'nombre': 'Gestión Cobranza'},
                            'keyConsultaCob': {'nombre': 'Consultas y Anulaciones'},
                            'keyInformesCob': {'nombre': 'Informes'},
                        }
                    },
                    'keyCompras': {
                        'nombre': 'Compras',
                        'hijos': {
                            'keyPreCompra': {'nombre': 'Presupuesto de Compra'},
                            'keyOCCompra': {'nombre': 'Orden de Compra'},
                            'keyFactCompra': {'nombre': 'Facturas de Compra'},
                            'keyNC-ND-Compra': {'nombre': 'Nota de Crédito / Nota de Débito'},
                            'keyCtaCte-Prov': {'nombre': 'Cuenta Corriente'},
                            'keyConsultaCompras': {'nombre': 'Consultas y Anulaciones'},
                            'keyInformesProv': {'nombre': 'Informes'},
                        }
                    },
                    'keyPago': {
                        'nombre': 'Pagos',
                        'hijos': {
                            'keyPagos': {'nombre': 'Gestión Pago'},
                            'keyConsultaPago': {'nombre': 'Consultas y Anulaciones'},
                            'keyInformesPago': {'nombre': 'Informes'},
                        }
                    },
                    'keyStock': {
                        'nombre': 'Stock',
                        'hijos': {
                            'keyCompStock': {'nombre': 'Ingreso Mov. Stock'},
                            'keyRemitoCompra': {'nombre': 'Remito de Compra'},
                            'keyRemitoVenta': {'nombre': 'Remito de Venta'},
                            'keyPedido_Interno': {'nombre': 'Pedido interno a depósito / compras'},
                            'keyInventario': {'nombre': 'Inventario'},
                            'keyConsultaStockRap': {'nombre': 'Consulta Ficha de Stock'},
                            'keyConsultaStock': {'nombre': 'Consultas y Anulaciones'},
                            'keyInformesStock': {'nombre': 'Informes'},
                        }
                    },
                    'keyCaja': {
                        'nombre': 'Caja',
                        'hijos': {
                            'keyCajaG': {'nombre': 'Efectivo'},
                            'keyCajaC': {'nombre': 'Cheques'},
                            'keyCajaT': {'nombre': 'Tarjetas'},
                            'keyCajaMC': {'nombre': 'Otros Medios de Cobro'},
                            'keyInformesCaja': {'nombre': 'Informes'},
                        }
                    },
                    'keyBanco': {
                        'nombre': 'Banco',
                        'hijos': {
                            'keyIngCompBanco': {'nombre': 'Ingreso de comprobantes'},
                            'keyGestionCheques': {'nombre': 'Gestión de cheques de terceros'},
                            'keyGestionChequesPropio': {'nombre': 'Gestión de cheques propios'},
                            'keyInformesBanco': {'nombre': 'Informes'},
                        }
                    },
                    'keyImp': {
                        'nombre': 'Impuestos',
                        'hijos': {
                            'keyGestionImp': {'nombre': 'Gestión Impuestos'},
                            'keyInfImpositivo': {'nombre': 'Informes'},
                        }
                    },
                    'keyInforme': {
                        'nombre': 'Informes Globales',
                        'hijos': {
                            'keyInfComerciales': {'nombre': 'Comerciales'},
                            'keyInfEstadisticas': {'nombre': 'Estadísticas'},
                        }
                    },
                }
            },
            'keyContabilidad': {
                'nombre': 'Contabilidad',
                'hijos': {
                    'keyConf_Contabilidad': {
                        'nombre': 'Configuración',
                        'hijos': {
                            'keyParametros_Contables': {'nombre': 'Parametros Contables Iniciales'},
                            'keyParametros_Cuentas_Contables': {'nombre': 'Parametros de Cuentas Contables'},
                            'keyParametros_Conceptos_Asientos': {'nombre': 'Conceptos de Asientos Contables'},
                            'keyParametros_Plantillas_Asientos': {'nombre': 'Plantillas de Asientos Contables'},
                            'keyCentro_Costos_Contables': {'nombre': 'Centro de Costos'},
                            'keyAjuste_Inflacion_Contables': {'nombre': 'Ajuste por Inflación'},
                        }
                    },
                    'keyEjercicio': {'nombre': 'Ejercicios y Periodos'},
                    'keyPlan_Cuentas': {'nombre': 'Plan de Cuentas'},
                    'keyProc_Asientos_Manuales': {'nombre': 'Asientos Contables'},
                    'keyProc_Contables': {'nombre': 'Procesos Contables'},
                    'keyInfo_Contables': {'nombre': 'Informes'},
                }
            },
            'keyErp': {
                'nombre': 'Proyecto',
                'hijos': {
                    'keyConf_Erp': {
                        'nombre': 'Configuración',
                        'hijos': {
                            'keyRecursos': {'nombre': 'Recursos'},
                            'keyTareas': {'nombre': 'Tareas'},
                            'keyZonas': {'nombre': 'Zonas'},
                            'keyPersonal': {'nombre': 'Ficha Personal'},
                            'keyCargo': {'nombre': 'Cargos'},
                        }
                    },
                    'keyProyecto': {'nombre': 'Proyectos'},
                    'keyCosteo': {'nombre': 'Costeo'},
                    'keyTareasProyecto': {'nombre': 'Planificación Tareas'},
                    'keyPDiario': {'nombre': 'Planificación Diaria'},
                    'keyObs': {'nombre': 'Observaciones'},
                    'keyConsultaERP': {'nombre': 'Consultas y Anulaciones'},
                    'keyInfo_Erp': {'nombre': 'Informes'},
                }
            },
            'keyEnsamblaje': {
                'nombre': 'MPR',
                'hijos': {
                    'keyEnsamblaje_Parametro': {
                        'nombre': 'Parametros MPR',
                        'hijos': {
                            'keyEnsamblajeGeneral': {'nombre': 'Configuración MPR'},
                            'keyEnsamblajeBascula': {'nombre': 'Configuración Báscula'},
                            'keyEnsamblajeTemporada': {'nombre': 'Temporada MPR'},
                            'keyEnsamblajeVehiculo': {'nombre': 'Vehiculo MPR'},
                            'keyPrecioTemporada': {'nombre': 'Tarifa de Zonas por Temporada MPR'},
                            'keyEnsamblajeTaraVehiculo': {'nombre': 'Tara de Vehiculos por Temporada'},
                            'keyEnsamblajeItemClasificacion': {'nombre': 'Items de Clasificación MPR'},
                            'keyEnsamblajeChofer': {'nombre': 'Chofer MPR'},
                        }
                    },
                    'keyEnAbmDef': {'nombre': 'Definición de ensamblaje'},
                    'keyEnAbmRef': {'nombre': 'Definición de referencias de ensamblaje'},
                    'keyEnOE': {'nombre': 'Generacion de OE'},
                    'keyGestionOE': {'nombre': 'Gestión de OE'},
                    'keyEnPesaje': {'nombre': 'Carga de Pesaje'},
                    'keyEnVale': {'nombre': 'Carga de Vales'},
                    'keyEnPesajeCla': {'nombre': 'Clasificar Pesajes'},
                    'keyEnConsulta': {'nombre': 'Consultas y Anulaciones'},
                    'keyEnInformes': {'nombre': 'Informes'},
                }
            },
            'keyLogistica': {
                'nombre': 'Logistica',
                'hijos': {
                    'keyLogiChofer': {'nombre': 'Chofer'},
                    'keyLogiUnidad': {'nombre': 'Unidad'},
                    'keyLogiRuta': {'nombre': 'Ruta'},
                    'keyLogiGestion': {'nombre': 'Gestión de logistica'},
                    'keyLogiConsulta': {'nombre': 'Consultas y Anulaciones'},
                    'keyLogiInformes': {'nombre': 'Informes'},
                }
            },
            'keyCrm': {
                'nombre': 'CRM',
                'hijos': {
                    'keyLlamada': {'nombre': 'Gestión de relaciones comerciales'},
                    'keyMotivo': {'nombre': 'Motivos de relaciones comerciales'},
                    'keyCliP': {'nombre': 'Clientes potenciales'},
                    'keyIntereses': {'nombre': 'Intereses'},
                    'keyGestionInt': {'nombre': 'Asignación de intereses'},
                    'keyContacto': {'nombre': 'Contactos'},
                    'keyAgenda': {
                        'nombre': 'Agenda',
                        'hijos': {
                            'keyCalendario': {'nombre': 'Calendario'},
                            'keyEvento': {'nombre': 'Eventos'},
                            'keyTarea': {'nombre': 'Tareas'},
                        }
                    },
                    'keyCrmInformes': {'nombre': 'Informes'},
                }
            },
            'keyTablero': {
                'nombre': 'Tablero',
                'hijos': {
                    'keyConfTablero': {'nombre': 'Configuración'},
                    'keyVerTablero': {'nombre': 'Ver tablero de control'},
                    'keyIndicadores': {'nombre': 'Indicadores'},
                }
            },
            'keyML': {
                'nombre': 'Mercado Libre',
                'hijos': {
                    'keyMLConfiguracion': {'nombre': 'Configuración'},
                    'keyMLSincronizacion': {'nombre': 'Sincronización de publicaciones'},
                    'keyMLInformes': {'nombre': 'Informes'},
                }
            },
            'keyHerramienta': {
                'nombre': 'Herramientas',
                'hijos': {
                    'keyImportacionBases': {'nombre': 'Importación de datos'},
                    'keyLogError': {'nombre': 'Log de errores'},
                    'keyCalculadora': {'nombre': 'Calculadora'},
                    'keyMensajeria': {'nombre': 'Mensajeria'},
                    'keyEmailLog': {'nombre': 'E-mail log'},
                    'keyCerrarVentana': {'nombre': 'Cerrar ventanas'},
                    'keyMinimizarVentana': {'nombre': 'Minimizar ventanas'},
                    'keyMaximizarVentana': {'nombre': 'Mostrar ventanas'},
                    'keyAutorizaPed': {'nombre': 'Autorización de pedidos'},
                    'keyAutorizaOC': {'nombre': 'Autorización de ordenes de compra'},
                }
            },
            'keyAyuda': {
                'nombre': 'Ayuda',
                'hijos': {
                    'keyManual': {'nombre': 'Manual'},
                    'keyCanal': {'nombre': 'Canal Youtube / tutoriales'},
                    'keyActualizacion': {'nombre': 'Actualizar'},
                    'keyDescargaInformes': {'nombre': 'Descarga de reportes y certificados'},
                    'keyDescargaCrystal': {'nombre': 'Descarga de Crystal Reports XI'},
                    'keyTeamViewer': {'nombre': 'Asistencia remota Teamviewer'},
                    'keyChangeLog': {'nombre': 'Changelog / Control de versiones'},
                    'keySoporte': {'nombre': 'Sistema de soporte de ticket'},
                    'keyAcerca': {'nombre': 'Acerca de'},
                }
            },
        }
    
    def obtener_permisos_puesto(self, base_empresa: str, id_puesto: int) -> Set[str]:
        """
        Obtiene los permisos del menú asignados a un puesto
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_puesto: ID del puesto
            
        Returns:
            Set con las claves de menú (Clavemenu) que tienen permiso = '1'
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT Clavemenu FROM permisos 
                WHERE IDpuesto = %s AND Permiso = '1' AND Clavemenu <> 'keyCajaF'
            """, [str(id_puesto)])
            
            permisos = {row[0] for row in cursor.fetchall()}
            
            cursor.close()
            conn.close()
            
            return permisos
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al obtener permisos del menú del puesto {id_puesto}: {e}")
            return set()
        except Exception as e:
            logger.error(f"Error inesperado al obtener permisos del menú: {e}", exc_info=True)
            return set()
    
    def guardar_permisos_puesto(self, base_empresa: str, id_puesto: int, permisos: Set[str]) -> bool:
        """
        Guarda los permisos del menú para un puesto
        
        Args:
            base_empresa: Nombre de la base de datos de la empresa
            id_puesto: ID del puesto
            permisos: Set con las claves de menú (Clavemenu) a asignar
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        try:
            conn = self._get_connection(base_empresa)
            cursor = conn.cursor()
            
            # Eliminar todos los permisos existentes del puesto
            cursor.execute("DELETE FROM permisos WHERE IDpuesto = %s", [str(id_puesto)])
            
            # Insertar los nuevos permisos
            for clavemenu in permisos:
                cursor.execute("""
                    INSERT INTO permisos (Clavemenu, IDpuesto, Permiso) 
                    VALUES (%s, %s, '1')
                """, [clavemenu, str(id_puesto)])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Permisos del menú guardados para puesto {id_puesto}")
            return True
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al guardar permisos del menú del puesto {id_puesto}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al guardar permisos del menú: {e}", exc_info=True)
            return False
    
    def obtener_todas_las_claves_menu(self) -> List[str]:
        """
        Obtiene todas las claves de menú disponibles recursivamente
        
        Returns:
            Lista con todas las claves de menú
        """
        def obtener_claves_recursivo(nodo: Dict, claves: List[str]):
            """Función recursiva para obtener todas las claves"""
            for clave, datos in nodo.items():
                claves.append(clave)
                if 'hijos' in datos:
                    obtener_claves_recursivo(datos['hijos'], claves)
        
        estructura = self.obtener_estructura_menu()
        claves = []
        obtener_claves_recursivo(estructura, claves)
        return claves
    
    def heredar_permisos_desde_puesto(self, base_empresa: str, id_puesto_destino: int, id_puesto_origen: int) -> bool:
        """
        Hereda todos los permisos del menú desde un puesto origen a un puesto destino
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
            
            # Copiar permisos del menú desde el puesto origen
            cursor.execute("""
                INSERT INTO permisos (Clavemenu, Permiso, IDpuesto) 
                SELECT Clavemenu, Permiso, %s
                FROM permisos 
                WHERE IDpuesto = %s
            """, [str(id_puesto_destino), str(id_puesto_origen)])
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Permisos del menú heredados desde puesto {id_puesto_origen} a puesto {id_puesto_destino}")
            return True
            
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL al heredar permisos del menú desde puesto {id_puesto_origen} a puesto {id_puesto_destino}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al heredar permisos del menú: {e}", exc_info=True)
            return False

