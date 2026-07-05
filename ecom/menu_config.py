"""Configuración del menú lateral — portal mayoristapp (paridad cards PHP)."""

MENU_CONFIG = [
    {
        "name": "ecom",
        "label": "E-commerce",
        "icon": "shopping_cart",
        "module": "ecom",
        "permission": "ecom.ver",
        "children": [
            {
                "name": "ecom_hub",
                "label": "Portal mayorista",
                "url": "ecom:mayoristapp_hub",
                "permission": "ecom.ver",
            },
            {
                "name": "ecom_compra",
                "label": "Compra mayorista",
                "url": "ecom:mayoristapp_compra",
                "permission": "ecom.carrito.editar",
            },
            {
                "name": "ecom_presupuestos",
                "label": "Presupuestos vendedor",
                "url": "ecom:mayoristapp_presupuestos_vendedor",
                "permission": "ecom.comprobantes.ver",
            },
            {
                "name": "ecom_pedidos",
                "label": "Pedidos vendedor",
                "url": "ecom:mayoristapp_pedidos_vendedor",
                "permission": "ecom.comprobantes.ver",
            },
            {
                "name": "ecom_remitos",
                "label": "Remitos",
                "url": "ecom:mayoristapp_listado_remitos",
                "permission": "ecom.comprobantes.ver",
            },
            {
                "name": "ecom_promociones",
                "label": "Promociones",
                "url": "ecom:mayoristapp_listado_promociones",
                "permission": "ecom.catalogo.ver",
            },
            {
                "name": "ecom_clientes",
                "label": "Clientes",
                "url": "ecom:mayoristapp_clientes",
                "permission": "ecom.clientes.ver",
            },
            {
                "name": "ecom_estado_pedidos",
                "label": "Preparación de pedidos",
                "url": "ecom:mayoristapp_estado_pedidos_preparacion",
                "permission": "ecom.logistica.ver",
            },
            {
                "name": "ecom_logistica_entregas",
                "label": "Entregas en ruta",
                "url": "logistica:entregas",
                "permission": "ecom.logistica.ver",
            },
        ],
    },
]
