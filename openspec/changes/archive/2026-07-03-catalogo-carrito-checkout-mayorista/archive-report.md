# Archive Report — Catálogo, carrito y checkout mayorista

**Change:** `catalogo-carrito-checkout-mayorista`
**Artifact Store:** openspec
**Fecha de archivado:** 2026-07-03
**Veredicto de verificación previo:** PASS (0 CRITICAL, 0 WARNING abiertos)

---

## Specs sincronizados a la fuente de verdad

Los tres delta specs no tenían spec principal previo → se copiaron como specs completos:

| Dominio | Acción | Destino |
|---------|--------|---------|
| `ecom-catalogo-producto-mayorista` | Creado | `openspec/specs/ecom-catalogo-producto-mayorista/spec.md` |
| `ecom-carrito-mayorista` | Creado | `openspec/specs/ecom-carrito-mayorista/spec.md` |
| `ecom-checkout-mayorista` | Creado | `openspec/specs/ecom-checkout-mayorista/spec.md` (incluye REQ-CHK-001..009, con REQ-CHK-009 percepciones IIBB P4) |

## Contenido archivado

`openspec/changes/archive/2026-07-03-catalogo-carrito-checkout-mayorista/`:
- proposal.md ✅
- exploration.md ✅
- design.md ✅ (arquitectura global + P0/P2/P4 detallados)
- specs/ ✅ (3 dominios)
- tasks.md ✅ (P0–P4 completas; pendientes solo follow-ups no bloqueantes)
- verify-report.md ✅ (PASS, 35/35 escenarios COMPLIANT, 36/36 tests)

## Resumen del ciclo

- **P0** Catálogo (listado/detalle/precios) — 8 escenarios.
- **P1** Carrito Postgres (CRUD/totales/descuentos) — 11 escenarios.
- **P2** Checkout transaccional MySQL (PED/PRE, numeración FOR UPDATE, crédito, idempotencia) — 13 escenarios.
- **P3** DEV, export PDF, restricciones por PV, UI web POS.
- **P4** Percepciones IIBB configurables por implementación (`sucursales.agente_percep`), REQ-CHK-009.

Migraciones/checkpoints `ecom/0015`–`0025`. Docs en `docs/ecom/` (`CATALOGO_MAYORISTA_P0`, `CARRITO_MAYORISTA_P1`, `CHECKOUT_MAYORISTA_P2`, `LISTA_PRECIOS_PDF_P3`, `RESTRICCIONES_CATALOGO_PV_P3`, `UI_COMPRA_MAYORISTA_P3`, `PERCEPCIONES_IIBB_P4`) + `DELTA_PHP_2026Q2.md`.

## Follow-ups (backlog, no bloqueantes)

- Imágenes de artículo en catálogo/ficha (paridad `foto.php`).
- Selector de cliente embebido + ficha visual con destacados en la UI web.
- Tests E2E de navegador de la UI.
- Índice único `comp_ped.CodigoMovimiento` (vía `legacy_mysql_schema/catalog.py`, previa auditoría de duplicados).
- Percepciones IIBB en DEV (devolución).
- Re-medir `LP_PDF_MAX_SECONDS*` en deploy.

## SDD Cycle Complete

El change fue planificado, implementado, verificado y archivado. Fuente de verdad actualizada en `openspec/specs/ecom-*`.
