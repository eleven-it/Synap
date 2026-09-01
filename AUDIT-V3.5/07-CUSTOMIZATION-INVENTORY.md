# 07 — Customization Inventory

**Estado:** COMPLETE

---

| # | Customization | Type | Client | Evidence | V2 classification | Action |
|---|---------------|------|--------|----------|---------------------|--------|
| 1 | DABRA consolidado remitos report | CUSTOM CODE | A | `dabra_consolidado_remitos.py` | EXTENSION | Parametrize `customer_code` |
| 2 | CODIGO_CLIENTE=368 SQL | CUSTOM CODE | A | line 37 same file | CONFIGURE | Installation config |
| 3 | SYNAP_PILOTO_CONT flags | FEATURE FLAG | A | settings env | FEATURE FLAG | Formalize |
| 4 | migracion-best URL suite | CUSTOM CODE | B | `mpr/urls.py` | FEATURE FLAG | `best_migration.enabled` |
| 5 | `_MARCA_ALIAS` mapping | BUSINESS POLICY | B | `administranet_articulo.py` | BUSINESS POLICY | DB or policy table |
| 6 | `es_ped_migracion_best()` | BUSINESS POLICY | B | `pedidos_hub_pipeline.py` | BUSINESS POLICY | Order type enum |
| 7 | Monthly Reporting Best Sox XLSX | CUSTOM CODE | B | `monthly_reporting_*.py` | EXTENSION | Template pack ID |
| 8 | 1 docena = 12 pares | BUSINESS POLICY | B | `mpr/services_parte_movil.py` | BUSINESS POLICY | `MprEmpresaConfig` v2 |
| 9 | `configuracion_ecom` per base | CONFIG | A+B | `ecom_config_mysql.py` | CONFIGURE | ✅ keep |
| 10 | `MprEmpresaConfig` per base | CONFIG | B | `mpr/models.py` | CONFIGURE | ✅ keep |
| 11 | `ModuleConfig` per deployment | CONFIG | A+B | Postgres | CONFIGURE | ✅ keep → Installation |
| 12 | Report slug seeds differ | CONFIG | A+B | migrations/seeds | CONFIGURE | Installation manifest |
| 13 | `revertir_partes_fecha` base guard | LEGACY HACK | B | management command | REMOVE | Env-based guard |
| 14 | ventas objetivos/presupuestos UI | INCOMPLETE | A+B | ventas/templates | CANDIDATE REMOVAL | Rewrite or LATER |
| 15 | Templates `* 2.html` | ACCIDENTAL | — | self_checkout, reports | CANDIDATE REMOVAL | Verify + delete |
| 16 | Dual Tailwind CDN/build | TECH DEBT | — | theme | STANDARDIZE | Single build |
| 17 | Menu EN/ES mix | TECH DEBT | — | APPS_MENU | STANDARDIZE | Spanish canon |
| 18 | Default CLI `administranet89` | DEV CONVENIENCE | A | management commands | REMOVE | No hardcoded defaults |
| 19 | tmp_exports PV200 script | EXPERIMENTAL | A | `tmp_exports/` | CANDIDATE REMOVAL | Not in product |
| 20 | DABRA/VMM shared discount factor | SHARED CODE | A | `comprobante_descuento_cabecera.py` | PRODUCT FEATURE | Generalize |

---

## Resumen por clasificación v2

| Classification | Count |
|----------------|------:|
| CONFIGURE (keep) | 4 |
| FEATURE FLAG | 2 |
| BUSINESS POLICY | 4 |
| EXTENSION | 3 |
| PRODUCT FEATURE | 1 |
| STANDARDIZE | 3 |
| REMOVE / CANDIDATE REMOVAL | 5 |

---

## Regla

> Ninguna fila con CUSTOM CODE debe llegar a v2 dominio sin reclasificación.

---

*Evidence: `04-CLIENT-VARIABILITY-MAP.md`, codebase search*
