# core/constantes_permisos.py

# Módulos que reciben un permiso comodín "modulo.*" (acceso total al módulo).
# Centralizado aquí para el catálogo Synap (synap_permiso) y el seed en synap_permisos_seed.
MODULOS_CON_COMODIN = ("reports", "stock", "self_checkout", "logistica")

# Mapeo Clavemenu (tabla permisos VB6/Principal) → key_permiso (permiso_sistema Synap).
# Si el puesto tiene la Clavemenu en permisos con Permiso = '1', se otorga el key_permiso en Synap.
# Equivalencia CargaMovStock / Ingreso Mov. Stock y resto del módulo Stock.
MAPEO_MENU_A_PERMISO = {
    "keyCompStock": "stock.crear_movimiento",
    "keyConsultaStock": "stock.consultas",
    "keyConsultaStockRap": "stock.consultas",
    "keyInformesStock": "stock.informes",
    # Ventas → Presupuesto (Principal.frm / keyPre)
    "keyPre": "ventas.presupuesto.ver",
}

PERMISOS_POR_MODULO = {
    "Clientes": [
        ("clientes.ver", "Ver clientes"),
        ("clientes.crear", "Crear clientes"),
        ("clientes.editar", "Editar clientes"),
        ("clientes.eliminar", "Eliminar clientes"),
        ("clientes.exportar", "Exportar clientes"),
        ("clientes.importar", "Importar clientes"),
        ("clientes.historial", "Ver historial de clientes"),
    ],
    "Proveedores": [
        ("proveedores.ver", "Ver proveedores"),
        ("proveedores.crear", "Crear proveedores"),
        ("proveedores.editar", "Editar proveedores"),
        ("proveedores.eliminar", "Eliminar proveedores"),
        ("proveedores.exportar", "Exportar proveedores"),
        ("proveedores.importar", "Importar proveedores"),
        ("proveedores.historial", "Ver historial de proveedores"),
    ],
    "Inventario": [
        ("inventory.ver_dashboard", "Ver dashboard de inventario"),
        ("inventory.ver_stock", "Ver stock actual"),
        
        ("inventory.ver_product", "Ver productos"),
        ("inventory.create_product", "Crear productos"),
        ("inventory.edit_product", "Editar productos"),
        ("inventory.delete_product", "Eliminar productos"),

        ("inventory.ver_warehouse", "Ver almacenes"),
        ("inventory.create_warehouse", "Crear almacenes"),
        ("inventory.edit_warehouse", "Editar almacenes"),
        
        ("inventory.ver_location", "Ver ubicaciones"),
        ("inventory.create_location", "Crear ubicaciones"),
        ("inventory.edit_location", "Editar ubicaciones"),

        ("inventory.view_brand", "Ver marcas"),
        ("inventory.add_brand", "Añadir marcas"),
        ("inventory.change_brand", "Cambiar marcas"),
        ("inventory.delete_brand", "Eliminar marcas"),

        ("inventory.view_category", "Ver rubros"),
        ("inventory.add_category", "Añadir rubros"),
        ("inventory.change_category", "Cambiar rubros"),
        ("inventory.delete_category", "Eliminar rubros"),

        ("inventory.view_subcategory", "Ver subrubros"),
        ("inventory.add_subcategory", "Añadir subrubros"),
        ("inventory.change_subcategory", "Cambiar subrubros"),
        ("inventory.delete_subcategory", "Eliminar subrubros"),

        ("inventory.realizar_ajuste", "Realizar ajustes de inventario"),
        ("inventory.ver_movements", "Ver historial de movimientos"),

        ("inventory.config_tiendanube", "Configurar TiendaNube"),
    ],
    "Ventas": [
        ("ventas.ver", "Ver ventas"),
        ("ventas.presupuesto.ver", "Ver presupuestos de venta"),
        ("ventas.presupuesto.editar", "Crear y editar presupuestos de venta"),
        ("ventas.precios_terminados.editar", "Actualizar precios de productos terminados"),
        ("ventas.precios_historial.ver", "Consultar histórico y evolución de precios"),
        ("ventas.crear", "Crear ventas"),
        ("ventas.editar", "Editar ventas"),
        ("ventas.eliminar", "Eliminar ventas"),
        ("ventas.anular", "Anular ventas"),
        ("ventas.facturar", "Generar facturas"),
        ("ventas.devoluciones", "Gestionar devoluciones"),
        ("ventas.reportes", "Ver reportes de ventas"),
        ("ventas.exportar", "Exportar ventas"),
    ],
    "Compras": [
        ("compras.ver", "Ver compras"),
        ("compras.crear", "Registrar compras"),
        ("compras.editar", "Editar compras"),
        ("compras.eliminar", "Eliminar compras"),
        ("compras.anular", "Anular compras"),
        ("compras.ordenes", "Gestionar órdenes de compra"),
        ("compras.reportes", "Ver reportes de compras"),
        ("compras.exportar", "Exportar compras"),
    ],
    "Purchases": [
        ("purchases.ver", "Ver purchases"),
        ("purchases.ver_dashboard", "Ver dashboard de purchases"),
        ("purchases.ver_supplier", "Ver proveedores"),
        ("purchases.crear_supplier", "Crear proveedores"),
        ("purchases.editar_supplier", "Editar proveedores"),
        ("purchases.eliminar_supplier", "Eliminar proveedores"),
        ("purchases.ver_request", "Ver solicitudes de compra"),
        ("purchases.crear_request", "Crear solicitudes de compra"),
        ("purchases.editar_request", "Editar solicitudes de compra"),
        ("purchases.eliminar_request", "Eliminar solicitudes de compra"),
        ("purchases.aprobar_request", "Aprobar solicitudes de compra"),
        ("purchases.ver_quotation", "Ver cotizaciones"),
        ("purchases.crear_quotation", "Crear cotizaciones"),
        ("purchases.editar_quotation", "Editar cotizaciones"),
        ("purchases.eliminar_quotation", "Eliminar cotizaciones"),
        ("purchases.evaluar_quotation", "Evaluar cotizaciones"),
        ("purchases.ver_order", "Ver órdenes de compra"),
        ("purchases.crear_order", "Crear órdenes de compra"),
        ("purchases.editar_order", "Editar órdenes de compra"),
        ("purchases.eliminar_order", "Eliminar órdenes de compra"),
        ("purchases.confirmar_order", "Confirmar órdenes de compra"),
        ("purchases.ver_receipt", "Ver recepciones"),
        ("purchases.aprobar_receipt", "Aprobar recepciones"),
        ("purchases.ver_rating", "Ver evaluaciones de proveedores"),
        ("purchases.crear_rating", "Crear evaluaciones de proveedores"),
        ("purchases.ver_workflow", "Ver flujos de aprobación"),
        ("purchases.crear_workflow", "Crear flujos de aprobación"),
        ("purchases.ver_report", "Ver reportes de compras"),
        ("purchases.ver_settings", "Ver configuración de compras"),
    ],
    "Finance": [
        ("finance.ver", "Ver finanzas"),
        ("finance.facturas", "Gestionar facturas"),
        ("finance.pagos", "Gestionar pagos"),
        ("finance.cobros", "Gestionar cobros"),
        ("finance.bancos", "Gestionar bancos"),
        ("finance.contabilidad", "Acceso a contabilidad"),
        ("finance.reportes", "Ver reportes financieros"),
        ("finance.exportar", "Exportar datos financieros"),
    ],
    "Stock": [
        ("stock.ver", "Ver módulo Stock"),
        ("stock.crear_movimiento", "Crear movimiento de stock"),
        ("stock.consultas", "Consultas y anulaciones de stock"),
        ("stock.ref_movstock", "ABM referencia de movimiento de stock"),
        ("stock.informes", "Informes de stock"),
    ],
    "Producción (MPR)": [
        ("mpr.ver", "Ver módulo Producción (MPR)"),
        ("mpr.imputar_armado_1ra", "Imputación de pedido — Armado 1ra (supervisor)"),
        ("mpr.maquinas_lineas", "Gestionar líneas, máquinas y habilitación de artículos (supervisor)"),
        ("mpr.aprobar_parte", "Aprobar partes de producción y registrar desvíos (supervisor)"),
        ("mpr.parte_operario", "Carga de parte de producción desde el móvil (operario)"),
    ],
    "Migración Odoo": [
        ("odoo_migracion.ver", "Ver módulo Migración Odoo (solo usuario supervisor en menú)"),
        ("odoo_migracion.conexiones", "Gestionar conexiones Odoo"),
        ("odoo_migracion.jobs", "Ejecutar y consultar jobs de migración"),
    ],
    "Self-Checkout / TPV": [
        ("self_checkout.ver", "Ver Self-Checkout / TPV"),
        ("self_checkout.kiosk", "Operar kiosco / TPV"),
        ("self_checkout.supervisor", "Supervisar autoservicios"),
        ("self_checkout.admin", "Configurar autoservicios y talonarios"),
    ],
    "Facturación AFIP": [
        ("fe_afip.view_afipconfig", "Ver configuración AFIP (factura electrónica)"),
        ("fe_afip.add_afipconfig", "Crear configuración AFIP"),
        ("fe_afip.change_afipconfig", "Editar configuración AFIP y certificados"),
        ("fe_afip.delete_afipconfig", "Eliminar configuración AFIP"),
    ],
    "Logística": [
        (
            "logistica_editar_entregas",
            "Operar entregas (pantalla Logística — Entregas)",
        ),
    ],
    "E-commerce Mayorista": [
        ("ecom.ver", "Acceder al módulo E-commerce mayorista"),
        ("ecom.catalogo.ver", "Ver catálogo y lista de precios"),
        ("ecom.carrito.editar", "Usar carrito y checkout mayorista"),
        ("ecom.pedidos.crear", "Crear pedidos (compra mayorista / checkout)"),
        ("ecom.pedidos.ver", "Ver listado y detalle de pedidos"),
        ("ecom.pedidos.ver_todos", "Ver pedidos de todos los vendedores (listado gerencial)"),
        ("ecom.pedido_masivo.usar", "Carga masiva de pedidos por sucursal (matriz)"),
        ("ecom.config_vendedor_cliente_marca", "Configurar territorio Vendedor→Cliente→Marca"),
        ("ecom.config_ajustes_ventas", "Configurar ajustes de ventas (ecom)"),
        ("ecom.comprobantes.ver", "Ver listados de comprobantes (PED/PRE/REM/FE/NC)"),
        ("ecom.comprobantes.anular", "Anular pedidos desde el portal"),
        ("ecom.clientes.ver", "Ver clientes del portal"),
        ("ecom.clientes.editar", "Editar clientes y domicilios del portal"),
        ("ecom.ctacte.ver", "Ver cuenta corriente y consumos del portal"),
        ("ecom.cobranzas.ver", "Ver recibos y cobranzas del portal"),
        ("ecom.cobranzas.editar", "Registrar recibos e imputaciones"),
        ("ecom.logistica.ver", "Ver logística operativa del portal"),
        ("ecom.informes.ver", "Acceder a informes enlazados desde E-commerce"),
    ],
    "Reportes": [
        ("reports.view_operational", "Informes operativos"),
        ("reports.view_managerial", "Informes gerenciales"),
        ("reports.ver", "Ver reportes"),
        ("reports.crear", "Crear reportes personalizados"),
        ("reports.editar", "Editar reportes"),
        ("reports.eliminar", "Eliminar reportes"),
        ("reports.exportar", "Exportar reportes"),
        ("reports.programar", "Programar reportes automáticos"),
        ("reports.dashboard", "Acceso a dashboards"),
        ("reports.builder", "Usar constructor visual de reportes"),
        ("reports.templates", "Gestionar templates de reportes"),
        ("reports.components", "Gestionar componentes de reportes"),
        ("reports.schedules", "Gestionar programación de reportes"),
        ("reports.ai", "Usar funcionalidades de IA para reportes"),
    ],
    "Usuarios": [
        ("usuarios.ver", "Ver usuarios"),
        ("usuarios.crear", "Crear usuarios"),
        ("usuarios.editar", "Editar usuarios"),
        ("usuarios.eliminar", "Eliminar usuarios"),
        ("usuarios.perfil", "Ver y editar perfil"),
        ("usuarios.dashboard", "Acceder al panel principal"),
        ("usuarios.historial", "Ver historial de actividad"),
        ("usuarios.roles.ver", "Ver roles"),
        ("usuarios.roles.crear", "Crear roles"),
        ("usuarios.roles.editar", "Editar roles"),
        ("usuarios.roles.eliminar", "Eliminar roles"),
        ("usuarios.permisos.ver", "Ver permisos"),
        ("usuarios.permisos.crear", "Crear permisos"),
        ("usuarios.permisos.editar", "Editar permisos"),
        ("usuarios.permisos.eliminar", "Eliminar permisos"),
    ],
    "Sistema": [
        ("configuracion.general", "Acceso a configuración general"),
        ("configuracion.empresa", "Configurar datos de empresa"),
        ("configuracion.moneda", "Configurar monedas"),
        ("configuracion.uom", "Configurar unidades de medida"),
        ("core.ver_contact", "Ver contactos universales"),
        ("core.crear_contact", "Crear contactos universales"),
        ("core.editar_contact", "Editar contactos universales"),
        ("core.eliminar_contact", "Eliminar contactos universales"),
        ("administrar.usuarios", "Administrar usuarios"),
        ("administrar.roles", "Administrar roles"),
        ("administrar.permisos", "Administrar permisos"),
        ("administrar.backup", "Realizar backups"),
        ("administrar.logs", "Ver logs del sistema"),
        ("administrar.sync", "Sincronización con sistemas externos"),
    ],
    "IA": [
        ("ia.ver", "Ver módulo IA"),
        ("ia.agentes", "Acceder a asistentes IA"),
        ("ia.reportes", "Generar reportes con IA"),
        ("ia.memoria", "Gestionar memoria de asistentes IA"),
        ("ia.recomendaciones", "Recibir recomendaciones de IA"),
        ("ia.predicciones", "Acceso a predicciones"),
        ("ia.automatizacion", "Configurar automatizaciones"),
        ("ia.admin", "Administrar agentes, modelos y políticas IA"),
    ],
    "TiendaNube": [
        ("tiendanube.access", "Access TiendaNube integration")
    ],
    "Tiendanube-AdministraNET": [
        # Dashboard y vistas generales
        ("tiendanube_administranet.view_customermapping", "Ver dashboard y mapeos de clientes"),
        ("tiendanube_administranet.view_tiendanubeconfig", "Ver estado del sistema"),
        
        # Customer Mappings
        ("tiendanube_administranet.add_customermapping", "Crear mapeos de clientes"),
        ("tiendanube_administranet.change_customermapping", "Editar mapeos de clientes"),
        ("tiendanube_administranet.delete_customermapping", "Eliminar mapeos de clientes"),
        
        # Product Mappings
        ("tiendanube_administranet.view_productmapping", "Ver mapeos de productos"),
        ("tiendanube_administranet.add_productmapping", "Crear mapeos de productos"),
        ("tiendanube_administranet.change_productmapping", "Editar mapeos de productos"),
        ("tiendanube_administranet.delete_productmapping", "Eliminar mapeos de productos"),
        
        # Order Mappings
        ("tiendanube_administranet.view_ordermapping", "Ver mapeos de pedidos"),
        ("tiendanube_administranet.add_ordermapping", "Crear mapeos de pedidos"),
        ("tiendanube_administranet.change_ordermapping", "Editar mapeos de pedidos"),
        ("tiendanube_administranet.delete_ordermapping", "Eliminar mapeos de pedidos"),
        
        # Sincronización
        ("tiendanube_administranet.run_sync", "Ejecutar sincronizaciones"),
        ("tiendanube_administranet.view_synclog", "Ver historial de sincronización"),
        
        # Configuración Tiendanube
        ("tiendanube_administranet.add_tiendanubeconfig", "Crear configuración de Tiendanube"),
        ("tiendanube_administranet.change_tiendanubeconfig", "Editar configuración de Tiendanube"),
        ("tiendanube_administranet.delete_tiendanubeconfig", "Eliminar configuración de Tiendanube"),
        
        # Configuración AdministraNET
        ("tiendanube_administranet.view_administranetconfig", "Ver configuración de AdministraNET"),
        ("tiendanube_administranet.change_administranetconfig", "Editar configuración de AdministraNET"),
        
        # Webhooks
        ("tiendanube_administranet.view_webhookconfig", "Ver configuraciones de webhook"),
        ("tiendanube_administranet.add_webhookconfig", "Crear webhooks"),
        ("tiendanube_administranet.change_webhookconfig", "Editar webhooks"),
        ("tiendanube_administranet.delete_webhookconfig", "Eliminar webhooks"),
        ("tiendanube_administranet.view_webhookevent", "Ver eventos de webhook"),
        ("tiendanube_administranet.change_webhookevent", "Procesar eventos de webhook"),
    ],
    "Integraciones": [
        ("core.can_manage_integrations", "Gestionar integraciones"),
        ("core.can_edit_mappings", "Editar mapeos de integración"),
        ("core.can_run_sync", "Ejecutar sincronizaciones"),
        ("core.can_view_sync_logs", "Ver logs de sincronización"),
        ("core.can_configure_integrations", "Configurar integraciones"),
        ("core.can_validate_data", "Validar datos de integración"),
        ("core.can_manage_validation_rules", "Gestionar reglas de validación"),
    ],
}

