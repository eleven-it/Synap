# 17 — V1 / V2 Backport Policy

**Estado:** COMPLETE

---

## Clasificación de cambios

| Type | v1 action | v2 action | Cross-port |
|------|-----------|-----------|:----------:|
| **SECURITY FIX** | ✅ Apply immediately | ✅ Apply if exists | v1→v2 **YES** |
| **DATA CORRUPTION FIX** | ✅ Apply immediately | ✅ Apply if exists | v1→v2 **YES** |
| **CRITICAL BUSINESS FIX** | ✅ Apply (customer down) | ✅ Apply if capability exists | v1→v2 **EVALUATE** |
| **FUNCTIONAL FIX** | ✅ If customer uses v1 | ✅ If in scope | v1→v2 if same capability |
| **UX FIX** | ⚠️ Minimal hotfix only | ✅ Normal development | v2→v1 **NO** |
| **NEW FEATURE** | ❌ **NO** (v1 frozen) | ✅ v2 only | — |
| **ARCHITECTURAL CHANGE** | ❌ **NO** | ✅ v2 only | v2→v1 **NEVER** |
| **PERFORMANCE** | ⚠️ If blocking ops | ✅ v2 normal | Evaluate case by case |
| **REFACTOR** | ❌ NO | ✅ v2 only | — |
| **DOCS** | ⚠️ v1 maintenance docs only | ✅ v2 product docs | Independent |

---

## Direction rules

### v1 → v2

| When | Action |
|------|--------|
| Security vulnerability in shared code pattern | Port fix to v2 foundation immediately |
| Business rule discovery (bug was "working as designed" wrong) | Document + implement correctly in v2 |
| Customer reports v1-only bug in non-migrated capability | Fix v1; **create v2 ticket** if capability in R1 scope |
| Data fix script | Run on shared MySQL; document for v2 adapter |

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
