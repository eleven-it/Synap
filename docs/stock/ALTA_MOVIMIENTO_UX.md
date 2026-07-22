# Alta de movimiento de stock — mejoras de UX (Synap)

**Plantilla:** `stock/templates/stock/alta_movimiento.html`
**Objetivo:** Mejor jerarquía visual, menos ruido y alineación con el acento violeta del shell Synap, **sin cambiar** lógica Alpine.js, `id` de campos, envíos ni validaciones.

## Rediseño artículos-first (pantalla única, full-width)

**Fecha:** 22/07/2026.
**Motivación:** las pestañas “Datos del movimiento” / “Artículos” forzaban un flujo secuencial y ocultaban el trabajo principal (cargar renglones). El contenedor `max-w-5xl` desperdiciaba ~20-25% del ancho, justo lo que necesitan las tablas de artículos. El botón **Continuar** solo cambiaba de pestaña y perdía sentido en pantalla única.

### Cambios de layout

1. **Contenedor full-width (patrón MPR).** Se eliminó `max-w-5xl`. Ahora la pantalla usa
   `mx-auto w-full min-w-0 max-w-none px-3 sm:px-4 md:px-6 lg:px-8 xl:px-10 2xl:px-12`,
   la misma convención de ancho que las pantallas MPR / dashboards de reportes
   (ver `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`). Las tablas siguen usando
   `overflow-x-auto` cuando hace falta.

2. **Header de página compacto.** Título + botón de ayuda + subtítulo corto nuevo:
   “Defina la cabecera e ingrese los artículos del movimiento.” (sin mencionar pestañas).

3. **Eliminación de las pestañas.** Se quitó por completo el `role="tablist"` y los
   `x-show="tabActivo === '...'"` de los paneles. La propiedad `tabActivo` se eliminó del
   estado Alpine (no quedó código muerto).

4. **Cabecera del movimiento (compacta y colapsable).** La cabecera dejó de ser un card
   grande tipo hero y pasó a ser una sección densa **colapsable** (`x-data="{ cabeceraAbierta: true }"`,
   por defecto **abierta**):
   - Barra superior con botón de colapso (chevron `expand_more` que rota), título
     “Cabecera del movimiento” e indicador **“Datos incompletos”** cuando falta la
     cabecera mínima (`!cabeceraMinimaCompleta`).
   - Al colapsar, muestra un **resumen** con chips: motivo, depósito origen (→ destino si
     aplica) y fecha en formato **dd/MM/yyyy** (según regla de fechas Synap).
   - Controles densificados: inputs/selects a `h-10`, franja principal con `gap-3`,
     `space-y-4` entre grupos y **Detalle** con `rows="2"`.
   - Objetivo: que la cabecera ocupe poco alto y los artículos predominen.

5. **Artículos = workspace principal.** Sección inmediatamente debajo, **siempre visible**,
   con encabezado propio: ícono `inventory_2`, título visible **“Artículos”** y **contador
   de renglones** (“N renglón/renglones”). Debajo, la búsqueda + tabla desktop y las cards
   mobile **tal como estaban** (se preservaron IDs, `x-ref`, handlers y el dropdown de
   sugerencias). El aviso `!cabeceraMinimaCompleta` sigue bloqueando el agregado de artículos.

6. **Pie de acciones fijo (sticky).** Barra `sticky bottom-0` con fondo `white/slate` y
   `backdrop-blur` (full-bleed mediante márgenes negativos que compensan el padding del
   contenedor). Solo dos acciones:
   - **Cancelar** (secundario con borde).
   - **Confirmar movimiento** (`emerald-600`, deshabilitado sin renglones o mientras guarda).
   - Se **eliminó** el botón **Continuar** (ya no tiene sentido en pantalla única).

### Cambios de comportamiento Alpine (mínimos, sin romper lógica)

- Se eliminó `tabActivo` del estado y todas sus referencias de UI.
- `setDefaultESDesdeMotivo()` se sigue llamando en `@change` del motivo y ahora **también
  en `init()`** (al cargar la pantalla), para que el valor por defecto de Entrada/Salida
  quede aplicado sin depender del cambio de pestaña.
- **No** se cambiaron firmas de APIs, payloads, validaciones ni modales existentes
  (resumen, lote, series, peso, pedidos internos/PEDI, proyectos, escáner mobile).
- Copys actualizados: se reemplazó “primera pestaña” / “siguiente pestaña” por
  referencias a “la cabecera”.

### Estilo

- Se mantuvo el design system Synap: Tailwind + Material Icons + Alpine, paleta **slate +
  acento purple**, dark mode y focus rings violeta existentes.
- Panel de artículos con más carácter de “workspace”: borde/sombra suave, encabezado con
  separador y padding útil, tabla aprovechando el ancho completo.

