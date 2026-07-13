# 00 · Resumen ejecutivo — Rediseño UI de toma de pedidos

- **Módulo:** Gestión de pedidos (Ventas · Pedidos) — App `ecom` / mayoristapp
- **Pantalla canónica:** `/ecom/mayoristapp/compra/` (`ecom/templates/ecom/compra_mayorista.html`)
- **Fecha:** 10/07/2026
- **Estado implementación:** ✅ **F1–F5 completas** (39/39 tareas SDD). Ver `10-estado-implementacion.md`.
- **Autor:** Product Designer Senior / UX ERP
- **Alcance:** Rediseño de presentación (frontend) — sin cambios de backend, modelos, APIs, cálculos ni permisos
- **Canon UI de referencia:** familia reportes/MPR (slate/sky). NO se toma como referencia visual ventas/presupuestos legacy.

---

## 1. Estado actual

> **Actualización 10/07/2026:** el rediseño OrderShell está **implementado** (F1–F5). La descripción siguiente refleja el estado **pre-rediseño** como referencia histórica; el estado actual se documenta en `10-estado-implementacion.md`.

La pantalla de toma de pedidos ya está migrada al canon Synap (reportes/MPR, familia slate/sky) sobre el stack **Django templates + Tailwind + Alpine 3 + fetch JSON**. Hereda el layout `ecom/templates/ecom/base_pedidos.html` y los tokens de `ecom/templates/ecom/includes/pedidos_page_styles.html` (clases `.pedidos-*` y `.compra-*`).

**Post-rediseño:** el componente `compraMayorista()` vive en módulos `.mjs` (`compra_mayorista_app.mjs` + mixins por dominio). La pantalla usa **OrderShell** de cinco regiones (header sticky, captura, líneas, summary sticky/bottom bar, secundario colapsable). Los modales de compra usan el canon (`order_dialogs.mjs` + `pedidos_modal.html`); no `confirm()` nativo en flujo compra.

El componente central **antes del rediseño** era el objeto Alpine `compraMayorista()` definido inline dentro de `compra_mayorista.html`, que orquestaba:

- Selección de **cliente predictivo** (dropdown único, no restaura sesión al refrescar; ver `ecom/static/ecom/js/compra_mayorista_cliente.mjs`).
- **Filtro de marcas** (`ecom/static/ecom/js/compra_mayorista_marcas.mjs`, include `includes/filtro_marcas_tags.html`).
- **Búsqueda de artículos estilo TPV** con navegación por teclado ↑ ↓ Enter (`ecom/templates/ecom/includes/pedidos_busqueda_articulos_tpv.html`).
- **Carrito** en panel derecho: cantidades, quitar, vaciar, descuento al pie %, punto de venta, forma de entrega, observaciones.
- **Totales** siempre calculados en backend (`serializar_carrito`) y devueltos por las APIs: neto, IVA, impuesto interno y total.
- **Checkout** vía modal de pre-confirmación → `POST checkout/confirmar`.
- **Modos de comprobante** PED / PRE / DEV (toggle en el hero, `ecom/templates/ecom/includes/pedidos_toggle_comprobante.html`).
- **Repetir pedido** (`ecom/static/ecom/js/repetir_pedido_modal.js`) y conversión PRE → PED.
- **Promociones** (filtro "Solo promociones" + badge) y estados de **empty/loading**.

El carrito funciona como **borrador persistente (EcomCart)**: los renglones sobreviven entre recargas mientras la sesión mantenga el carrito.

**Política de negocio confirmada:** no existe edición de pedidos ya confirmados; el patrón operativo es **anular + repetir**. Esto se mantiene sin cambios en el rediseño.

### Pantallas secundarias (coherencia, no foco primario)

- Hub: `ecom/templates/ecom/pedidos_hub.html`
- Listado pedidos: `ecom/templates/ecom/pedidos_vendedor.html` + `ecom/static/ecom/js/pedidos_vendedor.js`
- Listado presupuestos: `ecom/templates/ecom/presupuestos_vendedor.html`
- Detalle de pedido: `ecom/templates/ecom/pedido_detalle.html`
- Detalle comprobante comercial (PRE/DEV): `ecom/templates/ecom/comprobante_comercial_detalle.html`

---

## 2. Problemas principales

