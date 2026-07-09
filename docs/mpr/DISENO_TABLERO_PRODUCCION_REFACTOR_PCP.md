# Diseño UX/UI — Refactor Tablero de producción (alineación PCP)

**Rol:** Product Design  
**Fecha:** 07/07/2026  
**Estado:** Implementado (07/07/2026)  
**Canon Synap:** `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`, `docs/mpr/VENTANA_PACK_LAYOUT_DENSIDAD.md`  
**Negocio / fórmulas:** `docs/mpr/BEST_SOX_PCP_PRODUCCION_ALINEACION.md` §9  

---

## 1. Objetivo de experiencia

El operario de planta abre el tablero para responder en segundos:

1. **¿Qué debo enviar ahora?** → columna **Resta urgente** (pares).
2. **¿Cuánto falta en total (con reserva)?** → columna **Resta total** (secundaria).
3. **¿Dónde está el stock?** → bloque de etapas pipeline.
4. **¿Cuánto envío?** → inputs ligados a Resta urgente.

La pantalla debe sentirse **continua** con OPT demanda (`ventana_pack.html`) y el hero MPR (`slate-800` + acentos `purple`), no como un informe de reportes (`gray-*`).

---

## 2. Auditoría del estado actual

| Aspecto | Hoy | Problema | Acción |
|---------|-----|----------|--------|
| Título / migas | «Tablero de demanda consolidado» | No coincide con lenguaje planta ni PCP | Renombrar a **Tablero de producción** |
| Columna 2 | «Pendiente» en `red-600` | Mezcla urgente + reserva; sin grupo visual | **Resta urgente** con patrón rose de `ventana_pack` |
| Resta total | No existe | PCP col H invisible | Nueva columna secundaria |
| Stock etapas | 6 columnas planas mismo peso visual | Difícil escanear; Total verde compite con urgente | Agrupar cabecera «Stock en pipeline»; atenuar etapas |
| Total | `green-700` semibold | Parece «éxito» no «inventario» | Neutro `slate-700`; verde solo en KPI si aplica |
| Actualizar vista | `amber-600` | Desentonó vs MPR (`VENTANA_PACK_LAYOUT_DENSIDAD`) | **`purple-600`** como en demanda |
| Toggle | «Unidades» | Best Sox: unidad = par | Etiqueta **Pares** |
| Filtro chip | «Solo pendientes» `purple-700` | Semántica incorrecta | **«Solo urgentes»** con acento `rose` activo |
| Cabeceras tabla | Una fila plana | PCP usa grupos (Datos / Resta / Stock) | **Dos filas** `thead` con `colspan` |
| Enviar | Aislado a la derecha | No se percibe vínculo con urgente | Borde `emerald` + alineación visual con grupo operativo |
| KPIs totales | No hay | PCP muestra 28.522 / 12.470 docenas | **Franja KPI** bajo hero (opcional compacta) |

---

## 3. Arquitectura de información (columnas)

Orden alineado a PCP Produccion + operación MPR (bloque **Demanda a producir** = 6 columnas):

```
┌─────────────┬────────────────── Demanda a producir ──────────────────┬── En curso ──┬──────────── Stock en pipeline ────────────┬────────┐
│  Artículo   │ Pedido │ Reserva │ Resta total (P|D) │ Resta urgente (P|D) │ Fabricando │ Prod │ 2da │ Semi │ Desp.* │ Total │ Enviar │
└─────────────┴────────┴─────────┴─────────────────────┴─────────────────────┴────────────┴──────┴─────┴──────┴────────┴──────┴───────┴────────┘
  sticky-left    pares    pares        pares + docenas ÷12      pares + docenas ÷12
```

| # | Columna | Rol UX | Presentación |
|---|---------|--------|--------------|
| 1 | Artículo | Identidad | Sticky |
| 2 | **Pedido** | Demanda pedido | Solo **pares** (entero) |
| 3 | **Reserva** | Demanda reserva pack | Solo **pares** (`dem_res`) |
| 4–5 | **Resta total** | Brecha total (pedido + reserva) | **Pares** + **Docenas** (÷12 decimal PCP) |
| 6–7 | **Resta urgente** | **Primaria** — envío | **Pares** + **Docenas**; inputs Enviar |
| 8 | Fabricando | Compromiso ledger | Toggle Pares/Docenas; cupo = envíos − acreditado |
| 9–12 | Etapas + Desperdicio | Lectura stock pipeline componente | Producido, 2da, Semi, Desperdicio — **sin Terminado** |
| 13 | Total | Suma pipeline componente | Sin Desperdicio ni Terminado |
| 14 | Enviar | Input acción | CTA emerald; tope `a_enviar` |

