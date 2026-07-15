# 05 · Design System — Pedidos

- **Fecha:** 13/07/2026 (Oleada E — barrido purple)
- **Fuente de verdad de tokens:** `ecom/templates/ecom/includes/pedidos_page_styles.html` (clases `.pedidos-*` y `.compra-*`)
- **Canon superior:** `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` (familia reportes/MPR slate/sky)
- **Regla de oro:** **extender** los tokens `.pedidos-*` existentes. **No** inventar un sistema paralelo. Evitar el genérico purple-on-white de "AI"; mantener familia **slate / sky**.

> **Oleada E (13/07/2026):** se completó el barrido de purple en el flujo de pedido (simple y masivo). El CTA de confirmar PED, el toggle grande `.compra-toggle-btn-lg-ped-active` y el anillo de foco pasaron de `purple-600/500` a `sky-600/400`. El breadcrumb sobre tablero claro usa `variant="board"` (sky/slate) en lugar del antiguo `variant="purple"`. El único remanente de violeta es el token `.pedidos-btn-gradient`, **acotado** a acciones de hero en listados/presupuestos (pantalla completa) y **prohibido** como CTA de venta/masivo. Se agregó el token compartido `.pedidos-badge-lista`.

> Todos los valores citados provienen del `<style>` real de `pedidos_page_styles.html`. Las extensiones propuestas se marcan como **[nuevo]** y deben añadirse al mismo archivo de tokens, no a estilos sueltos por template.

---

## 1. Filosofía

1. **Un solo sistema.** Los pedidos ya viven en el canon de reportes/MPR. El rediseño consolida, no reemplaza.
2. **Tokens antes que utilidades sueltas.** Reemplazar inputs/botones inline (Tailwind ad hoc) por tokens `.pedidos-input`, `.pedidos-btn*`.
3. **Slate como neutro, sky como acento.** El violeta solo aparece en `.pedidos-btn-gradient`, acotado a acciones de hero en listados/presupuestos; **no** se usa como CTA de venta/masivo y no se propaga.
4. **Color semántico por modo:** PED = sky, PRE = amber, DEV = rose.
5. **Movimiento suave y funcional** (`.impeccable.md`): transiciones 150–300ms, sin animación decorativa.

---

## 2. Paleta

### 2.1 Neutros (slate)
| Rol | Valor (light) | Valor (dark) | Uso |
|---|---|---|---|
| Fondo página | `slate-50` (`bg-slate-50`) | `slate-950` | `section.pedidos-page` |
| Superficie card | `#fff` | `slate-900` (`rgb(15 23 42)`) | `.pedidos-card`, `.pedidos-workspace` |
| Borde | `slate-200` (`rgb(226 232 240)`) | `slate-800` (`rgb(30 41 59)`) | cards, tablas, inputs |
| Texto principal | `slate-900` | `#fff` / `slate-100` | títulos, totales |
| Texto secundario | `slate-500/600` | `slate-300/400` | labels, ayudas |
| Hero (gradiente) | `slate-900 → slate-800 → slate-900` | idem dark | `base_pedidos.html` |

### 2.2 Acento (sky)
| Token | Valor | Uso |
|---|---|---|
| Sky primario | `rgb(2 132 199)` (`sky-600`) | `.pedidos-btn-primary`, foco activo |
| Sky hover | `rgb(14 165 233)` (`sky-500`) | hover primario |
| Sky claro | `rgb(56 189 248)` / `sky-100` | selección, resaltados |
| Anillo foco | `rgba(14,165,233,0.25)` | `.pedidos-input:focus`, `focus-visible` |

### 2.3 Colores semánticos de modo
| Modo | Color base | Tokens/uso reales |
|---|---|---|
| **PED** | **sky** | `.compra-toggle-btn-ped-active` (`rgb(2 132 199)`), borde shell `.compra-modo-ped` |
| **PRE** | **amber** | `.compra-toggle-btn-pre-active` (`rgb(245 158 11)`), `.compra-modo-pre` |
| **DEV** | **rose** | `.compra-toggle-btn-dev-active` (`rgb(244 63 94)`), `.compra-modo-dev` |

### 2.4 Feedback
| Estado | Color | Uso |
|---|---|---|
| Éxito | `emerald-600` (`rgb(34 197 94)` familia) | `mensajeOk`, badges autorizado |
| Advertencia | `amber-600/700` | crédito no autorizado, aviso sin cliente |
| Error | `rose-600` (`rgb(225 29 72)`) | `.pedidos-btn-danger`, mensajes error |
| Info | `sky` sobre `slate-50` | `.pedidos-alert-info` |

---

## 3. Tipografía

Alineada a Synap/Tailwind (familia del proyecto, `slate` como color base). Escala derivada de los tokens actuales:

| Rol | Tamaño | Peso | Referencia real |
|---|---|---|---|
| Hero título | `1.875rem` → `md:2.25rem` | 600 | `.pedidos-hero-title` |
| Eyebrow | `11px`, tracking `0.25em`, uppercase | 600 | `.pedidos-eyebrow` |
| Título sección | `text-base`/`text-lg` | 600 | cabecera carrito, cards |
| Total (dominante) | `text-base`+ | 700 | totales carrito |
| Cuerpo | `0.875rem` (`text-sm`) | 400–500 | líneas, inputs |
| Label filtro | `0.75rem` | 600 | `.pedidos-filter-label` |
| Auxiliar | `10px`–`0.75rem` | 400–600 | embalaje, hints, badges |
| Numérico | `tabular-nums` | — | precios, totales, stock |

**Reglas:**
- Precios y totales **siempre** `tabular-nums` para alineación de columnas.
- Evitar tamaños < `10px`; revisar contraste de `text-[10px] text-slate-500` (ver diagnóstico §7).
- Mantener jerarquía: 1 título por región, cuerpo `text-sm`, auxiliares diferenciados por color/peso, no solo tamaño.

---

## 4. Espaciado

Escala coherente con los paddings de tokens (`1rem`, `1.5rem`, `3rem` en contenedor):

| Token conceptual | Valor | Uso |
|---|---|---|
| `space-xs` | `0.375rem` (6px) | gaps de botón (`.pedidos-btn`) |
| `space-sm` | `0.5rem`–`0.75rem` | padding inputs, gaps internos |
| `space-md` | `1rem` (16px) | padding card, gap grid mobile |
| `space-lg` | `1.5rem` (24px) | padding card KPI/CTA, gap grid desktop |
| `space-xl` | `2rem`–`3rem` | contenedor página (`lg`) |

Contenedor fluido: `.pedidos-contenedor-pagina` (`1rem` / `sm:1.5rem` / `lg:3rem`). El OrderShell **respeta** este contenedor.

---

## 5. Bordes y radios

| Token | Valor | Uso real |
|---|---|---|
| Radio card | `1rem` | `.pedidos-card`, `.pedidos-card-kpi/cta` |
| Radio workspace | `1.5rem` | `.pedidos-workspace` (panel carrito) |
| Radio input | `0.75rem` | `.pedidos-input`, `.pedidos-select` |
| Radio pill | `9999px` | `.pedidos-btn`, `.pedidos-badge` |
| Radio secciones internas | `0.75rem`–`0.5rem` | alertas, toggle |

**Acción de consolidación [nuevo]:** unificar los radios ad hoc del carrito/checkout (`rounded-lg`, `rounded-xl`) hacia esta escala. Preferir tokens antes que utilidades sueltas.

---

## 6. Sombras

| Token | Valor real | Uso |
|---|---|---|
| Sombra card | `0 10px 15px -3px rgba(15,23,42,0.08)` | `.pedidos-card` |
| Sombra workspace | `0 25px 50px -12px rgba(15,23,42,0.15)` | `.pedidos-workspace` |
| Sombra CTA | `0 10px 15px -3px rgba(14,165,233,0.25)` | `.pedidos-card-cta` |
| Sombra sticky bar [nuevo] | `0 -8px 20px -8px rgba(15,23,42,0.15)` | bottom bar mobile (sombra hacia arriba) |

---

## 7. Botones

Base: `.pedidos-btn` (pill, `9999px`, transición `0.3s`, foco de doble anillo).

| Variante | Token | Uso |
|---|---|---|
| Primario | `.pedidos-btn-primary` | confirmar PED, acciones clave |
| Fantasma sky | `.pedidos-btn-ghost-sky` | acciones secundarias sky |
| Oscuro | `.pedidos-btn-dark` / `.pedidos-btn-search` | búsqueda/hero |
| Peligro | `.pedidos-btn-danger` | vaciar, anular |
| Outline hero | `.pedidos-btn-outline-hero` | acciones sobre hero |
| Gradiente `@deprecated` | `.pedidos-btn-gradient` | **solo** acciones de hero en listados/presupuestos (pantalla completa); PROHIBIDO como CTA de venta/masivo (usar `.pedidos-btn-primary`) |

**Botones por modo [nuevo]** (para el CTA de confirmar del summary), consolidando lo que hoy se hace inline (líneas 204–210 de `compra_mayorista.html`):

```css
/* Añadir a pedidos_page_styles.html */
.pedidos-btn-modo-ped { color:#fff; background: rgb(2 132 199); }
.pedidos-btn-modo-ped:hover { background: rgb(14 165 233); }
.pedidos-btn-modo-pre { color:#fff; background: rgb(245 158 11); }
.pedidos-btn-modo-pre:hover { background: rgb(217 119 6); }
.pedidos-btn-modo-dev { color:#fff; background: rgb(244 63 94); }
.pedidos-btn-modo-dev:hover { background: rgb(225 29 72); }
```

**Reglas:** área táctil mínima `2.75rem`; estado `:disabled` con `opacity-50` + `pointer-events-none` (ya usado); un solo botón primario por región.

---

## 8. Inputs

Base: `.pedidos-input` / `.pedidos-select` (radio `0.75rem`, borde `slate-200`, foco sky anillo `3px`).

