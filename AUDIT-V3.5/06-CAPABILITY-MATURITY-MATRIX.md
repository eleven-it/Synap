# 06 — Capability Maturity Matrix

**Estado:** COMPLETE | Capabilities ≠ módulos

---

## Scorecard maestro

| Capability | A | B | Functional | Technical | Criticality | Custom | V2 R1 | Migration Risk |
|------------|:-:|:-:|:----------:|:---------:|:-----------:|:------:|:-----:|:--------------:|
| Login / select empresa | ✅ | ✅ | PRODUCTION | 4 | CRITICAL | No | **MUST** | Low |
| Manage users/permissions | ✅ | ✅ | PRODUCTION | 3 | HIGH | No | **MUST** | Medium |
| Create sales order (mayorista) | ✅ | ✅ | PRODUCTION | 3 | CRITICAL | Config | **MUST** | High |
| Pedido masivo Excel | ✅ | ✅ | PRODUCTION | 3 | HIGH | No | **MUST** | Medium |
| Hub pedidos kanban | ✅ | ✅ | PRODUCTION | 3 | CRITICAL | No | **MUST** | High |
| Check / adjust stock | ✅ | ✅ | PRODUCTION | 3.5 | CRITICAL | No | **MUST** | High |
| Physical inventory count | ⚠️ | ✅ | PRODUCTION | 3 | HIGH | No | **SHOULD** | Medium |
| Production OPT wizard | ❌ | ✅ | PRODUCTION | 3.5 | CRITICAL | Policy | **SHOULD** | **High** |
| Operator production report | ❌ | ✅ | PRODUCTION | 3 | CRITICAL | Policy | **SHOULD** | High |
| TPV sale | ⚠️ | ✅ | PRODUCTION | 3.5 | CRITICAL | No | **SHOULD** | **High** |
| Execute report dashboard | ✅ | ✅ | PRODUCTION | 3 | CRITICAL | No | **MUST** | Medium |
| Design custom report | ⚠️ | ⚠️ | PILOT | 2.5 | MEDIUM | No | LATER | Medium |
| DABRA consolidado remitos | ✅ | ❌ | PRODUCTION | 2.5 | CRITICAL | **Yes** | EXTENSION | Medium |
| Monthly licenciatarios pack | ❌ | ✅ | PRODUCTION | 2.5 | CRITICAL | **Yes** | EXTENSION | Medium |
| Accounting audit | ✅ | ❌ | PILOT | 3 | CRITICAL | Pilot flag | **SHOULD** | Medium |
| Invoice capture OCR | ⚠️ | ⚠️ | PILOT | 2.5 | MEDIUM | No | LATER | Medium |
| Electronic invoice AFIP | ⚠️ | ✅ | PRODUCTION | 3 | CRITICAL | No | **SHOULD** | **High** |
| TN catalog/order sync | ❌ | ✅ | PRODUCTION | 3 | HIGH | No | LATER | High |
| BEST migration cutover | ❌ | ✅ | DEVELOPMENT | 2 | HIGH | **Yes** | LATER | High |
| Odoo migration | ❌ | ⚠️ | DEVELOPMENT | 2 | MEDIUM | No | LATER | Medium |
| AI assistant | ⚠️ | ⚠️ | PILOT | 3 | LOW | No | LATER | Low |
| Sales objectives/budgets | ⚠️ | ⚠️ | PILOT | 2 | MEDIUM | No | LATER | Low |
| Delivery logistics | ⚠️ | ⚠️ | PILOT | 2.5 | MEDIUM | No | LATER | Medium |

**A** = CLIENT-A (DABRA), **B** = CLIENT-B (Best Sox)

---

## V2 R1 classification summary

| Class | Count | Capabilities |
|-------|------:|--------------|
| **MUST HAVE** | 7 | Login, users, sales order, masivo, hub, stock, reports execute |
| **SHOULD HAVE** | 6 | Inventory, MPR, parte, TPV, contab audit, AFIP |
| **EXTENSION** | 2 | DABRA report, Best monthly pack |
| **LATER** | 8 | TN, BEST migr, Odoo, captura, objectives, logistics, AI, report design |

---

## Priorización (migration order sugerido)

1. Login + permissions + shell (foundation)
2. Reports execute (shared, high visibility)
3. Stock view/move (shared)
4. Sales order + hub (shared critical)
5. Pedido masivo (shared)
6. MPR + TPV (CLIENT-B) — parallel track
7. Contab audit (CLIENT-A) — parallel track
8. Client extensions (DABRA, Best templates)
9. Integrations (TN, AFIP) — adapter phase

---

*Cross-ref: `14-V2-RELEASE-1-SCOPE.md`, `12-V1-V2-FUNCTIONAL-PARITY-MATRIX.md`*
