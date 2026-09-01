# 13 — Migration Acceptance Criteria

**Estado:** COMPLETE

---

## Estados de readiness por capability

| State | Criteria |
|-------|----------|
| **READY FOR INTERNAL QA** | Characterization tests pass; perm enforced backend; happy path manual QA |
| **READY FOR STAGING** | + parity matrix row complete; visual baseline; integration smoke |
| **READY FOR CUSTOMER PILOT** | + client config migrated; rollback tested; support runbook |
| **READY FOR PRODUCTION** | + customer sign-off; monitoring; 2-week parallel run optional |
| **READY TO RETIRE V1** | + zero v1 traffic 30d; all artifacts validated; decommission approved |

---

## Checklist per capability (minimum)

### All production capabilities

- [ ] Usage mapped (which client, frequency)
- [ ] V1 behavior documented (WF catalog reference)
- [ ] Characterization test suite green
- [ ] Permission test (authorized + unauthorized)
- [ ] API contract test (if API exists)
- [ ] Data behavior test (SoR fields)
- [ ] Artifact test (PDF/XLSX/ticket if applicable)
- [ ] Integration test (if external system)
- [ ] UI workflow test (critical path)
- [ ] Rollback procedure documented

### Financial / fiscal capabilities (AFIP, pedidos crédito)

- [ ] + dry-run mode
- [ ] + audit trail with operation_id
- [ ] + idempotency on writes

### Stock / production capabilities

- [ ] + concurrent write test
- [ ] + compensation path documented

---

## v1 retirement gate (per client)

Ningún componente v1 se retira hasta:

| # | Requirement |
|---|-------------|
| 1 | Usage mapped — zero critical workflows solo en v1 |
| 2 | Functional parity demonstrated (matrix 12) |
| 3 | Data migration validated (if PG schema change) |
| 4 | Permissions validated per role matrix |
| 5 | Artifacts validated (format, content spot-check) |
| 6 | Integrations validated (AFIP, TN, etc.) |
| 7 | **Customer sign-off** written |
| 8 | Rollback plan tested (< 4h RTO target) |
| 9 | 30-day hypercare period defined |

---

## Testing requirements by capability type

| Type | Required tests |
|------|----------------|
| CRUD screen | Char + perm + API contract |
| Workflow multi-step | Char + UI workflow + state machine |
| Report/dashboard | Char + data snapshot + export hash |
| Integration | Contract + retry + idempotency |
| Mobile | Char + responsive + offline behavior |
| Fiscal | Char + AFIP sandbox + audit |

---

## Critical workflows (must protect before any v2 pilot)

From `AUDIT-V3/PRODUCT/03-WORKFLOW-CATALOG.md`:

| WF | Priority | Reason |
|----|:--------:|--------|
| WF-01 Login | P0 | All access |
| WF-02 Pedido mayorista | P0 | Revenue |
| WF-06 TPV venta | P0 | Revenue + stock |
| WF-04 MPR OPT | P0 | Production CLIENT-B |
| WF-07 Reports | P0 | Management decisions |
| WF-03 Pedido masivo | P1 | Daily ops both |
| WF-08 Inventario | P1 | Stock accuracy |
| WF-05 Parte operario | P1 | Production data |
| WF-09 Auditoría contable | P1 | CLIENT-A compliance |
| WF-10 TN sync | P2 | CLIENT-B catalog |

---

*Cross-ref: `AUDIT-V3/TARGET/06-IMPLEMENTATION-READINESS.md`*