Ordenados por impacto sobre la operación (detalle en `02-diagnostico-ux-ui.md`):

1. **Layout 2/3 + 1/3 comprime el carrito.** En el grid `md:grid-cols-3` el catálogo ocupa 2 columnas y el carrito+checkout 1; en resoluciones intermedias el panel derecho queda estrecho y con scroll interno limitado (`compra-carrito-scroll` con `max-height: 46vh` en desktop).
2. **Checkout mezclado con el carrito.** Punto de venta, forma de entrega y observaciones viven en el mismo panel que las líneas, restando protagonismo a la acción de confirmar y saturando visualmente el flujo.
3. **Total no sticky en mobile.** El total y el botón de confirmar quedan al final del documento; en móvil obligan a scrollear todo el carrito para operar.
4. **Lógica Alpine monolítica.** El objeto `compraMayorista()` vive inline en el template (~700 líneas), mezclando estado, formato de moneda, llamadas a API, navegación de teclado y flujo de checkout. Difícil de mantener, testear y reutilizar.
5. **Confirm/prompt nativos.** Cambio de tipo de comprobante usa `confirm()` nativo; acciones como anular/enviar mail (en detalle) usan diálogos del navegador, rompiendo la consistencia visual con el canon Synap.
6. **Embalaje sin selector.** El backend expone presentación/UOM (`tipo_unidad`, `presentacion.opciones`, multiplicador) y el carrito muestra "Embalaje: …", pero la UI **siempre envía "Unidad"**: no hay forma de elegir bulto/display.
7. **Filtros ocultos / hint de barcode sin flujo.** El placeholder de búsqueda menciona "Código de barras" pero no hay flujo de escaneo dedicado ni foco garantizado. Los filtros (marcas, promo) están presentes pero con jerarquía inconsistente.
8. **Tabla de listado ancha en móvil.** Las pantallas secundarias de listado no degradan bien a tarjetas en pantallas chicas.
9. **Cliente se limpia al refresh.** Es intencional por diseño, pero no se comunica al usuario y puede percibirse como pérdida de trabajo.

---

## 3. Riesgos

- **Regresión de cálculos:** cualquier intento de mover lógica de totales al frontend rompería la fuente de verdad. **Mitigación:** los precios/totales siguen viniendo de `serializar_carrito`; el frontend solo presenta.
- **Divergencia del canon:** introducir un sistema visual paralelo (p. ej. purple-on-white genérico) rompería la consistencia con reportes/MPR. **Mitigación:** extender tokens `.pedidos-*`, no inventar.
- **Ruptura de contrato Alpine:** los includes dependen de nombres de estado/métodos concretos (`searchProductos`, `articulosGrid`, `selectedSearchIndex`, `soloPromo`, `$refs.busquedaDropdownList`, `cambiarTipo`, `money`, etc.). Refactorizar sin preservar el contrato rompería la pantalla. **Mitigación:** refactor incremental conservando la API pública del componente.
- **Expectativas de negocio no validadas:** funciones como selector de lista de precios, condición de venta, sucursal/depósito o edición de confirmados requieren definición de producto antes de tocarse.
- **Rendimiento en dispositivos de mostrador:** operadores intensivos en equipos modestos; animaciones/efectos deben mantenerse suaves y funcionales, sin costo de render.

---

## 4. Oportunidades

- **Shell unificado de pedido (OrderShell):** convertir el flujo en un contenedor claro con header sticky (cliente + modo + acciones), zona de productos dominante, líneas y summary sticky. Mejora foco y velocidad.
- **Summary sticky responsive:** lateral en desktop, barra inferior fija en mobile → confirmar siempre a un toque.
- **Secciones secundarias colapsables:** entrega y observaciones fuera del camino crítico, plegadas por defecto.
- **Componentización de includes y modularización de Alpine:** extraer el objeto a módulos `.mjs` reutilizables (sin romper contrato) y dividir la vista en includes con responsabilidad única.
- **Aprovechar APIs ya existentes sin costo backend:** productos más vendidos/frecuentes, repetir pedido, presentación/UOM, alta rápida de cliente y domicilio ya están soportados por el backend; habilitarlos en UI es principalmente trabajo de presentación (ver `07-funcionalidades-propuestas.md`).
- **Mejoras puramente frontend:** clientes recientes en `localStorage`, autoguardado visible (el carrito ya es borrador), diálogo de cambios sin guardar, atajos de teclado, reemplazo de confirm/prompt nativos por modales del canon.