**Cabecera tabla:** tres filas `thead` — grupo «Demanda a producir» (`colspan=6`), subgrupos Resta total / Resta urgente (`colspan=2`), fila Pares | Docenas.

\* Desperdicio: itálica + `slate-400`, tooltip «No suma al Total».

**Fase posterior (no bloquea):** Stock crudo (PCP J/K) como columna informativa tras Resta total.

---

## 4. Sistema visual — tokens Synap MPR

### 4.1 Paleta por función

| Token | Tailwind (claro) | Tailwind (oscuro) | Uso |
|-------|------------------|-------------------|-----|
| **Shell** | `bg-slate-50` | `dark:bg-slate-900` | Fondo página (mantener) |
| **Hero** | `bg-slate-800 border-slate-700` | `dark:bg-slate-900` | Encabezado (mantener) |
| **Acento navegación** | `text-purple-600` | `dark:text-purple-400` | Migas, filtros, Actualizar |
| **Urgente / resta** | `text-red-600`, `border-l-rose-200/80` | `dark:text-red-400`, `dark:border-l-rose-900/50` | Resta urgente > 0 — **mismo patrón que `ventana_pack` L198** |
| **Urgente fondo celda** | `bg-rose-50/40` si > 0, si no `bg-slate-50/90` | `dark:bg-rose-950/20` / `dark:bg-slate-800/35` | Solo columna Resta urgente |
| **Resta total** | `text-slate-700` | `dark:text-slate-300` | Sin rojo salvo = 0 → `slate-400` |
| **Fabricando** | `text-violet-700` | `dark:text-violet-300` | Diferencia de «comprometido» vs stock físico |
| **Stock etapas** | `text-slate-600` | `dark:text-slate-400` | Cuerpo tabla |
| **Total pipeline** | `text-slate-800 font-medium` | `dark:text-slate-200` | **Quitar verde** |
| **Desperdicio** | `text-slate-400 italic` | `dark:text-slate-500` | Mantener |
| **CTA enviar** | `bg-emerald-600` | `dark:bg-emerald-700` | Botón + focus inputs envío |
| **Input envío focus** | `ring-emerald-500/50` | igual | Vínculo con CTA |

**No usar:** `amber` en Actualizar (unificar purple). **No usar:** `green-700` en Total.

### 4.2 Tipografía

| Elemento | Clase | Notas |
|----------|-------|-------|
| H1 hero | `text-lg sm:text-xl md:text-2xl font-bold tracking-tight text-white` | Mantener |
| Migas | `text-xs` | Mantener |
| Labels filtros | `text-[10px] font-medium uppercase tracking-wide text-slate-400` | Mantener |
| **Cabecera grupo tabla** | `text-[10px] font-semibold uppercase tracking-wide` | Nueva fila 1 `thead` |
| Cabecera columna | `text-xs font-semibold text-slate-600` | Fila 2 `thead` |
| Código artículo | `text-sm font-semibold tabular-nums text-slate-800` | Mantener |
| Descripción | `text-xs sm:text-sm leading-snug text-slate-600` | Reducir 1px en móvil para densidad |
| **Resta urgente valor** | `text-sm font-semibold tabular-nums` | Destacar |
| Resta total valor | `text-sm tabular-nums font-medium` | Un peso menos |
| Stock / fabricando | `text-xs sm:text-sm tabular-nums` | Densidad operativa |
| Modo docenas secundario | `text-[11px] text-slate-500` | Línea baja «N doc · M pares» |
| Pie de tabla | `text-[11px] text-slate-400` | Mantener |

**Fuente:** hereda `base_app.html` (system UI). Cantidades: **siempre `tabular-nums`**.

### 4.3 Espaciado y densidad

| Zona | Especificación |
|------|----------------|
| Contenedor | `mpr-contenedor-pagina` + padding responsive (canon) |
| Hero | `p-3 sm:p-4`, `mb-3 sm:mb-4` (como `ventana_pack`) |
| Celda artículo | `px-4 py-2.5` sticky; `min-w-[18rem] sm:min-w-[20rem]` |
| Celdas numéricas | `px-3 py-2` (reducir de `py-2.5` en bloque stock) |
| Grupo urgente | `px-3 py-2.5` (más aire — columna crítica) |
| Separador grupos | `border-l border-slate-200 dark:border-slate-700` entre bloques |
| Tabla min-width | `min-w-[80rem]` (11 cols + grupos) |
| Scroll region | `rounded-lg border border-slate-200 shadow-sm` + `h-[min(28rem,52vh)] min-h-[14rem]` en viewport operativo |

