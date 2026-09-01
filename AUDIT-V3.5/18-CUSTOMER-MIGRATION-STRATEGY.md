# 18 — Customer Migration Strategy

**Estado:** COMPLETE | **NO big-bang** — incremental por cliente y capability

---

## Principios

1. **Clientes migran independientemente** — no simultáneo obligatorio
2. **Capability-by-capability** dentro de cada cliente cuando sea viable
3. **v1 operativo** hasta sign-off explícito
4. **Rollback < 4h** en todo momento durante pilot
5. **Parallel validation** — mismo dato ERP, dos UIs opcionales

---

## Estrategia por cliente (propuesta)

### CLIENT-B (Best Sox) — Pilot candidate #1

**Rationale:** Mayor superficie funcional (MPR, TPV); valida más capabilities; equipo conoce flujos producción.

```text
CLIENT-B v1 (Staging runtime)
        │
        ▼
v2 STAGING pilot (subdomain v2.best...)
        │
        ├── Parallel: pedidos + reports (MUST HAVE)
        ├── Parallel: stock + MPR (SHOULD HAVE)
        └── Parallel: TPV (SHOULD — highest risk)
        │
        ▼
Cutover por capability (toggle routing)
        │
        ▼
Full cutover CLIENT-B
        │
        ▼
30d hypercare → v1 maintenance read-only → retire v1-B
```

### CLIENT-A (DABRA) — Pilot candidate #2

**Rationale:** Menor superficie MPR; crítico contab audit + DABRA report extension.

```text
CLIENT-A v1
        │
        ▼
v2 pilot: pedidos + reports + DABRA extension
        │
        ▼
Add: contab audit (SHOULD)
        │
        ▼
Cutover CLIENT-A
```

**Order:** CLIENT-B first (broader test), CLIENT-A second (validates extension model).

---

## Estrategias evaluadas

| Strategy | Viable? | Verdict |
|----------|:-------:|---------|
| **Big bang** | ❌ | Rechazada — 2 clientes críticos, ERP shared |
| **Module-by-module** | ⚠️ | Parcial — modules share MySQL writes |
| **Capability-by-capability** | ✅ | **Preferida** — routing per workflow |
| **Customer-by-customer** | ✅ | **Preferida** — independent timelines |
| **Screen-by-screen** | ⚠️ | Sub-tactic within capability |

### Capability migration pattern

```text
1. Characterization tests v1
2. Implement v2 capability behind feature flag
3. Internal QA → Staging
4. Pilot: parallel run (same users, optional v2 URL)
5. Compare outputs (orders, stock, reports)
6. Enable v2 routing for capability
7. Monitor 2 weeks
8. Retire v1 capability route
```

---

## Rollback plan

| Trigger | Action | RTO target |
|---------|--------|:----------:|
| Data corruption detected | Disable v2 routing flag; v1 primary | < 1h |
| Critical workflow broken | Per-capability rollback | < 2h |
| Full pilot failure | DNS/routing back to v1 | < 4h |
| AFIP/fiscal error | Immediate v1 for fiscal capabilities | < 1h |

| Requirement | Detail |
|-------------|--------|
| Rollback artifact | Tagged v1 maintenance deploy ready |
| DB rollback | v2 PG separate — drop v2 writes only |
| MySQL | operation_id audit to identify v2 writes |
| Communication | Customer + ops runbook |

---

## Shared ERP risk mitigation

| Risk | Mitigation |
|------|------------|
| Dual write same table | Ownership contract; idempotency keys |
| v2 write v1 doesn't see | Eventual consistency + reconciliation job |
| Schema change | Only via legacy_mysql_schema catalog — both versions |

---

## Migration timeline (conceptual phases)

| Phase | Duration (indicative) | Deliverable |
|-------|----------------------|-------------|
| 0. Baseline approval | 2w | V3.5 approved |
| 1. v2 foundation | 8-12w | Repo, shell, auth, perms |
| 2. R1 MUST capabilities | 12-16w | Pedidos, stock, reports |
| 3. CLIENT-B pilot | 4-8w | Parallel validation |
| 4. R1 SHOULD capabilities | 8-12w | MPR, TPV |
| 5. CLIENT-A pilot | 4-6w | + audit, DABRA ext |
| 6. Full cutovers | 4w each | Sign-off |
| 7. v1 retirement | 3mo hypercare | Decommission |

*Durations indicative — require team sizing.*

---

## Per-capability migration priority

| Order | Capability | Client |
|:-----:|------------|--------|
| 1 | Login + shell | A+B |
| 2 | Reports execute | A+B |
| 3 | Stock consult | A+B |
| 4 | Sales order + hub | A+B |
| 5 | Pedido masivo | A+B |
| 6 | Stock movement | A+B |
| 7 | MPR OPT | B |
| 8 | Parte operario | B |
| 9 | TPV | B |
| 10 | Contab audit | A |
| 11 | DABRA report ext | A |
| 12 | Best monthly ext | B |
| 13 | AFIP | B |
| 14 | TN sync | B (LATER) |

---

*Cross-ref: `13-MIGRATION-ACCEPTANCE-CRITERIA.md`, `14-V2-RELEASE-1-SCOPE.md`*