**Acción [nuevo]:** migrar los inputs inline del carrito/checkout (cantidad, desc pie, PV, forma entrega, observaciones — líneas 151–199) a tokens:
- Input de cantidad → `.pedidos-input` variante compacta `.pedidos-input-qty` (ancho fijo, `text-right`, `tabular-nums`).
- Select PV → `.pedidos-select`.
- Textarea observaciones → `.pedidos-input` con `rows`.

```css
/* [nuevo] variante compacta numérica */
.pedidos-input-qty {
  width: 4rem;
  text-align: right;
  font-variant-numeric: tabular-nums;
  padding: 0.375rem 0.5rem;
}
```

En mobile mantener `min-height: 2.75rem` y `font-size: 1rem` (ya definido en `@media (max-width: 767px)`), para evitar zoom de iOS y mejorar toque.

---

## 9. Tablas

Base: `.pedidos-table` + `.pedidos-table-shell` (scroll horizontal). Encabezado uppercase `0.75rem` slate.

**Uso en OrderShell:**
- **Resultados de búsqueda:** ya usan tabla propia en el include TPV con `role="listbox"`. Mantener y alinear estilos de header al token `.pedidos-table thead`.
- **Líneas del carrito (desktop):** adoptar `.pedidos-table` con columnas Producto · UOM · Cant · P.unit · Total · (quitar).
- **Mobile:** **no** usar scroll horizontal; degradar a `OrderLineMobileCard` (ver `06-componentes.md`).

---

## 10. Badges

Base: `.pedidos-badge` (pill, `0.75rem`, 600).

| Badge | Color | Uso |
|---|---|---|
| Promo | amber (`bg-amber-100 text-amber-800`) | producto en promoción (ya existe en TPV) |
| Modo PED/PRE/DEV | sky/amber/rose | chip de modo en header |
| Estado stock [nuevo] | slate/amber | "Sin stock" / "Bajo" informativo |
| Autorizado | emerald | crédito autorizado |
| Borrador [nuevo] | slate | "Borrador guardado" en summary |
| Lista de precios | slate + chip sky | `.pedidos-badge-lista` (solo lectura + link PDF); **token compartido** por pedido simple y masivo (REQ-UI-04) |

---

## 11. Estados

| Estado | Patrón visual | Referencia |
|---|---|---|
| Loading | texto "Cargando…" + [nuevo] skeleton opcional | include TPV línea 83 |
| Empty (carrito) | mensaje centrado + hint | `compra_mayorista.html` 137–142 |
| Empty (búsqueda) | "Sin resultados / Escribí o escaneá…" | include TPV 84–92 |
| Éxito checkout | banda por modo (emerald/amber/rose) | `compra_mayorista.html` 97–120 |
| Error | mensaje rose + `aria-live` [nuevo] | `flash()` |
| Deshabilitado | `opacity-50` + `pointer-events-none` | botón confirmar |
| Selección (fila) | `bg-sky-100 border-l-4 border-sky-500` | include TPV 65–68 |

`.pedidos-alert-info` y `.pedidos-empty` ya definidos se reutilizan.

---

## 12. Patrones de interacción

- **Foco visible universal:** doble anillo `#fff` + `sky-500` (`.pedidos-btn:focus-visible`, líneas 62–65). Extender a filas y controles del summary.
- **Transiciones:** `all 0.3s` en botones; `background-color 0.15s` en filas/toggle. No exceder ~300ms.
- **Navegación de teclado (TPV):** ↑↓ mover, Enter agregar, Esc volver al buscador (contrato ya implementado). **No romper** al refactorizar.
- **Modales del canon [nuevo]:** overlay `bg-slate-900/50`, dialog `.pedidos-card` con `role="dialog"`, `aria-modal`, focus trap, cierre con `Esc`. Reemplaza `confirm()`/`prompt()` nativos.
- **`aria-live` [nuevo]:** región para anunciar agregado/error/éxito.
- **Sticky:** header y summary con `position: sticky`; bottom bar mobile con sombra hacia arriba `[nuevo]`.

---

## 13. Dark mode

Todos los tokens ya definen su par `.dark`. Regla: cualquier token nuevo **debe** incluir su variante dark (borde `slate-800/700`, superficie `slate-900`, texto `slate-100/200`), siguiendo el patrón existente.

---

## 14. Anti-patrones (prohibido)

- ❌ Introducir violeta/purple genérico fuera del único `.pedidos-btn-gradient` acotado (y este último **no** debe usarse como CTA de venta/masivo).
- ❌ Crear un archivo de estilos paralelo por template; todo va a `pedidos_page_styles.html`.
- ❌ Inputs/botones con utilidades Tailwind sueltas cuando existe token.
- ❌ Colores de modo cruzados (p. ej. DEV en sky).
- ❌ Animaciones decorativas o > 300ms.
- ❌ Calcular/formatear importes con lógica propia distinta de `money()` sobre datos del backend.

El uso concreto de estos tokens por componente se detalla en `06-componentes.md`.
