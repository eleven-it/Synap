# 13 — Legacy Extraction Seams

**Estado:** COMPLETE  
**Fecha:** 25/08/2026

---

## Seam ranking (viability × impact)

| # | Seam | Viability | Impact | Complexity |
|---|------|:---------:|:------:|:----------:|
| 1 | InventoryPort wrapping `administranet_stock.py` | HIGH | CRITICAL | HIGH |
| 2 | CompanyContextPort formalizing session | HIGH | CRITICAL | LOW |
| 3 | ReportDataSourcePort wrapping SqlQueryBuilder | HIGH | HIGH | MEDIUM |
| 4 | CustomerPort wrapping `cliente_rapido_escritura.py` | MEDIUM | HIGH | MEDIUM |
| 5 | SalesOrderPort wrapping checkout services | MEDIUM | HIGH | HIGH |
| 6 | AuthorizationPort + synap cutover | MEDIUM | HIGH | MEDIUM |
| 7 | AccountingPort wrapping legacy_db | LOW | CRITICAL | VERY HIGH |
| 8 | IdentityPort (decouple login) | LOW | CRITICAL | VERY HIGH |

---

## SEAM-01: Inventory

| Campo | Valor |
|-------|-------|
| **Current coupling** | mpr, ecom, sc, stock import `administranet_stock` or duplicate SQL |
| **Potential seam** | `InventoryPort` interface in `synap/ports/inventory.py` |
| **Affected code** | `core/services/administranet_stock.py`, `mpr/services.py` stock sections |
| **Business capability** | Stock availability, movements, reservations |
| **Tables** | stock, stock_deposito, stockp, movimiento_stock |
| **Risk** | Regression en checkout y producción |
| **Tests required** | Integration tests per movement type |
| **Migration** | 1) Extract interface 2) AN adapter wraps existing 3) Redirect callers incrementally |
| **Complexity** | HIGH — 44+ write paths in stock service alone |

---

## SEAM-02: CompanyContext

| Campo | Valor |
|-------|-------|
| **Current coupling** | `base_empresa` scattered in session, pool, reports filters |
| **Potential seam** | `CompanyContextPort.get_erp_database()` + `get_synap_empresa_id()` |
| **Affected** | mysql_pool, all services, factura_compra session_empresa |
| **Risk** | LOW if interface thin |
| **Complexity** | LOW — refactor localizado |

---

## SEAM-03: Reports DataSource

| Campo | Valor |
|-------|-------|
| **Current coupling** | SqlQueryBuilder knows MySQL table names |
| **Potential seam** | `ReportDataSourcePort` — `AdministraNETDataSource` implements |
| **Affected** | execution_engine.py, semantic_service.py, query_runner.py |
| **Risk** | MEDIUM — analytics only |
| **Complexity** | MEDIUM |

---

## SEAM-04: Customer

| Campo | Valor |
|-------|-------|
| **Current** | `ecom/services/cliente_rapido_escritura.py` direct SQL |
| **Seam** | `CustomerPort` — single entry for ecom, sc, TN |
| **Tables** | cliente, cliente_domicilio |
| **Complexity** | MEDIUM |

---

## SEAM-05: Ecom checkout

| Campo | Valor |
|-------|-------|
| **Current** | `mayorista_checkout_service.py` writes comp_ped, stockp, stock_deposito in one flow |
| **Seam** | Orchestrator uses SalesOrderPort + InventoryPort |
| **Risk** | HIGH — transacción multi-tabla |
| **Complexity** | HIGH |

---

## SEAM-06: Permissions cutover

| Campo | Valor |
|-------|-------|
| **Current** | `SYNAP_PERMISOS_SOURCE=legacy` default |
| **Seam** | `AuthorizationPort` with legacy/synap adapters |
| **Migration** | dual → synap with feature flag per cliente |
| **Complexity** | MEDIUM |

---

## Anti-seams (NO cortar aquí primero)

| Area | Razón |
|------|-------|
| `cont_recalculo_service.py` | Reglas contables opacas; blast radius CRITICAL |
| `login/administranet_auth.py` | Sin IdentityPort no hay sistema |
| `mpr/services.py` monolith | 222 writes — necesita InventoryPort primero |

---

## Respuesta pregunta 26-27

| # | Pregunta | Respuesta |
|---|----------|-----------|
| 26 | ¿Dónde introducir Ports sin romper? | CompanyContextPort → ReportDataSourcePort → CustomerPort → InventoryPort (orden) |
| 27 | ¿Mejores seams? | SEAM-02 (context), SEAM-03 (reports), SEAM-01 (inventory) |

---

*Transition architecture en `14-TRANSITION-ARCHITECTURE.md`.*