# Roles predefinidos con sus permisos
ROLES_PREDEFINIDOS = {
    "Administrador": {
        "descripcion": "Acceso total al sistema",
        "permisos": ["*"]  # Todos los permisos
    },
    "Gerente": {
        "descripcion": "Gestión completa de operaciones",
        "permisos": [
            "clientes.*", "proveedores.*", "inventory.*", 
            "sales.*", "purchases.*", "compras.*", "reports.*", "ecom.*",
            "core.ver_contact", "core.crear_contact", "core.editar_contact",
            "usuarios.ver", "usuarios.editar", "usuarios.perfil",
            "configuracion.general", "configuracion.empresa"
        ]
    },
    "Vendedor": {
        "descripcion": "Gestión de ventas y clientes",
        "permisos": [
            "clientes.ver", "clientes.crear", "clientes.editar",
            "ventas.ver", "ventas.crear", "ventas.editar",
            "inventario.ver", "inventario.ver_stock",
            "reports.ver", "usuarios.perfil",
            "ecom.ver", "ecom.catalogo.ver", "ecom.carrito.editar",
            "ecom.pedidos.crear", "ecom.pedidos.ver",
            "ecom.comprobantes.ver", "ecom.clientes.ver", "ecom.ctacte.ver",
            "ecom.logistica.ver", "ecom.informes.ver",
        ]
    },
    "Comprador": {
        "descripcion": "Gestión de compras y proveedores",
        "permisos": [
            "proveedores.ver", "proveedores.crear", "proveedores.editar",
            "compras.ver", "compras.crear", "compras.editar",
            "purchases.ver", "purchases.ver_dashboard", "purchases.ver_supplier", "purchases.crear_supplier", "purchases.editar_supplier",
            "purchases.ver_request", "purchases.crear_request", "purchases.editar_request", "purchases.aprobar_request",
            "purchases.ver_quotation", "purchases.crear_quotation", "purchases.editar_quotation", "purchases.evaluar_quotation",
            "purchases.ver_order", "purchases.crear_order", "purchases.editar_order", "purchases.confirmar_order",
            "purchases.ver_receipt", "purchases.aprobar_receipt", "purchases.ver_rating", "purchases.crear_rating",
            "purchases.ver_workflow", "purchases.crear_workflow", "purchases.ver_report", "purchases.ver_settings",
            "inventory.ver", "inventory.ver_stock",
            "reports.ver", "usuarios.perfil"
        ]
    },
    "Almacén": {
        "descripcion": "Gestión de inventario",
        "permisos": [
            "inventory.ver_dashboard",
            "inventory.ver_stock",
            "inventory.ver_product", "inventory.create_product", "inventory.edit_product", "inventory.delete_product",
            "inventory.ver_warehouse", "inventory.create_warehouse", "inventory.edit_warehouse",
            "inventory.ver_location", "inventory.create_location", "inventory.edit_location",
            "inventory.view_brand", "inventory.add_brand", "inventory.change_brand", "inventory.delete_brand",
            "inventory.view_category", "inventory.add_category", "inventory.change_category", "inventory.delete_category",
            "inventory.view_subcategory", "inventory.add_subcategory", "inventory.change_subcategory", "inventory.delete_subcategory",
            "inventory.realizar_ajuste",
            "inventory.ver_movements",
            "proveedores.ver",
            "compras.ver", 
            "reports.ver", 
            "usuarios.perfil"
        ]
    },
    "Contador": {
        "descripcion": "Gestión financiera y contable",
        "permisos": [
            "finance.*", "reports.ver", "reports.exportar",
            "usuarios.perfil"
        ]
    },
    "Consultor": {
        "descripcion": "Solo lectura y reportes",
        "permisos": [
            "clientes.ver", "proveedores.ver", "inventario.ver",
            "ventas.ver", "compras.ver", "reports.ver",
            "usuarios.perfil"
        ]
    }
}

