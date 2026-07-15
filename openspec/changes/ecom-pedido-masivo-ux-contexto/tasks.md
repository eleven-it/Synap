# Tasks: UX contexto y densidad — Pedido masivo por sucursales

**Change:** `ecom-pedido-masivo-ux-contexto` · **Ruta:** `/ecom/mayoristapp/pedido-masivo-sucursales/` · **Orden:** P0 → P1 → P2

> **P1 sticky (parcial en repo, 14/07/2026):** `syncPmStickyCols()` en `ecom/static/ecom/js/pedido_masivo_app.mjs` y tokens `.pm-matrix-*` en `ecom/templates/ecom/includes/pedidos_page_styles.html` ya existen. Las tareas P1.1–P1.2 son **verificar/completar** tras el refactor P0, no reimplementar.

---

## P0 — Barra contexto, auto-apertura y matriz always-on

- [x] P0.1 Reorganizar barra de contexto en `ecom/templates/ecom/pedido_masivo_sucursales.html`: fila `lg:flex-row` con vendedor (`w-56`) + cliente (`w-72`) + badge lista; sin `flex-1` en esos campos (REQ-MAS-12)
- [x] P0.2 Añadir variante inline en `ecom/templates/ecom/includes/pedidos_selector_vendedor.html`: clase condicional `.pedidos-vendedor-operativo--inline` (default off, no rompe otras pantallas)
- [x] P0.3 Estilos inline en `ecom/templates/ecom/includes/pedidos_page_styles.html`: `.pedidos-vendedor-operativo--inline` (sin `mt-2`, ancho `w-56`, alineado en fila)
- [x] P0.4 Flag `selectorVendedorInline: true` en `ecom/static/ecom/js/pedido_masivo_app.mjs`; embeber selector en barra contexto (eliminar card separada `mostrarSelectorVendedor`)
- [x] P0.5 Eliminar card «1. Elegí el cliente» y botón «Abrir matriz» de `ecom/templates/ecom/pedido_masivo_sucursales.html` (REQ-MAS-13)
- [x] P0.6 `elegirCliente(c)` async en `ecom/static/ecom/js/pedido_masivo_app.mjs`: tras setear `clienteSel`, invocar `abrirCliente()` automáticamente (REQ-MAS-13)
- [x] P0.7 Guard anti doble POST en `abrirCliente()` / `elegirCliente`: ignorar si `abriendo` o mismo `clienteSel` ya cargado con `draftId` (REQ-MAS-13)
- [x] P0.8 Spinner/estado `abriendo` inline en barra contexto (`pedido_masivo_sucursales.html`, `x-show="abriendo"`)
- [x] P0.9 Reemplazar `<template x-if="draftId">` por shell de matriz siempre montado en `pedido_masivo_sucursales.html`; empty states: `!draftId` → guía elegir cliente; `draftId && !articulos.length` → guía agregar artículos; mantener alerta amber sin sucursales (REQ-MAS-14)

---

## P1 — Sticky (completar), densidad y badge lista

- [ ] P1.1 **Verificar** sticky tras refactor P0: scroll horizontal con N sucursales; columnas Artículo/Precio/% Desc. alineadas (`syncPmStickyCols` + refs `pmStickyArt/Precio/Desc`) — **pending-manual** (REQ-MAS-15)
- [x] P1.2 **Completar** remeasure post auto-open: confirmar `$watch('draftId')` y `$watch('articulos'/'sucursales')` disparan `syncPmStickyCols` con matriz always-on; ajustar solo si falla tras P0 en `pedido_masivo_app.mjs`
- [x] P1.3 Densificar inputs cantidad y % desc. a `h-8 text-xs` en `pedido_masivo_sucursales.html`; tokens `.pm-*` en `pedidos_page_styles.html` si hace falta (REQ-MAS-16)
- [x] P1.4 Mover `{% include "ecom/includes/pedidos_lista_badge.html" %}` a barra contexto (fuera del bloque post-draft) en `pedido_masivo_sucursales.html` (REQ-MAS-17)
- [x] P1.5 Poblar `listaPrecio`/`listaPrecioPdfUrl` al elegir cliente en `pedido_masivo_app.mjs` (campo en item de búsqueda o dato de `aplicarMatriz` tras auto-open); badge visible con cliente seleccionado sin borrador previo si hay dato disponible — **sin cambiar** POST `…/abrir/` ni otros contratos masivo

---

## P2 — Responsive (acordeón y preview)

- [x] P2.1 Bloque acordeón `lg:hidden` por `id_cliente_domicilio` en `pedido_masivo_sucursales.html`; tabla desktop `hidden lg:block`; reutilizar `celda()`/`onCelda()`/`descFila()` (REQ-MAS-18)
- [x] P2.2 Media queries y estilos acordeón en `ecom/templates/ecom/includes/pedidos_page_styles.html`
- [ ] P2.3 Panel preview/totales apilado en viewport estrecho (`pedido_masivo_sucursales.html` + `pedidos_page_styles.html`); botones preview/confirmar alcanzables (REQ-MAS-19) — **pending-manual** tablet/móvil

---

## Documentación

- [x] DOC.1 Actualizar `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md`: flujo sin «Abrir matriz»; barra contexto compacta; matriz always-on; sticky/densidad; fechas **dd/MM/yyyy**

---

## Pruebas

- [x] T.1 Regresión backend: `docker exec Synap_app python manage.py test ecom.tests.test_pedido_masivo_matriz --keepdb`
- [x] T.2 Regresión operativo/VCM: `docker exec Synap_app python manage.py test ecom.tests.test_vcm_simple_operativo --keepdb`
- [ ] T.3 **pending-manual** — elegir cliente abre draft sin clic extra; un solo POST `…/abrir/` en Network (REQ-MAS-13)
- [ ] T.4 **pending-manual** — sticky Artículo/Precio/% Desc. con scroll horizontal y descripción larga (REQ-MAS-15)
- [ ] T.5 **pending-manual** — empty states sin cliente / sin sucursales / sin filas (REQ-MAS-14)
- [ ] T.6 **pending-manual** — regresión `compra_mayorista.html`: selector vendedor sin variante `--inline` intacto
- [ ] T.7 **pending-manual** — acordeón móvil y preview en tablet/móvil (REQ-MAS-18/19); sin harness JS en repo
