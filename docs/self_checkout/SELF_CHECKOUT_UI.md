# Self-Checkout UI · Epic 7

Documentación de la interfaz del kiosco autoservicio Synap.

**Modos:** la misma plantilla `kiosco.html` soporta **autoservicio** (`modoTpv === false`) y **TPV / mostrador** (`modoTpv === true`). Las extensiones de **paridad con AdministraNET** (`TPV.frm`: cobros, stock, reglas de negocio extendidas) aplican **solo en modo TPV**; el autoservicio no debe acumular esos pasos salvo decisión explícita. Ver [PARIDAD_TPV_ADMINISTRANET_ALCANCE.md](../general/PARIDAD_TPV_ADMINISTRANET_ALCANCE.md).

### Precheck negocio TPV (servidor)

Si el kiosco está en **modo TPV**, antes de confirmar la venta el servidor puede rechazar la operación por **permisos del puesto** (`obliga_selecpv`, `obliga_cambvendedor`), **crédito del cliente** o **tope de efectivo en caja** (`caja_abm`). Los mensajes usan códigos `E_TPV_OBLIGA_*`, `E_TPV_CREDITO_EXCEDIDO`, `E_TPV_LIMITE_EFECTIVO_CAJA` y se muestran como toast sin modal de fuera de servicio. Detalle: `TPV_PRECHECK_PERMISOS_LEGACY.md`.

### Series obligatorias (solo `modoTpv` en cliente)

Si el ítem viene del catálogo como seriado (`articulo.serie = 'Si'`), la API incluye `requiere_series` en cada línea del carrito. En **modo TPV**, no se abre el flujo de cobro (ni se llama a confirmar) hasta que cada línea pendiente tenga números asignados (`serie === 'Si'` en la línea). El servidor valida siempre que la cantidad de filas en `self_checkout_cart_item_serie` coincida con la cantidad vendida.

### Validación de medios de cobro (solo `modoTpv`)

En **TPV**, antes de llamar a `POST …/cart/<id>/confirm/`, el cliente comprueba que **efectivo + tarjeta + intereses** coincida con el total del carrito (tolerancia **±0,02**), alineado a `TPV.frm`. Si los importes explícitos suman **cero**, se muestra el mensaje equivalente a «al menos un medio». El servidor repite la misma regla **solo** si el kiosco tiene `modo_tpv` activo en `self_checkout_kiosk`; en caso contrario el flujo autoservicio no aplica estas validaciones. Respuestas API estables: `E_TPV_MEDIOS_TOTAL`, `E_TPV_MEDIOS_VACIOS` (no activan el modal genérico «fuera de servicio»).

---

## Pantallas

| Pantalla | Descripción |
|----------|-------------|
| **Principal** | 2 columnas: Scan/Entrada (izq) y Carrito/Total/CTA (der) |
| **Email** | Modal obligatorio antes de pago |
| **RFID Confirm** | Modal para confirmar ítems detectados (agrupar, editar cantidades) |
| **Pago** | Modal de cobro; al confirmarse la venta se cierra el modal y se llama `limpiarBuscadorArticulos()` (vacía búsqueda TPV, tabla de resultados y campo escáner autoservicio). En «Nueva compra» se repite la limpieza por si el estado quedó residual |
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

## Ticket impresión (`ticket_print.html`)

- **Datos:** `_get_ticket_data` (`self_checkout/views.py`) calcula `precio_unitario_ticket`: en **FB/FC** es `importe_total / cantidad`; en **FA** coincide con `precio_unitario` (neto). Si `total − subtotal` es relevante, `diferencia_impuestos` y filas **Subtotal neto**, **IVA / impuestos** (opcional) y **TOTAL**.
- **Layout:** cabecera emisor, bloque tipo/número/fecha (`Fecha: dd/mm/yyyy hh:mm`), cliente, totales en **tabla** y pie como en el diseño previo. Solo la sección **detalle de ítems** usa bloques multilínea (cantidad × P. unit., descripción, alícuota + importe) para evitar solapes en 80 mm. `overflow-x: hidden` en `body` y contenedor.
- **Copia de seguridad:** versión tabular íntegra anterior en `ticket_print.html.backup-antes-multiline`.

---

## Sin datos sensibles

Los errores de conexión muestran únicamente `window.location.host`. Nunca se exponen usuarios, contraseñas ni tokens en la UI.
