# 17 — V1 / V2 Backport Policy

**Estado:** COMPLETE — actualizado 02/09/2026  
**Complemento obligatorio:** [`20-V1-CHANGE-LEDGER.md`](./20-V1-CHANGE-LEDGER.md) (forward-port / contemplar cambios v1)

> **v1 no está congelado al 100%.** Puede recibir actualizaciones pequeñas (bugs, hotfixes, ajustes operativos).  
> **Toda** actualización post-kickoff v2 **debe** entrar al V1 Change Ledger.

---

## Clasificación de cambios

| Type | v1 action | v2 action | Cross-port |
|------|-----------|-----------|:----------:|
| **SECURITY FIX** | ✅ Apply immediately | ✅ Apply (ledger APPLY NOW) | v1→v2 **YES** |
| **DATA CORRUPTION FIX** | ✅ Apply immediately | ✅ Apply (ledger APPLY NOW) | v1→v2 **YES** |
| **CRITICAL BUSINESS FIX** | ✅ Apply (customer down) | Ledger EVALUATE → ticket | v1→v2 **YES eval** |
| **FUNCTIONAL FIX** | ✅ Permitido (pequeño) | Ledger → APPLY WHEN PORT READY | v1→v2 **track** |
| **UX FIX** | ⚠️ Solo si bloquea operación | **N/A** (UI v2 = shadcn) | v2→v1 **NO** |
| **NEW FEATURE** | ⚠️ Evitar; si inevitable → ledger + product | Preferir v2 only | Ledger **DEFER/APPLY** |
| **ARCHITECTURAL CHANGE** | ❌ **NO** en v1 | ✅ v2 only | v2→v1 **NEVER** |
| **PERFORMANCE** | ⚠️ Si bloquea ops | Evaluar + ledger | Case by case |
| **REFACTOR** | ❌ NO en v1 | ✅ v2 only | — |
| **DOCS** | ✅ v1 ok | N/A o espejo | Independent |
| **SCHEMA / MYSQL DDL** | ✅ vía catalog | Ledger **APPLY NOW** adapter | v1→v2 **YES** |

---

## Direction rules

### v1 → v2 (forward-port — vía Ledger)

| When | Action |
|------|--------|
| **Cualquier merge post-kickoff** | Fila en V1 Change Ledger + decisión |
| Security vulnerability in shared code pattern | Port fix to v2 **APPLY NOW** |
| Business rule discovery | Document + implement in v2; ticket ligado a Port |
| Customer reports v1-only bug | Fix v1; ledger; ticket v2 si capability en scope |
| Data fix / schema | Shared MySQL + documentar adapter v2 |
| UX-only v1 | Ledger **N/A** (no portar templates) |

### v2 → v1

| When | Action |
|------|--------|
| Architectural improvement | **NEVER** backport |
| New UI component | **NEVER** backport |
| Port/Adapter pattern | **NEVER** backport |
| Security fix found in v2 that also affects v1 code | **YES** — cherry-pick minimal fix to maintenance |
| Bug fix in business logic ported from v1 | Only if v1 still running same capability |

---

## Decision flowchart

```text
Change requested
    │
    ├─ Security/Data corruption? ──YES──► Fix v1 + v2
    │
    ├─ Architectural? ──YES──► v2 only
    │
    ├─ New feature? ──YES──► v2 only
    │
    ├─ v1 customer blocked? ──YES──► Fix v1 maintenance
    │                                    └─► Ticket v2 if in scope
    │
    └─ UX only? ──► v2 only (v1 cosmetic only if embarrassing)
```

---

## Cherry-pick rules (v1 maintenance branch)

| Rule | Detail |
|------|--------|
| Minimal diff | Only security/critical business |
| No refactor | No "while we're here" |
| Test on Staging v1 | Before customer deploy |
| Document in changelog | Both v1 and v2 trackers |
| Tag v1 releases | `v1.x.y` semver on maintenance |

---

## No-contamination examples

| Change | v1 | v2 |
|--------|----|----|
| Introduce ExecutionContext | ❌ | ✅ |
| Extract InventoryPort | ❌ | ✅ |
| Design System tokens | ❌ | ✅ |
| Fix IDOR captura | ✅ (security) | ✅ when porting captura |
| Fix pedido masivo Excel bug | ✅ | ✅ when porting WF-03 |
| Unify ConfirmDialog | ❌ | ✅ |

---

*Cross-ref: `02-V1-V2-COEXISTENCE-MODEL.md`*
