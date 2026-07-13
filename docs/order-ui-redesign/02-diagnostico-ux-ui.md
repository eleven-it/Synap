# 02 · Diagnóstico UX/UI — Toma de pedidos

- **Fecha:** 10/07/2026
- **Pantalla analizada:** `/ecom/mayoristapp/compra/`
- **Archivos base:**
  - `ecom/templates/ecom/compra_mayorista.html` (vista + objeto Alpine `compraMayorista()`)
  - `ecom/templates/ecom/base_pedidos.html` (layout/hero)
  - `ecom/templates/ecom/includes/pedidos_page_styles.html` (tokens `.pedidos-*`, `.compra-*`)
  - `ecom/templates/ecom/includes/pedidos_busqueda_articulos_tpv.html` (búsqueda TPV)
  - `ecom/templates/ecom/includes/pedidos_toggle_comprobante.html` (toggle PED/PRE/DEV)
  - `ecom/static/ecom/js/compra_mayorista_cliente.mjs`, `compra_mayorista_marcas.mjs`, `repetir_pedido_modal.js`

> Nota de método: este diagnóstico evalúa **presentación y experiencia**. Todo hallazgo asume la restricción de no tocar backend, cálculos ni APIs.

---

## 1. Fricciones del flujo

### 1.1 Checkout mezclado con el carrito
En `compra_mayorista.html` el panel derecho `.compra-carrito-panel` concentra en un solo bloque: cabecera del carrito, líneas, totales, **y** el checkout (punto de venta, forma de entrega, observaciones) y el botón de confirmar (líneas 128–211). El usuario no distingue con claridad "revisar el carrito" de "completar datos del comprobante". Los campos de checkout compiten por atención con las líneas.

> Fricción: la acción primaria (confirmar) queda al fondo de un panel largo, después de campos secundarios.

### 1.2 Cambio de tipo con `confirm()` nativo
```390:404:ecom/templates/ecom/compra_mayorista.html
    async cambiarTipo(nuevo) {
      const t = String(nuevo || '').toUpperCase();
      if (!t || t === this.tipo) return;
      if (this.cart.items && this.cart.items.length) {
        const ok = confirm('¿Cambiar el tipo de comprobante? El carrito actual se mantiene pero el comportamiento de stock y confirmación cambia.');
        if (!ok) return;
      }
```
El `confirm()` del navegador rompe la estética Synap y no es traducible/estilable. Debe reemplazarse por un modal del canon (mismo patrón que el modal de pre-confirmación ya existente, líneas 216–234).

### 1.3 Embalaje sin selector real
El carrito muestra el embalaje cuando no es "Unidad":
```148:148:ecom/templates/ecom/compra_mayorista.html
              <p x-show="it.tipo_unidad && it.tipo_unidad !== 'Unidad'" class="text-[10px] text-slate-500 mt-0.5" x-text="`Embalaje: ${it.tipo_unidad}`"></p>
```
Pero al agregar siempre se fuerza `Unidad`:
```629:641:ecom/templates/ecom/compra_mayorista.html
    async agregarDesdeBusqueda(art) {
      const raw = art._raw || art;
      const item = {
        ...raw,
        _cant: 1,
        _tipo: (raw.presentacion && raw.presentacion.tipo_unidad_defecto) || 'Unidad',
      };
      await this.agregar(item);
```
El backend acepta `tipo_unidad` y `multiplicador` (método `agregar`, líneas 655–666) y expone `presentacion.opciones`, pero **la UI nunca ofrece elegir** entre Unidad / Bulto / Display. Hay lógica muerta (`embalaje`, `mostrarEmbalaje` en el estado, líneas 258, 352–357) sin punto de interacción.

### 1.4 Hint de barcode sin flujo
El input sugiere escaneo:
```11:19:ecom/templates/ecom/includes/pedidos_busqueda_articulos_tpv.html
      <input id="pedidos-busqueda-producto"
             type="text"
             x-model="searchProductos"
             placeholder="Código de barras, código o nombre… (↑↓ elegir, Enter agregar)"
```
No hay foco automático al cargar la pantalla ni manejo específico de lectura de barcode (sufijo Enter del lector cae en `onBusquedaProductosEnter`, que agrega la fila seleccionada, pero sin garantía de match exacto ni feedback de "no encontrado por código"). El hint promete algo que el flujo no acompaña.

