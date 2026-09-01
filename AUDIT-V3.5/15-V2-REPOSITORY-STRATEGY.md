# 15 — V2 Repository Strategy

**Estado:** COMPLETE | **RECOMENDACIÓN EXPLÍCITA**

---

## Situación actual (v1) — evaluada

| Aspecto | Realidad |
|---------|----------|
| Repos | **1 repo** (`eleven-it/Synap`) |
| "Development/Staging/Production" | **3 ramas**, no 3 repos |
| Source of truth desarrollo | Rama **Desarrollo** |
| Customer runtime | Rama **Staging** (678 commits ahead of Produccion) |
| Default remote branch | **Produccion** (stale) |
| Docs en Staging/Prod | **Removidos** en merge |
| Divergencia | Alta — merges irregulares |

### Option A — Tres repos v2 (replicar v1)

```text
Synap-v2-Development / Synap-v2-Staging / Synap-v2-Production
```

| Pros | Contras |
|------|---------|
| Familiar al equipo | **Replica el anti-pattern actual** |
| | 3× CI/CD, 3× drift risk |
| | No Single Source of Truth |
| | Hotfix/backport nightmare |
| | **RECHAZADA** |

---

### Option B — Un repo v2, branches por ambiente ✅ RECOMENDADA

```text
Synap-v2 (nuevo repo)
├── develop      → DEV v2
├── staging      → STAGING / PREPROD v2
├── main         → PRODUCTION v2
├── feature/*
├── release/*
└── hotfix/*
```

| Pros | Contras |
|------|---------|
| **Single Source of Truth** | Requiere disciplina merge |
| CODEBASE ≠ ENVIRONMENT | Migración mental del equipo |
| CI/CD estándar (GitFlow adaptado) | |
| Rollback = revert/tag en main | |
| Traceability con tags semver | |
| v1 repo separado = coexistence clean | |
| Docs **permanecen** en todas las ramas (v2 es product repo) | |

---

### Option C — Trunk-based + release tags

```text
main + feature flags + release/x.y.z tags
```

| Pros | Contras |
|------|---------|
| Simple, fast CI | Menos familiar para equipo actual |
| Good for continuous delivery | Staging/preprod = deploy de tag, no branch |
| | Requiere feature flags maduros |

**Veredicto:** Viable como evolución post-R1; **no** para arranque v2 con equipo actual.

---

### Option D — Monorepo v1+v2

```text
Synap/
├── v1/  (subtree o branch maintenance)
└── v2/  (new code)
```

| Pros | Contras |
|------|---------|
| Un clone | Contaminación risk |
| Shared tooling | Confusion CI/CD |
| | **RECHAZADA** — viola no-contamination |

---

## Recomendación final

### **Option B: Repo nuevo `Synap-v2` + GitFlow adaptado**

| Elemento | Decisión |
|----------|----------|
| v1 repo | `eleven-it/Synap` → renombrar conceptualmente a **Synap-v1**; rama `maintenance` desde snapshot Staging actual |
| v2 repo | `eleven-it/Synap-v2` (nuevo) |
| Default branch v2 | `develop` |
| Production branch v2 | `main` (protected) |
| Versioning | SemVer tags on `main`: `v2.0.0`, `v2.1.0` |
| Docs | **In repo** en v2 (product documentation) |
| `.env` | Never in repo; secrets in vault/CI |

---

## v1 maintenance post-split

```text
Synap (v1)
└── maintenance branch (from Staging snapshot @ cutover date)
    ├── hotfix/* → maintenance → deploy v1 customer runtime
    └── NO merges from v2
```

---

## Evaluation criteria scores

| Criterion | Option A | **Option B** | Option C |
|-----------|:--------:|:------------:|:--------:|
| Single Source of Truth | 1 | **5** | 4 |
| CI/CD simplicity | 2 | **4** | 5 |
| Rollback | 2 | **5** | 4 |
| Hotfix traceability | 2 | **4** | 3 |
| Environment parity | 2 | **5** | 4 |
| v1/v2 coexistence | 3 | **5** | 4 |
| Team familiarity | 4 | **4** | 2 |
| Customer safety | 3 | **5** | 4 |

---

## Principio reforzado

> **CODEBASE ≠ ENVIRONMENT**

Diferencias DEV/STAGING/PROD = config + secrets + infra + data + feature flags — **no** repos ni ramas divergentes con código distinto.

---

*NO crear repo hasta aprobación humana.*
