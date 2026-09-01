# 05 — Estrategia de Migración UI/UX

**Estado:** COMPLETE | **NO big-bang** — orden por dependencias

---

## Estrategia elegida: incremental por capas

```text
Fase 0: Aprobación contrato + blueprint + readiness
Fase 1: Tokens + shell (navbar, feedback unificado)
Fase 2: Primitives (Button, Modal, Toast, ConfirmDialog)
Fase 3: Patterns (DataGrid, FilterBar, FormField, SubmitWithLoading)
Fase 4: Pantallas piloto (1 lista + 1 dashboard + 1 form)
Fase 5: Módulo por módulo según matriz prioridad
```

---

## Orden de módulos (post Fase 4)

| Orden | Módulo | Razón |
|:-----:|--------|-------|
| 1 | **theme/shell** | Dependencia universal |
| 2 | **reports** | P0 JS debt; canon visual; alto impacto gerencial |
| 3 | **ventas** (objetivos/presupuestos) | Excluidos canon; rewrite limpio |
| 4 | **ecom** hub | Alto tráfico; duplicación navegación |
| 5 | **stock** desktop | RESTYLE; móvil después |
| 6 | **core/archivo** | Admin frecuente |
| 7 | **mpr** | RESTYLE only — ya canon |
| 8 | **tiendanube** | Menor criticidad diaria |
| 9 | **contabilidad_audit, captura, sia, ia** | Cola larga |

**TPV y login:** RESTYLE tardío; no bloquear operación.

---

## Tácticas por estrategia

| Táctica | Aplicación Synap |
|---------|------------------|
| **App shell first** | Fase 1: navbar + status + toast unificado |
| **Design tokens** | Fase 1: `tailwind.extend` slate + purple |
| **Shared components** | Fase 2–3: includes Django |
| **Strangler en reports** | Extraer JS de dashboard_detail sin cambiar API |
| **Module by module** | Fase 5 |
| **Screen by screen** | Dentro de módulo; piloto primero |
| **Navigation first** | Paralelo Fase 2: breadcrumb partial + menú Comercial unificado |
| **Characterization tests** | **Antes** de cada REDESIGN/REWRITE |

---

## Convivencia legacy / nuevo

| Regla | Detalle |
|-------|---------|
| Pantallas no migradas | Siguen funcionando; no blocker |
| Nuevas pantallas | **MUST** usar DS desde Fase 2 |
| CSS dual | Permitido solo durante Fase 1; eliminar CDN en Fase 2 |
| Alpine + HTMX | Coexisten; HTMX solo pantallas nuevas |

---

## Riesgos y mitigación

| Riesgo | Mitigación |
|--------|------------|
| Romper WF-06 TPV | No tocar hasta Fase 5+; tests E2E |
| Regresión reports widgets | Visual baseline + API contract tests |
| Inconsistencia durante migración | Documentar "migrated" flag en screen catalog |
| Scope creep en MPR | RESTYLE only; no cambiar wizard logic |

---

## Criterio de "módulo migrado"

- [ ] Todas pantallas L3+ usan primitives DS
- [ ] Sin Tailwind CDN en templates del módulo
- [ ] Confirm/Toast unificados
- [ ] Breadcrumbs en pantallas profundas
- [ ] Characterization tests verdes
- [ ] Screen catalog actualizado

---

*Referencia: `TARGET/04-UI-REFRACTOR-BOUNDARIES.md`, `ARCHITECTURE/02-TARGET-VS-TRANSITION-RULES.md`*
