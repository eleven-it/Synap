# Checklist refactor Stitch → Django (self_checkout)

Verificación de funcionalidad, dispositivo y responsive tras el refactor de templates.

---

## 1. Verificación funcional

Comprobar que todo lo siguiente sigue funcionando igual que antes del refactor:

- [ ] **Escaneo:** Input código de barras (self-checkout); agregar por código; feedback "Agregado" / error / stock insuficiente.
- [ ] **Búsqueda TPV:** Input `tpv-busqueda-producto`; ↑↓ para elegir en tabla; Enter para agregar; Tab/Esc para foco.
- [ ] **Carrito:** Lista ítems (vista TPV tabla y vista compacta); +/- cantidad; quitar ítem; descuento por ítem (x-ref `descuentoInput`); descuento al pie (x-ref `descuentoPieInput`).
- [ ] **Modales:** Cliente (búsqueda), Lista precio, Vendedor, Vouchers, Cuenta corriente, Series, Email (Factura A / Consumidor Final, x-ref `emailInputFa` / `emailInputCf`).
- [ ] **Pago:** Botón "Pagar"; flujo email → métodos de pago; estados paying/confirming; Mercado Pago / efectivo según backend.
- [ ] **Post-venta:** Pantalla éxito; imprimir ticket; Ver comprobante; Nueva compra.
- [ ] **Overlays:** AFIP fuera de línea; modal supervisor CAEA; modal fuera de servicio; modal confirmar eliminar ítem.

---

## 2. Verificación por dispositivo (mobile)

- [ ] Con `request.is_mobile` true (o User-Agent móvil), se sirve el template `self_checkout/mobile/kiosco.html`.
- [ ] Layout en mobile: columna única; carrito como bottom-sheet (max-height 45vh, handle visual).
- [ ] Toda la funcionalidad de la lista anterior funciona en mobile (escaneo, carrito, modales, pago, post-venta).
- [ ] Clases `.kiosk-main-two-cols`, `.kiosk-col-left`, `.kiosk-col-right` siguen siendo el objetivo de los overrides en `mobile/kiosco.html`.

---

## 3. Verificación responsive

- [ ] **Viewports:** Probar en 320px, 375px, 768px, 1024px, 1440px.
- [ ] **Orientación:** Portrait y landscape en móvil.
- [ ] **Modales:** En mobile usables en fullscreen o casi fullscreen; contenido no cortado.
- [ ] **Inputs:** En mobile, `font-size` ≥ 16px en inputs para evitar zoom no deseado en iOS.
- [ ] **Touch:** Botones y enlaces con min-height ≥ 44px (2.75rem) en mobile; sin delay 300ms (touch-action si aplica).
- [ ] **Safe area:** En dispositivos con notch, el bottom-sheet del carrito respeta `env(safe-area-inset-bottom)`.

---

## 4. Puntos de riesgo (contrato JS)

No cambiar sin actualizar Alpine/JS:

| Elemento | Uso |
|----------|-----|
| `x-ref="scanInput"` | Input escáner; focus y agregar por código |
| `id="tpv-busqueda-producto"` | Búsqueda predictiva TPV; teclado |
| `x-ref="busquedaDropdownList"` | Contenedor lista resultados búsqueda |
| `:data-search-index="index"` (en `<tr>`) | Selección por teclado en tabla búsqueda |
| `x-ref="descuentoInput"` | Descuento por ítem |
| `x-ref="descuentoPieInput"` | Descuento global al carrito |
| `x-ref="emailInputFa"` / `x-ref="emailInputCf"` | Inputs email en modales Factura A / Consumidor Final |
| Variables Alpine (x-show) para modales | modalSeries, modalTpvCliente, modalListaPrecio, modalVendedor, modalVouchers, modalCuentaCorriente, modalEmail, pantalla pago, post-venta |

---

## 5. Estructura de includes creada

- `includes/_header_kiosk.html` — Cabecera kiosco/TPV
- `includes/_context_bar_tpv.html` — Barra Cliente / Lista precio / Vendedor / Descuentos / Cta. corriente
- `includes/_search_scan.html` — Feedback scan, búsqueda por código, barra TPV, modal cuenta corriente, búsqueda predictiva TPV, opciones extra
- `includes/_cart_list.html` — Lista de ítems (vacío, tabla TPV, vista compacta)
- `includes/_cart_totals.html` — Descuento al pie + total
- `includes/_payment_keypad.html` — CTA "Pagar"
- `includes/_post_sale.html` — Pantalla éxito (imprimir, ver comprobante, nueva compra)

Los modales (email, cliente, vendedor, lista precio, vouchers, series, etc.) siguen inline en `kiosco.html`; pueden extraerse a includes en un siguiente paso.

---

## 6. Fase 3 — HTML exacto Stitch (no adaptación)

La UI usa el **HTML exacto** de los templates Stitch descargados; solo se inyectan bindings Alpine/Django (x-ref, id, x-model, x-on:click, x-text).

- **\_header_kiosk.html:** Header exacto `kiosk_active_cart_1`: logo/point_of_sale, "AdministraNET", "Retail Management System", barra TPV (Cliente, Lista de Precios, Vendedor, Descuentos y voucher, Cta. corriente), kioskId, fullscreen.
- **\_search_scan.html:** Card escaneo exacta Stitch ("Escanea tus productos", input + barcode_scanner, Búsqueda Teclado / Explorar Categorías), caja ofertas ámbar, búsqueda TPV (contrato id/tpv-busqueda-producto, busquedaDropdownList, data-search-index), opciones 3 botones. x-ref="scanInput".
- **\_cart_list.html:** Vacío y tabla exactos Stitch (shopping_cart_off, "Tu carrito está vacío"; tabla 4 cols Producto/Cant./Precio/Total). Tabla TPV con x-ref="descuentoInput".
- **\_cart_totals.html:** Totales exactos Stitch (Subtotal, Descuento Oferta, Impuestos, TOTAL). x-ref="descuentoPieInput" en bloque descuento al pie (modoTpv).
- **\_payment_keypad.html:** "Pagar ahora" + 3 botones (Tarjeta Regalo, Asistencia, Cancelar) exactos Stitch. irAPago().
- **\_post_sale.html:** Pantalla éxito exacta `pago_exitoso_y_ticket_digital`. comprobanteTexto, imprimirTicket(), mostrarReceipt, nuevaCompra().

En `kiosco.html`: Manrope + Material Symbols, Tailwind primary #2b6cee, background-light/dark; main/aside con estructura Stitch (flex-[1.2], flex-1, gap-6, p-8). Barra TPV integrada en header (no include _context_bar_tpv).

---

## 7. Base TPV

- `base_tpv.html` existe y define viewport + bloques (title, extra_css, content, extra_js). Opcional: hacer que `kiosco.html` extienda `base_tpv.html` en lugar de `base_app.html` y usar `{{ block.super }}` en extra_css para conservar viewport.
