# 15 — Architectural Invariants

**Estado:** COMPLETE — candidatas para `SYNAP-ARCHITECTURE-CONTRACT.md`  
**Fecha:** 25/08/2026

---

## Invariantes validadas contra arquitectura posible

| ID | Invariante | Validada | Notas |
|----|------------|:--------:|-------|
| INV-01 | Domain modules MUST NOT connect to MySQL except via Port or Adapter | ✓ | Hoy violado — target state |
| INV-02 | Domain modules MUST NOT import legacy table names in new code | ✓ | Hoy violado |
| INV-03 | Core MUST NOT contain domain business logic (stock, sales rules) | ✓ | Hoy violado — administranet_stock en core |
| INV-04 | Core MUST NOT depend on domain modules (ecom, mpr, reports) | ✓ | Hoy violado — 11 outbound imports |
| INV-05 | TenantContext MUST be explicit for tenant-scoped PG operations | ✓ | Hoy violado — IDOR captura |
| INV-06 | CompanyContext MUST be resolved once per request | ✓ | Parcial — session scattered |
| INV-07 | ERP writes MUST go through transactional Port | ✓ | Target — 587 direct writes today |
| INV-08 | Reports execution MUST use ReportDataSourcePort | ✓ | Target |
| INV-09 | Permissions MUST be checked at API boundary, not only UI | ✓ | Hoy parcial |
| INV-10 | Async jobs MUST carry CompanyContext | ✓ | Hoy violado — jobs sin context |
| INV-11 | Cache keys MUST include company/tenant scope | ✓ | Hoy parcial |
| INV-12 | Architectural Deviations MUST be documented | ✓ | New process |

---

## Invariantes rechazadas (no aplican hoy)

| Invariante propuesta | Por qué NO ahora |
|---------------------|------------------|
| "All data in PostgreSQL" | ERP SoR must stay MySQL medium-term |
| "No raw SQL anywhere" | Impractical for AN adapter phase 1 |
| "Single IdP Synap" | Requires product decision + migration |
| "Microservices per module" | Monolith modular is viable |

---

## Invariantes derivadas de seguridad

| ID | Regla |
|----|-------|
| SEC-INV-01 | API object-level authorization MUST match web views for same resource |
| SEC-INV-02 | No DEFAULT_BASE_EMPRESA for authenticated user requests |
| SEC-INV-03 | SQL dynamic execution MUST re-validate or use read-only DB role |
| SEC-INV-04 | Secrets MUST NOT have code defaults in production |

---

## Respuesta pregunta 29

> ¿Qué reglas deben volverse obligatorias?

Las 12 invariantes INV-01 a INV-12 + SEC-INV-01 a SEC-INV-04 — formalizadas en `SYNAP-ARCHITECTURE-CONTRACT.md`.

---

*Contrato normativo siguiente.*
