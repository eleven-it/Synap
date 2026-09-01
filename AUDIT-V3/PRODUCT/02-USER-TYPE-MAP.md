# 02 — Mapa de Tipos de Usuario

**Estado:** COMPLETE | Inferido desde permisos y pantallas — no personas ficticias

| Rol funcional | Evidencia | Permisos clave | Pantallas principales |
|---------------|-----------|----------------|----------------------|
| **Administrador sistema** | `cod_usuario=supervisor` | `*` | Archivo, Settings, Module Mgmt, Odoo |
| **Gerente / backoffice** | `ROLES_PREDEFINIDOS.Gerente` | reports, ecom, usuarios | Dashboard, reports, ecom hub |
| **Vendedor comercial** | `ecom.*`, `ventas.ver` | catálogo, pedidos, presupuestos | ecom portal, pedidos hub |
| **Supervisor ventas** | `permiso_supervisor_venta` | edición cabecera comercial | ecom pedidos |
| **Comprador** | `compras.*`, `purchases.*` | compras, captura | compras expediente |
| **Almacén / stock** | `stock.*` | movimientos, inventario | stock, conteo móvil |
| **Operario producción** | `mpr.parte_operario` | carga parte móvil | mpr/parte-produccion mobile |
| **Supervisor producción** | `mpr.aprobar_parte`, `imputar_armado` | aprobación, tablero | mpr tablero, partes pendientes |
| **Cajero TPV** | `self_checkout.kiosk` | venta kiosco | self_checkout kiosco |
| **Supervisor TPV** | `self_checkout.supervisor` | supervisión caja | sc config |
| **Contador** | `contabilidad.auditoria.*`, `finance.*` | auditoría, cotización | contabilidad tablero |
| **Analista / gerencia** | `reports.view_managerial` | dashboards ejecutivos | reports command center |
| **Integrador TN** | `tiendanube_administranet.*` | sync, mappings | TN dashboard |
| **Puesto "Supervisor" (nombre)** | `nombre_puesto` | **NO admin** — solo reports extra | Según permisos puesto |

**Ambigüedad documentada:** 4 tipos de "supervisor" distintos (sistema, puesto nombre, ventas, TPV).

**Evidence:** `core/constantes_permisos.py`, `ecom/services/mayoristapp_sesion_contexto.py`, `administranet_permisos_usuario.py`.
