# 04 — Client Variability Map

**Estado:** COMPLETE

---

## Arquitectura de variabilidad actual

```text
Un codebase Synap
      │
      ├── .env (deployment)
      ├── ModuleConfig (Postgres per deployment)
      ├── configuracion_ecom (MySQL per base_empresa)
      ├── MprEmpresaConfig (MySQL per base_empresa)
      ├── ReportDefinition seeds (per deployment)
      └── Hardcoded client artifacts (excepciones)
```

**No hay** `if base_empresa == "x"` en lógica de negocio Python de producción.

---

## Diferencias por categoría

### CONFIGURATION (estándar v2)

| Item | CLIENT-A | CLIENT-B | Mecanismo |
|------|----------|----------|-----------|
| `DB_NAME` | administranet89 | administranet | `.env` |
| `BEST_AZURE_*` | vacío | configurado | `.env` |
| `configuracion_ecom.*` | valores DABRA | valores Best | MySQL por base |
| `MprEmpresaConfig` | N/A o default | bloqueo parte, etc. | MySQL |
| `ModuleConfig.is_active` | subset módulos | incluye mpr, TN | Postgres |

### FEATURE FLAG

| Flag | Scope | Afecta |
|------|-------|--------|
| `SYNAP_PERMISOS_SOURCE` | deployment | menú/permisos |
| `TIENDANUBE_SYNC_ENABLED` | deployment | sync TN |
| `ecom_aprobacion_pedidos_activa` | per base_empresa | workflow pedidos |
| `ecom_credito_pedidos_activa` | per base_empresa | crédito |
| PWA Nivel A | per user permissions | menú móvil |

### PERMISSION

| Permiso | CLIENT-A típico | CLIENT-B típico |
|---------|-----------------|-----------------|
| `reports.dabra_consolidado_remitos` | ✅ asignado | ❌ |
| `mpr.*` | limitado | ✅ amplio |
| `reports.view_managerial` | ✅ | ✅ |

### BUSINESS POLICY

| Policy | CLIENT-A | CLIENT-B |
|--------|----------|----------|
| Aprobación pedidos por monto | config ecom | config ecom |
| Crédito hold prep | config | config |
| 1 docena = 12 pares (MPR) | N/A | `mpr/services_parte_movil.py` |

### INTEGRATION

| Integration | CLIENT-A | CLIENT-B |
|-------------|----------|----------|
| AdministraNET MySQL | ✅ | ✅ |
| AFIP/ARCA | ⚠️ | ✅ |
| Azure SQL BEST | ❌ | ✅ |
| Tienda Nube | ⚠️ | ✅ |
| Odoo migration | ❌ | ⚠️ |

### CUSTOM CODE (client-specific)

| Item | Client | File | Decisión v2 |
|------|--------|------|-------------|
| DABRA consolidado remitos | A | `reports/services/dabra_consolidado_remitos.py` | **EXTENSION** o report config |
| CODIGO_CLIENTE=368 hardcoded | A | mismo | **CONFIGURE** (customer_id param) |
| migracion-best routes | B | `mpr/urls.py` | **FEATURE FLAG** + adapter |
| `_MARCA_ALIAS` BEST | B | `administranet_articulo.py` | **BUSINESS POLICY** / adapter |
| Monthly Reporting Best Sox templates | B | `reports/services/monthly_*` | **EXTENSION** template pack |
| `es_ped_migracion_best()` | B | `pedidos_hub_pipeline.py` | **BUSINESS POLICY** tag |

### LEGACY HACK

| Item | Evidence | Decisión v2 |
|------|----------|-------------|
| `revertir_partes_fecha` guard `administranet` | `mpr/management/commands/` | **REMOVE** — usar env guard |
| Menu inglés/español mix | `APPS_MENU` | **STANDARDIZE** |
| Dual Tailwind CDN/build | theme | **REMOVE** |

### DATA DIFFERENCE

| Data | Nota |
|------|------|
| Esquema MySQL | Mismo schema AdministraNET; datos distintos por base |
| Report seeds | Distintos slugs instalados por deployment |
| Permisos por puesto | Distintos por empresa en MySQL |

---

## Matriz de decisión v2 (por diferencia)

| Diferencia | Decisión |
|------------|----------|
| `.env` DB_NAME | CONFIGURE |
| configuracion_ecom | CONFIGURE (per company) |
| ModuleConfig | CONFIGURE (per installation) |
| DABRA report cod 368 | CONFIGURE + EXTENSION |
| BEST migration module | FEATURE FLAG |
| BEST marca aliases | BUSINESS POLICY / adapter |
| Best Sox Excel templates | EXTENSION (template pack) |
| MPR docena=12 pares | BUSINESS POLICY |
| SYNAP_PILOTO_CONT | FEATURE FLAG → deprecate |

---

## Objetivo v2

```text
NO CLIENT-SPECIFIC BUSINESS CODE
```

Salvo extensiones explícitas:

```text
Configuration → Feature Flag → Business Policy → Adapter → Extension Point
```

---

*Evidence: client variability subagent audit, `ecom/services/ecom_config_mysql.py`, `mpr/models.py::MprEmpresaConfig`*
