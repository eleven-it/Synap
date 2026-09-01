# SYNAP v2 Product Baseline

**Versión:** 1.0 (Release 1 definition)  
**Fecha:** 26/08/2026  
**Estado:** COMPLETE — **REQUIERE APROBACIÓN HUMANA**

---

## 1. Product Definition

**Synap v2** es una plataforma web de operaciones empresariales **productizada**, construida sobre arquitectura Ports/Adapters, con UI/UX unificada (Design System), permisos capability-based, y modelo de instalación configurable — **sin código específico por cliente en el dominio**.

**No es:** una copia limpia de las customizaciones DABRA + Best Sox.  
**Es:** el producto que emerge de estandarizar lo compartido y modelar las diferencias como configuración, políticas, flags y extensiones.

---

## 2. Supported Capabilities — v2 R1

### MUST HAVE

| Capability | WF |
|------------|-----|
| Authentication + company selection | WF-01 |
| User & permission administration | — |
| Sales order (mayorista) create/checkout | WF-02 |
| Pedidos hub kanban | WF-02 |
| Pedido masivo Excel import | WF-03 |
| Stock consult & movement | — |
| Reports dashboard execute + export | WF-07 |
| Installation configuration | — |

### SHOULD HAVE (R1 or R1.1)

| Capability | Client | WF |
|------------|--------|-----|
| MPR production OPT | B | WF-04 |
| Operator production report (mobile) | B | WF-05 |
| TPV self-checkout sale | B | WF-06 |
| Physical inventory count | A+B | WF-08 |
| Accounting audit | A | WF-09 |
| AFIP electronic invoice | B | — |
| Extension: DABRA consolidado remitos | A | — |
| Extension: Best monthly reporting pack | B | — |

### EXPLICITLY NOT IN R1

Tienda Nube full sync, BEST Azure migration, Odoo migration, report builder, OCR captura, ventas objetivos/presupuestos, IA assistant, logística, MercadoPago.

---

## 3. Supported User Types

14 roles funcionales (ver `10-ROLE-MATRIX.md`). v2 **MUST** authorize by permission, not role name.

---

## 4. Permission Model (v2 target)

```text
Principal
  └── permissions: Set<CapabilityPermission>
        e.g. sales.order.view, inventory.movement.create, reports.export
```

| Rule | Detail |
|------|--------|
| Backend enforcement | **MUST** on every mutating endpoint |
| No UI-only security | Hidden button ≠ authorization |
| Wildcards | `inventory.*` supported; menu uses same resolver |
| Company scope | Via ExecutionContext.company — not session raw |
| Admin break-glass | `system.superuser` — audited |

**Migration:** mapping from 244 v1 codes in `09-PERMISSION-CAPABILITY-MATRIX.md`.

---

## 5. Installation Model

```text
SynapInstallation
├── installation_id
├── Tenant (deployment operator)
├── Companies[] (ERP connections)
│     ├── company_id
│     ├── erp_adapter: administranet
│     └── external_reference (base_empresa)
├── enabled_modules: Module[]
├── enabled_capabilities: Capability[]
├── feature_flags: Map<string, bool>
├── business_policies: Map<string, value>
├── integration_adapters: Map<string, config>
├── extension_packs: ExtensionPack[]  (DABRA report, Best templates)
├── roles[] (synap_rol per puesto — transitional)
└── permissions[] (capability grants)
```

**v1 gap:** Model exists implicitly via `.env` + ModuleConfig + MySQL config tables — v2 formalizes.

---

## 6. Supported ERP Backends

| Backend | R1 | Adapter |
|---------|:--:|---------|
| AdministraNET MySQL | ✅ | AdministraNETAdapter (per Port) |
| Odoo 19 | LATER | OdooAdapter |
| Odoo via migration tool | LATER | — |

---

## 7. Supported Integrations

| Integration | R1 | Notes |
|-------------|:--:|-------|
| AFIP/ARCA | SHOULD | Fiscal — sandbox + prod |
| Tienda Nube | LATER | Outbox pattern exists in v1 |
| Azure SQL BEST | LATER | CLIENT-B migration only |
| Email SMTP | ✅ | Outbound notifications |
| Google Geocoding | OPTIONAL | Server-side |

---

## 8. Supported Artifacts

| Artifact | R1 |
|----------|:--:|
| PDF (pedido, OPT, stock) | ✅ |
| XLSX export (reports, pedido masivo) | ✅ |
| CSV export (audit) | SHOULD |
| Ticket print 80mm (TPV) | SHOULD |
| Email notifications | ✅ |

---

## 9. Supported Deployment Models

| Model | R1 |
|-------|:--:|
| Docker Compose (single host) | ✅ |
| Docker per environment | ✅ |
| Multi-installation same release | ✅ |
| On-premise customer | ✅ (current model) |

---

## 10. Client Configuration Model

| Mechanism | Example |
|-----------|---------|
| **Configuration** | `DB_NAME`, `SITE_URL`, warehouse defaults |
| **Feature flag** | `production.enabled`, `tn.sync.enabled` |
| **Business policy** | `sales.approval_threshold`, `mpr.docena_pairs=12` |
| **Extension pack** | `dabra.consolidado_remitos`, `best.monthly_reporting` |
| **Permission grant** | Per puesto/capability |

**FORBIDDEN in domain:** `if client == X`, `if base_empresa == Y`.

---

## 11. V1 Compatibility Expectations

| Aspect | Expectation |
|--------|-------------|
| Shared MySQL ERP | v1 and v2 may write during transition — ownership contract applies |
| Parallel operation | v1 maintenance branch until client sign-off |
| Data parity | Same business outcomes for migrated capabilities |
| Permission parity | Equivalent or stricter |
| No forced simultaneous migration | Per client timeline |