---

## 5. Componentes — especificación detallada

### 5.1 Hero y KPIs (como PCP fila I2/M2)

Debajo del título, **franja KPI compacta** (una línea en desktop, wrap en móvil):

```
┌──────────────────────────────────────────────────────────────┐
│  Docenas resta urgente: 12.470    Docenas resta total: 28.522 │
│  (suma visible según modo presentación / filtro activo)        │
└──────────────────────────────────────────────────────────────┘
```

| Elemento | Estilo |
|----------|--------|
| Contenedor KPI | `flex flex-wrap gap-4 border-t border-slate-700 pt-2 mt-2` |
| Label KPI | `text-[10px] uppercase tracking-wide text-slate-400` |
| Valor urgente | `text-sm font-bold tabular-nums text-rose-300` |
| Valor total | `text-sm font-semibold tabular-nums text-slate-200` |

Solo visible si hay filas tras filtro. Recalcula en servidor (no Alpine).

### 5.2 Filtro «Solo urgentes»

| Estado | Clases |
|--------|--------|
| Activo | `bg-rose-600/90 text-white` + icono `filter_alt` |
| Inactivo | `border border-slate-600 text-slate-300 hover:bg-slate-700` |

Texto: **«Solo urgentes»** (no «pendientes»). Query: `solo_urgente=1`.

### 5.3 Toggle presentación

Actualizar `toggle_presentacion_cantidad.html` en contexto tablero:

| Opción | Etiqueta |
|--------|----------|
| `docenas` | Docenas |
| `unidades` | **Pares** |

Subtexto en modo docenas: **«N docenas · M pares»** (no «unidades»).

### 5.4 Tabla — cabecera en dos filas

**Fila 1 (grupos):**

| Grupo | colspan | Fondo thead |
|-------|---------|-------------|
| Artículo | 1 | `bg-slate-100 dark:bg-slate-800` |
| Demanda a producir | 2 | `bg-rose-50/80 dark:bg-rose-950/25` + texto `text-rose-800 dark:text-rose-200` |
| En curso | 1 | `bg-violet-50/60 dark:bg-violet-950/20` |
| Stock en pipeline | 6 | `bg-slate-100 dark:bg-slate-800` |
| Acción | 1 | `bg-emerald-50/60 dark:bg-emerald-950/20` |

**Fila 2 (columnas):** nombres cortos; Resta urgente con `title` tooltip:

> «max(0, Dem. pedido − stock en proceso). 1 unidad = 1 par. Paridad PCP.»

### 5.5 Filas de datos — estados

| Condición | Tratamiento fila |
|-----------|------------------|
| `resta_urgente > 0` | Fila normal; celda urgente resaltada |
| `resta_urgente = 0` y `resta_total > 0` | Fila `opacity-90`; urgente en gris — **solo reserva pendiente** |
| Ambas = 0 | Oculta si «Solo urgentes»; en «Ver todos» gris tenue |
| Hover | `hover:bg-slate-50/80 dark:hover:bg-slate-800/40` (mantener) |

**Celda Resta urgente (> 0):**

```html
<!-- patrón canónico (ventana_pack) -->
<td class="border-l-2 border-l-rose-200/80 bg-rose-50/30 px-3 py-2.5 text-right text-sm font-semibold tabular-nums text-red-600 dark:border-l-rose-900/50 dark:bg-rose-950/20 dark:text-red-400">
```

**Celda Resta total:** sin borde rose; `font-medium text-slate-700`.

**Celda Fabricando:** si > 0, `text-violet-700 dark:text-violet-300` (diferenciación vs stock).

### 5.6 Columna Enviar

- Inputs deshabilitados si `resta_urgente <= 0` (no `pendiente`).
- Precarga: docenas/pares desde `resta_urgente`.
- Contenedor: `rounded-lg border border-emerald-200/80 bg-emerald-50/30 dark:border-emerald-800/50 dark:bg-emerald-950/15 p-1`.
- Placeholders: `doc` / `par` (no `u`).
- Hidden: `resta_urgente_{{ id }}` para validación POST.

