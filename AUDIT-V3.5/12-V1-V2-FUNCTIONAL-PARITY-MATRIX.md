# 12 — V1 → V2 Functional Parity Matrix

**Estado:** COMPLETE

**Definición migrado:** NO basta pantalla v2 — requiere parity según columnas marcadas ✅.

---

| Capability | V1 function | Client usage | Required v2? | V2 target | Perm parity | Data parity | Workflow | Artifact | Integration | UX change OK? | Status |
|------------|-------------|--------------|:------------:|-----------|:-----------:|:-----------:|:--------:|:--------:|:-------------:|:-------------:|--------|
| Login | session + empresa | A+B CRITICAL | ✅ | OIDC-ready Principal | ✅ | ✅ | ✅ | — | AN auth | RESTYLE | NOT STARTED |
| Sales order | mayorista checkout | A+B CRITICAL | ✅ | Port SalesOrderPort | ✅ | ✅ | ✅ | PDF | MySQL | RESTYLE | NOT STARTED |
| Pedido masivo | Excel import | A+B HIGH | ✅ | Same flow + DS | ✅ | ✅ | ✅ | XLSX | MySQL | RESTYLE | NOT STARTED |
| Hub kanban | estado pipeline | A+B CRITICAL | ✅ | Same states | ✅ | ✅ | ✅ | — | MySQL+PG | RESTYLE | NOT STARTED |
| Stock move | alta movimiento | A+B CRITICAL | ✅ | InventoryPort | ✅ | ✅ | ✅ | PDF | MySQL | RESTYLE | NOT STARTED |
| Stock consult | consultas | A+B HIGH | ✅ | Read port | ✅ | ✅ | ✅ | — | MySQL | RESTYLE | NOT STARTED |
| Inventory count | QR mobile | B HIGH, A MED | ✅ | Mobile pattern | ✅ | ✅ | ✅ | — | MySQL | REUSE mobile | NOT STARTED |
| MPR OPT | wizard 4-step | B CRITICAL | ✅ SHOULD | ProductionPort | ✅ | ✅ | ✅ | PDF | MySQL | RESTYLE | NOT STARTED |
| Parte operario | mobile form | B CRITICAL | ✅ SHOULD | Same | ✅ | ✅ | ✅ | — | MySQL | REUSE | NOT STARTED |
| TPV sale | kiosco flow | B CRITICAL | ✅ SHOULD | PointOfSalePort | ✅ | ✅ | ✅ | ticket | MySQL | REUSE touch | NOT STARTED |
| Reports execute | dashboard widgets | A+B CRITICAL | ✅ | semantic-v2 path | ✅ | ✅ read | ✅ | XLSX | MySQL | RESTYLE | NOT STARTED |
| DABRA report | consolidado remitos | A CRITICAL | ✅ EXT | Extension + config | ✅ | ✅ | ✅ | export | MySQL | RESTYLE | NOT STARTED |
| Best monthly pack | licenciatarios XLSX | B CRITICAL | ✅ EXT | Template pack | ✅ | ✅ | ✅ | XLSX | MySQL | RESTYLE | NOT STARTED |
| Contab audit | run/apply checks | A CRITICAL | ✅ SHOULD | AccountingPort read | ✅ | ✅ | ✅ dry-run | CSV/XLSX | MySQL | RESTYLE | NOT STARTED |
| AFIP FE | emit invoice | B CRITICAL | ✅ SHOULD | TaxPort | ✅ | ✅ | ✅ | XML/CAE | AFIP | RESTYLE | NOT STARTED |
| TN sync | catalog/orders | B HIGH | LATER | EcommercePort | ✅ | ✅ | ✅ | webhook | TN API | — | DEFERRED |
| BEST migration | Azure→MPR | B HIGH | LATER | Migration tool | — | — | ✅ | — | Azure | — | DEFERRED |
| Captura OCR | upload/review | A+B MED | LATER | DocumentCapturePort | ✅ fix IDOR | ✅ | ✅ | PDF | PG+FS | REDESIGN | DEFERRED |
| Objectives/budgets | ventas module | A+B LOW | LATER | Rewrite | ✅ | ✅ | ⚠️ | — | MySQL | REDESIGN | DEFERRED |
| IA assistant | chat tools | A+B LOW | LATER | PolicyGate | ✅ | ✅ | ✅ | — | PG | RESTYLE | DEFERRED |
| Odoo migration | sync jobs | B MED | LATER | Integration | — | — | — | — | Odoo | — | DEFERRED |

---

## Parity dimensions explained

| Dimension | Criterion |
|-----------|-----------|
| **Functional** | Same business outcome (order created, stock moved, etc.) |
| **Permission** | Equivalent or stricter auth; no UI-only security |
| **Data** | Same SoR fields written; no silent schema change |
| **Workflow** | Same steps/decisions (approval thresholds configurable) |
| **Artifact** | Same output formats where operationally required |
| **Integration** | Same external contracts (AFIP, TN, etc.) |

---

## UX changes allowed in v2

| Allowed | Not allowed without parity test |
|---------|--------------------------------|
| Visual restyle (canon DS) | Remove approval step |
| Breadcrumbs added | Change order states |
| Unified confirm dialogs | Skip stock validation |
| Density preserved/improved | Drop Excel import columns |
| Keyboard shortcuts added | Change fiscal emission flow |

---

*Cross-ref: `06-CAPABILITY-MATURITY-MATRIX.md`, `13-MIGRATION-ACCEPTANCE-CRITERIA.md`*
