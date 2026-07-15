# Informe de archivo SDD

**Change:** `ecom-pedidos-usabilidad-supervisor`  
**Fecha de archivo:** 13/07/2026  
**Modo:** hybrid (OpenSpec + Engram)  
**Veredicto de verificación:** PASS WITH WARNINGS (autorizado por usuario)

---

## Resumen ejecutivo

El change cierra brechas de usabilidad y paridad en pedido simple y masivo mayorista: supervisor operativo por vendedor, VCM dual con viajante efectivo, descuentos renglón/pie, lista de precios solo lectura, precio real en masivo, UI slate/sky y fix de `CodViajante`. Tras sincronizar 9 dominios de specs al source of truth y mover la carpeta a archivo, el ciclo SDD queda completo.

---

## Trazabilidad Engram (IDs de observación)

| Artefacto | ID Engram | topic_key |
|-----------|-----------|-----------|
| Proposal | #1657 | `sdd/ecom-pedidos-usabilidad-supervisor/proposal` |
| Spec (resumen) | #1658 | `sdd/ecom-pedidos-usabilidad-supervisor/spec` |
| Design | #1659 | `sdd/ecom-pedidos-usabilidad-supervisor/design` |
| Tasks | #1660 | `sdd/ecom-pedidos-usabilidad-supervisor/tasks` |
| Verify report | #1668 | `sdd/ecom-pedidos-usabilidad-supervisor/verify-report` |
| Archive report | (este documento) | `sdd/ecom-pedidos-usabilidad-supervisor/archive-report` |

---

## Specs sincronizadas

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `ecom-vendedor-operativo` | **Creada** | Spec completa: 6 REQ (VOP-01..06) |
| `ecom-ui-pedidos-tokens` | **Creada** | Spec completa: 4 REQ (UI-01..04) |
| `ecom-pedido-venta-shell` | **Creada** | VTA-01..04 (base `ecom-venta-pedido-unificada`) + 5 ADDED (VTA-05..09) |
| `ecom-descuentos-pedido-mayorista` | **Creada** | Spec completa: 5 REQ (DSC-01..05) |
| `ecom-vendedor-cliente-marca` | **Actualizada** | 1 MODIFIED (VCM-04), 1 ADDED (VCM-05) |
| `ecom-carrito-mayorista` | **Actualizada** | 3 ADDED (CAR-005..007) |
| `ecom-catalogo-producto-mayorista` | **Actualizada** | 3 ADDED (CAT-004..006) |
| `ecom-checkout-mayorista` | **Actualizada** | 3 ADDED (CHK-010..012) |
| `ecom-pedido-masivo-sucursales` | **Actualizada** | 2 MODIFIED (MAS-03, MAS-06), 5 ADDED (MAS-07..11) |

**Totales delta:** 34 requisitos · ~58 escenarios · 0 REMOVED

---

## Contenido archivado

Ruta: `openspec/changes/archive/2026-07-13-ecom-pedidos-usabilidad-supervisor/`

| Artefacto | Estado |
|-----------|--------|
| `proposal.md` | ✅ |
| `exploration.md` | ✅ |
| `design.md` | ✅ |
| `tasks.md` | ✅ (29/29 completadas) |
| `verify-report.md` | ✅ PASS WITH WARNINGS |
| `state.yaml` | ✅ |
| `specs/` (9 dominios) | ✅ |

La carpeta activa `openspec/changes/ecom-pedidos-usabilidad-supervisor/` ya no existe.

---

## Source of truth actualizado

- `openspec/specs/ecom-vendedor-operativo/spec.md`
- `openspec/specs/ecom-ui-pedidos-tokens/spec.md`
- `openspec/specs/ecom-pedido-venta-shell/spec.md`
- `openspec/specs/ecom-descuentos-pedido-mayorista/spec.md`
- `openspec/specs/ecom-vendedor-cliente-marca/spec.md`
- `openspec/specs/ecom-carrito-mayorista/spec.md`
- `openspec/specs/ecom-catalogo-producto-mayorista/spec.md`
- `openspec/specs/ecom-checkout-mayorista/spec.md`
- `openspec/specs/ecom-pedido-masivo-sucursales/spec.md`

---

## Verificación al archivar

- [x] Main specs actualizadas antes del movimiento
- [x] Carpeta movida a `archive/2026-07-13-ecom-pedidos-usabilidad-supervisor/`
- [x] Sin issues CRITICAL en verify-report
- [x] Tareas 29/29 completadas
- [x] Tests: 78/78 OK (suite ecom del change)

---

## Advertencias heredadas (no bloqueantes)

1. **Latencia preview masivo** con `price_rules_engine` en lotes grandes; límite blando 200 celdas.
2. **Seed manual** `configuracion_ecom` (`ecom_vendedores_a_cargo_<CodViajante>`) por base desplegada.
3. **Escenarios UI** (banner, selector, tokens) con evidencia estática; sin tests E2E automatizados.
4. **Purple residual** en hub pedidos (`pedidos_hub.html`) — fuera de alcance oleada E.2.
5. **`ecom-pedido-venta-shell` VTA-01..04** provienen del change activo `ecom-venta-pedido-unificada` (aún no archivado); la main spec consolidada incluye ambos conjuntos.

---

## Ciclo SDD

**Completo.** El change fue planificado, implementado, verificado y archivado. Listo para el siguiente `/sdd-new` si aplica.