## Iteración «concepto pedido masivo» — contexto denso (22/07/2026)

**Motivación:** tras el rediseño artículos-first, la cabecera seguía con labels
apilados verticalmente (`label` arriba + control abajo), controles `h-10` y
bastante whitespace, ocupando ~40 % del alto. Se pidió **compactar usando el mismo
concepto que «Carga masiva de pedidos»** (`ecom/templates/ecom/pedido_masivo_sucursales.html`).

### Qué se compactó

1. **Hero bar compacta (una fila).** El header pasó de card claro con subtítulo largo
   a una **barra `slate-800`** con título blanco a la izquierda y el botón de ayuda a la
   derecha. Se agregaron chips de estado en el hero: **“Datos incompletos”** (ámbar) o el
   **contador de renglones** (esmeralda). Se eliminó el subtítulo largo (el eyebrow de la
   tarjeta ya orienta).
2. **Tarjeta de contexto densa y colapsable** (equivalente a «Contexto comercial»):
   - **Eyebrow** uppercase pequeño “Cabecera del movimiento” + **chevron** toggle
     (`contextoAbierto`, renombrado desde `cabeceraAbierta`).
   - **Al colapsar:** resumen inline `Label: valor` (Motivo, Depósito origen → destino,
     Fecha en **dd/MM/yyyy**), estilo `pm-context-summary`.
   - **Al expandir:** **grid 2 columnas** (`lg:grid-cols-2`, `gap-x-6 gap-y-2`) con filas
     **label inline + control en la misma línea** (`.ims-field-row` con `display:flex;
     align-items:center`), en vez de label arriba + campo abajo.
   - **Controles densos:** `h-8`, `text-xs`, `rounded-md`, clase `.ims-input-dense`
     (min-height 2rem). Botones PEDI/Proyecto también `h-8`.
   - **Detalle:** pasó de `textarea` de 2–3 filas a un **input de una sola fila densa**
     que ocupa las 2 columnas (`lg:col-span-2`). PEDI también ocupa 2 columnas.
   - **Helper text verbose eliminado:** la aclaración bajo *Referencia* y bajo *Cantidad
     armado* se movieron a `title` (tooltip), sin ocupar alto.
3. **Artículos = resto del viewport.** Encabezado más bajo (`px-3 py-2`, ícono/título más
   chicos), cuerpo con menos padding (`p-3`) y la sección con `flex-1 min-h-0` para tomar
   el espacio restante. **No** se impuso `height:100dvh` ni scroll anidado (riesgo con
   modales/scanner en stock): se prioriza densidad + flujo de página normal.
4. **Pie de acciones más bajo:** botones `min-h-8`, `py-1.5 text-xs`, `rounded-lg`
   (antes `py-2.5/3`, `text-sm`). Sigue siendo sticky full-bleed.

### Estilos locales (sin acoplar ecom)

Se agregó un `<style>` **scoped** en la plantilla stock con clases propias inspiradas en
`pm-*` (no se importó `pedidos_page_styles.html`, para no acoplar ecom):

- `.ims-context-card` — degradado suave (purple/slate) del panel de contexto.
- `.ims-field-row` — `display:flex; align-items:center; gap:.5rem` (label + control inline).
- `.ims-label-inline` — label a la izquierda, `min-width:6.5rem`, `11px`, slate-600/300.
- `.ims-input-dense` — `font-size:.75rem; min-height:2rem` + focus ring **purple** (no sky).
- `.ims-input-date`, `.ims-context-summary` — detalles de fecha nativa y resumen.

**Mapeo pedido-masivo → stock:** `pm-hero-bar`→hero `slate-800`; `pm-context-card`→
`.ims-context-card`; `pm-field-row`→`.ims-field-row`; `pm-label-inline`→`.ims-label-inline`;
`pm-input-dense`→`.ims-input-dense`; `pm-context-summary`→`.ims-context-summary`. El acento
**sky** de ecom se reemplazó por **purple** (design system stock).

### Sin cambios de lógica

No se tocó lógica Alpine de negocio, IDs de campos/modales, handlers `@change`/`@click`,
`x-model`, `x-ref`, APIs ni validaciones. Solo cambió la presentación (markup + estilos).

## Iteración — tabla de artículos prolija (22/07/2026)

Refactor visual de la sección Artículos (solo frontend):

- **Avisos eliminados** (solo el copy; la lógica se mantiene):
  - «El tipo de movimiento (Entrada/Salida) queda fijo según el motivo elegido en la cabecera.»
    (`x-show="!puedeCambiarES"`).
  - Banner ámbar «Complete los datos mínimos del movimiento…» (`x-show="!cabeceraMinimaCompleta"`).
    El feedback ya lo da el chip **“Datos incompletos”** del hero. El botón **Agregar** sigue
    deshabilitado con `!cabeceraMinimaCompleta` (no se tocó la lógica).
  - Hint «Escriba en la fila de búsqueda y pulse Enter para agregar.» (ruido redundante).
