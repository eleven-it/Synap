# 01 — Mapa de Capacidades de Producto

**Estado:** COMPLETE | **471 templates, 18 menú apps**

| Capability (usuario) | Module | Screens (approx) | APIs | Data | ERP dep |
|---------------------|--------|------------------:|------|------|:-------:|
| Iniciar sesión / elegir empresa | login | 10 | 5 | usuarios, sesion | **CRITICAL** |
| Administrar usuarios y permisos | core/archivo | 25 | 15 | usuarios, synap_* | HIGH |
| Consultar dashboard módulos | core/dashboard | 3 | — | ModuleConfig | LOW |
| Registrar movimientos stock | stock | 15 | 10 | stock*, movimiento | HIGH |
| Inventario físico / conteo móvil | stock | 8 | 8 | inv_fisico_* | MEDIUM |
| Gestionar pedidos mayorista | ecom | 20 | 60+ | comp_ped, cliente | HIGH |
| Hub pedidos kanban | ecom | 5 | 15 | PG + MySQL | HIGH |
| Pedido masivo sucursales | ecom | 2 | 5 | Excel + comp_ped | HIGH |
| Presupuestos y objetivos venta | ventas | 9 | 10 | comp_ped, objetivos | HIGH |
| Producción diaria / OPT | mpr | 50+ | 35 | mpr_*, stock* | HIGH |
| Parte operario móvil | mpr | 3 | 5 | mpr_parte | MEDIUM |
| TPV / self-checkout | self_checkout | 20 | 39 | resumen_venta_cv, stock | HIGH |
| Informes y dashboards | reports | 15 | 72 | MySQL read | READ |
| Constructor de reportes | reports | 5 | 20 | PG metadata | LOW |
| Auditoría contable | contabilidad_audit | 9 | 5 | cont_asiento read | READ |
| Captura factura compra | compras/captura | 5 | 33 | PG + proveedor | MEDIUM |
| Integración Tienda Nube | tiendanube | 25 | 28 | mappings PG + sync | HIGH |
| Asistente IA | ia | 5 | 25 | PG | LOW |
| Facturación electrónica AFIP | fe_afip | 3 | 8 | AFIP + cuentacliente | HIGH |
| Logística entregas | logistica | 3 | 25 | comp_ped | MEDIUM |
| Migración Odoo | odoo_migracion | 15 | — | PG jobs | MEDIUM |

**Evidence:** `core/utils/utils.py` APPS_MENU, module URLs, subagent product audit.
