# 16 — V2 Environment Topology

**Estado:** COMPLETE | Diseño conceptual — **no crear infraestructura**

---

## Topología objetivo

```text
Developer Local (Docker)
        │
        ▼
   DEV v2 (develop branch deploy)
        │
        ▼
 Integration / QA (automated + manual)
        │
        ▼
 STAGING / PREPRODUCTION v2 (staging branch)
        │
        ├── Customer Pilot A (optional dedicated)
        └── Customer Pilot B (optional dedicated)
        │
        ▼
 PRODUCTION v2 (main + semver tag)
        │
        ├── Installation: CLIENT-A
        └── Installation: CLIENT-B

Parallel during transition:
 STAGING v1 (maintenance) ──► Customer Runtime v1 (current)
```

---

## Entornos necesarios

| Environment | Needed? | Purpose | Branch | Data |
|-------------|:-------:|---------|--------|------|
| **Developer local** | ✅ | Daily dev | feature/* | Docker MySQL+PG seed |
| **DEV v2** | ✅ | Integration deploy | develop | Synthetic / anonymized |
| **QA / Integration** | ✅ | Automated tests, CI | develop/staging | Test fixtures |
| **Staging/Preprod v2** | ✅ | Release candidate | staging | Copy anonymized prod |
| **Customer Pilot** | ✅ | Per-client validation | staging tag | Real (read-heavy) or parallel |
| **Production v2** | ✅ | Customer runtime target | main + tag | Real |
| **v1 Maintenance** | ✅ (transition) | Current customers | maintenance | Real (current) |

**No necesitamos** replicar el anti-pattern de 3 repos.

---

## Diferenciación por configuración (no código)

| Dimension | DEV | STAGING | PRODUCTION |
|-----------|-----|---------|------------|
| `ENVIRONMENT` | development | staging | production |
| `DEBUG` | True | False | False |
| Secrets | dev vault | staging vault | prod vault |
| MySQL | seed/snapshot | anonymized snapshot | live ERP |
| PostgreSQL | local | staging DB | prod DB |
| Feature flags | all on for testing | prod-like | per installation |
| AFIP | sandbox/homologación | homologación | producción |
| `SITE_URL` | localhost | staging.domain | customer.domain |
| TLS | optional | required | required |

---

## Customer Runtime vs Release Production

| Concept | Definition |
|---------|------------|
| **Release production** | A semver-tagged build (`v2.0.0`) deployed to `main` environment |
| **Customer installation** | A configured instance: modules, flags, ERP adapter, company data |
| **Multi-customer production** | One release build → N installations (different `.env` + config) |

```text
Release v2.0.0 (immutable artifact)
    ├── Installation CLIENT-A (config A, administranet89)
    └── Installation CLIENT-B (config B, administranet)
```

---

## v1 environment clarification (current)

| Name today | Actual role | v2 future name |
|------------|-------------|----------------|
| Staging branch deploy | **Customer Production Runtime v1** | v1-maintenance |
| Produccion branch | Legacy/stale archive | Deprecate or realign |
| Desarrollo branch | v1 development | v1-frozen after split |

---

## Network / routing during coexistence

| Pattern | Option |
|---------|--------|
| Path-based | `synap.client.com/v2/` |
| Subdomain | `v2.synap.client.com` |
| Separate host | Dedicated v2 URL per pilot |

**Recommendation:** Subdomain for pilot; path for final cutover option.

---

## Data isolation

| Resource | v1/v2 parallel strategy |
|----------|-------------------------|
| MySQL ERP | **Shared read**; writes via Ports with operation_id — **HIGH RISK** |
| PostgreSQL Synap | **Separate DB** recommended for v2 |
| Redis | Key prefix `v1:` / `v2:` |
| File storage | Separate paths per version |

---

*Cross-ref: `15-V2-REPOSITORY-STRATEGY.md`, `02-V1-V2-COEXISTENCE-MODEL.md`*
