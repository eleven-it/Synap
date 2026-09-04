# Kickoff Synap v2 — Fase 0

**Fecha:** 02/09/2026

## Decisiones cerradas

| # | Decisión | Valor |
|---|----------|-------|
| 1 | Repo | Nuevo `Synap-v2` (Option B) |
| 2 | Auth | Session cookie same-site (ADR-003) |
| 3 | UI | Vite + React + shadcn (ADR-002) |
| 4 | Sync v1 | V1 Change Ledger obligatorio |

## Baseline v1

| Campo | Valor |
|-------|-------|
| SHA `origin/Staging` | `aec7dbb36bccd9d6de2434e1d1be345949a6bf2a` |
| Mensaje | `Merge origin/Staging con fix desglose CC` |
| Tag pendiente | `v1-kickoff-v2` (requiere push con write a `eleven-it/Synap`) |

## Artefactos creados este kickoff

| Artefacto | Ubicación |
|-----------|-----------|
| Scaffold repo v2 | `../Synap-v2/` (local) |
| Ledger canónico | `Synap-v2/docs/migration/V1_CHANGE_LEDGER.md` |
| ADRs 001–003 | `Synap-v2/docs/adr/` |
| Checklist PR v1 | `Synap/.github/PULL_REQUEST_TEMPLATE.md` |
| Espejo proceso | `AUDIT-V3.5/20-V1-CHANGE-LEDGER.md` |

## Bloqueadores (acción humana org)

1. **Permiso GitHub:** la cuenta actual tiene `READ` en `eleven-it/Synap` — no puede crear `eleven-it/Synap-v2` ni pushear el tag.
2. Un admin con **write/admin** debe:
   - Crear repo vacío `eleven-it/Synap-v2` (private)
   - Añadir remote y push de `develop` / `staging` / `main`
   - Activar branch protection
   - `git tag v1-kickoff-v2 aec7dbb3 && git push origin v1-kickoff-v2` desde Staging

## Siguiente (Fase 0 restante / Fase 1)

- [ ] Push remoto Synap-v2
- [ ] Docker Compose DEV (PG + Redis + app stub)
- [ ] CI GitHub Actions (lint/test stub)
- [ ] Scaffold Django `backend/` + `ExecutionContext` (Fase 1)