---

## 5. Visión del rediseño

> Una **estación de carga dinámica para vendedores**: máxima velocidad operativa, contexto comercial siempre a mano y confirmación segura — sin forzar metáforas de “carrito e-com” ni de “formulario ERP clásico”.

### Decisión de producto (10/07/2026)

**Criterio único:** la mejor opción para vendedores que cargan muchos pedidos al día.  
**No es criterio:** “parecer ERP” ni “parecer carrito de compras”.

Se toma de cada patrón solo lo que acelera la operación:

| De la velocidad TPV / captura continua | Del contexto comercial ERP |
|---|---|
| Búsqueda dominante + teclado (↑↓ Enter) | Cliente, crédito y modo PED/PRE/DEV visibles |
| Agregar sin modal por cada ítem | Líneas editables (cant., UOM) como superficie de trabajo |
| Total y confirmar siempre a un toque | Totales/precios solo del backend; sin recalcular en FE |
| Flujo continuo: buscar → agregar → seguir | Entrega/obs fuera del camino crítico |

**Modelo mental del usuario:** “estoy armando un pedido”, no “estoy comprando en una tienda” ni “estoy llenando un formulario denso”. El lenguaje de UI sigue ese trabajo (pedido, líneas, confirmar) cuando ayuda a la claridad; no se usa “carrito” como metáfora principal.

Principios rectores (alineados con `.impeccable.md`):

1. **Dinámica del vendedor primero** — menos clics, teclado, cambio rápido de cliente/producto.
2. **Claridad sobre novedad** — jerarquía estable; una acción primaria por región.
3. **Reutilizar antes de crear** — extender reportes/MPR y tokens `.pedidos-*`.
4. **El backend manda en los números** — el frontend nunca calcula precios ni totales.
5. **Consistencia multi-dispositivo** — mismo modelo mental en desktop/tablet/mobile.

### Estructura objetivo (OrderShell)

- **Header sticky:** cliente + modo (PED/PRE/DEV) + acciones frecuentes.
- **Captura de productos:** búsqueda TPV dominante (foco continuo).
- **Líneas del pedido:** tabla desktop / cards mobile (superficie principal de edición).
- **Resumen sticky:** totales + confirmar (lateral desktop / barra inferior mobile).
- **Secundario colapsable:** entrega y observaciones.

El detalle vive en `04-wireframe-conceptual.md`; el mapeo a componentes reales en `06-componentes.md`.

---

## 6. Alcance

**Foco primario:** `compra_mayorista` (toma de pedidos) + shell de pedidos (`base_pedidos.html`, tokens `pedidos_page_styles.html`, includes de la pantalla de compra).

**Foco secundario (coherencia):** listados y detalle (hub, listado, detalle de pedido, detalle comprobante comercial) se ajustan solo para mantener coherencia visual con el nuevo shell; no son el objetivo primario del rediseño.

**Fuera de alcance (explícito):** backend, modelos, APIs, cálculos, permisos, `.env`. Toda propuesta que requiera tocar estos aspectos se etiqueta como *"Requiere extensión backend"*, *"Requiere validación de negocio"* o *"Recomendación futura"* en `07-funcionalidades-propuestas.md`.

---

## 7. Beneficio esperado

| Dimensión | Estado actual | Con rediseño |
|---|---|---|
| Tiempo de alta de un pedido | Alto (scroll, foco disperso, carrito comprimido) | Menor (búsqueda dominante, teclado, summary sticky) |
| Fricción en mobile | Alta (total no sticky, tabla ancha) | Baja (bottom bar, cards) |
| Consistencia visual | Buena en compra, dispar en secundarias | Uniforme en todo el módulo |
| Mantenibilidad del código | Baja (Alpine monolítico ~700 líneas) | Alta (includes + módulos `.mjs`) |
| Errores de operación | Confirm/prompt nativos, embalaje ambiguo | Modales del canon, selección explícita de UOM |
| Reutilización | Includes parciales | Componentes con responsabilidad única |

**Resultado esperado:** una pantalla de pedidos más rápida de operar, más fácil de mantener y visualmente coherente con el resto de Synap, sin ningún cambio en la lógica de negocio ni en los números que el backend calcula.
