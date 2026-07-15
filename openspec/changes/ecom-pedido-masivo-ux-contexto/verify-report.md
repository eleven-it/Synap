# Informe de verificación — `ecom-pedido-masivo-ux-contexto`

**Change:** `ecom-pedido-masivo-ux-contexto`  
**Fecha:** 14/07/2026  
**Modo:** Standard (sin Strict TDD)  
**Almacén:** hybrid (OpenSpec + Engram)

---

## Veredicto

**PASS WITH WARNINGS**

Implementación P0/P1/P2 y documentación completas en código; regresión backend en verde (19 tests). Escenarios UI (sticky, auto-apertura Network, empty states, compra_mayorista, preview móvil) quedan **pending manual QA** según autorización del orquestador. Sin violaciones CRITICAL de REQ-MAS-12…19.

---

## Completitud de tareas

| Métrica | Valor |
|--------|-------|
| Tareas totales | 25 |
| Completadas `[x]` | 18 |
| Pendientes (manual QA) | 7 |

### Pendientes (no bloquean archive con autorización)

| ID | Descripción |
|----|-------------|
| P1.1 | Verificar sticky scroll horizontal — pending-manual |
| P2.3 | Preview/totales en viewport estrecho — pending-manual |
| T.3 | Auto-apertura + un solo POST `…/abrir/` — pending-manual |
| T.4 | Sticky Artículo/Precio/% Desc. — pending-manual |
| T.5 | Empty states (sin cliente / sin sucursales / sin filas) — pending-manual |
| T.6 | Regresión `compra_mayorista` selector sin `--inline` — pending-manual |
| T.7 | Acordeón móvil + preview tablet/móvil — pending-manual |

Tareas de implementación P0, P1.2–P1.5, P2.1–P2.2 y DOC.1: **completas**.

---

## Ejecución build y tests

**Build (`manage.py check`):** ✅ Passed (0 issues)

**Tests:** ✅ 19 passed / 0 failed / 0 skipped

```bash
docker exec Synap_app python manage.py test ecom.tests.test_pedido_masivo_matriz ecom.tests.test_vcm_simple_operativo --keepdb
```

```
Ran 19 tests in 0.715s — OK
```

**Coverage:** ➖ No disponible / no configurado para este change.

---

## Matriz de cumplimiento spec (REQ-MAS-12…19)

| Requisito | Escenario | Evidencia | Resultado |
|-----------|-----------|-----------|-----------|
| REQ-MAS-12 Barra contexto | Fila compacta desktop | `pedido_masivo_sucursales.html` L57 `lg:flex-row`; vendedor+cliente+badge en misma fila | ✅ COMPLIANT (estático) |
| REQ-MAS-12 | Anchos semánticos | `lg:w-56` vendedor L58; `lg:w-72` cliente L62; selector `w-56 shrink-0` sin `flex-1` en inline | ✅ COMPLIANT (estático) |
| REQ-MAS-13 Auto-apertura | Selección abre sin clic extra | `elegirCliente` → `abrirCliente()` L129–138 `pedido_masivo_app.mjs`; sin «Abrir matriz» en repo | ✅ COMPLIANT (estático) / ⚠️ T.3 manual |
| REQ-MAS-13 | Cliente sin sucursales | Alerta amber L126–128; no bloquea UI | ✅ COMPLIANT (estático) |
| REQ-MAS-13 | Anti doble POST | Guards `abriendo` L131, L227–228; mismo cliente+draft L132, L228 | ✅ COMPLIANT (estático) |
| REQ-MAS-14 Matriz always-on | Carga inicial sin borrador | Shell tabla L132+ acordeón L268+; guía L162–166 / L269–271; sin `x-if="draftId"` | ✅ COMPLIANT (estático) / ⚠️ T.5 manual |
| REQ-MAS-14 | Borrador sin artículos | Guía L169–173; buscador fila nueva L207+ | ✅ COMPLIANT (estático) |
| REQ-MAS-15 Sticky | Scroll horizontal columnas fijas | `.pm-matrix-*` + `syncPmStickyCols` L99–114; `$watch` draftId/articulos/sucursales L90–92 | ✅ COMPLIANT (estático) / ⚠️ P1.1, T.4 manual |
| REQ-MAS-15 | Ancho artículo con cap | `max-width: 12rem` L933 `pedidos_page_styles.html`; `-webkit-line-clamp: 2` | ✅ COMPLIANT (estático) |
| REQ-MAS-16 Densidad | Inputs compactos | `h-8 text-xs` + `.pm-input-dense` en matriz y acordeón | ✅ COMPLIANT (estático) |
| REQ-MAS-17 Badge lista | Visible sin borrador | `_aplicarListaDesdeCliente` L118–127; badge en barra L93–94. API `listar_clientes_con_ternas` no devuelve `lista_precio`; `serializar_matriz` no incluye nombre lista | ⚠️ PARTIAL |
| REQ-MAS-17 | Persistente con borrador | Badge en barra; `aplicarMatriz` actualiza `listaPrecio` L177–186 | ✅ COMPLIANT (estático) |
| REQ-MAS-18 Acordeón | Desktop sin acordeón | Tabla `hidden lg:block` L132; acordeón `lg:hidden` L268 | ✅ COMPLIANT (estático) |
| REQ-MAS-18 | Móvil colapsable | `<details>` por sucursal L309+; reutiliza `celda`/`onCelda`/`descFila` | ✅ COMPLIANT (estático) / ⚠️ T.7 manual |
| REQ-MAS-19 Preview responsive | Tablet | `.pm-preview-totals` grid `grid-cols-1 sm:grid-cols-3` L369; media query L1024–1030 | ✅ COMPLIANT (estático) / ⚠️ P2.3, T.7 manual |
| REQ-MAS-19 | Móvil | Apilamiento vertical totales; CTA header `Confirmar lote` L39–42 siempre visible | ✅ COMPLIANT (estático) / ⚠️ P2.3 manual |