---

## 12. Migration Requirements

See `13-MIGRATION-ACCEPTANCE-CRITERIA.md`, `18-CUSTOMER-MIGRATION-STRATEGY.md`.

**Pilot order:** CLIENT-B (Best Sox) → CLIENT-A (DABRA).

---

## 13. Repository & Environment (v2)

| Decision | Value |
|----------|-------|
| Repo strategy | **Option B:** new `Synap-v2` repo |
| Branches | `develop` / `staging` / `main` |
| Versioning | SemVer tags on `main` |
| v1 repo | `Synap` → `maintenance` branch from Staging snapshot |
| Principle | **CODEBASE ≠ ENVIRONMENT** |

---

## 14. Architecture Contract (inherited from V3)

Permanent rules: `AUDIT-V3/ARCHITECTURE/SYNAP-ARCHITECTURE-CONTRACT-v1.0.md`

v2 **MUST** implement from day one:
- ExecutionContext
- Port/Adapter boundaries
- No domain ERP table names
- Cross-system operation_id / idempotency

---

## 15. Maturity Scorecard (master)

| Capability | A | B | Functional | Technical | Criticality | Custom | V2 R1 | Risk |
|------------|:-:|:-:|:----------:|:---------:|:-----------:|:------:|:-----:|:----:|
| Login | ✅ | ✅ | PROD | 4 | CRIT | No | MUST | Low |
| Sales order | ✅ | ✅ | PROD | 3 | CRIT | Config | MUST | High |
| Reports | ✅ | ✅ | PROD | 3 | CRIT | No | MUST | Med |
| Stock | ✅ | ✅ | PROD | 3.5 | CRIT | No | MUST | High |
| MPR | ❌ | ✅ | PROD | 3.5 | CRIT | Policy | SHOULD | High |
| TPV | ⚠️ | ✅ | PROD | 3.5 | CRIT | No | SHOULD | High |
| DABRA rpt | ✅ | ❌ | PROD | 2.5 | CRIT | Yes | EXT | Med |
| Best monthly | ❌ | ✅ | PROD | 2.5 | CRIT | Yes | EXT | Med |
| Contab audit | ✅ | ❌ | PILOT | 3 | CRIT | Flag | SHOULD | Med |
| TN sync | ❌ | ✅ | PROD | 3 | HIGH | No | LATER | High |

---

## 16. Explicitly Unsupported in R1

- Multi-ERP simultaneous (beyond AdministraNET)
- SaaS multi-tenant single deployment
- Mobile-native apps (PWA acceptable)
- Offline-first TPV
- Real-time collaborative editing
- Scheduled report delivery (not in v1 either)

---

## 17. Deferred Features (v2 roadmap, NOT baseline)

- semantic-v2 report builder
- Full Tienda Nube bidirectional
- Odoo as primary ERP
- OIDC/SSO (architecture ready, not R1)
- AI agent marketplace
- MercadoPago integration

---

## 18. Human Decisions Required

| # | Decision | Options |
|---|----------|---------|
| 1 | Repo name `Synap-v2` vs monorepo | **Recommend Synap-v2** |
| 2 | CLIENT-B first pilot? | **Recommend YES** |
| 3 | MPR/TPV in R1 or R1.1? | **Recommend R1.1 if capacity tight** |
| 4 | Shared MySQL during pilot? | **YES with strict ownership** |
| 5 | Staging v1 freeze date? | TBD |
| 6 | DABRA report: extension vs product feature? | **Extension pack** |

---

## 19. Stop Condition

```text
✅ V3.5 documentation COMPLETE
⬜ Human approval SYNAP-V2-PRODUCT-BASELINE
⬜ Human approval V2-RELEASE-1-SCOPE
⬜ Human approval V2-REPOSITORY-STRATEGY
⛔ NO create Synap-v2 repo until approved
⛔ NO Foundation implementation until approved
```

---

## 20. Document Index

```text
AUDIT-V3.5/
├── 01-VERSION-AND-RELEASE-TOPOLOGY.md
├── 02-V1-V2-COEXISTENCE-MODEL.md
├── 03-CLIENT-INSTALLATION-MATRIX.md
├── 04-CLIENT-VARIABILITY-MAP.md
├── 05-MODULE-MATURITY-MATRIX.md
├── 06-CAPABILITY-MATURITY-MATRIX.md
├── 07-CUSTOMIZATION-INVENTORY.md
├── 08-PERMISSION-INVENTORY.md
├── 09-PERMISSION-CAPABILITY-MATRIX.md
├── 10-ROLE-MATRIX.md
├── 11-FEATURE-FLAG-CONFIGURATION-MAP.md
├── 12-V1-V2-FUNCTIONAL-PARITY-MATRIX.md
├── 13-MIGRATION-ACCEPTANCE-CRITERIA.md
├── 14-V2-RELEASE-1-SCOPE.md
├── 15-V2-REPOSITORY-STRATEGY.md
├── 16-V2-ENVIRONMENT-TOPOLOGY.md
├── 17-V1-V2-BACKPORT-POLICY.md
├── 18-CUSTOMER-MIGRATION-STRATEGY.md
└── SYNAP-V2-PRODUCT-BASELINE.md (this document)
```

---

**SYNAP V2 MUST BE A PRODUCT — NOT A CLEANER COPY OF TWO CUSTOMER CUSTOMIZATIONS.**

*Baseline ≠ Roadmap. R1 scope is minimal viable product for both clients.*