### 1.5 Cliente se limpia al refresh (intencional, no comunicado)
`compra_mayorista_cliente.mjs` documenta que el cliente no se restaura desde sesión. Es una decisión de diseño válida, pero la UI no lo anticipa: si el operador recarga, pierde la referencia del cliente sin aviso previo. Falta microcopy o confirmación en acciones que impliquen recargar.

### 1.6 Repetir/PRE→PED sin previsualización de diferencias de precio
Al repetir un pedido se recalculan precios ("Precios actualizados", línea 288) pero no se muestran diferencias respecto al comprobante origen. El usuario no ve qué cambió.

---

## 2. Jerarquía visual

- **Hero potente, cuerpo plano.** El hero (`base_pedidos.html`, gradiente slate) tiene peso visual alto; el cuerpo, en cambio, presenta cliente/marcas/recientes/catálogo/carrito como una secuencia de cards de peso similar, sin una jerarquía que grite "primero cliente, después productos, después confirmar".
- **La acción primaria compite.** El botón "Revisar y confirmar" (líneas 204–210) es fuerte, pero está enterrado bajo checkout; en pantallas medianas queda fuera del viewport.
- **Totales sin dominancia suficiente.** El bloque de totales (líneas 163–175) usa `text-base font-bold` para el total; correcto, pero al estar embebido entre desc. al pie y checkout, pierde protagonismo.
- **Pedidos recientes ocupan ancho completo** (`md:col-span-3`, línea 81) antes del catálogo, empujando hacia abajo el área de trabajo real.

---

## 3. Navegación

- **Breadcrumb + hero** correctos y consistentes (`pedidos_breadcrumb.html`).
- **Toggle de modo en el hero** (`pedidos_toggle_comprobante.html`): buena ubicación, pero el cambio de modo altera comportamiento de stock/confirmación y hoy solo se advierte con `confirm()` nativo.
- **Post-confirmación:** el bloque de éxito (líneas 97–120) ofrece "Ver detalle / Ver listado / Nuevo comprobante / Ir al hub". Es claro, aunque aparece embebido en el grid y desplaza el layout.
- **Salida sin guardar:** no existe diálogo de "cambios sin guardar" al navegar fuera con carrito cargado (aunque el carrito es borrador persistente, el usuario no lo sabe).

---

## 4. Carga y estados

- **Loading de búsqueda:** manejado (`articulosGridLoading`, "Cargando…", línea 83 del include TPV). Correcto.
- **Empty states:** carrito vacío (líneas 137–142) y sin resultados (líneas 84–92 del include) están cubiertos con buen microcopy.
- **Abort de requests:** la búsqueda cancela peticiones en vuelo (`articulosBusquedaAbort`, líneas 502–506). Buena práctica ya presente.
- **Feedback de acción:** `flash()` (línea 715) muestra mensajes ok/error, pero es un `<p>` dentro del checkout (línea 202); en mobile puede quedar fuera de vista.
- **Confirmando:** el botón muestra "Confirmando…" (línea 209). Correcto.
- **Falta:** skeletons en carga inicial de contexto (`cargarContexto`) y estados de error de red diferenciados de errores de negocio.

---

## 5. Responsive

- **Grid principal `md:grid-cols-3`** (línea 78): catálogo 2 col + carrito 1 col. En el rango `md` (768–1024px) el carrito queda estrecho para líneas con descripción larga (se trunca con `truncate`, línea 146).
- **Scroll interno del carrito:** en desktop `.compra-carrito-scroll { max-height: 46vh }` (líneas 382–386); combinado con checkout debajo, el área útil de líneas es pequeña.
- **Mobile:** las reglas `@media (max-width: 767px)` (líneas 367–381) sueltan el `max-height` y agrandan inputs a `min-height: 2.75rem` (buena ergonomía táctil), pero **el total y el botón de confirmar no son sticky**: el operador scrollea todo el carrito para confirmar.
- **Listados secundarios:** las tablas (`listado_mayoristapp.html`) usan `pedidos-table-shell` con `overflow-x: auto` (tokens líneas 133), lo que produce scroll horizontal en móvil en lugar de degradar a tarjetas.

---

## 6. Accesibilidad (a11y)

