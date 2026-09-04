# Auditoría V3.5 — Synap v2 Product Baseline

**Inicio:** 26/08/2026  
**Modo:** READ ONLY (análisis; sin crear repos, branches ni refactor)  
**Precedentes:** `AUDIT/`, `AUDIT-V2/`, `AUDIT-V3/`

---

## Pregunta central

> ¿Qué es exactamente **Synap v2 Release 1** y cómo construirlo en paralelo a Synap v1 sin perder funcionalidad existente?

---

## Estado de documentos

| # | Documento | Estado |
|---|-----------|--------|
| 01 | [VERSION-AND-RELEASE-TOPOLOGY](./01-VERSION-AND-RELEASE-TOPOLOGY.md) | **COMPLETE** |
| 02 | [V1-V2-COEXISTENCE-MODEL](./02-V1-V2-COEXISTENCE-MODEL.md) | **COMPLETE** |
| 03 | [CLIENT-INSTALLATION-MATRIX](./03-CLIENT-INSTALLATION-MATRIX.md) | **COMPLETE** |
| 04 | [CLIENT-VARIABILITY-MAP](./04-CLIENT-VARIABILITY-MAP.md) | **COMPLETE** |
| 05 | [MODULE-MATURITY-MATRIX](./05-MODULE-MATURITY-MATRIX.md) | **COMPLETE** |
| 06 | [CAPABILITY-MATURITY-MATRIX](./06-CAPABILITY-MATURITY-MATRIX.md) | **COMPLETE** |
| 07 | [CUSTOMIZATION-INVENTORY](./07-CUSTOMIZATION-INVENTORY.md) | **COMPLETE** |
| 08 | [PERMISSION-INVENTORY](./08-PERMISSION-INVENTORY.md) | **COMPLETE** |
| 09 | [PERMISSION-CAPABILITY-MATRIX](./09-PERMISSION-CAPABILITY-MATRIX.md) | **COMPLETE** |
| 10 | [ROLE-MATRIX](./10-ROLE-MATRIX.md) | **COMPLETE** |
| 11 | [FEATURE-FLAG-CONFIGURATION-MAP](./11-FEATURE-FLAG-CONFIGURATION-MAP.md) | **COMPLETE** |
| 12 | [V1-V2-FUNCTIONAL-PARITY-MATRIX](./12-V1-V2-FUNCTIONAL-PARITY-MATRIX.md) | **COMPLETE** |
| 13 | [MIGRATION-ACCEPTANCE-CRITERIA](./13-MIGRATION-ACCEPTANCE-CRITERIA.md) | **COMPLETE** |
| 14 | [V2-RELEASE-1-SCOPE](./14-V2-RELEASE-1-SCOPE.md) | **COMPLETE** |
| 15 | [V2-REPOSITORY-STRATEGY](./15-V2-REPOSITORY-STRATEGY.md) | **COMPLETE** |
| 16 | [V2-ENVIRONMENT-TOPOLOGY](./16-V2-ENVIRONMENT-TOPOLOGY.md) | **COMPLETE** |
| 17 | [V1-V2-BACKPORT-POLICY](./17-V1-V2-BACKPORT-POLICY.md) | **COMPLETE** |
| 18 | [CUSTOMER-MIGRATION-STRATEGY](./18-CUSTOMER-MIGRATION-STRATEGY.md) | **COMPLETE** |
| 19 | [SYNAP-V2-SOLUTION-ARCHITECTURE-PLAN](./19-SYNAP-V2-SOLUTION-ARCHITECTURE-PLAN.md) | **COMPLETE — APROBADO** |
| 20 | [V1-CHANGE-LEDGER](./20-V1-CHANGE-LEDGER.md) | **ACTIVE PROCESS** |
| 21 | [V2-KICKOFF-STATUS](./21-V2-KICKOFF-STATUS.md) | **IN PROGRESS** |
| — | [SYNAP-V2-PRODUCT-BASELINE](./SYNAP-V2-PRODUCT-BASELINE.md) | **COMPLETE — REQUIERE APROBACIÓN** |

---

## Hallazgos ejecutivos

| Tema | Conclusión |
|------|------------|
| **Repos actuales** | **Un solo repo** (`eleven-it/Synap`); ramas Desarrollo / Staging / Produccion — **no** tres repos |
| **Rol real de Staging** | **Customer Production Runtime** para clientes actuales (evidencia operativa + divergencia 678 commits vs Produccion) |
| **Clientes** | **CLIENT-A (DABRA)** + **CLIENT-B (Best Sox)** — un codebase, deployments distintos |
| **Variabilidad** | Mayormente config/DB; código client-specific acotado (DABRA report, BEST migration) |
| **Repo v2 recomendado** | **Option B:** repo nuevo `Synap-v2` con branches develop/staging/main — **no** replicar 3 repos |
| **v2 R1 scope** | Capacidades compartidas críticas + arquitectura nueva; **no** todo v1 |
| **Sync v1→v2** | **V1 Change Ledger** obligatorio post-kickoff — v1 sigue con updates pequeñas |
| **UI v2** | shadcn + sidebar vertical; backend API-first primero |

---

## Punto de entrada

1. [`19-SYNAP-V2-SOLUTION-ARCHITECTURE-PLAN.md`](./19-SYNAP-V2-SOLUTION-ARCHITECTURE-PLAN.md)
2. [`20-V1-CHANGE-LEDGER.md`](./20-V1-CHANGE-LEDGER.md)
3. [`SYNAP-V2-PRODUCT-BASELINE.md`](./SYNAP-V2-PRODUCT-BASELINE.md)
4. [`15-V2-REPOSITORY-STRATEGY.md`](./15-V2-REPOSITORY-STRATEGY.md)

---

## Stop condition

**NO** crear Synap-v2, branches, Foundation ni refactor hasta aprobación humana.

*Auditoría V3.5 — READ ONLY — 26/08/2026*
