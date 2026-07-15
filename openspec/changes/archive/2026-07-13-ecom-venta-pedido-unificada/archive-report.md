# Informe de archivo SDD

**Change:** `ecom-venta-pedido-unificada`  
**Fecha de archivo:** 13/07/2026  
**Modo:** hybrid (OpenSpec + Engram)  
**Veredicto de verificación:** PASS WITH WARNINGS (autorizado por usuario)

---

## Resumen ejecutivo

El change unifica crear, editar (Pendiente) y consultar PED en OrderShell canónico `/ecom/mayoristapp/venta/`, depreca `/compra/` y `/pedidos/<cod_mov>/`, y redirige hub/menú/relay a la ruta de venta. Tras sincronizar specs al source of truth y mover la carpeta a archivo, el ciclo SDD queda completo.

---

## Trazabilidad Engram (IDs de observación)

| Artefacto | ID Engram | topic_key | Notas |
|-----------|-----------|-----------|-------|
| Proposal | — | `sdd/ecom-venta-pedido-unificada/proposal` | Solo filesystem (`proposal.md`) |
| Spec (delta) | — | `sdd/ecom-venta-pedido-unificada/spec` | Solo filesystem (`specs/`) |
| Design | — | `sdd/ecom-venta-pedido-unificada/design` | Solo filesystem (`design.md`) |
| Tasks | — | `sdd/ecom-venta-pedido-unificada/tasks` | Solo filesystem (`tasks.md`) |
| Verify report | #1686 | `sdd/ecom-venta-pedido-unificada/verify-report` | PASS WITH WARNINGS |
| Archive report | (este documento) | `sdd/ecom-venta-pedido-unificada/archive-report` | Persistido en Engram |

---

## Specs sincronizadas

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `ecom-pedido-venta-shell` | **Sin cambio** (ya consolidada) | REQ-VTA-01..04 del delta **equivalentes** a la main spec existente. VTA-05..09 **preservados** (incorporados por archive `ecom-pedidos-usabilidad-supervisor`, 13/07/2026). Nota: *already merged by usabilidad-supervisor archive* para el bloque VTA-01..04; solo se actualizó metadata de origen en main. |
| `ecom-gestion-pedidos-navegacion` | **Creada** | 3 REQ ADDED (NAV-01..03): redirect `/compra/`, redirect detalle PED, hub/menú → venta |

**Totales delta de este change:** 7 requisitos (VTA-01..04 + NAV-01..03) · 0 MODIFIED · 0 REMOVED

---

## Notas de merge (instrucción explícita)

- **`ecom-pedido-venta-shell`:** La main spec en `openspec/specs/ecom-pedido-venta-shell/spec.md` ya contenía VTA-01..09 tras el archive de `ecom-pedidos-usabilidad-supervisor`. **No se eliminaron** VTA-05..09. El delta de este change (VTA-01..04) coincide texto y escenarios con la main; **no se reescribió** el cuerpo de requisitos.
- **`ecom-gestion-pedidos-navegacion`:** Dominio nuevo; delta copiado íntegro a main spec.

---

## Contenido archivado

Ruta: `openspec/changes/archive/2026-07-13-ecom-venta-pedido-unificada/`

| Artefacto | Estado |
|-----------|--------|
| `proposal.md` | ✅ |
| `exploration.md` | ✅ |
| `design.md` | ✅ |
| `tasks.md` | ✅ (17/17 completadas) |
| `verify-report.md` | ✅ PASS WITH WARNINGS |
| `state.yaml` | ✅ |
| `specs/ecom-pedido-venta-shell/spec.md` | ✅ (delta) |
| `specs/ecom-gestion-pedidos-navegacion/spec.md` | ✅ (delta) |

La carpeta activa `openspec/changes/ecom-venta-pedido-unificada/` ya no existe.

---

## Source of truth actualizado

- `openspec/specs/ecom-pedido-venta-shell/spec.md` — metadata origen (ambos changes archivados)
- `openspec/specs/ecom-gestion-pedidos-navegacion/spec.md` — **nueva**

---

## Verificación al archivar

- [x] Main specs actualizadas antes del movimiento
- [x] VTA-05..09 preservados en `ecom-pedido-venta-shell`
- [x] Carpeta movida a `archive/2026-07-13-ecom-venta-pedido-unificada/`
- [x] Sin issues CRITICAL en verify-report
- [x] Tareas 17/17 completadas
- [x] Tests obligatorios: 44/44 OK

---

## Advertencias heredadas (no bloqueantes)

1. **5 escenarios delta sin test automatizado** — modos editable/consulta, modal confirmar cambios, hero Anular y carga `?cod_mov=` (evidencia estática en JS/vista).
2. **REQ-NAV-03 parcial** — pipeline hub genera URLs correctas; sin assert dedicado en tests del hub.
3. **`test_cliente_relay`** no ejecutable en contenedor (`pytest` ausente); relay `frm=0` → `/venta/` implementado pero no verificado en corrida verify.

---

## Ciclo SDD

**Completo.** El change fue planificado, implementado, verificado y archivado. Listo para el siguiente `/sdd-new` si aplica.
