# 06 — Implementation Readiness

**Estado:** COMPLETE | **Gate antes del primer refactor**

---

## Resumen ejecutivo

| Área | Listo | Bloqueadores |
|------|:-----:|---------------|
| Architecture Contract v1.0 | ⚠️ | **Aprobación humana pendiente** |
| Product discovery | ✅ | — |
| UI/UX inventory | ✅ | — |
| Design System architecture | ✅ | — |
| Artifacts catalog | ✅ | — |
| Target experience docs | ✅ | — |
| Runtime visual evidence | ❌ | `EVIDENCE/` vacío — navegación local no realizada |
| Characterization tests | ❌ | No existen para pantallas críticas |
| Visual regression strategy | ❌ | No definida en CI |

**Veredicto:** **Casi listo** — aprobación humana + tests de caracterización son prerequisitos bloqueantes.

---

## Checklist obligatorio

### A. Gobernanza

| # | Condición | Estado |
|---|-----------|:------:|
| A1 | `SYNAP-ARCHITECTURE-CONTRACT-v1.0.md` aprobado por arquitectura/producto | ⬜ |
| A2 | Design System Contract aprobado (`DESIGN-SYSTEM/06`) | ⬜ |
| A3 | Transition rules documentadas y aceptadas (`ARCHITECTURE/02`) | ✅ |
| A4 | Registro de desviaciones arquitectónicas definido | ✅ (en contrato) |

### B. Producto y UX

| # | Condición | Estado |
|---|-----------|:------:|
| B1 | Capability map completo | ✅ |
| B2 | Workflows críticos WF-01–WF-10 documentados | ✅ |
| B3 | Screen catalog (~250–300 pantallas) | ✅ |
| B4 | Navigation map + duplicaciones identificadas | ✅ |
| B5 | Component inventory + duplicados clasificados | ✅ |
| B6 | Artifact lifecycle documentado | ✅ |

### C. Técnico pre-refactor

| # | Condición | Estado |
|---|-----------|:------:|
| C1 | Characterization tests — login (WF-01) | ⬜ |
| C2 | Characterization tests — TPV venta (WF-06) | ⬜ |
| C3 | Characterization tests — MPR wizard paso 1 (WF-04) | ⬜ |
| C4 | Characterization tests — reports dashboard execute (WF-07) | ⬜ |
| C5 | API contract tests — ecom hub, reports export | ⬜ |
| C6 | Visual baseline — reports dashboard, MPR opt_list, pedidos hub | ⬜ |
| C7 | Estrategia visual regression en CI documentada | ⬜ |
| C8 | Tailwind build único (eliminar CDN) planificado | ✅ (en migration strategy) |

### D. Seguridad (paralelo a UI, no blocker UI fase 1)

| # | Condición | Estado |
|---|-----------|:------:|
| D1 | IDOR captura factura compra corregido | ⬜ (hallazgo V2) |
| D2 | Object-level auth en APIs multi-empresa | ⬜ parcial |

### E. Equipo

| # | Condición | Estado |
|---|-----------|:------:|
| E1 | Responsable Design System asignado | ⬜ |
| E2 | Orden módulos acordado (`TARGET/05`) | ⬜ |
| E3 | Definición "pantalla migrada" aceptada | ✅ |

---

## Pantallas críticas — tests requeridos antes de REDESIGN

| Screen | Workflow | Tests mínimos |
|--------|----------|---------------|
| `login/` | WF-01 | functional + session bootstrap |
| `self_checkout/kiosco` | WF-06 | E2E venta + stock assertion |
| `mpr/wizard/` | WF-04 | wizard step transitions |
| `reports/dashboard/<slug>` | WF-07 | widget render + filter + export |
| `ecom/pedidos_hub` | WF-02 | kanban load + estado change |
| `stock/conteo/mobile` | WF-08 | QR scan mock + submit |
| `ecom/pedido-masivo` | WF-03 | import validation matrix |

---

## Qué se puede iniciar con aprobación parcial

| Con solo A1 aprobado | Con A1 + C1–C4 |
|----------------------|----------------|
| Design tokens en tailwind.config | REDESIGN pantallas piloto |
| Extraer JS dashboard_detail | REWRITE ventas presupuestos |
| Breadcrumb partial | Cambios navegación Comercial |
| ConfirmDialog primitive | — |

**NO iniciar** REWRITE de TPV o MPR wizard sin C2/C3.

---

## Evidencia opcional recomendada

| Item | Acción | Impacto |
|------|--------|---------|
| `AUDIT-V3/EVIDENCE/` screenshots | Navegar Synap local read-only | Valida screen catalog vs runtime |
| Conteo `alert/confirm` nativos | grep acotado por app | Completa feedback audit |

---

## Sign-off requerido

| Rol | Documento | Firma |
|-----|-----------|:-----:|
| Arquitectura | SYNAP-ARCHITECTURE-CONTRACT-v1.0 | ⬜ |
| Producto | SYNAP-PRODUCT-DESIGN-BLUEPRINT | ⬜ |
| UX/Design | DESIGN-SYSTEM/06 Contract | ⬜ |
| Engineering lead | TARGET/06 checklist C1–C7 | ⬜ |

---

**STOP:** No iniciar refactor general hasta ⬜ en A1, A2 y al menos C1, C4, C6.

*Fecha auditoría: 25/08/2026*
