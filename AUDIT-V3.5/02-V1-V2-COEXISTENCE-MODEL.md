# 02 — V1 / V2 Coexistence Model

**Estado:** COMPLETE

---

## Modelo conceptual

```text
                    SYNAP v1 (repo Synap, rama maintenance)
                    │
                    ├── Customer Runtime (Staging snapshot)
                    │       ├── CLIENT-A (DABRA)
                    │       └── CLIENT-B (Best Sox)
                    │
                    ├── security fixes
                    ├── critical business fixes
                    ├── data corruption fixes
                    └── customer support (no new features)

                    SYNAP v2 (repo Synap-v2, nuevo)
                    │
                    ├── new architecture (Ports, ExecutionContext)
                    ├── new UI/UX + Design System
                    ├── standardized capabilities
                    ├── productized configuration (no client-specific code)
                    └── migration target

                    Transición futura (por cliente, por capability)
                    v1 installation ──pilot──► v2 installation ──cutover──► v1 retired
```

---

## Principios de coexistencia

| # | Principio | Detalle |
|---|-----------|---------|
| 1 | **Paralelismo** | v1 y v2 codebases separados; mismos datos ERP compartidos durante transición |
| 2 | **v1 congelado funcionalmente** | No nuevas features en v1 salvo excepciones backport policy |
| 3 | **v2 greenfield arquitectura** | No arrastrar deuda legacy como regla permanente |
| 4 | **Datos compartidos** | MySQL AdministraNET + PostgreSQL Synap — ambos leen/escriben con ownership contract (V3) |
| 5 | **Migración incremental** | Por capability y por cliente — no big-bang |
| 6 | **Rollback siempre posible** | v1 permanece operativo hasta sign-off cliente |

---

## Regla de no contaminación

> Las decisiones arquitectónicas de v2 (**Ports, ExecutionContext, semantic reports, permission model**) **NO** deben backportearse automáticamente a v1.

> Los fixes funcionales críticos de v1 **deben evaluarse** para aplicar en v2 si la capability ya existe o está planificada.

---

## Límites de responsabilidad

| Área | v1 | v2 |
|------|----|----|
| Nuevas pantallas | ❌ | ✅ |
| Refactor UI | ❌ (solo hotfix visual crítico) | ✅ |
| Ports/Adapters | ❌ | ✅ |
| Nuevos reportes slug-legacy | ❌ | ❌ (semantic-v2 only) |
| Security patches | ✅ ambos | ✅ |
| Integraciones nuevas | ❌ v1 | ✅ v2 |
| Permisos synap store cutover | ⚠️ v1 puede completar migración | ✅ modelo target |

---

## Shared infrastructure durante transición

| Recurso | Compartido | Riesgo | Mitigación |
|---------|:----------:|--------|------------|
| MySQL AdministraNET | ✅ | Escrituras duales v1+v2 | Ownership contract; operation_id |
| PostgreSQL Synap | ⚠️ Parcial | Schema drift | v2 DB separada o schema versionado |
| Redis | ⚠️ | Cache key collision | Prefix `v1:` / `v2:` |
| AFIP certs | ✅ | — | Adapter compartido o copia |
| Dominio / reverse proxy | ✅ | Routing | `/v2/` path o subdomain |

---

## Timeline conceptual (no fechas)

```text
Phase 0: V3.5 baseline approved
Phase 1: v2 repo + foundation + DS tokens
Phase 2: v2 R1 capabilities (piloto interno)
Phase 3: CLIENT-B pilot (mayor superficie MPR)
Phase 4: CLIENT-A pilot (ecom + reports)
Phase 5: Cutover por cliente
Phase 6: v1 maintenance mode → retirement
```

---

*Ver también: `17-V1-V2-BACKPORT-POLICY.md`, `18-CUSTOMER-MIGRATION-STRATEGY.md`*
