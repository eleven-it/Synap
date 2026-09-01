# 08 — Permission Inventory

**Estado:** COMPLETE | **CRÍTICO** — 244 códigos synap + legacy

---

## Modelo de autorización v1

```text
Authentication (login/session)
    → Identity (cod_usuario, id_puesto, base_empresa)
        → Permission resolution (SYNAP_PERMISOS_SOURCE)
            → Role (synap_rol per id_puesto OR legacy permiso_sistema_puesto)
                → Permission codes (synap_permiso catalog)
                    → Module gate (ModuleMiddleware)
                        → View/API check (@tiene_permiso, DRF)
                            → Data scope (base_empresa session)
```

---

## Fuentes de autorización

| Source | Location | Runtime |
|--------|----------|---------|
| **synap_permiso** (244 codes) | `core/constantes_permisos.py` → MySQL | `SYNAP_PERMISOS_SOURCE=synap` |
| **permiso_sistema** + **permiso_sistema_puesto** | MySQL legacy VB6 | `legacy` or `dual` |
| **permisos** (Clavemenu) | MySQL | Always merged complement |
| **ROLES_PREDEFINIDOS** | Python templates | Documentation only — not auto-assigned |
| **Django Permiso/Rol** | PostgreSQL | `UsuarioExtendido` path (legacy Synap) |
| **module_registry permissions** | `core/module_registry.py` | Module middleware (misaligned keys) |
| **Supervisor rules** | `administranet_permisos_usuario.py` | `cod_usuario=supervisor` → `*` |

### Feature flag

```text
SYNAP_PERMISOS_SOURCE = legacy | synap | dual  (default: legacy)
```

`.env.example` recommends `synap` for new deployments.

---

## Tipos de permiso

| Type | Examples | Enforced where |
|------|----------|----------------|
| **NAVIGATION** | Menu visibility `APPS_MENU` | `apps_visibles_para_usuario()` — **exact match only** |
| **MODULE** | Module active + module perms | `ModuleMiddleware`, `ModulePermissionMiddleware` |
| **SCREEN** | `@tiene_permiso("mpr.ver")` | View decorator |
| **ACTION** | `stock.crear_movimiento`, `ecom.aprobar_pedido` | View/API |
| **DATA** | Implicit via `base_empresa` session | All MySQL queries |
| **COMPANY SCOPE** | `base_empresa` per session | Login — one DB = one company |
| **TENANT SCOPE** | Not formal — deployment = tenant | `.env` |
| **ADMINISTRATIVE** | `cod_usuario=supervisor`, `@solo_usuario_supervisor` | Special bypass |
| **REPORT** | `reports.ver`, `reports.dabra_consolidado_remitos` | reports views + DRF |
| **INTEGRATION** | `tiendanube_administranet.sync` | TN views |

---

## Catálogo synap (módulos)

`PERMISOS_POR_MODULO` groups: Clientes, Proveedores, Inventario, Ventas, Compras, Stock, MPR, Self-Checkout, FE AFIP, Logística, E-commerce, Reportes, Usuarios, Sistema, IA, TiendaNube, Contabilidad audit, Odoo, etc.

**Wildcards:** `reports.*`, `stock.*`, `self_checkout.*`, `logistica.*`

---

## UI vs Backend enforcement gaps (migration-critical)

| Gap | Risk | Evidence |
|-----|------|----------|
| `/api/` bypasses ModulePermissionMiddleware | **HIGH** | `module_middleware.py:121` |
| Menu ignores wildcards | MEDIUM | `_permiso_menu_ok` exact match |
| `articulo_search_api` session only | **HIGH** | `core/api/views.py` |
| `EcomMayoristappSessionPermission` = session only | **HIGH** | `ecom/permissions.py` |
| Finance credit reads stale session perms | MEDIUM | `ecom/permissions.py` |
| MPR custom inline checks | LOW | `mpr/views.py` — consistent internally |
| module_registry keys ≠ synap_permiso keys | MEDIUM | `core.view_usuario` vs `usuarios.ver` |
| factura_compra_captura IDOR | **CRITICAL** | AUDIT-V2 security finding |
| UI hidden but API callable | **UNKNOWN count** | Requires per-endpoint audit |

---

## Company scoping

- **Model:** 1 MySQL database = 1 company (`base_empresa`)
- Session: `base_empresa`, `id_empresa`, `id_sucursal`, `id_puesto`
- Permission queries always scoped by `base_empresa` + `id_puesto`
- **No cross-company** permission inheritance

---

## Key files

| File | Role |
|------|------|
| `core/constantes_permisos.py` | Catalog |
| `core/services/synap_permisos.py` | Synap store read |
| `core/services/administranet_permisos_usuario.py` | Runtime facade |
| `core/decorators.py` | `@tiene_permiso` |
| `core/middleware/module_middleware.py` | Module gates |
| `core/utils/utils.py` | Menu filtering |
| `ecom/permissions.py`, `reports/permissions.py` | DRF |
| `docs/general/PERMISOS_SYNAP_STORE.md` | Canonical doc |

---

## v2 target principle

> CODE SHOULD DEPEND ON PERMISSIONS, NOT ROLE NAMES.

> Every sensitive action MUST have backend authorization — not hidden UI alone.

---

*Evidence: permissions subagent audit, `core/tests/test_synap_permisos.py`*
