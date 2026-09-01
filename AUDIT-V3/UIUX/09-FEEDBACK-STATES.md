# 09 — Estados de Feedback

**Estado:** COMPLETE

| State | Implementation | Coverage |
|-------|----------------|----------|
| Loading | post-loading modal, spinners, skeleton rare | Partial |
| Success | SynapMessages toast, Django messages | Good |
| Warning | amber toasts, mprShowAviso | Partial |
| Error | red toasts, inline field errors | Partial |
| Empty | some tables have empty row message | **Gap** many screens |
| No permission | 403 pages, redirect login | OK |
| No data | filter returns 0 rows — varies | Inconsistent |
| Offline | `inv_fisico_offline.js` PWA stock | **Only stock** |
| Processing | post-loading modal | Forms only |
| Partial failure | batch operations — manual | **Gap** |

## Confirmaciones

| Mechanism | Usage | Policy |
|-----------|-------|--------|
| `window.alert/confirm` | residual — policy forbids new | **MUST NOT** per contract |
| `mprShowAviso` | MPR confirm | Canon partial |
| `synap_confirm_modal.html` | TN | Local |
| Inline modals | reports catalog delete | Ad-hoc |
| SynapMessages | info only, not confirm | Toast |

**Inconsistency:** 3+ confirm patterns — target unified ConfirmDialog component.
