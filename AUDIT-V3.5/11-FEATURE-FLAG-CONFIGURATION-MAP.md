# 11 — Feature Flag & Configuration Map

**Estado:** COMPLETE

---

## Taxonomía

| Category | Definition | Example |
|----------|------------|---------|
| **CONFIGURATION** | Static deployment/install values | `DB_NAME`, `SITE_URL` |
| **FEATURE** | Enables/disables capability | `TIENDANUBE_SYNC_ENABLED` |
| **PERMISSION** | User authorization | `ecom.aprobar_pedido` |
| **BUSINESS POLICY** | Rule within enabled feature | `production.requires_approval` |
| **INTEGRATION** | External system toggle | `BEST_AZURE_*` presence |

---

## Deployment-level (.env / settings.py)

| Key | Default | Type | Purpose |
|-----|---------|------|---------|
| `ENVIRONMENT` | production | CONFIG | Security hardening |
| `DEBUG` | False | CONFIG | Dev only |
| `SYNAP_PERMISOS_SOURCE` | legacy | FEATURE | Permission store cutover |
| `SYNAP_AUTO_ENSURE_SCHEMA` | True | FEATURE | Auto DDL synap_* on login |
| `SYNAP_BLOQUEAR_CREAR_PUESTOS` | True | POLICY | Block puesto creation |
| `SYNAP_AUTO_SYNC_PERMISSIONS` | False | FEATURE (deprecated) | Legacy sync |
| `TIENDANUBE_SYNC_ENABLED` | True | FEATURE | Kill switch TN |
| `TIENDANUBE_WEBHOOKS_ENABLED` | True | FEATURE | TN webhooks |
| `FACTURA_COMPRA_LEGACY_SQL_ENABLED` | False | FEATURE | Compras SQL writes |
| `FACTURA_COMPRA_POSTING_BACKEND` | fake | FEATURE | Posting adapter |
| `WEBAUTHN_UNLOCK_ENABLED` | False | FEATURE (deprecated) | Use SystemConfiguration |
| `BEST_AZURE_*` | empty | INTEGRATION | CLIENT-B Azure SQL |
| `SYNAP_PILOTO_CONT` | test | FEATURE | CLIENT-A contab pilot |
| `SYNAP_PILOTO_BASE_EMPRESA` | — | CONFIG | Pilot scope |
| `FACTURA_COMPRA_OCR_*` | various | CONFIG | OCR adapter |

---

## Runtime DB (PostgreSQL SystemConfiguration)

| Key | Type | Purpose |
|-----|------|---------|
| `login.webauthn.unlock_enabled` | FEATURE | PWA WebAuthn unlock |

---

## Per-company MySQL (configuracion_ecom)

| Key | Type | Purpose |
|-----|------|---------|
| `ecom_workflow_jerarquia_comercial` | POLICY | Commercial hierarchy |
| `ecom_aprobacion_pedidos_activa` | FEATURE | Approval workflow |
| `ecom_credito_pedidos_activa` | FEATURE | Credit checks |
| `ecom_credito_hold_prep_activo` | POLICY | Credit hold |
| `ecom_validar_stock_pedidos` | POLICY | Stock validation |
| `ecom_objetivos_en_pedidos` | FEATURE | Objectives in orders |
| `ecom_backorder_en_pedidos` | POLICY | Backorder allowed |

---

## Per-company MySQL (MprEmpresaConfig)

| Field | Type | Purpose |
|-------|------|---------|
| `bloquear_parte_supera_fabricando` | POLICY | Block over-production |
| (other fields) | CONFIG/POLICY | MPR behavior per base |

---

## Module enablement (ModuleConfig Postgres)

| Field | Type | Purpose |
|-------|------|---------|
| `is_active` | FEATURE | Module on/off per installation |
| `name` | CONFIG | Module id (mpr, ecom, reports…) |

Default bootstrap: `core, login, dashboard, reports`.

---

## PWA Nivel A (permission-driven, not per-client)

| Component | Type |
|-----------|------|
| `PWA_MENU_APP_IDS` | CONFIG (code) |
| `MobileLevelAOnlyMiddleware` | FEATURE gate |
| Visibility | PERMISSION + ModuleConfig |

---

## v2 target model

```text
SynapInstallation
  ├── feature_flags: { "production.enabled": true, "tn.sync": false }
  ├── business_policies: { "sales.approval_threshold": 50000 }
  ├── integrations: { "azure_best": { enabled, connection } }
  └── modules: { "mpr": { enabled: true } }
```

**MUST NOT** conflate permission with feature flag in v2.

---

*Evidence: `.env.example`, `django_project/settings.py`, `ecom_config_mysql.py`, `core/module_manager.py`*