**Resumen cumplimiento:** 16/16 escenarios con evidencia estática alineada a MUST; 7 escenarios con validación comportamental **pending manual QA**; 1 escenario **PARTIAL** (badge pre-borrador depende de datos no expuestos por API clientes masivo).

**REQ-MAS-01…11 (spec principal):** Sin cambios backend; regresión `test_pedido_masivo_matriz` + `test_vcm_simple_operativo` en verde.

---

## Correctitud (evidencia estática)

| Requisito | Estado | Notas |
|-----------|--------|-------|
| REQ-MAS-12 | ✅ | Barra contexto compacta; include vendedor embebido |
| REQ-MAS-13 | ✅ | Botón «Abrir matriz» eliminado; auto-open + spinner inline |
| REQ-MAS-14 | ✅ | Matriz always-on; empty states guía |
| REQ-MAS-15 | ✅ | Sticky infra presente; remeasure post auto-open |
| REQ-MAS-16 | ✅ | Inputs densos `h-8`/`text-xs` |
| REQ-MAS-17 | ⚠️ Partial | UI lista en barra OK; dato lista pre-`draftId` no llega del GET clientes |
| REQ-MAS-18 | ✅ | Acordeón móvil + tabla desktop |
| REQ-MAS-19 | ✅ | Panel preview responsive en markup/CSS |

---

## Coherencia (design)

| Decisión | ¿Seguida? | Notas |
|----------|-----------|-------|
| Barra contexto P0 | ✅ | Fila `lg:flex-row`, `w-56`/`w-72` |
| Auto-apertura + guard | ✅ | `elegirCliente` async encadena `abrirCliente` |
| Matriz always-on | ✅ | Sin `x-if="draftId"`; shell permanente |
| Selector `--inline` aditivo | ✅ | Flag `selectorVendedorInline: true` solo en masivo; `compra_mayorista_app.mjs` no define flag |
| Sticky conservado | ✅ | `syncPmStickyCols` + vars CSS |
| Acordeón presentacional P2 | ✅ | `lg:hidden` / `hidden lg:block` |
| Sin purple en CTAs masivo | ✅ | `bg-sky-600` confirmar; tokens slate/sky |
| Sin cambios backend/contratos | ✅ | Solo front + docs |
| Docs actualizadas | ✅ | `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md` flujo 14/07/2026 |

---

## Issues

### CRITICAL (0)

Ninguno. No se detectó «Abrir matriz», `x-if` que oculte la matriz entera, CTAs purple en pedido masivo, ni rotura del selector en compra_mayorista (flag inline opt-in).

### WARNING (7)

1. **P1.1 / T.4** — Sticky en scroll horizontal con N sucursales: pending manual QA.
2. **T.3** — Verificar un solo POST `…/abrir/` al elegir cliente (Network DevTools).
3. **T.5** — Recorrido empty states (sin cliente / sin sucursales / sin filas).
4. **T.6** — Regresión visual selector vendedor en `/ecom/mayoristapp/` (compra mayorista).
5. **P2.3 / T.7** — Preview/totales y botones en tablet/móvil.
6. **REQ-MAS-17 PARTIAL** — Badge lista antes de `draftId`: front preparado (`_aplicarListaDesdeCliente`) pero `listar_clientes_con_ternas` no incluye `lista_precio`; badge aparece tras `aplicarMatriz` si el backend provee el campo (hoy `serializar_matriz` expone `lista_id` sin nombre). Alineado con pregunta abierta del design (default oculto hasta draft).
7. **Tareas manual** — 7 ítems en `tasks.md` siguen `[ ]`; esperado para cierre QA manual.

### SUGGESTION (2)

1. Exponer `lista_precio` (nombre + PDF URL) en GET `pedido-masivo/clientes/` o en `serializar_matriz` para cerrar REQ-MAS-17 escenario «sin borrador» sin depender solo del timing del auto-open.
2. Añadir smoke E2E mínimo (Playwright) para T.3/T.5 en una iteración futura.

---

## Archivos verificados

| Archivo | Rol |
|---------|-----|
| `ecom/templates/ecom/pedido_masivo_sucursales.html` | Barra contexto, matriz always-on, acordeón, preview |
| `ecom/static/ecom/js/pedido_masivo_app.mjs` | Auto-open, sticky, badge lista |
| `ecom/templates/ecom/includes/pedidos_selector_vendedor.html` | Variante `--inline` |
| `ecom/templates/ecom/includes/pedidos_page_styles.html` | Tokens `.pm-*`, sticky, responsive |
| `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md` | Documentación flujo UX |

---

## Próximo paso recomendado

**`sdd-archive`** — Tras PASS WITH WARNINGS y autorización de QA manual diferido; opcional cerrar WARNINGS en sesión de prueba operativa antes de merge a Staging.
