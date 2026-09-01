# 09 — Permission → Capability Matrix

**Estado:** COMPLETE | Extracto de capacidades críticas — catálogo completo: 244 códigos

---

## Matriz (capacidades críticas)

| Capability | View | Create | Update | Delete | Execute | Approve | Export |
|------------|------|--------|--------|--------|---------|---------|--------|
| **Sales order** | `ecom.ver` | `ecom.crear_pedido` | `ecom.editar_pedido` | — | checkout | `ecom.aprobar_pedido` | PDF |
| **Pedido masivo** | `ecom.ver` | import | — | — | confirm | — | plantilla XLSX |
| **Hub kanban** | `ecom.ver` | — | estado change | — | pipeline | `ecom.aprobar_pedido` | — |
| **Stock movement** | `stock.ver` / `stock.*` | `stock.crear_movimiento` | — | — | post | — | PDF |
| **Stock consult** | `stock.consultas` | — | — | — | — | — | — |
| **Inventory count** | `stock.ver` | campaña | conteo | — | ajuste | autorizar | — |
| **MPR OPT** | `mpr.ver` | `mpr.crear_opt` | wizard steps | — | confirm/cierre | `mpr.aprobar_parte` | PDF |
| **Parte operario** | `mpr.parte_operario` | parte | — | — | submit | — | — |
| **TPV sale** | `self_checkout.kiosk` | venta | — | — | confirm | `self_checkout.supervisor` | ticket |
| **Reports dashboard** | `reports.ver` | — | — | — | execute | — | `reports.exportar` |
| **Report design** | `reports.disenar` | builder | edit def | delete | publish | — | JSON |
| **DABRA report** | `reports.dabra_consolidado_remitos` | — | — | — | execute | — | export |
| **Contab audit** | `contabilidad.auditoria.ver` | policy | — | — | run | apply | CSV/XLSX |
| **Users admin** | `usuarios.ver` | `usuarios.crear` | `usuarios.editar` | — | — | — | — |
| **TN sync** | `tiendanube_administranet.ver` | mapping | edit | — | sync | — | CSV |
| **AFIP FE** | `fe_afip.ver` | — | config | — | emit | — | — |
| **IA tools** | `ia.ver` | — | — | — | chat/tool | — | — |

---

## Mapping v1 → v2 permission candidates (documentary — NOT implemented)

| V1 code | V2 candidate | Notes |
|---------|--------------|-------|
| `ecom.ver` | `sales.order.view` | Module namespace |
| `ecom.crear_pedido` | `sales.order.create` | |
| `ecom.aprobar_pedido` | `sales.order.approve` | |
| `stock.crear_movimiento` | `inventory.movement.create` | |
| `stock.*` | `inventory.*` | Wildcard preserved |
| `mpr.crear_opt` | `production.order.create` | |
| `mpr.aprobar_parte` | `production.timesheet.approve` | |
| `self_checkout.kiosk` | `pos.sale.execute` | |
| `reports.ver` | `reports.view` | |
| `reports.exportar` | `reports.export` | |
| `reports.dabra_consolidado_remitos` | `reports.extension.dabra_remitos` | Extension perm |
| `contabilidad.auditoria.ver` | `accounting.audit.view` | |
| `usuarios.ver` | `admin.users.view` | |
| `*` (supervisor) | `system.superuser` | Explicit break-glass |

---

## Enforcement matrix (sample)

| Permission | UI menu | HTML view | API | Data scope |
|------------|:-------:|:---------:|:---:|:----------:|
| `ecom.ver` | ✅ | ✅ | ⚠️ partial | ✅ base_empresa |
| `ecom.aprobar_pedido` | N/A | ✅ | ✅ credit APIs | ✅ |
| `stock.crear_movimiento` | ✅ | ✅ | ✅ stock API | ✅ |
| `reports.ver` | ✅ | ✅ | ✅ reports API | ✅ read |
| `reports.dabra_consolidado_remitos` | ✅ | ✅ | ✅ | ✅ |
| `articulo_search` | N/A | N/A | ❌ **perm only session** | ✅ |

---

*Full catalog: `core/constantes_permisos.py` (244 codes)*
