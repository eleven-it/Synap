# Self-Checkout UI · Epic 7

Documentación de la interfaz del kiosco autoservicio Synap.

---

## Pantallas

| Pantalla | Descripción |
|----------|-------------|
| **Principal** | 2 columnas: Scan/Entrada (izq) y Carrito/Total/CTA (der) |
| **Email** | Modal obligatorio antes de pago |
| **RFID Confirm** | Modal para confirmar ítems detectados (agrupar, editar cantidades) |
| **Pago** | UI de estados (pendiente/aprobado/rechazado) — stub |
| **Comprobante** | Modal post-venta con opciones impresión/email |
| **Conexión** | Modal genérico si falla el servidor (sin credenciales) |

---

## Estados (máquina simple)

| Estado | Descripción |
|--------|-------------|
| `idle` | Listo para escanear |
| `scanning` | Agregando producto |
| `rfid_review` | Modal RFID abierto |
| `cart_ready` | Carrito con ítems, puede continuar |
| `email_required` | Modal email abierto |
| `paying` | Pantalla de pago |
| `confirming` | Enviando confirmación al backend |
| `success` | Compra exitosa |
| `error` | Error genérico |

---

## Refinamiento visual (plantillas)

Ajustes solo de HTML/Tailwind en `kiosco.html` e includes (`_header_kiosk`, `_search_scan`, `_promo_ofertas_footer`, `_cart_*`, `_payment_keypad`): jerarquía (total y CTA principal), menos ruido en la barra TPV (un contenedor con separadores), espaciado coherente en columnas y pie de carrito, textos de ayuda de búsqueda acotados sin duplicar el placeholder.

**Banner “Aprovecha nuestras ofertas”:** vive en `includes/_promo_ofertas_footer.html`, al pie de la tarjeta del kiosco (debajo del `main`), con `x-show="!modoTpv && estado !== 'success'"` — solo autoservicio, no TPV. En mobile (`_kiosk_main_mobile.html`) va justo encima de la barra fija inferior.

**Lista del carrito (columna derecha):** el contenedor de ítems usa `min-h-0` y `flex-[1_1_28rem]` sobre la tarjeta con `min-h-0` para que el scroll vertical sea interno (no se recorten filas por `overflow:hidden` del layout flex). La base `28rem` apunta a mostrar del orden de **10 líneas** de grilla TPV; con más ítems, scroll dentro de esa zona. Cabecera “Tus productos”, bloque de totales y teclado de pago llevan `shrink-0` donde aplica.

## Componentes UI

- **KioskHeader**: Cabecera con kiosk_id
- **ScanPanel**: Input siempre enfocado, feedback visual, botón agregar
- **CartPanel**: Lista ítems, +/- por ítem, quitar, total, CTA pago
- **RfidConfirmModal**: Ítems agrupados, editar cantidades, confirmar/cancelar
- **EmailCapture**: Input email con validación
- **PaymentStatus**: Badge estado (pendiente/aprobado/rechazado)
- **ReceiptOptionsModal**: Comprobante, opciones impresión/email (placeholder)
- **ConnectionErrorModal**: "Problemas de conexión con servidor \<host\>" — **sin usuarios ni claves**

## Foco en modales

Al abrir un modal del kiosco, el foco pasa al primer campo de formulario visible (`input`, `select` o `textarea` habilitado) dentro del overlay, cuando existe. En pantallas solo con botones no hay campo que enfocar. En el modal de factura, al cambiar de paso (p. ej. Ticket Factura / Consumidor Final con email) se vuelve a aplicar el mismo criterio. En el modal de números de serie, el foco se intenta tras terminar de cargar la lista.

## Atajos de teclado TPV

En la barra TPV del header, las etiquetas muestran la tecla entre paréntesis (p. ej. `Cliente (F1)`). En el header mobile, el atajo va junto al texto del chip.

Atajos activos solo cuando `modoTpv` está habilitado y no hay modal abierto.  
Se ejecutan aunque el foco esté en el input de búsqueda u otros campos editables.

- `F1`: abrir clientes
- `F2`: abrir listas de precio
- `F3`: abrir vendedor
- `F4`: abrir descuentos y vouchers
- `F5`: abrir cuenta corriente (solo si el cliente no es Consumidor final; el botón **Ver** de cta. cte. se muestra siempre y queda deshabilitado si no aplica)
- `F8`: eliminar la línea con foco en carrito (sin confirmación)
- `F12`: ir a pagar ahora

---

## Cómo probar

1. **Acceso**: `/self-checkout/kiosco/<kiosk_id>/` (ej: `kiosk-01`)
2. **Requisitos**: Usuario autenticado, permiso `self_checkout.kiosk`, empresa con base MySQL
3. **Flujo**:
   - Escanear o ingresar código de artículo
   - Ver carrito a la derecha
   - +/- para cambiar cantidad, ✕ para quitar
   - "Continuar al pago" → modal email
   - Ingresar email válido → modal pago
   - "Simular aprobado" (stub) → confirmación → pantalla éxito
   - "Nueva compra" para reiniciar

4. **RFID simulado**: Botón "Simular RFID masivo" → modal con ítems → editar cantidades → Confirmar

5. **Stock**: Si un ítem excede DISPONIBLE, se muestra mensaje y se bloquea el pago

6. **Conexión**: Desconectar red para ver modal de error (solo muestra host, sin credenciales)

---

## Stack

- Tailwind CSS (CDN)
- Alpine.js 3.x
- Plantillas Django

---

## Contrato JS para refactor Stitch (Alpine / DOM)

Al refactorizar los templates Stitch a Django (includes), los siguientes identificadores y atributos son **contrato obligatorio** y no deben cambiarse; cualquier include debe preservarlos en el mismo nodo o en uno que Alpine siga encontrando:

| Contrato | Uso |
|----------|-----|
| `x-ref="scanInput"` | Input escáner; focus y agregar por código |
| `id="tpv-busqueda-producto"` | Búsqueda predictiva TPV; teclado (↑↓ Enter) |
| `x-ref="busquedaDropdownList"` | Contenedor lista resultados búsqueda |
| `:data-search-index="index"` (en cada `<tr>`) | Selección por teclado en tabla búsqueda |
| `x-ref="descuentoInput"` | Descuento por ítem |
| `x-ref="descuentoPieInput"` | Descuento global al carrito |
| `x-ref="emailInputFa"` / `x-ref="emailInputCf"` | Inputs email en modales (Factura A / Consumidor Final) |
| Variables Alpine (x-show) para modales | modalSeries, modalTpvCliente, modalListaPrecio, modalVendedor, modalVouchers, modalCuentaCorriente, modalEmail, pantalla pago, post-venta |

Mapeo completo de templates Stitch a includes y tabla de contrato: [STITCH_TEMPLATES_MAP.md](STITCH_TEMPLATES_MAP.md).

---

## Sin datos sensibles

Los errores de conexión muestran únicamente `window.location.host`. Nunca se exponen usuarios, contraseñas ni tokens en la UI.