# Permisos críticos que requieren confirmación especial
PERMISOS_CRITICOS = [
    "usuarios.eliminar",
    "administrar.backup",
    "administrar.logs",
    "configuracion.general",
    "finance.contabilidad"
]

# Permisos que requieren auditoría
PERMISOS_AUDITABLES = [
    "usuarios.eliminar",
    "clientes.eliminar",
    "proveedores.eliminar",
    "inventory.ajustar_stock",
    "ventas.anular",
    "compras.anular",
    "finance.pagos",
    "administrar.backup"
]

# Constantes de permisos para integraciones
CAN_MANAGE_INTEGRATIONS = "core.can_manage_integrations"
CAN_EDIT_MAPPINGS = "core.can_edit_mappings"
CAN_RUN_SYNC = "core.can_run_sync"
CAN_VIEW_SYNC_LOGS = "core.can_view_sync_logs"
CAN_CONFIGURE_INTEGRATIONS = "core.can_configure_integrations"
CAN_VALIDATE_DATA = "core.can_validate_data"
CAN_MANAGE_VALIDATION_RULES = "core.can_manage_validation_rules"

# Self-Checkout (AdministraNET permiso_sistema, compatibles con PERMISOS_POR_MODULO y sync)
SCO_VER = "self_checkout.ver"
SCO_KIOSK = "self_checkout.kiosk"
SCO_SUPERVISOR = "self_checkout.supervisor"
SCO_ADMIN = "self_checkout.admin"
SCO_PERMISSIONS = (SCO_VER, SCO_KIOSK, SCO_SUPERVISOR, SCO_ADMIN)