# Design: UX contexto y densidad — Pedido masivo por sucursales

**Change:** `ecom-pedido-masivo-ux-contexto` · **Ruta:** `/ecom/mayoristapp/pedido-masivo-sucursales/` · **Fecha:** 14/07/2026

## Enfoque técnico

Corte vertical P0→P1→P2 solo en front (Alpine + plantillas + tokens `.pedidos-*`/`.pm-matrix-*`). Sin tocar `pedido_masivo_matriz.py` ni `batch_checkout_masivo.py` ni el payload de `abrir/celda/descuento/preview/confirmar`. Se reordena el layout en una **barra de contexto** (vendedor + cliente + badge lista), se automatiza la apertura del borrador al elegir cliente y se hace la **matriz siempre visible** con estados vacíos. Sticky y densidad (P1) ya están parcialmente en repo (`syncPmStickyCols`, CSS vars): se validan y protegen de regresión. Responsive (P2) es presentacional sobre el mismo modelo Alpine.

## Decisiones de arquitectura

### Barra de contexto (P0)
| Opción | Trade-off | Decisión |
|--------|-----------|----------|
| Fila única vendedor+cliente+lista, anchos `w-56`/`w-72` | Requiere reordenar 3 bloques | ✅ Elegida |
| Mantener cards separadas apiladas | Menos denso, más scroll vertical | ❌ |
Rationale: concentra el contexto operativo sin `flex-1` a viewport completo; el badge lista deja de depender del draft.

### Auto-apertura al elegir cliente (P0)
| Opción | Trade-off | Decisión |
|--------|-----------|----------|
| `elegirCliente(c)` encadena `abrirCliente()` | Riesgo doble POST | ✅ + guard `abriendo` |
| Mantener botón «Abrir matriz» | Clic extra, más fricción | ❌ eliminado |
Rationale: `elegirCliente` fija `clienteSel` y llama `abrirCliente()`; guard: si `this.abriendo` o `clienteSel === idCliente` cargado, se ignora. Spinner inline en barra (`x-show="abriendo"`). Cliente sin sucursales → alerta amber, sin bloquear.

### Matriz siempre visible (P0)
| Opción | Trade-off | Decisión |
|--------|-----------|----------|
| Shell tabla siempre montado + empty states por `x-show` | refs sticky siempre presentes | ✅ Elegida |
| `x-if="draftId"` actual | desmonta refs, oculta matriz | ❌ |
Rationale: se reemplaza `<template x-if="draftId">` por render permanente. Estados: `!draftId` → copy guía «Elegí un cliente…»; `draftId && !sucursales.length` → alerta amber existente; `draftId && !articulos.length` → fila buscador visible. Se elimina la card «1. Elegí el cliente».

### Selector vendedor compacto sin romper otras pantallas (P0)
| Opción | Trade-off | Decisión |
|--------|-----------|----------|
| Modificador `--inline` togglable por flag Alpine `selectorVendedorInline` | Cambio aditivo, default intacto | ✅ Elegida |
| Editar markup base del include | Rompe compra_mayorista | ❌ |
Rationale: el include se comparte. Se añade `:class` condicional (default `false`) y CSS `.pedidos-vendedor-operativo--inline` (sin `mt-2`, ancho `w-56`, inline en la fila). Otras pantallas no setean el flag y quedan igual.

### Sticky columnas fijas (P1 — completar, no regresar)
| Opción | Trade-off | Decisión |
|--------|-----------|----------|
| Conservar CSS vars `--pm-left-precio/desc` + `syncPmStickyCols` | Ya funciona parcialmente | ✅ Validar |
| Reescribir con anchos fijos hardcode | Rompe medición dinámica | ❌ |
Rationale: mantener medición en `$nextTick`+`rAF`; re-medir tras auto-open vía `$watch('draftId')` ya presente. Densidad: inputs cantidad/% a `h-8 text-xs`; verificar que no altere el ancho de Artículo medido.

### Acordeón móvil (P2)
| Opción | Trade-off | Decisión |
|--------|-----------|----------|
| Bloque presentacional `lg:hidden` por sucursal, matriz `hidden lg:block` | Duplica marcado, mismo modelo | ✅ Elegida |
| Transformar tabla con CSS puro | Frágil con sticky | ❌ |
Rationale: acordeón agrupa por `id_cliente_domicilio` reutilizando `celda()`/`onCelda()`/`descFila()`; sin estado nuevo → sin desincronización.

## Flujo de datos (P0)

    elegirCliente(c) ──set clienteSel──▶ abrirCliente() ──POST /abrir/──▶ aplicarMatriz()
         │  (guard: abriendo / mismo cliente)                                   │
         └───────────── barra contexto (spinner) ◀── draftId/sucursales/lista ──┘
                                                        │
                                              matriz siempre montada
                                              (empty-state ↔ filas)

## Cambios de archivos

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `ecom/templates/ecom/pedido_masivo_sucursales.html` | Modify | Barra contexto (vendedor+cliente+badge lista); quitar card paso-1 y botón «Abrir matriz»; matriz always-on + empty states; bloque acordeón `lg:hidden` |
| `ecom/static/ecom/js/pedido_masivo_app.mjs` | Modify | `elegirCliente`→`abrirCliente()` con guard; flag `selectorVendedorInline`; sin cambios de contrato |
| `ecom/templates/ecom/includes/pedidos_selector_vendedor.html` | Modify | `:class` para variante `--inline` (aditivo, default off) |
| `ecom/templates/ecom/includes/pedidos_page_styles.html` | Modify | `.pedidos-vendedor-operativo--inline`; densidad inputs `.pm-*`; media query acordeón; polish preview |
| `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md` | Modify | Flujo sin «Abrir matriz»; barra contexto; fechas dd/MM/yyyy |

## Contratos / interfaces

Sin nuevos endpoints ni cambios de payload. Estado Alpine nuevo (solo UI): `selectorVendedorInline: false`. `elegirCliente(c)` pasa a ser `async` y llama `abrirCliente()`.

## Estrategia de pruebas

| Capa | Qué | Cómo |
|------|-----|------|
| Manual | Elegir cliente abre draft sin clic extra; sin doble POST | DevTools Network, N sucursales |
| Manual | Sticky Artículo/Precio/%Desc en scroll horizontal | viewport angosto + muchas sucursales |
| Manual | Empty states (sin cliente / sin sucursales / sin filas) | recorrido UI |
| Regresión | compra_mayorista usa el include sin variante | abrir `/ecom/mayoristapp/` |

## Migración / rollout

No requiere migración DB. Rollback = revert del commit (restaura card paso-1, botón «Abrir matriz» y `x-if="draftId"`); CSS/JS sticky previo compatible.

## Preguntas abiertas

- [ ] ¿Badge lista visible antes del draft muestra placeholder o se oculta hasta `aplicarMatriz`? (default: oculto hasta draft, como hoy).
