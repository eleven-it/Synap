# 04 — Port & Adapter Rules

**Estado:** COMPLETE | **Fecha:** 25/08/2026

## Dependency inversion (validated)

```text
Application / Domain Service
        │
        ▼
      Port (interface — synap/ports/)
        ▲
        │ implements
   Adapter (adapters/administranet/, adapters/odoo/)
        │
        ▼
   External System
```

**NEVER:** Domain → concrete adapter | Port → AdministraNET types | Core → Domain

## Port refinement (from V2 catalog)

| Port V2 | Verdict | Refinement |
|---------|---------|------------|
| CustomerPort | **KEEP** | Capability — OK |
| AccountsReceivablePort | **KEEP** | Distinct from Customer |
| ProductCatalogPort | **KEEP** | |
| InventoryPort | **KEEP** | Critical |
| SalesOrderPort | **KEEP** | |
| PointOfSalePort | **KEEP** | Separate from SalesOrder (resumen_venta_cv model) |
| AccountingPort | **KEEP** | Not splittable short-term |
| TaxPort | **MERGE** into TaxCompliancePort or part of Invoicing | Low write surface |
| PaymentsPort | **NEW** | CashManagement + MP/Clover |
| PurchasingPort | **NEW** | compras + captura posting |
| IdentityPort | **KEEP** | Auth boundary |
| AuthorizationPort | **KEEP** | Not Identity |
| CompanyContextPort | **KEEP** | Infrastructure Port |
| ReportDataSourcePort | **KEEP** | Analytics, not transactional |

**Not Ports:** Report builder UI orchestration → Application Service. Pedido hub kanban state → Application Service. OCR pipeline → Domain Service (Synap-native).

## Adapter registry (future)

```text
AdapterCapabilities: supports_inventory_reservation, supports_native_accounting, ...
```

Adapters declare capabilities; application checks before invoking.