Botón flotante **Enviar a producción**: mantener `emerald-600` a la derecha de búsqueda.

### 5.7 Modal confirmación envío

Mantener patrón actual (`slate` card + `emerald` confirmar). Copy: «¿Confirma enviar N componentes a producción?» — sin cambio estructural.

---

## 6. Responsive y accesibilidad

| Breakpoint | Comportamiento |
|------------|----------------|
| `< sm` | Hero acciones en columna; KPI en stack; tabla scroll horizontal obligatorio |
| `sm+` | Filtros y acciones en una fila; hint scroll horizontal |
| Sticky | Artículo `left-0 z-20`; thead `top-0 z-10` |

**A11y:**

- `aria-label` en región tabla: «Tablero de producción por componente».
- Grupos `thead` con `scope="colgroup"` + `abbr` en Resta urgente.
- Contraste rojo urgente: usar `red-600` sobre blanco / `red-400` en dark (WCAG AA con `font-semibold`).
- Focus visible: `focus-visible:ring-2 ring-purple-500` (navegación) / `ring-emerald-500` (envío).

---

## 7. Wireframe ASCII (desktop)

```
┌─ Hero slate-800 ─────────────────────────────────────────────────────────────┐
│ Producción / Tablero de producción                                            │
│ [Fechas PED] [Filtrar]     [Docenas|Pares] [Actualizar] [Parte] [Clasif.] …  │
│ Última act: 07/07/2026 10:30    [■ Solo urgentes]                             │
│ ─────────────────────────────────────────────────────────────────────────── │
│ DOCENAS RESTA URGENTE: 12.470        DOCENAS RESTA TOTAL: 28.522            │
└──────────────────────────────────────────────────────────────────────────────┘
  [scroll hint]                              [Buscar…] [Enviar a producción ▶]

┌─ Tabla ──────────────────────────────────────────────────────────────────────┐
│ Artículo │══ Demanda a producir ══│En curso│════ Stock en pipeline ════│Env│
│          │ Resta urg. │ Resta tot. │ Fabr.  │Prod│2da│Semi│Desp│Term│Tot│   │
│──────────┼────────────┼────────────┼────────┼────┼───┼────┼────┼────┼───┼───│
│ SEAT…    │ ▌  120     │    120     │   0    │ 0  │ 0 │  0 │ 0  │ 0  │ 0 │[▢]│
│ M003…    │ ▌   20     │     20     │   0    │ 0  │ 0 │  0 │ 0  │ 0  │ 0 │[▢]│
└──────────────────────────────────────────────────────────────────────────────┘
  ▌ = borde rose (urgente > 0)
```

---

## 8. Checklist de implementación (handoff dev)

- [ ] Renombrar títulos/migas: «Tablero de producción»
- [ ] Servicio: `resta_urgente`, `resta_total`, `stock_proceso`, KPIs suma
- [ ] `thead` dos filas con `colgroup` y fondos por grupo
- [ ] Aplicar tokens §4.1 (quitar verde Total, amber Actualizar → purple)
- [ ] Toggle «Pares» + copy docenas «· M pares»
- [ ] Filtro `solo_urgente` + chip rose
- [ ] Enviar atado a `resta_urgente`
- [ ] Actualizar `TABLERO_CONSOLIDADO.md` columnas canónicas
- [ ] Captura comparativa antes/después para QA visual

---

## 9. Referencias cruzadas

| Documento | Relación |
|-----------|----------|
| `BEST_SOX_PCP_PRODUCCION_ALINEACION.md` | Fórmulas y decisiones producto |
| `VENTANA_PACK_LAYOUT_DENSIDAD.md` | Patrón grupo Urgente rose |
| `ventana_pack.html` L198–202 | Implementación referencia urgente |
| `tablero_produccion.html` | Pantalla a refactorizar |
| `FUENTE_VERDAD_UI_REPORTES_MPR.md` | Canon MPR slate + purple |

---

## 10. Criterios de aceptación UX

1. Un operario identifica **Resta urgente** en &lt; 2 s sin leer el pie de tabla.
2. **Resta total** es legible pero claramente **secundaria** respecto a urgente.
3. La pantalla es **visualmente coherente** con OPT demanda (mismos acentos rose/purple/emerald).
4. En modo docenas, el texto secundario dice **pares**, no unidades.
5. Con «Solo urgentes», no aparecen filas con urgente = 0 salvo búsqueda explícita que las traiga de «Ver todos» (navegación previa).
