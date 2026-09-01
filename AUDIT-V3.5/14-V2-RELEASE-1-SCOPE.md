# 14 — Synap v2 Release 1 Scope

**Estado:** COMPLETE — **REQUIERE APROBACIÓN PRODUCTO**

---

## Definición

**Synap v2 R1** = primera release productizable con arquitectura v2 (ExecutionContext, Ports foundation, Design System shell) que soporta **capacidades compartidas críticas** de ambos clientes + **extensiones explícitas** por instalación.

**NO incluye** todo v1.

---

## MUST HAVE (v2 R1)

| # | Capability | Rationale |
|---|------------|-----------|
| 1 | **Authentication + ExecutionContext** | Foundation |
| 2 | **Permission model v2** (capability-based, backend enforced) | Security |
| 3 | **App shell + Design System primitives** | UX foundation |
| 4 | **Login + empresa selection** | WF-01 |
| 5 | **User/permission admin** (supervisor) | Operations |
| 6 | **Sales order create/checkout** | WF-02 — both clients |
| 7 | **Pedidos hub kanban** | WF-02 — both clients |
| 8 | **Pedido masivo Excel** | WF-03 — both clients |
| 9 | **Stock consult + movement** | WF shared |
| 10 | **Reports dashboard execute + export** | WF-07 — both clients |
| 11 | **Module/installation configuration model** | Productization |

---

## SHOULD HAVE (v2 R1 if capacity allows)

| # | Capability | Primary client | Note |
|---|------------|----------------|------|
| 12 | MPR OPT wizard | B | High complexity — may slip to R1.1 |
| 13 | Parte operario mobile | B | Reuse pattern from v1 |
| 14 | TPV sale | B | High risk — characterization mandatory |
| 15 | Physical inventory count | B (+ A) | Mobile critical |
| 16 | Accounting audit | A | Pilot feature |
| 17 | AFIP electronic invoice | B | Fiscal — adapter phase |
| 18 | Extension: DABRA consolidado report | A | Config + extension |
| 19 | Extension: Best monthly reporting pack | B | Template pack |

---

## V2 LATER (post R1)

| Capability | Reason defer |
|------------|--------------|
| Tienda Nube full sync | Integration complexity |
| BEST Azure migration tool | CLIENT-B specific, dev maturity |
| Odoo migration | DEVELOPMENT maturity |
| Report builder/design | PILOT; execute sufficient for R1 |
| Captura factura OCR | Security IDOR fix first in v1 |
| Ventas objetivos/presupuestos | UI rewrite — low daily use |
| IA assistant | LOW criticality |
| Logística entregas | PILOT |
| MercadoPago (dead module) | Not in v1 prod |

---

## DEPRECATED / REMOVE (do not port to v2)

| Item | Reason |
|------|--------|
| `dashboard` stub app | DEAD |
| Dual Tailwind CDN | Tech debt |
| `permiso_sistema` as primary store | Legacy — v2 uses capability perms only |
| Client-specific `if base_empresa` patterns | None exist — keep it that way |
| Templates `* 2.html` | Accidental duplicates |
| `SYNAP_AUTO_SYNC_PERMISSIONS` | Deprecated |
| Slug-dispatch legacy reports | semantic-v2 only for new |
| module_registry Django-style perm keys | Align to synap catalog |

---

## EXPERIMENTAL (not in R1)

- Odoo migración full pipeline
- Report AI features
- WebAuthn (unless security mandates)

---

## Priorización matrix

| Capability | Customer crit | Func mat | Tech mat | Legacy coupling | Migration risk | Strategic | **R1?** |
|------------|:-------------:|:--------:|:--------:|:---------------:|:--------------:|:---------:|:-------:|
| Login | 5 | 5 | 4 | 4 | 2 | 5 | **MUST** |
| Sales order | 5 | 5 | 3 | 5 | 4 | 5 | **MUST** |
| Reports execute | 5 | 5 | 3 | 4 | 3 | 5 | **MUST** |
| Stock | 5 | 5 | 3.5 | 5 | 4 | 5 | **MUST** |
| MPR | 5 (B) | 5 | 3.5 | 5 | 5 | 4 | **SHOULD** |
| TPV | 5 (B) | 5 | 3.5 | 5 | 5 | 4 | **SHOULD** |
| TN sync | 4 (B) | 5 | 3 | 5 | 5 | 3 | LATER |
| IA | 1 | 3 | 3 | 1 | 2 | 3 | LATER |

---

## R1 success criteria

1. CLIENT-A can run daily: pedidos + reports + audit (if SHOULD included)
2. CLIENT-B can run daily: pedidos + stock + reports (+ MPR/TPV if SHOULD included)
3. Zero client-specific code in domain layer
4. All R1 capabilities pass acceptance criteria STAGING gate
5. v1 remains operational for gaps

---

*Baseline contractual: `SYNAP-V2-PRODUCT-BASELINE.md`*
