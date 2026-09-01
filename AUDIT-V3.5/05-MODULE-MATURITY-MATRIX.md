# 05 — Module Maturity Matrix

**Estado:** COMPLETE | 22 apps en `INSTALLED_APPS` propias

**Leyenda Functional:** PRODUCTION | PILOT | STAGING | DEVELOPMENT | EXPERIMENTAL | INCOMPLETE | DEPRECATED | DEAD  
**Technical score:** 0–5 (Architecture, Testing, Security, Observability, Maintainability, Data, UI, Docs)

---

| Module | Purpose | Client A | Client B | Functional | Tech (avg) | Legacy coupling | UI maturity | Notes |
|--------|---------|:--------:|:--------:|:------------|:----------:|:---------------:|:-------------:|-------|
| **core** | Platform, users, modules, perms | ✅ | ✅ | PRODUCTION | 3.5 | HIGH | 3 | 587 MySQL writes via services |
| **login** | Auth, session, empresa | ✅ | ✅ | PRODUCTION | 4 | HIGH | 3 | session_bootstrap critical |
| **dashboard** | Module dashboard stub | ✅ | ✅ | DEVELOPMENT | 2 | LOW | 2 | Minimal UI |
| **theme** | UI shell, Tailwind | ✅ | ✅ | PRODUCTION | 3 | LOW | 3 | No tokens central |
| **reports** | Dashboards, builder | ✅ | ✅ | PRODUCTION | 3 | HIGH | 4 | dashboard_detail 5300 LOC JS |
| **stock** | Movimientos, inventario | ✅ | ✅ | PRODUCTION | 3.5 | HIGH | 3 | MOBILE conteo |
| **ecom** | Mayorista B2B, hub | ✅ | ✅ | PRODUCTION | 3 | HIGH | 4 | 60+ APIs |
| **ventas** | Objetivos, presupuestos | ⚠️ | ⚠️ | PILOT | 2 | HIGH | 1 | **Excluded UI canon** |
| **mpr** | Producción OPT | ❌ | ✅ | PRODUCTION | 3.5 | HIGH | 4 | **Canon UI**; 109 tpl |
| **self_checkout** | TPV kiosco | ⚠️ | ✅ | PRODUCTION | 3.5 | HIGH | 3 | Touch-first |
| **compras** | Remitos compra | ⚠️ | ⚠️ | PILOT | 2.5 | HIGH | 2 | Limited surface |
| **factura_compra_captura** | OCR expediente | ⚠️ | ⚠️ | PILOT | 2.5 | MEDIUM | 3 | **IDOR gap V2** |
| **factura_compra_posting** | Posting stub | — | — | INCOMPLETE | 2 | LOW | — | Fake backend default |
| **contabilidad_audit** | Auditoría contable | ✅ | ❌ | PILOT | 3 | MEDIUM | 3 | CLIENT-A critical |
| **fe_afip** | Factura electrónica | ⚠️ | ✅ | PRODUCTION | 3 | HIGH | 2 | Fiscal critical |
| **logistica** | Entregas | ⚠️ | ⚠️ | PILOT | 2.5 | HIGH | 2 | Shared MySQL w/ reports |
| **tiendanube_administranet** | TN sync | ❌ | ✅ | PRODUCTION | 3 | HIGH | 3 | Outbox pattern |
| **legacy_db** | MySQL write layer | ✅ | ✅ | PRODUCTION | 2.5 | **CRITICAL** | — | Transition boundary |
| **odoo_migracion** | Odoo 19 sync | ❌ | ⚠️ | DEVELOPMENT | 2 | MEDIUM | 2 | CLIENT-B only |
| **ia** | AI assistants | ⚠️ | ⚠️ | PILOT | 3 | LOW | 3 | PolicyGate |
| **legacy_db/scripts** | One-off scripts | — | — | DEVELOPMENT | 1 | HIGH | — | Not product |

**Apps comentadas (DEAD en repo):** mercadopago, finance, logistics, tiendanube (old), sales, inventory, accounting, purchases, celery.

---

## Technical maturity detail (selected)

| Module | Arch | Test | Security | Obs | Maint | Data | UI | Docs |
|--------|:----:|:----:|:--------:|:---:|:-----:|:----:|:--:|:----:|
| core | 3 | 4 | 3 | 2 | 3 | 3 | 3 | 4 |
| ecom | 3 | 3 | 3 | 2 | 3 | 3 | 4 | 4 |
| mpr | 3 | 3 | 3 | 2 | 3 | 4 | 4 | 5 |
| reports | 2 | 3 | 3 | 2 | 2 | 3 | 4 | 4 |
| self_checkout | 3 | 3 | 4 | 2 | 3 | 4 | 3 | 4 |
| ventas | 2 | 2 | 3 | 1 | 2 | 3 | 1 | 2 |
| factura_compra_captura | 2 | 2 | **2** | 1 | 2 | 3 | 3 | 3 |

---

## Clasificación agregada

| Functional state | Count | Modules |
|------------------|------:|---------|
| PRODUCTION | 9 | core, login, reports, stock, ecom, mpr*, sc*, fe_afip*, TN*, legacy_db |
| PILOT | 6 | ventas, compras, captura, contab_audit, logistica, ia |
| DEVELOPMENT | 2 | dashboard, odoo_migracion |
| INCOMPLETE | 1 | factura_compra_posting |
| DEAD (commented) | 8+ | mercadopago, finance, etc. |

\* uso varía por cliente — ver matriz Client A/B.

---

## Principio aplicado

> Production ≠ technically good  
> Development ≠ bad

Ejemplo: **ventas** está en PILOT/PRODUCTION parcial pero technical score bajo (UI excluded canon).  
**legacy_db** es PRODUCTION-critical pero architectural debt máximo.

---

*Evidence: `INSTALLED_APPS`, `03-CLIENT-INSTALLATION-MATRIX.md`, AUDIT-V3 UIUX/PRODUCT*
