# Proposal: UX contexto y densidad — Pedido masivo por sucursales

**Change:** `ecom-pedido-masivo-ux-contexto`  
**Ruta:** `/ecom/mayoristapp/pedido-masivo-sucursales/`  
**Fecha:** 14/07/2026

## Intent

Reducir fricción operativa en la captura masiva: eliminar el paso explícito «Abrir matriz», concentrar vendedor + cliente + lista en una barra de contexto compacta y mostrar la matriz desde el primer render (estado vacío guiado). Completar sticky/densidad P1 y pulir responsive P2 sin tocar contratos backend.

## Scope

### In Scope
- **P0 — Barra de contexto:** vendedor operativo y cliente en la misma fila; anchos semánticos `w-56` / `w-72`; sin `flex-1` a ancho completo del viewport.
- **P0 — Auto-apertura:** quitar botón «Abrir matriz»; `elegirCliente` invoca `abrirCliente()` → POST `…/abrir/`; spinner/estado `abriendo` inline.
- **P0 — Matriz siempre visible:** shell de tabla con copy guía cuando `!draftId` o sin filas; sin card «Paso 1» que oculte la matriz.
- **P1 — Sticky (completar):** validar `.pm-matrix-*` + `syncPmStickyCols` en scroll real; densificar inputs cantidad/% desc.; badge lista de precios en barra de contexto (no solo post-draft).
- **P2 — Responsive:** acordeón por sucursal en viewport estrecho (opcional, sin romper desktop); panel preview/totales adaptable.

### Out of Scope
- Nuevos endpoints o cambios en payload POST abrir/matriz/celda/preview/confirmar.
- Lógica de precios, descuentos, batch checkout o borrador Postgres.
- Rediseño hub/kanban; patrón visual de ventas/objetivos o presupuestos.
- Override de lista de precios.

## Capabilities

### New Capabilities
- *(ninguna)*

### Modified Capabilities
- `ecom-pedido-masivo-sucursales`: requisitos UI ADDED — barra contexto compacta, auto-apertura al elegir cliente, matriz empty-state persistente, sticky columnas fijas completado, densidad inputs, badge lista en contexto, acordeón móvil y preview responsive. REQ-MAS-01…11 sin cambio funcional backend.

## Approach

Corte vertical P0→P1→P2 en front Alpine (`pedido_masivo_app.mjs`) + plantilla `pedido_masivo_sucursales.html` + tokens `.pm-matrix-*` / `.pedidos-*` en `pedidos_page_styles.html`. Reutilizar `pedidos_selector_vendedor.html` embebido en barra contexto. `elegirCliente` encadena `abrirCliente()` con guard anti doble POST. Matriz: `x-show` unificado (draft o skeleton); filas vacías con mensaje operativo. P1: revisar offsets sticky tras auto-open; inputs `h-8`/`text-xs`. P2: breakpoint Tailwind + bloques colapsables por `id_cliente_domicilio`. Sin cambios en `pedido_masivo_matriz.py` ni `batch_checkout_masivo.py`.

## Affected Areas

| Area | Impact | Descripción |
|------|--------|-------------|
| `ecom/templates/ecom/pedido_masivo_sucursales.html` | Modified | Barra contexto, quitar paso-1/botón, matriz always-on, acordeón móvil |
| `ecom/static/ecom/js/pedido_masivo_app.mjs` | Modified | Auto-open en `elegirCliente`, estados loading, sticky post-render |
| `ecom/templates/ecom/includes/pedidos_selector_vendedor.html` | Modified | Layout compacto en barra contexto |
| `ecom/templates/ecom/includes/pedidos_page_styles.html` | Modified | Densidad inputs, sticky polish, responsive acordeón |
| `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md` | Modified | Flujo sin «Abrir matriz»; barra contexto; fechas dd/MM/yyyy |

## Risks

| Risk | L | Mitigation |
|------|---|------------|
| Doble POST abrir al elegir cliente | M | Flag `abriendo`; ignorar selección duplicada |
| Auto-open con cliente sin sucursales | M | Mantener alerta amber; no bloquear UI |
| Regresión sticky tras refactor layout | M | Probar scroll con N sucursales; `syncPmStickyCols` en `$watch` |
| Acordeón móvil desincroniza celdas | L | Solo presentación; mismo modelo Alpine |
| UX confusa sin botón explícito | L | Copy guía + spinner en barra contexto |

## Rollback Plan

Revert commit del change: restaurar card paso-1 y botón «Abrir matriz»; `elegirCliente` sin auto-open; matriz condicionada a `draftId`. CSS/JS sticky previo permanece compatible. Sin migraciones DB.

## Dependencies

- Spec main `openspec/specs/ecom-pedido-masivo-sucursales/spec.md` (REQ-MAS-01…11).
- Canon UI `openspec/specs/ui-fuente-verdad-reportes-mpr/spec.md` y tokens `.pedidos-*`.
- Sticky parcial ya en repo (14/07/2026).

## Success Criteria

- [ ] Elegir cliente abre draft y muestra matriz sin clic extra.
- [ ] Vendedor + cliente + badge lista en una fila compacta (w-56/w-72).
- [ ] Matriz visible al cargar con guía cuando no hay draft/filas.
- [ ] Sticky Artículo/Precio/% Desc. OK con scroll horizontal.
- [ ] Inputs densos; preview usable en móvil/tablet.
- [ ] Sin purple; sin nuevos endpoints; docs actualizadas.