- **Barra de ingreso fuera de la tabla:** el input de búsqueda dejó de vivir en una fila
  `colspan` desalineada dentro del `<tbody>`. Ahora es una **barra flex** encima de la tabla
  (Buscar artículo `flex-1` + Movimiento E/S + Cantidad + Embalaje/Peso condicionales +
  botón **Agregar**), patrón POS/matriz. Se preservan `x-ref="inputBusquedaArt"`, handlers
  (`buscarArticulosDebounce`, `onEnterFilaBusqueda`, `confirmarFilaBusqueda`, `filaBusqueda.*`)
  y el dropdown de sugerencias (`x-ref="listaResultadosBusqueda"`), ahora **anclado bajo la barra**.
- **Tabla más limpia:** `table-fixed` con anchos coherentes; **sin Cod. sist.**; **Cod. manual**
  `w-40` sin truncate; **Descripción** absorbe el sobrante; Movimiento / Cantidad / Nro. ped. /
  Lote / Series / Eliminar con anchos fijos. Se elimina el hueco enorme entre columnas.
- **Headers consistentes:** una sola línea (`whitespace-nowrap`), `text-xs font-semibold
  uppercase tracking-wide text-slate-500`, padding `px-2 py-2`, fondo `bg-slate-50
  dark:bg-slate-700/50`, borde inferior sutil. «Nro. Pedido int.» se acortó a **«Nro. ped.»**
  con `title="Nro. pedido interno"` para no partirse en dos líneas.
- **Celdas:** `text-sm`, `px-2 py-1.5`, `truncate` + `:title` con el valor completo en
  Cod. manual / Descripción / Nro. ped.
- **Estado vacío único:** fila con `colspan` dinámico (`8 + embalaje + peso`) “No hay artículos
  agregados…” en desktop; el bloque mobile conserva su propio mensaje. Sin duplicados por viewport.
- **Tooltip «Detalle línea»:** eliminado (hover sobre renglones). La información ya está
  en la tabla; no se recrea el DOM flotante ni los handlers `mouseenter`/`mouseleave`.

## Dropdown de búsqueda — solo nombre + teclado (22/07/2026)

- Cada ítem del dropdown muestra **solo `Descripcion`** (nombre). Se eliminaron precios
  (P. Costo / PV 1 / Alic) y el desglose de stock por depósito.
- Navegación con teclado: **↓ / ↑** resaltan ítems (`idxDropdown`), **Enter** selecciona el
  resaltado (o cae al flujo por código si no hay lista), **Esc** cierra el dropdown.
- El primer ítem seleccionable queda resaltado al recibir resultados; el resaltado hace
  `scrollIntoView` dentro de la lista.

## Historial previo (acento y jerarquía)

- Acento **purple** coherente con el navbar Synap en enlaces, botones secundarios, escáner,
  tabla, modales y sugerencias.
- Títulos duplicados de paneles resueltos con `<h2 class="sr-only">` (accesibilidad sin ruido).
- Texto auxiliar bajo **Referencia** aclarando que es lista parametrizada (opcional).
- **PEDI:** el bloque “Pedidos internos a depósito” usa `md:col-span-3` y botón `w-full`
  centrado para no quedar a ~1/3 del ancho cuando es el único campo visible.

## No modificado (a propósito)

- Handlers `@click`, `@change`, `x-model`, `x-show`, IDs de campos y modales, `x-ref`,
  atributos ARIA esenciales y toda la lógica de negocio.
- **Backend**: vistas, servicios, formularios Django, APIs y URLs. El rediseño es
  **solo frontend** (plantilla + esta documentación).

## Verificación manual sugerida

- Cargar la pantalla: la cabecera aparece abierta; si faltan datos mínimos, se ve el chip
  “Datos incompletos” del hero (Agregar queda deshabilitado).
- Colapsar la cabecera: aparece el resumen (motivo, depósitos, fecha dd/MM/yyyy) y los
  artículos ganan espacio.
- En desktop ancho: la tabla de artículos usa todo el ancho; el pie queda fijo al hacer scroll.
- Buscar artículo: el dropdown muestra solo el nombre; ↓/↑ navega, Enter selecciona, Esc cierra.
- Cambiar el motivo: se recalcula Entrada/Salida por defecto y aparecen/ocultan campos
  condicionales (destino, cliente, vendedor, OPT, valor variable, PEDI, proyecto).
- Confirmar movimiento: abre el modal de resumen y guarda como antes; Cancelar sale.
- Mobile: búsqueda + cards + escáner de código de barras siguen operativos.
