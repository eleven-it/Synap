# 10 — Role Matrix

**Estado:** COMPLETE | Roles funcionales inferidos — no personas

---

## Modelo v1

Runtime roles = **1 synap_rol per id_puesto** (job position), NOT named business roles.

`ROLES_PREDEFINIDOS` en Python son **plantillas documentales** (Administrador, Gerente, Vendedor, etc.) — no se asignan automáticamente.

---

## Matriz por rol funcional

| Role (functional) | Client A | Client B | Permissions (typical) | Capabilities | Modules | Data scope |
|-------------------|:--------:|:--------:|----------------------|--------------|---------|------------|
| **Admin sistema** (`supervisor`) | ✅ | ✅ | `*` | All | All active | All companies login |
| **Gerente / backoffice** | ✅ | ✅ | reports.*, ecom.*, usuarios | Dashboards, pedidos, users | reports, ecom, core | base_empresa |
| **Vendedor** | ✅ | ✅ | ecom.ver, crear_pedido | Catálogo, pedidos | ecom | base_empresa |
| **Supervisor ventas** | ✅ | ✅ | + aprobar, edit cabecera | Hub approval | ecom | base_empresa |
| **Almacén** | ✅ | ✅ | stock.* | Movimientos, conteo | stock | + sucursal |
| **Operario producción** | ❌ | ✅ | mpr.parte_operario | Parte móvil | mpr | base_empresa |
| **Supervisor producción** | ❌ | ✅ | mpr.aprobar_parte, imputar | Tablero, OPT | mpr | base_empresa |
| **Cajero TPV** | ⚠️ | ✅ | self_checkout.kiosk | Venta kiosco | self_checkout | sucursal/caja |
| **Supervisor TPV** | ⚠️ | ✅ | self_checkout.supervisor | Config, supervisión | self_checkout | base_empresa |
| **Contador** | ✅ | ⚠️ | contabilidad.auditoria.* | Auditoría | contab_audit | base_empresa |
| **Analista gerencia** | ✅ | ✅ | reports.view_managerial | Command center | reports | read-only |
| **Integrador TN** | ❌ | ✅ | tiendanube_administranet.* | Sync, mappings | TN | base_empresa |
| **Comprador** | ⚠️ | ⚠️ | compras.*, captura | Remitos, OCR | compras, captura | base_empresa |
| **Puesto "Supervisor" (nombre)** | ✅ | ✅ | +reports extras only | **NOT admin** | reports | base_empresa |

---

## Ambigüedades documentadas

| Término | Significado 1 | Significado 2 |
|---------|-----------------|---------------|
| supervisor | `cod_usuario='supervisor'` → admin | — |
| Supervisor | `nombre_puesto='Supervisor'` → NOT admin | Reports extras only |
| supervisor ventas | `permiso_supervisor_venta` flag | ecom approval |
| supervisor TPV | `self_checkout.supervisor` perm | caja |

**v2 MUST** eliminate name-based checks; use permission codes only.

---

## Screens por rol (top)

| Role | Primary screens |
|------|-----------------|
| Vendedor | `/ecom/mayoristapp/`, pedidos hub |
| Operario | `/mpr/parte-produccion/` (mobile) |
| Supervisor MPR | `/mpr/wizard/`, `/mpr/tablero/` |
| Cajero | `/self_checkout/kiosco/<id>/` |
| Contador | `/contabilidad/auditoria/` |
| Gerente | `/reports/dashboard/<slug>/` |
| Admin | `/core/archivo/usuarios/`, module mgmt |

---

*Evidence: `AUDIT-V3/PRODUCT/02-USER-TYPE-MAP.md`, `core/constantes_permisos.py::ROLES_PREDEFINIDOS`*