**Aciertos existentes:**
- Combobox del cliente con `role="combobox"`, `aria-autocomplete`, `aria-controls` (líneas 42–44).
- Búsqueda TPV con `role="listbox"`/`role="option"`, `aria-selected`, label `sr-only` (include TPV, líneas 10, 45–46, 62–63).
- Toggle con `role="tablist"`/`role="tab"`, `aria-selected` (toggle, líneas 9–23).
- Foco visible: `.pedidos-btn:focus-visible` con doble anillo (tokens, líneas 62–65).
- Áreas táctiles: `min-h-[2.75rem]`/`min-h-[3rem]` en botones y inputs clave.

**Brechas:**
- **`confirm()`/`prompt()` nativos** no anuncian correctamente en algunos lectores y no respetan idioma/estilo.
- **Mensajes `flash`** no usan `aria-live`; los cambios de estado (agregado/error) no se anuncian.
- **Modal de resumen** (líneas 216–234) no declara `role="dialog"`, `aria-modal`, ni gestiona *focus trap* / retorno de foco / cierre con `Esc`.
- **Bloque de éxito** aparece dinámicamente sin `aria-live` ni foco dirigido.
- **Contraste de textos auxiliares** `text-[10px] text-slate-500` (embalaje, promo en carrito) puede quedar por debajo del umbral en modo claro.

---

## 7. Aspectos visuales

- **Consistencia con canon:** sólida. Usa `.pedidos-card`, `.pedidos-workspace`, `.pedidos-btn*`, familia slate/sky, y colores semánticos por modo (PED sky, PRE amber, DEV rose) tanto en toggle como en bordes de shell (tokens, líneas 339–363). **No** hay purple-on-white genérico salvo el gradiente decorativo `pedidos-btn-gradient` del botón PED (líneas 83–87), que conviene revisar para no introducir violeta fuera del canon.
- **Densidad:** media, correcta para ERP. El carrito por línea (líneas 143–159) es legible.
- **Inconsistencia de radios:** conviven `rounded-lg`, `rounded-xl`, `rounded-2xl`, `rounded-full` y tokens `.pedidos-card` (1rem) / `.pedidos-workspace` (1.5rem). Falta unificar a escala de tokens.
- **Inputs ad hoc:** varios inputs del carrito/checkout usan clases Tailwind inline (`rounded-lg border border-slate-200 …`, líneas 151–199) en lugar del token `.pedidos-input`, generando divergencia sutil de estilos.
- **Botones mezclados:** conviven `.pedidos-btn` (canon) con botones construidos con utilidades Tailwind sueltas (bloque de éxito, líneas 108–118).

---

## 8. Deuda técnica de presentación

- **Alpine monolítico:** `compraMayorista()` (~470 líneas de JS dentro de un template de ~720) concentra estado, formato, red, teclado, checkout y modo. Difícil de testear y de reutilizar en listados/detalle.
- **Lógica de embalaje huérfana:** estado presente, sin UI.
- **URLs por template string:** manipulación de plantillas de URL con regex (`detalleUrl`, `itemUrl`, líneas 376–378, 439) es frágil ante cambios de rutas.
- **Estilos duplicados:** inputs/botones repetidos inline vs tokens.

---

## 9. Síntesis de severidad

| # | Hallazgo | Severidad | Tipo |
|---|---|---|---|
| 1 | Total/confirmar no sticky en mobile | Alta | Flujo/Responsive |
| 2 | Checkout mezclado con carrito | Alta | Jerarquía/Flujo |
| 3 | Alpine monolítico inline | Alta | Deuda técnica |
| 4 | Embalaje sin selector (UOM) | Media-alta | Funcional/Flujo |
| 5 | `confirm()`/`prompt()` nativos | Media | a11y/Visual |
| 6 | Layout 2/3+1/3 comprime carrito | Media | Responsive |
| 7 | Modal sin `role="dialog"`/focus trap | Media | a11y |
| 8 | `flash` sin `aria-live` | Media | a11y |
| 9 | Tabla listado ancha en móvil | Media | Responsive |
| 10 | Hint barcode sin flujo/foco | Media | Flujo |
| 11 | Inputs/botones inline vs tokens | Baja | Visual/Consistencia |
| 12 | Cliente se limpia al refresh sin aviso | Baja | Microcopy |

Las soluciones se desarrollan en `03-flujo-propuesto.md` (flujo), `04-wireframe-conceptual.md` (estructura), `05-design-system-pedidos.md` (tokens), `06-componentes.md` (componentes) y `07-funcionalidades-propuestas.md` (clasificación de propuestas).
